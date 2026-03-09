#ifndef CdTrigEvt_h
#define CdTrigEvt_h

#include "Event/EventObject.h"
#include "Context/TimeStamp.h"

namespace Tao
{

   class CdTrigEvt : public JM::EventObject
   {
       public:
           CdTrigEvt();
           CdTrigEvt(Int_t eventid);
           ~CdTrigEvt();
   
           //setters
           void setTrigTime(TimeStamp t) {  fTrigTime   = t;    }
           void setNFiredChan(int n)     {  fNFiredChan = n;    }
   
           //getters
           TimeStamp getTrigTime()       {  return fTrigTime;   }
           int       getNFiredChan()     {  return fNFiredChan; }
   
       private:
           TimeStamp fTrigTime;
           int fNFiredChan;
   
           CdTrigEvt(const CdTrigEvt& event);
   
       public:
   
           ClassDef(CdTrigEvt, 2)
   };
}
#endif
