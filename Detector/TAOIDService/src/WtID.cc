//
//  Author: Jiayang Xu  2023.10.23
//  E-mail:xujy@ihep.ac.cn
//
#include "TAOIDService/WtID.h"
#include <assert.h>
#include <iostream>

uint64_t WtID::MODULE_MAX = 300;


WtID::WtID(void)
{
}

WtID::~WtID(void)
{
}

//----------------------------------------------------------------------------
bool WtID::valuesOk ( const uint64_t module,
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
Identifier WtID::id ( uint64_t module,
                      uint64_t pmt
                    )
{
    /*if (module >= MODULE_20INCH_SHIFT) {
        module = MODULE_20INCH_MIN + (module - MODULE_20INCH_SHIFT);
    }*/
    assert ( valuesOk(module, pmt) );
    uint64_t value = (TAODetectorID::WT_ID << WT_INDEX) |
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
uint64_t WtID::getIntID ( uint64_t module,
                              uint64_t pmt
                            )
{
    uint64_t value = (TAODetectorID::WT_ID << WT_INDEX) |
                         (module << MODULE_INDEX) |
                         (pmt << PMT_INDEX);
    return value;
}
