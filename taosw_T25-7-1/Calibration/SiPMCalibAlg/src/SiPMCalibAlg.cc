//
//  Author: Jiayang Xu  2023.3.20
//  E-mail:xujy@ihep.ac.cn
//
#include "SiPMCalibAlg.h"
#include "RelativePDECalibTool.h"
#include "DarkCountRateCalibTool.h"
#include "TimeoffsetCalibTool.h"
#include "GainCalibTool.h"
#include "InternalCrossTalkCalibTool.h"
#include "Event/CdElecHeader.h"
#include "Event/CdElecChannel.h"
#include "Event/CdElecEvt.h"
#include "SniperKernel/AlgFactory.h"
#include "SniperKernel/Incident.h"
#include "SniperKernel/SniperDataPtr.h"
#include "SniperKernel/AlgFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/SniperLog.h"
#include "RootWriter/RootWriter.h"
#include "BufferMemMgr/IDataMemMgr.h"
#include "EvtNavigator/NavBuffer.h"

#include "TROOT.h"
#include <TF1.h>
#include <TGeoManager.h>
#include <vector>
#include <boost/python.hpp>
#include <TMath.h>
#include <TCanvas.h>



DECLARE_ALGORITHM(SiPMCalibAlg);


SiPMCalibAlg::SiPMCalibAlg(const std::string& name)
    : AlgBase(name)
{
    declProp("dcrflag",    m_dcrflag = 1);
    declProp("timeflag",    m_timeflag = 1);
    declProp("pdeflag",    m_pdeflag = 1);
    declProp("gainflag",    m_gainflag = 1);
    declProp("inctflag",    m_inctflag = 1);

}

SiPMCalibAlg::~SiPMCalibAlg()
{

}


bool
SiPMCalibAlg::initialize()
{
    
    darkcountrate_tool = tool<DarkCountRateCalibTool>("DarkCountRateCalibTool");
    if(!darkcountrate_tool) {
        LogError << "DarkCountRate Calib Tool cannot be achieved." << std::endl;
        return false;
    }
    relativepde_tool = tool<RelativePDECalibTool>("RelativePDECalibTool");
    if(!relativepde_tool) {
        LogError << "Relative PDE Calib Tool cannot be achieved." << std::endl;
        return false;
    }
    timeoffset_tool = tool<TimeoffsetCalibTool>("TimeoffsetCalibTool");
    if(!timeoffset_tool) {
        LogError << "Relative Timeoffset Tool cannot be achieved." << std::endl;
        return false;
    }
    gain_tool = tool<GainCalibTool>("GainCalibTool");
    if(!gain_tool) {
        LogError << "Gain Tool cannot be achieved." << std::endl;
        return false;
    }

    inct_tool = tool<InternalCrossTalkCalibTool>("InternalCrossTalkCalibTool");
    if(!inct_tool) {
        LogError << "Internal CrossTalk Tool cannot be achieved." << std::endl;
        return false;
    }
    // Add new tool

    // = get RootWriter =
    SniperPtr<RootWriter> rootwriter(getParent(), "RootWriter");
    if (rootwriter.invalid()) {
        LogError << "Can't Find RootWriter. "
                 << std::endl;
        return false;
    }
    darkcountrate_tool->init();
    relativepde_tool->init();
    timeoffset_tool->init();
    gain_tool->init();
    inct_tool->init();
    //Add New Tool
#ifndef SNIPER_VERSION_2
    evt = rootwriter->bookTree("ANASIMEVT/myevt", "user defined data");
#else
    evt = rootwriter->bookTree(*getParent(), "ANASIMEVT/myevt", "user defined data");
#endif
    std::string histoname1;
    std::string histoname2;
    std::string histoname3; 
    std::string histoname4;
    std::string histoname5;
    for(int i=0;i<8048;i++)
    {
        histoname1.clear();
        histoname2.clear();
        histoname3.clear();
        histoname4.clear();
        histoname5.clear();
        histoname1 = "h_ADCs";
        histoname2 = "h_TDCs";
        histoname3 = "h_DNADCs";
        histoname4 = "h_DNTDCs";
        histoname5 = "h_FirstHitTime";
        histoname1 += std::to_string(i);
        histoname2 += std::to_string(i);
        histoname3 += std::to_string(i);
        histoname4 += std::to_string(i);
        histoname5 += std::to_string(i);
        h_ADCs[i] = TH1F(histoname1.c_str(),histoname1.c_str(),250,0,50000);
        h_TDCs[i] = TH1F(histoname2.c_str(),histoname2.c_str(),250,-100,900);
        h_DNADCs[i] = TH1F(histoname3.c_str(),histoname3.c_str(),250,0,50000);
        h_DNTDCs[i] = TH1F(histoname4.c_str(),histoname4.c_str(),250,-100,900);
        h_FirstHitTime[i] = TH1F(histoname5.c_str(),histoname5.c_str(),250,-100,900);
        zeroPE[i]=0;
        DCR[i] = 0;
        RelativePDE[i] = 0;
        timeoffset[i] = 0;
        gain[i] = 0;
        InCTLamda[i] = 0;
    }
    fevents=0;
    evt->Branch("gain", gain, "gain[8048]/F");
    evt->Branch("timeoffset", timeoffset, "timeoffset[8048]/F");
    evt->Branch("DCR", DCR, "DCR[8048]/F");
    evt->Branch("RelativePDE", RelativePDE, "RelativePDE[8048]/F");
    evt->Branch("InCTLamda", InCTLamda, "InCTLamda[8048]/F");
	return true;
}

bool
SiPMCalibAlg::execute()
{
    //Read out the elesim charge and time into memory and save it into a map. 
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

    Tao::CdElecHeader* elec_hdr = dynamic_cast<Tao::CdElecHeader*>(evt_nav->getHeader("/Event/Elec"));
    if (not elec_hdr) {
        LogWarn<<"no cd data is found, skip this event."<<std::endl;
        return true;
    }
    if (!elec_hdr->hasEvent()) {
        LogWarn<<"no cd data is found, skip this event."<<std::endl;
        return true;
    }
    
    // == get event ==
    Tao::CdElecEvt* elec_event = dynamic_cast<Tao::CdElecEvt*>(elec_hdr->event());
    int allcharge = 0;
    
	// == get channel vector==	
    fADCs.clear();
    fTDCs.clear();
    std::vector<Tao::CdElecChannel> elec_Channels = elec_event->GetElecChannels();
    // == get channel ==
	for (auto it_channel = elec_Channels.begin();
              it_channel != elec_Channels.end(); ++it_channel){
	
	    auto it = *it_channel;
        fChannelID = int(it.getChannelID());
        if(fChannelID>=8048)
        {
            continue;
        }		
        fADCs = it.getADCs();	
        fTDCs = it.getTDCs();
        zeroPE[fChannelID]+=1;
        for(int i=0;i<fADCs.size();i++)
        {
            if(fTDCs[i]>-100 && fTDCs[i]<0)
            {
                h_DNADCs[fChannelID].Fill(fADCs[i]);
                h_DNTDCs[fChannelID].Fill(float(fTDCs[i]));
            }
            h_ADCs[fChannelID].Fill(fADCs[i]);
            h_TDCs[fChannelID].Fill(float(fTDCs[i]));
            if(i==0)
            {
                h_FirstHitTime[fChannelID].Fill(float(fTDCs[i]));
            }
        }
        
    
    
    }
    if(fevents<=100)
    {
        LogInfo<<"Event:"<<fevents<<std::endl;
    }
    else
    {
        if(fevents%1000==0)
        {
            LogInfo<<"Event:"<<fevents<<std::endl;
        }
    }
    


    //Total number of events 
    fevents++;

    return true;
}

bool
SiPMCalibAlg::finalize()
{
    for(int i=0;i<8048;i++)
    {
        zeroPE[i]=fevents-zeroPE[i];
    }
    
    bool status;
    if(m_dcrflag==1)
    {
        status=darkcountrate_tool->CalibDarkCountRate(DCR,h_TDCs,fevents);
    }
    if(m_timeflag==1)
    {
        status=timeoffset_tool->CalibTimeoffset(timeoffset,h_FirstHitTime);
    }
    if(m_pdeflag==1)
    {
        status=relativepde_tool->CalibRelativePDE(RelativePDE,zeroPE,fevents);
    }
    if(m_gainflag==1)
    {
        status=gain_tool->CalibGain(gain,h_ADCs);
    }
    if(m_inctflag==1)
    {
        status=inct_tool->CalibInternalCrossTalk(InCTLamda,h_ADCs);
    }
    //Add New Tool
    evt->Fill();
    
    return true;
}

