#!/bin/bash

# If Viperlight is not installed on your system:
# > wget https://s3.amazonaws.com/viperlight-scanner/latest/viperlight.zip
# > unzip viperlight.zip
# > ./install.sh (require npm)
# > also install https://github.com/PyCQA/bandit (pip install bandit)

# If CFN_NAG_SCAN is not installed on your system
# > https://github.com/stelligent/cfn_nag
#

CFN_NAG_SCAN=$(which cfn_nag_scan)
CWD=$(dirname "${BASH_SOURCE[0]}")
VIPERLIGHT=$(which viperlight)

cd $CWD/../
viperlight scan
$CFN_NAG_SCAN  -i $CWD/../source/solution-for-scale-out-computing-on-aws.template --fail-on-warnings
for template in $(ls $CWD/../source/templates);
    do
       $CFN_NAG_SCAN  -i $CWD/../source/templates/$template --fail-on-warnings
done





