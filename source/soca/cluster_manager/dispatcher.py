"""
DT HPC DYNAMIC CLUSTER MANAGER
This script retrieve all queued jobs, calculate PBS resources required to launch each job
and provision EC2 capacity if all resources conditions are met.
"""
import json
import argparse
import boto3
import logging
import fnmatch
import re
import subprocess
import yaml
import datetime
from datetime import timedelta
import pytz
import ast
import os
import sys
sys.path.append(os.path.dirname(__file__))
import configuration
import add_nodes


def run_command(cmd, type):
    try:
        if type == "check_output":
            command = subprocess.check_output(cmd)
        elif type == "call":
            command = subprocess.call(cmd)
        else:
            print("Command not Defined")
            exit(1)
        return command
    except subprocess.CalledProcessError as e:
        return ""


def fair_share_job_id_order(sorted_queued_job, user_fair_share):
    '''
    Generate the job order to provision based on fair share score

    example:
    sorted_queued_job = [
        {'get_job_id': 1, 'get_job_owner': 'mcrozes'},
        {'get_job_id': 2, 'get_job_owner': 'mcrozes'},
        {'get_job_id': 3, 'get_job_owner': 'mcrozes'},
        {'get_job_id': 4, 'get_job_owner': 'test'},
        {'get_job_id': 5, 'get_job_owner': 'test'},
    ]
    user_fair_share = {'mcrozes': 100,
                       'test': 50}

    Result:
    Next User is mcrozes
Next User is test
Next User is mcrozes
Next User is test
Next User is mcrozes
Next User is test
[1, 4, 2, 5, 3]

    '''

    job_ids_to_start = []
    order = 0
    while order <= sorted_queued_job.__len__():
        sorted_user_fair_share = sorted(user_fair_share.items(), key=lambda kv: kv[1], reverse=True)
        logpush('Fair Share Score: ' + str(sorted_user_fair_share))

        next_user = sorted_user_fair_share[0][0]
        logpush('Next User is ' + next_user)

        next_user_jobs = [i['get_job_id'] for i in sorted_queued_job if i['get_job_owner'] == next_user]
        logpush('Next Job for user is ' + str(next_user_jobs))
        for job_id in next_user_jobs:
            if job_id in job_ids_to_start:
                if next_user_jobs.__len__() == 1:
                    # User don't have any more queued job
                    del user_fair_share[next_user]
            else:
                job_ids_to_start.append(job_id)
                user_fair_share[next_user] = user_fair_share[next_user] + fair_share_running_job_malus
                break

        order += 1

    logpush('jobs id re-order based on fairshare: ' +str(job_ids_to_start))
    return job_ids_to_start


def fair_share_score(queued_jobs, running_jobs, queue):
    user_score = {}
    now = int((datetime.datetime.now()).strftime('%s'))

    # First, apply malus for users who already have running job
    for r_job_data in running_jobs:
        if r_job_data['get_job_owner'] not in user_score.keys():
            user_score[r_job_data['get_job_owner']] = fair_share_start_score + fair_share_running_job_malus
        else:
            user_score[r_job_data['get_job_owner']] = user_score[r_job_data['get_job_owner']] + fair_share_running_job_malus

    for q_job_data in queued_jobs:
        if 'stack_id' in q_job_data['get_job_resource_list'].keys():
            # If job is queued and in the process of start (provision capacity), we apply the running job malus
            job_bonus_score = fair_share_running_job_malus

        else:

            # Begin FairShare Formula
            timestamp_submission = q_job_data['get_job_queue_time_epoch']
            resource_name = q_job_data['get_job_resource_list'].keys()
            license = 0

            for license_name in fnmatch.filter(resource_name, '*_lic*'):
                logpush('Job use the following licenses:' + str(license_name) + ' - ' + str(q_job_data['get_job_resource_list'][license_name]))
                license += int(q_job_data['get_job_resource_list'][license_name])

            required_resource = int(q_job_data['get_job_nodect']) + license
            logpush('Job Required Resource Bonus ' + str(required_resource))

            if queue in ['normal', 'burst', 'low', 'normalplus', 'datacheck']:
                # Abaqus jobs have different coefficient
                c1 = 0.5
                c2 = 1.7
                job_bonus_score = required_resource * (c1 * ((int(now) - int(timestamp_submission))/3600/24) ** c2)
            else:
                c1 = 1
                c2 = 0
                job_bonus_score = 1

            logpush('Job ' + str(q_job_data['get_job_id']) + ' queued for ' + str((int(now) - int(timestamp_submission)) / 60) + ' minutes: bonus %.2f' % job_bonus_score)

            # END
        if q_job_data['get_job_owner'] not in user_score.keys():
            user_score[q_job_data['get_job_owner']] = fair_share_start_score + job_bonus_score
        else:
            user_score[q_job_data['get_job_owner']] = user_score[q_job_data['get_job_owner']] + job_bonus_score

        '''
        # Old 
        if q_job_data['get_job_owner'] not in user_score.keys():
            user_score[q_job_data['get_job_owner']] = fair_share_start_score + ranking[queue_time]
        else:
            user_score[q_job_data['get_job_owner']] = user_score[q_job_data['get_job_owner']] + ranking[queue_time]
        '''


    # Remove user with no queued job
    for user, score in user_score.items():
        if [i['get_job_owner'] for i in queued_jobs if i['get_job_owner'] == user]:
            pass
        else:
            del user_score[user]

    return user_score


def send_notification(subject, email_message, job_owner):
    '''
    Todo/ Email Addresses should be retrieved as part of LDAP attribute
    But just in case here is an example of how to use SES
    try:
        ses_client = boto3.client('ses', region_name='us-west-2')
        ses_client.send_email(
            Source='<your_email>',
            Destination={
                'ToAddresses': [
                    job_owner + '@<your_tld>',
                ]},
            Message={
                'Subject': {
                    'Data': subject,
                },
                'Body': {
                    'Html': {
                        'Data': email_message,
                    }
                }}, )
    except Exception as err:
        logpush(err)
    '''
    pass


def logpush(message, status='info'):
    if status == 'error':
        logger.error(message)
    else:
        logger.info(message)


def get_jobs_infos(queue):
    command = [system_cmds['aligoqstat'], '-f', 'json', '-u', 'all',  '-q', queue]
    output = run_command(command, "check_output")
    return json.loads(output)


def check_if_queue_started(queue_name):
    queue_start = run_command([system_cmds['qmgr'], '-c', 'print queue ' + queue_name + ' started'], "check_output")
    queue_enabled = run_command([system_cmds['qmgr'], '-c', 'print queue ' + queue_name + ' enabled'], "check_output")
    if 'True' in str(queue_start) and 'True' in str(queue_enabled):
        return True
    else:
        return False


# BEGIN FLEXLM FUNCTIONS
def check_available_licenses(commands, license_to_check):
    output = {}
    if commands.__len__() == 0:
        return {}

    for pbs_resource, flexlm_cmd in commands.items():
        if pbs_resource in license_to_check:
            try:
                available_licenses = run_command([flexlm_cmd.split()], "check_output")
                output[pbs_resource] = int(available_licenses.rstrip())

            except subprocess.CalledProcessError as e:
                logpush("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output), 'error')
                exit(1)

    return output
# END FLEXLM FUNCTIONS


# BEGIN EC2 FUNCTIONS


def can_launch_capacity(instance_type, count, image_id, job_id):
    try:
        ec2.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            SubnetId=aligo_configuration['PrivateSubnet1'], #in case of very old AWS account which used to have Classic EC2
            MaxCount=count,
            MinCount=count,
            DryRun=True)

    except Exception as e:
        if e.response['Error'].get('Code') == 'DryRunOperation':
            logpush('Dry Run Succeed, capacity can be added')
            return True
        else:
            logpush('Dry Run Failed, capacity can not be added: ' +str(e), 'error')
            if 'InstanceType' in str(e):
                print('''
                Your Job ''' + str(job_id) + ''' has been removed from the queue.<hr> 
                <h2>Error #003</h2> Your EC2 instance type (''' + str(instance_type) + ''') is not valid.
                <h2>How to fix</h2> https://confluence.amazon.com/display/DTHPC/Job+Submission+Errors#JobSubmissionsError-003:InstanceTypeisIncorrect
                ''')
                run_command([system_cmds['qdel'], str(job_id)], "check_output")
            return False

def clean_cloudformation_stack():
    pass
    # handle specific use case where
    # user submit job with SPOT instance
    # stack created, spot instance requested
    # spot instance can't be fulfilled
    # user delete job from the queue
    # stakc will stay forever. Instead we need to describe all stacks and delete them if they are assigned to a job that no longer exist

def check_cloudformation_status(stack_id, job_id, job_select_resource):
    # This function is only called if we detect a queued job with an already assigned Compute Unit
    try:
        logpush('Checking existing cloudformation ' +str(stack_id))
        check_stack_status = cloudformation.describe_stacks(StackName=stack_id)
        if check_stack_status['Stacks'][0]['StackStatus'] == 'CREATE_COMPLETE':
            logpush(job_id + ' is queued but CI has been specified and CloudFormation has been created.')
            stack_creation_time = check_stack_status['Stacks'][0]['CreationTime']
            now = pytz.utc.localize(datetime.datetime.utcnow())
            if now > (stack_creation_time + timedelta(hours=1)):
                logpush(job_id + ' Stack has been created for more than 1 hour. Because job has not started by then, rollback compute_node value')
                new_job_select = job_select_resource.split(':compute_node')[0] + ':compute_node=tbd'
                qalter_cmd = [system_cmds['qalter'], "-l", "stack_id=", "-l", "select=" + new_job_select, str(job_id)]
                run_command(qalter_cmd, "call")
                cloudformation.delete_stack(StackName=stack_id)
            else:
                logpush(job_id + ' Stack has been created for more less than 1 hour. Let wait a bit before killing the CI and reset the compute_node value')

        elif check_stack_status['Stacks'][0]['StackStatus'] == 'CREATE_IN_PROGRESS':
            logpush(job_id + ' is queued but have a valid CI assigned. However CloudFormation stack is not completed yet so we exit the script. See https://issues-pdx.amazon.com/issues/DTSYS-1433 for more details')
            return False

        elif check_stack_status['Stacks'][0]['StackStatus'] in ['CREATE_FAILED', 'ROLLBACK_COMPLETE']:
            logpush(job_id + ' is queued but have a valid CI assigned. However CloudFormation stack is ' + str(check_stack_status['Stacks'][0]['StackStatus']) +'.  Because job has not started by then, rollback compute_node value and delete stack')
            new_job_select = job_select_resource.split(':compute_node')[0] + ':compute_node=tbd'
            qalter_cmd = [system_cmds['qalter'], "-l", "stack_id=", "-l", "select=" + new_job_select, str(job_id)]
            run_command(qalter_cmd, "call")
            cloudformation.delete_stack(StackName=stack_id)

        else:
            pass

    except:
        # Stack does not exist (job could not start for whatever reason but compute has been provisioned
        logpush(job_id + ' is queued with a valid compute Unit. However we did not detect any cloudformation stack. To ensure job can start, we rollback compute_node to default value in order for hosts to be re-provisioned')
        # Rollback compute_node value to default 'tobereplaced' to retry job
        new_job_select = job_select_resource.split(':compute_node')[0] + ':compute_node=tbd'
        qalter_cmd = [system_cmds['qalter'], "-l", "stack_id=", "select=" + new_job_select, str(job_id)]
        run_command(qalter_cmd, "call")

    return True

# END EC2 FUNCTIONS



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', nargs='?', required=True, help="Path to a configuration file")
    parser.add_argument('-t', '--type', nargs='?', required=True, help="queue type - ex: graphics, compute .. Open YML file for more info")
    arg = parser.parse_args()
    queue_type = (arg.type)

    # Begin Pre-requisite
    system_cmds = {
        'qstat': '/opt/pbs/bin/qstat',
        'qmgr': '/opt/pbs/bin/qmgr',
        'qalter': '/opt/pbs/bin/qalter',
        'qdel': '/opt/pbs/bin/qdel',
        'aligoqstat': '/apps/soca/cluster_manager/aligoqstat.py'
    }

    # AWS Clients
    ses = boto3.client('ses')
    ec2 = boto3.client('ec2')
    cloudformation = boto3.client('cloudformation')
    aligo_configuration = configuration.get_aligo_configuration()

    # General Variables
    instance_type = None
    queues = None
    custom_ami = None
    asg_name = None
    spot_price = None
    efa_support = None
    placement_group = 'true' # use str, not bool
    fair_share_running_job_malus = -60
    fair_share_start_score = 100

    # Generate PBS configuration mapping
    stream_resource_mapping = open('/apps/soca/cluster_manager/settings/queue_mapping.yml', "r")
    docs = yaml.load_all(stream_resource_mapping)
    for doc in docs:
        for items in doc.values():
            for type, info in items.items():
                if type == queue_type:
                    instance_type = info['default_instance']
                    queues = info['queues']
                    custom_ami = info['default_ami']
                    if 'scratch_size' in info.keys():
                        scratch_size = info['scratch_size']
                    else:
                        scratch_size = False

        stream_resource_mapping.close()

    if instance_type is None or queues is None or custom_ami is None:
        print('Error, instance_type, queues or custom ami is None')
        print(instance_type)
        print(queue_type)
        print(custom_ami)
        exit(0)

    default_instance_type = instance_type

    # Generate FlexLM mapping
    stream_flexlm_mapping = open('/apps/soca/cluster_manager/settings/licenses_mapping.yml', "r")
    docs = yaml.load_all(stream_flexlm_mapping)
    custom_flexlm_resources = {}
    for doc in docs:
        for k, v in doc.items():
            for license_name, license_output in v.items():
                custom_flexlm_resources[license_name] = license_output
    stream_flexlm_mapping.close()

    # End Pre-requisite

    for queue_name in queues:
        log_file = logging.FileHandler('/apps/soca/cluster_manager/logs/' + queue_name + '.log','a')
        formatter = logging.Formatter('[%(asctime)s] [%(lineno)d] [%(levelname)s] [%(message)s]')
        log_file.setFormatter(formatter)
        logger = logging.getLogger('tcpserver')
        for hdlr in logger.handlers[:]:  # remove all old handlers
            logger.removeHandler(hdlr)

        logger.addHandler(log_file)  # set the new handler
        logger.setLevel(logging.DEBUG)
        skip_queue = False

        get_jobs = get_jobs_infos(queue_name)
        logpush('================================================================')

        # Check if there is any queued job with valid compute unit but has not started within 1 hour
        for job_id, job_data in get_jobs.items():
            if job_data['get_job_state'] == 'Q':
                check_compute_unit = re.search(r'compute_node=(\w+)', job_data['get_job_resource_list']['select'])
                if check_compute_unit:
                    job_data['get_job_resource_list']['compute_node'] = check_compute_unit.group(1)
                    try:
                        if check_cloudformation_status(job_data['get_job_resource_list']['stack_id'], job_id, job_data['get_job_resource_list']['select']) is False:
                            logpush('Skipping ' + str(job_id))
                            # Because applications are license dependant, we want to make sure we won't launch any new jobs until previous launched jobs are running and using the license
                            #skip_queue = True
                    except KeyError:
                        # in certain very rare case, stack_id is not present (after a AWS outage causing some API to fail), in this case we just ignore
                        pass

                else:
                    get_jobs[job_id]['get_job_resource_list']['compute_node'] = 'tbd'




        queued_jobs = [get_jobs[k] for k, v in get_jobs.items() if v['get_job_state'] == 'Q']
        running_jobs = [get_jobs[k] for k, v in get_jobs.items() if v['get_job_state'] == 'R']
        user_fair_share = fair_share_score(queued_jobs, running_jobs, queue_name)
        logpush('Detected Default Instance Type: ' + instance_type)
        #logpush('Queued Jobs: ' + str(queued_jobs))

        if check_if_queue_started(queue_name) is False:
            logpush('Queue does not seems to be enabled')
            skip_queue = True

        if queued_jobs.__len__() == 0:
            skip_queue = True

        if skip_queue is False:
            # Find all Licenses required by the jobs. licenses must use  *_lic_* format
            licenses_required = []
            for job_data in queued_jobs:
                resource_name = job_data['get_job_resource_list'].keys()
                for license_name in fnmatch.filter(resource_name, '*_lic*'):
                    if license_name not in licenses_required:
                        licenses_required.append(license_name)

            # on les list de required_pbs_reosurce, trouver tout ce qu'il ya "_lic_"
            license_available = check_available_licenses(custom_flexlm_resources, licenses_required)
            logpush('License Available: ' + str(license_available))
            #logpush('Queued Jobs: ' +str(queued_jobs))
            logpush('User Fair Share: ' + str(user_fair_share))
            job_id_order_based_on_fairshare = fair_share_job_id_order(sorted(queued_jobs, key=lambda k: k['get_job_order_in_queue']), user_fair_share)

            logpush('Job_id_order_based_on_fairshare: ' + str(job_id_order_based_on_fairshare))



            queue_mode = 'fairshare'

            if queue_mode == 'fairshare':
                job_list = job_id_order_based_on_fairshare
            elif queue_mode == 'fifo':
                job_list = sorted(queued_jobs, key=lambda k: k['get_job_order_in_queue'])
            else:
                print('queue mode must either be fairshare or fifo')
                exit(1)

            for job_id in job_list:
                if queue_mode == 'fifo':
                    job = job_id
                else:
                    job = get_jobs[job_id]


                job_owner = str(job['get_job_owner'])
                job_id = str(job['get_job_id'])

                if job ['get_job_resource_list']['compute_node'] != 'tbd':
                    skip_job = True
                else:
                    skip_job = False

                if skip_job is False:
                        instance_type = default_instance_type
                        job_required_resource = job['get_job_resource_list']
                        tmp = {}
                        logpush('Checking if we have enough resources available to run job_' + job_id)
                        can_run = True

                        for res in job_required_resource:
                            if 'instance_type' in res:
                                logpush('instancetype resource is specified, will use new ec2 instance type: ' + job_required_resource['instance_type'])
                                instance_type = job_required_resource['instance_type']

                            if 'instance_ami' in res:
                                logpush('image resource is specified, will use new ec2 AMI: ' + job_required_resource['instance_ami'])
                                custom_ami = job_required_resource['instance_ami']

                            if 'scratch_size' in res:
                                logpush('scratch_size resource is specified, will use custom scratch of (GB): ' + job_required_resource['scratch_size'])
                                scratch_size = job_required_resource['scratch_size']

                            if 'spot_price' in res:
                                spot_price = job_required_resource['spot_price']
                                logpush('spot_price resource is specified, will use SPOT instances with BID: ' + str(spot_price))
                                if isinstance(spot_price, float) is True:
                                    spot_price = str(job_required_resource['spot_price'])
                                else:
                                    logpush("spot price must be a float. Ignoring " + str(spot_price) + " and capacity will run as OnDemand")

                            if 'placement_group' in res:
                                if job_required_resource['placement_group'] in ['true', 'false']:
                                    logpush('placement_group resource is specified, will use custom scratch of (GB): ' + job_required_resource['placement_group'])
                                    placement_group = job_required_resource['placement_group']


                            if 'efa_support' in res:
                                logpush('efa_support resource is specified, will attach one EFA adapter')
                                efa_support = 'true'



                            try:
                                if fnmatch.filter([res], '*_lic*'):
                                    if int(job_required_resource[res]) <= license_available[res]:
                                        # job can run
                                        tmp[res] = int(job_required_resource[res])
                                    else:
                                        logpush('Ignoring job_' + job_id + ' as we we dont have enough: ' + str(res))
                                        can_run = False
                            except:
                                logpush('One required PBS resource has not been specified on the JSON input for ' + job_id + ': ' + str(res) +' . Please update custom_flexlm_resources on ' +str(arg.config))
                                exit(1)

                        ec2_instances_to_add = int(job_required_resource['nodect'])
                        cpus_count_pattern = re.search(r'[.](\d+)', instance_type)
                        if cpus_count_pattern:
                            cpu_per_system = int(cpus_count_pattern.group(1)) * 2
                        else:
                            cpu_per_system = '2'

                        # Checking Pre-requisite
                        if 'ppn' in job_required_resource.keys():
                            if job_required_resource['ppn'] > cpu_per_system:
                                logpush('Ignoring Job ' + job_id + ' as the PPN specified (' + str(job_required_resource['ppn']) + ') is higher than the number of cpu per system : ' + str(cpu_per_system), 'error')
                                error_msg = '''
                                    Your Job ''' + job_id + ''' has been removed from the queue.<hr> 
                                    <h2>Error #002</h2> Detected ''' + str(job_required_resource['ppn']) + ''' PPN (process-per-node) which is higher than the PPN for the EC2 instance configured.<br>
                                    <ul><li> Instance Type: ''' + instance_type + '''</li> <li> Max PPN: ''' + str(cpu_per_system) + ''' </li></ul>
                                    <h2>How to fix </h2> https://confluence.amazon.com/display/DTHPC/Job+Submission+Errors#JobSubmissionsError-002:PPNisIncorrect
                                    '''
                                print(error_msg)
                                run_command([system_cmds['qdel'], job_id], 'check_output')
                                can_run = False

                        if can_run is True:
                            logpush('job_' + job_id + ' can run, doing dry run test ...')
                            if can_launch_capacity(instance_type, ec2_instances_to_add, custom_ami, job_id) is True:
                                try:
                                    keep_forever = 'false'
                                    create_new_asg = add_nodes.main(instance_type,
                                                                    ec2_instances_to_add,
                                                                    queue_name,
                                                                    custom_ami,
                                                                    job_id,
                                                                    job['get_job_name'],
                                                                    job['get_job_owner'],
                                                                    job['get_job_project'],
                                                                    keep_forever,
                                                                    scratch_size,
                                                                    placement_group,
                                                                    spot_price if spot_price is not None else 'false',
                                                                    efa_support,
                                                                    # Additional tags below
                                                                    {})

                                    if create_new_asg['success'] is True:
                                        compute_unit = create_new_asg['compute_node']
                                        stack_id = create_new_asg['stack_name']
                                        logpush(str(job_id) + " : compute_node=" + str(compute_unit) + " | stack_id=" +str(stack_id))

                                        # Add new PBS resource to the job
                                        # stack_id=xxx -> CloudFormation Stack Name
                                        # compute_node=xxx -> Unique ID that will be assigned to all EC2 hosts for this job

                                        select = job_required_resource['select'].split(':compute_node')[0] + ':compute_node=' + str(compute_unit)
                                        logpush('select variable: ' +str(select))

                                        run_command([system_cmds['qalter'], "-l", "select="+select, str(job_id)], "call")
                                        run_command([system_cmds['qalter'], "-l", "stack_id=" + stack_id, str(job_id)], "call")

                                        for resource, count_to_substract in tmp.items():
                                            license_available[resource] = (license_available[resource] - count_to_substract)
                                            logpush('License available: ' + str(license_available[resource]))

                                    else:
                                        logpush('Error while trying to create ASG: ' + str(create_new_asg['error']))
                                        send_notification('Error creating ASG', 'Create ASG failed for job_' + job_id + ' with error: ' +  str(create_new_asg['error']),'mcrozes')
                                        '''
                                        # Most likely, problem is that stack exist but not recognized correctly, as a failover we force the compute_node value
                                        try:
                                            select = job_required_resource['select'].split(':compute_node')[0] + ':compute_node=job' + str(job_id)
                                            logpush('forcing re-creation of select variable: ' + str(select))
                                            subprocess.check_output(system_cmds['qalter'] + " -l select=" + select + " " + str(job_id),shell=True)
                                            subprocess.check_output(system_cmds['qalter'] + " -l stack_id=soca-job-" + str(job_id) ,shell=True)

                                        except Exception as e:
                                            logpush('Error, can not force back select parameters to default value')
                                        '''

                                except Exception as e:
                                    logpush('Create ASG failed for job_'+job_id + ' with error: ' + str(e) + ' This may be due to an CloudFormation having the same name already exist.', 'error')
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                    logpush(str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))
