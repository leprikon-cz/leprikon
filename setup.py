# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from setuptools import setup, find_packages

from leprikon import __version__

setup(
    name            = 'leprikon',
    version         = __version__,
    description     = 'Django CMS based IS for leisure centre',
    author          = 'Jakub Dorňák',
    author_email    = 'jakub.dornak@misli.cz',
    license         = 'BSD',
    url             = 'https://github.com/leprikon-cz/leprikon',
    packages        = find_packages(),
    classifiers     = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ],
)
