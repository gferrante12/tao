#ifndef CdTrigHeader_h
#define CdTrigHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/CdTrigEvt.h"
#include <string>

namespace Tao
{
    class CdTrigHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;

        public:
            CdTrigHeader();
            ~CdTrigHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(CdTrigEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(CdTrigHeader,1)
    };
}

#endif
