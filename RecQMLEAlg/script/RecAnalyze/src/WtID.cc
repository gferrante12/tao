//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/WtID.h"
#include <assert.h>
#include <iostream>

unsigned int WtID::MODULE_MAX = 300;
//unsigned int WtID::MODULE_20INCH_MIN = 0;
//unsigned int WtID::MODULE_20INCH_MAX = 2307;

WtID::WtID(void)
{
}

WtID::~WtID(void)
{
}

//----------------------------------------------------------------------------
bool WtID::valuesOk ( const unsigned int module,
                       const unsigned int pmt
                     )
{
    // Check values
    //std::cout << " module = " << module << " pmt = " << pmt <<std::endl;

    if ( module  > MODULE_MAX)  return false;
    if ( pmt > MODULE_PMT_MAX)  return false;

    return true;
}

//----------------------------------------------------------------------------
int WtID::module (const Identifier& id)
{
    return ((id.getValue() & WtID::MODULE_MASK) >>  WtID::MODULE_INDEX);
}

//----------------------------------------------------------------------------
int WtID::pmt (const Identifier& id)
{
    return ((id.getValue() & WtID::PMT_MASK) >>  WtID::PMT_INDEX);
}

//----------------------------------------------------------------------------
/*bool WtID::is20inch (const Identifier& id)
{
    return (module(id) >= MODULE_20INCH_MIN && module(id) <= MODULE_20INCH_MAX);
}*/

//----------------------------------------------------------------------------
int WtID::moduleMax()
{
    return MODULE_MAX;
}

//----------------------------------------------------------------------------
int WtID::moduleMin()
{
    return MODULE_MIN;
}

//----------------------------------------------------------------------------
int WtID::modulePmtMax()
{
    return MODULE_PMT_MAX;
}

//----------------------------------------------------------------------------
int WtID::modulePmtMin()
{
    return MODULE_PMT_MIN;
}

//----------------------------------------------------------------------------
/*int WtID::module20inchMin()
{
    return MODULE_20INCH_MIN;
}

//----------------------------------------------------------------------------
int WtID::module20inchMax()
{
    return MODULE_20INCH_MAX;
}

//----------------------------------------------------------------------------
int WtID::module20inchNumber()
{
    return module20inchMax() - module20inchMin() + 1;
}*/

//----------------------------------------------------------------------------
Identifier WtID::id ( unsigned int module,
                      unsigned int pmt
                    )
{
    /*if (module >= MODULE_20INCH_SHIFT) {
        module = MODULE_20INCH_MIN + (module - MODULE_20INCH_SHIFT);
    }*/
    assert ( valuesOk(module, pmt) );
    unsigned int value = (TAODetectorID::WT_ID << WT_INDEX) |
                         (module << MODULE_INDEX) |
                         (pmt << PMT_INDEX);
    return Identifier(value);
}

//---------------------------------------------------------------------------- 
Identifier WtID::id(int value)
{
    return Identifier(value);
}

//---------------------------------------------------------------------------- 
unsigned int WtID::getIntID ( unsigned int module,
                              unsigned int pmt
                            )
{
    unsigned int value = (TAODetectorID::WT_ID << WT_INDEX) |
                         (module << MODULE_INDEX) |
                         (pmt << PMT_INDEX);
    return value;
}
