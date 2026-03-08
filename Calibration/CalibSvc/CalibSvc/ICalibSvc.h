#ifndef ICalibSvc_h
#define ICalibSvc_h

/* Author: Guofu Cao  2026.01.11
 * E-mail:caogf@ihep.ac.cn

 * Description:
 *   This is the interface for CalibSvc.
 *
 *   User should use this class to access CalibSvc

*/


class ICalibSvc {

    public:
        
        virtual ~ICalibSvc() = 0;


        virtual const float GetGain(int chid) = 0;
        virtual const float GetMean0(int chid) = 0;
        virtual const float GetTimeOffset(int chid) = 0;
        virtual const float GetDCR(int chid) = 0;
        virtual const float GetBaseline(int chid) = 0;
        virtual const bool UseDynamicBaseline() = 0;

        virtual bool SetGain(int chid, float gain) = 0;
        virtual bool SetMean0(int chid, float mean0) = 0;
        virtual bool SetTimeOffset(int chid, float timeoffset) = 0;
        virtual bool SetDCR(int chid, float dcr) = 0;
        virtual bool SetBaseline(int id, float baseline) = 0;
};

#endif
