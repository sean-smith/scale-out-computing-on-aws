import ldap
from decorators import private_api
from flask_restful import Resource
import config
import logging

logger = logging.getLogger("soca_api")


class Ids(Resource):
    def get(self):
        """
                         Return next available GID/UID as well as list of used IDs
                        ---
                        tags:
                          - LDAP management
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

        used_uid = []
        used_gid = []
        conn = ldap.initialize("ldap://" + config.Config.LDAP_HOST)
        res = conn.search_s(config.Config.LDAP_BASE_DN,
                            ldap.SCOPE_SUBTREE,
                            'objectClass=posixAccount',
                            ['uidNumber', 'gidNumber']
        )
        UID = 5000
        GID = 5000
        for a in res:
            uid_temp = int(a[1].get('uidNumber')[0])
            used_uid.append(uid_temp)
            if uid_temp > UID:
                uid = uid_temp

        for a in res:
            gid_temp = int(a[1].get('gidNumber')[0])
            used_gid.append(gid_temp)
            if gid_temp > GID:
                gid = gid_temp

        return {"success": True,
                "message": {
                    "next_uid": int(uid) + 1,
                    "used_uid": used_uid,
                    "next_gid": int(gid) + 1,
                    "used_gid": used_gid}
                }, 200


