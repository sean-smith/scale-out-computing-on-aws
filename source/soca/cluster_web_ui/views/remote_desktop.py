import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, delete
from decorators import login_required
import boto3
from models import db, DCVSessions
logger = logging.getLogger("api_log")
remote_desktop = Blueprint('remote_desktop', __name__, template_folder='templates')
client = boto3.client('ec2')


@remote_desktop.route('/remote_desktop', methods=['GET'])
@login_required
def index():
    user_sessions = DCVSessions.query.filter_by(user=session["user"]).all()
    if user_sessions:
        print(user_sessions)

    max_number_of_sessions = config.Config.DCV_MAX_SESSION_COUNT
    # List of instances not available for DCV. Adjust as needed
    blacklist = ['metal', 'nano', 'micro']
    all_instances_available = client._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    return render_template('remote_desktop.html',
                           user_sessions={},
                           page='remote_desktop',
                           all_instances=all_instances,
                           max_number_of_sessions=max_number_of_sessions)

@remote_desktop.route('/remote_desktop/create', methods=['POST'])
@login_required
def create():
    user_sessions = DCVSessions.query.filter_by(user=session["user"]).all()
    if user_sessions:
        print(user_sessions)

    max_number_of_sessions = config.Config.DCV_MAX_SESSION_COUNT
    # List of instances not available for DCV. Adjust as needed
    blacklist = ['metal', 'nano', 'micro']
    all_instances_available = client._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    return render_template('remote_desktop.html',
                           user_sessions={},
                           page='remote_desktop',
                           all_instances=all_instances,
                           max_number_of_sessions=max_number_of_sessions)