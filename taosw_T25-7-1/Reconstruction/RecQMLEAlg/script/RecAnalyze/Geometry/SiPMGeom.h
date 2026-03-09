#ifndef SiPMGeom_h
#define SiPMGeom_h

#include "Identifier.h"
#include <vector>
#include <cmath>

#include "TVector3.h"

class TVector2;
class TGeoPhysicalNode;

class SiPMGeom
{
    public :

        SiPMGeom();
        ~SiPMGeom();

        SiPMGeom(Identifier id);

        Identifier getId() { return m_id; }
        bool setPhyNode(TGeoPhysicalNode* phyNode);
        TGeoPhysicalNode* getPhyNode();
        void set20inch(bool is20inch) { m_is20inch = is20inch; }
        bool is20inch() { return m_is20inch; }

        void getGlobal(double *local, double *global);
        void getLocal(double *local, double *global);
        TVector3 getGlobal(TVector3 localVec);
        TVector3 getLocal(TVector3 globalVec);

        void setCenterFast(TVector3 center) { m_center = center; }
        void setAxisDirFast(TVector3 axisDir) { m_axisDir = axisDir; }
        TVector3 getCenter();
        TVector3 getAxisDir();
        TVector2 getCenterAitoff();

        // Check whether a vertex + direction intersects with this SiPM
        bool isCrossed(const TVector3 vtx, const TVector3 dir);
        //Retrun SiPad Message
        void setLayer(int layer)     { m_layer = layer; }
        void setAzimuth(int azimuth) { m_azimuth = azimuth; }
        void setSiPM(int SiPM)         { m_SiPM = SiPM; }
        void setSiPM_r(double SiPM_r)  { m_SiPM_r = SiPM_r; }

        int getLayer()   { return m_layer; }
        int getAzimuth() { return m_azimuth; }
        int getSiPM()     { return m_SiPM; }

        double getTheta() {return acos((getCenter().Z()+8212.8)/(sqrt((getCenter().X()+2446)*(getCenter().X()+2446)+(getCenter().Y()+2446)*(getCenter().Y()+2446)+(getCenter().Z()+8212.8)*(getCenter().Z()+8212.8))));}
        double getPhi();
      

        double getX()  { return getCenter().X(); }
        double getY()  { return getCenter().Y(); }
        double getZ()  { return getCenter().Z(); }
        double getR()  { return sqrt((getCenter().X()+2446)*(getCenter().X()+2446)+(getCenter().Y()+2446)*(getCenter().Y()+2446)+(getCenter().Z()+8212.8)*(getCenter().Z()+8212.8)); }

        double getSiPM_r() { return m_SiPM_r; }

        static int ChannelIDToSiPMID(int channelid);
        int getSiPMID(Identifier id);
        
        void print();
	    void print(int verb);

        //Return Channel Message
        //void getGlobal(double *local, double *global);
        //void getLocal(double *local, double *global);
        TVector3 getChannelCenter(int channelid);
        double getChannelTheta(int channelid) {return acos((getChannelCenter(channelid).Z()+8212.8)/(sqrt((getChannelCenter(channelid).X()+2446)*(getChannelCenter(channelid).X()+2446)+(getChannelCenter(channelid).Y()+2446)*(getChannelCenter(channelid).Y()+2446)+(getChannelCenter(channelid).Z()+8212.8)*(getChannelCenter(channelid).Z()+8212.8))));}
        double getChannelPhi(int channelid); 
        double getChannelX(int channelid) { return getChannelCenter(channelid).X(); }  
        double getChannelY(int channelid) { return getChannelCenter(channelid).Y(); }    
        double getChannelZ(int channelid) { return getChannelCenter(channelid).Z(); }    
        double getChannelR(int channelid) { return sqrt((getChannelCenter(channelid).X()+2446)*(getChannelCenter(channelid).X()+2446)+(getChannelCenter(channelid).Y()+2446)*(getChannelCenter(channelid).Y()+2446)+(getChannelCenter(channelid).Z()+8212.8)*(getChannelCenter(channelid).Z()+8212.8)); }
  


    private :

        Identifier m_id;
        TGeoPhysicalNode* m_phyNode;
        bool m_is20inch;
        
        int m_layer;
        int m_azimuth;
        int m_SiPM;

        TVector3 m_center;
        TVector3 m_axisDir;
        double m_SiPM_r;
        
};

#endif 
