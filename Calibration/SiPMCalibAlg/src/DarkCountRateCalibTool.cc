//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//

#include "DarkCountRateCalibTool.h"

#include "TH1F.h"
#include "SniperKernel/SniperDataPtr.h"
#include "SniperKernel/SniperLog.h"


DECLARE_TOOL(DarkCountRateCalibTool);

DarkCountRateCalibTool::DarkCountRateCalibTool(const std::string& name):ToolBase(name){

}
DarkCountRateCalibTool::~DarkCountRateCalibTool() {

}
bool DarkCountRateCalibTool::init() {

    return true;
}

bool DarkCountRateCalibTool::CalibDarkCountRate(float *DCR, TH1F *h_TDCs,int events) {
    //Sensitive Area of One Channel(mm^2)
    float S=72*16;
    float darknoise;
    for(int i=0;i<8048;i++)
    {
        //trigger timewindow:-100~900 ns, 0~-100ns:dark noise;
        //TDC Sensitive Area:4ns one point
        darknoise=0;
        for(int j=0;j<=100/4;j++)
        {
            darknoise+=h_TDCs[i].GetBinContent(j+1);
        }
        DCR[i]=darknoise/(S*1e-7*float(events));
    }

    return true;
}