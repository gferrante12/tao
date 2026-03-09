#include "Event/CdElecEvt.h"
#include <cassert>

ClassImp(Tao::CdElecEvt)

namespace Tao
{
    CdElecEvt::CdElecEvt(){
        fOnlineX = 0;
        fOnlineY = 0;
        fOnlineZ = 0;
        fOnlinePE = 0;
        fOnlineEvtType = false;
    }

    CdElecEvt::CdElecEvt(Int_t eventid){
        fOnlineX = 0;
        fOnlineY = 0;
        fOnlineZ = 0;
        fOnlinePE = 0;
        fOnlineEvtType = false; 
    }
        

    CdElecEvt::~CdElecEvt(){
    
    }

}
