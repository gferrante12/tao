//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//

#include "TAOGeometry/CdGeom.h"
#include "TAOGeometry/SiPMGeom.h"
#include "TAOGeometry/GeoUtil.h"

#include "TAOIDService/Identifier.h"
#include "TAOIDService/TAODetectorID.h"
#include "TAOIDService/CdID.h"
#include "TAOIDService/TAOIDService.h"

//#include "RootIOSvc/IInputSvc.h"

#include "SniperKernel/SvcFactory.h"
#include "SniperKernel/SniperLog.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/Incident.h"

#include "TGeoManager.h"
#include "TGeoNode.h"
#include "TGeoPhysicalNode.h"
#include "TGeoSphere.h"
#include "TGeoCompositeShape.h"
#include "TGeoBoolNode.h"
#include "TGeoTube.h"

#include <TFile.h>
#include <TError.h>
#include "TSystem.h"
#include "TString.h"
#include "TVector2.h"
#include "TVector3.h"
#include "TMath.h"

#include <assert.h>
#include <iostream>
#include <iomanip>
#include <string>
#include <list>
#include <cassert>
#include <vector>



CdGeom::CdGeom()
:  m_geom(0), m_fastInit(false)
{

}

CdGeom::~CdGeom()
{

}


bool CdGeom::init()
{
    initRootGeo();
    return true;
}

bool CdGeom::initRootGeo()
{   
    idServ = TAOIDService::getIdServ();
    idServ->init_cd();
    readRootGeoFile();
    SetPhyNodes();
    orgnizeSiPM();
    printSiPM();
    return true;
}

/*
bool CdGeom::initialize()
{

    readRootGeoFile();
    SetPhyNodes();
    orgnizeSiPM();
    printSiPM();
    return true;
}
*/



/*
bool CdGeom::finalize()
{
    // if need to output the geometry
    //
    return true;
}
*/

void CdGeom::SimGeomExecute()
{
    /*
    readRootGeoFile();
    SetPhyNodes();
    orgnizeSiPM();
    */
}

void CdGeom::geom(TGeoManager* v)
{
    m_geom = v;
}

TGeoManager* CdGeom::geom()
{
    if (!m_geom) {
        readRootGeoFile();
    }
    return m_geom;
}

void CdGeom::readRootGeoFile()
{
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"readRootGeoFile start"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
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
        //Incident::fire("StopRun");
        //getParent()->stop();
        return;
    }
    if (gGeoManager) 
    {
        m_geom = gGeoManager;
    }
    else
    {
        m_geom = TGeoManager::Import(m_input_root_file.c_str(),
                                    "TaoGeom");
    }
    if (m_geom) {
        LogInfo << "load geometry successfully" << std::endl;
    }
    gErrorIgnoreLevel = olderrlevel;
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"readRootGeoFile end"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
}

bool CdGeom::SetPhyNodes()
{
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"SetCDPhyNodes start"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
    bool status = false;
    status = setPhyNodesAuto();
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"SetCDPhyNodes end"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
    return status;
}

bool CdGeom::setPhyNodesAuto()
{
    analyzeGeomStructure();
    TGeoPhysicalNode *phyNode = 0;
    int nNodesSiPMLevel = m_nodeSiPMMother->GetNdaughters();
    int iSiPM = 0;
    
    for (int iNode = 0; iNode < nNodesSiPMLevel; iNode++) {
        TGeoNode *nodeSiPM = m_nodeSiPMMother->GetDaughter(iNode);
        TString phyNodeName = m_pathMother + "/" + nodeSiPM->GetName();
        int SiPMType = getSiPMType(nodeSiPM->GetName());
        if(SiPMType==1)
        {
            Identifier SiPMID; 
            //Identifier SiPMID = CdID::id(iSiPM, 0);
            if(idServ->fCdChannel2Id(iSiPM*2)==Identifier(0xFFFFFFFFFFFFFFFF))
            {
                SiPMID = CdID::id(iSiPM, 0);
            }
            else
            {
                SiPMID = idServ->fCdChannel2Id(iSiPM*2);
            }
            //Identifier SiPMID = idServ->fCdChannel2Id(iSiPM*2);
            SiPMGeom* SiPM = 0;
            //m_fastInit I don't use

            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            SiPM = addSiPM(SiPMID, phyNode, SiPMType); 
            iSiPM++;
        }
    
    }
    return true;
}
SiPMGeom* CdGeom::FindSiPM(int channelid)
{
    //CdGeom a;
    int sipmid1=SiPMGeom::ChannelIDToSiPMID(channelid);
    Identifier sipmid2;
    //Identifier sipmid2 = CdID::id(sipmid1, 0);
    //Identifier sipmid2 = idServ->fCdChannel2Id(sipmid1*2);
    if(idServ->fCdChannel2Id(sipmid1*2)==Identifier(0xFFFFFFFFFFFFFFFF))
    {
        sipmid2 = CdID::id(sipmid1, 0);
    }
    else
    {
        sipmid2 = idServ->fCdChannel2Id(sipmid1*2);
    }
    return getSiPM(sipmid2);

}
void CdGeom::analyzeGeomStructure()
{
    m_isSiPMMotherFound = false;
    m_nodeMotherVec.clear();
    searchSiPMMother( m_geom->GetTopNode() );
    searchSiPM();
    CdID::setModuleMax( findSiPMNum()-1 );
}

void CdGeom::searchSiPMMother(TGeoNode* node)
{
    if ( !m_isSiPMMotherFound ) {
      m_nodeMotherVec.push_back(node);
    }
    assert(node);
    int nChild = node->GetNdaughters();
        if ( nChild > 3500 ) {  // assume the total SiPM in CD is greater than 10000, so this level
        m_nodeSiPMMother = node;
        m_isSiPMMotherFound = true;
    }

    for (int iChild = 0; iChild < nChild && (!m_isSiPMMotherFound); iChild++) {
        TGeoNode* childNode = node->GetDaughter(iChild);
        searchSiPMMother(childNode);
        if ( !m_isSiPMMotherFound ) {
            m_nodeMotherVec.pop_back();
        }
    }
    setPathMother();
}

void CdGeom::setPathMother()
{
    m_pathMother = TString("");
    for (int iNode = 0; iNode < (int)m_nodeMotherVec.size(); iNode++) {
        m_pathMother += "/";
        m_pathMother += m_nodeMotherVec[iNode]->GetName();
        //if ( getVerb() >= 3) std::cout << m_nodeMotherVec[iNode]->GetName() << std::endl;
    }
}

void CdGeom::searchSiPM()
{
    m_nSiPM = 0;
    m_nodeSiPM = 0;
    assert(m_nodeSiPMMother);
    int nNodesSiPMLevel = m_nodeSiPMMother->GetNdaughters();
    for ( int iNode = 0; iNode < nNodesSiPMLevel; iNode++ ) {
       TString volSiPMName = m_nodeSiPMMother->GetDaughter(iNode)->GetVolume()->GetName();
       if(volSiPMName.Contains("SiPM"))
       {
            m_nSiPM++;
            m_nodeSiPM = m_nodeSiPMMother->GetDaughter(iNode);
       }      
    }
}


unsigned int CdGeom::findSiPMNum() 
{ 
    return m_nSiPM; 
}
int CdGeom::getSiPMType(TString name)
{
    if ( name.Contains("SiPad")) return 1;
    return 0;
}




SiPMGeom* CdGeom::addSiPM(Identifier id, TGeoPhysicalNode *phyNode, int SiPMType)
{
    std::map<Identifier, SiPMGeom*>::iterator it = m_mapIdToSiPM.find(id);
    if ( it == m_mapIdToSiPM.end() ) {
        SiPMGeom* SiPM = new SiPMGeom(id);
        SiPM->setPhyNode(phyNode);

        /*if (SiPMType == 1) SiPM->set20inch(true); 
        else if (SiPMType == 2) SiPM->set20inch(false);*/

        m_mapIdToSiPM[id] = SiPM;

        return SiPM;
    }
    else {
        return it->second;
    }
}

bool CdGeom::orgnizeSiPM()
{
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"orgnizeSiPM start"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
    int layer = -1;
    int azimuth = 0;
    std::vector<int> azimuthOnLayer;
    TVector3 center;
    TVector3 center_old(-9, -9, -9);
    for (SiPMMapIt it = m_mapIdToSiPM.begin(); it != m_mapIdToSiPM.end(); it++) {
        Identifier SiPMID = it->first;
        SiPMGeom *SiPM = it->second;
        center = SiPM->getCenter();
        if ( fabs(center.z() - center_old.z()) > 3 ) //maybe charge the value
        {
            if (layer >= 0) {
                //if ( getVerb() >= 3) std::cout << "layer " << layer << " azimuth " << azimuth << std::endl;
                azimuthOnLayer.push_back(azimuth+1);
            }
            layer++;
            azimuth = 0;
        }
        else { // same layer
            azimuth++;
        }

        SiPM->setLayer(layer);
        SiPM->setAzimuth(azimuth);
        SiPM->setSiPM(0);
        center_old = center;
        

    
    }
    azimuthOnLayer.push_back(azimuth+1);
    for (std::vector<int>::iterator it = azimuthOnLayer.begin(); it != azimuthOnLayer.end(); it++) {
        m_azimuthNum.push_back(*it);
    }
    m_layerNum = m_azimuthNum.size();
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"orgnizeSiPM end"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
    return true;
}

void CdGeom::printSiPM()
{
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"printSiPM start"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
    
    LogInfo << "Print first 17 SiPM... " << std::endl;
    for (SiPMMapIt it = m_mapIdToSiPM.begin(); it != m_mapIdToSiPM.end(); it++) {
        Identifier SiPMID = it->first;
        SiPMGeom *SiPM = it->second;
        //std::cout << CdID::module(SiPMID) << std::endl;
        //if (CdID::module(SiPMID) < 17) {
        SiPM->print();
    }
    /*
    LogInfo << "Print last SiPM on each layer..." << std::endl;
    for (int layer = 0; layer < getLayerNum(); layer++) {
        getSiPM(layer, getAzimuthNum(layer)-1, 0)->print();
    }

    int KS = 6;
    int NSiPM=0;
    for (int layer = 0; layer < getLayerNum(); layer++) {
        LogInfo << "Layer " << std::setw(KS) << layer 
            << " AzimuthNum " << std::setw(KS) << getAzimuthNum(layer)
            << std::endl;

        NSiPM+=getAzimuthNum(layer);

    }
    
    LogInfo << "LayerNum " << getLayerNum() << std::endl;
    LogInfo <<"SiPMNum "<<NSiPM<<std::endl;*/
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"printSiPM end"<<std::endl;
    //std::cout<<"////////////"<<std::endl;

}

int CdGeom::getAzimuthNum(int layer)
{
    if ( layer >= 0 && layer < (int)m_azimuthNum.size() ) {
        return m_azimuthNum[layer];
    }
    else {
        //std::cout << "CdGeom::getAzimuthNum at layer " << layer << " is wrong" << std::endl;
        return -9;
    }
}

SiPMGeom* CdGeom::getSiPM(Identifier id)
{
    std::map<Identifier, SiPMGeom*>::iterator it = m_mapIdToSiPM.find(id);
    if ( it == m_mapIdToSiPM.end() ) {
        /*std::cerr << "id " << id << "(" << CdID::module(id) << ", " << CdID::SiPM(id)
            << ")'s SiPMGeom does not exist " << std::endl;*/
        return 0;
    }
    return m_mapIdToSiPM[id];
}

SiPMGeom* CdGeom::getSiPM(int layer, int azimuth, int SiPM)
{
    int module = 0;
    for (int i = 0; i < layer; i++) {
        module += getAzimuthNum(i);
    }
    module += azimuth;

    //if ( getVerb() >= 2) std::cout << "layer " << layer << " azimuth " << azimuth << " module " << module << std::endl;
    Identifier SiPMID;
    if(idServ->fCdChannel2Id(module*2)==Identifier(0xFFFFFFFFFFFFFFFF))
    {
        SiPMID = CdID::id(module, 0);
    }
    else
    {
        SiPMID = idServ->fCdChannel2Id(module*2);
    }
    
    //Identifier SiPMID = CdID::id(module, SiPM);
    //Identifier SiPMID = idServ->fCdChannel2Id(module*2);
    return getSiPM(SiPMID);
}


