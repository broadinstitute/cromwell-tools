import json
import requests
import requests.auth
from oauth2client.service_account import ServiceAccountCredentials
from ._cromwell_api import CromwellAPI


class AuthenticationError(Exception):
    pass


class CromwellAuth:

    def __init__(self, url, header, auth):
        """Authentication Helper for a Cromwell Server

        :param dict header: authorization header
        """
        if not header and not auth:
            raise ValueError("either header or auth must be passed")

        if header is not None:
            if not isinstance(header, dict):
                raise TypeError('if passed, header must be a dict')
            if "Authorization" not in header.keys():
                raise TypeError('the header must have an "Authorization" key')
        self.header = header

        # what is the type and what checks can be run?
        self.auth = auth

        if isinstance(url, str) and 'http' in url:
            self.url = url
        else:
            raise ValueError("url must be an str that points to an http endpoint.")

        # todo might need to change this re: cyclical import
        # todo the health API endpoint wants an instance of this class, not just the auth object.
        # if not CromwellAPI.health(auth).status_code == 200:
        #     raise AuthenticationError(
        #         'Could not connect to Cromwell at {url} given provided credentials'.format(
        #             url=url))

    @classmethod
    def from_caas_key(cls, caas_key, url):
        scopes = [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(caas_key, scopes=scopes)
        header = {"Authorization": "bearer " + credentials.get_access_token().access_token}
        return cls(url=url, header=header, auth=None)

    @classmethod
    def from_secrets_file(cls, secrets_file):
        with open(secrets_file, 'r') as f:
            secrets = json.load(f)
        auth = requests.auth.HTTPBasicAuth(
            secrets['username'],
            secrets['password']
        )
        url = secrets['url']
        return cls(url=url, header=None, auth=auth)

    @classmethod
    def from_user_password(cls, username, password, url):
        auth = requests.auth.HTTPBasicAuth(username, password)
        return cls(url=url, header=None, auth=auth)

    @classmethod
    def harmonize_credentials(
            cls, username=None, password=None, url=None, secrets_file=None, caas_key=None,
            **kwargs):

        # verify only one credential provided
        credentials = {
            "caas_key": True if caas_key else False,
            "secrets_file": True if secrets_file else False,
            "user_password": True if all((username, password, url)) else False
        }
        if sum(credentials.values()) != 1:
            raise ValueError(
                "Exactly one set of credentials must be passed.\nCredentials: {}".format(
                    repr(credentials)))

        if credentials["caas_key"]:
            return cls.from_caas_key(caas_key, url)
        if credentials["secrets_file"]:
            return cls.from_secrets_file(secrets_file)
        if credentials["user_password"]:
            return cls.from_user_password(username, password, url)
