#ifndef ChargeTemplateRec_h
#define ChargeTemplateRec_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition

#include "TTree.h"
#include "SniperKernel/AlgBase.h"
#include "SniperKernel/AlgFactory.h"
#include "RecChargeTemplateAlg/ChargeTemplate.h"
#include "TAOGeometry/SimGeomSvc.h"

#include "Math/Minimizer.h"
#include "Math/Functor.h"
#include "Math/Factory.h"
#include "Minuit2/FCNBase.h"
#include <vector>
#include <string>

#define NSCAN 360
#define SIPMNUM 4024
#define CHANNELNUM SIPMNUM*2

/*
 * ChargeTemplateRec
 */

class ChargeTemplateRec : public AlgBase
{
    public:
        ChargeTemplateRec(const std::string & name);
        ~ChargeTemplateRec();      

        double Chi2(double nhit,double x,double y,double z, double alpha_ge68);
        double LogPoisson(double obj,double exp);
        void CorrectVertex(float& hits, float& r, float& theta, float& phi, float& ge68_alpha);

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
                VertexRecLikelihoodFCN(ChargeTemplateRec* rec_alg) { m_alg = rec_alg; }
                double operator() (const std::vector<double>& x) const{
                    return m_alg->Chi2(x[0],x[1],x[2],x[3],x[4]);
                }
                double operator() (const double *x) const{
                    std::vector<double> p(x,x+5);
                    return (*this)(p);
                }
                double Up() const { return 0.5; }
            private:
                ChargeTemplateRec* m_alg;
        };

        // charge expectation
        float CalExpChargeHit(float radius,float theta, float alpha, float alpha_ge68);

    private:
        int m_iEvt;
        // input
        // TaoReadoutChannel* tao_readout_channel;
        ChargeTemplate* charge_template;
        ChargeTemplate* charge_template_ge68;
        float CD_radius;

        //minimizer
        ROOT::Math::Minimizer* vtxllminimizer;
        ROOT::Math::Minimizer* vtxllminimizer_migrad;
        VertexRecLikelihoodFCN* vtxllfcn; 
        
        // result
        TTree* evt;
        int evtID;
        int fChannelTotHit;
        // vector<float> fChannelHit;
        float fChannelHit[CHANNELNUM] = {0};
        float fRecNHit;
        float fRecX;
        float fRecY;
        float fRecZ;
        float fRecR;
        float fRecTheta;
        float fRecPhi;
        float fCCRecX;
        float fCCRecY;
        float fCCRecZ;
        float fCCRecR;
        float fCCRecTheta;
        float fCCRecPhi;
        float fRecGammaTempRatio;
        float gamma_tmp_ratio[2] = {0,1};
        float fChi2;
        float fEdm;

        // params to control the alg
        // char* charge_template_file;
        std::string charge_template_file;
        float cc_factor;
        float QSPE_factor; 

        //center detector geometry
        CdGeom*  m_cdGeom;
        unsigned int SiPMNum = SIPMNUM;   
        int ChannelNum = CHANNELNUM;
        SiPMGeom* m_SiPMGeom;
        //param of channel
        float channel_area = 50.71 * 50.71 / 2;         //mm^2
        float channel_noise = 20;                       //Hz/mm^2
        float channel_readout_window = 1000 * 1.e-9;    //s
        float dark_noise_prob = channel_area*channel_noise*channel_readout_window;
        float saturation = 1.e5;
        double SiPMRadius = 939.515;    //mm
        float channel_theta[CHANNELNUM] = {0};
        float channel_phi[CHANNELNUM] = {0};
        TVector3 channel_vec[CHANNELNUM];
        float channel_n_theta[CHANNELNUM] = {0};
        float channel_n_phi[CHANNELNUM] = {0};
        TVector3 channel_n_vec[CHANNELNUM];
};

#endif
