import json
import dateutil.parser
import re
from itertools import groupby
from functools import reduce
from googleapiclient import discovery
from google.oauth2 import service_account
from cromwell_tools.cromwell_api import CromwellAPI
from cromwell_tools.cromwell_auth import CromwellAuth
from cromwell_tools import exceptions


OUTPUT_HEADER = "\t".join(
    [
        "Task Name",
        "Job ID",
        "Shard Index",
        "Latest Attempt #",
        "Status",
        "Machine Type",
        "CPUs",
        "Mem (Mbs)",
        "Preemptible?",
        "Total Runtime (Minutes)",
        "Cromwell Preprocessing",
        "Waiting for Quota",
        "VM Setup",
        "Pulling Google SDK",
        "Pulling Docker(s)",
        "Localization",
        "User Action / Running Docker",
        "Delocalization",
        "VM Shutdown",
        "Cromwell Postprocessing",
    ]
)

CROMWELL_PREPROCESSING = [
    # Shared
    "Pending",
    "WaitingForValueStore",
    "RequestingExecutionToken",
    "PreparingJob",
    "RunningJob",
]
WAITING_FOR_QUOTA = [
    # Shared
    "waiting for quota"
]
VM_SETUP = [
    # PAPI-v2
    re.compile("Worker .*assigned"),
    # Shared
    "Background",
    "ContainerSetup",
    # PAPI-v1
    "initializing VM",
    "start",
]
PULLING_GOOGLE_SDK = [
    # PAPI-v2
    "Pulling \"google"
]
PULLING_DOCKER = [
    # PAPI-v2
    re.compile("Pulling \"(?!google)"),
    # PAPI-v1
    "pulling-image",
]
LOCALIZATION = [
    # PAPI-v2
    "Localization",
    # PAPI-v1
    re.compile("^localizing-files"),
]
ACTION = [
    # PAPI-v2
    "UserAction",
    # PAPI-v1
    "running-docker",
]
DELOCALIZATION = [
    # PAPI-v2
    "Delocalization",
    # PAPI-v1
    "delocalizing-files",
]
VM_SHUTDOWN = [
    # PAPI-v2
    "Worker released",
    # PAPI-v1
    "ok",
]
CROMWELL_POSTPROCESSING = [
    # Shared
    "UpdatingCallCache",
    "UpdatingJobStore",
]


def select_latest(task1, task2):
    if task1['attempt'] > task2['attempt']:
        return task1
    else:
        return task2


def get_latest_attempts(tasks):
    def shardIndex(task):
        return task['shardIndex']

    sorted_tasks = sorted(tasks, key=shardIndex)
    tasks_by_shard = groupby(sorted_tasks, key=shardIndex)
    return [reduce(select_latest, g) for k, g in tasks_by_shard]


def flatten_subworkflow_tasks(calls):
    flat_tasks = []
    for task_name, tasks in calls.items():
        latest_attempts = get_latest_attempts(tasks)
        for task in latest_attempts:
            if 'subWorkflowMetadata' in task:
                subwf_tasks = flatten_subworkflow_tasks(
                    task['subWorkflowMetadata']['calls']
                )
                [flat_tasks.append(subwf_task) for subwf_task in subwf_tasks]
            else:
                task['name'] = task_name
                flat_tasks.append(task)
    return flat_tasks


def time_elapsed(start_stamp, end_stamp):
    start = dateutil.parser.parse(start_stamp)
    end = dateutil.parser.parse(end_stamp)
    elapsed = end - start
    seconds = elapsed.days * 24 * 60 * 60 + elapsed.seconds
    return round(seconds / 60.0, 2)


def is_event_type(event, event_type):
    description = event['description']
    match = False
    for identifier in event_type:
        if isinstance(identifier, str):
            match = match or identifier in description
        else:
            match = match or identifier.match(description)

    return match


def exec_event_type_time(execution_events, event_type):
    events_of_type = [
        event for event in execution_events if is_event_type(event, event_type)
    ]
    if len(events_of_type) == 0:
        return 'N/A'
    else:
        times = [
            time_elapsed(event['startTime'], event['endTime'])
            for event in events_of_type
        ]
        return str(reduce(lambda x, y: x + y, times))


def parse_machine_type(raw_value):
    if 'custom' in raw_value:
        return raw_value
    else:
        return raw_value.split("/")[1]


def get_machine_types(project, service_account_json):
    scopes = ['https://www.googleapis.com/auth/compute']
    credentials = service_account.Credentials.from_service_account_info(
        service_account_json, scopes=scopes
    )
    service = discovery.build('compute', 'v1', credentials=credentials)
    request = service.machineTypes().aggregatedList(project=project)
    machine_types = {}

    while request is not None:
        response = request.execute()
        for data in response['items'].values():
            if 'machineTypes' in data:
                for machine_type in data['machineTypes']:
                    name = machine_type['name']
                    mem = machine_type['memoryMb']
                    cpus = machine_type['guestCpus']
                    machine_types[name] = {'memory': mem, 'cpus': cpus}
        request = service.machineTypes().aggregatedList_next(
            previous_request=request, previous_response=response
        )

    return machine_types


def specs_from_machine(machine_type, machine_types):
    if 'custom' in machine_type:
        components = machine_type.split("-")
        cpus, mem = components[1], components[2]
    else:
        machine_specs = machine_types[machine_type]
        cpus, mem = machine_specs['cpus'], machine_specs['memory']

    return cpus, mem


def output_row(task, machine_types):
    events = task['executionEvents']
    runtime = task['runtimeAttributes']
    machine_type = parse_machine_type(task['jes']['machineType'])
    cpus, mem = specs_from_machine(machine_type, machine_types)
    return "\t".join(
        [
            task['name'],
            task['jobId'],
            str(task['shardIndex']),
            str(task['attempt']),
            task['executionStatus'],
            machine_type,
            str(cpus),
            str(mem),
            str(task['preemptible']),
            str(time_elapsed(task['start'], task['end'])),
            exec_event_type_time(events, CROMWELL_PREPROCESSING),
            exec_event_type_time(events, WAITING_FOR_QUOTA),
            exec_event_type_time(events, VM_SETUP),
            exec_event_type_time(events, PULLING_GOOGLE_SDK),
            exec_event_type_time(events, PULLING_DOCKER),
            exec_event_type_time(events, LOCALIZATION),
            exec_event_type_time(events, ACTION),
            exec_event_type_time(events, DELOCALIZATION),
            exec_event_type_time(events, VM_SHUTDOWN),
            exec_event_type_time(events, CROMWELL_POSTPROCESSING),
        ]
    )


def print_task_runtime_data(metadata, service_account_json):
    tasks = flatten_subworkflow_tasks(metadata['calls'])
    project = tasks[0]['jes']['googleProject']
    machine_types = get_machine_types(project, service_account_json)
    print(OUTPUT_HEADER)
    [print(output_row(task, machine_types)) for task in tasks]


def run(auth: CromwellAuth, metadata: str = None, uuid: str = None):
    if metadata is not None:
        with open(metadata) as data_file:
            metadata = json.load(data_file)
    # cli top level parsing ensures metadata is set otherwise
    else:
        response = CromwellAPI.metadata(
            uuid=uuid, auth=auth, expandSubWorkflows=True, raise_for_status=True,
        )
        metadata = response.json()

    if auth.service_key_content is None:
        raise exceptions.CromwellAuthenticationError(
            "task_runtime requires a service account key"
        )

    print_task_runtime_data(metadata, auth.service_key_content)
