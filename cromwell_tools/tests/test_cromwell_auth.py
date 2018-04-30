import tempfile
import json

import pytest

import requests_mock

from .._cromwell_auth import CromwellAuth


def setup_auth_types():
    temp_dir = tempfile.mkdtemp()
    secrets_file = temp_dir + 'fake_secrets.json'
    username = "fake_user"
    password = "fake_password"
    url = "https://fake_url"

    user_password = {
        "url": url,
        "user": username,
        "password": password
    }
    with open(secrets_file, 'w') as f:
        json.dump(user_password, f)

    # produce authentication types
    return {
        "secrets_file": {"secrets_file": secrets_file},
        "caas_key": {"caas_key": "path/fake_key.json", "cromwell_url": url},
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
        CromwellAuth(**auth_types)


@requests_mock.mock()
def test_get_workflow_statuses(self, mock_request):
    def _request_callback(request, context):
        context.status_code = 200
        context.headers['test'] = 'header'
        return {'request': {'body': "content"}}

    def _request_callback_status(request, context):
        context.status_code = 200
        context.headers['test'] = 'header'
        return {'status': 'Succeeded'}

    ids = ["01234"]
    mock_request.post(self.url, json=_request_callback)
    mock_request.get(self.url + '/api/workflows/v1/{}/status'.format(ids[0]), json=_request_callback_status)
    result = cromwell_tools.get_workflow_statuses(ids, self.url, self.user, self.password)
    self.assertIn('Succeeded', result)
