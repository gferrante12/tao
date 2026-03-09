//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//


#include "TimeoffsetCalibTool.h"

#include "TH1F.h"
#include "SniperKernel/SniperDataPtr.h"
#include "SniperKernel/SniperLog.h"
#include <TF1.h>
#include <TMath.h>
#include <TCanvas.h>
#include <TFile.h>
#include "RooDataHist.h"
#include "RooGenericPdf.h"
#include "RooFitResult.h"
#include "RooRealVar.h"
#include "RooArgList.h"
#include "RooCrystalBall.h"
#include "RooPlot.h"
DECLARE_TOOL(TimeoffsetCalibTool);

TimeoffsetCalibTool::TimeoffsetCalibTool(const std::string& name):ToolBase(name){

    declProp("outtimefile",    m_outtime = "./outtimeoffset.root");
    declProp("outtimeflag",    m_outflag = -1);

}
TimeoffsetCalibTool::~TimeoffsetCalibTool() {
}
bool TimeoffsetCalibTool::init() {
    return true;
}
bool TimeoffsetCalibTool::CalibTimeoffset(float *timeoffset, TH1F *h_FirstHitTime) {

   
    if(m_outflag!=-1)
    {
        f1 = new TFile(m_outtime.c_str(), "RECREATE");
        c1 = new TCanvas("c2","c2",800,600);
        f1->cd();
    }
    TH1F* histo = new TH1F("histo","histo",250,-100,900);
    for(int i=0;i<8048;i++)
    {
        for(int j=0;j<250;j++)
        {
            histo->SetBinContent(j+1,h_FirstHitTime[i].GetBinContent(j+1));
        }
        RooRealVar x("x", "x", -100,900);
        RooDataHist dataHist1("dataHist1", "Data Histogram", x, histo);
        RooRealVar mean("mean", "mean", 300, 250,350);
        RooRealVar sigmaL("sigmaL", "sigmaL", 10, 0.1, 100);
        RooRealVar alphaL("alphaL", "alphaL", 1, 1e-3, 10);
        RooRealVar nL("nL", "nL", 1, 1e-3, 10);
        RooRealVar sigmaR("sigmaR", "sigmaR", 10, 0.1, 100);
        RooRealVar alphaR("alphaR", "alphaR", 1, 1e-3, 10);
        RooRealVar nR("nR", "nR", 1, 1e-3, 10);
        RooCrystalBall crystalBall("crystalBall", "Crystal Ball", x, mean, sigmaL,sigmaR, alphaL, nL, alphaR, nR);
        RooFitResult* fitResult1 = crystalBall.chi2FitTo(dataHist1, RooFit::Save(), RooFit::Range(200,350));
        fitResult1->Print();
        if(m_outflag!=-1)
        {
            RooPlot* frame = x.frame();
            dataHist1.plotOn(frame);
            crystalBall.plotOn(frame);
            frame->GetXaxis()->SetTitle("Time[ns]");
            frame->GetYaxis()->SetTitle("Events");
            c1->cd();
            frame->Draw();
            std::string hist_name = "Ch";
            hist_name+=std::to_string(i);
            hist_name+="_TimeOffsetFit";
            c1->Write(hist_name.c_str());
        }
        timeoffset[i] = mean.getVal();
    }
    float timeoffsetzero = timeoffset[0];
    for(int i=0;i<8048;i++)
    {
        timeoffset[i] = timeoffset[i] - timeoffsetzero;
    }
    delete histo;
    if(m_outflag!=-1)
    {
        f1->Close();
        delete f1;
        delete c1;
    }
    return true;
    
}