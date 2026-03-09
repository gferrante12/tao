#include <iostream>
#include <fstream>
#include <cmath>
#include <vector>
#include <string>
#include "TApplication.h"
#include "TCanvas.h"
#include "TGraph.h"
#include "TAxis.h"
#include "TStyle.h"
#include "TH2F.h"
#include "TLegend.h"
#include "TBox.h"
#include "TColor.h"

// 计算模 R 和极角 theta
void calculateRTheta(double x, double y, double z, double& R, double& theta) {
    R = std::sqrt(x * x + y * y + z * z);
    theta = std::atan2(std::sqrt(x * x + y * y), z) * 180 / M_PI;
}

int plotInitialP() {
    // 输入文件路径
    const char* file_ACU = "/junofs/users/shihangyu/workspace/reconstruction/CreateCoordinnate/ACU_Ge43p.txt";
    const char* file_CLS = "/junofs/users/shihangyu/workspace/reconstruction/CreateCoordinnate/CLSPosition_20251223_45deg.txt";

    // 存储 ACU 和 CLS 的 R 和 theta
    std::vector<double> R_values_ACU, theta_values_ACU;
    std::vector<double> R_values_CLS, theta_values_CLS;

    // 读取 ACU 数据
    {
        std::ifstream file(file_ACU);
        if (!file.is_open()) {
            std::cerr << "Error: Could not open file " << file_ACU << std::endl;
            return 1;
        }
        std::string line;
        while (std::getline(file, line)) {
            if (line.empty()) continue;
            char name[100];
            int id;
            double x, y, z;
            std::sscanf(line.c_str(), "%s %d %lf %lf %lf", name, &id, &x, &y, &z);
            double R, theta;
            calculateRTheta(x, y, z, R, theta);
            if (R == 0) continue;
            R_values_ACU.push_back(R);
            theta_values_ACU.push_back(theta);
        }
        file.close();
    }
    // 读取 CLS 数据
    {
        std::ifstream file(file_CLS);
        if (!file.is_open()) {
            std::cerr << "Error: Could not open file " << file_CLS << std::endl;
            return 1;
        }
        std::string line;
        while (std::getline(file, line)) {
            if (line.empty()) continue;
            char name[100];
            int id;
            double x, y, z;
            std::sscanf(line.c_str(), "%s %d %lf %lf %lf", name, &id, &x, &y, &z);
            double R, theta;
            calculateRTheta(x, y, z, R, theta);
            if (R == 0) continue;
            R_values_CLS.push_back(R);
            theta_values_CLS.push_back(theta);
        }
        file.close();
    }

    // 创建画布
    TCanvas* canvas = new TCanvas("canvas", "2D Plot", 800, 600);

    double leftMargin = 0.12;
    double rightMargin = 0.05;
    double topMargin = 0.05;
    double bottomMargin = 0.12;
    canvas->SetMargin(leftMargin, rightMargin, bottomMargin, topMargin);

    // TGraph
    TGraph* graph_ACU = new TGraph(R_values_ACU.size(), &R_values_ACU[0], &theta_values_ACU[0]);
    TGraph* graph_CLS = new TGraph(R_values_CLS.size(), &R_values_CLS[0], &theta_values_CLS[0]);

    int color_ACU = TColor::GetColor(191, 29, 45);
    int color_CLS = TColor::GetColor(80, 148, 213);

    graph_ACU->SetMarkerStyle(20);
    graph_ACU->SetMarkerColor(color_ACU);
    graph_ACU->SetLineColor(kWhite);

    graph_CLS->SetMarkerStyle(20);
    graph_CLS->SetMarkerColor(color_CLS);
    graph_CLS->SetLineColor(kWhite);

    graph_ACU->GetXaxis()->SetTitle("#it{R} [mm]");
    graph_ACU->GetYaxis()->SetTitle("#it{#theta} [#circ]");
    graph_ACU->SetTitle("");
    graph_ACU->GetXaxis()->CenterTitle();
    graph_ACU->GetYaxis()->CenterTitle();

    graph_ACU->GetXaxis()->SetRangeUser(-20, 900);
    graph_ACU->GetYaxis()->SetRangeUser(-10, 190);

    double labelSize = 0.036;
    double titleSize = 0.04;
    double titleOffset = 1.2;
    double LabelFont = 62;
    double TitleFont = 62;
    graph_ACU->GetXaxis()->SetTitleOffset(titleOffset);
    graph_ACU->GetYaxis()->SetTitleOffset(titleOffset);
    graph_ACU->GetXaxis()->SetLabelFont(LabelFont);
    graph_ACU->GetYaxis()->SetLabelFont(LabelFont);
    graph_ACU->GetXaxis()->SetTitleFont(TitleFont);
    graph_ACU->GetYaxis()->SetTitleFont(TitleFont);
    graph_ACU->GetXaxis()->SetLabelSize(labelSize);
    graph_ACU->GetYaxis()->SetLabelSize(labelSize);
    graph_ACU->GetYaxis()->SetTitleSize(titleSize);
    graph_ACU->GetXaxis()->SetTitleSize(titleSize);

    graph_ACU->Draw("AP");
    graph_CLS->Draw("P SAME");

    double Transparency = 0.3;

    int color_200 = TColor::GetColor(173, 216, 230); // 浅蓝
    int color_300 = TColor::GetColor(144, 238, 144); // 浅绿
    int color_400 = TColor::GetColor(255, 255, 153); // 浅黄
    int color_500 = TColor::GetColor(255, 218, 185); // 浅橙
    int color_650 = TColor::GetColor(221, 160, 221); // 浅紫

    // TBox* box_200 = new TBox(0, 0, 200, 180);
    // box_200->SetFillColorAlpha(color_200, Transparency);
    // box_200->Draw("same");
    // TBox* box_300 = new TBox(200, 0, 300, 180);
    // box_300->SetFillColorAlpha(color_300, Transparency);
    // box_300->Draw("same");
    // TBox* box_400 = new TBox(300, 0, 400, 180);
    // box_400->SetFillColorAlpha(color_400, Transparency);
    // box_400->Draw("same");
    // TBox* box_500 = new TBox(400, 0, 500, 180);
    // box_500->SetFillColorAlpha(color_500, Transparency);
    // box_500->Draw("same");
    // TBox* box_650 = new TBox(500, 0, 650, 180);
    // box_650->SetFillColorAlpha(color_650, Transparency);
    // box_650->Draw("same");

    TLegend* legend = new TLegend(0.15, 0.7, 0.32, 0.85);
    legend->AddEntry(graph_ACU, "ACU position", "p");
    legend->AddEntry(graph_CLS, "CLS position", "p");
    // legend->AddEntry(box_200, "0-200 mm", "f");
    // legend->AddEntry(box_300, "200-300 mm", "f");
    // legend->AddEntry(box_400, "300-400 mm", "f");
    // legend->AddEntry(box_500, "400-500 mm", "f");
    // legend->AddEntry(box_650, "500-650 mm", "f");
    legend->SetTextSize(0.028);
    legend->SetTextFont(60);
    //无边框无填充
legend->SetBorderSize(0);  // 去掉边框
legend->SetFillStyle(0);   // 使图例背景透明无填充

    //无边框无填充
    legend->Draw("same");

    canvas->Update();
    TFile *f = new TFile("R_vs_theta.root", "recreate");
    canvas->Write();
    canvas->SaveAs("R_vs_theta.pdf");

    return 0;
}

int main(int argc, char** argv) {
    TApplication app("app", &argc, argv);
    plotInitialP();
    app.Run();
    return 0;
}
