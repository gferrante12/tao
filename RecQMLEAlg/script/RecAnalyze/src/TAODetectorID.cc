//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/TAODetectorID.h"
#include <iostream>
#include <stdio.h>
#include <assert.h>

TAODetectorID::TAODetectorID(void) :
    m_CdId(TAODetectorID::CD_ID),     
    m_WtId(TAODetectorID::WT_ID),      	
    m_TvtId(TAODetectorID::TVT_ID)	
{
}

TAODetectorID::~TAODetectorID(void)
{
}

bool TAODetectorID::isCd (const Identifier& id)
{
    Identifier::value_type value = id.getValue(); 
    return ((value  &  CD_MASK) >> CD_INDEX) == CD_ID ? true : false;    
}

bool TAODetectorID::isWt (const Identifier& id)
{
    Identifier::value_type value = id.getValue(); 
    return ((value  &  WT_MASK) >> WT_INDEX) == WT_ID ? true : false;
}

bool TAODetectorID::isTvt (const Identifier& id)
{
    Identifier::value_type value = id.getValue(); 
    return ((value  &  TVT_MASK) >> TVT_INDEX) == TVT_ID ? true : false;   
}
 
Identifier TAODetectorID::Cd(void) const
{
    Identifier id = Identifier(  m_CdId << CD_INDEX );
    return id; 
}

Identifier TAODetectorID::Wt(void) const
{
    Identifier id = Identifier(  m_WtId << WT_INDEX );
    return id; 
}
  
Identifier TAODetectorID::Tvt(void) const
{
    Identifier id = Identifier(  m_TvtId << TVT_INDEX );
    return id; 
}