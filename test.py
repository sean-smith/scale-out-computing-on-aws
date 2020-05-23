
import re


payload = '''

#pbs sdasd 
dsadas
sdffs
#PBS -N teub dsad g
#PBS -P tdsad df f 
dsad
dsa '''

# Basic Input verificationc
check_job_name = re.search(r'#PBS -N (.+)', payload)
check_job_project = re.search(r'#PBS -P (.+)', payload)

if check_job_name:
    sanitized_job_name = re.sub(r'\W+', '', check_job_name.group(1))  # remove invalid char,space etc...
    payload = payload.replace("#PBS -N " + check_job_name.group(1), "#PBS -N " + sanitized_job_name)
else:
    job_name = ""

if check_job_project:
   sanitized_job_project = re.sub(r'\W+', '', check_job_project.group(1))  # remove invalid char,space etc...
   payload = payload.replace("#PBS -P " + check_job_project.group(1), "#PBS -P " + sanitized_job_project)


print(payload)