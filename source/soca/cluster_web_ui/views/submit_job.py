import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint, send_file
import errno
import math
import os
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
import json
import base64
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


def validate_input_file(file_uid):
    validate_input_file = decrypt(file_uid)
    if validate_input_file["success"] is True:
        input_file_info = json.loads(validate_input_file["message"])
        current_user = session["user"]
        if current_user != input_file_info["file_owner"]:
            return {"success": False, "message": "You are not authorized to use this file"}
        else:
            return {"success": True, "message": config.Config.USER_HOME + "/" + input_file_info["file_path"]}
    else:
        return {"success": False, "message": "You are not authorized to use this file"}


@submit_job.route('/submit_job', methods=['GET'])
@login_required
def index():
    app = request.args.get("app", None)
    input_file = request.args.get("input_file", None)
    if app is None:
        application_profiles = {}
        get_all_application_profiles = ApplicationProfiles.query.all()
        for profile in get_all_application_profiles:
            application_profiles[profile.id] = {"profile_name": profile.profile_name,
                                                "forward_input": input_file
                                                }

        return render_template('submit_job.html',
                               user=session["user"],
                               application_profiles=application_profiles)
    else:
        input_file_info = False
        get_application_profile = ApplicationProfiles.query.filter_by(id=app).first()
        if get_application_profile:
            if input_file is not None:
                file_info = validate_input_file(input_file)
                if file_info["success"] is True:
                    input_file_info = file_info["message"]
                else:
                    flash(file_info["message"], "error")
                    input_file_info = False

            application_parameters = json.loads(base64.b64decode(get_application_profile.profile_parameters))
            client_ec2 = boto3.client("ec2")
            get_all_ec2_instances = client_ec2._service_model.shape_for('InstanceType').enum

            return render_template('submit_job_selected_application.html',
                                   user=session["user"],
                                   application_parameters=application_parameters,
                                   input_file_info=input_file_info,
                                   get_all_ec2_instances=get_all_ec2_instances)
        else:
            flash("Application not found.", "error")
            return redirect("/submit_job")


