//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/PmtGeom.h"
#include "Geometry/GeoUtil.h"
#include "Geometry/CdID.h"
#include "TMath.h"
#include "TVector3.h"
#include "TVector2.h"
#include "TGeoManager.h"
#include "TGeoPhysicalNode.h"
#include <iostream>
#include <iomanip>
PmtGeom::PmtGeom()
{
}

PmtGeom::~PmtGeom()
{
}

PmtGeom::PmtGeom(Identifier id)
    : m_id(id),
      //m_is20inch(true),
      m_layer(0),
      m_azimuth(0),
      m_pmt(0)
{
    m_phyNode = 0;
    m_center = TVector3(0,0,0);
    m_axisDir = TVector3(0,0,1);
}

bool PmtGeom::setPhyNode(TGeoPhysicalNode *phyNode)
{
  m_phyNode = phyNode;
  return true;
}

TGeoPhysicalNode* PmtGeom::getPhyNode()
{
    if (m_phyNode) {
        return m_phyNode;
    }
    else {
        std::cerr << "PmtGeom::GetPhyNode Id " << m_id << " does not exist!" << std::endl;
        return 0;
    }
}

void PmtGeom::getGlobal(double *local, double *global)
{
    //cout << local[0] << " " << local[1] << " " << local[2] << endl;
    //cout << global[0] << " " << global[1] << " " << global[2] << endl;
    getPhyNode()->GetMatrix(-1*getPhyNode()->GetLevel())->LocalToMaster(local, &global[0]);
}

void PmtGeom::getLocal(double *local, double *global)
{
    //cout << local[0] << " " << local[1] << " " << local[2] << endl;
    //cout << global[0] << " " << global[1] << " " << global[2] << endl;
    getPhyNode()->GetMatrix(-1*getPhyNode()->GetLevel())->MasterToLocal(global, &local[0]);
}

TVector3 PmtGeom::getGlobal(TVector3 localVec)
{
    double local[3]  = { localVec[0]*GeoUtil::mm2cm(),
                         localVec[1]*GeoUtil::mm2cm(), 
                         localVec[2]*GeoUtil::mm2cm()
                       };
    double global[3] = {0.0, 0.0, 0.0};
    getGlobal(local, global);

    return TVector3( global[0]*GeoUtil::cm2mm(),
                     global[1]*GeoUtil::cm2mm(),
                     global[2]*GeoUtil::cm2mm()
                   );
}

TVector3 PmtGeom::getLocal(TVector3 globalVec)
{
  double global[3]  = { globalVec[0]*GeoUtil::mm2cm(),
                        globalVec[1]*GeoUtil::mm2cm(),
                        globalVec[2]*GeoUtil::mm2cm()
                      };
  double local[3] = {0.0, 0.0, 0.0};
  getLocal(local, global);

  return TVector3( local[0]*GeoUtil::cm2mm(),
                   local[1]*GeoUtil::cm2mm(),
                   local[2]*GeoUtil::cm2mm()
                 );
}

TVector3 PmtGeom::getCenter()
{
    if ( m_phyNode ) {
        return getGlobal(TVector3(0,0,0));
    }
    else {
        return m_center;
    }
}

TVector3 PmtGeom::getAxisDir()
{
    if ( m_phyNode ) {   
        TVector3 center = getCenter();
        TVector3 ref = getGlobal(TVector3(0,0,1.0));

        return ref-center;
    }
    else {
        return m_axisDir;
    }
}

TVector2 PmtGeom::getCenterAitoff()
{
    TVector3 center = getCenter();

    double org_theta = center.Theta()*TMath::RadToDeg();
    double org_phi   = center.Phi()*TMath::RadToDeg();
    org_theta = 90.0 - org_theta;

    double project_x, project_y;
    GeoUtil::projectAitoff2xy(org_phi, org_theta, project_x, project_y);

    return TVector2(project_x, project_y);
}

void PmtGeom::print()
{
    int KS = 6;
    TVector3 center = getCenter();
    TVector3 dir    = getAxisDir();
    TVector2 atioff = getCenterAitoff();

    std::cout << "Pmt "      << std::setw(KS) << m_id
              << " Center("  << std::setw(2*KS) << center.x()
              << ", "        << std::setw(2*KS) << center.y()
              << ", "        << std::setw(2*KS) << center.z() << ")"
              << " Layer "   << std::setw(  KS) << getLayer()
              << " Azimuth " << std::setw(  KS) << getAzimuth()
              << " LatLong(" << std::setw(2*KS) << 90-center.Theta()*TMath::RadToDeg()
              << ", "        << std::setw(2*KS) << center.Phi()*TMath::RadToDeg() << ")"
//            << " R "       << std::setw(2*KS) << center.Mag()
              << " Dir("     << std::setw(2*KS) << dir.Theta()
              << ", "        << std::setw(2*KS) << dir.Phi() << ")"
//            << " Aitoff "  << std::setw(2*KS) << atioff.X()
//            << ", "        << std::setw(2*KS) << atioff.Y()
              << std::endl;
}

void PmtGeom::print(int verb)
{
    int KS = 6;
    TVector3 center = getCenter();
    if (verb == 3) {
    std::cout << "PS: " << std::setw(KS) << m_id
    
    	      << " Center("  << std::setw(2*KS) << center.x()
    	      << ", "        << std::setw(2*KS) << center.y()
	      << ", "        << std::setw(2*KS) << center.z() << ")"
	      << std::endl;
    }
}


bool PmtGeom::isCrossed(const TVector3 vtx, const TVector3 dir)
{
    TVector3 localVtx = getLocal(vtx);
    TVector3 localDir = getLocal(vtx+dir) - localVtx;
    //int KS = 6;
    //std::cout << "Pmt " << std::setw(KS) << getLayer() << std::setw(KS) << getAzimuth() << std::endl;
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