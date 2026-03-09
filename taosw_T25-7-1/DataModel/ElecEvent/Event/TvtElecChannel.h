#ifndef TvtElecChannel_h
#define TvtElecChannel_h

#include <TObject.h>
#include <vector>

namespace Tao
{
    class TvtElecChannel: public TObject {
        private:
            uint16_t fChannelId;

            // T/Q pairs
            std::vector<uint8_t> fUpper8ADCs;
            std::vector<uint16_t> fLower16ADCs;
            std::vector<int64_t> fTDCs;
            std::vector<uint16_t> fWidths;
            std::vector<uint16_t> fBaselines;
            std::vector<bool> fOF1s;
            std::vector<bool> fOF2s; 
            std::vector<bool> fOF3s; 
            //std::vector<uint16_t> fLower16_flag_baseline_widths;
            //std::vector<uint8_t> fUpper8_flag_baseline_widths;

        public:
            TvtElecChannel(){
                fChannelId = -9;
            }

            ~TvtElecChannel(){
            }

        public:
            //getters
            uint16_t getChannelID()                        {   return fChannelId;     }
            std::vector<float> getADCs() {   
                
                std::vector<float> fADCs;
                fADCs.resize(fUpper8ADCs.size());
                for(std::size_t i=0;i<fUpper8ADCs.size();i++)
                {
                    uint32_t charge = (static_cast<uint32_t>(fUpper8ADCs[i]) << 16) | static_cast<uint32_t>(fLower16ADCs[i]);
                    fADCs[i] = static_cast<float>(charge);
                }
                return fADCs;          
            }

        
            std::vector<uint16_t> getWidths(){
                return fWidths; 
            }

            std::vector<uint16_t> getBaselines(){
                return fBaselines; 
            }

            std::vector<bool> getOF1s(){
                return fOF1s; 
            }

            std::vector<bool> getOF2s(){
                return fOF2s; 
            }

            std::vector<bool> getOF3s(){
                return fOF3s; 
            }

            /*std::vector<uint16_t> getWidths(){
                
                std::vector<uint16_t> fWidths;
                fWidths.resize(fLower16_flag_baseline_widths.size());
                for(std::size_t i=0;i<fLower16_flag_baseline_widths.size();i++)
                {
                    uint16_t width = fLower16_flag_baseline_widths[i] & 0x03FF;
                    fWidths[i] = width;
                }
                return fWidths; 
            }

            std::vector<uint16_t> getBaselines(){
                
                std::vector<uint16_t> fBaselines;
                fBaselines.resize(fLower16_flag_baseline_widths.size());
                for(std::size_t i=0;i<fLower16_flag_baseline_widths.size();i++)
                {
                    uint16_t baseline = ((fLower16_flag_baseline_widths[i] >> 10) & 0x003F) | ((fUpper8_flag_baseline_widths[i] & 0x3F) << 6);
                    fBaselines[i] = baseline;
                }
                return fBaselines; 
            }
            
            std::vector<uint8_t> getOF2s(){
                
                std::vector<uint8_t> fOF2s;
                fOF2s.resize(fUpper8_flag_baseline_widths.size());
                for(std::size_t i=0;i<fUpper8_flag_baseline_widths.size();i++)
                {
                    uint8_t OF2 = (fUpper8_flag_baseline_widths[i] >> 6) & 0x01;
                    fOF2s[i] = OF2;
                }
                return fOF2s; 
            }

            std::vector<uint8_t> getOF1s(){
                
                std::vector<uint8_t> fOF1s;
                fOF1s.resize(fUpper8_flag_baseline_widths.size());
                for(std::size_t i=0;i<fUpper8_flag_baseline_widths.size();i++)
                {
                    uint8_t OF1 = (fUpper8_flag_baseline_widths[i] >> 7) & 0x01;
                    fOF1s[i] = OF1;
                }
                return fOF1s; 
            }*/
            
            
            
            const std::vector<int64_t>& getTDCs() const   {   return fTDCs;          }
            //const std::vector<uint16_t>& getWidths() const {   return fWidths;        }
            const std::vector<uint8_t>& getUpper8ADCs() const {   return fUpper8ADCs;        }
            const std::vector<uint16_t>& getLower16ADCs() const {   return fLower16ADCs;        }

            //const std::vector<uint8_t>& getUpper8_flag_baseline_widths() const {   return fUpper8_flag_baseline_widths;        }
            //const std::vector<uint16_t>& getLower16_flag_baseline_widths() const {   return fLower16_flag_baseline_widths;        }

            //setters
            void setChannelID(uint16_t id)                 {  fChannelId = id;        }
            void setUpper8ADC(uint8_t adc)                      {  fUpper8ADCs.push_back(adc);   }
            //void setLower16_flag_baseline_width(uint16_t adc)                      {  fLower16_flag_baseline_widths.push_back(adc);   }
            //void setUpper8_flag_baseline_width(uint8_t adc)                      {  fUpper8_flag_baseline_widths.push_back(adc);   }
            void setLower16ADC(uint16_t adc)                      {  fLower16ADCs.push_back(adc);   }
            void setTDC(int64_t tdc)                      {  fTDCs.push_back(tdc);   }
            void setWidth(uint16_t w)                      {  fWidths.push_back(w);   }
            void setBaseline(uint16_t w)                      {  fBaselines.push_back(w);   }
            void setOF1(bool w)                      {  fOF1s.push_back(w);   }
            void setOF2(bool w)                      {  fOF2s.push_back(w);   }
            void setOF3(bool w)                      {  fOF3s.push_back(w);   }
            void setUpper8ADCs(const std::vector<uint8_t>& v)   {  fUpper8ADCs = v;              }
            void setLower16ADCs(const std::vector<uint16_t>& v)   {  fLower16ADCs = v;              }
            //void setLower16_flag_baseline_widths(const std::vector<uint16_t>& v)                      {  fLower16_flag_baseline_widths = v;   }
            //void setUpper8_flag_baseline_widths(const std::vector<uint8_t>& v)                      {  fUpper8_flag_baseline_widths = v;   }
            void setTDCs(const std::vector<int64_t>& v)   {  fTDCs = v;              }
            void setWidths(const std::vector<uint16_t>& v) {  fWidths = v;            }
            void setBaselines(const std::vector<uint16_t>& v) {  fBaselines = v;            }
            void setOF1s(const std::vector<bool>& v) {  fOF1s = v;            }
            void setOF2s(const std::vector<bool>& v) {  fOF2s= v;            }
            void setOF3s(const std::vector<bool>& v) {  fOF3s = v;            }

        public:

            ClassDef(TvtElecChannel,2)
    };
}

#endif


