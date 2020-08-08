import config
import ldap
from flask_restful import Resource, reqparse
import logging
from decorators import admin_api, restricted_api, private_api
from flask import Response
import base64
import ast
import errors
from models import db, DCVSessions, WindowsDCVSessions

logger = logging.getLogger("soca_api")


class DcvAuthenticator(Resource):
    def post(self):
        """
        Authenticate DCV sessions
        ---
        tags:
          - System
        responses:
          200:
            description: Pair of user/token is valid
          401:
            description: Invalid user/token pair
        """
        parser = reqparse.RequestParser()
        parser.add_argument('sessionId', type=str, location='form')
        parser.add_argument('authenticationToken', type=str, location='form')
        parser.add_argument('clientAddress', type=str, location='form')
        args = parser.parse_args()
        session_id = args["sessionId"]
        authentication_token = args['authenticationToken']
        client_address = args["clientAddress"]
        file1 = open("myfile.txt", "w")
        file1.write(str(args))
        file1.close()
        error = False
        user = False
        required_params = ["system", "session_user", "session_token", "session_instance_id"]
        session_info = {}

        if session_id is None or authentication_token is None:
            return errors.all_errors('CLIENT_MISSING_PARAMETER', "sessionId (str) and authenticationToken (str) are required.")

        try:
            decoded_token = base64.b64decode(authentication_token)
            decoded_token = ast.literal_eval(decoded_token.decode("utf-8"))
        except Exception as err:
            logger.error("Unable to b64decode DCV authentication token {} due to {}".format(authentication_token, err))
            error = True

        if error is False:
            for param in required_params:
                if param not in decoded_token.keys():
                    logger.error("Unable to find {} in {}".format(decoded_token, decoded_token))
                    error = True
                else:
                    session_info[param] = decoded_token[param]
        if error is False:
            if session_info["system"].lower() == "windows":
                validate_session = WindowsDCVSessions.query.filter_by(user=session_info["session_user"],
                                                                      session_token=session_info["session_token"],
                                                                      session_instance_id=session_info["session_instance_id"],
                                                                      is_active=True).first()

            else:
                validate_session = DCVSessions.query.filter_by(user=session_info["session_user"],
                                                               session_token=session_info["session_token"],
                                                               session_instance_id=session_id["session_instance_id"],
                                                               is_active=True).first()
            if validate_session:
                if session_info["system"].lower() == "windows":
                    user = "Administrator"  # will need to be changed when we support AD authentication
                else:
                    user = session_info["user"]
            else:
                logger.error("Unable to authenticate DCV session for {}".format(decoded_token))
                error = True

        if error is False and user is not False:
            xml_response = '<auth result="yes"><username>' + user +'</username></auth>'
        else:
            xml_response = '<auth result="no"/>'
        return Response(xml_response, mimetype='text/xml')
