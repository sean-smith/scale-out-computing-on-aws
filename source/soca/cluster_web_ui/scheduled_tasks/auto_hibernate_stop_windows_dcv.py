import boto3
import logging
import os
import config
import datetime
import re
import json
import time
from dateutil.parser import parse

logger = logging.getLogger("api_log")

client_ec2 = boto3.client("ec2")
client_ssm = boto3.client("ssm")


def retrieve_host(instance_state):
    host_info = {}
    token = True
    next_token = ''
    while token is True:
        response = client_ec2.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [instance_state]
                },
                {
                    'Name': 'tag:soca:JobQueue',
                    'Values': ["desktop"]
                },
                {
                    "Key": "tag:soca:ClusterId",
                    "Value": [os.environ["SOCA_CONFIGURATION"]]
                },
                {
                    "Name": "tag:soca:NodeType",
                    "Value": ["soca-compute-node-windows"]
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
                stopped_time = parse(re.findall('.*\((.*)\)', instance["StateTransitionReason"])[0])
                host_info[instance["InstanceId"]] = {"stopped_time": stopped_time,
                                                     "current_time": current_time}

    return host_info


def auto_hibernate_instance():
    hibernate_idle_instance_after = config.Config.DCV_WINDOWS_HIBERNATE_IDLE_SESSION
    if hibernate_idle_instance_after > 0:
        for instance_id in ["i-0efb2e79c9f4aca89"]:
            powershell_command = ["Invoke-Expression \"& 'C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv' describe-session console -j\""]
            check_dcv_session = client_ssm.send_command(InstanceIds=[instance_id],
                                                        DocumentName='AWS-RunPowerShellScript',
                                                        Parameters={"commands": powershell_command},
                                                        TimeoutSeconds=30)
            ssm_command_id = check_dcv_session["Command"]["CommandId"]

            while client_ssm.list_commands(CommandId=ssm_command_id)['Commands'][0]['Status'] != "Success":
                time.sleep(2)
                if client_ssm.list_commands(CommandId=ssm_command_id)['Commands'][0]['Status'] == "Failed":
                    logger.error("Unable to query DCV for {} with SSM id ".format(instance_id, ssm_command_id))
                    return False

            ssm_output = client_ssm.get_command_invocation(CommandId=ssm_command_id, InstanceId=instance_id)
            session_info = json.loads(ssm_output["StandardOutputContent"])
            if not session_info["last-disconnection-time"]:
                # handle case where user launched DCV but never accessed it
                last_dcv_disconnect = parse(session_info["creation-time"])
            else:
                last_dcv_disconnect = parse(session_info["last-disconnection-time"])

            current_time = parse(datetime.datetime.now().replace(microsecond=0).replace(tzinfo=datetime.timezone.utc).isoformat())
            if (last_dcv_disconnect + datetime.timedelta(hours=hibernate_idle_instance_after)) < current_time:
                print("{} is ready for hibernation. Last access time {}".format(instance_id, last_dcv_disconnect))

                try:
                    client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True, DryRun=True)
                except Exception as e:
                    if e.response['Error'].get('Code') == 'DryRunOperation':
                        client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True)
                    else:
                        logger.error("Unable to hibernate instance ({}) due to {}".format(instance_id, e), "error")
            else:
                print("{} NOT ready for hibernation. Last access time {}".format(instance_id, last_dcv_disconnect))


def auto_terminate_stopped_instance():
    terminate_stopped_instance_after = config.Config.DCV_WINDOWS_TERMINATE_STOPPED_SESSION  # in hours
    if terminate_stopped_instance_after > 0:
        get_host_to_terminate = retrieve_host(instance_state="stopped")
        for instance_id, time_info in get_host_to_terminate.items():
            if (time_info["stopped_time"] + datetime.timedelta(hours=terminate_stopped_instance_after)) < time_info["current_time"]:
                try:
                    client_ec2.terminate_instances(InstanceIds=[instance_id], DryRun=True)
                except Exception as e:
                    if e.response['Error'].get('Code') == 'DryRunOperation':
                        client_ec2.terminate_instances(InstanceIds=[instance_id])
                    else:
                        logger.error("Unable to delete associated instance ({}) due to {}".format(instance_id, e))
            else:
                logger.info("stopped instance ({}) is not ready to be terminated. terminate_stopped_instance_after: {}".format(instance_id, terminate_stopped_instance_after))