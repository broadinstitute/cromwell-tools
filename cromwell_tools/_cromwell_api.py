from datetime import datetime, timedelta
import time

import requests
import requests_mock

from tenacity import retry, wait_exponential, stop_after_delay
from ._utilities import validate_cromwell_label, prepare_workflow_manifest


class WorkflowFailedException(Exception):
    pass


class WorkflowUnknownException(Exception):
    pass


# todo functools partial for get, post (set the authenticate commands)
class CromwellAPI:

    # todo remove this if it is not critical for mocking
    requests = requests

    _status_endpoint = '/api/workflows/v1/{uuid}/status'
    _workflow_endpoint = '/api/workflows/v1'
    _metadata_endpoint = '/api/workflows/v1/{uuid}/metadata'
    _health_endpoint = '/api/engine/v1'

    _failed_statuses = ['Failed', 'Aborted', 'Aborting']

    @classmethod
    def status(cls, uuid, auth, **kwargs):
        return cls.requests.get(
            auth.url + cls._status_endpoint.format(uuid=uuid), auth=auth.auth, headers=auth.header)

    @classmethod
    def health(cls, auth, **kwargs):
        return cls.requests.get(
            auth.url + cls._health_endpoint, auth=auth.auth, headers=auth.header)

    @classmethod
    @retry(reraise=True, wait=wait_exponential(multiplier=1, max=10), stop=stop_after_delay(20))
    def run(cls, auth, wdl_file, inputs_json, options_json=None, inputs2_json=None,
            dependencies_json=None, collection_name=None, label=None, validate_labels=True,
            **kwargs):
        """Start workflow in Cromwell

        retry with exponentially increasing wait times if there are failure(s)

        :param _io.BytesIO wdl_file: wdl file.
        :param _io.BytesIO inputs_json: inputs file.
        :param _io.BytesIO options_json: (optional) cromwell configs file.
        :param _io.BytesIO inputs2_json: (optional) inputs file 2.
        :param _io.BytesIO dependencies_json: (optional) zip file containing dependencies.
        :param CromwellAuth auth: authentication to a cromwell instance
        :param str collection_name: (optional) collection in SAM that the workflow should belong to.
        :param str|_io.BytesIO label: (optional) JSON file containing a collection of key/value
            pairs for workflow labels.
        :param bool validate_labels: (optional) Whether to validate labels or not, using
            cromwell-tools' built-in validators. It is set to True by default.

        :return requests.Response response: HTTP response from cromwell.
        """
        manifest = prepare_workflow_manifest(
            wdl_file, inputs_json, dependencies_json, options_json, inputs2_json)

        if validate_labels and label is not None:
            validate_cromwell_label(label)

        files = {
            'workflowSource': wdl_file,
            'workflowInputs': inputs_json,
        }

        # todo these three checks should be done inside prepare workflow manifest?
        if 'inputs2_json' in manifest:
            files['workflowInputs_2'] = manifest['inputs2_json']
        if 'dependencies_json' in manifest:
            files['workflowDependencies'] = manifest['dependencies_json']
        if 'options_json' in manifest:
            files['workflowOptions'] = manifest['options_json']

        if label:
            files['labels'] = label
        if collection_name:  # todo this check should happen elsewhere, related to caas
            files['collectionName'] = collection_name

        response = cls.requests.post(
            auth.url + cls._workflow_endpoint, files=files, auth=auth.auth, headers=auth.header)
        response.raise_for_status()

        return response

    @staticmethod
    def _parse_status(response):
        """

        :param response:
        :return:
        """
        if response.status_code != 200:
            raise WorkFlowUnknownException(
                'Status could not be determined, endpoint returned {0}'.format(
                    response.return_code))
        else:
            return response.json()['status']

    @classmethod
    def wait(
            cls, workflow_ids, timeout_minutes, auth, poll_interval_seconds=30, verbose=True,
            **kwargs):
        """ wait until cromwell returns successfully for each provided workflow
        Given a list of workflow ids, wait until cromwell returns successfully for each status, or
        one of the workflows fails or is aborted.

        :param list workflow_ids:
        :param int timeout_minutes:
        :param int poll_interval_seconds: number of seconds between checks for workflow completion
          (default 30)
        :param CromwellAuth auth:
        :param bool verbose:

        :return:
        """
        start = datetime.now()
        timeout = timedelta(minutes=int(timeout_minutes))

        while True:

            if datetime.now() - start > timeout:
                msg = 'Unfinished workflows after {0} minutes.'
                raise Exception(msg.format(timeout))

            all_succeeded = True
            for uuid in workflow_ids:
                response = cls.status(uuid, auth)
                status = cls._parse_status(response)
                if status in cls._failed_statuses:
                    raise WorkflowFailedException('Workflow {0} returned status {1}'.format(
                        uuid, status))
                elif status != 'Succeeded':
                    all_succeeded = False

            if all_succeeded:
                if verbose:
                    print('All workflows succeeded!')
                return

            time.sleep(poll_interval_seconds)



