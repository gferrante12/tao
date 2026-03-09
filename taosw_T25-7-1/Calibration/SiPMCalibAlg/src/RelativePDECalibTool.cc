//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//


#include "RelativePDECalibTool.h"

#include "TH1F.h"
#include "SniperKernel/SniperDataPtr.h"
#include "SniperKernel/SniperLog.h"


DECLARE_TOOL(RelativePDECalibTool);

RelativePDECalibTool::RelativePDECalibTool(const std::string& name):ToolBase(name){

}
RelativePDECalibTool::~RelativePDECalibTool() {

}
bool RelativePDECalibTool::init() {

    return true;
}

bool RelativePDECalibTool::CalibRelativePDE(float *RelativePDE, float *zeroPE,int event) {
    
    
    float mu[8048];
    for(int i=0;i<8048;i++)
    {
        mu[i]=-log(zeroPE[i]/event);
        RelativePDE[i]=(mu[i]/mu[0]);
    }
    return true;
    
}