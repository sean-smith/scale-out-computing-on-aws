#!/usr/bin/bash

# This script create a test user, provision 2d & 3d hosts and submit a test job

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

. /etc/environment
USER='testuser'
PASSWORD='testpasswd'

echo " "
echo "Creating a new LDAP user ($USER/$PASSWORD)"
echo " "
python3 /apps/soca/cluster_manager/ldap_manager.py -u $USER -p $PASSWORD

# Launch new DCV 2D
echo " "
echo "Launching 2D DCV host ... "
echo " "
python3 /apps/soca/cluster_manager/add_nodes.py --instance_type=c5.large --queue=desktop2d --job_owner=root --job_name=testdesktop2d --desired_capacity 1 --keep_forever

# Launch new DCV 3D
echo " "
echo "Launching 3D DCV host ... "
echo " "
python3 /apps/soca/cluster_manager/add_nodes.py --instance_type=g3.4xlarge --queue=desktop3d --job_owner=root --job_name=testdesktop3d --desired_capacity 1 --keep_forever


# Test job
echo " "
echo "Submit test job for $USER, output will be located at /data/home/$USER"
echo " "

cd /data/home/$USER
su $USER -c "qsub -- /bin/echo HelloWorld"