#ifndef TvtTrigEvt_h
#define TvtTrigEvt_h

#include "Event/EventObject.h"
#include "Context/TimeStamp.h"

namespace Tao
{

   class TvtTrigEvt : public JM::EventObject
   {
       public:
           TvtTrigEvt();
           TvtTrigEvt(Int_t eventid);
           ~TvtTrigEvt();
   
           //setters
           void setTrigTime(TimeStamp t) {  fTrigTime   = t;    }
           void setNFiredChan(int n)     {  fNFiredChan = n;    }
   
           //getters
           TimeStamp getTrigTime()       {  return fTrigTime;   }
           int       getNFiredChan()     {  return fNFiredChan; }
   
       private:
           TimeStamp fTrigTime;
           int fNFiredChan;
   
           TvtTrigEvt(const TvtTrigEvt& event);
   
       public:
   
           ClassDef(TvtTrigEvt, 2)
   };
}
#endif
