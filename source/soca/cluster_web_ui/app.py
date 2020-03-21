import logging
from logging.handlers import RotatingFileHandler

from api.v1.create_api_key import create_api_key
from api.v1.invalidate_api_key import invalidate_api_key
from api.v1.list_api_key import list_api_key
from api.v1.validate_ldap_user import validate_ldap_user
from api.v1.validate_ldap_user_sudoers import validate_ldap_user_sudoers
from config import app_config
from flask import Flask
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
csrf.exempt("api.v1.create_api_key.main")
csrf.exempt("api.v1.invalidate_api_key.main")
csrf.exempt("api.v1.validate_ldap_user.main")


# Register routes
app.config.from_object(app_config)
app.register_blueprint(web_job_submission)
app.register_blueprint(index)
app.register_blueprint(submit_job)
app.register_blueprint(create_api_key)
app.register_blueprint(list_api_key)
app.register_blueprint(invalidate_api_key)
app.register_blueprint(validate_ldap_user)
app.register_blueprint(validate_ldap_user_sudoers)

# Manage logger
logger = logging.getLogger()
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(module)s] [%(message)s]')
log = RotatingFileHandler("soca_web.log", "a", 500000, 5)  # rotate when > 50mb, keep 5 backups
log.setFormatter(formatter)
log.setLevel(logging.DEBUG)
logger.addHandler(log)
logger.setLevel(logging.DEBUG)

with app.test_request_context():
    db.init_app(app)
    csrf.init_app(app)
    db.create_all()
    app_session = Session(app)
    app_session.app.session_interface.db.create_all()
    app.config["SESSION_SQLALCHEMY"] = SQLAlchemy(app)


if __name__ == '__main__':
    app.run()
