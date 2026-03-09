//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#include "TAOIDService/TvtID.h"
#include <assert.h>
#include <iostream>
#include <algorithm>
#include <sstream>
#include <string>
#include <cstdlib>
#include <stdexcept>

uint64_t TvtID::MODULE_MAX = 159;

TvtID::TvtID(void)
{
}

TvtID::~TvtID(void)
{
}

//----------------------------------------------------------------------------
bool TvtID::valuesOk ( const uint64_t module,
                       const uint64_t pmt
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
Identifier TvtID::id ( uint64_t module,
                      uint64_t pmt
                    )
{
    assert ( valuesOk(module, pmt) );
    uint64_t value = (TAODetectorID::TVT_ID << TVT_INDEX) |
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
uint64_t TvtID::getIntID ( uint64_t module,
                              uint64_t pmt
                            )
{
    uint64_t value = (TAODetectorID::TVT_ID << TVT_INDEX) |
                         (module << MODULE_INDEX) |
                         (pmt << PMT_INDEX);
    return value;
}