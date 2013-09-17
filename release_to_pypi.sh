#!/bin/sh

#################################
# Building and Releasing Portal #
#################################

# SCRIPT BEGIN

# Are we doing a dry run or is this a real release?
UPLOAD_TO_PYPI=0

if [ ${#} -gt 0 ]; then
    while [ "${1}" != "" ]; do
       currentArgument="${1}";
       shift;

       case "${currentArgument}" in
          --upload)
             UPLOAD_TO_PYPI=1
          ;;

          *)
             echo "${0} <--upload>"
             exit 1;
          ;;
       esac
    done
fi

if [ ${UPLOAD_TO_PYPI} -eq 0 ]; then
    echo 'Doing a dry run of the release process...'
fi

# Clean the dist and directories
rm -rf dist/*
rm -rf build/*

# Run the clean build
python setup.py clean

# Generate the Cython C code
python setup.py build

# Build the C code in place
python setup.py build_ext --inplace

# Run the tests
nosetests

if [ ${?} == 0 ] && [ ${UPLOAD_TO_PYPI} -ne 0 ]; then
    # Build the source distribution and upload the file to Pypi
    python setup.py sdist --formats=gztar upload
fi
