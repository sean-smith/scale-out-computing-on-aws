#!/bin/bash

# If Viperlight is not installed on your system:
# > wget https://s3.amazonaws.com/viperlight-scanner/latest/viperlight.zip
# > unzip viperlight.zip
# > ./install.sh (require npm)
# > also install https://github.com/PyCQA/bandit (pip install bandit)

# If CFN_NAG_SCAN is not installed on your system
# > https://github.com/stelligent/cfn_nag
#


# Validate CloudFormation templates
sudo gem install cfn-nag
CFN_NAG_SCAN=$(which cfn_nag_scan)
CWD=$(dirname "${BASH_SOURCE[0]}")
VIPERLIGHT=$(which viperlight)

# Validate Docs and codebase
cd $CWD/../
viperlight scan
$CFN_NAG_SCAN  -i $CWD/../source/solution-for-scale-out-computing-on-aws.template --fail-on-warnings
for template in $(ls $CWD/../source/templates);
    do
       $CFN_NAG_SCAN  -i $CWD/../source/templates/$template --fail-on-warnings || ec2=$?
done

# Dead Links checkers. Mkdocs must be up and running
MKDOCS_URL="http://127.0.0.1:8000"
blc $MKDOCS_URL -ro

