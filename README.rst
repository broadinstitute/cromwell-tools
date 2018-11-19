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
From version ``v1.0.0``, you can install cromwell-tools from `PyPI <https://pypi.org/>`_:

.. code:: bash

    pip install cromwell-tools

To install the testing requirements as extras of the library, use:

.. code:: bash

    pip install "cromwell-tools[test]"

Usage
=====

Python API
----------
In Python, you can import the package with:

.. code:: python

    import cromwell_tools.api as cwt
    cwt.submit(*args)

assuming args is a list of arguments needed. For more details, please check the example `Jupyter Notebooks <https://github.com/broadinstitute/cromwell-tools/tree/master/notebooks/Quickstart>`_.

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
status of jobs and validate workflow files are exposed by this CLI.

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
