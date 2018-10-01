"""
TODO: add some module docs
"""

import time

import requests
from datetime import datetime, timedelta
from tenacity import retry, stop_after_delay, wait_exponential

from cromwell_tools._utilities import prepare_workflow_manifest, validate_cromwell_label


class WorkflowFailedException(Exception):
    pass


class WorkflowUnknownException(Exception):
    pass


# todo functools partial for get, post (set the authenticate commands)
class CromwellAPI(object):
    """Contains a set of classmethods that implement interfaces to cromwell REST API endpoints.
    """

    # TODO: remove this if it is not critical for mocking
    requests = requests

    _status_endpoint = '/api/workflows/v1/{uuid}/status'
    _workflow_endpoint = '/api/workflows/v1'
    _metadata_endpoint = '/api/workflows/v1/{uuid}/metadata'
    _health_endpoint = '/api/engine/v1/status'

    _failed_statuses = ['Failed', 'Aborted', 'Aborting']

    @classmethod
    def status(cls, uuid, auth, **kwargs):
        """Retrieves the current state for a workflow by UUID.

        Args:
            uuid (str): A Cromwell workflow UUID, which is the workflow identifier.
            auth (cromwell_tools._cromwell_auth.CromwellAuth): The authentication class holding headers or auth
                information to a Cromwell server.

        Returns:
            requests.Response: HTTP response from Cromwell.
        """
        return cls.requests.get(auth.url + cls._status_endpoint.format(uuid=uuid),
                                auth=auth.auth,
                                headers=auth.header)

    @classmethod
    def health(cls, auth, **kwargs):
        """Return the current health status of any monitored subsystems of the Cromwell Server.

        Args:
            auth (cromwell_tools._cromwell_auth.CromwellAuth): authentication class holding headers or auth
                information to a Cromwell server.

        Returns:
            requests.Response: HTTP response from Cromwell.
        """
        return cls.requests.get(auth.url + cls._health_endpoint,
                                auth=auth.auth,
                                headers=auth.header)

    @classmethod
    @retry(reraise=True,
           wait=wait_exponential(multiplier=1, max=10),
           stop=stop_after_delay(20))
    def submit(cls, auth, wdl_file, inputs_json, options_json=None, inputs2_json=None, dependencies_json=None,
            collection_name=None, label=None, validate_labels=True, **kwargs):
        """Submits a workflow to Cromwell.

        This function has retry policy with exponentially increasing wait times if there are failure(s).

        Args:
            wdl_file (_io.BytesIO or str): The workflow source file to submit for execution. From version 35, Cromwell starts
                to accept URL to the WDL file besides actual WDL files.
            inputs_json (_io.BytesIO): File-like object containing input data in JSON format.
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
            requests.Response: HTTP response from Cromwell.
        """
        manifest = prepare_workflow_manifest(
                wdl_file, inputs_json, dependencies_json, options_json, inputs2_json)

        if validate_labels and label is not None:
            validate_cromwell_label(label)

        files = {
            'workflowSource': wdl_file,
            'workflowInputs': inputs_json,
        }

        # TODO: these three checks should be done inside prepare workflow manifest?
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
