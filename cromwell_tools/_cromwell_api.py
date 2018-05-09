"""
TODO: add some module docs
"""

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
    """Contains a set of classmethods that implement interfaces to cromwell REST API endpoints

    Methods:
    status(uuid, auth, **kwargs)
        get workflow status
    health(auth, **kwargs)
        get health of cromwell server
    run(auth, wdl_file, inputs_json, options_json, inputs2_json, dependencies_json, ... )
        run a new workflow
    metadata(uuid, auth, **kwargs)
        retrieve workflow metadata
    wait(uuid, auth)
        helper function that waits until workflow at uuid reaches a terminal status

    """

    # todo remove this if it is not critical for mocking
    requests = requests

    _status_endpoint = '/api/workflows/v1/{uuid}/status'
    _workflow_endpoint = '/api/workflows/v1'
    _metadata_endpoint = '/api/workflows/v1/{uuid}/metadata'
    _health_endpoint = '/api/engine/v1/status'

    _failed_statuses = ['Failed', 'Aborted', 'Aborting']

    @classmethod
    def status(cls, uuid, auth, **kwargs):
        """Get workflow status

        Args:
        uuid (str): workflow identifier
        auth (cromwell_tools._cromwell_auth.CromwellAuth): authentication class holding headers
            or auth information to a Cromwell server

        Returns:
        requests.Response: HTTP response from cromwell
        """
        return cls.requests.get(
            auth.url + cls._status_endpoint.format(uuid=uuid), auth=auth.auth, headers=auth.header)

    @classmethod
    def health(cls, auth, **kwargs):
        """Get Cromwell health

        Args:
        auth (cromwell_tools._cromwell_auth.CromwellAuth): authentication class holding headers or
            auth information to a Cromwell server

        Returns:
        requests.Response: HTTP response from cromwell
        """
        return cls.requests.get(
            auth.url + cls._health_endpoint, auth=auth.auth, headers=auth.header)

    @classmethod
    @retry(reraise=True, wait=wait_exponential(multiplier=1, max=10), stop=stop_after_delay(20))
    def run(cls, auth, wdl_file, inputs_json, options_json=None, inputs2_json=None,
            dependencies_json=None, collection_name=None, label=None, validate_labels=True,
            **kwargs):
        """Start workflow in Cromwell

        retry with exponentially increasing wait times if there are failure(s)

        Args:
        wdl_file (_io.BytesIO): wdl file containing the workflow to execute
        inputs_json (_io.BytesIO): file-like object containing input data in json format
        options_json (Optional[_io.BytesIO]): Cromwell configs file.
        inputs2_json (Optional[_io.BytesIO]): Inputs file 2.
        dependencies_json (Optional[_io.BytesIO]): Zip file containing dependencies.
        auth (cromwell_tools._cromwell_auth.CromwellAuth): authentication class holding headers or
            auth information to a Cromwell server
        collection_name (Optional[str]): Collection in SAM that the workflow should belong to.
        label (Optional[Union[str, _io.BytesIO]]): JSON file containing a collection of
            key/value pairs for workflow labels.
            # TODO verify these types are accurate
        validate_labels (Optional[bool]) If True, validate cromwell labels (default False)

        Returns:
        requests.Response: HTTP response from cromwell
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
        """helper function to parse a status response

        Args:
        response (requests.Response): status response from Cromwell

        Raises:
        WorkflowUnknownException: raised when Cromwell returns a status code != 200

        Returns:
        str: status response string
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
        """Wait until cromwell returns successfully for each provided workflow

        Given a list of workflow ids, wait until cromwell returns successfully for each status, or
        one of the workflows fails or is aborted.

        Args:
        workflow_ids (List): Workflow ids to wait for terminal status
        timeout_minutes (int): Maximum number of minutes to wait
        auth (cromwell_tools._cromwell_auth.CromwellAuth): Authentication class holding headers
            or auth information to a Cromwell server
        poll_interval_seconds (Optional[int]): Number of seconds between checks for workflow
            completion (default 30)
        verbose (Optional[bool]): If True, report to stdout when all workflows succeed
            (default True)

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

