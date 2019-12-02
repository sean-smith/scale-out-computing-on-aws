---
title: Job customization for EC2
---

Scale-Out Computing on AWS made [job submission on EC2 very easy](../../launch-your-first-job/) and is fully integrated with EC2.
Below is a list of parameters you can specify when you request your simulation to ensure the hardware provisioned will exactly match your simulation requirements. 

!!!info 
    If you don't specify them, your job will use the default values configured for your queue (see `/apps/soca/cluster_manager/settings/queue_mapping.yml`)  

## Compute

| Parameter | Note  | Example  |
|---|---|---|
| -l instance_type | Reference to the type of instance you want to provision for the job   | -l instance_type=c5.xlarge |
| -l instance_ami| Reference to a custom AMI you want to use  | -l instance_ami=ami-12345|
| -l base_os | Select the base OS of the AMI (centos7, rhel7 or amazonlinux2) | -l base_os=centos7 |
| -l spot_price | Enable support for spot instance by specifying the maximum price you are willing to pay. Use "auto" to cap at OD price  | -l spot_price=1.5 / -l spot_price=auto|
| -l subnet_id | Deploy capacity in a specific private subnet | -l subnet_id=sub-12345 |
| -l ht_support | Enable or disable support for Hyper Threading (disabled by default) | -l ht_support=yes |

## Storage

| Parameter | Note  | Example  |
|---|---|---|
| -l root_size | Reference to the size of the local root volume you want to allocate (in GB) |  -l root_size=600 |
| -l scratch_size | Reference to the size of the local /scratch (SSD - gp2 type) you want to allocate (in GB). |  -l scratch_size=600 |
| -l scratch_iops | IOps to specify for scratch disk. When used, EBS default to io1 type |  -l scratch_iops=3000 |
| -l fsx_lustre_bucket | Create an epehmeral FSx for your job and mount the  S3 bucket specified |  -l fsx_lustre_bucket=s3://my_bucket/mypath |
| -l fsx_lustre_size | Size in GB of your FSx. Default to the smallest (1200GB) option. Must be 1200, 2400 or increment of 3600|  -l fsx_lustre_size=7200 |
| -l fsx_lustre_dns |  DNS of the FSx you want to mount|  -l fsx_lustre_dns=fs-abcde.fsx.us-west-2.amazonaws.com |




## Network


| Parameter | Note  | Example  |
|---|---|---|
| -l placement_group| Enable or disable placement group (enabled by default when using more than 1 node unless placement_group=false is specified)  | -l placement_group=true|
| -l efa_support | Enable Elastic Fabric Adapter (when instance supports it) | -l efa_support=yes |



## How to use custom parameters

!!!example
    Here is an example about how to use a custom AMI at job or queue level. This example is applicable to all other parameters (simply change the parameter name to the one you one to use). 
    
#### For a single job
Use `-l instance_ami` parameter if you want to only change the AMI for a single job

~~~bash
$ qsub -l instance_ami=ami-082b... -- /bin/echo Hello
~~~

!!!note "Priority"
    Job resources have the highest priorities. Your job will always use the AMI specified at submission time even if it's different thant the one configure at queue level.

#### For an entire queue

Edit `/apps/soca/cluster_manager/settings/queue_mapping.yml` and update the default `instance_ami` parameter if you want all jobs in this queue to use your new AMI:

~~~yaml hl_lines="4"
queue_type:
  compute:
    queues: ["queue1", "queue2", "queue3"] 
    instance_ami: "<YOUR_AMI_ID>" # <- Add your new AMI 
    instance_type: ...
    root_size: ...
    scratch_size: ...
    efa: ...
    ....
~~~
