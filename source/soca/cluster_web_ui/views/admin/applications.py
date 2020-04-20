import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post, delete, put
from models import db, ApplicationProfiles
from decorators import login_required, admin_only
import base64
import datetime
import json
logger = logging.getLogger("api_log")
admin_applications = Blueprint('admin_applications', __name__, template_folder='templates')


@admin_applications.route('/admin/applications', methods=['GET'])
@login_required
@admin_only
def index():
    form_builder = {
        "profile_name": {
            "placeholder": "Name of your application profile",
            "help": "Name or your profile (must be smaller than 255 characters) <br> Choose a friendly naming convention such as 'My Application (version 1)' ",
            "required": True},
        "binary": {
            "placeholder": "Location of the application binary",
            "help": "The binary (or executable) path to use to launch your application. It's usually located within the 'bin' folder of your app.",
            "required": True},
        "input_parameter": {
            "placeholder": "Input parameter (Eg: -i , --input)",
            "help": "The parameter to choose when launching a job",
            "required": False},
        "required_parameters": {
            "placeholder": "Required parameters you want your users to configure",
            "help": "Comma separated list of parameters you want your users to specify",
            "required": False},
        "optional_parameters": {
            "placeholder": "(Optional) List of any additional parameters",
            "help": "Commad separated list of parameters/commands to be automatically added to the job command on behalf of the users. Users cannot remove/change them.",
            "required": False},
        "scheduler_parameters": {
            "placeholder": "List of scheduler parameters you want to apply to the job.",
            "help": "<a target='_blank' href='https://awslabs.github.io/scale-out-computing-on-aws/tutorials/integration-ec2-job-parameters/'>See this link</a> for a list of available parameters. <hr> If you want to enable 300 GB scratch disk and EFA by default, enter 'scratch_size=300,efa_support=True'",
            "required": False},
        "ld_library_path": {
            "placeholder": "(Optional) Append your $LD_LIBRARY_PATH",
            "help": "If your application require specific library, you can append the location to your system $LD_LIBRARY_PATH",
            "required": False},
        "path": {
            "placeholder": "(Optional) Append your $PATH",
            "help": "If your application require specific path, you can append the location to your system $PATH",
            "required": False},
        "help": {
            "placeholder": "(Optional) Link to your own help/wiki",
            "help": "Specify a link (such as wiki or internal documentation) your users access to learn more about this application.",
            "required": False},

    }

    return render_template('admin_applications.html', user=session['user'],form_builder=form_builder)


@admin_applications.route('/admin/applications/create', methods=['post'])
@login_required
@admin_only
def create_application():
    parameters = ["profile_name",
                  "binary",
                  "input_parameter",
                  "required_parameters",
                  "optional_parameters",
                  "ld_library_path",
                  "path"]

    for parameter in parameters:
        if parameter not in request.form.keys():
            flash("Missing parameters", "error")
            return redirect("/admin/applications")
    if request.form["profile_name"].__len__() > 255:
        flash("Profile name must be lower than 255 characters", "error")
        return redirect("/admin/applications")

    # encode parameters to simplify DB storage
    profile_info = json.dumps({
        "profile_name": request.form["profile_name"],
        "binary": request.form["binary"],
        "input_parameter": request.form["input_parameter"],
        "required_parameters": request.form["required_parameters"].split(","),
        "optional_parameters": request.form["optional_parameters"].split(","),
        "ld_library_path": request.form["ld_library_path"],
        "path": request.form["path"],
        "pre-exec": False if "pre-exec" not in request.form.keys() else True,
        "post-exec": False if "post-exec" not in request.form.keys() else True,
    })

    new_app_profile = ApplicationProfiles(creator=session["user"],
                                          profile_name=request.form["profile_name"],
                                          profile_parameters=base64.b64encode(profile_info.encode()),
                                          created_on=datetime.datetime.utcnow())
    db.session.add(new_app_profile)
    db.session.commit()
    flash(request.form["profile_name"] + " created successfully.", "success")
    return redirect("/admin/applications")

