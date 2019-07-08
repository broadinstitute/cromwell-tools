import io
import json
import os
import re
import requests
import shutil
import warnings
import zipfile
from typing import List, Union, Dict, Match, Any
from cromwell_tools.cromwell_auth import CromwellAuth


# Note: the following rules for validating labels were originally based on Cromwell's documentation on Github:
# https://github.com/broadinstitute/cromwell/blob/32/CHANGELOG.md
# However, from Cromwell v32, most of the restrictions on the labels have been moved, according to
# https://cromwell.readthedocs.io/en/stable/Labels/, below are the requirements for a valid label
#  key/value pair in Cromwell:
#
# - Label keys may not be empty but label values may be empty.
# - Label key and values have a max char limit of 255.

_CROMWELL_LABEL_LENGTH = 63
_CROMWELL_LABEL_KEY_REGEX = '[a-z]([-a-z0-9]*[a-z0-9])?'
_CROMWELL_LABEL_VALUE_REGEX = '([a-z0-9]*[-a-z0-9]*[a-z0-9])?'


def _emulate_python_fullmatch(
    regex: str, string: str, flags: Union[int, str] = 0
) -> Union[Match[str], None]:
    """Backport Python 3.4's regular expression "fullmatch()" to Python 2 by emulating python-3.4 re.fullmatch().

    If the whole string matches the regular expression pattern, return a corresponding match object. Return None
    if the string does not match the pattern; note that this is different from a zero-length match.

    Args:
        regex: A regex string.
        string: The string that you want to apply regex match to.
        flags: The expression's behaviour can be modified by specifying a flags value. Values can be any of
            the variables listed in https://docs.python.org/3/library/re.html

    Returns:
        A matched object, or None if the string does not match the pattern.
    """
    return re.match("(?:" + regex + r")\Z", string, flags=flags)


if "fullmatch" not in dir(re):  # For Python3.4+
    re.fullmatch = _emulate_python_fullmatch


def download_to_map(urls: List[str]) -> Dict[str, Any]:
    """Reads contents from each url into memory and returns a map of urls to their contents.

    Args:
        urls: A list of urls to the contents to be downloaded.

    Returns:
        url_to_contents: A dict representing the mapping from url to the downloaded contents in-memory.
    """
    url_to_contents = {}
    for url in urls:
        contents = download(url)
        url_to_contents[url] = contents
    return url_to_contents


def make_zip_in_memory(url_to_contents: Dict[str, Any]) -> io.BytesIO:
    """Given a map of urls and their contents, returns an in-memory zip file containing each file.

    For each url, the part after the last slash is used as the file name when writing to the zip archive.

    Args:
        url_to_contents: A dict representing the mapping from url to the downloaded contents in-memory.

    Returns:
        bytes_buf: Zipped files content in bytes.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zip_buffer:
        for url, contents in url_to_contents.items():
            name = url.split('/')[-1]
            zip_buffer.writestr(name, contents)

    # To properly send the zip to Cromwell in start_workflow, we need it to be an io.BytesIO.
    # If we don't convert, start_workflow appears to succeed, but Cromwell can't find
    # anything in the zip.
    # (six.BytesIO is just an alias for StringIO in Python 2 and for BytesIO in Python 3.)
    bytes_buf = io.BytesIO(buf.getvalue())
    return bytes_buf


def download(url: str) -> Union[str, bytes]:
    """Reads the contents located at the url into memory and returns them.

    Urls starting with http are fetched with an http request. All others are assumed to be local file paths
    and read from the local file system.

    Args:
        url: The url to the content to be downloaded, or the path to the local file.

    Returns:
        Downloaded content in str or bytes format.

    Raises:
        TypeError: If the url is not a str type.
    """
    if not isinstance(url, str):
        raise TypeError('The url/path must be a (str) type, not {}!'.format(type(url)))

    if url.startswith('http'):
        return download_http(url)
    else:
        return read_local_file(url)


def download_http(url: str) -> Union[str, bytes]:
    """
    Makes an http request for the contents at the given url and returns the response body.

    Args:
        url: The url to the content to be downloaded.

    Returns:
        response_str: Content returned from the server. Will be `str` in Python2 and bytes in `Python3`.
    """
    response = requests.get(url)
    response.raise_for_status()

    # Encoding here prevents a UnicodeDecodeError later in make_zip_in_memory in Python 2.
    response_str = response.text.encode('utf-8')
    return response_str


def read_local_file(path: str) -> Union[str, bytes]:
    """Reads the file contents and returns them.

    Args:
        path: Path to the local file to be loaded.

    Returns:
        contents: The loaded content. bytes in Python3 and str in Python2.
    """
    with open(os.path.abspath(path), 'rb') as f:
        contents = f.read()
    return contents


def _localize_file(url: str, target_directory: str = '.') -> None:
    """Localize file url to a directory. Supports both local files and http(s) endpoints.

    Args:
        url: URL of local or http target.
        target_directory: Directory to localize file to.
    """
    if not os.path.isdir(target_directory):
        raise NotADirectoryError(
            'target_directory must be a valid directory on the local filesystem'
        )

    basename = os.path.basename(url)
    target_file = os.path.join(target_directory, basename)

    if url.startswith('http'):
        data = download_http(url)
        with open(target_file, 'wb') as f:
            f.write(data)
    else:
        if not os.path.isfile(url):
            raise FileNotFoundError(
                'non-http files must point to a valid file on the local filesystem. Not found: {}'.format(
                    url
                )
            )
        else:
            shutil.copy(url, target_file)


def _content_checker(regex: str, content: str) -> str:
    """Helper function to check if a string is obeying the rule described by a regex string or not.

    Args:
        regex: A regex string defines valid content.
        content: A string to be validated.

    Returns:
        A string of error message if validation fails, or an empty string if validation succeeds.
    """
    matched = re.fullmatch(regex, content)

    if not matched:
        return f'Invalid label: {content} does not match the regex {regex}.\n'
    else:
        return ''


def _length_checker(length: int, content: str) -> str:
    """Helper function to check if a string is shorter than expected length of not.

    Args:
        length: Maximum length of an expected string.
        content: A string to be validated.

    Returns:
        A string of error message if validation fails, or an empty string if validation succeeds.
    """
    if len(content) > length:
        return f'Invalid label: {content} has {len(content)} characters. The maximum is {length}.\n'
    else:
        return ''


def validate_cromwell_label(
    label_object: Union[str, io.BytesIO, bytes, Dict[str, str]]
) -> None:
    """Check if the label object is valid for Cromwell.

    Note: this function as well as the global variables _CROMWELL_LABEL_LENGTH, _CROMWELL_LABEL_KEY_REGEX
    and _CROMWELL_LABEL_VALUE_REGEX are implemented based on the Cromwell's documentation:
    https://cromwell.readthedocs.io/en/develop/Labels/ and the Cromwell's code base:
    https://github.com/broadinstitute/cromwell/blob/master/core/src/main/scala/cromwell/core/labels/Label.scala#L16
    Both the docs and the code base of Cromwell could possibly change in the future, please update this
    checker on demand.

    Args:
        label_object: A dictionary or a key-value object string defines a Cromwell label.

    Raises:
        ValueError: This validator will raise an exception if the label_object is invalid as a Cromwell label.
    """
    warnings.warn(
        "This function doesn't work for Cromwell v32 and later versions and has been deprecated, "
        "be aware of using this validator when using Cromwell v32(+). Check "
        "https://cromwell.readthedocs.io/en/stable/Labels/ for details.",
        PendingDeprecationWarning,
    )

    err_msg = ''

    if isinstance(label_object, str):
        label_object = json.loads(label_object)
    elif isinstance(label_object, bytes):
        label_object = json.loads(label_object.decode('utf-8'))
    elif isinstance(label_object, io.BytesIO):
        label_object = json.loads(label_object.getvalue())

    for label_key, label_value in label_object.items():
        err_msg += _content_checker(_CROMWELL_LABEL_KEY_REGEX, label_key)
        err_msg += _content_checker(_CROMWELL_LABEL_VALUE_REGEX, label_value)
        err_msg += _length_checker(_CROMWELL_LABEL_LENGTH, label_key)
        err_msg += _length_checker(_CROMWELL_LABEL_LENGTH, label_value)

    if err_msg != '':
        raise ValueError(err_msg)


def prepare_workflow_manifest(
    wdl_file: Union[str, io.BytesIO],
    inputs_files: Union[List[Union[str, io.BytesIO]], str, io.BytesIO] = None,
    options_file: Union[str, io.BytesIO] = None,
    dependencies: Union[str, List[str], io.BytesIO] = None,
    label_file: Union[str, io.BytesIO] = None,
    collection_name: str = None,
    on_hold: bool = False,
) -> Dict[str, Union[io.BytesIO, str]]:
    """Prepare the submission manifest for a workflow submission.

    Args:
        wdl_file: The workflow source file to submit for execution. Could be either the path
            to the file (str) or the file content in io.BytesIO.
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

    Returns:
        workflow_manifest: A dictionary representing the workflow manifest ready for workflow submission.

    Raises:
        ValueError: If a str ing of path to the dependencies is given but not endswith ".zip".
    """
    workflow_manifest = {}

    # Compose WDL source file
    workflow_manifest['workflowSource'] = _download_to_BytesIO_if_string(wdl_file)

    # Compose WDL inputs
    if inputs_files:
        if not isinstance(inputs_files, list):
            inputs_files = [inputs_files]

        for idx, inputs_file in enumerate(inputs_files):
            if idx == 0:
                # Compose WDL inputs 1
                input_file_key = 'workflowInputs'
            else:
                # Compose other WDL inputs (from 2 - many)
                input_file_key = 'workflowInputs_{X}'.format(X=idx + 1)

            workflow_manifest[input_file_key] = _download_to_BytesIO_if_string(
                inputs_file
            )

    # Compose WDL options
    if options_file:
        workflow_manifest['workflowOptions'] = _download_to_BytesIO_if_string(
            options_file
        )

    # Compose WDL labels
    if label_file:
        workflow_manifest['labels'] = _download_to_BytesIO_if_string(label_file)

    # Compose WDL dependencies
    if dependencies:
        if isinstance(dependencies, list):
            if len(dependencies) == 1 and dependencies[0].endswith('.zip'):
                # when a single zip file is provided in a list
                zip_file = _download_to_BytesIO_if_string(dependencies[0])
            else:
                # when a single wdl file or multiple wdl files are provided in a list
                zip_file = make_zip_in_memory(download_to_map(dependencies))
        elif isinstance(dependencies, str) and not dependencies.endswith('.zip'):
            # when a single file is provided as a string but not zipped
            raise ValueError(
                'The dependency file path must point to a ".zip" file! Or you may want to provide a list of WDL file(s).'
            )
        else:
            # when a single zip file is provided as a string
            zip_file = _download_to_BytesIO_if_string(dependencies)
        workflow_manifest['workflowDependencies'] = zip_file

    # Compose collection name (if use CaaS)
    if collection_name:
        workflow_manifest['collectionName'] = collection_name

    # Compose the On Hold switch for workflow submission
    workflow_manifest['workflowOnHold'] = json.dumps(on_hold)

    return workflow_manifest


def _download_to_BytesIO_if_string(file: Union[str, io.BytesIO]) -> io.BytesIO:
    """Download a file if given a string of the file path or return the input if it's in io.BytesIO.

    Args:
        file: A string of the path to the file or the file content in io.BytesIO.

    Returns:
        File content in io.BytesIO.

    Raises:
        TypeError: If the input is not a str nor io.BytesIO.
    """
    # TODO: add validation for JSON files
    if isinstance(file, str):
        return io.BytesIO(download(file))
    elif isinstance(file, io.BytesIO) or not file:
        return file
    else:
        raise TypeError('Please make sure to pass in Union[str, io.BytesIO] types!')


def compose_oauth_options_for_jes_backend_cromwell(
    auth: CromwellAuth,
    cromwell_options_file: io.BytesIO = None,
    execution_bucket: str = None,
) -> io.BytesIO:
    """Append special options that are required by JES(Google Job Execution Service) backend Cromwell.

    This helper function will append special options that are required by JES(Google Job Execution Service)
    backend Cromwell/Cromwell-as-a-Service to the default workflow options. Note: These options only work
    with Cromwell instances that use the Google Cloud Backend and allow user-service-account authentication.

    Args:
        auth: authentication class holding auth information to a Cromwell server.
        cromwell_options_file: Optional, contents of the options for a workflow in BytesIO format.
            if not specified, this function will create an empty option stream and add the necessary keys to it.
        execution_bucket: Optional, the Google CLoud Bucket that Cromwell will use to output
            execution results and store temporary scripts. If not specified, it will use
            'gs://{google_project}-cromwell-execution/caas-cromwell-executions' by default.

    Returns:
        options_stream: BytesIO object of the updated workflow options with the required auth fields.
    """
    if not cromwell_options_file:
        cromwell_options_file = io.BytesIO(json.dumps({}).encode())

    # using `getvalue()` here so we don't have to seek back to the beginning if we need the value again
    options_json = json.loads(cromwell_options_file.getvalue())
    google_project = auth.service_key_content['project_id']

    options_json.update(
        {
            'jes_gcs_root': execution_bucket
            or f'gs://{google_project}-cromwell-execution/caas-cromwell-executions',
            'google_project': google_project,
            'user_service_account_json': json.dumps(auth.service_key_content),
            'google_compute_service_account': auth.service_key_content['client_email'],
        }
    )
    options_stream = io.BytesIO(json.dumps(options_json).encode())
    return options_stream
