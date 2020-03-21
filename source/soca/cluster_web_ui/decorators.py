import urllib
from functools import wraps

import config
from flask import jsonify, request, redirect, session, make_response


def private_api(f):
    @wraps(f)
    def protect_resource(*args, **kwargs):
        if request.environ.get("REMOTE_ADDR", False) == "127.0.0.1" \
                and request.headers.get('X-SOCA-TOKEN', None) == config.Config.SERVER_API_KEY:
            return f(*args, **kwargs)
        else:
            return make_response(jsonify({"success": False, "message": "NOT_PERMITTED"}), 403)

    return protect_resource


def login_required(f):
    @wraps(f)
    def validate_account():
        if 'username' in session:
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