#!/bin/bash
# build_tao.sh
#
# Builds the OrsaClassification library for the TAO environment.
#
# Steps:
#   1. Sources the TAO software environment.
#   2. Configures the build with CMake, setting the install prefix to
#      ./InstallArea/taosw.
#   3. Compiles and installs the library.
#
# Note: defines TAO_ENV implicitly via the environment variables sourced.

echo "Building for TAO..."
# Source TAO environment
source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/Jlatest/setup-tao.sh

# Define paths
root_dir=$(cd "$(dirname "$0")"; pwd)
prefix=${root_dir}/InstallArea/taosw
build_dir=${root_dir}/build/taosw

# Clean and configure
mkdir -p $build_dir
cmake -S $root_dir -B $build_dir -DCMAKE_INSTALL_PREFIX=$prefix -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-march=native -mtune=native" || exit -1

# Build and Install
cmake --build $build_dir -- -j10 || exit -1
cmake --install $build_dir || exit -1

echo "TAO build installed to $prefix"
