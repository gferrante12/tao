//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#include "TAOGeometry/WtGeom.h"
#include "TAOGeometry/GeoUtil.h"
#include "TAOIDService/WtID.h"
#include "TSystem.h"
#include "TGeoManager.h"
#include "TGeoNode.h"
#include "TGeoPhysicalNode.h"
#include "TGeoTube.h"
#include "TString.h"
#include "TVector2.h"
#include "TVector3.h"
#include "TMath.h"
#include <iostream>
#include <iomanip>
#include <string>
#include <list>
#include <cassert>
#include "SniperKernel/SvcFactory.h"
#include "SniperKernel/SniperLog.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/Incident.h"
#include <TFile.h>
WtGeom::WtGeom()
    : m_geom(0)
    , m_fastInit(false)
    , m_layerNum(0)
    , m_verb(0)
{
}

WtGeom::~WtGeom()
{
}

bool WtGeom::init()
{
    initRootGeo();

    return true;
}

bool WtGeom::initRootGeo()
{
    readRootGeoFile();
    setPhyNodes();
    orgnizePmt();
    printPmt();

    return true;
}

bool WtGeom::readRootGeoFile()
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
        // Incident::fire("StopRun");
        //getParent()->stop();
        return false;
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
    return true;
}

bool WtGeom::setPhyNodes()
{
    LogInfo<<"SetWTPhyNodes Start"<<std::endl;
    bool status = false;
    // if ( m_useDefaultGeom ) {
    //     status = setPhyNodesManually();
    // }
    // else {
    //     status = setPhyNodesAuto();
    // }
    status = setPhyNodesAuto();
    LogInfo<<"SetWTPhyNodes end"<<std::endl;

    return status;
}

int WtGeom::getPmtType(TString name)
{
    if ( name.Contains("PMT")) return 1;
    return 0;
}

bool WtGeom::setPhyNodesAuto()
{
    analyzeGeomStructure();

    TGeoPhysicalNode *phyNode = 0;
    int nNodesPmtLevel1 = m_nodePmtMother1->GetNdaughters();
    int nNodesPmtLevel2 = m_nodePmtMother2->GetNdaughters();
    int nNodesPmtLevel3 = m_nodePmtMother3->GetNdaughters();
    int iPmt = 1;
    for (int iNode = 0; iNode < 64; iNode++) 
    {
        TGeoNode *nodePmt = m_nodePmtMother1->GetDaughter(iNode);
        TString phyNodeName = m_pathMother1 + "/" + nodePmt->GetName();
        int pmtType = getPmtType(nodePmt->GetName());
        if ( pmtType == 1 ) {
            Identifier pmtID = WtID::id(iPmt, 0);
            PmtGeom* pmt = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            pmt = addPmt(pmtID, phyNode, pmtType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iPmt++;
        }
    }
    for (int iNode = 0; iNode < 95; iNode++) 
    {
        TGeoNode *nodePmt = m_nodePmtMother2->GetDaughter(iNode);
        TString phyNodeName = m_pathMother2 + "/" + nodePmt->GetName();
        int pmtType = getPmtType(nodePmt->GetName());
        if ( pmtType == 1 ) {
            Identifier pmtID = WtID::id(iPmt, 0);
            PmtGeom* pmt = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            pmt = addPmt(pmtID, phyNode, pmtType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iPmt++;
        }
    }
    for (int iNode = 0; iNode < 110; iNode++) 
    {
        TGeoNode *nodePmt = m_nodePmtMother3->GetDaughter(iNode);
        TString phyNodeName = m_pathMother3 + "/" + nodePmt->GetName();
        int pmtType = getPmtType(nodePmt->GetName());
        if ( pmtType == 1 ) {
            Identifier pmtID = WtID::id(iPmt, 0);
            PmtGeom* pmt = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            pmt = addPmt(pmtID, phyNode, pmtType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iPmt++;
        }
    }
    ///////////////////////////////////
    for (int iNode = 64; iNode < 73; iNode++) 
    {
        TGeoNode *nodePmt = m_nodePmtMother1->GetDaughter(iNode);
        TString phyNodeName = m_pathMother1 + "/" + nodePmt->GetName();
        int pmtType = getPmtType(nodePmt->GetName());
        if ( pmtType == 1 ) {
            Identifier pmtID = WtID::id(iPmt, 0);
            PmtGeom* pmt = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            pmt = addPmt(pmtID, phyNode, pmtType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iPmt++;
        }
    }
    for (int iNode = 95; iNode < 105; iNode++) 
    {
        TGeoNode *nodePmt = m_nodePmtMother2->GetDaughter(iNode);
        TString phyNodeName = m_pathMother2 + "/" + nodePmt->GetName();
        int pmtType = getPmtType(nodePmt->GetName());
        if ( pmtType == 1 ) {
            Identifier pmtID = WtID::id(iPmt, 0);
            PmtGeom* pmt = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            pmt = addPmt(pmtID, phyNode, pmtType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iPmt++;
        }
    }
    for (int iNode = 110; iNode < 122; iNode++) 
    {
        TGeoNode *nodePmt = m_nodePmtMother3->GetDaughter(iNode);
        TString phyNodeName = m_pathMother3 + "/" + nodePmt->GetName();
        int pmtType = getPmtType(nodePmt->GetName());
        if ( pmtType == 1 ) {
            Identifier pmtID = WtID::id(iPmt, 0);
            PmtGeom* pmt = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            pmt = addPmt(pmtID, phyNode, pmtType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iPmt++;
        }
    }
    std::cout << "Auto WtDetector Pmt size " << m_mapIdToPmt.size() << std::endl;
    return true;
}

void WtGeom::analyzeGeomStructure()
{

    m_isPmtMotherFound = false;
    m_nodeMotherVec1.clear();
    searchPmtMother1( m_geom->GetTopNode() );
    m_isPmtMotherFound = false;
    m_nodeMotherVec2.clear();
    searchPmtMother2( m_geom->GetTopNode() );
    m_isPmtMotherFound = false;
    m_nodeMotherVec3.clear();
    searchPmtMother3( m_geom->GetTopNode() );
    searchPmt();
    WtID::setModuleMax( findPmtNum()-1 );
}

void WtGeom::searchPmt()
{
    m_nPmt = 1;
    //assert(m_nodePmtMother);
    int nNodesPmtLevel1 = m_nodePmtMother1->GetNdaughters();
    int nNodesPmtLevel2 = m_nodePmtMother2->GetNdaughters();
    int nNodesPmtLevel3 = m_nodePmtMother3->GetNdaughters();

//    m_volPmt = m_nodePmtMother->GetDaughter(nNodesPmtLevel/2)->GetVolume();
//    TString volPmtName = m_volPmt->GetName();
//    if ( getVerb() >= 1) std::cout << "PmtName " << volPmtName << std::endl;

    for ( int iNode = 0; iNode < nNodesPmtLevel1; iNode++ ) {
        TString volPmtName = m_nodePmtMother1->GetDaughter(iNode)->GetVolume()->GetName();
        if(volPmtName.Contains("PMT"))
        {
            m_nPmt++;
            m_nodePmt = m_nodePmtMother1->GetDaughter(iNode);
        } 
    }
    for ( int iNode = 0; iNode < nNodesPmtLevel2; iNode++ ) {
        TString volPmtName = m_nodePmtMother2->GetDaughter(iNode)->GetVolume()->GetName();
        if(volPmtName.Contains("PMT"))
        {
            m_nPmt++;
            m_nodePmt = m_nodePmtMother2->GetDaughter(iNode);
        } 
    }
    for ( int iNode = 0; iNode < nNodesPmtLevel3; iNode++ ) {
        TString volPmtName = m_nodePmtMother3->GetDaughter(iNode)->GetVolume()->GetName();
        if(volPmtName.Contains("PMT"))
        {
            m_nPmt++;
            m_nodePmt = m_nodePmtMother3->GetDaughter(iNode);
        } 
    }
    //std::cout << "nPmt " << m_nPmt<<std::endl;
}

void WtGeom::searchPmtMother1(TGeoNode* node)
{   
    if ( !m_isPmtMotherFound ) {
      m_nodeMotherVec1.push_back(node);
    }

    assert(node);
    int nChild = node->GetNdaughters();
    if ( nChild == 73 ) {  
        m_nodePmtMother1 = node;
        m_isPmtMotherFound = true;
    }

    for (int iChild = 0; iChild < nChild && (!m_isPmtMotherFound); iChild++) {
        TGeoNode* childNode = node->GetDaughter(iChild);
        searchPmtMother1(childNode);
        if ( !m_isPmtMotherFound ) {
            m_nodeMotherVec1.pop_back();
        }
    } 

    setPathMother1();
}   

void WtGeom::setPathMother1()
{
    m_pathMother1 = TString("");
    //if ( getVerb() >= 3) std::cout << m_nodeMotherVec.size() << std::endl;

    for (int iNode = 0; iNode < (int)m_nodeMotherVec1.size(); iNode++) {
        m_pathMother1 += "/";
        m_pathMother1 += m_nodeMotherVec1[iNode]->GetName();
        //if ( getVerb() >= 3) std::cout << m_nodeMotherVec[iNode]->GetName() << std::endl;
    }
}

void WtGeom::searchPmtMother2(TGeoNode* node)
{   
    if ( !m_isPmtMotherFound ) {
      m_nodeMotherVec2.push_back(node);
    }

    assert(node);
    int nChild = node->GetNdaughters();
    if ( nChild == 105 ) {  
        m_nodePmtMother2 = node;
        m_isPmtMotherFound = true;
    }

    for (int iChild = 0; iChild < nChild && (!m_isPmtMotherFound); iChild++) {
        TGeoNode* childNode = node->GetDaughter(iChild);
        searchPmtMother2(childNode);
        if ( !m_isPmtMotherFound ) {
            m_nodeMotherVec2.pop_back();
        }
    } 

    setPathMother2();
}   

void WtGeom::setPathMother2()
{
    m_pathMother2 = TString("");
    //if ( getVerb() >= 3) std::cout << m_nodeMotherVec.size() << std::endl;

    for (int iNode = 0; iNode < (int)m_nodeMotherVec2.size(); iNode++) {
        m_pathMother2 += "/";
        m_pathMother2 += m_nodeMotherVec2[iNode]->GetName();
        //if ( getVerb() >= 3) std::cout << m_nodeMotherVec[iNode]->GetName() << std::endl;
    }
}

void WtGeom::searchPmtMother3(TGeoNode* node)
{   
    if ( !m_isPmtMotherFound ) {
      m_nodeMotherVec3.push_back(node);
    }

    assert(node);
    int nChild = node->GetNdaughters();
    if ( nChild == 122 ) {  
        m_nodePmtMother3 = node;
        m_isPmtMotherFound = true;
    }

    for (int iChild = 0; iChild < nChild && (!m_isPmtMotherFound); iChild++) {
        TGeoNode* childNode = node->GetDaughter(iChild);
        searchPmtMother3(childNode);
        if ( !m_isPmtMotherFound ) {
            m_nodeMotherVec3.pop_back();
        }
    } 

    setPathMother3();
}   

void WtGeom::setPathMother3()
{
    m_pathMother3 = TString("");
    //if ( getVerb() >= 3) std::cout << m_nodeMotherVec.size() << std::endl;

    for (int iNode = 0; iNode < (int)m_nodeMotherVec3.size(); iNode++) {
        m_pathMother3 += "/";
        m_pathMother3 += m_nodeMotherVec3[iNode]->GetName();
        //if ( getVerb() >= 3) std::cout << m_nodeMotherVec[iNode]->GetName() << std::endl;
    }
}

PmtGeom* WtGeom::addPmt(Identifier id, TGeoPhysicalNode *phyNode, int pmtType)
{
    std::map<Identifier, PmtGeom*>::iterator it = m_mapIdToPmt.find(id);
    if ( it == m_mapIdToPmt.end() ) {
        PmtGeom* pmt = new PmtGeom(id);
        pmt->setPhyNode(phyNode);

        m_mapIdToPmt[id] = pmt;

        return pmt;
    }
    else {
        return it->second;
    }
}

PmtGeom* WtGeom::getPmt(Identifier id)
{
    std::map<Identifier, PmtGeom*>::iterator it = m_mapIdToPmt.find(id);
    if ( it == m_mapIdToPmt.end() ) {
        //std::cerr << "id " << id << "(" << WtID::module(id) << ", " << WtID::pmt(id)
           // << ")'s PmtGeom does not exist " << std::endl;
        return 0;
    }
    return m_mapIdToPmt[id];
}

PmtGeom* WtGeom::getPmt(int layer, int azimuth, int pmt)
{
    int module = 0;
    for (int i = 0; i < layer; i++) {
        module += getAzimuthNum(i);
    }
    module += azimuth;

    //if ( getVerb() >= 2) std::cout << "layer " << layer << " azimuth " << azimuth << " module " << module << std::endl;
    Identifier pmtID = WtID::id(module, pmt);
  
    return getPmt(pmtID);
}

void WtGeom::printPmt()
{
    //std::cout << "waterpool " << __func__ << " begin " << getVerb() << std::endl;
    LogInfo<<"printPMT start"<<std::endl;
    for (PmtMapIt it = m_mapIdToPmt.begin(); it != m_mapIdToPmt.end(); it++) {
        Identifier pmtID = it->first;
        PmtGeom *pmt = it->second;
        //std::cout << WtID::module(pmtID) << std::endl;
        pmt->print();
    }
    LogInfo<<"printPMT end"<<std::endl;
}

bool WtGeom::orgnizePmt()
{
    LogInfo<<"orgnizePMT start"<<std::endl;
    int layer = -1;
    int azimuth = 0;
    std::vector<int> azimuthOnLayer;
    TVector3 center;
    TVector3 center_old(-9, -9, -9);

    for (PmtMapIt it = m_mapIdToPmt.begin(); it != m_mapIdToPmt.end(); it++) {
        Identifier pmtID = it->first;
        PmtGeom *pmt = it->second;
        center = pmt->getCenter();
        if ( fabs(center.z() - center_old.z()) > 3 ) { // new layer
            if (layer >= 0) {
                azimuthOnLayer.push_back(azimuth+1);
            }
            layer++;
            azimuth = 0;
        }
        else { // same layer
            azimuth++;
        }

        pmt->setLayer(layer);
        pmt->setAzimuth(azimuth);
        pmt->setPmt(0);
        center_old = center;
    }
    azimuthOnLayer.push_back(azimuth+1);
    for (std::vector<int>::iterator it = azimuthOnLayer.begin(); it != azimuthOnLayer.end(); it++) {
        m_azimuthNum.push_back(*it);
    }
    m_layerNum = m_azimuthNum.size();

    LogInfo<<"orgnizePMT end"<<std::endl;

    return true;
}

int WtGeom::getAzimuthNum(int layer)
{
    if ( layer >= 0 && layer < (int)m_azimuthNum.size() ) {
        return m_azimuthNum[layer];
    }
    else {
        std::cerr << "WtGeom::getAzimuthNum at layer " << layer << " is wrong" << std::endl;
        return -9;
    }
}

