import logging.config

from api.v1.ldap.check_sudo import check_sudo
from api.v1.ldap.check_user import check_user
from api.v1.users.authenticate import authenticate
from api.v1.users.create_api_key import create_api_key
from api.v1.users.invalidate_api_key import invalidate_api_key
from api.v1.users.list_api_key import list_api_key
from config import app_config
from flask import Flask, request
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from models import db
from views.index import index
from views.submit_job import submit_job
from views.web_job_submission import web_job_submission

app = Flask(__name__)
# Manage CSRF
csrf = CSRFProtect(app)
csrf.exempt("views.submit_job.generate_qsub")
csrf.exempt("api.v1.users.create_api_key.main")
csrf.exempt("api.v1.users.invalidate_api_key.main")
csrf.exempt("api.v1.authenticate_ldap_user.main")


# Register routes
app.config.from_object(app_config)
app.register_blueprint(web_job_submission)
app.register_blueprint(index)
app.register_blueprint(submit_job)
app.register_blueprint(create_api_key)
app.register_blueprint(list_api_key)
app.register_blueprint(invalidate_api_key)
app.register_blueprint(check_user)
app.register_blueprint(check_sudo)
app.register_blueprint(authenticate)

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
    csrf.init_app(app)
    db.create_all()
    app_session = Session(app)
    app_session.app.session_interface.db.create_all()
    app.config["SESSION_SQLALCHEMY"] = SQLAlchemy(app)
    app.config["FLASK_ENDPOINT"] = request.host_url

if __name__ == '__main__':
    app.run()
