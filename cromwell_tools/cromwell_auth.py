import json
import requests
import requests.auth
from oauth2client.service_account import ServiceAccountCredentials


class AuthenticationError(Exception):
    pass


class CromwellAuth:

    def __init__(self, url, header, auth):
        """Authentication Helper Class for a Cromwell Server.

        Currently this class only supports 3 Auth methods with Cromwell:
            - OAuth2 through Google by passing a service account JSON key file.
            - HTTPBasic Authentication.
            - No Auth

        Args:
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"
            header (dict or None): Dictionary containing the (bearer token) authorization header.
            auth (requests.auth.HTTPBasicAuth or None): HTTP Basic Authentication information,
                i.e. username and password.
        """

        # TODO: add a step to validate the auth information with Cromwell Server, requires /auth endpoint from Cromwell
        self._validate_auth(header, auth)
        self.header = header
        self.auth = auth
        self.url = self._validate_url(url)

    @staticmethod
    def _validate_auth(header, auth):
        """Validate the format of the auth header and the HTTPBasic Auth credentials.

        Args:
            header (dict or None): Dictionary containing the (bearer token) authorization header.
            auth (requests.auth.HTTPBasicAuth or None): HTTP Basic Authentication information,
                i.e. username and password.

        Raises:
            TypeError: when no credentials are provided or auth is not a valid HTTPBasicAuth object.
            ValueError: when the header is not a valid header(with Bearer token).
        """
        if not header and not auth:
            raise ValueError("Either a header containing bearer token or a HTTPBasic Auth object must be passed.")

        if header:
            if not isinstance(header, dict):
                raise TypeError('If passed, header must be a dict.')
            if "Authorization" not in header.keys():
                raise TypeError('The header must have an "Authorization" key')

        if auth:
            if not isinstance(auth, requests.auth.HTTPBasicAuth):
                raise TypeError('The auth object must be a valid "requests.auth.HTTPBasicAuth" object!')

    @staticmethod
    def _validate_url(url):
        """Validate the input Cromwell url and harmonize it.

        Args:
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"

        Returns:
            str: The URL to the Cromwell server without slash at the end. e.g. "https://cromwell.server.org"

        Raises:
            ValueError: If the input url is invalid, i.e. not following http(s) schema.
        """
        if isinstance(url, str) and url.startswith('http'):
            return url.strip('/')
        else:
            raise ValueError("url must be an str that points to an http(s) endpoint.")

    @classmethod
    def from_service_account_key_file(cls, service_account_key, url):
        """Generate an authentication object from a Service Account JSON key file.

        The service account key file will be required if you are using Cromwell-as-a-Service or
        you are using OAuth for your Cromwell Server.

        Args:
            service_account_key (str): Path to the JSON key file(service account key) for authenticating with CaaS.
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"

        Returns:
            CromwellAuth: An instance of this auth helper class with valid OAuth Auth header.
        """
        scopes = [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(service_account_key, scopes=scopes)
        header = {"Authorization": "bearer " + credentials.get_access_token().access_token}
        return cls(url=url, header=header, auth=None)

    @classmethod
    def from_secrets_file(cls, secrets_file):
        """Generate an authentication object from a JSON file that contains credentials info for HTTPBasicAuth.

        Args:
            secrets_file (str): JSON file containing username, password, and url fields. e.g.
                {
                    "username": "",
                    "password": "",
                    "url": ""
                }

        Returns:
            CromwellAuth: An instance of this auth helper class with valid u/p and url for HTTPBasicAuth.
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
        """Generate an authentication object from username, password, and Cromwell url.

        Args:
            username (str): Cromwell username for HTTPBasicAuth.
            password (str): Cromwell password for HTTPBasicAuth.
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"

        Returns:
            CromwellAuth: An instance of this auth helper class with valid u/p and url for HTTPBasicAuth.
        """
        auth = requests.auth.HTTPBasicAuth(username, password)
        return cls(url=url, header=None, auth=auth)

    @classmethod
    def harmonize_credentials(
            cls, username=None, password=None, url=None, secrets_file=None, caas_key=None):
        """Parse and harmonize user inputted credentials and generate proper authentication object for cromwell-tools.

        Args:
            username (str): Cromwell username for HTTPBasicAuth.
            password (str): Cromwell password for HTTPBasicAuth.
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"
            secrets_file (str): JSON file containing username, password, and url fields. e.g.
                {
                    "username": "",
                    "password": "",
                    "url": ""
                }
            caas_key (str): Path to the JSON key file(service account key) for authenticating with CaaS.

        Returns:
            CromwellAuth: An instance of this auth helper class with proper credentials for authenticating with
                Cromwell or CaaS.
        """
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
            return cls.from_service_account_key_file(caas_key, url)
        if credentials["secrets_file"]:
            return cls.from_secrets_file(secrets_file)
        if credentials["user_password"]:
            return cls.from_user_password(username, password, url)
