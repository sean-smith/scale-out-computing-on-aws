import random
import re
import uuid
import string
a = '''
#dsasd
sad
sad
s
adsa
#PBS -N re@@@#$arfsd
cdfsfsd
fds
'''
request_user = "mcrozes"
check_job_name = re.search(r'#PBS -N (.+)', a)
if check_job_name:
    job_name = re.sub(r'\W+', '', check_job_name.group(1))

z = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))

job_output_path =   "/" + request_user + "/soca_job_output/" + job_name + "_" + z

print(job_output_path)