#ifndef CdCalibChannel_h
#define CdCalibChannel_h

#include <TObject.h>
#include <vector>
namespace Tao
{
    class CdCalibChannel: public TObject {
    private:
            Int_t CalibfChannelId;

            // T/Q pairs
            std::vector<float> CalibPEs;
            std::vector<float> CalibfTimes;
            std::vector<float> CalibfWidths;
            public:
            CdCalibChannel(){
                CalibfChannelId = -9;
            }

            ~CdCalibChannel(){
            }
    public:
            //getters
            Int_t CalibgetChannelID()                        {   return CalibfChannelId;     }
            const std::vector<float>& CalibgetPEs() const   {   return CalibPEs;          }
            const std::vector<float>& CalibgetTDCs() const   {   return CalibfTimes;          }
            const std::vector<float>& CalibgetWidths() const {   return CalibfWidths;        }

            //setters
            void CalibsetChannelID(Int_t id)                 {  CalibfChannelId = id;        }
            void CalibsetPE(float adc)                      {  CalibPEs.push_back(adc);   }
            void CalibsetTime(float tdc)                      {  CalibfTimes.push_back(tdc);   }
            void CalibsetWidth(float w)                      {  CalibfWidths.push_back(w);   }
            void CalibsetPEs(const std::vector<float>& v)   {  CalibPEs = v;              }
            void CalibsetTimes(const std::vector<float>& v)   {  CalibfTimes = v;              }
            void CalibsetWidths(const std::vector<float>& v) {  CalibfWidths = v;            }

        public:

            ClassDef(CdCalibChannel,2)
    
    };
}

#endif