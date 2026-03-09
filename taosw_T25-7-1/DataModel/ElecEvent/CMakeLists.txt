include (EDM)

EDM(ElecEvent
    NOXOD
    FILES
      CdElecChannel
      CdElecEvt
      CdElecHeader
      CdTrigEvt
      CdTrigHeader
      TvtElecChannel
      TvtElecEvt
      TvtElecHeader
      TvtTrigEvt
      TvtTrigHeader
      WtElecChannel
      WtElecEvt
      WtElecHeader
      WtTrigEvt
      WtTrigHeader
    DEPENDS
      ${ROOT_Physics_LIBRARY}
      Context
      TAOEDMUtil
)
