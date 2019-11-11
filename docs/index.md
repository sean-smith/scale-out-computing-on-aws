---
title: What is SOCA ?
---
<p align="center">
<img src="imgs/soca_logo_WT_BG.png" height="150px">
</p>

Scale-Out Computing on AWS is a solution that helps customers more easily deploy and operate a multiuser environment for computationally intensive workflows. The solution features a large selection of compute resources; fast network backbone; unlimited storage; and budget and cost management directly integrated within AWS. The solution also deploys a user interface (UI) and automation tools that allows you to create your own queues, scheduler resources, Amazon Machine Images (AMIs), software, and libraries. 
This solution is designed to provide a production ready reference implementation to be a starting point for deploying an AWS environment to run scale-out workloads, allowing you to focus on running simulations designed to solve complex computational problems.  
____
## Easy installation
[Installation of your SOCA cluster](/install-soca-cluster/) is fully automated and managed by CloudFormation 

!!!info "Did you know?"
    - You can have multiple SOCA clusters on the same AWS account
    - SOCA comes with a list of unique tags, making resource tracking easy for AWS Administrators

## Access your cluster in 1 click
You can [access your SOCA cluster](/access-soca-cluster/) either using DCV (Desktop Cloud Visualization)[^1] or through SSH.

[^1]: [DCV](https://docs.aws.amazon.com/dcv/latest/adminguide/what-is-dcv.html) is a remote visualization technology that enables users to easily and securely connect to graphic-intensive 3D applications hosted on a remote high-performance server.*

## Simple Job Submission
SOCA supports a list of parameters designed to simplify your job submission on AWS. Advanced users can either manually choose compute/storage/network configuration for their job or simply ignore these parameters and let SOCA choose the most optimal hardware (defined by the HPC administrator)

~~~bash
# Advanced Configuration
user@host$ qsub -l instance_type=c5n.18xlarge \
    -l instance_ami=ami-123abcde
    -l nodes=2 
    -l scratch_size=300 
    -l efa_support=true
    -l spot_price=1.55 myscript.sh

# Basic Configuration
user@host$ qsub myscript.sh
~~~

- [Refer to this page for tutorial and examples](/tutorials/launch-your-first-job/)
- [Refer to this page to list all supported parameters](/tutorials/integration-ec2-job-parameters/)

## OS agnostic and support for custom AMI
Customers can integrate their Centos7/Rhel7/AmazonLinux2 AMI automatically by simply using ==-l instance_ami=<ami_id\>== at job submission. There is no limitation in term of AMI numbers (you can have 10 jobs running simultaneously using 10 different AMIs)

!!!danger "AMI using OS different than the scheduler"
    In case your AMI is different than your scheduler host, you can specify the OS manually to ensure packages will be installed based on the node distribution.

    In this example, we assume your SOCA deployment was done using AmazonLinux2, but you want to submit a job on your personal RHEL7 AMI
 
    ~~~bash
    user@host$ qsub -l instance_ami=<ami_id> -l base_os=rhel7 myscript.sh
    ~~~
    
    _____

!!!info "SOCA AMI requirements"
    When you use a custom AMI, just make sure that your AMI does not use /apps, /scratch or /data partitions as SOCA will need to use these locations during the deployment

## Budgets and Cost Management
You can [review your HPC costs](/analytics/review-hpc-costs/) filtered by user/team/project/queue very easily using AWS Cost Explorer. 

SOCA also supports AWS Budget and [let you create budgets](/analytics/set-up-budget-project/) assigned to user/team/project or queue. To prevent over-spend, SOCA includes hooks to restrict job submission when customer-defined budget has expired.

## Detailed Cluster Analytics 
SOCA [includes ElasticSearch and automatically ingest job and hosts data](/analytics/monitor-cluster-activity/) in real-time for accurate visualization of your cluster activity.

!!!success "Don't know where to start?"
    SOCA [includes dashboard examples](/analytics/build-kibana-dashboards/) if you are not familiar with ElasticSearch or Kibana.
    
## 100% Customizable
SOCA is built entirely on top of AWS and can be customized by users as needed. Most of the logic is based of CloudFormation templates and EC2 User Data scripts.
More importantly, the entire SOCA codebase is open-source and [available on Github](https://github.com/awslabs/scale-out-computing-on-aws).

## Persistent and Unlimited Storage
SOCA includes two unlimited EFS storage (/apps and /data). Customers also have the ability to deploy high-speed SSD EBS disks or FSx for Lustre as scratch location on their compute nodes. [Refer to this page to learn more about the various storage options](/storage/backend-storage-options/) offered by SOCA

## Centralized user-management
Customers [can create unlimited LDAP users and groups](/tutorials/manage-ldap-users/). By default SOCA includes a default LDAP account provisioned during installation as well as a "Sudoers" LDAP group which manage SUDO permission on the cluster.

## Support for network licenses
SOCA includes a FlexLM-enabled script which calculate the number of license for a given features and only start the job/provision the capacity when enough licenses are available. 

## Automatic Errors Handling
SOCA performs various dry run checks before provisioning the capacity. However, it may happen than AWS can't fullfill all requests (eg: need 5 instances but only 3 can be provisioned due to capacity shortage within a placement group). In this case, SOCA will try to provision the capacity for 30 minutes. After 30 minutes, and if the capacity is still not available, SOCA will automatically reset the request and try to provision capacity in a different availability zone.

## Web UI
SOCA includes a simple web ui designed to simplify user interactions such as:

- Start/Stop DCV sessions in 1 click
- Download private key in both PEM or PPK format
- Check the queue status in real-time
- Add/Remove LDAP users 
- Access the analytic dashboard

## Custom fair-share
Each user is given a score which vary based on:

- Number of job in the queue
- Time each job is queued
- Priority of each job
- Type of instance

Job that belong to the user with the highest score will start next 
