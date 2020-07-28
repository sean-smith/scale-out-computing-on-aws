import boto3
import logging
logger = logging.getLogger("api_log")

client_ec2 = boto3.client("ec2")
client_ssm = boto3.client("ssm")
def clean_tmp_folders():# need to run ssm
    # $scanresults = Invoke-Expression "& 'C:\Program Files\NICE\DCV\Server\bin\dcv' list-sessions"

