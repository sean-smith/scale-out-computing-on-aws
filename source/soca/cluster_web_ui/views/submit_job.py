import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
import json
import base64
from views.my_files import decrypt, user_has_permission
from models import ApplicationProfiles
import boto3

logger = logging.getLogger(__name__)
submit_job = Blueprint('submit_job', __name__, template_folder='templates')



@submit_job.route('/submit_job', methods=['GET'])
@login_required
def index():
    app = request.args.get("app", None)
    input_file = request.args.get("input_file", None)
    if input_file is None:
        # User must specify input first
        flash("What input file do you want to use? <hr> Navigate to the folder where your input file is located then click 'Use as Simulation Input' icon: <i class='fas fa-microchip fa-lg'  style='color: grey'></i>", "info")
        return redirect("/my_files")

    if app is None:
        # Input specified but not app
        application_profiles = {}
        get_all_application_profiles = ApplicationProfiles.query.all()
        for profile in get_all_application_profiles:
            application_profiles[profile.id] = {"profile_name": profile.profile_name}
        return render_template('submit_job.html',
                               user=session["user"],
                               application_profiles=application_profiles,
                               input_file=input_file)
    else:
        # input and app specified
        input_file_info = request.args.get('input_file')
        get_application_profile = ApplicationProfiles.query.filter_by(id=app).first()
        if get_application_profile:
            profile_form = base64.b64decode(get_application_profile.profile_form)
            profile_job = base64.b64decode(get_application_profile.profile_job)

            return render_template('submit_job_selected_application.html',
                                   user=session["user"],
                                   profile_form=profile_form,
                                   profile_job=profile_job)
        else:
            flash("Application not found.", "error")
            return redirect("/submit_job")


@submit_job.route('/submit_job', methods=['POST'])
@login_required
def job_submission():
    if "app" not in request.form or "input_file" not in request.form:
        flash("Missing required parameters.", "error")
        return redirect("/submit_job")

    app = request.form["app"]
    input_file_info = request.form['input_file']
    get_application_profile = ApplicationProfiles.query.filter_by(id=app).first()
    if get_application_profile:
        file_info = decrypt(input_file_info)
        if file_info["success"] != True:
            flash("Unable to read this file because of " + str(file_info), "error")
            return redirect("/submit_job")
        profile_form = base64.b64decode(get_application_profile.profile_form).decode()


        profile_job = base64.b64decode(get_application_profile.profile_job)

        input_path = json.loads(file_info["message"])["file_path"]
        input_name = input_path.split("/")[-1]

        return render_template('submit_job_selected_application.html',
                                   profile_name=get_application_profile.profile_name,
                                   user=session["user"],
                                   profile_form=profile_form,
                                   profile_job=profile_job,
                                   input_path=input_path,
                                   input_name=input_name)
                                   #get_all_ec2_instances=get_all_ec2_instances)
    else:
        flash("Application not found.", "error")
        return redirect("/submit_job")


@submit_job.route('/submit_job/send', methods=['POST'])
@login_required
def send_job():
    return str(request.form)