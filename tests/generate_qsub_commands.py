import os

# Note: AMIs are for us-west-2. Adjust if using different region (find AMIs on the primary template mapping)
distribution = {'amazonlinux2': 'ami-082b5a644766e0e6f',
                'centos7': 'ami-01ed306a12b7d1c96',
                'rhel7': 'ami-036affea69a1101c9'}

# S3 Bucket to mount on FSx. Make sure you DO have updated your IAM policy and added API permission to your bucket for the scheduler
# Must start with s3://
fsx_s3_bucket = ''

for distro, ami_id in distribution.items():
    print('Generating commands to test EFA ... for ' + distro)
    print('qsub -N ' + distro + '_efa -l instance_type=c5n.18xlarge -l efa_support=true -l instance_ami=' +ami_id + ' -l base_os=' + distro + ' -- /opt/amazon/efa/bin/fi_info -p efa')
    print('Generating commands to test custom root/scratch size ... for ' + distro)
    print('qsub -N ' + distro + '_root_scratch -l root_size=26 -l scratch_size=98 -l instance_ami=' +ami_id + ' -l base_os=' + distro + ' -- /bin/df -h')
    print('Generating commands to test automatic detection of instance store as /scratch partition ... for ' + distro)
    print('qsub -N ' + distro + '_instance_store -l instance_type=m5ad.4xlarge -l instance_ami=' +ami_id + ' -l base_os=' + distro + ' -- /bin/df -h')
    if fsx_s3_bucket != '':
        print('Generating commands to test FSx ... for ' + distro)
        print('qsub -N ' + distro + '_fsx -l fsx_lustre_bucket=s3://'+fsx_s3_bucket+' -l instance_ami=' +ami_id + ' -l base_os=' + distro + ' -- /bin/df -h')

