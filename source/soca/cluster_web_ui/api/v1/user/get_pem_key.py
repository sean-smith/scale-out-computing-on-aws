from flask import send_file, session

from decorators import private_api
from flask import Blueprint, request

get_pem_key = Blueprint('get_pem_key', __name__)

@get_pem_key.route("/api/users/get_pem_key",  methods=["POST"])
@private_api
def main():
    username = request.form.get("username", False)
    if username is False:
        return {"success": False,
                "message": "USERNAME_CANT_BE_FALSE"}
    else:
        username = session['username']
        user_private_key_path = '/data/home/' + username + '/.ssh/id_rsa'
        return send_file(user_private_key_path,
                         as_attachment=True,
                         attachment_filename=username+'_soca_privatekey.pem')
