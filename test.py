
import re

job_to_submit = """#!/bin/bash #PBS -N %job_name% #PBS -P %job_project% # I do not want my user to be able to change the queue #PBS -q myqueue #PBS -l instance_type=%instance_type% # CD into current working directory cd $PBS_O_WORKDIR # Prepare the job environment, edit the current PATH, License Server etc export PATH=/apps/softwarename/%version%/ export LICENSE_SERVER=1234@licenseserver.internal # Run the solver /apps/softwarename/%version%/bin/solver --cpus %cpus% \ --input-file %input_file% \ --parameter1 %parameter1% BACKUP=%backup% if [[ "$BACKUP" -eq 1 ]]; then aws s3 sync . s3://%bucket_to_archive%/ fi"""
nodect = 50
cpu_per_system = 10


check_job_node_count = re.search(r'#PBS -l select=(\d+)', job_to_submit)
find_shebang = re.search(r'#!([^\s]+)', job_to_submit)

if find_shebang:
    shebang = find_shebang.group(1)
else:
    shebang = False

if check_job_node_count:
    if str(check_job_node_count.group(1)) != str(nodect):
        job_to_submit = job_to_submit.replace("#PBS -l select=" + str(check_job_node_count.group(1)),
                                              "#PBS -l select=" + str(nodect))
else:
    if shebang:
        # Add right after shebang
        job_to_submit = job_to_submit.replace(shebang, shebang + " " + "#PBS -l select=" + str(nodect) + ":ncpus=" + str(cpu_per_system) + " # Added by SOCA Web UI")
    else:
        # Add first line
        job_to_submit = "#PBS -l select=" + str(nodect) + ":ncpus=" + str(cpu_per_system) + " # Added by SOCA Web UI" + job_to_submit


