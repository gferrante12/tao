//
//  Author: Jiayang Xu  2023.3.20
//  E-mail:xujy@ihep.ac.cn
//

#include "CalibAnaTest.h"
#include "Event/CdCalibHeader.h"
#include "Event/CdCalibChannel.h"
#include "Event/CdCalibEvt.h"

#include "SniperKernel/AlgFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/SniperLog.h"
#include "RootWriter/RootWriter.h"
#include "BufferMemMgr/IDataMemMgr.h"
#include "EvtNavigator/NavBuffer.h"

#include "TROOT.h"
#include <TGeoManager.h>
#include <vector>
#include <boost/python.hpp>

DECLARE_ALGORITHM(CalibAnaTest);

CalibAnaTest::CalibAnaTest(const std::string& name)
    : AlgBase(name), evt(0)
{


}

CalibAnaTest::~CalibAnaTest()
{

}

bool
CalibAnaTest::initialize()
{

    // = get RootWriter =
    SniperPtr<RootWriter> rootwriter(getParent(), "RootWriter");
    if (rootwriter.invalid()) {
        LogError << "Can't Find RootWriter. "
                 << std::endl;
        return false;
    }

#ifndef SNIPER_VERSION_2
    evt = rootwriter->bookTree("ANASIMEVT/myevt", "user defined data");
#else
    evt = rootwriter->bookTree(*getParent(), "ANASIMEVT/myevt", "user defined data");
#endif

	fevtID=0;
    np=0;
	pfPEs[10000]={0};
	pfTDCs[10000]={0};
	
    evt->Branch("fevtID", &fevtID, "fevtID/I");
    evt->Branch("fChannelID", &fChannelID, "fChannelID/I");
    evt->Branch("np", &np, "np/I");
    evt->Branch("pfPEs", pfPEs, "pfPEs[np]/F");
    evt->Branch("pfTDCs", pfTDCs, "pfTDCs[np]/F");
	return true;
}

bool
CalibAnaTest::execute()
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

    Tao::CdCalibHeader* cal_hdr = dynamic_cast<Tao::CdCalibHeader*>(evt_nav->getHeader("/Event/Calib"));
    if (not cal_hdr) {
        return 0;
    }
    if (!cal_hdr->hasEvent()) {
        std::cout<<"no data is found, skip this event."<<std::endl;
        return true;
    }
    
    // == get event ==
    Tao::CdCalibEvt* cal_event = dynamic_cast<Tao::CdCalibEvt*>(cal_hdr->event());
    int allcharge = 0;
    
	// == get channel vector==	
    std::vector<Tao::CdCalibChannel> cal_Channels = cal_event->GetCalibChannels();
    // == get channel ==
	for (auto it_channel = cal_Channels.begin();
              it_channel != cal_Channels.end(); ++it_channel){
	
    //Tao::CdElecChannel elec_channel;
    np = 0;
	auto it = *it_channel;
	
    fChannelID = it.CalibgetChannelID();	
    fPEs = it.CalibgetPEs();	
    fTDCs = it.CalibgetTDCs();
    
	
	for (int i=0; i<fPEs.size();i++){
    pfPEs[i]=fPEs[i];
    pfTDCs[i]=fTDCs[i];
    np++;
    }

    evt->Fill();
    }
    



    fevtID++;

    // = Fill Data =
    
   
   return true;
}

bool
CalibAnaTest::finalize()
{
    return true;
}
