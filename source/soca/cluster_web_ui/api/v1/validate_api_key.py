from decorators import private_api
from flask import Blueprint
from models import ApiKeys

validate_api_key = Blueprint('validate_api_key', __name__)


@private_api
def validate_api_key(token=False, username=False):
    if token is False:
        return {"success": False,
                "message": "TOKEN_CANT_BE_FALSE"}
    if username is False:
        return {"success": False,
                "message": "USERNAME_CANT_BE_FALSE"}
    else:
        check_existing_key = ApiKeys.query.filter_by(username=username, token=token, is_active=True).first()
        if check_existing_key:
            return {"success": True,
                    "message": check_existing_key}
        else:
            return {"success": False,
                    "message": "TOKEN_DOES_NOT_EXIST"}

