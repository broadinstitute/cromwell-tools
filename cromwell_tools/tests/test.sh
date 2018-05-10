#! /usr/bin/env bash

# note that this script can only be executed within the directory it lives in.
docker build -t cromwell-tools:test ../..

# Run unit tests in docker container
docker run --entrypoint python3 cromwell-tools:test -m unittest discover -v
