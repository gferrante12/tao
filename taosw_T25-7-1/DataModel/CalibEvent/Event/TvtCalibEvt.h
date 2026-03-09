#ifndef TvtCalibEvt_h
#define TvtCalibEvt_h

#include "Event/EventObject.h"
#include "Event/TvtCalibChannel.h"
#include <vector>
namespace Tao
{
    class TvtCalibEvt : public JM::EventObject
    {
        public:
           TvtCalibEvt();
           TvtCalibEvt(Int_t eventid);
           ~TvtCalibEvt();

           //set
           void CalibChannels(const std::vector<Tao::TvtCalibChannel>& channels) {  CalfChannels = channels; }
           void AddCalibChannel(const Tao::TvtCalibChannel& v)  {   CalfChannels.push_back(v); }
           void SetTotalPE(double v) {  totalPE = v; }
   
           //get
           const std::vector<Tao::TvtCalibChannel>& GetCalibChannels()  const {  return CalfChannels; }
           double GetTotalPE() { return totalPE;}
       private:
           std::vector<Tao::TvtCalibChannel> CalfChannels;
           double totalPE;
           TvtCalibEvt(const TvtCalibEvt& event);
   
       public:
   
           ClassDef(TvtCalibEvt, 2)
    };
}


#endif
