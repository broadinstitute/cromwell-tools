import json
import os
import requests
import requests_mock
import six
import tempfile
import unittest
import zipfile
import pytest


six.add_move(six.MovedModule('mock', 'mock', 'unittest.mock'))

from cromwell_tools import utilities as utils


class TestUtilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Change to test directory, as tests may have been invoked from another dir
        dir_ = os.path.abspath(os.path.dirname(__file__))
        os.chdir(dir_)
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

    @requests_mock.mock()
    def test_download_http_raises_error_on_bad_status_code(self, mock_request):

        def _request_callback(request, context):
            context.status_code = 404
            return 'Not found'

        fake_url = 'https://fake_url'
        mock_request.get(fake_url, json=_request_callback)

        with self.assertRaises(requests.HTTPError):
            utils.download_http(fake_url)

    @requests_mock.mock()
    def test_download_http_no_error_on_200(self, mock_request):

        def _request_callback(request, context):
            context.status_code = 200
            return 'foo'

        fake_url = 'https://fake_url'

        mock_request.get(fake_url, json=_request_callback)
        try:
            utils.download_http(fake_url)
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
            utils.download_http(fake_url)
        except requests.HTTPError:
            self.fail('Raised HTTPError for status 301')

    def test_download_to_map(self):
        """Test download_to_map with local files to ensure it builds the map of paths to contents correctly"""
        urls = ['data/a.txt', 'data/b.txt']
        urls_to_content = utils.download_to_map(urls)
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
        bytes_buf = utils.make_zip_in_memory(urls_to_content)
        with zipfile.ZipFile(bytes_buf, 'r') as zf:
            with zf.open('a.txt') as f1:
                f1_contents = f1.read()
            with zf.open('b.txt') as f2:
                f2_contents = f2.read()
        self.assertEqual(f1_contents, b'aaa\n')
        self.assertEqual(f2_contents, b'bbb\n')

    def test_validate_cromwell_label_on_invalid_labels_object(self):
        self.assertRaises(ValueError, utils.validate_cromwell_label,
                          self.invalid_labels)

    def test_validate_cromwell_label_on_invalid_labels_str_object(self):
        self.assertRaises(ValueError, utils.validate_cromwell_label,
                          json.dumps(self.invalid_labels))

    def test_validate_cromwell_label_on_invalid_labels_bytes_object(self):
        self.assertRaises(ValueError, utils.validate_cromwell_label,
                          json.dumps(self.invalid_labels).encode('utf-8'))

    def test_validate_cromwell_label_on_valid_labels_object(self):
        self.assertIsNone(utils.validate_cromwell_label(self.valid_labels))

    def test_validate_cromwell_label_on_valid_labels_str_object(self):
        self.assertIsNone(utils.validate_cromwell_label(json.dumps(self.valid_labels)))

    def test_validate_cromwell_label_on_valid_labels_bytes_object(self):
        self.assertIsNone(utils.validate_cromwell_label(json.dumps(self.valid_labels).encode('utf-8')))

    def test_localize_file_https(self):
        temporary_directory = tempfile.mkdtemp()
        # grab this file from the master branch of the cromwell-tools repository
        target = ('https://raw.githubusercontent.com/broadinstitute/cromwell-tools/'
                  'v0.3.1/cromwell_tools/tests/test_cromwell_tools.py')
        utils._localize_file(target, temporary_directory)
        localized_file = os.path.join(temporary_directory, os.path.basename(target))

        # verify the file was downloaded and that it contains some content we expect
        assert os.path.isfile(localized_file)
        with open(localized_file, 'r') as f:
            assert 'cromwell_tools' in f.read()
