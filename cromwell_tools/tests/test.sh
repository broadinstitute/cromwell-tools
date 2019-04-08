#! /usr/bin/env bash

# note that this script can only be executed within the directory it lives in.
docker build -t cromwell-tools:test ../..

# Run unit tests in docker container
docker run cromwell-tools:test python -m pytest --cov=cromwell_tools cromwell_tools/tests
