import config
import ldap
from flask import Blueprint, jsonify

list_users = Blueprint('list_users', __name__)


@list_users.route("/api/ldap/list_users",  methods=["GET"])
def main():
    ldap_host = config.Config.LDAP_HOST
    base_dn = config.Config.LDAP_BASE_DN
    all_ldap_users = {}
    user_search_base = "ou=People," + base_dn
    user_search_scope = ldap.SCOPE_SUBTREE
    user_filter = 'uid=*'
    con = ldap.initialize('ldap://{}'.format(ldap_host))
    users = con.search_s(user_search_base, user_search_scope, user_filter)
    for user in users:
        user_base = user[0]
        username = user[1]['uid'][0].decode('utf-8')
        all_ldap_users[username] = user_base

    return jsonify(all_ldap_users)