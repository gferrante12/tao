//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//

#ifndef DarkCountRateCalibTool_h
#define DarkCountRateCalibTool_h
#include <boost/python.hpp>
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "TH1F.h"

class DarkCountRateCalibTool: public ToolBase {
public:

  DarkCountRateCalibTool(const std::string& name);
  ~DarkCountRateCalibTool();

  bool init();
  bool CalibDarkCountRate(float *DCR, TH1F *h_TDC,int events);
  

private:
 
};


#endif