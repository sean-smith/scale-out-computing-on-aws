import hashlib
import os
from base64 import b64encode as encode

import config
import ldap
from flask_restful import Resource, reqparse


def find_ids():
    used_uid = []
    used_gid = []
    conn = ldap.initialize('ldap://' + config.Config.LDAP_HOST)
    res = conn.search_s(config.Config.LDAP_BASE_DN,
                                     ldap.SCOPE_SUBTREE,
                                     'objectClass=posixAccount',
                                     ['uidNumber', 'gidNumber']
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


class User(Resource):
    def post(self):
        # Create LDAP user
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
        current_ldap_ids = find_ids()

        if username is None or password is None or sudoers is None or email is None:
            return {"success": False,
                    "message": "username (str), password (str), sudoers (bool) and email (str) parameters are required"}

        if email.split("@").__len__() != 2:
            return {"success": False, "message": "Email address seems to be invalid."}
        if uid is None:
            uid = current_ldap_ids['next_uid']
        else:
            if uid in current_ldap_ids['used_uid']:
                return {"success": False, "message": "UID already in use."}

        if gid is None:
            gid = current_ldap_ids['next_gid']
        else:
            if gid in current_ldap_ids['used_gid']:
                return {"success": False, "message": "GID already in use."}

        conn = ldap.initialize('ldap://127.0.0.1')
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
        except Exception as err:
            return {"success": False, "message": str(err)}

        try:
            conn.add_s(dn_user, attrs)

        except ldap.ALREADY_EXISTS:
            return {"success": False, "message": "User already exist"}

        except Exception as err:
            return {"success": False, "message": str(err)}

