import ldap
from decorators import private_api
from flask_restful import Resource
import config
import logging
from random import choice
logger = logging.getLogger("soca_api")


class Ids(Resource):
    def get(self):
        """
        Return available Linux UID/GID numbers
        ---
        tags:
          - LDAP management
        responses:
          200:
            description: Return list of UID/GID
          500:
            description: Unable to contact LDAP server
          501:
           description: Unknown error (followed by trace)
        """

        uid_in_use = []
        gid_in_use = []
        try:
            conn = ldap.initialize("ldap://" + config.Config.LDAP_HOST)
            get_all_ids = conn.search_s(config.Config.LDAP_BASE_DN,
                                        ldap.SCOPE_SUBTREE,
                                        'objectClass=posixAccount',
                                        ['uidNumber', 'gidNumber'])
        except ldap.SERVER_DOWN:
            return {"success": False, "message": "Unable to contact LDAP server"}, 500
        except Exception as err:
            return {"success": False, "message": "Unknown error try to retrieve LDAP ids: " + str(err)}, 501

        UID = 5000
        GID = 5000
        MAX_IDS = 65533  # 65534 is for "nobody" and 65535 is reserved

        print(get_all_ids)

        for uid in get_all_ids:
            uid_temp = int(uid[1].get('uidNumber')[0])
            uid_in_use.append(uid_temp)

        for gid in get_all_ids:
            gid_temp = int(gid[1].get('gidNumber')[0])
            gid_in_use.append(gid_temp)

        return {"success": True,
                "message": {
                    "proposed_uid": choice([i for i in range(UID, MAX_IDS) if i not in uid_in_use]),
                    "proposed_gid": choice([i for i in range(GID, MAX_IDS) if i not in gid_in_use]),
                    "uid_in_use": uid_in_use,
                    "gid_in_use": gid_in_use}
                }, 200


