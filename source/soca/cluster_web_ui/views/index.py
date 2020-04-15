import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint
from requests import post, get

logger = logging.getLogger(__name__)
index = Blueprint('index', __name__, template_folder='templates')





@index.route('/', methods=['GET'])
@login_required
def home():
    user = session['user']
    sudoers = session['sudoers']
    return render_template('index.html', user=user, sudoers=sudoers)

@index.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@index.route('/logout', methods=['GET'])
def logout():
    session_data = ["user", "sudoers", "api_key"]
    for param in session_data:
        session.pop(param, None)
    return redirect('/')

@index.route('/auth', methods=['POST'])
def authenticate():
    user = request.form.get('user')
    password = request.form.get('password')
    logger.info("Received login request for : " + str(user))
    if user is not None and password is not None:
        check_auth = post(config.Config.FLASK_ENDPOINT + '/api/ldap/authenticate',
                          data={"user": user, "password": password},
                          verify=False)
        logger.info(check_auth)
        if check_auth.status_code != 200:
            flash(check_auth.json()['message'])
            return redirect('/login')
        else:
            session['user'] = user.lower()
            logger.info("User authenticated, checking sudo permissions")
            check_sudo_permission = get(config.Config.FLASK_ENDPOINT + '/api/ldap/sudo',
                                        headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                        params={"user": user},
                                        verify=False)
            if check_sudo_permission.status_code == 200:
                session["sudoers"] = True
            else:
                session["sudoers"] = False


            return redirect('/')

    else:
        return redirect('/login')
