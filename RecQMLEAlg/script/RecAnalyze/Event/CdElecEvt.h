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
   
           //get
           const std::vector<Tao::CdElecChannel>& GetElecChannels()  const {  return fChannels; }
   
       private:
           std::vector<Tao::CdElecChannel> fChannels;
   
           CdElecEvt(const CdElecEvt& event);
   
       public:
   
           ClassDef(CdElecEvt, 2)
   };
}
#endif
