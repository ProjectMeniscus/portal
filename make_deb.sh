#!/bin/sh

PROJECT_NAME="meniscus-portal"
PROJECT_VERSION="$(cat VERSION)"

python build.py meniscus-portal
fpm -d python -d libzmq1 -d libzmq-dev -v "${PROJECT_VERSION}" -n "${PROJECT_NAME}" -t deb --after-install ./pkg/post_install.deb.sh --after-remove ./pkg/post_remove.deb.sh -s tar "./${PROJECT_NAME}_${PROJECT_VERSION}.tar.gz"
