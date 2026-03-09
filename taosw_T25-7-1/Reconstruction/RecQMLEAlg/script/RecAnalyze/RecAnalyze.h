#ifndef RecAnalyze_h
#define RecAnalyze_h

#include "TFile.h"
#include <string>
#include <vector>
#include "TH1F.h"
#include "TCanvas.h"
#include <iostream>
#include "TPaveStats.h"
#include <algorithm>
#include "TGraph.h"
#include "TGraphErrors.h"
#include "TGeoManager.h"
#include "TLegend.h"

#include <fstream>
#include <iostream>
#include "math.h"
#include <map>
#include <numeric>
#include <chrono>
#include <cmath>

#include "Event/SimTrack.h"
#include "Event/SimPMTHit.h"
#include "Event/SimEvt.h"
#include "Event/CdCalibHeader.h"
#include "Event/CdCalibEvt.h"
#include "Event/CdCalibChannel.h"
#include "Geometry/CdGeom.h"
#include "Geometry/SiPMGeom.h"


using namespace std;
using namespace std::chrono;

struct Position {
    float x;
    float y;
    float z;
    float Evis;   //沉积能量
};

// 获取root文件
TFile* GetRootFile(string fileName){
    TFile *file;
    string substr = "root://junoeos01.ihep.ac.cn//eos/";
    
    size_t found = fileName.find(substr);  // 使用find()函数查找子字符串
    if (found != std::string::npos) {
        file = TFile::Open(fileName.c_str());  //  读取EOS中的root文件
    } else {
        file = new TFile(fileName.c_str());  //  读取本地root文件
    }

    if (!file || file->IsZombie()) {
        std::cerr << "Error opening file: "<< fileName << endl;
        // exit(-1);
        // continue;
    }

    return file;
}

//  查找vector中最大值
float GetVectorMax(vector<float>& vec){
    float val = vec[0];
    for(int i =1; i < vec.size(); i++){
        if(val <= vec[i]) {
            val = vec[i];
        }
    }
    return val;
}

//  查找vector中最小值
float GetVectorMin(vector<float>& vec){
    float val = vec[0];
    for(int i =1; i < vec.size(); i++){
        if(val >= vec[i]) {
            val = vec[i];
        }
    }
    return val;
}

// //  画二维 Histogram
// void Draw2DHist(vector<float>& xbin, vector<float>& ybin, /*TFile* outFile,*/string outputFileName, string histTitle, string type ){
    
//     TH2F* hist = new TH2F(histTitle.c_str(), histTitle.c_str(), 100, GetVectorMin(xbin), GetVectorMax(xbin), 100, GetVectorMin(ybin), GetVectorMax(ybin));
//     // TH2F* hist = new TH2F("pe","hist_tile",100,0,100,100,0,100);
//     // 获取x轴、y轴和z轴对象，并设置标题
//     hist->GetXaxis()->SetTitle("x");
//     hist->GetYaxis()->SetTitle("y");
//     hist->GetZaxis()->SetTitle("z");

//     for(int i = 0; i < xbin.size(); i++){
//         hist->Fill(xbin[i], ybin[i]);
//     }
    
//     // // 将直方图写入 ROOT 文件
//     // outFile->cd();
//     TFile* outFile =new TFile(outputFileName.c_str(), type.c_str());
//     hist->Write();
//     // 关闭 ROOT 文件
//     outFile->Close();
//     delete hist;
// }


//  画二维 Histogram
void Draw2DHist(vector<float>& xbin, vector<float>& ybin, float ymin, float ymax, string x_title, string y_title, string outputFileName, string histTitle, string type ){
    // TH2F* hist = new TH2F(histTitle.c_str(), histTitle.c_str(), 100, GetVectorMin(xbin), GetVectorMax(xbin), 100, GetVectorMin(ybin), GetVectorMax(ybin));
    // TH2F* hist = new TH2F(histTitle.c_str(), histTitle.c_str(), 100, GetVectorMin(xbin), GetVectorMax(xbin), 100, -1, 1);
    TH2F* hist = new TH2F(histTitle.c_str(), histTitle.c_str(), 100, GetVectorMin(xbin), GetVectorMax(xbin), 400, ymin, ymax);
    // TH2F* hist = new TH2F(histTitle.c_str(), histTitle.c_str(), 7, 0, 700, 100, ymin, ymax);
    // 获取x轴、y轴和z轴对象，并设置标题
    hist->GetXaxis()->SetTitle(x_title.c_str());
    hist->GetYaxis()->SetTitle(y_title.c_str());
    // hist->GetZaxis()->SetTitle("counter");
    // hist->SetLabelSize(0.04, "X");
    // hist->SetLabelSize(0.04, "Y");
    // hist->SetLabelSize(0.04, "Z");
    // hist->SetTitleSize(0.05, "X");
    // hist->SetTitleSize(0.05, "Y");
    // hist->SetTitleSize(0.05, "Z");
    // 禁用统计框
    hist->SetStats(kFALSE);

    for(int i = 0; i < xbin.size(); i++){
        hist->Fill(xbin[i], ybin[i]);
    }
    // 查找每个 xbin 下的 ybin的均值
    // int nBinsX = hist->GetNbinsX();
    // TGraph* graph = new TGraph(nBinsX/5);
    // for (int i = 0; i <= nBinsX/5; i++) {
    //     if(i==0){
    //         double content = hist->ProjectionY("", 1, 1)->GetMean();
    //         graph->SetPoint(0, hist->GetXaxis()->GetBinCenter(1), content);
    //     }else{
    //         double content = hist->ProjectionY("", i*5, i*5)->GetMean();
    //         graph->SetPoint(i-1, hist->GetXaxis()->GetBinCenter(i*5), content);
    //     }
        
    // }

    int nBinsX = hist->GetNbinsX();
    TGraph* graph = new TGraph(nBinsX);
    for (int i = 1; i <= nBinsX; i++) {
        double content = hist->ProjectionY("", i, i)->GetMean();
        graph->SetPoint(i-1, hist->GetXaxis()->GetBinCenter(i), content);
    }
    // 创建画布
    TCanvas* c1 = new TCanvas(histTitle.c_str(), histTitle.c_str(), 800, 600);
    c1->SetLeftMargin(0.2); // 设置画布向右偏移
    c1->SetRightMargin(0.2); // 设置画布向右偏移
    c1->SetBottomMargin(0.2); // 设置画布下边距为0.2
    c1->SetGrid(); // 显示网格

    // 创建一个TGraph对象来存储拟合数据点
    TGraph *graph2 = new TGraph();

    // 遍历每个x bin，找出对应的y bin的最大值，并将这些最大值作为数据点
    for (int i = 1; i <= hist->GetNbinsX(); i++) {
        int maxBinY = hist->ProjectionY("", i, i)->GetMaximumBin();
        double maxY = hist->GetYaxis()->GetBinCenter(maxBinY);
        graph2->SetPoint(i-1, hist->GetXaxis()->GetBinCenter(i), maxY);
    }

    // 创建一个TF1对象并进行一次函数拟合
    TF1 *linearFit = new TF1("linearFit", "pol1", GetVectorMin(xbin), GetVectorMax(xbin));
    graph2->Fit(linearFit, "R");

    // 创建一个TF1对象并进行二次函数拟合
    TF1 *quadraticFit = new TF1("quadraticFit", "pol2", GetVectorMin(xbin), GetVectorMax(xbin));
    graph2->Fit(quadraticFit, "R");
    quadraticFit->SetLineStyle(2);

    hist->Draw("COLZ"); //显示直方图
    graph->SetLineColor(kRed); // 设置曲线颜色为红色
    graph->SetLineStyle(2); // 设置曲线为虚线
    graph->SetLineWidth(4); // 设置线条宽度为2
    // graph->Draw("LP"); // 绘制曲线
    // graph2->Draw("AP"); // 绘制曲线
    // linearFit->Draw("same");
    // quadraticFit->Draw("same");
    // // 在图中写入拟合结果的函数形式
    // TPaveText *fitInfo = new TPaveText(0.5, 0.7, 0.9, 0.9, "NDC");
    // fitInfo->SetFillColor(0);
    // fitInfo->SetBorderSize(0);
    // fitInfo->Draw("same");

    // 创建一个图例
    TLegend *legend = new TLegend(0.2, 0.8, 0.9, 0.9);
    legend->AddEntry(linearFit, Form("y = %.2fx + %.2f, chi2/ndf %.f/%d", linearFit->GetParameter(1), linearFit->GetParameter(0), linearFit->GetChisquare(), linearFit->GetNDF()), "l");
    legend->AddEntry(quadraticFit, Form("y = %.5fx^2 + %.2fx + %.2f, chi2/ndf %.f/%d", quadraticFit->GetParameter(2), quadraticFit->GetParameter(1), quadraticFit->GetParameter(0), quadraticFit->GetChisquare(), quadraticFit->GetNDF()), "l");
    // 设置图例的文本大小
    // legend->SetTextSize(0.03); // 设置字体大小为0.04
    // legend->Draw("same");

    c1->Draw();
    

    // // 将直方图写入 ROOT 文件
    TFile* outFile =new TFile(outputFileName.c_str(), type.c_str());
    // hist->Write();
    c1->Write();
    // 关闭 ROOT 文件
    outFile->Close();
    delete hist;
}

// 求vector的平均值
float calculateMean(const std::vector<float>& data) {
    float sum = std::accumulate(data.begin(), data.end(), 0.0);
    return sum / data.size();
}

// 求vector的标准差
float calculateStandardDeviation(const std::vector<float>& data) {
    float mean = calculateMean(data);
    float sum = 0.0;
    for (float value : data) {
        sum += pow(value - mean, 2);
    }
    float variance = sum / data.size();
    return sqrt(variance);
}


// 遍历root文件中所有TCanvas文件，提取指定对象中，指定统计信息
enum Statistics{
        mean,   // 0
        rms,    // 1
        fit,    // 2
        other
    };
// vector<float> GetCanvasStatisticsInfo(TFile *file, string str, Statistics stat, int ParIndex=0){ // 当stat=fit时，表示需要获取拟合参数，此时par才有意义
//     vector<float> vec;
//     vec.clear();
//     // 获取root文件中的所有键值
//     TList* list = file->GetListOfKeys();
//     TIter next(list);
//     TKey* key;
//     int count =0;
//     while ((key = (TKey*)next())) { //遍历所有键
//         TObject* obj = key->ReadObj();
//         if (obj->InheritsFrom("TCanvas")) {
//             TCanvas* canvas = (TCanvas*)obj;
//             string canvasName = canvas->GetName();
//             // std::cout << "画布名字： " << canvasName << std::endl;
//             // 使用find函数来查找子字符串
//             size_t found = canvasName.find(str);
//             if (found != std::string::npos) {
//                 // std::cout << "画布名字： " << canvasName << std::endl;

//                 // 获取TCanvas中的所有图形对象
//                 TList *listOfPrimitives = canvas->GetListOfPrimitives();
//                 // 遍历列表来获取TH1F的名字
//                 TIter next(listOfPrimitives);
//                 TObject *obj;
//                 while ((obj = next())) {
//                     if (obj->InheritsFrom(TH1F::Class())) {
//                         TH1F *histogram = (TH1F*)obj;
//                         const char* histTitle = histogram->GetTitle();
//                         // printf("TH1F的名字是：%s\n", histTitle);
//                         if(stat == 0){
//                             vec.push_back(histogram->GetMean());
//                             // std::cout << "mean: "<< histogram->GetMean() <<std::endl;
//                         }else if(stat == 1){
//                             vec.push_back(histogram->GetRMS());
//                             // std::cout << "rms: "<<histogram->GetRMS()<<std::endl;
//                         }else if(stat == 2){
//                             TList *functions = histogram->GetListOfFunctions();
//                             int entries = functions->GetEntries();
//                             TObject *obj2;
//                             while ((obj2 = next())) {
//                                 if (obj2->InheritsFrom("TF1")) {
//                                     TF1 *fitFunc = (TF1*)obj2;
//                                     // std::cout << "Function name: " << fitFunc->GetName() << std::endl;
//                                     for (int i = 0; i < fitFunc->GetNpar(); i++) {
//                                         std::cout << "Parameter " << i << ": " << fitFunc->GetParameter(i) << std::endl;
//                                     }
//                                     vec.push_back(fitFunc->GetParameter(ParIndex));
//                                 }
//                             }    
//                         }else {
//                             std::cout << "参数输入错误" << std::endl;
//                         }
                        
//                     }
//                 }

//             } else {
//                 // std::cout << "输入不合法" << std::endl;
//             }
//         }
//     }
//     return vec;
// }

float GetCanvasStatisticsInfo(TFile *file, string str, Statistics stat, int ParIndex=0){ // 当stat=fit时，表示需要获取拟合参数，此时par才有意义
    // vector<float> vec;
    // vec.clear();
    float result;
    // 获取root文件中的所有键值
    TList* list = file->GetListOfKeys();
    TIter next(list);
    TKey* key;
    int count =0;
    while ((key = (TKey*)next())) { //遍历所有键
        TObject* obj = key->ReadObj();
        if (obj->InheritsFrom("TCanvas")) {
            TCanvas* canvas = (TCanvas*)obj;
            string canvasName = canvas->GetName();
            // std::cout << "画布名字： " << canvasName << std::endl;
            // 使用find函数来查找子字符串
            size_t found = canvasName.find(str);
            if (found != std::string::npos) {
                // std::cout << "画布名字： " << canvasName << std::endl;

                // 获取TCanvas中的所有图形对象
                TList *listOfPrimitives = canvas->GetListOfPrimitives();
                // 遍历列表来获取TH1F的名字
                TIter next(listOfPrimitives);
                TObject *obj;
                while ((obj = next())) {
                    if (obj->InheritsFrom(TH1F::Class())) {
                        TH1F *histogram = (TH1F*)obj;
                        const char* histTitle = histogram->GetTitle();
                        // printf("TH1F的名字是：%s\n", histTitle);
                        if(stat == 0){
                            // vec.push_back(histogram->GetMean());
                            result = histogram->GetMean();
                            // std::cout << "mean: "<< histogram->GetMean() <<std::endl;
                        }else if(stat == 1){
                            // vec.push_back(histogram->GetRMS());
                            result = histogram->GetRMS();
                            // std::cout << "rms: "<<histogram->GetRMS()<<std::endl;
                        }else if(stat == 2){
                            TList *functions = histogram->GetListOfFunctions();
                            int entries = functions->GetEntries();
                            // std::cout << "flag 1, " << entries << std::endl;
                            TIter next(functions);
                            TObject *obj2;
                            while ((obj2 = next())) {
                                if (obj2->InheritsFrom("TF1")) {
                                    TF1 *fitFunc = (TF1*)obj2;
                                    // std::cout << "Function name: " << fitFunc->GetName() << std::endl;
                                    for (int i = 0; i < fitFunc->GetNpar(); i++) {
                                        // std::cout << "Parameter " << i << ": " << fitFunc->GetParameter(i) << std::endl;
                                    }
                                    // vec.push_back(fitFunc->GetParameter(ParIndex));
                                    result = fitFunc->GetParameter(ParIndex);
                                }
                            }    
                        }else {
                            std::cout << "参数输入错误" << std::endl;
                        }
                        
                    }
                }

            } else {
                // std::cout << "输入不合法" << std::endl;
            }
        }
    }
    // return vec;
    return result;
}





#endif
