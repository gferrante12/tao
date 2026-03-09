//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/TvtID.h"
#include <assert.h>
#include <iostream>
#include <algorithm>
#include <sstream>
#include <string>
#include <cstdlib>
#include <stdexcept>

unsigned int TvtID::MODULE_MAX = 159;
//unsigned int TvtID::MODULE_20INCH_MIN = 0;
//unsigned int TvtID::MODULE_20INCH_MAX = 2307;

TvtID::TvtID(void)
{
}

TvtID::~TvtID(void)
{
}

//----------------------------------------------------------------------------
bool TvtID::valuesOk ( const unsigned int module,
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
int TvtID::module (const Identifier& id)
{
    return ((id.getValue() & TvtID::MODULE_MASK) >>  TvtID::MODULE_INDEX);
}

//----------------------------------------------------------------------------
int TvtID::pmt (const Identifier& id)
{
    return ((id.getValue() & TvtID::PMT_MASK) >>  TvtID::PMT_INDEX);
}

//----------------------------------------------------------------------------
/*bool TvtID::is20inch (const Identifier& id)
{
    return (module(id) >= MODULE_20INCH_MIN && module(id) <= MODULE_20INCH_MAX);
}*/

//----------------------------------------------------------------------------
int TvtID::moduleMax()
{
    return MODULE_MAX;
}

//----------------------------------------------------------------------------
int TvtID::moduleMin()
{
    return MODULE_MIN;
}

//----------------------------------------------------------------------------
int TvtID::modulePmtMax()
{
    return MODULE_PMT_MAX;
}

//----------------------------------------------------------------------------
int TvtID::modulePmtMin()
{
    return MODULE_PMT_MIN;
}

//----------------------------------------------------------------------------
/*int TvtID::module20inchMin()
{
    return MODULE_20INCH_MIN;
}

//----------------------------------------------------------------------------
int TvtID::module20inchMax()
{
    return MODULE_20INCH_MAX;
}

//----------------------------------------------------------------------------
int TvtID::module20inchNumber()
{
    return module20inchMax() - module20inchMin() + 1;
}*/

//----------------------------------------------------------------------------
Identifier TvtID::id ( unsigned int module,
                      unsigned int pmt
                    )
{
    /*if (module >= MODULE_20INCH_SHIFT) {
        module = MODULE_20INCH_MIN + (module - MODULE_20INCH_SHIFT);
    }*/
    assert ( valuesOk(module, pmt) );
    unsigned int value = (TAODetectorID::TVT_ID << TVT_INDEX) |
                         (module << MODULE_INDEX) |
                         (pmt << PMT_INDEX);
    return Identifier(value);
}

//---------------------------------------------------------------------------- 
Identifier TvtID::id(int value)
{
    return Identifier(value);
}

//---------------------------------------------------------------------------- 
unsigned int TvtID::getIntID ( unsigned int module,
                              unsigned int pmt
                            )
{
    unsigned int value = (TAODetectorID::TVT_ID << TVT_INDEX) |
                         (module << MODULE_INDEX) |
                         (pmt << PMT_INDEX);
    return value;
}