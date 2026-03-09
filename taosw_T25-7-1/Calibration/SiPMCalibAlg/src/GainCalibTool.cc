//
//  Author: Jiayang Xu  2023.11.15
//  E-mail:xujy@ihep.ac.cn
//


#include "GainCalibTool.h"

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

DECLARE_TOOL(GainCalibTool);

GainCalibTool::GainCalibTool(const std::string& name):ToolBase(name){
    declProp("outgainfile",    m_outgain = "./outgain.root");
    declProp("outgainflag",    m_outflag = -1);
}
GainCalibTool::~GainCalibTool() {
    
}
bool GainCalibTool::init() {
    return true;
}
double GainCalibTool::line(double *x, double *par)
{
    double y=0;
    y=par[0]*x[0]+par[1];
    return y;
}
bool GainCalibTool::CalibGain(float *gain, TH1F *h_ADCs) {
   
    TF1* fFunctionGainLine = new TF1("functiongainline", GainCalibTool::line, 0,14000 ,2);    
    if(m_outflag!=-1)
    {
        f2 = new TFile(m_outgain.c_str(), "RECREATE");
        c2 = new TCanvas("c2","c2",800,600);
        c3 = new TCanvas("c3","c3",800,600);
        f2->cd();
    }
    float mu[4];
    TGraph *gr = new TGraph();
    gr->SetMarkerStyle(20);
    gr->SetMarkerSize(0.8);
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
        RooRealVar x("x", "x", 0,xpeak[4]+500);
        RooRealVar sigma1("sigma1","sigma1",sqrt(1)*xpeak[0]*0.15,sqrt(1)*xpeak[0]*0.05,sqrt(1)*xpeak[0]*0.25);
        RooRealVar sigma2("sigma2","sigma2",sqrt(2)*xpeak[0]*0.15,xpeak[0]*0.05*sqrt(2),xpeak[0]*0.25*sqrt(2));
        RooRealVar sigma3("sigma3","sigma3",sqrt(3)*xpeak[0]*0.15,xpeak[0]*0.05*sqrt(3),xpeak[0]*0.25*sqrt(3));
        RooRealVar sigma4("sigma4","sigma4",sqrt(4)*xpeak[0]*0.15,xpeak[0]*0.05*sqrt(4),xpeak[0]*0.25*sqrt(4));
        RooRealVar sigma5("sigma5","sigma5",sqrt(5)*xpeak[0]*0.15,xpeak[0]*0.05*sqrt(5),xpeak[0]*0.25*sqrt(5));

        RooRealVar mean1("mean1","mean1",xpeak[0],xpeak[0]-1000,xpeak[0]+1000);
        RooRealVar mean2("mean2","mean2",xpeak[1],xpeak[1]-1000,xpeak[1]+1000);
        RooRealVar mean3("mean3","mean3",xpeak[2],xpeak[2]-1000,xpeak[2]+1000);
        RooRealVar mean4("mean4","mean4",xpeak[3],xpeak[3]-1000,xpeak[3]+1000);
        RooRealVar mean5("mean5","mean5",xpeak[4],xpeak[4]-1000,xpeak[4]+1000);


        RooRealVar n1("n1","n1",ypeak[0],0.5*ypeak[0],2*ypeak[0]);
        RooRealVar n2("n2","n2",ypeak[1],0.5*ypeak[1],2*ypeak[1]);
        RooRealVar n3("n3","n3",ypeak[2],0.5*ypeak[2],2*ypeak[2]);
        RooRealVar n4("n4","n4",ypeak[3],0.5*ypeak[3],2*ypeak[3]);
        RooRealVar n5("n5","n5",ypeak[4],0.5*ypeak[4],2*ypeak[4]);

        RooDataHist dataHist("dataHist", "Data Histogram", x, histo);
        std::string formula;
        formula = "n1*exp(-(x-mean1)*(x-mean1)/(2*sigma1*sigma1))";
        formula += "+n2*exp(-(x-mean2)*(x-mean2)/(2*sigma2*sigma2))";
        formula += "+n3*exp(-(x-mean3)*(x-mean3)/(2*sigma3*sigma3))";
        formula += "+n4*exp(-(x-mean4)*(x-mean4)/(2*sigma4*sigma4))";
        formula += "+n5*exp(-(x-mean5)*(x-mean5)/(2*sigma5*sigma5))";

        RooGenericPdf pdf("pdf", "pdf", formula.c_str(), RooArgList(x,sigma1,sigma2,sigma3,sigma4,sigma5,mean1,mean2,mean3,mean4,mean5,n1,n2,n3,n4,n5));
        RooFitResult* fitResult = pdf.fitTo(dataHist, RooFit::Save(),RooFit::Range(0,xpeak[4]+500));
        fitResult->Print();
        gr->SetPoint(1,1,mean1.getVal());
        gr->SetPoint(2,2,mean2.getVal());
        gr->SetPoint(3,3,mean3.getVal());
        gr->SetPoint(4,4,mean4.getVal());
        if(m_outflag!=-1)
        {
            RooPlot* frame = x.frame();
            dataHist.plotOn(frame);
            pdf.plotOn(frame);
            frame->GetXaxis()->SetTitle("Charge");
            frame->GetYaxis()->SetTitle("Events");
            c2->cd();
            frame->Draw();
            std::string hist_name = "Ch";
            hist_name+=std::to_string(i);
            hist_name+="_ChargeFit";
            c2->Write(hist_name.c_str());
        }   
        gr->Fit("functiongainline","R","",0,5);
        if(m_outflag!=-1)
        {
            c3->cd();
            gr->Draw("AP");
            std::string hist_name1 = "Ch";
            hist_name1+=std::to_string(i);
            hist_name1+="_GainFit";
            c3->Write(hist_name1.c_str()); 
        }
        gain[i] = fFunctionGainLine->GetParameter(0);
    }
    delete gr;
    delete histo;
    delete fFunctionGainLine;
    delete QSpectrum;
    if(m_outflag!=-1)
    {
        f2->Close();
        delete f2;
        delete c2;
        delete c3;
    }
    return true;
}