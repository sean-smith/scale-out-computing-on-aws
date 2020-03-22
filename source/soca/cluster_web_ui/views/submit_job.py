import base64
import json
import logging

import api.v1.users.validate_api_key as validate_api_key
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
submit_job = Blueprint('submit_job', __name__, template_folder='templates')

@submit_job.route("/submit_job", methods=["POST"])
def generate_qsub():
    token = request.headers.get('X-SOCA-TOKEN', None)
    username = request.headers.get('X-SOCA-USER', None)
    if token is not None and username is not None:
        check_token = validate_api_key.main(token=token, username=username)
        if check_token["success"] is True:
            try:
                request_data = json.loads(request.data)
            except json.decoder.JSONDecodeError as err:
                return jsonify({"success": False,
                                "message": "MALFORMED_JSON"})

            try:
                payload = base64.b64decode(request_data["payload"]).decode("utf-8")
            except UnicodeDecodeError:
                return jsonify({"success": False,
                                "message": "MALFORMED_BASE64_HASH"})



            return jsonify({"success": True,
                            "message":   str(payload)})

        else:
            return jsonify({"success": False,
                    "message": "INVALID_TOKEN"})
    else:
        return jsonify({"success": False,
                        "message": "INVALID_TOKEN_OR_USER"})
