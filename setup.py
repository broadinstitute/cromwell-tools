from setuptools import setup

setup(name='cromwell-tools',
      version='1.0.0.dev1',
      description='Utilities for interacting with the Cromwell workflow engine',
      url='http://github.com/broadinstitute/cromwell-tools',
      author='Mint Team',
      author_email='mintteam@broadinstitute.org',
      license='BSD 3-clause "New" or "Revised" License',
      packages=['cromwell_tools'],
      install_requires=[
          'requests'
      ],
      include_package_data=True
      )
