//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//

#include "Geometry/TvtGeom.h"
#include "Geometry/GeoUtil.h"
#include "Geometry/TvtID.h"
#include "TSystem.h"
#include "TGeoManager.h"
#include "TGeoNode.h"
#include "TGeoPhysicalNode.h"
#include "TString.h"
#include "TVector2.h"
#include "TVector3.h"
#include "TMath.h"
#include <iostream>
#include <iomanip>
#include <string>
#include <list>
#include <cassert>
#include "TGeoBBox.h"
#include "TGeoCompositeShape.h"
#include "TGeoBoolNode.h"
#include "TGeoTube.h"
#include "SniperKernel/SvcFactory.h"
#include "SniperKernel/SniperLog.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/Incident.h"
#include <TFile.h>
TvtGeom::TvtGeom()
    : m_geom(0)
    , m_fastInit(false)
    , m_verb(0)
{
}

bool TvtGeom::init()
{
    initRootGeo();

    return true;
}

bool TvtGeom::initRootGeo()
{
    readRootGeoFile();
    setPhyNodes();
    printChannel();
   
    return true;
}

bool TvtGeom::readRootGeoFile()
{
    //std::cout<<"////////////"<<std::endl;
    LogInfo<<"readRootGeoFile start"<<std::endl;
    //std::cout<<"////////////"<<std::endl;
    Int_t olderrlevel = gErrorIgnoreLevel;
    gErrorIgnoreLevel = kWarning;
    std::string geometryPath = getenv("GEOMETRYROOT");
    m_input_root_file=geometryPath+"/python/Geometry/sample-detsim1.root";
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

bool TvtGeom::setPhyNodes()
{
    LogInfo<<"SetTVTPhyNodes Start"<<std::endl;
    bool status = false;
    status = setPhyNodesAuto();
    LogInfo<<"SetTVTPhyNodes end"<<std::endl;

    return status;
}

int TvtGeom::getChannelType(TString name)
{
    if ( name.Contains("Pscint") ) return 1;
    //else return 2;

    return 0;
}

bool TvtGeom::setPhyNodesAuto()
{
    analyzeGeomStructure();

    TGeoPhysicalNode *phyNode = 0;

    int nNodesWallLevel = m_nodeChannelMother->GetNdaughters();
    //std::cout << "number of  Walls " << nNodesWallLevel << std::endl;

    int iChannel = 0;
    for (int iNode = 0; iNode < nNodesWallLevel; iNode++) {
	    TGeoNode *nodeWall = m_nodeChannelMother->GetDaughter(iNode);
	    TString phyNodeName = m_pathMother + "/" + nodeWall->GetName();
		int channelType = getChannelType(nodeWall->GetName());

		if (channelType == 1) {
			/*Identifier channelID = TvtID::id(phyNodeName.Data());
			int wall  = TvtID::wall_id(channelID);
			int pmt   = TvtID::pmt   (channelID);
			int strip = TvtID::strip (channelID);
			pmt = TvtID::pmt_other_end(pmt);
			Identifier channelID_otherend = TvtID::id(TvtID::getIntID(wall,pmt,strip));
			//Identifier channelID = TvtID::id(0,iChannel);
			PmtGeom* channel = 0;
			phyNode = m_geom->MakePhysicalNode(phyNodeName);
			channel = addChannel(channelID, phyNode, channelType);
			phyNode = m_geom->MakePhysicalNode(phyNodeName);
			channel = addChannel(channelID_otherend, phyNode, channelType);

         	//if (iNode == 0 && jNode == 0 && kNode == 0 && lNode == 0 && mNode == 0)
			//phyNode->Print();

		    iChannel++;*/
            Identifier channelID = TvtID::id(iChannel, 0);
            PmtGeom* channel = 0;
            phyNode = m_geom->MakePhysicalNode(phyNodeName);
            channel = addChannel(channelID, phyNode, channelType);
            //std::cout << phyNode->GetName() << std::endl;
            //phyNode->Print();
            iChannel++;
		}
	}
    //std::cout << "Auto TVTDetector size " << m_mapIdToChannel.size() << std::endl;
    return true;
}

PmtGeom* TvtGeom::addChannel(Identifier id, TGeoPhysicalNode *phyNode, int channelType)
{
    std::map<Identifier, PmtGeom*>::iterator it = m_mapIdToChannel.find(id);
    if ( it == m_mapIdToChannel.end() ) {
	PmtGeom* channel = new PmtGeom(id);
	channel->setPhyNode(phyNode);

	m_mapIdToChannel[id] = channel;

	return channel;
    }
    else {
        //std::cerr  << "TT Channel with ID " << id << " already added." << std::endl;
        //throw std::runtime_error("Adding TT channel to TvtGeom that was already added before");
        return it->second;
    }
}

PmtGeom* TvtGeom::getChannel(Identifier id)
{
    std::map<Identifier, PmtGeom*>::iterator it = m_mapIdToChannel.find(id);
    if ( it == m_mapIdToChannel.end() ) {
        //std::cerr << "id " << id << "(" << TvtID::wall_id(id) << ", " << TvtID::channel(id)
		    //<< ")'s Geom does not exist " << std::endl;
        return 0;
    }
    return m_mapIdToChannel[id];
}

double TvtGeom::getBoundingDx(){
    TGeoVolume * TVTAir_vol = m_nodeChannelMother->GetVolume();
    TGeoCompositeShape * TVTAir_shape = (TGeoCompositeShape*) TVTAir_vol->GetShape();
    double half_width  = TVTAir_shape->GetDX();
    return half_width*GeoUtil::cm2mm();
}

double TvtGeom::getBoundingDy(){
    TGeoVolume * TVTAir_vol = m_nodeChannelMother->GetVolume();
    TGeoCompositeShape * TVTAir_shape = (TGeoCompositeShape*) TVTAir_vol->GetShape();
    double half_width  = TVTAir_shape->GetDY();
    return half_width*GeoUtil::cm2mm();
}

double TvtGeom::getBoundingDz(){
    TGeoVolume * TVTAir_vol = m_nodeChannelMother->GetVolume();
    TGeoCompositeShape * TVTAir_shape = (TGeoCompositeShape*) TVTAir_vol->GetShape();
    double half_width  = TVTAir_shape->GetDZ();
    return half_width*GeoUtil::cm2mm();
}

std::map<Identifier, TVector3> * TvtGeom::ms_StripSizeMap = new std::map<Identifier, TVector3>;

TVector3 TvtGeom::GetStripSizeFromCache(PmtGeom* pmt){
    Identifier id = pmt->getId();
    if(ms_StripSizeMap->find(id) == ms_StripSizeMap->end()){
        TVector3 strip_center = pmt->getCenter();
        strip_center *= 1./GeoUtil::cm2mm();

        double box[3];
        strip_center.GetXYZ(box);

        box[0] += ((TGeoBBox*)(pmt->getPhyNode()->GetShape()))->GetDX();
        box[1] += ((TGeoBBox*)(pmt->getPhyNode()->GetShape()))->GetDY();
        box[2] += ((TGeoBBox*)(pmt->getPhyNode()->GetShape()))->GetDZ();

        double half_width[3];

        pmt->getPhyNode()->GetMatrix()->MasterToLocal(box, half_width);

        (*ms_StripSizeMap)[id] = TVector3(half_width)*GeoUtil::cm2mm();
    }
    return (*ms_StripSizeMap)[id];
}

double TvtGeom::getStripDx(PmtGeom* pmt){
    TVector3 strip_size = GetStripSizeFromCache(pmt);
    return std::abs(strip_size.x());
}

double TvtGeom::getStripDy(PmtGeom* pmt){
    TVector3 strip_size = GetStripSizeFromCache(pmt);
    return std::abs(strip_size.y());
}

double TvtGeom::getStripDz(PmtGeom* pmt){
    TVector3 strip_size = GetStripSizeFromCache(pmt);
    return std::abs(strip_size.z());
}
////////////////////////
void TvtGeom::analyzeGeomStructure()
{
    m_isChannelMotherFound = false;
    m_nodeMotherVec.clear();
    searchChannelMother( m_geom->GetTopNode() );
    searchWall();
    m_isChannelBottomFound = false;
    TvtID::setModuleMax( findPSNum()-1 );
    /*m_nodeBottomVec.clear();
    if ( findWallNum() > 0 ) {
        searchChannelBottom( m_nodeWall );
        m_pathBottomWall = setPathBottom();
        if ( getVerb() >= 1) std::cout << "pathBottom " << m_pathBottomWall << std::endl;
    }*/
}

void TvtGeom::searchWall()
{
    m_nWall = 0;
    //assert(m_nodeChannelMother);
    int nNodesWallLevel = m_nodeChannelMother->GetNdaughters();

    m_nodeWall = 0;
    for ( int iNode = 0; iNode < nNodesWallLevel; iNode++ ) {
        TString volChannelName = m_nodeChannelMother->GetDaughter(iNode)->GetVolume()->GetName();
        if ( volChannelName.Contains("Pscint")) {
            m_nodeWall = m_nodeChannelMother->GetDaughter(iNode);
            m_nWall++;
        }
    }
    //std::cout << "nPscint " << m_nWall << std::endl;
}

void TvtGeom::searchChannelMother(TGeoNode* node)
{   
    if ( !m_isChannelMotherFound ) {
      m_nodeMotherVec.push_back(node);
    }

    //assert(node);
    int nChild = node->GetNdaughters();
    if ( nChild > 130 && nChild < 200 ) {
        m_nodeChannelMother = node;
        m_isChannelMotherFound = true;
    }

    for (int iChild = 0; iChild < nChild && (!m_isChannelMotherFound); iChild++) {
        TGeoNode* childNode = node->GetDaughter(iChild);
        searchChannelMother(childNode);
        if ( !m_isChannelMotherFound ) {
            m_nodeMotherVec.pop_back();
        }
    } 

    setPathMother();
}

void TvtGeom::setPathMother()
{
    m_pathMother = TString("");

    for (int iNode = 0; iNode < (int)m_nodeMotherVec.size(); iNode++) {
        m_pathMother += "/";
        m_pathMother += m_nodeMotherVec[iNode]->GetName();
    }
}

void TvtGeom::printChannel()
{
    LogInfo<<"printPS start"<<std::endl;
    for (ChannelMapIt it = m_mapIdToChannel.begin(); it != m_mapIdToChannel.end(); it++) {
        Identifier pmtID = it->first;
        PmtGeom *pmt = it->second;
        pmt->print(3);
        
    }
    LogInfo<<"printPS end"<<std::endl;    


}
    



