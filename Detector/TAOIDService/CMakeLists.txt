include (PKG)
PKG(TAOIDService
    DEPENDS
    	RootIOSvcLib
        boost_filesystem boost_system
        SNiPER::SniperKernel
        Boost::system
        Boost::python
        Python::Python
        ROOT::Core
)

