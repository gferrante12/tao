//// before running this script, setup taosw environment
//  cd $OFFLINE_TAO_OFF
//  source setup.sh
//  ******************
//  Usage: for Ge68 template. Samples are generated based on ACU and CLS.
//  ( RADIUS = {0, 100, 200, 300, 350, 375, 400, 500, 550, 600, 650, 700, 750, 800, 850} )
//
//  Terminal Command:
//  root 'create_charge_template_Ge68.cpp(RADIUS)'

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
    t1->GetEntry(EventIndex);    //get Event[i]

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
        // 判断文件是否存在，不存在就跳过
        if(ElecFile && ElecFile->IsOpen()){
            
        } else {
            std::cout << CalibRootFile << " does not exist." << std::endl;
            continue;
        }

        TTree *Elec_tree;  // Get Tree
        Elec_tree= (TTree*)ElecFile->Get("Event/Sim/SimEvt");
        Tao::SimEvt* SimEvt = NULL;
        Elec_tree->SetBranchAddress("SimEvt", &SimEvt);          //  获取TBranch

        // 获取calibAlg
        TFile *CalibFile = GetRootFile(CalibRootFile.c_str());    //  获取elecSim的root文件
        // 判断文件是否存在，不存在就跳过
        if(CalibFile && CalibFile->IsOpen()){
            
        } else {
            std::cout << CalibRootFile << " does not exist." << std::endl;
            continue;
        }

        TTree* Calib_tree = (TTree*)CalibFile->Get("Event/Calib/CdCalibEvt");
        // Get CalibAlg's Branch
        Tao::CdCalibEvt* Calib_event = new Tao::CdCalibEvt();   // create an event object, the Tao::CdCalibEvt is a Custom Class
        Calib_tree->SetBranchAddress("CdCalibEvt", &Calib_event);   // link variable "m_event" to branch "CdCalibmEvt"

        // 检查两个root文件的Event数是否匹配
        if ( Elec_tree->GetEntries() != Calib_tree->GetEntries() ){
            std::cout<<"Warning : " << Elec_tree->GetEntries() << " events in detsim, "<<Calib_tree->GetEntries()<<" events in elecsim"<<std::endl;
            return 0;
        }

        TVector3 vertex = TVector3(0,0,1);
        float angle = 0.;
        int counter = 0;
        float Edep_Pos[5]={0.};
        float Calib_Hit[8048]={0.};
        std::cout << "Total Event: "<< Elec_tree->GetEntries() <<std::endl;

        TVector3 r_initial = TVector3(0,0,0);       
        if(radius != 0){                          
            if(filesNum<20){
                if(useXaxis){
                r_initial = TVector3(radius,0,0);   // x_axis  
                std::cout << to_string(filesNum+1) << " (" << radius << ", 0, 0)" << std::endl;  // x_axis
                } else {
                    r_initial = TVector3(0,0,radius);
                    std::cout << to_string(filesNum+1) << " (0, 0, " << radius << ")" << std::endl;
                }
            } else if (filesNum>=20 && filesNum<40){
                if(useXaxis){
                    r_initial = TVector3(-radius,0,0);  // x_axis
                    std::cout << to_string(filesNum+1) << " (-" << radius << ", 0, 0)" << std::endl;  // x_axis
                } else {
                    r_initial = TVector3(0,0,-radius);  
                    std::cout << to_string(filesNum+1) << " (0, 0, -" << radius << ")" << std::endl;
                }
                
            }else {
                ifstream CLS_coordinatelFile("/afs/ihep.ac.cn/users/x/xiexc82/workspace/run/CLS/"+to_string(radius)+"/CLS_coordinate.txt");
                string line;
                int lineNum = int( (float(filesNum)-40.)/20. );
                int currentLine = 0;
                while (getline(CLS_coordinatelFile, line)) {
                    currentLine++;
                    if (currentLine == lineNum+1) {
                        // return line;
                        char delimiter = ' ';
                        std::vector<std::string> elements = split(line, delimiter);
                        std::cout << filesNum << " ("<< elements[1] << ", " << elements[2] << ", " << elements[3] << ")" << std::endl;

                        r_initial = TVector3( stoi(elements[1]), stoi(elements[2]), stoi(elements[3]));

                    }
                }
                
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
            
            Double_t distance = (r_edep - r_initial).Mag();
            // std::cout << "edepR=("<< r_edep.X() << ", " << r_edep.Y() << ", " << r_edep.Z() <<")\tinitialR=(" << r_initial.X() << ", " << r_initial.Y() << ", " << r_initial.Z() << ")\t" << "distance : " << distance << std::endl;
            if ( distance > 10 ) continue; // discard large bias event

            if ( 0.8733 > Edep_Pos[4] || Edep_Pos[4] > 0.9003 ) {continue;} //沉积能量与预期沉积能量偏差太大，就舍弃掉 e+ 1 sigma
            counter++;

            GetCalibEvt(Calib_tree, Calib_event, eventIndex, Calib_Hit);
            
            for(int channelId=0; channelId <8048; channelId++){ //遍历通道    
                angle = GetAngle(channelPosition_vec, r_edep, channelId);  //顶点与channel的夹角
                
                bin_index = hist->Fill(angle, (Calib_Hit[channelId] - dark_noise) );  //
                // std::cout << "angle = " << angle << ", PE = " << Calib_Hit[channelId] - dark_noise << std::endl;
                num_counted[bin_index - 1] +=1;
            }

        }

        std::cout << "(| edep_r - radius | <= 10 ) && ( 0.8325<= Qedep <= 0.9425) Events: " << counter << std::endl;

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

    // create ROOT File
    TFile *outputFile = new TFile("0616_Ge68_charge_template.root", "UPDATE");

    // save histogram 
    hist->Write();

    // close ROOT File
    outputFile->Close();

    // running  time
    auto end_time = high_resolution_clock::now();
    auto duration = duration_cast<seconds>(end_time - start_time);
    std::cout<< "Running Time: "<< float(duration.count()/60.) << " mins." <<std::endl;

}

void create_charge_template_Ge68(int RADIUS){
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

    
    std::map<std::string, int> Ge68template;
    Ge68template["0"] = 50;    // R=0, number of root files = 160
    Ge68template["100"] = 40;   // R=100, number of root files = 40
    Ge68template["200"] = 80;   // R=200, number of root files = 80
    Ge68template["300"] = 80;   // R=300, number of root files = 80
    Ge68template["350"] = 80;   // R=350, number of root files = 80
    Ge68template["375"] = 80;   // R=375, number of root files = 80
    Ge68template["400"] = 80;   // R=400, number of root files = 80
    Ge68template["500"] = 80;   // R=500, number of root files = 80
    Ge68template["550"] = 160;  // R=550, number of root files = 160
    Ge68template["600"] = 160;
    Ge68template["650"] = 160;
    Ge68template["700"] = 160;
    Ge68template["750"] = 160;
    Ge68template["800"] = 160;
    Ge68template["850"] = 160;

    bool useXaxis = false;
    for (int index = 1; index<=Ge68template[to_string(RADIUS)]; index++){   //1-20 samples are taken from the positive direction of ACU, 21-40 samples are taken from the negative direction of ACU, >40 samples are taken from CLS
        if(index<=40 && useXaxis && RADIUS != 0){
            // 使用x轴代替ACU
            ElecRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e+/diffPos_diffEk/"+to_string(RADIUS)+"/e+_1000_0Mev_R"+to_string(RADIUS)+"_elecSim_x_"+to_string(index)+".root");
            CalibRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e+/diffPos_diffEk/"+to_string(RADIUS)+"/e+_1000_0Mev_R"+to_string(RADIUS)+"_CalibAlg_x_"+to_string(index)+".root"); 
        } else{
            ElecRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e+/diffPos_diffEk/"+to_string(RADIUS)+"/e+_1000_0Mev_R"+to_string(RADIUS)+"_elecSim_"+to_string(index)+".root");
            CalibRootFile.push_back("root://junoeos01.ihep.ac.cn//eos/juno/groups/TAO/xiexc/e+/diffPos_diffEk/"+to_string(RADIUS)+"/e+_1000_0Mev_R"+to_string(RADIUS)+"_CalibAlg_"+to_string(index)+".root");  
        }
    }
    CreateProcess(ElecRootFile, CalibRootFile, RADIUS, channelPosition_vec, useXaxis);
    
}