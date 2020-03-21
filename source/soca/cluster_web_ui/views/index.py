import logging

import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint
from requests import post

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
    if username is not None and password is not None:
        check_auth = post(config.Config.FLASK_ENDPOINT + '/api/validate_ldap_user',
                          headers={"X-SOCA-ADMIN": config.Config.SERVER_API_KEY},
                          data={"username": username, "password": password},
                          verify=False)
        logger.info(check_auth.json())
        if check_auth.json()['success'] is False:
            flash(check_auth.json()['message'])
            return redirect('/login')
        else:
            return redirect('/')

    else:
        return redirect('/login')
