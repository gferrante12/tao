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
   
           //get
           const std::vector<Tao::CdCalibChannel>& GetCalibChannels()  const {  return CalfChannels; }
   
       private:
           std::vector<Tao::CdCalibChannel> CalfChannels;
   
           CdCalibEvt(const CdCalibEvt& event);
   
       public:
   
           ClassDef(CdCalibEvt, 2)
    };
}


#endif