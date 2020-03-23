from flask_restful import Resource, reqparse
from models import ApiKeys


class Sudo(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='args')
        parser.add_argument('token', type=str, location='args')
        args = parser.parse_args()
        if args["username"] is None:
            return {"success": False, "message": "username can not be empty"}
        if args["token"] is None:
            return {"success": False, "message": "token can not be empty"}

        has_sudo_permissions = ApiKeys.query.filter_by(username=args["username"],
                                                       token=args["token"],
                                                       is_active=True,
                                                       has_sudo=True).first()
        if has_sudo_permissions:
            return {"success": True,
                    "message": ""}
        else:
            return {"success": False,
                    "message": "Key does not have sudo permissions."}

