Cromwell-tools
##############

.. image:: https://quay.io/repository/broadinstitute/cromwell-tools/status
    :target: https://quay.io/repository/broadinstitute/cromwell-tools
    :alt: Container Build Status
    
.. image:: https://travis-ci.org/broadinstitute/cromwell-tools.svg?branch=master
    :target: https://travis-ci.org/broadinstitute/cromwell-tools
    :alt: Test Status (Python2/3)

.. image:: https://readthedocs.org/projects/cromwell-tools/badge/?version=latest
    :target: http://cromwell-tools.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

Overview
========

This repo contains a cromwell_tools Python package, accessory scripts and IPython notebooks.

The cromwell_tools Python package is designed to be a Python API and Command Line Tool for interacting with the `Cromwell <https://github.com/broadinstitute/cromwell>`_. with the following features:
    - Python2/3 compatible.
    - Consistency in authentication to work with Cromwell.
    - Consistency between API and CLI interfaces.
    - Sufficient test cases.
    - User-friendly documentation on `Read The Docs <https://cromwell-tools.readthedocs.io/en/latest/>`_.

The accessory scripts and IPython notebooks are useful to:
    - Monitor the resource usages of workflows running in Cromwell.
    - Visualize the workflows benchmarking metrics.


Installation
============
Version ``v1.0.0`` will be on `PyPI <https://pypi.org/>`_ but until then we need to install from GitHub:

.. code:: bash

    pip install "git+git://github.com/broadinstitute/cromwell-tools.git@master#egg=cromwell-tools[test]"

You can omit [test] at the end of the pip invocation if you don't need the test cases this library provides.

Usage
=====

Python API
----------
In Python, you can import the package with:

.. code:: python

    import cromwell_tools.api as cwt
    cwt.submit(*args)

assuming args is a list of arguments needed.

Commandline Interface
---------------------

This package also installs a command line interface that mirrors the API and is used as follows:

.. code::

    $> cromwell-tools -h
    usage: cromwell-tools [-h]
                      {submit,wait,status,abort,release_hold,query,health,validate}
                      ...

    positional arguments:
      {submit,wait,status,abort,release_hold,query,health,validate}
                            sub-command help
        submit              submit help
        wait                wait help
        status              status help
        abort               abort help
        release_hold        release_hold help
        query               query help
        health              health help
        validate            validate help

    optional arguments:
      -h, --help            show this help message and exit


A set of sub-commands to submit, query, abort, release on-hold workflows, wait for workflow completion, determining
status of jobs and validate workflow files are exposed by this CLI:

- To submit a job:

.. code::

    $> cromwell-tools submit -h
    usage: cromwell-tools submit [-h] [--url URL] [--username USERNAME]
                             [--password PASSWORD]
                             [--secrets-file SECRETS_FILE]
                             [--caas-key CAAS_KEY] --wdl-file WDL_FILE
                             --inputs-file INPUTS_FILE [--zip-file ZIP_FILE]
                             [--inputs-file2 INPUTS_FILE2]
                             [--options-file OPTIONS_FILE]
                             [--collection-name COLLECTION_NAME]
                             [--label LABEL]
                             [--validate-labels VALIDATE_LABELS]
                             [--on-hold ON_HOLD]

    Submit a WDL workflow on Cromwell.

    optional arguments:
      -h, --help            show this help message and exit
      --url URL             The URL to the Cromwell server. e.g.
                            "https://cromwell.server.org/"
      --username USERNAME   Cromwell username for HTTPBasicAuth.
      --password PASSWORD   Cromwell password for HTTPBasicAuth.
      --secrets-file SECRETS_FILE
                            Path to the JSON file containing username, password,
                            and url fields.
      --caas-key CAAS_KEY   Path to the JSON key file(service account key) for
                            authenticating with CaaS.
      --wdl-file WDL_FILE   The workflow source file to submit for execution.
      --inputs-file INPUTS_FILE
                            File-like object containing input data in JSON format.
      --zip-file ZIP_FILE   Zip file containing dependencies.
      --inputs-file2 INPUTS_FILE2
                            Inputs file 2.
      --options-file OPTIONS_FILE
                            Cromwell configs file.
      --collection-name COLLECTION_NAME
                            Collection in SAM that the workflow should belong to,
                            if use CaaS.
      --label LABEL         JSON file containing a collection of key/value pairs
                            for workflow labels.
      --validate-labels VALIDATE_LABELS
                            Whether to validate cromwell labels.
      --on-hold ON_HOLD     Whether to submit the workflow in "On Hold" status.



- To wait for completion of jobs:

.. code::

    $> cromwell-tools wait -h
    usage: cromwell-tools wait [-h] [--url URL] [--username USERNAME]
                           [--password PASSWORD] [--secrets-file SECRETS_FILE]
                           [--caas-key CAAS_KEY]
                           [--timeout-minutes TIMEOUT_MINUTES]
                           [--poll-interval-seconds POLL_INTERVAL_SECONDS]
                           workflow-ids [workflow-ids ...]

    Wait for one or more running workflow to finish.

    positional arguments:
      workflow-ids

    optional arguments:
      -h, --help            show this help message and exit
      --url URL             The URL to the Cromwell server. e.g.
                            "https://cromwell.server.org/"
      --username USERNAME   Cromwell username for HTTPBasicAuth.
      --password PASSWORD   Cromwell password for HTTPBasicAuth.
      --secrets-file SECRETS_FILE
                            Path to the JSON file containing username, password,
                            and url fields.
      --caas-key CAAS_KEY   Path to the JSON key file(service account key) for
                            authenticating with CaaS.
      --timeout-minutes TIMEOUT_MINUTES
                            number of minutes to wait before timeout
      --poll-interval-seconds POLL_INTERVAL_SECONDS
                            seconds between polling cromwell for workflow status


- To determine the status(es) of jobs:

.. code::

    $> cromwell-tools status -h
    usage: cromwell-tools status [-h] [--url URL] [--username USERNAME]
                             [--password PASSWORD]
                             [--secrets-file SECRETS_FILE]
                             [--caas-key CAAS_KEY] --uuid UUID

    Get the status of one or more workflows.

    optional arguments:
      -h, --help            show this help message and exit
      --url URL             The URL to the Cromwell server. e.g.
                            "https://cromwell.server.org/"
      --username USERNAME   Cromwell username for HTTPBasicAuth.
      --password PASSWORD   Cromwell password for HTTPBasicAuth.
      --secrets-file SECRETS_FILE
                            Path to the JSON file containing username, password,
                            and url fields.
      --caas-key CAAS_KEY   Path to the JSON key file(service account key) for
                            authenticating with CaaS.
      --uuid UUID           A Cromwell workflow UUID, which is the workflow
                            identifier.


- To abort a job:

.. code::

    $> cromwell-tools abort -h
    usage: cromwell-tools abort [-h] --uuid UUID

    Request Cromwell to abort a running workflow by UUID.

    optional arguments:
      -h, --help   show this help message and exit
      --uuid UUID  A Cromwell workflow UUID, which is the workflow identifier.


- To release a job in "On Hold" status:

.. code::

    $> cromwell-tools release_hold -h
    usage: cromwell-tools release_hold [-h] --uuid UUID

    Request Cromwell to release the hold on a workflow.

    optional arguments:
      -h, --help   show this help message and exit
      --uuid UUID  A Cromwell workflow UUID, which is the workflow identifier.


- To query for jobs:

.. code::

    $> cromwell-tools query -h
    usage: cromwell-tools query [-h]

    [NOT IMPLEMENTED IN CLI] Query for workflows.

    optional arguments:
      -h, --help  show this help message and exit


- To validate the WDL file(s) of jobs:

.. code::

    $> cromwell-tools validate -h
    usage: cromwell-tools validate [-h] --wdl-file WDL_FILE --womtool-path
                               WOMTOOL_PATH
                               [--dependencies-json DEPENDENCIES_JSON]

    Validate a cromwell workflow using womtool.

    optional arguments:
      -h, --help            show this help message and exit
      --wdl-file WDL_FILE
      --womtool-path WOMTOOL_PATH
                            path to cromwell womtool jar
      --dependencies-json DEPENDENCIES_JSON


- To check the health state of the Cromwell server:

.. code::

    $> cromwell-tools health -h
    usage: cromwell-tools health [-h] [--url URL] [--username USERNAME]
                             [--password PASSWORD]
                             [--secrets-file SECRETS_FILE]
                             [--caas-key CAAS_KEY]

    Check that cromwell is running and that provided authentication is valid.

    optional arguments:
      -h, --help            show this help message and exit
      --url URL             The URL to the Cromwell server. e.g.
                            "https://cromwell.server.org/"
      --username USERNAME   Cromwell username for HTTPBasicAuth.
      --password PASSWORD   Cromwell password for HTTPBasicAuth.
      --secrets-file SECRETS_FILE
                            Path to the JSON file containing username, password,
                            and url fields.
      --caas-key CAAS_KEY   Path to the JSON key file(service account key) for
                            authenticating with CaaS.


Testing
=======

To run tests:

Run Tests with Docker
---------------------
Running the tests within docker image is the recommended way, to do this, you need to have docker-daemon installed
in your environment. From the root of the cromwell-tools repo:

- Testing with Python 2.7, run:

.. code::

    cd cromwell_tools/tests && bash test.sh "python2"

- Testing with Python 3.5, run:

.. code::

    cd cromwell_tools/tests && bash test.sh "python3"


Run Tests with local Python environment
---------------------------------------
- If you have to run the tests with your local Python environment, we highly recommend to create and activate a
  `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ with requirements before you run the tests:

.. code::

    virtualenv test-env
    source test-env/bin/activate
    pip install -r requirements.txt -r requirements-test.txt

- Besides, the ``validate`` command of cromwell-tools requires you specify the path to the
  `womtool.jar <https://github.com/broadinstitute/cromwell/tree/master/womtool>`_ so if you are running the tests
  without using the docker image, you have to export the path to the womtool as an environment variable as follows,
  otherwise the test suite will skip running the tests for ``validate``!

.. code::

    export WOMTOOL="/path/to/the/womtool/womtool-35.jar"


- Finally, from the root of the cromwell-tools repo, run the tests with:

.. code::

    python -m pytest --cov=cromwell_tools cromwell_tools/tests

.. note::

    Which version of Python is used to run the tests here depends on the virtualenv parameter. You can use
    ``virtualenv -p`` to choose which Python version you want to create the virtual environment.


Development
===========

When upgrading the dependencies of cromwell-tools, please make sure ``requirements.txt``, ``requirements-test.txt``
and ``setup.py`` are consistent!
