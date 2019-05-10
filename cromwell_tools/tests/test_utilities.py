import io
import json
import os
import requests
import requests_mock
import six
import tempfile
import unittest
import zipfile


six.add_move(six.MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock  # noqa

from cromwell_tools import utilities as utils  # noqa
from cromwell_tools.cromwell_auth import CromwellAuth  # noqa


class TestUtilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Change to test directory, as tests may have been invoked from another dir
        dir_ = os.path.abspath(os.path.dirname(__file__))
        os.chdir(dir_)

    @staticmethod
    def _load_test_data_as_BytesIO(path):
        with open(path, 'rb') as fp:
            stream = io.BytesIO(fp.read())
        return stream

    def setUp(self):
        self.invalid_labels = {
            "0-label-key-1": "0-label-value-1",
            "the-maximum-allowed-character-length-for-label-pairs-is-sixty-three": "cromwell-please-dont-validate-these-labels",
            "": "not a great label key",
            "Comment": "This-is-a-test-label",
        }
        self.valid_labels = {
            "label-key-1": "label-value-1",
            "label-key-2": "label-value-2",
            "only-key": "",
            "fc-id": "0123-abcd-4567-efgh",
            "comment": "this-is-a-test-label",
        }
        self.wdl_file_path = 'data/test_workflow.wdl'
        self.wdl_file_BytesIO = self._load_test_data_as_BytesIO(self.wdl_file_path)

        self.inputs_file_path = 'data/test_inputs1.json'
        self.inputs_file_BytesIO = self._load_test_data_as_BytesIO(
            self.inputs_file_path
        )

        self.inputs_file_path_list = [
            'data/test_inputs1.json',
            'data/test_inputs2.json',
        ]
        self.inputs_file_BytesIO_list = [
            self._load_test_data_as_BytesIO(f) for f in self.inputs_file_path_list
        ]

        self.options_file_path = 'data/test_options.json'
        self.options_file_BytesIO = self._load_test_data_as_BytesIO(
            self.options_file_path
        )

        self.label_file_path = 'data/test_labels.json'
        self.label_file_BytesIO = self._load_test_data_as_BytesIO(self.label_file_path)

        self.deps_zip_file_path = 'data/test_deps.zip'
        self.deps_files_paths_list = ['data/test_task.wdl']
        self.deps_zip_file_BytesIO = self._load_test_data_as_BytesIO(
            self.deps_zip_file_path
        )

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
        self.assertEqual(urls_to_content['data/a.txt'], b'aaa\n')
        self.assertEqual(urls_to_content['data/b.txt'], b'bbb\n')

    def test_make_zip_in_memory(self):
        """Test make_zip_in_memory produces an in-memory zip file with the expected contents"""

        # Encoding the values below gives more realistic inputs for this test.
        # It gives us str instances in Python 2 and bytes instances in Python 3,
        # which is what is actually received respectively in these two versions by
        # make_zip_in_memory.
        urls_to_content = {
            'data/a.txt': 'aaa\n'.encode('utf-8'),
            'data/b.txt': 'bbb\n'.encode('utf-8'),
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
        self.assertRaises(
            ValueError, utils.validate_cromwell_label, self.invalid_labels
        )

    def test_validate_cromwell_label_on_invalid_labels_str_object(self):
        self.assertRaises(
            ValueError, utils.validate_cromwell_label, json.dumps(self.invalid_labels)
        )

    def test_validate_cromwell_label_on_invalid_labels_bytes_object(self):
        self.assertRaises(
            ValueError,
            utils.validate_cromwell_label,
            json.dumps(self.invalid_labels).encode('utf-8'),
        )

    def test_validate_cromwell_label_on_valid_labels_object(self):
        self.assertIsNone(utils.validate_cromwell_label(self.valid_labels))

    def test_validate_cromwell_label_on_valid_labels_str_object(self):
        self.assertIsNone(utils.validate_cromwell_label(json.dumps(self.valid_labels)))

    def test_validate_cromwell_label_on_valid_labels_bytes_object(self):
        self.assertIsNone(
            utils.validate_cromwell_label(json.dumps(self.valid_labels).encode('utf-8'))
        )

    def test_localize_file(self):
        temporary_directory = tempfile.mkdtemp()
        # test that we can localize both local and https files. Use this file as a convenient target
        targets = (
            'https://raw.githubusercontent.com/broadinstitute/cromwell-tools/'
            'v0.5.0/cromwell_tools/tests/test_cromwell_tools.py',
            __file__,
        )
        for target in targets:
            utils._localize_file(target, temporary_directory)
            localized_file = os.path.join(temporary_directory, os.path.basename(target))

            # verify the file was downloaded and that it contains some content we expect
            assert os.path.isfile(localized_file)
            with open(localized_file, 'r') as f:
                assert 'cromwell_tools' in f.read()
            os.remove(localized_file)

    def test_prepare_workflow_manifest_works_for_wdl_file_with_filepath(self):
        manifest = utils.prepare_workflow_manifest(wdl_file=self.wdl_file_path)
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowSource'].getvalue()
            == expected_manifest['workflowSource'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_wdl_file_with_BytesIO(self):
        manifest = utils.prepare_workflow_manifest(wdl_file=self.wdl_file_BytesIO)
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowSource'].getvalue()
            == expected_manifest['workflowSource'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_one_inputs_file_with_filepath(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, inputs_files=self.inputs_file_path
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowInputs': self.inputs_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowInputs'].getvalue()
            == expected_manifest['workflowInputs'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_one_inputs_file_with_BytesIO(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, inputs_files=self.inputs_file_BytesIO
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowInputs': self.inputs_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowInputs'].getvalue()
            == expected_manifest['workflowInputs'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_multiple_inputs_files_with_filepath(
        self
    ):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, inputs_files=self.inputs_file_path_list
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowInputs': self.inputs_file_BytesIO_list[0],
            'workflowInputs_2': self.inputs_file_BytesIO_list[1],
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowInputs'].getvalue()
            == expected_manifest['workflowInputs'].getvalue()
        )
        assert (
            manifest['workflowInputs_2'].getvalue()
            == expected_manifest['workflowInputs_2'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_multiple_inputs_files_with_BytesIO(
        self
    ):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, inputs_files=self.inputs_file_BytesIO_list
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowInputs': self.inputs_file_BytesIO_list[0],
            'workflowInputs_2': self.inputs_file_BytesIO_list[1],
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowInputs'].getvalue()
            == expected_manifest['workflowInputs'].getvalue()
        )
        assert (
            manifest['workflowInputs_2'].getvalue()
            == expected_manifest['workflowInputs_2'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_dependencies_file_with_filepath(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, dependencies=self.deps_zip_file_path
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowDependencies': self.deps_zip_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowDependencies'].getvalue()
            == expected_manifest['workflowDependencies'].getvalue()
        )

    def test_prepare_workflow_manifest_raises_an_error_for_dependencies_file_with_filepath_not_pointing_to_zip(
        self
    ):
        with self.assertRaises(ValueError):
            utils.prepare_workflow_manifest(
                wdl_file=self.wdl_file_path, dependencies="data/fake_test_deps.wdl"
            )

    def test_prepare_workflow_manifest_works_for_dependencies_file_with_filepath_in_a_list(
        self
    ):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, dependencies=[self.deps_zip_file_path]
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowDependencies': self.deps_zip_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowDependencies'].getvalue()
            == expected_manifest['workflowDependencies'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_dependencies_file_with_list_of_files(
        self
    ):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, dependencies=self.deps_files_paths_list
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowDependencies': self.deps_zip_file_BytesIO,
            'workflowOnHold': 'false',
        }
        with zipfile.ZipFile(manifest['workflowDependencies'], 'r') as zf:
            with zf.open('test_task.wdl') as dep_file:
                contents = io.BytesIO(dep_file.read())

        with zipfile.ZipFile(expected_manifest['workflowDependencies'], 'r') as zf:
            with zf.open('test_task.wdl') as dep_file:
                expected_contents = io.BytesIO(dep_file.read())

        # we have to unzip both of them to get the proper comparison during the test
        assert contents.getvalue() == expected_contents.getvalue()

    def test_prepare_workflow_manifest_works_for_dependencies_file_with_BytesIO(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, dependencies=self.deps_zip_file_BytesIO
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowDependencies': self.deps_zip_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowDependencies'].getvalue()
            == expected_manifest['workflowDependencies'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_collection_name(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, collection_name='test_collection'
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'collectionName': 'test_collection',
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowSource'].getvalue()
            == expected_manifest['workflowSource'].getvalue()
        )
        assert manifest['collectionName'] == expected_manifest['collectionName']

    def test_prepare_workflow_manifest_works_for_on_hold(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, on_hold=True
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowOnHold': 'true',
        }
        assert (
            manifest['workflowSource'].getvalue()
            == expected_manifest['workflowSource'].getvalue()
        )
        assert manifest['workflowOnHold'] == expected_manifest['workflowOnHold']

    def test_prepare_workflow_manifest_works_for_label_file_with_filepath(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, label_file=self.label_file_path
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'labels': self.label_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert manifest['labels'].getvalue() == expected_manifest['labels'].getvalue()

    def test_prepare_workflow_manifest_works_for_label_file_with_BytesIO(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, label_file=self.label_file_BytesIO
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'labels': self.label_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert manifest['labels'].getvalue() == expected_manifest['labels'].getvalue()

    def test_prepare_workflow_manifest_works_for_options_file_with_filepath(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, options_file=self.options_file_path
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowOptions': self.options_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowOptions'].getvalue()
            == expected_manifest['workflowOptions'].getvalue()
        )

    def test_prepare_workflow_manifest_works_for_options_file_with_BytesIO(self):
        manifest = utils.prepare_workflow_manifest(
            wdl_file=self.wdl_file_path, options_file=self.options_file_BytesIO
        )
        expected_manifest = {
            'workflowSource': self.wdl_file_BytesIO,
            'workflowOptions': self.options_file_BytesIO,
            'workflowOnHold': 'false',
        }
        assert (
            manifest['workflowOptions'].getvalue()
            == expected_manifest['workflowOptions'].getvalue()
        )

    def test_compose_oauth_options_for_jes_backend_cromwell_add_required_fields_to_workflow_options(
        self
    ):
        test_url = 'https://fake_url'
        test_service_account_key = 'data/fake_account_key.json'
        with open(test_service_account_key, 'r') as f:
            test_service_account_key_content = json.load(f)

        test_auth = CromwellAuth(
            url=test_url,
            header={"Authorization": "bearer fake_token"},
            auth=None,
            service_key_content=test_service_account_key_content,
        )

        result_options = utils.compose_oauth_options_for_jes_backend_cromwell(
            test_auth, self.options_file_BytesIO
        )
        result_options_in_dict = json.loads(result_options.getvalue())

        assert (
            result_options_in_dict['read_from_cache']
            == json.loads(self.options_file_BytesIO.getvalue())['read_from_cache']
        )
        assert (
            result_options_in_dict['google_project']
            == test_service_account_key_content['project_id']
        )
        assert (
            result_options_in_dict['google_compute_service_account']
            == test_service_account_key_content['client_email']
        )
        assert result_options_in_dict['user_service_account_json'] == json.dumps(
            test_service_account_key_content
        )

    def test_if_compose_oauth_options_for_jes_backend_cromwell_can_deal_with_null_workflow_options(
        self
    ):
        test_url = 'https://fake_url'
        test_service_account_key = 'data/fake_account_key.json'
        with open(test_service_account_key, 'r') as f:
            test_service_account_key_content = json.load(f)

        test_auth = CromwellAuth(
            url=test_url,
            header={"Authorization": "bearer fake_token"},
            auth=None,
            service_key_content=test_service_account_key_content,
        )

        result_options = utils.compose_oauth_options_for_jes_backend_cromwell(test_auth)
        result_options_in_dict = json.loads(result_options.getvalue())

        assert (
            result_options_in_dict['google_project']
            == test_service_account_key_content['project_id']
        )
        assert (
            result_options_in_dict['google_compute_service_account']
            == test_service_account_key_content['client_email']
        )
        assert result_options_in_dict['user_service_account_json'] == json.dumps(
            test_service_account_key_content
        )
