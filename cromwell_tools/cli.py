import argparse
import requests
from cromwell_tools.cromwell_api import CromwellAPI
from cromwell_tools.cromwell_auth import CromwellAuth
from cromwell_tools import __version__


def parser(arguments=None):
    # TODO: dynamically walk through the commands and automatcally create parsers here

    main_parser = argparse.ArgumentParser()

    # Check the installed version of Cromwell-tools
    main_parser.add_argument(
        '-V', '--version', action='version', version=f'%(prog)s {__version__}'
    )

    subparsers = main_parser.add_subparsers(help='sub-command help', dest='command')

    # sub-commands of cromwell-tools
    submit = subparsers.add_parser(
        'submit', help='submit help', description='Submit a WDL workflow on Cromwell.'
    )
    wait = subparsers.add_parser(
        'wait',
        help='wait help',
        description='Wait for one or more running workflow to finish.',
    )
    status = subparsers.add_parser(
        'status',
        help='status help',
        description='Get the status of one or more workflows.',
    )
    abort = subparsers.add_parser(
        'abort',
        help='abort help',
        description='Request Cromwell to abort a running workflow by UUID.',
    )
    release_hold = subparsers.add_parser(
        'release_hold',
        help='release_hold help',
        description='Request Cromwell to release the hold on a workflow.',
    )
    query = subparsers.add_parser(
        'query',
        help='query help',
        description='[NOT IMPLEMENTED IN CLI] Query for workflows.',
    )
    health = subparsers.add_parser(
        'health',
        help='health help',
        description='Check that cromwell is running and that provided authentication is valid.',
    )

    # cromwell url and authentication arguments apply to all sub-commands
    cromwell_sub_commands = (submit, wait, status, abort, release_hold, query, health)
    auth_args = {
        'url': 'The URL to the Cromwell server. e.g. "https://cromwell.server.org/"',
        'username': 'Cromwell username for HTTPBasicAuth.',
        'password': 'Cromwell password for HTTPBasicAuth.',
        'secrets_file': 'Path to the JSON file containing username, password, and url fields.',
        'service_account_key': 'Path to the JSON key file for authenticating with CaaS.',
    }

    def add_auth_args(subcommand_parser):
        for arg_dest, help_text in auth_args.items():
            subcommand_parser.add_argument(
                '--{arg}'.format(arg=arg_dest.replace('_', '-')),
                dest=arg_dest,
                default=None,
                type=str,
                help=help_text,
            )

    # TODO: this should be a group which is called authentication
    for p in cromwell_sub_commands:
        add_auth_args(p)

    # submit arguments
    submit.add_argument(
        '-w',
        '--wdl-file',
        dest='wdl_file',
        type=str,
        required=True,
        help='Path to the workflow source file to submit for execution.',
    )
    submit.add_argument(
        '-i',
        '--inputs-files',
        dest='inputs_files',
        nargs='+',
        type=str,
        required=True,
        help='Path(s) to the input file(s) containing input data in JSON format, separated by space.',
    )
    submit.add_argument(
        '-d',
        '--deps-file',
        dest='dependencies',
        nargs='+',
        type=str,
        help='Path to the Zip file containing dependencies, or a list of raw dependency files to '
        'be zipped together separated by space.',
    )
    submit.add_argument(
        '-o',
        '--options-file',
        dest='options_file',
        type=str,
        help='Path to the Cromwell configs JSON file.',
    )
    # TODO: add a mutually exclusive group to make it easy to add labels for users
    submit.add_argument(
        '-l',
        '--label-file',
        dest='label_file',
        type=str,
        default=None,
        help='Path to the JSON file containing a collection of key/value pairs for workflow labels.',
    )
    submit.add_argument(
        '-c',
        '--collection-name',
        dest='collection_name',
        type=str,
        default=None,
        help='Collection in SAM that the workflow should belong to, if use CaaS.',
    )
    submit.add_argument(
        '--on-hold',
        dest='on_hold',
        type=bool,
        default=False,
        help='Whether to submit the workflow in "On Hold" status.',
    )
    submit.add_argument(
        '--validate-labels',
        dest='validate_labels',
        type=bool,
        default=False,
        help='Whether to validate cromwell labels.',
    )

    # wait arguments
    wait.add_argument('workflow_ids', nargs='+')
    wait.add_argument(
        '--timeout-minutes',
        dest='timeout_minutes',
        type=int,
        default=120,
        help='number of minutes to wait before timeout.',
    )
    wait.add_argument(
        '--poll-interval-seconds',
        dest='poll_interval_seconds',
        type=int,
        default=30,
        help='seconds between polling cromwell for workflow status.',
    )
    wait.add_argument(
        '--silent',
        dest='verbose',
        action='store_false',
        help='whether to silently print verbose workflow information while polling cromwell.',
    )

    # status arguments
    status.add_argument(
        '--uuid',
        required=True,
        help='A Cromwell workflow UUID, which is the workflow identifier.',
    )

    # abort arguments
    abort.add_argument(
        '--uuid',
        required=True,
        help='A Cromwell workflow UUID, which is the workflow identifier.',
    )

    # release_hold arguments
    release_hold.add_argument(
        '--uuid',
        required=True,
        help='A Cromwell workflow UUID, which is the workflow identifier.',
    )

    # query arguments
    # TODO: implement CLI entry for query API.

    # group all of the arguments
    args = vars(main_parser.parse_args(arguments))

    # TODO: see if this can be moved or if the commands can be populated from above
    if args['command'] in (
        'submit',
        'wait',
        'status',
        'abort',
        'release_hold',
        'health',
    ):
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
