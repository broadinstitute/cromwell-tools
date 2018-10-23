#! /usr/bin/env bash

# Usage: bash test.sh [python_version] where python_version is in {"python2", "python3"}
# By default, it this script will run on python3

python_version=${1:-"python3"}

# note that this script can only be executed within the directory it lives in.
docker build -t cromwell-tools:test ../..

# Run unit tests in docker container
if [ "$python_version" == "python2" ]; then
  docker run cromwell-tools:test python2 -m pytest --cov=cromwell_tools cromwell_tools/tests
else
  docker run cromwell-tools:test python3 -m pytest --cov=cromwell_tools cromwell_tools/tests
fi
