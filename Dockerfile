FROM ubuntu:16.04

LABEL maintainer = "Mint Team <mintteam@broadinstitute.org>" \
  software = "cromwell-tools" \
  description = "python package and CLI for interacting with cromwell" \
  website = "https://github.com/broadinstitute/cromwell-tools.git"

# Install required packages
RUN apt-get update && apt-get upgrade -y && apt-get -y install --no-install-recommends --fix-missing \
    python-pip \
    python3-pip \
    git

# Install java 8
RUN apt-get update && \
    apt-get install -y openjdk-8-jdk && \
    apt-get clean all

# Download and expose womtool
ADD https://github.com/broadinstitute/cromwell/releases/download/35/womtool-35.jar /usr/local/bin/womtool/womtool-35.jar
ENV WOMTOOL /usr/local/bin/womtool/womtool-35.jar

# Upgrade pip for Python2
RUN pip install --upgrade pip
RUN pip install wheel
RUN pip install --upgrade setuptools

# Upgrade pip3 for Python3
RUN pip3 install -U setuptools
RUN pip3 install -U pip
RUN pip3 install wheel

# Copy the whole module
WORKDIR /cromwell-tools
COPY . .

# Install dependencies(including those for testing)
RUN pip2 install .[test]
RUN pip3 install .[test]
