//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#ifndef WtGeom_h
#define WtGeom_h

#include "TAOIDService/Identifier.h"
#include "TAOGeometry/PmtGeom.h"
#include "TString.h"
#include <map>
#include <vector>
#include "GeoUtil.h"
#include "TGeoTube.h"

class TGeoManager;
class TGeoVolume;
class TGeoNode;
class TGeoPhysicalNode;
class WtGeom
{
    public :

        typedef std::map<Identifier, PmtGeom*>::iterator PmtMapIt; 

        WtGeom();
        ~WtGeom();

        // Initialization
        //-----------------------------------------------
        bool init();
        bool initRootGeo();
        void setGeomFileName(std::string name) { m_geomFileName = name; }
        void setGeomPathName(std::string name) { m_geomPathName = name; }
        void setFastInit(bool fastInit) { m_fastInit = fastInit; }
        bool readRootGeoFile();

        // Getter
        //-----------------------------------------------
        unsigned int findPmtNum() { return m_nPmt; }
        //unsigned int findPmt20inchNum() { return m_nPmt20inch; }

        PmtGeom* getPmt(Identifier id);
        PmtGeom* getPmt(int layer, int azimuth, int pmt);
        unsigned int getPmtNum() { return m_mapIdToPmt.size(); }
        int getPmtType(TString name);

        // Useful functions  
        //-----------------------------------------------
        void printPmt();
        void initWtInfo(); 

        // Find the intersected Pmt from a vertex + direction
        PmtGeom* findCrossedPmt(const TVector3 vtx, const TVector3 dir);
        PmtGeom* findCrossedPmtFast(const TVector3 vtx, const TVector3 dir);

        // Orgnize Pmts into layers
        bool orgnizePmt(); 
        int getLayerNum() { return m_layerNum; }
        int getAzimuthNum(int layer);
    
        // Verbosisty
        void setVerb(int value) { m_verb = value; }
        int  getVerb() { return m_verb; }

        // Get Wt info; unit mm
        double getWtRmax() { return pWt->GetRmax()*GeoUtil::cm2mm(); }
        double getWtDz() { return pWt->GetDz()*GeoUtil::cm2mm(); }         
        void printWt();

    private :
        std::string m_input_root_file;
        // analyze TGeo tree and set 
        //-----------------------------------------------
        void analyzeGeomStructure();
        void searchPmt();
        void searchPmtBottom(TGeoNode* node);
        //void searchPmtMother(TGeoNode* node);
        //void setPathMother();
        void searchPmtMother1(TGeoNode* node);
        void setPathMother1();
        void searchPmtMother2(TGeoNode* node);
        void setPathMother2();
        void searchPmtMother3(TGeoNode* node);
        void setPathMother3();
        TString setPathBottom();

        bool setPhyNodes();
        bool setPhyNodesManually();
        bool setPhyNodesAuto();
        PmtGeom* addPmt(Identifier id, TGeoPhysicalNode *phyNode, int pmtType);

        // members

        bool m_useDefaultGeom;
        std::string m_geomFileName;
        std::string m_geomPathName;
        TGeoManager *m_geom;
        std::map<Identifier, PmtGeom*> m_mapIdToPmt;
        bool m_fastInit;

        // root geometry structur analysis
        int m_nPmt;
        int m_nPmt20inch;
        TGeoVolume* m_volPmt;
        TGeoNode*   m_nodePmt;

        bool m_isPmtMotherFound;
        /*TGeoNode* m_nodePmtMother;
        std::vector<TGeoNode*> m_nodeMotherVec; 
        TString m_pathMother;*/
        
        //bool m_isPmtMotherFound1;
        TGeoNode* m_nodePmtMother1;
        std::vector<TGeoNode*> m_nodeMotherVec1; 
        TString m_pathMother1;

        //bool m_isPmtMotherFound2;
        TGeoNode* m_nodePmtMother2;
        std::vector<TGeoNode*> m_nodeMotherVec2; 
        TString m_pathMother2;

        //bool m_isPmtMotherFound3;
        TGeoNode* m_nodePmtMother3;
        std::vector<TGeoNode*> m_nodeMotherVec3; 
        TString m_pathMother3;

        
        
        
        bool m_isPmtBottomFound;
        std::vector<TGeoNode*> m_nodeBottomVec;
        TString m_pathBottom20inch;
        TString m_pathBottom3inch;

        // re-organize with layer
        int m_layerNum;
        std::vector<int> m_azimuthNum; 

        int m_verb;

        // get Wt info
        TGeoTube *pWt;
};

#endif 
