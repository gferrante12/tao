#!/bin/bash
# build_juno.sh
#
# Builds the OrsaClassification library for the JUNO offline environment.
#
# Steps:
#   1. Sources the JUNO software environment (J25.6.4 / Jlatest).
#   2. Configures the build with CMake, setting the install prefix to
#      ./InstallArea/junosw.
#   3. Compiles and installs the library.
#
# Dependencies: Requires access to /cvmfs/juno.ihep.ac.cn

echo "Building for JUNO..."
# Source JUNO environment
source /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/Jlatest/setup.sh

# Define paths
# Start from the script's directory (assumed to be package root)
root_dir=$(cd "$(dirname "$0")"; pwd)
prefix=${root_dir}/InstallArea/junosw
build_dir=${root_dir}/build/junosw

# Clean and configure
mkdir -p $build_dir
cmake -S $root_dir -B $build_dir -DCMAKE_INSTALL_PREFIX=$prefix -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-march=native -mtune=native" || exit -1

# Build and Install
# -j10 for parallel compilation
cmake --build $build_dir -- -j10 || exit -1
cmake --install $build_dir || exit -1

echo "JUNO build installed to $prefix"
