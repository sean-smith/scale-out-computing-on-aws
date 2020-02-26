#!/bin/bash -xe

source /etc/environment
source /apps/soca/$SOCA_CONFIGURATION/cluster_node_boostrap/config.cfg

# First flush the current crontab to prevent this script to run on the next reboot
crontab -r

# Copy  Aligo scripts file structure
AWS=$(which aws)
# Retrieve SOCA configuration under soca.tar.gz and extract it on /apps/

# Generate default queue_mapping file based on default AMI choosen by customer




## Update PBS Hooks with the current script location


# Reload config
systemctl restart pbs


# Install OpenMPI
# This will take a while and is not system blocking, so adding at the end of the install process
mkdir -p /apps/soca/$SOCA_CONFIGURATION/openmpi/installer
cd /apps/soca/$SOCA_CONFIGURATION/openmpi/installer

wget $OPENMPI_URL
if [[ $(md5sum $OPENMPI_TGZ | awk '{print $1}') != $OPENMPI_HASH ]];  then
    echo -e "FATAL ERROR: Checksum for OpenMPI failed. File may be compromised." > /etc/motd
    exit 1
fi

tar xvf $OPENMPI_TGZ
cd openmpi-$OPENMPI_VERSION
./configure --prefix=/apps/soca/$SOCA_CONFIGURATION/openmpi/$OPENMPI_VERSION
make
make install
