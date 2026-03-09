/*================================================================
*   Filename   : sim_event.cpp
*   Author     : Yuyi Wang
*   Created on  Fri 8 Jan 2021 19:44:51 PM CST
*   Description:
*
================================================================*/

#include "convert.hpp"

#include "Event/SimEvt.h"
#include "Event/SimHeader.h"
#include <iostream>

using namespace std;

struct SimEvent_t
{
    int32_t EventID;
    int32_t SipmHits;
    int32_t RandomSeed;

    float Edep;
    float EdepX;
    float EdepY;
    float EdepZ;

    int32_t EventType;
    int32_t NTracks;

    SimEvent_t(Tao::SimEvt* sim_event)
    {
#define ASSIGN(name) this->name = sim_event->get##name()
        ASSIGN(EventID);
        ASSIGN(SipmHits);
        ASSIGN(RandomSeed);

        ASSIGN(Edep);
        ASSIGN(EdepX);
        ASSIGN(EdepY);
        ASSIGN(EdepZ);

        ASSIGN(EventType);
        ASSIGN(NTracks);
#undef ASSIGN
    }

    static const H5::DataType& get_h5_type()
    {
        static auto type = H5::CompType(sizeof(SimEvent_t));
#define INSERT(name) INSERT_(type, SimEvent_t, name)
        INSERT(EventID);
        INSERT(SipmHits);
        INSERT(RandomSeed);

        INSERT(Edep);
        INSERT(EdepX);
        INSERT(EdepY);
        INSERT(EdepZ);

        INSERT(EventType);
        INSERT(NTracks);
#undef INSERT
        return type;
    }
};

SPEC_H5TYPE_IMPL(SimEvent_t)

struct SimTrack_t
{
    int32_t EventID;
    int32_t PDGID;
    int32_t TrackID;
    float InitPx;
    float InitPy;
    float InitPz;
    float InitKE;
    float InitX;
    float InitY;
    float InitZ;
    double InitT;
    float ExitPx;
    float ExitPy;
    float ExitPz;
    float ExitKE;
    float ExitX;
    float ExitY;
    float ExitZ;
    double ExitT;
    float TrackLength;
    float Edep;
    float EdepX;
    float EdepY;
    float EdepZ;
    float QEdep;
    float QEdepX;
    float QEdepY;
    float QEdepZ;
    float EdepNotInLS;

    SimTrack_t(Tao::SimEvt* sim_event, Tao::SimTrack* sim_track)
    {
        this->EventID = sim_event->getEventID();
#define ASSIGN(name) this->name = sim_track->get##name()
        ASSIGN(PDGID);
        ASSIGN(TrackID);

        ASSIGN(InitPx);
        ASSIGN(InitPy);
        ASSIGN(InitPz);
        ASSIGN(InitKE);

        ASSIGN(InitX);
        ASSIGN(InitY);
        ASSIGN(InitZ);
        ASSIGN(InitT);

        ASSIGN(ExitPx);
        ASSIGN(ExitPy);
        ASSIGN(ExitPz);
        ASSIGN(ExitKE);

        ASSIGN(ExitX);
        ASSIGN(ExitY);
        ASSIGN(ExitZ);
        ASSIGN(ExitT);

        ASSIGN(TrackLength);

        ASSIGN(Edep);
        ASSIGN(EdepX);
        ASSIGN(EdepY);
        ASSIGN(EdepZ);

        ASSIGN(QEdep);
        ASSIGN(QEdepX);
        ASSIGN(QEdepY);
        ASSIGN(QEdepZ);

        ASSIGN(EdepNotInLS);
#undef ASSIGN
    }

    static const H5::DataType& get_h5_type()
    {
        static auto type = H5::CompType(sizeof(SimTrack_t));
#define INSERT(name) INSERT_(type, SimTrack_t, name);
        INSERT(EventID);
        INSERT(PDGID);
        INSERT(TrackID);

        INSERT(InitPx);
        INSERT(InitPy);
        INSERT(InitPz);
        INSERT(InitKE);

        INSERT(InitX);
        INSERT(InitY);
        INSERT(InitZ);
        INSERT(InitT);

        INSERT(ExitPx);
        INSERT(ExitPy);
        INSERT(ExitPz);
        INSERT(ExitKE);

        INSERT(ExitX);
        INSERT(ExitY);
        INSERT(ExitZ);
        INSERT(ExitT);

        INSERT(TrackLength);

        INSERT(Edep);
        INSERT(EdepX);
        INSERT(EdepY);
        INSERT(EdepZ);

        INSERT(QEdep);
        INSERT(QEdepX);
        INSERT(QEdepY);
        INSERT(QEdepZ);

        INSERT(EdepNotInLS);
#undef INSERT
        return type;
    }
};

SPEC_H5TYPE_IMPL(SimTrack_t)

struct SimSiPMHit_t
{
    int32_t EventID;
    int32_t SipmID;
    double HitTime;
    double TimeWindow;
    int32_t TrackID;

    float SiPMHitLocalX;
    float SiPMHitLocalY;
    float SiPMHitLocalZ;

    SimSiPMHit_t(Tao::SimEvt* sim_event, Tao::SimSipmHit* cd_hit)
    {
        this->EventID = sim_event->getEventID();
#define ASSIGN(name) this->name = cd_hit->get##name()
        ASSIGN(SipmID);
        ASSIGN(HitTime);
        ASSIGN(TimeWindow);
        ASSIGN(TrackID);

        ASSIGN(SiPMHitLocalX);
        ASSIGN(SiPMHitLocalY);
        ASSIGN(SiPMHitLocalZ);
#undef ASSIGN
    }

    static const H5::DataType& get_h5_type()
    {
        static auto type = H5::CompType(sizeof(SimSiPMHit_t));
#define INSERT(name) INSERT_(type, SimSiPMHit_t, name)
        INSERT(EventID);
        INSERT(SipmID);
        INSERT(HitTime);
        INSERT(TimeWindow);
        INSERT(TrackID);

        INSERT(SiPMHitLocalX);
        INSERT(SiPMHitLocalY);
        INSERT(SiPMHitLocalZ);
#undef INSERT
        return type;
    }
};

SPEC_H5TYPE_IMPL(SimSiPMHit_t)

struct SimPMTHit_t
{
    int32_t EventID;
    int32_t PMTID;
    int32_t NPE;
    double HitTime;
    double TimeWindow;
    int32_t TrackID;

    double LocalX;
    double LocalY;
    double LocalZ;

    SimPMTHit_t(Tao::SimEvt* sim_event, Tao::SimPmtHit* wp_hit)
    {
        this->EventID = sim_event->getEventID();
#define ASSIGN(name) this->name = wp_hit->get##name()
        ASSIGN(PMTID);
        ASSIGN(NPE);
        ASSIGN(HitTime);
        ASSIGN(TimeWindow);
        ASSIGN(TrackID);

        ASSIGN(LocalX);
        ASSIGN(LocalY);
        ASSIGN(LocalZ);
#undef ASSIGN
    }

    static const H5::DataType& get_h5_type()
    {
        static auto type = H5::CompType(sizeof(SimPMTHit_t));
#define INSERT(name) INSERT_(type, SimPMTHit_t, name)
        INSERT(EventID);
        INSERT(PMTID);
        INSERT(NPE);
        INSERT(HitTime);
        INSERT(TimeWindow);
        INSERT(TrackID);

        INSERT(LocalX);
        INSERT(LocalY);
        INSERT(LocalZ);
#undef INSERT
        return type;
    }
};

SPEC_H5TYPE_IMPL(SimPMTHit_t)

void transform_sim_event(TTree* sim_tree, H5::Group& output, const H5::DSetCreatPropList& dsp)
{
    Tao::SimEvt* sim_event = nullptr;
    sim_tree->SetBranchAddress("SimEvt", &sim_event);
    auto count = sim_tree->GetEntries();
    auto group = output.createGroup("SimEvent");
    auto event_data = buffered_packet_table<SimEvent_t>(group, "Event", count, dsp);
    auto vertex_data = buffered_packet_table<SimTrack_t>(group, "Track", count, dsp);
    auto sipm_data = buffered_packet_table<SimSiPMHit_t>(group, "CDHit", count, dsp);
    auto pmt_data = buffered_packet_table<SimPMTHit_t>(group, "WPHit", count, dsp);
    cout << "Transforming SimEvent..." << count << " in total." << endl;
    for (Long64_t i = 0; i < count; i++)
    {
        sim_tree->GetEntry(i);
        event_data.push_back(SimEvent_t(sim_event));
        auto& tracks = sim_event->getTracksVec();
        for (auto track : tracks)
        {
            vertex_data.push_back(SimTrack_t(sim_event, track));
        }
        auto& cd_hits = sim_event->getCDHitsVec();
        for (auto cd_hit : cd_hits)
        {
            sipm_data.push_back(SimSiPMHit_t(sim_event, cd_hit));
        }
        auto& wp_hits = sim_event->getPmtHitVec();
        for (auto wp_hit : wp_hits)
        {
            pmt_data.push_back(SimPMTHit_t(sim_event, wp_hit));
        }
        if ((i + 1) % LOG_PROCESS_UNIT == 0)
        {
            cout << "Processed " << (i + 1) << " entries." << endl;
        }
    }
    cout << "Done." << endl;
}

struct SimHeader_t
{
    const char* EventType;
    double CDLPMTtimeWindow;
    int32_t CDLPMTtotalHits;

    SimHeader_t(Tao::SimHeader* sim_header)
    {
        EventType = get_raw_str(sim_header->getEventType());
        CDLPMTtimeWindow = sim_header->getCDLPMTtimeWindow();
        CDLPMTtotalHits = sim_header->getCDLPMTtotalHits();
    }

    static const H5::DataType& get_h5_type()
    {
        static auto type = H5::CompType(sizeof(SimHeader_t));
#define INSERT(name) INSERT_(type, SimHeader_t, name)
        INSERT(EventType);
        INSERT(CDLPMTtimeWindow);
        INSERT(CDLPMTtotalHits);
#undef INSERT
        return type;
    }
};

SPEC_H5TYPE_IMPL(SimHeader_t)

void transform_sim_header(TTree* sim_tree, H5::Group& output, const H5::DSetCreatPropList& dsp)
{
    Tao::SimHeader* sim_header = nullptr;
    sim_tree->SetBranchAddress("SimHeader", &sim_header);
    auto count = sim_tree->GetEntries();
    auto header_data = buffered_packet_table<SimHeader_t>(output, "Header", count, dsp);
    cout << "Transforming SimHeader..." << count << " in total." << endl;
    for (Long64_t i = 0; i < count; i++)
    {
        sim_tree->GetEntry(i);
        header_data.push_back(SimHeader_t(sim_header));
        if ((i + 1) % LOG_PROCESS_UNIT == 0)
        {
            cout << "Processed " << (i + 1) << " entries." << endl;
        }
    }
    cout << "Done." << endl;
}
