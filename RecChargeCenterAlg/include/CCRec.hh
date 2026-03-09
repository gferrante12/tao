#ifndef CCREC_HH
#define CCREC_HH

#include "TTree.h"
#include "SniperKernel/AlgBase.h"
#include "SniperKernel/AlgFactory.h"
#include "TAOGeometry/SimGeomSvc.h"

#include "Math/Minimizer.h"
#include "Math/Functor.h"
#include "Math/Factory.h"
#include "Minuit2/FCNBase.h"
#include <vector>
#include <string>
#include "TGraph2D.h"
#include "CalibSvc/ICalibSvc.h"
#include <map>

#include "include/ChargeCenterUtils.hh"



class ChargeCenterRec : public AlgBase
{
    public:
        ChargeCenterRec(const std::string & name);
        ~ChargeCenterRec();      
        bool initialize();
        bool execute();
        bool finalize();
        // Charge Center Reconstruction
        bool CalChargeCenter(const std::vector<TVector3>& channelPositionVec, bool isCalculateInitialP=false, bool isDNcorrection=true ,std::string Pattern="None",bool ifClearBadChannelsPE=true,bool ifPixelCorrection=true);
        double EnergyRec(double fccRecR, double fCCRecTheta, double totalPE, std::string ParameterSelection);
        // Read Channel Positions
        std::vector<TVector3> ReadChannelPositions(const TString& filePath1, const TString& filePath2);
        std::vector<TVector3> ReadPixelPositions(const TString& filePath1);
        // Read Bad Channel ID
        std::vector<int> ReadBadChannelID(const TString& filePath1);
        // Read pixel
        std::vector<int> ReadchannelToPixelVec(const TString& csvPath, int channelNum);
        //
        TVector3 CalculateChargeCenter_Pixel (const std::vector<int>& fchannelToPixelVec,  const double* fChannelPE, const std::vector<TVector3>& fpixelPositionsVec,const std::vector<int>& fBadChannelIDVec);
        //
        std::map<int, double> ReadChannelDCR(const std::string& filename);
        TGraph2D* loadGraph2D(const std::string& filePath) {
            std::ifstream file(filePath);
            if (!file.is_open()) {
                std::cerr << "Error: Failed to open file " << filePath << "!" << std::endl;
                return nullptr;
            }
            std::string header;
            std::getline(file, header);

            // read data for interpolation map
            TGraph2D* graph = new TGraph2D();
            double x, y, z;
            int count = 0;
            while (file >> x >> y >> z) {
                graph->SetPoint(count, x, y, z);
                count++;
            }

            file.close();
            return graph;
        }
        struct ChannelInfo {
            int channelID;
            float x, y, z;
            int pixelLabel;
        };

    private:
        
        // result
        TTree* evt;
        int evtID;
        double initX,initY,initZ,kE,initR,initTheta,initPhi;
        double EdepX,EdepY,EdepZ,Edep,EdepR,EdepTheta,EdepPhi;
        double QEdepX,QEdepY,QEdepZ,QEdep,QEdepR,QEdepTheta,QEdepPhi;
        double fCCRecX,fCCRecY,fCCRecZ,fCCRecR,fCCRecTheta,fCCRecPhi;
        double totalPE,EvisRec,TimeStamp;
        double diffPerformanceR;
        double diffPerformanceTheta;
        double diffPerformancePhi;
        double p0, p1, p2, p3, p4, p5, p6;
        double fChannelHitPE[CHANNELNUM_total] = {0.0};
        double QEdepPE_factor; // the average PE of 1 MeV quenching energy deposition in the detector center
        std::vector<double> EScale = {5937.0, 6000.0};
        double maxPE[5];
        int maxPE_channelID[5];
        double totalPE_corr;
        double totalPE_corr_g;
        double BadChannelsTotalPECorr;
        double BadChannelsTotalPEReal;
        double BadChannelsTotalPE_Pixel;

        std::vector<int> channelToPixelVec;

        std::string InputElecFile;
        std::string BadChannelIDFile;
        std::vector<TVector3> channelPositionsVec;
        std::vector<TVector3> pixelPositionsVec;
        std::vector<int> BadChannelIDVec;

        Tao::SimEvt* ElecSim_Event= nullptr;
        TFile* ElecSim_File= nullptr;  
        TTree* ElecSim_Tree;

        TVector3 InitialQEdepPoint; 
        bool isRealData;
        bool isOpeningCorrection;
        bool isDarkNoiseCorrection;
        bool isEnergyCorrection;
        bool m_useDynamicBaseline;
        std::string CurveCorrectionPattern;
        TH1F *QEdepR_ifFccRbeyond900_merge;

        TGraph2D* g_graph;
        std::string nonUniformMapFile;
        std::string CurveParamsFile;

        std::ifstream channelFile2;
        std::ifstream BadChannelFile;
        TFile *func_file;

        std::map<int, TH1F*> histPEsMap;
        std::map<int, TH1F*> histTDCtimeMap;
        std::map<int, double> dcrMap;
        float minTDC;
        float maxTDC;
        ICalibSvc* m_calibsvc;
        // 构造值-索引对
        std::vector<std::pair<double, int>> v;

};



#endif