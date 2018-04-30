import re
import zipfile
import io
import requests
import json


# Note: the following rules for validating labels are based on Cromwell's documentation:
# https://cromwell.readthedocs.io/en/develop/Labels/ and they could be changed in the future.
_CROMWELL_LABEL_LENGTH = 63
_CROMWELL_LABEL_KEY_REGEX = '[a-z]([-a-z0-9]*[a-z0-9])?'
_CROMWELL_LABEL_VALUE_REGEX = '([a-z0-9]*[-a-z0-9]*[a-z0-9])?'


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

    :param str|_io.BytesIO label_object: A dictionary or a key-value object string that define a Cromwell label.

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


def prepare_workflow_manifest(
        wdl_file, inputs_json, dependencies_json=None, options_json=None, inputs2_json=None,
        **kwargs):
    """prepare a cromwell manifest by localizing input files

    localize files from aws, gcp, https, or local endpoints

    :param wdl_file:
    :param inputs_json:
    :param dependencies_json:
    :param options_json:
    :param inputs2_json:
    :param dict kwargs: accept arbitrary arguments

    :return dict: manifest for workflow
    """

    def download_if_string(string_or_buffer):
        if isinstance(string_or_buffer, str):
            string_or_buffer = download(string_or_buffer)
        return string_or_buffer

    manifest = {
        'wdl_file': download_if_string(wdl_file),
        'inputs_json': download_if_string(inputs_json)
    }

    # add optional files
    if dependencies_json is not None:
        dependencies_bytes = download_if_string(dependencies_json)
        dependencies_json = json.loads(dependencies_bytes)
        manifest['dependencies_zip'] = make_zip_in_memory(
            {k: download(v) for k, v in dependencies_json.items()}
        )
    if options_json is not None:
        manifest['options_json'] = download_if_string(options_json)

    if inputs2_json is not None:
        manifest['inputs2_json'] = download_if_string(inputs2_json)

    return manifest
