import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post, delete
from models import ApiKeys
from decorators import login_required

logger = logging.getLogger("api_log")
admin_groups = Blueprint('admin_groups', __name__, template_folder='templates')



@admin_groups.route('/admin/groups', methods=['GET'])
@login_required
def index():
    get_all_groups = get(config.Config.FLASK_ENDPOINT + "/api/ldap/groups",
                         headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY})

    if get_all_groups.status_code == 200:
        all_groups = get_all_groups.json()["message"].keys()
    else:
        flash("Unable to list groups: " + str(get_all_groups._content), "error")
        all_groups = {}

    get_all_users = get(config.Config.FLASK_ENDPOINT + "/api/ldap/users",
                        headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY})

    if get_all_users.status_code == 200:
        all_users = get_all_users.json()["message"].keys()
    else:
        flash("Unable to list all_users: " + str(get_all_users._content), "error")
        all_users = {}

    return render_template('admin_groups.html', user=session['user'],
                           sudoers=session['sudoers'],
                           all_groups=all_groups,
                           all_users=all_users)


@admin_groups.route('/admin/manage_sudo', methods=['POST'])
@login_required
def manage_sudo():
    user = request.form.get('user', None)
    action = request.form.get('action', None)
    if user == session["user"]:
        flash("You can not manage your own Admin permissions.", "error")
        return redirect("/admin/users")

    if action in ["grant", "revoke"]:
        if user is not None:
            give_sudo = post(config.Config.FLASK_ENDPOINT + "/api/ldap/sudo",
                                   headers={"X-SOCA-TOKEN": session["api_key"],
                                            "X-SOCA-USER": session["user"]},
                                   data={"user": user})

            if give_sudo.status_code == 200:
                flash("Admin permissions granted", "success")
            elif give_sudo.status_code == 203:
                if action == "grant":
                    flash(user + " already has Admin permission", "error")
                else:
                    flash(user + " does not have Admin privileges", "error")
                return redirect("/admin")

            else:
                flash("Unable to grant user Admin permission: " + str(give_sudo._content) , "error")
            return redirect("/admin/users")
        else:
            return redirect("/admin/users")
    else:
        return redirect("/admin/users")

@admin_groups.route('/admin/create_new_account', methods=['POST'])
@login_required
def create_new_account():
        user = str(request.form.get('user'))
        password = str(request.form.get('password'))
        email = str(request.form.get('email'))
        sudoers = bool(request.form.get('sudo'))
        uid = request.form.get('uid', None)
        gid = request.form.get('gid', None)
        create_new_user = post(config.Config.FLASK_ENDPOINT + "/api/ldap/user",
                               headers={"X-SOCA-TOKEN": session["api_key"],
                                        "X-SOCA-USER": session["user"]},
                               data={"user": user,
                                     "password": password,
                                     "email": email,
                                     "sudoers": sudoers,
                                     "uid": uid,
                                     "gid": gid}).json()

        if create_new_user["success"] is False:
            flash("Unable to create " + user +" for the following reason: " + create_new_user["message"], "error")
            return redirect('/admin/users')
        else:
            # Create API key
            create_user_key = get(config.Config.FLASK_ENDPOINT + '/api/user/api_key',
                                  headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                  params={"user": user}, verify=False).json()
            if create_user_key["success"] is False:
                flash("User created but unable to generate API token: " + str(create_user_key._content), "error")
            else:
                flash("User " + user + " has been created successfully", "success")
        return redirect('/admin/users')


@admin_groups.route('/admin/delete_account', methods=['POST'])
@login_required
def delete_account():
    if session['sudoers'] is True:
        user = str(request.form.get('user_to_delete'))
        if session['user'] == user:
            flash("You cannot delete your own account.", "error")
            return redirect('/admin/users')

        delete_user = delete(config.Config.FLASK_ENDPOINT + "/api/ldap/user",
                             headers={"X-SOCA-TOKEN": session["api_key"],
                                      "X-SOCA-USER": session["user"]},
                             data={"user": user}).json()

        if delete_user["success"] is True:
            flash('User: ' + user + ' has been deleted correctly', "success")
        else:
            flash('Could not delete user: ' + user + '. Check trace: ' + str(delete_user), "error")

        return redirect('/admin/users')

    else:
        return redirect('/')