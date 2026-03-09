#include "RecChargeTemplateAlg/ChargeTemplateRec.h"
#include "RecChargeTemplateAlg/ChargeTemplate.h"
#include "RecChargeTemplateAlg/Functions.h"
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

DECLARE_ALGORITHM(ChargeTemplateRec);

ChargeTemplateRec::ChargeTemplateRec(const std::string& name)
    : AlgBase(name),evt(0)
{
    CD_radius = 900;

    declProp("ChargeTemplateFile",charge_template_file = "charge_template");
    declProp("CCFactor",cc_factor = 0.7);
    declProp("QSPE",QSPE_factor = 3100);
}

ChargeTemplateRec::~ChargeTemplateRec()
{
}

bool ChargeTemplateRec::initialize()
{
    std::cout << "Charge center alg. factor : "<<cc_factor<<std::endl;

    charge_template = new ChargeTemplate("Alpha_" + std::string(charge_template_file));
    charge_template_ge68 = new ChargeTemplate("Ge68_" + std::string(charge_template_file));

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
        TVector3 center = m_SiPMGeom->getCenter();
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
        channel_n_vec[i] = n_pos;
        channel_n_theta[i] = m_SiPMTheta;
        channel_n_phi[i] = m_SiPMPhi;      

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

#ifndef SNIPER_VERSION_2
    evt = rootwriter->bookTree("RECEVT/RecEvt", "user defined data");
#else
    evt = rootwriter->bookTree(*getParent(), "RECEVT/RecEvt", "user defined data");
#endif
    evt->Branch("evtID", &evtID, "evtID/I");
    // evt->Branch("fChannelHit", &fChannelHit);
    evt->Branch("fChannelTotHit", &fChannelTotHit, "fChannelTotHit/I");
    evt->Branch("fRecNHit", &fRecNHit, "fRecNHit/f");
    evt->Branch("fRecX", &fRecX, "fRecX/f");
    evt->Branch("fRecY", &fRecY, "fRecY/f");
    evt->Branch("fRecZ", &fRecZ, "fRecZ/f");
    evt->Branch("fRecR", &fRecR, "fRecR/f");
    evt->Branch("fRecTheta", &fRecTheta, "fRecTheta/f");
    evt->Branch("fRecPhi", &fRecPhi, "fRecPhi/f");
    evt->Branch("fRecGammaTempRatio", &fRecGammaTempRatio, "fRecGammaTempRatio/f");
    evt->Branch("fCCRecX", &fCCRecX, "fCCRecX/f");
    evt->Branch("fCCRecY", &fCCRecY, "fCCRecY/f");
    evt->Branch("fCCRecZ", &fCCRecZ, "fCCRecZ/f");
    evt->Branch("fCCRecR", &fCCRecR, "fCCRecR/f");
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

bool ChargeTemplateRec::execute()
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

    Tao::CdCalibHeader* cd_calib_hdr = dynamic_cast<Tao::CdCalibHeader*>(evt_nav->getHeader("/Event/Calib"));
    if (not cd_calib_hdr) {
        return 0;
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

    // == get event ==
    Tao::CdCalibEvt* calib_event = dynamic_cast<Tao::CdCalibEvt*>(cd_calib_hdr->event());
    evtID += 1;
    std::vector<Tao::CdCalibChannel> channels = calib_event -> GetCalibChannels();
    for (int i = 0; i < channels.size(); i++) {
        int id = channels.at(i).CalibgetChannelID();
        std::vector<float> PEs = channels.at(i).CalibgetPEs();  
        float tot_PEs = 0;
        for (int j = 0; j < PEs.size(); j++) {
            tot_PEs += PEs.at(j);
        }
        fChannelHit[id] = int(round(tot_PEs));
        fChannelTotHit += int(round(tot_PEs));
    }

    // charge center reconstruction
    CalChargeCenter();

    // start reconstruction
    VertexMinimize();
    
    // fill the event.
    evt->Fill();

    // EDM output
    cd_rec_evt -> setPESum(fChannelTotHit);   
    cd_rec_evt -> setEnergy(0);;
    cd_rec_evt -> setEprec(0);
    cd_rec_evt -> setX(fRecX);
    cd_rec_evt -> setY(fRecY);
    cd_rec_evt -> setZ(fRecZ);
    cd_rec_evt -> setPx(0);
    cd_rec_evt -> setPy(0);
    cd_rec_evt -> setPz(0);
    cd_rec_evt -> setChisq(fChi2);
    cd_rec_evt -> setEnergyQuality(0);
    cd_rec_evt -> setPositionQuality(0); 
    cd_rec_evt_header -> setCdVertexEvent(cd_rec_evt);
    evt_nav -> addHeader("/Event/Rec/ChargeTemplate", cd_rec_evt_header);

    //update here
    update();
    return true;
}

bool ChargeTemplateRec::finalize()
{
    charge_template->finalize();
    return true;
}

double ChargeTemplateRec::Chi2(
        double nhit,double vr,double vtheta,double vphi,double alpha_ge68)
{
    float total_chi2 = 0;
    float exp_dark_noise = CHANNELNUM * dark_noise_prob;
    // calculate some value that is needed.
    TVector3 v_vec = TVector3(0, 0 ,1);
    v_vec.SetMagThetaPhi(vr,vtheta,vphi);
    
    for(int i=0; i < CHANNELNUM; i++)
    {
        int id = i;
        float angle = v_vec.Angle(channel_vec[id]);
        float exp_hit = CalExpChargeHit(vr, angle*180/PI, nhit, alpha_ge68);
        exp_hit += dark_noise_prob;
        if(exp_hit > saturation){
            exp_hit = saturation;
        }
        total_chi2 += LogPoisson(fChannelHit[i],exp_hit);
    }
    return total_chi2;
}

bool ChargeTemplateRec::update()
{
    fChannelTotHit = 0;
    for(int i=0; i < CHANNELNUM; i++) {
        fChannelHit[i] = 0;
    }
    return true;
}

bool ChargeTemplateRec::VertexMinimize()
{

    ROOT::Math::Functor vtxllf(*vtxllfcn,5);
    vtxllminimizer->SetFunction(vtxllf);
    vtxllminimizer->SetMaxFunctionCalls(1e4);
    vtxllminimizer->SetMaxIterations(1e4);
    vtxllminimizer->SetTolerance(1.e-1);
    vtxllminimizer->SetStrategy(1);
    vtxllminimizer->SetPrintLevel(1);

    vtxllminimizer_migrad->SetFunction(vtxllf);
    vtxllminimizer_migrad->SetMaxFunctionCalls(1e4);
    vtxllminimizer_migrad->SetMaxIterations(1e4);
    vtxllminimizer_migrad->SetTolerance(1.e-3);
    vtxllminimizer_migrad->SetStrategy(1);
    vtxllminimizer_migrad->SetPrintLevel(1);
    
    // Calculate initialize value
    float fCCRadius = fCCRecR;
    while (fCCRadius > 900)
    {
        fCCRadius = 890;
    } 
    
    float exp_hit_init = fChannelTotHit;
    exp_hit_init -= CHANNELNUM * dark_noise_prob;
    fRecGammaTempRatio = gamma_tmp_ratio[1] * 0.3;
    // fRecGammaTempRatio = 1;
    // CorrectVertex(exp_hit_init, fCCRadius, fCCRecTheta, fCCRecPhi, fRecGammaTempRatio);

    int goodness = 0;
    // use migrad to minimize again
    vtxllminimizer_migrad->SetVariable(0,"hits",exp_hit_init,1);
    vtxllminimizer_migrad->SetVariable(1,"radius",fCCRadius,0.3);
    vtxllminimizer_migrad->SetFixedVariable(2,"theta",fCCRecTheta);
    vtxllminimizer_migrad->SetFixedVariable(3,"phi",fCCRecPhi);
    // vtxllminimizer_migrad->SetFixedVariable(4,"alpha_ge68",fRecGammaTempRatio);
    // vtxllminimizer_migrad->SetVariable(4,"alpha_ge68",fRecGammaTempRatio,0.02);
    vtxllminimizer_migrad->SetLimitedVariable(4,"alpha_ge68", fRecGammaTempRatio, 0.02, 0, 1);
    goodness = vtxllminimizer_migrad->Minimize();
    std::cout << "Acc. Vertex Minimize :: Goodness = " << goodness << std::endl;
    const double *xs = vtxllminimizer_migrad->X();

    TVector3 v_rec(0,0,1);
    v_rec.SetMagThetaPhi(xs[1],xs[2],xs[3]);
    fRecNHit = xs[0];
    fRecX    = v_rec.X();
    fRecY    = v_rec.Y();
    fRecZ    = v_rec.Z();
    fRecR    = xs[1];
    fRecTheta    = xs[2];
    fRecPhi    = xs[3];
    fRecGammaTempRatio = xs[4];
    std::cout << "Migrad : (R, Hit, Gamma_Alpha)" << fRecR << "," << fRecNHit << "," << fRecGammaTempRatio << std::endl; 
    fChi2    = vtxllminimizer_migrad->MinValue(); 
    fEdm     = vtxllminimizer_migrad->Edm();
    return true;
}

void ChargeTemplateRec::CorrectVertex(float &hits, float &r, float &theta, float &phi, float &ge68_alpha)
{
    int max_step = 300;
    float grad_delta_param = 0.01;
    float lr = 2;
    float new_r = r;
    float new_hits = hits;
    float new_ge68_alpha = ge68_alpha;
    float chi2 = Chi2(new_hits, new_r, theta, phi, new_ge68_alpha); 
    std::cout << "Start (R, Hits) = (" << new_r << "," << new_hits <<"," << new_ge68_alpha <<  "); New Chi2 : " << chi2 << std::endl;
    for(int i = 0; i < max_step; i++)
    {
        float up_lim = 1 + grad_delta_param;
        float down_lim = 1 - grad_delta_param;

        // r update
        float grad_r = (Chi2(new_hits, new_r * up_lim, theta, phi, new_ge68_alpha) - \
                    Chi2(new_hits, new_r * down_lim, theta, phi, new_ge68_alpha))/ \
                 (new_r * grad_delta_param * 2);
        grad_r = -1 * lr * grad_r;
        if( (grad_r > 0) & (new_r < (900 - 1)) ){
            new_r += (900 - new_r) * xsigmoid( grad_r / (900 - new_r));
        }else if( (grad_r < 0) & (new_r > 1)){
            new_r += (new_r) * xsigmoid( grad_r / new_r );
        }
        
        // hits update
        float grad_hits = (Chi2(new_hits * up_lim, new_r, theta, phi, new_ge68_alpha) - \
                    Chi2(new_hits * down_lim, new_r, theta, phi, new_ge68_alpha))/ \
                 (new_hits * grad_delta_param * 2);
        new_hits -= 100 * lr * grad_hits;

        // float grad_ge_alpha = (Chi2(new_hits, new_r, theta, phi, new_ge68_alpha * up_lim) - \
        //             Chi2(new_hits, new_r, theta, phi, new_ge68_alpha * down_lim))/ \
        //          (new_ge68_alpha * grad_delta_param * 2);
        // grad_ge_alpha = -0.001 * lr * grad_ge_alpha;
        // if((grad_ge_alpha > 0) & (new_ge68_alpha < gamma_tmp_ratio[1]*0.99)){
        //     new_ge68_alpha += (gamma_tmp_ratio[1] - new_ge68_alpha) * xsigmoid( grad_ge_alpha / (gamma_tmp_ratio[1] - new_ge68_alpha) );
        // }else if( grad_ge_alpha < 0 & (new_ge68_alpha > 1.e-2)){
        //     new_ge68_alpha += (new_ge68_alpha) * xsigmoid( grad_ge_alpha / new_ge68_alpha );
        // }

        float new_chi2 = Chi2(new_hits, new_r, theta, phi, new_ge68_alpha);
        if((new_chi2 - chi2 < 0) & (new_chi2 - chi2 > - 0.1))
        {
            break;
        }
        chi2 = new_chi2;
        // if (fGdLSEdepR > 800){
        //     std::cout << "Grad: (R,  Hits) = (" << grad_r << "," << grad_hits <<"," << grad_ge_alpha <<  "); New Chi2 : " << chi2 << std::endl;
        // }
    }
    hits = new_hits;
    r = new_r;
    ge68_alpha = new_ge68_alpha;
    std::cout << "End (R, Hits) = (" << new_r << "," << new_hits <<"," << new_ge68_alpha <<  "); New Chi2 : " << chi2 << std::endl;
}

bool ChargeTemplateRec::CalChargeCenter()
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
    fCCRecTheta = cc_vec.Theta();
    fCCRecPhi = cc_vec.Phi();
} 
 
double ChargeTemplateRec::LogPoisson(double obj,double exp_n)
{
    // likelihood ratio
    double p=2*(exp_n-obj);
    if(obj>0.01){
        p+=2*obj*TMath::Log(obj/exp_n);
    }
    return p;
}

float ChargeTemplateRec::CalExpChargeHit(float radius, float theta, float alpha, float alpha_ge68)
{
    float ge68_alpha = alpha_ge68;
    float exp_hit = charge_template -> CalExpChargeHit(radius, theta); 
    float exp_hit_ge68 = charge_template_ge68 -> CalExpChargeHit(radius, theta);
    return alpha*((1 - ge68_alpha)*exp_hit + ge68_alpha * exp_hit_ge68);
}
