//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/CdID.h"
#include <assert.h>
#include <iostream>

unsigned int CdID::MODULE_MAX = 4023;  
//unsigned int CdID::MODULE_20INCH_MIN = 0;
//unsigned int CdID::MODULE_20INCH_MAX = 17612; // 17738; // 17745; // findSiPM20inchNum()-1
//unsigned int CdID::MODULE_3INCH_MIN  = 17613; // 17739; // 17746; // findSiPM20inchNum()
//unsigned int CdID::MODULE_3INCH_MAX  = 47485; // 54310; // 54317; // findSiPM20inchNum()+findSiPM3inchNum()-1


CdID::CdID(void)
{
}

CdID::~CdID(void)
{
}

//----------------------------------------------------------------------------
bool CdID::valuesOk ( const unsigned int module,  
                       const unsigned int SiPM
		     )
{
    // Check values
    //std::cout << " module = " << module << " SiPM = " << SiPM <<std::endl;
  
    if ( module  > MODULE_MAX)  return false;
    if ( SiPM > MODULE_SiPM_MAX)  return false;

    return true;
}

//----------------------------------------------------------------------------
int CdID::module (const Identifier& id)
{
    return ((id.getValue() & CdID::MODULE_MASK) >>  CdID::MODULE_INDEX);
}

//----------------------------------------------------------------------------
int CdID::SiPM (const Identifier& id)
{
    return ((id.getValue() & CdID::SiPM_MASK) >>  CdID::SiPM_INDEX);
}

//----------------------------------------------------------------------------
/*bool CdID::is20inch (const Identifier& id)
{
    return (module(id) >= MODULE_20INCH_MIN && module(id) <= MODULE_20INCH_MAX);
}

//----------------------------------------------------------------------------
bool CdID::is3inch (const Identifier& id)
{
    return (module(id) >= MODULE_3INCH_MIN && module(id) <= MODULE_3INCH_MAX);
}*/

//----------------------------------------------------------------------------
int CdID::moduleMax()
{
    return MODULE_MAX;
}

//----------------------------------------------------------------------------
int CdID::moduleMin()
{
    return MODULE_MIN;
}

//----------------------------------------------------------------------------
int CdID::moduleSiPMMax()
{
    return MODULE_SiPM_MAX;
}

//----------------------------------------------------------------------------
int CdID::moduleSiPMMin()
{
    return MODULE_SiPM_MIN;
}

//----------------------------------------------------------------------------
/*int CdID::module20inchMin()
{
    return MODULE_20INCH_MIN;
}

//----------------------------------------------------------------------------
int CdID::module20inchMax()
{
    return MODULE_20INCH_MAX; 
}

//----------------------------------------------------------------------------
int CdID::module3inchMin()
{
    return MODULE_3INCH_MIN; 
}

//----------------------------------------------------------------------------
int CdID::module3inchMax()
{
    return MODULE_3INCH_MAX;
}

//----------------------------------------------------------------------------
int CdID::module20inchNumber() 
{
    return module20inchMax() - module20inchMin() + 1;
}

//----------------------------------------------------------------------------
int CdID::module3inchNumber() 
{ 
    return module3inchMax() - module3inchMin() + 1;
}*/

//----------------------------------------------------------------------------
Identifier CdID::id ( unsigned int module,
                      unsigned int SiPM
                    )
{
    /*if (module >= MODULE_3INCH_SHIFT) {
        module = MODULE_3INCH_MIN + (module - MODULE_3INCH_SHIFT);
    }*/
 
    assert ( valuesOk(module, SiPM) ); 
    unsigned int value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (module << MODULE_INDEX) |
                         (SiPM << SiPM_INDEX);
    return Identifier(value); 
}

//----------------------------------------------------------------------------
Identifier CdID::id(unsigned int value)
{
    return Identifier(value);
}

//----------------------------------------------------------------------------
unsigned int CdID::getIntID ( unsigned int module,
                              unsigned int SiPM
                            )
{
    unsigned int value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (module << MODULE_INDEX) |
                         (SiPM << SiPM_INDEX);
    return value;
}
