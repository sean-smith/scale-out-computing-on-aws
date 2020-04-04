import hashlib
import os
from base64 import b64encode as encode
from email.utils import parseaddr
import config
import ldap
from flask_restful import Resource, reqparse
from requests import get
import json
import logging
from decorators import private_api, admin_api
import re
from flask import session
import ldap.modlist as modlist
from datetime import datetime
logger = logging.getLogger("soca_api")


class Group(Resource):
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
                group_name = group[1]['cn'][0].decode('utf-8')
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

    @admin_api
    def post(self):
        """
        Create a new LDAP user
        ---
        tags:
          - User Management
        parameters:
          - in: body
            name: body
            schema:
              id: NewUser
              required:
                - user
                - password
                - sudoers
                - email
              optional:
                - uid
                - gid
              properties:
                user:
                  type: string
                  description: user you want to create
                password:
                  type: string
                  description: Password for the new user
                sudoers:
                  type: boolean
                  description: True (give user SUDO permissions) or False
                email:
                  type: string
                  description: Email address associated to the user
                uid:
                  type: integer
                  description: Linux UID to be associated to the user
                gid:
                  type: integer
                  description: Linux GID to be associated to user's group
        responses:
          200:
            description: User created
          203:
            description: User already exist
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument('user', type=str, location='form')
        parser.add_argument('password', type=str, location='form')
        parser.add_argument('sudoers', type=bool, location='form')
        parser.add_argument('email', type=str, location='form')
        parser.add_argument('uid', type=int, location='form')
        parser.add_argument('gid', type=int, location='form')
        args = parser.parse_args()
        user = args["user"]
        password = args["password"]
        sudoers = args["sudoers"]
        email = args["email"]
        uid = args["uid"]
        gid = args["gid"]
        if uid is None or gid is None:
            get_id = get(config.Config.FLASK_ENDPOINT + '/api/ldap/ids', verify=False)
            if get_id.status_code == 200:
                current_ldap_ids = (json.loads(get_id.text))
            else:
                logger.error("/api/ldap/ids returned error : " + str(get_id.__dict__))
                return {"success": False, "message": "/api/ldap/ids returned error: " +str(get_id.__dict__)}, 500

        if user is None or password is None or sudoers is None or email is None:
            return {"success": False,
                    "message": "user (str), password (str), sudoers (bool) and email (str) parameters are required"},  400

        # Note: parseaddr adheres to rfc5322 , which means user@domain is a correct address.
        # You do not necessarily need to add a tld at the end
        if "@" not in parseaddr(email)[1]:
            return {"success": False, "message": "Email address seems to be invalid."}, 400

        if uid is None:
            uid = current_ldap_ids["message"]['next_uid']
        else:
            if uid in current_ldap_ids["message"]['used_uid']:
                return {"success": False, "message": "UID already in use."}, 203

        if gid is None:
            gid = current_ldap_ids["message"]['next_gid']
        else:
            if gid in current_ldap_ids["message"]['used_gid']:
                return {"success": False, "message": "GID already in use."}, 203

        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down."}, 500

        dn_user = "uid=" + user + ",ou=people," + config.Config.LDAP_BASE_DN
        enc_passwd = bytes(password, 'utf-8')
        salt = os.urandom(16)
        sha = hashlib.sha1(enc_passwd)
        sha.update(salt)
        digest = sha.digest()
        b64_envelop = encode(digest + salt)
        passwd = '{{SSHA}}{}'.format(b64_envelop.decode('utf-8'))
        attrs = [
                ('objectClass', ['top'.encode('utf-8'),
                                 'person'.encode('utf-8'),
                                 'posixAccount'.encode('utf-8'),
                                 'shadowAccount'.encode('utf-8'),
                                 'inetOrgPerson'.encode('utf-8'),
                                 'organizationalPerson'.encode('utf-8')]),
                ('uid', [str(user).encode('utf-8')]),
                ('uidNumber', [str(uid).encode('utf-8')]),
                ('gidNumber', [str(gid).encode('utf-8')]),
                ('mail', [email.encode('utf-8')]),
                ('cn', [str(user).encode('utf-8')]),
                ('sn', [str(user).encode('utf-8')]),
                ('loginShell', ['/bin/bash'.encode('utf-8')]),
                ('homeDirectory', (config.Config.USER_HOME + '/' + str(user)).encode('utf-8')),
                ('userPassword', [passwd.encode('utf-8')])
            ]

        try:
            conn.simple_bind_s(config.Config.ROOT_DN, config.Config.ROOT_PW)
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401

        try:
            conn.add_s(dn_user, attrs)
            return {"success": True, "message": "Added user."}, 200

        except ldap.ALREADY_EXISTS:
            return {"success": False, "message": "User already exist"}, 203

        except Exception as err:
            return {"success": False, "message": "Uknown error" + str(err)}, 500

    @admin_api
    def delete(self):
        """
        Delete a LDAP user ($HOME is preserved on EFS)
        ---
        tags:
          - User Management
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
        Change LDAP attribute for a user. Supported attributes: ["userPassword"]. This is a generic API for @admin_only. Users hwo wants to change their OWN password muse use /api/user/reset_password endpoint
        ---
        tags:
          - User Management
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
              id: LDAPModify
              required:
                - user
                - attribute
                - value
              properties:
                user:
                  type: string
                  description: user of the SOCA user
                attribute:
                  type: string
                  description: Attribute to change
                value:
                  type: string
                  description: New attribute value

        responses:
          200:
            description: Pair of user/token is valid
          203:
            description: Invalid user/token pair
          400:
            description: Malformed client input
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
            return {"success": True, "message": "User do not belong to the group"}, 203
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401
        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 401
