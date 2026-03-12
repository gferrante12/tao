#!/bin/bash
# build.sh
#
# Master build script for OrsaClassification.
# Orchestrates the build of both the JUNO (offline) and TAO (online/offline)
# versions of the library by calling the respective environment-specific scripts.
#
# Usage: ./build.sh
# Returns: 0 on success, non-zero if either build fails.

# Make scripts executable if they aren't
chmod +x build_juno.sh build_tao.sh

# 1. Build JUNO version
./build_juno.sh || exit -1
echo "------------------------------------------------"

# 2. Build TAO version
./build_tao.sh || exit -1

echo "All builds complete."
