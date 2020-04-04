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
    get_ldap_info = get(config.Config.FLASK_ENDPOINT + "/api/ldap/user",
                               headers={"X-SOCA-TOKEN": session["api_key"],
                                        "X-SOCA-USER": session["user"]},
                               params={"user": session["user"]})

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
                           user=session["user"],
                           user_dn=user_dn,
                           user_data=user_data)


@my_account.route("/reset_password", methods=["POST"])
def reset_key():
    password = request.form.get("password", None)
    password_verif = request.form.get("password_verif", None)
    admin_reset = request.form.get("admin_reset", None)
    if admin_reset == "yes":
        # Admin can generate a temp password on behalf of the user
        user = request.form.get("user", None)
        if user is None:
            return redirect("/admin/users")
        elif user == session["user"]:
            flash("You can not reset your own password using this tool. Please visit 'My Account' section for that", "error")
            return redirect("/admin/users")
        else:
            password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(8))
            change_password = post(config.Config.FLASK_ENDPOINT + '/api/user/reset_password',
                                       headers={"X-SOCA-TOKEN": session["api_key"],
                                                "X-SOCA-USER": session["user"]},
                                       data={"user": user,
                                             "password": password},
                                       verify=False)
            if change_password.status_code == 200:
                flash("Password for " + user + " has been changed to " + password + "<hr> User is recommended to change it using 'My Account' section", "success")
                return redirect("/admin/users")
            else:
                flash("Unable to reset password. Error: " + str(change_password._content), "error")
                return redirect("/admin/users")
    else:
        if password is not None:
            # User can change their own password
            if password == password_verif:
                change_password = post(config.Config.FLASK_ENDPOINT + '/api/user/reset_password',
                                       headers={"X-SOCA-TOKEN": session["api_key"],
                                                "X-SOCA-USER": session["user"]},
                                       data={"user": session["user"],
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