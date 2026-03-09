#ifndef WtTrigHeader_h
#define WtTrigHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/WtTrigEvt.h"
#include <string>

namespace Tao
{
    class WtTrigHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;

        public:
            WtTrigHeader();
            ~WtTrigHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(WtTrigEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(WtTrigHeader,1)
    };
}

#endif