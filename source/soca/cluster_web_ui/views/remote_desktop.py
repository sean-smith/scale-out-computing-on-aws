import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash, Response
from requests import get
from decorators import login_required
import boto3
from models import db, LinuxDCVSessions
import uuid
import random
import string
import base64
import datetime
import read_secretmanager
from botocore.exceptions import ClientError
import re
import os
import json
from cryptography.fernet import Fernet


remote_desktop = Blueprint('remote_desktop', __name__, template_folder='templates')
client_ec2 = boto3.client('ec2')
logger = logging.getLogger("application")


def encrypt(message):
    key = config.Config.DCV_TOKEN_SYMMETRIC_KEY
    cipher_suite = Fernet(key)
    return cipher_suite.encrypt(message.encode("utf-8"))


def launch_instance(launch_parameters, dry_run):
    # Launch Actual Capacity
    try:
        client_ec2.run_instances(
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': 30 if launch_parameters["disk_size"] is False else int(launch_parameters["disk_size"]),
                        'VolumeType': 'gp2',
                        'Encrypted': True
                    },
                },
            ],
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[launch_parameters["security_group_id"]],
            InstanceType=launch_parameters["instance_type"],
            IamInstanceProfile={'Arn': launch_parameters["instance_profile"]},
            SubnetId=random.choice(launch_parameters["soca_private_subnets"]),
            UserData=launch_parameters["user_data"],
            ImageId=launch_parameters["image_id"],
            DryRun=False if dry_run is False else True,
            HibernationOptions={'Configured': launch_parameters["hibernate"]},
            TagSpecifications=[
                {"ResourceType": "instance",
                 "Tags": [
                     {
                         "Key": "Name",
                         "Value": launch_parameters["cluster_id"] + "-" + launch_parameters["session_name"] + "-" + session["user"]
                     },
                     {
                         "Key": "soca:JobName",
                         "Value": launch_parameters["session_name"]
                     },
                     {
                         "Key": "soca:JobOwner",
                         "Value": session["user"]
                     },
                     {
                         "Key": "soca:JobProject",
                         "Value": "Desktop"
                     },
                     {
                         "Key": "soca:DCVSupportHibernate",
                         "Value": str(launch_parameters["hibernate"]).lower()
                     },
                     {
                         "Key": "soca:ClusterId",
                         "Value": launch_parameters["cluster_id"]
                     },
                     {
                         "Key": "soca:DCVSessionUUID",
                         "Value": launch_parameters["session_uuid"]
                     },
                     {
                         "Key": "soca:NodeType",
                         "Value": "soca-dcv"
                     },
                     {
                         "Key": "soca:DCVSystem",
                         "Value": "linux"
                     }
                 ]}]
        )

    except ClientError as err:
        if dry_run is True:
            if err.response['Error'].get('Code') == 'DryRunOperation':
                return True
            else:
                return "Dry run failed. Unable to launch capacity due to: {}".format(err)
        else:
            return "Unable to provision capacity due to {}".format(err)

    return True


def get_host_info(tag_uuid, cluster_id):
    host_info = {}
    token = True
    next_token = ''
    while token is True:
        response = client_ec2.describe_instances(
            Filters=[
                {
                    'Name': 'tag:soca:DCVSessionUUID',
                    'Values': [tag_uuid]
                },
                {
                    "Name": "tag:soca:ClusterId",
                    "Values": [cluster_id]
                },
                {
                    "Name": "tag:soca:DCVSystem",
                    "Values": ["linux"]
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
                if instance['PrivateDnsName'].split('.')[0]:
                    host_info["private_dns"] = instance['PrivateDnsName'].split('.')[0]
                    host_info["private_ip"] = instance['PrivateIpAddress']
                    host_info["instance_id"] = instance['InstanceId']
                    host_info["status"] = instance['State']['Name']

    return host_info


@remote_desktop.route('/remote_desktop', methods=['GET'])
@login_required
def index():
    user_sessions = {}
    for session_info in LinuxDCVSessions.query.filter_by(user=session["user"], is_active=True).all():
        session_number = session_info.session_number
        session_state = session_info.session_state
        tag_uuid = session_info.tag_uuid
        session_name = session_info.session_name
        session_host_private_dns = session_info.session_host_private_dns
        session_token = session_info.session_token
        session_instance_type = session_info.session_instance_type
        session_instance_id = session_info.session_instance_id
        support_hibernation = session_info.support_hibernation
        dcv_authentication_token = session_info.dcv_authentication_token
        session_id = session_info.session_id
        host_info = get_host_info(session_id, read_secretmanager.get_soca_configuration()["ClusterId"])
        if not host_info:
            # no host detected, session no longer active
            session_info.is_active = False
            session_info.deactivated_on = datetime.datetime.utcnow()
            db.session.commit()
        else:
            # detected EC2 host for the session
            if not dcv_authentication_token:
                session_info.session_host_private_dns = host_info["private_dns"]
                session_info.session_host_private_ip = host_info["private_ip"]
                session_info.session_instance_id = host_info["instance_id"]
                authentication_data = json.dumps({"system": "linux",
                                                  "session_instance_id": host_info["instance_id"],
                                                  "session_token": session_token,
                                                  "session_user": session["user"]})
                session_authentication_token = base64.b64encode(encrypt(authentication_data)).decode("utf-8")
                session_info.dcv_authentication_token = session_authentication_token
                db.session.commit()

        if host_info["status"] in ["stopped", "stopping"] and session_state != "stopped":
            session_state = "stopped"
            session_info.session_state = "stopped"
            db.session.commit()

        if session_state == "pending" and session_host_private_dns is not False:
            check_dcv_state = get('https://' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '/' + session_host_private_dns + '/',
                                  allow_redirects=False,
                                  verify=False)

            logger.info("Checking {} for {} and received status {} ".format('https://' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '/' + session_host_private_dns + '/',
                                                                            session_info,
                                                                            check_dcv_state.status_code))

            if check_dcv_state.status_code == 200:
                session_info.session_state = "running"
                db.session.commit()

        user_sessions[session_number] = {
            "url": 'https://' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '/' + session_host_private_dns +'/',
            "session_state": session_state,
            "session_authentication_token": dcv_authentication_token,
            "session_id": session_id,
            "session_name": session_name,
            "session_instance_id": session_instance_id,
            "session_instance_type": session_instance_type,
            "tag_uuid": tag_uuid,
            "support_hibernation": support_hibernation}

    max_number_of_sessions = config.Config.DCV_LINUX_SESSION_COUNT
    # List of instances not available for DCV. Adjust as needed
    blacklist = config.Config.DCV_BLACKLIST_INSTANCE_TYPE
    all_instances_available = client_ec2._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    return render_template('remote_desktop.html',
                           user=session["user"],
                           user_sessions=user_sessions,
                           hibernate_idle_session=config.Config.DCV_LINUX_HIBERNATE_IDLE_SESSION,
                           stop_idle_session=config.Config.DCV_LINUX_STOP_IDLE_SESSION,
                           terminate_stopped_session=config.Config.DCV_LINUX_TERMINATE_STOPPED_SESSION,
                           terminate_session=config.Config.DCV_LINUX_TERMINATE_STOPPED_SESSION,
                           allow_instance_change=config.Config.DCV_LINUX_ALLOW_INSTANCE_CHANGE,
                           page='remote_desktop',
                           all_instances=all_instances,
                           max_number_of_sessions=max_number_of_sessions)


@remote_desktop.route('/remote_desktop/create', methods=['POST'])
@login_required
def create():
    parameters = {}
    for parameter in ["instance_type", "disk_size", "session_number", "session_name", "instance_ami", "hibernate"]:
        if not request.form[parameter]:
            parameters[parameter] = False
        else:
            if request.form[parameter].lower() in ["yes", "true"]:
                parameters[parameter] = True
            elif request.form[parameter].lower() in ["no", "false"]:
                parameters[parameter] = False
            else:
                parameters[parameter] = request.form[parameter]

    session_uuid = str(uuid.uuid4())
    region = os.environ["AWS_DEFAULT_REGION"]
    instance_type = parameters["instance_type"]
    soca_configuration = read_secretmanager.get_soca_configuration()
    instance_profile = soca_configuration["ComputeNodeInstanceProfileArn"]
    security_group_id = soca_configuration["ComputeNodeSecurityGroup"]
    soca_private_subnets = [soca_configuration["PrivateSubnet1"],
                            soca_configuration["PrivateSubnet2"],
                            soca_configuration["PrivateSubnet3"]]

    # sanitize session_name, limit to 255 chars
    if parameters["session_name"] is False:
        session_name = 'LinuxDesktop' + str(parameters["session_number"])
    else:
        session_name = re.sub(r'\W+', '', parameters["session_name"])[:255]
        if session_name == "":
            # handle case when session name specified by user only contains invalid char
            session_name = 'LinuxDesktop' + str(parameters["session_number"])

    if parameters["instance_ami"] == "base":
        image_id = soca_configuration["CustomAMI"]
    else:
        image_id = parameters["instance_ami"]
        if not image_id.startswith("ami-"):
            flash("AMI selectioned {} does not seems to be valid. Must start with ami-<id>".format(image_id), "error")
            return redirect("/remote_desktop")

    user_data = '''#!/bin/bash -x
    export PATH=$PATH:/usr/local/bin
    if [[ "''' + soca_configuration['BaseOS'] + '''" == "centos7" ]] || [[ "''' + soca_configuration['BaseOS'] + '''" == "rhel7" ]];
        then
            EASY_INSTALL=$(which easy_install-2.7)
            $EASY_INSTALL pip
            PIP=$(which pip2.7)
            $PIP install awscli
            yum install -y nfs-utils # enforce install of nfs-utils
    else
         # Upgrade awscli on ALI (do not use yum)
         EASY_INSTALL=$(which easy_install-2.7)
         $EASY_INSTALL pip
         PIP=$(which pip)
         $PIP install awscli --upgrade 
    fi
    if [[ "''' + soca_configuration['BaseOS'] + '''" == "amazonlinux2" ]];
        then
            /usr/sbin/update-motd --disable
    fi
    
    GET_INSTANCE_TYPE=$(curl http://169.254.169.254/latest/meta-data/instance-type)
    echo export "SOCA_DCV_AUTHENTICATOR="https://''' + soca_configuration['SchedulerPrivateDnsName'] + ''':8443/api/dcv/authenticator"" >> /etc/environment
    echo export "SOCA_DCV_SESSION_ID="''' + str(session_uuid) +'''"" >> /etc/environment
    echo export "SOCA_CONFIGURATION="''' + str(soca_configuration['ClusterId']) + '''"" >> /etc/environment
    echo export "SOCA_DCV_OWNER="''' + str(session["user"]) + '''"" >> /etc/environment
    echo export "SOCA_BASE_OS="''' + str(soca_configuration['BaseOS']) + '''"" >> /etc/environment
    echo export "SOCA_JOB_TYPE="desktop"" >> /etc/environment
    echo export "SOCA_SCRATCH_SIZE=''' + str(parameters['disk_size']) + '''" >> /etc/environment
    echo export "SOCA_INSTALL_BUCKET="''' + str(soca_configuration['S3Bucket']) + '''"" >> /etc/environment
    echo export "SOCA_INSTALL_BUCKET_FOLDER="''' + str(soca_configuration['S3InstallFolder']) + '''"" >> /etc/environment
    echo export "SOCA_INSTANCE_TYPE=$GET_INSTANCE_TYPE" >> /etc/environment
    echo export "SOCA_HOST_SYSTEM_LOG="/apps/soca/''' + str(soca_configuration['ClusterId']) + '''/cluster_node_bootstrap/logs/desktop/''' + str(session["user"]) + '''/''' + session_name + '''/$(hostname -s)"" >> /etc/environment
    echo export "AWS_DEFAULT_REGION="'''+region+'''"" >> /etc/environment
    source /etc/environment
    AWS=$(which aws)
    # Give yum permission to the user on this specific machine
    echo "''' + session['user'] + ''' ALL=(ALL) /bin/yum" >> /etc/sudoers

    mkdir -p /apps
    mkdir -p /data

    # Mount EFS
    echo "''' + soca_configuration['EFSDataDns'] + ''':/ /data nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0" >> /etc/fstab
    echo "''' + soca_configuration['EFSAppsDns'] + ''':/ /apps nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0" >> /etc/fstab
    EFS_MOUNT=0
    mount -a 
    while [[ $? -ne 0 ]] && [[ $EFS_MOUNT -lt 5 ]]
      do
        SLEEP_TIME=$(( RANDOM % 60 ))
        echo "Failed to mount EFS, retrying in $SLEEP_TIME seconds and Loop $EFS_MOUNT/5..."
        sleep $SLEEP_TIME
        ((EFS_MOUNT++))
        mount -a
      done

    # Configure NTP
    yum remove -y ntp
    yum install -y chrony
    mv /etc/chrony.conf  /etc/chrony.conf.original
    echo -e """
    # use the local instance NTP service, if available
    server 169.254.169.123 prefer iburst minpoll 4 maxpoll 4

    # Use public servers from the pool.ntp.org project.
    # Please consider joining the pool (http://www.pool.ntp.org/join.html).
    # !!! [BEGIN] SOCA REQUIREMENT
    # You will need to open UDP egress traffic on your security group if you want to enable public pool
    #pool 2.amazon.pool.ntp.org iburst
    # !!! [END] SOCA REQUIREMENT
    # Record the rate at which the system clock gains/losses time.
    driftfile /var/lib/chrony/drift

    # Allow the system clock to be stepped in the first three updates
    # if its offset is larger than 1 second.
    makestep 1.0 3

    # Specify file containing keys for NTP authentication.
    keyfile /etc/chrony.keys

    # Specify directory for log files.
    logdir /var/log/chrony

    # save data between restarts for fast re-load
    dumponexit
    dumpdir /var/run/chrony
    """ > /etc/chrony.conf
    systemctl enable chronyd

    # Prepare  Log folder
    mkdir -p $SOCA_HOST_SYSTEM_LOG
    echo "@reboot /bin/bash /apps/soca/$SOCA_CONFIGURATION/cluster_node_bootstrap/ComputeNodePostReboot.sh >> $SOCA_HOST_SYSTEM_LOG/ComputeNodePostReboot.log 2>&1" | crontab -
    $AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/config.cfg /root/
    /bin/bash /apps/soca/$SOCA_CONFIGURATION/cluster_node_bootstrap/ComputeNode.sh ''' + soca_configuration['SchedulerPrivateDnsName'] + ''' >> $SOCA_HOST_SYSTEM_LOG/ComputeNode.sh.log 2>&1'''



    check_hibernation_support = client_ec2.describe_instance_types(
        InstanceTypes=[instance_type],
        Filters=[
            {"Name": "hibernation-supported",
             "Values": ["true"]}]
    )
    logger.info("Checking in {} support Hibernation : {}".format(instance_type, check_hibernation_support))
    if len(check_hibernation_support["InstanceTypes"]) == 0:
        if config.Config.DCV_FORCE_INSTANCE_HIBERNATE_SUPPORT is True:
            flash("Sorry your administrator limited <a href='https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Hibernate.html' target='_blank'>DCV to instances that support hibernation mode</a> <br> Please choose a different type of instance.")
            return redirect("/remote_desktop")
        else:
            hibernate_support = False
    else:
        hibernate_support = True

    if parameters["hibernate"] and not hibernate_support:
        flash("Sorry you have selected {} with hibernation support, but this instance type does not support it. Either disable hibernation support or pick a different instance type".format(instance_type), "error")
        return redirect("/remote_desktop")

    launch_parameters = {"security_group_id": security_group_id,
                         "instance_profile": instance_profile,
                         "instance_type": instance_type,
                         "soca_private_subnets": soca_private_subnets,
                         "user_data": user_data,
                         "image_id": image_id,
                         "session_name": session_name,
                         "session_uuid": session_uuid,
                         "disk_size": parameters["disk_size"],
                         "cluster_id": soca_configuration["ClusterId"],
                         "hibernate": parameters["hibernate"]
                         }
    dry_run_launch = launch_instance(launch_parameters, dry_run=True)
    if dry_run_launch is True:
        actual_launch = launch_instance(launch_parameters, dry_run=False)
        if actual_launch is not True:
            flash(actual_launch, "error")
            return redirect("/remote_desktop")
    else:
        flash(dry_run_launch, "error")
        return redirect("/remote_desktop")

    flash("Your session has been initiated. It will be ready within 10 minutes.", "success")
    new_session = LinuxDCVSessions(user=session["user"],
                                     session_number=parameters["session_number"],
                                     session_name=session_name,
                                     session_state="pending",
                                     session_host_private_dns=False,
                                     session_host_private_ip=False,
                                     session_instance_type=instance_type,
                                     dcv_authentication_token=None,
                                     session_id=session_uuid,
                                     tag_uuid=session_uuid,
                                     session_token=str(uuid.uuid4()),
                                     is_active=True,
                                     support_hibernation=parameters["hibernate"],
                                     created_on=datetime.datetime.utcnow())
    db.session.add(new_session)
    db.session.commit()
    return redirect("/remote_desktop")


@remote_desktop.route('/remote_desktop/delete', methods=['GET'])
@login_required
def delete():
    dcv_session = request.args.get("session", None)
    action = request.args.get("action", None)
    if action not in ["terminate", "stop", "hibernate"]:
        flash("action must be either terminate, stop or hibernate")
        return redirect("/remote_desktop")

    if dcv_session is None:
        flash("Invalid graphical session ID", "error")
        return redirect("/remote_desktop")

    check_session = LinuxDCVSessions.query.filter_by(user=session["user"],
                                                       session_number=dcv_session,
                                                       is_active=True).first()
    if check_session:
        instance_id = check_session.session_instance_id
        if action == "hibernate":
            # Hibernate instance
            try:
                client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True, DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') == 'DryRunOperation':
                    client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True)
                    check_session.session_state = "stopped"
                    db.session.commit()
                else:
                    flash("Unable to hibernate instance ({}) due to {}".format(instance_id, e), "error")

        elif action == "stop":
            # Stop Instance
            try:
                client_ec2.stop_instances(InstanceIds=[instance_id], DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') == 'DryRunOperation':
                    client_ec2.stop_instances(InstanceIds=[instance_id])
                    check_session.session_state = "stopped"
                    db.session.commit()
                else:
                    flash("Unable to Stop instance ({}) due to {}".format(instance_id, e), "error")

        else:
            # Terminate instance
            try:
                client_ec2.terminate_instances(InstanceIds=[instance_id], DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') == 'DryRunOperation':
                    client_ec2.terminate_instances(InstanceIds=[instance_id])
                    flash("Your graphical session is about to be terminated.", "success")
                    check_session.is_active = False
                    check_session.deactivated_on = datetime.datetime.utcnow()
                    db.session.commit()
                    return redirect("/remote_desktop")
                else:
                    flash("Unable to delete associated instance ({}) due to {}".format(instance_id, e), "error")

    else:
        flash("Unable to retrieve this session", "error")

    return redirect("/remote_desktop")


@remote_desktop.route('/remote_desktop/restart', methods=['GET'])
@login_required
def restart_from_hibernate():
    dcv_session = request.args.get("session", None)
    if dcv_session is None:
        flash("Invalid graphical session", "error")
        return redirect("/remote_desktop")

    check_session = LinuxDCVSessions.query.filter_by(user=session["user"],
                                                       session_number=dcv_session,
                                                       session_state="stopped",
                                                       is_active=True).first()
    if check_session:
        instance_id = check_session.session_instance_id
        try:
            client_ec2.start_instances(InstanceIds=[instance_id], DryRun=True)
        except Exception as e:
            if e.response['Error'].get('Code') == 'DryRunOperation':
                try:
                    client_ec2.start_instances(InstanceIds=[instance_id])
                    check_session.session_state = "pending"
                    db.session.commit()
                except Exception as err:
                    flash("Please wait a little bit before restarting this session as the underlying resource is still being stopped.", "error")

            else:
                flash("Unable to restart instance ({}) due to {}".format(instance_id, e), "error")
    else:
        flash("Unable to retrieve this session", "error")

    return redirect("/remote_desktop")

@remote_desktop.route('/remote_desktop/modify', methods=['POST'])
@login_required
def modify():
    dcv_session = None if not "session_number" in request.form else request.form["session_number"]
    new_instance_type = None if not "instance_type" in request.form else request.form["instance_type"]
    if dcv_session is None:
        flash("Invalid graphical session", "error")
        return redirect("/remote_desktop")

    if new_instance_type is None:
        flash("Invalid new EC2 instance type", "error")
        return redirect("/remote_desktop")

    blacklist = config.Config.DCV_BLACKLIST_INSTANCE_TYPE
    all_instances_available = client_ec2._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    if new_instance_type not in all_instances:
        flash("This EC2 instance type is not authorized", "error")
        return redirect("/remote_desktop")

    check_session = LinuxDCVSessions.query.filter_by(user=session["user"],
                                                       session_number=dcv_session,
                                                       session_state="stopped",
                                                       is_active=True).first()
    if check_session:
        instance_id = check_session.session_instance_id
        try:
            client_ec2.modify_instance_attribute(InstanceId=instance_id,
                                                 InstanceType={'Value': new_instance_type},
                                                 DryRun=True)
        except ClientError as e:
            if e.response['Error'].get('Code') == 'DryRunOperation':
                try:
                    client_ec2.modify_instance_attribute(InstanceId=instance_id,
                                                         InstanceType={'Value': new_instance_type})
                    check_session.session_instance_type = new_instance_type
                    db.session.commit()
                    flash("Your EC2 instance has been updated successfully to: {}".format(new_instance_type), "success")
                except ClientError as err:
                    if "not supported for instances with hibernation configured." in err.response['Error'].get('Code'):
                        flash("Your intance has been started with hibernation enabled. You cannot change the instance type. Start a new session with Hibernation disabled if you want to be able to change your instance type. ", "error")
                    else:
                        flash("Unable to modify EC2 instance type due to {}".format(err), "error")
            else:
                flash("Unable to modify instance ({}) due to {}".format(instance_id, e), "error")
    else:
        flash("Unable to retrieve this session. Either session does not exist or is not stopped", "error")

    return redirect("/remote_desktop")


@remote_desktop.route('/remote_desktop/client', methods=['GET'])
@login_required
def generate_client():
    dcv_session = request.args.get("session", None)
    if dcv_session is None:
        flash("Invalid graphical sessions", "error")
        return redirect("/remote_desktop")

    check_session = LinuxDCVSessions.query.filter_by(user=session["user"],
                                                       session_number=dcv_session,
                                                       is_active=True).first()
    if check_session:
        session_file = '''
[version]
format=1.0

[connect]
host=''' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '''
port=443
sessionid='''+check_session.session_id+'''
user='''+session["user"]+'''
authToken='''+check_session.dcv_authentication_token+'''
weburlpath=/''' + check_session.session_host_private_dns + '''
'''
        return Response(
            session_file,
            mimetype='text/txt',
            headers={'Content-disposition': 'attachment; filename=' + session['user'] + '_soca_' + str(dcv_session) + '.dcv'})

    else:
        flash("Unable to retrieve this session. This session may have been terminated.", "error")
        return redirect("/remote_desktop")

