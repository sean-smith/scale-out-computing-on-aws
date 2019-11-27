from troposphere import Base64, GetAtt
from troposphere import Equals
from troposphere import If, Not, Sub
from troposphere import Parameter, Ref, Tags, Template
from troposphere.autoscaling import AutoScalingGroup, LaunchTemplateSpecification
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


def main():
    # Metadata
    t = Template()
    t.set_version("2010-09-09")
    t.set_description("(SOCA) - Base template to deploy compute nodes.")

    # Parameters
    Version = t.add_parameter(Parameter("Version", Type="String"))
    S3Bucket = t.add_parameter(Parameter("S3Bucket", Type="String"))
    UsePlacementGroup = t.add_parameter(Parameter("PlacementGroup",  Type="String", AllowedValues=[True, False]))
    SecurityGroupId = t.add_parameter(Parameter("SecurityGroupId", Type="List<AWS::EC2::SecurityGroup::Id>"))
    KeepForever = t.add_parameter(Parameter("KeepForever", Default=False, Type="String"))
    SSHKeyPair = t.add_parameter(Parameter("SSHKeyPair", Type="AWS::EC2::KeyPair::KeyName"))
    ComputeNodeInstanceProfile = t.add_parameter(Parameter("ComputeNodeInstanceProfile", Type="String"))
    JobId = t.add_parameter(Parameter("JobId", Type="String",))
    JobProject = t.add_parameter(Parameter("JobProject", Type="String", Default=False))
    ScratchSize = t.add_parameter(Parameter("ScratchSize", Type="Number", Default=0))
    RootSize = t.add_parameter(Parameter("RootSize", Type="Number"))
    ImageId = t.add_parameter(Parameter("ImageId", Type="String"))
    JobName = t.add_parameter(Parameter("JobName", Type="String"))
    JobQueue = t.add_parameter(Parameter("JobQueue", Type="String"))
    JobOwner = t.add_parameter(Parameter("JobOwner", Type="String"))
    ClusterId = t.add_parameter(Parameter("ClusterId", Type="String"))
    EFSAppsDns = t.add_parameter(Parameter("EFSAppsDns", Type="String"))
    EFSDataDns = t.add_parameter(Parameter("EFSDataDns", Type="String"))
    SubnetId = t.add_parameter(Parameter("SubnetId", Type="List<AWS::EC2::Subnet::Id>"))
    InstanceType = t.add_parameter(Parameter("InstanceType", Type="String"))
    SchedulerHostname = t.add_parameter(Parameter("SchedulerHostname", Type="String"))
    DesiredCapacity = t.add_parameter(Parameter("DesiredCapacity", Type="Number"))
    BaseOS = t.add_parameter(Parameter("BaseOS", Type="String"))
    Efa = t.add_parameter(Parameter("Efa", Type="String",AllowedValues=[True, False],Default=False))
    S3InstallFolder = t.add_parameter(Parameter("S3InstallFolder", Type="String"))
    SpotPrice = t.add_parameter(Parameter("SpotPrice", Type="String",Default=False))
    CoreCount = t.add_parameter(Parameter("CoreCount", Type="Number"))
    ThreadsPerCore = t.add_parameter(Parameter("ThreadsPerCore", Type="Number", Default=1))
    VolumeTypeIops = t.add_parameter(Parameter("VolumeTypeIops", Type="Number", Default=0))

    # Conditions
    t.add_condition("UsePlacementGroup", Equals(Ref(UsePlacementGroup), True))
    t.add_condition("UseEFA", Equals(Ref(Efa), True))
    t.add_condition("UseSpotInstance", Not(Equals(Ref(SpotPrice), False)))
    t.add_condition("UseScratchDisk", Not(Equals(Ref(ScratchSize), 0)))
    t.add_condition("UseAmazonLinux", Equals(Ref(BaseOS), "amazonlinux2"))
    t.add_condition("UseProvisionedIo", Not(Equals(Ref(VolumeTypeIops), 0)))

    # Resources

    ## Begin Placement Group
    pg = PlacementGroup("ComputeNodePlacementGroup")
    pg.Strategy = "cluster"
    pg.Condition = "UsePlacementGroup"
    t.add_resource(pg)
    ## End Placement Group

    ## Begin LaunchTemplateData
    UserData = """
    #!/bin/bash -xe
    # Aligo Specific - DO NOT EDIT
    export PATH=$PATH:/usr/local/bin
    if [ "${BaseOS}" == "centos7" ] || [ "${BaseOS}" == "rhel7" ];
        then
            EASY_INSTALL=$(which easy_install-2.7)
            $EASY_INSTALL pip
            PIP=$(which pip2.7)
            $PIP install awscli
    fi
    
    if [ "${BaseOS}" == "amazonlinux2" ];
        then
            /usr/sbin/update-motd --disable
    fi
    echo export "SOCA_BASE_OS='${BaseOS}'" >> /etc/environment
    echo export "SOCA_JOB_QUEUE='${JobQueue}'" >> /etc/environment
    echo export "SOCA_JOB_OWNER='${JobOwner}'" >> /etc/environment
    echo export "SOCA_JOB_NAME='${JobName}'" >> /etc/environment
    echo export "SOCA_JOB_PROJECT='${JobProject}'" >> /etc/environment
    echo export "SOCA_VERSION='${Version}'" >> /etc/environment
    echo export "SOCA_JOB_EFA='${Efa}'" >> /etc/environment
    echo export "SOCA_JOB_ID='${JobId}'" >> /etc/environment
    echo export "SOCA_SCRATCH_SIZE=${ScratchSize}" >> /etc/environment
    echo export "SOCA_INSTALL_BUCKET='${S3Bucket}'" >> /etc/environment
    echo export "SOCA_INSTALL_BUCKET_FOLDER='${S3InstallFolder}'" >> /etc/environment
    echo export "SOCA_VERSION='${Version}'" >> /etc/environment
    echo export "SOCA_FSX_LUSTRE_BUCKET='${FSxLustreBucket}'" >> /etc/environment
    echo export "SOCA_FSX_LUSTRE_DNS='${FSxLustreDns}'" >> /etc/environment
    echo export "AWS_STACK_ID=${AWS::StackName}" >> /etc/environment
    echo export "AWS_DEFAULT_REGION=${AWS::Region}" >> /etc/environment
    
    
    source /etc/environment
    AWS=$(which aws)
    
    # Tag EBS disks manually as CFN does not support it
    AWS_AVAIL_ZONE=$(curl http://169.254.169.254/latest/meta-data/placement/availability-zone)
    AWS_REGION="`echo \"$AWS_AVAIL_ZONE\" | sed 's/[a-z]$//'`"
    AWS_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
    EBS_IDS=$(aws ec2 describe-volumes --filters Name=attachment.instance-id,Values="$AWS_INSTANCE_ID" --region $AWS_REGION --query 'Volumes[*].[VolumeId]' --out text | tr "\n" " ")
    $AWS ec2 create-tags --resources $EBS_IDS --region $AWS_REGION --tags Key=soca:JobOwner,Value="$SOCA_JOB_OWNER" Key=soca:JobProject,Value="$SOCA_JOB_PROJECT" Key=Name,Value="soca-job-$SOCA_JOB_ID"  Key=soca:JobId,Value="$SOCA_JOB_ID" Key=soca:JobQueue,Value="$SOCA_JOB_QUEUE"
    
    # Give some sudo permission to the user on this specific machine
    echo "${JobOwner} ALL=(ALL) /bin/yum" >> /etc/sudoers
    
    echo "@reboot /bin/aws s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/ComputeNodePostReboot.sh /root && /bin/bash /root/ComputeNodePostReboot.sh >> /root/ComputeNodePostInstall.log 2>&1" | crontab -
    # Feel free to add new scripts based on your own requirement.
    
    $AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/config.cfg /root/
    $AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/ComputeNode.sh /root/
    /bin/bash /root/ComputeNode.sh ${S3Bucket} ${EFSDataDns} ${EFSAppsDns} ${SchedulerHostname} >> /root/ComputeNode.sh.log 2>&1  
    
        """
    ltd = LaunchTemplateData()
    ltd.EbsOptimized = True
    ltd.CpuOptions = CpuOptions(
        CoreCount=Ref(CoreCount),
        ThreadsPerCore=Ref(ThreadsPerCore))
    ltd.IamInstanceProfile = IamInstanceProfile(Arn=Ref(ComputeNodeInstanceProfile))
    ltd.KeyName = Ref(SSHKeyPair)
    ltd.ImageId = Ref(ImageId)
    ltd.InstanceMarketOptions = InstanceMarketOptions(
        MarketType=If("UseSpotInstance", "spot", Ref("AWS::NoValue")),
        SpotOptions=SpotOptions(MaxPrice=If("UseSpotInstance", Ref(SpotPrice), Ref("AWS::NoValue"))))
    ltd.InstanceType = Ref(InstanceType)
    ltd.NetworkInterfaces = [NetworkInterfaces(
        InterfaceType=If("UseEFA", "efa", Ref("AWS::NoValue")),
        DeleteOnTermination=True,
        DeviceIndex=0,
        Groups=Ref(SecurityGroupId)
    )]
    ltd.UserData = Base64(Sub(UserData))
    ltd.BlockDeviceMappings = [
        BlockDeviceMapping(
            DeviceName=If("UseAmazonLinux", "/dev/xvda", "/dev/sda1"),
            Ebs=EBSBlockDevice(
                VolumeSize=Ref(RootSize),
                VolumeType="gp2",
                DeleteOnTermination=True
        )),
        If("UseScratchDisk", BlockDeviceMapping(
            DeviceName="/dev/xvdbx",
            Ebs=EBSBlockDevice(
                VolumeSize=Ref(ScratchSize),
                VolumeType=If("UseProvisionedIo", "gp2", "io1"),
                Iops=If("UseProvisionedIo", Ref(VolumeTypeIops),  Ref("AWS::NoValue")),
                DeleteOnTermination=True
        )), Ref("AWS::NoValue"))]
    ## End LaunchTemplateData

    ## Begin Launch Template Resource
    lt = LaunchTemplate("NodeLaunchTemplate")
    lt.LaunchTemplateName = Sub("${ClusterId}-${JobId}")
    lt.LaunchTemplateData = ltd
    t.add_resource(lt)
    ## End Launch Template Resource

    ## Begin AutoScalingGroup Resource
    asg = AutoScalingGroup("AutoScalingComputeGroup")
    asg.DependsOn = "NodeLaunchTemplate"
    asg.LaunchTemplate = LaunchTemplateSpecification(
        LaunchTemplateId=Ref(lt),
        Version=GetAtt(lt, "LatestVersionNumber"))
    asg.MinSize = Ref(DesiredCapacity)
    asg.MaxSize = Ref(DesiredCapacity)
    asg.VPCZoneIdentifier = Ref(SubnetId)
    asg.PlacementGroup = If("UsePlacementGroup", Ref(pg), Ref("AWS::NoValue"))
    asg.Tags = Tags(
        Name={"Fn::Sub": "${ClusterId}-compute-job-${JobId}"},
        _soca_JobId=Ref(JobId),
        _soca_JobName=Ref(JobName),
        _soca_JobQueue=Ref(JobQueue),
        _soca_StackId={"Fn::Sub": "${AWS::StackName}"},
        _soca_JobOwner=Ref(JobOwner),
        _soca_JobProject=Ref(JobProject),
        _soca_KeepForever=Ref(KeepForever),
        _soca_ClusterId=Ref(ClusterId),
        _soca_Node_Type="soca-compute-node")
    t.add_resource(asg)
    ## End AutoScalingGroup Resource

    # Tags must use 'soca:<Key>' syntax
    template_output = t.to_yaml().replace('_soca_', 'soca:')

    return template_output
