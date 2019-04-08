#!/usr/bin/env python
import io
import json
import os
import requests
import requests_mock
import six
import tempfile
import unittest


six.add_move(six.MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock  # noqa

from cromwell_tools.cromwell_api import CromwellAPI  # noqa
from cromwell_tools.cromwell_auth import CromwellAuth  # noqa
from cromwell_tools import utilities as utils  # noqa


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Change to test directory, as tests may have been invoked from another dir
        dir_ = os.path.abspath(os.path.dirname(__file__))
        os.chdir(dir_)

    def setUp(self):
        self.wdl_file = io.BytesIO(b"wdl_file_content")
        self.zip_file = io.BytesIO(b"zip_file_content")
        self.inputs_file = io.BytesIO(b"inputs_file_content")
        self.options_file = io.BytesIO(b"options_file_content")
        self.label = io.BytesIO(b'{"test-label-key": "test-label-value"}')
        self.auth_options = self.set_up_auth()

    @mock.patch(
        'cromwell_tools.cromwell_auth.CromwellAuth.from_service_account_key_file'
    )
    def set_up_auth(self, mock_header):
        # set up authentication options for the tests
        temp_dir = tempfile.mkdtemp()
        secrets_file = temp_dir + 'fake_secrets.json'
        service_account_key = os.path.join(temp_dir, 'fake_key.json')
        username = "fake_user"
        password = "fake_password"
        url = "https://fake_url"
        auth = {"url": url, "username": username, "password": password}
        with open(secrets_file, 'w') as f:
            json.dump(auth, f)
        mock_header.return_value = CromwellAuth(
            url=url, header={"Authorization": "bearer fake_token"}, auth=None
        )

        auth_options = (
            CromwellAuth.harmonize_credentials(**auth),  # HTTPBasicAuth
            CromwellAuth.harmonize_credentials(
                **{"secrets_file": secrets_file}
            ),  # Secret file
            CromwellAuth.harmonize_credentials(
                **{"service_account_key": service_account_key, "url": url}
            ),  # OAuth
            CromwellAuth.harmonize_credentials(url=url),  # No Auth
        )
        return auth_options

    def _submit_workflows(self, cromwell_auth, mock_request, _request_callback):
        mock_request.post(
            cromwell_auth.url + '/api/workflows/v1', json=_request_callback
        )
        return CromwellAPI.submit(
            auth=cromwell_auth,
            wdl_file=self.wdl_file,
            inputs_files=self.inputs_file,
            options_file=self.options_file,
            dependencies=self.zip_file,
            label_file=self.label,
        )

    @requests_mock.mock()
    def test_submit_workflow(self, mock_request):
        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {'request': {'body': "content"}}

        for cromwell_auth in self.auth_options:
            result = self._submit_workflows(
                cromwell_auth, mock_request, _request_callback
            )
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.headers.get('test'), 'header')

    @requests_mock.mock()
    def test_submit_workflow_handlers_error_response(self, mock_request):
        def _request_callback(request, context):
            context.status_code = 500
            context.headers['test'] = 'header'
            return {'status': 'error', 'message': 'Internal Server Error'}

        # Check request actions
        for cromwell_auth in self.auth_options:
            with self.assertRaises(requests.HTTPError):
                self._submit_workflows(
                    cromwell_auth, mock_request, _request_callback
                ).raise_for_status()

    @requests_mock.mock()
    def test_query_workflows_returns_200(self, mock_request):
        query_dict = {
            'status': ['Running', 'Failed'],
            'label': {'label_key1': 'label_value1', 'label_key2': 'label_value2'},
        }

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {
                'results': [
                    {
                        'name': 'workflow1',
                        'submission': 'submission1',
                        'id': 'id1',
                        'status': 'Failed',
                        'start': 'start1',
                        'end': 'end1',
                    },
                    {
                        'name': 'workflow2',
                        'submission': 'submission2',
                        'id': 'id2',
                        'status': 'Running',
                        'start': 'start2',
                        'end': 'end2',
                    },
                ],
                'totalResultsCount': 2,
            }

        for cromwell_auth in self.auth_options:
            mock_request.post(
                '{}/api/workflows/v1/query'.format(cromwell_auth.url),
                json=_request_callback,
            )
            result = CromwellAPI.query(query_dict, cromwell_auth)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['totalResultsCount'], 2)

    def test_compose_query_params_can_compose_simple_query_dicts(self):
        query_dict = {
            'status': 'Running',
            'start': '2018-01-01T00:00:00.000Z',
            'end': '2018-01-01T12:00:00.000Z',
            'label': {'Comment': 'test'},
            'page': 1,
            'pageSize': 10,
        }

        expect_params = [
            {'status': 'Running'},
            {'start': '2018-01-01T00:00:00.000Z'},
            {'end': '2018-01-01T12:00:00.000Z'},
            {'label': 'Comment:test'},
            {'page': '1'},
            {'pageSize': '10'},
        ]

        six.assertCountEqual(
            self, CromwellAPI._compose_query_params(query_dict), expect_params
        )

    def test_compose_query_params_can_compose_nested_query_dicts(self):
        query_dict = {
            'status': ['Running', 'Failed', 'Submitted'],
            'start': '2018-01-01T00:00:00.000Z',
            'end': '2018-01-01T12:00:00.000Z',
            'label': {'Comment1': 'test1', 'Comment2': 'test2', 'Comment3': 'test3'},
        }

        expect_params = [
            {'status': 'Running'},
            {'status': 'Failed'},
            {'status': 'Submitted'},
            {'start': '2018-01-01T00:00:00.000Z'},
            {'end': '2018-01-01T12:00:00.000Z'},
            {'label': 'Comment1:test1'},
            {'label': 'Comment2:test2'},
            {'label': 'Comment3:test3'},
        ]
        six.assertCountEqual(
            self, CromwellAPI._compose_query_params(query_dict), expect_params
        )

    def test_compose_query_params_can_convert_bools_within_query_dicts(self):
        query_dict = {
            'status': ['Running', 'Failed', 'Submitted'],
            'start': '2018-01-01T00:00:00.000Z',
            'end': '2018-01-01T12:00:00.000Z',
            'label': {'Comment1': 'test1', 'Comment2': 'test2', 'Comment3': 'test3'},
            'includeSubworkflows': True,
        }

        expect_params = [
            {'status': 'Running'},
            {'status': 'Failed'},
            {'status': 'Submitted'},
            {'start': '2018-01-01T00:00:00.000Z'},
            {'end': '2018-01-01T12:00:00.000Z'},
            {'label': 'Comment1:test1'},
            {'label': 'Comment2:test2'},
            {'label': 'Comment3:test3'},
            {'includeSubworkflows': 'true'},
        ]
        six.assertCountEqual(
            self, CromwellAPI._compose_query_params(query_dict), expect_params
        )

    def test_compose_query_params_raises_error_for_invalid_query_dict_that_has_multiple_values_for_exclusive_keys(
        self
    ):
        query_dict = {
            'status': ['Running', 'Failed', 'Submitted'],
            'start': ['2018-01-01T00:00:00.000Z', '2018-01-02T00:00:00.000Z'],
            'end': '2018-01-01T12:00:00.000Z',
            'label': {'Comment1': 'test1', 'Comment2': 'test2', 'Comment3': 'test3'},
        }

        with self.assertRaises(ValueError):
            CromwellAPI._compose_query_params(query_dict)

    @requests_mock.mock()
    def test_release_onhold_returns_200(self, mock_request):
        workflow_id = '12345abcde'

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {'id': request.url.split('/')[-2], 'status': 'Submitted'}

        for cromwell_auth in self.auth_options:
            mock_request.post(
                '{0}/api/workflows/v1/{1}/releaseHold'.format(
                    cromwell_auth.url, workflow_id
                ),
                json=_request_callback,
            )
            result = CromwellAPI.release_hold(workflow_id, cromwell_auth)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['id'], workflow_id)
            self.assertEqual(result.json()['status'], 'Submitted')

    @requests_mock.mock()
    def test_release_workflow_that_is_not_on_hold_returns_error(self, mock_request):
        workflow_id = 'test'

        def _request_callback(request, context):
            context.status_code = 403
            context.headers['test'] = 'header'
            return {
                'status': 'error',
                'message': 'Couldn\'t change status of workflow {} to \'Submitted\' because the workflow is not in '
                '\'On Hold\' state'.format(request.url.split('/')[-2]),
            }

        for cromwell_auth in self.auth_options:
            mock_request.post(
                '{0}/api/workflows/v1/{1}/releaseHold'.format(
                    cromwell_auth.url, workflow_id
                ),
                json=_request_callback,
            )
            with self.assertRaises(requests.exceptions.HTTPError):
                CromwellAPI.release_hold(workflow_id, cromwell_auth).raise_for_status()

    @requests_mock.mock()
    def test_health_returns_200(self, mock_request):
        expected = {
            "DockerHub": {"ok": "true"},
            "Engine Database": {"ok": "true"},
            "PAPI": {"ok": "true"},
            "GCS": {"ok": "true"},
        }

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return expected

        for cromwell_auth in self.auth_options:
            mock_request.get(
                '{0}/engine/v1/status'.format(cromwell_auth.url), json=_request_callback
            )
            result = CromwellAPI.health(cromwell_auth)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), expected)

    @requests_mock.mock()
    def test_abort(self, mock_request):
        workflow_id = "01234"
        expected = {"id": workflow_id, "status": "Aborting"}

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return expected

        for cromwell_auth in self.auth_options:
            mock_request.post(
                cromwell_auth.url + '/api/workflows/v1/{}/abort'.format(workflow_id),
                json=_request_callback,
            )
            result = CromwellAPI.abort(workflow_id, cromwell_auth)
            self.assertEqual(result.json(), expected)

    @requests_mock.mock()
    def test_status(self, mock_request):
        def _request_callback_status(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {'status': 'Succeeded'}

        workflow_id = "01234"
        for cromwell_auth in self.auth_options:
            mock_request.get(
                cromwell_auth.url + '/api/workflows/v1/{}/status'.format(workflow_id),
                json=_request_callback_status,
            )
            result = CromwellAPI.status(workflow_id, cromwell_auth)
            self.assertEqual(result.json()['status'], 'Succeeded')


if __name__ == '__main__':
    unittest.main()
