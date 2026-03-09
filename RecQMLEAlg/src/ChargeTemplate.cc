#include "RecQMLEAlg/ChargeTemplate.h"
#include "TFile.h"
#include "math.h"
#include "TString.h"
#include "TVector3.h"
#include <iostream>
#include <fstream>
#include <string>
#include "RecQMLEAlg/Functions.h"

using namespace std;

ChargeTemplate::ChargeTemplate(string charge_tmp_file)
{
    tmp_num = TEMPLATENUM;
    cd_radius = 900;
    sipm_radius = 939.5;
    max_tmp_radius = 0;
    tmp_numbers = 0;
    charge_template_file = charge_tmp_file;
    initialize();
}

ChargeTemplate::~ChargeTemplate()
{
    
}

bool ChargeTemplate::initialize()
{
    string root_dir = getenv("RECQMLEALGROOT");
    ifstream info_file((root_dir + "/input/" + charge_template_file + ".txt").c_str());
    string file_name = "/input/" + charge_template_file +".root";
    tmp_file = new TFile((root_dir + file_name).c_str());

    double radius = 0;
    char tmp_name[30];
    while(info_file >> radius >> tmp_name)
    { 
        tmp_radius.push_back(radius);
        TH1F* hist = (TH1F*) tmp_file->Get(tmp_name);
        hist->GetBinContent(1);
        tmp.push_back(hist);
        // cout << "Template radius : "<< radius <<" name : "<< tmp_name <<endl;
        tmp_numbers ++;
        max_tmp_radius = radius;
    }
    // cout << "Max template radius : " << max_tmp_radius << "\nTemplate numbers : "<< tmp_numbers << endl;
    info_file.close();

    cout << "ChargeTemplate Initialization Finished !!!" << endl;
    return true;
}

bool ChargeTemplate::finalize()
{
    tmp_file->Close();
    return true;
}

TH1F* ChargeTemplate::get_template(int index)
{
    return tmp[index];
}

float ChargeTemplate::get_template_radius(int index)
{
    return tmp_radius[index];
}

float ChargeTemplate::cal_sipm_proj(float radius, float sipm_distance)
{
    float cos_theta_proj = (sipm_distance*sipm_distance + sipm_radius*sipm_radius - radius*radius)/(2*sipm_distance*sipm_radius);
    return cos_theta_proj;
}

float ChargeTemplate::cal_sipm_distance(float radius, float theta)
{
    float cos_theta = cos(theta*PI/180);
    float d = sqrt(sipm_radius*sipm_radius + radius*radius - 2*radius*sipm_radius*cos_theta);
    return d;
}

float ChargeTemplate::LinearInterpolation(float radius, float x0, float y0, float x1, float y1)
{
    float value = 0;
    if (fabs(x0 - x1) < 1.e-2)
    {
        value = (y0 + y1)/2.0;
    }else{
        value = y0 + (radius - x0)*(y1 - y0)/(x1 - x0);
    }
    return value;
}

int ChargeTemplate::FindBeforeIndex(float radius, int low, int high)
{
    if (low == high){
        if(radius < tmp_radius[low]){
            return max(low - 1, 0);
        }else{
            return low;
        }
    }else if(high < low){
        return max(low - 1, 0);
    }
    int mid = int((low + high)/2);
    if(radius >= tmp_radius[mid]){
        return FindBeforeIndex(radius, mid + 1, high);
    }else{
        return FindBeforeIndex(radius, low, mid - 1);
    }

}

float ChargeTemplate::CalExpChargeHit(float radius, float theta)    // theta --顶点与SiPM之间的夹角
{

    int bindex = FindBeforeIndex(radius,0,tmp_numbers-1);   // 获取小于等于0的template的索引值
    int findex = bindex + 1;
    if(radius >= max_tmp_radius)
    {
        findex = tmp_numbers - 1;
        bindex = findex - 1;
    }
    float cos_theta = cos(theta*PI/180);
    float sin_theta = sin(theta*PI/180);
    float sipm_distance = cal_sipm_distance(radius, theta); // 顶点到SiPM之间的距离
    float correct_factor = cal_sipm_proj(radius, sipm_distance)/pow(sipm_distance,2);   // 修正系数，因为顶点不是垂直入射SiPM，即顶点入射方向与SiPM法线之间存在夹角α。计算顶点投影在SiPM的立体角。当SiPM表面积足够小时，可以近似有立体角Ω=(Acosα)/（R*R）,A是SiPM表面积，R是SiPM到球心的距离，即探测器半径

    // before charge template information
    float b_tmp_radius = get_template_radius(bindex);
    float b_sipm_distance = cal_sipm_distance(b_tmp_radius, theta);
    float b_correct_factor = cal_sipm_proj(b_tmp_radius, b_sipm_distance)/pow(b_sipm_distance,2);
    TH1F* b_temp = get_template(bindex);
    float b_temp_hit = b_temp -> Interpolate(theta) * correct_factor / b_correct_factor;

    // after charge template information
    float f_tmp_radius = get_template_radius(findex);
    float f_sipm_distance = cal_sipm_distance(f_tmp_radius, theta);
    float f_correct_factor = cal_sipm_proj(f_tmp_radius, f_sipm_distance)/pow(f_sipm_distance,2);
    TH1F* f_temp = get_template(findex);
    float f_temp_hit = f_temp -> Interpolate(theta) * correct_factor / f_correct_factor;    
    
    // get linear interpolation
    float exp_hit = LinearInterpolation(radius, b_tmp_radius, b_temp_hit, f_tmp_radius, f_temp_hit);
    
    return exp_hit;
}
