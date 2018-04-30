import argparse

from ._cromwell_api import CromwellAPI
from ._cromwell_auth import CromwellAuth


def parser(arguments=None):
    main_parser = argparse.ArgumentParser()

    subparsers = main_parser.add_subparsers(help='sub-command help', dest='command')

    # sub-commands of cromwell-tools
    run = subparsers.add_parser(
        'run', help='run help', description='Run a WDL workflow on Cromwell.')
    wait = subparsers.add_parser(
        'wait', help='wait help', description='Wait for one or more running workflow to finish.')
    status = subparsers.add_parser(
        'status', help='status help', description='Get the status of one or more workflows.')
    health = subparsers.add_parser(
        'health', help='health help',
        description='Check that cromwell is running and that provided authentication is valid')

    # cromwell url and security arguments apply to all sub-commands
    cromwell_sub_commands = [run, wait, status, health]
    # todo this should be a group which is called authentication
    for p in cromwell_sub_commands:
        p.add_argument('--url', default=None)
        p.add_argument('--username', default=None)
        p.add_argument('--password', default=None)
        p.add_argument('--secrets-file', default=None)
        p.add_argument('--caas-key', default=None)

    # run arguments
    run.add_argument('--wdl-file', type=str, required=True)
    run.add_argument('--inputs-json', type=str, required=True)
    run.add_argument('--dependencies-json', type=str)
    run.add_argument('--inputs2-json', type=str)
    run.add_argument('--options-file', type=str)

    # wait arguments
    wait.add_argument('workflow-ids', nargs='+')
    wait.add_argument('--timeout-minutes', type=int, default=120,
                      help='number of minutes to wait before timeout')
    wait.add_argument('--poll-interval-seconds', type=int, default=30,
                      help='seconds between polling cromwell for workflow status')

    # status arguments
    status.add_argument('--uuid', required=True)

    args = vars(main_parser.parse_args(arguments))

    # todo see if this can be moved or if the commands can be populated from above
    if args['command'] in ('run', 'wait', 'status', 'health'):
        auth = CromwellAuth.harmonize_credentials(**args)
        args['auth'] = auth

    command = getattr(CromwellAPI, args['command'])
    del args['command']
    return command, args


# this should just getattr from CromwellAPI and call the func with args.
def main(arguments=None):
    command, args = parser(arguments)
    command(**args)
