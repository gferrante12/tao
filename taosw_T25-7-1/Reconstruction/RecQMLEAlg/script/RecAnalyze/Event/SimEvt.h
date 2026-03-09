#ifndef SimEvt_h
#define SimEvt_h

#include "Event/EventObject.h"
#include "Event/SimSipmHit.h"
#include "Event/SimTrack.h"
#include <vector>
#include "Event/SimPmtHit.h"
#include "Event/SimTVTHit.h"
namespace Tao
{
    class SimSipmHit;
    class SimTrack;
    class SimPmtHit;
	// class SimTTHit;
    class SimTVTHit;
    class SimEvt: public JM::EventObject
    {
        private:
            std::vector<SimTrack*> m_primary_tracks;  
            std::vector<SimSipmHit*> m_cd_hits; 
		std::vector<SimPmtHit*> m_wp_hits;
		
       //     std::vector<SimTTHit*> m_tt_hits; 
	    std::vector<SimTVTHit*> m_tvt_hits; 
            Int_t m_nhits;
            Int_t m_ntrks;
          //  Int_t m_nbars;

            Int_t m_counter; // only for debug
            Int_t m_eventid;
            Int_t m_cd_nhits;    
	    Int_t m_sipm_nhits;
	    Int_t m_tvt_nhits;
	    Int_t m_Sipm_nhits;
	    Int_t m_EvtType;
	    Int_t m_wp_nhits;
	    Int_t m_pmt_nhits;
	    Int_t fRndSeed;
  
	    Float_t GdLs_edep;
            Float_t GdLs_edep_x;
            Float_t GdLs_edep_y;
            Float_t GdLs_edep_z;

            // don't support the copy constructor
            SimEvt(const SimEvt& event);

        public:
            SimEvt();
            SimEvt(Int_t evtid);
            ~SimEvt();

            // == Initial Track Info ==
            Tao::SimTrack *addTrack();
            const std::vector<Tao::SimTrack*>& getTracksVec() const {return m_primary_tracks;}
            Tao::SimTrack *findTrackByTrkID(int trkid);

            // == CD (Central Detector) Related ==
            Tao::SimSipmHit *addCDHit();
            const std::vector<Tao::SimSipmHit*>& getCDHitsVec() const {return m_cd_hits;}
	    //Tao::SimSipmHit *findCdSipmHitBySipmHitID(int sipmhitid);
			
            Tao::SimPmtHit *addWpHit();
            const std::vector<Tao::SimPmtHit*>& getPmtHitVec() const {return m_wp_hits;}


/*
            // == TT (Top Tracker) Related ==
            Tao::SimTTHit *addTTHit();
            const std::vector<Tao::SimTTHit*>& getTTHitsVec() const {return m_tt_hits;}
*/
            Tao::SimTVTHit *addTVTHit();
	    const std::vector<Tao::SimTVTHit*>& getTVTHitsVec() const {return m_tvt_hits;} 
	    // == Event ID ==
            Int_t getEventID() { return m_eventid; }
            void setEventID(Int_t val) { m_eventid = val; }
             
            Int_t getSipmHits() { return m_sipm_nhits; }
            void setSipmHits(Int_t hits) { m_sipm_nhits = hits ; }

	    Int_t getRandomSeed() { return fRndSeed; }
            void setRandomSeed(Int_t val) { fRndSeed = val; }	    

	    void setEdep(float val) {GdLs_edep = val;}
            void setEdepX(float val) {GdLs_edep_x = val;}
            void setEdepY(float val) {GdLs_edep_y = val;}
            void setEdepZ(float val) {GdLs_edep_z = val;}
	    float getEdep() {return GdLs_edep;}
            float getEdepX() {return GdLs_edep_x;}
            float getEdepY() {return GdLs_edep_y;}
            float getEdepZ() {return GdLs_edep_z;}

		Int_t getEventType() { return m_EvtType; }
		void setEventType(Int_t val) { m_EvtType = val; }
		Int_t getNTracks() { return m_ntrks;}

            ClassDef(SimEvt, 10)

    };
}

#endif
