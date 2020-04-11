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
    SECRET_KEY = os.environ["FLASK_SECRET_KEY"]
    API_ROOT_KEY = secrets.token_hex(32)
    SOCA_DATA_SHARING_SYMMETRIC_KEY = Fernet.generate_key()

    # List of file admins can edit via web ui
    CONFIGURATION_FILE_CUSTOMIZABLE_VIA_WEB = {1: "/Users/mcrozes/Desktop/test_file_1.yml",
                                               2: "/Users/mcrozes/Desktop/test_file_2",
                                               3: "/Users/mcrozes/Desktop/test_file_3",
                                               4: "/apps/soca/soca-" + os.environ["SOCA_CONFIGURATION"] + '/cluster_manager/settings/queue_mapping.yml',
                                               5: "/apps/soca/soca-" + os.environ["SOCA_CONFIGURATION"] + '/cluster_manager/settings/licenses_mapping.yml',
                                               6: "/apps/soca/soca-" + os.environ["SOCA_CONFIGURATION"] + '/cluster_manager/settings/project_cost_manager.txt',
                                               }



    # GUNICORN SETTINGS
    FLASK_HOST = "127.0.0.1"
    FLASK_PROTOCOL = "http://"
    FLASK_PORT = "5000"
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
    LDAP_HOST = "18.232.5.215"
    LDAP_BASE_DN = "dc=soca,dc=local"
    LDAP_ADMIN_PASSWORD_FILE = "/root/OpenLdapAdminPassword.txt"
    LDAP_ADMIN_USERNAME_FILE = "/root/OpenLdapAdminUsername.txt"
    USER_HOME = "/data/home"

    #ROOT_DN = 'CN='+open(LDAP_ADMIN_USERNAME_FILE, 'r').read().rstrip().lstrip()+',' + LDAP_BASE_DN
    #ROOT_PW = open(LDAP_ADMIN_PASSWORD_FILE, 'r').read().rstrip().lstrip()
    ROOT_DN = 'CN=admin,' + LDAP_BASE_DN
    ROOT_PW = '6trXQVL4'

    # PBS
    PBS_QSTAT = "/opt/pbs/bin/qstat"
    PBS_QDEL = "/opt/pbs/bin/qdel"
    # SSH
    SSH_PRIVATE_KEY_LOCATION = "tmp/ssh"


app_config = Config()