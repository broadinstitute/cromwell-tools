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


class TestUtils(unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()
