import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, delete
from decorators import login_required
import ast

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

