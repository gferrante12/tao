#ifndef SimGeomSvc_h
#define SimGeomSvc_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition
#include "SniperKernel/SvcBase.h"
#include "TGeoManager.h"
#include "Geometry/Identifier.h"
#include "Geometry/CdGeom.h"
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
        bool m_initWp;
        bool m_initTt;
        CdGeom* m_CdGeom;
        
};

#endif
