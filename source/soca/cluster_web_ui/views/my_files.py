import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint, send_file
from requests import post, get
import math
import os
from datetime import datetime
import base64
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
import json


logger = logging.getLogger(__name__)
my_files = Blueprint('my_files', __name__, template_folder='templates')


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def encrypt(file_path):
    ## handle file with space
    try:
        key = config.Config.SOCA_DATA_SHARING_SYMMETRIC_KEY
        cipher_suite = Fernet(key)
        payload = {"file_owner": session["user"],
                   "file_path": file_path}

        encrypted_text = cipher_suite.encrypt(json.dumps(payload).encode("utf-8"))
        return {"success": True, "message": encrypted_text.decode()}
    except Exception as err:
        return {"success": False, "message": "UNABLE_TO_GENERATE_TOKEN"}


def decrypt(encrypted_text):
    try:
        key = config.Config.SOCA_DATA_SHARING_SYMMETRIC_KEY
        cipher_suite = Fernet(key)
        decrypted_text = cipher_suite.decrypt(encrypted_text.encode())
        return {"success": True, "message": decrypted_text}
    except InvalidToken:
        return {"success": False, "message": "Invalid Token"}
    except InvalidSignature:
        return {"success": False, "message": "Invalid Signature"}
    except Exception as err:
        return {"success": False, "message": str(err)}


@my_files.route('/my_files', methods=['GET'])
@login_required
def index():
    path = request.args.get("path", None)
    home_location = config.Config.USER_HOME + "/"
    home_location = "/Users/"
    folders = {}
    files = {}
    breadcrumb = {}
    if path is None:
        path = session["user"]

    # Prevent user to access directory they are not supposed to
    if path.split('/')[0] != session["user"]:
        return redirect("/my_files")

    # Build Breadcrumb
    count = 1
    for level in path.split("/")[0:]:
        breadcrumb[level] = "/".join(path.split('/')[:count])
        count += 1

    # Retrieve files/folders
    try:
        for entry in os.scandir(home_location + path):
            if entry.is_dir():
                folders[entry.name] = path+"/"+entry.name
            elif entry.is_file():
                files[entry.name] = {"uid": encrypt(home_location +"/"+path+"/"+entry.name)["message"],
                                     "st_size": convert_size(entry.stat().st_size),
                                     "st_mtime": datetime.utcfromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
            else:
                pass
    except Exception as err:
        flash("Could not locate the directory", "error")
        return redirect("/my_files")

    return render_template('my_files.html', user=session["user"],
                           files=files,
                           folders=folders,
                           breadcrumb=breadcrumb,
                           path=path+"/")


@my_files.route('/my_files/download', methods=['GET'])
@login_required
def download():
    uid = request.args.get("uid", None)
    if uid is None:
        return redirect("/my_files")

    file_information = decrypt(uid)
    if file_information["success"] is True:
        file_info = json.loads(file_information["message"])
        current_user = session["user"]
        if current_user == file_info["file_owner"]:
            try:
                return send_file(file_info["file_path"],
                             as_attachment=True,
                             attachment_filename=file_info["file_path"].split("/")[-1])
            except Exception as err:
                flash("Unable to download file. Did you remove it?", "error")
                return redirect("/my_files")
        else:
            flash("You do not have the permission to download this file", "error")
            return redirect("/my_files")

    else:
        flash("Unable to download " + file_information["message"], "error")
        return redirect("/my_files")

@my_files.route('/my_files/delete', methods=['GET'])
@login_required
def delete():
    uid = request.args.get("uid", None)
    if uid is None:
        return redirect("/my_files")

    home_location = config.Config.USER_HOME + "/"
    home_location = "/Users/"
    file_information = decrypt(uid)
    if file_information["success"] is True:
        file_info = json.loads(file_information["message"])
        current_user = session["user"]
        if current_user == file_info["file_owner"]:
            try:
                file_to_delete = file_info["file_path"]
                path_location = file_info["file_path"].split("/")[-3:-1]  # remove the Home Location and file name
                os.remove(file_to_delete)
                flash(file_info["file_path"].split("/")[-1] + " removed from the filesystem", "success")
                return redirect("/my_files?path=" + "/".join(path_location))

            except Exception as err:
                flash("Unable to download file. Did you remove it?", "error")

        else:
            flash("You do not have the permission to download this file", "error")
            return redirect("/my_files")

    else:
        flash("Unable to download " + file_information["message"], "error")
        return redirect("/my_files")


@my_files.route('/my_files/upload', methods=['POST'])
@login_required
def upload():
    path = request.form["path"]
    file_list = request.files.getlist("file")
    if not file_list:
        return redirect("/my_files")
    for file in file_list:
        destination = config.Config.USER_HOME + "/" + path
        destination = "/Users" + "/" + path + file.filename
        file.save(destination)

    return "Success", 200