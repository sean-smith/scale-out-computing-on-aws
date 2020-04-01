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
from flask import session
import ldap.modlist as modlist
from datetime import datetime
logger = logging.getLogger("soca_api")


class Reset(Resource):
    @private_api
    def post(self):
        """
        Allow user to change their own password.
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
                - username
                - password
              properties:
                username:
                  type: string
                  description: username of the SOCA user
                password:
                  type: string
                  description: Your new password

        responses:
          200:
            description: Pair of username/token is valid
          203:
            description: Invalid username/token pair
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, location="form")
        parser.add_argument("password", type=str, location="form")
        args = parser.parse_args()
        username = args["username"]
        password = args["password"]
        if username is None or password is None:
            return {"success": False,
                    "message": "username (str) and password (str) parameters are required"}, 400

        dn_user = "uid=" + username + ",ou=people," + config.Config.LDAP_BASE_DN
        enc_passwd = bytes(password, 'utf-8')
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
            return {"success": True, "message": "Password updated correctly."}, 200
        except ldap.INVALID_CREDENTIALS:
            return {"success": False, "message": "Unable to LDAP bind, Please verify cn=Admin credentials"}, 401
        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 401
