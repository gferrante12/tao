#ifndef ORSACLASSIFICATION_ISOLATIONBURSTRULE_H
#define ORSACLASSIFICATION_ISOLATIONBURSTRULE_H

// IsolationBurstRule.h
//
// Formally identifies high-density topological clusters of events characterized by
// a designated nomenclature tag occurring within a strictly bounded temporal integration
// window. Upon surpassing the prescribed multiplicity threshold, the entire sequence
// of constituent events undergoes uniform re-tagging via the designated result identifier.
//
// Primary analytical applications include the robust tagging of complex spallation
// neutron multiplets subsequent to primary muon transversals, and comprehensive burst
// vetoing wherein temporally anomalous low-energy fluctuations are collectively
// isolated for downstream background suppression.

#include "CorrelationEngine.h"
#include <string>
#include <deque>

namespace Orsa {

    class IsolationBurstRule : public CorrelationRule {
    public:
        // countTag    tag to count (e.g. "Spallation_Follower_Candidate")
        // minCount    minimum multiplicity to trigger the burst tag
        // timeWindow  clustering window [ns]
        // resultTag   tag applied to ALL members of the cluster
        IsolationBurstRule(const std::string& name, int countTag, int minCount, 
                         int64_t timeWindow, int resultTag)
            : m_name(name), m_countTag(countTag), m_minCount(minCount), 
              m_timeWindow(timeWindow), m_resultTag(resultTag) {}

        bool check(Candidate& curr, std::deque<Candidate>& window, CorrelationEngine& engine) override {
            if (!curr.hasTag(m_countTag)) return false;

            // Count how many candidates (including curr) carry the counting
            // tag within the time window.
            int count = 1;
            std::vector<Candidate*> matchCands;
            matchCands.push_back(&curr);

            for (auto& cand : window) {
                if (&cand == &curr) continue;
                if ((curr.time - cand.time) > m_timeWindow) continue;
                if (cand.hasTag(m_countTag)) {
                    count++;
                    matchCands.push_back(&cand);
                }
            }

            // If the threshold is met, tag every member of the cluster.
            if (count >= m_minCount) {
                for (auto* ptr : matchCands) {
                    engine.addTag(*ptr, m_resultTag);
                }
                return true; 
            }
            return false;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        int m_countTag;
        int m_minCount;
        int64_t m_timeWindow;
        int m_resultTag;
    };

}

#endif // ORSACLASSIFICATION_ISOLATIONBURSTRULE_H
