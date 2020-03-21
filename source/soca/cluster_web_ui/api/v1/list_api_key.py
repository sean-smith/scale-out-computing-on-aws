from decorators import private_api
from flask import Blueprint, jsonify, make_response
from models import ApiKeys

list_api_key = Blueprint('list_api_key', __name__)


@list_api_key.route("/api/list_api_key/<string:username>",  methods=["GET"])
@private_api
def main(username):
    check_key = ApiKeys.query.filter_by(username=str(username).lower(), is_active=True).first()
    if check_key:
        return make_response(jsonify({"success": True, "message": check_key.as_dict()}), 200)
    else:
        return make_response(jsonify({"success": False, "message": "NO_KEY_FOUND"}), 200)