# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
    from setuptools.command import easy_install
    from multiprocessing import util
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
    from setuptools.command import easy_install

from distutils.core import setup
from distutils.extension import Extension

try:
    from Cython.Compiler.Main import compile
    from Cython.Distutils import build_ext
    has_cython = True
except ImportError:
    has_cython = False

SOURCES = [
    ('portal.input.jsonep', ['portal/input/jsonep.pyx', 'portal/input/jsonep.c']),
    ('portal.input.rfc5424', ['portal/input/rfc5424.pyx', 'portal/input/rfc5424.c']),
    ('portal.input.usyslog', ['portal/input/usyslog.pyx', 'portal/input/usyslog.c'])
]

cmdclass = {}
ext_modules = []

def ez_install(package):
    easy_install.main(["-U", package])

def fendswith(varray, farray):
    filtered = []
    for value in varray:
        for filter in farray:
            if value.endswith(filter):
                filtered.append(value)
                break
    return filtered

def cythonize():
    if has_cython:
        cmdclass.update({
            'build_ext': build_ext
        })

    for stuple in SOURCES:
        if has_cython:
            build_list = fendswith(stuple[1], ['.pyx', '.pyd'])
            for build_target in build_list:
                compile(build_target)
            ext_modules.append(Extension(
                stuple[0],
                build_list))
        else:
            build_list = fendswith(stuple[1], ['.c'])
            ext_modules.append(Extension(
                stuple[0],
                build_list))

try:
    import pyev
except ImportError:
    ez_install('pyev')

cythonize()

setup(
    name = 'Meniscus Portal',
    version = '0.1.2',
    description = '',
    author = 'John Hopper',
    author_email='',
    tests_require=[
        "mock",
        "nose",
    ],
    install_requires=[
        "simplejson",
    ],
    test_suite = 'nose.collector',
    zip_safe = False,
    include_package_data = True,
    packages = find_packages(exclude=['ez_setup']),
    cmdclass = cmdclass,
    ext_modules = ext_modules
)

