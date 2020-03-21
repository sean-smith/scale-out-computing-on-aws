import datetime
import secrets

from decorators import private_api
from flask import Blueprint, jsonify, make_response, request
from models import db, ApiKeys

create_api_key = Blueprint('create_api_key', __name__)


@create_api_key.route("/api/create_api_key",  methods=["POST"])
@private_api
def main():
    username = request.form.get("username", False)
    if username is not False:
        check_existing_key = ApiKeys.query.filter_by(username=str(username).lower(), is_active=True).all()
        if check_existing_key != 0:
            for key in check_existing_key:
                key.is_active = False
                db.session.commit()

        try:
            api_token = secrets.token_hex(16)
            new_key = ApiKeys(username=username,
                              token=api_token,
                              is_active=True,
                              created_on=datetime.datetime.utcnow())
            db.session.add(new_key)
            db.session.commit()
            return make_response(jsonify({"success": True, "message": api_token}), 200)
        except Exception as err:
            return make_response(jsonify({"success": False, "message": err}), 304)

    else:
        return make_response(jsonify({"success": False, "message": "INVALID_USERNAME"}), 200)
