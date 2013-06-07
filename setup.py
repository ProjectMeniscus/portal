# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
    from setuptools.command import easy_install
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
    from setuptools.command import easy_install

try:
    from Cython.Compiler.Main import compile
    from Cython.Distutils import build_ext
    has_cython = True
except ImportError:
    has_cython = False

import sys
from os import path
from distutils.core import setup
from distutils.extension import Extension

IS_INSTALL = 'install' in sys.argv

C_LIBRARIES = list()
cmdclass = dict()
ext_modules = list()


def read(relative):
    contents = open(relative, 'r').read()
    return [l for l in contents.split('\n') if l != '']


def ez_install(package):
    easy_install.main(["-U", package])


def module_files(module_name, *extensions):
    found = list()
    filename_base = module_name.replace('.', '/')
    for extension in extensions:
        filename = '{}.{}'.format(filename_base, extension)
        if path.exists(filename):
            found.append(filename)
    return found


def cythonize():
    if has_cython:
        cmdclass.update({
            'build_ext': build_ext
        })

    for module in read('./tools/cython-modules'):
        if has_cython:
            build_list = module_files(module, 'pyx', 'pyd')
            for build_target in build_list:
                compile(build_target)
        else:
            build_list = module_files(module, 'c')

        ext_modules.append(
            Extension(
                module,
                build_list,
                libraries=C_LIBRARIES))

if IS_INSTALL:
    try:
        import pyev
    except ImportError:
        ez_install('pyev')

cythonize()

setup(
    name='meniscus_portal',
    version='0.1.5',
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
    packages=find_packages(exclude=['ez_setup']),
    cmdclass=cmdclass,
    ext_modules=ext_modules)
