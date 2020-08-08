import boto3
import logging
import os
import config
import datetime
import re
import json
import time
from dateutil.parser import parse
from models import db, WindowsDCVSessions
from botocore.exceptions import ClientError
from models import db
logger = logging.getLogger("api_log")
client_ec2 = boto3.client("ec2")
client_ssm = boto3.client("ssm")


def retrieve_host(instance_state, hibernate):
    host_info = {}
    token = True
    next_token = ''
    while token is True:
        response = client_ec2.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': instance_state
                },
                {
                    'Name': 'tag:soca:JobQueue',
                    'Values': ["desktop"]
                },
                {
                    "Name": "tag:soca:ClusterId",
                    "Values": [os.environ["SOCA_CONFIGURATION"]]
                },
                {
                    "Name": "tag:soca:DCVSupportHibernate",
                    "Values": hibernate
                },
                {
                    "Name": "tag:soca:NodeType",
                    "Values": ["soca-dcv-windows"]
                }
            ],
            MaxResults=1000,
            NextToken=next_token,
        )

        try:
            next_token = response['NextToken']
        except KeyError:
            token = False

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                current_time = parse(response['ResponseMetadata']['HTTPHeaders']['date'])
                if instance_state == "stopped":
                    stopped_time = parse(re.findall('.*\((.*)\)', instance["StateTransitionReason"])[0])
                else:
                    stopped_time = False
                host_info[instance["InstanceId"]] = {"stopped_time": stopped_time,
                                                     "current_time": current_time}

    return host_info


def auto_hibernate_instance():
    with db.app.app_context():
        logger.info("Scheduled Task: auto_hibernate_instance")
        hibernate_idle_instance_after = config.Config.DCV_WINDOWS_HIBERNATE_IDLE_SESSION
        if hibernate_idle_instance_after > 0:
            get_host_to_hibernate = retrieve_host(instance_state=["running"], hibernate=["true"])
            logger.info("List of hosts that are subject to hibernation if inactive for more than {} hours: {}".format(hibernate_idle_instance_after,get_host_to_hibernate))
            for instance_id in get_host_to_hibernate.keys():
                logger.info("Checking Instance ID: {}".format(instance_id))
                ssm_failed = False
                ssm_list_command_loop = 0
                powershell_command = ["Invoke-Expression \"& 'C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv' describe-session console -j\""]
                try:
                    check_dcv_session = client_ssm.send_command(InstanceIds=[instance_id],
                                                                DocumentName='AWS-RunPowerShellScript',
                                                                Parameters={"commands": powershell_command},
                                                                TimeoutSeconds=30)
                except ClientError as e:
                    logger.error("Unable to query SSM for {} : {}".format(instance_id, e))
                    if "InvalidInstanceId" in str(e):
                        logger.error("Instance is not in Running state or SSM daemon is not running. This instance is probably still starting up ...")
                    ssm_failed = True

                if ssm_failed is False:
                    ssm_command_id = check_dcv_session["Command"]["CommandId"]
                    while ssm_list_command_loop < 6:
                        check_command_status = client_ssm.list_commands(CommandId=ssm_command_id)['Commands'][0]['Status']
                        if check_command_status != "Success":
                            logger.error("SSM command ({}) executed but did not succeed or failed yet. Waiting 20 seconds ... {} ".format(ssm_command_id, client_ssm.list_commands(CommandId=ssm_command_id)['Commands']))
                            if check_command_status == "Failed":
                                logger.error("Unable to query DCV for {} with SSM id ".format(instance_id, ssm_command_id))
                                ssm_failed = True
                            time.sleep(20)
                            ssm_list_command_loop += 1
                        else:
                            break

                if ssm_list_command_loop >= 5:
                    logger.error("Unable to determine status SSM responses after 2 minutes timemout for {} : {} ".format(ssm_command_id, str(client_ssm.list_commands(CommandId=ssm_command_id))))
                    ssm_failed = True

                if ssm_failed is False:
                    ssm_output = client_ssm.get_command_invocation(CommandId=ssm_command_id, InstanceId=instance_id)
                    session_info = json.loads(ssm_output["StandardOutputContent"])
                    session_current_connection = session_info["num-of-connections"]
                    if not session_info["last-disconnection-time"]:
                        # handle case where user launched DCV but never accessed it
                        last_dcv_disconnect = parse(session_info["creation-time"])
                    else:
                        last_dcv_disconnect = parse(session_info["last-disconnection-time"])
                    if session_current_connection == 0:
                        current_time = parse(datetime.datetime.now().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat())
                        if (last_dcv_disconnect + datetime.timedelta(hours=hibernate_idle_instance_after)) < current_time:
                            logger.info("{} is ready for hibernation. Last access time {}".format(instance_id, last_dcv_disconnect))
                            try:
                                client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True, DryRun=True)
                            except ClientError as e:
                                if e.response['Error'].get('Code') == 'DryRunOperation':
                                    client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True)
                                    logging.info("Stopped {}".format(instance_id))
                                    try:
                                        check_session = WindowsDCVSessions.query.filter_by(session_instance_id=instance_id,
                                                                                           session_state="running",
                                                                                           is_active=True).first()
                                        if check_session:
                                            check_session.session_state = "stopped"
                                            db.session.commit()
                                            logger.info("DB entry updated")
                                        else:
                                            logger.error("Instance ({}) has been stopped but could not find associated database entry".format(instance_id), "error")
                                    except Exception as e:
                                        logger.error("SQL Query error:".format(e), "error")
                                else:
                                    logger.error("Unable to hibernate instance ({}) due to {}".format(instance_id, e), "error")
                        else:
                            logger.info("{} NOT ready for hibernation. Last access time {}".format(instance_id, last_dcv_disconnect))
                    else:
                        logger.info("{} currently has active DCV sessions")
                else:
                    logger.error("SSM failed for {} with ssm_id {}".format(instance_id, ssm_command_id))


def auto_terminate_stopped_instance():
    with db.app.app_context():
        logger.info("Scheduled Task: auto_terminate_stopped_instance")
        terminate_stopped_instance_after = config.Config.DCV_WINDOWS_TERMINATE_STOPPED_SESSION  # in hours
        if terminate_stopped_instance_after > 0:
            get_host_to_terminate = retrieve_host(instance_state=["stopped"], hibernate=["true", "false"])
            logger.info("List of hosts that are subject to termination if stopped for more than {} hours: {}".format(terminate_stopped_instance_after, get_host_to_terminate))
            for instance_id, time_info in get_host_to_terminate.items():
                if (time_info["stopped_time"] + datetime.timedelta(hours=terminate_stopped_instance_after)) < time_info["current_time"]:
                    logger.info("Instance {} is ready to be terminated".format(instance_id))
                    try:
                        client_ec2.terminate_instances(InstanceIds=[instance_id], DryRun=True)
                    except ClientError as e:
                        if e.response['Error'].get('Code') == 'DryRunOperation':
                            client_ec2.terminate_instances(InstanceIds=[instance_id])
                            try:
                                check_session = WindowsDCVSessions.query.filter_by(session_instance_id=instance_id,
                                                                                   session_state="running",
                                                                                   is_active=True).first()
                                if check_session:
                                    check_session.is_active = False
                                    check_session.deactivated_in = datetime.datetime.utcnow()
                                    db.session.commit()
                                    logger.info("{} has been terminated and set to inactive on the database.".format(instance_id))
                                else:
                                    logger.error("Instance ({}) has been stopped but could not find associated database entry".format(instance_id), "error")
                            except Exception as e:
                                logger.error("SQL Query error:".format(e), "error")
                        else:
                            logger.error("Unable to delete associated instance ({}) due to {}".format(instance_id, e))
                else:
                    logger.info("Stopped instance ({}) is not ready to be terminated. Instance was stopped at: {}".format(instance_id, time_info["stopped_time"]))


def auto_terminate_instance():
    with db.app.app_context():
        logger.info("Scheduled Task: auto_terminate_instance")
        terminate_session_after = config.Config.DCV_WINDOWS_TERMINATE_SESSION  # in hours
        if terminate_session_after > 0:
            if config.Config.DCV_WINDOWS_TERMINATE_RUNNING_SESSION_THAT_CAN_BE_STOPPED is True:
                logger.info("DCV_WINDOWS_TERMINATE_RUNNING_SESSION_THAT_CAN_BE_STOPPED is set to True. Running instances that can be hibernated will be directly terminated if eligible.")
                get_host_to_terminate = retrieve_host(instance_state=["running", "stopped"], hibernate=["true", "false"])
            else:
                logger.info("DCV_WINDOWS_TERMINATE_RUNNING_SESSION_THAT_CAN_BE_STOPPED is set to False. Only running instances that CANNOT be hibernated will he terminated.")
                get_host_to_terminate = retrieve_host(instance_state=["running"], hibernate=["false"])

            for instance_id, time_info in get_host_to_terminate.items():
                if (time_info["stopped_time"] + datetime.timedelta(hours=terminate_session_after)) < time_info["current_time"]:
                    try:
                        client_ec2.terminate_instances(InstanceIds=[instance_id], DryRun=True)
                    except ClientError as e:
                        if e.response['Error'].get('Code') == 'DryRunOperation':
                            client_ec2.terminate_instances(InstanceIds=[instance_id])
                            try:
                                check_session = WindowsDCVSessions.query.filter_by(session_instance_id=instance_id,
                                                                                   session_state="running",
                                                                                   is_active=True).first()
                                if check_session:
                                    check_session.is_active = False
                                    check_session.deactivated_in = datetime.datetime.utcnow()
                                    db.session.commit()
                                    logger.info("{} has been set to terminated and inactive on the database.".format(instance_id))
                                else:
                                    logger.error("Instance ({}) has been terminated but could not find associated database entry".format(instance_id), "error")
                            except Exception as e:
                                logger.error("SQL Query error:".format(e), "error")
                        else:
                            logger.error("Unable to delete associated instance ({}) due to {}".format(instance_id, e))
                else:
                    logger.info("stopped instance ({}) is not ready to be terminated. terminate_stopped_instance_after: {}".format(instance_id, terminate_session_after))