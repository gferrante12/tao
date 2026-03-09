#ifndef CdCalibHeader_h
#define CdCalibHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/CdCalibEvt.h"
#include <string>
namespace Tao
{
    class CdCalibHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;
        public:
            CdCalibHeader();
            ~CdCalibHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(Tao::CdCalibEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(CdCalibHeader,1)
    };
}

#endif