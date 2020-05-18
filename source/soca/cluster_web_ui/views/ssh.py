import logging
from decorators import login_required
import config
import subprocess
import os
from flask import send_file, render_template, Blueprint, session, redirect, request
import read_secretmanager
import os
logger = logging.getLogger(__name__)

ssh = Blueprint('ssh', __name__, template_folder='templates')

@ssh.route('/ssh', methods=['GET'])
@login_required
def home():
    scheduler_ip = read_secretmanager.get_soca_configuration()['SchedulerPublicIP']
    return render_template('ssh.html', user=session["user"], scheduler_ip=scheduler_ip)


@ssh.route('/ssh/get_key', methods=['GET'])
@login_required
def get_key():
    type = request.args.get("type", None)
    if type is None or type not in ["pem", "ppk"]:
        return redirect("/ssh")

    user = session['user']
    user_private_key_path = config.Config.USER_HOME + "/" + user + "/.ssh/id_rsa"
    if type == "pem":

        return send_file(user_private_key_path,
                         as_attachment=True,
                         attachment_filename=user + '_soca_privatekey.pem')
    else:
        generate_ppk = ['/apps/soca/' + read_secretmanager.get_soca_configuration()['ClusterId'] + '/cluster_web_ui/unix/puttygen', user_private_key_path,
                        '-o',
                        config.Config.SSH_PRIVATE_KEY_LOCATION + '/' + user + '_soca_privatekey.ppk']
        subprocess.call(generate_ppk)
        os.chmod(config.Config.SSH_PRIVATE_KEY_LOCATION + '/' + user + '_soca_privatekey.ppk', 0o700)
        return send_file(config.Config.SSH_PRIVATE_KEY_LOCATION + '/' + user + '_soca_privatekey.ppk',
                         as_attachment=True,
                         attachment_filename=user + '_soca_privatekey.ppk')




