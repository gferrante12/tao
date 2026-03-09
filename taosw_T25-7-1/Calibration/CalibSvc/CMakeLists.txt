PKG(CalibSvc
   MODULE
   SHARED
       src/ICalibSvc.cc
   DEPENDS
	CondDB
       	CondObj
       	TaoPathHelper
        ${SNIPER_RootWriter_LIBRARY}
)



