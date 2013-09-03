# -*- coding: utf-8 -*-
import sys
import os

import portal.input.syslog as syslog

from setuptools import setup, find_packages
from setuptools.command import easy_install
from distutils.extension import Extension

try:
    from Cython.Compiler.Main import compile
    from Cython.Distutils import build_ext
    has_cython = True
except ImportError:
    has_cython = False


def read(relative):
    contents = open(relative, 'r').read()
    return [l for l in contents.split('\n') if l != '']


ext_modules = list()
ext_modules.append(syslog.FFI.verifier.get_extension())

setup(
    name='meniscus-portal',
    version='0.2.0.2',
    description='low level parsing bindings for meniscus',
    author='John Hopper',
    author_email='john.hopper@jpserver.net',
    url='https://github.com/ProjectMeniscus/portal',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Logging',
        'Programming Language :: Python',
        'Programming Language :: Cython',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3'
    ],
    tests_require=read('./tools/test-requires'),
    install_requires=read('./tools/pip-requires'),
    test_suite='nose.collector',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['*.tests']),
    ext_modules=ext_modules)
