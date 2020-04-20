import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
import json
import base64
#from my_files import decrypt, user_has_permission
from models import ApplicationProfiles
import boto3

logger = logging.getLogger(__name__)
submit_job = Blueprint('submit_job', __name__, template_folder='templates')


def decrypt(encrypted_text):
    try:
        key = config.Config.SOCA_DATA_SHARING_SYMMETRIC_KEY
        cipher_suite = Fernet(key)
        decrypted_text = cipher_suite.decrypt(encrypted_text.encode())
        return {"success": True, "message": decrypted_text}
    except InvalidToken:
        return {"success": False, "message": "Invalid Token"}
    except InvalidSignature:
        return {"success": False, "message": "Invalid Signature"}
    except Exception as err:
        return {"success": False, "message": str(err)}



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
        input_file_info = False
        get_application_profile = ApplicationProfiles.query.filter_by(id=app).first()
        if get_application_profile:
            '''if input_file is not None:
                file_info = validate_input_file(input_file)
                if file_info["success"] is True:
                    input_file_info = file_info["message"]
                else:
                    flash(file_info["message"], "error")
                    input_file_info = False'''

            application_parameters = json.loads(base64.b64decode(get_application_profile.profile_parameters))
            print(application_parameters)
            client_ec2 = boto3.client("ec2")
            #get_all_ec2_instances = client_ec2._service_model.shape_for('InstanceType').enum

            return render_template('submit_job_selected_application.html',
                                   user=session["user"],
                                   application_parameters=application_parameters,
                                   input_file_info=input_file_info)
                                   #get_all_ec2_instances=get_all_ec2_instances)
        else:
            flash("Application not found.", "error")
            return redirect("/submit_job")


