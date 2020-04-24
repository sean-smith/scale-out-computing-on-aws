import logging
import config
from flask import render_template, Blueprint, request, redirect, session, flash
from requests import get, post, delete, put
from models import db, ApplicationProfiles
from decorators import login_required, admin_only
import base64
import datetime
import json
logger = logging.getLogger("api_log")
admin_applications = Blueprint('admin_applications', __name__, template_folder='templates')


@admin_applications.route('/admin/applications', methods=['GET'])
@login_required
@admin_only
def index():
    form_builder = {
        "profile_name": {
            "placeholder": "Name of your application profile",
            "help": "Name or your profile. Choose a friendly naming convention such as 'My Software'",
            "required": True},
        "binary": {
            "placeholder": "Where is your application binary located?",
            "help": """Comma separated list of the binary (or executable) path(s) to use to launch your application. It's usually located within the 'bin' folder of your software. <br>
            We recommend you adding a label using <kbd>=</kbd>
            <hr>
            <h5> Example without label</h5> 
            <div class="row">
                <div class="col-md-6">
                    What you configure: <br> <code>/path/to/bin1</code> 
                    <br>
                </div>
                <div class="col-md-6">
                    What users see: <br> <select class="form-control"><option>/path/to/bin1</option></select> 
                    <br>
                </div>
                <div class="col-md-6">
                    What you configure: <br> <code>/path/to/bin1,/path/to/bin2,/path/to/bin3</code> 
                </div>
                <div class="col-md-6">
                    What users see: <br> <select class="form-control"><option>/path/to/bin1</option><option>/path/to/bin2</option><option>/path/to/bin3</option></select> 
                </div>     
            </div>
            <hr>
            <h5> Example with label</h5> 
            <div class="row">
                <div class="col-md-6">
                    What you configure: <br> <code>/path/to/bin1=Version 2020,/path/to/bin2=Version 2019,/path/to/bin3=Beta</code> 
                </div>
                <div class="col-md-6">
                    What users see: <br> <select class="form-control"><option>Version 2020</option><option>Version 2019</option><option>Beta</option></select> 
                </div>      
            </div>
            
            
            """,
            "required": True},
        "input_parameter": {
            "placeholder": "What is the input parameter of your application?",
            "help": "The parameter to choose when launching a job (usually it's -i, --input, -job ...)",
            "required": False},
        "required_parameters": {
            "placeholder": "What parameters you want your users to configure?",
            "help": """Comma separated list of parameters you want your user to specify. If needed you can specify a label using <kbd>=</kbd>.
            <hr>
            <h5> Example without label</h5> 
            <div class="row">
                <div class="col-md-4">
                    What you configure: <br> <code>-a,-b,--param_name</code> 
                </div>
                <div class="col-md-8">
                    What users see: <br> 
                    <div class="form-group">
                        <div class="input-group mb-2">
                            <div class="input-group-prepend">
                                <div class="input-group-text">-a</div>
                            </div>
                            <input type="text" class="form-control" placeholder="Enter value for -a parameter">
                        </div>
                    </div>
                    <br>
                    <div class="form-group">
                        <div class="input-group mb-2">
                            <div class="input-group-prepend">
                                <div class="input-group-text">-b</div>
                            </div>
                            <input type="text" class="form-control" placeholder="Enter value for -b parameter">
                        </div>
                    </div>
                    <br>
                    <div class="form-group">
                        <div class="input-group mb-2">
                            <div class="input-group-prepend">
                                <div class="input-group-text">--param_name</div>
                            </div>
                            <input type="text" class="form-control" placeholder="Enter value for --param_name parameter">
                        </div>
                    </div>
                </div>
            </div>
            <hr>
            <h5> Example with label</h5> 
            <div class="row">
                <div class="col-md-4">
                    What you configure: <br> <code>-a=Process Count,-b=Model Size,--param_name=Version</code> 
                </div>
                <div class="col-md-8">
                    What users see: <br> 
                    <div class="form-group">
                        <div class="input-group mb-2">
                            <div class="input-group-prepend">
                                <div class="input-group-text">Process Count</div>
                            </div>
                            <input type="text" class="form-control" placeholder="Enter value for Process Count (-a) parameter">
                        </div>
                    </div>
                    <br>
                    <div class="form-group">
                        <div class="input-group mb-2">
                            <div class="input-group-prepend">
                                <div class="input-group-text">Model Size</div>
                            </div>
                            <input type="text" class="form-control" placeholder="Enter value for Model Size (-b) parameter">
                        </div>
                    </div>
                    <br>
                    <div class="form-group">
                        <div class="input-group mb-2">
                            <div class="input-group-prepend">
                                <div class="input-group-text">Version</div>
                            </div>
                            <input type="text" class="form-control" placeholder="Enter value for Version (--param_name) parameter">
                        </div>
                    </div>
                </div>
            </div>
            
            """,
            "required": False},
        "queue_name": {
            "placeholder": "Comma separated list of queues your users can use. Left blank for all",
            "help": """
                Comma separated list of queues you want your user to be able to choose. Left blank to list all queues
                <hr>
                <h5> Example with no queue enforced</h5> 
                <div class="row">
                    <div class="col-md-6">
                        What you configure: <br> Nothing, left the entry blank
                    </div>
                    <div class="col-md-6">
                        What users see: <br> <select class="form-control"><option>queue 1</option><option>...</option><option>queue N</option></select> 
                    </div>
                </div>
                <hr>
                <h5> Example with only 1 queue</h5>
                <div class="row">
                    <div class="col-md-6">
                        What you configure: <br>
                        <code>queue1</code>
                    </div>
                    <div class="col-md-6">          
                        What users see:<br>
                        Nothing. Only one queue is selected so user will be forced to use it
                    </div>
                 </div>
                 <hr>
                 <h5> Example with multiple queues</h5>
                <div class="row">
                    <div class="col-md-6">
                        What you configure: <br>
                        <code>queue1,queue2,queue3</code>
                    </div>
                    <div class="col-md-6">          
                        What users see:<br> <select class="form-control"><option>queue 1</option><option>queue2</option><option>queue3</option></select> 

                    </div>
                 </div>
                """,
        "required": False},
        "instance_type": {
            "placeholder": "Comma separated list of instance type(s) you want your users to choose.",
            "help": """
            Comma separated list of instance type(s) you want your user to be able to choose. If needed you can specify a label using <kbd>=</kbd>.
            <hr>
            <h5> Example without label</h5> 
            <div class="row">
                <div class="col-md-6">
                    What you configure: <br> <code>c5.large,r5.large,m5.large</code> 
                </div>
                <div class="col-md-6">
                    What users see: <br> <select class="form-control"><option>c5.large</option><option>m5.large</option><option>r5.large</option></select> 
                </div>
            </div>
            <hr>
            <h5> Example with label</h5>
            <div class="row">
                <div class="col-md-6">
                    What you configure: <br>
                    <code>c5.large=CPU Optimized,r5.large=High Memory,m5.large=General Purpose</code>
                </div>
                <div class="col-md-6">          
                    What users see:<br>
                    <select class="form-control"><option>CPU Optimized</option><option>High Memory</option><option>General Purpose</option></select> 
                </div>
             </div>
            """,
            "required": True},
        "optional_parameters": {
            "placeholder": "(Optional) List of any additional parameters to append to the solver command",
            "help": "Comma separated list of parameters/commands to be automatically added to the job command on behalf of the users. Users cannot remove/change them.",
            "required": False},
        "scheduler_parameters": {
            "placeholder": "(Optional) List of scheduler parameters you want to apply to the job.",
            "help": "<a target='_blank' href='https://awslabs.github.io/scale-out-computing-on-aws/tutorials/integration-ec2-job-parameters/'>See this link</a> for a list of available parameters. <hr> <h3>Example</h3> If you want to enable 300 GB scratch disk and EFA by default, enter <code>scratch_size=300,efa_support=True</code>",
            "required": False},
        "ld_library_path": {
            "placeholder": "(Optional) Append your $LD_LIBRARY_PATH",
            "help": "If your application require specific library, you can append the location to your system $LD_LIBRARY_PATH",
            "required": False},
        "path": {
            "placeholder": "(Optional) Append your $PATH",
            "help": "If your application require specific path, you can append the location to your system $PATH",
            "required": False},
        "help": {
            "placeholder": "(Optional) Link to your own help/wiki",
            "help": "Specify a link (such as wiki or internal documentation) your users access to learn more about this application.",
            "required": False},
    }

    return render_template('admin_applications.html', user=session['user'],form_builder=form_builder)


@admin_applications.route('/admin/applications/create', methods=['post'])
@login_required
@admin_only
def create_application():
    profile_info = {}
    form_params_to_ignore = ["csrf_token"]
    checkboxes = ["pre_exec", "post_exec", "user_customization"]

    for checkbox in checkboxes:
        if checkbox in request.form.keys():
            profile_info[checkbox] = True
        else:
            profile_info[checkbox] = False

    for parameter in request.form.keys():
        if parameter not in form_params_to_ignore and parameter not in profile_info.keys():
            if "," in request.form[parameter]:
                profile_info[parameter] = request.form[parameter].split(',')
            else:
                profile_info[parameter] = request.form[parameter]

    new_app_profile = ApplicationProfiles(creator=session["user"],
                                          profile_name=request.form["profile_name"],
                                          profile_parameters=base64.b64encode(json.dumps(profile_info).encode()),
                                          created_on=datetime.datetime.utcnow())
    db.session.add(new_app_profile)
    db.session.commit()
    flash(request.form["profile_name"] + " created successfully.", "success")
    return redirect("/admin/applications")

