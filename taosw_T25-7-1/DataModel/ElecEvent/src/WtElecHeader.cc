#include "Event/WtElecHeader.h"

ClassImp(Tao::WtElecHeader);

namespace Tao
{
    WtElecHeader::WtElecHeader(){

    }

    WtElecHeader::~WtElecHeader(){

    }

    void WtElecHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::WtElecEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* WtElecHeader::event(const std::string& eventname) {
        if(eventname == "Tao::WtElecEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool WtElecHeader::hasEvent(){
        return m_event.HasObject();
    }
}