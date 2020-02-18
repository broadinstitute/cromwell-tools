"""
TODO: add some module docs
TODO: once switched to support only Py3.7+, replace all 'cls'
type annotations with the actual Types, rather than using the strings.
This in Py3.6(-) is limited by the lack of Postponed Evaluation of Annotations, see:
https://www.python.org/dev/peps/pep-0563/
"""

import time

import io
import json
import logging
import requests
from datetime import datetime, timedelta

from cromwell_tools.cromwell_auth import CromwellAuth
from cromwell_tools import utilities
from cromwell_tools.utilities import validate_cromwell_label
from cromwell_tools import exceptions
from typing import List, Union, Dict


logger = logging.getLogger(__name__)

_failed_statuses = ('Failed', 'Aborted', 'Aborting')

_cromwell_exclusive_query_keys = {
    'end',
    'includeSubworkflows',
    'start',
    'submission',
    'page',
    'pageSize',
}

_cromwell_inclusive_query_keys = {
    'additionalQueryResultFields',
    'excludeLabelAnd',
    'excludeLabelOr',
    'id',
    'includeSubworkflows',
    'label',
    'labelor',
    'name',
    'status',
}

_cromwell_query_keys = _cromwell_exclusive_query_keys.union(
    _cromwell_inclusive_query_keys
)


# TODO: use functools partial for get, post (set the authenticate commands)
class CromwellAPI(object):
    """Contains a set of classmethods that implement interfaces to cromwell REST API endpoints."""

    # TODO: move the endpoints definitions to the corresponding functions after refactoring the unit tests and mocks
    _abort_endpoint = '/api/workflows/v1/{uuid}/abort'
    _status_endpoint = '/api/workflows/v1/{uuid}/status'
    _submit_endpoint = '/api/workflows/v1'
    _metadata_endpoint = '/api/workflows/v1/{uuid}/metadata'
    _health_endpoint = '/engine/v1/status'
    _release_hold_endpoint = '/api/workflows/v1/{uuid}/releaseHold'
    _query_endpoint = '/api/workflows/v1/query'
    _labels_endpoint = '/api/workflows/v1/{uuid}/labels'

    @classmethod
    def abort(
        cls: 'CromwellAPI',
        uuid: str,
        auth: CromwellAuth,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """Request Cromwell to abort a running workflow by UUID.

        Args:
            uuid: A Cromwell workflow UUID, which is the workflow identifier.
            auth: The authentication class holding headers or auth
                information to a Cromwell server.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """
        response = requests.post(
            url=auth.url + cls._abort_endpoint.format(uuid=uuid),
            auth=auth.auth,
            headers=auth.header,
        )

        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def metadata(
        cls: 'CromwellAPI',
        uuid: str,
        auth: CromwellAuth,
        includeKey: Union[List[str], str] = None,
        excludeKey: Union[List[str], str] = None,
        expandSubWorkflows: bool = False,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """Retrieve the workflow and call-level metadata for a specified workflow by UUID.

        Args:
            uuid: A Cromwell workflow UUID, which is the workflow identifier.
            auth: The authentication class holding headers or auth
                information to a Cromwell server.
            includeKey: When specified key(s) to include from the metadata. Matches any key
                starting with the value. May not be used with excludeKey.
            excludeKey: When specified key(s) to exclude from the metadata. Matches any key
                starting with the value. May not be used with includeKey.
            expandSubWorkflows: When true, metadata for sub workflows will be fetched
                and inserted automatically in the metadata response.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """

        if excludeKey and includeKey:
            raise ValueError('includeKey and excludeKey may not be specified together!')

        params = {'expandSubWorkflows': json.dumps(expandSubWorkflows)}

        if isinstance(excludeKey, str):
            logger.info('Adding %s to the request parameter list.' % excludeKey)
            params['excludeKey'] = [excludeKey]
        elif isinstance(excludeKey, list) and len(excludeKey) >= 1:
            params['excludeKey'] = excludeKey

        if isinstance(includeKey, str):
            logger.info('Adding %s to the request parameter list.' % includeKey)
            params['includeKey'] = [includeKey]
        elif isinstance(includeKey, list) and len(includeKey) >= 1:
            params['includeKey'] = includeKey

        response = requests.get(
            url=auth.url + cls._metadata_endpoint.format(uuid=uuid),
            auth=auth.auth,
            headers=auth.header,
            params=params,
        )

        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def status(
        cls: 'CromwellAPI',
        uuid: str,
        auth: CromwellAuth,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """Retrieves the current state for a workflow by UUID.

        Args:
            uuid: A Cromwell workflow UUID, which is the workflow identifier.
            auth: The authentication class holding headers or auth
                information to a Cromwell server.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """
        response = requests.get(
            url=auth.url + cls._status_endpoint.format(uuid=uuid),
            auth=auth.auth,
            headers=auth.header,
        )

        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def health(
        cls: 'CromwellAPI', auth: CromwellAuth, raise_for_status: bool = False
    ) -> requests.Response:
        """Return the current health status of any monitored subsystems of the Cromwell Server.

        Args:
            auth: authentication class holding headers or auth
                information to a Cromwell server.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """
        response = requests.get(
            url=auth.url + cls._health_endpoint, auth=auth.auth, headers=auth.header
        )

        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def submit(
        cls: 'CromwellAPI',
        auth: CromwellAuth,
        wdl_file: Union[str, io.BytesIO],
        inputs_files: Union[List[Union[str, io.BytesIO]], str, io.BytesIO] = None,
        options_file: Union[str, io.BytesIO] = None,
        dependencies: Union[str, List[str], io.BytesIO] = None,
        label_file: Union[str, io.BytesIO] = None,
        collection_name: str = None,
        on_hold: bool = False,
        validate_labels: bool = False,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """ Submits a workflow to Cromwell.

        Args:
            auth: authentication class holding auth information to a
                Cromwell server.
            wdl_file: The workflow source file to submit for execution. Could be either the
                path to the file (str) or the file content in io.BytesIO.
            inputs_files: The input data in JSON
                format. Could be either the path to the file (str) or the file content in io.BytesIO. This could also
                be a list of unlimited input file paths/contents, each of them should have a type of
                Union[str, io.BytesIO].
            options_file: The Cromwell options file for workflows. Could be either
                the path to the file (str) or the file content in io.BytesIO.
            dependencies: Workflow dependency files. Could be the path to
                the zipped file (str) containing dependencies, a list of paths(List[str]) to all dependency files to be
                zipped or a zipped file in io.BytesIO.
            label_file: A collection of key/value pairs for workflow labels in JSON
                format, could be either the path to the JSON file (str) or the file content in io.BytesIO.
            collection_name: Collection in SAM that the workflow should belong to, if use CaaS.
            on_hold: Whether to submit the workflow in "On Hold" status.
            validate_labels: If True, validate cromwell labels.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """
        submission_manifest = utilities.prepare_workflow_manifest(
            wdl_file=wdl_file,
            inputs_files=inputs_files,
            options_file=options_file,
            dependencies=dependencies,
            label_file=label_file,
            collection_name=collection_name,
            on_hold=on_hold,
        )

        if auth.service_key_content:
            submission_manifest[
                'workflowOptions'
            ] = utilities.compose_oauth_options_for_jes_backend_cromwell(
                auth, submission_manifest.get('workflowOptions')
            )

        if validate_labels and label_file is not None:
            validate_cromwell_label(submission_manifest['labels'])

        response = requests.post(
            auth.url + cls._submit_endpoint,
            files=submission_manifest,
            auth=auth.auth,
            headers=auth.header,
        )

        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def wait(
        cls: 'CromwellAPI',
        workflow_ids: List[str],
        auth: CromwellAuth,
        timeout_minutes: int = 120,
        poll_interval_seconds: int = 30,
        verbose: bool = True,
    ) -> None:
        """Wait until cromwell returns successfully for each provided workflow

        Given a list of workflow ids, wait until cromwell returns successfully for each status, or
        one of the workflows fails or is aborted.

        Args:
            workflow_ids: A list of workflow ids to wait for terminal status.
            timeout_minutes: Maximum number of minutes to wait.
            auth: Authentication class holding headers
                or auth information to a Cromwell server.
            poll_interval_seconds: Number of seconds between checks for workflow
                completion.
            verbose: If True, report to stdout when all workflows succeed.
        """
        start = datetime.now()
        timeout = timedelta(minutes=int(timeout_minutes))

        while True:

            if datetime.now() - start > timeout:
                msg = 'Unfinished workflows after %s minutes.' % timeout
                raise Exception(msg.format(timeout))

            all_succeeded = True

            if verbose:
                print('--- polling from cromwell ---')

            for uuid in workflow_ids:
                response = cls.status(uuid, auth)
                status = cls._parse_workflow_status(response)

                if verbose:
                    print('Workflow %s returned status %s' % (uuid, status))

                if status in _failed_statuses:
                    raise exceptions.WorkflowFailedError(
                        'Workflow %s returned status %s' % (uuid, status)
                    )
                elif status != 'Succeeded':
                    all_succeeded = False

            if all_succeeded:
                print('All workflows succeeded!')
                return ''

            time.sleep(poll_interval_seconds)

    @classmethod
    def release_hold(
        cls: 'CromwellAPI',
        uuid: str,
        auth: CromwellAuth,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """Request Cromwell to release the hold on a workflow.

        It will switch the status of a workflow from 'On Hold' to 'Submitted' so it can be picked for running. For
        a workflow that was not submitted with `workflowOnHold = true`, Cromwell will throw an error.

        Args:
            uuid: A Cromwell workflow UUID, which is the workflow identifier. The workflow is expected to have
                `On Hold` status.
            auth: The authentication class holding headers or auth
                information to a Cromwell server.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """
        response = requests.post(
            url=auth.url + cls._release_hold_endpoint.format(uuid=uuid),
            auth=auth.auth,
            headers=auth.header,
        )
        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def query(
        cls: 'CromwellAPI',
        query_dict: Dict[str, Union[str, List[str], Dict[str, str], bool]],
        auth: CromwellAuth,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """Query for workflows.

        TODO: Given that Cromwell-as-a-Service blocks a set of features that are available in Cromwell, e.g. 'labelor',
        for security concerns, the first iteration of this API doesn't come up with the advanced query keys of the
        Cromwell except a set of necessary ones. However, we need to implement this for completeness and keep an eye
        on the compatibility between CaaS and Cromwell.

        All of the query keys will be used in an OR manner, except the keys within `labels`, which are defined in
        an AND relation. For instance, [{'status': 'Succeeded'}, {'status': 'Failed'}] will give you all of the
        workflows that in either `Succeeded` or `Failed` statuses.

        Args:
            query_dict: A dictionary representing the query key-value paris. The keys should be accepted by the
                Cromwell or they will get ignored. The values could be str, list or dict.
            auth: The authentication class holding headers or auth
                information to a Cromwell server.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """
        if (
            'additionalQueryResultFields' in query_dict.keys()
            or 'includeSubworkflows' in query_dict.keys()
        ):
            logging.warning(
                'Note: additionalQueryResultFields, includeSubworkflows may not scale due to the '
                'following issues with Cromwell: https://github.com/broadinstitute/cromwell/issues/3115 '
                'and https://github.com/broadinstitute/cromwell/issues/3873'
            )

        query_params = cls._compose_query_params(query_dict)

        response = requests.post(
            url=auth.url + cls._query_endpoint,
            json=query_params,
            auth=auth.auth,
            headers=auth.header,
        )
        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def patch_labels(
        cls: 'CromwellAPI',
        uuid: str,
        labels: Dict[str, str],
        auth: CromwellAuth,
        raise_for_status: bool = False,
    ) -> requests.Response:
        """Add new labels or patch existing labels for an existing workflow.

        Args:
            uuid: A Cromwell workflow UUID, which is the workflow identifier.
            labels: A dictionary representing the label key-value pairs.
            auth: The authentication class holding headers or auth
                information to a Cromwell server.
            raise_for_status: Whether to check and raise for status based on the response.

        Raises:
            requests.exceptions.HTTPError: This will be raised when raise_for_status is True and Cromwell returns
                a response that satisfies 400 <= response.status_code < 600.

        Returns:
            HTTP response from Cromwell.
        """

        response = requests.patch(
            url=auth.url + cls._labels_endpoint.format(uuid=uuid),
            json=labels,
            auth=auth.auth,
            headers=auth.header,
        )
        if raise_for_status:
            cls._check_and_raise_status(response)
        return response

    @classmethod
    def _compose_query_params(
        cls: 'CromwellAPI',
        query_dict: Dict[str, Union[str, List[str], Dict[str, str], bool]],
    ) -> List[Dict[str, str]]:
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
            query_dict: A dictionary representing the query key-value paris. The keys should be accepted by the
                Cromwell or they will get ignored. The values could be str, list or dict.

        Raises:
            TypeError: If the input query_dict is not a dictionary.
            ValueError: If a list of values are assigned to a query key that belongs to _cromwell_exclusive_query_keys.

        Returns:
            query_params: A composed list of query objects.
        """
        if not isinstance(query_dict, dict):
            raise TypeError('A valid dictionary with query keys is required!')

        query_params = []
        for k, v in query_dict.items():
            if k in _cromwell_query_keys:
                if k == 'label' and isinstance(v, dict):
                    query_params.extend(
                        [
                            {'label': label_key + ':' + label_value}
                            for label_key, label_value in v.items()
                        ]
                    )
                elif isinstance(v, list):
                    if k in _cromwell_exclusive_query_keys:
                        raise ValueError(
                            '{} cannot be specified multiple times!'.format(k)
                        )
                    query_params.extend(
                        [
                            {k: json.dumps(val)}
                            if not isinstance(val, str)
                            else {k: val}
                            for val in set(v)
                        ]
                    )
                else:
                    query_params.append(
                        {k: json.dumps(v)} if not isinstance(v, str) else {k: v}
                    )
            else:
                logger.info(
                    '{} is not an allowed query key in Cromwell, will be ignored in this query.'.format(
                        k
                    )
                )
        return query_params

    @staticmethod
    def _parse_workflow_status(response: requests.Response) -> str:
        """Helper function to parse a status response.

        Args:
            response: A status response object from Cromwell.

        Raises:
            WorkflowUnknownError: This will be raised when Cromwell returns a status code != 200.

        Returns:
            String representing status response.
        """
        if response.status_code != 200:
            raise exceptions.WorkflowUnknownError(
                'Status could not be determined, endpoint returned {0}'.format(
                    response.status_code
                )
            )
        else:
            return response.json()['status']

    @staticmethod
    def _check_and_raise_status(response: requests.Response) -> None:
        """Helper function to check the status of a response and raise a friendly message if there are errors.

        This functions is using the `response.ok` which wraps the `raise_for_status()`, by doing this, we can
        produce the actual error messages from the Cromwell, instead of shadowing them with `raise_for_status()`.

        Args:
            response: A status response object from Cromwell.

        Raises:
            requests.exceptions.HTTPError: This will be raised when Cromwell returns a response that satisfies
                400 <= response.status_code < 600.
        """
        if not response.ok:
            raise requests.exceptions.HTTPError(
                'Error Code {0}: {1}'.format(response.status_code, response.text),
                response=response,
            )
