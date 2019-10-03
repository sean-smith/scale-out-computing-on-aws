#!/bin/bash -xe

cd /root/
curl --silent -O https://s3-us-west-2.amazonaws.com/aws-efa-installer/aws-efa-installer-1.5.4.tar.gz
tar -xf aws-efa-installer-1.5.4.tar.gz
cd aws-efa-installer
./efa_installer.sh -y