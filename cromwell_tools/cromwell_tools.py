"""This module contains utility functions to interact with Cromwell.
"""
import requests
from requests.auth import HTTPBasicAuth


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
