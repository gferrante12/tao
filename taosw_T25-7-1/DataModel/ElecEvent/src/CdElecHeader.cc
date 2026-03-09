#include "Event/CdElecHeader.h"

ClassImp(Tao::CdElecHeader);

namespace Tao
{
    CdElecHeader::CdElecHeader(){

    }

    CdElecHeader::~CdElecHeader(){

    }

    void CdElecHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::CdElecEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* CdElecHeader::event(const std::string& eventname) {
        if(eventname == "Tao::CdElecEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool CdElecHeader::hasEvent(){
        return m_event.HasObject();
    }
}
