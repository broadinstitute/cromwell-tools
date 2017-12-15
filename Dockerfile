FROM ubuntu:17.04

LABEL maintainer = "Ambrose J. Carr <acarr@broadinstitute.org>" \
  software = "cromwell-tools" \
  version = "1.0.1" \
  description = "python package and CLI for interacting with cromwell" \
  website = "https://github.com/broadinstitute/cromwell-tools.git"

RUN apt-get update && apt-get upgrade -y

RUN apt-get -y install --no-install-recommends \
  python-pip \
  python-setuptools

RUN pip install wheel

COPY . .
RUN pip install -r requirements.txt
RUN pip install .
