#include "Event/CdTrigHeader.h"

ClassImp(Tao::CdTrigHeader);

namespace Tao
{
    CdTrigHeader::CdTrigHeader(){

    }

    CdTrigHeader::~CdTrigHeader(){

    }

    void CdTrigHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::CdTrigEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* CdTrigHeader::event(const std::string& eventname) {
        if(eventname == "Tao::CdTrigEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool CdTrigHeader::hasEvent(){
        return m_event.HasObject();
    }
}
