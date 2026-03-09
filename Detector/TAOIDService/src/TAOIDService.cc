//
//  Author: Jiayang Xu  2025.7.15
//  E-mail:xujy@ihep.ac.cn
//


#include "TAOIDService/TAOIDService.h"

#include "SniperKernel/SvcFactory.h"
#include "SniperKernel/SniperLog.h"
#include "SniperKernel/SniperPtr.h"
#include "SniperKernel/Incident.h"

#include <DataPathHelper/Path.hh>

#include "TSystem.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <boost/filesystem.hpp>


TAOIDService::TAOIDService() 
{

}

TAOIDService::~TAOIDService()
{
    
}

void TAOIDService::init()
{
    init_cd();
}


std::vector<std::string> TAOIDService::split(const std::string &s) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream(s);
    
    while (std::getline(tokenStream, token, ',')) {
        size_t start = token.find_first_not_of(" \t");
        size_t end = token.find_last_not_of(" \t");
        if (start != std::string::npos && end != std::string::npos) {
            tokens.push_back(token.substr(start, end - start + 1));
        } else if (start != std::string::npos) { 
            tokens.push_back(token.substr(start));
        } else if (end != std::string::npos) { 
            tokens.push_back(token.substr(0, end + 1));
        } else {
            tokens.push_back(""); 
        }
    }
    return tokens;
}

void TAOIDService::init_cd()
{
    std::string IDPath = getenv("TAOIDSERVICEROOT");
    std::string m_input_cdid_file = IDPath+"/python/TAOIDService/CDSIPMID.csv";
    std::ifstream sipmsrc(m_input_cdid_file.c_str());
    if (!sipmsrc.is_open()) {
        LogError << "Failed to open the file:"<< m_input_cdid_file << std::endl;
        return;
    }
    std::vector<std::vector<std::string>> csvData;
    std::string firstLine;
    std::getline(sipmsrc, firstLine);
    std::string line;
    while (std::getline(sipmsrc, line)) {
        if (line.empty()) continue; // 跳过空行
        std::vector<std::string> row = split(line);
        csvData.push_back(row);
    }
    uint64_t SiPMNo,HVBundleID,HVCableID,SignalCableID,CopyNo,ChID,FECID,FECChID;
    for(int i=0;i<csvData.size();i++)
    {
        SiPMNo = uint64_t(std::stoi(csvData[i][3]));
        SignalCableID = uint64_t(std::stoi(csvData[i][4]));
        HVBundleID = uint64_t(std::stoi(csvData[i][5]));
        HVCableID = uint64_t(std::stoi(csvData[i][6]));
        CopyNo = uint64_t(std::stoi(csvData[i][9]));
        FECID = uint64_t(std::stoi(csvData[i][13]));
        FECChID = uint64_t(std::stoi(csvData[i][14]));
        if(FECChID%2==0)
        {
            ChID = 0;
        }
        else
        {
            ChID = 1;
        }
        
        Identifier id = CdID::id(SiPMNo,SignalCableID,HVBundleID,HVCableID,CopyNo,ChID);
        CdChannel2Id[int(CopyNo*2+ChID)]=id;
        Id2CdChannelId[id]= int(CopyNo*2+ChID);
        CdFEC2Id[int(FECID*1000+FECChID)]=id;
        Id2CdFEC[id]=int(FECID*1000+FECChID);
    }
    sipmsrc.close();

}

TAOIDService* TAOIDService::getIdServ()
{
    static TAOIDService instance;
    return &instance;
}

Identifier TAOIDService::fCdChannel2Id(const int& ChannelID)
{
    auto it = CdChannel2Id.find(ChannelID);
    if ( it == CdChannel2Id.end() ) {
        LogDebug << "ChannelID " << ChannelID <<  "'s id does not exist " << std::endl;
        return Identifier(0xFFFFFFFFFFFFFFFF);
    }
    return it-> second; 
}

int TAOIDService::fid2CdChannelId(const Identifier& id)
{
    auto it = Id2CdChannelId.find(id);
    if ( it == Id2CdChannelId.end() ) {
        LogError << "id " << id <<  "'s Channel ID does not exist " << std::endl;
        return -1;
    }
    return it-> second;  
}

Identifier TAOIDService::fCdFEC2Id(const int& ChannelID)
{
    auto it = CdFEC2Id.find(ChannelID);
    if ( it == CdFEC2Id.end() ) {
        LogDebug << "FEC ChannelID " << ChannelID <<  "'s id does not exist " << std::endl;
        return Identifier(0xFFFFFFFFFFFFFFFF);
    }
    return it-> second; 
}

int TAOIDService::fid2CdFEC(const Identifier& id)
{
    auto it = Id2CdFEC.find(id);
    if ( it == Id2CdFEC.end() ) {
        LogError << "id " << id <<  "'s FEC Channel ID does not exist " << std::endl;
        return -1;
    }
    return it-> second;  
}