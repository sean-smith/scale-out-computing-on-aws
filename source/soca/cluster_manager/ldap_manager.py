import ldap
import argparse
import sys
import hashlib
from base64 import b64encode as encode
import shutil
import os
sys.path.append(os.path.dirname(__file__))
import configuration
import binascii
import uuid
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
import subprocess

def run_command(cmd):
    try:
        command = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = command.communicate()
        return stdout
    except subprocess.CalledProcessError as e:
        exit(1)

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


def create_home(username):
    try:

        key = rsa.generate_private_key(backend=crypto_default_backend(),public_exponent=65537,key_size=2048)
        
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption())
        
        public_key = key.public_key().public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH
        )

        private_key_str = private_key.decode('utf-8')
        public_key_str = public_key.decode('utf-8')
        # Create user directory structure and permissions
        user_path = user_home + '/' + username + '/.ssh'
        run_command('mkdir -p ' + user_path)
        print(private_key_str, file=open(user_path + '/id_rsa', 'w'))
        print(public_key_str, file=open(user_path + '/id_rsa.pub', 'w'))
        print(public_key_str, file=open(user_path + '/authorized_keys', 'w'))
        os.chmod(user_home + '/' + username + '/.ssh', 0o700)
        os.chmod(user_home + '/' + username + '/.ssh/id_rsa', 0o600)
        os.chmod(user_home + '/' + username + '/.ssh/authorized_keys', 0o600)
        shutil.chown(user_home + '/' + username +'/', user=username, group=username)
        shutil.chown(user_home + '/' + username + '/.ssh', user=username, group=username)
        shutil.chown(user_home + '/' + username + '/.ssh/authorized_keys', user=username, group=username)
        shutil.chown(user_home + '/' + username + '/.ssh/id_rsa', user=username, group=username)
        shutil.chown(user_home + '/' + username + '/.ssh/id_rsa.pub', user=username, group=username)
        return True
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return e


def create_group(username, gid_number):
    dn_group = "cn="+username+",ou=group," + ldap_base
    attrs = [
        ('objectClass', ['top'.encode('utf-8'),
                         'posixGroup'.encode('utf-8')]),
        ('gidNumber', [str(gid_number).encode('utf-8')]),
        ('cn', [str(username).encode('utf-8')])
    ]

    try:
        con.add_s(dn_group, attrs)
        return True
    except Exception as e:
        return e


def create_user(username, password, sudoers, email=False, uid=False, gid=False):
    dn_user = "uid="+username+",ou=people," + ldap_base
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
        ('cn', [str(username).encode('utf-8')]),
        ('sn', [str(username).encode('utf-8')]),
        ('loginShell', ['/bin/bash'.encode('utf-8')]),
        ('homeDirectory', (str(user_home)+'/'+str(username)).encode('utf-8')),
        ('userPassword', [passwd.encode('utf-8')])
    ]

    if email is not False:
        attrs.append(('mail', [email.encode('utf-8')]))

    try:
        con.add_s(dn_user, attrs)
        if sudoers is True:
            sudo = add_sudo(username)
            if sudo is True:
                print('Added user as sudoers')
            else:
                print(sudo)
        return True
    except Exception as e:
        return e




def add_sudo(username):
    dn_user = "cn=" + username + ",ou=Sudoers," + ldap_base
    attrs = [
        ('objectClass', ['top'.encode('utf-8'),
                         'sudoRole'.encode('utf-8')]),
        ('sudoHost', ['ALL'.encode('utf-8')]),
        ('sudoUser', [str(username).encode('utf-8')]),
        ('sudoCommand', ['ALL'.encode('utf-8')])
    ]

    try:
        con.add_s(dn_user, attrs)
        return True
    except Exception as e:
        return e


if __name__ == "__main__":
    aligo_configuration = configuration.get_aligo_configuration()
    ldap_base = 'DC=soca,DC=local'
    user_home = '/data/home'
    slappasswd = '/sbin/slappasswd'
    root_dn = 'CN=admin,DC=soca,DC=local'
    root_pw = open('/root/OpenLdapAdminPassword.txt', 'r').read()
    ldap_args = '-ZZ -x -H "ldap://' + aligo_configuration['SchedulerPrivateDnsName'] + '" -D ' + root_dn + ' -y ' + root_pw
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', nargs='?', required=True, help='LDAP username')
    parser.add_argument('-p', '--password', nargs='?', required=True, help='User password')
    parser.add_argument('-e', '--email', nargs='?', help='User email')
    parser.add_argument('--uid', nargs='?', help='Specify custom Uid')
    parser.add_argument('--gid', nargs='?', help='Specific custom Gid')
    parser.add_argument('--admin', action='store_const', const=True, help='If flag is specified, user will be added to sudoers group')
    arg = parser.parse_args()
    con = ldap.initialize('ldap://'+aligo_configuration['SchedulerPrivateDnsName'])
    con.simple_bind_s(root_dn, root_pw)
    ldap_ids = find_ids()
    gid = ldap_ids['next_gid']
    uid = ldap_ids['next_uid']

    if arg.email is not None:
        email = arg.email
    else:
        email = False


    add_user = create_user(str(arg.username), str(arg.password), arg.admin, email, uid, gid)
    add_group = create_group(str(arg.username), gid)
    add_home = create_home(arg.username)

    if add_user is True:
        print('Created User: ' +str(arg.username) + ' id: ' +str(uid))
    else:
        print('Unable to create user:' + add_user)
        sys.exit(1)
    if add_group is True:
        print('Created group')
    else:
        print('Unable to create group:' + add_group)
        sys.exit(1)

    if add_home is True:
        print('Home directory created correctly')
    else:
        print('Unable to create Home structure:' + add_home)
        sys.exit(1)


    con.unbind_s()


