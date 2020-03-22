import datetime

from decorators import private_api
from flask import Blueprint, jsonify, make_response, request
from models import db, ApiKeys

invalidate_api_key = Blueprint('invalidate_api_key', __name__)


@invalidate_api_key.route("/api/users/invalidate_api_key",  methods=["POST"])
@private_api
def main():
    token = request.form.get("token", False)
    username = request.form.get("username", False)
    if token is False and username is not False:
        return make_response(jsonify({"success": False, "message": "TOKEN_OR_USERNAME_CANT_BE_FALSE"}), 200)
    else:
        try:
            check_existing_key = ApiKeys.query.filter_by(token=token, username=username).first()
            if check_existing_key:
                check_existing_key.is_active = False
                check_existing_key.deactivated_on = datetime.datetime.utcnow()
                db.session.commit()
                return make_response(jsonify({"success": True, "message": check_existing_key.as_dict()}), 200)
            else:
                return make_response(jsonify({"success": False, "message": "TOKEN_NOT_FOUND: " + str(token)}), 200)

        except Exception as err:
            return make_response(jsonify({"success": False, "message": "UNKNOWN_ERROR: " + str(err)}), 200)
