#include "Event/TvtElecHeader.h"

ClassImp(Tao::TvtElecHeader);

namespace Tao
{
    TvtElecHeader::TvtElecHeader(){

    }

    TvtElecHeader::~TvtElecHeader(){

    }

    void TvtElecHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::TvtElecEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* TvtElecHeader::event(const std::string& eventname) {
        if(eventname == "Tao::TvtElecEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool TvtElecHeader::hasEvent(){
        return m_event.HasObject();
    }
}
