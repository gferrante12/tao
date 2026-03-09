#ifndef WtTrigEvt_h
#define WtTrigEvt_h

#include "Event/EventObject.h"
#include "Context/TimeStamp.h"

namespace Tao
{

   class WtTrigEvt : public JM::EventObject
   {
       public:
           WtTrigEvt();
           WtTrigEvt(Int_t eventid);
           ~WtTrigEvt();
   
           //setters
           void setTrigTime(TimeStamp t) {  fTrigTime   = t;    }
           void setNFiredChan(int n)     {  fNFiredChan = n;    }
   
           //getters
           TimeStamp getTrigTime()       {  return fTrigTime;   }
           int       getNFiredChan()     {  return fNFiredChan; }
   
       private:
           TimeStamp fTrigTime;
           int fNFiredChan;
   
           WtTrigEvt(const WtTrigEvt& event);
   
       public:
   
           ClassDef(WtTrigEvt, 2)
   };
}
#endif