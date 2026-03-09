#ifndef TvtElecEvt_h
#define TvtElecEvt_h

#include "Event/EventObject.h"
#include "Event/TvtElecChannel.h"
#include <vector>

namespace Tao
{

   class TvtElecEvt : public JM::EventObject
   {
       public:
           TvtElecEvt();
           TvtElecEvt(Int_t eventid);
           ~TvtElecEvt();
   
           //set
           void ElecChannels(const std::vector<Tao::TvtElecChannel>& channels) {  fChannels = channels; }
           void AddElecChannel(const Tao::TvtElecChannel& v)  {   fChannels.push_back(v); }
   
           //get
           const std::vector<Tao::TvtElecChannel>& GetElecChannels()  const {  return fChannels; }
   
       private:
           std::vector<Tao::TvtElecChannel> fChannels;
   
           TvtElecEvt(const TvtElecEvt& event);
   
       public:
   
           ClassDef(TvtElecEvt, 2)
   };
}
#endif
