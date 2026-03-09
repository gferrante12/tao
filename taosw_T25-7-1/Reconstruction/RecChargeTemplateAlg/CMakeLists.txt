include (PKG)

PKG(RecChargeTemplateAlg
    DEPENDS
        TAOGeometry
        EvtNavigator
        SimEvent
        ElecEvent
        CalibEvent
        RecEvent
        BufferMemMgr
        ${SNIPER_RootWriter_LIBRARY}
)
