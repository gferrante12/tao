//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#ifndef SimGeomSvc_h
#define SimGeomSvc_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition
#include "SniperKernel/SvcBase.h"
#include "TGeoManager.h"
#include "TAOIDService/Identifier.h"
#include "TAOGeometry/CdGeom.h"
#include "TAOGeometry/WtGeom.h"
#include "TAOGeometry/TvtGeom.h"
#include <map>

/*  
 * SimGeomSvc is used to manage ROOT gGeoManager Object.
 * There are several cases:
 * 1. run detector simulation only. output is gGeoManager.
 * 2. run electronics simulation only. input is gGeoManager.
 * 3. run both detector and electronics simulation.
 *
 * When electronics simulation is running, we look for geometry
 * as following:
 * 1. the geometry set from detector simulation.
 * 2. the geometry loaded from file.
 *
 * Because the geometry may be not ready during initialize phase,
 * we lazy load the geometry.
 */

class SimGeomSvc: public SvcBase
{
    public:
        SimGeomSvc(const std::string& name);
        virtual ~SimGeomSvc();

        bool initialize();
        bool finalize();

        void geom(TGeoManager* v);
        TGeoManager* geom();
        bool initRootGeom();
        bool initCdGeom();
        void initCdGeomControl(bool value);
        CdGeom* getCdGeom();

        bool initWtGeom();
        void initWtGeomControl(bool value);
        WtGeom* getWtGeom();

        bool initTvtGeom();
        void initTvtGeomControl(bool value);
        TvtGeom* getTvtGeom();

        
        

    private:
        void load_from_root();

    private:
        TGeoManager* m_geo_mgr;
    private:
        // the property is used when geometry need to be loaded from file.
        std::string m_input_root_file;
        // we can also output the geometry in a different file
        std::string m_output_root_file;
        std::string m_geomFileName;
        std::string m_geomPathName;
        bool m_fastInit;
        bool m_initCd;
        bool m_initWt;
        bool m_initTvt;
        CdGeom* m_CdGeom;
        WtGeom* m_WtGeom;
        TvtGeom* m_TvtGeom;
        
};

#endif
