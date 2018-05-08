import json
from collections import namedtuple

import requests
import requests.auth
from oauth2client.service_account import ServiceAccountCredentials

from ._cromwell_api import CromwellAPI


class AuthenticationError(Exception):
    pass


class CromwellAuth:

    def __init__(self, url, header, auth):
        """Authentication Helper for a Cromwell Server

        Args:
        url (str): Cromwell url
        header (dict): authorization header
        auth (str): authorization key
        """

        self._validate_auth(header, auth)
        self.header = header
        self.auth = auth

        self._validate_url(url)
        self.url =url

        self._validate_connection(self.header, self.auth, self.url)

    @staticmethod
    def _validate_auth(header, auth):
        if not header and not auth:
            raise ValueError("either header or auth must be passed")

        if header is not None:
            if not isinstance(header, dict):
                raise TypeError('if passed, header must be a dict')
            if "Authorization" not in header.keys():
                raise TypeError('the header must have an "Authorization" key')

    @staticmethod
    def _validate_url(url):
        if isinstance(url, str) and url.startswith('http'):
            pass
        else:
            raise ValueError("url must be an str that points to an http(s) endpoint.")

    @staticmethod
    def _validate_connection(header, auth, url):
        dummy_auth = namedtuple('dummy_auth', ['header', 'auth', 'url'])
        namespace = dummy_auth(header, auth, url)
        if not CromwellAPI.health(namespace).status_code == 200:
            raise AuthenticationError(
                'Could not connect to Cromwell at {url} given provided credentials'.format(
                    url=url))

    @classmethod
    def from_caas_key(cls, caas_key, url):
        """Generate an auth object from a CaaS key

        Args:
        caas_key (str): CaaS authentication key
        url (str): Cromwell URL

        """
        scopes = [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(caas_key, scopes=scopes)
        header = {"Authorization": "bearer " + credentials.get_access_token().access_token}
        return cls(url=url, header=header, auth=None)

    @classmethod
    def from_secrets_file(cls, secrets_file):
        """Generate an auth object from a secrets json file

        Args:
        secrets_file (str): json file containing username, password, and url fields

        """
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
        """Generate an auth object from a username, password, and url

        Args:
        username (str): cromwell username
        password (str): cromwell password
        url (str): cromwell URL

        """
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

