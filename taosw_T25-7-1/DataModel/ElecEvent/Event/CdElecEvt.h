#ifndef CdElecEvt_h
#define CdElecEvt_h

#include "Event/EventObject.h"
#include "Event/CdElecChannel.h"
#include <vector>

namespace Tao
{

    class CdElecEvt : public JM::EventObject
    {
        public:
            CdElecEvt();
            CdElecEvt(Int_t eventid);
            ~CdElecEvt();
            
            //set
            void ElecChannels(const std::vector<Tao::CdElecChannel>& channels) {  fChannels = channels; }
            void AddElecChannel(const Tao::CdElecChannel& v)  {   fChannels.push_back(v); }
            void setOnlineX(double v) {fOnlineX = v; }
            void setOnlineY(double v) {fOnlineY = v; }
            void setOnlineZ(double v) {fOnlineZ = v; }
            void setOnlinePE(int v) { fOnlinePE = v; }
            void setOnlineEvtType(bool v) { fOnlineEvtType = v; }
            //get
            const std::vector<Tao::CdElecChannel>& GetElecChannels()  const {  return fChannels; }
            double getOnlineX() {return fOnlineX; }
            double getOnlineY() {return fOnlineY; }
            double getOnlineZ() {return fOnlineZ; }
            int getOnlinePE() { return fOnlinePE; }
            bool getOnlineEvtType() { return fOnlineEvtType; }
        private:
            std::vector<Tao::CdElecChannel> fChannels;
            double fOnlineX;
            double fOnlineY;
            double fOnlineZ;
            int fOnlinePE;
            bool fOnlineEvtType;
            CdElecEvt(const CdElecEvt& event);
    
        public:
    
            ClassDef(CdElecEvt, 2)
    };
}
#endif
