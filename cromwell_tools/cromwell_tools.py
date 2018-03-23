"""This module contains utility functions to interact with Cromwell.
"""
import io
import zipfile
import json
from datetime import datetime, timedelta
import time
import requests
from requests.auth import HTTPBasicAuth
import six
import re


_failed_statuses = ['Failed', 'Aborted', 'Aborting']

# Note: the following rules for validating labels are based on Cromwell's documentation:
# https://cromwell.readthedocs.io/en/develop/Labels/ and they could be changed in the future.
_CROMWELL_LABEL_LENGTH = 63
_CROMWELL_LABEL_KEY_REGEX = '[a-z]([-a-z0-9]*[a-z0-9])?'
_CROMWELL_LABEL_VALUE_REGEX = '([a-z0-9]*[-a-z0-9]*[a-z0-9])?'


def harmonize_credentials(secrets_file=None, cromwell_username=None, cromwell_password=None):
    """
    Takes all of the valid ways of providing authentication to cromwell and returns a username
    and password

    :param str cromwell_password:
    :param str cromwell_username:
    :param str secrets_file: json file containing fields cromwell_user and cromwell_password

    :return str: cromwell username
    :return str: cromwell password
    """
    if cromwell_username is None or cromwell_password is None:
        if secrets_file is None:
            raise ValueError('One form of cromwell authentication must be provided, please pass '
                             'either cromwell_user and cromwell_password or a secrets_file.')
        else:
            with open(secrets_file) as f:
                secrets = json.load(f)
                cromwell_username = secrets['cromwell_user']
                cromwell_password = secrets['cromwell_password']
    return cromwell_username, cromwell_password


def get_workflow_statuses(
        ids, cromwell_url, cromwell_user=None, cromwell_password=None, secrets_file=None):
    """ Given a list of workflow ids, query cromwell url for their statuses

    :param list ids:
    :param str cromwell_url:
    :param str cromwell_user:
    :param str cromwell_password:
    :param str secrets_file:
    :return list: list of workflow statuses
    """
    cromwell_user, cromwell_password = harmonize_credentials(
        secrets_file, cromwell_user, cromwell_password)
    statuses = []
    for id_ in ids:
        full_url = cromwell_url + '/api/workflows/v1/{0}/status'.format(id_)
        auth = requests.auth.HTTPBasicAuth(cromwell_user, cromwell_password)
        response = requests.get(full_url, auth=auth)
        if response.status_code != 200:
            print('Could not get status for {0}. Cromwell at {1} returned status {2}'.format(
                id_, cromwell_url, response.status_code))
            statuses.append('Unknown')
        else:
            response_json = response.json()
            status = response_json['status']
            statuses.append(status)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print('{0} workflow {1}: {2}'.format(timestamp, id_, status))
    return statuses


def wait_until_workflow_completes(
        cromwell_url, workflow_ids, timeout_minutes, poll_interval_seconds=30, cromwell_user=None,
        cromwell_password=None, secrets_file=None):
    """
    Given a list of workflow ids, wait until cromwell returns successfully for each status, or
    one of the workflows fails or is aborted.

    :param list workflow_ids:
    :param int timeout_minutes:
    :param int poll_interval_seconds: number of seconds between checks for workflow completion
      (default 30)
    :param str cromwell_url:
    :param str cromwell_user:
    :param str cromwell_password:
    :param str secrets_file:
    :return:
    """
    cromwell_user, cromwell_password = harmonize_credentials(
        secrets_file, cromwell_user, cromwell_password)
    start = datetime.now()
    timeout = timedelta(minutes=int(timeout_minutes))
    while True:
        if datetime.now() - start > timeout:
            msg = 'Unfinished workflows after {0} minutes.'
            raise Exception(msg.format(timeout))
        statuses = get_workflow_statuses(workflow_ids, cromwell_url, cromwell_user, cromwell_password)
        all_succeeded = True
        for i, status in enumerate(statuses):
            if status in _failed_statuses:
                raise Exception('Stopping because workflow {0} {1}'.format(workflow_ids[i], status))
            elif status != 'Succeeded':
                all_succeeded = False
        if all_succeeded:
            print('All workflows succeeded!')
            break
        else:
            time.sleep(poll_interval_seconds)


def start_workflow(
        wdl_file, inputs_file, url, options_file=None, inputs_file2=None, zip_file=None, user=None,
        password=None, label=None, validate_labels=True):
    """Use HTTP POST to start workflow in Cromwell.

    The requests library could accept both Bytes and String objects as parameters of files, so there is no
        strict restrictions on the type of inputs of this function.

    :param _io.BytesIO wdl_file: wdl file.
    :param _io.BytesIO inputs_file: inputs file.
    :param str url: cromwell url.
    :param _io.BytesIO options_file: (optional) cromwell configs file.
    :param _io.BytesIO inputs_file2: (optional) inputs file 2.
    :param _io.BytesIO zip_file: (optional) zip file containing dependencies.
    :param str user: (optional) cromwell username.
    :param str password: (optional) cromwell password.
    :param _io.BytesIO label: (optional) JSON file containing a collection of key/value pairs for workflow labels.
    :param bool validate_labels: (optional) Whether to validate labels or not, using cromwell-tools' built-in
     validators. It is set to True by default.

    :return requests.Response response: HTTP response from cromwell.
    """
    if validate_labels:
        validate_cromwell_label(label)

    files = {
        'workflowSource': wdl_file,
        'workflowInputs': inputs_file,
    }

    if inputs_file2 is not None:
        files['workflowInputs_2'] = inputs_file2
    if zip_file is not None:
        files['workflowDependencies'] = zip_file
    if options_file is not None:
        files['workflowOptions'] = options_file

    if user and password:
        auth = HTTPBasicAuth(user, password)
    else:
        auth = None

    if label:
        files['labels'] = label

    response = requests.post(url, files=files, auth=auth)
    return response


def download_to_map(urls):
    """
    Reads contents from each url into memory and returns a
    map of urls to their contents
    """
    url_to_contents = {}
    for url in urls:
        contents = download(url)
        url_to_contents[url] = contents
    return url_to_contents


def make_zip_in_memory(url_to_contents):
    """
    Given a map of urls and their contents, returns an in-memory zip file
    containing each file. For each url, the part after the last slash is used
    as the file name when writing to the zip archive.
    """
    buf = six.BytesIO()
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


def download(url):
    """
    Reads the contents located at the url into memory and returns them.
    Urls starting with http are fetched with an http request. All others are
    assumed to be local file paths and read from the local file system.
    """
    if url.startswith('http'):
        return download_http(url)
    else:
        return read_local_file(url)


def download_http(url):
    """
    Makes an http request for the contents at the given url and returns the response body.
    """
    response = requests.get(url)
    response.raise_for_status()

    # Encoding here prevents a UnicodeDecodeError later in make_zip_in_memory in Python 2.
    response_str = response.text.encode('utf-8')
    return response_str


def read_local_file(path):
    """
    Reads the file contents and returns them.
    """
    with open(path) as f:
        contents = f.read()
    return contents


def _content_checker(regex, content):
    """Helper function to check if a string is obeying the rule described by a regex string or not.

    :param str regex: A regex string defines valid content.
    :param str content: A string to be validated.

    :return str: A string of error message if validation fails, or an empty string if validation succeeds.
    """
    if "fullmatch" in dir(re):  # For Python3.4+
        matched = re.fullmatch(regex, content)
    else:  # For Python3.3/2.7 or earlier versions
        matched = _emulate_python_fullmatch(regex, content)

    if not matched:
        return 'Invalid label: {0} did not match the regex {1}.\n'.format(content, regex)
    else:
        return ''


def _length_checker(length, content):
    """Helper function to check if a string is shorter than expected length of not.

    :param int length: Maximum length of an expected string.
    :param str content: A string to be validated.

    :return str: A string of error message if validation fails, or an empty string if validation succeeds.
    """
    if len(content) > length:
        return 'Invalid label: {0} has {1} characters. The maximum is {2}.\n'.format(content, len(content), length)
    else:
        return ''


def _emulate_python_fullmatch(regex, string, flags=0):
    """Backport Python 3.4's regular expression "fullmatch()" to Python 2 by emulating python-3.4 re.fullmatch().

    If the whole string matches the regular expression pattern, return a corresponding match object.
     Return None if the string does not match the pattern; note that this is different from a zero-length match.

    :param str regex: A regex string.
    :param str string: The string that you want to apply regex match to.
    :param str|int flags: The expression's behaviour can be modified by specifying a flags value. Values can be any of
     the variables listed in https://docs.python.org/3/library/re.html

    :return SRE_Match/None: return a corresponding match object, or None if the string does not match the pattern.
    """
    return re.match("(?:" + regex + r")\Z", string, flags=flags)


def validate_cromwell_label(label_object):
    """Check if the label object is valid for Cromwell.

    Note: this function as well as the global variables _CROMWELL_LABEL_LENGTH, _CROMWELL_LABEL_KEY_REGEX
        and _CROMWELL_LABEL_VALUE_REGEX are implemented based on the Cromwell's documentation:
        https://cromwell.readthedocs.io/en/develop/Labels/ and the Cromwell's code base:
        https://github.com/broadinstitute/cromwell/blob/master/core/src/main/scala/cromwell/core/labels/Label.scala#L16
        Both the docs and the code base of Cromwell could possibly change in the future, please update this
        checker on demand.

    :param str label_object: A dictionary or a key-value object string that define a Cromwell label.

    :raises ValueError: This validator will raise an exception if the label_object is invalid as a Cromwell label.
    """
    err_msg = ''

    if isinstance(label_object, str) or isinstance(label_object, bytes):
        label_object = json.loads(label_object)
    elif isinstance(label_object, io.BytesIO):
        label_object = json.loads(label_object.getvalue())

    for label_key, label_value in label_object.items():
        err_msg += _content_checker(_CROMWELL_LABEL_KEY_REGEX, label_key)
        err_msg += _content_checker(_CROMWELL_LABEL_VALUE_REGEX, label_value)
        err_msg += _length_checker(_CROMWELL_LABEL_LENGTH, label_key)
        err_msg += _length_checker(_CROMWELL_LABEL_LENGTH, label_value)

    if err_msg != '':
        raise ValueError(err_msg)
