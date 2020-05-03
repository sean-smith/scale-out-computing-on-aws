import os
from datetime import timedelta
import secrets
from cryptography.fernet import Fernet

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # APP
    DEBUG = False
    TESTING = False
    USE_PERMANENT_SESSION = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_TYPE = "sqlalchemy"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_SQLALCHEMY_TABLE = "flask_sessions"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "db.sqlite")
    SECRET_KEY = os.environ["SOCA_FLASK_SECRET_KEY"]
    API_ROOT_KEY = os.environ["SOCA_FLASK_API_ROOT_KEY"] #secrets.token_hex(32)


    # WEB
    USER_HOME = "/data/home"
    DEFAULT_CACHE_TIME = 500  # 5 minutes
    APPS_LOCATION = "/apps/"
    SOCA_DATA_SHARING_SYMMETRIC_KEY = os.environ["SOCA_FLASK_FERNET_KEY"]

    # UWSGI SETTINGS
    FLASK_HOST = "127.0.0.1"
    FLASK_PROTOCOL = "https://"
    FLASK_PORT = "8443"
    FLASK_ENDPOINT = FLASK_PROTOCOL + FLASK_HOST + ":" + FLASK_PORT

    # COGNITO
    ENABLE_SSO = False
    COGNITO_OAUTH_AUTHORIZE_ENDPOINT = "https://<YOUR_COGNITO_POOL>.auth.<YOUR_REGION>.amazoncognito.com/oauth2/authorize"
    COGNITO_OAUTH_TOKEN_ENDPOINT = "https://<YOUR_COGNITO_POOL>.auth.<YOUR_REGION>.amazoncognito.com/oauth2/token"
    COGNITO_JWS_KEYS_ENDPOINT = "https://cognito-idp.<YOUR_REGION>.amazonaws.com/<YOUR_REGION>_<YOUR_ID>/.well-known/jwks.json"
    COGNITO_APP_SECRET = "<YOUR_APP_SECRET>"
    COGNITO_APP_ID = "<YOUR_APP_ID>"
    COGNITO_ROOT_URL = "<YOUR_WEB_URL>"
    COGNITO_CALLBACK_URL= "<YOUR_CALLBACK_URL>"

    # DCV
    DCV_BIN = "/usr/bin/dcv"
    DCV_AUTH_DIR = "/var/run/dcvsimpleextauth"
    DCV_SIMPLE_AUTH = "/usr/libexec/dcvsimpleextauth.py"
    DCV_SESSION_LOCATION = "tmp/dcv_sessions"
    DCV_MAX_SESSION_ACOUNT = 4

    # LDAP
    LDAP_HOST = "127.0.0.1"
    LDAP_BASE_DN = "dc=soca,dc=local"
    LDAP_ADMIN_PASSWORD_FILE = "/root/OpenLdapAdminPassword.txt"
    LDAP_ADMIN_USERNAME_FILE = "/root/OpenLdapAdminUsername.txt"
    #ROOT_DN = 'CN=' + open(LDAP_ADMIN_USERNAME_FILE, 'r').read().rstrip().lstrip() + ',' + LDAP_BASE_DN
    #ROOT_PW = open(LDAP_ADMIN_PASSWORD_FILE, 'r').read().rstrip().lstrip()

    # PBS
    PBS_QSTAT = "/opt/pbs/bin/qstat"
    PBS_QDEL = "/opt/pbs/bin/qdel"
    PBS_QSUB = "/opt/pbs/bin/qsub"
    PBS_QMGR = "/opt/pbs/bin/qmgr"
    # SSH
    SSH_PRIVATE_KEY_LOCATION = "tmp/ssh"

    # Dev mickael test
    LDAP_HOST = "52.7.198.13"
    ROOT_PW = 'ylS.aCiW'
    OOT_DN = 'CN=admin,dc=soca,dc=local'
    FLASK_HOST = "127.0.0.1"
    FLASK_PROTOCOL = "http://"
    FLASK_PORT = "5000"
    FLASK_ENDPOINT = FLASK_PROTOCOL + FLASK_HOST + ":" + FLASK_PORT
    USER_HOME = "/Users"


app_config = Config()