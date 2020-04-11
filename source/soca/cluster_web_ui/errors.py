

def all_errors(error_name, trace=False):
    error_list = {
        "INVALID_CREDENTIALS": [{"success": False, "message": "Invalid user credentials"}, 401],
        "LDAP_SERVER_DOWN": [{"success": False, "message": "LDAP server seems to be down or unreachable"}, 500],
        "CLIENT_MISSING_PARAMETER": [{"success": False, "message": "Client input malformed: " + str(trace)}, 400]}

    if error_name in error_list.keys():
        return error_list[error_name][0], error_list[error_name][1]  # error message, status code
    else:
        return {"success": False, "message": "Unknown error caused by: " + str(trace)}, 500


