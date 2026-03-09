//
//  Author: Jiayang Xu  2023.3.20
//  E-mail:xujy@ihep.ac.cn
//  Modified by Jianrun Hu


#include "CalibAlg/CalibAlg.h"
#include "Event/CdElecHeader.h"
#include "Event/CdElecChannel.h"
#include "Event/CdElecEvt.h"

#include "Event/CdCalibHeader.h"
#include "Event/CdCalibChannel.h"
#include "Event/CdCalibEvt.h"
#include "Event/WtTrigHeader.h"
#include "Event/TvtTrigHeader.h"
#include "Event/WtElecHeader.h"
#include "Event/TvtElecHeader.h"

#include "SniperKernel/AlgFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/SniperLog.h"
#include "RootWriter/RootWriter.h"
#include "BufferMemMgr/IDataMemMgr.h"
#include "EvtNavigator/NavBuffer.h"
#include "EvtNavigator/EvtNavHelper.h"
#include "EvtNavigator/EvtNavigator.h"
#include "TROOT.h"
#include <TF1.h>
#include <TGeoManager.h>
#include <vector>
#include <boost/python.hpp>
#include <TMath.h>
#include <TCanvas.h>
#include <fstream>
#include <iostream>
#include "TFile.h"
#include "TTree.h"
#include "TChain.h"

DECLARE_ALGORITHM(CalibAlg);

CalibAlg::CalibAlg(const std::string& name) : AlgBase(name)
{

}

CalibAlg::~CalibAlg()
{

}
bool
CalibAlg::initialize()
{
    
    SniperPtr<ICalibSvc> Calib_svc (getParent(), "CalibSvc");
    if (Calib_svc.invalid()) {
       LogError << "can't find service CalibSvc" << std::endl;
       return false;
    }
    m_calibsvc = Calib_svc.data();       
    // 输出前几个通道的校准参数用于调试
    LogInfo << "Calibration parameters for first 5 channels:" << std::endl;
    for(int i=0; i<5; i++) {
        LogInfo << "Channel " << i << ": gain = " << m_calibsvc->GetGain(i)
                << ", mean0 = " << m_calibsvc->GetMean0(i)
                << ", timeoffset = " << m_calibsvc->GetTimeOffset(i) 
                << ", baseline=" << m_calibsvc->GetBaseline(i)
                << ", dcr = " << m_calibsvc->GetDCR(i) << std::endl;
    }
    m_useDynamicBaseline=m_calibsvc->UseDynamicBaseline();
    LogInfo << "UseDynamicBaseline = "
        << (m_useDynamicBaseline ? "ON" : "OFF")
        << std::endl;
    m_bfix.assign(NCH, 0.0);
    m_mean0.assign(NCH, 0.0);
    m_gain.assign(NCH, 1.0);

    for (int ch = 0; ch < NCH; ++ch) {
        m_bfix[ch]  = m_calibsvc->GetBaseline(ch);
        m_mean0[ch] = m_calibsvc->GetMean0(ch);
        m_gain[ch]  = m_calibsvc->GetGain(ch);
        if (m_gain[ch] == 0) m_gain[ch] = 1e12; 
    }
    m_cacheReady = true;

    
    return true;

}
bool
CalibAlg::execute()
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

    Tao::TvtElecHeader* tvt_elec_hdr = dynamic_cast<Tao::TvtElecHeader*>(evt_nav->getHeader("/Event/TvtElec"));
    if (tvt_elec_hdr && tvt_elec_hdr->hasEvent()) {
        return true;
    }
    
    Tao::WtElecHeader* wt_elec_hdr = dynamic_cast<Tao::WtElecHeader*>(evt_nav->getHeader("/Event/WtElec"));
    if (wt_elec_hdr && wt_elec_hdr->hasEvent()) {
        return true;
        }

    Tao::CdElecHeader* elec_hdr = dynamic_cast<Tao::CdElecHeader*>(evt_nav->getHeader("/Event/Elec"));
    if (not elec_hdr) {
        LogWarn<<"no cd data is found, skip this event."<<std::endl;
        return true;
    }
    if (!elec_hdr->hasEvent()) {
        LogWarn<<"no cd data is found, skip this event."<<std::endl;
        return true;
    }
    
    /////////////////
    // == get event ==
    Tao::CdElecEvt* elec_event = dynamic_cast<Tao::CdElecEvt*>(elec_hdr->event());
    int allcharge = 0;
    
    auto cal_header = JM::getHeaderObject<Tao::CdCalibHeader>(evt_nav);
    if (!cal_header){
      cal_header = new Tao::CdCalibHeader();
      JM::addHeaderObject(evt_nav, cal_header);
    }

    Tao::CdCalibEvt* CalibEvt = new Tao::CdCalibEvt();

    if(elec_event->getOnlineEvtType() ) {
      CalibEvt->setOnlineX( elec_event->getOnlineX() );
      CalibEvt->setOnlineY( elec_event->getOnlineY() );
      CalibEvt->setOnlineZ( elec_event->getOnlineZ() );
      CalibEvt->setOnlineEvtType( true );
    }
	// == get channel vector==	
    fADCs.clear();
    fTDCs.clear();
    fWidths.clear();
    fBaselines.clear();
    CalibPEs.clear();
    CalibfTDCs.clear();
    CalibfWidths.clear();
    double totalPE = 0;
    std::vector<Tao::CdElecChannel> elec_Channels = elec_event->GetElecChannels();
    
    Tao::CdCalibChannel Calibchannel;
    //Use SiPM Parameters of Calibration to correct the charge and time in each channel
    
    for (auto it_channel = elec_Channels.begin();
              it_channel != elec_Channels.end(); ++it_channel){
	
    
	    auto it = *it_channel;
	
        fChannelID = int(it.getChannelID());
        if(fChannelID>8048)
        {
            continue;
        }	
        fADCs = it.getADCs();	
        fTDCs = it.getTDCs();
        fWidths = it.getWidths();
        fBaselines = it.getBaselines();
        Calibchannel.CalibsetChannelID(fChannelID);
        //get correction of PE number in each channel 
        // 修改：使用新的校准公式 (ADC - mean0) / gain
        for(int i=0;i<fADCs.size();i++)
        {
            if (fChannelID==8048){
                double calibrated_charge = (fADCs.at(i));
                CalibPEs.push_back(calibrated_charge);
                totalPE += calibrated_charge;   
            }
            else{
                const int ch = fChannelID;
                if (!m_cacheReady || ch < 0 || ch >= NCH) continue;
                const double W    = fWidths.at(i);
                const double bdyn = fBaselines.at(i);
                double q = fADCs.at(i);

                if (m_useDynamicBaseline) q = q + (m_bfix[ch] - bdyn) * W;
                const double calibrated_charge = (q - m_mean0[ch]) / m_gain[ch];
            //double calibrated_charge = (fADCs.at(i) - m_calibsvc->GetMean0(fChannelID)) / m_calibsvc->GetGain(fChannelID);
            CalibPEs.push_back(calibrated_charge);
            totalPE += calibrated_charge;             
            }
            // // 调试输出前几个hit的信息
            // if (fChannelID < 5 && i == 0) {
            //     LogDebug << "Channel " << fChannelID << ": ADC=" << fADCs.at(i) 
            //              << ", mean0=" << mean01[fChannelID] 
            //              << ", gain=" << gain1[fChannelID]
            //              << ", calibrated_charge=" << calibrated_charge << std::endl;
            // }
        }

        //get correction of time in each channel 
        for(int i=0;i<fTDCs.size();i++)
        {
            CalibfTDCs.push_back(float(fTDCs.at(i)-m_calibsvc->GetTimeOffset(fChannelID)));
        }
        for(int i=0;i<fWidths.size();i++)
        {
            CalibfWidths.push_back(float(fWidths.at(i)));
        }
        Calibchannel.CalibsetPEs(CalibPEs);
        Calibchannel.CalibsetTimes(CalibfTDCs);
        Calibchannel.CalibsetWidths(CalibfWidths);
        CalibEvt->AddCalibChannel(Calibchannel);
        CalibPEs.clear();
        CalibfTDCs.clear();
        CalibfWidths.clear();
        
    
    }

    if(elec_event->getOnlineEvtType() ) CalibEvt->SetTotalPE(elec_event->getOnlinePE());
    else CalibEvt->SetTotalPE(totalPE);

    cal_header->setEvent(CalibEvt);
    evt_nav->addHeader("/Event/Calib", cal_header);
    return true;



}
bool
CalibAlg::finalize()
{
    
    return true;
}
