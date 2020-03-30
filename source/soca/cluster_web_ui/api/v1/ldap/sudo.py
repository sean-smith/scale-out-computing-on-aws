from flask_restful import Resource, reqparse
import config
import ldap
from flask import jsonify
from decorators import restricted_api, admin_api


class Sudo(Resource):
    @admin_api
    def get(self):
        #
        """
                                 Check if user has sudo permissions on the cluster
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
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='args')
        args = parser.parse_args()
        username = args["username"]
        if args["username"] is None:
            return {"success": False, "message": "username can not be empty"}, 400

        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN

        try:
            con = ldap.initialize('ldap://{}'.format(ldap_host))
            sudoers_search_base = "ou=Sudoers," + base_dn
            sudoers_search_scope = ldap.SCOPE_SUBTREE
            sudoers_filter = 'cn=' + username
            is_sudo = con.search_s(sudoers_search_base, sudoers_search_scope, sudoers_filter)
            if is_sudo.__len__() > 0:
                return {'success': True, 'message': "User has SUDO permissions."}, 200
            else:
                return {'success': False, 'message': "User does not have SUDO permissions."}, 203

        except ldap.SERVER_DOWN:
            return {'success': False, 'message': 'LDAP server is down'}, 500

        except Exception as err:
            return {'success': False, 'message': "Unknown error: " + str(err)}, 500

    @admin_api
    def post(self):
        """
        Add SUDO permission for a user
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
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='form')
        args = parser.parse_args()
        username = args["username"]
        if args["username"] is None:
            return {"success": False, "message": "username can not be empty"}, 400

        # check if user exist
        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN
        try:
            conn = ldap.initialize('ldap://{}'.format(ldap_host))
            dn_user = "cn=" + username + ",ou=Sudoers," + base_dn
            attrs = [
                    ('objectClass', ['top'.encode('utf-8'),
                                     'sudoRole'.encode('utf-8')]),
                    ('sudoHost', ['ALL'.encode('utf-8')]),
                    ('sudoUser', [str(username).encode('utf-8')]),
                    ('sudoCommand', ['ALL'.encode('utf-8')])
                ]

            conn.add_s(dn_user, attrs)
            return {"success": True, "message": "User granted SUDO permission"}, 200

        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server is down"}, 500

        except Exception as err:
            return {"false": True, "message": "Unknown error: " +str(err)}, 500

    # Delete SUDO permission for a user
    def delete(self):
        """
                                                 Delete SUDO permission for a user
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
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='form')
        args = parser.parse_args()
        username = args["username"]
        if args["username"] is None:
            return jsonify({"success": False, "message": "username can not be empty"})
        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN
        con = ldap.initialize('ldap://{}'.format(ldap_host))
        dn_user = "cn=" + username + ",ou=Sudoers," + base_dn
        attrs = [
            ('objectClass', ['top'.encode('utf-8'),
                             'sudoRole'.encode('utf-8')]),
            ('sudoHost', ['ALL'.encode('utf-8')]),
            ('sudoUser', [str(username).encode('utf-8')]),
            ('sudoCommand', ['ALL'.encode('utf-8')])
        ]

        try:
            con.delete_s(dn_user, attrs)
            return jsonify({"success": True, "message": "Removed SUDO permission"})
        except Exception as e:
            return jsonify({"false": True, "message": "Error: " + str(e)})
