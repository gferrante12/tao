//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#ifndef TvtID_h
#define TvtID_h
#include "TAOIDService/TAODetectorID.h"
#include <string>
#include <assert.h>
#include <cstdint>
class TvtID : public TAODetectorID
{
    public:

        typedef Identifier::size_type  size_type; 
        typedef Identifier::value_type value_type; 

        /// constructor
        TvtID();

        /// destructor 
        ~TvtID();
 
        /// For a single pmt
        static Identifier id ( uint64_t module,
                               uint64_t pmt
                             );
        static Identifier id ( int value );
        static value_type getIntID ( uint64_t module,
                                     uint64_t pmt
                                   );

        static bool valuesOk ( const uint64_t module,
                                const uint64_t pmt
                              ) ;

        /// Values of different levels (failure returns 0)
        static int module (const Identifier& id);
        static int pmt    (const Identifier& id);

        /// Max/Min values for each field (error returns -999)
        static int moduleMin();
        static int moduleMax();
        static int modulePmtMin();
        static int modulePmtMax();


        /// Set Module Max (when geometry not fixed)
        static void setModuleMax(uint64_t value) { MODULE_MAX = value; }

    private:

        typedef std::vector<Identifier> idVec;
        typedef idVec::const_iterator   idVecIt;

        static const uint64_t MODULE_INDEX    = 8;
        static const uint64_t MODULE_MASK     = 0x00FFFF00;


        static const uint64_t PMT_INDEX       = 0;
        static const uint64_t PMT_MASK        = 0x000000FF;

        static const uint64_t MODULE_MIN      = 0;
        static       uint64_t MODULE_MAX;    


        static const uint64_t MODULE_PMT_MAX  = 0;
        static const uint64_t MODULE_PMT_MIN  = 0;

};

#endif