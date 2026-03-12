#ifndef ORSACLASSIFICATION_CORRELATIONENGINE_H
#define ORSACLASSIFICATION_CORRELATIONENGINE_H

// CorrelationEngine.h
//
// Represents the primary analytical core for multi-event temporal and spatial
// correlations. The CorrelationEngine orchestrates a dynamic, sliding time window
// of discrete EventCandidates and sequentially applies a configured taxonomy of
// CorrelationRules to evaluate coincidence signatures.
//
// The engine oversees continuous operation and shares instances of auxiliary managers
// necessary for context preservation: the MuonManager, which holds a time-ordered
// buffer for veto logic; the HistoryManager, facilitating extended baseline cosmogenic
// correlation searches; and the OutputManager, coordinating tree synchronization.
//
// Context persistence is achieved via a time-ordered data deque. Candidates extending
// beyond the maximum temporal threshold, governed by the longest correlation rule
// specified in the initialization configuration, are systematically pruned to ensure
// steady-state memory utilization.

#include "Candidate.h"
#include "MuonManager.h"
#include "HistoryManager.h"
#include "OutputManager.h"
#include "TagRegistry.h"
#include <deque>
#include <functional>
#include <memory>

namespace Orsa {

    class CorrelationEngine; // forward declaration for CorrelationRule

    // Defines the abstract base structure interface for correlation evaluation.
    // Derived rules examine incoming candidates against contextual data
    // provided by the temporal window and active manager state. Depending on
    // analytical criteria, rules might annotate the candidate, update history,
    // or trigger persistence in the output stream.
    class CorrelationRule {
    public:
        virtual ~CorrelationRule() {}

        // Processes the correlation logic for an individual arriving candidate.
        // It provides access to the candidate under evaluation, the sequence of
        // recent historical events, and the primary engine interface for broader
        // manager communication. The Boolean return signifies successful matching
        // under the defined implementation criteria.
        virtual bool check(Candidate& curr, std::deque<Candidate>& window, CorrelationEngine& engine) = 0;

        // Indicates whether the associated analytical rule necessitates execution
        // over untagged background data points evaluated at the given timestamp.
        virtual bool wantsUntagged(int64_t /*time*/) const { return false; }
        
        // Exposes the required historical time boundary in nanoseconds necessary
        // for rigorous application of the rule.
        virtual int64_t maxNeededWindow() const { return 0; }

        // Supplies the nominal string identifier utilized for runtime logging
        // and structure output key assignments.
        virtual std::string name() const = 0;

        // Integrates an exclusion sequence of tag identifiers. A candidate carrying
        // an exact matching tag will be systematically bypassed by the internal
        // logic of the correlation rule implementation.
        void setVetoTags(const std::vector<int>& tags) { m_vetoTags = tags; }
        
        // Queries the active candidate attributes against the established 
        // analytical exclusion criteria to govern processing flow.
        bool checkVeto(const Candidate& cand) const {
            for (int tag : m_vetoTags) {
                if (cand.hasTag(tag)) return true;
            }
            return false;
        }

    protected:
        std::vector<int> m_vetoTags;
    };

    class CorrelationEngine {
    public:
        CorrelationEngine();
        ~CorrelationEngine();

        void setMuonManager(std::shared_ptr<MuonManager> mm) { m_muons = mm; }
        std::shared_ptr<MuonManager> getMuonManager() { return m_muons; }

        void setOutputManager(std::shared_ptr<OutputManager> om) { m_output = om; }
        std::shared_ptr<OutputManager> getOutputManager() { return m_output; }

        void addRule(std::shared_ptr<CorrelationRule> rule);

        void setTagRegistry(std::shared_ptr<TagRegistry> reg) { m_registry = reg; }
        
        // Registers a tag on the target candidate and synchronizes the central
        // diagnostic tag counters. This unified interface prevents statistical
        // divergence in comprehensive analysis logs.
        void addTag(Candidate& cand, int tagID) {
            cand.addTag(tagID);
            if (m_registry) m_registry->incrementCount(tagID);
        }

        // Enforces the historical retention span configured in nanoseconds. The
        // processing cycle explicitly removes stale entries from the temporal queue.
        // This limit is dynamically established upon initialization by scanning
        // all incorporated analysis rules.
        void setWindow(int64_t nanoseconds) { m_maxWindow = nanoseconds; }

        // Introduces an event entity to the analysis scope, subsequently evaluating
        // the candidate against the taxonomy of connected correlation definitions,
        // and incorporating the event into longer baseline history management.
        void process(Candidate& cand);

        const std::deque<Candidate>& getWindow() const { return m_window; }
        std::deque<Candidate>& getWindow() { return m_window; }
        
        void setHistoryManager(std::shared_ptr<HistoryManager> hm) { m_history = hm; }
        std::shared_ptr<HistoryManager> getHistoryManager() { return m_history; }

        // Queries across all loaded rules to determine whether unmodified entries
        // necessitate analysis execution based on a designated reference timestamp.
        bool wantsUntagged(int64_t time) const;

    private:
        std::deque<Candidate> m_window;
        std::shared_ptr<MuonManager> m_muons;
        std::shared_ptr<HistoryManager> m_history;
        std::shared_ptr<OutputManager> m_output;
        std::shared_ptr<TagRegistry> m_registry;
        std::vector<std::shared_ptr<CorrelationRule>> m_rules;
        int64_t m_maxWindow = 1000000000LL; // default 1 second

        // Discards candidate records violating temporal boundary conditions and
        // prompts deterministic garbage collection in connected infrastructure modules.
        void cleanOld(int64_t current_time);

        int64_t m_cleanCounter = 0; // Cumulative counter regulating history tree index maintenance
    };

}

#endif // ORSACLASSIFICATION_CORRELATIONENGINE_H
