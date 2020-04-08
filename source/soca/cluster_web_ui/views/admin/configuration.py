import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post, delete, put
from models import ApiKeys
from decorators import login_required, admin_only

logger = logging.getLogger("api_log")
configuration = Blueprint('configuration', __name__, template_folder='templates')


@configuration.route('/admin/configuration', methods=['GET'])
def index():
    ALLOWED_FILES_TO_EDIT = {1: "/Users/mcrozes/Desktop/test_file_1",
                             2: "/Users/mcrozes/Desktop/test_file_2"}
    try:
        file_selection = int(request.args.get("fid", 1))
    except ValueError:
        flash("Unknown file", "error")
        return redirect("/admin/configuration")

    if file_selection is None:
        file_to_edit = ALLOWED_FILES_TO_EDIT[1]
    else:
        if file_selection in ALLOWED_FILES_TO_EDIT.keys():
            file_to_edit = ALLOWED_FILES_TO_EDIT[file_selection]
        else:
            flash("Unknown file", "error")
            return redirect("/admin/configuration")

    file_syntax = "yaml"
    text = get(config.Config.FLASK_ENDPOINT + '/api/system/files',
               headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
               params={"file": file_to_edit},
               verify=False
    )
    if text.status_code != 200:
        flash("Unable to read file because of: " + text.json()["message"])
        file_data = []
    else:
        file_data = text.json()["message"]

    return render_template('configuration.html',
                           file_data=file_data,
                           file_syntax=file_syntax, file_to_edit=file_to_edit,
                           user=session["user"],
                           api_key=session["api_key"],
                           config_files=ALLOWED_FILES_TO_EDIT)