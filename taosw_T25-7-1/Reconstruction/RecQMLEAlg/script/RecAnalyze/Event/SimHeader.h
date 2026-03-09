#ifndef SimHeader_h
#define SimHeader_h

#include "Event/HeaderObject.h"
#include "EDMUtil/SmartRef.h"
#include "Event/SimEvt.h"
#include <string>

namespace Tao
{
    class SimHeader: public JM::HeaderObject {
        private:
            JM::SmartRef m_event; // ||
            /* 
             * Describe what's type of the current event.
             * + IBD
             * + U
             * + Th
             * + ...
             * or 
             * + Mixing
             */
            std::string m_evt_type; 
            double m_CdSipm_timewindow;
            int m_CdSipm_totalhits;
        public:
            SimHeader();
            ~SimHeader();

            JM::EventObject* event() {
                return m_event.GetObject();
            }
            void setEvent(SimEvt* value) {
                m_event = value;
            }
            void setEventEntry(const std::string& eventName, Long64_t& value);
            JM::EventObject* event(const std::string& eventName);
            bool hasEvent();

        public:

            const std::string& getEventType() {
                return m_evt_type;
            }

            void setEventType(const std::string& evt_type) {
                m_evt_type = evt_type;
            }

            double getCDLPMTtimeWindow()  {
                return m_CdSipm_timewindow;
            }

            void setCDLPMTtimeWindow(double timewindow)
            {
                m_CdSipm_timewindow = timewindow;
            }

            int getCDLPMTtotalHits()  {
                return m_CdSipm_totalhits;
            }

            void setCDLPMTtotalHits( int totalhits)
            {
                m_CdSipm_totalhits = totalhits;
            }
        public:
            ClassDef(SimHeader,4)

    };
}

#endif
