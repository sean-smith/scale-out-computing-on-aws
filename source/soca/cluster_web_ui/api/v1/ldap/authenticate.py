from flask_restful import Resource, reqparse
import config
import ldap
from errors import all_errors

class Authenticate(Resource):
    def post(self):
        """
        Validate a LDAP user/password
        ---
        tags:
          - LDAP management
        parameters:
          - in: body
            name: body
            schema:
              id: GETApiKey
              required:
                - user
                - password
              properties:
                user:
                  type: string
                  description: user of the SOCA user
                token:
                  type: string
                  description: token associated to the user

        responses:
          200:
            description: Pair of user/token is valid
          203:
            description: Invalid user/token pair
          400:
            description: Client error
          500:
            description: Backend error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('user', type=str, location='form')
        parser.add_argument('password', type=str, location='form')
        args = parser.parse_args()
        user = args["user"]
        password = args["password"]
        if user is None or password is None:
            return all_errors('CLIENT_MISSING_PARAMETER', "user (str) and password (str) are required.")

        ldap_host = config.Config.LDAP_HOST
        base_dn = config.Config.LDAP_BASE_DN
        user_dn = 'uid={},ou=people,{}'.format(user, base_dn)
        try:
            conn = ldap.initialize('ldap://{}'.format(ldap_host))
            conn.bind_s(user_dn, password, ldap.AUTH_SIMPLE)
            return {'success': True, 'message': 'User is valid'}, 200
        except Exception as err:
            return all_errors(type(err).__name__, err)
