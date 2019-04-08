FROM python:3.6

LABEL maintainer = "Mint Team <mintteam@broadinstitute.org>" \
  software = "cromwell-tools" \
  description = "python package and CLI for interacting with cromwell" \
  website = "https://github.com/broadinstitute/cromwell-tools.git"

# Upgrade pip
RUN pip install --upgrade pip
RUN pip install wheel
RUN pip install --upgrade setuptools

# Copy the source code
WORKDIR /cromwell-tools
COPY . .

# Install dependencies(including those for testing) from the source code
RUN pip install .[test]
