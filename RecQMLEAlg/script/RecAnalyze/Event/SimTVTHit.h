#ifndef SimTVTHit_h
#define SimTVTHit_h

#include "TObject.h"
#include <vector>
#include <iostream>

namespace Tao
{
    class SimTVTHit: public TObject {
        private:
            int PSid;
            int npe;
	    double edep;
            double hittime;
            double timewindow;
            int trackid; // ref to Track ID. but if hits are merged, unknown.
            
		Float_t localX;
		Float_t localY;
		Float_t localZ;
/*		Float_t fSiPMHitX;
		Float_t fSiPMHitY;
		Float_t fSiPMHitZ;
		Float_t fSiPMHitE;
		Float_t fSiPMHitPX;
		Float_t fSiPMHitPY;
		Float_t fSiPMHitPZ;
		Int_t fSiPMHitProcessCreator;
*/


// 	    double localtheta;
//            double localphi;
        public:
            SimTVTHit() {
                PSid = -1;
                npe = 1;
                edep = 1;
		hittime = -1;
                timewindow = 1;
                trackid = -1;
//                localtheta = -1;
//                localphi = -1;
            
		localX = 0;
                localY = 0;
                localZ = 0;
/*                fSiPMHitX = 0;
                fSiPMHitY = 0;
                fSiPMHitZ = 0;
                fSiPMHitE = 0;
                fSiPMHitPX = 0;
                fSiPMHitPY = 0;
                fSiPMHitPZ = 0;
*/


	}

            virtual ~SimTVTHit() {}

        public:
            int getPSID() {return PSid;}
            int getNPE() {return npe;}
            double getHitTime() {return hittime;}
	    double getedep() {return edep;}
            double getTimeWindow() {return timewindow;}
            int getTrackID() { return trackid; }
//            double getLocalTheta(){return localtheta;}
//            double getLocalPhi(){ return localphi;}
	    
		float getPSHitLocalX(){return localX;}
		float getPSHitLocalY(){return localY;}
		float getPSHitLocalZ(){return localZ;}
/*		float getSiPMHitX(){return fSiPMHitX;}
		float getSiPMHitY(){return fSiPMHitY;}
		float getSiPMHitZ(){return fSiPMHitZ;}
		float getSiPMHitE(){return fSiPMHitE;}			
		float getSiPMHitPX(){return fSiPMHitPX;}
		float getSiPMHitPY(){return fSiPMHitPY;}
		float getSiPMHitPZ(){return fSiPMHitPZ;}
		int getSiPMHitProcessCreator(){return fSiPMHitProcessCreator;}
*/


            void setPSID(int val) {PSid=val;}
            void setNPE(int val) {npe=val;}
            void setHitTime(double val) {hittime = val;}
            void setTimeWindow(double val) {timewindow = val;}
	    void setedep(double val) {edep = val;}
            void setTrackID(int val) {trackid = val;}
//            void setLocalTheta(double val) {localtheta = val;}
//            void setLocalPhi(double val) {localphi = val;}

		void setPSHitLocalX(float val) {localX = val;}
		void setPSHitLocalY(float val) {localY = val;}
		void setPSHitLocalZ(float val) {localZ = val;}
/*		void setSiPMHitX(float val) {fSiPMHitX = val;}
		void setSiPMHitY(float val) {fSiPMHitY = val;}
		void setSiPMHitZ(float val) {fSiPMHitZ = val;}
		void setSiPMHitPX(float val) {fSiPMHitPX = val;}
		void setSiPMHitPY(float val) {fSiPMHitPY = val;}
		void setSiPMHitPZ(float val) {fSiPMHitPZ = val;}
		void setSiPMHitE(float val) {fSiPMHitE = val;}
		void setSiPMHitProcessCreator(int val) {fSiPMHitProcessCreator = val;}		
*/





            ClassDef(SimTVTHit, 7)
    };
}

#endif
