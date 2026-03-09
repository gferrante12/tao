#ifndef CdElecHeader_h
#define CdElecHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/CdElecEvt.h"
#include <string>

namespace Tao
{
    class CdElecHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;

        public:
            CdElecHeader();
            ~CdElecHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(Tao::CdElecEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(CdElecHeader,1)
    };
}

#endif
