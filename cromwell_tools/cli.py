import argparse
import requests
from cromwell_tools.cromwell_api import CromwellAPI
from cromwell_tools.cromwell_auth import CromwellAuth


def parser(arguments=None):
    # TODO: dynamically walk through the commands and automatcially create parsers here

    main_parser = argparse.ArgumentParser()

    subparsers = main_parser.add_subparsers(help='sub-command help', dest='command')
    # sub-commands of cromwell-tools
    submit = subparsers.add_parser(
            'submit', help='submit help', description='Submit a WDL workflow on Cromwell.')
    wait = subparsers.add_parser(
            'wait', help='wait help', description='Wait for one or more running workflow to finish.')
    status = subparsers.add_parser(
            'status', help='status help', description='Get the status of one or more workflows.')
    abort = subparsers.add_parser(
            'abort', help='abort help', description='Request Cromwell to abort a running workflow by UUID.')
    release_hold = subparsers.add_parser(
            'release_hold', help='release_hold help', description='Request Cromwell to release the hold on a workflow.')
    query = subparsers.add_parser(
            'query', help='query help', description='[NOT IMPLEMENTED IN CLI] Query for workflows.')
    health = subparsers.add_parser(
            'health', help='health help',
            description='Check that cromwell is running and that provided authentication is valid.')
    validate = subparsers.add_parser(
        'validate', help='validate help', description='Validate a cromwell workflow using womtool.')

    # cromwell url and authentication arguments apply to all sub-commands
    cromwell_sub_commands = (submit, wait, status, abort, release_hold, query, health)
    auth_args = {
        'url': 'The URL to the Cromwell server. e.g. "https://cromwell.server.org/"',
        'username':  'Cromwell username for HTTPBasicAuth.',
        'password': 'Cromwell password for HTTPBasicAuth.',
        'secrets_file': 'Path to the JSON file containing username, password, and url fields.',
        'service_account_key': 'Path to the JSON key file for authenticating with CaaS.'
    }

    def add_auth_args(subcommand_parser):
        for arg_dest, help_text in auth_args.items():
            subcommand_parser.add_argument('--{arg}'.format(arg=arg_dest.replace('_', '-')),
                                           dest=arg_dest, default=None, type=str, help=help_text)
    # TODO: this should be a group which is called authentication
    for p in cromwell_sub_commands:
        add_auth_args(p)

    # submit arguments
    # TODO: add short flags for arguments
    submit.add_argument('--wdl-file', dest='wdl_file', type=argparse.FileType('r'), required=True,
                        help='The workflow source file to submit for execution.')
    submit.add_argument('--inputs-file', dest='inputs_file', type=argparse.FileType('r'), required=True,
                        help='File-like object containing input data in JSON format.')
    submit.add_argument('--zip-file', dest='zip_file', type=argparse.FileType('r'),
                        help='Zip file containing dependencies.')
    submit.add_argument('--inputs-file2', dest='inputs_file2', type=argparse.FileType('r'),
                        help='Inputs file 2.')
    submit.add_argument('--options-file', dest='options_file', type=argparse.FileType('r'),
                        help='Cromwell configs file.')

    submit.add_argument('--collection-name', dest='collection_name', type=str, default=None,
                        help='Collection in SAM that the workflow should belong to, if use CaaS.')
    submit.add_argument('--label', dest='label', type=argparse.FileType('r'), default=None,
                        help='JSON file containing a collection of key/value pairs for workflow labels.')
    submit.add_argument('--validate-labels', dest='validate_labels', type=bool, default=False,
                        help='Whether to validate cromwell labels.')
    submit.add_argument('--on-hold', dest='on_hold', type=bool, default=False,
                        help='Whether to submit the workflow in "On Hold" status.')

    # wait arguments
    wait.add_argument('workflow_ids', nargs='+')
    wait.add_argument('--timeout-minutes', dest='timeout_minutes', type=int, default=120,
                      help='number of minutes to wait before timeout')
    wait.add_argument('--poll-interval-seconds', dest='poll_interval_seconds', type=int, default=30,
                      help='seconds between polling cromwell for workflow status')

    # status arguments
    status.add_argument('--uuid', required=True, help='A Cromwell workflow UUID, which is the workflow identifier.')

    # abort arguments
    abort.add_argument('--uuid', required=True, help='A Cromwell workflow UUID, which is the workflow identifier.')

    # release_hold arguments
    release_hold.add_argument('--uuid', required=True, help='A Cromwell workflow UUID, which is the workflow identifier.')

    # query arguments
    # TODO: implement CLI entry for query API.

    # validate arguments
    validate.add_argument('--wdl-file', dest='wdl', type=str, required=True)
    validate.add_argument('--womtool-path', dest='womtool_path', type=str, required=True,
                          help='path to cromwell womtool jar')
    validate.add_argument('--dependencies-json', dest='dependencies_json', type=str, default=None)

    args = vars(main_parser.parse_args(arguments))
    # TODO: see if this can be moved or if the commands can be populated from above
    if args['command'] in ('submit', 'wait', 'status', 'abort', 'release_hold', 'health', 'validate'):
        if args['command'] == 'validate': args['command'] = 'validate_workflow'
        else:
            auth_arg_dict = {k: args.get(k) for k in auth_args.keys()}
            auth = CromwellAuth.harmonize_credentials(**auth_arg_dict)
            args['auth'] = auth
        for k in auth_args:
            if k in args:
                del args[k]
    command = getattr(CromwellAPI, args['command'])
    del args['command']
    return command, args


# this should just getattr from CromwellAPI and call the func with args.
# TODO: refactor this module into class-based parsers
def main(arguments=None):
    command, args = parser(arguments)
    API_result = command(**args)
    if isinstance(API_result, requests.Response):
        print(API_result.text)
    else:
        print(API_result)
