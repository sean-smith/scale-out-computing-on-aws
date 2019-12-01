import os
import sys

from troposphere import Base64, GetAtt
from troposphere import Ref, Template
from troposphere import Tags as default_tags  # without PropagateAtLaunch
from troposphere.autoscaling import AutoScalingGroup, \
    LaunchTemplateSpecification, \
    Tags
from troposphere.cloudformation import AWSCustomObject
from troposphere.ec2 import PlacementGroup, \
    BlockDeviceMapping, \
    LaunchTemplate, \
    LaunchTemplateData, \
    EBSBlockDevice, \
    CpuOptions, \
    IamInstanceProfile, \
    InstanceMarketOptions, \
    NetworkInterfaces, \
    SpotOptions
from troposphere.fsx import FileSystem, LustreConfiguration


class CustomResourceSendAnonymousMetrics(AWSCustomObject):
    resource_type = "Custom::SendAnonymousMetrics"
    props = {
        "ServiceToken": (str, True),
        "DesiredCapacity": (str, True),
        "InstanceType": (str, True),
        "Efa": (str, True),
        "ScratchSize": (str, True),
        "RootSize": (str, True),
        "SpotPrice": (str, True),
        "BaseOS": (str, True),
        "StackUUID": (str, True),
        "KeepForever": (str, True),
        "FsxLustre": (str, True),
    }

# Metadata
t = Template()
t.set_version("2010-09-09")
t.set_description("(SOCA) - Base template to deploy compute nodes.")
allow_anonymous_data_collection = True  # change to False to disable.
debug = False

def main(**params):
    try:
        # Begin LaunchTemplateData
        UserData = '''
        #!/bin/bash -xe
        # Aligo Specific - DO NOT EDIT
        export PATH=$PATH:/usr/local/bin
        if [ "''' + params['BaseOS'] + '''" == "centos7" ] || [ "''' + params['BaseOS'] + '''" == "rhel7" ];
            then
                EASY_INSTALL=$(which easy_install-2.7)
                $EASY_INSTALL pip
                PIP=$(which pip2.7)
                $PIP install awscli
        fi
        if [ "''' + params['BaseOS'] + '''" == "amazonlinux2" ];
            then
                /usr/sbin/update-motd --disable
        fi
        echo export "SOCA_BASE_OS="''' + params['BaseOS'] + '''"" >> /etc/environment
        echo export "SOCA_JOB_QUEUE="''' + params['JobQueue'] + '''"" >> /etc/environment
        echo export "SOCA_JOB_OWNER="''' + params['JobOwner'] + '''"" >> /etc/environment
        echo export "SOCA_JOB_NAME="''' + params['JobName'] + '''"" >> /etc/environment
        echo export "SOCA_JOB_PROJECT="''' + params['JobProject'] + '''"" >> /etc/environment
        echo export "SOCA_VERSION="''' + params['Version'] + '''"" >> /etc/environment
        echo export "SOCA_JOB_EFA="''' + str(params['Efa']).lower() + '''"" >> /etc/environment
        echo export "SOCA_JOB_ID="''' + params['JobId'] + '''"" >> /etc/environment
        echo export "SOCA_SCRATCH_SIZE=''' + str(params['ScratchSize']) + '''" >> /etc/environment
        echo export "SOCA_INSTALL_BUCKET="''' + params['S3Bucket'] + '''"" >> /etc/environment
        echo export "SOCA_INSTALL_BUCKET_FOLDER="''' + params['S3InstallFolder'] + '''"" >> /etc/environment
        echo export "SOCA_FSX_LUSTRE_BUCKET="''' + str(params['FSxLustreBucket']).lower() + '''"" >> /etc/environment
        echo export "SOCA_FSX_LUSTRE_DNS="''' + str(params['FSxLustreDns']).lower() + '''"" >> /etc/environment
        echo export "AWS_STACK_ID=${AWS::StackName}" >> /etc/environment
        echo export "AWS_DEFAULT_REGION=${AWS::Region}" >> /etc/environment
        
        
        source /etc/environment
        AWS=$(which aws)
        
        # Tag EBS disks manually as CFN does not support it
        AWS_AVAIL_ZONE=$(curl http://169.254.169.254/latest/meta-data/placement/availability-zone)
        AWS_REGION="`echo \"$AWS_AVAIL_ZONE\" | sed "s/[a-z]$//"`"
        AWS_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
        EBS_IDS=$(aws ec2 describe-volumes --filters Name=attachment.instance-id,Values="$AWS_INSTANCE_ID" --region $AWS_REGION --query "Volumes[*].[VolumeId]" --out text | tr "\n" " ")
        $AWS ec2 create-tags --resources $EBS_IDS --region $AWS_REGION --tags Key=soca:JobOwner,Value="$SOCA_JOB_OWNER" Key=soca:JobProject,Value="$SOCA_JOB_PROJECT" Key=Name,Value="soca-job-$SOCA_JOB_ID"  Key=soca:JobId,Value="$SOCA_JOB_ID" Key=soca:JobQueue,Value="$SOCA_JOB_QUEUE"
        
        # Give some sudo permission to the user on this specific machine
        echo "''' + params['JobOwner'] + ''' ALL=(ALL) /bin/yum" >> /etc/sudoers
        
        echo "@reboot /bin/aws s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/ComputeNodePostReboot.sh /root && /bin/bash /root/ComputeNodePostReboot.sh >> /root/ComputeNodePostInstall.log 2>&1" | crontab -
        # Feel free to add new scripts based on your own requirement.
        
        $AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/config.cfg /root/
        $AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/ComputeNode.sh /root/
        /bin/bash /root/ComputeNode.sh ''' + params['S3Bucket'] + ''' ''' + params['EFSDataDns'] + ''' ''' + params['EFSAppsDns'] + ''' ''' + params['SchedulerHostname'] + ''' >> /root/ComputeNode.sh.log 2>&1      
        '''

        ltd = LaunchTemplateData("NodeLaunchTemplateData")
        ltd.EbsOptimized = True
        ltd.CpuOptions = CpuOptions(
            CoreCount=int(params["CoreCount"]),
            ThreadsPerCore=1 if params["ThreadsPerCore"] is False else 2)
        ltd.IamInstanceProfile = IamInstanceProfile(Arn=params["ComputeNodeInstanceProfileArn"])
        ltd.KeyName = params["SSHKeyPair"]
        ltd.ImageId = params["ImageId"]
        if params["SpotPrice"] is not False:
            ltd.InstanceMarketOptions = InstanceMarketOptions(
                MarketType="spot",
                SpotOptions=SpotOptions(
                    MaxPrice=params["SpotPrice"]))

        ltd.InstanceType = params["InstanceType"]
        ltd.NetworkInterfaces = [NetworkInterfaces(
            InterfaceType="efa" if params["Efa"] is not False else Ref("AWS::NoValue"),
            DeleteOnTermination=True,
            DeviceIndex=0,
            Groups=[params["SecurityGroupId"]]
        )]

        ltd.UserData = Base64(UserData)
        ltd.BlockDeviceMappings = [
            BlockDeviceMapping(
                DeviceName="/dev/xvda" if params["BaseOS"] == "amazonlinux2" else "/dev/sda1",
                Ebs=EBSBlockDevice(
                    VolumeSize=params["RootSize"],
                    VolumeType="gp2",
                    DeleteOnTermination=True,
                    Encrypted=True))
        ]
        if params["ScratchSize"] > 0:
            ltd.BlockDeviceMappings.append(
                BlockDeviceMapping(
                    DeviceName="/dev/xvdbx",
                    Ebs=EBSBlockDevice(
                        VolumeSize=params["ScratchSize"],
                        VolumeType="io1" if params["VolumeTypeIops"] > 0 else "gp2",
                        Iops=params["VolumeTypeIops"] if params["VolumeTypeIops"] > 0 else Ref("AWS::NoValue"),
                        DeleteOnTermination=True,
                        Encrypted=True))
            )
        # End LaunchTemplateData

        # Begin Launch Template Resource
        lt = LaunchTemplate("NodeLaunchTemplate")
        lt.LaunchTemplateName = params["ClusterId"] + "-" + params["JobId"]
        lt.LaunchTemplateData = ltd
        t.add_resource(lt)
        # End Launch Template Resource

        # If More than 1 instance, create MixedInstancesPolicy
        instance_type_count = (params["InstanceType"].split(",")).__len__()
        '''        
        if instance_type_count > 1:
            mip = MixedInstancesPolicy()
            id = InstancesDistribution()
            # if Spot detected, create EC2 Spot Fleet
            """
            "OnDemandAllocationStrategy": (basestring, False),
            "OnDemandBaseCapacity": (integer, False),
            "OnDemandPercentageAboveBaseCapacity": (integer, False),
            "SpotAllocationStrategy": (basestring, False),
            "SpotInstancePools": (integer, False),
            "SpotMaxPrice": (basestring, False),
            """
            mip.LaunchTemplate = Ref(lt)
            mip.InstancesDistribution = Ref(id)
            # Will Create Override
            pass
        # End
        '''
        # Begin FSx for Lustre
        if params["FSxLustreBucket"] is not False:
            fsx_lustre_configuration = LustreConfiguration()
            fsx_lustre_configuration.ImportPath = params["FSxLustreBucket"]
            fsx_lustre_configuration.ExportPath = params['FSxLustreBucket'] + "/" + params["ClusterId"] + "-fsxoutput/job-" + params["JobId"] + "/"
            fsx_lustre = FileSystem("FSxForLustre")
            fsx_lustre.FileSystemType = "LUSTRE"
            fsx_lustre.StorageCapacity = params["FSxLustreSize"]
            fsx_lustre.SecurityGroupIds = [params["SecurityGroupId"]]
            fsx_lustre.SubnetIds = [params["SubnetId"]]
            fsx_lustre.LustreConfiguration = fsx_lustre_configuration
            fsx_lustre.Tags = default_tags(
                # False disable PropagateAtLaunch
                Name=params["ClusterId"]+"-compute-job-" + params["JobId"],
                _soca_JobId=params["JobId"],
                _soca_JobName=params["JobName"],
                _soca_JobQueue=params["JobQueue"],
                _soca_StackId=Ref("AWS::StackName"),
                _soca_JobOwner=params["JobOwner"],
                _soca_JobProject=params["JobProject"],
                _soca_KeepForever=params["KeepForever"],
                _soca_FSx="True",
                _soca_ClusterId=params["ClusterId"],
            )
            t.add_resource(fsx_lustre)
        # End FSx For Lustre

        # End FSx for Lustre
        # Begin AutoScalingGroup Resource
        asg = AutoScalingGroup("AutoScalingComputeGroup")
        asg.DependsOn = "NodeLaunchTemplate"
        asg.LaunchTemplate = LaunchTemplateSpecification(
            LaunchTemplateId=Ref(lt),
            Version=GetAtt(lt, "LatestVersionNumber"))
        asg.MinSize = int(params["DesiredCapacity"])
        asg.MaxSize = int(params["DesiredCapacity"])
        asg.VPCZoneIdentifier = [params["SubnetId"]]
        if params["PlacementGroup"] is True:
            pg = PlacementGroup("ComputeNodePlacementGroup")
            pg.Strategy = "cluster"
            t.add_resource(pg)
            asg.PlacementGroup = Ref(pg)

        asg.Tags = Tags(
            Name=params["ClusterId"]+"-compute-job-" + params["JobId"],
            _soca_JobId=params["JobId"],
            _soca_JobName=params["JobName"],
            _soca_JobQueue=params["JobQueue"],
            _soca_StackId=Ref("AWS::StackName"),
            _soca_JobOwner=params["JobOwner"],
            _soca_JobProject=params["JobProject"],
            _soca_KeepForever=params["KeepForever"],
            _soca_ClusterId=params["ClusterId"],
            _soca_NodeType="soca-compute-node")
        t.add_resource(asg)
        # End AutoScalingGroup Resource

        # Begin Custom Resource
        # Change Mapping to No if you want to disable this
        if allow_anonymous_data_collection is True:
            metrics = CustomResourceSendAnonymousMetrics("SendAnonymousData")
            metrics.ServiceToken = params["SolutionMetricLambda"]
            metrics.DesiredCapacity = str(params["DesiredCapacity"])
            metrics.InstanceType = str(params["InstanceType"])
            metrics.Efa = str(params["Efa"])
            metrics.ScratchSize = str(params["ScratchSize"])
            metrics.RootSize = str(params["RootSize"])
            metrics.SpotPrice = str(params["SpotPrice"])
            metrics.BaseOS = str(params["BaseOS"])
            metrics.StackUUID = str(params["StackUUID"])
            metrics.KeepForever = str(params["KeepForever"])
            metrics.FsxLustre = "False" if params["FSxLustreBucket"] is False else 'True'
            t.add_resource(metrics)
            # End Custom Resource

        if debug is True:
            print(t.to_json())
        # Tags must use "soca:<Key>" syntax
        template_output = t.to_yaml().replace("_soca_", "soca:")
        return {'success': True,
                'output': template_output}
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        return {'success': False,
                'output': 'cloudformation_builder.py: ' + (str(e) + ': error :' + str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))}
