import argparse
import boto3
import yaml
import random
import uuid
import sys
import os
import ast
sys.path.append(os.path.dirname(__file__))
import configuration


def can_launch_capacity(instance_type, count, image_id, subnet_id):
    try:
        ec2 = boto3.client('ec2')
        ec2.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            SubnetId=subnet_id,
            MaxCount=int(count),
            MinCount=int(count),
            DryRun=True)

    except Exception as e:
        if e.response['Error'].get('Code') == 'DryRunOperation':
            return True
        else:
            print('Dry Run Failed, capacity can not be added: ' +str(e))
            return False


def main(instance_type,
         desired_capacity,
         queue,
         custom_ami,
         job_id,
         job_name,
         job_owner,
         job_project,
         keep_forever,
         scratch_size,
         root_size,
         placement_group,
         spot_price,
         efa_support,
         base_os,
         subnet,
         tags
         ):

    cloudformation = boto3.client('cloudformation')
    s3 = boto3.resource('s3')

    aligo_configuration = configuration.get_aligo_configuration()
    # Note: If you change the ComputeNode, you also need to adjust the IAM policy to match your new template name
    create_stack_location = s3.Object(aligo_configuration['S3Bucket'], aligo_configuration['S3InstallFolder'] +'/templates/ComputeNode.template')
    stack_template = create_stack_location.get()['Body'].read().decode('utf-8')
    soca_private_subnets = [aligo_configuration['PrivateSubnet1'], aligo_configuration['PrivateSubnet2'], aligo_configuration['PrivateSubnet3']]

    if subnet is False:
        subnet_id = random.choice(soca_private_subnets)
    else:
       if subnet in soca_private_subnets:
            subnet_id = subnet
       else:
           return {'success': False,
                   'error': 'Incorrect subnet_id. Must be one of ' + str(soca_private_subnets)}

    if int(desired_capacity) > 1:
        if placement_group == 'false':
            # for testing purpose, sometimes we want to compare performance w/ and w/o placement group
            placement_group = 'false'
        else:
            placement_group = 'true'
    else:
        placement_group = 'false'

        # Force Tag if they don't exist. DO NOT DELETE them or host won't be able to be registered by nodes_manager.py
    if keep_forever is True:
        unique_id = str(uuid.uuid4())
        stack_name = aligo_configuration['ClusterId'] + '-keepforever-' + queue + '-' + unique_id
        job_id = stack_name
        tags['soca:KeepForever'] = 'true'
    else:
        stack_name = aligo_configuration['ClusterId'] + '-job-' + str(job_id)
        tags['soca:KeepForever'] = 'false'

    if 'soca:NodeType' not in tags.keys():
        tags['soca:NodeType'] = 'soca-compute-node'

    if 'soca:ClusterId' not in tags.keys():
        tags['soca:ClusterId'] = aligo_configuration['ClusterId']

    if 'soca:JobId' not in tags.keys():
        tags['soca:JobId'] = job_id

    if 'Name' not in tags.keys():
        tags['Name'] = stack_name.replace('_', '-')

    job_parameters = {
        'Version': aligo_configuration['Version'],
        'S3InstallFolder': aligo_configuration['S3InstallFolder'],
        'S3Bucket': aligo_configuration['S3Bucket'],
        'PlacementGroup':  placement_group,
        'SecurityGroupId': aligo_configuration['ComputeNodeSecurityGroup'],
        'KeepForever': 'true' if keep_forever is True else 'false', # needs to be lowercase
        'SSHKeyPair': aligo_configuration['SSHKeyPair'],
        'ComputeNodeInstanceProfile': aligo_configuration['ComputeNodeInstanceProfile'],
        'Efa': efa_support,
        'JobId': job_id,
        'ScratchSize': 0 if scratch_size is False else scratch_size,
        'RootSize': 10 if root_size is False else root_size,
        'ImageId': custom_ami if custom_ami is not None else aligo_configuration['CustomAMI'],
        'JobName': job_name,
        'JobQueue': queue,
        'JobOwner': job_owner,
        'JobProject': job_project,
        'ClusterId': aligo_configuration['ClusterId'],
        'EFSAppsDns': aligo_configuration['EFSAppsDns'],
        'EFSDataDns': aligo_configuration['EFSDataDns'],
        'SubnetId': subnet_id,
        'InstanceType': instance_type,
        'SchedulerHostname': aligo_configuration['SchedulerPrivateDnsName'],
        'DesiredCapacity': desired_capacity,
        'BaseOS': aligo_configuration['BaseOS'] if base_os is False else base_os,
        'SpotPrice': spot_price if spot_price is not None else 'false',
    }

    stack_tags = [{'Key': str(k), 'Value': str(v)} for k, v in tags.items() if v]
    stack_params = [{'ParameterKey': str(k), 'ParameterValue': str(v)} for k, v in job_parameters.items() if v]

    if job_parameters['BaseOS'] not in ['rhel7', 'centos7', 'amazonlinux2']:
        return {'success': False,
                'error': 'base_os must be one of the following value: centos7, amazonlinux2, rhel7'}

    if job_parameters['Efa'] == 'true':
        if not 'n' in job_parameters['InstanceType']:
            return {'success': False,
                    'error': 'You have requested EFA support but your instance type does not support EFA: ' + str(job_parameters['InstanceType'])}

    can_launch = can_launch_capacity(job_parameters['InstanceType'], job_parameters['DesiredCapacity'], job_parameters['ImageId'], subnet_id)

    if can_launch is True:
        try:
            launch = cloudformation.create_stack(StackName=stack_name,
                                        TemplateBody=stack_template,
                                        Parameters=stack_params,
                                        Tags=stack_tags)

            # PBS configuration is automatically updated by nodes_manager
            return {'success': True,
                    'stack_name': stack_name,
                    'compute_node': 'job'+str(job_id)
                    }

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            return {'success': False,
                    'error':  str(exc_type) + ' : ' + str(fname) + ' : ' + str(exc_tb.tb_lineno) + ' : ' + str(e) + ' : ' + str(launch)}
    else:
        return {'success': False }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance_type', nargs='?', required=True, help="Instance type you want to deploy")
    parser.add_argument('--desired_capacity', nargs='?', required=True, help="Number of EC2 instances to deploy")
    parser.add_argument('--queue', nargs='?', required=True, help="Queue to map the capacity")
    parser.add_argument('--instance_ami', nargs='?', help="AMI to use")
    parser.add_argument('--subnet_id', default=None, help='Launch capacity in a special subnet')
    parser.add_argument('--job_id', nargs='?', help="Job ID for which the capacity is being provisioned")
    parser.add_argument('--job_name', nargs='?', required=True, help="Job Name for which the capacity is being provisioned")
    parser.add_argument('--job_owner', nargs='?', required=True, help="Job Owner for which the capacity is being provisioned")
    parser.add_argument('--job_project', nargs='?', default=False, help="Job Owner for which the capacity is being provisioned")
    parser.add_argument('--scratch_size', default=False, nargs='?', help="Size of /scratch in GB")
    parser.add_argument('--root_size', default=False, nargs='?', help="Size of Root partition in GB")
    parser.add_argument('--placement_group', help="Enable or disable placement group")
    parser.add_argument('--tags', nargs='?', help="Tags, format must be {'Key':'Value'}")
    parser.add_argument('--keep_forever', action='store_const', const=True, help="Wheter or not capacity will stay forever")
    parser.add_argument('--base_os', default=False, help="Specify custom Base OK")
    parser.add_argument('--efa', action='store_const', const='true', help="Support for EFA")
    parser.add_argument('--spot_price', nargs='?', help="Spot Price")

    arg = parser.parse_args()

    if arg.job_id is None and arg.keep_forever is None:
        print('--job_id or --keep_forever must be specified')
        exit(1)

    if arg.placement_group is None:
        placement_group = 'true'
    else:
        if arg.placement_group not in ['true', 'false']:
            print('--placement_group must either be true or false')
            exit(1)

    if not isinstance(int(arg.desired_capacity), int):
        print('Desired Capacity must be an int')
        exit(1)

    if arg.tags is None:
        arg.tags = {}
    else:
        try:
            arg.tags = ast.literal_eval(arg.tags)
            if not isinstance(arg.tags, dict):
                print('Tags must be a valid dictionary')
                exit(1)
        except ValueError:
            print('Tags must be a valid dictionary')
            exit(1)

    launch = (main(arg.instance_type,
               arg.desired_capacity,
               arg.queue,
               arg.instance_ami,
               arg.job_id,
               arg.job_name,
               arg.job_owner,
               arg.job_project,
               arg.keep_forever,
               arg.scratch_size,
               arg.root_size,
               arg.placement_group,
               arg.spot_price,
               False if arg.efa is None else arg.efa,
               arg.base_os,
               False if arg.subnet_id is None else arg.subnet_id,
               arg.tags))

    if launch['success'] is True:
        if arg.keep_forever is True:
            print("""
            IMPORTANT:
            You specified --keep-forever flag. This instance will be running 24/7 until you MANUALLY terminate the Cloudformation Stack  
            """)
    else:
        print('Error: ' +str(launch))
