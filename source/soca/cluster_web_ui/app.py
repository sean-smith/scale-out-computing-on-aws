from flask import Flask, render_template, session, redirect, request, flash
import datetime
import logging
import collections
import generic.parameters as parameters
from datetime import timedelta
from generic import auth, dcv, qstat
from api.get_ppk_key import get_ppk_key
from api.get_pem_key import get_pem_key
from api.dcv_management import dcv_management
import boto3


app = Flask(__name__)
app.secret_key = '9q50NGgFlwgacIPpB8r-fmFcfVpvQRIIKFS9I-OC8hg'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
app.register_blueprint(get_ppk_key)
app.register_blueprint(get_pem_key)
app.register_blueprint(dcv_management)
client = boto3.client('ec2')

@app.route('/', methods=['GET'])
@auth.login_required
def index():
    username = session['username']
    return render_template('index.html', username=username)


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/logout', methods=['GET'])
def logout():
    if 'username' in session.keys():
        del session['username']

    return redirect('/')


@app.route('/dashboard', methods=['GET'])
def dashboard():
    analytics_dashboard = parameters.get_aligo_configuration()['ESDomainEndpoint']
    return redirect('https://' + analytics_dashboard + '/_plugin/kibana/')


@app.route('/auth', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    password = request.form.get('password')
    if username is not None and password is not None:
        check_auth = auth.validate_ldap(username, password)
        print(check_auth)
        if check_auth['success'] is False:
            flash(check_auth['message'])
            return redirect('/login')
        else:
            return redirect('/')

    else:
        return redirect('/login')

@app.route('/remotedesktop', methods=['GET'])
@auth.login_required
def remotedesktop():
    username = session['username']
    user_sessions = dcv.check_user_session(username)
    max_number_of_sessions = parameters.authorized_dcv_session_count()
    # List of instances not available for DCV. Adjust as needed
    blacklist = ['t1', 't2', 'm1', 'm4', 'c3', 'p2', 'p3', 'r3', 'r4', 'metal', 'nano', 'micro']
    all_instances_available = client._service_model.shape_for('InstanceType').enum
    all_instances = [p for p in all_instances_available if not any(substr in p for substr in blacklist)]
    return render_template('remotedesktop.html', user_sessions=user_sessions, username=username, view='remotedesktop',
                           all_instances=all_instances, max_number_of_sessions=max_number_of_sessions)

@app.route('/ssh', methods=['GET'])
@auth.login_required
def ssh():
    username = session['username']
    scheduler_ip = parameters.get_aligo_configuration()['SchedulerPublicIP']
    app.logger.warning(username + ' checking ssh')
    return render_template('ssh.html', username=username, scheduler_ip=scheduler_ip )


@app.route('/qstat', methods=['GET'])
@auth.login_required
def job_queue():
    username = session['username']
    jobs = qstat.get_user_queue(username)
    return render_template('qstat.html', username=username, jobs=jobs, view='qstat')


@app.route('/howto', methods=['GET'])
@auth.login_required
def howto():
    username = session['username']
    return render_template('howto.html', username=username)


@app.route('/sftp', methods=['GET'])
@auth.login_required
def sftp():
    username = session['username']
    scheduler_ip = parameters.get_aligo_configuration()['SchedulerPublicIP']
    return render_template('sftp.html', scheduler_ip=scheduler_ip, username=username)


@app.route('/ping', methods=['GET'])
def check_alive():
    return 'Check Alive', 200


@app.errorhandler(404)
def page_not_found(e):
    return redirect('/')


if __name__ == '__main__':

    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.run(debug=False, host='0.0.0.0', port=8443, ssl_context='adhoc')
