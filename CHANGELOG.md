# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2020-02-01
- Added support for MixedInstancePolicy and InstanceDistribution
- Added support for non-EBS optimized instances such as t2
- Added integration for AWS Session Manager
- Added integration for AWS Backup
- Added integration for AWS Cognito
- Added integration for Troposphere
- Added support for ACLs at queue level
- Ignore installation if PBSPro is already configured on the AMI
- Default IP during installation to 0.0.0.0/0
- Fixed bug when stack name only use uppercase
- ComputeNode bootstrap scripts are now loaded from EFS
- Users can now install SOCA using existing resources such as VPC, Security Groups ...
- Users now have the ability to retain EBS disks associated to a simulation for debugging purposes
- Users can now open a SSH session using SSM Session Manager
- Processes are now automatically launched upon scheduler reboot 
- Spot price now default to the OD price
- Ulimit is now disabled by default on all compute nodes
- Dispatcher automatically append "s3://" if not present when using FSx For Lustre
- Updated default ElasticSeach instance to m5.large to support encryption at rest
- SOCA libraries are now installed under /apps/soca/<CLUSTER_ID> location to support multi SOCA environments 
- SOCA now prevent jobs to be submitted if .yaml configuration files are malformed
- Web UI now display the reason when a DCV job can't be submitted
- Scheduler Root EBS is now tagged with cluster ID 
- Scheduler Network Interface is now tagged with cluster ID 
- Scheduler and Compute hosts are now sync with Chrony

## [1.0.0] - 2019-11-20
- Release Candidate

