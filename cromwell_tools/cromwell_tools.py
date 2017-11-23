"""This module contains utility functions to interact with Cromwell.
"""
import requests
from requests.auth import HTTPBasicAuth
import io
import requests
import zipfile
from StringIO import StringIO


def start_workflow(wdl_file, zip_file, inputs_file, inputs_file2, options_file, url, user=None, password=None):
    """Use HTTP POST to start workflow in Cromwell.

    :param _io.BytesIO wdl_file: wdl file.
    :param _io.BytesIO zip_file: zip file.
    :param _io.BytesIO inputs_file: inputs file.
    :param _io.BytesIO inputs_file2: inputs file 2.
    :param _io.BytesIO options_file: configs file.
    :param ListenerConfig green_config: The ListenerConfig class of current app.
    :return requests.Response response: HTTP response from cromwell.
    """
    files = {
        'wdlSource': wdl_file,
        'workflowInputs': inputs_file,
        'workflowInputs_2': inputs_file2,
        'wdlDependencies': zip_file,
        'workflowOptions': options_file
    }

    if user and password:
        auth=HTTPBasicAuth(user, password)
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
    buf = StringIO()
    with zipfile.ZipFile(buf, 'w') as zip_buffer:
        for url, contents in url_to_contents.items():
            name = url.split('/')[-1]
            zip_buffer.writestr(name, contents)

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
    response_str = response.text.encode('utf-8')
    return response_str


def read_local_file(path):
    """
    Reads the file contents and returns them.
    """
    with open(path) as f:
        contents = f.read()
    return contents
