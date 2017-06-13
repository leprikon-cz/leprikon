#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages

from leprikon import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    long_description = readme.read()

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as requirements:
    install_requires = [
        line.strip() for line in requirements.readlines()
        if not line.startswith('#')
    ]

setup(
    name='leprikon',
    version=__version__,
    description='Django CMS based IS for leisure centre',
    long_description=long_description,
    author='Jakub Dorňák',
    author_email='jakub.dornak@misli.cz',
    license='BSD',
    url='https://github.com/leprikon-cz/leprikon',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    scripts=['bin/leprikon'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Natural Language :: Czech',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
