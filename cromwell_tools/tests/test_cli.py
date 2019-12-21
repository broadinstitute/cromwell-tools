import pytest
from cromwell_tools.cli import parser as cli_parser
import tempfile
import os
import six
import json
from cromwell_tools.cromwell_auth import CromwellAuth


six.add_move(six.MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock  # noqa


@pytest.fixture(scope="module")
def username_password_auth():
    return [
        "--username",
        "fake-user",
        "--password",
        "fake-pwd",
        "--url",
        "https://fake-cromwell",
    ]


@pytest.fixture(scope="module")
def no_auth():
    return ["--url", "https://fake-cromwell"]


@pytest.fixture(scope="module")
def service_account_auth():
    temp_dir = tempfile.mkdtemp()
    service_account_key = os.path.join(temp_dir, 'fake_key.json')
    fake_svc_info = {"token_uri": "foo", "client_email": "bar", "private_key": "baz"}
    with open(service_account_key, 'w') as f:
        json.dump(fake_svc_info, f)
    return [
        "--service-account-key",
        service_account_key,
        "--url",
        "https://fake-cromwell",
    ]


@pytest.fixture(scope="module")
def secret_file_auth():
    temp_dir = tempfile.mkdtemp()
    secrets_file = os.path.join(temp_dir, 'fake_secrets.json')
    auth_params = {
        "url": "https://fake-cromwell",
        "username": "fake-user",
        "password": "fake-pwd",
    }
    with open(secrets_file, 'w') as f:
        json.dump(auth_params, f)
    return ["--secrets-file", secrets_file]


def test_cli_print_version_info():
    """Make sure the CLI prints version info properly"""
    user_inputs = ["-V"]
    with pytest.raises(SystemExit) as pytest_wrapped_exit:
        cli_parser(user_inputs)
    assert pytest_wrapped_exit.type == SystemExit
    assert pytest_wrapped_exit.value.code == 0


def test_cli_command_raise_value_error_when_no_creds_provided():
    """Make sure the CLI raise exception about the auth when no creds provided."""
    user_inputs = ["submit", "--wdl-file", "fake.wdl", "--inputs-files", "fake.json"]
    with pytest.raises(ValueError):
        command, args = cli_parser(user_inputs)


def test_cli_command_works_with_username_password_auth(username_password_auth):
    """Use the submit command as an example to prove CLI works with u/p auth."""
    user_inputs = [
        "submit",
        "--wdl-file",
        "fake.wdl",
        "--inputs-files",
        "fake.json",
    ] + username_password_auth
    command, args = cli_parser(user_inputs)


def test_cli_command_works_with_no_auth(no_auth):
    """Use the submit command as an example to prove CLI works with u/p auth."""
    user_inputs = [
        "submit",
        "--wdl-file",
        "fake.wdl",
        "--inputs-files",
        "fake.json",
    ] + no_auth
    command, args = cli_parser(user_inputs)


@mock.patch('cromwell_tools.cromwell_auth.CromwellAuth.from_service_account_key_file')
def test_cli_command_works_with_service_account_auth(mock_header, service_account_auth):
    """Use the submit command as an example to prove CLI works with u/p auth."""
    expected_auth = CromwellAuth(
        url="https://fake-cromwell",
        header={"Authorization": "bearer fake_token"},
        auth=None,
    )
    mock_header.return_value = expected_auth
    user_inputs = [
        "submit",
        "--wdl-file",
        "fake.wdl",
        "--inputs-files",
        "fake.json",
    ] + service_account_auth
    command, args = cli_parser(user_inputs)


def test_cli_command_works_with_secrets_file_auth(secret_file_auth):
    """Use the submit command as an example to prove CLI works with u/p auth."""
    user_inputs = [
        "submit",
        "--wdl-file",
        "fake.wdl",
        "--inputs-files",
        "fake.json",
    ] + secret_file_auth
    command, args = cli_parser(user_inputs)


def test_cli_submit_command(no_auth):
    """Test the submit command (with no-auth for simplicity)."""
    user_inputs = [
        "submit",
        "--wdl-file",
        "fake.wdl",
        "--inputs-files",
        "fake.json",
    ] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "submit"
    assert args['wdl_file'] == "fake.wdl"
    assert "fake.json" in args['inputs_files']


def test_cli_wait_command(no_auth):
    """Test the wait command (with no-auth for simplicity)."""
    user_inputs = [
        "wait",
        "--poll-interval-seconds",
        "10",
        "00000000-0000-0000-0000-000000000000",
        "00000000-0000-0000-0000-000000000000",
    ] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "wait"
    assert "00000000-0000-0000-0000-000000000000" in args["workflow_ids"]


def test_cli_status_command(no_auth):
    """Test the status command (with no-auth for simplicity)."""
    user_inputs = ["status", "--uuid", "00000000-0000-0000-0000-000000000000"] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "status"
    assert args["uuid"] == "00000000-0000-0000-0000-000000000000"


def test_cli_abort_command(no_auth):
    """Test the abort command (with no-auth for simplicity)."""
    user_inputs = ["abort", "--uuid", "00000000-0000-0000-0000-000000000000"] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "abort"
    assert args["uuid"] == "00000000-0000-0000-0000-000000000000"


def test_cli_release_hold_command(no_auth):
    """Test the release hold command (with no-auth for simplicity)."""
    user_inputs = [
        "release_hold",
        "--uuid",
        "00000000-0000-0000-0000-000000000000",
    ] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "release_hold"
    assert args["uuid"] == "00000000-0000-0000-0000-000000000000"


def test_cli_metadata_command(no_auth):
    """Test the metadata command (with no-auth for simplicity)."""
    user_inputs = [
        "metadata",
        "--uuid",
        "00000000-0000-0000-0000-000000000000",
        "--includeKey",
        "jobId",
    ] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "metadata"
    assert args["uuid"] == "00000000-0000-0000-0000-000000000000"
    assert "jobId" in args["includeKey"]


def test_cli_query_command(no_auth):
    """Test the query command (with no-auth for simplicity)."""
    # Not Implemented yet
    assert True


def test_cli_health_command(no_auth):
    """Test the health command (with no-auth for simplicity)."""
    user_inputs = ["health"] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "health"


def test_cli_task_runtime_command(no_auth):
    """Test the task_runtime command (with no-auth for simplicity)."""
    user_inputs = [
        "task_runtime",
        "--uuid",
        "00000000-0000-0000-0000-000000000000",
    ] + no_auth
    command, args = cli_parser(user_inputs)
    assert command.__name__ == "run"  # task_runtime's entrypoint is run()
    assert args["uuid"] == "00000000-0000-0000-0000-000000000000"
