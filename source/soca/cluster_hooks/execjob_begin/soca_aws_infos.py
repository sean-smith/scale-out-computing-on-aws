#!/apps/python/latest/bin/python3

'''
This hook output resource_user.instance_type_used to the current EC2 instance type to the accounting logs

create hook soca_aws_infos event=execjob_begin
import hook soca_aws_infos application/x-python default /apps/soca/cluster_hooks/execjob_begin/soca_aws_infos.py
'''

import pbs
import sys

if "/apps/python/latest/lib/python3.7/site-packages" not in sys.path:
    sys.path.append("/apps/python/latest/lib/python3.7/site-packages/")

import urllib2

instance_type = urllib2.urlopen("http://169.254.169.254/latest/meta-data/instance-type").read()
instance_type = instance_type
e = pbs.event()
j = e.job
j.resources_used["instance_type_used"] = str(instance_type)



