import logging.config

from api.v1.ldap.group import Group
from api.v1.ldap.sudo import Sudo
from api.v1.ldap.user import User
from config import app_config
from flask import Flask, request
from flask_restful import Api
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from models import db

app = Flask(__name__)


api_errors = {
    'UserAlreadyExistsError': {
        'message': "A user with that username already exists.",
        'status': 444,
    },
    'ResourceDoesNotExist': {
        'message': "A resource with that ID no longer exists.",
        'status': 410,
        'extra': "Any extra information you want.",
    },
}
api = Api(app, errors=api_errors)
# Manage CSRF
#csrf = CSRFProtect(app)
#csrf.exempt("views.submit_job.generate_qsub")
#csrf.exempt("api.v1.users.create_api_key.main")
#csrf.exempt("api.v1.users.invalidate_api_key.main")
#csrf.exempt("api.v1.ldap.group.group")


# Register routes
app.config.from_object(app_config)
api.add_resource(Group, '/')
api.add_resource(Sudo, '/sudo')
api.add_resource(User, '/user')

'''
app.register_blueprint(web_job_submission)
app.register_blueprint(index)
app.register_blueprint(submit_job)
app.register_blueprint(create_api_key)
app.register_blueprint(list_api_key)
app.register_blueprint(invalidate_api_key)
app.register_blueprint(check_user)
app.register_blueprint(check_sudo)
app.register_blueprint(authenticate)
app.register_blueprint(list_users)
'''

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

if __name__ == '__main__':
    app.run()
