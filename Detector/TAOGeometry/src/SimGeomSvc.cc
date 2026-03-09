//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "TAOGeometry/SimGeomSvc.h"
#include "SniperKernel/SvcFactory.h"
#include "SniperKernel/SniperLog.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/Incident.h"
#include "RootIOSvc/IInputSvc.h"

#include <TFile.h>
#include <TError.h>

DECLARE_SERVICE(SimGeomSvc);

SimGeomSvc::SimGeomSvc(const std::string& name)
: SvcBase(name), m_geo_mgr(0),m_CdGeom(0),m_WtGeom(0),m_TvtGeom(0)
{
    declProp("InitCD", m_initCd=true);
    declProp("InitWT", m_initWt=true);
    declProp("InitTVT", m_initTvt=true);
}

SimGeomSvc::~SimGeomSvc()
{

}

bool SimGeomSvc::initialize()
{
    initRootGeom();

    return true;
}

bool SimGeomSvc::finalize()
{
    // if need to output the geometry
    //
    return true;
}

void SimGeomSvc::geom(TGeoManager* v)
{
    m_geo_mgr = v;
}

TGeoManager* SimGeomSvc::geom()
{
    if (!m_geo_mgr) {
        load_from_root();
    }
    return m_geo_mgr;
}

// load from file
void SimGeomSvc::load_from_root()
{
    
    Int_t olderrlevel = gErrorIgnoreLevel;
    gErrorIgnoreLevel = kWarning;
    std::string geometryPath = getenv("TAOGEOMETRYROOT");
    m_input_root_file=geometryPath+"/python/TAOGeometry/sample-detsim1.root";
    TFile* f = TFile::Open(m_input_root_file.c_str());
    if (!f) {
        LogError << "can't open the input file ["
                 << m_input_root_file
                 << "]"
                 << std::endl;
        // Incident::fire("StopRun");
        //getParent()->stop();
        return;
    }
    if (gGeoManager) 
    {
        m_geo_mgr = gGeoManager;
    }
    else
    {
        m_geo_mgr = TGeoManager::Import(m_input_root_file.c_str(),
                                    "TaoGeom");
    }
    if (m_geo_mgr) {
        LogInfo << "load geometry successfully" << std::endl;
    }
    gErrorIgnoreLevel = olderrlevel;
    
}

bool SimGeomSvc::initRootGeom()
{
    initCdGeomControl(m_initCd);
    initWtGeomControl(m_initWt);
    initTvtGeomControl(m_initTvt);

    return true;
}

void SimGeomSvc::initCdGeomControl(bool value)
{
     if (value)
     initCdGeom();
     else
     LogDebug << "Do not initialize CdGeom." << std::endl;
}

void SimGeomSvc::initWtGeomControl(bool value)
{
     if (value)
     initWtGeom();
     else
     LogDebug << "Do not initialize WtGeom." << std::endl;
}

void SimGeomSvc::initTvtGeomControl(bool value)
{
     if (value)
     initTvtGeom();
     else
     LogDebug << "Do not initialize TvtGeom." << std::endl;
}


bool SimGeomSvc::initCdGeom()
{
    LogDebug << "initCdGeom " << std::endl;
    //LogDebug << "GeomFile " << m_geomFileName << std::endl;

    m_CdGeom = new CdGeom();
    //m_CdGeom->setVerb(0);
    //m_CdGeom->setGeomFileName(m_geomFileName);
    //m_CdGeom->setGeomPathName(m_geomPathName);
    //m_CdGeom->setFastInit(m_fastInit);
    m_CdGeom->initRootGeo();
    //m_CdGeom->printCd();
    //LogInfo << "CdDetector SiPM size " << m_CdGeom->getSiPMNum() << std::endl;
  
    return true;
}

bool SimGeomSvc::initWtGeom()
{
    LogDebug << "initWtGeom " << std::endl;
    //LogDebug << "GeomFile " << m_geomFileName << std::endl;

    m_WtGeom = new WtGeom();
    //m_CdGeom->setVerb(0);
    //m_CdGeom->setGeomFileName(m_geomFileName);
    //m_CdGeom->setGeomPathName(m_geomPathName);
    //m_CdGeom->setFastInit(m_fastInit);
    m_WtGeom->initRootGeo();
    //m_CdGeom->printCd();
    //LogInfo << "CdDetector SiPM size " << m_CdGeom->getSiPMNum() << std::endl;
  
    return true;
}

bool SimGeomSvc::initTvtGeom()
{
    LogDebug << "initTvtGeom " << std::endl;
    //LogDebug << "GeomFile " << m_geomFileName << std::endl;

    m_TvtGeom = new TvtGeom();
    //m_CdGeom->setVerb(0);
    //m_CdGeom->setGeomFileName(m_geomFileName);
    //m_CdGeom->setGeomPathName(m_geomPathName);
    //m_CdGeom->setFastInit(m_fastInit);
    m_TvtGeom->initRootGeo();
    //m_CdGeom->printCd();
    //LogInfo << "CdDetector SiPM size " << m_CdGeom->getSiPMNum() << std::endl;
  
    return true;
}

CdGeom* SimGeomSvc::getCdGeom()
{
  //if (!m_CdGeom)
  //{
    //LogDebug << "getCdGeom instance does not exist " << std::endl;
    //return 0;
  //}
  //else
  //{
    return m_CdGeom;
  //}
}

WtGeom* SimGeomSvc::getWtGeom()
{
  //if (!m_CdGeom)
  //{
    //LogDebug << "getCdGeom instance does not exist " << std::endl;
    //return 0;
  //}
  //else
  //{
    return m_WtGeom;
  //}
}

TvtGeom* SimGeomSvc::getTvtGeom()
{
  //if (!m_CdGeom)
  //{
    //LogDebug << "getCdGeom instance does not exist " << std::endl;
    //return 0;
  //}
  //else
  //{
    return m_TvtGeom;
  //}
}