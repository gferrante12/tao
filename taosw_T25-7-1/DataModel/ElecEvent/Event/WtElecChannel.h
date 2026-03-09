#ifndef WtElecChannel_h
#define WtElecChannel_h

#include <TObject.h>
#include <vector>

namespace Tao
{
    class WtElecChannel: public TObject {
        private:
            uint16_t fChannelId;
            uint8_t fBlockChannelId;
            uint8_t Gain_Type;
            uint8_t Trigger_Type;
            // T/Q pairs
            std::vector<uint16_t> fADCs;
            //std::vector<float> fTDCs;
            std::vector<uint16_t> fCTOverflows;
            std::vector<uint32_t> fBECTimes;
            std::vector<uint32_t> fCoarseTimes;
            std::vector<uint16_t> fFineTimes;

        public:
            WtElecChannel(){
                fChannelId = 0;
                fBlockChannelId = 0; 
            }

            ~WtElecChannel(){
            }

        public:
            //getters
            uint8_t getBlockChannelID()                        {   return fBlockChannelId;     }
            uint16_t getChannelID()                        {   return fChannelId;     }
            uint8_t getTriggerType()                        {   return Trigger_Type;     }
            uint8_t getGainType()                        {   return Gain_Type;     }
            const std::vector<uint16_t>& getADCs() const   {   return fADCs;          }
            const std::vector<uint16_t>& getCTOverflows() const   {   return fCTOverflows;          }
            const std::vector<uint32_t>& getBECTimes() const   {   return fBECTimes;          }
            const std::vector<uint32_t>& getCoarseTimes() const   {   return fCoarseTimes;          }
            const std::vector<uint16_t>& getFineTimes() const   {   return fFineTimes;          }
            //const std::vector<float>& getTDCs() const   {   return fTDCs;          }

            //setters
            void setBlockChannelID(uint8_t id)                 {  fBlockChannelId = id;        }
            void setChannelID(uint16_t id)                 {  fChannelId = id;        }
            void setTriggerType(uint8_t n)                 {  Trigger_Type = n;        }
            void setGainType(uint8_t n)                 {  Gain_Type = n;        }
            void setADC(uint16_t adc)                      {  fADCs.push_back(adc);   }
            void setCTOverflow(uint16_t t)   {   fCTOverflows.push_back(t);          }
            void setBECTime(uint32_t t)   {   fBECTimes.push_back(t);         }
            void setCoarseTime(uint32_t t)   {   fCoarseTimes.push_back(t);          }
            void setFineTime(uint16_t t)  {   fFineTimes.push_back(t);          }
            //void setTDC(float tdc)                      {  fTDCs.push_back(tdc);   }
            void setADCs(const std::vector<uint16_t>& v)   {  fADCs = v;              }
            void setCTOverflows(const std::vector<uint16_t>& v)   {   fCTOverflows = v;         }
            void setBECTimes(const std::vector<uint32_t>& v)   {   fBECTimes = v;          }
            void setCoarseTimes(const std::vector<uint32_t>& v)  {   fCoarseTimes = v;         }
            void setFineTimes(const std::vector<uint16_t>& v)   {   fFineTimes = v;          }
            //void setTDCs(const std::vector<float>& v)   {  fTDCs = v;              }

        public:

            ClassDef(WtElecChannel,2)
    };
}

#endif
