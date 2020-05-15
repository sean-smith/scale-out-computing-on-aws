import config
import subprocess
from flask import request
from flask_restful import Resource, reqparse
import logging
import base64
from decorators import private_api
from requests import get
import json
import shlex
import sys
import errors
import os
import uuid
import re
import random
import string

logger = logging.getLogger("soca_api")


class Job(Resource):
    @private_api
    def get(self):
        """
        Return information for a given job
        ---
        tags:
          - Scheduler
        parameters:
          - in: body
            name: body
            schema:
              optional:
                - job_id
              properties:
                job_id:
                   type: string
                   description: ID of the job
        responses:
          200:
            description: List of all jobs
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('job_id', type=str, location='args')
        args = parser.parse_args()
        job_id = args['job_id']
        if job_id is None:
            return errors.all_errors("CLIENT_MISSING_PARAMETER", "job_id (str) parameter is required")

        try:
            qstat_command = config.Config.PBS_QSTAT + " -f " + job_id + " -Fjson"
            try:
                get_job_info = subprocess.check_output(shlex.split(qstat_command))
                try:
                    job_info = json.loads(((get_job_info.decode('utf-8')).rstrip().lstrip()))
                except Exception as err:
                    return {"success": False, "message": "Unable to retrieve this job. Job may have terminated."}, 210

                job_key = list(job_info["Jobs"].keys())[0]
                return {"success": True, "message": job_info["Jobs"][job_key]}, 200

            except Exception as err:
                return {"succes": False, "message": "Unable to retrieve Job ID (job may have terminated and is no longer in the queue)"}, 210

        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    @private_api
    def post(self):
        """
        Submit a job to the queue
        ---
        tags:
          - Scheduler
        parameters:
          - in: body
            name: body
            schema:
              required:
                - payload
              properties:
                payload:
                  type: string
                  description: Base 64 encoding of a job submission file
        responses:
          200:
            description: Job submitted correctly
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('payload', type=str, location='form')
        args = parser.parse_args()
        try:
            payload = base64.b64decode(args['payload']).decode()
        except KeyError:
            return errors.all_errors("CLIENT_MISSING_PARAMETER", "group (str) parameter is required")
        except UnicodeError:
            return errors.all_errors("UNICODE_ERROR", "payload (str) does not seems to be a valid base64")
        except Exception as err:
            return errors.all_errors(type(err).__name__, err)

        try:
            qsub_script = """<<EOF
            """ + payload + """
            EOF
            """

            request_user = request.headers.get("X-SOCA-USER")
            if request_user is None:
                return errors.all_errors("X-SOCA-USER_MISSING")

            # Basic Input verification
            check_job_name = re.search(r'#PBS -N (.+)', payload)
            if check_job_name:
                if " " in check_job_name:
                    return {"succes": False, "message": "Space are not authorized in job name"}, 500

                job_name = re.sub(r'\W+', '', check_job_name.group(1))
            else:
                job_name = ""

            submit_job_command = config.Config.PBS_QSUB + " " + qsub_script
            try:
                random_id = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(10))
                job_output_path = config.Config.USER_HOME + "/" + request_user + "/soca_job_output/" + job_name + "_" +str(random_id)
                os.makedirs(job_output_path)
                os.chdir(job_output_path)
                launch_job = subprocess.check_output(['su', request_user, '-c', submit_job_command], stderr=subprocess.PIPE)
                job_id = ((launch_job.decode('utf-8')).rstrip().lstrip()).split('.')[0]
                return {"success": True, "message": str(job_id)}, 200
            except subprocess.CalledProcessError as e:
                return {"succes": False,
                        "message": {
                            "error": "Unable to submit the job. Please verify your script file (eg: malformed inputs, syntax error, extra space in the PBS variables ...) or refer to the 'stderr' message.",
                            "stderr": '{}'.format(e.stderr.decode(sys.getfilesystemencoding())),
                            "stdout": '{}'.format(e.output.decode(sys.getfilesystemencoding())),
                            "job_script": str(payload)}
                        }, 500

            except Exception as err:
                return {"succes": False, "message": {"error": "Unable to run Qsub command.",
                                                     "trace": err,
                                                     "job_script": str(payload)}}, 500


        except Exception as err:
            return errors.all_errors(type(err).__name__, err)

    @private_api
    def delete(self):
        """
        Delete a job from the queue
        ---
        tags:
          - Scheduler
        parameters:
          - in: body
            name: body
            schema:
              required:
                - job_id
              properties:
                job_id:
                  type: string
                  description: ID of the job to remove
        responses:
          200:
            description: Job submitted correctly
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('job_id', type=str, location='args')
        args = parser.parse_args()
        job_id = args['job_id']

        get_job_info = get(config.Config.FLASK_ENDPOINT + "/api/scheduler/job",
                           headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                           params={"job_id": job_id},
                           verify=False)

        if get_job_info.status_code != 200:
            return {"success": False, "message": "Unable to retrieve this job. Job may have terminated"}, 500
        else:
            job_info = get_job_info.json()["message"]
            job_owner = job_info["Job_Owner"].split("@")[0]
            request_user = request.headers.get("X-SOCA-USER")
            if request_user is None:
                return errors.all_errors("X-SOCA-USER_MISSING")
            if request_user != job_owner:
                return errors.all_errors("CLIENT_NOT_OWNER")
            try:
                qdel_command = config.Config.PBS_QDEL + " " + job_id
                try:
                    delete_job = subprocess.check_output(shlex.split(qdel_command))
                    return {"success": True, "message": "Job deleted"}
                except Exception as err:
                    return {"succes": False, "message": "Unable to execute qsub command: " + str(err)}, 500

            except Exception as err:
                return {"success": False, "message": "Unknown error: " + str(err)}, 500
