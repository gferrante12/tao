#ifndef ORSACLASSIFICATION_ORSAALG_H
#define ORSACLASSIFICATION_ORSAALG_H

// OrsaAlg.h
//
// Functions as the primary execution algorithm within the SNiPER framework architecture.
// OrsaAlg orchestrates the continuous, chronological evaluation pipeline handling
// primary initialization of the configuration matrix, executing immediate categorical
// single-event selection across sequential incoming signals, and driving the comprehensive
// delayed-correlation engine capable of extensive macro-temporal matching.
//
// Core execution progressively extracts immutable event quantities, allocates
// identification nomenclature dynamically, dispatches relevant topologies to decoupled
// auxiliary management systems, and finalizes integrated analysis logs. Dynamic properties
// exposed to the overarching execution script enable flexible adaptation of operational
// constraints and physical reconstruction pathways.

#include "SniperKernel/AlgBase.h"
#include "EvtNavigator/NavBuffer.h"
#include "CorrelationEngine.h"
#include "Selector.h"
#include "TagRegistry.h"
#include "OutputManager.h"

class JunoTimer;

namespace Orsa {

class OrsaAlg : public AlgBase {
public:
    OrsaAlg(const std::string& name);
    ~OrsaAlg();

    bool initialize() override;
    bool execute() override;
    bool finalize() override;

private:
    // Load and parse the JSON config file, populating m_selectors,
    // m_engine, m_registry, and m_output.
    void loadConfig();

    JM::NavBuffer* m_buf = nullptr;         // shared event buffer
    std::string m_input_file;               // input file path (SNiPER property)
    int m_evtmax = -1;                      // max events to process (SNiPER property)
    std::string m_config_file;              // path to JSON config
    std::string m_rec_alg;                  // reconstruction algorithm path

    std::shared_ptr<CorrelationEngine> m_engine;
    std::shared_ptr<TagRegistry> m_registry;
    std::shared_ptr<OutputManager> m_output;

    std::vector<std::shared_ptr<Selector>> m_selectors;  // single-event category filters
    std::vector<int> m_muonTags;              // tag IDs auto-detected as muon-related
    std::vector<std::string> m_managerTags;   // substrings to match for MuonManager inclusion

    // Counters for the end-of-job summary.
    long long m_processed_events = 0;
    long long m_tagged_events = 0;
    long long m_energy_events = 0;

    JunoTimer* m_timer = nullptr;
};

}

#endif // ORSACLASSIFICATION_ORSAALG_H
