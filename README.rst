Cromwell-tools
##############

.. image:: https://travis-ci.org/broadinstitute/cromwell-tools.svg?branch=master
    :target: https://travis-ci.org/broadinstitute/cromwell-tools

.. image:: https://readthedocs.org/projects/cromwell-tools/badge/?version=latest
    :target: http://cromwell-tools.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. note::
    This tool is still under active development, so there could be significant changes to its API.

Overview
========

This repo contains a cromwell_tools Python package and IPython notebooks for interacting with the `Cromwell <https://github.com/broadinstitute/cromwell>`_

Installation
============

Install it like this:

.. code:: bash

    pip install git+git://github.com/broadinstitute/cromwell-tools.git


Usage
=====

Commandline Interface
---------------------

This package installs a command line interface, which is used as follows:

.. code::

    $> cromwell-tools -h
    usage: cromwell-tools [-h] {run,wait,status} ...

    positional arguments:
      {run,wait,status}  sub-command help
        run              run help
        wait             wait help
        status           status help

    optional arguments:
      -h, --help         show this help message and exit


Sub-commands to start, wait for completion, and determining status of jobs are exposed by this CLI:

- To start a job:

.. code::

    cromwell-tools run -h
    usage: cromwell-tools run [-h] [-c CROMWELL_URL] [-u USERNAME] [-p PASSWORD]
                              [-s SECRETS_FILE] --wdl-file WDL_FILE
                              [--dependencies-json DEPENDENCIES_JSON]
                              --inputs-json INPUTS_JSON
                              [--inputs2-json INPUTS2_JSON]
                              [--options-file OPTIONS_FILE]

    Run a WDL workflow on Cromwell.

    optional arguments:
      -h, --help            show this help message and exit
      -c CROMWELL_URL, --cromwell-url CROMWELL_URL
      -u USERNAME, --username USERNAME
      -p PASSWORD, --password PASSWORD
      -s SECRETS_FILE, --secrets-file SECRETS_FILE
      --wdl-file WDL_FILE
      --dependencies-json DEPENDENCIES_JSON
      --inputs-json INPUTS_JSON
      --inputs2-json INPUTS2_JSON
      --options-file OPTIONS_FILE

- To wait for completion of jobs:

.. code::

    $> cromwell-tools wait -h
    usage: cromwell-tools wait [-h] [-c CROMWELL_URL] [-u USERNAME] [-p PASSWORD]
                               [-s SECRETS_FILE] --workflow-ids WORKFLOW_IDS
                               [WORKFLOW_IDS ...]
                               [--timeout-minutes TIMEOUT_MINUTES]
                               [--poll-interval-seconds POLL_INTERVAL_SECONDS]

    Wait for one or more running workflow to finish.

    optional arguments:
      -h, --help            show this help message and exit
      -c CROMWELL_URL, --cromwell-url CROMWELL_URL
      -u USERNAME, --username USERNAME
      -p PASSWORD, --password PASSWORD
      -s SECRETS_FILE, --secrets-file SECRETS_FILE
      --workflow-ids WORKFLOW_IDS [WORKFLOW_IDS ...]
      --timeout-minutes TIMEOUT_MINUTES
                            number of minutes to wait before timeout
      --poll-interval-seconds POLL_INTERVAL_SECONDS
                            seconds between polling cromwell for workflow status

- To determine the status(es) of jobs:

.. code::

    cromwell-tools status -h
    usage: cromwell-tools status [-h] [-c CROMWELL_URL] [-u USERNAME]
                                 [-p PASSWORD] [-s SECRETS_FILE] --workflow-ids
                                 WORKFLOW_IDS [WORKFLOW_IDS ...]

    Get the status of one or more workflows.

    optional arguments:
      -h, --help            show this help message and exit
      -c CROMWELL_URL, --cromwell-url CROMWELL_URL
      -u USERNAME, --username USERNAME
      -p PASSWORD, --password PASSWORD
      -s SECRETS_FILE, --secrets-file SECRETS_FILE
      --workflow-ids WORKFLOW_IDS [WORKFLOW_IDS ...]

Python API
----------
The rest of the package consists of scripts that are meant to be invoked from the command line.

In Python, you can then import the package with:

.. code:: python

    from cromwell_tools import cromwell_tools
    cromwell_tools.start_workflow(*args)

assuming args is a list of arguments needed.

Testing
=======

To run tests:

Create and activate a virtualenv with requirements:

.. code::

    virtualenv test-env
    pip install -r requirements.txt -r test-requirements.txt
    source test-env/bin/activate


Then, from the root of the cromwell-tools repo, do:

.. code::

    python -m unittest discover -v

This runs all the tests in the cromwell_tools package.
