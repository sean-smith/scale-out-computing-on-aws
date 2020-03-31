import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post, delete
from models import ApiKeys
from decorators import login_required

logger = logging.getLogger("api_log")
users = Blueprint('users', __name__, template_folder='templates')



@users.route('/users', methods=['GET'])
@login_required
def index():
    username = session['username']
    sudoers = session['sudoers']
    get_all_users = get(config.Config.FLASK_ENDPOINT + "/api/ldap/users",
                        headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY}).json()
    all_users = get_all_users["message"].keys()
    return render_template('users.html', username=username, sudoers=sudoers, all_users=all_users)

@users.route('/create_new_account', methods=['POST'])
@login_required
def create_new_account():
    if session['sudoers'] is True:
        username = str(request.form.get('username'))
        password = str(request.form.get('password'))
        email = str(request.form.get('email'))
        sudoers = bool(request.form.get('sudo'))
        uid = request.form.get('uid', None)
        gid = request.form.get('gid', None)
        create_new_user = post(config.Config.FLASK_ENDPOINT + "/api/ldap/user",
                               headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                               data={"username": username,
                                     "password": password,
                                     "email": email,
                                     "sudoers": sudoers,
                                     "uid": uid,
                                     "gid": gid}).json()

        if create_new_user["success"] is False:
            flash("Unable to create " + username +" for the following reason: " +create_new_user["message"], "error")
            return redirect('/users')
        else:
            # Create API key
            create_user_key = get(config.Config.FLASK_ENDPOINT + '/api/user/api_key',
                                  headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                  params={"username": username}, verify=False).json()
            if create_user_key["success"] is False:
                flash("User created but unable to generate API token: " + str(create_user_key._content), "error")
            else:
                flash("User " + username + " has been created successfully", "success")
            return redirect('/users')

    else:
        return redirect('/')

@users.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    if session['sudoers'] is True:
        username = str(request.form.get('user_to_delete'))
        if session['username'] == username:
            flash("You cannot delete your own account.", "error")
            return redirect('/users')

        delete_user = delete(config.Config.FLASK_ENDPOINT + "/api/ldap/user",
                               headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                               data={"username": username}).json()

        if delete_user["success"] is True:
            flash('User: ' + username + ' has been deleted correctly', "success")
        else:
            flash('Could not delete user: ' + username + '. Check trace: ' + str(delete_user), "error")

        return redirect('/users')

    else:
        return redirect('/')