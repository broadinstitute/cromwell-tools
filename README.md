# cromwell-tools

This repo contains a cromwell_tools Python package and IPython notebooks for interacting with Cromwell.

# Install and use
```
pip install git+git://github.com/broadinstitute/cromwell-tools.git
```

In Python, you can then do:
```
from cromwell_tools import cromwell_tools
cromwell_tools.start_workflow(*args)
```
assuming args is a list of arguments needed

# Run tests
Create and activate a virtualenv with requirements
```
virtualenv test-env
pip install -r requirements.txt -r test-requirements.txt
source test-env/bin/activate
```

Then, from the root of the cromwell-tools repo, do:
```
python -m unittest discover -v
```

This runs all the tests in the cromwell_tools package.
