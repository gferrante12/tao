//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//


#ifndef RelativePDECalibTool_h
#define RelativePDECalibTool_h
#include <boost/python.hpp>
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "TH1F.h"
class RelativePDECalibTool: public ToolBase {
public:

  RelativePDECalibTool(const std::string& name);
  ~RelativePDECalibTool();

  bool init();
  bool CalibRelativePDE(float *RelativePDE, float *zeroPE,int event);
  

private:
 
};


#endif