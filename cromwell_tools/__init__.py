"""The pkg_resources module will try to get the right version through the setuptools_scm, which will try to
detect the version of cromwell_tools package from any git tags, commit hash codes. This works if this Python package
 is either installed from PyPI or installed via git directly."""

from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass
