x = {"message": {
        "timestamp": 1588099398,
        "pbs_version": "18.1.4",
        "pbs_server": "ip-180-0-2-229",
        "Jobs": {
            "6.ip-180-0-2-229": {
                "Job_Name": "test",
                "Job_Owner": "mickael@ip-180-0-2-229.ec2.internal",
                "job_state": "Q",
                "queue": "normal",
                "server": "ip-180-0-2-229",
                "Checkpoint": "u",
                "ctime": "Tue Apr 28 18:43:16 2020",
                "Error_Path": "ip-180-0-2-229.ec2.internal:/apps/soca/soca-t2a6/cluster_web_ui/test.e6",
                "Hold_Types": "n",
                "Join_Path": "n",
                "Keep_Files": "n",
                "Mail_Points": "a",
                "mtime": "Tue Apr 28 18:43:16 2020",
                "Output_Path": "ip-180-0-2-229.ec2.internal:/apps/soca/soca-t2a6/cluster_web_ui/test.o6",
                "Priority": 0,
                "qtime": "Tue Apr 28 18:43:16 2020",
                "Rerunable": "True",
                "Resource_List": {
                    "ncpus": 1,
                    "nodect": 1,
                    "place": "pack",
                    "select": "1:ncpus=1"
                },
                "schedselect": "1:ncpus=1:compute_node=tbd",
                "substate": 10,
                "Variable_List": {
                    "PBS_O_SYSTEM": "Linux",
                    "PBS_O_SHELL": "/bin/bash",
                    "PBS_O_HOME": "/data/home/mickael",
                    "PBS_O_LOGNAME": "mickael",
                    "PBS_O_WORKDIR": "/apps/soca/soca-t2a6/cluster_web_ui",
                    "PBS_O_LANG": "en_US.UTF-8",
                    "PBS_O_PATH": "/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/pbs/bin:/opt/pbs/sbin:/opt/pbs/bin:/apps/soca/soca-t2a6/python/latest/bin",
                    "PBS_O_MAIL": "/var/spool/mail/root",
                    "PBS_O_QUEUE": "normal",
                    "PBS_O_HOST": "ip-180-0-2-229.ec2.internal"
                },
                "euser": "mickael",
                "egroup": "mickael",
                "queue_rank": 1588099396652,
                "queue_type": "E",
                "comment": "Can Never Run: Insufficient amount of resource: compute_node (tbd != job5)",
                "etime": "Tue Apr 28 18:43:16 2020",
                "project": "_pbs_project_default"
            }
        }
    }}

print(list((x["message"]["Jobs"].keys())))