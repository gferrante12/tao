//
//  Author: Jiayang Xu  2023.3.20
//  E-mail:xujy@ihep.ac.cn
//

#ifndef CalibAnaTest_h
#define CalibAnaTest_h

#undef _POSIX_C_SOURCE // to remove warning message of redefinition
#undef _XOPEN_SOURCE // to remove warning message of redefinition
#include "SniperKernel/AlgBase.h"

#include <TTree.h>
#include <vector>
#include <TH1.h>
#include <TH2.h>

class CalibAnaTest: public AlgBase
{
    public:
        CalibAnaTest(const std::string& name);
        ~CalibAnaTest();

        bool initialize();
        bool execute();
        bool finalize();

    private:
        int nevt_processed;
	TTree* evt;
 	
	Int_t fChannelID;
	Int_t fevtID;
	std::vector<float> fPEs;
    std::vector<float> fTDCs;
	int np;
	float pfPEs[10000];
	float pfTDCs[10000];
	
 	
};

#endif
