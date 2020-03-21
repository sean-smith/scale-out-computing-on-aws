from flask import send_file, session


def main(username=False):
    if username is False:
        return {"success": False,
                "message": "USERNAME_CANT_BE_FALSE"}
    else:
        username = session['username']
        user_private_key_path = '/data/home/' + username + '/.ssh/id_rsa'
        return send_file(user_private_key_path,
                         as_attachment=True,
                         attachment_filename=username+'_soca_privatekey.pem')
