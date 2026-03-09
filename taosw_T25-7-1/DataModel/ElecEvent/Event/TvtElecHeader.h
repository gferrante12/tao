#ifndef TvtElecHeader_h
#define TvtElecHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/TvtElecEvt.h"
#include <string>

namespace Tao
{
    class TvtElecHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;

        public:
            TvtElecHeader();
            ~TvtElecHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(Tao::TvtElecEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(TvtElecHeader,1)
    };
}

#endif
