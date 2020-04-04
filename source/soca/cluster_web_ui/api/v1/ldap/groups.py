import config
import ldap
from flask_restful import Resource
import logging
from decorators import admin_api
import re

logger = logging.getLogger("soca_api")


class Groups(Resource):
    #@admin_api
    def get(self):
        """
        List all LDAP groups
        ---
        tags:
          - Group Management
        responses:
          200:
            description: Pair of user/token is valid
          203:
            description: Invalid user/token pair
          400:
            description: Malformed client input
        """
        # List all LDAP users
        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN
        all_ldap_groups = {}
        group_search_base = "ou=Group," + base_dn
        group_search_scope = ldap.SCOPE_SUBTREE
        group_filter = 'cn=*'
        try:
            con = ldap.initialize('ldap://{}'.format(ldap_host))
            groups = con.search_s(group_search_base, group_search_scope, group_filter, ["cn", "memberUid"])
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

                all_ldap_groups[group_name] = {"group_dn": group_base, "members": members}

            return {"success": True, "message": all_ldap_groups}, 200

        except ldap.SERVER_DOWN:
            return {"success": False, "message": "LDAP server seems to be down."}, 500

        except ldap.NO_SUCH_OBJECT:
            return {"success": False, "message": "Group does not exist"}, 203

        except Exception as err:
            return {"success": False, "message": "Unknown Error: " + str(err)}, 500
