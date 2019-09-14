'''
This hook output resource_user.instance_type_used to the current EC2 instance type to the accounting logs

create hook aligo_aws_infos event=execjob_begin
import hook aligo_aws_infos application/x-python default /apps/soca/cluster_hooks/execjob_begin/soca_aws_infos.py
'''

#!/usr/bin/env python
import pbs
import sys
if "/usr/lib/python2.7/site-packages" not in sys.path:
    sys.path.append("/usr/lib/python2.7/site-packages")

if "/usr/lib64/python2.7/site-packages" not in sys.path:
    sys.path.append("/usr/lib64/python2.7/site-packages")

import urllib2

instance_type = urllib2.urlopen("http://169.254.169.254/latest/meta-data/instance-type").read()
instance_type = instance_type.replace('.', '_')
e = pbs.event()
j = e.job
j.resources_used["instance_type_used"] = str(instance_type)



