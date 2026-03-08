include (PKG)

PKG(RecChargeCenterAlg
    DEPENDS
        TAOGeometry
        EvtNavigator
        SimEvent
        ElecEvent
        CalibEvent
        RecEvent
        BufferMemMgr
        CalibSvcLib
        ${SNIPER_RootWriter_LIBRARY}
)
