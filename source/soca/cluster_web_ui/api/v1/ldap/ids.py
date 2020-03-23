import ldap
from decorators import private_api
from flask_restful import Resource


class Group(Resource):
    @private_api
    def get(self):
        # Return information related to a specific LDAP group

        def find_ids():
            used_uid = []
            used_gid = []
            res = con.search_s(ldap_base,
                               ldap.SCOPE_SUBTREE,
                               'objectClass=posixAccount', ['uidNumber', 'gidNumber']
                               )
            # Any users/group created will start with uid/gid => 5000
            uid = 5000
            gid = 5000
            for a in res:
                uid_temp = int(a[1].get('uidNumber')[0])
                used_uid.append(uid_temp)
                if uid_temp > uid:
                    uid = uid_temp

            for a in res:
                gid_temp = int(a[1].get('gidNumber')[0])
                used_gid.append(gid_temp)
                if gid_temp > gid:
                    gid = gid_temp

            return {'next_uid': int(uid) + 1,
                    'used_uid': used_uid,
                    'next_gid': int(gid) + 1,
                    'used_gid': used_gid}

        return {'action': 'get'}

