include (PKG)

PKG(CalibAna
    DEPENDS
        EvtNavigator
        BufferMemMgr
        CalibEvent
        ${SNIPER_RootWriter_LIBRARY}
)

