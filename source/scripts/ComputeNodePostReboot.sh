#!/bin/bash -xe

source /etc/environment
source /root/config.cfg
AWS=$(which aws)
echo "BEGIN"  >> /root/ComputeNodeUserCustomization.log 2>&1

# Make sure system is clean and PBS is stopped
crontab -r
systemctl stop pbs

# Begin USER Customization
$AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/ComputeNodeUserCustomization.sh /root/
/bin/bash /root/ComputeNodeUserCustomization.sh >> /root/ComputeNodeUserCustomization.log 2>&1
rm /root/ComputeNodeUserCustomization.sh
# End USER Customization

# Begin DCV Customization
if [ "$SOCA_JOB_QUEUE" == "desktop" ]; then
    echo "Installing DCV"
    $AWS s3 cp s3://$SOCA_INSTALL_BUCKET/$SOCA_INSTALL_BUCKET_FOLDER/scripts/ComputeNodeInstallDCV.sh /root/
    /bin/bash /root/ComputeNodeInstallDCV.sh >> /root/ComputeNodeInstallDCV.log 2>&1
    rm /root/ComputeNodeInstallDCV.sh
    sleep 30
fi
# End DCV Customization

# Begin EFA Customization
if [ $SOCA_JOB_EFA == "true" ]; then
    echo "Installing EFA"
    cd /root/
    curl --silent -O $EFA_URL
    if [[ $(md5sum $EFA_TGZ | awk '{print $1}') != $EFA_HASH ]];  then
        echo -e "FATAL ERROR: Checksum for EFA failed. File may be compromised." > /etc/motd
        exit 1
    fi
    tar -xf $EFA_TGZ
    cd aws-efa-installer
    /bin/bash efa_installer.sh -y
fi
# End EFA customization

# Post-Boot routine completed, starting PBS
systemctl start pbs
echo -e "
Compute Node Ready for queue: $SOCA_JOB_QUEUE
" > /etc/motd