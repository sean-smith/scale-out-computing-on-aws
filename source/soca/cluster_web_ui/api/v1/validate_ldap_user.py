import config
import ldap
from decorators import private_api
from flask import Blueprint, jsonify, make_response, request

validate_ldap_user = Blueprint('validate_ldap_user', __name__)


@validate_ldap_user.route("/api/validate_ldap_user",  methods=["POST"])
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

            # Check if user has sudo permissions
            sudoers_search_base = "ou=Sudoers," + base_dn
            sudoers_search_scope = ldap.SCOPE_SUBTREE
            sudoers_filter = 'cn=' + username
            is_sudo = con.search_s(sudoers_search_base, sudoers_search_scope, sudoers_filter)
            if is_sudo.__len__() > 0:
                sudoers = True
            else:
                sudoers = False

            return make_response(jsonify({'success': True, 'message': 'USER_VALID'}))

        except ldap.INVALID_CREDENTIALS:
            return make_response(jsonify({'success': False, 'message': 'INVALID_USER_CREDENTIAL'}))

        except ldap.SERVER_DOWN:
            return make_response(jsonify({'success': False, 'message': 'LDAP_SERVER_DOWN'}))
    else:
        return make_response(jsonify({'success': False, 'message': 'USERNAME_OR_PASSWORD_MISSING'}))
