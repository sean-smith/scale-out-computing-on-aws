import config
from cryptography.fernet import Fernet
from flask_restful import Resource, reqparse
from flask import request
import logging
from flask import Response
import base64
import ast
import errors
from models import db, DCVSessions, WindowsDCVSessions

logger = logging.getLogger("api")


def decrypt(encrypted_text):
    try:
        key = config.Config.DCV_TOKEN_SYMMETRIC_KEY
        cipher_suite = Fernet(key)
        decrypted_text = cipher_suite.decrypt(encrypted_text)
        return decrypted_text.decode()
    except Exception as err:
        print(err)
        return False


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
        logger.info("DCV Auth")
        parser = reqparse.RequestParser()
        parser.add_argument('sessionId', type=str, location='form')
        parser.add_argument('authenticationToken', type=str, location='form')
        parser.add_argument('clientAddress', type=str, location='form')
        args = parser.parse_args()
        x_forwarded_for = request.headers.get("X-Forwarded-For", None)
        session_id = args["sessionId"]
        authentication_token = args['authenticationToken']
        client_address = args["clientAddress"].split(":")[0]  # keep only ip, remove port
        error = False
        user = False
        required_params = ["system", "session_user", "session_token", "session_instance_id"]
        session_info = {}
        if session_id is None or authentication_token is None or client_address is None:
            return errors.all_errors('CLIENT_MISSING_PARAMETER', "sessionId (str), clientAddress (str) and authenticationToken (str) are required.")
        try:
            decoded_token = decrypt(base64.b64decode(authentication_token))
            decoded_token = ast.literal_eval(decoded_token)
        except Exception as err:
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
                                                                      session_host_private_ip=client_address,
                                                                      session_token=session_info["session_token"],
                                                                      session_instance_id=session_info["session_instance_id"],
                                                                      is_active=True).first()

            else:
                validate_session = DCVSessions.query.filter_by(user=session_info["session_user"],
                                                               session_host_private_ip=client_address,
                                                               session_token=session_info["session_token"],
                                                               session_instance_id=session_id["session_instance_id"],
                                                               is_active=True).first()
            if validate_session:
                if session_info["system"].lower() == "windows":
                    user = "Administrator"  # will need to be changed when we support AD authentication
                else:
                    user = session_info["user"]
            else:
                logger.error("Unable to authenticate DCV session for {} with args {}".format(decoded_token, args))
                error = True

        if error is False and user is not False:
            xml_response = '<auth result="yes"><username>' + user +'</username></auth>'
            status = 200
        else:
            xml_response = '<auth result="no"/>'
            status = 401
        return Response(xml_response, status=status, mimetype='text/xml')
