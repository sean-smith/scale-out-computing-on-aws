import config
import ldap
from decorators import private_api
from flask import Blueprint, jsonify, make_response, request

authenticate = Blueprint('authenticate', __name__)


@authenticate.route("/api/ldap/authenticate",  methods=["POST"])
@private_api
def main():
    username = request.form.get("username", False)
    password = request.form.get("password", False)
    if username is not False and password is not False:
        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN
        user_dn = 'uid={},ou=people,{}'.format(username, base_dn)
        con = ldap.initialize('ldap://{}'.format(ldap_host))
        try:
            con.bind_s(user_dn, password, ldap.AUTH_SIMPLE)
            return make_response(jsonify({'success': True, 'message': 'USER_VALID'}))

        except ldap.INVALID_CREDENTIALS:
            return make_response(jsonify({'success': False, 'message': 'INVALID_USER_CREDENTIAL'}))

        except ldap.SERVER_DOWN:
            return make_response(jsonify({'success': False, 'message': 'LDAP_SERVER_DOWN'}))
    else:
        return make_response(jsonify({'success': False, 'message': 'USERNAME_OR_PASSWORD_MISSING'}))
