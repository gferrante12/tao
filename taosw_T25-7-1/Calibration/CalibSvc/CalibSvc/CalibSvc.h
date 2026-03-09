//
//  Author: Jiayang Xu  2025.12.17
//  E-mail:xujy@ihep.ac.cn
//


#ifndef CalibSvc_h
#define CalibSvc_h

#include "SniperKernel/SvcBase.h"
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/SvcFactory.h"
#include "SniperKernel/SharedElemFactory.h"

#include <CondDB/ICondDBSvc.h>
#include <CondDB/IRepo.h>
#include <CondDB/ICnvFromPayload.h>
#include <CondObj/CommonCondObj.h>

#include "CalibSvc/ICalibSvc.h"

#include "TFile.h"
#include "TTree.h"

#include <fstream>
#include <iostream>

class CalibSvc : public ICalibSvc, public SvcBase
{
    public:
        CalibSvc(const std::string &name);
        ~CalibSvc();

        bool initialize();
        bool finalize();

        const float GetGain(int chid);
        const float GetMean0(int chid);
        const float GetTimeOffset(int chid);
        const float GetDCR(int chid);
        const float GetBaseline(int chid);
        const bool UseDynamicBaseline();

	    bool SetGain(int id, float gain);
	    bool SetMean0(int id, float mean0);
	    bool SetTimeOffset(int id, float timeOffset);
	    bool SetDCR(int id, float dcr);
        bool SetBaseline(int id, float baseline);

    private:
        float m_gain[8048];
        float m_mean0[8048];
        float m_timeoffset[8048];
        float m_dcr[8048];
        float m_baseline[8048];
        bool m_useDynamicBaseline;

        TFile* f;
        CondDB::ICondDBSvc* m_conddb_svc;
        CondObj::Common::CommonCondObj m_sipm_path;
        std::string m_input_root_file;
        bool m_EnableCondDB;
        int m_IOV;
        std::string m_Tag;
        std::string m_inputcalibpar;
};

#endif
