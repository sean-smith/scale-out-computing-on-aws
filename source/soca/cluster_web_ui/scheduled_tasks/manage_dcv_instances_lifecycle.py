import boto3
import logging
import os
import config
import datetime
import re
import json
import time
from dateutil.parser import parse
from models import db, WindowsDCVSessions, LinuxDCVSessions
from botocore.exceptions import ClientError
from models import db
logger = logging.getLogger("scheduled_tasks")
client_ec2 = boto3.client("ec2")
client_ssm = boto3.client("ssm")


def retrieve_host(instance_state, operating_system):
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
                    "Name": "tag:soca:ClusterId",
                    "Values": [os.environ["SOCA_CONFIGURATION"]]
                },
                {
                    "Name": "tag:soca:DCVSupportHibernate",
                    "Values": ["true", "false"]
                },
                {
                    "Name": "tag:soca:NodeType",
                    "Values": ["soca-dcv"]
                },
                {
                    "Name": "tag:soca:DCVSystem",
                    "Values": [operating_system]
                },
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
                session_uuid = False
                current_time = parse(response['ResponseMetadata']['HTTPHeaders']['date'])
                if instance_state == "stopped":
                    stopped_time = parse(re.findall('.*\((.*)\)', instance["StateTransitionReason"])[0])
                else:
                    stopped_time = False
                for instance in reservation['Instances']:
                    hibernate_enabled = False
                    for tag in instance["Tags"]:
                        if tag["Key"] == "soca:DCVSupportHibernate":
                            if tag["Value"] == "true":
                                hibernate_enabled = True
                            if tag["Key"] == "soca:DCVSessionUUID":
                                session_uuid = tag["Value"]

                    host_info[instance["InstanceId"]] = {"stopped_time": stopped_time,
                                                         "current_time": current_time,
                                                         "hibernate_enabled": hibernate_enabled,
                                                         "session_uuid": session_uuid}

    return host_info


def windows_auto_stop_instance():
    # Automatically stop or hibernate (when possible) instances based on Idle time and CPU usage
    with db.app.app_context():
        logger.info("Scheduled Task: auto_stop_instance {}")
        get_host_to_stop = retrieve_host(["running"], "windows")
        logger.info("List of DCV hosts subject to stop/hibernate {}".format(get_host_to_stop))
        for instance_id, instance_data in get_host_to_stop.items():
            if instance_data["hibernate_enabled"] is True:
                action = "hibernate"
                stop_instance_after = config.Config.DCV_WINDOWS_HIBERNATE_IDLE_SESSION
            else:
                action = "stop"
                stop_instance_after = config.Config.DCV_WINDOWS_STOP_IDLE_SESSION

            logger.info("Trying to {} instance {} if idle for more than {} hours and  CPU % is below {}".format(action,
                                                                                                            instance_id,
                                                                                                            stop_instance_after,
                                                                                                            config.Config.DCV_IDLE_CPU_THRESHOLD))
            if stop_instance_after > 0:
                for instance_id in get_host_to_stop.keys():
                    logger.info("Checking Instance ID: {}".format(instance_id))
                    ssm_failed = False
                    ssm_list_command_loop = 0
                    powershell_commands = [
                        "$DCV_Describe_Session = Invoke-Expression \"& 'C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv' describe-session console -j\" | ConvertFrom-Json",
                        "$CPUAveragePerformanceLast10Secs = (GET-COUNTER -Counter \"\\Processor(_Total)\\% Processor Time\" -SampleInterval 2 -MaxSamples 5 |select -ExpandProperty countersamples | select -ExpandProperty cookedvalue | Measure-Object -Average).average",
                        "$output = @{}",
                        "$output[\"CPUAveragePerformanceLast10Secs\"] = $CPUAveragePerformanceLast10Secs",
                        "$output[\"DCVCurrentConnections\"] = $DCV_Describe_Session.\"num-of-connections\"",
                        "$output[\"DCVCreationTime\"] = $DCV_Describe_Session.\"creation-time\"",
                        "$output[\"DCVLastDisconnectTime\"] = $DCV_Describe_Session.\"last-disconnection-time\"",
                        "$output | ConvertTo-Json"]

                    try:
                        check_dcv_session = client_ssm.send_command(InstanceIds=[instance_id],
                                                                    DocumentName='AWS-RunPowerShellScript',
                                                                    Parameters={"commands": powershell_commands},
                                                                    TimeoutSeconds=30)
                    except ClientError as e:
                        logger.error("Unable to query SSM for {} : {}".format(instance_id, e))
                        if "InvalidInstanceId" in str(e):
                            logger.error(
                                "Instance is not in Running state or SSM daemon is not running. This instance is probably still starting up ...")
                        ssm_failed = True

                    if ssm_failed is False:
                        ssm_command_id = check_dcv_session["Command"]["CommandId"]
                        while ssm_list_command_loop < 6:
                            check_command_status = \
                            client_ssm.list_commands(CommandId=ssm_command_id)['Commands'][0]['Status']
                            if check_command_status != "Success":
                                logger.info("SSM command ({}) executed but did not succeed or failed yet. Waiting 20 seconds ... {} ".format(ssm_command_id, client_ssm.list_commands(CommandId=ssm_command_id)['Commands']))
                                if check_command_status == "Failed":
                                    logger.error("Unable to query DCV for {} with SSM id ".format(instance_id,ssm_command_id))
                                    ssm_failed = True
                                    break
                                time.sleep(20)
                                ssm_list_command_loop += 1
                            else:
                                break

                    if ssm_list_command_loop >= 5:
                       logger.error("Unable to determine status SSM responses after 2 minutes timeout for {} : {} ".format(ssm_command_id, str(client_ssm.list_commands(CommandId=ssm_command_id))))
                       ssm_failed = True

                    if ssm_failed is False:
                        ssm_output = client_ssm.get_command_invocation(CommandId=ssm_command_id,InstanceId=instance_id)
                        session_info = json.loads(ssm_output["StandardOutputContent"])
                        session_current_connection = session_info["DCVCurrentConnections"]
                        if not session_info["DCVLastDisconnectTime"]:
                            # handle case where user launched DCV but never accessed it
                            last_dcv_disconnect = parse(session_info["DCVCreationTime"])
                        else:
                            last_dcv_disconnect = parse(session_info["DCVLastDisconnectTime"])
                        logger.info(session_info)
                        session_cpu_average = session_info["CPUAveragePerformanceLast10Secs"]
                        if session_cpu_average < config.Config.DCV_IDLE_CPU_THRESHOLD:
                            if session_current_connection == 0:
                                current_time = parse(datetime.datetime.now().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat())
                                if (last_dcv_disconnect + datetime.timedelta(hours=stop_instance_after)) < current_time:
                                    logger.info("{} is ready for {}. Last access time {}".format(instance_id, action, last_dcv_disconnect))
                                    try:
                                        if action == "hibernate":
                                            client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True, DryRun=True)
                                        else:
                                            client_ec2.stop_instances(InstanceIds=[instance_id], DryRun=True)
                                    except ClientError as e:
                                        if e.response['Error'].get('Code') == 'DryRunOperation':
                                            if action == "hibernate":
                                                client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True)
                                            else:
                                                client_ec2.stop_instances(InstanceIds=[instance_id])

                                            logging.info("Stopped {}".format(instance_id))
                                            try:
                                                check_session = WindowsDCVSessions.query.filter_by(session_instance_id=instance_id, session_state="running", is_active=True).first()
                                                if check_session:
                                                    check_session.session_state = "stopped"
                                                    db.session.commit()
                                                    logger.info("DB entry updated")
                                                else:
                                                    logger.error("Instance ({}) has been stopped but could not find associated database entry".format(instance_id), "error")
                                            except Exception as e:
                                                logger.error("SQL Query error:".format(e), "error")
                                        else:
                                            logger.error("Unable to {} instance ({}) due to {}".format(action, instance_id,e), "error")
                                else:
                                    logger.info("{} NOT ready for {}. Last access time {}".format(instance_id, action,last_dcv_disconnect))
                            else:
                                logger.info("{} currently has active DCV sessions".format(instance_id))
                        else:
                            logger.info("CPU usage {} is above threshold {} so this host won't be subject to {}.".format(session_cpu_average, config.Config.DCV_IDLE_CPU_THRESHOLD, action))
                    else:
                        logger.error("SSM failed for {} with ssm_id {}".format(instance_id, ssm_command_id))


def linux_auto_stop_instance():
    # Automatically stop or hibernate (when possible) instances based on Idle time and CPU usage
    with db.app.app_context():
        logger.info("Scheduled Task: auto_stop_instance {} ")
        get_host_to_stop = retrieve_host(["running"], "linux")
        logger.info("List of DCV hosts subject to stop/hibernate {}".format(get_host_to_stop))
        for instance_id, instance_data in get_host_to_stop.items():
            if instance_data["hibernate_enabled"] is True:
                action = "hibernate"
                stop_instance_after = config.Config.DCV_LINUX_HIBERNATE_IDLE_SESSION
            else:
                action = "stop"
                stop_instance_after = config.Config.DCV_LINUX_STOP_IDLE_SESSION

            logger.info("Trying to {} instance {} if idle for more than {} hours and  CPU % is below {}".format(action, instance_id, stop_instance_after, config.Config.DCV_IDLE_CPU_THRESHOLD))
            if stop_instance_after > 0:
                for instance_id in get_host_to_stop.keys():
                    logger.info("Checking Instance ID: {}".format(instance_id))
                    ssm_failed = False
                    ssm_list_command_loop = 0
                    shell_commands = [
                        "DCV_Describe_Session=$(dcv describe-session " + instance_data["session_uuid"] + " -j)",
                        "CPUAveragePerformanceLast10Secs=$(top -d 5 -b -n2 | grep 'Cpu(s)' |tail -n 1 | awk '{print $2 + $4}')",
                        "echo '{\"DCV\": '"'$DCV_Describe_Session'"' , \"CPUAveragePerformanceLast10Secs\": '"'$CPUAveragePerformanceLast10Secs'"'}'"]

                    try:
                        check_dcv_session = client_ssm.send_command(InstanceIds=[instance_id],
                                                                    DocumentName='AWS-RunShellScript',
                                                                    Parameters={"commands": shell_commands},
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
                                logger.info("SSM command ({}) executed but did not succeed or failed yet. Waiting 20 seconds ... {} ".format(ssm_command_id, client_ssm.list_commands(CommandId=ssm_command_id)['Commands']))
                                if check_command_status == "Failed":
                                    logger.error("Unable to query DCV for {} with SSM id ".format(instance_id, ssm_command_id))
                                    ssm_failed = True
                                    break
                                time.sleep(20)
                                ssm_list_command_loop += 1
                            else:
                                break

                    if ssm_list_command_loop >= 5:
                        logger.error("Unable to determine status SSM responses after 2 minutes timeout for {} : {} ".format(ssm_command_id, str(client_ssm.list_commands(CommandId=ssm_command_id))))
                        ssm_failed = True

                    if ssm_failed is False:
                        ssm_output = client_ssm.get_command_invocation(CommandId=ssm_command_id, InstanceId=instance_id)
                        session_info = json.loads(ssm_output["StandardOutputContent"])
                        session_current_connection = session_info["DCV"]["num-of-connections"]
                        if not session_info["DCV"]["last-disconnection-time"]:
                            # handle case where user launched DCV but never accessed it
                            last_dcv_disconnect = parse(session_info["DCV"]["creation-time"])
                        else:
                            last_dcv_disconnect = parse(session_info["DCV"]["last-disconnection-time"])

                        logger.info(session_info)
                        session_cpu_average = session_info["CPUAveragePerformanceLast10Secs"]
                        if session_cpu_average < config.Config.DCV_IDLE_CPU_THRESHOLD:
                            if session_current_connection == 0:
                                current_time = parse(datetime.datetime.now().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat())
                                if (last_dcv_disconnect + datetime.timedelta(hours=stop_instance_after)) < current_time:
                                    logger.info("{} is ready for {}. Last access time {}".format(instance_id,action, last_dcv_disconnect))
                                    try:
                                        if action == "hibernate":
                                            client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True, DryRun=True)
                                        else:
                                            client_ec2.stop_instances(InstanceIds=[instance_id], DryRun=True)
                                    except ClientError as e:
                                        if e.response['Error'].get('Code') == 'DryRunOperation':
                                            if action == "hibernate":
                                                client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True)
                                            else:
                                                client_ec2.stop_instances(InstanceIds=[instance_id])

                                            logging.info("Stopped {}".format(instance_id))
                                            try:
                                                check_session = LinuxDCVSessions.query.filter_by(session_instance_id=instance_id,
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
                                            logger.error("Unable to {} instance ({}) due to {}".format(action, instance_id, e), "error")
                                else:
                                    logger.info("{} NOT ready for {}. Last access time {}".format(instance_id, action, last_dcv_disconnect))
                            else:
                                logger.info("{} currently has active DCV sessions")
                        else:
                            logger.info("CPU usage {} is above threshold {} so this host won't be subject to {}.".format(session_cpu_average, config.Config.DCV_IDLE_CPU_THRESHOLD, action))
                    else:
                        logger.error("SSM failed for {} with ssm_id {}".format(instance_id, ssm_command_id))

def auto_terminate_stopped_instance():
    with db.app.app_context():
        for distribution in ["linux", "windows"]:
            logger.info("Scheduled Task: auto_terminate_stopped_instance {} ".format(distribution))
            if distribution == "windows":
                terminate_stopped_instance_after = config.Config.DCV_WINDOWS_TERMINATE_STOPPED_SESSION
            else:
                terminate_stopped_instance_after = config.Config.DCV_LINUX_TERMINATE_STOPPED_SESSION

            if terminate_stopped_instance_after > 0:
                get_host_to_terminate = retrieve_host(["stopped"], distribution)
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
                                    if distribution == "windows":
                                        check_session = WindowsDCVSessions.query.filter_by(session_instance_id=instance_id,
                                                                                           session_state="running",
                                                                                           is_active=True).first()
                                    else:
                                        check_session = LinuxDCVSessions.query.filter_by(session_instance_id=instance_id,
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
