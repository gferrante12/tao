#include "CalibSvc/CalibSvc.h"
#include <TaoPathHelper/TaoPath.hh>


DECLARE_SERVICE(CalibSvc);
DECLARE_CAN_BE_SHARED(CalibSvc);

CalibSvc::CalibSvc(const std::string& name) : SvcBase(name), m_EnableCondDB(true), m_Tag("Calib.SiPMCalibAlg.Para"), m_IOV(20230711), m_inputcalibpar(""), m_useDynamicBaseline(false)
{
    declProp("EnableCondDB", m_EnableCondDB);
    declProp("Tag", m_Tag);
    declProp("IOV", m_IOV);
    declProp("inputcalibpar", m_inputcalibpar);
    declProp("UseDynamicBaseline", m_useDynamicBaseline);
}

CalibSvc::~CalibSvc()
{
}

bool CalibSvc::initialize()
{
    if(m_EnableCondDB)
    {
        SniperPtr<CondDB::ICondDBSvc> conddb(getParent(), "CondDBSvc");
        if (conddb.invalid()) {
            LogError << "Failed to get CondDBSvc!" << std::endl;
            LogError << "CondDB will not be used during reconstruction. " << std::endl;
	    } else {
	        m_conddb_svc = conddb.data();
	        bool declCondObj_done = m_conddb_svc->declCondObj(m_Tag.c_str(), m_sipm_path);
    	    m_conddb_svc->setCurrent(m_IOV);
            LogInfo << "path1: " << m_sipm_path.path() << std::endl;
        }   
        m_input_root_file= m_sipm_path.path();
        m_input_root_file= Tao::TaoPath::resolve(m_input_root_file.c_str());
    }
    else
    {
        if(m_inputcalibpar.size()==0)
        {
            std::string SiPMCalParPath = getenv("SIPMCALIBALGROOT");
            m_input_root_file=SiPMCalParPath+"/share/cal_par.root";
            LogInfo << "path2: " << m_input_root_file << std::endl;
        }
        else
        {
            m_input_root_file = m_inputcalibpar;
            LogInfo << "path3: " << m_input_root_file << std::endl;
        }
    
        
    }
    f = TFile::Open(m_input_root_file.c_str());
    if (!f) {
        LogError << "can't open the input file ["
                 << m_input_root_file
                 << "]"
                 << std::endl;
        return false;
    }
    float timeoffset[8048]={0};
    float gain[8048]={0};
    float mean0[8048]={0};  
    float baseline[8048]  = {0};
    float dcr[8048]={0};  
    
    auto t3 = (TTree*)f->Get("myevt");
    if (m_useDynamicBaseline) {t3->SetBranchAddress("gain_dyn", gain); t3->SetBranchAddress("mean0_dyn", mean0);}
    else  {t3->SetBranchAddress("gain", gain); t3->SetBranchAddress("mean0", mean0);}
    t3->SetBranchAddress("timeoffset", timeoffset);
    t3->SetBranchAddress("baseline", baseline);
    t3->SetBranchAddress("dcr", dcr);
    
    t3->GetEntry(0);
    for(int i=0;i<8048;i++)
    {
        m_gain[i]       = gain[i];
        m_mean0[i]      = mean0[i];
        m_timeoffset[i] = timeoffset[i];
        m_baseline[i]  = baseline[i];
        m_dcr[i]        = dcr[i];
    }
    f->Close();
    return true;
}

bool CalibSvc::finalize()
{
    return true;
}

const float CalibSvc::GetGain(int chid)
{
    return m_gain[chid];
}

const float CalibSvc::GetMean0(int chid)
{
    return m_mean0[chid];
}

const float CalibSvc::GetTimeOffset(int chid)
{
    return m_timeoffset[chid];
}

const float CalibSvc::GetDCR(int chid)
{
    return m_dcr[chid];
}

const float CalibSvc::GetBaseline(int chid)
{
    return m_baseline[chid];
}

const bool CalibSvc::UseDynamicBaseline()
{
    return m_useDynamicBaseline;
}

bool CalibSvc::SetGain(int chid, float gain)
{
    m_gain[chid] = gain;
    return true;
}

bool CalibSvc::SetMean0(int chid, float mean0)
{
    m_gain[chid] = mean0;
    return true;
}

bool CalibSvc::SetTimeOffset(int chid, float timeoffset)
{
    m_timeoffset[chid] = timeoffset;
    return true;
}

bool CalibSvc::SetDCR(int chid, float dcr)
{
    m_dcr[chid] = dcr;
    return true;
}

bool CalibSvc::SetBaseline(int chid, float baseline)
{
    m_baseline[chid] = baseline;
    return true;
}

