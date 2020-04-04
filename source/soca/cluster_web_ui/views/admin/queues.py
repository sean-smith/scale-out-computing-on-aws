import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post, delete
from models import ApiKeys
from decorators import login_required

logger = logging.getLogger("api_log")
admin_queues = Blueprint('admin_queues', __name__, template_folder='templates')



@admin_queues.route('/admin/queues', methods=['GET'])
@login_required
def index():
    get_all_users = get(config.Config.FLASK_ENDPOINT + "/api/ldap/users",
                        headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY}).json()

    all_users = get_all_users["message"].keys()
    return render_template('admin_queues.html', username=session['username'], sudoers=session['sudoers'], all_users=all_users)
