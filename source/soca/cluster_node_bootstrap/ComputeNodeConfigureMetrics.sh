#!/bin/bash -xe

# Make sure to update your ELK Access Policy if you do not use the default environment and have configured multiple NAT gateway


source /etc/environment
source /root/config.cfg
cd /root


if [[ $SOCA_SYSTEM_METRICS == "true" ]];
then
  echo "Installing and configuring MetricBeat"
  wget $METRICBEAT_URL
  if [[ $(md5sum $METRICBEAST_RPM | awk '{print $1}') != $METRICBEAT_HASH ]];  then
    echo -e "FATAL ERROR: Checksum for metricbeat failed. File may be compromised."
    exit 1
  fi

  sudo rpm -vi $METRICBEAST_RPM
  METRICBEAT=$(which metricbeat)

  # Copy conf
  cp /apps/soca/$SOCA_CONFIGURATION/cluster_analytics/metricbeat/system.yml /etc/metricbeat/modules.d/

  # Enable AWS module (only if using commercial binary)
  # $METRICBEAT module enable aws
  # Start MetricBeat in background
  $METRICBEAT run -E "setup.kibana.host='https://$SOCA_ESDOMAIN_ENDPOINT:443/_plugin/kibana'" \
      -E "output.elasticsearch.hosts=['https://$SOCA_ESDOMAIN_ENDPOINT:443']" \
      -E "setup.ilm.enabled='false'" \
      -E "fields.job_id='$SOCA_JOB_ID'" \
      -E "fields.job_owner='$SOCA_JOB_OWNER'" \
      -E "fields.job_name='$SOCA_JOB_NAME'" \
      -E "fields.job_project='$SOCA_JOB_PROJECT'" \
      -E "fields.job_queue='$SOCA_JOB_QUEUE'" &

else
  echo "MetricBeat disabled for this run "
fi