//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#ifndef CdID_h
#define CdID_h


#include "TAOIDService/TAODetectorID.h"
#include "TAOIDService/TAOIDService.h"

#include <string>
#include <cstdint>
#include <assert.h>

class CdID : public TAODetectorID
{
    public:

        typedef Identifier::size_type  size_type; 
        typedef Identifier::value_type value_type; 

        /// constructor
        CdID();

        /// destructor 
        ~CdID();
 
        /// For a single SiPM
        static Identifier id ( uint64_t module,
                               uint64_t SiPM
                             );
        static Identifier id ( uint64_t value );

       /*static Identifier id ( uint64_t Laryer,
                               uint64_t PositionID,
                               uint64_t ChannelFlag,
                               uint64_t CopyNo,
                               uint64_t ChannelID
                             );*/
        static Identifier id ( uint64_t SiPMNo,
                               uint64_t SignalCableID,
                               uint64_t HVBundleID,
                               uint64_t HVCableID,
                               uint64_t CopyNo,
                               uint64_t ChannelID
                             );
        static bool valuesOk ( const uint64_t module,  
                               const uint64_t SiPM 
                             ) ;
        /*static value_type getIntID ( uint64_t Laryer,
                                     uint64_t PositionID,
                                     uint64_t ChannelFlag,
                                     uint64_t CopyNo,
                                     uint64_t ChannelID
                                   );*/
        static value_type getIntID ( uint64_t SiPMNo,
                               uint64_t SignalCableID,
                               uint64_t HVBundleID,
                               uint64_t HVCableID,
                               uint64_t CopyNo,
                               uint64_t ChannelID
                             );
        /// Values of different levels (failure returns 0)
        static int module (const Identifier& id);
        static int SiPM    (const Identifier& id); 
 
        /// Max/Min values for each field (error returns -999)
        static int moduleMin();
        static int moduleMax();
        static int moduleSiPMMin();
        static int moduleSiPMMax();

  
        /// Set Module Max (when geometry not fixed)
        static void setModuleMax(uint64_t value) { MODULE_MAX = value; }

        /*static int Laryer (const Identifier& id);    
        static int PositionID (const Identifier& id);    
        static int ChannelFlag (const Identifier& id);   
        static int CopyNo (const Identifier& id);  
        static int ChannelID (const Identifier& id);*/
        static int SiPMNo (const Identifier& id);    
        static int HVBundleID (const Identifier& id);    
        static int HVCableID (const Identifier& id);  
        static int SignalCableID (const Identifier& id); 
        static int CopyNo (const Identifier& id);
        static int ChannelID (const Identifier& id);    
  

        
    private:

        typedef std::vector<Identifier> idVec;
        typedef idVec::const_iterator   idVecIt;

        static const uint64_t MODULE_INDEX    = 8;
        static const uint64_t MODULE_MASK     = 0x00FFFF00;

        static const uint64_t SiPM_INDEX       = 0;
        static const uint64_t SiPM_MASK        = 0x000000FF;

        static const uint64_t MODULE_MIN      = 0;
        static       uint64_t MODULE_MAX;     //= 65535;  // 14518 for DetSim0, 16719 for DetSim1, 18305 DetSim1 update



        static const uint64_t MODULE_SiPM_MAX  = 0;
        static const uint64_t MODULE_SiPM_MIN  = 0; 
        
        //-----------------------------------------



        /*static const uint64_t Laryer_INDEX   = 24;    
        static const uint64_t Laryer_MASK    = 0x3F000000;      
        

    
        static const uint64_t PositionID_INDEX   = 16;    
        static const uint64_t PositionID_MASK    = 0x00FF0000;      


        static const uint64_t ChannelFlag_INDEX    = 13;
        static const uint64_t ChannelFlag_MASK     = 0x00002000;


        static const uint64_t CopyNo_INDEX    = 1;
        static const uint64_t CopyNo_MASK     = 0x00001FFE;



        static const uint64_t ChannelID_INDEX   = 0;    
        static const uint64_t ChannelID_MASK    = 0x00000001; */ 
        
        

        static const uint64_t CopyNo_INDEX    = 40;
        static const uint64_t CopyNo_MASK     = uint64_t(0b111111111111)<<40;

        static const uint64_t ChannelID_INDEX   = 39;    
        static const uint64_t ChannelID_MASK    = uint64_t(1)<<39;
        
        static const uint64_t HVBundleID_INDEX   = 31;
        static const uint64_t HVBundleID_MASK   = uint64_t(0b11111111) << 31;

        static const uint64_t HVCableID_INDEX   = 25;
        static const uint64_t HVCableID_MASK   = uint64_t(0b111111) << 25;

        static const uint64_t SignalCableID_INDEX   = 13;
        static const uint64_t SignalCableID_MASK   = uint64_t(0b111111111111) << 13;

        static const uint64_t SiPMNo_INDEX   = 0;
        static const uint64_t SiPMNo_MASK   = uint64_t(0b1111111111111);


      

};

#endif 