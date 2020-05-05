import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import post, get, delete
from decorators import login_required
import boto3
from models import db, DCVSessions
import uuid
import random
import string
import base64
import datetime
import os
import json

logger = logging.getLogger("api_log")
remote_desktop = Blueprint('remote_desktop', __name__, template_folder='templates')
client = boto3.client('ec2')


def get_soca_configuration():
    secretsmanager_client = boto3.client('secretsmanager')
    configuration_secret_name = os.environ['SOCA_CONFIGURATION']
    response = secretsmanager_client.get_secret_value(SecretId=configuration_secret_name)
    return json.loads(response['SecretString'])

@remote_desktop.route('/remote_desktop', methods=['GET'])
@login_required
def index():
    user_sessions = {}
    for session_info in DCVSessions.query.filter_by(user=session["user"], is_active=True).all():
        session_number = session_info.session_number
        session_state = session_info.session_state
        session_password = session_info.session_password
        session_uuid = session_info.session_uuid
        session_host = session_info.session_host
        job_id = session_info.job_id

        get_job_info = get(#config.Config.FLASK_ENDPOINT + "/api/scheduler/job",
            "https://soca-a5m4-viewer-2002948608.us-east-1.elb.amazonaws.com/api/scheduler/job",
            headers={"X-SOCA-USER": session["user"],
                     "X-SOCA-TOKEN": session["api_key"]},
                     params={"job_id": job_id},
                     verify=False)

        check_session = DCVSessions.query.filter_by(job_id=job_id).first()
        if get_job_info.status_code == 200:
            # Job in queue, edit only if state is running
            job_state = get_job_info.json()["message"]["job_state"]
            if job_state == "R" and check_session.session_state != "running":
                exec_host = (get_job_info.json()["message"]["exec_host"]).split("/")[0]
                # Only edit the DB is needed
                if check_session:
                    check_session.session_host = exec_host
                    check_session.session_state = "running"
                    db.session.commit()

        elif get_job_info.status_code == 210:
            # Job is no longer in the queue
            check_session.is_active = False
            check_session.deactivated_on = datetime.datetime.utcnow()
            db.session.commit()
        else:
            flash("Unknown error for session " + str(session_number) + " assigned to job " + str(job_id) + " with error " + str(get_job_info.text), "error")

        user_sessions[session_number] = {
                "url": 'https://' + get_soca_configuration()['LoadBalancerDNSName'] + '/' + check_session.session_host  + '/?authToken=' + session_password + '#' + session_uuid ,
                "session_state": session_state}


    max_number_of_sessions = config.Config.DCV_MAX_SESSION_COUNT
    # List of instances not available for DCV. Adjust as needed
    blacklist = ['metal', 'nano', 'micro']
    all_instances_available = client._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    return render_template('remote_desktop.html',
                           user_sessions=user_sessions,
                           page='remote_desktop',
                           all_instances=all_instances,
                           max_number_of_sessions=max_number_of_sessions)

@remote_desktop.route('/remote_desktop/create', methods=['POST'])
@login_required
def create():
    parameters = {}
    for parameter in ["walltime", "instance_type", "session_number", "instance_ami", "base_os", "scratch_size"]:
        if not request.form[parameter]:
            parameters[parameter] = False
        else:
            parameters[parameter] = request.form[parameter]

    session_uuid = str(uuid.uuid4())
    session_password = ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(80))

    command_dcv_create_session = config.Config.DCV_BIN + " create-session --user  " + session["user"] + " --owner " + session["user"] + " " + session_uuid
    params = {'pbs_job_name': 'Desktop' + str(parameters["session_number"]),
              'pbs_queue': 'desktop',
              'pbs_project': 'gui',
              'instance_type': parameters["instance_type"],
              'instance_ami': parameters["instance_ami"],
              'base_os': parameters["base_os"],
              'scratch_size': parameters["scratch_size"],
              'session_password': session_password,
              'session_password_b64': (base64.b64encode(session_password.encode('utf-8'))).decode('utf-8'),
              'walltime': parameters["walltime"]}


    ## build job
    job_to_submit = '''
    #PBS -N ''' + params['pbs_job_name'] + '''
    #PBS -q ''' + params['pbs_queue'] + '''
    #PBS -P ''' + params['pbs_project'] + '''
    #PBS -l walltime=''' + params['walltime'] + '''
    #PBS -l instance_type=''' + params['instance_type'] + '''
    #PBS -e /dev/null
    #PBS -o /dev/null
    # Create the DCV Session
    ''' + command_dcv_create_session + '''

    # Query dcvsimpleauth with add-user
    echo ''' + params['session_password_b64'] + ''' | base64 --decode | ''' + config.Config.DCV_SIMPLE_AUTH + ''' add-user --user ''' + session["user"] + ''' --session ''' + session_uuid + ''' --auth-dir ''' + config.Config.DCV_AUTH_DIR + '''

    # Uncomment if you want to disable Gnome Lock Screen (require webui restart)
    # GSETTINGS=$(which gsettings)
    # $GSETTINGS set org.gnome.desktop.lockdown disable-lock-screen true
    # $GSETTINGS set org.gnome.desktop.session idle-delay 0

    # Keep job open
    while true
        do
            session_keepalive=$(''' + config.Config.DCV_BIN + ''' list-sessions | grep ''' + session_uuid + ''' | wc -l)
            if [ $session_keepalive -ne 1 ]
                then
                    exit 0
            fi
            sleep 3600
        done
    '''

    payload = base64.b64encode(job_to_submit.encode()).decode()
    send_to_to_queue = post(config.Config.FLASK_ENDPOINT + "/api/scheduler/job",
                            headers={"X-SOCA-TOKEN": session["api_key"],
                                     "X-SOCA-USER": session["user"]},
                            data={"payload": payload},
                            verify=False)

    if send_to_to_queue.status_code == 200:
        job_id = str(send_to_to_queue.json()["message"])
        flash("Your session has been initiated (job number " + job_id + "). It will be ready within 20 minutes.", "success")
        new_session = DCVSessions(user=session["user"],
                                  job_id=job_id,
                                  session_number=parameters["session_number"],
                                  session_state="pending",
                                  session_host=False,
                                  session_password=session_password,
                                  session_uuid=session_uuid,
                                  is_active=True,
                                  created_on=datetime.datetime.utcnow())
        db.session.add(new_session)
        db.session.commit()
    else:
        flash("Error during job submission: " + str(send_to_to_queue.json()["message"]), "error")
    return redirect("/remote_desktop")
