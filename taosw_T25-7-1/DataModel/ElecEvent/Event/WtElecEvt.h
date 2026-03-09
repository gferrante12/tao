#ifndef WtElecEvt_h
#define WtElecEvt_h

#include "Event/EventObject.h"
#include "Event/WtElecChannel.h"
#include <vector>

namespace Tao
{

   class WtElecEvt : public JM::EventObject
   {
       public:
           WtElecEvt();
           WtElecEvt(Int_t eventid);
           ~WtElecEvt();
   
           //set
           void ElecChannels(const std::vector<Tao::WtElecChannel>& channels) {  fChannels = channels; }
           void AddElecChannel(const Tao::WtElecChannel& v)  {   fChannels.push_back(v); }
   
           //get
           const std::vector<Tao::WtElecChannel>& GetElecChannels()  const {  return fChannels; }
   
       private:
           std::vector<Tao::WtElecChannel> fChannels;
   
           WtElecEvt(const WtElecEvt& event);
   
       public:
   
           ClassDef(WtElecEvt, 2)
   };
}
#endif