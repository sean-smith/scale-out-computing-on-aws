from decorators import private_api
from flask import Blueprint, jsonify, make_response
from models import ApiKeys

check_ldap_user = Blueprint('check_ldap_user', __name__)


@check_ldap_user.route("/api/check_ldap_user/<string:username>",  methods=["GET"])
@private_api
def main(username):
    check_key = ApiKeys.query.filter_by(username=str(username).lower(), is_active=True).first()
    if check_key:
        return make_response(jsonify({"success": True, "message": check_key.as_dict()}), 200)
    else:
        return make_response(jsonify({"success": False, "message": "NO_KEY_FOUND"}), 200)