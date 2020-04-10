import logging
import config
from decorators import login_required
from flask import render_template, request, redirect, session, flash, Blueprint
from requests import post, get
import math
import os
from datetime import datetime
from cryptography.fernet import Fernet
import base64


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
    key = base64.b64encode(config.Config.API_ROOT_KEY.encode("utf-8"))
    cipher_suite = Fernet(key)
    encoded_text = cipher_suite.encrypt()
    decoded_text = cipher_suite.decrypt(encoded_text)

@my_files.route('/my_files', methods=['GET'])
def index():
    hierarchy = "/Users/mcrozes/Desktop"
    folders = []
    files = {}

    for entry in os.scandir(hierarchy):
        if entry.is_dir():
            folders.append(entry.name)
        elif entry.is_file():

            files[entry.name] = {"st_size": convert_size(entry.stat().st_size),
                                 "st_mtime": datetime.utcfromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
        else:
            pass

    return render_template('my_files.html', files=files, folders=folders, breadcrumb=hierarchy.split("/"))

