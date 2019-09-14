from flask import session, redirect, request
from functools import wraps
import generic.parameters as parameters
import ldap


def login_required(f):
    @wraps(f)
    def validate_account():
        #print(request.__dict__)
        if 'username' in session:
            return f()
        else:
           return redirect('/login')
    return validate_account


def validate_ldap(username, password):
    ldap_host = parameters.get_parameter('ldap', 'host')
    base_dn = parameters.get_parameter('ldap', 'base_dn')
    user_dn = 'uid={},ou=people,{}'.format(username, base_dn)
    con = ldap.initialize('ldap://{}'.format(ldap_host))
    try:
        con.bind_s(user_dn, password, ldap.AUTH_SIMPLE)
        session['username'] = username
        return {'success': True,
                'message': ''}

    except ldap.INVALID_CREDENTIALS:
        return {'success': False,
                'message': 'Invalid credentials.'}

    except ldap.SERVER_DOWN:
        return {'success': False,
                'message': 'LDAP server is down.'}

