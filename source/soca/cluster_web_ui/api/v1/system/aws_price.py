from flask_restful import Resource, reqparse
import logging
import boto3
import ast
import re
import math
logger = logging.getLogger("soca_api")


def get_compute_pricing(client_pricing, ec2_instance_type):
    pricing = {}
    response = client_pricing.get_products(
        ServiceCode='AmazonEC2',
        Filters=[
            {
                'Type': 'TERM_MATCH',
                'Field': 'usageType',
                'Value': 'BoxUsage:' + ec2_instance_type
            },
        ],

    )
    for data in response['PriceList']:
        data = ast.literal_eval(data)
        for k, v in data['terms'].items():
            if k == 'OnDemand':
                for skus in v.keys():
                    for ratecode in v[skus]['priceDimensions'].keys():
                        instance_data = v[skus]['priceDimensions'][ratecode]
                        if 'on demand linux ' + str(ec2_instance_type) + ' instance hour' in instance_data['description'].lower():
                            pricing['ondemand'] = float(instance_data['pricePerUnit']['USD'])
            else:
                for skus in v.keys():
                    if v[skus]['termAttributes']['OfferingClass'] == 'standard' \
                            and v[skus]['termAttributes']['LeaseContractLength'] == '1yr' \
                            and v[skus]['termAttributes']['PurchaseOption'] == 'No Upfront':
                        for ratecode in v[skus]['priceDimensions'].keys():
                            instance_data = v[skus]['priceDimensions'][ratecode]
                            if 'Linux/UNIX (Amazon VPC)' in instance_data['description']:
                                pricing['reserved'] = float(instance_data['pricePerUnit']['USD'])

    return pricing


def compute(instance_type, wall_time, nodect):
    client_pricing = boto3.client("pricing", region_name="us-east-1")
    compute_data = {}

    if instance_type:
        compute_price = get_compute_pricing(client_pricing, instance_type)

    compute_data["on_demand_hourly_rate"] = "%.3f" % compute_price["ondemand"]
    compute_data["reserved_hourly_rate"] ="%.3f" % compute_price["reserved"]
    compute_data["nodes"] = nodect
    compute_data["wall_time"] = wall_time
    compute_data["instance_type"] = instance_type
    compute_data["estimated_on_demand_cost"] = "%.3f" % ((compute_price["ondemand"] * nodect) * (wall_time / 60))
    compute_data["estimated_reserved_cost"] = "%.3f" % ((compute_price["reserved"] * nodect) * (wall_time / 60))
    return compute_data

class AwsPrice(Resource):
    def get(self):
        """
        Return RI/OD price based on compute/storage inputs
        ---
        tags:
          - AWS
        responses:
          200:
            description: Pair of user/token is valid
          203:
            description: Invalid user/token pair
          400:
            description: Malformed client input
        """
        parser = reqparse.RequestParser()
        parser.add_argument('instance_type', type=str, location='args')
        parser.add_argument('wall_time', type=int, location='args', help="Please specify wall_time in minutes", default=60)
        parser.add_argument('cpus', type=int, location='args', help="Please specify how many cpus you want to allocate")
        parser.add_argument('ebs_storage', type=int, location='args', help="Please specify ebs_storage in GB", default=0)
        parser.add_argument('fsx_storage', type=int, location='args', help="Please specify fsx_storage in GB", default=0)
        parser.add_argument('fsx_type', type=str, location='args', default="SCRATCH_2")
        args = parser.parse_args()
        instance_type = args['instance_type']
        wall_time = args['wall_time']
        ebs_storage = args['ebs_storage']
        fsx_storage = args['fsx_storage']
        fsx_type = args['fsx_type']
        cpus = args['cpus']
        sim_cost = {}
        ebs_gp2_storage_baseline = 0.1  # 0.1 cts per gb per month
        fsx_storage_baseline = 0.14 #   Persistent (50 MB/s/TiB baseline, up to 1.3 GB/s/TiB burst)  Scratch (200 MB/s/TiB baseline, up to 1.3 GB/s/TiB burst)


        if cpus is None:
            nodect = 1
        else:
            cpus_count_pattern = re.search(r'[.](\d+)', instance_type)
            if cpus_count_pattern:
                cpu_per_system = int(cpus_count_pattern.group(1)) * 2
            else:
                cpu_per_system = 2
            nodect = math.ceil(int(cpus) / cpu_per_system)


        if ebs_storage == 0:
            sim_cost["ebs_storage"] = 0
        else:
            # storage * ebs_price * sim_time_in_secds / (second_in_a_day * 30 days) * number of nodes
            sim_cost["ebs_storage"] = "%.3f" % ((ebs_storage * ebs_gp2_storage_baseline * (wall_time * 60) / (86400 * 30)) * nodect)

        if fsx_storage == 0:
            sim_cost["fsx_storage"] = 0
        else:
            # storage * ebs_price * sim_time_in_secds / (second_in_a_day * 30 days) * number of nodes
            sim_cost["fsx_storage"] = "%.3f" % ((fsx_storage * fsx_storage_baseline * (wall_time * 60) / (86400 * 30)) * nodect)

        try:
            sim_cost["compute"] = compute(instance_type, wall_time,nodect)
        except:
            sim_cost["compute"] = {"message": "Unable to get compute price. Please verify the input parameters (instance type may be incorrect?)"}
            return sim_cost, 500
        sim_cost["estimated_storage_cost"] = "%.3f" % (float(sim_cost["fsx_storage"]) + float(sim_cost["ebs_storage"]))
        sim_cost["estimated_total_cost"] = "%.3f" % (float(sim_cost["estimated_storage_cost"]) + float(sim_cost["compute"]["estimated_on_demand_cost"]))
        sim_cost["storage_pct"] = "%.3f" % (float(sim_cost["estimated_storage_cost"]) / float(sim_cost["estimated_total_cost"]) * 100)
        sim_cost["compute_pct"] = "%.3f" % (float(sim_cost["compute"]["estimated_on_demand_cost"]) / float(sim_cost["estimated_total_cost"]) * 100)
        sim_cost["compute"]["cpus"] = cpus
        return sim_cost


