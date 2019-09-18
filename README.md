# Solution for Scale Out Computing on AWS (SOCA)

## :wrench: How to install SOCA
### 1) Automated installer

Visit https://aws.amazon.com/solutions/<link_tbd>

:rotating_light: If you are planning to heavily customize your cluster, it's recommended you go with option 2 instead.

### 2) Build and install SOCA on your own AWS account

+ 1\) Clone this git repository
```bash
git clone https://github.com/awslabs/solution-for-scale-out-computing-on-aws `
```
+ 2\) Create your own installer by running:
```bash
# You can use either Python2 or Python3
python source/manual_build.py
```

+ 3\) Output will be created under `source/dist/<build_id>`

+ 4\) Upload `source/dist/<build_id>` folder to your own S3 bucket

+ 5\) Launch CloudFormation and use `solution-for-scale-out-computing-on-aws.template` as base template

## :book: Documentation

### New User Guide
link TBD

### Administrator Guide
link tbd

## File Structure
The AWS SOCA project consists in a collection of CloudFormation template, EC2 User-Data and Python scripts

```bash
.
├── solution-for-scale-out-computing-on-aws.template    [ Soca Install Template ]
├── soca                           
│   ├── cluster_analytics                               [ Scripts to ingest cluster/job data into ELK ]
│   ├── cluster_hooks                                   [ Scheduler Hooks ]
│   ├── cluster_logs_management                         [ Scripts to manage cluster log rotation ]
│   ├── cluster_manager                                 [ Scripts to control Soca cluster ]
│   └── cluster_web_ui                                  [ Web Interface ]
├── scripts                                             
│   ├── ComputeNode.sh                                  [ Configure Compute Node ]
│   ├── ComputeNodeInstallDCV.sh                        [ Configure DCV Host ]
│   ├── ComputeNodePostReboot.sh                        [ Post Reboot Compute Node actions ]
│   ├── ComputeNodeUserCustomization.sh                 [ User customization ]
│   ├── config.cfg                                      [ List of all packages to install ]
│   ├── Scheduler.sh                                    [ Configure Schedule Node ]
│   └── SchedulerPostReboot.sh                          [ Post Reboot Scheduler Node actions ]
└── templates                              
    ├── Analytics.template                              [ Manage ELK stack for your cluster ]
    ├── ComputeNode.template                            [ Manage simulation nodes ]
    ├── Configuration.template                          [ Centralize cluster configuration ]
    ├── Network.template                                [ Manage VPC configuration ]
    ├── Scheduler.template                              [ Manage Scheduler host ]
    ├── Security.template                               [ Manage ACL, IAM and SGs ]
    ├── Storage.template                                [ Manage backend storage ]
    └── Viewer.template                                 [ Manage DCV sessions ]
```

***

Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
