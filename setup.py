from setuptools import setup


CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Natural Language :: English",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
]

install_requires = [
    'requests>=2.20.0,<3',
    'six>=1.11.0',
    'google-auth>=1.6.1,<2' 'setuptools_scm>=3.1.0,<4',
]

extras_require = {
    'test': [
        'black==19.3b0',
        'flake8==3.7.7',
        'mock>=2.0.0',
        'requests_mock>=1.4.0',
        'pre-commit==1.14.4',
        'pytest-cov>=2.5.1',
        'pytest>=3.6.3',
        'pytest-timeout>=1.3.1',
    ]
}

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
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={'console_scripts': ['cromwell-tools = cromwell_tools.cli:main']},
    include_package_data=True,
)
