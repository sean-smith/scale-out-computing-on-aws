import config
import subprocess
from flask_restful import Resource, reqparse
import logging
from decorators import admin_only
import shlex
logger = logging.getLogger("soca_api")


class Queues(Resource):
    @admin_only
    def post(self):
        """
        Create a new queue
        ---
        tags:
          - Scheduler
        responses:
          200:
            description: List of queue
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('type', type=str, location='form')
        parser.add_argument('name', type=str, location='form')
        args = parser.parse_args()
        queue_type = args['type']
        queue_name = args['name']
        QUEUE_TYPE = ["ondemand", "alwayson"]
        if queue_name is None:
            return {"success": False, "message": "name (str) is required parameter"}, 400

        if queue_type not in QUEUE_TYPE:
            return {"success": False, "message": "Invalid queue type, must be alwayson or ondemand"}, 400

        try:
            commands_ondemand = ["create queue " + queue_name,
                                 "set queue " + queue_name + " queue_type = Execution",
                                 "set queue " + queue_name + " default_chunk.compute_node = tbd",
                                 "set queue " + queue_name + " enabled = True",
                                 "set queue " + queue_name + " enabled = True"]

            commands_alwayson = ["create queue " + queue_name,
                                 "set queue " + queue_name + " queue_type = Execution",
                                 "set queue " + queue_name + " enabled = True",
                                 "set queue " + queue_name + " enabled = True"]

            if queue_type == "ondemand":
                for command in commands_ondemand:
                    try:
                        subprocess.Popen(shlex.split(config.Config.PBS_QMGR + ' -c "' + command + '"'))
                    except Exception as err:
                        return {"success": False, "message": "Error with " + command + " Trace: " + str(err)}, 500
            else:
                for command in commands_alwayson:
                    try:
                        subprocess.Popen(shlex.split(config.Config.PBS_QMGR + ' -c "' + command + '"'))
                    except Exception as err:
                        return {"success": False, "message": "Error with " + command + " Trace: " + str(err)}, 500

            return {"success": True, "message": "d"}, 200
        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    @admin_only
    def delete(self):
        """
        Delete a queue
        ---
        tags:
          - Scheduler
        responses:
          200:
            description: List of queue
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, location='form')
        args = parser.parse_args()
        queue_name = args['name']
        if queue_name is None:
            return {"success": False, "message": "name (str) is required parameter"}, 400

        try:
            delete_queue = subprocess.Popen(shlex.split(config.Config.PBS_QMGR + ' -c "delete queue ' + queue_name + '"'))
            return {"success": True, "message": "Queue deleted"}, 200
        except Exception as err:
            return {"success": False, "message": "Unable to delete queue: " + str(err) + ". Trace: " + str(delete_queue)}, 200
