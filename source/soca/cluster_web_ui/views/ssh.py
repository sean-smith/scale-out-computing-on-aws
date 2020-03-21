import logging

import api.v1.get_pem_key as get_pem_key
from flask import send_file, render_template, Blueprint, session, redirect

logger = logging.getLogger(__name__)

ssh = Blueprint('ssh', __name__, template_folder='templates')

@ssh.route('/ssh', methods=['GET'])
@auth.login_required
def home():
    username = session_info()['username']
    sudoers = session_info()['sudoers']
    scheduler_ip = parameters.get_aligo_configuration()['SchedulerPublicIP']
    app.logger.warning(username + ' checking ssh')
    return render_template('ssh.html', username=username, scheduler_ip=scheduler_ip, sudoers=sudoers)


@ssh.route('/ssh/get_pem_key', methods=['GET'])
@auth.login_required
def f():
    username = session['username']
    get_pem_key.main(username)
    return redirect("/ssh")




@ssh.route('/ssh/get_ppk_key', methods=['GET'])
@auth.login_required
def f():
    username = session['username']
    user_private_key_path = '/data/home/' + username + '/.ssh/id_rsa'
    generate_ppk = ['unix/puttygen', user_private_key_path, '-o', parameters.get_parameter('ssh', 'private_key_location')+'/' + username+'_soca_privatekey.ppk']
    subprocess.call(generate_ppk)
    os.chmod(parameters.get_parameter('ssh', 'private_key_location')+'/'+username+'_soca_privatekey.ppk', 0o700)
    return send_file(parameters.get_parameter('ssh', 'private_key_location')+'/'+username+'_soca_privatekey.ppk',
                     as_attachment=True,
                     attachment_filename=username+'_soca_privatekey.ppk')

