cmake_minimum_required(VERSION 3.15)
project(OrsaClassification)

# --- JUNO / SNiPER Integration ---
# Find the SNiPER and JUNO offline software packages.

# Suppress CMP0167 warning (CMake 3.30+ removed FindBoost)
if(POLICY CMP0167)
    cmake_policy(SET CMP0167 OLD)
endif()

# Suppress commonsw warning by providing a dummy path if not found
if(NOT commonsw_DIR)
    set(commonsw_DIR "NOTFOUND" CACHE PATH "Path to commonsw" FORCE)
endif()

find_package(junosw)

set(CMAKE_CXX_STANDARD 17)

# Detect TAO environment and define macro for conditional compilation.
if(DEFINED ENV{TAOTOP})
    add_definitions(-DTAO_ENV)
    message(STATUS "TAO Environment detected, defining TAO_ENV")
endif()

# --- Include Directories ---
# Add local include/ and system includes from JUNO/TAO
include_directories(include)
include_directories(${JUNOSW_INCLUDE_DIRS})
include_directories($ENV{JUNOTOP}/include) # Fallback

# Explicitly add InstallArea includes for TAO/JUNO if env vars are present
if(DEFINED ENV{TAOTOP})
    include_directories($ENV{TAOTOP}/taosw/InstallArea/include)
endif()
if(DEFINED ENV{JUNOTOP})
    include_directories($ENV{JUNOTOP}/junosw/InstallArea/include)
endif()

message(STATUS "JUNOSW_INCLUDE_DIRS: ${JUNOSW_INCLUDE_DIRS}")
message(STATUS "JUNOTOP: $ENV{JUNOTOP}")

# --- Build Target ---
# Collect all source files
file(GLOB sources "src/*.cc")

# Define the shared library. This library is dynamically loaded by SNiPER
# via the DLL loading mechanism (see DECLARE_ALGORITHM macro).
add_library(OrsaClassification SHARED ${sources})

# Link Dependencies
# Link against core JUNO/SNiPER libraries.
target_link_libraries(OrsaClassification 
    ${JUNOSW_LIBRARIES} 
    ${ROOT_LIBRARIES}
    junosw::EvtNavigator
    junosw::RecEvent
    junosw::CalibEvent
    junosw::ElecEvent
    junosw::GeometryLib
    junosw::JunoTimer
    junosw::OecEvent
    SNiPER::RootWriterLib
)

# --- Installation ---
# Install library, headers, python scripts, and shell scripts.
install(TARGETS OrsaClassification DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY share/ DESTINATION share)

# Generate and install the setup script (setup.sh)
# This script is configured with the install paths to set LD_LIBRARY_PATH/PYTHONPATH.
configure_file(setup.sh.in ${CMAKE_BINARY_DIR}/setup.sh @ONLY)
install(FILES ${CMAKE_BINARY_DIR}/setup.sh DESTINATION .)
