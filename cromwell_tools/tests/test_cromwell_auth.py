import os
import tempfile
import json
import six
import pytest
import requests
from cromwell_tools.cromwell_auth import CromwellAuth


six.add_move(six.MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock  # noqa


def setup_auth_types():
    temp_dir = tempfile.mkdtemp()
    secrets_file = os.path.join(temp_dir, 'fake_secrets.json')
    service_account_key = os.path.join(temp_dir, 'fake_key.json')
    username = "fake_user"
    password = "fake_password"
    url = "https://fake_url"

    auth_params = {"url": url, "username": username, "password": password}
    with open(secrets_file, 'w') as f:
        json.dump(auth_params, f)

    auth_params['secrets_file'] = {"secrets_file": secrets_file}
    auth_params['service_account_key'] = {
        "service_account_key": service_account_key,
        "url": url,
    }
    return auth_params


auth_types = setup_auth_types()


@mock.patch('cromwell_tools.cromwell_auth.CromwellAuth.from_service_account_key_file')
def test_harmonize_credentials_only_takes_one_auth_type(mock_header):
    url = 'https://cromwell.server.org'
    expected_auth = CromwellAuth(
        url=url, header={"Authorization": "bearer fake_token"}, auth=None
    )
    mock_header.return_value = expected_auth
    with pytest.raises(ValueError):
        CromwellAuth.harmonize_credentials(**auth_types)


def test_harmonize_credentials_user_password():
    username = 'fake_user'
    password = 'fake_password'
    url = 'https://cromwell.server.org'
    expected_auth = CromwellAuth(
        url=url, header=None, auth=requests.auth.HTTPBasicAuth(username, password)
    )
    auth = CromwellAuth.harmonize_credentials(
        username=username, password=password, url=url
    )
    assert auth.auth == expected_auth.auth
    assert auth.header == expected_auth.header


def test_harmonize_credentials_from_secrets_file():
    username = "fake_user"
    password = "fake_password"
    url = "https://fake_url"
    expected_auth = CromwellAuth(
        url=url, header=None, auth=requests.auth.HTTPBasicAuth(username, password)
    )
    auth = CromwellAuth.harmonize_credentials(
        secrets_file=auth_types['secrets_file']['secrets_file']
    )
    assert auth.auth == expected_auth.auth
    assert auth.header == expected_auth.header


@mock.patch('cromwell_tools.cromwell_auth.CromwellAuth.from_service_account_key_file')
def test_harmonize_credentials_from_service_account_key(mock_header):
    service_account_key = 'fake_key.json'
    url = 'https://cromwell.server.org'
    expected_auth = CromwellAuth(
        url=url, header={"Authorization": "bearer fake_token"}, auth=None
    )
    mock_header.return_value = expected_auth
    auth = CromwellAuth.harmonize_credentials(
        url=url, service_account_key=service_account_key
    )
    assert auth == expected_auth


@mock.patch('cromwell_tools.cromwell_auth.CromwellAuth.from_service_account_key_file')
def test_harmonize_credentials_from_service_account_key_content(mock_header):
    service_account_key = {'client_email': 'fake_email', 'token_uri': 'fake_uri'}
    url = 'https://cromwell.server.org'
    expected_auth = CromwellAuth(
        url=url, header={"Authorization": "bearer fake_token"}, auth=None
    )
    mock_header.return_value = expected_auth
    auth = CromwellAuth.harmonize_credentials(
        url=url, service_account_key=service_account_key
    )
    assert auth == expected_auth


def test_harmonize_credentials_from_no_authentication():
    url = "https://fake_url"
    expected_auth = CromwellAuth(url=url, header=None, auth=None)
    auth = CromwellAuth.harmonize_credentials(url=url)
    assert auth.auth == expected_auth.auth
    assert auth.header == expected_auth.header
