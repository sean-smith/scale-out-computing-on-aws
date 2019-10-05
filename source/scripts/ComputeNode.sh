#!/bin/bash -xe

source /etc/environment
source /root/config.cfg

if [ $# -lt 4 ]
  then
    exit 0
fi

BUCKET=$1
EFS_DATA=$2
EFS_APPS=$3
SCHEDULER_HOSTNAME=$4

# Mount EFS
mkdir /data
mkdir /apps

echo "$EFS_DATA:/ /data/ nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 0 0" >> /etc/fstab
echo "$EFS_APPS:/ /apps nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 0 0" >> /etc/fstab
mount -a

# Configure Scratch Directory if needed
if [ $SOCA_SCRATCH_SIZE -ne 0 ];
then
    mkdir /scratch/
    check_storage=`lsblk | grep disk | tail -n 1 | awk '{print $1'}`
    if [$check_storage == 'xvda'];
    then
        echo "Non NVME driver, device mapping is xvdbx"
        DEVICE_NAME="/dev/xvdbx"

    else
        echo "NVME driver, device mapping is nvme1n1"
        DEVICE_NAME="/dev/nvme1n1"
    fi

    echo "$DEVICE_NAME /scratch ext4 defaults 0 0" >> /etc/fstab
    mkfs -t ext4 $DEVICE_NAME
    mount -t ext4 $DEVICE_NAME /scratch
    chmod 777 /scratch/
fi




# Prepare PBS/System
cd ~

# Install System required libraries

if [[ $SOCA_BASE_OS = "rhel7" ]]
then
    yum install -y $(echo ${SYSTEM_PKGS[*]}) --enablerepo rhui-REGION-rhel-server-optional
    yum install -y $(echo ${SCHEDULER_PKGS[*]}) --enablerepo rhui-REGION-rhel-server-optional
else
    yum install -y $(echo ${SYSTEM_PKGS[*]})
    yum install -y $(echo ${SCHEDULER_PKGS[*]})
fi

yum install -y $(echo ${OPENLDAP_SERVER_PKGS[*]})
yum install -y $(echo ${SSSD_PKGS[*]})

# Install PBSPro
cd ~
wget $PBSPRO_URL
if [[ $(md5sum $PBSPRO_TGZ | awk '{print $1}') != $PBSPRO_HASH ]];  then
    echo -e "FATAL ERROR: Checksum for PBSPro failed. File may be compromised." > /etc/motd
    exit 1
fi
tar zxvf $PBSPRO_TGZ
cd pbspro-$PBSPRO_VERSION
./autogen.sh
./configure --prefix=/opt/pbs
make -j6
make install -j6
/opt/pbs/libexec/pbs_postinstall
chmod 4755 /opt/pbs/sbin/pbs_iff /opt/pbs/sbin/pbs_rcp

# Edit path with new scheduler/python locations
echo "export PATH=\"/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/pbs/bin:/opt/pbs/sbin:/opt/pbs/bin:/apps/python/latest/bin\" " >> /etc/environment

systemctl enable pbs
systemctl start pbs

# Disable SELINUX
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

# Configure Host
SERVER_IP=$(hostname -I)
SERVER_HOSTNAME=$(hostname)
SERVER_HOSTNAME_ALT=$(echo $SERVER_HOSTNAME | cut -d. -f1)
echo $SERVER_IP $SERVER_HOSTNAME $SERVER_HOSTNAME_ALT >> /etc/hosts


# Configure Ldap
echo "URI ldap://$SCHEDULER_HOSTNAME" >> /etc/openldap/ldap.conf
echo "BASE $LDAP_BASE" >> /etc/openldap/ldap.conf

echo -e "[domain/default]
enumerate = True
autofs_provider = ldap
cache_credentials = True
ldap_search_base = $LDAP_BASE
id_provider = ldap
auth_provider = ldap
chpass_provider = ldap
sudo_provider = ldap
ldap_sudo_search_base = ou=Sudoers,$LDAP_BASE
ldap_uri = ldap://$SCHEDULER_HOSTNAME
ldap_id_use_start_tls = True
use_fully_qualified_names = False
ldap_tls_cacertdir = /etc/openldap/cacerts

[sssd]
services = nss, pam, autofs, sudo
full_name_format = %2\$s\%1\$s
domains = default

[nss]
homedir_substring = /data/home

[pam]

[sudo]
ldap_sudo_full_refresh_interval=86400
ldap_sudo_smart_refresh_interval=3600

[autofs]

[ssh]

[pac]

[ifp]

[secrets]" > /etc/sssd/sssd.conf


chmod 600 /etc/sssd/sssd.conf
systemctl enable sssd
systemctl restart sssd

echo | openssl s_client -connect $SCHEDULER_HOSTNAME:389 -starttls ldap > /root/open_ssl_ldap
mkdir /etc/openldap/cacerts/
cat /root/open_ssl_ldap | openssl x509 > /etc/openldap/cacerts/openldap-server.pem

authconfig --disablesssd --disablesssdauth --disableldap --disableldapauth --disablekrb5 --disablekrb5kdcdns --disablekrb5realmdns --disablewinbind --disablewinbindauth --disablewinbindkrb5 --disableldaptls --disablerfc2307bis --updateall
sss_cache -E
authconfig --enablesssd --enablesssdauth --enableldap --enableldaptls --enableldapauth --ldapserver=ldap://$SCHEDULER_HOSTNAME --ldapbasedn=$LDAP_BASE --enablelocauthorize --enablemkhomedir --enablecachecreds --updateall

echo "sudoers: files sss" >> /etc/nsswitch.conf

# Install SSM
yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
systemctl enable amazon-ssm-agent
systemctl restart amazon-ssm-agent

# Disable SELINUX & firewalld
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

systemctl stop firewalld
systemctl disable firewalld

# Disable StrictHostKeyChecking
echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config
echo "UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

# Configure PBS
cp /etc/pbs.conf /etc/pbs.conf.orig
echo -e "
PBS_SERVER=$SCHEDULER_HOSTNAME
PBS_START_SERVER=0
PBS_START_SCHED=0
PBS_START_COMM=0
PBS_START_MOM=1
PBS_EXEC=/opt/pbs
PBS_HOME=/var/spool/pbs
PBS_CORE_LIMIT=unlimited
PBS_SCP=/usr/bin/scp
" > /etc/pbs.conf

cp /var/spool/pbs/mom_priv/config /var/spool/pbs/mom_priv/config.orig
echo -e "
\$clienthost $SCHEDULER_HOSTNAME
"  > /var/spool/pbs/mom_priv/config

systemctl enable pbs

INSTANCE_TYPE=`curl --silent  http://169.254.169.254/latest/meta-data/instance-type | cut -d. -f1`

# If GPU instance, disable NOUVEAU drivers before installing DCV as this require a reboot
# Rest of the DCV configuration is managed by ComputeNodeInstallDCV.sh
if [[ "$INSTANCE_TYPE" == "g2" || "$INSTANCE_TYPE" == "g3" ]]
then
    cat << EOF | sudo tee --append /etc/modprobe.d/blacklist.conf
blacklist vga16fb
blacklist nouveau
blacklist rivafb
blacklist nvidiafb
blacklist rivatv
EOF
    echo GRUB_CMDLINE_LINUX="rdblacklist=nouveau" >> /etc/default/grub
    sudo grub2-mkconfig -o /boot/grub2/grub.cfg
fi

# Reboot to disable SELINUX
sudo reboot
# Upon reboot, ComputenodePostinstall will be executed