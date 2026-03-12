// CorrelationEngine.cc
//
// CorrelationEngine.cc
//
// Defines the core execution mechanics of the chronologically ordered sliding-window
// correlation architecture.
//
// The central sequence execution dynamically prunes expired candidate records
// falling outside the maximum unified retention threshold, subsequently integrating
// newly identified tagged entries into the active topological queue. Following
// integration, the algorithm systematically applies all registered CorrelationRule
// evaluations against the updated data structure, finally delegating long-baseline
// contextual properties to the extended HistoryManager for persistence.
//
// Buffer maintenance algorithms enforce routine chronological expiration across
// both immediate operational queues and auxiliary preservation managers dynamically,
// while complex spatial reconstruction indices undergo intermittent regeneration
// to mathematically amortize systematic processing overhead spanning extensive
// topological queries.

#include "CorrelationEngine.h"

namespace Orsa {

    CorrelationEngine::CorrelationEngine() {
        m_muons = std::make_shared<MuonManager>();
        m_history = std::make_shared<HistoryManager>();
    }

    CorrelationEngine::~CorrelationEngine() {
    }

    void CorrelationEngine::addRule(std::shared_ptr<CorrelationRule> rule) {
        if (!rule) return;
        m_rules.push_back(rule);
        if (rule->maxNeededWindow() > m_maxWindow) {
            m_maxWindow = rule->maxNeededWindow();
        }
    }

    bool CorrelationEngine::wantsUntagged(int64_t time) const {
        for (const auto& rule : m_rules) {
            if (rule->wantsUntagged(time)) return true;
        }
        return false;
    }

    void CorrelationEngine::process(Candidate& cand) {
        // Prune old candidates from the sliding window.
        cleanOld(cand.time);

        // Add the new candidate to the window. Rules decide which tags
        // are relevant; the engine stores all tagged candidates.
        m_window.push_back(cand);

        // Evaluate every registered rule against the new candidate.
        for (auto& rule : m_rules) {
            rule->check(cand, m_window, *this);
        }
        
        // Record tagged events into the long-term history for rules
        // that need minutes-scale lookback (e.g. C11 spallation).
        if (m_history && !cand.tagCounts.empty()) {
             for (size_t tag = 0; tag < cand.tagCounts.size(); ++tag) {
                 if (cand.tagCounts[tag] > 0) {
                     m_history->add((int)tag, cand.time, cand.pos);
                 }
             }
        }
    }

    void CorrelationEngine::cleanOld(int64_t current_time) {
        // Pop candidates that have fallen out of the correlation window.
        while (!m_window.empty() && (current_time - m_window.front().time > m_maxWindow)) {
            m_window.pop_front();
        }
        
        // Keep the muon buffer in sync with the same time horizon.
        if (m_muons) {
            m_muons->cleanOld(current_time);
        }

        // Prune history deques every event (cheap: just pops from front).
        // Rebuild spatial indices only every 1000 events to avoid the
        // expensive O(N) grid sweep on every call.
        if (m_history) {
            m_history->cleanDeques(current_time);
            m_cleanCounter++;
            if (m_cleanCounter % 1000 == 0) {
                m_history->rebuildIndices();
            }
        }
    }

}
