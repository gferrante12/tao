#ifndef TvtCalibHeader_h
#define TvtCalibHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/TvtCalibEvt.h"
#include <string>
namespace Tao
{
    class TvtCalibHeader: public JM::HeaderObject
    {
        private:
            JM::SmartRef m_event;
        public:
            TvtCalibHeader();
            ~TvtCalibHeader();

            Long64_t getEventEntry() const{
                return m_event.entry();
            }

            JM::EventObject* event(){
                return m_event.GetObject();
            }
            void setEvent(Tao::TvtCalibEvt* value){
                m_event = value;
            }
            void setEventEntry(const std::string& eventname,Long64_t& value);
            EventObject* event(const std::string& eventname);
            bool hasEvent();

        public:
            ClassDef(TvtCalibHeader,1)
    };
}

#endif
