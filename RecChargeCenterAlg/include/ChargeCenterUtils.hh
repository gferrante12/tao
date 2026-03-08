
#ifndef CHARGECENTER_UTILS_HH
#define CHARGECENTER_UTILS_HH

#include "TRandom3.h"
#include "TTree.h"
#include "SniperKernel/AlgBase.h"
#include "SniperKernel/AlgFactory.h"
#include "TAOGeometry/SimGeomSvc.h"
#include <TObject.h>
#include "Math/Minimizer.h"
#include "Math/Functor.h"
#include "Math/Factory.h"
#include "Minuit2/FCNBase.h"
#include <vector>
#include <string>
#include "TH2F.h"
#include "TH1F.h"
#include "TF1.h"
#include "TFile.h"
#include "Event/SimEvt.h"
#include "Event/SimTrack.h"
#include "TGraph2D.h"

#include <fstream> 
#include <TString.h> 
#include <iostream>  

using namespace std;

#define CHANNELNUM 8048
#define CHANNELNUM_ADD 102
#define CHANNELNUM_total (CHANNELNUM + CHANNELNUM_ADD) 

extern float channel_area;                  // mm^2
extern float channel_noise;                  // Hz/mm^2
extern float channel_readout_window;         // s
extern float dark_noise_prob;                // Hz
extern TString ChanelFile_path;              
extern TString ChanelFile2_path;             
extern TString xyz_label_healpix_path;        
extern TString Pixel_position_path;     

// Channel geometry parameters
extern std::unordered_map<int, int> SuPPoint_CHPoint_indexMap;
extern std::unordered_map<int, int> SuPPoint_SuPPoint_indexMap;

struct EdepCH_DistanceData {
    int index;
    double x, y, z;
    double R, theta, phi;
    double distance;

    EdepCH_DistanceData(int index, double x, double y, double z, double R, double theta, double phi, double distance)
        : index(index), x(x), y(y), z(z), R(R), theta(theta), phi(phi), distance(distance) {}
};

/*== Curve Correction parameters ==*/
// define the fit parameters for the multi-curve fit
using FitParams_multicurve = std::tuple<double, double,double>; 
inline double fitFunction(double x, const FitParams_multicurve& params) {
    // return params.first * x * x + params.second * x+ params.third;
    return std::get<0>(params) * x * x + std::get<1>(params) * x + std::get<2>(params);

}

extern std::map<std::pair<double, double>, FitParams_multicurve> multiCurveParams;
extern std::map<std::string, FitParams_multicurve> singleCurveParams;
/*== 2D interpolate function==*/
//
struct FitParams {
    double p0, p1, p2, p3, p4, p5, p6;
};
// Initialize fit parameters for 2D function interpolation
const std::map<std::string, FitParams> fitParamsTable = {
    {"Cs137_initial",   {-2.34023e-07, -1.27398e-10, 4.04935e-09, -2.04658e-11, -1.46475e-05, 1.62557e-05, 0.999451}},
    {"Cs137_Edep",      {-5.36352e-07, -2.27306e-10, 5.52445e-09, -2.62956e-11, 4.86215e-06, 6.1047e-05, 0.996084}},
    {"neutron_initial", {1.11026e-07, -8.71058e-11, 3.03898e-09, -1.75773e-11, -5.34787e-05, -1.43708e-05, 1.00311}},
    {"neutron_Edep",    {1.31906e-08, -2.17537e-10, 4.77138e-09, -2.65505e-11, -4.31907e-05, -1.1216e-06, 1.0005}}
};
// 2D interpolation using fit function
inline double interpolateZ(double x, double y, const FitParams& params) {
    double x2 = x * x;
    double y2 = y * y;
    double x3 = x2 * x;
    double x2y2 = x2 * y2;

    return params.p0 * x * y +
           params.p1 * x3 +
           params.p2 * x2 * y +
           params.p3 * x2y2 +
           params.p4 * x +
           params.p5 * y +
           params.p6;
}
///////////////////////////////////////

//
std::array<double, 3> xyz2rthetaphi(double x, double y, double z);
void FindNearChannelIndices(int index_SuppCH,
                           const std::unordered_map<int, int>& SuPPoint_CHPoint_indexMap,
                           const std::unordered_map<int, int>& SuPPoint_SuPPoint_indexMap,
                           std::vector<int>& IndexVec);
std::vector<int> PrintDistanceMatchingIndices(const std::vector<EdepCH_DistanceData>& distancesVec, double Distance2);
void CalculateEdepCHDistance(const TVector3& EdepPoint, std::vector<EdepCH_DistanceData>& distancesVec,TString CHfilePath, std::vector<int>& BadChannelIDVec,bool If_continue_badCH);
void CalculateSuppChannelPEs(std::istream& channelFile2, const TVector3& QEdepPoint,
                              const std::vector<EdepCH_DistanceData>& distancesVec,
                              double* fChannelHitPE);
void UpdateBadChannelPEs(std::istream& BadChannelFile, const TVector3& QEdepPoint,
                              const std::vector<EdepCH_DistanceData>& distancesVec,
                              double* fChannelHitPE);
double calculateNewFccRecR(double fCCRecR, double ori_fCCRecR, const std::string& Pattern);
double calculateNewFccRecR_detsim(double fCCRecR, double ori_fCCRecR);

double FitFuncinterpolate2D(double inputX, double inputY, const std::string& selection);

double interpolate2D(TGraph2D* graph, double inputX, double inputY);

double newFccRecrRandom(double new_fccRecR, const TH1F *QEdepR_ifFccRbeyond900_merge);

bool loadCurveParams(const std::string& filename);


#endif // CHARGECENTER_UTILS_H