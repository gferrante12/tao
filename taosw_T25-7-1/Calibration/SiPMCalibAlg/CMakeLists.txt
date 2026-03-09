include (PKG)

PKG(SiPMCalibAlg
    DEPENDS
        EvtNavigator
        SimEvent
        ElecEvent
        BufferMemMgr
        ${SNIPER_RootWriter_LIBRARY}
        RootIOSvcLib
	    Context
	    InputReviser
        ${ROOT_LIBRARIES}
        RooFit
        RooFitCore
        Minuit2
        Spectrum
)