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
from datetime import datetime
logger = logging.getLogger("soca_api")


class User(Resource):
    def get(self):
        """
        Retrieve information for a specific user
        ---
        tags:
          - LDAP Management (Users)
        parameters:
          - in: body
            name: body
            schema:
            id: User
            required:
              - username
            properties:
              username:
                type: string
                description: username of the SOCA user

        responses:
          200:
            description: Return user information
          203:
            description: Unknown user
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='args')
        args = parser.parse_args()
        username = args["username"]
        if username is None:
            return {"success": False,
                    "message": "username (str) parameter is required"}, 400

        user_filter = 'cn='+username
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
          - LDAP Management (Users)
        parameters:
          - in: body
            name: body
            schema:
              id: NewUser
              required:
                - username
                - password
                - sudoers
                - email
              optional:
                - uid
                - gid
              properties:
                username:
                  type: string
                  description: Username you want to create
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
        parser.add_argument('username', type=str, location='form')
        parser.add_argument('password', type=str, location='form')
        parser.add_argument('sudoers', type=bool, location='form')
        parser.add_argument('email', type=str, location='form')
        parser.add_argument('uid', type=int, location='form')
        parser.add_argument('gid', type=int, location='form')
        args = parser.parse_args()
        username = args["username"]
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

        if username is None or password is None or sudoers is None or email is None:
            return {"success": False,
                    "message": "username (str), password (str), sudoers (bool) and email (str) parameters are required"},  400

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

        dn_user = "uid=" + username + ",ou=people," + config.Config.LDAP_BASE_DN
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
                ('uid', [str(username).encode('utf-8')]),
                ('uidNumber', [str(uid).encode('utf-8')]),
                ('gidNumber', [str(gid).encode('utf-8')]),
                ('mail', [email.encode('utf-8')]),
                ('cn', [str(username).encode('utf-8')]),
                ('sn', [str(username).encode('utf-8')]),
                ('loginShell', ['/bin/bash'.encode('utf-8')]),
                ('homeDirectory', (config.Config.USER_HOME + '/' + str(username)).encode('utf-8')),
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
          - LDAP Management (Users)
        parameters:
          - in: body
            name: body
            schema:
              id: User
              required:
                - username
              properties:
                username:
                  type: string
                  description: username of the SOCA user

        responses:
          200:
            description: Deleted user
          203:
            description: Unknown user
          400:
            description: Malformed client input
                """
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='form')
        args = parser.parse_args()
        username = args["username"]
        if username is None:
            return {"success": False,
                    "message": "username (str) parameter is required"}, 400
        ldap_base = config.Config.LDAP_BASE_DN
        try:
            conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down."}, 500

        try:
            conn.simple_bind_s(config.Config.ROOT_DN, config.Config.ROOT_PW)
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401

        entries_to_delete = ["uid=" + username + ",ou=People," + ldap_base,
                             "cn=" + username + ",ou=Group," + ldap_base,
                             "cn=" + username + ",ou=Sudoers," + ldap_base]

        #print(datetime.now().strftime("%s"))
        #today = datetime.datetime.utcnow().strftime("%s")
        #print(today)
        #run_command('mv /data/home/' + username + ' /data/home/' + username + '_' + str(today))
        for entry in entries_to_delete:
            try:
                conn.delete_s(entry)
            except ldap.NO_SUCH_OBJECT:
                if entry == "uid=" + username + ",ou=People," + ldap_base:
                    return {"success": False, "message": "Unknown user"}, 203
                else:
                    pass
            except Exception as err:
                return {"success": False, "message": "Unknown error: " + str(err)}, 500

        return {"success": True, "message": "Deleted user."}, 200



    @admin_api
    def put(self):
        """
                                                                     Change user parameters
                                                                    ---
                                                                    tags:
                                                                      - LDAP Management (Users)
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
        pass
