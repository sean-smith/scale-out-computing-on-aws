'''
This hook reject the job if the user does not have a valid budget associated
Doc: https://awslabs.github.io/scale-out-computing-on-aws/analytics/set-up-budget-project/
create hook check_project_budget event=queuejob
import hook check_project_budget application/x-python default /apps/soca/cluster_hooks/queuejob/check_project_budget.py

Note: If you make any change to this file, you MUST re-execute the import command
'''

#!/apps/python/latest/bin/python3

import sys

import pbs
from ConfigParser import SafeConfigParser  # PBS env is py2.7, so use ConfigParser and not configparser

if "/apps/python/latest/lib/python3.7/site-packages" not in sys.path:
    sys.path.append("/apps/python/latest/lib/python3.7/site-packages/")


def get_all_budgets():
    config = SafeConfigParser(allow_no_value=True)
    budget_per_project = {}
    try:
        config.read(budget_config_file)
        # Get list of all budget
        for section in config.sections():
            budget_per_project[section] = []
            for account in config.options(section):
                budget_per_project[section].append(account)
    except Exception as ex:
        msg = 'Error. Budget file is incorrect: ' + str(ex)
        e.reject(msg)
    return budget_per_project


e = pbs.event()
j = e.job
job_owner = str(e.requestor)
job_queue = str(j.queue)

# User Variables
queue_file = '/apps/soca/cluster_manager/settings/queue_mapping.yml'


