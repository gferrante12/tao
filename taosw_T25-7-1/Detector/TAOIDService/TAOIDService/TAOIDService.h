//
//  Author: Jiayang Xu  2025.7.15
//  E-mail:xujy@ihep.ac.cn
//

#ifndef TAO_ID_SERVICE_H
#define TAO_ID_SERVICE_H

#include "TAOIDService/Identifier.h"
#include "TAOIDService/CdID.h"
#include "TAOIDService/WtID.h"
#include "TAOIDService/Identifier.h"
#include "TAOIDService/TAODetectorID.h"

#include <unordered_map>
#include <string>
#include <vector>
#include <atomic>
#include <cstdint>

class TAOIDService
{
    public:
        static TAOIDService *getIdServ();
        void init();
        void init_cd();
        

        Identifier fCdChannel2Id(const int& ChannelID);
        int fid2CdChannelId(const Identifier& id);
        Identifier fCdFEC2Id(const int& ChannelID);
        int fid2CdFEC(const Identifier& id);
        std::vector<std::string> split(const std::string &s);
    
    private:
        
        TAOIDService();
        ~TAOIDService();
        

        std::unordered_map<int, Identifier> CdChannel2Id;
        std::unordered_map<Identifier, int> Id2CdChannelId;
        std::unordered_map<int, Identifier> CdFEC2Id;
        std::unordered_map<Identifier,int> Id2CdFEC;

};

#endif // TAO_ID_SERVICE_H
