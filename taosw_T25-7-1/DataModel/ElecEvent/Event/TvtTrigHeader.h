#ifndef TvtTrigHeader_h
#define TvtTrigHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/TvtTrigEvt.h"
#include <string>

namespace Tao
{
    class TvtTrigHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;

        public:
            TvtTrigHeader();
            ~TvtTrigHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(TvtTrigEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(TvtTrigHeader,1)
    };
}

#endif
