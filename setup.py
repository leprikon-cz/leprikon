#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

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
    include_package_data = True,
    install_requires=[
        'django>=1.9',
        'django-cms>=3.4',
        'djangocms_text_ckeditor',
        'django-filer',
        'cmsplugin-filer',
        'django-localflavor',
        'xhtml2pdf',
        'django-ganalytics',
        'django-countries',
    ],
    classifiers     = [
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
