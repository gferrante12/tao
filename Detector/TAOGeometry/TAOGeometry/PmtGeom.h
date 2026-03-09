//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#ifndef PmtGeom_h
#define PmtGeom_h

#include "TAOIDService/Identifier.h"

#include <vector>

#include "TVector3.h"

class TVector2;
class TGeoPhysicalNode;

class PmtGeom
{
    public :

        PmtGeom();
        ~PmtGeom();

        PmtGeom(Identifier id);

        Identifier getId() { return m_id; }
        void setId(Identifier id) {m_id = id;}
        bool setPhyNode(TGeoPhysicalNode* phyNode);
        TGeoPhysicalNode* getPhyNode();
        //void set20inch(bool is20inch) { m_is20inch = is20inch; }
        //bool is20inch() { return m_is20inch; }

        void getGlobal(double *local, double *global);
        void getLocal(double *local, double *global);
        TVector3 getGlobal(TVector3 localVec);
        TVector3 getLocal(TVector3 globalVec);

        void setCenterFast(TVector3 center) { m_center = center; }
        void setAxisDirFast(TVector3 axisDir) { m_axisDir = axisDir; }
        TVector3 getCenter();
        TVector3 getAxisDir();
        TVector2 getCenterAitoff();
        double GetTVTXlength();
        double GetTVTYlength();
        double GetTVTZlength();
        TVector3 getTVTPoint1();
        TVector3 getTVTPoint2();
        TVector3 getTVTPoint3();
        TVector3 getTVTPoint4();
        TVector3 getTVTPoint5();
        TVector3 getTVTPoint6();
        TVector3 getTVTPoint7();
        TVector3 getTVTPoint8();

        // Check whether a vertex + direction intersects with this Pmt
        bool isCrossed(const TVector3 vtx, const TVector3 dir);

        void setLayer(int layer)     { m_layer = layer; }
        void setAzimuth(int azimuth) { m_azimuth = azimuth; }
        void setPmt(int pmt)         { m_pmt = pmt; }

        int getLayer()   { return m_layer; }
        int getAzimuth() { return m_azimuth; }
        int getPmt()     { return m_pmt; }
        double getTheta()  { return getCenter().Theta(); }
        double getPhi()  { return getCenter().Phi(); }
        double getX()  { return getCenter().X(); }
        double getY()  { return getCenter().Y(); }
        double getZ()  { return getCenter().Z(); }
        double getR()  { return getCenter().Mag(); }
        
        void print();
	    void print(int verb);
    private :
        Identifier m_id;
        TGeoPhysicalNode* m_phyNode;
        //bool m_is20inch;
        
        int m_layer;
        int m_azimuth;
        int m_pmt;

        TVector3 m_center;
        TVector3 m_axisDir;
};


#endif