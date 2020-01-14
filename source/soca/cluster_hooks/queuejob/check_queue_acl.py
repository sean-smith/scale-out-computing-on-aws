'''
This hook reject the job if the user is not allowed to use the queue
Doc: https://awslabs.github.io/scale-out-computing-on-aws/tutorials/manage-queue-acls/
create hook check_queue_acl event=queuejob
import hook check_queue_acl application/x-python default /apps/soca/cluster_hooks/queuejob/check_queue_acl.py

Note: If you make any change to this file, you MUST re-execute the import command
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


e = pbs.event()
j = e.job
job_owner = str(e.requestor)
job_queue = "normal" if str(j.queue) == "" else str(j.queue)
pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: job_queue  ' + str(j.queue))
queue_settings_file = "/apps/soca/%SOCA_CONFIGURATION/cluster_manager/settings/queue_mapping.yml"
reader = open(queue_settings_file, "r")

try:
    docs = yaml.load_all(reader)
except Exception as err:
    message = "Unable to open " + queue_settings_file + " due to " + str(err)
    e.reject(message)

for doc in docs:
    for items in doc.values():
        for info in items.values():
            queues = info['queues']
            if job_queue in queues:
                allowed_users = []
                excluded_users = []

                if isinstance(info['allowed_users'], list) is not True:
                    e.reject("allowed_users (" + queue_settings_file + ") must be a list. Detected: " +str(type(info['allowed_users'])))

                if isinstance(info['excluded_users'], list) is not True:
                    e.reject("excluded_users (" + queue_settings_file + ") must be a list. Detected: " + str(type(info['excluded_users'])))

                if 'allowed_users' in info.keys():
                    for user in info['allowed_users']:
                        if "cn=" in user.lower():
                            allowed_users = allowed_users + find_users_in_ldap_group(user)
                        else:
                            allowed_users.append(user)

                    #pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: allowed_users  ' + str(allowed_users))

                else:
                    message = "allowed_users directive not detected on " + str(queue_settings_file)
                    e.reject(message)

                if 'excluded_users' in info.keys():
                    for user in info['excluded_users']:
                        if "cn=" in user.lower():
                            excluded_users = allowed_users + find_users_in_ldap_group(user)
                        else:
                            excluded_users.append(user)
                    #pbs.logmsg(pbs.LOG_DEBUG, 'queue_acl: excluded_users  ' + str(excluded_users))
                else:
                    message = "excluded_users directive not detected on " + str(queue_settings_file)
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

reader.close()
