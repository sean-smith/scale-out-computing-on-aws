from decorators import private_api
from flask_restful import Resource, abort

class Group(Resource):
    @private_api
    def get(self):
        #
        """
                                                                    Return information related to a specific LDAP group
                                                                    ---
                                                                    tags:
                                                                      - LDAP Management (Groups)
                                                                    parameters:
                                                                      - in: body
                                                                        name: body
                                                                        schema:
                                                                          id: GETApiKey
                                                                          required:
                                                                            - username
                                                                            - token
                                                                          properties:
                                                                            username:
                                                                              type: string
                                                                              description: username of the SOCA user
                                                                            token:
                                                                              type: string
                                                                              description: token associated to the user

                                                                    responses:
                                                                      200:
                                                                        description: Pair of username/token is valid
                                                                      203:
                                                                        description: Invalid username/token pair
                                                                      400:
                                                                        description: Malformed client input
                                                                    """
        return {'action': 'get'}


    def post(self):
        # Create a new  LDAP group
        """
                                                                            Create a new LDAP group
                                                                            ---
                                                                            tags:
                                                                              - LDAP Management (Groups)
                                                                            parameters:
                                                                              - in: body
                                                                                name: body
                                                                                schema:
                                                                                  id: GETApiKey
                                                                                  required:
                                                                                    - username
                                                                                    - token
                                                                                  properties:
                                                                                    username:
                                                                                      type: string
                                                                                      description: username of the SOCA user
                                                                                    token:
                                                                                      type: string
                                                                                      description: token associated to the user

                                                                            responses:
                                                                              200:
                                                                                description: Pair of username/token is valid
                                                                              203:
                                                                                description: Invalid username/token pair
                                                                              400:
                                                                                description: Malformed client input
                                                                            """
        return abort(409)


    def delete(self):
        # Delete a LDAP group
        """
                                                                            Delete a LDAP group
                                                                            ---
                                                                            tags:
                                                                              - LDAP Management (Groups)
                                                                            parameters:
                                                                              - in: body
                                                                                name: body
                                                                                schema:
                                                                                  id: GETApiKey
                                                                                  required:
                                                                                    - username
                                                                                    - token
                                                                                  properties:
                                                                                    username:
                                                                                      type: string
                                                                                      description: username of the SOCA user
                                                                                    token:
                                                                                      type: string
                                                                                      description: token associated to the user

                                                                            responses:
                                                                              200:
                                                                                description: Pair of username/token is valid
                                                                              203:
                                                                                description: Invalid username/token pair
                                                                              400:
                                                                                description: Malformed client input
                                                                            """
        return {'action': 'delete'}


    def put(self):
        # add user to group
        # PREVENT ANY ACTION TO OU=Sudoers
        """
                                                                            Modify LDAP group
                                                                            ---
                                                                            tags:
                                                                              - LDAP Management (Groups)
                                                                            parameters:
                                                                              - in: body
                                                                                name: body
                                                                                schema:
                                                                                  id: GETApiKey
                                                                                  required:
                                                                                    - username
                                                                                    - token
                                                                                  properties:
                                                                                    username:
                                                                                      type: string
                                                                                      description: username of the SOCA user
                                                                                    token:
                                                                                      type: string
                                                                                      description: token associated to the user

                                                                            responses:
                                                                              200:
                                                                                description: Pair of username/token is valid
                                                                              203:
                                                                                description: Invalid username/token pair
                                                                              400:
                                                                                description: Malformed client input
                                                                            """
        return {'action': 'PUT'}

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