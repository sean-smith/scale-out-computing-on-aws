'''
This hook reject the job if the user is not allowed to use the queue
Doc: https://awslabs.github.io/scale-out-computing-on-aws/tutorials/manage-queue-acls/
create hook check_queue_config event=queuejob
import hook check_queue_config application/x-python default /apps/soca/<CLUSTER_ID>/cluster_hooks/queuejob/check_queue_config.py

Note: If you make any change to this file, you MUST re-execute the import command.
If you are installing this file manually, make sure to replace %SOCA_CONFIGURATION path below
--

"allowed_users" / "excluded_users" must be:
 1 - Be a list of username: allowed_users = ["user1","user2"]
 2 - Be a list of OpenLDAP group: allowed_user=["DC=mygroup,OU=Group,DC=soca,DC=local"]
 3 - Or both: allowed_users = ["user1", "DC=mygroup,OU=Group,DC=soca,DC=local", "user2"]
'''

import os
import sys

import pbs

sys.path.append('/usr/lib64/python2.7/site-packages')
import yaml


def find_users_in_ldap_group(group_dn):
    cmd = "ldapsearch -x -b " + group_dn + " -LLL | grep memberUid | awk '{print $2}'"
    users_in_group = os.popen(cmd).read()
    pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: find_users_in_ldap_group' + str(users_in_group))
    return list(filter(None, users_in_group.split('\n')))


def is_allowed_instance_type(instance_type, allowed_instance_types, excluded_instance_types):
    #A very basic sanity check on instance_type provided by user
    if '.' in instance_type:
        family = instance_type.split('.')[0]
    else:
        return False

    all_instances_allowed = True if len(allowed_instance_types) == 0 else False
    no_instances_excluded = True if len(excluded_instance_types) == 0 else False

    if all_instances_allowed and no_instances_excluded:
       return True

    #check if on exclude list
    for excluded_type in excluded_instance_types:
        if instance_type == excluded_type:
            return False
        elif '.' not in excluded_type and family == excluded_type:
            return False

    #check if on allowed list
    for allowed_type in allowed_instance_types:
        if instance_type == allowed_type:
            return True
        elif '.' not in allowed_type and family == allowed_type:
            return True

    #if all instances are allowed default to true otherwise false
    if all_instances_allowed:
        return True
    else:
        return False

      
e = pbs.event()
j = e.job
job_owner = str(e.requestor)
job_queue = "normal" if str(j.queue) == "" else str(j.queue)
pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: job_queue  ' + str(j.queue))
if 'instance_type' in j.Resource_List:
    instance_type = j.Resource_List['instance_type']
else:
    instance_type = None

# Validate license_mapping YAML is not malformed
try:
    license_settings_file = "/apps/soca/%SOCA_CONFIGURATION/cluster_manager/settings/licenses_mapping.yml"
    lic_reader = open(license_settings_file, "r")
    lic_data = yaml.safe_load(lic_reader)
except Exception as err:
    message = "Job cannot be submitted. Unable to read " + license_settings_file + ". Double chek the YAML syntax is correct and you don't have any invalid indent.\n Error: " + str(err)
    e.reject(message)

# Validate queue_mapping YAML is not malformed
try:
    queue_settings_file = "/apps/soca/%SOCA_CONFIGURATION/cluster_manager/settings/queue_mapping.yml"
    queue_reader = open(queue_settings_file, "r")
    docs = yaml.safe_load(queue_reader)
except Exception as err:
    message = "Job cannot be submitted. Unable to read " + queue_settings_file + ". Double chek the YAML syntax is correct and you don't have any invalid indent.\n Error: " + str(err)
    e.reject(message)

# Validate Queue ACLs
for doc in docs.values():
    for k, v in doc.items():
        queues = v['queues']
        if job_queue in queues:
            allowed_users = []
            excluded_users = []
            if isinstance(v['allowed_users'], list) is not True:
                e.reject("allowed_users (" + queue_settings_file + ") must be a list. Detected: " +str(type(v['allowed_users'])))
            if isinstance(v['excluded_users'], list) is not True:
                e.reject("excluded_users (" + queue_settings_file + ") must be a list. Detected: " + str(type(v['excluded_users'])))
            if isinstance(v['allowed_instance_types'], list) is not True:
                e.reject("allowed_instance_types (" + queue_settings_file + ") must be a list. Detected: " +            str(type(v['allowed_instance_types'])))
            if isinstance(v['excluded_instance_types'], list) is not True:
                e.reject("excluded_instance_types (" + queue_settings_file + ") must be a list. Detected: " +           str(type(v['excluded_instance_types'])))

            allowed_instance_types = v['allowed_instance_types']
            excluded_instance_types = v['excluded_instance_types']

            if instance_type:
                 is_valid_instance = is_allowed_instance_type(instance_type, allowed_instance_types,                      excluded_instance_types)
            else:
                 #if no instance tpe in resource list default is used which is assumed to be valid.
                 is_valid_instance = True

            if 'allowed_users' in v.keys():
                for user in v['allowed_users']:
                    if "cn=" in user.lower():
                        allowed_users = allowed_users + find_users_in_ldap_group(user)
                    else:
                        allowed_users.append(user)
                #pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: allowed_users  ' + str(allowed_users))

            else:
                message = "allowed_users directive not detected on " + str(queue_settings_file)
                e.reject(message)

            if 'excluded_users' in v.keys():
                for user in v['excluded_users']:
                    if "cn=" in user.lower():
                        excluded_users = allowed_users + find_users_in_ldap_group(user)
                    else:
                        excluded_users.append(user)
                    #pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: excluded_users  ' + str(excluded_users))
            else:
                message = "excluded_users directive not detected on " + str(queue_settings_file)
                e.reject(message)

            if not is_valid_instance:
                  message = instance_type + " is not allowed for queue " + job_queue + ". Contact your HPC admin and update " + queue_settings_file
                  e.reject(message)

            if excluded_users.__len__() == 0 and allowed_users.__len__() == 0:
                e.accept()
            else:

                if excluded_users[0] == "*" and job_owner not in allowed_users:
                    message = job_owner + " is not authorized to use submit this job on the queue " + job_queue + ". Contact your HPC admin and update " + queue_settings_file
                    e.reject(message)

                if job_owner in allowed_users:
                    e.accept()

                if job_owner in excluded_users:
                    message = job_owner + " is not authorized to use submit this job on the queue " + job_queue + ". Contact your HPC admin and update " + queue_settings_file
                    e.reject(message)

