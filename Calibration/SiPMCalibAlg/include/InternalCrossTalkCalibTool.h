#ifndef InternalCrossTalkCalibTool_h
#define InternalCrossTalkCalibTool_h

#include <boost/python.hpp>
#include "SniperKernel/ToolBase.h"
#include "SniperKernel/ToolFactory.h"
#include "SniperKernel/SniperPtr.h"

#include "TH1F.h"
#include <TFile.h>
#include <TCanvas.h>

#include <string>


class InternalCrossTalkCalibTool: public ToolBase {
    public:
    
      InternalCrossTalkCalibTool(const std::string& name);
      ~InternalCrossTalkCalibTool();
    
      bool init();
      bool CalibInternalCrossTalk(float *inct, TH1F *h_ADCs);
      static double GPFunction(double mu,double lamda,int n);
      static double GausVaule(double x,double mu, double sigma);

    private:
        TFile* f3;
        TCanvas* c4;
        int m_outflag;
        std::string m_outinct;
     
    };



#endif