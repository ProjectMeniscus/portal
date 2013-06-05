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

from os import path
from distutils.core import setup
from distutils.extension import Extension


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
            break
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
            print('Build list is: {}'.format(build_list))

        ext_modules.append(
            Extension(
                module,
                build_list,
                libraries=C_LIBRARIES))


try:
    import pyev
except ImportError:
    ez_install('pyev')

cythonize()

setup(
    name='Meniscus Portal',
    version='0.1.5',
    description='low level parsing bindings for meniscus',
    author='John Hopper',
    author_email='john.hopper@jpserver.net',
    tests_require=read('./tools/test-requires'),
    install_requires=read('./tools/pip-requires'),
    test_suite='nose.collector',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup']),
    cmdclass=cmdclass,
    ext_modules=ext_modules
)

