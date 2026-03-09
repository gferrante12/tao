#include "RecQMLEAlg/QMLERec.h"
#include "RecQMLEAlg/ChargeTemplate.h"
#include "RecQMLEAlg/Functions.h"
#include "Math/Minimizer.h"
#include "Math/GSLMinimizer.h"
#include "Math/Functor.h"
#include "Math/Factory.h"
#include "Minuit2/FCNBase.h"
#include "TVector3.h"
#include "TMath.h"
#include "TF1.h"
#include "TGraph2D.h"
#include "TCanvas.h"
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


#include "SniperKernel/AlgFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/SniperLog.h"
#include "RootWriter/RootWriter.h"
#include "BufferMemMgr/IDataMemMgr.h"
#include "EvtNavigator/NavBuffer.h"
#include "TAOGeometry/SimGeomSvc.h"

#include <TGeoManager.h>

#include <boost/python.hpp>
#include <vector>
#include <iostream>
#include <string>
#include <fstream>

DECLARE_ALGORITHM(QMLERec);

QMLERec::QMLERec(const std::string& name)
    : AlgBase(name),evt(0)
{
    CD_radius = 900;

    declProp("ChargeTemplateFile",charge_template_file = "charge_template");
    declProp("CCFactor",cc_factor = 0.66);
    declProp("QSPE",QSPE_factor = 3100);
    declProp("nonuniformity",nonuniformity_file = "uniformityMap.root");   
    declProp("useTrueVertex", useTrueVertex);
    declProp("trueVertexFile", trueVertexFile);
}

QMLERec::~QMLERec()
{
}

bool QMLERec::initialize()
{   
    // std::cout << "enable Charge Info: " << enableChargeInfo << std::endl;
    std::cout << "Charge center alg. factor : "<<cc_factor<<std::endl;
    std::cout << "****************e- Template File: e-_" << std::string(charge_template_file) <<std::endl;
    charge_template = new ChargeTemplate("e-_" + std::string(charge_template_file));
    std::cout << "****************Ge68 Template File: Ge68_" << std::string(charge_template_file) <<std::endl;
    charge_template_ge68 = new ChargeTemplate("Ge68_" + std::string(charge_template_file));
    std::cout << "**************** useTrueVertex: " << std::to_string(useTrueVertex) << ", File Path: " <<  trueVertexFile << std::endl;
    if(useTrueVertex){
        vertexFile = TFile::Open(trueVertexFile.c_str());
        vertexTree = (TTree*)vertexFile->Get("Event/Sim/SimEvt");
        vertexTree->SetBranchAddress("SimEvt", &SimEvt);
    }
    // =================================================
    std::string root_dir = getenv("RECQMLEALGROOT");
    std::string uniformity_filename = root_dir + "/input/" + nonuniformity_file;
    std::cout << "*************** Uniformity Map: " << uniformity_filename << std::endl;
    nonuniformityFile = new TFile(uniformity_filename.c_str(), "READ");
    nonuniformity = (TH2F*)nonuniformityFile->Get("uniformity");
    // =================================================
    
    // = access the geometry =
    SniperPtr<SimGeomSvc> simgeom_svc(getParent(), "SimGeomSvc");
    // == check exist or not ==
    if (simgeom_svc.invalid()) {
        LogError << "can't find SimGeomSvc" << std::endl;
        return false;
    }
    // == get Sipm & channel parameter
    m_cdGeom = simgeom_svc->getCdGeom();
    for(int i = 0;i < CHANNELNUM; i++)
    {
        m_SiPMGeom = m_cdGeom->FindSiPM(i); //get SIPM object
        double m_SiPMTheta = m_SiPMGeom->getChannelTheta(i);   //get SiPM's theta, unit: rad
        double m_SiPMPhi = m_SiPMGeom->getChannelPhi(i);   //get SiPM's Phi, unit: rad
        TVector3 n_pos = TVector3(
                1*sin(m_SiPMTheta)*cos(m_SiPMPhi),
                1*sin(m_SiPMTheta)*sin(m_SiPMPhi),
                1*cos(m_SiPMTheta)
                );
        channel_vec[i] = SiPMRadius * n_pos;    
        channel_theta[i] = m_SiPMTheta;
        channel_phi[i] = m_SiPMPhi;   
    }
    LogInfo << "Total SiPM & Channel: " << SIPMNUM << '\t' <<CHANNELNUM<<std::endl;

    // // == get the ROOT TAOGeometry Manager ==
    // TGeoManager* geom = simgeom_svc->geom();
    // if (geom) {
    //     LogInfo << "get geometry geom: " << geom << std::endl;
    // }

    // = get RootWriter =
    SniperPtr<RootWriter> rootwriter(getParent(), "RootWriter");
    if (rootwriter.invalid()) {
        LogError << "Can't Find RootWriter. "
                 << std::endl;
        return false;
    }

////////////////////////////////////////////
fChannelID.clear();
fChannelHitTime.clear();
fChannelExpPEVec.clear();
fChannelHitPEVec.clear();
////////////////////////////////////////////

#ifndef SNIPER_VERSION_2
    evt = rootwriter->bookTree("RECEVT/RecEvt", "user defined data");
#else
    evt = rootwriter->bookTree(*getParent(), "RECEVT/RecEvt", "user defined data");
#endif
    evt->Branch("evtID", &evtID, "evtID/I");
    evt->Branch("fChannelHit", fChannelHit,"fChannelHit[8048]/f");
    evt->Branch("fChannelTotHit", &fChannelTotHit, "fChannelTotHit/f");
    evt->Branch("fChannelExpPE", fChannelExpPE, "fChannelExpPE[8048]/f");   
    evt->Branch("fChannelID", &fChannelID);                               
    evt->Branch("fChannelHitTime", &fChannelHitTime);   
    evt->Branch("fExpPE", &fExpPE, "fExpPE/f"); // total expected PE
    evt->Branch("fRecEvis", &fRecEvis, "fRecEvis/f");   //  reconstructed energy by Charge Template method
    evt->Branch("fRecX", &fRecX, "fRecX/f");
    evt->Branch("fRecY", &fRecY, "fRecY/f");
    evt->Branch("fRecZ", &fRecZ, "fRecZ/f");
    evt->Branch("fRecR", &fRecR, "fRecR/f");
    evt->Branch("fRecTheta", &fRecTheta, "fRecTheta/f");
    evt->Branch("fRecPhi", &fRecPhi, "fRecPhi/f");
    evt->Branch("fCCRecEvis", &fCCRecEvis, "fCCRecEvis/f");   //  reconstructed energy by Charge Center method
    evt->Branch("fCCRecX", &fCCRecX, "fCCRecX/f");
    evt->Branch("fCCRecY", &fCCRecY, "fCCRecY/f");
    evt->Branch("fCCRecZ", &fCCRecZ, "fCCRecZ/f");
    evt->Branch("fCCRecR", &fCCRecR, "fCCRecR/f");
    evt->Branch("fCCRecR2", &fCCRecR2, "fCCRecR2/f");
    evt->Branch("fCCRecTheta", &fCCRecTheta, "fCCRecTheta/f");
    evt->Branch("fCCRecPhi", &fCCRecPhi, "fCCRecPhi/f");
    evt->Branch("fChi2", &fChi2, "fChi2/f");
    evt->Branch("fEdm", &fEdm, "fEdm/f");

    // create minimizer
    vtxllfcn = new VertexRecLikelihoodFCN(this);
    vtxllminimizer_migrad = ROOT::Math::Factory::CreateMinimizer("Minuit2","Migrad");
    vtxllminimizer = ROOT::Math::Factory::CreateMinimizer("Minuit2","Simplex");
    return true;
}

bool QMLERec::execute()
{

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

    Tao::CdVertexRecHeader* cd_rec_evt_header = NULL;
    Tao::CdVertexRecEvt* cd_rec_evt = NULL;
    if(! cd_rec_evt_header) {
        cd_rec_evt_header = new Tao::CdVertexRecHeader();
        cd_rec_evt = new Tao::CdVertexRecEvt();
    }

        Tao::CdCalibHeader* cd_calib_hdr = dynamic_cast<Tao::CdCalibHeader*>(evt_nav->getHeader("/Event/Calib"));
        if (not cd_calib_hdr) {
            return 0;
        }
        if (!cd_calib_hdr->hasEvent()) {
            std::cout<<"no data is found, skip this event."<<std::endl;
            return true;
        }
        
        // == get event ==
        Tao::CdCalibEvt* calib_event = dynamic_cast<Tao::CdCalibEvt*>(cd_calib_hdr->event());
        evtID += 1;
        std::vector<Tao::CdCalibChannel> channels = calib_event -> GetCalibChannels();
        for (int i = 0; i < channels.size(); i++) {
            int id = channels.at(i).CalibgetChannelID();
            std::vector<float> PEs = channels.at(i).CalibgetPEs();  // Get Charge from single channel, unit: p.e. 
            float tot_PEs = 0;
            for (int j = 0; j < PEs.size(); j++) {
                tot_PEs += PEs.at(j);
            }

            // fChannelHit[id] = int(round(tot_PEs));  //   四舍五入后将电荷数视为PE数，因为此时输入的电荷信息已经换算为了p.e.为单位
            // fChannelTotHit += int(round(tot_PEs));  //   光电子数，unit: 个
            fChannelHit[id] = tot_PEs;  //   
            fChannelTotHit += tot_PEs;  //   

            fChannelID.push_back(id);
            fChannelHitTime.push_back(channels.at(i).CalibgetTDCs()[0]);
            fChannelHitPEVec.push_back(tot_PEs);
        }

    if(useTrueVertex){
        vertexTree->GetEntry(evtID);
    }
    
    std::cout << "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv Event[" << evtID << "] vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv" << std::endl;

    // charge center reconstruction
    CalChargeCenter();

    // start reconstruction
    VertexMinimize();
    
    // fill the event.
    evt->Fill();

    // EDM output
    cd_rec_evt -> setPESum(fChannelTotHit);   
    cd_rec_evt -> setEnergy(fRecEvis);
    cd_rec_evt -> setEprec(0);
    cd_rec_evt -> setX(fRecX);
    cd_rec_evt -> setY(fRecY);
    cd_rec_evt -> setZ(fRecZ);
    cd_rec_evt -> setPx(0);
    cd_rec_evt -> setPy(0);
    cd_rec_evt -> setPz(0);
    cd_rec_evt -> setChisq(0);
    ////////
    // cd_rec_evt -> setChannelId(fChannelID);
    // cd_rec_evt -> setChannelHitTime(fChannelHitTime);
    // cd_rec_evt -> setChannelExpPE(fChannelExpPEVec);
    // cd_rec_evt -> setChannelHitPE(fChannelHitPEVec);
    ////////
    cd_rec_evt -> setEnergyQuality(0);
    cd_rec_evt -> setPositionQuality(0); 
    cd_rec_evt_header -> setCdVertexEvent(cd_rec_evt);
    // evt_nav -> addHeader("/Event/Rec/ChargeTemplate", cd_rec_evt_header);
    evt_nav -> addHeader("/Event/Rec/QMLE", cd_rec_evt_header);

    // update here
    update();
    return true;
}

bool QMLERec::finalize()
{
    if(useTrueVertex){
    vertexFile->Close();
    }
    charge_template->finalize();
    
    return true;
}

float QMLERec::QMLE(
    double Evis,double vr,double vtheta,double vphi)    // vtheta=(0,PI)
{   
    m_Likelihood = 0.;
    TF1* GausFunc = new TF1("mGaus", "gaus");
    float exp_dark_noise = dark_noise_prob;         // dark noise
    TVector3 v_vec = TVector3(0, 0 ,1);
    v_vec.SetMagThetaPhi(vr,vtheta,vphi);           // Convert spherical coordinate system to Cartesian coordinate system
    for(int i = 0; i < CHANNELNUM; i++)
    {   
        float Pro_Qi = 0.;
        int id = i;
        float angle = v_vec.Angle(channel_vec[id]); // The angle between vertex and channel, range in（0, pi）
        float exp_hit = CalExpChargeHit(vr, angle*180/TMath::Pi(), Evis);
        exp_hit += dark_noise_prob;
        if(exp_hit > saturation){
            exp_hit = saturation;
        }
        
        //////////////
        float meas_hit = fChannelHit[i];    // measured charge on channel
        
        if(meas_hit < QThreshold){ // channel does not get charge
            float Poisson0 = exp(-exp_hit);
            double paraTemp[3] = {1.0/sqrt(2*TMath::Pi())/S1, Q1, S1};
            GausFunc->SetParameters(paraTemp);      // SPES obeys N~(Q1,S1)
            float probtemp = GausFunc->Integral(0, QThreshold);
         
            Pro_Qi = Poisson0 + exp_hit * Poisson0 * probtemp; 
            
        } else {    // channel has charge
            float Poisson = exp(-exp_hit);
            float proTemp = 0.;
            float proTemp_last = 0.;
            for(int k = 1; k < 1000; k++)   // 
            {   
                proTemp = TMath::Gaus(meas_hit, k*Q1, sqrt(k)*S1)/sqrt(2.*TMath::Pi()*k*S1*S1);   //multi-PES obeys N~(kQ1,sqrt(k)*S1) 
                if(proTemp<0.0) {proTemp = probPrcs/10.;}
                if(proTemp < probPrcs && proTemp_last > probPrcs) break;
                proTemp_last = proTemp;

                Poisson = Poisson * exp_hit / float(k);
                Pro_Qi += Poisson*proTemp;
            }       
        }

        // Likelihood
        if(Pro_Qi<1e-16) Pro_Qi = 1e-16;
        m_Likelihood = m_Likelihood - 2. * log(Pro_Qi);     
    }    

    return m_Likelihood;
}



bool QMLERec::update()
{
    m_Likelihood = 0.;
    fChannelTotHit = 0.;
    for(int i=0; i < CHANNELNUM; i++) {
        fChannelHit[i] = 0.;
    }
    fChannelID.clear();
    fChannelHitTime.clear();
    fChannelExpPEVec.clear();
    fChannelHitPEVec.clear();
    return true;
}

bool QMLERec::VertexMinimize()
{

    ROOT::Math::Functor vtxllf(*vtxllfcn,4);

    vtxllminimizer_migrad->SetFunction(vtxllf);
    vtxllminimizer_migrad->SetMaxFunctionCalls(1e5);
    vtxllminimizer_migrad->SetMaxIterations(1e5);
    vtxllminimizer_migrad->SetTolerance(1.e-3);
    vtxllminimizer_migrad->SetStrategy(1);
    vtxllminimizer_migrad->SetPrintLevel(1);
    
    // Calculate initialize value
    float fCCRadius = fCCRecR;
    if (fCCRadius > 900)
    {
        fCCRadius = 890;
    } 
    
    float exp_hit_init = fChannelTotHit;
    exp_hit_init -= CHANNELNUM * dark_noise_prob;

    int goodness = 0;
    // use migrad to minimize
    vtxllminimizer_migrad->SetLimitedVariable(0, "Evis", exp_hit_init/3650, 0.2, 0, 10);
    if(!useTrueVertex){
        vtxllminimizer_migrad->SetVariable(1,"radius",fCCRecR, 10);
        vtxllminimizer_migrad->SetFixedVariable(2,"theta",fCCRecTheta);
        vtxllminimizer_migrad->SetFixedVariable(3,"phi",fCCRecPhi);
    } else{
        Tao::SimTrack* mPrimaryTracks = SimEvt->getTracksVec()[0];
        float QedepR = sqrt( pow(mPrimaryTracks->getQEdepX(), 2) + pow(mPrimaryTracks->getQEdepY(), 2) + pow(mPrimaryTracks->getQEdepZ(), 2) );
        vtxllminimizer_migrad->SetFixedVariable(1,"radius", QedepR);
        vtxllminimizer_migrad->SetFixedVariable(2,"theta", acos( mPrimaryTracks->getQEdepZ() / QedepR ));
        vtxllminimizer_migrad->SetFixedVariable(3,"phi", atan2( mPrimaryTracks->getQEdepY() , mPrimaryTracks->getQEdepX() ));
    }
    
    goodness = vtxllminimizer_migrad->Minimize();
    std::cout << "Acc. Vertex Minimize :: Goodness = " << goodness << std::endl;
    const double *xs = vtxllminimizer_migrad->X();

    TVector3 v_rec(0,0,1);
    v_rec.SetMagThetaPhi(xs[1],xs[2],xs[3]);
    fRecEvis = xs[0];
    fRecX    = v_rec.X();
    fRecY    = v_rec.Y();
    fRecZ    = v_rec.Z();
    fRecR    = xs[1];
    fRecTheta    = xs[2];
    fRecPhi    = xs[3];
    std::cout << "QMLE Evis = " << fRecEvis << " (R, Theta, Phi) = (" << fRecR << ", " << fRecTheta << ", " << fRecPhi << ")"<<std::endl;
    fChi2    = vtxllminimizer_migrad->MinValue(); 
    fEdm     = vtxllminimizer_migrad->Edm();

    ///////////////////////////////////////
    float exp_dark_noise = dark_noise_prob;
    // calculate some value that is needed.
    TVector3 v_vec = TVector3(0, 0 ,1);
    v_vec.SetMagThetaPhi(fRecR,fRecTheta,fRecPhi);
    fExpPE = 0.;
    float angle;
    float exp_hit;
    for(int i=0; i < CHANNELNUM; i++)
    {
        angle = v_vec.Angle(channel_vec[i]);   
        exp_hit = CalExpChargeHit(fRecR, angle*180/PI, fRecEvis);
        exp_hit += dark_noise_prob;
        if(exp_hit > saturation){
            exp_hit = saturation;
        }
        fExpPE += exp_hit;
        fChannelExpPE[i] = exp_hit;
        fChannelExpPEVec.push_back(exp_hit);
        
        // std::cout << "channel["<< i <<"] measured Charge: " << fChannelHit[i] << "\texpected nPE: " << exp_hit << "\tPro_Q: " << Pro_Qi_arr[i] <<std::endl;
    }
    /////////////////////////////////////////////////////////////////////////////////////////////////
    // if(fRecEvis<0.883){
    //     energy_Ge = fRecEvis; energy_Ek =0.;
    // }else{
    //     energy_Ge = 0.883; energy_Ek=fRecEvis-0.883;
    // }
    return true;
}

bool QMLERec::CalChargeCenter()
{
    TVector3 cc_vec(0,0,0);
    for(int i=0; i < CHANNELNUM; i++){
        int channel_id = i;
        cc_vec += fChannelHit[i] * channel_vec[channel_id];
    }
    cc_vec *= (1.0/fChannelTotHit);
    float exp_dark_noise = CHANNELNUM * dark_noise_prob;
    float cor_factor = fChannelTotHit/(fChannelTotHit - exp_dark_noise);
    cc_vec *= cor_factor / cc_factor;
    fCCRecX = cc_vec.X();
    fCCRecY = cc_vec.Y();
    fCCRecZ = cc_vec.Z();
    fCCRecR = cc_vec.Mag();
    fCCRecR2 = (sqrt(cc_vec.Mag()+290.62998)-17.41149)/0.013784;
    fCCRecTheta = cc_vec.Theta();
    fCCRecPhi = cc_vec.Phi();
    //////
    float rawEnergy = fChannelTotHit / Y0;      
    Double_t nonuniformityValue = nonuniformity->Interpolate(fCCRecR, fCCRecTheta*180/TMath::Pi());
    float uniformEnergy = rawEnergy / nonuniformityValue;   // 非均匀性修正
    float Enrec = uniformEnergy * 1; // 非线性修正

    fCCRecEvis = Enrec;
    /////
    if(useTrueVertex){
        Tao::SimTrack* mPrimaryTracks = SimEvt->getTracksVec()[0];
        float QedepR = sqrt( pow(mPrimaryTracks->getQEdepX(), 2) + pow(mPrimaryTracks->getQEdepY(), 2) + pow(mPrimaryTracks->getQEdepZ(), 2) );
        std::cout << "************* True Vertex(R, Theta, Phi) = (" << QedepR << ", " << acos( mPrimaryTracks->getQEdepZ() / QedepR ) << ", " << atan2( mPrimaryTracks->getQEdepY() , mPrimaryTracks->getQEdepX() ) << ")" <<std::endl;
    }
    std::cout << "************* Charge Center: "  << "CCEvis = " << fCCRecEvis <<",\tCC vertex(R, Theta, Phi) = "<< "("<<fCCRecR<<", "<< fCCRecTheta <<", "<< fCCRecPhi <<")"<<std::endl;
    
} 
 
double QMLERec::LogPoisson(double obj,double exp_n)
{
    // likelihood ratio
    double p=2*(exp_n-obj);
    if(obj>0.01){
        p+=2*obj*TMath::Log(obj/exp_n);
    }
    return p;
}

float QMLERec::CalExpChargeHit(float radius, float theta, float Evis) // theta unit: 角度制 顶点与SiPM通道之间的夹角
{
    float exp_hit = charge_template -> CalExpChargeHit(radius, theta);  
    float exp_hit_ge68 = charge_template_ge68 -> CalExpChargeHit(radius, theta);

    // float GeEvis = 3458. / 4200.;   // nPE of Ge68 at detector center = 3458
    // float EkEvis = 3830. / 4200.;   // nPE of e- at detector center = 3830
    float GeEvis = 0.886;   // mean value of Qedep from detSim
    float EkEvis = 0.963;   // mean value of Qedep from detSim

    // 设Ge68的可见能量大小为GeEvis, 动能部分的可见能量为Evis-GeEvis
    if(Evis>GeEvis){
        m_average_PE = ( exp_hit_ge68 + ( Evis - GeEvis ) * exp_hit / EkEvis);
    }else {
        m_average_PE = Evis * exp_hit_ge68 / GeEvis;
    }
    // m_average_PE 直接从template中计算得到。template应该是通过刻度源，消除掉PDE和暗噪声后得到的
    m_expected_hit = m_average_PE*PDE/ESF;

    return m_expected_hit;   
}
