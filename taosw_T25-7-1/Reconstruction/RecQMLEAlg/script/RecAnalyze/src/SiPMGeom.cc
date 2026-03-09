//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/SiPMGeom.h"
#include "Geometry/GeoUtil.h"
#include "Geometry/SimGeomSvc.h"
#include "Geometry/Identifier.h"
#include "TMath.h"
#include "TVector3.h"
#include "TVector2.h"
#include "TGeoManager.h"
#include "TGeoPhysicalNode.h"
#include <iostream>
#include <iomanip>
#include <string>

SiPMGeom::SiPMGeom()
{
}

SiPMGeom::~SiPMGeom()
{
}

SiPMGeom::SiPMGeom(Identifier id)
    : m_id(id),
      //m_is20inch(true),
      m_layer(0),
      m_azimuth(0),
      m_SiPM(0)
{
    m_phyNode = 0;
    m_center = TVector3(0, 0, 0);
    m_axisDir = TVector3(0,0,1);
}

bool SiPMGeom::setPhyNode(TGeoPhysicalNode *phyNode)
{
  m_phyNode = phyNode;
  return true;
}

TGeoPhysicalNode* SiPMGeom::getPhyNode()
{
    if (m_phyNode) {
        return m_phyNode;
    }
    else {
        std::cerr << "SiPMGeom::GetPhyNode Id " << m_id << " does not exist!" << std::endl;
        return 0;
    }
}

void SiPMGeom::getGlobal(double *local, double *global)
{
    //std::cout << local[0] << " " << local[1] << " " << local[2] << std::endl;
    //std::cout << global[0] << " " << global[1] << " " << global[2] << std::endl;
    getPhyNode()->GetMatrix(-1*getPhyNode()->GetLevel())->LocalToMaster(local, &global[0]);
    //std::cout << local[0] << " " << local[1] << " " << local[2] << std::endl;
    //std::cout << global[0] << " " << global[1] << " " << global[2] << std::endl;
}

void SiPMGeom::getLocal(double *local, double *global)
{
    //std::cout << local[0] << " " << local[1] << " " << local[2] << std::endl;
    //std::cout << global[0] << " " << global[1] << " " << global[2] << std::endl;
    getPhyNode()->GetMatrix(-1*getPhyNode()->GetLevel())->MasterToLocal(global, &local[0]);
    //std::cout << local[0] << " " << local[1] << " " << local[2] << std::endl;
    //std::cout << global[0] << " " << global[1] << " " << global[2] << std::endl;
}

TVector3 SiPMGeom::getGlobal(TVector3 localVec)
{
    double local[3]  = { localVec[0]*GeoUtil::mm2cm(),
                         localVec[1]*GeoUtil::mm2cm(), 
                         localVec[2]*GeoUtil::mm2cm()
                       };
    double global[3] = {0.0, 0.0, 1.0};
    getGlobal(local, global);

    return TVector3( global[0]*GeoUtil::cm2mm(),
                     global[1]*GeoUtil::cm2mm(),
                     global[2]*GeoUtil::cm2mm()
                   );
}

TVector3 SiPMGeom::getLocal(TVector3 globalVec)
{
  double global[3]  = { globalVec[0]*GeoUtil::mm2cm(),
                        globalVec[1]*GeoUtil::mm2cm(),
                        globalVec[2]*GeoUtil::mm2cm()
                      };
  double local[3] = {0.0, 0.0, 1.0};
  getLocal(local, global);

  return TVector3( local[0]*GeoUtil::cm2mm(),
                   local[1]*GeoUtil::cm2mm(),
                   local[2]*GeoUtil::cm2mm()
                 );
}

TVector3 SiPMGeom::getCenter()
{
    if ( m_phyNode ) {
        return getGlobal(TVector3(0, 0, 0));
    }
    else {
        return m_center;
    }
}

double SiPMGeom::getPhi()  
{

    //return getCenter().Phi();
    double xx=getCenter().X()+2446;
    double yy=getCenter().Y()+2446;

    if(xx>=0 && yy>=0)
    {
        return atan(yy/xx);
    }
    if(xx<0 && yy>=0)
    {
        return atan(yy/xx)+M_PI;
    }
    if(xx<0 && yy<0)
    {
        return atan(yy/xx)+M_PI;
    }
    if(xx>=0 && yy<0)
    {
        return atan(yy/xx)+2*M_PI;
    }

   
}

TVector3 SiPMGeom::getAxisDir()
{
    if ( m_phyNode ) {   
        //TVector3 center = getCenter();
        TVector3 re_center = getCenter();
        TVector3 center(re_center.X()+2446, re_center.Y()+2446, re_center.Z()+8212.8);

        TVector3 ref = getGlobal(TVector3(0,0,1.0)); // (0,0,200.0)

        return ref-center;
    }
    else {
        return m_axisDir;
    }
}

TVector2 SiPMGeom::getCenterAitoff()
{
    double theta = getTheta();
    double phi = getPhi();
    
    double org_theta = theta*TMath::RadToDeg();
    double org_phi   = phi*TMath::RadToDeg();
    // transformation of coordinates
    org_phi = 180.0 - org_phi;
    org_theta = 90.0 - org_theta;

    double project_x, project_y;
    GeoUtil::projectAitoff2xy(org_phi, org_theta, project_x, project_y);

    return TVector2(project_x, project_y);
}

int SiPMGeom::getSiPMID (Identifier id)
{
    
    int iid=0;
    if(id.getString().at(5)>='0'&&id.getString().at(5)<='9')
    {
        iid+=16*16*(id.getString().at(5)-48);
    }
    else
    {
        iid+=16*16*(id.getString().at(5)-87);
    }
    if(id.getString().at(6)>='0'&&id.getString().at(6)<='9')
    {
        iid+=16*(id.getString().at(6)-48);
    }
    else
    {
        iid+=16*(id.getString().at(6)-87);
    }
    if(id.getString().at(7)>='0'&&id.getString().at(7)<='9')
    {
        iid+=(id.getString().at(7)-48);
    }
    else
    {
        iid+=(id.getString().at(7)-87);
    }
    return iid;

}

int SiPMGeom::ChannelIDToSiPMID(int channelid)
{
    int sipmid =int(channelid/2); 
    return sipmid;
}

void SiPMGeom::print()
{
    int KS = 6;
    TVector3 center = getCenter();
    //TVector3 dir    = getAxisDir();
    //TVector2 atioff = getCenterAitoff();

    std::cout << " SiPM "      << std::setw(KS) << m_id
              //<< " SiPM "      << std::setw(KS) << m_id.getString().at(5)<<m_id.getString().at(6)<<m_id.getString().at(7)
              << " SiPM "      << std::setw(KS) << getSiPMID(m_id)
              << " Center("  << std::setw(2*KS) << center.x()
              << ", "        << std::setw(2*KS) << center.y()
              << ", "        << std::setw(2*KS) << center.z() << ")"
              << " Layer "   << std::setw(  KS) << getLayer()
              << " Azimuth " << std::setw(  KS) << getAzimuth()
              <<" phi "<<std::setw(  KS) <<getPhi()
              <<" theta "<<std::setw(  KS) <<getTheta()
              //<< " LatLong(" << std::setw(2*KS) << 90-center.Theta()*TMath::RadToDeg()
              //<< ", "        << std::setw(2*KS) << center.Phi()*TMath::RadToDeg() << ")"
//            << " R "       << std::setw(2*KS) << center.Mag()
              //<< " Dir("     << std::setw(2*KS) << dir.Theta()
              //<< ", "        << std::setw(2*KS) << dir.Phi() << ")"
//            << " Aitoff "  << std::setw(2*KS) << atioff.X()
//            << ", "        << std::setw(2*KS) << atioff.Y()
              <<" R( "<<sqrt((center.x()+2446)*(center.x()+2446)+(center.y()+2446)*(center.y()+2446)+(center.z()+8212.8)*(center.z()+8212.8))<<" )"
              <<" Channelid"<<std::setw(KS)<< getSiPMID(m_id)*2
              << " Center("  << std::setw(2*KS) << getChannelCenter(getSiPMID(m_id)*2).x()
              << ", "        << std::setw(2*KS) << getChannelCenter(getSiPMID(m_id)*2).y()
              << ", "        << std::setw(2*KS) << getChannelCenter(getSiPMID(m_id)*2).z() << ")"
              <<" Channelid"<<std::setw(KS)<< getSiPMID(m_id)*2+1
              << " Center("  << std::setw(2*KS) << getChannelCenter(getSiPMID(m_id)*2+1).x()
              << ", "        << std::setw(2*KS) << getChannelCenter(getSiPMID(m_id)*2+1).y()
              << ", "        << std::setw(2*KS) << getChannelCenter(getSiPMID(m_id)*2+1).z() << ")"
              << std::endl;
    
}

void SiPMGeom::print(int verb)
{
    int KS = 6;
    TVector3 center = getCenter();
    if (verb == 3) {
    std::cout << "Channel " << std::setw(KS) << m_id
    
    	      << " Center("  << std::setw(2*KS) << center.x()
    	      << ", "        << std::setw(2*KS) << center.y()
	      << ", "        << std::setw(2*KS) << center.z() << ")"
	      << std::endl;
    }
}


bool SiPMGeom::isCrossed(const TVector3 vtx, const TVector3 dir)
{
    TVector3 localVtx = getLocal(vtx);
    TVector3 localDir = getLocal(vtx+dir) - localVtx;
    //int KS = 6;
    //std::cout << "SiPM " << std::setw(KS) << getLayer() << std::setw(KS) << getAzimuth() << std::endl;
    //localVtx.Print();
    //localDir.Print();

    // Must transform to cm system because all shape dimensions uses cm unit.
    double localVtxArray[3];
    localVtxArray[0] = localVtx.x()*GeoUtil::mm2cm();
    localVtxArray[1] = localVtx.y()*GeoUtil::mm2cm();
    localVtxArray[2] = localVtx.z()*GeoUtil::mm2cm();

    double localDirArray[3];
    localDirArray[0] = localDir.x();
    localDirArray[1] = localDir.y();
    localDirArray[2] = localDir.z();

    if (!getPhyNode()->GetShape()->CouldBeCrossed(localVtxArray, localDirArray)) {
        return false;
    }

    //print();   
    //bool inside = false;
    double safe[6];
    double dist = getPhyNode()->GetShape()->DistFromOutside(localVtxArray, localDirArray, 3, 1E50, safe);
    //std::cout << "dist " << dist << std::endl;

    if (dist < TGeoShape::Big()) {
        return true;
    }
    else {
        return false;
    }
}

/*
void RecGeo::get_projection_pos(int SiPMID, double &project_x, double &project_y)
{
//    TVector3 center = get_SiPM_center_fast(SiPMID);

    double org_theta = center.Theta()*TMath::RadToDeg();
    double org_phi   = center.Phi()*TMath::RadToDeg();
    org_theta = 90 - org_theta;
    ProjectAitoff2xy(org_phi, org_theta, project_x, project_y);
}
*/
TVector3 SiPMGeom::getChannelCenter(int channelid)
{
    
    
    if (m_phyNode) {
    
        if(channelid%2==0)
        {
            double localVec[3]= {0.0, 0.0, 0.0};
            double local[3]  = { localVec[0]*GeoUtil::mm2cm(),
                         localVec[1]*GeoUtil::mm2cm(), 
                         localVec[2]*GeoUtil::mm2cm()
                       };
            double global[3] = {0.0, 0.0, 0.0};
            double global1[3] = {0.0, 0.0, 0.0};
            TGeoNode* node = m_phyNode->GetNode();
            int nChild = node->GetNdaughters();
            //std::cout<<"nChild:"<<nChild<<std::endl;
            for(int iChild=0;iChild<=15;iChild++)
            {
                for(int i=0;i<3;i++)
                {
                    global[i]=0.0;
                    localVec[i]=0.0;
                    local[i]=localVec[i]*GeoUtil::mm2cm();
                }
                TGeoNode* childNode = node->GetDaughter(iChild);
                childNode->GetMatrix()->LocalToMaster(local, &global[0]);
                
                for(int i=0;i<3;i++)
                {
                    global1[i]+=global[i];
                    //std::cout<<"global[i]:"<<global[i]<<std::endl;
                }
            }
            for(int i=0;i<3;i++)
            {
                global1[i]/=16;
            }
            return  getGlobal(TVector3( global1[0]*GeoUtil::cm2mm(),global1[1]*GeoUtil::cm2mm(),global1[2]*GeoUtil::cm2mm())); 
            
        }
        else
        {
            double localVec[3]= {0.0, 0.0, 0.0};
            double local[3]  = { localVec[0]*GeoUtil::mm2cm(),
                         localVec[1]*GeoUtil::mm2cm(), 
                         localVec[2]*GeoUtil::mm2cm()
                       };
            double global[3] = {0.0, 0.0, 0.0};
            double global1[3] = {0.0, 0.0, 0.0};
            TGeoNode* node = m_phyNode->GetNode();
            int nChild = node->GetNdaughters();
            //std::cout<<"nChild:"<<nChild<<std::endl;
            for(int iChild=16;iChild<=31;iChild++)
            {
                for(int i=0;i<3;i++)
                {
                    global[i]=0.0;
                    localVec[i]=0.0;
                    local[i]=localVec[i]*GeoUtil::mm2cm();
                }
                TGeoNode* childNode = node->GetDaughter(iChild);
                childNode->GetMatrix()->LocalToMaster(local, &global[0]);
                for(int i=0;i<3;i++)
                {
                    global1[i]+=global[i];
                    //std::cout<<"global[i]:"<<global[i]<<std::endl;
                }
            }
            for(int i=0;i<3;i++)
            {
                global1[i]/=16;
            }
            return getGlobal(TVector3( global1[0]*GeoUtil::cm2mm(),global1[1]*GeoUtil::cm2mm(),global1[2]*GeoUtil::cm2mm()));
        }
    }
    else
    {
        return m_center;
    }
} 
double SiPMGeom::getChannelPhi(int channelid)
{
     double xx=getChannelCenter(channelid).X()+2446;
    double yy=getChannelCenter(channelid).Y()+2446;
    if(xx>=0 && yy>=0)
    {
        return atan(yy/xx);
    }
    if(xx<0 && yy>=0)
    {
        return atan(yy/xx)+M_PI;
    }
    if(xx<0 && yy<0)
    {
        return atan(yy/xx)+M_PI;
    }
    if(xx>=0 && yy<0)
    {
        return atan(yy/xx)+2*M_PI;
    }
}
