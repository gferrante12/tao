#ifndef SimPmtHit_h
#define SimPmtHit_h

#include "TObject.h"
#include <vector>
#include <iostream>

namespace Tao
{
    class SimPmtHit: public TObject {

 	private:
   	    int pmtid;
            int npe;
            double hittime;
            double timewindow;
            int trackid; // ref to Track ID. but if hits are merged, unknown.
            double localX;
            double localY;
	    double localZ;
        public:
            SimPmtHit() {
                pmtid = -1;
                npe = -1;
                hittime = -1;
                timewindow = 0;
                trackid = -1;
                localX = -1;
                localY = -1;
	        localZ = -1;
            }

            virtual ~SimPmtHit() {}

        public:
            int getPMTID() {return pmtid;}
            int getNPE() {return npe;}
            double getHitTime() {return hittime;}
            double getTimeWindow() {return timewindow;}
            int getTrackID() { return trackid; }
            double getLocalX(){return localX;}
            double getLocalY(){ return localY;}
	    double getLocalZ(){ return localZ;}

            void setPMTID(int val) {pmtid=val;}
            void setNPE(int val) {npe=val;}
            void setHitTime(double val) {hittime = val;}
            void setTimeWindow(double val) {timewindow = val;}
            void setTrackID(int val) {trackid = val;}
            void setLocalX(double val) {localX = val;}
            void setLocalY(double val) {localY = val;}   
	    void setLocalZ(double val) {localZ = val;}		 
         /*private:
            Int_t m_pmt_id;
            Float_t fPMTHitX;
            Float_t fPMTHitY;
            Float_t fPMTHitZ;
            Double_t fPMTHitT;
            Float_t fPMTHitE;
            Float_t fPMTHitPX;
            Float_t fPMTHitPY;
            Float_t fPMTHitPZ;

	public:
                int getPMTHitID()	{ return m_pmt_id;}
		float getPMTHitX()	{ return fPMTHitX;}
		float getPMTHitY()      { return fPMTHitY;}
		float getPMTHitZ()      { return fPMTHitZ;}
		float getPMTHitE()      { return fPMTHitE;}
		float getPMTHitPX()     { return fPMTHitPX;}
		float getPMTHitPY()     { return fPMTHitPY;}
		float getPMTHitPZ()     { return fPMTHitPZ;}
		double getPMTHitT()	{ return fPMTHitT;}

		void setPMTHitID	(int val)       { m_pmt_id = val;}
		void setPMTHitX		(float val)	{ fPMTHitX = val;}
		void setPMTHitY		(float val)     { fPMTHitY = val;}
		void setPMTHitZ		(float val)     { fPMTHitZ = val;}
		void setPMTHitE		(float val)     { fPMTHitE = val;}
		void setPMTHitPX	(float val)	{ fPMTHitPX = val;}
		void setPMTHitPY	(float val)	{ fPMTHitPY = val;}
		void setPMTHitPZ	(float val)	{ fPMTHitPZ = val;}
		void setPMTHitT		(double val)	{ fPMTHitT = val;}
*/




            ClassDef(SimPmtHit, 3)
    };

}

#endif














