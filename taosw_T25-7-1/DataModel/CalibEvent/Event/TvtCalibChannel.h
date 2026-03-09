#ifndef TvtCalibChannel_h
#define TvtCalibChannel_h

#include <TObject.h>
#include <vector>
namespace Tao
{
    class TvtCalibChannel: public TObject {
    private:
            Int_t CalibfChannelId;

            // T/Q pairs
            std::vector<float> CalibPEs;
            std::vector<float> CalibfTimes;
            std::vector<float> CalibfWidths;
            public:
            TvtCalibChannel(){
                CalibfChannelId = -9;
            }

            ~TvtCalibChannel(){
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

            ClassDef(TvtCalibChannel,2)
    
    };
}

#endif
