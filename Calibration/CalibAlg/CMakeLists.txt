include (PKG)

PKG(CalibAlg
    MODULE
    DEPENDS
        EvtNavigator
	CalibSvcLib
        SimEvent
        ElecEvent
        CalibEvent
        BufferMemMgr
        CondDB CondObj 
        ${SNIPER_RootWriter_LIBRARY}
)
