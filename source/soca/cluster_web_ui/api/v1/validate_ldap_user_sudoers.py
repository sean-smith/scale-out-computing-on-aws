import config
import ldap
from decorators import private_api
from flask import Blueprint, jsonify, make_response

validate_ldap_user_sudoers = Blueprint('validate_ldap_user_sudoers', __name__)


@validate_ldap_user_sudoers.route("/api/validate_ldap_user_sudoers/<string:username>",  methods=["GET"])
@private_api
def main(username):
    ldap_host = config.Config.LDAP_HOST
    base_dn = config.Config.LDAP_BASE_DN
    con = ldap.initialize('ldap://{}'.format(ldap_host))
    try:
        sudoers_search_base = "ou=Sudoers," + base_dn
        sudoers_search_scope = ldap.SCOPE_SUBTREE
        sudoers_filter = 'cn=' + username
        is_sudo = con.search_s(sudoers_search_base, sudoers_search_scope, sudoers_filter)
        if is_sudo.__len__() > 0:
            return make_response(jsonify({'success': True, 'message': "USER_HAS_SUDO_PERMISSION"}))
        else:
            return make_response(jsonify({'success': False, 'message': "NO_SUDO_PERMISSION"}))

    except ldap.SERVER_DOWN:
        return make_response(jsonify({'success': False, 'message': 'LDAP_SERVER_DOWN'}))