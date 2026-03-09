#include "Event/TvtCalibHeader.h"

ClassImp(Tao::TvtCalibHeader);

namespace Tao
{
     TvtCalibHeader::TvtCalibHeader(){

    }

    TvtCalibHeader::~TvtCalibHeader(){

    }

    void TvtCalibHeader::setEventEntry(const std::string& eventname,Long64_t& value){
        if(eventname == "Tao::TvtCalibEvt"){
            m_event.setEntry(value);
        }
    }

    JM::EventObject* TvtCalibHeader::event(const std::string& eventname) {
        if(eventname == "Tao::TvtCalibEvt"){
            return m_event.GetObject();
        }
        return 0;
    }

    bool TvtCalibHeader::hasEvent(){
        return m_event.HasObject();
    }
}
