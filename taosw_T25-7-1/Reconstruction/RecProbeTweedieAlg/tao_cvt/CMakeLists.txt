include (PKG)

find_package(HDF5 COMPONENTS CXX HL)
find_package(Boost COMPONENTS program_options container)

PKG(TaoDataConverter
    APPONLY
        tao_cvt
    FILES
        main.cpp
        convert.cpp
        sim_event.cpp
        elec_event.cpp
    DEPENDS
        Context
        EDMUtil
        SimEvent
        ElecEvent
        ${ROOT_LIBRARIES}
        ${HDF5_LIBRARIES}
        ${HDF5_HL_LIBRARIES}
        Boost::program_options
        Boost::container
)
