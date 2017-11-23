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


class TestUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Change to test directory, as tests may have been invoked from another dir
        dir = os.path.abspath(os.path.dirname(__file__))
        os.chdir(dir)

    @requests_mock.mock()
    def test_start_workflow(self, mock_request):
        """Unit test using mocks
        """
        wdl_file = io.BytesIO(b"wdl_file_content")
        zip_file = io.BytesIO(b"zip_file_content")
        inputs_file = io.BytesIO(b"inputs_file_content")
        inputs_file2 = io.BytesIO(b"inputs_file2_content")
        options_file = io.BytesIO(b"options_file_content")

        def _request_callback(request, context):
            context.status_code = 200
            context.headers['test'] = 'header'
            return {'request': {'body': "content"}}

        url = "https://fake_url"
        user = "fake_user"
        password = "fake_password"
        # Check request actions
        mock_request.post(url, json=_request_callback)
        result = cromwell_tools.start_workflow(wdl_file, zip_file, inputs_file,
            inputs_file2, options_file, url, user, password)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers.get('test'), 'header')

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
        urls_to_content = {
            'data/a.txt': 'aaa\n',
            'data/b.txt': 'bbb\n'
        }
        bytes_buf = cromwell_tools.make_zip_in_memory(urls_to_content)
        with zipfile.ZipFile(bytes_buf, 'r') as zf:
            with zf.open('a.txt') as f1:
                f1_contents = f1.read()
            with zf.open('b.txt') as f2:
                f2_contents = f2.read()
        self.assertEqual(f1_contents, 'aaa\n')
        self.assertEqual(f2_contents, 'bbb\n')


if __name__ == '__main__':
    unittest.main()
