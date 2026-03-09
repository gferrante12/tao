#ifndef QMLERec_h
#define QMLERec_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition

#include "TTree.h"
#include "SniperKernel/AlgBase.h"
#include "SniperKernel/AlgFactory.h"
#include "RecQMLEAlg/ChargeTemplate.h"
#include "TAOGeometry/SimGeomSvc.h"
#include <TObject.h>
#include "Math/Minimizer.h"
#include "Math/Functor.h"
#include "Math/Factory.h"
#include "Minuit2/FCNBase.h"
#include <vector>
#include <string>
#include "TH2F.h"
#include "TF1.h"
#include "Event/SimEvt.h"
#include "Event/SimTrack.h"

#define NSCAN 360
#define SIPMNUM 4024
#define CHANNELNUM SIPMNUM*2

/*
 * QMLERec
 */

class QMLERec : public AlgBase
{
    public:
        QMLERec(const std::string & name);
        ~QMLERec();      

        double LogPoisson(double obj,double exp);
        // void CorrectVertex(float& hits, float& r, float& theta, float& phi, float& ge68_alpha);

        bool initialize();
        bool execute();
        bool finalize();

        // update some state
        bool update();
        
        // Charge Center Reconstruction
        bool CalChargeCenter();

        // Use Minimizer for vertex reconstruction
        bool VertexMinimize();
        class VertexRecLikelihoodFCN: public ROOT::Minuit2::FCNBase {
            public:
                VertexRecLikelihoodFCN(QMLERec* rec_alg) { m_alg = rec_alg; }
                double operator() (const std::vector<double>& x) const{
                    return m_alg->QMLE(x[0],x[1],x[2],x[3]);
                }
                double operator() (const double *x) const{
                    std::vector<double> p(x,x+4);
                    return (*this)(p);
                }
                double Up() const { return 0.5; }
            private:
                QMLERec* m_alg;
        };

        // charge expectation
        float CalExpChargeHit(float radius, float theta, float Evis);

        float QMLE(double Evis,double vr,double vtheta,double vphi);

    private:
        int m_iEvt;
        // input
        ChargeTemplate* charge_template;
        ChargeTemplate* charge_template_ge68;
        float CD_radius;
        TFile *nonuniformityFile = NULL;
        TH2F * nonuniformity = NULL;

        std::string nonuniformity_file;
        bool useTrueVertex;
        std::string trueVertexFile;
        TFile *vertexFile = NULL;
        TTree *vertexTree = NULL;
        Tao::SimEvt* SimEvt = NULL;
        Tao::SimTrack* mPrimaryTracks = NULL;
        
        //minimizer
        ROOT::Math::Minimizer* vtxllminimizer;
        ROOT::Math::Minimizer* vtxllminimizer_migrad;
        VertexRecLikelihoodFCN* vtxllfcn; 
        
        // result
        TTree* evt;
        int evtID=0;
        float fChannelTotHit = 0.;
        float fChannelHit[8048] = {0.};
        ////
        float fChannelExpPE[8048] = {0.};
        std::vector<Int_t> fChannelID;
        std::vector<float> fChannelHitTime;
        std::vector<float> fChannelExpPEVec;
        std::vector<float> fChannelHitPEVec;
        /////
        float fExpPE;   // total expect number of PE
        float fRecEvis;
        float fRecNHit;
        float fRecX;
        float fRecY;
        float fRecZ;
        float fRecR;
        float fRecTheta;    //(0, pi) unit: rad
        float fRecPhi;      //(-pi, pi) unit: rad
        float fCCRecEvis;
        float fCCRecX;
        float fCCRecY;
        float fCCRecZ;
        float fCCRecR;
        float fCCRecR2;
        float fCCRecTheta;
        float fCCRecPhi;

        float fChi2;
        float fEdm;

        // params to control the alg
        std::string charge_template_file;
        float cc_factor;
        float QSPE_factor; 
        

        // center detector geometry
        CdGeom*  m_cdGeom;
        unsigned int SiPMNum = SIPMNUM;   
        int ChannelNum = CHANNELNUM;
        SiPMGeom* m_SiPMGeom;
        //param of channel
        float channel_area = 72*16;                     //mm^2
        float channel_noise = 20;                       //Hz/mm^2
        float channel_readout_window = 1000 * 1.e-9;    //s
        float dark_noise_prob = channel_area * channel_noise * channel_readout_window;
        // float dark_noise_prob = 0.;
        double m_average_PE = 0.;
        float m_expected_hit = 0.;
        

        float saturation = 1.e5;
        double SiPMRadius = 939.515;    //mm
        float channel_theta[CHANNELNUM] = {0};
        float channel_phi[CHANNELNUM] = {0};
        TVector3 channel_vec[CHANNELNUM];
        float channel_n_theta[CHANNELNUM] = {0};
        float channel_n_phi[CHANNELNUM] = {0};
        TVector3 channel_n_vec[CHANNELNUM];

        //////
        float ESF =1.;  // energy scale factor
        float PDE =1.;  // 

        // float ES = 3458/1.022; // energy scale, npe of Ge68 is 3458
        float Y0 = 4200; // photoelectron yield, unit:p.e./MeV 

        //QMLE
        float QThreshold = 0.25; // unit : 0.25 p.e.
        float Q1 = 0.9716;    //  mean of SPES, unit: p.e.
        float S1 = 0.1562;    //  sigma of SPES, unit: p.e.
        double probPrcs = 1.e-10;
        float m_Likelihood = 0.;
        // float energy_Ge = 0.;
        // float energy_Ek = 0.;

};

#endif
