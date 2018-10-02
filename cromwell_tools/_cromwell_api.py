"""
TODO: add some module docs
"""

import time

import json
import logging
import requests
from datetime import datetime, timedelta
from tenacity import retry, stop_after_delay, wait_exponential

from cromwell_tools._utilities import prepare_workflow_manifest, validate_cromwell_label


logger = logging.getLogger(__name__)


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

    _abort_endpoint = '/api/workflows/v1/{uuid}/abort'

    _status_endpoint = '/api/workflows/v1/{uuid}/status'

    _workflow_endpoint = '/api/workflows/v1'

    _metadata_endpoint = '/api/workflows/v1/{uuid}/metadata'

    _health_endpoint = '/api/engine/v1/status'

    _release_hold_endpoint = 'api/workflows/v1/{uuid}/releaseHold'

    _query_endpoint = 'api/workflows/v1/query'

    _failed_statuses = ('Failed', 'Aborted', 'Aborting')

    _cromwell_exclusive_query_keys = {'end', 'includeSubworkflows', 'start', 'submission'}

    _cromwell_inclusive_query_keys = {'additionalQueryResultFields', 'excludeLabelAnd', 'excludeLabelOr',
                                      'id', 'includeSubworkflows', 'label', 'labelor', 'name', 'status'}

    _cromwell_query_keys = _cromwell_exclusive_query_keys.union(_cromwell_inclusive_query_keys)

    @classmethod
    def abort(cls, uuid, auth):
        """Request Cromwell to abort a running workflow by UUID.

        Args:
            uuid (str): A Cromwell workflow UUID, which is the workflow identifier.
            auth (cromwell_tools._cromwell_auth.CromwellAuth): The authentication class holding headers or auth
                information to a Cromwell server.
        Returns:
            requests.Response: HTTP response from Cromwell.
        """
        return cls.requests.post(url=auth.url + cls._abort_endpoint.format(uuid=uuid),
                                 auth=auth.auth,
                                 headers=auth.header)

    @classmethod
    def status(cls, uuid, auth):
        """Retrieves the current state for a workflow by UUID.

        Args:
            uuid (str): A Cromwell workflow UUID, which is the workflow identifier.
            auth (cromwell_tools._cromwell_auth.CromwellAuth): The authentication class holding headers or auth
                information to a Cromwell server.

        Returns:
            requests.Response: HTTP response from Cromwell.
        """
        return cls.requests.get(url=auth.url + cls._status_endpoint.format(uuid=uuid),
                                auth=auth.auth,
                                headers=auth.header)

    @classmethod
    def health(cls, auth):
        """Return the current health status of any monitored subsystems of the Cromwell Server.

        Args:
            auth (cromwell_tools._cromwell_auth.CromwellAuth): authentication class holding headers or auth
                information to a Cromwell server.

        Returns:
            requests.Response: HTTP response from Cromwell.
        """
        return cls.requests.get(url=auth.url + cls._health_endpoint,
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
            wdl_file (_io.BytesIO or str): The workflow source file to submit for execution. From version 35,
            Cromwell starts
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

        response = cls.requests.post(url=auth.url + cls._workflow_endpoint,
                                     files=files,
                                     auth=auth.auth,
                                     headers=auth.header)
        response.raise_for_status()

        return response

    @classmethod
    def wait(cls, workflow_ids, timeout_minutes, auth, poll_interval_seconds=30, verbose=True):
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

    @classmethod
    def release_hold(cls, uuid, auth):
        """Request Cromwell to release the hold on a workflow.

        It will switch the status of a workflow from ‘On Hold’ to ‘Submitted’ so it can be picked for running. For
        a workflow that was not submitted with `workflowOnHold = true`, Cromwell will ignore the request.

        Args:
            uuid: A Cromwell workflow UUID, which is the workflow identifier. The workflow is expected to have
                `On Hold` status.
            auth (cromwell_tools._cromwell_auth.CromwellAuth): The authentication class holding headers or auth
                information to a Cromwell server.

        Returns:
            response (requests.Response): HTTP response from Cromwell.

        """
        response = cls.requests.post(url=auth.url + cls._release_hold_endpoint.format(uuid=uuid),
                                     auth=auth.auth,
                                     headers=auth.header)
        return response

    @classmethod
    def query(cls, query_dict, auth):
        """
        TODO: Given that Cromwell-as-a-Service blocks a set of features that are available in Cromwell, e.g. 'labelor',
        for security concerns, the first iteration of this API doesn't come up with the advanced query keys of the
        Cromwell except a set of necessary ones. However, we need to implement this for completeness and keep an eye
        on the compatibility between CaaS and Cromwell.

        _All of the query keys will be used in an OR manner, except the keys within `labels`, which are defined in
        an AND relation_ For instance, [{'status': 'Succeeded'}, {'status': 'Failed'}] will give you all of the
        workflows that in either `Succeeded` or `Failed` statuses.

        Args:
            query_dict:
            auth (cromwell_tools._cromwell_auth.CromwellAuth): The authentication class holding headers or auth
                information to a Cromwell server.

        Returns:
            response (requests.Response): HTTP response from Cromwell.

        """
        query_params = cls._compose_query_params(query_dict)
        response = cls.requests.post(url=auth.url + cls._query_endpoint,
                                     json=query_params,
                                     auth=auth.auth,
                                     headers=auth.header)
        return response

    @classmethod
    def _compose_query_params(cls, query_dict):
        """Helper function to compose the query params that could be accepted by Cromwell.

        This function will parse and compose the query params for Cromwell's /query endpoint from an user's input
        query dictionary. It also provides very basic inputs validation so users don't have to wait for the error
        response from Cromwell for a long time.

        The query keys should be one of the following strings in the `cls._cromwell_query_keys` set, otherwise
        they will be ignore by this function.

        In general, this method is expecting the input query dictionary follows a basic
        structure like below:

        ```
        query_dict = {
            'label': {
                'cromwell-workflow-id': 'cromwell-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
            },
            'status': ['Running', 'Succeeded'],
            'id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            'additionalQueryResultFields': 'labels',
            'submission': '2018-01-01T00:01:01.410150Z',
            'start': '2018-01-01T01:01:01.410150Z',
            'end': '2018-01-01T02:01:01.410150Z',
            'name': ['WorkflowName1', 'WorkflowName2'],
            'additionalQueryResultFields': ['labels', 'parentWorkflowId'],
            'includeSubworkflows': True
        }
        ```

        which will be converted to the following query parameters:

        ```
        query_params = [
            {'label': 'cromwell-workflow-id:cromwell-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'},
            {'status': 'Running'},
            {'status': 'Succeeded'},
            {'id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'},
            {'additionalQueryResultFields': 'labels'},
            {'submission': '2018-01-01T00:01:01.410150Z'},
            {'start': '2018-01-01T01:01:01.410150Z'},
            {'end': '2018-01-01T02:01:01.410150Z'},
            {'name': 'WorkflowName1'},
            {'name': 'WorkflowName2'},
            {'additionalQueryResultFields': 'labels'},
            {'additionalQueryResultFields': 'parentWorkflowId'},
            {'includeSubworkflows': 'true'}
        ]
        ```
        Args:
            query_dict (dict): A dictionary representing the query key-value paris. The keys should be accepted by the
                Cromwell or they will get ignored. The values could be str, list or dict.

        Returns:
            query_params (List[dict]): A composed lsit of query objects.
        """
        if not isinstance(query_dict, dict):
            raise TypeError('A valid dictionary with query keys is required!')

        query_params = []
        for k, v in query_dict.items():
            if k in cls._cromwell_query_keys:
                if k is 'label' and isinstance(v, dict):
                    query_params.extend([
                        {'label': label_key + ':' + label_value} for label_key, label_value in v.items()
                    ])
                elif isinstance(v, list):
                    if k in cls._cromwell_exclusive_query_keys:
                        raise ValueError('{} cannot be specified multiple times!'.format(k))
                    query_params.extend([
                        {k: json.dumps(val)} if not isinstance(val, str) else {k: val} for val in set(v)
                    ])
                else:
                    query_params.append(
                            {k: json.dumps(v)} if not isinstance(v, str) else {k: v}
                    )
            else:
                logger.info('{} is not an allowed query key in Cromwell, will be ignored in this query.'.format(k))
        return query_params

    @staticmethod
    def _parse_status(response):
        """Helper function to parse a status response.

        Args:
            response (requests.Response): A status response object from Cromwell.

        Raises:
            WorkflowUnknownException: This will be raised when Cromwell returns a status code != 200.

        Returns:
            str: String representing status response.
        """
        if response.status_code != 200:
            raise WorkflowUnknownException(
                    'Status could not be determined, endpoint returned {0}'.format(
                            response.status_code))
        else:
            return response.json()['status']
