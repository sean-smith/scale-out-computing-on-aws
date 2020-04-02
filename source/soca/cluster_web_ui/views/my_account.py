import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post
from decorators import login_required
import ast
import string
import random

logger = logging.getLogger("api_log")
my_account = Blueprint('my_account', __name__, template_folder='templates')


@my_account.route("/my_account", methods=["GET"])
@login_required
def index():
    print(session["api_key"])
    get_ldap_info = get(config.Config.FLASK_ENDPOINT + "/api/ldap/user",
                               headers={"X-SOCA-TOKEN": session["api_key"],
                                        "X-SOCA-USERNAME": session["username"]},
                               params={"username": session["username"]})

    if get_ldap_info.status_code == 200:
        info = ast.literal_eval(get_ldap_info.json()["message"])
        for attribute in info:
            user_dn = attribute[0]
            user_data = attribute[1]

    else:
        user_dn = "UNKNOWN"
        user_data = {}
        flash("Unable to retrieve your LDAP information. Error: " + str(get_ldap_info._content), "error")

    return render_template("my_account.html",
                           username=session["username"],
                           user_dn=user_dn,
                           user_data=user_data)


@my_account.route("/reset_password", methods=["POST"])
def reset_key():
    password = request.form.get("password", None)
    password_verif = request.form.get("password_verif", None)
    admin_reset = request.form.get("admin_reset", None)
    if admin_reset == "yes":
        # Admin can generate a temp password on behalf of the user
        username = request.form.get("username", None)
        if username is None:
            return redirect("/admin")
        elif username == session["username"]:
            flash("You can not reset your own password using this tool. Please visit 'My Account' section for that", "error")
            return redirect("/admin")
        else:
            password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(8))
            change_password = post(config.Config.FLASK_ENDPOINT + '/api/user/reset_password',
                                       headers={"X-SOCA-TOKEN": session["api_key"],
                                                "X-SOCA-USERNAME": session["username"]},
                                       data={"username": username,
                                             "password": password},
                                       verify=False)
            if change_password.status_code == 200:
                flash("Password for " + username + " has been changed to " + password + ".<hr> User is recommended to change it using 'My Account' section", "success")
                return redirect("/admin")
            else:
                flash("Unable to reset password. Error: " + str(change_password._content), "error")
                return redirect("/admin")
    else:
        if password is not None:
            # User can change their own password
            if password == password_verif:
                change_password = post(config.Config.FLASK_ENDPOINT + '/api/user/reset_password',
                                       headers={"X-SOCA-TOKEN": session["api_key"],
                                                "X-SOCA-USERNAME": session["username"]},
                                       data={"username": session["username"],
                                             "password": password},
                                       verify=False)

                if change_password.status_code == 200:
                    flash("Your password has been changed succesfully.", "success")
                    return redirect("/my_account")
                else:
                    flash("Unable to reset your password. Error: " +str(change_password._content), "error")
                    return redirect("/my_account")
            else:
                flash("Password does not match", "error")
                return redirect("/my_account")
        else:
            return redirect("/my_account")