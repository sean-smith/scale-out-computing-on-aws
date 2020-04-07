import urllib
from functools import wraps
import config
from models import ApiKeys
from flask import request, redirect, session, flash
from requests import get


# Restricted API can only be accessed using Flask Root API key
# In other words, @restricted_api can only be triggered by the web application
def restricted_api(f):
    @wraps(f)
    def restricted_resource(*args, **kwargs):
        token = request.headers.get("X-SOCA-TOKEN", None)
        if token == config.Config.API_ROOT_KEY:
                return f(*args, **kwargs)
        return {"success": False, "message": "Not authorized"}, 401
    return restricted_resource


# Admin API can only be accessed by a token who as "sudo" permission or using Flask root API key
def admin_api(f):
    @wraps(f)
    def admin_resource(*args, **kwargs):
        user = request.headers.get("X-SOCA-USER", None)
        token = request.headers.get("X-SOCA-TOKEN", None)
        if token == config.Config.API_ROOT_KEY:
                return f(*args, **kwargs)

        if user is None or token is None:
            return {"success": False, "message": "Not Authorized"}, 401
        else:
            token_has_sudo = ApiKeys.query.filter_by(token=token,
                                                     user=user,
                                                     scope="sudo",
                                                     is_active=True).first()
            if token_has_sudo:
                if request.method == "DELETE":
                    target_user = request.args.get("user", None)
                    target_group = request.args.get("group", None)
                    if target_user == user:
                        return {"success": False, "message": "You can not delete your own user"}, 401
                    elif user+"group" == target_group:
                        return {"success": False, "message": "You can not delete your own group"}, 401
                    else:
                        return f(*args, **kwargs)
                else:
                    return f(*args, **kwargs)
            else:
                return {"success": False, "message": "Not authorized"}, 401
    return admin_resource


# Private API can only be accessed with a valid pair of user/token
# User can only interact with their own environment
def private_api(f):
    @wraps(f)
    def private_resource(*args, **kwargs):
        user = request.headers.get("X-SOCA-USER", None)
        token = request.headers.get("X-SOCA-TOKEN", None)
        if request.method == "GET":
            target_user = request.args.get("user", None)
            target_group = request.args.get("group", None)
        else:
            target_user = request.form.get("user", None)
            target_group = request.form.get("group", None)

        if token == config.Config.API_ROOT_KEY:
            return f(*args, **kwargs)

        if user is None or token is None:
            return {"success": False, "message": "NOT_PERMITTED"}, 401
        else:
            token_is_valid = ApiKeys.query.filter_by(token=token,
                                                     user=user,
                                                     is_active=True).first()
            if token_is_valid and token_is_valid.scope == "sudo":
                return f(*args, **kwargs)
            else:
                if request.method == "DELETE":
                    if token_is_valid and user == target_user:
                        return {"success": False, "message": "You can not delete your own user"}, 401
                    elif token_is_valid and user + "group" == target_group:
                        return {"success": False, "message": "You can not delete your own group"}, 401
                    else:
                        return {"success": False, "message": "Not authorized"}, 401
                else:
                    if (token_is_valid and user == target_user) or (token_is_valid and user + "group" == target_group):
                        return f(*args, **kwargs)
                    else:
                        return {"success": False, "message": "Not authorized"}, 401

    return private_resource


# Read/Only APIs only require a valid pair of token
def read_only_api(f):
    @wraps(f)
    def ro_resource(*args, **kwargs):
        user = request.headers.get("X-SOCA-USER", None)
        token = request.headers.get("X-SOCA-TOKEN", None)
        if token == config.Config.API_ROOT_KEY:
            return f(*args, **kwargs)

        token_is_valid = ApiKeys.query.filter_by(token=token,
                                                 user=user,
                                                 is_active=True).first()

        if token_is_valid and request.method == "GET":
            return f(*args, **kwargs)
        else:
            return {"success": False, "message": "Not authorized"}, 401

    return ro_resource


# Views require a valid login
def login_required(f):
    @wraps(f)
    def validate_account():
        if "user" in session:
            if "api_key" in session:
                # If a new API key has been issued,
                check_existing_key = ApiKeys.query.filter_by(user=session["user"], is_active=True).first()
                if check_existing_key.token != session["api_key"]:
                    # Update API Key in session
                    session["api_key"] = check_existing_key.token
                else:
                    # API Key exist and is already up-to-date
                    pass

                #  Make sure the scope still align with SUDO permissions (eg: when admin grant/revoke sudo)
                if session["sudoers"] is True and check_existing_key.scope == "user":
                    # SUDO permissions were revoked for the user
                    session["sudoers"] = False

                if session["sudoers"] is False and check_existing_key.scope == "sudo":
                    # SUDO permissions were granted to the user
                    session["sudoers"] = True

            else:
                # Retrieve current API key for the user or create a new one
                check_user_key = get(config.Config.FLASK_ENDPOINT + "/api/user/api_key",
                                     headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                     params={"user": session["user"]}).json()
                session["api_key"] = check_user_key["message"]

            return f()
        else:
            if config.Config.ENABLE_SSO is True:
                data = {'redirect_uri': config.Config.COGNITO_CALLBACK_URL,
                        'client_id': config.Config.COGNITO_APP_ID,
                        'response_type': 'code',
                        'state': request.path}
                oauth_url = config.Config.COGNITO_OAUTH_AUTHORIZE_ENDPOINT + '?' + urllib.parse.urlencode(data)
                return redirect(oauth_url)
            else:
                return redirect('/login')
    return validate_account


# Views restricted to admin
def admin_only(f):
    @wraps(f)
    def validate_account():
        if "sudoers" in session:
            if session["sudoers"] is True:
                return f()
            else:
                flash("Sorry this page requires admin privileges.", "error")
                return redirect("/")

        else:
            return redirect('/login')

    return validate_account