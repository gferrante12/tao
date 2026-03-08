//
//  Author: Jiayang Xu  2023.3.20
//  E-mail:xujy@ihep.ac.cn
//

#ifndef SiPMCalibAlg_h
#define SiPMCalibAlg_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition
#include "SniperKernel/AlgBase.h"
#include "DarkCountRateCalibTool.h"
#include "RelativePDECalibTool.h"
#include "TimeoffsetCalibTool.h"
#include "InternalCrossTalkCalibTool.h"
#include "GainCalibTool.h"
#include <TTree.h>
#include <vector>
#include <TH1.h>
#include <TH2.h>
#include <TF1.h>
#include <TMath.h>






class SiPMCalibAlg: public AlgBase
{
    public:
        SiPMCalibAlg(const std::string& name);
        ~SiPMCalibAlg();
        

        bool initialize();
        bool execute();
        bool finalize();

    

    private:
    
    
    int nevt_processed;
	TTree* evt;
 	std::vector<float> fADCs;
    std::vector<int64_t> fTDCs;
	Int_t fChannelID;
	int fevents;
    float zeroPE[8048];
    float gain[8048];
    float timeoffset[8048];
    float DCR[8048];
    float RelativePDE[8048];
    float InCTLamda[8048];
    TH1F h_ADCs[8048];
    TH1F h_TDCs[8048];
    TH1F h_FirstHitTime[8048];
    TH1F h_DNADCs[8048];
    TH1F h_DNTDCs[8048];

    DarkCountRateCalibTool* darkcountrate_tool; 
    RelativePDECalibTool* relativepde_tool;
    TimeoffsetCalibTool* timeoffset_tool;
    GainCalibTool* gain_tool;
    InternalCrossTalkCalibTool* inct_tool;

    int m_dcrflag;
    int m_timeflag;
    int m_pdeflag;
    int m_gainflag;
    int m_inctflag;
    

	
 	
};

#endif