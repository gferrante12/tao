#include "Math/Minimizer.h"
#include "Math/GSLMinimizer.h"
#include "Math/Functor.h"
#include "Math/Factory.h"
#include "Minuit2/FCNBase.h"
#include "TVector3.h"
#include <cmath>

#include "Event/SimHeader.h"
#include "Event/CdElecHeader.h"
#include "Event/CdElecEvt.h"
#include "Event/CdElecChannel.h"
#include "Event/CdVertexRecEvt.h"
#include "Event/CdVertexRecHeader.h"

#include "Event/CdCalibHeader.h"
#include "Event/CdCalibEvt.h"
#include "Event/CdCalibChannel.h"
#include "Event/WtTrigHeader.h"
#include "Event/TvtTrigHeader.h"
#include "Event/WtElecHeader.h"
#include "Event/TvtElecHeader.h"


#include "SniperKernel/AlgFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/SniperLog.h"
#include "RootWriter/RootWriter.h"
#include "EvtNavigator/EvtNavHelper.h"
#include "BufferMemMgr/IDataMemMgr.h"
#include "EvtNavigator/NavBuffer.h"
#include "TAOGeometry/SimGeomSvc.h"
#include "TFile.h"
#include "TTree.h"
#include "TChain.h"
#include "TGraph2D.h"

#include <TGeoManager.h>
#include <numeric> 
#include <boost/python.hpp>
#include <vector>
#include <iostream>
#include <string>
#include <algorithm>

#include "include/ChargeCenterUtils.hh"
#include "include/CCRec.hh"
#include <iomanip>
#include <random>
DECLARE_ALGORITHM(ChargeCenterRec);

ChargeCenterRec::ChargeCenterRec(const std::string& name)
    : AlgBase(name),evt(0), fChannelHitPE{0.0}
{
    evtID = 0;
    // QEdepPE_factor = 5937; // from e+
    // std::string ChanelFile_path_env = getenv("RECCHARGECENTERALGROOT");
    // nonUniformMapFile = ChanelFile_path_env + "/script/all_R_theta_G_CT2Dinterpolator.txt";
    declProp("EnergyScaleFactor",EScale);
    declProp("input_ElecFile",InputElecFile = "input_ElecFile.root");
    declProp("isRealData",isRealData = false);
    declProp("isOpeningsCorrection",isOpeningCorrection = true);
    declProp("isDarkNoiseCorrection",isDarkNoiseCorrection = true);
    declProp("CurveCorrectionPattern",CurveCorrectionPattern = "multicurve");
    declProp("minTDC",minTDC=-160);
    declProp("maxTDC",maxTDC=1280);
    declProp("BadChannelIDFile",BadChannelIDFile );
    declProp("nonUniformMapFile",nonUniformMapFile );
    declProp("CurveParamsFile",CurveParamsFile);
    declProp("isEnergyCorrection",isEnergyCorrection = true);
}

ChargeCenterRec::~ChargeCenterRec()
{
}

bool ChargeCenterRec::initialize()
{
    SniperPtr<ICalibSvc> Calib_svc (getParent(), "CalibSvc");
    if (Calib_svc.invalid()) {
       LogError << "can't find service CalibSvc" << std::endl;
       return false;
    }
    m_calibsvc = Calib_svc.data();  
    m_useDynamicBaseline=m_calibsvc->UseDynamicBaseline();
    std::cout<<"m_useDynamicBaseline: "<<m_useDynamicBaseline<<std::endl;
    bool m_saveRootFile = true;
    // = get RootWriter =
    std::string rootPath = getenv("RECCHARGECENTERALGROOT");
    SniperPtr<RootWriter> rootwriter(getParent(), "RootWriter");
    if (rootwriter.invalid()) {
        LogInfo << "Don't Load RootWriter"
                << std::endl;
        m_saveRootFile = false;
        // return false;
    }
    if(m_saveRootFile){
        #ifndef SNIPER_VERSION_2
            evt = rootwriter->bookTree("RECEVT/RecEvt", "user defined data");
        #else
            evt = rootwriter->bookTree(*getParent(), "RECEVT/RecEvt", "user defined data");
        #endif
    
        if (isRealData){    
            evt->Branch("evtID", &evtID, "evtID/I");
            evt->Branch("fCCRecX",&fCCRecX,"fCCRecX/D");
            evt->Branch("fCCRecY",&fCCRecY,"fCCRecY/D");
            evt->Branch("fCCRecZ",&fCCRecZ,"fCCRecZ/D");
            evt->Branch("fCCRecR",&fCCRecR,"fCCRecR/D");
            evt->Branch("fCCRecTheta",&fCCRecTheta,"fCCRecTheta/D");
            evt->Branch("fCCRecPhi",&fCCRecPhi,"fCCRecPhi/D");
            evt->Branch("totalPE",&totalPE,"totalPE/D");
            evt->Branch("totalPE_corr",&totalPE_corr,"totalPE_corr/D");
            evt->Branch("totalPE_corr_g",&totalPE_corr_g,"totalPE_corr_g/D");
            evt->Branch("BadChannelsTotalPECorr",&BadChannelsTotalPECorr,"BadChannelsTotalPECorr/D"); // Symmetry-based correction 
            evt->Branch("BadChannelsTotalPEReal",&BadChannelsTotalPEReal,"BadChannelsTotalPEReal/D"); // It is valid only for simulation
            evt->Branch("BadChannelsTotalPE_Pixel",&BadChannelsTotalPE_Pixel,"BadChannelsTotalPE_Pixel/D"); // pixel-based correction 
            evt->Branch("EvisRec",&EvisRec,"EvisRec/D");
            evt->Branch("TimeStamp",&TimeStamp,"TimeStamp/D");
            evt->Branch("maxPE",&maxPE,"maxPE[5]/D");
            evt->Branch("maxPE_channelID",&maxPE_channelID,"maxPE_channelID[5]/I");

        }
        else if (!isRealData){
            evt->Branch("evtID", &evtID, "evtID/I");
            evt->Branch("initX",&initX,"initX/D");
            evt->Branch("initY",&initY,"initY/D");
            evt->Branch("initZ",&initZ,"initZ/D");
            evt->Branch("initkE",&kE,"kE/D");
            evt->Branch("initR",&initR,"initR/D");
            evt->Branch("initTheta",&initTheta,"initTheta/D");
            evt->Branch("initPhi",&initPhi,"initPhi/D");
            evt->Branch("EdepX",&EdepX,"EdepX/D");
            evt->Branch("EdepY",&EdepY,"EdepY/D");
            evt->Branch("EdepZ",&EdepZ,"EdepZ/D");
            evt->Branch("Edep",&Edep,"Edep/D");
            evt->Branch("EdepR",&EdepR,"EdepR/D");
            evt->Branch("EdepTheta",&EdepTheta,"EdepTheta/D");
            evt->Branch("EdepPhi",&EdepPhi,"EdepPhi/D");
            evt->Branch("QEdepX",&QEdepX,"QEdepX/D");
            evt->Branch("QEdepY",&QEdepY,"QEdepY/D");
            evt->Branch("QEdepZ",&QEdepZ,"QEdepZ/D");
            evt->Branch("QEdep",&QEdep,"QEdep/D");
            evt->Branch("QEdepR",&QEdepR,"QEdepR/D");
            evt->Branch("QEdepTheta",&QEdepTheta,"QEdepTheta/D");
            evt->Branch("QEdepPhi",&QEdepPhi,"QEdepPhi/D");
            evt->Branch("fCCRecX",&fCCRecX,"fCCRecX/D");
            evt->Branch("fCCRecY",&fCCRecY,"fCCRecY/D");
            evt->Branch("fCCRecZ",&fCCRecZ,"fCCRecZ/D");
            evt->Branch("fCCRecR",&fCCRecR,"fCCRecR/D");
            evt->Branch("fCCRecTheta",&fCCRecTheta,"fCCRecTheta/D");
            evt->Branch("fCCRecPhi",&fCCRecPhi,"fCCRecPhi/D");
            evt->Branch("totalPE",&totalPE,"totalPE/D"); // totalPE = good Channel totalPEs
            evt->Branch("totalPE_corr",&totalPE_corr,"totalPE_corr/D"); // totalPE_corr = good Channel totalPEs + bad Channel totalPEs
            evt->Branch("totalPE_corr_g",&totalPE_corr_g,"totalPE_corr_g/D"); // totalPE_corr/g(r,theta)
            evt->Branch("BadChannelsTotalPECorr",&BadChannelsTotalPECorr,"BadChannelsTotalPECorr/D"); // Symmetry-based correction 
            evt->Branch("BadChannelsTotalPEReal",&BadChannelsTotalPEReal,"BadChannelsTotalPEReal/D"); // It is valid only for simulation
            evt->Branch("BadChannelsTotalPE_Pixel",&BadChannelsTotalPE_Pixel,"BadChannelsTotalPE_Pixel/D"); // pixel-based correction 
            evt->Branch("EvisRec",&EvisRec,"EvisRec/D");
            evt->Branch("diffPerformanceR",&diffPerformanceR,"diffPerformanceR/D");
            evt->Branch("diffPerformanceTheta",&diffPerformanceTheta,"diffPerformanceTheta/D");
            evt->Branch("diffPerformancePhi",&diffPerformancePhi,"diffPerformancePhi/D");
            // 
            ElecSim_Event = new Tao::SimEvt();
            ElecSim_File = TFile::Open(InputElecFile.c_str());
            ElecSim_Tree = (TTree*)ElecSim_File->Get("/Event/Sim/SimEvt");
            ElecSim_Tree->SetBranchAddress("SimEvt", &ElecSim_Event);
            cout<<"ElecSim_Tree->GetEntries() is: "<<ElecSim_Tree->GetEntries()<<endl;
        }
        else {
            LogError << "Error: isRealData is not defined." << std::endl;
            return false;
        }
    }else{
        evt = nullptr;
        LogInfo << "Not save UserRec RootFile." << std::endl;
    }
    LogInfo<<"min: "<<minTDC<<" max:"<< maxTDC <<std::endl;
    channel_readout_window = (maxTDC - minTDC)*1e-9;
    LogInfo<<"channel_readout_window: "<<channel_readout_window <<" s" <<std::endl;
    // = read all channel positions =
    LogInfo <<"ChanelFile_path: "<< ChanelFile_path << endl;
    LogInfo <<"ChanelFile2_path: "<< ChanelFile2_path << endl;
    channelPositionsVec = ChargeCenterRec::ReadChannelPositions(ChanelFile_path, ChanelFile2_path);

    // = read bad channel infomation  =
    if(BadChannelIDFile.size()==0)
    {
    //    BadChannelIDFile = rootPath+"/script/Bad_channels961_20251206.txt";
        if (m_useDynamicBaseline){
            BadChannelIDFile = rootPath+"/script/ALLBad_channels_20260112_1039_dy.txt";
            LogInfo << "Use dynamic baseline, BadChannelIDFile: " << BadChannelIDFile << std::endl;
        } else {
            BadChannelIDFile = rootPath+"/script/ALLBad_channels_20260112_1053_st.txt";
            LogInfo << "Use static baseline, BadChannelIDFile: " << BadChannelIDFile << std::endl;
        }

    }
    LogInfo << "The bad channel file: " << BadChannelIDFile << std::endl;    
    BadChannelIDVec = ChargeCenterRec::ReadBadChannelID(BadChannelIDFile);
    LogInfo<<"channelPositionsVec.size(): "<<channelPositionsVec.size()<<std::endl;
    LogInfo<<"BadChannelIDVec.Size(): "<<BadChannelIDVec.size()<<std::endl;
    BadChannelFile.open(BadChannelIDFile.c_str());
    if (!BadChannelFile.is_open()) {
        LogError << "Error opening file: " << BadChannelIDFile.c_str() << std::endl;
        return true;
    }    

    // read non-uniform map
    if(nonUniformMapFile.size()==0)
    {
       if(m_useDynamicBaseline){
            nonUniformMapFile = rootPath+"/script/Enegy_nonUniformityMap_DynamicBaseline.txt";
            LogInfo << "Use dynamic baseline, nonUniformMapFile: " << nonUniformMapFile << std::endl;
       } else {
            nonUniformMapFile = rootPath+"/script/Energy_nonUniformityMap_StaticBaseline.txt";
            LogInfo << "Use static baseline, nonUniformMapFile: " << nonUniformMapFile << std::endl;
       }
    }
    g_graph = ChargeCenterRec::loadGraph2D(nonUniformMapFile);
    //

    std::string FileName = rootPath + "/script/openEffsample_beyond900Points.root";
    func_file = new TFile(FileName.c_str(), "read");
    QEdepR_ifFccRbeyond900_merge = (TH1F*)func_file->Get("QEdepR_ifFccRbeyond900");
    //
    channelFile2.open(ChanelFile2_path.Data());
    if (!channelFile2.is_open()) {
        LogError << "Error opening file: " << ChanelFile2_path.Data() << std::endl;
        return true;
    }
    //
    channelToPixelVec = ChargeCenterRec::ReadchannelToPixelVec(xyz_label_healpix_path, 8048);
    LogInfo<<"channelToPixelVec.size(): "<<channelToPixelVec.size()<<std::endl;
    //
    pixelPositionsVec = ChargeCenterRec::ReadPixelPositions(Pixel_position_path);
    LogInfo<<"pixelPositionsVec.size(): "<<pixelPositionsVec.size()<<std::endl;
    //
    for(int i=0; i<5; i++) {
        LogInfo << "ChannelID: " << i << ", DCR = " << m_calibsvc->GetDCR(i) << std::endl;
    }
    //
    // std::string CurveParamsFile;
    if (CurveParamsFile.size()==0){
        if (m_useDynamicBaseline){
            CurveParamsFile = rootPath + "/script/curve_params_DynamicBaseline.csv";
        } else {
            CurveParamsFile = rootPath + "/script/curve_params_StaticBaseline.csv";
        }        
    }
    LogInfo << "CurveParamsFile: " << CurveParamsFile << std::endl;  
    if (!loadCurveParams(CurveParamsFile)) {
        LogError << "Failed to load curve parameters\n";
        return true;
    }      
    //
    if (m_useDynamicBaseline){
        QEdepPE_factor = EScale[1];
    } else {
        QEdepPE_factor = EScale[0];
    }      
    LogInfo << "QEdepPE_factor: " << QEdepPE_factor << std::endl;


    //
    channelToPixelVec = ChargeCenterRec::ReadchannelToPixelVec(xyz_label_healpix_path, 8048);
    std::cout<<"channelToPixelVec.size(): "<<channelToPixelVec.size()<<std::endl;
    //
    pixelPositionsVec = ChargeCenterRec::ReadPixelPositions(Pixel_position_path);
    std::cout<<"pixelPositionsVec.size(): "<<pixelPositionsVec.size()<<std::endl;
    //


    return true;
}

bool ChargeCenterRec::execute()
{
    // = initialize =
    std::fill(std::begin(fChannelHitPE), std::end(fChannelHitPE), 0.0);
    SniperDataPtr<JM::NavBuffer> navBuf(getRoot(), "/Event");
    if (navBuf.invalid()) {
        return 0;
    }
    LogDebug << "navBuf: " << navBuf.data() << std::endl;

    JM::EvtNavigator* evt_nav = navBuf->curEvt();
    LogDebug << "evt_nav: " << evt_nav << std::endl;
    if (not evt_nav) {
        return 0;
    }

    Tao::TvtElecHeader* tvt_elec_hdr = dynamic_cast<Tao::TvtElecHeader*>(evt_nav->getHeader("/Event/TvtElec"));
    if (tvt_elec_hdr && tvt_elec_hdr->hasEvent()) {
        return true;
    }
    
    Tao::WtElecHeader* wt_elec_hdr = dynamic_cast<Tao::WtElecHeader*>(evt_nav->getHeader("/Event/WtElec"));
    if (wt_elec_hdr && wt_elec_hdr->hasEvent()) {
        return true;
    }


    Tao::CdCalibHeader* cd_calib_hdr = dynamic_cast<Tao::CdCalibHeader*>(evt_nav->getHeader("/Event/Calib"));
    if (not cd_calib_hdr) {
        return true;
    }
    if (!cd_calib_hdr->hasEvent()) {
        std::cout<<"no data is found, skip this event."<<std::endl;
        return true;
    }

    Tao::CdVertexRecHeader* cd_rec_evt_header = NULL;
    Tao::CdVertexRecEvt* cd_rec_evt = NULL;
    if(! cd_rec_evt_header) {
        cd_rec_evt_header = new Tao::CdVertexRecHeader();
        cd_rec_evt = new Tao::CdVertexRecEvt();
    }
    // == get calib event ==
    Tao::CdCalibEvt* calib_event = dynamic_cast<Tao::CdCalibEvt*>(cd_calib_hdr->event());
    TimeStamp=evt_nav->TimeStamp();
    std::vector<Tao::CdCalibChannel> cal_Channels = calib_event->GetCalibChannels(); 
    double sumPE =0;   
    double PE;
    bool muonflag=false;
    fCCRecX = 2000;
    fCCRecY = 2000;
    fCCRecZ = 2000;
    fCCRecR = 2000;
    fCCRecTheta = 200;
    fCCRecPhi=400;
    totalPE_corr = 0;
    totalPE_corr_g=0;
    totalPE = 0;
    BadChannelsTotalPECorr = 0;
    BadChannelsTotalPEReal = 0;
    BadChannelsTotalPE_Pixel = 0;
    EvisRec = 0;
    for (auto it_channel = cal_Channels.begin();it_channel != cal_Channels.end(); ++it_channel){ 
        auto it = *it_channel; //
        if (it.CalibgetChannelID()>8048) continue;

        //  Calculate the total PE of the event
        std::vector<float> PEs = it.CalibgetPEs();
        std::vector<float> TDCtime = it.CalibgetTDCs();
        double PE_size = PEs.size();
        double TDCtime_size = TDCtime.size();
        PE = 0;
        for (int i=0;i<PE_size;i++){
            
            if (TDCtime[i]>minTDC && TDCtime[i]<maxTDC){
                PE += PEs[i];                
            }        
        }
        // std::cout<< "evtID: "<<evtID<<" it.CalibgetChannelID(): "<<it.CalibgetChannelID()<< " PE:"<< PE <<std::endl;
        if (it.CalibgetChannelID()==8048) {
            PE=std::accumulate(PEs.begin(), PEs.end(), 0.0f);
            muonflag=true;
        }
        if(isDarkNoiseCorrection) {
            // auto it_dcr = dcrMap.find(it.CalibgetChannelID());
            double dcr = 0;
            // if (it_dcr != dcrMap.end()) dcr = it_dcr->second; 
            if (isRealData){
                dcr = m_calibsvc->GetDCR(it.CalibgetChannelID());
            }else{
                dcr = 20*channel_area*channel_readout_window;
                if (CurveCorrectionPattern == "AllCalibcurve" || CurveCorrectionPattern == "CLScurve" || CurveCorrectionPattern == "ACUcurve" ||CurveCorrectionPattern == "multicurve") dcr=0;
            }
            int roundedPE = static_cast<int>(std::round(PE));
            PE = roundedPE - dcr*channel_readout_window;
            if (PE<0) PE=0;
        }
        sumPE += PE;
        fChannelHitPE[it.CalibgetChannelID()] = PE;
    }
    double BadChannelsTotalPEReal_Sum = 0;
    for (int id : BadChannelIDVec){
        BadChannelsTotalPEReal_Sum += fChannelHitPE[id];
    }
    BadChannelsTotalPEReal = BadChannelsTotalPEReal_Sum;
    // std::cout<<"muonflag: "<<muonflag<<" sumPE: "<<sumPE<<std::endl;
    //
    if (muonflag){
        totalPE = sumPE;
        totalPE_corr = sumPE;      
        totalPE_corr_g = sumPE;
        EvisRec = totalPE/QEdepPE_factor;
        if (evt) evt->Fill();
        cd_rec_evt -> setPESum(totalPE);   
        cd_rec_evt -> setPESum_g(totalPE_corr_g);
        cd_rec_evt -> setEnergy(EvisRec); // fRecEvis = Enrec
        cd_rec_evt -> setX(2000);
        cd_rec_evt -> setY(2000);
        cd_rec_evt -> setZ(2000);
        cd_rec_evt -> setTimeStamp(TimeStamp);
        cd_rec_evt_header -> setCdVertexEvent(cd_rec_evt);
        evt_nav -> addHeader("/Event/Rec/ChargeCenterAlg", cd_rec_evt_header);

        evtID += 1; 
        return true;
    }
    
    if (isRealData){    // if isRealData is true, then the event is real data, calculate the charge center for "InitialQEdepPoint"
        if (isOpeningCorrection){ // correct openings
            ChargeCenterRec::CalChargeCenter(channelPositionsVec,true,isDarkNoiseCorrection, CurveCorrectionPattern);            
            std::vector<EdepCH_DistanceData> distancesVec;
            CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, false); // 计算能量沉积点和所有通道的位置
            CalculateSuppChannelPEs(channelFile2, InitialQEdepPoint, distancesVec, fChannelHitPE);
            // charge center reconstruction
            ChargeCenterRec::CalChargeCenter(channelPositionsVec,false,isDarkNoiseCorrection, CurveCorrectionPattern,false);
        }
        else {// 先不修正上下两个开孔
            
            if (CurveCorrectionPattern=="None" || CurveCorrectionPattern == "AllCalibcurve" || CurveCorrectionPattern == "CLScurve" || CurveCorrectionPattern == "ACUcurve" || CurveCorrectionPattern == "multicurve"){
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = false;
                std::cout<<"CurveCorrectionPattern: "<<CurveCorrectionPattern<<std::endl;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test02"|| CurveCorrectionPattern=="Test02R1364" || CurveCorrectionPattern=="Test05"||CurveCorrectionPattern=="Test06"||CurveCorrectionPattern=="Test07"){ //相比于None只做特征聚合处理，即 ifPixelCorrection = true
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test02R" || CurveCorrectionPattern=="Test05R"|| CurveCorrectionPattern=="Test05RTheta"||CurveCorrectionPattern=="Test06R"||CurveCorrectionPattern=="Test07R"){ //使用test02的结果带入修正曲线，即 ifPixelCorrection = true后使用修正曲线
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test03"){ //先使用Test02R的结果补全坏通道
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02R", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  

            }
            else if (CurveCorrectionPattern=="Test03R"){ //基于test03的结果带入修正曲线
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02R", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test04"){ // 补全坏通道，同时补全上下顶部位置的通道
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02R", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                // openings correction
                std::vector<EdepCH_DistanceData> distancesVec2_8048CH;
                std::vector<int> noBadChannelID_emptyVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec2_8048CH, ChanelFile_path, noBadChannelID_emptyVec, true);
                CalculateSuppChannelPEs(channelFile2, InitialQEdepPoint, distancesVec2_8048CH, fChannelHitPE);
                //
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection); 
            }
            else if (CurveCorrectionPattern=="Test04R"){ 
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02R", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                // openings correction
                std::vector<EdepCH_DistanceData> distancesVec2_8048CH;
                std::vector<int> noBadChannelID_emptyVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec2_8048CH, ChanelFile_path, noBadChannelID_emptyVec, true);
                CalculateSuppChannelPEs(channelFile2, InitialQEdepPoint, distancesVec2_8048CH, fChannelHitPE);
                //
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection); 

            }
            
            
            else{ 
                std::cout<<"CurveCorrectionPattern: "<<CurveCorrectionPattern<< " is not supported"<<std::endl;
                return false;
              
            }

        }


    }
    else if (!isRealData){
        // == get elec event ==
        ElecSim_Tree->GetEntry(evtID);
        const auto& PrimaryEvent = ElecSim_Event->getTracksVec();
        initX = PrimaryEvent[0]->getInitX();
        initY = PrimaryEvent[0]->getInitY();
        initZ = PrimaryEvent[0]->getInitZ();
        kE = PrimaryEvent[0]->getInitKE();
        initR = sqrt(initX*initX + initY*initY + initZ*initZ);
        initTheta = (acos(initZ/initR))*180/M_PI;
        initPhi = atan2(initY,initX)*180/M_PI;
        //
        EdepX = ElecSim_Event->getEdepX();
        EdepY = ElecSim_Event->getEdepY();
        EdepZ = ElecSim_Event->getEdepZ();
        Edep = ElecSim_Event->getEdep();
        EdepR = sqrt(EdepX*EdepX + EdepY*EdepY + EdepZ*EdepZ);
        EdepTheta = acos(EdepZ/EdepR)*180/M_PI;
        EdepPhi = atan2(EdepY,EdepX)*180/M_PI;
        //
        QEdepX = PrimaryEvent[0]->getQEdepX();
        QEdepY = PrimaryEvent[0]->getQEdepY();
        QEdepZ = PrimaryEvent[0]->getQEdepZ();
        QEdep = PrimaryEvent[0]->getQEdep();
        QEdepR = sqrt(QEdepX*QEdepX + QEdepY*QEdepY + QEdepZ*QEdepZ);
        QEdepTheta = acos(QEdepZ/QEdepR)*180/M_PI;
        QEdepPhi = atan2(QEdepY,QEdepX)*180/M_PI;
        InitialQEdepPoint = TVector3(QEdepX, QEdepY, QEdepZ);   
        if (isOpeningCorrection){ // correct openings
            if(CurveCorrectionPattern == "AllCalibcurve" || CurveCorrectionPattern == "CLScurve" || CurveCorrectionPattern == "ACUcurve" || CurveCorrectionPattern == "multicurve"){
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true; //这种情况对应没有坏通道，所以不用清除坏通道PE
                bool ifPixelCorrection = false;
                // std::cout<<"CurveCorrectionPattern: "<<CurveCorrectionPattern<<std::endl;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);   
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, false); // 计算能量沉积点和所有通道的位置
                CalculateSuppChannelPEs(channelFile2, InitialQEdepPoint, distancesVec, fChannelHitPE);   
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);                              
            }else{
                std::cout<<"CurveCorrectionPattern: "<<CurveCorrectionPattern<< " is not supported, when isOpeningCorrection = true"<<std::endl;
                return false;
            }
        }
        else {// 先不修正上下两个开孔
            
            if (CurveCorrectionPattern=="None"){
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = false;
                // std::cout<<"CurveCorrectionPattern: "<<CurveCorrectionPattern<<std::endl;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test02" || CurveCorrectionPattern=="Test05"||CurveCorrectionPattern=="Test06"||CurveCorrectionPattern=="Test07"){ //相比于None只做特征聚合处理，即 ifPixelCorrection = true
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test02R"|| CurveCorrectionPattern=="Test02R1364"|| CurveCorrectionPattern=="Test02RSim" || CurveCorrectionPattern=="Test05R"|| CurveCorrectionPattern=="Test05RTheta"||CurveCorrectionPattern=="Test06R"||CurveCorrectionPattern=="Test07R"){ //使用test02的结果带入修正曲线，即 ifPixelCorrection = true后使用修正曲线
                bool isCalculateInitialP=false;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test03"){ //先使用Test02R的结果补全坏通道
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02R", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  

            }
            else if (CurveCorrectionPattern=="Test03R"){ //基于test03的结果带入修正曲线
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02R", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection);  
            }
            else if (CurveCorrectionPattern=="Test04"){ // 补全坏通道，同时补全上下顶部位置的通道
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02RSim", ifClearBadChannelsPE, ifPixelCorrection);  
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                // openings correction
                std::vector<EdepCH_DistanceData> distancesVec2_8048CH;
                std::vector<int> noBadChannelID_emptyVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec2_8048CH, ChanelFile_path, noBadChannelID_emptyVec, true);
                CalculateSuppChannelPEs(channelFile2, InitialQEdepPoint, distancesVec2_8048CH, fChannelHitPE);
                //
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection); 
            }
            else if (CurveCorrectionPattern=="Test04R" || CurveCorrectionPattern=="Test04RSim"){ 
                bool isCalculateInitialP=true;
                bool ifClearBadChannelsPE = true;
                bool ifPixelCorrection = true;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, "Test02RSim", ifClearBadChannelsPE, ifPixelCorrection);  
                double BadChannelsTotalPE_Pixel_Temp = BadChannelsTotalPE_Pixel; 
                std::vector<EdepCH_DistanceData> distancesVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec, ChanelFile_path, BadChannelIDVec, true); // 计算能量沉积点和所有Good通道的位置
                UpdateBadChannelPEs(BadChannelFile, InitialQEdepPoint, distancesVec, fChannelHitPE);
                // openings correction
                std::vector<EdepCH_DistanceData> distancesVec2_8048CH;
                std::vector<int> noBadChannelID_emptyVec;
                CalculateEdepCHDistance(InitialQEdepPoint, distancesVec2_8048CH, ChanelFile_path, noBadChannelID_emptyVec, true);
                CalculateSuppChannelPEs(channelFile2, InitialQEdepPoint, distancesVec2_8048CH, fChannelHitPE);
                //
                isCalculateInitialP=false;
                ifClearBadChannelsPE = false;
                ifPixelCorrection = false;
                ChargeCenterRec::CalChargeCenter(channelPositionsVec,isCalculateInitialP,isDarkNoiseCorrection, CurveCorrectionPattern, ifClearBadChannelsPE, ifPixelCorrection); 
                double BadCHsPESum = 0;
                for (int id : BadChannelIDVec) {
                    BadCHsPESum += fChannelHitPE[id];
                }
                BadChannelsTotalPECorr = BadCHsPESum;
                BadChannelsTotalPE_Pixel=BadChannelsTotalPE_Pixel_Temp;

            }
            
            
            else{ //Test03的执行：
                std::cout<<"CurveCorrectionPattern: "<<CurveCorrectionPattern<< " is not supported"<<std::endl;
                return false;
              
            }

        }
    }
    else {
        LogError << "Error: isRealData is not defined." << std::endl;
        return false;
    }
    if (isEnergyCorrection){
        EvisRec = ChargeCenterRec::EnergyRec(fCCRecR, fCCRecTheta, totalPE_corr,"map");  
    }
    else{
        EvisRec = totalPE/QEdepPE_factor;   
    }
    //
    if (evt) evt->Fill();
    // EDM output
    cd_rec_evt -> setPESum(totalPE);   
    cd_rec_evt -> setPESum_g(totalPE_corr_g);
    cd_rec_evt -> setEnergy(EvisRec); // fRecEvis = Enrec
    cd_rec_evt -> setX(fCCRecX);
    cd_rec_evt -> setY(fCCRecY);
    cd_rec_evt -> setZ(fCCRecZ);
    cd_rec_evt -> setTimeStamp(TimeStamp);
    cd_rec_evt_header -> setCdVertexEvent(cd_rec_evt);
    evt_nav -> addHeader("/Event/Rec/ChargeCenterAlg", cd_rec_evt_header);

    evtID += 1; 
    return true;
}

bool ChargeCenterRec::finalize()
{
    // = close file =
    if (ElecSim_Event) {
        delete ElecSim_Event;
        ElecSim_Event = nullptr;
    }
    if (ElecSim_File) {
        ElecSim_File->Close();
        delete ElecSim_File;
        ElecSim_File = nullptr;
    }
    if (func_file) {
        func_file->Close();
        delete func_file;
        func_file = nullptr;
    }
    if (channelFile2.is_open()) {
        channelFile2.close();
    }
    if (BadChannelFile.is_open()) {
        BadChannelFile.close();
    }
    if (g_graph) {
        delete g_graph;
        g_graph = nullptr;
    }

    return true;
}

// Calculate the charge center weighted by PE
bool ChargeCenterRec::CalChargeCenter(const std::vector<TVector3>& channelPositionVec, bool CalculateInitialP,bool isDNcorrection ,std::string Pattern,bool ifClearBadChannelsPE, bool ifPixelUpdate) {

    TVector3 cc_vec(0, 0, 0);
    double sumPE2 = 0; 
    //==
    // 4. 将坏通道对应数组位置置0
    if (ifClearBadChannelsPE) {
        for (int id : BadChannelIDVec) {
            fChannelHitPE[id] = 0.0;  // 若数组是int类型，改为0
            if (fChannelHitPE[id]!=0) 
            std::cout<<"fChannelHitPE["<<id<<"]: "<< fChannelHitPE[id] <<std::endl;
        }
    }
    //==
    for (int i = 0; i < CHANNELNUM_total; i++) { //calculate the charge center weighted by PE
        int channel_id = i;
        cc_vec += fChannelHitPE[i] * channelPositionVec[channel_id];
        sumPE2 += fChannelHitPE[i];
    }
    totalPE = sumPE2;

//--------------------------------//
    // 聚合计算：每个像素编号的PE和计数, 计算分块像素下的中心值
    BadChannelsTotalPE_Pixel = 0;
    if (ifPixelUpdate) {
        // std::cout<<"ifPixelUpdate: "<<ifPixelUpdate<<std::endl;
        cc_vec = ChargeCenterRec::CalculateChargeCenter_Pixel(channelToPixelVec, fChannelHitPE, pixelPositionsVec,BadChannelIDVec);}
    else {
        cc_vec *= (1.0 / sumPE2);
        cc_vec *= 1.5; // Geometry factor
        //
        double exp_dark_noise = CHANNELNUM_total * dark_noise_prob;
        double cor_factor = sumPE2 / (sumPE2 - exp_dark_noise);
        if (isDNcorrection) cc_vec *= cor_factor; // Dark noise correction
    }
    totalPE_corr = totalPE + BadChannelsTotalPE_Pixel;
//--------------------------------//
    fCCRecX = cc_vec.X();
    fCCRecY = cc_vec.Y();
    fCCRecZ = cc_vec.Z();
    //
    fCCRecR = cc_vec.Mag();
    fCCRecTheta = (cc_vec.Theta()) * 180 / M_PI;
    fCCRecPhi=atan2(fCCRecY,fCCRecX)*180/M_PI;
    fCCRecPhi = fCCRecPhi < 0 ? fCCRecPhi + 360 : fCCRecPhi;
    //
    // ----------- // 正常修正

    double ori_fCCRecR=fCCRecR;

    // ------------------ R 修正 ---------------//
    fCCRecR = calculateNewFccRecR(ori_fCCRecR, ori_fCCRecR, Pattern);
    if (fCCRecR >= 900) {
        fCCRecR = newFccRecrRandom(fCCRecR,QEdepR_ifFccRbeyond900_merge);
    }
    
    fCCRecX = fCCRecR*sin(fCCRecTheta*M_PI/180)*cos(fCCRecPhi*M_PI/180);
    fCCRecY = fCCRecR*sin(fCCRecTheta*M_PI/180)*sin(fCCRecPhi*M_PI/180);
    fCCRecZ = fCCRecR*cos(fCCRecTheta*M_PI/180);
    if (CalculateInitialP) { 
        InitialQEdepPoint = TVector3(fCCRecX, fCCRecY, fCCRecZ);
        return true; 
    }    
    // fill the difference between the reconstructed charge center and the true charge center
    diffPerformanceR = fCCRecR-QEdepR;
    diffPerformanceTheta = fCCRecTheta-QEdepTheta;
    if (fCCRecPhi-QEdepPhi>180){fCCRecPhi=fCCRecPhi-360;}
    if (fCCRecPhi-QEdepPhi<-180){fCCRecPhi=fCCRecPhi+360;}
    diffPerformancePhi = fCCRecPhi-QEdepPhi;

    return true;
}


std::vector<TVector3>  ChargeCenterRec::ReadChannelPositions(const TString& filePath1, const TString& filePath2) {
    std::vector<TVector3> channelPositionVec;

    //
    std::ifstream channelFile1(filePath1.Data());
    if (!channelFile1.is_open()) {
        LogError << "Error: Failed to open file: " << filePath1 << std::endl;
        return channelPositionVec;
    }
    int index = 0;
    double x = 0.0, y = 0.0, z = 0.0, R = 0.0, theta = 0.0, phi = 0.0;
    const double offsetX = -2446.0;
    const double offsetY = -2446.0;
    const double offsetZ = -8212.8;    
    while (channelFile1 >> index >> x >> y >> z >> R >> theta >> phi) {
        TVector3 channelPos;
        channelPos.SetXYZ(x - offsetX, y - offsetY, z - offsetZ);
        channelPositionVec.push_back(channelPos);
    }
    channelFile1.close();

    std::ifstream channelFile2(filePath2.Data());
    if (!channelFile2.is_open()) {
        LogError << "Error: Failed to open file: " << filePath2 << std::endl;
        return channelPositionVec;
    }
    while (channelFile2 >> index >> x >> y >> z >> R >> theta >> phi) {
        TVector3 suppChannelPos;
        suppChannelPos.SetXYZ(x - offsetX, y - offsetY, z - offsetZ);
        channelPositionVec.push_back(suppChannelPos);
    }
    channelFile2.close();

    return channelPositionVec;
} 

double ChargeCenterRec::EnergyRec(double fccRecR, double fCCRecTheta, double totalPE_in, std::string ParameterSelection) {

    double g=0;
    double x = fccRecR;
    double y = fCCRecTheta;
    if (ParameterSelection=="map"||ParameterSelection=="Map"){
        g= interpolate2D(g_graph,x,y);               
    }else{
        g=FitFuncinterpolate2D(x,y,ParameterSelection); 
    }

    // Calculate raw_PE (for simplification, using a placeholder value for demonstration)
    double raw_PE = totalPE_in / g; 
    totalPE_corr_g = raw_PE;
    // Calculate EdepVis_rec
    double EdepVis_rec = raw_PE / QEdepPE_factor; 

    return EdepVis_rec;
}

std::vector<int>  ChargeCenterRec::ReadBadChannelID(const TString& filePath1) {
    std::vector<int> BadChannelIDVec;

    //
    std::ifstream channelFile1(filePath1.Data());
    if (!channelFile1.is_open()) {
        LogError << "Error: Failed to open file: " << filePath1 << std::endl;
        return BadChannelIDVec;
    }
    int ChannelID = 0;
    double x = 0.0, y = 0.0, z = 0.0, R = 0.0, theta = 0.0, phi = 0.0;
    while (channelFile1 >> ChannelID >> x >> y >> z >> R >> theta >> phi) {

        BadChannelIDVec.push_back(ChannelID);
    }
    channelFile1.close();

    return BadChannelIDVec;
} 

std::vector<int> ChargeCenterRec::ReadchannelToPixelVec(const TString& filePath1, int channelNum) {
    std::vector<int> channelPixelLabel_vec(channelNum, -1);

    std::ifstream fin(filePath1.Data());
    if (!fin) {
        LogError << "无法打开文件 " << filePath1 << std::endl;
        return channelPixelLabel_vec; // 返回全-1，表示失败
    }
    std::string line;
    // 跳过表头
    std::getline(fin, line);

    // 解析每行
    while (std::getline(fin, line)) {
        std::stringstream ss(line);
        std::string token;
        int channelID = -1, label = -1;
        float x, y, z;

        // channelID
        std::getline(ss, token, ',');
        if(token.empty()) continue;
        channelID = std::stoi(token);
        // x
        std::getline(ss, token, ',');
        // y
        std::getline(ss, token, ',');
        // z
        std::getline(ss, token, ',');
        // label
        std::getline(ss, token, ',');
        if(token.empty()) continue;
        label = std::stoi(token);

        if (channelID >= 0 && channelID < channelNum) {
            channelPixelLabel_vec[channelID] = label;
        } else {
            LogError << "channelID超出范围: " << channelID << std::endl;
        }
    }

    fin.close();
    return channelPixelLabel_vec;
}

TVector3 ChargeCenterRec::CalculateChargeCenter_Pixel(
    const std::vector<int>& fchannelToPixelVec, 
    const double* fChannelPE,
    const std::vector<TVector3>& fpixelPositionsVec,
    const std::vector<int>& fBadChannelIDVec
)
{
    std::unordered_set<int> badChannelSet(fBadChannelIDVec.begin(), fBadChannelIDVec.end());
    std::unordered_map<int, double> pixelPeSum;
    std::unordered_map<int, int> pixelCount;

    int nChannels = fchannelToPixelVec.size();
    // std::cout << "nChannels: " << nChannels << std::endl;
    // std::cout << "Size of fchannelToPixelVec: " << fchannelToPixelVec.size() << std::endl;
    for (int i = 0; i < nChannels; ++i) {
        if (badChannelSet.count(i)) { continue; }
        int label = fchannelToPixelVec[i];
        if (label == -1) {
            continue; // 跳过无效像素编号
        }
        pixelPeSum[label] += fChannelPE[i];
        pixelCount[label] += 1;
    }

    std::unordered_map<int, double> pixelPeAvg;
    for (const auto& kv : pixelPeSum) {
        int label = kv.first;
        double sumPe = kv.second;
        int count = pixelCount[label];
        if (count > 0) {
            pixelPeAvg[label] = sumPe / count;
        }
    }
//
    // 3. 统计坏通道对应的PE总和（用对应像素平均PE填充）
    double badChannelsTotalPE = 0.0;
    for (int i = 0; i < nChannels; ++i) {
        if (badChannelSet.count(i)) {
            int label = fchannelToPixelVec[i];
            if (label == -1) {
                continue; // 无效像素，坏通道PE视为0
            }
            auto it = pixelPeAvg.find(label);
            if (it != pixelPeAvg.end()) {
                badChannelsTotalPE += it->second;
            } else {
                // 该像素没有平均PE，视为0
            }
        }
    }

    //
    BadChannelsTotalPE_Pixel=badChannelsTotalPE;
//
    TVector3 cc_vec_agg(0.0, 0.0, 0.0);
    double sumPE2_agg = 0.0;
    for (const auto& kv : pixelPeAvg) {
        int label = kv.first;
        double avgPe = kv.second;

        // 这里用vector直接通过label访问，确保label有效
        if (label < 0 || label >= (int)fpixelPositionsVec.size()) {
            // 
            std::cout << "The label is out of range: " << label << std::endl;
            continue;
        }

        cc_vec_agg += avgPe * fpixelPositionsVec[label];
        sumPE2_agg += avgPe;
    }

    if (sumPE2_agg > 0) {
        cc_vec_agg *= (1.0 / sumPE2_agg);
    } else {
        std::cout <<"eventID: "<< evtID <<" totalPE: "<<sumPE2_agg<<std::endl;
        std::cout << "ERROR: sumPE2_agg is zero, set cc_vec_agg to zero" << std::endl;
        cc_vec_agg = TVector3(0.0, 0.0, 0.0);
    }
    cc_vec_agg *= 1.5;
    return cc_vec_agg;
}

std::vector<TVector3> ChargeCenterRec:: ReadPixelPositions(const TString& filePath1) {
    std::vector<TVector3> pixelPositionVec;

    //
    std::ifstream PixelFile1(filePath1.Data());
    if (!PixelFile1.is_open()) {
        LogError << "Error: Failed to open file: " << filePath1 << std::endl;
        return pixelPositionVec;
    }
    int PixelID = 0;
    double x = 0.0, y = 0.0, z = 0.0;
    while (PixelFile1 >> PixelID >> x >> y >> z) {

        TVector3 pixelPos;
        pixelPos.SetXYZ(x, y, z);
        pixelPositionVec.push_back(pixelPos);
    }
    PixelFile1.close();

    return pixelPositionVec;
} 

std::map<int, double> ChargeCenterRec::ReadChannelDCR(const std::string& filename) {
    std::map<int, double> channelDCRMap;
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        LogError << "Error: cannot open file " << filename << std::endl;
        return channelDCRMap;
    }

    std::string line;

    // 跳过第一行表头
    if (!std::getline(infile, line)) {
        LogError << "Error: file is empty: " << filename << std::endl;
        return channelDCRMap;
    }

    // 逐行读取数据
    while (std::getline(infile, line)) {
        if (line.empty()) continue;

        std::istringstream ss(line);
        std::string channelStr, dcrStr;

        if (!std::getline(ss, channelStr, ',')) continue;
        if (!std::getline(ss, dcrStr, ',')) continue;

        try {
            int channelID = std::stoi(channelStr);
            double dcr = std::stod(dcrStr);
            channelDCRMap[channelID] = dcr;
        } catch (const std::exception& e) {
            LogError << "Warning: skipping invalid line: " << line << std::endl;
            continue;
        }
    }

    infile.close();
    return channelDCRMap;
}