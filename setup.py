#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'cinder',
]

test_requirements = [
]

setup(
    name='alt_cinder_sch',
    version='0.1.0',
    description=("Alternative Classes -filter, host manager, etc.- for "
                 "OpenStack's Cinder"),
    long_description=readme + '\n\n' + history,
    author="Gorka Eguileor",
    author_email='gorka@eguileor.com',
    url='https://github.com/akrog/alt_cinder_sch',
    packages=[
        'alt_cinder_sch', 'alt_cinder_sch.filters',
    ],
    package_dir={'alt_cinder_sch':
                 'alt_cinder_sch'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='OpenStack Cinder scheduler filter',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points={
        'cinder.scheduler.filters': [
            'AltCapacityFilter = alt_cinder_sch.filters.capacity_filter:'
            'AltCapacityFilter',
        ],
    }
)
