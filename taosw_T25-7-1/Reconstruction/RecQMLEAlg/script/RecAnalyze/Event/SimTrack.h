#ifndef SimTrack_h
#define SimTrack_h

#include "TObject.h"
#include <vector>

namespace Tao
{
    class SimTrack: public TObject {
        private:
            Int_t pdg_id;
            Int_t track_id;
            // == Init ==
            //Float_t init_mass;
            Float_t init_px;
            Float_t init_py;
            Float_t init_pz;
            Float_t init_ke;
	    Float_t init_x;
            Float_t init_y;
            Float_t init_z;
            Double_t init_t;

            // == Exit ==
            Float_t exit_px;
            Float_t exit_py;
            Float_t exit_pz;
	    Float_t exit_ke;
            Float_t exit_x;
            Float_t exit_y;
            Float_t exit_z;
            Double_t exit_t;

            Float_t track_length;

            // == Visible or Deposit Energy Related ==
            Float_t edep;
            Float_t edep_x;
            Float_t edep_y;
            Float_t edep_z;

            Float_t Qedep;
            Float_t Qedep_x;
            Float_t Qedep_y;
            Float_t Qedep_z;

            Float_t edep_notinLS;

	    
        public:

            SimTrack() {
                pdg_id = 0;
                track_id = -1;

                // == Init ==
                //init_mass = 0;
                init_px = 0;
                init_py = 0;
                init_pz = 0;

                init_x = 0;
                init_y = 0;
                init_z = 0;
                init_t = 0;
                // == Exit ==
                exit_px = 0;
                exit_py = 0;
                exit_pz = 0;

                exit_x = 0;
                exit_y = 0;
                exit_z = 0;
                exit_t = 0;

                track_length = 0;
                // == Visible or Deposit Energy Related ==
                edep = 0;
                edep_x = 0;
                edep_y = 0;
                edep_z = 0;
                Qedep = 0;
                Qedep_x = 0;
                Qedep_y = 0;
                Qedep_z = 0;
                edep_notinLS = 0;
            }
            virtual ~SimTrack() {}

            // = getter =
            int getPDGID() {return pdg_id;}
            int getTrackID() {return track_id;}
            //float getInitMass() {return init_mass;}
            // == Init ==
            float getInitPx() {return init_px;}
            float getInitPy() {return init_py;}
            float getInitPz() {return init_pz;}
            float getInitKE(){return init_ke;}
	    float getInitX() {return init_x;}
            float getInitY() {return init_y;}
            float getInitZ() {return init_z;}
            double getInitT() {return init_t;}
            // == Exit or Died ==
            float getExitPx() {return exit_px;}
            float getExitPy() {return exit_py;}
            float getExitPz() {return exit_pz;}
	    float getExitKE(){return exit_ke;}
            float getExitX() {return exit_x;}
            float getExitY() {return exit_y;}
            float getExitZ() {return exit_z;}
            double getExitT() {return exit_t;}
            float getTrackLength() {return track_length;}
            // == Visible or Deposit Energy Related ==
            float getEdep() {return edep;}
            float getEdepX() {return edep_x;}
            float getEdepY() {return edep_y;}
            float getEdepZ() {return edep_z;}
            float getQEdep() {return Qedep;}
            float getQEdepX() {return Qedep_x;}
            float getQEdepY() {return Qedep_y;}
            float getQEdepZ() {return Qedep_z;}
            float getEdepNotInLS() {return edep_notinLS;}

            // setter
            void setPDGID(int val) {pdg_id = val;}
            void setTrackID(int val) {track_id = val;}
            //void setInitMass(float val) {init_mass = val;}
            // == Init ==
            void setInitPx(float val) {init_px = val;}
            void setInitPy(float val) {init_py = val;}
            void setInitPz(float val) {init_pz = val;}
            void setInitKE(float val) {init_ke = val;}
	    void setInitX(float val) {init_x = val;}
            void setInitY(float val) {init_y = val;}
            void setInitZ(float val) {init_z = val;}
            void setInitT(double val) {init_t = val;}
            // == Exit or Died ==
            void setExitPx(float val) {exit_px = val;}
            void setExitPy(float val) {exit_py = val;}
            void setExitPz(float val) {exit_pz = val;}
 	    void setExitKE(float val) {exit_ke = val;}
            void setExitX(float val) {exit_x = val;}
            void setExitY(float val) {exit_y = val;}
            void setExitZ(float val) {exit_z = val;}
            void setExitT(double val) {exit_t = val;}
            void setTrackLength(float val) {track_length = val;}
            // == Visible or Deposit Energy Related ==
            void setEdep(float val) {edep = val;}
            void setEdepX(float val) {edep_x = val;}
            void setEdepY(float val) {edep_y = val;}
            void setEdepZ(float val) {edep_z = val;}
            void setQEdep(float val) {Qedep = val;}
            void setQEdepX(float val) {Qedep_x = val;}
            void setQEdepY(float val) {Qedep_y = val;}
            void setQEdepZ(float val) {Qedep_z = val;}
            void setEdepNotInLS(float val) {edep_notinLS = val;}

            ClassDef(SimTrack, 5)
    };

}

#endif
