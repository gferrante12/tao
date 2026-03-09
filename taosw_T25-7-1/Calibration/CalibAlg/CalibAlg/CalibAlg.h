//
//  Author: Jiayang Xu  2023.3.20
//  E-mail:xujy@ihep.ac.cn
//

#ifndef CalibAlg_h
#define CalibAlg_h
#include "SniperKernel/AlgBase.h"

#include <TTree.h>
#include <vector>
#include <TH1.h>
#include <TH2.h>
#include <TF1.h>
#include <TMath.h>
#include "TF1.h"
#include "TFile.h"
#include "TTree.h"
#include "TChain.h"
#include <map>
#include <boost/python.hpp>
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "EvtNavigator/NavBuffer.h"
#include "Event/CdElecHeader.h"
#include "Event/CdElecEvt.h"
#include "Event/CdElecChannel.h"

#include "Event/CdCalibHeader.h"
#include "Event/CdCalibEvt.h"
#include "Event/CdCalibChannel.h"

#include <CondDB/ICondDBSvc.h>
#include <CondDB/IRepo.h>
#include <CondDB/ICnvFromPayload.h>
#include <CondObj/CommonCondObj.h>
#include "CalibSvc/ICalibSvc.h"

class CalibAlg: public AlgBase
{    
    public:
        CalibAlg(const std::string& name);
        ~CalibAlg();
        bool initialize();
        bool execute();
        bool finalize();
    private:
        bool m_useDynamicBaseline=false;
        Int_t fChannelID;
        //TFile* f;
        //float gain1[8048];
        //float mean01[8048];
        //float timeoffset1[8048];
        std::vector<float> fADCs;
        std::vector<int64_t> fTDCs;
        std::vector<uint16_t> fWidths;
        std::vector<uint16_t> fBaselines;
        std::vector<float> CalibPEs;
        std::vector<float> CalibfTDCs;
        std::vector<float> CalibfWidths;
        ICalibSvc* m_calibsvc;
        static constexpr int NCH = 8048;
        std::vector<double> m_bfix;
        std::vector<double> m_mean0;
        std::vector<double> m_gain;
        bool m_cacheReady = false;
        //CondDB::ICondDBSvc* m_conddb_svc;
        //CondObj::Common::CommonCondObj m_sipm_path;
        //std::string m_input_root_file;
        //bool m_EnableCondDB;
        //int m_IOV;
        //std::string m_Tag;
        //std::string m_inputcalibpar;
};

#endif
