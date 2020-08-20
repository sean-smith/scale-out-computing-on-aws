from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ApiKeys(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean)
    scope = db.Column(db.String(255), nullable=False)
    created_on = db.Column(db.DateTime)
    deactivated_on = db.Column(db.DateTime)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ApplicationProfiles(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    creator = db.Column(db.String(255), nullable=False)
    profile_name = db.Column(db.String(255), nullable=False)
    profile_form = db.Column(db.Text, nullable=False)
    profile_job = db.Column(db.Text, nullable=False)
    profile_interpreter = db.Column(db.Text, nullable=False)
    profile_thumbnail = db.Column(db.Text, nullable=False)
    acl_allowed_users = db.Column(db.Text)
    acl_restricted_users = db.Column(db.Text)
    created_on = db.Column(db.DateTime)
    deactivated_on = db.Column(db.DateTime)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class LinuxDCVSessions(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.String(255), nullable=False)  # Session owner
    tag_uuid = db.Column(db.Text)  # Manage EC2 tag soca:DCVSessionUUID
    session_name = db.Column(db.String(255))  # Session name specified by the user
    session_number = db.Column(db.Integer, nullable=False)  # DCV session number
    session_state = db.Column(db.String(255), nullable=False)  # State of the session (pending/stopped/running)
    session_host_private_dns = db.Column(db.String(255))  # Private DNS of the EC2 host
    session_host_private_ip = db.Column(db.String(255))  # Private IP of the EC2 host
    session_instance_id = db.Column(db.String(255))  # Instance ID of the EC2 host
    session_instance_type = db.Column(db.String(255))  # Instance type of the EC2 host
    session_token = db.Column(db.String(255))  # Unique token associated to each session
    session_id = db.Column(db.String(255), nullable=False)  # DCV session ID, default to console for windows
    session_thumbnail = db.Column(db.Text)  # DCV session screenshot
    support_hibernation = db.Column(db.Boolean, nullable=False)  # If EC2 host has hibernation turned on/off
    dcv_authentication_token = db.Column(db.String(255))  # Encrypted authentication token
    is_active = db.Column(db.Boolean)  # If session is active or not
    created_on = db.Column(db.DateTime)  # Timestamp when session was created
    deactivated_on = db.Column(db.DateTime)  # Timestamp when session was deleted
    session_schedule_monday = db.Column(db.String(255))  # Schedule for monday. Can be norun, allday or start,stop such as 8,17
    session_schedule_tuesday = db.Column(db.String(255))  # Schedule for tuesday. Can be norun, allday or start,stop such as 8,17
    session_schedule_wednesday = db.Column(db.String(255))  # Schedule for wednesday. Can be norun, allday or start,stop such as 8,17
    session_schedule_thursday = db.Column(db.String(255))  # Schedule for thursday. Can be norun, allday or start,stop such as 8,17
    session_schedule_friday = db.Column(db.String(255))  # Schedule for friday. Can be norun, allday or start,stop such as 8,17
    session_schedule_saturday = db.Column(db.String(255))  # Schedule for saturday. Can be norun, allday or start,stop such as 8,17
    session_schedule_sunday = db.Column(db.String(255))  # Schedule for sunday. Can be norun, allday or start,stop such as 8,17


class WindowsDCVSessions(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.String(255), nullable=False)  # Session owner
    tag_uuid = db.Column(db.Text)  # Manage EC2 tag soca:DCVWindowsSessionUUID
    session_name = db.Column(db.String(255))  # Session name specified by the user
    session_number = db.Column(db.Integer, nullable=False)  # DCV session number
    session_state = db.Column(db.String(255), nullable=False)  # State of the session (pending/stopped/running)
    session_host_private_dns = db.Column(db.String(255))  # Private DNS of the EC2 host
    session_host_private_ip = db.Column(db.String(255))  # Private IP of the EC2 host
    session_instance_id = db.Column(db.String(255))  # Instance ID of the EC2 host
    session_instance_type = db.Column(db.String(255))  # Instance type of the EC2 host
    session_local_admin_password = db.Column(db.String(255), nullable=False)  # Local admin password (if windows)
    session_token = db.Column(db.String(255))  # Unique token associated to each session
    session_id = db.Column(db.String(255), nullable=False)  # DCV session ID, default to console for windows
    session_thumbnail = db.Column(db.Text)  # DCV session screenshot
    support_hibernation = db.Column(db.Boolean, nullable=False)  # If EC2 host has hibernation turned on/off
    dcv_authentication_token = db.Column(db.String(255))  # Encrypted authentication token
    is_active = db.Column(db.Boolean)  # If session is active or not
    created_on = db.Column(db.DateTime)  # Timestamp when session was created
    deactivated_on = db.Column(db.DateTime)  # Timestamp when session was deleted
    session_schedule_monday = db.Column(db.String(255))  # Schedule for monday. Can be norun, allday or start,stop such as 8,17
    session_schedule_tuesday = db.Column(db.String(255))  # Schedule for tuesday. Can be norun, allday or start,stop such as 8,17
    session_schedule_wednesday = db.Column(db.String(255))  # Schedule for wednesday. Can be norun, allday or start,stop such as 8,17
    session_schedule_thursday = db.Column(db.String(255))  # Schedule for thursday. Can be norun, allday or start,stop such as 8,17
    session_schedule_friday = db.Column(db.String(255))  # Schedule for friday. Can be norun, allday or start,stop such as 8,17
    session_schedule_saturday = db.Column(db.String(255))  # Schedule for saturday. Can be norun, allday or start,stop such as 8,17
    session_schedule_sunday = db.Column(db.String(255))  # Schedule for sunday. Can be norun, allday or start,stop such as 8,17






    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ProjectList(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    creator = db.Column(db.String(255), nullable=False)
    project_name = db.Column(db.String(255), nullable=False)
    project_queues = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime)
    deactivated_on = db.Column(db.DateTime)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}