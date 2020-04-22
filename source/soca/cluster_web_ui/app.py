import logging.config
import subprocess
from flask import Flask, request, jsonify, render_template
from flask_restful import Api
from flask_session import Session
from flask_restful_swagger import swagger
from flask_sqlalchemy import SQLAlchemy
from api.v1.ldap.sudo import Sudo
from api.v1.ldap.ids import Ids
from api.v1.ldap.user import User
from api.v1.ldap.users import Users
from api.v1.user.reset_password import Reset
from api.v1.user.api_key import ApiKey
from api.v1.ldap.group import Group
from api.v1.ldap.groups import Groups
from api.v1.ldap.authenticate import Authenticate
from api.v1.system.files import Files
from views.index import index
from views.ssh import ssh
from views.sftp import sftp
from views.my_api_key import my_api_key
from views.admin.users import admin_users
from views.admin.queues import admin_queues
from views.admin.groups import admin_groups
from views.admin.applications import admin_applications


from views.my_account import my_account
from views.my_files import my_files
from views.submit_job import submit_job

from flask_wtf.csrf import CSRFProtect
from config import app_config
from models import db
from flask_swagger import swagger
from swagger_ui import api_doc
import config
app = Flask(__name__)
csrf = CSRFProtect(app)
csrf.exempt("api")

# Register routes
app.config.from_object(app_config)

# Add API
api = Api(app, decorators=[csrf.exempt])

# LDAP
api.add_resource(Sudo, '/api/ldap/sudo')
api.add_resource(Authenticate, '/api/ldap/authenticate')
api.add_resource(Ids, '/api/ldap/ids')
api.add_resource(User, '/api/ldap/user')
api.add_resource(Users, '/api/ldap/users')
api.add_resource(Group, '/api/ldap/group')
api.add_resource(Groups, '/api/ldap/groups')
# Users
api.add_resource(ApiKey, '/api/user/api_key')
api.add_resource(Reset, '/api/user/reset_password')
# System
api.add_resource(Files, '/api/system/files')


# Register views
app.register_blueprint(index)
app.register_blueprint(my_api_key)
app.register_blueprint(my_account)
app.register_blueprint(admin_users)
app.register_blueprint(admin_queues)
app.register_blueprint(admin_groups)
app.register_blueprint(admin_applications)
app.register_blueprint(my_files)
app.register_blueprint(submit_job)
app.register_blueprint(ssh)
app.register_blueprint(sftp)




# Custom Jinja2 filters

@app.template_filter('folder_name_truncate')
def folder_name_truncate(folder_name):
    # This make sure folders with long name on /my_files are displayed correctly
    if folder_name.__len__() < 20:
        return folder_name
    else:
        split_number = [20, 40, 60]
        for number in split_number:
            try:
                if folder_name[number] != "-" and folder_name[number-1] != "-" and folder_name[number+1] != "-":
                    folder_name = folder_name[:number] + '-' + folder_name[number:]
            except IndexError:
                break
        return folder_name
app.jinja_env.filters['folder_name_truncate'] = folder_name_truncate

@app.route("/api/spec.json")
def spec():
    swag = swagger(app)
    swag['info']['version'] = "1.0"
    swag['info']['title'] = "SOCA Web API"
    swag['info']['description'] = "<h3>Documentation for your Scale-Out Computing on AWS (SOCA) API</h3><hr>" \
                                  "<li>User and Admin Documentation: https://awslabs.github.io/scale-out-computing-on-aws/</li>" \
                                  "<li>CodeBase: https://github.com/awslabs/scale-out-computing-on-aws</li>"
    return jsonify(swag)


# Manage logger
dict_config = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] [%(levelname)s] [%(module)s] [%(message)s]',
        }
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': "soca_api.log",
            'when': "midnight",
            'interval': 1,
            'backupCount': 15
        },
    },
    'loggers': {
        'api_log': {
            'handlers': ["default"],
            'level': 'DEBUG',
        },
    }
}

logger = logging.getLogger("api_log")
logging.config.dictConfig(dict_config)
app.logger.addHandler(logger)

with app.app_context():
    db.init_app(app)
    db.create_all()
    app_session = Session(app)
    app_session.app.session_interface.db.create_all()
    app.config["SESSION_SQLALCHEMY"] = SQLAlchemy(app)
    #app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
    api_doc(app, config_url=config.Config.FLASK_ENDPOINT + "/api/spec.json", url_prefix="/api/doc", title="SOCA API Documentation")

if __name__ == '__main__':
    app.run()


