import pytest
import random
import string
import random
from requests import get, post, delete, put

# Change Flask Endpoint to point to your test SOCA environment.
FLASK_ENDPOINT = "http://localhost:5000"
USERNAME = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
PASSWORD = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
UID = random.randint(7000, 8000)
GID = random.randint(8001, 9000)

MICKAEL_TOEN="35d20e134a607c8afe32c9d94dee71d5"

print("Test User: " + USERNAME)
print("Test Password: " + PASSWORD)
print("UID: " + str(UID))
print("GID: " + str(GID))


def test_get_index():
    assert get(FLASK_ENDPOINT).status_code == 200


def test_create_user():
    resource = "/api/ldap/user"
    data = {"username": USERNAME,
            "password": PASSWORD,
            "sudoers": False,
            "uid": UID,
            "gid": GID}

    headers = {"X-SOCA-TOKEN"}




def test_get_users():
    resource = "/api/ldap/users"
    assert get(FLASK_ENDPOINT + resource).status_code == 200


# checl ldap group # check sudo # add sudo # check group

