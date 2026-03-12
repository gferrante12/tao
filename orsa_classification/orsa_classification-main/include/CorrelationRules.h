#ifndef ORSACLASSIFICATION_CORRELATIONRULES_H
#define ORSACLASSIFICATION_CORRELATIONRULES_H

// CorrelationRules.h
//
// Defines the concrete implementations of the abstract CorrelationRule interface.
// The configuration parsing infrastructure dynamically instantiates these logical
// units based upon external structural parameterizations, subsequently registering
// them within the centralized CorrelationEngine for sequential execution against
// all incoming event candidates.
//
// This comprehensive taxonomy encompasses standard delayed-coincidence pairing
// optimized for inverse beta decay identification, versatile timing window vetoes
// correlated with generalized muon topologies or specific spallation interactions,
// extended historical baselines for cosmogenic isotope tracking, and data quality
// monitoring mechanisms mitigating detector acquisition dead-times. Additionally,
// compound logical chaining allows the synthesis of complex multi-category criteria.

#include "CorrelationEngine.h"
#include "OutputManager.h"
#include "SniperKernel/SniperLog.h"
#include "TTree.h"
#include <string>
#include <deque>
#include <vector>
#include <cmath>

#include "TimeWindowPickerRule.h"

namespace Orsa {

    // ... (rest of the file until LongHistoryRule)

    // Long-baseline history lookup for cosmogenic isotope searches.
    class LongHistoryRule : public CorrelationRule {
    public:
        LongHistoryRule(const std::string& name, int candTag, int histTag, int64_t minWin, int64_t maxWin, double radius, int resTag)
            : m_name(name), m_candTag(candTag), m_histTag(histTag), m_minWin(minWin), m_maxWin(maxWin), m_radius(radius), m_resTag(resTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            if (m_candTag >= 0 && !curr.hasTag(m_candTag)) return false;
            
            auto hm = engine.getHistoryManager();
            if (!hm) return false;
            
            int64_t tMin = curr.time - m_maxWin;
            int64_t tMax = curr.time - m_minWin;
            
            int64_t matchTime = 0;
            TVector3 matchPos;
            
            if (hm->getNearest(m_histTag, tMin, tMax, curr.pos, m_radius, matchTime, matchPos)) {
                engine.addTag(curr, m_resTag);
                
                auto om = engine.getOutputManager();
                if (om) {
                    // Reconstruct a partial candidate from the history match.
                    Candidate match;
                    match.time = matchTime;
                    match.pos = matchPos;
                    match.setTag(m_histTag);
                    
                    // Use the standard output manager to fill a pair entry.
                    // This creates a standard tree schema (t_p, t_d, dt, dr, etc.)
                    // Note: match is "prompt" (past), curr is "delayed" (current).
                    om->getOrBookTree(m_name, "Long History Pairs for " + m_name);
                    om->fillPair(m_name, match, curr, engine.getMuonManager().get());
                }
                return true;
            }
            return false;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int m_candTag, m_histTag;
        int64_t m_minWin, m_maxWin; // lookback range [ns]
        double m_radius;             // spatial radius [mm]
        int m_resTag;
    };

// 
// Pair-correlation rule for delayed-coincidence searches (e.g. IBD).
    //
    // When a new candidate arrives carrying the delayed tag, the rule
    // scans backwards through the correlation window looking for a
    // prompt candidate within [dt_min, dt_max] and closer than dr_max.
    // For each matching pair it:
    //   - computes isolation counters in configurable time windows
    //   - fills the signal output tree
    //   - optionally tags both candidates with a new tag
    //
    // If accidental windows are configured, the same search is repeated
    // at N time offsets (shifted well outside the signal window) to
    // estimate the accidental background rate.
    //
    // The rule supports separate tag requirements for prompt and delayed
    // candidates (requires_tag_prompt / requires_tag_delayed), as well
    // as a global requires_tag that applies to both.  The negate flags
    // invert the requirement (e.g. "NOT MuonVetoed").
    class StandardPairRule : public CorrelationRule {
        std::string m_name;
        int m_pTag;
        int m_dTag;
        int64_t m_dt_min;
        int64_t m_dt_max;
        double m_dr_max;
        int m_newTag;
        int m_isolationTag;
        int64_t m_iso_window_before;
        int64_t m_iso_window_after;
        
        // Per-leg tag requirements
        int m_requiresTag;
        bool m_negateRequiresTag;
        int m_reqTagPrompt;
        bool m_negReqTagPrompt;
        int m_reqTagDelayed;
        bool m_negReqTagDelayed;

        double m_dr_max_mm;
        double m_dr_max_mm_sq;

        // Accidental config
        int m_acc_n_windows = 0;
        int64_t m_acc_shift = 0;
        TVector3 m_acc_offset = {0,0,0};

        // Isolation cuts (veto if counts > max)
        int m_iso_before_max = -1;
        int m_iso_between_max = -1;
        int m_iso_after_max = -1;

    public:
        StandardPairRule(const std::string& name, int pTag, int dTag,
                         int64_t dt_min, int64_t dt_max, double dr_max, 
                         int newTag = -1, int isolationTag = -1,
                         int64_t iso_window_before = 1000000, int64_t iso_window_after = 1000000,
                         int requiresTag = -1, bool negateRequiresTag = false,
                         int reqTagPrompt = -1, bool negReqTagPrompt = false,
                         int reqTagDelayed = -1, bool negReqTagDelayed = false,
                         int isoBeforeMax = -1, int isoBetweenMax = -1, int isoAfterMax = -1)
            : m_name(name), m_pTag(pTag), m_dTag(dTag), 
              m_dt_min(dt_min), m_dt_max(dt_max), m_dr_max(dr_max), 
              m_newTag(newTag), m_isolationTag(isolationTag),
              m_iso_window_before(iso_window_before), m_iso_window_after(iso_window_after),
              m_iso_before_max(isoBeforeMax), m_iso_between_max(isoBetweenMax), m_iso_after_max(isoAfterMax)
        {
            // Per-leg tag requirements: use the specific prompt/delayed requirement
            // if provided, otherwise fall back to the generic requires_tag.
            m_reqTagPrompt = (reqTagPrompt != -1) ? reqTagPrompt : requiresTag;
            m_negReqTagPrompt = (reqTagPrompt != -1) ? negReqTagPrompt : negateRequiresTag;
            
            m_reqTagDelayed = (reqTagDelayed != -1) ? reqTagDelayed : requiresTag;
            m_negReqTagDelayed = (reqTagDelayed != -1) ? negReqTagDelayed : negateRequiresTag;

            // Pre-compute the squared distance threshold to avoid sqrt
            // in the inner loop (we compare Mag2 against this).
            m_dr_max_mm = m_dr_max;
            m_dr_max_mm_sq = m_dr_max_mm * m_dr_max_mm;
        }

        bool check(Candidate& curr, std::deque<Candidate>& window, CorrelationEngine& engine) override {
            // Only proceed if the incoming candidate carries the delayed tag.
            if (!curr.hasTag(m_dTag)) return false;
            if (checkVeto(curr)) return false;
            // Check per-leg tag requirement on the delayed candidate.
            if (m_reqTagDelayed >= 0) {
                bool has = curr.hasTag(m_reqTagDelayed);
                if (m_negReqTagDelayed ? has : !has) return false;
            }

            bool foundSignal = false;
            auto mm = engine.getMuonManager();

            // processWindow: scans a sub-window of the correlation window for
            // prompt candidates matching this delayed.  Used for both the signal
            // window and each accidental (shifted) window.
            auto processWindow = [&](int64_t t_start, int64_t t_end, bool isAccidental, int64_t shift, const TVector3& offset) {
                // Binary search for the first candidate at or after t_start.
                auto startIt = std::lower_bound(window.begin(), window.end(), t_start, 
                    [](const Candidate& c, int64_t val){ return c.time < val; });

                for (auto it = startIt; it != window.end(); ++it) {
                    auto& cand = *it;
                    if (cand.time > t_end) break;
                    if (&cand == &curr) continue;
                    if (!cand.hasTag(m_pTag)) continue;
                    if (checkVeto(cand)) continue;
                    // Check per-leg tag requirement on the prompt candidate.
                    if (m_reqTagPrompt >= 0) {
                        bool has = cand.hasTag(m_reqTagPrompt);
                        if (m_negReqTagPrompt ? has : !has) continue;
                    }

                    // Fast pre-check: reject pairs whose Z separation already
                    // exceeds the full dr threshold before computing full 3D distance.
                    double dz;
                    if (isAccidental) dz = std::abs(curr.pos.Z() - (cand.pos.Z() + offset.Z()));
                    else dz = std::abs(curr.pos.Z() - cand.pos.Z());
                    if (dz > m_dr_max_mm) continue;

                    // Full 3D distance check using squared magnitude (no sqrt).
                    double drSq;
                    if (isAccidental) drSq = (curr.pos - (cand.pos + offset)).Mag2();
                    else drSq = (curr.pos - cand.pos).Mag2();
                    if (drSq > m_dr_max_mm_sq) continue;

                    double dr = std::sqrt(drSq);

                    if (!isAccidental) {
                         LogInfo << m_name << " SIGNAL: dt=" << (curr.time - cand.time)/1.0e6 << "ms"
                                 << " Ep=" << cand.energy << " Ed=" << curr.energy 
                                 << " dr=" << dr << "mm" << std::endl;
                    }

                    // Compute isolation: count events carrying the isolation tag
                    // in three regions around the pair.
                    int iso_before = 0, iso_between = 0, iso_after = 0;
                    if (m_isolationTag != -1) {
                        int64_t m_start = cand.time - m_iso_window_before;
                        int64_t m_end = curr.time + m_iso_window_after;
                        
                        auto mIt = std::lower_bound(window.begin(), window.end(), m_start, 
                            [](const Candidate& c, int64_t val){ return c.time < val; });
                        
                        for (; mIt != window.end(); ++mIt) {
                            const auto& wCand = *mIt;
                            if (wCand.time > m_end) break;
                            if (!wCand.hasTag(m_isolationTag)) continue;
                            if (&wCand == &cand || &wCand == &curr) continue; 
                            
                            if (wCand.time < cand.time) iso_before++;
                            else if (wCand.time > cand.time && wCand.time < curr.time) iso_between++;
                            else if (wCand.time > curr.time) iso_after++;
                        }
                    }

                    // Apply isolation cuts if configured.
                    if (m_iso_before_max >= 0 && iso_before > m_iso_before_max) continue;
                    if (m_iso_between_max >= 0 && iso_between > m_iso_between_max) continue;
                    if (m_iso_after_max >= 0 && iso_after > m_iso_after_max) continue;
                    
                    if (!isAccidental) {
                         LogInfo << m_name << " SIGNAL: dt=" << (curr.time - cand.time)/1.0e6 << "ms"
                                 << " Ep=" << cand.energy << " Ed=" << curr.energy 
                                 << " dr=" << dr << "mm"
                                 << " iso(" << iso_before << "," << iso_between << "," << iso_after << ")" << std::endl;
                    }
                    
                    // Attach isolation counters to the prompt candidate so they
                    // can be written to the output tree.
                    cand.isolation.iso_before = iso_before;
                    cand.isolation.iso_between = iso_between;
                    cand.isolation.iso_after = iso_after;

                    auto om = engine.getOutputManager();
                    if (om) {
                        if (isAccidental) {
                             std::string accName = m_name + "_Acc";
                             om->getOrBookTree(accName, "Accidentals for " + m_name);
                             om->fillPair(accName, cand, curr, mm.get(), shift, offset, true);
                        } else {
                             om->getOrBookTree(m_name, "Signal Pairs for " + m_name);
                             om->fillPair(m_name, cand, curr, mm.get()); 
                             if (m_newTag >= 0) {
                                 engine.addTag(curr, m_newTag);
                                 engine.addTag(cand, m_newTag);
                             }
                             foundSignal = true; 
                        }
                    }
                }
            };

            // Signal window: search backwards from the delayed by [dt_min, dt_max].
            int64_t sig_start = curr.time - m_dt_max;
            int64_t sig_end = curr.time - m_dt_min;
            processWindow(sig_start, sig_end, false, 0, {0,0,0});

            // Accidental windows: time-shifted copies of the signal window.
            // Each window is shifted by acc_shift + (i-1)*dt_max relative to the delayed.
            if (m_acc_n_windows > 0) {
                for (int i = 1; i <= m_acc_n_windows; ++i) {
                    int64_t shift = m_acc_shift + (i - 1) * m_dt_max;
                    int64_t acc_start = curr.time - shift - m_dt_max;
                    int64_t acc_end = curr.time - shift - m_dt_min;
                    processWindow(acc_start, acc_end, true, shift, m_acc_offset);
                }
            }
            
            return foundSignal;
        }

        std::string name() const override { return m_name; }

        // Configure accidental background estimation windows.
        // n:      number of shifted windows
        // shift:  base time offset [ns] (should be >> dt_max to avoid signal contamination)
        // offset: spatial offset applied to the prompt position (usually zero)
        void setAccidentalConfig(int n, int64_t shift, const TVector3& offset) {
            m_acc_n_windows = n; m_acc_shift = shift; m_acc_offset = offset;
        }

        // Return the maximum lookback this rule needs, accounting for
        // both the signal window and any accidental windows.  Used by
        // ConfigLoader to size the engine's sliding window.
        int64_t maxNeededWindow() const {
             int64_t w = m_dt_max;
             if (m_acc_n_windows > 0) w = std::max(w, m_acc_shift + (int64_t)m_acc_n_windows * m_dt_max);
             return w;
        }


    };


    // Tags events occurring within a configurable time window after a muon.
    // Supports per-muon-type veto durations: if the muon carries a neutron
    // tag (indicating spallation), a longer veto_time_with_n is applied.
    class MuonVetoRule : public CorrelationRule {
    public:
        // vetoTime     default veto duration [ns]
        // vetoTagID    tag applied to vetoed events
        // muonTagID    only veto after muons carrying this tag (-1 = any muon)
        // nTagID       neutron tag on the muon (for extended veto)
        // vetoTimeWithN  extended veto duration when the muon has nTagID
        MuonVetoRule(const std::string& name, int64_t vetoTime, int vetoTagID, int muonTagID = -1, int nTagID = -1, int64_t vetoTimeWithN = -1) 
            : m_name(name), m_vetoTime(vetoTime), m_vetoTagID(vetoTagID), m_muonTagID(muonTagID), m_nTagID(nTagID), m_vetoTimeWithN(vetoTimeWithN) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            auto mm = engine.getMuonManager();
            if (!mm) return false;
            
            // Use the longer of the two veto times as the lookback range.
            int64_t maxVeto = m_vetoTime;
            if (m_vetoTimeWithN > m_vetoTime) maxVeto = m_vetoTimeWithN;

            mm->forEachMuon(curr.time, maxVeto, [&](const Candidate& mu) {
                // If a specific muon tag is required, skip muons without it.
                if (m_muonTagID >= 0 && !mu.hasTag(m_muonTagID)) return true;
                
                int64_t dt = curr.time - mu.time;

                // Choose the veto duration: extended if the muon produced neutrons.
                int64_t ruleVetoTime = m_vetoTime;
                if (m_nTagID >= 0 && mu.hasTag(m_nTagID) && m_vetoTimeWithN > 0) {
                    ruleVetoTime = m_vetoTimeWithN;
                }

                if (dt > 0 && dt < ruleVetoTime) {
                    engine.addTag(curr, m_vetoTagID); 
                    return false; // vetoed — stop iterating over muons
                }
                return true; // continue checking older muons
            });
            return false; // veto rules only tag; they never "consume" events
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int64_t m_vetoTime;
        int m_vetoTagID;
        int m_muonTagID;
        int m_nTagID;
        int64_t m_vetoTimeWithN;
    };


    // Retroactively tags muons that are followed by a neutron-like event
    // within dtMax nanoseconds.  Runs on neutron candidates: for each one,
    // it finds the closest preceding muon and applies the result tag to
    // the muon (not the neutron).
    class MuonNeutronRule : public CorrelationRule {
    public:
        MuonNeutronRule(const std::string& name, int muonTag, int neutronTag, int64_t dtMax, int resTag)
            : m_name(name), m_muonTag(muonTag), m_neutronTag(neutronTag), m_dtMax(dtMax), m_resTag(resTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            if (m_neutronTag >= 0 && !curr.hasTag(m_neutronTag)) return false;
            
            auto mm = engine.getMuonManager();
            if (!mm) return false;
            
            Candidate* mu = mm->closestInTime(curr.time);
            if (mu && (m_muonTag < 0 || mu->hasTag(m_muonTag))) {
                int64_t dt = curr.time - mu->time;
                if (dt > 0 && dt < m_dtMax) {
                    engine.addTag(*mu, m_resTag); 
                }
            }
            return false;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int m_muonTag;
        int m_neutronTag;
        int64_t m_dtMax;
        int m_resTag;
    };


    // Tags events as spallation products if they fall within a configurable
    // time window and spatial radius of the most recent muon.
    // Both time and distance are measured from the muon to the current
    // candidate.  Distance is point-to-point [mm].
    class SpallationRule : public CorrelationRule {
    public:
        SpallationRule(const std::string& name, int64_t timeWindow, double radius, int spallationTagID, int targetTag = -1) 
            : m_name(name), m_timeWindow(timeWindow), m_radius(radius), m_spallationTagID(spallationTagID), m_targetTag(targetTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            // Only consider candidates that carry the target tag (if configured).
            if (m_targetTag >= 0 && !curr.hasTag(m_targetTag)) return false;

            auto mm = engine.getMuonManager();
            if (!mm) return false;

            // Iterate over all muons in the time window.  If any one is within
            // the spatial radius, tag the candidate as a spallation product.
            bool found = false;
            mm->forEachMuon(curr.time, m_timeWindow, [&](const Candidate& mu) {
                 double dist = MuonManager::distToMuon(curr.pos, mu);
                 if (dist < m_radius) {
                      engine.addTag(curr, m_spallationTagID);
                      found = true;
                      return false; // Stop searching once a match is found
                 }
                 return true; // Continue searching
            });
            return found;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int64_t m_timeWindow;   // [ns]
        double m_radius;        // [mm]
        int m_spallationTagID;
        int m_targetTag;
    };

    
    // Generalized spatial veto rule.  Iterates over events in the MuonManager
    // (which can now hold Neutrons or other tags) and vetoes the current
    // candidate if it is within (time, space) of a manager event carrying
    // the target tag.
    class SpatialVetoRule : public CorrelationRule {
    public:
        SpatialVetoRule(const std::string& name, int64_t timeWindow, double radius, int vetoTagID, int targetTagID) 
            : m_name(name), m_timeWindow(timeWindow), m_radius(radius), m_vetoTagID(vetoTagID), m_targetTagID(targetTagID) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            auto mm = engine.getMuonManager();
            if (!mm) return false;

            bool found = false;
            mm->forEachMuon(curr.time, m_timeWindow, [&](const Candidate& prev) {
                 // Skip events that don't match the target tag (e.g. only check Neutrons)
                 if (!prev.hasTag(m_targetTagID)) return true;

                 // Check spatial distance
                 double dist = MuonManager::distToMuon(curr.pos, prev);
                 if (dist < m_radius) {
                      engine.addTag(curr, m_vetoTagID);
                      found = true;
                      return false; // Veto applied, stop searching
                 }
                 return true;
            });
            return found;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int64_t m_timeWindow;
        double m_radius;
        int m_vetoTagID;
        int m_targetTagID;
    };

    // Data quality monitor: detects gaps in the WP and CD event streams
    // and applies a dead-time veto after each gap.  The first events of
    // a job can also be vetoed (job_start_veto flag) to allow the detector
    // to reach a stable state.
    //
    // Gap thresholds and dead-time durations are all in nanoseconds.
    class DataQualityRule : public CorrelationRule {
    public:
        DataQualityRule(const std::string& name, int64_t wpGap, int64_t cdGap, int64_t gapDeadTime, 
                        bool jobStartVeto, int vetoTagID)
            : m_name(name), m_wpGap(wpGap), m_cdGap(cdGap), m_gapDeadTime(gapDeadTime), 
              m_jobStartVeto(jobStartVeto), m_vetoTagID(vetoTagID) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            int det = curr.detType; 
            int64_t t = curr.time;
            
            // Handle the very first event of the job.
            if (m_firstEvent) {
                m_firstEvent = false;
                if (m_jobStartVeto) m_vetoUntil = t + m_gapDeadTime; 
                if (det == 2) m_lastWP = t;
                if (det == 1) m_lastCD = t;
                if (t < m_vetoUntil) engine.addTag(curr, m_vetoTagID);
                return false; 
            }

            // Check for gaps: if the time since the last event of the same
            // detector type exceeds the threshold, extend the veto window.
            if (det == 2) { 
                if (m_lastWP > 0 && (t - m_lastWP > m_wpGap)) {
                    int64_t vetoEnd = t + m_gapDeadTime;
                    if (vetoEnd > m_vetoUntil) m_vetoUntil = vetoEnd;
                }
                m_lastWP = t;
            } else if (det == 1) { 
                if (m_lastCD > 0 && (t - m_lastCD > m_cdGap)) {
                    int64_t vetoEnd = t + m_gapDeadTime;
                    if (vetoEnd > m_vetoUntil) m_vetoUntil = vetoEnd;
                }
                m_lastCD = t;
            }

            if (t < m_vetoUntil) {
                 engine.addTag(curr, m_vetoTagID);
            }
            return false;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int64_t m_wpGap, m_cdGap, m_gapDeadTime;
        bool m_jobStartVeto;
        int m_vetoTagID;
        int64_t m_lastWP = 0, m_lastCD = 0, m_vetoUntil = 0;
        bool m_firstEvent = true;
    };


    // Post-pairing isolation quality cut.  Checks the isolation counters
    // (iso_before, iso_between, iso_after) on candidates that carry a
    // given tag.  Candidates passing all thresholds receive a new tag.
    //
    // A threshold of -1 disables checking for that counter.
    class IsolationQualityRule : public CorrelationRule {
    public:
        IsolationQualityRule(const std::string& name, int requiresTag, int newTag,
                               int maxBefore = -1, int maxBetween = -1, int maxAfter = -1)
            : m_name(name), m_requiresTag(requiresTag), m_newTag(newTag),
              m_maxBefore(maxBefore), m_maxBetween(maxBetween), m_maxAfter(maxAfter) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            if (m_requiresTag >= 0 && !curr.hasTag(m_requiresTag)) return false;
            
            bool passes = true;
            if (m_maxBefore >= 0 && curr.isolation.iso_before > m_maxBefore) passes = false;
            if (m_maxBetween >= 0 && curr.isolation.iso_between > m_maxBetween) passes = false;
            if (m_maxAfter >= 0 && curr.isolation.iso_after > m_maxAfter) passes = false;
            
            if (passes) engine.addTag(curr, m_newTag);
            return false;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int m_requiresTag, m_newTag;
        int m_maxBefore, m_maxBetween, m_maxAfter;
    };


    // Generic coincidence rule: tags events of two different types that
    // occur within a time window of each other.  When an event of tag_1
    // arrives, it scans the window for tag_2 events (and vice versa).
    // Both matched events receive newTag.
    class CoincidenceRule : public CorrelationRule {
    public:
        CoincidenceRule(const std::string& name, int tag1, int tag2, int64_t dt_window, int newTag)
            : m_name(name), m_tag1(tag1), m_tag2(tag2), m_dt(dt_window), m_newTag(newTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& window, CorrelationEngine& engine) override {
            bool isTag1 = curr.hasTag(m_tag1);
            bool isTag2 = curr.hasTag(m_tag2);
            if (!isTag1 && !isTag2) return false;

            if (isTag1) {
                for (auto& cand : window) {
                    if (&cand == &curr) continue;
                    if (cand.hasTag(m_tag2) && std::abs(curr.time - cand.time) <= m_dt) {
                        engine.addTag(curr, m_newTag);
                        return false; 
                    }
                }
            }
            if (isTag2) {
                for (auto& cand : window) {
                    if (&cand == &curr) continue;
                    if (cand.hasTag(m_tag1) && std::abs(curr.time - cand.time) <= m_dt) {
                        engine.addTag(cand, m_newTag);
                        engine.addTag(curr, m_newTag); 
                    }
                }
            }
            return false;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int m_tag1, m_tag2;
        int64_t m_dt;
        int m_newTag;
    };


    // Compound rule: wraps N sub-rules and evaluates them as OR or AND.
    // OR mode returns true if ANY sub-rule matches; AND mode returns true
    // only if ALL match.  Optionally applies a result tag on match.
    class CompoundRule : public CorrelationRule {
    public:
        CompoundRule(const std::string& name, std::vector<std::shared_ptr<CorrelationRule>> children, bool isOR, int resultTag = -1)
            : m_name(name), m_children(std::move(children)), m_isOR(isOR), m_resultTag(resultTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& window, CorrelationEngine& engine) override {
            bool anyMatched = false;
            for (auto& child : m_children) {
                bool matched = child->check(curr, window, engine);
                if (m_isOR && matched) anyMatched = true;
                if (!m_isOR && !matched) return false; // AND short-circuit
            }
            
            bool result = m_isOR ? anyMatched : true;
            if (result && m_resultTag >= 0) {
                engine.addTag(curr, m_resultTag);
            }
            return result;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        std::vector<std::shared_ptr<CorrelationRule>> m_children;
        bool m_isOR;
        int m_resultTag;
    };


    // Promotes an existing category tag into a rule-level output tag.
    // Used inside CompoundRules to build multi-step classification logic
    // (e.g. "HardMuon_CD AND NOT Is_Overlap_Muon → SpallationMuon").
    // Also writes a single-event output tree entry for diagnostics.
    class CategoryTagRule : public CorrelationRule {
    public:
        CategoryTagRule(const std::string& name, int categoryTag, int newTag, 
                        int requiresTag = -1, bool negateRequiresTag = false)
            : m_name(name), m_categoryTag(categoryTag), m_newTag(newTag),
              m_requiresTag(requiresTag), m_negateRequiresTag(negateRequiresTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& /*window*/, CorrelationEngine& engine) override {
            if (!curr.hasTag(m_categoryTag)) return false;
            
            // Optional prerequisite tag (with optional negation).
            if (m_requiresTag >= 0) {
                bool has = curr.hasTag(m_requiresTag);
                if (m_negateRequiresTag ? has : !has) return false;
            }

            if (m_newTag >= 0) {
                engine.addTag(curr, m_newTag);
            }

            // Write a single-event output tree entry for diagnostics.
            auto om = engine.getOutputManager();
            if (om) {
                om->fillSingle(m_name, curr, engine.getMuonManager().get());
            }

            return true;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int m_categoryTag;
        int m_newTag;
        int m_requiresTag;
        bool m_negateRequiresTag;
    };
}
#endif
