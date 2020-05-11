from flask_restful import Resource, reqparse
import logging
import boto3
import ast
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
        client_pricing = boto3.client("pricing", region_name="us-east-1")
        parser = reqparse.RequestParser()
        parser.add_argument('file', type=str, location='args')
        parser.add_argument('wall_time', type=int, location='args')
        parser.add_argument('node_count', type=int, location='args')
        parser.add_argument('storage', type=int, location='args')
        args = parser.parse_args()
        instance_type = str(args['instance_type'])
        wall_time = args['wall_time']
        storage = args['storage']
        node_count = args['node_count']
        if instance_type is None:
            return {"success": False,
                    "message": "instance_type (str) parameter is required"}, 400

        if wall_time is None:
            wall_time = 60  # default per hour
        else:
            if not isinstance(wall_time, int) or wall_time < 0:
                return {"success": False,
                        "message": "wall_time (int) must be an integer greated than 0"}, 400
        if node_count is None:
            node_count = 1  # default to 1
        else:
            if not isinstance(node_count, int) or wall_time < 1:
                return {"success": False,
                        "message": "node_count (int) must be an integer greated than 1"}, 400

        if storage is None:
            storage = 0
        else:
            if not isinstance(storage, int) or storage < 0:
                return {"success": False,
                        "message": "storage (int) must be an integer greated than 0"}, 400

        # Calculate estimated compute price
        compute_price = get_compute_pricing(client_pricing, instance_type)
        if not compute_price:
            return {"success": False,
                    "message": "Unable to compute price for " + str(instance_type + ". Is that a valid instance type?")}, 400

