FROM ubuntu:16.04

LABEL maintainer = "Mint Team <mintteam@broadinstitute.org>" \
  software = "cromwell-tools" \
  description = "python package and CLI for interacting with cromwell" \
  website = "https://github.com/broadinstitute/cromwell-tools.git"

RUN apt-get update && apt-get upgrade -y

RUN apt-get -y install --no-install-recommends \
  python-pip \
  git

RUN pip install --upgrade pip

RUN pip install wheel
RUN pip install --upgrade setuptools

COPY . .

RUN pip install -r requirements.txt

RUN python setup.py install
