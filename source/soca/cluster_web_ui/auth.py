import base64
import os

import api.openldap as openldap
import requests
from flask import session
from jose import jwt


def sso_authorization(code):
    authorization = 'Basic ' + base64.b64encode(parameters.get_parameter("cognito","cognito_app_id").encode() + ':'.encode() + parameters.get_parameter("cognito","cognito_app_secret").encode()).decode()
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'Authorization': authorization}

    data = {'grant_type': 'authorization_code',
            'client_id': parameters.get_parameter("cognito", "cognito_app_id"),
            'code': code,
            'redirect_uri': parameters.get_parameter("cognito", "cognito_callback_url")}

    oauth_token = requests.post(parameters.get_parameter("cognito", "cognito_oauth_token_endpoint"), data=data, headers=headers).json()
    id_token = oauth_token['id_token']
    access_token = oauth_token['access_token']
    headers = jwt.get_unverified_headers(id_token)
    keys = requests.get(parameters.get_parameter("cognito","cognito_jws_keys_endpoint")).json().get('keys')
    key = list(filter(lambda k: k['kid'] == headers['kid'], keys)).pop()
    claims = jwt.decode(id_token, key, access_token=access_token, algorithms=[key['alg']], audience=parameters.get_parameter("cognito","cognito_app_id"))
    if claims:
        try:
            username = claims['email'].split('@')[0]
        except Exception as err:
            return {'success': False,
                    'message': 'Error reading SSO claims. ' + str(claims) + ' Err: ' + str(err)}

        # Simply check if user exist
        # We could do a simply ldap lookup, but making sure user has a private key is more important
        # without private key, a user (even with valid ldap account) won't be able to do anything
        check_if_file_exist = os.path.isfile('/data/home/' + username + '/.ssh/id_rsa')
        if check_if_file_exist is True:
            # Valid user, create session
            session['username'] = username
            # verify sudo permission
            if openldap.verify_sudo_permissions(username)["success"] is True:
                session["sudoers"] = True
            else:
                session["sudoers"] = False

            return {'success': True,
                    'message': ''}
        else:
            return {'success': False,
                    'message': 'user_not_found'}
    else:
        return {'success': False,
                'message': 'SSO error. ' + str(claims)}