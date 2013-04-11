# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
    from multiprocessing import util
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

COMPILER_ARGS = ['-O2']

def sources_of(name):
    return [name + '.pyx']

setup(
    name = 'Meniscus Portal',
    version = '0.1',
    description = '',
    author = 'John Hopper',
    author_email='',
    tests_require=[
        "mock",
        "nose",
    ],
    install_requires=[
        "cython",
        "pyev"
    ],
    test_suite = 'nose.collector',
    zip_safe = False,
    include_package_data = True,
    packages = find_packages(exclude=['ez_setup']),
    cmdclass = {
        'build_ext': build_ext
    },
    ext_modules = [
        Extension("portal.input.rfc5424",
                  sources_of('portal/input/rfc5424'),
                  extra_compile_args=COMPILER_ARGS),
        Extension("portal.input.json_stream",
                  sources_of('portal/input/json_stream'),
                  extra_compile_args=COMPILER_ARGS)
    ]
)

