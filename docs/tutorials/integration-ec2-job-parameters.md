---
title: Job customization for EC2
---

Scale-Out Computing on AWS made [job submission on EC2 very easy](../../launch-your-first-job/) and is fully integrated with EC2.
Below is a list of parameters you can specify when you request your simulation to ensure the hardware provisioned will exactly match your simulation requirements. 

!!!info 
    If you don't specify them, your job will use the default values configured for your queue (see `/apps/soca/cluster_manager/settings/queue_mapping.yml`)
    ____
    You can [the web-based simulator](../../job-configuration-generator/) to generate your qsub command very easily.

## Compute

#### base_os

- Description: Reference to the base OS of the AMI you are using
- Allowed Values: `amazonlinux2` `centos7` `rhel7`
- Default: If not specified, value default to the OS of the install AMI
- Examples: 
    - `-l base_os=centos7`: Instances provisioned will be deployed against centos manifest
 
#### ht_support

*Disabled by default*

- Description: Enable support for hyper-threading
- [Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-launchtemplate-launchtemplatedata-cpuoptions.html)
- Allowed Value: `yes` `true` (case insensitive) 
- Examples:
    - `-l ht_support=True`: Enable hyper-threading for all instances
    - `-l ht_support=False`: Disable hyper-threading for all instances (default)
       
#### instance_ami

- Description: Reference to a custom AMI you want to use
- Default: If not specified, value default to the AMI specified during installation
- Examples:
    - `-l instance_ami=ami-abcde123`: Capacity provisioned for the job will use the specific AMI

!!!info 
    If your are planning to use an AMI which is *not using the same OS* as the scheduler, you will need to specify `base_os` parameter

#### instance_type

- Description: The type of instance to provision for the simulation
- Examples:
    - `-l instance_type=c5.large`: Provision a c5.large for the simulation
    - `-l instance_type=c5.large+c5.2xlarge`: Provision a mix of c5.large and c5.2xlarge for the simulation.

!!!info
    You can specify multiple instance type using "+" sign.
     When using more than 1 instance type, AWS will prioritize the capacity based on the order (eg: launch c5.large first and switch to c5.2xlarge if needed)

#### spot_allocation_count

- Description: Specify the % of SPOT instances to launch when provisioning both OD (On Demand) and SPOT instances
- [Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-autoscaling-autoscalinggroup-instancesdistribution.html#cfn-autoscaling-autoscalinggroup-instancesdistribution-ondemandbasecapacity)
- Allowed Value: Integer
- Default: 100
- Examples:
    - `-l spot_price=auto -l spot_allocation_pct=50`: Will provision 50% OD instance, 50% SPOT with max spot price capped to OD price
    - `-l spot_price=1.4 -l spot_allocation_pct=25`: Will provision 75% OD instance, 25% SPOT with max spot price set to $1.4 
    - `-l spot_price=auto`: Only provision SPOT instances

!!!note
    This parameter is ignored if `spot_price` is not specified
    
#### spot_allocation_strategy

- Description: Choose allocation strategy when using multiple SPOT instances type
- [Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-autoscaling-autoscalinggroup-instancesdistribution.html#cfn-autoscaling-autoscalinggroup-instancesdistribution-spotallocationstrategy)
- Allowed Value: `capacity-optimized` or `lowest-cost`
- Default Value: `lowest-cost`
- Examples:
    - `-l spot_allocation_strategy=capacity-optimized`: AWS will provision compute nodes based on capacity availabilities


#### spot_price

- Description: Enable support for SPOT instances
- [Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-launchtemplate-launchtemplatedata-instancemarketoptions-spotoptions.html#cfn-ec2-launchtemplate-launchtemplatedata-instancemarketoptions-spotoptions-maxprice)
- Allowed Value: any float value or `auto`
- Examples:
    - `-l spot_price=auto`: Max price will be capped to the On-Demand price
    - `-l spot_price=1.4`: Max price you are willing to pay for this instance will be $1.4 an hour.

#### subnet_id

- Description: Reference to a subnet ID to use
- Default: If not specified, value default to one of the three private subnets created during installation
- Examples:
    - `-l subnet_id=sub-abcde123`

      
## Storage

### EBS

#### root_size

- Description: Define the size of the local root volume
- Unit: GB
- Example: `-l root_size=300` -> Provision a 300 GB disk

#### scratch_size

- Description: Define the size of the local root volume
- Unity: GB
- Example: `-l scratch_size=300` -> Provision a 300 GB disk mounted under /scratcj

!!!info
    scratch disk is automatically mounted on all nodes associated to the simulation under `/scratch`

#### instance_store

!!!info 
    SOCA automatically mount instance storage when available. 
    For instances having more than 1 volume, SOCA will create a raid device (link for More info)
    in all cases, instance store volumes will be mounted on `/scratch`

#### scratch_iops

- Description: Define the number of provisioned IOPS to allocate for your `/scratch` device
- Unity: IOPS
- Example: `-l scratch_iops=3000`

!!!info
    It is recommended to set the IOPs to 3x storage capacity of your EBS disk



### FSx for Lustre

#### fsx_lustre_bucket

- Description: Create an ephemeral FSx for your job and mount the  S3 bucket specified 
- Example: `-l fsx_lustre_bucket=my-bucket-name` -> Provision a 300 GB disk

!!!info
    You need to give IAM permission first <add link>

    If not specified, SOCA automatically prefix your bucket name with  `s3://`
    
    If `fsx_lustre_size` is not specified, default to 1200 GB

#### fsx_lustre_size

- Description: Create an ephemeral FSx for your job and mount the  S3 bucket specified 
- Example: `-l fsx_lustre_capacity=3600` -> Provision a 3.6TB EFS disk

!!!info    
    If `fsx_lustre_size` is not specified, default to 1200 GB
    
#### fsx_lustre_dns

- Description: Mount an existing FSx 
- Example: `-l fsx_lustre_dns=xxx` -> Provision a 3.6TB EFS disk

!!!info    
    `fsx_lustre_bucket` is ignore if  `fsx_lustre_bucket` is specified.

## Network

#### efa_support

- Description: Enable EFA support
- Allowed Value: yes, true, True 
- Example: `-l efa_support=True` -> Provision a 3.6TB EFS disk

!!!info    
    You must use an EFA compatible instance, otherwise your job will stay in the queue



#### placement_group

*Enabled by default*

- Description: Disable support for hyper-threading
- Allowed Value: yes, true, True 
- Example: `-l ht_support=True` -> Enable hyper-threading for all instances


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


## Examples


**Launch On-Demand instance**
    
`-l instance_type=c5.large`
    
**Launch SPOT instance capped to OD price**
    
`-l instance_type=c5.large -l spot_price=auto`
    
**Launch SPOT instance capped to specific (less than OD) price**
    
`-l instance_type=c5.large -l spot_price=0.8`
    
**Launch multiple On-Demand instances**
    
`-l instance_type=c5.large+c5.9xlarge`
    
**Launch multiple SPOT instances**
    
`-l instance_type=c5.large+c5.9xlarge -l spot_price=auto`
    
**Launch mix of On-Demand and Spot (80% SPOT capped at $1.8 20% on-demand)**
    
`-l instance_type=c5.large -l spot_price=1.8 -l spot_allocation_pct=80`

**Launch multiple spot instances and provision them based on capacity availability**
    
`-l instance_type=c5.large+5.2xlarge -l spot_price=auto -l spot_allocation_strategy=capacity-optimized`

**Launch multiple spot instances and provision them based on price (default value if spot_allocation_strategy is not specified)**
    
`-l instance_type=c5.large+5.2xlarge -l spot_price=auto -l spot_allocation_strategy=lowest-price`
       