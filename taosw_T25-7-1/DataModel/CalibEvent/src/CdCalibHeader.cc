#include "Event/CdCalibHeader.h"

ClassImp(Tao::CdCalibHeader);

namespace Tao
{
     CdCalibHeader::CdCalibHeader(){

    }

    CdCalibHeader::~CdCalibHeader(){

    }

    void CdCalibHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::CdCalibEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* CdCalibHeader::event(const std::string& eventname) {
        if(eventname == "Tao::CdCalibEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool CdCalibHeader::hasEvent(){
        return m_event.HasObject();
    }
}