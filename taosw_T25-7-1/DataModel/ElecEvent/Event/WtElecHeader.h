#ifndef WtElecHeader_h
#define WtElecHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/WtElecEvt.h"
#include <string>

namespace Tao
{
    class WtElecHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;

        public:
            WtElecHeader();
            ~WtElecHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(Tao::WtElecEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(WtElecHeader,1)
    };
}

#endif