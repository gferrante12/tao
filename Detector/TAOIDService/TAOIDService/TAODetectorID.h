//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#ifndef TAODetectorID_h
#define TAODetectorID_h

#include "TAOIDService/Identifier.h"
#include <string>
#include <cstdint>
class TAODetectorID
{
    public:    

        TAODetectorID(void);
        ~TAODetectorID(void);
    
        // Detector systems:
        Identifier  Cd(void) const;
        Identifier  Wt(void) const;
        Identifier  Tvt(void) const;  

        // Short print out of any identifier (optionally provide
        // separation character - default is '.'):
        // void show(const Identifier& id, char sep = '.' ) const;

        // or provide the printout in string form
        // std::string 	show_to_string	(const Identifier& id, char sep = '.'  ) const;

        // Expanded print out of any identifier
        // void print(const Identifier& id) const;

        // or provide the printout in string form
        // std::string 	print_to_string	(const Identifier& id) const;

        // Test of an Identifier to see if it belongs to a particular
        // detector system:
        static bool isCd (const Identifier& id);
        static bool isWt (const Identifier& id);
        static bool isTvt (const Identifier& id);

    //protected:

        /// Provide efficient access to individual field values
        int  CdFieldValue  () const;     
        int  WtFieldValue  () const;
        int  TvtFieldValue  () const;

        // extract detector id information
        int getDetectorID (const Identifier& id) const;  
    
        static const uint64_t CD_ID      = 0x1;
        static const uint64_t CD_INDEX   = 62;
        static const uint64_t CD_MASK    = 0xC000000000000000;

        static const uint64_t WT_ID      = 0x2;
        static const uint64_t WT_INDEX   = 62;
        static const uint64_t WT_MASK    = 0xC000000000000000;

        static const uint64_t TVT_ID      = 0x3;
        static const uint64_t TVT_INDEX   = 62;
        static const uint64_t TVT_MASK    = 0xC000000000000000;

    private:

        int  m_CdId;     
        int  m_WtId;      	
        int  m_TvtId; 	
};

//<<<<<< INLINE MEMBER FUNCTIONS                                        >>>>>>
inline int                 
TAODetectorID::CdFieldValue() const {return (m_CdId);}     

inline int                 
TAODetectorID::WtFieldValue() const {return (m_WtId);}

inline int                 
TAODetectorID::TvtFieldValue() const {return (m_TvtId);}       

#endif // TAO_DETECTOR_ID_H
