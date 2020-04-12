import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint, send_file
import errno
import math
import os
from datetime import datetime
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


def validate_path(path):
    # make sure user can't access files/folder they are not supposed to
    # Prevent user to access directory they are not supposed to
    for char in ["..", ".", "~", "#", "$", "!"]:
        if char in path.split('/'):
            return False

    if path.split('/')[0] != session["user"] or path.split("/")[-1] == "":
        return False

    return True


@my_files.route('/my_files', methods=['GET'])
@login_required
def index():
    path = request.args.get("path", None)
    folders = {}
    files = {}
    breadcrumb = {}
    if path is None:
        path = session["user"]

    if validate_path(path) is False:
        return redirect("/my_files")

    # Build Breadcrumb
    count = 1
    for level in path.split("/")[0:]:
        breadcrumb["/".join(path.split('/')[:count])] = level
        count += 1

    # Retrieve files/folders
    try:
        for entry in os.scandir(config.Config.USER_HOME + "/" + path):
            if entry.is_dir():
                if not entry.name.startswith("."):
                    folders[entry.name] = {"path": path+"/"+entry.name,
                                           "uid": encrypt(path+"/"+entry.name)["message"]}
            elif entry.is_file():
                if not entry.name.startswith("."):
                    files[entry.name] = {"uid": encrypt(path+"/"+entry.name)["message"],
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
                return send_file(config.Config.USER_HOME + "/" + file_info["file_path"],
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


@my_files.route('/my_files/upload', methods=['POST'])
@login_required
def upload():
    path = request.form["path"]
    file_list = request.files.getlist("file")
    if not file_list:
        return redirect("/my_files")
    for file in file_list:
        try:
            destination = config.Config.USER_HOME + "/" + path + file.filename
            file.save(destination)
        except Exception as err:
            print(err)
            return {"success": False, "message": str(err)}, 500

    return {"success": True, "message": "Uploaded."}, 200


@my_files.route('/my_files/create_folder', methods=['POST'])
@login_required
def create():
    if "folder_name" not in request.form.keys() or "path" not in request.form.keys():
        return redirect("/my_files")
    try:
        folder_name = request.form["folder_name"]
        folder_path = request.form["path"]
        print(folder_path.split("/"))

        folder_to_create = config.Config.USER_HOME + "/" + folder_path + folder_name
        access_right = 0o750
        os.makedirs(folder_to_create, access_right)
        flash(folder_path + folder_name + " created successfully.", "success")
    except OSError as err:
        if err.errno == errno.EEXIST:
            flash("This folder already exist, choose a different name", "error")
        else:
            flash("Unable to create: " + folder_path + folder_name + ". Error: " + str(err.errno), "error")
    except Exception as err:
        print(err)
        flash("Unable to create: " + folder_path + folder_name, "error")

    return redirect("/my_files?path="+folder_path)


@my_files.route('/my_files/delete', methods=['GET'])
@login_required
def delete():
    uid = request.args.get("uid", None)
    if uid is None:
        return redirect("/my_files")

    file_information = decrypt(uid)
    if file_information["success"] is True:
        file_info = json.loads(file_information["message"])
        current_user = session["user"]
        if current_user == file_info["file_owner"]:
            try:
                if os.path.isfile(config.Config.USER_HOME + "/" + file_info["file_path"]):
                    os.remove(config.Config.USER_HOME + "/"  + file_info["file_path"])
                    flash("File removed", "success")

                elif os.path.isdir(config.Config.USER_HOME + "/" + file_info["file_path"]):
                    files_in_folder = [f for f in os.listdir(config.Config.USER_HOME + "/" + file_info["file_path"]) if not f.startswith('.')]
                    if files_in_folder.__len__() == 0:
                        os.rmdir(config.Config.USER_HOME + "/" + file_info["file_path"])
                        flash("Folder removed", "success")
                    else:
                        flash("This folder is not empty.", "error")
                else:
                    pass

                return redirect("/my_files?path=" + "/".join(file_info["file_path"].split("/")[:-1]))

            except Exception as err:
                print(err)
                flash("Unable to download file. Did you remove it?", "error")
                return redirect("/my_files")

        else:
            flash("You do not have the permission to download this file", "error")
            return redirect("/my_files")

    else:
        flash("Unable to delete " + file_information["message"], "error")
        return redirect("/my_files")
