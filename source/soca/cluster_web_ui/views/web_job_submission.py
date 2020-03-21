import logging

import api.v1.create_api_key as create_api_key
import api.v1.invalidate_api_key as invalidate_api_key
import api.v1.list_api_key as list_api_key
from flask import render_template, Blueprint, request, session, redirect

logger = logging.getLogger(__name__)

web_job_submission = Blueprint('web_job_submission', __name__, template_folder='templates')


@web_job_submission.route("/web_job_submission", methods=["GET"])
def check():
    username = "test"
    check_user_key = list_api_key.main(username)
    if check_user_key["success"] is False:
        if check_user_key["message"] == "NO_KEY_FOUND":
            create_user_key = create_api_key.main(username)
            if create_user_key["success"] is True:
                user_token = create_user_key["message"]
            else:
                logger.error("Unable to create API key for user: " + username + " with error: " + str(create_user_key))

    else:
        user_token = check_user_key["message"].token

    return render_template("web_based_submission.html",
                           username=username,
                           user_token=user_token,
                           master_host=request.host_url)


@web_job_submission.route("/reset_api_key", methods=["POST"])
def reset_key():
    username = request.form.get("username", None)
    token = request.form.get("token", None)
    if username == session["username"]:
        invalidate_user_key = invalidate_api_key.main(token)
        if invalidate_user_key["message"] is True:
            return redirect("/web_job_submission")
        else:
            logger.error("Error while trying to reset token: " + str(token) + " Trace: " +str(invalidate_user_key))
            return redirect("/web_job_submission")