import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash, Response
from requests import post, get, delete
from decorators import login_required
import boto3
from models import db, WindowsDCVSessions
import uuid
import random
import string
import base64
import datetime
import read_secretmanager
from botocore.exceptions import ClientError
import re
import os

remote_desktop_windows = Blueprint('remote_desktop_windows', __name__, template_folder='templates')
client_ec2 = boto3.client('ec2')
logger = logging.getLogger("api_log")


def launch_instance(launch_parameters, dry_run):
    # Launch Actual Capacity
    try:
        client_ec2.run_instances(
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': 30 if launch_parameters["disk_size"] is False else launch_parameters["disk_size"],
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
                         "Key": "soca:JobQueue",
                         "Value": "desktop"
                     },
                     {
                         "Key": "soca:KeepForever",
                         "Value": "false"
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
                         "Key": "soca:DCVWindowsSessionUUID",
                         "Value": launch_parameters["session_uuid"]
                     },
                     {
                         "Key": "soca:NodeType",
                         "Value": "soca-dcv-windows"
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


def get_host_info(session_uuid):
    host_info = {}
    token = True
    next_token = ''
    while token is True:
        response = client_ec2.describe_instances(
            Filters=[
                {
                    'Name': 'tag:soca:DCVWindowsSessionUUID',
                    'Values': [session_uuid]
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
                if instance['PrivateDnsName'].split('.')[0]:
                    host_info["private_dns"] = instance['PrivateDnsName'].split('.')[0]
                    host_info["instance_id"] = instance['InstanceId']

    return host_info


@remote_desktop_windows.route('/remote_desktop_windows', methods=['GET'])
@login_required
def index():
    user_sessions = {}
    for session_info in WindowsDCVSessions.query.filter_by(user=session["user"], is_active=True).all():
        session_number = session_info.session_number
        session_state = session_info.session_state
        session_password = session_info.session_password
        session_uuid = session_info.session_uuid
        session_name = session_info.session_name
        session_host = session_info.session_host
        support_hibernation = session_info.support_hibernation
        host_info = get_host_info(session_uuid)
        if not host_info:
            # no host detected, session no longer active
            session_info.is_active = False
            session_info.deactivated_on = datetime.datetime.utcnow()
            db.session.commit()
        else:
            # detected EC2 host for the session
            session_info.session_host = host_info["private_dns"]
            session_info.session_instance_id = host_info["instance_id"]
            db.session.commit()

        if session_state == "pending" and session_host is not False:
            check_dcv_state = get('https://' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '/' + session_host + '/',
                                  allow_redirects=False,
                                  verify=False)

            logger.info("Checking {} for {} and received status {} ".format('https://' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '/' + session_host + '/',
                                                                            session_info,
                                                                            check_dcv_state.status_code))

            if check_dcv_state.status_code == 200:
                session_info.session_state = "running"
                db.session.commit()

        user_sessions[session_number] = {
            "url": 'https://' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '/' + session_host +'/',
            "session_password": session_password,
            "session_state": session_state,
            "session_name": session_name,
            "support_hibernation": support_hibernation}

    max_number_of_sessions = config.Config.DCV_MAX_SESSION_COUNT
    # List of instances not available for DCV. Adjust as needed
    blacklist = ['metal', 'nano', 'micro', 'p3', 'p2']
    all_instances_available = client_ec2._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    return render_template('remote_desktop_windows.html',
                           user=session["user"],
                           user_sessions=user_sessions,
                           hibernate_idle_session=config.Config.DCV_WINDOWS_HIBERNATE_IDLE_SESSION,
                           terminate_stopped_session=config.Config.DCV_WINDOWS_TERMINATE_STOPPED_SESSION,
                           terminate_session=config.Config.DCV_WINDOWS_TERMINATE_SESSION,
                           page='remote_desktop',
                           all_instances=all_instances,
                           max_number_of_sessions=max_number_of_sessions)


@remote_desktop_windows.route('/remote_desktop_windows/create', methods=['POST'])
@login_required
def create():
    parameters = {}
    for parameter in ["instance_type", "disk_size", "session_number", "session_name", "instance_ami"]:
        if not request.form[parameter]:
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
        session_name = 'WindowsDesktop' + str(parameters["session_number"])
    else:
        session_name = re.sub(r'\W+', '', parameters["session_name"])[:255]
        if session_name == "":
            # handle case when session name specified by user only contains invalid char
            session_name = 'WindowsDesktop' + str(parameters["session_number"])

    # Official DCV AMI
    # https://aws.amazon.com/marketplace/pp/B07TVL513S + https://aws.amazon.com/marketplace/pp/B082HYM34K
    # Non graphics is everything but g3/g4
    if parameters["instance_ami"] == "base":
        dcv_windows_ami = config.Config.DCV_WINDOWS_AMI
        if instance_type.startswith("g"):
            if region not in dcv_windows_ami["graphics"].keys() and parameters["instance_ami"] is False:
                flash("Sorry, Windows Desktop is not available on your AWS region. Base AMI are only available on {}".format(dcv_windows_ami["graphics"].keys()),"error")
                return redirect("/remote_desktop_windows")
            else:
                image_id = dcv_windows_ami["graphics"][region]
        else:
            if region not in dcv_windows_ami["non-graphics"].keys() and parameters["instance_ami"] is False:
                flash("Sorry, Windows Desktop is not available on your AWS region. Base AMI are only available on {}".format(dcv_windows_ami["non-graphics"].keys()), "error")

                return redirect("/remote_desktop_windows")
            else:
                image_id = dcv_windows_ami["non-graphics"][region]
    else:
        image_id = parameters["instance_ami"]
        if not image_id.startswith("ami-"):
            flash("AMI selectioned {} does not seems to be valid. Must start with ami-<id>".format(image_id), "error")
            return redirect("/remote_desktop_windows")

    digits = ([random.choice(''.join(random.choice(string.digits) for _ in range(10))) for _ in range(3)])
    uppercase = ([random.choice(''.join(random.choice(string.ascii_uppercase) for _ in range(10))) for _ in range(3)])
    lowercase = ([random.choice(''.join(random.choice(string.ascii_lowercase) for _ in range(10))) for _ in range(3)])
    pw = digits + uppercase + lowercase
    session_password = ''.join(random.sample(pw, len(pw)))
    user_data_script = open("/apps/soca/"+soca_configuration["ClusterId"]+"/cluster_node_bootstrap/ComputeNodeInstallDCVWindows.ps", "r")
    user_data = user_data_script.read()
    user_data_script.close()
    user_data = user_data.replace("%SOCA_USER_PASSWORD%", session_password)

    check_hibernation_support = client_ec2.describe_instance_types(
        InstanceTypes=[instance_type],
        Filters=[
            {"Name": "hibernation-supported",
             "Values": ["true"]}
        ]
    )
    if len(check_hibernation_support["InstanceTypes"]) == 0:
        if config.Config.DCV_FORCE_INSTANCE_HIBERNATE_SUPPORT is True:
            flash("Sorry your administrator limited <a href='https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/Hibernate.html#hibernating-prerequisites' target='_blank'>DCV to instances that support hibernation mode</a> <br> Please choose a different type of instance.")
            return redirect("/remote_desktop_windows")
        else:
            hibernate = False
    else:
        hibernate = True

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
                         "hibernate": hibernate
                         }
    dry_run_launch = launch_instance(launch_parameters, dry_run=True)
    if dry_run_launch is True:
        actual_launch = launch_instance(launch_parameters, dry_run=False)
        if actual_launch is not True:
            flash(actual_launch, "error")
            return redirect("/remote_desktop_windows")
    else:
        flash(dry_run_launch, "error")
        return redirect("/remote_desktop_windows")

    flash("Your session has been initiated. It will be ready within 10 minutes.", "success")
    new_session = WindowsDCVSessions(user=session["user"],
                                     session_number=parameters["session_number"],
                                     session_name=session_name,
                                     session_state="pending",
                                     session_host=False,
                                     session_password=session_password,
                                     session_uuid=session_uuid,
                                     is_active=True,
                                     support_hibernation=hibernate,
                                     created_on=datetime.datetime.utcnow())
    db.session.add(new_session)
    db.session.commit()
    return redirect("/remote_desktop_windows")


@remote_desktop_windows.route('/remote_desktop_windows/delete', methods=['GET'])
@login_required
def delete_job():
    dcv_session = request.args.get("session", None)
    hibernate = request.args.get("hibernate", None)
    if dcv_session is None:
        flash("Invalid DCV sessions", "error")
        return redirect("/remote_desktop_windows")

    check_session = WindowsDCVSessions.query.filter_by(user=session["user"],
                                                       session_number=dcv_session,
                                                       is_active=True).first()
    if check_session:
        instance_id = check_session.session_instance_id
        if hibernate:
            try:
                client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True, DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') == 'DryRunOperation':
                    client_ec2.stop_instances(InstanceIds=[instance_id], Hibernate=True)
                    check_session.session_state = "stopped"
                    db.session.commit()
                else:
                    flash("Unable to hibernate instance ({}) due to {}".format(instance_id, e), "error")
        else:
            try:
                client_ec2.terminate_instances(InstanceIds=[instance_id], DryRun=True)
            except Exception as e:
                if e.response['Error'].get('Code') == 'DryRunOperation':
                    client_ec2.terminate_instances(InstanceIds=[instance_id])
                    flash("DCV session is about to be terminated.", "success")
                    check_session.is_active = False
                    check_session.deactivated_on = datetime.datetime.utcnow()
                    db.session.commit()
                    return redirect("/remote_desktop_windows")
                else:
                    flash("Unable to delete associated instance ({}) due to {}".format(instance_id, e), "error")

    else:
        flash("Unable to retrieve this session", "error")

    return redirect("/remote_desktop_windows")


@remote_desktop_windows.route('/remote_desktop_windows/restart', methods=['GET'])
@login_required
def restart_from_hibernate():
    dcv_session = request.args.get("session", None)
    if dcv_session is None:
        flash("Invalid DCV sessions", "error")
        return redirect("/remote_desktop_windows")

    check_session = WindowsDCVSessions.query.filter_by(user=session["user"],
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

    return redirect("/remote_desktop_windows")


@remote_desktop_windows.route('/remote_desktop_windows/client', methods=['GET'])
@login_required
def generate_client():
    dcv_session = request.args.get("session", None)
    if dcv_session is None:
        flash("Invalid DCV sessions", "error")
        return redirect("/remote_desktop_windows")

    check_session = WindowsDCVSessions.query.filter_by(user=session["user"], session_number=dcv_session, is_active=True).first()
    if check_session:
        session_file = '''
[version]
format=1.0

[connect]
host=''' + read_secretmanager.get_soca_configuration()['LoadBalancerDNSName'] + '''
port=443
weburlpath=/''' + check_session.session_host + '''
'''
        return Response(
            session_file,
            mimetype='text/txt',
            headers={'Content-disposition': 'attachment; filename=' + session['user'] + '_soca_' + str(dcv_session) + '.dcv'})

    else:
        flash("Unable to retrieve this session. This session may have been terminated.", "error")
        return redirect("/remote_desktop_windows")

