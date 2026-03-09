#include "Event/CdCalibEvt.h"
#include <cassert>

ClassImp(Tao::CdCalibEvt)

namespace Tao
{
    CdCalibEvt::CdCalibEvt() {
	fOnlineX   = 0;
        fOnlineY   = 0;
        fOnlineZ   = 0;
        fTotalPE    = 0;
        fOnlineEvtType = false;
    
    }

    CdCalibEvt::CdCalibEvt(Int_t eventid){
	fOnlineX   = 0;
        fOnlineY   = 0;
        fOnlineZ   = 0;
        fTotalPE   = 0;
        fOnlineEvtType = false;
    }
        

    CdCalibEvt::~CdCalibEvt(){
    
    }

}
