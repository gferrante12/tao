//// before running this script, setup taosw environment
//  cd $OFFLINE_TAO_OFF
//  source setup.sh
//  ******************
//
//  Usage: for e- template. Use RADIUS as a sphere and take 25 points on the sphere to generate samples.
//  ( RADIUS = {0, 9, 18, 27, 36, 45, 54, 63, 72, 81, 90, 99, 108, 117, 126, 135, 144, 153, 162, 171, 180, 189, 198, 207, 216, 225, 234, 243, 252, 261, 270, 279, 288, 297, 306, 315, 324, 333, 342, 351, 360, 378, 387, 396, 405, 414, 423, 432, 441, 450, 459, 468, 477, 486, 495, 504, 522, 531, 540, 549, 558, 567, 576, 585, 594, 603, 612, 621, 639, 648, 657, 666, 675, 693, 702, 711, 720, 729, 738, 747, 756, 765, 774, 783, 801, 810, 819, 828, 837, 846, 855, 864, 882, 891 } )
//
//  Terminal Command:
//  root 'create_charge_template_Ek.cpp(RADIUS)'

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
#include "TVector3.h"

#include <fstream>
#include <iostream>
#include "math.h"
#include <map>
#include <numeric>
#include <chrono>
#include <unistd.h>
#include <sys/resource.h>
#include <cmath>
#include <map>

#include "RecAnalyze/RecAnalyze.h"

using namespace std;
using namespace std::chrono;

float channel_area = 72*16;         //mm^2
float channel_noise = 20;                       //Hz/mm^2
float channel_readout_window = 1000 * 1.e-9;    //s
float dark_noise = channel_area * channel_noise * channel_readout_window;
// float dark_noise = 0.;

struct channelPosition {
    float x;
    float y;
    float z;
};

std::vector<std::string> split(const std::string &s, char delimiter) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream(s);
    while (std::getline(tokenStream, token, delimiter)) {
        tokens.push_back(token);
    }
    return tokens;
}

void GetDetSimEvt(TTree *t1, Tao::SimEvt *SimEvt, int& EventIndex, float (&m_edep_pos)[5]){
    //Get Event
    t1->GetEntry(EventIndex);    //get Event[i]
    Tao::SimTrack* mPrimaryTracks = SimEvt->getTracksVec()[0];
    // float m_edep_r = sqrt( pow(mPrimaryTracks->getQEdepX(), 2) + pow(mPrimaryTracks->getQEdepY(), 2) + pow(mPrimaryTracks->getQEdepZ(), 2) );
    float m_edep_r = sqrt( pow(SimEvt->getEdepX(), 2) + pow(SimEvt->getEdepY(), 2) + pow(SimEvt->getEdepZ(), 2) );
    
    m_edep_pos[0]=SimEvt->getEdepX();
    m_edep_pos[1]=SimEvt->getEdepY();
    m_edep_pos[2]=SimEvt->getEdepZ();
    m_edep_pos[3]=m_edep_r;
    m_edep_pos[4]=mPrimaryTracks->getQEdep();
}

void GetCalibEvt(TTree *t1, Tao::CdCalibEvt* m_event, int& EventIndex, float (&arr)[8048] ){
    vector<Tao::CdCalibChannel> CalfChannels_vec;    //创建vector对象，用于存放当前Event的所有通道的hit 信息
    Tao::CdCalibChannel* CalfChannel;                //根据SimSipmHit.h, 创建类SimSipmHit，用于存放当前通道

    // Get Event
    t1->GetEntry(EventIndex);   

    CalfChannels_vec.clear();

    CalfChannels_vec = m_event->GetCalibChannels();

    for (unsigned int k =0; k < CalfChannels_vec.size(); k++){  //遍历通道
        CalfChannel = &CalfChannels_vec[k];
        for (unsigned int k2 =0; k2 < CalfChannel->CalibgetPEs().size(); k2++){  //遍历该通道的hit, 每次hit的PE数
            arr[ CalfChannel->CalibgetChannelID() ] += CalfChannel->CalibgetPEs()[k2];
        }
    }
}

float GetAngle( vector<channelPosition> channelPosition_vec, TVector3 vertex,int channelId){ //获取channel与vertex 之间的夹角
    double m_channel_x = channelPosition_vec[channelId].x - (-2446.);
    double m_channel_y = channelPosition_vec[channelId].y - (-2446.);
    double m_channel_z = channelPosition_vec[channelId].z - (-8212.8);
    float angle = vertex.Angle(TVector3(m_channel_x, m_channel_y, m_channel_z)) / M_PI * 180.0; // unit: deg

    return angle;
}

void CreateProcess(vector<string> ElecRootFiles, vector<string> CalibRootFiles, int radius, vector<channelPosition> channelPosition_vec, bool useXaxis){ 
    auto start_time = high_resolution_clock::now();

    // 创建直方图对象
    string hist_title ="r_"+to_string(radius);
    TH1F* hist = new TH1F(hist_title.c_str(), hist_title.c_str(), 360, 0, 180);
    int num_counted[360] = {0};
    int bin_index = 0;
    // 获取 x 轴和 y 轴对象
    TAxis *xaxis = hist->GetXaxis();
    TAxis *yaxis = hist->GetYaxis();
    // 设置坐标轴标题
    xaxis->SetTitle("#theta_{vertex_channel} [deg]");
    yaxis->SetTitle("Charge [p.e.]");

    int FILESNUM = CalibRootFiles.size();
    for (int filesNum = 0; filesNum < FILESNUM; filesNum++){
        std::cout << "("<< to_string(filesNum+1) <<"/"<< to_string(FILESNUM)  <<")" << std::endl;
        string ElecRootFile = ElecRootFiles[filesNum];
        string CalibRootFile = CalibRootFiles[filesNum];

        // 获取elecSim 中关联的detSim 文件
        TFile *ElecFile = GetRootFile(ElecRootFile.c_str());    //  获取elecSim的root文件
        if(ElecFile && ElecFile->IsOpen()){
            
        } else {
            std::cout << CalibRootFile << " does not exist." << std::endl;
            continue;
        }
        TTree *Elec_tree;  // Get Tree
        Elec_tree= (TTree*)ElecFile->Get("Event/Sim/SimEvt");
        Tao::SimEvt* SimEvt = NULL;
        Elec_tree->SetBranchAddress("SimEvt", &SimEvt);          //  Get TBranch


        // 获取calibAlg
        TFile *CalibFile = GetRootFile(CalibRootFile.c_str());
        if(CalibFile && CalibFile->IsOpen()){
            
        } else {
            std::cout << CalibRootFile << " does not exist." << std::endl;
            continue;
        }
        TTree* Calib_tree = (TTree*)CalibFile->Get("Event/Calib/CdCalibEvt");
        // 获取Calib 的Branch
        Tao::CdCalibEvt* Calib_event = new Tao::CdCalibEvt();   // create an event object, the Tao::CdCalibEvt is a Custom Class
        Calib_tree->SetBranchAddress("CdCalibEvt", &Calib_event);   // link variable "m_event" to branch "CdCalibmEvt"

        // 检查两个root文件的Event数是否匹配
        if ( Elec_tree->GetEntries() != Calib_tree->GetEntries() ){
            std::cout<<"Warning : " << Elec_tree->GetEntries() << " events in detsim, "<<Calib_tree->GetEntries()<<" events in elecsim"<<std::endl;
            return 0;
        }

        //  遍历Event
        TVector3 vertex = TVector3(0,0,1);
        float angle = 0.;
        int counter = 0;
        float Edep_Pos[5]={0.};
        float Calib_Hit[8048]={0.};
        std::cout << "Total Event: "<< Elec_tree->GetEntries() <<std::endl;

        TVector3 r_initial = TVector3(0,0,0);       
        if(radius != 0){       
            std::ifstream inputFile( ("/afs/ihep.ac.cn/users/x/xiexc82/workspace/run/Ek_template/"+to_string(radius)+"/coordinates.txt").c_str() ); //this file records sample's initial coordinate.
            int targetLine = FILESNUM-filesNum;  // according to the coordinates.txt, Line Number is opposite to Index Number.
            if (inputFile.is_open()) {
                std::string line;
                int currentLine = 1;
                while (std::getline(inputFile, line)) {
                    if (currentLine == targetLine) {
                        char delimiter = '\t';
                        std::vector<std::string> elements = split(line, delimiter);
                        r_initial = TVector3( stoi(elements[1]), stoi(elements[2]), stoi(elements[3]));
                        break;  // exit loop
                    }
                    currentLine++;
                }
                inputFile.close();
            } else {
                std::cout << "Unable to open the file" << std::endl;
            }

        } else{
            r_initial = TVector3(0,0,radius);
        }

        for(int eventIndex = 0; eventIndex < Elec_tree->GetEntries(); eventIndex++){
            float Calib_Hit[8048]={0.};
            GetDetSimEvt(Elec_tree, SimEvt, eventIndex, Edep_Pos);

            TVector3 r_edep = TVector3(
                                        Edep_Pos[0],
                                        Edep_Pos[1],
                                        Edep_Pos[2]
                                        );
            
            Double_t distance = (r_edep - r_initial).Mag();    //矢量差
            // std::cout << "edepR=("<< r_edep.X() << ", " << r_edep.Y() << ", " << r_edep.Z() <<")\tinitialR=(" << r_initial.X() << ", " << r_initial.Y() << ", " << r_initial.Z() << ")\t" << "distance : " << distance << std::endl;
            if ( distance > 10 ) continue; // discard large bias event
            
            if ( 0.94 > Edep_Pos[4] || Edep_Pos[4] > 0.971 ) {continue;} // 沉积能量与预期沉积能量偏差太大，就舍弃掉, e-
            counter++;

            GetCalibEvt(Calib_tree, Calib_event, eventIndex, Calib_Hit);
            
            for(int channelId=0; channelId <8048; channelId++){ //遍历通道
                angle = GetAngle(channelPosition_vec, r_edep, channelId);  //顶点与channel的夹角
                
                bin_index = hist->Fill(angle, (Calib_Hit[channelId] - dark_noise) );  //
                // std::cout << "angle = " << angle << ", PE = " << Calib_Hit[channelId] - dark_noise << std::endl;
                num_counted[bin_index - 1] +=1;
            }

        }
        std::cout << "(| edep_r - radius | <= 10 ) && ( 0.94<= Qedep <= 0.971 ) Events: " << counter << std::endl;

        ElecFile->Close();
        CalibFile->Close();  // close root file

    }

    float binContent = 0.;
    for(int i = 0; i < 360; i++){
        if(num_counted[i] < 1) continue;
        binContent = hist->GetBinContent(i+1);
        hist->SetBinContent(i +1, binContent / num_counted[i]);
        hist->SetBinError(i+1 , sqrt(binContent / num_counted[i])/num_counted[i]);
    }

    // 创建 ROOT 文件

    // TFile *outputFile = new TFile("0615_Ge68_charge_template.root", "UPDATE");
    TFile *outputFile = new TFile("0616_e-_charge_template.root", "UPDATE");

    // 将直方图写入 ROOT 文件
    hist->Write();

    // 关闭 ROOT 文件
    outputFile->Close();

    // running  time
    auto end_time = high_resolution_clock::now();
    auto duration = duration_cast<seconds>(end_time - start_time);
    std::cout<< "Running Time: "<< float(duration.count()/60.) << " mins." <<std::endl;

}

/////////////////
void create_charge_template_Ek(int RADIUS){
    std::cout << "r = " << to_string(RADIUS) << std::endl;
    vector<string> ElecRootFile;
    vector<string> CalibRootFile;
    ElecRootFile.clear();
    CalibRootFile.clear();

    // 获取几何文件 channel的坐标
    int index = 0;
    float x = 0.;
    float y = 0.;
    float z = 0.;
    int Layer = 0;
    int Azimuth = 0;
    vector<channelPosition> channelPosition_vec;
    ifstream channelFile("channel_position.txt");
    while(channelFile >> index >> x >> y >> z >> Layer >> Azimuth){
        channelPosition channel_Pos;
        channel_Pos.x = x;
        channel_Pos.y = y;
        channel_Pos.z = z;
        channelPosition_vec.push_back(channel_Pos);
    }

    bool useXaxis = false;
    for (int index = 1; index<=25; index++){   //e-
        if(index<=40 && useXaxis && RADIUS != 0){
            // 使用x轴代替ACU
            ElecRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e+/diffPos_diffEk/"+to_string(RADIUS)+"/e+_1000_0Mev_R"+to_string(RADIUS)+"_elecSim_x_"+to_string(index)+".root");
            CalibRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e+/diffPos_diffEk/"+to_string(RADIUS)+"/e+_1000_0Mev_R"+to_string(RADIUS)+"_CalibAlg_x_"+to_string(index)+".root"); 
        } else{
            ElecRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e-/Ek_template/e-_1000_1Mev_R"+to_string(RADIUS)+"_elecSim_"+to_string(index)+".root");
            CalibRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e-/Ek_template/e-_1000_1Mev_R"+to_string(RADIUS)+"_CalibAlg_"+to_string(index)+".root"); 
        }
    }
    CreateProcess(ElecRootFile, CalibRootFile, RADIUS, channelPosition_vec, useXaxis);
    
}