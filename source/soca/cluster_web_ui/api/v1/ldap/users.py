import config
import ldap
from flask_restful import Resource
import logging
from decorators import admin_api

logger = logging.getLogger("soca_api")


class Users(Resource):
    @admin_api
    def get(self):
        """
        List all LDAP users
        ---
        tags:
          - LDAP Management (Users)
        responses:
          200:
            description: Pair of username/token is valid
          203:
            description: Invalid username/token pair
          400:
            description: Malformed client input
        """
        # List all LDAP users
        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN
        all_ldap_users = {}
        user_search_base = "ou=People," + base_dn
        user_search_scope = ldap.SCOPE_SUBTREE
        user_filter = 'uid=*'
        try:
            con = ldap.initialize('ldap://{}'.format(ldap_host))
            users = con.search_s(user_search_base, user_search_scope, user_filter)
            for user in users:
                user_base = user[0]
                username = user[1]['uid'][0].decode('utf-8')
                all_ldap_users[username] = user_base

            return {"success": True, "message": all_ldap_users}, 200

        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server seems to be down."}, 500

        except Exception as err:
            return {"success": False, "message": "Unknown Error: " + str(err)}, 500
