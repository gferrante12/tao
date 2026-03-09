#ifndef CdCalibEvt_h
#define CdCalibEvt_h

#include "Event/EventObject.h"
#include "Event/CdCalibChannel.h"
#include <vector>
namespace Tao
{
    class CdCalibEvt : public JM::EventObject
    {
        public:
           CdCalibEvt();
           CdCalibEvt(Int_t eventid);
           ~CdCalibEvt();

           //set
           void CalibChannels(const std::vector<Tao::CdCalibChannel>& channels) {  CalfChannels = channels; }
           void AddCalibChannel(const Tao::CdCalibChannel& v)  {   CalfChannels.push_back(v); }
           void SetTotalPE(double v) {  fTotalPE = v; }
   
	   void setOnlineX(double v) { fOnlineX = v; }
           void setOnlineY(double v) { fOnlineY = v; }
           void setOnlineZ(double v) { fOnlineZ = v; }
           void setOnlineEvtType(bool v) { fOnlineEvtType = v; }
           
	   //get
           double getOnlineX() { return fOnlineX; }
           double getOnlineY() { return fOnlineY; }
           double getOnlineZ() { return fOnlineZ; }
           bool   getOnlineEvtType() { return fOnlineEvtType; }

           const std::vector<Tao::CdCalibChannel>& GetCalibChannels()  const {  return CalfChannels; }
           double GetTotalPE() { return fTotalPE;}

       private:
           std::vector<Tao::CdCalibChannel> CalfChannels;

           double fTotalPE;
	   double fOnlineX;
	   double fOnlineY;
	   double fOnlineZ;
	   bool   fOnlineEvtType;

           CdCalibEvt(const CdCalibEvt& event);
   
       public:
   
           ClassDef(CdCalibEvt, 2)
    };
}


#endif
