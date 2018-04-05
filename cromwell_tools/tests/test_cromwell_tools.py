#!/usr/bin/env python
import io
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
import zipfile
import os
import json
from tenacity import stop_after_delay, stop_after_attempt


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
        self.url = "https://fake_url"
        self.user = "fake_user"
        self.password = "fake_password"

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
            self.password, self.label)
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
                self.user, self.password, self.label)
            self.assertNotEqual(mock_request.call_count, 1)

        # Reset default retry value
        cromwell_tools.start_workflow.retry.stop = stop_after_delay(20)

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


if __name__ == '__main__':
    unittest.main()
