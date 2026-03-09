#include "Event/TvtTrigHeader.h"

ClassImp(Tao::TvtTrigHeader);

namespace Tao
{
    TvtTrigHeader::TvtTrigHeader(){

    }

    TvtTrigHeader::~TvtTrigHeader(){

    }

    void TvtTrigHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::TvtTrigEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* TvtTrigHeader::event(const std::string& eventname) {
        if(eventname == "Tao::TvtTrigEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool TvtTrigHeader::hasEvent(){
        return m_event.HasObject();
    }
}
