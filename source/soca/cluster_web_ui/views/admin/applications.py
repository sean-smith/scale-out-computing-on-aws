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
    return render_template('admin_applications.html',
                           user=session['user'],
                           page="application")


@admin_applications.route('/admin/applications/create', methods=['post'])
@login_required
@admin_only
def create_application():
    required_parameters = ["submit_job_script", "profile_name", "submit_job_form"]
    print(request.form)
    for parameter in required_parameters:
        if parameter not in request.form:
            flash("Missing parameters. Make sure you have sent the correct inputs", "error")
            return redirect("/admin/applications")

    new_app_profile = ApplicationProfiles(creator=session["user"],
                                          profile_name=request.form["profile_name"],
                                          profile_form=request.form["submit_job_form"],
                                          profile_job=request.form["submit_job_script"],
                                          created_on=datetime.datetime.utcnow())
    db.session.add(new_app_profile)
    db.session.commit()
    flash(request.form["profile_name"] + " created successfully.", "success")
    return redirect("/admin/applications")

