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
logger = logging.getLogger("soca_api")


class Job(Resource):
    def get(self):
        """
        Get info for a job
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
        parser.add_argument('job_id', type=str, location='args')
        args = parser.parse_args()
        job_id = args['job_id']

        try:
            qstat_command = config.Config.PBS_QSTAT + " -f " + job_id + " -Fjson"
            try:
                get_job_info = subprocess.check_output(shlex.split(qstat_command))
                try:
                    job_info = json.loads(((get_job_info.decode('utf-8')).rstrip().lstrip()))
                except Exception as err:
                    return {"success": False, "message": "Unable to retrieve this job. Job may have terminated."}, 500

                return {"success": True, "message": job_info}, 200
            except Exception as err:
                return {"succes": False, "message": "Unable to retrieve Job ID (job may have terminated and is no longer in the queue)"}, 500

        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    @private_api
    def post(self):
        """
        Submit a job
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
        parser.add_argument('payload', type=str, location='form')
        args = parser.parse_args()
        try:
            payload = base64.b64decode(args['payload']).decode()
        except KeyError:
            return {"succes": False, "message": "payload (str) parameter is required"}, 500
        except UnicodeError:
            return {"succes": False, "message": "payload (str) does not seems to be a valid base64"}, 500
        except Exception as err:
            return {"succes": False, "message": "Unknown error: " + str(err)}, 500

        try:
            qsub_script = """<<EOF
            """ + payload + """
            EOF
            """

            request_user = request.headers.get("X-SOCA-USER")
            if request_user is None:
                return {"succes": False, "message": "Unable to retrieve request owner. X-SOCA-USER must be set"}, 500

            submit_job_command = config.Config.PBS_QSUB + " " + qsub_script
            try:
                launch_job = subprocess.check_output(['su', request_user, '-c', submit_job_command], stderr=subprocess.PIPE)
                job_id = ((launch_job.decode('utf-8')).rstrip().lstrip()).split('.')[0]
                return {"success": True, "message": str(job_id)}, 200
            except subprocess.CalledProcessError as e:
                return {"succes": False,
                        "message": {
                            "error": "Unable to submit the job. Your job script is invalid (eg: malformed, syntax error...)",
                            "stderr": '{}'.format(e.stderr.decode(sys.getfilesystemencoding())),
                            "stdout": '{}'.format(e.output.decode(sys.getfilesystemencoding())),
                            "job_script": str(payload)}
                        }, 500

            except Exception as err:
                return {"succes": False, "message": {"error": "Unable to run Qsub command.",
                                                     "trace": err,
                                                     "job_script": str(payload)}}, 500


        except Exception as err:
            return {"success": False, "message": "Unknown error: " + str(err)}, 500

    @private_api
    def delete(self):
        """
       Delete a job
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
            job_id_key = list(job_info["Jobs"].keys())
            job_owner = job_info["Jobs"][job_id_key[0]]["Job_Owner"].split("@")[0]
            request_user = request.headers.get("X-SOCA-USER")
            if request_user is None:
                return {"succes": False, "message": "Unable to retrieve request owner. X-SOCA-USER must be set"}, 500
            if request_user != job_owner:
                return {"succes": False, "message": "This job does not seems to be owned by you"}, 500
            try:
                qdel_command = config.Config.PBS_QDEL + " " + job_id
                try:
                    delete_job = subprocess.check_output(shlex.split(qdel_command))
                    return {"success": True, "message": "Job deleted"}
                except Exception as err:
                    return {"succes": False, "message": "Unable to execute qsub command: " + str(err)}, 500

            except Exception as err:
                return {"success": False, "message": "Unknown error: " + str(err)}, 500
