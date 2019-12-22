# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2019-12-20
- Added support for Troposphere
- Ignore installation if Python/PBSPro is already configured on the AMI
- Default IP during installation to 0.0.0.0/0
- Fixed bug when stack name only use uppercase
- ComputeNode bootstrap scripts are now loaded from EFS
- Support for MixedInstancePolicy and InstanceDistribution
- Support for non-EBS optimized instances such as t2
- Users now have the ability to retain EBS disks associated to a simulation for debugging purposes
- Supports for Session Manager
- Other various improvements

## [1.0.0] - 2019-11-20
- Release Candidate

