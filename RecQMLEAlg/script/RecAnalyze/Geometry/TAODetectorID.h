#ifndef TAODetectorID_h
#define TAODetectorID_h

#include "Identifier.h"
#include <string>

class TAODetectorID
{
    public:    

        TAODetectorID(void);
        ~TAODetectorID(void);
    
        // Detector systems:
        Identifier  Cd(void) const;
        Identifier  Wp(void) const;
        Identifier  Tt(void) const;  

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
        static bool isWp (const Identifier& id);
        static bool isTt (const Identifier& id);

    //protected:

        /// Provide efficient access to individual field values
        int  CdFieldValue  () const;     
        int  WpFieldValue  () const;
        int  TtFieldValue  () const;

        // extract detector id information
        int getDetectorID (const Identifier& id) const;  
    
        static const unsigned int CD_ID      = 0x10;
        static const unsigned int CD_INDEX   = 24;
        static const unsigned int CD_MASK    = 0xFF000000;

        static const unsigned int WP_ID      = 0x20;
        static const unsigned int WP_INDEX   = 24;
        static const unsigned int WP_MASK    = 0xFF000000;

        static const unsigned int TT_ID      = 0x30;
        static const unsigned int TT_INDEX   = 24;
        static const unsigned int TT_MASK    = 0xFF000000;

    private:

        int  m_CdId;     
        int  m_WpId;      	
        int  m_TtId; 	
};

//<<<<<< INLINE MEMBER FUNCTIONS                                        >>>>>>
inline int                 
TAODetectorID::CdFieldValue() const {return (m_CdId);}     

inline int                 
TAODetectorID::WpFieldValue() const {return (m_WpId);}

inline int                 
TAODetectorID::TtFieldValue() const {return (m_TtId);}       

#endif // TAO_DETECTOR_ID_H