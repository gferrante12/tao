#ifndef ORSACLASSIFICATION_EVENTWRAPPER_H
#define ORSACLASSIFICATION_EVENTWRAPPER_H

// EventWrapper.h
//
// Establishes a homogenous, immutable interface to fundamental event-level quantities,
// standardizing properties such as reconstructed visible energy, spatial coordinates,
// collected charge, component categorization, and calibration statistics, completely
// abstracting the divergent underlying JUNO and TAO detector-specific data models.
//
// The standard concrete encapsulation mechanism initializes via a native EvtNavigator
// and aggressively defers detailed sub-header ingestion until requisite access occurs.
// This strict lazy-evaluation strategy guarantees minimal memory and processing overhead
// by discarding unused analytical paths. Preprocessor-level directives dynamically
// dictate environment-specific header resolutions during initial compilation.

#include "EvtNavigator/EvtNavigator.h"
#include "EvtNavigator/EvtNavHelper.h"
#include "EvtNavigator/NavBuffer.h"
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wreorder"

#include "Event/CdVertexRecHeader.h"
#include "Event/CdVertexRecEvt.h"

#ifdef TAO_ENV
#include "Event/CdCalibHeader.h"
#include "Event/CdCalibEvt.h"
#include "Event/WtElecHeader.h"
#include "Event/WtElecEvt.h"
#include "Event/TvtElecHeader.h"
#include "Event/TvtElecEvt.h"
#else
#include "Event/CdLpmtCalibHeader.h"
#include "Event/CdLpmtCalibEvt.h"
#include "Event/WpRecHeader.h"
#include "Event/WpRecEvt.h"
#include "Event/CdTrackRecHeader.h" // Added for CD tracks
#include "Event/CdTrackRecEvt.h"    // Added for CD tracks
#include "Event/RecTrack.h"
#include "Event/WpCalibHeader.h"
#include "Event/WpCalibEvt.h"
#include "CLHEP/Vector/LorentzVector.h"
#endif

#include "Event/OecHeader.h"
#include "Event/OecEvt.h"

#pragma GCC diagnostic pop
#include "TVector3.h"
#include <memory>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <iostream>

// Macro aliases: the reconstruction header and event classes have
// different names in JUNO (JM namespace) and TAO (Tao namespace).
// These macros let the rest of the code use a single type name.
#ifdef TAO_ENV
#define RecHeaderType Tao::CdVertexRecHeader
#define RecEvtType Tao::CdVertexRecEvt
#define RECO_NAMESPACE_STR "Tao"
#else
#define RecHeaderType JM::CdVertexRecHeader
#define RecEvtType JM::CdVertexRecEvt
#define RECO_NAMESPACE_STR "JM"
#endif


// Comprehensive calibration-level characterization parameter sets derived directly
// from primary waveform reconstruction. Execution follows lazy-evaluation principles.
// Integrated total charge metrics refer to photoelectrons, timing parameters utilize nanoseconds.
struct CalibStats {
    int nFired = 0;              // number of fired PMT channels
    float totalPE = 0;           // total collected photoelectrons
    float max_pmt_PE = 0;        // charge of the single brightest PMT
    float second_max_pmt_PE = 0; // charge of the second-brightest PMT
    float charge_ratio = 1e6;    // max_pmt_PE / totalPE  (large → single-PMT dominated)
    bool is_flasher = false;     // flasher flag from the elliptical NTQ cut
    bool is_lowEMuon = false;    // low-energy muon flag from the empirical three-parameter cut
    float ntq_mean = 0;          // mean of the hits-per-PMT distribution
    float ntq_std = 0;           // standard deviation of hits-per-PMT
    float hit_t_mean = 0;        // mean hit time [ns]
    float hit_t_std = 0;         // standard deviation of hit times [ns]
    float hit_q_mean = 0;        // mean charge per fired channel [PE]
    float hit_q_std = 0;         // standard deviation of per-channel charge [PE]
};

// Encapsulates reconstructed topological parameters concerning detected muon crossings.
// Within specific environments lacking inherent tracking capability, the mechanism gracefully
// defaults to an initialized negative identification state.
struct TrackInfo {
    bool exists = false;
    TVector3 start;
    TVector3 end;
    double length = 0;
    int ntracks = 0;     // total number of WP tracks in this event
};

// Transient isolation evaluation boundaries coupled directly to verified selection candidates
// following correlation execution. Aggregation reflects surrounding background event frequency.
struct IsolationInfo {
    int iso_before = 0;  // events of the isolation tag BEFORE the prompt
    int iso_between = 0; // events BETWEEN prompt and delayed
    int iso_after = 0;   // events AFTER the delayed
};


// Analytically evaluates population statistical invariants over arbitrary parameter distributions,
// standardizing calculation algorithms referencing generalized analysis framework directives.
static inline void computeMeanStd(const std::vector<float>& values,
                                   float& mean, float& stddev) {
    if (values.empty()) { mean = 0; stddev = 0; return; }
    double sum = 0;
    for (float v : values) sum += v;
    mean = (float)(sum / values.size());
    double var = 0;
    for (float v : values) { double d = v - mean; var += d * d; }
    stddev = (float)std::sqrt(var / values.size());
}

// Evaluates a rigorous multi-parameter empirical classification criterion differentiating
// minimum-ionizing particle interactions. The classification logically conjoins constraints
// spanning peak charge density, normalized statistical moment distributions, and primary
// sequence amplitude ratios.
static inline bool IsLowEMuon(float totalQ, float maxQ, float secondQ,
                               float qMean, float qStd) {
    if (totalQ <= 0 || secondQ <= 0) return false;
    bool p1 = (maxQ / totalQ) > (std::exp(-totalQ * 2.8e-4f - 1.5f) + 0.017f);
    bool p2 = (qMean * 28 - 43) > qStd;
    bool p3 = ((maxQ - secondQ) / secondQ) < 2;
    return p1 && p2 && p3;
}


// Abstract foundational protocol defining universal event evaluation methodology.
// Inheriting configurations establish direct data links mapping abstract queries
// against proprietary reconstruction structure standards.
class EventWrapper {
public:
    virtual ~EventWrapper() {}

    // Absolute event timestamp in nanoseconds since epoch.
    virtual int64_t getTime() const = 0;

    // Reconstructed visible energy [MeV].  `source` selects the
    // reconstruction algorithm: "RecHeader", "OEC", or "" (auto).
    virtual double getEnergy(const std::string& source = "") const = 0;

    // Reconstructed vertex position [mm].
    virtual TVector3 getPos(const std::string& source = "") const = 0;

    // Total collected charge [photoelectrons].
    virtual double getCharge() const = 0;

    // Detector sub-system identifier:  1 = CD,  2 = WP,  4 = TT.
    virtual int getDetectorType() const = 0;

    // Number of fired PMT channels for the given sub-detector.
    virtual int getNFired(const std::string& source = "") const = 0;

    // Number of fired Front-End Cards (or Modules) for the given sub-detector.
    virtual int getNFECs(const std::string& source = "") const = 0;

    // Time difference to the previous event in the NavBuffer [ns].
    virtual double getDTPrev() const = 0;

    // Full calibration-level statistics (charge distribution, flasher
    // flag, etc.).  Computed lazily on first access.
    virtual CalibStats getCalibStats() const = 0;

    // Muon track information (JUNO only; returns default on TAO).
    virtual TrackInfo getTrackInfo() const { return {}; }

    // Check whether a coincident event of a given detector type exists
    // within [dt_min, dt_max] ns and above a minimum charge threshold.
    virtual bool hasCoincidence(int targetDet, double dt_min, double dt_max, double minQ) const = 0;

    // Returns false if no valid sub-header could be loaded for this event.
    virtual bool isValid() const = 0;
};


// Concrete EventWrapper implementation for JUNO/TAO data read through
// SNiPER's EvtNavigator.  Each getter lazily loads the corresponding
// header on first call and caches the result for subsequent accesses.
class JunoEventWrapper : public EventWrapper {
public:
    // nav  : pointer to this event's EvtNavigator
    // buf  : pointer to the shared NavBuffer (needed for dt_prev and coincidence checks)
    // recPath : reconstruction algorithm path, e.g. "OMILREC"
    JunoEventWrapper(JM::EvtNavigator* nav, JM::NavBuffer* buf, const std::string& recPath)
        : m_nav(nav), m_buf(buf), m_rec_alg(recPath) {
        if (m_nav) {
            const TTimeStamp& ts = m_nav->TimeStamp();
            m_time = (int64_t)ts.GetSec() * 1000000000LL + (int64_t)ts.GetNanoSec();
        }
    }

    int64_t getTime() const { return m_time; }

    // Energy resolution: try RecHeader first, fall back to OEC if rec
    // returns zero (e.g. for events that failed vertex reconstruction).
    double getEnergy(const std::string& source = "") const override {
        if (source == "OEC") return getOEC().energy;
        if (source == "RecHeader" || source == "default") return getRec().energy;
        double recE = getRec().energy;
        if (recE > 0) return recE;
        return getOEC().energy;
    }

    // Same fallback logic as getEnergy for the vertex position.
    TVector3 getPos(const std::string& source = "") const override {
        if (source == "OEC") return getOEC().pos;
        if (source == "RecHeader" || source == "default") return getRec().pos;
        double recE = getRec().energy;
        if (recE > 0) return getRec().pos;
        return getOEC().pos;
    }

    // Determine which sub-detector this event belongs to by checking
    // which headers are present.  Priority: Rec > Calib > WT > TVT > OEC.
    int getDetectorType() const {
        if (getRec().valid) return 1;
    #ifdef TAO_ENV
        if (getCalib().valid) return 1;
        if (getWt().valid) return 2;
        if (getTvt().valid) return 4;
    #else
        if (getCalib().valid) return 1;
    #endif
        if (getOEC().valid) return 1;
        return 0;
    }

    double getCharge() const {
        return getCalib().charge;
    }

    // Return fired channel count for the requested sub-detector.
    // On TAO the source can be "CD", "WT", or "TVT"; on JUNO only "CD".
    int getNFired(const std::string& source = "") const override {
    #ifdef TAO_ENV
        if (source == "WT") return getWt().nFired;
        if (source == "TVT") return getTvt().nFired;
        if (source == "CD") return getCalib().nFired;
        int det = getDetectorType();
        if (det == 1) return getCalib().nFired;
        if (det == 2) return getWt().nFired;
        if (det == 4) return getTvt().nFired;
    #else
        if (source == "CD" || source.empty()) return getCalib().nFired;
    #endif
        return 0;
    }

    // Return the number of unique "FECs" (or Modules) fired.
    virtual int getNFECs(const std::string& source = "") const override {
        (void)source;
    #ifdef TAO_ENV
        if (source == "TVT" || (source.empty() && getDetectorType() == 4)) {
            const auto& channels = getTvt().channels; // Need to ensure getTvt() exposes channels or create a new struct member
            if (channels.empty()) return 0;
            
            // Count unique modules. From TvtID.h: Module is bits 8-23.
            std::vector<int> modules;
            modules.reserve(channels.size());
            for (const auto& ch : channels) {
                // TvtID::module construction logic.
                // TvtElecChannel::getChannelID() is not const-qualified in some releases, so we cast.
                Tao::TvtElecChannel& nonConstCh = const_cast<Tao::TvtElecChannel&>(ch);
                int mod = (nonConstCh.getChannelID() >> 8) & 0xFFFF; 
                modules.push_back(mod);
            }
            std::sort(modules.begin(), modules.end());
            auto last = std::unique(modules.begin(), modules.end());
            return (int)std::distance(modules.begin(), last);
        }
    #endif
        return 0;
    }

    CalibStats getCalibStats() const {
        return getCalib().stats;
    }

    TrackInfo getTrackInfo() const override {
    #ifndef TAO_ENV
        return loadTrackInfo();
    #else
        return {};
    #endif
    }

    bool isValid() const override {
        return getDetectorType() != 0;
    }

    // Scan the NavBuffer for a coincident event in a different sub-detector
    // within a time window.  Used by CoincidenceSelector to tag, e.g.,
    // CD events accompanied by a WP muon hit.
    bool hasCoincidence(int targetDet, double dt_min, double dt_max, double minQ) const override {
        if (!m_buf) return false;
        for (auto it = m_buf->begin(); it != m_buf->end(); ++it) {
            auto nav = it->get();
            if (nav == m_nav) continue;
            const TTimeStamp& t1 = m_nav->TimeStamp();
            const TTimeStamp& t2 = nav->TimeStamp();
            double dSec = (t2.GetSec() - t1.GetSec());
            double dNano = (t2.GetNanoSec() - t1.GetNanoSec());
            double dt_ns = dSec * 1e9 + dNano;
            if (dt_ns >= dt_min && dt_ns <= dt_max) {
                JunoEventWrapper candWrap(nav, nullptr, m_rec_alg);
                int candDet = candWrap.getDetectorType();
                if (candDet == targetDet) {
                    if (minQ <= 0 || candWrap.getCharge() >= minQ) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // Time since the immediately preceding event in the buffer [ns].
    // Returns -1 if this is the first event or the buffer is unavailable.
    double getDTPrev() const override {
        if (!m_buf) return -1;
        auto it = m_buf->find(m_nav);
        if (it == m_buf->begin() || it == m_buf->end()) return -1;
        auto prev_nav = std::prev(it)->get();
        if (!prev_nav) return -1;
        const TTimeStamp& t1 = prev_nav->TimeStamp();
        const TTimeStamp& t2 = m_nav->TimeStamp();
        double dSec = (t2.GetSec() - t1.GetSec());
        double dNano = (t2.GetNanoSec() - t1.GetNanoSec());
        return dSec * 1e9 + dNano;
    }

protected:
    JM::EvtNavigator* m_nav;
    JM::NavBuffer* m_buf;
    int64_t m_time = 0;

private:
    std::string m_rec_alg;

    // Lazy-loaded data caches.  Each struct has a `checked` flag so the
    // corresponding header is loaded at most once per event.
    struct RecData  { bool checked=false; bool valid=false; double energy=0; TVector3 pos; };
    struct CalibData { bool checked=false; bool valid=false; double charge=0; int nFired=0; CalibStats stats; };
    struct WtData   { bool checked=false; bool valid=false; int nFired=0; };
    struct TvtData  { 
        bool checked=false; 
        bool valid=false; 
        int nFired=0; 
#ifdef TAO_ENV
        std::vector<Tao::TvtElecChannel> channels;
#endif
    };
    struct OecData  { bool checked=false; bool valid=false; double energy=0; TVector3 pos; };

    mutable RecData   m_recData;
    mutable CalibData m_calibData;
    mutable WtData    m_wtData;
    mutable TvtData   m_tvtData;
    mutable OecData   m_oecData;

    // Load the CdVertexRec header and extract energy + position.
    // Tries multiple header paths in order of specificity to handle
    // different JUNO software versions.
    const RecData& getRec() const {
        if (m_recData.checked) return m_recData;
        m_recData.checked = true;

        std::string rec_path = m_rec_alg;
        if (rec_path.empty() || rec_path[0] != '/') rec_path = "/Event/CdVertexRec" + m_rec_alg;

        auto cd_rec = JM::getHeaderObject<RecHeaderType>(m_nav, rec_path);
        if (!cd_rec) cd_rec = JM::getHeaderObject<RecHeaderType>(m_nav, "/Event/CdVertexRec");
        if (!cd_rec) cd_rec = JM::getHeaderObject<RecHeaderType>(m_nav, "/Event/Rec/ChargeCenterAlg");

        if (cd_rec) {
            auto rec_evt = dynamic_cast<RecEvtType*>(cd_rec->event(RECO_NAMESPACE_STR "::CdVertexRecEvt"));
            if (rec_evt) {
                m_recData.valid = true;
#ifdef TAO_ENV
                // TAO: energy and position are direct members of CdVertexRecEvt.
                m_recData.energy = rec_evt->energy();
                m_recData.pos = TVector3(rec_evt->x(), rec_evt->y(), rec_evt->z());
#else
                // JUNO: CdVertexRecEvt holds a vector of vertices; take the first.
                if (!rec_evt->vertices().empty()) {
                    auto vtx = rec_evt->vertices().front();
                    m_recData.energy = vtx->energy();
                    m_recData.pos = TVector3(vtx->x(), vtx->y(), vtx->z());
                }
#endif
            }
        }
        return m_recData;
    }

    // Load calibration data from the PMT-level calib header and compute
    // all CalibStats fields: charge distribution, hit time distribution,
    // NTQ (number of hits per PMT) distribution, flasher flag, and
    // low-energy muon flag.
    const CalibData& getCalib() const {
        if (m_calibData.checked) return m_calibData;
        m_calibData.checked = true;

#ifdef TAO_ENV
        auto cd_calib_hdr = JM::getHeaderObject<Tao::CdCalibHeader>(m_nav, "/Event/Calib");
        if (!cd_calib_hdr) return m_calibData;
        auto calib_evt = dynamic_cast<Tao::CdCalibEvt*>(cd_calib_hdr->event("Tao::CdCalibEvt"));
        if (!calib_evt) return m_calibData;

        m_calibData.valid = true;
        const auto& channels = calib_evt->GetCalibChannels();
        m_calibData.nFired = (int)channels.size();

        // Collect per-channel statistics.
        std::vector<float> nhits_per_pmt;
        std::vector<float> charges;
        std::vector<float> all_times;
        nhits_per_pmt.reserve(m_calibData.nFired);
        charges.reserve(m_calibData.nFired);
        all_times.reserve(m_calibData.nFired * 2);

        double totalPESum = 0;
        float maxQ = 0, secondQ = 0;

        for (const auto& ch : channels) {
            const auto& pes = ch.CalibgetPEs();
            const auto& times = ch.CalibgetTDCs();

            // Sum all PE values on this channel.
            float channelQ = 0;
            for (float pe : pes) channelQ += pe;

            if (channelQ > 0) {
                totalPESum += channelQ;
                charges.push_back(channelQ);
                // Track the two brightest channels for flasher / low-E muon cuts.
                if (channelQ > maxQ) {
                    secondQ = maxQ;
                    maxQ = channelQ;
                } else if (channelQ > secondQ) {
                    secondQ = channelQ;
                }
            }

            // NTQ: number of TDC hits on this PMT.
            if (!times.empty()) {
                nhits_per_pmt.push_back((float)times.size());
                all_times.insert(all_times.end(), times.begin(), times.end());
            }
        }

        m_calibData.charge = totalPESum;

        CalibStats& st = m_calibData.stats;
        st.nFired = m_calibData.nFired;
        st.totalPE = (float)totalPESum;
        st.max_pmt_PE = maxQ;
        st.second_max_pmt_PE = secondQ;
        st.charge_ratio = (st.totalPE > 0) ? (maxQ / st.totalPE) : 1e6f;

        computeMeanStd(all_times, st.hit_t_mean, st.hit_t_std);
        computeMeanStd(nhits_per_pmt, st.ntq_mean, st.ntq_std);
        computeMeanStd(charges, st.hit_q_mean, st.hit_q_std);

        // Flasher identification: elliptical cut in the (ntq_std, hit_t_std) plane.
        // Events inside the ellipse (eps < 1) are normal physics; outside are flashers.
        if (!nhits_per_pmt.empty()) {
            double eps = std::pow((st.ntq_std - 0.55) / 0.45, 2)
                       + std::pow((st.hit_t_std - 170.0) / 80.0, 2);
            st.is_flasher = (eps > 1.0);
        }

        st.is_lowEMuon = IsLowEMuon(st.totalPE, maxQ, secondQ,
                                     st.hit_q_mean, st.hit_q_std);

#else  // JUNO
        auto cd_hdr = JM::getHeaderObject<JM::CdLpmtCalibHeader>(m_nav);
        if (!cd_hdr) return m_calibData;
        auto calibEvt = dynamic_cast<JM::CdLpmtCalibEvt*>(cd_hdr->event());
        if (!calibEvt) return m_calibData;

        m_calibData.valid = true;
        const auto& channels = calibEvt->calibPMTCol();
        m_calibData.nFired = (int)channels.size();

        std::vector<float> nhits_per_pmt;
        std::vector<float> charges;
        std::vector<float> all_times;
        nhits_per_pmt.reserve(m_calibData.nFired);
        charges.reserve(m_calibData.nFired);
        all_times.reserve(m_calibData.nFired * 2);

        double totalPESum = 0;
        float maxQ = 0, secondQ = 0;

        for (auto ch : channels) {
            const auto& times = ch->time();
            float channelQ = ch->sumCharge();

            if (channelQ > 0) {
                totalPESum += channelQ;
                charges.push_back(channelQ);
                if (channelQ > maxQ) {
                    secondQ = maxQ;
                    maxQ = channelQ;
                } else if (channelQ > secondQ) {
                    secondQ = channelQ;
                }
            }

            if (!times.empty()) {
                nhits_per_pmt.push_back((float)times.size());
                all_times.insert(all_times.end(), times.begin(), times.end());
            }
        }

        m_calibData.charge = totalPESum;

        CalibStats& st = m_calibData.stats;
        st.nFired = m_calibData.nFired;
        st.totalPE = (float)totalPESum;
        st.max_pmt_PE = maxQ;
        st.second_max_pmt_PE = secondQ;
        st.charge_ratio = (st.totalPE > 0) ? (maxQ / st.totalPE) : 1e6f;

        computeMeanStd(all_times, st.hit_t_mean, st.hit_t_std);
        computeMeanStd(nhits_per_pmt, st.ntq_mean, st.ntq_std);
        computeMeanStd(charges, st.hit_q_mean, st.hit_q_std);

        if (!nhits_per_pmt.empty()) {
            double eps = std::pow((st.ntq_std - 0.55) / 0.45, 2)
                       + std::pow((st.hit_t_std - 170.0) / 80.0, 2);
            st.is_flasher = (eps > 1.0);
        }

        st.is_lowEMuon = IsLowEMuon(st.totalPE, maxQ, secondQ,
                                     st.hit_q_mean, st.hit_q_std);
#endif
        return m_calibData;
    }

#ifdef TAO_ENV
    // Load the water-tank electronics header (TAO only).
    // The WT provides muon tagging via channel multiplicity.
    const WtData& getWt() const {
        if (m_wtData.checked) return m_wtData;
        m_wtData.checked = true;
        auto wt_hdr = JM::getHeaderObject<Tao::WtElecHeader>(m_nav, "/Event/WtElec");
        if (wt_hdr) {
            auto wt_evt = dynamic_cast<Tao::WtElecEvt*>(wt_hdr->event("Tao::WtElecEvt"));
            if (wt_evt) {
                m_wtData.valid = true;
                m_wtData.nFired = (int)wt_evt->GetElecChannels().size();
            }
        }
        return m_wtData;
    }

    // Load the top-veto-tracker electronics header (TAO only).
    const TvtData& getTvt() const {
        if (m_tvtData.checked) return m_tvtData;
        m_tvtData.checked = true;
        auto tvt_hdr = JM::getHeaderObject<Tao::TvtElecHeader>(m_nav, "/Event/TvtElec");
        if (tvt_hdr) {
            auto tvt_evt = dynamic_cast<Tao::TvtElecEvt*>(tvt_hdr->event("Tao::TvtElecEvt"));
            if (tvt_evt) {
                m_tvtData.valid = true;
                const auto& chans = tvt_evt->GetElecChannels();
                m_tvtData.nFired = (int)chans.size();
                m_tvtData.channels = chans;
            }
        }
        return m_tvtData;
    }
#else
    const WtData& getWt() const { return m_wtData; }
    const TvtData& getTvt() const { return m_tvtData; }

    // Extract the longest muon track from the water pool reconstruction.
    // JUNO only; TAO has no water pool tracking.
    // Extract the longest muon track from reconstruction (WP or CD).
    // JUNO only; TAO has no tracking.
    TrackInfo loadTrackInfo() const {
        TrackInfo info;
        // 1. Try Water Pool (WP) Reconstruction
        auto wprechdr = JM::getHeaderObject<JM::WpRecHeader>(m_nav);
        if (wprechdr) {
            auto WPEvt = dynamic_cast<JM::WpRecEvt*>(wprechdr->event("JM::WpRecEvt"));
            if (WPEvt) {
                const auto& tracks = WPEvt->tracks();
                if (!tracks.empty()) {
                   const JM::RecTrack* longest = *std::max_element(
                        tracks.begin(), tracks.end(),
                        [](const JM::RecTrack* a, const JM::RecTrack* b) {
                            if (!a || !b) return b != nullptr;
                            return (a->end() - a->start()).mag2() < (b->end() - b->start()).mag2();
                        });
                    if (longest) {
                        info.exists = true;
                        info.start = TVector3(longest->start().x(), longest->start().y(), longest->start().z());
                        info.end = TVector3(longest->end().x(), longest->end().y(), longest->end().z());
                        info.length = (info.end - info.start).Mag();
                        info.ntracks = (int)tracks.size();
                        return info; 
                    }
                }
            }
        }

        // 2. Try Central Detector (CD) Reconstruction
        auto cdrechdr = JM::getHeaderObject<JM::CdTrackRecHeader>(m_nav);
        if (cdrechdr) {
            auto CDEvt = dynamic_cast<JM::CdTrackRecEvt*>(cdrechdr->event("JM::CdTrackRecEvt"));
            if (CDEvt) {
                 const auto& tracks = CDEvt->tracks();
                 if (!tracks.empty()) {
                    const JM::RecTrack* longest = *std::max_element(
                        tracks.begin(), tracks.end(),
                        [](const JM::RecTrack* a, const JM::RecTrack* b) {
                            if (!a || !b) return b != nullptr;
                            return (a->end() - a->start()).mag2() < (b->end() - b->start()).mag2();
                        });
                    if (longest) {
                        info.exists = true;
                        info.start = TVector3(longest->start().x(), longest->start().y(), longest->start().z());
                        info.end = TVector3(longest->end().x(), longest->end().y(), longest->end().z());
                        info.length = (info.end - info.start).Mag();
                        info.ntracks = (int)tracks.size(); // Or add to existing if both present? Usually mutually exclusive.
                        return info;
                    }
                 }
            }
        }

        return info;
    }
#endif

    // Load the Online Event Classification header.
    // OEC provides a fast energy estimate; used as fallback when the
    // full vertex reconstruction is not available.
    const OecData& getOEC() const {
        if (m_oecData.checked) return m_oecData;
        m_oecData.checked = true;
        auto oec_hdr_obj = JM::getHeaderObject<JM::OecHeader>(m_nav);
        if (oec_hdr_obj) {
            auto oec_evt = dynamic_cast<JM::OecEvt*>(oec_hdr_obj->event("JM::OecEvt"));
            if (oec_evt) {
                m_oecData.valid = true;
                m_oecData.energy = oec_evt->getEnergy();
                m_oecData.pos = TVector3(oec_evt->getVertexX(), oec_evt->getVertexY(), oec_evt->getVertexZ());
            }
        }
        return m_oecData;
    }
};

#endif // ORSACLASSIFICATION_EVENTWRAPPER_H
