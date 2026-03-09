//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//


#ifndef TimeoffsetCalibTool_h
#define TimeoffsetCalibTool_h
#include <boost/python.hpp>
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "TH1F.h"
#include <TF1.h>
#include <TMath.h>
#include <TCanvas.h>
#include <TFile.h>
class TimeoffsetCalibTool: public ToolBase {
public:

  TimeoffsetCalibTool(const std::string& name);
  ~TimeoffsetCalibTool();

  bool init();
  bool CalibTimeoffset(float *timeoffset, TH1F *h_FirstHitTime);
  static double gaussion(double *x, double *par);
  

private:
    //TF1*  fFunctionTimeoffset;
    TFile* f1;
    TCanvas* c1;
    int m_outflag;
    std::string m_outtime;
 
};


#endif