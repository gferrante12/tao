//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//


#ifndef GainCalibTool_h
#define GainCalibTool_h
#include <boost/python.hpp>
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"
#include "TH1F.h"
#include <TF1.h>
#include <TMath.h>
#include <TCanvas.h>
#include <TFile.h>
#include <string>
class GainCalibTool: public ToolBase {
public:

  GainCalibTool(const std::string& name);
  ~GainCalibTool();

  bool init();
  bool CalibGain(float *gain, TH1F *h_ADCs);
  static double mutigaussion(double *x, double *par);
  static double line(double *x, double *par);
  

private:
    //TF1*  fFunctionGainGaus;
    //TF1*  fFunctionGainLine;
    TFile* f2;
    TCanvas* c2;
    TCanvas* c3;
    int m_outflag;
    std::string m_outgain;
 
};


#endif