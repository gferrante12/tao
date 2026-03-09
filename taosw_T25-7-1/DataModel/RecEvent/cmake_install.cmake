# Install script for directory: /cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/InstallArea")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Debug")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "0")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/contrib/binutils/2.35.2/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/Event" TYPE FILE FILES "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/CdVertexRecEvt.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/Event" TYPE FILE FILES "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/CdVertexRecHeader.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/Event" TYPE FILE FILES "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/TvtVertexRecEvt.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/Event" TYPE FILE FILES "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/RecEvent/Event/TvtVertexRecHeader.h")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libRecEvent.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libRecEvent.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libRecEvent.so"
         RPATH "")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE SHARED_LIBRARY FILES "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/lib/libRecEvent.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libRecEvent.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libRecEvent.so")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/contrib/binutils/2.35.2/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib64/libRecEvent.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/lib/libRecEvent.rootmap")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "shlib" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib64" TYPE FILE FILES
    "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent/src/CdVertexRecEvtDict_rdict.pcm"
    "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent/src/CdVertexRecHeaderDict_rdict.pcm"
    "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent/src/TvtVertexRecEvtDict_rdict.pcm"
    "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/RecEvent/src/TvtVertexRecHeaderDict_rdict.pcm"
    )
endif()

