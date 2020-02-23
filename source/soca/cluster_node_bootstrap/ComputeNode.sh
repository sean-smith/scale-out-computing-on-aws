#!/bin/bash -xe

if [ $# -lt 1 ]
  then
    exit 0
fi

set -a
source /etc/environment
source /apps/soca/$SOCA_CONFIGURATION/cluster_node_boostrap/config.cfg
set +a
export SCHEDULER_HOSTNAME=$1

# chdir to ansible folder and start init playbook
cd /apps/soca/$SOCA_CONFIGURATION/cluster_node_boostrap/ansible/
ANSIBLE_PLAYBOOK=$(which ansible-playbook)
$ANSIBLE_PLAYBOOK -i localhost compute_host_setup.yml





