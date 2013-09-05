# -*- coding: utf-8 -*-
import sys
import os

from setuptools import setup, find_packages
from distutils.extension import Extension

try:
    from Cython.Compiler.Main import compile
    from Cython.Distutils import build_ext
    has_cython = True
except ImportError:
    has_cython = False


COMPILER_ARGS = list()

DEBUG = os.getenv('DEBUG')

if DEBUG and DEBUG.lower() == 'true':
    COMPILER_ARGS.append('-D DEBUG_OUTPUT')


def read(relative):
    contents = open(relative, 'r').read()
    return [l for l in contents.split('\n') if l != '']


def module_files(module_name, *extensions):
    found = list()
    filename_base = module_name.replace('.', '/')
    for extension in extensions:
        filename = '{}.{}'.format(filename_base, extension)
        if os.path.isfile(filename):
            found.append(filename)
    return found


def fail_build(reason, code=1):
    print(reason)
    sys.exit(code)


def cythonize():
    if not has_cython:
        fail_build('In order to build this project, cython is required.')

    for module in read('./tools/cython-modules'):
        if has_cython:
            for cython_target in module_files(module, 'pyx', 'pyd'):
                compile(cython_target)


def package_c():
    extensions = list()
    extensions.append(Extension(
        'portal.input.syslog.usyslog',
        include_dirs=['include/'],
        sources=[
            'include/usyslog.c',
            'include/cstr.c',
            'portal/input/syslog/usyslog.c'
        ],
        extra_compile_args=COMPILER_ARGS))
    return extensions

ext_modules = None

# Got tired of fighting build_ext
if 'build' in sys.argv:
    cythonize()

ext_modules = package_c()

setup(
    name='meniscus-portal',
    version='0.2.1.0',
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
