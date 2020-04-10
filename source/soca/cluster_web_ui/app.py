import logging.config
from flask import Flask, request, jsonify
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
from views.my_api_key import my_api_key
from views.admin.users import admin_users
from views.admin.queues import admin_queues
from views.admin.groups import admin_groups
from views.admin.configuration import configuration
from views.my_account import my_account
from views.my_files import my_files

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
app.register_blueprint(configuration)
app.register_blueprint(my_files)


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



#gunicorn_logger = logging.getLogger('gunicorn.error')
#app.logger.handlers.extend(gunicorn_logger.handlers)
#app.logger.setLevel(logging.DEBUG)
#app.logger.debug('this will show in the log')

with app.test_request_context():
    db.init_app(app)
    #csrf.init_app(app)
    db.create_all()
    app_session = Session(app)
    app_session.app.session_interface.db.create_all()
    app.config["SESSION_SQLALCHEMY"] = SQLAlchemy(app)
    app.config["FLASK_ENDPOINT"] = request.host_url
    api_doc(app, config_url=config.Config.FLASK_ENDPOINT + "/api/spec.json", url_prefix="/api/doc", title="SOCA API Documentation")

if __name__ == '__main__':
    app.run()
