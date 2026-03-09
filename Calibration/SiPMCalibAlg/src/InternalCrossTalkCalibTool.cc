#include "InternalCrossTalkCalibTool.h"

#include "TH1F.h"
#include "SniperKernel/SniperDataPtr.h"
#include "SniperKernel/SniperLog.h"
#include <TF1.h>
#include <TMath.h>
#include <TGraph.h>
#include <TCanvas.h>
#include <TFile.h>
#include "TSpectrum.h"
#include "RooDataHist.h"
#include "RooGenericPdf.h"
#include "RooFitResult.h"
#include "RooRealVar.h"
#include "RooArgList.h"
#include "RooPlot.h"
#include <iostream>
#include <string>

#include <map>
#include <cmath>

DECLARE_TOOL(InternalCrossTalkCalibTool);

InternalCrossTalkCalibTool::InternalCrossTalkCalibTool(const std::string& name):ToolBase(name){
    declProp("outinctfile",    m_outinct = "./outinct.root");
    declProp("outinctflag",    m_outflag = -1);
}
InternalCrossTalkCalibTool::~InternalCrossTalkCalibTool() {
    
}
bool InternalCrossTalkCalibTool::init() {
    return true;
}
double InternalCrossTalkCalibTool::GPFunction(double mu,double lamda,int n)
{
    double GP=mu*pow((mu+double(n)*lamda),double(n-1))*exp(-(mu+double(n)*lamda))/double(TMath::Factorial(n));
    return GP;
}
double InternalCrossTalkCalibTool::GausVaule(double x,double mu, double sigma)
{
    return TMath::Gaus(x,mu,sigma,kTRUE);
}
bool InternalCrossTalkCalibTool::CalibInternalCrossTalk(float *inct, TH1F *h_ADCs) {

    std::string dir = getenv("SIPMCALIBALGROOT");
    dir+="/include/InternalCrossTalkCalibTool.h";
    std::string path = "#include \"";
    path+=dir;
    path+="\"";
    gInterpreter->Declare(path.c_str());
    
    if(m_outflag!=-1)
    {
        f3 = new TFile(m_outinct.c_str(), "RECREATE");
        c4 = new TCanvas("c4","c4",800,600);
        f3->cd();
    }

    TH1F* histo = new TH1F("histo","histo",250,0,50000);
    TSpectrum *QSpectrum = new TSpectrum();
    for(int i=0;i<8048;i++)
    {
        
        for(int j=0;j<250;j++)
        {
            histo->SetBinContent(j+1,h_ADCs[i].GetBinContent(j+1));
            
        }

        histo->Smooth();
        std::map<double, double> peakmap;
        peakmap.clear(); 
        Int_t nPeaks = QSpectrum->Search(histo, 2, "", 0.001);
        Double_t *xpositions= QSpectrum->GetPositionX();
        Double_t *ypositions= QSpectrum->GetPositionY();
        LogDebug<<"----------------PEAKS::"<<nPeaks<<std::endl;
        for(int j=0;j<nPeaks;j++)
        {
            peakmap.insert(std::make_pair(xpositions[j],ypositions[j]));
        }
        double xpeak[nPeaks],ypeak[nPeaks];
        int countmap = 0;
        for (auto it = peakmap.begin(); it != peakmap.end() && countmap < nPeaks; ++it) {
            xpeak[countmap] = it->first;
            ypeak[countmap] = it->second;
            countmap++;       
        }

        RooRealVar x("x", "x", xpeak[0]-1000,xpeak[2]+500);
        RooRealVar sigma1("sigma1","sigma1",sqrt(1)*xpeak[0]*0.15,sqrt(1)*xpeak[0]*0.1,sqrt(1)*xpeak[0]*0.2);
        RooRealVar sigma2("sigma2","sigma2",sqrt(2)*xpeak[0]*0.15,xpeak[0]*0.1*sqrt(2),xpeak[0]*0.2*sqrt(2));
        RooRealVar sigma3("sigma3","sigma3",sqrt(3)*xpeak[0]*0.15,xpeak[0]*0.1*sqrt(3),xpeak[0]*0.2*sqrt(3));

        RooRealVar mean1("mean1","mean1",xpeak[0],xpeak[0]-1000,xpeak[0]+1000);
        RooRealVar mean2("mean2","mean2",xpeak[1],xpeak[1]-1000,xpeak[1]+1000);
        RooRealVar mean3("mean3","mean3",xpeak[2],xpeak[2]-1000,xpeak[2]+1000);

        RooRealVar N("N", "N", 1000,10,1e9);

        RooRealVar mu("mu", "mu", 0.5,0,25);
        RooRealVar lamda("lamda", "lamda", 0.1,0.01,0.4);
        RooDataHist dataHist("dataHist", "Data Histogram", x, histo);
        std::string formula = "N*InternalCrossTalkCalibTool::GPFunction(mu,lamda,1)*InternalCrossTalkCalibTool::GausVaule(x,mean1,sigma1)";
        formula += "+N*InternalCrossTalkCalibTool::GPFunction(mu,lamda,2)*InternalCrossTalkCalibTool::GausVaule(x,mean2,sigma2)";
        formula += "+N*InternalCrossTalkCalibTool::GPFunction(mu,lamda,3)*InternalCrossTalkCalibTool::GausVaule(x,mean3,sigma3)";
        
        
        RooGenericPdf pdf("pdf", "pdf", formula.c_str(), RooArgList(x,N,mu,lamda,mean1,sigma1,mean2,sigma2,mean3,sigma3));
        RooFitResult* fitResult = pdf.chi2FitTo(dataHist, RooFit::Save(), RooFit::Minimizer("Minuit2"), RooFit::Range(xpeak[0]-1000,xpeak[2]+500));
        fitResult->Print();

        if(m_outflag!=-1)
        {
            RooPlot* frame = x.frame();
            dataHist.plotOn(frame);
            pdf.plotOn(frame);
            frame->GetXaxis()->SetTitle("Charge");
            frame->GetYaxis()->SetTitle("Events");
            c4->cd();
            frame->Draw();
            std::string hist_name = "Ch";
            hist_name+=std::to_string(i);
            hist_name+="_ChargeFit";
            c4->Write(hist_name.c_str());
        }   
        inct[i] = lamda.getVal();
    }

    delete histo;
    delete QSpectrum;

    if(m_outflag!=-1)
    {
        f3->Close();
        delete f3;
        delete c4;
    }
    return true;


}