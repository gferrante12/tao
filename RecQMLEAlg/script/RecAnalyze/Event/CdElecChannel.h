#ifndef CdElecChannel_h
#define CdElecChannel_h

#include <TObject.h>
#include <vector>

namespace Tao
{
    class CdElecChannel: public TObject {
        private:
            Int_t fChannelId;

            // T/Q pairs
            std::vector<float> fADCs;
            std::vector<float> fTDCs;
            std::vector<float> fWidths;

        public:
            CdElecChannel(){
                fChannelId = -9;
            }

            ~CdElecChannel(){
            }

        public:
            //getters
            Int_t getChannelID()                        {   return fChannelId;     }
            const std::vector<float>& getADCs() const   {   return fADCs;          }
            const std::vector<float>& getTDCs() const   {   return fTDCs;          }
            const std::vector<float>& getWidths() const {   return fWidths;        }

            //setters
            void setChannelID(Int_t id)                 {  fChannelId = id;        }
            void setADC(float adc)                      {  fADCs.push_back(adc);   }
            void setTDC(float tdc)                      {  fTDCs.push_back(tdc);   }
            void setWidth(float w)                      {  fWidths.push_back(w);   }
            void setADCs(const std::vector<float>& v)   {  fADCs = v;              }
            void setTDCs(const std::vector<float>& v)   {  fTDCs = v;              }
            void setWidths(const std::vector<float>& v) {  fWidths = v;            }

        public:

            ClassDef(CdElecChannel,2)
    };
}

#endif


