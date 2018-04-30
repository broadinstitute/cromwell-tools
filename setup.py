from setuptools import setup

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Natural Language :: English",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
]


setup(
    name='cromwell-tools',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    description='Utilities for interacting with the Cromwell workflow engine',
    classifiers=CLASSIFIERS,
    url='http://github.com/broadinstitute/cromwell-tools',
    author='Mint Team',
    author_email='mintteam@broadinstitute.org',
    license='BSD 3-clause "New" or "Revised" License',
    packages=['cromwell_tools'],
    install_requires=[
        'requests>=2.18.4',
        'six>=1.11.0',
        'oauth2client>=4.1.2',
        'tenacity>=4.10.0',
        'setuptools_scm>=2.0.0'
    ],
    scripts=['cromwell_tools/scripts/cromwell-tools'],
    include_package_data=True
)

