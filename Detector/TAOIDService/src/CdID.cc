//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "TAOIDService/CdID.h"
#include "TAOIDService/TAOIDService.h"

#include <assert.h>
#include <iostream>

uint64_t CdID::MODULE_MAX = 4023;  

CdID::CdID(void)
{
}

CdID::~CdID(void)
{
}

//----------------------------------------------------------------------------
bool CdID::valuesOk ( const uint64_t module,  
                       const uint64_t SiPM
		            )
{
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
Identifier CdID::id ( uint64_t module,
                      uint64_t SiPM
                    )
{
    assert ( valuesOk(module, SiPM) ); 
    uint64_t value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (module << MODULE_INDEX) |
                         (SiPM << SiPM_INDEX);
    return Identifier(value); 
}

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
Identifier CdID::id(uint64_t value)
{
    return Identifier(value);
}

//----------------------------------------------------------------------------
/*uint64_t CdID::getIntID ( uint64_t Laryer,
                              uint64_t PositionID,
                              uint64_t ChannelFlag,
                              uint64_t CopyNo,
                              uint64_t ChannelID
                            )
{
    uint64_t value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (Laryer << Laryer_INDEX) |
                         (PositionID << PositionID_INDEX) |
                         (ChannelFlag << ChannelFlag_INDEX) |
                         (CopyNo << CopyNo_INDEX) |
                         (ChannelID << ChannelID_INDEX);
    return value;
}*/
/*Identifier CdID::id ( uint64_t Laryer,
                      uint64_t PositionID,
                      uint64_t ChannelFlag,
                      uint64_t CopyNo,
                      uint64_t ChannelID
                    )
{


    uint64_t value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (Laryer << Laryer_INDEX) |
                         (PositionID << PositionID_INDEX) |
                         (ChannelFlag << ChannelFlag_INDEX) |
                         (CopyNo << CopyNo_INDEX) |
                         (ChannelID << ChannelID_INDEX);
                         
    return Identifier(value); 
}
int CdID::Laryer (const Identifier& id)    
{
    return ((id.getValue() & CdID::Laryer_MASK) >>  Laryer_INDEX);
}
int CdID::PositionID (const Identifier& id)    
{
    return ((id.getValue() & CdID::PositionID_MASK) >>  PositionID_INDEX);
}
int CdID::ChannelFlag (const Identifier& id)   
{
    return ((id.getValue() & CdID::ChannelFlag_MASK) >>  ChannelFlag_INDEX);
}
int CdID::CopyNo (const Identifier& id)  
{
    return ((id.getValue() & CdID::CopyNo_MASK) >>  CopyNo_INDEX);
}
int CdID::ChannelID (const Identifier& id)    
{
    return ((id.getValue() & CdID::ChannelID_MASK) >>  ChannelID_INDEX);

}*/
uint64_t CdID::getIntID ( uint64_t SiPMNo,
                               uint64_t SignalCableID,
                               uint64_t HVBundleID,
                               uint64_t HVCableID,
                               uint64_t CopyNo,
                               uint64_t ChannelID
                            )
{
    uint64_t value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (SiPMNo << SiPMNo_INDEX) |
                         (HVBundleID << HVBundleID_INDEX) |
                         (HVCableID << HVCableID_INDEX) |
                         (SignalCableID << SignalCableID_INDEX) |
                         (CopyNo << CopyNo_INDEX) |
                         (ChannelID << ChannelID_INDEX);                     
    return value;
}
Identifier CdID::id ( uint64_t SiPMNo,
                               uint64_t SignalCableID,
                               uint64_t HVBundleID,
                               uint64_t HVCableID,
                               uint64_t CopyNo,
                               uint64_t ChannelID
                             )
{
    uint64_t value = (TAODetectorID::CD_ID << CD_INDEX) | 
                         (SiPMNo << SiPMNo_INDEX) |
                         (HVBundleID << HVBundleID_INDEX) |
                         (HVCableID << HVCableID_INDEX) |
                         (SignalCableID << SignalCableID_INDEX) |
                         (CopyNo << CopyNo_INDEX) |
                         (ChannelID << ChannelID_INDEX);
                         
    return Identifier(value); 
}

int CdID::SiPMNo (const Identifier& id)    
{
    return int((id.getValue() & CdID::SiPMNo_MASK) >> SiPMNo_INDEX);
}

int CdID::HVBundleID (const Identifier& id)    
{
    return int((id.getValue() & CdID::HVBundleID_MASK) >> HVBundleID_INDEX);
}

int CdID::HVCableID (const Identifier& id)    
{
    return int((id.getValue() & CdID::HVCableID_MASK) >> HVCableID_INDEX);
}

int CdID::SignalCableID (const Identifier& id)   
{
    return int((id.getValue() & CdID::SignalCableID_MASK) >>  SignalCableID_INDEX);
}

int CdID::CopyNo (const Identifier& id)  
{
    return int((id.getValue() & CdID::CopyNo_MASK) >>  CopyNo_INDEX);
}

int CdID::ChannelID (const Identifier& id)    
{
    return int((id.getValue() & CdID::ChannelID_MASK) >>  ChannelID_INDEX);
}