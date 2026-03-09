//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#ifndef CdGeom_h
#define CdGeom_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition

#include "TAOIDService/TAOIDService.h"
#include "TAOIDService/Identifier.h"
#include "TAOIDService/TAODetectorID.h"
#include "TAOIDService/CdID.h"

#include "TAOGeometry/SiPMGeom.h"
#include "TAOGeometry/GeoUtil.h"

#include <string>
#include <assert.h>
#include <map>
#include <vector>

#include "TGeoManager.h"
#include "TGeoSphere.h"
#include "TGeoTube.h"
#include "GeoUtil.h"
#include "TGeoMatrix.h"
#include "TGeoVoxelFinder.h"

#include "TStopwatch.h"
#include "TString.h"

class TGeoManager;
class TGeoVolume;
class TGeoNode;
class TGeoPhysicalNode;

typedef  std::vector<Identifier> SiPMIdVec;
typedef  std::vector<SiPMGeom*> SiPMGeomVec;



class CdGeom
{
    public:
        CdGeom();
        ~CdGeom();

        void geom(TGeoManager* v);
        TGeoManager* geom();

        typedef std::map<Identifier, SiPMGeom*>::iterator SiPMMapIt;
        typedef std::vector<SiPMGeom*>::iterator SiPMGeomIt;
        typedef std::vector<Identifier>::iterator SiPMIdIt;
        ///////////////////////////////////////////

        void setGeomFileName(std::string name) { m_geomFileName = name; }
        void setGeomPathName(std::string name) { m_geomPathName = name; }       

        bool orgnizeSiPM();
        void SimGeomExecute();
        SiPMGeom* FindSiPM(int channelid);
        void readRootGeoFile();
        bool SetPhyNodes();
        bool setPhyNodesAuto();
        void analyzeGeomStructure();
        void searchSiPMMother(TGeoNode* node);
        void setPathMother();
        void searchSiPM();
        unsigned int findSiPMNum();
        int getSiPMType(TString name);
        SiPMGeom* addSiPM(Identifier id, TGeoPhysicalNode *phyNode, int SiPMType);
        void printSiPM();
        int getLayerNum() { return m_layerNum; }
        int getAzimuthNum(int layer);
        SiPMGeom* getSiPM(Identifier id);
        SiPMGeom* getSiPM(int layer, int azimuth, int SiPM);
        void initCdInfo();
        bool init();
        bool initRootGeo();
        void setVerb(int value) { m_verb = value; }
        int  getVerb() { return m_verb; }

   // private:
        
       

        


    private:
        TGeoManager* m_geom;
        TAOIDService* idServ;
    private:
        // the property is used when geometry need to be loaded from file.
        std::string m_input_root_file;
        // we can also output the geometry in a different file
        std::string m_output_root_file;
        bool m_isSiPMMotherFound;
        std::vector<TGeoNode*> m_nodeMotherVec;
        TGeoNode* m_nodeSiPMMother;
        TString m_pathMother;
        int m_nSiPM;
        TGeoNode* m_nodeSiPM;
    
        bool m_isSiPMBottomFound;
        std::vector<TGeoNode*> m_nodeBottomVec;
        
        bool m_fastInit;
        std::map<Identifier, SiPMGeom*> m_mapIdToSiPM;

        // re-organize with layer
        int m_layerNum;
        std::vector<int> m_azimuthNum; 
        int m_verb;

        std::string m_geomFileName;
        std::string m_geomPathName;


};

#endif
