import os
import json
from google.cloud import storage
from google.oauth2 import service_account


# ask about optional arguments
def get_benchmark(
    output_dir,
    parent_workflow_name,
    cromwell_id,
    google_bucket,
    project_id,
    credentials=None,
):
    """
    Saves a monitoring log for the tasks being called by your pipeline as a combined file (JSON)

    :param output_dir: the desired output directory to store the monitoring log, plots and json file
    :param parent_workflow_name: the name of the workflow being run
    :param cromwell_id: the cromwell id for the workflow being run
    :param google_bucket: the name of google bucket where your workflow was run
    :param project_id: The google project id for the workflow
    :param credentials: your credentials for google as a JSON file (optional
    """

    calls = get_calls(
        google_bucket, project_id, parent_workflow_name, cromwell_id, credentials
    )

    call_logs = get_call_logs(calls)

    file_name = get_path(
        parent_workflow_name + "_" + cromwell_id + "_benchmark_logs.json", output_dir
    )
    store_benchmark(call_logs, file_name)


def get_calls(
    google_bucket, project_id, parent_workflow_name, cromwell_id, credentials=None
):
    """
    :param google_bucket: the name of google bucket where your workflow was run
    :param project_id: The google project id for the workflow
    :param parent_workflow_name: the name of the workflow being run
    :param cromwell_id: the cromwell id for the workflow being run
    :param credentials: your credentials for google as a JSON file
    :return: a list of every call for the monitoring logs
    """

    # if the user does not provide credentials
    if credentials is not None:
        cred = service_account.Credentials.from_service_account_file(credentials)
        storage_client = storage.Client(project_id, credentials=cred)

    else:
        storage_client = storage.Client(project_id)

    # get the appropriate bucket and then task calls of the workflow/cromwell id
    bucket = storage_client.get_bucket(google_bucket)
    blobs = bucket.list_blobs(prefix=parent_workflow_name + "/" + cromwell_id)

    calls = []
    for blob in blobs:
        # if the task call contains a monitoring log
        if "monitoring.log" in blob.name:
            calls.append(blob)

    # return the task calls
    return calls


def get_call_logs(calls):
    """
    :param calls: a list of every call that contians a monitoring log
    :return: returns the information/log of every task call
    """

    call_logs = {}
    for call in calls:
        # get the information of that call
        call_name = os.path.dirname(call.name)
        call_info = call.download_as_string()
        call_logs[call_name] = call_info

    # returns the information/log of every task call
    return call_logs


def get_path(filename, output_dir):
    """
    :param filename: the filename to be saved in the output directory
    :param output_dir: the desired output directory to store the monitoring log, plots and json file
    :return: returns the combined path of file name and  output directory
    """

    # get the combined path of output dir path, filename and sub dir path
    path = os.path.join(output_dir, filename)

    # if the combined path exist
    if os.path.isfile(path):
        # delete that current path
        os.remove(path)

    # return combined path
    return path


def store_benchmark(call_logs, file_name):
    """
    dumps the information of each call task in dictionary format into one JSON file

    :param call_logs: the information of each call task in dictionary format
    :param file_name: name of the file with absolute path to dump the dictionay into
    """

    with open(file_name, "w") as logs:
        json.dump(call_logs, logs, sort_keys=False, indent=4)
