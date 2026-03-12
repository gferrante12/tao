// OrsaAlg.cc
//
// OrsaAlg.cc
//
// Constitutes the explicit implementation of the principal SNiPER algorithmic
// framework execution model. The module rigorously instantiates foundational
// operational properties connecting physical reconstruction pathways to logical
// analysis systems.
//
// The operational timeline defines sequential initialization encompassing critical
// buffer allocations, external data serialization setups, and overarching logic engine
// construction; dynamic, cyclic event interrogation systematically managing continuous
// signal flows; and conclusive termination protocols aggregating statistical distributions
// and embedding defining operational parameters within structured metadata archives.

#include "OrsaAlg.h"
#include "EventWrapper.h"
#include "ConfigLoader.h"
#include <SniperKernel/AlgFactory.h>
#include "RootWriter/RootWriter.h"
#include "SniperKernel/ExecUnit.h"
#include "TTree.h"
#include <fstream>
#include <sstream>
#include "JunoTimer/JunoTimer.h"

namespace Orsa {

    OrsaAlg::OrsaAlg(const std::string& name)
        : AlgBase(name), m_processed_events(0), m_tagged_events(0), m_energy_events(0)
    {
        // Declare SNiPER properties configurable from the steering script.
        declProp("InputFile", m_input_file);
        declProp("EvtMax", m_evtmax);
        declProp("RecAlg", m_rec_alg="OMILREC");
        declProp("Config", m_config_file="config.json"); 
        declProp("ManagerTags", m_managerTags={"Muon"}); 
    }

    OrsaAlg::~OrsaAlg() {}

    bool OrsaAlg::initialize() {
        m_timer = new JunoTimer("OrsaAlg");
        m_timer->start();

        // Resolve the NavBuffer once (reused in every execute() call).
        SniperDataPtr<JM::NavBuffer> navBuf(getParent(), "/Event");
        if (navBuf.invalid()) {
            LogError << "cannot get the NavBuffer @ /Event" << std::endl;
            return false;
        }
        m_buf = navBuf.data();

        // Setup RootWriter-backed OutputManager for dynamic tree booking.
        // The lambda captures the RootWriter service and uses it to book
        // TTree objects on demand from within the OutputManager.
        SniperPtr<RootWriter> rw(getParent(), "RootWriter");
        if (rw.valid()) {
            m_output = std::make_shared<OutputManager>();
            m_output->setTreeBooker([this](const std::string& path, const std::string& desc) -> TTree* {
                SniperPtr<RootWriter> rw_inner(getParent(), "RootWriter");
                if (rw_inner.invalid()) return nullptr;
                auto* task = dynamic_cast<ExecUnit*>(getParent());
                if (!task) return nullptr;
                return rw_inner->bookTree(*task, path, desc);
            });
        } else {
             LogWarn << "RootWriter not found. Output disabled." << std::endl;
        }

        // Create the correlation engine and shared tag registry.
        m_engine = std::make_shared<CorrelationEngine>();
        m_engine->setOutputManager(m_output);
        m_registry = std::make_shared<TagRegistry>();
        m_engine->setTagRegistry(m_registry);

        // Parse the JSON config file: populates m_selectors and registers
        // rules with the engine.
        loadConfig();

        // Auto-detect muon tags by name convention: any registered tag whose
        // name contains "Muon" is treated as a muon identifier.  These tags
        // are used in execute() to feed muons into the MuonManager.
        // Auto-detect tags to feed into the MuonManager (e.g. "Muon", "Neutron").
        if (m_registry) {
            auto allTags = m_registry->getAllTags();
            for (auto const& [id, name] : allTags) {
                for (const auto& substr : m_managerTags) {
                    if (name.find(substr) != std::string::npos) {
                        m_muonTags.push_back(id);
                        LogInfo << "Registered manager-tracked tag: " << name << " (ID " << id << ")" << std::endl;
                        break; 
                    }
                }
            }
        }

        return true;
    }

    bool OrsaAlg::execute() {
        m_processed_events++;
        
        // Retrieve the current EvtNavigator from the buffer.
        auto nav = m_buf->curEvt();
        if (!nav) return true;

        // Stack-allocated wrapper: lazy-loads headers only if accessed.
        JunoEventWrapper wrapper(nav, m_buf, m_rec_alg);
        if (!wrapper.isValid()) return true;

        // Snapshot the event data into a Candidate for the correlation window.
        Candidate cand(wrapper);

        // Apply single-event selectors (categorisation / tagging).
        // Each selector that passes assigns its tag to the candidate.
        int tagCount = 0;
        for (const auto& sel : m_selectors) {
            if (sel->pass(wrapper)) {
                cand.setTag(sel->getTagID());
                m_registry->incrementCount(sel->getTagID());
                tagCount++;
            }
        }
        
        if (tagCount > 0) m_tagged_events++;
        if (wrapper.getEnergy() > 0) m_energy_events++;

        // Feed muons into the MuonManager for downstream veto and
        // spallation rules.  A candidate is considered a muon if it
        // carries any of the auto-detected muon tags.
        bool isMuon = false;
        for (int mID : m_muonTags) {
            if (cand.hasTag(mID)) {
                isMuon = true;
                break;
            }
        }
        if (isMuon) {
            if (m_engine->getMuonManager()) {
                m_engine->getMuonManager()->addMuon(cand);
            }
        }

        // Push all candidates into the correlation engine.
        // Rules decide what to do; untagged events won't enter the HistoryManager
        // but can still be used by e.g. TimeWindowPickerRule.
        // Optimization: only process untagged events if a rule specifically requests them at this time.
        if (tagCount > 0 || m_engine->wantsUntagged(cand.time)) {
            m_engine->process(cand);
        }

        // Periodic progress logging (every 1000 events).
        if (m_processed_events % 1000 == 0) {
            LogInfo << "Processed " << m_processed_events << " events. "
                    << "Stats: Physical(E>0)=" << m_energy_events 
                    << ", Tagged=" << m_tagged_events 
                    << " (This event: tags=" << tagCount 
                    << ", E=" << wrapper.getEnergy() << " MeV)" << std::endl;
        }

        return true;
    }

    bool OrsaAlg::finalize() {
        LogInfo << "Processed " << m_processed_events << " events." << std::endl;

        // --- Save Metadata ---
        // Embed the JSON configuration and the tag map into the output ROOT
        // file's UserMetadata tree.
        if (m_output) {
            std::string configContent;
            if (!m_config_file.empty()) {
                std::ifstream confFile(m_config_file);
                if (confFile.is_open()) {
                    std::stringstream buffer;
                    buffer << confFile.rdbuf();
                    configContent = buffer.str();
                } else {
                    LogWarn << "Could not open config file for saving: " << m_config_file << std::endl;
                }
            }

            std::map<std::string, int> tagMap;
            if (m_registry) {
                 const auto& tm = m_registry->getTagMap();
                 tagMap.insert(tm.begin(), tm.end());
            }
            
            m_output->saveMetadata(configContent, tagMap);
        }
        
        // Print per-tag event counts for a quick sanity check at end of job.
        if (m_registry) {
            LogInfo << "--- Tag Statistics ---" << std::endl;
            auto allTags = m_registry->getAllTags();
            for (auto const& [id, name] : allTags) {
                 LogInfo << "  - " << name << ": " << m_registry->getCount(id) << " events" << std::endl;
            }
        }
        
        if (m_timer) delete m_timer;
        return true;
    }

    void OrsaAlg::loadConfig() {
        ConfigLoader loader;
        if (!loader.load(m_config_file, m_selectors, m_engine, m_registry)) {
            LogError << "Failed to load config from " << m_config_file << std::endl;
        }
    }

} // namespace Orsa

using Orsa::OrsaAlg;
DECLARE_ALGORITHM(OrsaAlg);
