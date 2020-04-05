import config
import ldap
from flask_restful import Resource, reqparse
from requests import get
import logging
from decorators import private_api, admin_api
import re
logger = logging.getLogger("soca_api")


class Group(Resource):
    @admin_api
    def get(self):
        """
        Retrieve information for a specific group
        ---
        tags:
          - Group Management
        parameters:
          - in: body
            name: body
            schema:
            id: Group
            required:
              - group
            properties:
              group:
                type: string
                description: user of the SOCA user

        responses:
          200:
            description: Return user information
          203:
            description: Unknown user
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument('group', type=str, location='args')
        args = parser.parse_args()
        group = args["group"]
        if group is None:
            return {"success": False,
                    "message": "group (str) parameter is required"}, 400

        group_search_base = "ou=Group," + config.Config.LDAP_BASE_DN
        group_search_scope = ldap.SCOPE_SUBTREE
        group_filter = 'cn=' + group
        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
            groups = conn.search_s(group_search_base, group_search_scope, group_filter, ["cn", "memberUid"])
            if groups.__len__() == 0:
                return {"success": False,
                        "message": "Group does not exist"}, 203
            for group in groups:
                group_base = group[0]
                members = []
                if "memberUid" in group[1].keys():
                    for member in group[1]["memberUid"]:
                        user = re.match("uid=(\w+),", member.decode("utf-8"))
                        if user:
                            members.append(user.group(1))
                        else:
                            return {"success": False, "message": "Unable to retrieve memberUid for this group"}, 500

            return {"success": True, "message": {"group_dn": group_base, "members": members}}


        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    #@admin_api
    def post(self):
        """
        Create a new LDAP group
        ---
        tags:
          - Group Management
        parameters:
          - in: body
            name: body
            schema:
              id: Group
              required:
                - group
              optional:
                - gid
                - users
              properties:
                group:
                  type: string
                  description: Name of the group
                gid:
                  type: integer
                  description: Linux GID to be associated to the group
                users:
                  type: list
                  description: List of user(s) to add to the group


        responses:
          200:
            description: Group created
          203:
            description: Group already exist
          204:
            description: User does not exist and can't be added to the group
          400:
            description: Malformed client input
          500:
            description: Backend issue
        """
        parser = reqparse.RequestParser()
        parser.add_argument('group', type=str, location='form')
        parser.add_argument('gid', type=int, location='form')
        parser.add_argument('users', type=str, location='form')
        args = parser.parse_args()
        group = ''.join(x for x in args["group"] if x.isalpha() or x.isdigit()) # Sanitize Input
        gid = args["gid"]
        users = args["users"]
        get_gid = get(config.Config.FLASK_ENDPOINT + '/api/ldap/ids',
                      headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                      verify=False)
        if get_gid.status_code == 200:
            current_ldap_gids = get_gid.json()
        else:
            return {"success": False, "message": "Unable to retrieve GID: " +str(get_gid._content)}, 500

        if gid is None:
            group_id = current_ldap_gids["message"]["proposed_gid"]
        else:
            if gid in current_ldap_gids["message"]["gid_in_use"]:
                return {"success": False, "message": "GID already in use."}, 203
            group_id = gid

        if group is None:
            return {"success": False,
                    "message": "group (str) parameter is required"},  400

        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down."}, 500

        group_members = []
        if users is not None:
            if not isinstance(users, list):
                return {"success": False,
                        "message": "users must be a valid list"}, 400

            get_all_users = get(config.Config.FLASK_ENDPOINT + "/api/ldap/users",
                                headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY})

            if get_all_users.status_code == 200:
                all_users = get_all_users.json()["message"]

            for member in users:
                if member not in all_users.keys():
                    return {"success": False,
                            "message": "User (" + member +") does not exist."}, 204
                else:
                    group_members.append(member)

        #
        group_dn = "cn=" + group + ",ou=Group," + config.Config.LDAP_BASE_DN
        attrs = [
            ('objectClass', ['top'.encode('utf-8'),
                             'posixGroup'.encode('utf-8')]),
            ('gidNumber', [str(group_id).encode('utf-8')]),
            ('cn', [str(group).encode('utf-8')])

        ]

        try:
            conn.simple_bind_s(config.Config.ROOT_DN, config.Config.ROOT_PW)
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401

        try:
            conn.add_s(group_dn, attrs)
            return {"success": True, "message": "Group created successfully"}, 200

        except ldap.ALREADY_EXISTS:
            return {"success": False, "message": "Group already exist"}, 203

        except Exception as err:
            return {"success": False, "message": "Unknown error when trying to create a group: " + str(err)}, 500

    @admin_api
    def delete(self):
        """
        Delete a LDAP group
        ---
        tags:
          - Group Management
        parameters:
          - in: body
            name: body
            schema:
              id: User
              required:
                - user
              properties:
                user:
                  type: string
                  description: user of the SOCA user

        responses:
          200:
            description: Deleted user
          203:
            description: Unknown user
          400:
            description: Malformed client input
                """
        parser = reqparse.RequestParser()
        parser.add_argument('user', type=str, location='form')
        args = parser.parse_args()
        user = args["user"]
        if user is None:
            return {"success": False,
                    "message": "user (str) parameter is required"}, 400
        ldap_base = config.Config.LDAP_BASE_DN
        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down."}, 500

        try:
            conn.simple_bind_s(config.Config.ROOT_DN, config.Config.ROOT_PW)
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401

        entries_to_delete = ["uid=" + user + ",ou=People," + ldap_base,
                             "cn=" + user + ",ou=Group," + ldap_base,
                             "cn=" + user + ",ou=Sudoers," + ldap_base]

        #print(datetime.now().strftime("%s"))
        #today = datetime.datetime.utcnow().strftime("%s")
        #print(today)
        #run_command('mv /data/home/' + user + ' /data/home/' + user + '_' + str(today))
        for entry in entries_to_delete:
            try:
                conn.delete_s(entry)
            except ldap.NO_SUCH_OBJECT:
                if entry == "uid=" + user + ",ou=People," + ldap_base:
                    return {"success": False, "message": "Unknown user"}, 203
                else:
                    pass
            except Exception as err:
                return {"success": False, "message": "Unknown error: " + str(err)}, 500

        return {"success": True, "message": "Deleted user."}, 200


    #@admin_api
    def put(self):
        """
        Add/Remove user to/from a LDAP group
        ---
        tags:
          - Group Management
        securityDefinitions:
          api_key:
            type: apiKey
            name: x-api-key
            in: header
        security:
          - api_key: []
        parameters:
          - in: body
            name: body
            schema:
              id: d
              required:
                - user
                - attribute
                - value
              properties:
                group:
                  type: string
                  description: user of the SOCA user
                user:
                  type: string
                  description: Attribute to change
                action:
                  type: string
                  description: New attribute value

        responses:
          200:
            description: LDAP attribute modified successfully
          203:
            description: User already belongs to the group
          204:
            description: User does not belong to the group
          400:
            description: Malformed client input
          401:
            description: Unable to bind LDAP (invalid credentials)
          500:
            description: Backend issue (see trace)
        """
        parser = reqparse.RequestParser()
        parser.add_argument('group', type=str, location='form')
        parser.add_argument('user', type=str, location='form')
        parser.add_argument('action', type=str, location='form')
        args = parser.parse_args()
        group = args["group"]
        user = args["user"]
        action = args["action"]
        ALLOWED_ACTIONS = ["add", "remove"]
        if user is None or group is None or action is None:
            return {"success": False,
                    "message": "user (str), group (str) and action (str) parameters are required"}, 400

        if action not in ALLOWED_ACTIONS:
            return {"success": False,
                    "message": "attribute is not supported"}, 400

        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down."}, 500

        user_dn = "uid=" + user + ",ou=People," + config.Config.LDAP_BASE_DN
        group_dn = "cn=" + group + ",ou=Group," + config.Config.LDAP_BASE_DN

        get_all_users = get(config.Config.FLASK_ENDPOINT + "/api/ldap/users",
                            headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY})

        if get_all_users.status_code == 200:
            all_users = get_all_users.json()["message"]
            if user_dn not in all_users.values():
                return {"success": False,
                        "message": "User do not exist."}, 203
        else:
            return {"success": False,
                    "message": "Unable to retrieve list of LDAP users. " + str(get_all_users._content)}, 500

        if action == "add":
            mod_attrs = [(ldap.MOD_ADD, 'memberUid', [user_dn.encode("utf-8")])]
        else:
            mod_attrs = [(ldap.MOD_DELETE, 'memberUid', [user_dn.encode("utf-8")])]

        try:
            conn.simple_bind_s(config.Config.ROOT_DN, config.Config.ROOT_PW)
            conn.modify_s(group_dn, mod_attrs)
            return {"success": True, "message": "LDAP attribute has been modified correctly"}, 200
        except ldap.TYPE_OR_VALUE_EXISTS:
            return {"success": True, "message": "User already part of the group"}, 203
        except ldap.NO_SUCH_ATTRIBUTE:
            return {"success": True, "message": "User do not belong to the group"}, 204
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401
        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 401
