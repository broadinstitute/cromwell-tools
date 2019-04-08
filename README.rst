Cromwell-tools
##############

.. image:: https://quay.io/repository/broadinstitute/cromwell-tools/status
    :target: https://quay.io/repository/broadinstitute/cromwell-tools
    :alt: Container Build Status
    
.. image:: https://img.shields.io/travis/com/broadinstitute/cromwell-tools.svg?label=Unit%20Test%20on%20Travis%20CI%20&style=flat-square
    :target: https://travis-ci.org/broadinstitute/cromwell-tools
    :alt: Unit Test Status

.. image:: https://img.shields.io/readthedocs/cromwell-tools/latest.svg?label=ReadtheDocs%3A%20Latest&logo=Read%20the%20Docs&style=flat-square
    :target: http://cromwell-tools.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/github/release/broadinstitute/cromwell-tools.svg?label=Latest%20Release&style=flat-square&colorB=green
    :target: https://github.com/broadinstitute/cromwell-tools/releases
    :alt: Latest Release

.. image:: https://img.shields.io/github/license/broadinstitute/cromwell-tools.svg?style=flat-square
    :target: https://img.shields.io/github/license/broadinstitute/cromwell-tools.svg?style=flat-square
    :alt: License

.. image:: https://img.shields.io/badge/python-3.6-green.svg?style=flat-square&logo=python&colorB=blue
    :target: https://img.shields.io/badge/python-3.6-green.svg?style=flat-square&logo=python&colorB=blue
    :alt: Language

.. image:: https://img.shields.io/badge/Code%20Style-black-000000.svg?style=flat-square
    :target: https://github.com/ambv/black
    :alt: Code Style

Overview
========

This repo contains a cromwell_tools Python package, accessory scripts and IPython notebooks.

The cromwell_tools Python package is designed to be a Python API and Command Line Tool for interacting with the `Cromwell <https://github.com/broadinstitute/cromwell>`_. with the following features:
    - Python3 compatible. (Starting from release v2.0.0, cromwell-tools will no longer support Python 2.7)
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
                      {submit,wait,status,abort,release_hold,query,health}
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

.. code::

    cd cromwell_tools/tests && bash test.sh


Run Tests with local Python environment
---------------------------------------
- If you have to run the tests with your local Python environment, we highly recommend to create and activate a
  `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ with requirements before you run the tests:

.. code::

    virtualenv test-env
    source test-env/bin/activate
    pip install -r requirements.txt -r requirements-test.txt

- Finally, from the root of the cromwell-tools repo, run the tests with:

.. code::

    python -m pytest --cov=cromwell_tools cromwell_tools/tests

.. note::

    Which version of Python is used to run the tests here depends on the virtualenv parameter. You can use
    ``virtualenv -p`` to choose which Python version you want to create the virtual environment.


Development
===========

Code Style
----------
The cromwell-tools code base is complying with the PEP-8 and using `Black <https://github.com/ambv/black>`_ to
format our code, in order to avoid "nitpicky" comments during the code review process so we spend more time discussing about the logic, 
not code styles.

In order to enable the auto-formatting in the development process, you have to spend a few seconds setting 
up the ``pre-commit`` the first time you clone the repo:

1. Install ``pre-commit`` by running: ``pip install pre-commit`` (or simply run ``pip install -r requirements.txt``).
2. Run `pre-commit install` to install the git hook.

Once you successfully install the ``pre-commit`` hook to this repo, the Black linter/formatter will be automatically triggered and run on this repo. Please make sure you followed the above steps, otherwise your commits might fail at the linting test!

If you really want to manually trigger the linters and formatters on your code, make sure ``Black`` and ``flake8`` are installed in your Python environment and run ``flake8 DIR1 DIR2`` and ``black DIR1 DIR2 --skip-string-normalization`` respectively.

Dependencies
------------
When upgrading the dependencies of cromwell-tools, please make sure ``requirements.txt``, ``requirements-test.txt`` and ``setup.py`` are consistent!
