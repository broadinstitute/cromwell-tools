import json
import requests
import requests.auth
import six
from google.oauth2 import service_account
import google.auth.transport.requests
import logging


class AuthenticationError(Exception):
    pass


class CromwellAuth:
    def __init__(
        self, url, header, auth, oauth_credentials=None, service_key_content=None
    ):
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
            oauth_credentials (service_account.Credentials or None): Optional, service_account.Credentials object,
            used for refreshing the Authentication headers when using OAuth.
            service_key_content (dict): Optional, required by JES-backend Cromwells that use OAuth.
        """

        # TODO: add a step to validate the auth information with Cromwell Server, requires /auth endpoint from Cromwell
        self._validate_auth(header, auth)
        self._header = header
        self._auth = auth
        self._credentials = oauth_credentials
        self.url = self._validate_url(url)
        self._service_key_content = service_key_content

    @property
    def auth(self):
        """The property of HTTP Basic Authentication information, i.e. username and password."""
        return self._auth

    @property
    def service_key_content(self):
        """The content of the service account key, if applicable. This is required by JES-backend Cromwell using OAuth."""
        return self._service_key_content

    @property
    def header(self):
        """Dictionary containing the (bearer token) authorization header.

        If the credentials are provided to create the object, this property will make sure the token is not expired.
        """
        if self._credentials:
            if not self._credentials.valid:
                self._credentials.refresh(google.auth.transport.requests.Request())
                header = {}
                self._credentials.apply(header)
                self._header = header
        return self._header

    @staticmethod
    def _validate_auth(header, auth):
        """Validate the format of the auth header and the HTTPBasic Auth credentials.

        Args:
            header (dict or None): Dictionary containing the (bearer token) authorization header.
            auth (requests.auth.HTTPBasicAuth or None): HTTP Basic Authentication information,
                i.e. username and password.

        Raises:
            TypeError: when header is not a valid `dict` or the auth object is not a valid
                `requests.auth.HTTPBasicAuth` object.
            ValueError: when the header is not a valid header(with Bearer token).
        """
        if not header and not auth:
            logging.warning(
                'You are not using any authentication with Cromwell. For security purposes, '
                'please consider adding authentication in front of your Cromwell instance!'
            )

        if header:
            if not isinstance(header, dict):
                raise TypeError('If passed, header must be a dict.')
            if "authorization" not in [k.lower() for k in header.keys()]:
                raise ValueError(
                    'The header must have an "Authorization" or "authorization" key!'
                )

        if auth and not isinstance(auth, requests.auth.HTTPBasicAuth):
            raise TypeError(
                'The auth object must be a valid "requests.auth.HTTPBasicAuth" object!'
            )

    @staticmethod
    def _validate_url(url):
        """Validate the input Cromwell url and remove the trailing slash.

        Args:
            url (str or unicode): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"

        Returns:
            str: The URL to the Cromwell server without slash at the end. e.g. "https://cromwell.server.org"

        Raises:
            ValueError: If the input url is invalid, i.e. not following http(s) schema.
        """
        if isinstance(url, six.string_types) and url.startswith('http'):
            return str(url.strip('/'))
        else:
            raise ValueError("url must be an str pointing to an http(s) endpoint.")

    @classmethod
    def from_service_account_key_file(cls, service_account_key, url):
        """Generate an authentication object from a Service Account JSON key file.

        The service account key file will be required if you are using Cromwell-as-a-Service or
        you are using OAuth for your Cromwell Server.

        Args:
            service_account_key (str or dict): Path to the JSON key file(service account key), or a dict of
                the JSON content of the key file, for authenticating with CaaS.
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"

        Returns:
            CromwellAuth: An instance of this auth helper class with valid OAuth Auth header.
        """
        scopes = ['email', 'openid', 'profile']
        if isinstance(service_account_key, dict):
            credentials = service_account.Credentials.from_service_account_info(
                service_account_key, scopes=scopes
            )
            service_key_content = service_account_key
        else:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_key, scopes=scopes
            )
            with open(service_account_key, 'r') as f:
                service_key_content = json.load(f)

        if not credentials.valid:
            credentials.refresh(google.auth.transport.requests.Request())
        header = {}
        credentials.apply(header)
        return cls(
            url=url,
            header=header,
            auth=None,
            oauth_credentials=credentials,
            service_key_content=service_key_content,
        )

    @classmethod
    def from_secrets_file(cls, secrets_file):
        """Generate an authentication object from a JSON file that contains credentials info for HTTPBasicAuth.

        Args:
            secrets_file (str): Path to the JSON file containing username, password, and url fields. e.g.
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
        auth = requests.auth.HTTPBasicAuth(secrets['username'], secrets['password'])
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
    def from_no_authentication(cls, url):
        """Generate an authentication object which does use any auth methods.

        Args:
            url (str): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"

        Returns:
            CromwellAuth: An instance of this auth helper class with url and has no auth methods.
        """
        return cls(url=url, header=None, auth=None)

    @classmethod
    def harmonize_credentials(
        cls,
        username=None,
        password=None,
        url=None,
        secrets_file=None,
        service_account_key=None,
    ):
        """Parse and harmonize user inputted credentials and generate proper authentication object for cromwell-tools.

        Args:
            username (str or None): Cromwell username for HTTPBasicAuth.
            password (str or None): Cromwell password for HTTPBasicAuth.
            url (str or None): The URL to the Cromwell server. e.g. "https://cromwell.server.org/"
            secrets_file (str or None): Path to the JSON file containing username, password, and url fields. e.g.
                {
                    "username": "",
                    "password": "",
                    "url": ""
                }
            service_account_key (str or None): Path to the JSON key file(service account key) for authenticating
                with CaaS or any Cromwell instances that using OAuth.

        Returns:
            CromwellAuth: An instance of this auth helper class with proper credentials for authenticating with
                Cromwell or CaaS.
        """
        # verify only one credential provided
        credentials = {
            "service_account_key": all((service_account_key, url)),
            "secrets_file": True if secrets_file else False,
            "user_password": all((username, password, url)),
            "no_auth": True
            if (
                not any((service_account_key, secrets_file, username, password)) and url
            )
            else False,
        }
        if sum(credentials.values()) != 1:
            raise ValueError(
                "Exactly one set of credentials must be passed.\nCredentials: {}".format(
                    repr(credentials)
                )
            )

        if credentials["service_account_key"]:
            return cls.from_service_account_key_file(service_account_key, url)
        if credentials["secrets_file"]:
            return cls.from_secrets_file(secrets_file)
        if credentials["user_password"]:
            return cls.from_user_password(username, password, url)
        if credentials["no_auth"]:
            return cls.from_no_authentication(url=url)
