import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint, send_file
import errno
import math
import os
from requests import get
from cryptography.fernet import Fernet, InvalidToken, InvalidSignature
import json
import pwd
from collections import OrderedDict
import subprocess
logger = logging.getLogger(__name__)
my_files = Blueprint('my_files', __name__, template_folder='templates')


def change_ownership(file_path):
    user_info = pwd.getpwnam(session["user"])
    uid = user_info.pw_uid
    gid = user_info.pw_gid
    os.chown(file_path, uid, gid)
    return {"success": True, "message": "Permission updated correctly"}


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


def demote(user_uid, user_gid):
    def set_ids():
        os.setgid(user_gid)
        os.setuid(user_uid)
    return set_ids


def user_has_permission(path, permission_required, type):
    if type not in ["file", "folder"]:
        print("Type must be file or folder")
        return False
    if permission_required not in ["create", "delete"]:
        print("permission_required must be create or delete")
        return False

    if type == "folder":
        if permission_required == "create":
            cmd = "mkdir " + path
        else:
            cmd = "rmdir " + path
    else:
        if permission_required == "create":
            cmd = "mkdir " + path
        else:
            cmd = "rm " + path

    user_uid = pwd.getpwnam(session["user"]).pw_uid
    user_gid = pwd.getpwnam(session["user"]).pw_gid
    print("Check permission for " + permission_required + " on " + path)
    try:
        process = subprocess.Popen(cmd.split(), preexec_fn=demote(user_uid, user_gid))
        print(process)
    except Exception as err:
        return (err)





def okuser_has_permission(path, permission_required, type):
    if type == "folder" and permission_required == "create":
        path = "/".join(path.split("/")[:-1])
    can_perform_action = True
    user_uid = pwd.getpwnam(session["user"]).pw_uid
    user_gid = pwd.getpwnam(session["user"]).pw_gid


    os.setuid(user_uid)
    os.setgid(user_gid)
    print("Check permission for " + permission_required + " on " + path)

    if permission_required in ["create", "delete"]:

        if os.access(path, os.W_OK) is False:
            can_perform_action = False
    elif permission_required == "read":
        if os.access(path, os.R_OK) is False:
            can_perform_action = False
    elif permission_required == "execute":
        if os.access(path, os.X_OK) is False:
            can_perform_action = False
    else:
        can_perform_action = False

    return can_perform_action


@my_files.route('/my_files', methods=['GET'])
@login_required
def index():
    path = request.args.get("path", None)
    filesystem = {}
    breadcrumb = {}
    if path is None:
        path = config.Config.USER_HOME.lower() + "/" + session["user"].lower()
    else:
        path = path.lower()

    if user_has_permission(path, "read", "folder") is False:
        if path == config.Config.USER_HOME.lower() + "/" + session["user"].lower():
            flash("We cannot access to your own home directory. Please ask a admin to rollback your folder ACLs to 750")
            return redirect("/")
        else:
            flash("You are not authorized to access this location.", "error")
            return redirect("/my_files")

    # Build breadcrumb
    count = 1
    for level in path.split("/"):
        if level == "":
            breadcrumb["/"] = "root"
        else:
            breadcrumb["/".join(path.split('/')[:count])] = level

        count += 1

    # Retrieve files/folders
    try:
        for entry in os.scandir(path):
            if not entry.name.startswith("."):
                filesystem[entry.name] = {"path": path + "/" + entry.name,
                                          "uid": encrypt(path + "/" + entry.name)["message"],
                                          "type": "folder" if entry.is_dir() else "file",
                                          "st_size": convert_size(entry.stat().st_size),
                                          "st_mtime": entry.stat().st_mtime}#datetime.utcfromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}

    except Exception as err:
        if err.errno == errno.EPERM:
            flash("Sorry we could not access this location due to a permission error", "error")
        elif err.errno == errno.ENOENT:
            flash("Could not locate the directory. Did you delete it ?", "error")
        else:
            flash("Could not locate the directory: " +str(err), "error")
        print(err)
        return redirect("/my_files")

    return render_template('my_files.html', user=session["user"],
                           filesystem=OrderedDict(sorted(filesystem.items(), key=lambda t: t[0].lower())),
                           breadcrumb=breadcrumb,
                           path=path,
                           page="my_files")


@my_files.route('/my_files/download', methods=['GET'])
@login_required
def download():
    uid = request.args.get("uid", None)
    if uid is None:
        return redirect("/my_files")

    file_information = decrypt(uid)
    if file_information["success"] is True:
        if user_has_permission(file_information["file_path"], "read") is False:
            flash(" You are not authorized to download this file")
            return redirect("/my_files")

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
            destination = path + file.filename
            if user_has_permission(destination, "create", "folder") is False:
                flash("You are not authorized to upload in this location")
                return "Unthorized", 401
            else:
                file.save(destination)
                change_ownership(destination)
        except Exception as err:
            return str(err), 500

    flash("File(s) uploaded", "success")
    return "Success", 200


@my_files.route('/my_files/create_folder', methods=['POST'])
@login_required
def create():
    if "folder_name" not in request.form.keys() or "path" not in request.form.keys():
        return redirect("/my_files")
    try:
        folder_name = request.form["folder_name"]
        folder_path = request.form["path"]
        folder_to_create = folder_path + folder_name
        if user_has_permission(folder_to_create, "create", "folder") is False:
            flash("You do not have write permission on this folder.", "error")
            return redirect("/my_files?path="+folder_path)

        access_right = 0o750
        os.makedirs(folder_to_create, access_right)
        change_ownership(folder_to_create)
        flash(folder_to_create + " created successfully.", "success")
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
                if os.path.isfile(file_info["file_path"]):
                    if user_has_permission(file_info["file_path"], "delete", "file") is True:
                        flash("File removed", "success")
                    else:
                        flash("You do not have the permission to delete this file.", "error")

                elif os.path.isdir(file_info["file_path"]):
                    files_in_folder = [f for f in os.listdir(file_info["file_path"]) if not f.startswith('.')]
                    if files_in_folder.__len__() == 0:
                        if user_has_permission(file_info["file_path"], "delete", "folder") is True:
                            flash("Folder removed.", "success")
                        else:
                            flash("You do not have the permission to delete this folder.", "error")
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


@my_files.route('/editor', methods=['GET'])
@login_required
def editor():
    uid = request.args.get("uid", None)
    if uid is None:
        return redirect("/my_files")

    file_information = decrypt(uid)
    if file_information["success"] is True:
        file_info = json.loads(file_information["message"])
        if user_has_permission(file_info["file_path"], "write", "file") is False:
            flash("You do not have permission to edit this file")
            return redirect("/my_files")

        text = get(config.Config.FLASK_ENDPOINT + '/api/system/files',
                   headers={"X-SOCA-TOKEN": config.Config.API_ROOT_KEY},
                   params={"file": file_info["file_path"]},
                   verify=False
                   )
        if text.status_code != 200:
            flash(text.json()["message"])
            return redirect("/my_files")
        else:
            file_data = text.json()["message"]

        known_extensions = {".txt": "text",
                            ".log": "text",
                            ".conf": "text",
                            ".cfg": "text",
                            ".csv": "csv",
                            ".json": "json",
                            ".yml": "yaml",
                            ".yaml": "yaml"
        }
        if file_info["file_path"].split(".")[-1] in known_extensions.keys():
            file_syntax = known_extensions[file_info["file_path"].split(".")[-1]]
        else:
            file_syntax = "text"

        return render_template("editor.html",
                               page="editor",
                               file_to_edit=file_info["file_path"],
                               file_data=file_data,
                               file_syntax=file_syntax,
                               user=session["user"],
                               api_key=session["api_key"]
                               )
    else:
        flash("Unable to delete " + file_information["message"], "error")
        return redirect("/my_files")

