import config
import ldap
from decorators import private_api
from flask import Blueprint, jsonify, make_response

validate_ldap_user = Blueprint('validate_ldap_user', __name__)


@validate_ldap_user.route("/api/validate_ldap_user/<string:username>",  methods=["GET"])
@private_api
def main(username):
    ldap_host = config.Config.LDAP_HOST
    base_dn = config.Config.LDAP_BASE_DN
    con = ldap.initialize('ldap://{}'.format(ldap_host))
    try:
        people_search_base = "ou=People," + base_dn
        people_search_scope = ldap.SCOPE_SUBTREE
        people_filter = 'cn=' + username
        is_valid_user = con.search_s(people_search_base, people_search_scope, people_filter)
        if is_valid_user.__len__() == 1:
            return make_response(jsonify({'success': True, 'message': "USER_EXIST"}), 200)
        else:
            return make_response(jsonify({'success': False, 'message': "UNKNOWN_USER"}), 200)

    except ldap.SERVER_DOWN:
        return make_response(jsonify({'success': False, 'message': 'LDAP_SERVER_DOWN'}), 500)