from decorators import private_api
from flask_restful import Resource

class Groups(Resource):
    @private_api
    def get(self):
        # Return all LDAP groups
        return {'hello': 'world'}

'''
@group.route("/api/ldap/group",  methods=["GET"])
def list_group_membership():
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


@group.route("/api/ldap/group",  methods=["POST"])
def create_group():
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


@group.route("/api/ldap/group",  methods=["DELETE"])
def delete_group():
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


@group.route("/api/ldap/group",  methods=["PUT"])
def update_group_membership():
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
'''