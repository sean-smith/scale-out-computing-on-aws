import logging

import config
from flask import render_template, Blueprint, request, redirect
from requests import get, post

logger = logging.getLogger("api_log")
web_job_submission = Blueprint('web_job_submission', __name__, template_folder='templates')


@web_job_submission.route("/web_job_submission", methods=["GET"])
def check():
    username = "mickael"
    check_user_key = get(config.Config.FLASK_ENDPOINT + "/api/users/list_api_key/" + username,
                         headers={"X-SOCA-ADMIN": config.Config.SERVER_API_KEY})
    logger.info(str(request) + ": check_user_key: Status: " + str(check_user_key.status_code))
    logger.debug("check_user_key: Content: " + str(check_user_key._content))

    if check_user_key.json()["success"] is False:
        if check_user_key.json()["message"] == "NO_KEY_FOUND":
            create_user_key = post(config.Config.FLASK_ENDPOINT + '/api/users/create_api_key',
                                   headers={"X-SOCA-ADMIN": config.Config.SERVER_API_KEY},
                                   data={"username": username},
                                   verify=False)
            logger.info(str(request) + ": create_user_key: Status: " + str(create_user_key.status_code))
            logger.debug("create_user_key: Content: " + str(create_user_key._content))
            if create_user_key.json()["success"] is True:
                user_token = create_user_key.json()["message"]
            else:
                logger.error("Unable to create API key for user: " + username + " with error: " + str(create_user_key))
                user_token = "UNABLE_TO_GENERATE_TOKEN"
    else:
        user_token = check_user_key.json()["message"]["token"]

    return render_template("web_based_submission.html",
                           username=username,
                           user_token=user_token,
                           master_host=request.host_url)


@web_job_submission.route("/reset_api_key", methods=["POST"])
def reset_key():
    username = request.form.get("username", None)
    token = request.form.get("token", None)
    if username is not None and token is not None:
        invalidate_user_key = post(config.Config.FLASK_ENDPOINT + '/api/users/invalidate_api_key',
                                   headers={"X-SOCA-ADMIN": config.Config.SERVER_API_KEY},
                                   data={"token": token, "username": username},
                                   verify=False)
        logger.info(str(request) + ": invalidate_user_key: Status: " + str(invalidate_user_key.status_code))
        logger.debug("invalidate_user_key: Content: " + str(invalidate_user_key._content))
        if invalidate_user_key.json()["message"] is True:
            return redirect("/web_job_submission")
        else:
            logger.error("Error while trying to reset token: " + str(token) + " Trace: " +str(invalidate_user_key))
            return redirect("/web_job_submission")

    else:
        return redirect("/web_job_submission")