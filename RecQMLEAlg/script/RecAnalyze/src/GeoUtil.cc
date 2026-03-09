//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "Geometry/GeoUtil.h"
#include "TMath.h"
#include "TVector3.h"

int GeoUtil::projectAitoff2xy(double l, double b, double &Al, double &Ab)
{

    double x, y;

    double alpha2 = (l/2)*TMath::DegToRad();
    double delta  = b*TMath::DegToRad();
    double r2     = TMath::Sqrt(2.);
    double f      = 2*r2/TMath::Pi();
    double cdec   = TMath::Cos(delta);
    double denom  = TMath::Sqrt(1. + cdec*TMath::Cos(alpha2));
    x      = cdec*TMath::Sin(alpha2)*2.*r2/denom;
    y      = TMath::Sin(delta)*r2/denom;
    x     *= TMath::RadToDeg()/f;
    y     *= TMath::RadToDeg()/f;
    //x *= -1.; // for a skymap swap left<->right      

    Al = x;
    Ab = y;

    return 0;
}

TVector3 GeoUtil::getSphereIntersection(TVector3 vtx, TVector3 dir, double r)
{
    const double k_r_ball = r;
    const double k_v = 1.0;

    TVector3 intersection(0,0,0);
    TVector3 step_pos = vtx;
    TVector3 pre_step_pos = step_pos;

    double mag = 0;
    double pre_mag = 0;
    double v_ratio = 1.0;
    for (int i_step = 0; i_step < 2.05*(k_r_ball/k_v); i_step++) {
        step_pos = pre_step_pos + dir*k_v*v_ratio;
        mag = step_pos.Mag();
        if (mag - k_r_ball >= 0 && pre_mag - k_r_ball <= 0)
        {
            intersection = step_pos;
            //cout << "i_step " << i_step << endl;
            break;
        }
        pre_mag = mag;
        pre_step_pos = step_pos;

        //step_pos.Print();
        if ((k_r_ball - mag) > 30*k_v) v_ratio = 10.0; // when intersection is far, use 5x speed to accelerate, save time
        else v_ratio = 1.0;
    }
 
    //cout << dir.Theta() << "  " << dir.Phi() << " mag " << mag << "  ";
    //intersection.Print();

    return intersection;
}
