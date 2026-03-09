include (EDM)

EDM(CalibEvent
    NOXOD
    FILES
      CdCalibChannel
      CdCalibEvt
      CdCalibHeader
      TvtCalibChannel
      TvtCalibEvt
      TvtCalibHeader
    DEPENDS
      ${ROOT_Physics_LIBRARY}
      TAOEDMUtil
)
