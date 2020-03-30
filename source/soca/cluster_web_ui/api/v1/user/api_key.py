from flask_restful import Resource, reqparse
from models import db, ApiKeys
from requests import get
import datetime
import secrets
import config
from decorators import restricted_api, admin_api


class ApiKey(Resource):
    @restricted_api
    def get(self):
        """
        Retrieve API key of the user
        ---
        tags:
          - LDAP Management (Users)
        parameters:
          - in: body
            name: body
            schema:
              id: GETApiKey
              required:
                - username
              properties:
                username:
                  type: string
                  description: username of the SOCA user

        responses:
          200:
            description: Return the token associated to the user
          203:
            description: No token detected
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, location='args')
        args = parser.parse_args()
        username = args["username"]
        if username is None:
            return {"success": False,
                    "message": "username (str) parameter is required"}, 400

        try:
            check_existing_key = ApiKeys.query.filter_by(username=username,
                                                         is_active=True).first()
            if check_existing_key:
                return {"success": True, "message": check_existing_key.token}, 200
            else:
                try:
                    permissions = get(config.Config.FLASK_ENDPOINT + "/api/ldap/sudo",
                                      headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                                      params={"username": username})

                    if permissions.status_code == 200:
                        scope = "sudo"
                    else:
                        scope = "user"
                    api_token = secrets.token_hex(16)
                    new_key = ApiKeys(username=username,
                                      token=api_token,
                                      is_active=True,
                                      scope=scope,
                                      created_on=datetime.datetime.utcnow())
                    db.session.add(new_key)
                    db.session.commit()
                    return {"success": True,
                            "message": api_token}, 200

                except Exception as err:
                    return {"success": False, "message": "Unknown error: " + str(err)}, 500
        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    @admin_api
    def delete(self):
        """
        Delete API key(s) associated to a user
        ---
        tags:
          - LDAP Management (Users)
        parameters:
            - in: body
              name: body
              schema:
                id: DELETEApiKey
                required:
                  - username
                properties:
                    username:
                        type: string
                        description: username of the SOCA user

        responses:
            200:
                description: Key(s) has been deleted successfully.
            203:
                description: Unable to find a token.
            400:
               description: Client error.
        """
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, location='form')
        args = parser.parse_args()
        username = args["username"]
        if username is None:
            return {"success": False, "message": "Username (str) parameters is required"}, 400
        try:
            check_existing_keys = ApiKeys.query.filter_by(username=username, is_active=True).all()
            if check_existing_keys:
                for key in check_existing_keys:
                    key.is_active = False
                    key.deactivated_on = datetime.datetime.utcnow()
                    db.session.commit()
                return {"success": True, "message": "Successfully deactivated"}, 200
            else:
                return {"success": False, "message": "Could not find any active token for user"}, 203

        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

