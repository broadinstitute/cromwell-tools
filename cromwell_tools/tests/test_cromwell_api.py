import io
import zipfile
import tempfile
import os
import json

from tenacity import stop_after_delay, stop_after_attempt
import requests
import requests_mock
import pytest

from .._cromwell_api import CromwellAPI
from .._cromwell_auth import CromwellAuth


def setup_auth_types():
    temp_dir = tempfile.mkdtemp()
    secrets_file = os.path.join(temp_dir, 'fake_secrets.json')
    caas_key_file = os.path.join(temp_dir, 'fake_key.json')
    username = "fake_user"
    password = "fake_password"
    url = "https://fake_url"

    user_password = {
        "url": url,
        "username": username,
        "password": password
    }
    with open(secrets_file, 'w') as f:
        json.dump(user_password, f)

    with open(caas_key_file, 'w') as f:
        json.dump(user_password, f)

    # produce authentication types
    return {
        "secrets_file": {"secrets_file": secrets_file},
        "caas_key": {"caas_key": caas_key_file, "cromwell_url": url},
        "user_password": user_password
    }

auth_types = setup_auth_types()


@pytest.fixture(scope='module', params=auth_types.values(), ids=auth_types.keys())
def auth_types(request):
    return request.param


def test_cromwell_auth(auth_types):

    def _request_callback(request, context):
        context.status_code = 200
        context.headers['test'] = 'header'
        return {'request': {'body': "content"}}

    def _request_callback_status(request, context):
        context.status_code = 200
        context.headers['test'] = 'header'
        return {'status': 'Succeeded'}

    with requests_mock.mock() as mock_request:
        CromwellAuth.harmonize_credentials(**auth_types)

