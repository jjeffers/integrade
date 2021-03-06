#!/usr/bin/env python3
"""A setuptools-based script for installing integrade."""
import os

from setuptools import find_packages, setup

_project_root = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(_project_root, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='integrade',
    author='Cloudigrade QE Team',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Quality Assurance'
    ],
    description=(
        'A GPL-licensed Python library that facilitates functional testing of '
        'cloudigrade.'
    ),
    extras_require={
        'dev': [
            # For `make lint`
            'flake8',
            'flake8-docstrings',
            'flake8-import-order',
            'flake8-quotes',
            # For `make test-coverage`
            'pytest-cov',
        ],
    },
    install_requires=[
        'awscli',
        'boto3',
        'click',
        'flaky',
        'pytest',
        'pytest-selenium',
        'python-dateutil',
        'pyxdg',
        'pyyaml',
        'requests',
        'widgetastic.core',
        'widgetastic.patternfly',
    ],
    license='GPLv3',
    long_description=long_description,
    packages=find_packages(include=['integrade*']),
    url='https://gitlab.com/cloudigrade/integrade',
)
