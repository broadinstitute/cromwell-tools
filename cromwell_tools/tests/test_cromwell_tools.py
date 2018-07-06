#!/usr/bin/env python
import io
import zipfile
import os
import json
import tempfile

from tenacity import stop_after_delay, stop_after_attempt
import requests
import requests_mock
import unittest

try:
    # if python3
    import unittest.mock as mock
except ImportError:
    # if python2
    import mock

from cromwell_tools import cromwell_tools


class TestUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Change to test directory, as tests may have been invoked from another dir
        dir = os.path.abspath(os.path.dirname(__file__))
        os.chdir(dir)
        cls.invalid_labels = {
            "0-label-key-1": "0-label-value-1",
            "the-maximum-allowed-character-length-for-label-pairs-is-sixty-three":
                "cromwell-please-dont-validate-these-labels",
            "": "not a great label key",
            "Comment": "This-is-a-test-label"
        }
        cls.valid_labels = {
            "label-key-1": "label-value-1",
            "label-key-2": "label-value-2",
            "only-key": "",
            "fc-id": "0123-abcd-4567-efgh",
            "comment": "this-is-a-test-label"
        }

    def setUp(self):
        self.wdl_file = io.BytesIO(b"wdl_file_content")
        self.zip_file = io.BytesIO(b"zip_file_content")
        self.inputs_file = io.BytesIO(b"inputs_file_content")
        self.inputs_file2 = io.BytesIO(b"inputs_file2_content")
        self.options_file = io.BytesIO(b"options_file_content")
        self.label = io.BytesIO(b'{"test-label-key": "test-label-value"}')
        self.on_hold = False
        self.url = "https://fake_url"
        self.user = "fake_user"
        self.password = "fake_password"
        self.caas_key = "path/fake_key.json"
        self.workflow_id = "xxx-xxx-xxx-id"

    @requests_mock.mock()
    def test_query_workflows_returns_200(self, mock_request):
        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {
                'results': [
                    {'name': 'workflow1',
                     'submission': 'submission1',
                     'id': 'id1',
                     'status': 'Failed',
                     'start': 'start1',
                     'end': 'end1'},
                    {'name': 'workflow2',
                     'submission': 'submission2',
                     'id': 'id2',
                     'status': 'Running',
                     'start': 'start2',
                     'end': 'end2'}
                ],
                'totalResultsCount': 2}

        mock_request.post('{}/query'.format(self.url), json=_request_callback)

        query_dict = {
            'status': ['Running', 'Failed'],
            'label': {
                'label_key1': 'label_value1',
                'label_key2': 'label_value2'
            }
        }
        result = cromwell_tools.query_workflows(self.url, query_dict, cromwell_user=self.user,
                                                cromwell_password=self.password)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['totalResultsCount'], 2)

    @requests_mock.mock()
    @mock.patch('cromwell_tools.cromwell_tools.generate_auth_header_from_key_file')
    def test_query_workflows_returns_200_in_cromwell_as_a_service(self, mock_request, mock_header):
        mock_header.return_value = {"Authorization": "bearer fake_token"}

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {
                'results': [
                    {'name': 'workflow1',
                     'submission': 'submission1',
                     'id': 'id1',
                     'status': 'Failed',
                     'start': 'start1',
                     'end': 'end1'},
                    {'name': 'workflow2',
                     'submission': 'submission2',
                     'id': 'id2',
                     'status': 'Running',
                     'start': 'start2',
                     'end': 'end2'}
                ],
                'totalResultsCount': 2}

        mock_request.post('{}/query'.format(self.url), json=_request_callback)

        query_dict = {
            'status': ['Running', 'Failed'],
            'label': {
                'label_key1': 'label_value1',
                'label_key2': 'label_value2'
            }
        }
        result = cromwell_tools.query_workflows(self.url, query_dict, caas_key=self.caas_key)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['totalResultsCount'], 2)

    def test_compose_query_params_can_compose_simple_query_dicts(self):
        query_dict = {'status': 'Running',
                      'start': '2018-01-01T00:00:00.000Z',
                      'end': '2018-01-01T12:00:00.000Z',
                      'label': {'Comment': 'test'}
                      }

        expect_params = [
            {'status': 'Running'},
            {'start': '2018-01-01T00:00:00.000Z'},
            {'end': '2018-01-01T12:00:00.000Z'},
            {'label': 'Comment:test'}
        ]

        self.assertEqual(sorted(cromwell_tools._compose_query_params(query_dict)), sorted(expect_params))

    def test_compose_query_params_can_compose_nested_query_dicts(self):
        query_dict = {'status': ['Running', 'Failed', 'Submitted'],
                      'start': '2018-01-01T00:00:00.000Z',
                      'end': '2018-01-01T12:00:00.000Z',
                      'label': {'Comment1': 'test1',
                                'Comment2': 'test2',
                                'Comment3': 'test3'}
                      }

        expect_params = [
            {'status': 'Running'},
            {'status': 'Failed'},
            {'status': 'Submitted'},
            {'start': '2018-01-01T00:00:00.000Z'},
            {'end': '2018-01-01T12:00:00.000Z'},
            {'label': 'Comment1:test1'},
            {'label': 'Comment2:test2'},
            {'label': 'Comment3:test3'}
        ]
        self.assertCountEqual(cromwell_tools._compose_query_params(query_dict), expect_params)

    @requests_mock.mock()
    def test_start_workflow(self, mock_request):
        """Unit test using mocks
        """

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {'request': {'body': "content"}}

        # Check request actions
        mock_request.post(self.url, json=_request_callback)
        result = cromwell_tools.start_workflow(
            self.wdl_file, self.inputs_file, self.url, self.options_file, self.inputs_file2, self.zip_file, self.user,
            self.password, label=self.label, on_hold=self.on_hold)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers.get('test'), 'header')

    @requests_mock.mock()
    def test_start_workflow_retries_on_error(self, mock_request):
        def _request_callback(request, context):
            context.status_code = 500
            context.headers['test'] = 'header'
            return {'status': 'error', 'message': 'Internal Server Error'}

        # Make the test complete faster by limiting the number of retries
        cromwell_tools.start_workflow.retry.stop = stop_after_attempt(3)

        # Check request actions
        mock_request.post(self.url, json=_request_callback)
        with self.assertRaises(requests.HTTPError):
            result = cromwell_tools.start_workflow(
                self.wdl_file, self.inputs_file, self.url, self.options_file, self.inputs_file2, self.zip_file,
                self.user, self.password, label=self.label, on_hold=self.on_hold)
            self.assertNotEqual(mock_request.call_count, 1)

        # Reset default retry value
        cromwell_tools.start_workflow.retry.stop = stop_after_delay(20)

    @requests_mock.mock()
    @mock.patch('cromwell_tools.cromwell_tools.generate_auth_header_from_key_file')
    def test_start_workflow_in_cromwell_as_a_service(self, mock_request, mock_header):
        mock_header.return_value = {"Authorization": "bearer fake_token"}

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {'request': {'body': "content"}}

        # Check request actions
        mock_request.post(self.url, json=_request_callback)
        result = cromwell_tools.start_workflow(
            self.wdl_file, self.inputs_file, self.url, self.options_file, self.inputs_file2, self.zip_file,
            caas_key=self.caas_key, label=self.label, on_hold=self.on_hold)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers.get('test'), 'header')

    @requests_mock.mock()
    def test_release_workflow_returns_200(self, mock_request):
        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {
                'id': request.url.split('/')[-2],
                'status': 'Submitted'
            }

        mock_request.post('{0}/{1}/releaseHold'.format(self.url, self.workflow_id), json=_request_callback)
        result = cromwell_tools.release_workflow(self.url, self.workflow_id, cromwell_user=self.user,
                                                 cromwell_password=self.password)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['id'], self.workflow_id)
        self.assertEqual(result.json()['status'], 'Submitted')

    @requests_mock.mock()
    def test_release_workflow_that_is_not_on_hold_returns_error(self, mock_request):
        def _request_callback(request, context):
            context.status_code = 403
            context.headers['test'] = 'header'
            return {
                'status': 'error',
                'message': 'Couldn\'t change status of workflow {} to \'Submitted\' because the workflow is not in \'On Hold\' state'.format(
                    request.url.split('/')[-2])
            }

        mock_request.post('{0}/{1}/releaseHold'.format(self.url, self.workflow_id), json=_request_callback)

        with self.assertRaises(requests.exceptions.HTTPError):
            cromwell_tools.release_workflow(self.url, self.workflow_id, cromwell_user=self.user,
                                            cromwell_password=self.password)

    @requests_mock.mock()
    @mock.patch('cromwell_tools.cromwell_tools.generate_auth_header_from_key_file')
    def test_release_workflow_returns_200_in_cromwell_as_a_service(self, mock_request, mock_header):
        mock_header.return_value = {"Authorization": "bearer fake_token"}

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {
                'id': request.url.split('/')[-2],
                'status': 'Submitted'
            }

        mock_request.post('{0}/{1}/releaseHold'.format(self.url, self.workflow_id), json=_request_callback)
        result = cromwell_tools.release_workflow(self.url, self.workflow_id, caas_key=self.caas_key)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['id'], self.workflow_id)
        self.assertEqual(result.json()['status'], 'Submitted')

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

    @requests_mock.mock()
    @mock.patch('cromwell_tools.cromwell_tools.generate_auth_header_from_key_file')
    def test_get_workflow_statuses_in_cromwell_as_a_service(self, mock_request, mock_header):
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
        result = cromwell_tools.get_workflow_statuses(ids, self.url, caas_key=self.caas_key)
        self.assertIn('Succeeded', result)

    @requests_mock.mock()
    def test_download_http_raises_error_on_bad_status_code(self, mock_request):

        def _request_callback(request, context):
            context.status_code = 404
            return 'Not found'

        fake_url = 'https://fake_url'
        mock_request.get(fake_url, json=_request_callback)

        with self.assertRaises(requests.HTTPError):
            cromwell_tools.download_http(fake_url)

    @requests_mock.mock()
    def test_download_http_no_error_on_200(self, mock_request):

        def _request_callback(request, context):
            context.status_code = 200
            return 'foo'

        fake_url = 'https://fake_url'

        mock_request.get(fake_url, json=_request_callback)
        try:
            cromwell_tools.download_http(fake_url)
        except requests.HTTPError:
            self.fail('Raised HTTPError for status 200')

    @requests_mock.mock()
    def test_download_http_no_error_on_301(self, mock_request):

        def _request_callback(request, context):
            context.status_code = 301
            return 'foo'

        fake_url = 'https://fake_url'
        mock_request.get(fake_url, json=_request_callback)
        try:
            cromwell_tools.download_http(fake_url)
        except requests.HTTPError:
            self.fail('Raised HTTPError for status 301')

    def test_download_to_map(self):
        """Test download_to_map with local files to ensure it builds the map of paths to contents correctly"""
        urls = ['data/a.txt', 'data/b.txt']
        urls_to_content = cromwell_tools.download_to_map(urls)
        self.assertIn('data/a.txt', urls_to_content)
        self.assertIn('data/b.txt', urls_to_content)
        self.assertEqual(urls_to_content['data/a.txt'], 'aaa\n')
        self.assertEqual(urls_to_content['data/b.txt'], 'bbb\n')

    def test_make_zip_in_memory(self):
        """Test make_zip_in_memory produces an in-memory zip file with the expected contents"""

        # Encoding the values below gives more realistic inputs for this test.
        # It gives us str instances in Python 2 and bytes instances in Python 3,
        # which is what is actually received respectively in these two versions by
        # make_zip_in_memory.
        urls_to_content = {
            'data/a.txt': 'aaa\n'.encode('utf-8'),
            'data/b.txt': 'bbb\n'.encode('utf-8')
        }
        bytes_buf = cromwell_tools.make_zip_in_memory(urls_to_content)
        with zipfile.ZipFile(bytes_buf, 'r') as zf:
            with zf.open('a.txt') as f1:
                f1_contents = f1.read()
            with zf.open('b.txt') as f2:
                f2_contents = f2.read()
        self.assertEqual(f1_contents, b'aaa\n')
        self.assertEqual(f2_contents, b'bbb\n')

    def test_validate_cromwell_label_on_invalid_labels_object(self):
        self.assertRaises(ValueError, cromwell_tools.validate_cromwell_label,
                          self.invalid_labels)

    def test_validate_cromwell_label_on_invalid_labels_str_object(self):
        self.assertRaises(ValueError, cromwell_tools.validate_cromwell_label,
                          json.dumps(self.invalid_labels))

    def test_validate_cromwell_label_on_invalid_labels_bytes_object(self):
        self.assertRaises(ValueError, cromwell_tools.validate_cromwell_label,
                          json.dumps(self.invalid_labels).encode('utf-8'))

    def test_validate_cromwell_label_on_valid_labels_object(self):
        self.assertIsNone(cromwell_tools.validate_cromwell_label(self.valid_labels))

    def test_validate_cromwell_label_on_valid_labels_str_object(self):
        self.assertIsNone(cromwell_tools.validate_cromwell_label(json.dumps(self.valid_labels)))

    def test_validate_cromwell_label_on_valid_labels_bytes_object(self):
        self.assertIsNone(cromwell_tools.validate_cromwell_label(json.dumps(self.valid_labels).encode('utf-8')))

    def test_localize_file_https(self):
        temporary_directory = tempfile.mkdtemp()
        # grab this file from the master branch of the cromwell-tools repository
        target = ('https://raw.githubusercontent.com/broadinstitute/cromwell-tools/'
                  'v0.3.1/cromwell_tools/tests/test_cromwell_tools.py')
        cromwell_tools._localize_file(target, temporary_directory)
        localized_file = os.path.join(temporary_directory, os.path.basename(target))

        # verify the file was downloaded and that it contains some content we expect
        assert os.path.isfile(localized_file)
        with open(localized_file, 'r') as f:
            assert 'cromwell_tools' in f.read()


class TestValidate(unittest.TestCase):

    def test_localize_file(self):
        temporary_directory = tempfile.mkdtemp()

        # test that we can localize both local and https files. Use this file as a convenient target
        targets = [
            'https://raw.githubusercontent.com/broadinstitute/cromwell-tools/master/'
            'cromwell_tools/tests/test_cromwell_tools.py',
            __file__
        ]
        for target in targets:
            cromwell_tools._localize_file(target, temporary_directory)
            localized_file = os.path.join(temporary_directory, os.path.basename(target))

            # verify the file was localized and that it contains some expected content
            assert os.path.isfile(localized_file)
            with open(localized_file, 'r') as f:
                assert 'cromwell_tools' in f.read()
            os.remove(localized_file)

    def test_validate_wdl(self):
        # change dir so we can leverage relative paths to data
        cwd = os.getcwd()
        test_directory = os.path.dirname(__file__)
        os.chdir(test_directory)

        womtool = os.environ['WOMTOOL']
        wdl = 'data/test_workflow.wdl'
        dependencies_json = 'data/test_dependencies.json'
        cromwell_tools.validate_workflow(wdl, womtool, dependencies_json)

        # put the directory back how we found it
        os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
