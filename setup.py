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

try:
    from Cython.Compiler.Main import compile
    from Cython.Distutils import build_ext
    has_cython = True
except ImportError:
    has_cython = False

COMPILER_ARGS = ['-O2']
SOURCES = [
    ('portal.input.jsonep', ['portal/input/jsonep.pyx', 'portal/input/jsonep.c']),
    ('portal.input.rfc5424', ['portal/input/rfc5424.pyx', 'portal/input/rfc5424.c'])
]

cmdclass = {}
ext_modules = []

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
                build_list,
                extra_compile_args=COMPILER_ARGS))
        else:
            build_list = fendswith(stuple[1], ['.c'])
            ext_modules.append(Extension(
                stuple[0],
                build_list))

cythonize()
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
    cmdclass = cmdclass,
    ext_modules = ext_modules
)

