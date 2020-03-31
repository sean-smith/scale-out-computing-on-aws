import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint
from requests import post, get
from models import FlaskSessions

logger = logging.getLogger(__name__)
index = Blueprint('index', __name__, template_folder='templates')


def session_info():
    return {'username': session['username'].lower(),
            'sudoers': session['sudoers']
            }


@index.route('/', methods=['GET'])
@login_required
def home():
    username = session_info()['username']
    sudoers = session_info()['sudoers']
    return render_template('index.html', username=username, sudoers=sudoers)


@index.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@index.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect('/')


@index.route('/auth', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    password = request.form.get('password')
    logger.info("Received login request for : " + str(username))
    if username is not None and password is not None:
        check_auth = post(config.Config.FLASK_ENDPOINT + '/api/ldap/authenticate',
                          data={"username": username, "password": password},
                          verify=False).json()

        logger.info(check_auth)
        if check_auth['success'] is False:
            flash(check_auth['message'])
            return redirect('/login')
        else:
            session['username'] = username
            logger.info("User authenticated, checking sudo permissions")
            check_sudo_permission = get(config.Config.FLASK_ENDPOINT + '/api/ldap/sudo',
                                        headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                        params={"username": username},
                                        verify=False).json()
            logger.info(check_sudo_permission)
            if check_sudo_permission["success"] is True:
                session["sudoers"] = True
            else:
                session["sudoers"] = False

            return redirect('/')

    else:
        return redirect('/login')
