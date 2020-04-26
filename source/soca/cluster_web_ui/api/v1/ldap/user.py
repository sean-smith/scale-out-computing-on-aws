import hashlib
import os
from base64 import b64encode as encode
from email.utils import parseaddr
import config
import ldap
from flask_restful import Resource, reqparse
from requests import get, post, put
import json
import logging
from decorators import private_api, admin_api
from flask import session
import shutil
import ldap.modlist as modlist
import datetime
logger = logging.getLogger("soca_api")


class User(Resource):
    @private_api
    def get(self):
        """
        Retrieve information for a specific user
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
            description: Return user information
          203:
            description: Unknown user
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument('user', type=str, location='args')
        args = parser.parse_args()
        user = args["user"]
        if user is None:
            return {"success": False,
                    "message": "user (str) parameter is required"}, 400

        user_filter = 'cn='+user
        user_search_base = "ou=People," + config.Config.LDAP_BASE_DN
        user_search_scope = ldap.SCOPE_SUBTREE
        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
            check_user = conn.search_s(user_search_base, user_search_scope, user_filter)
            if check_user.__len__() == 0:
                return {"success": False, "message": "Unknown user"}, 203
            else:
                return {"success": True, "message": str(check_user)}, 200

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
        user = ''.join(x for x in args["user"] if x.isalpha() or x.isdigit()).lower()  # Sanitize input
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
            uid = current_ldap_ids["message"]['proposed_uid']
        else:
            if uid in current_ldap_ids["message"]['uid_in_use']:
                return {"success": False, "message": "UID already in use."}, 215

        if gid is None:
            gid = current_ldap_ids["message"]['proposed_gid']
        else:
            if gid in current_ldap_ids["message"]['gid_in_use']:
                return {"success": False, "message": "UID already in use."}, 215
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
            return {"success": False, "message": "Unable to bind LDAP. Please verify cn=Admin credentials"}, 401

        try:
            # Create group first to prevent GID issue
            create_user_group = post(config.Config.FLASK_ENDPOINT + "/api/ldap/group",
                                     headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                     data={"group": user, "gid": gid},
                                     verify=False)
            if create_user_group.status_code != 200:
                return {"success": True, "message": "Could not create user group " +str(create_user_group.text)}, 203

            # Assign user
            conn.add_s(dn_user, attrs)

            # Add user to group
            update_group = put(config.Config.FLASK_ENDPOINT + "/api/ldap/group",
                               headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                               data={"group": user,
                                     "user": user,
                                     "action": "add"},
                               verify=False)
            if update_group.status_code != 200:
                return {"success": True, "message": "User/Group created but could not add user to his group"}, 203

            return {"success": True, "message": "Added user"}, 200

        except ldap.ALREADY_EXISTS:
            return {"success": False, "message": "User already exist"}, 203

        except Exception as err:
            return {"success": False, "message": "Unknown error" + str(err)}, 500

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

        today = datetime.datetime.utcnow().strftime("%s")
        user_home = config.Config.USER_HOME + "/" + user
        backup_folder = config.Config.USER_HOME + "/" + user + "_" + today
        shutil.move(user_home, backup_folder)
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


    @admin_api
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
        parser.add_argument('user', type=str, location='form')
        parser.add_argument('attribute', type=str, location='form')
        parser.add_argument('value', type=str, location='form')
        args = parser.parse_args()
        user = args["user"]
        attribute = args["attribute"]
        value = args["value"]
        ALLOWED_ATTRIBUTES = ["userPassword"]
        if user is None or value is None or attribute is None:
            return {"success": False,
                    "message": "user (str), attribute (str) and value (str) parameters are required"}, 400

        if attribute not in ALLOWED_ATTRIBUTES:
            return {"success": False,
                    "message": "attribute is not supported"}, 400

        dn_user = "uid=" + user + ",ou=people," + config.Config.LDAP_BASE_DN
        if attribute == "userPassword":
            enc_passwd = bytes(value, 'utf-8')
            salt = os.urandom(16)
            sha = hashlib.sha1(enc_passwd)
            sha.update(salt)
            digest = sha.digest()
            b64_envelop = encode(digest + salt)
            passwd = '{{SSHA}}{}'.format(b64_envelop.decode('utf-8'))
            new_value = passwd
        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down."}, 500

        try:
            conn.simple_bind_s(config.Config.ROOT_DN, config.Config.ROOT_PW)
            mod_attrs = [(ldap.MOD_REPLACE, "userPassword", new_value.encode('utf-8'))]
            conn.modify_s(dn_user, mod_attrs)
            return {"success": True, "message": "LDAP attribute has been modified correctly."}, 200
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401
        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 401
