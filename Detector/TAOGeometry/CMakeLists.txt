include (PKG)
PKG(TAOGeometry
    DEPENDS
    	RootIOSvcLib
        ${ROOT_Geom_LIBRARY}
        boost_filesystem boost_system
        SNiPER::SniperKernel
        TAOIDService
)

