// OutputManager.cc
//
// OutputManager.cc
//
// Provides the definitive implementation of external data serialization mechanisms
// targeting structural ROOT object methodologies. The architecture robustly defines
// dynamic topological branch construction reacting directly to incoming data schemas.
//
// Specialized integration routines dynamically aggregate complex multiparameter
// property distributions into unified transition arrays preceding high-efficiency
// binary data flushes. The serialization system simultaneously handles complex
// topological relationships referencing generalized structural backgrounds while
// maintaining specialized isolated event structures organically. Comprehensive
// metadata persistence algorithms dynamically embed overarching analytical
// configuration parameters natively mapping generated structural components.

#include "OutputManager.h"
#include "TTree.h"

namespace Orsa {

    OutputManager::OutputManager(TTree* defaultTree) : m_defaultTree(defaultTree) {
        m_defaultSettings.saveTags = true;
        m_defaultSettings.saveMuonInfo = true;
    }

    OutputManager::~OutputManager() {}

    TTree* OutputManager::getOrBookTree(const std::string& name, const std::string& desc) {
        auto it = m_trees.find(name);
        if (it != m_trees.end()) return it->second;
        
        if (m_defaultTree && name == "default") return m_defaultTree;

        TTree* newTree = nullptr;
        if (m_booker) {
            // Use the path from OutputSettings if configured, otherwise
            // default to "output/<name>".
            std::string path = "output/" + name;
            auto sIt = m_treeSettings.find(name);
            if (sIt != m_treeSettings.end() && !sIt->second.path.empty()) {
                path = sIt->second.path;
            }
            newTree = m_booker(path, desc);
        }
        
        if (newTree) m_trees[name] = newTree;
        return newTree;
    }
    
    // Create branches on first fill.  The branch schema adapts to:
    //   - Pair vs single-event (delayed branches only for pairs)
    //   - OutputSettings flags (muon info, calib stats, tags)
    //   - Accidental shift branches (always present for bookkeeping)
    void OutputManager::ensureBranches(TTree* tree, bool isPair) {
        if (!tree) return;
        std::string key = tree->GetName();
        if (m_initialized[key]) return;
        
        OutputSettings s = m_defaultSettings;
        auto sIt = m_treeSettings.find(key);
        if (sIt != m_treeSettings.end()) s = sIt->second;

        // --- Core kinematics (always present) ---
        tree->Branch("t_p", &m_vars.t_p, "t_p/L");
        tree->Branch("E_p", &m_vars.E_p, "E_p/D");
        tree->Branch("x_p", &m_vars.x_p, "x_p/D");
        tree->Branch("y_p", &m_vars.y_p, "y_p/D");
        tree->Branch("z_p", &m_vars.z_p, "z_p/D");
        
        if (isPair) {
            tree->Branch("t_d", &m_vars.t_d, "t_d/L");
            tree->Branch("E_d", &m_vars.E_d, "E_d/D");
            tree->Branch("x_d", &m_vars.x_d, "x_d/D");
            tree->Branch("y_d", &m_vars.y_d, "y_d/D");
            tree->Branch("z_d", &m_vars.z_d, "z_d/D");
            
            tree->Branch("dt", &m_vars.dt, "dt/D");
            tree->Branch("dr", &m_vars.dr, "dr/D");
        }
        
        // --- Muon proximity branches ---
        if (s.saveMuonInfo) {
            // Simple point-to-point distance to closest muon.
            tree->Branch("dt_mu", &m_vars.dt_mu, "dt_mu/L");
            tree->Branch("dist_mu", &m_vars.dist_mu, "dist_mu/D");
            // Track-level distance to the closest muon in time.
            tree->Branch("dist_track_time", &m_vars.dist_track_time, "dist_track_time/D");
            tree->Branch("dt_mu_time", &m_vars.dt_mu_time, "dt_mu_time/L");
            tree->Branch("ntracks_time", &m_vars.ntracks_time, "ntracks_time/I");
            // Track-level distance to the spatially closest muon.
            tree->Branch("dist_track_dist", &m_vars.dist_track_dist, "dist_track_dist/D");
            tree->Branch("dt_mu_dist", &m_vars.dt_mu_dist, "dt_mu_dist/L");
            tree->Branch("ntracks_dist", &m_vars.ntracks_dist, "ntracks_dist/I");
        }

        // --- Per-event tag vectors ---
        if (s.saveTags) {
             tree->Branch("tags_p", &m_vars.tags_p);
             if (isPair) tree->Branch("tags_d", &m_vars.tags_d);
        }
        
        // --- Isolation counters (pairs only) ---
        if (isPair) {
             tree->Branch("iso_before", &m_vars.iso_before, "iso_before/I");
             tree->Branch("iso_between", &m_vars.iso_between, "iso_between/I");
             tree->Branch("iso_after", &m_vars.iso_after, "iso_after/I");
        }
        
        // --- PMT-level calibration statistics ---
        if (s.saveCalibInfo) {
            // Prompt calib branches.
            tree->Branch("nFired_p", &m_vars.nFired_p, "nFired_p/I");
            tree->Branch("totalPE_p", &m_vars.totalPE_p, "totalPE_p/F");
            tree->Branch("max_pmt_PE_p", &m_vars.max_pmt_PE_p, "max_pmt_PE_p/F");
            tree->Branch("second_max_pmt_PE_p", &m_vars.second_max_pmt_PE_p, "second_max_pmt_PE_p/F");
            tree->Branch("charge_ratio_p", &m_vars.charge_ratio_p, "charge_ratio_p/F");
            tree->Branch("is_flasher_p", &m_vars.is_flasher_p, "is_flasher_p/O");
            tree->Branch("is_lowEMuon_p", &m_vars.is_lowEMuon_p, "is_lowEMuon_p/O");
            tree->Branch("ntq_mean_p", &m_vars.ntq_mean_p, "ntq_mean_p/F");
            tree->Branch("ntq_std_p", &m_vars.ntq_std_p, "ntq_std_p/F");
            tree->Branch("hit_t_mean_p", &m_vars.hit_t_mean_p, "hit_t_mean_p/F");
            tree->Branch("hit_t_std_p", &m_vars.hit_t_std_p, "hit_t_std_p/F");
            tree->Branch("hit_q_mean_p", &m_vars.hit_q_mean_p, "hit_q_mean_p/F");
            tree->Branch("hit_q_std_p", &m_vars.hit_q_std_p, "hit_q_std_p/F");

            if (isPair) {
                // Delayed calib branches.
                tree->Branch("nFired_d", &m_vars.nFired_d, "nFired_d/I");
                tree->Branch("totalPE_d", &m_vars.totalPE_d, "totalPE_d/F");
                tree->Branch("max_pmt_PE_d", &m_vars.max_pmt_PE_d, "max_pmt_PE_d/F");
                tree->Branch("second_max_pmt_PE_d", &m_vars.second_max_pmt_PE_d, "second_max_pmt_PE_d/F");
                tree->Branch("charge_ratio_d", &m_vars.charge_ratio_d, "charge_ratio_d/F");
                tree->Branch("is_flasher_d", &m_vars.is_flasher_d, "is_flasher_d/O");
                tree->Branch("is_lowEMuon_d", &m_vars.is_lowEMuon_d, "is_lowEMuon_d/O");
                tree->Branch("ntq_mean_d", &m_vars.ntq_mean_d, "ntq_mean_d/F");
                tree->Branch("ntq_std_d", &m_vars.ntq_std_d, "ntq_std_d/F");
                tree->Branch("hit_t_mean_d", &m_vars.hit_t_mean_d, "hit_t_mean_d/F");
                tree->Branch("hit_t_std_d", &m_vars.hit_t_std_d, "hit_t_std_d/F");
                tree->Branch("hit_q_mean_d", &m_vars.hit_q_mean_d, "hit_q_mean_d/F");
                tree->Branch("hit_q_std_d", &m_vars.hit_q_std_d, "hit_q_std_d/F");
            }
        }
        
        // --- Accidental shift metadata ---
        tree->Branch("acc_shift_t", &m_vars.acc_shift_t, "acc_shift_t/L");
        tree->Branch("acc_shift_x", &m_vars.acc_shift_x, "acc_shift_x/D");
        tree->Branch("acc_shift_y", &m_vars.acc_shift_y, "acc_shift_y/D");
        tree->Branch("acc_shift_z", &m_vars.acc_shift_z, "acc_shift_z/D");
        
        m_initialized[key] = true;
    }

    // Fill a prompt-delayed pair entry.
    // For accidental pairs, t_off and s_off are applied to the prompt
    // candidate to shift it in time and space relative to the delayed.
    void OutputManager::fillPair(const std::string& treeName, const Candidate& p, const Candidate& d, 
                      const MuonManager* mm, int64_t t_off, const TVector3& s_off, bool /*isAcc*/) {
        
        auto it = m_trees.find(treeName);
        if (it == m_trees.end() || !it->second) return;
        TTree* tree = it->second;
        
        ensureBranches(tree, true);
        m_vars.reset();
        
        // Apply accidental offsets to the prompt candidate.
        int64_t tp_eff = p.time + t_off;
        TVector3 pos_eff = p.pos + s_off;
        
        // Prompt kinematics.
        m_vars.t_p = tp_eff;
        m_vars.E_p = p.energy;
        m_vars.x_p = pos_eff.X();
        m_vars.y_p = pos_eff.Y();
        m_vars.z_p = pos_eff.Z();
        
        // Prompt tags: convert the tagCounts vector to a list of active IDs.
        m_vars.tags_p.clear();
        for (size_t i = 0; i < p.tagCounts.size(); ++i) {
            if (p.tagCounts[i] > 0) m_vars.tags_p.push_back(i);
        }

        // Delayed kinematics.
        m_vars.t_d = d.time;
        m_vars.E_d = d.energy;
        m_vars.x_d = d.pos.X();
        m_vars.y_d = d.pos.Y();
        m_vars.z_d = d.pos.Z();
        
        m_vars.tags_d.clear();
        for (size_t i = 0; i < d.tagCounts.size(); ++i) {
            if (d.tagCounts[i] > 0) m_vars.tags_d.push_back(i);
        }
        
        // Pair separation.
        m_vars.dt = (double)(d.time - tp_eff);
        m_vars.dr = (d.pos - pos_eff).Mag();
        
        // Accidental shift metadata.
        m_vars.acc_shift_t = t_off;
        m_vars.acc_shift_x = s_off.X();
        m_vars.acc_shift_y = s_off.Y();
        m_vars.acc_shift_z = s_off.Z();
        
        // Muon proximity: use the ORIGINAL (unshifted) prompt position
        // and time for muon lookups — the shift is for pair kinematics only.
        if (mm) {
            m_vars.dt_mu = mm->dtToPrevMuon(p.time);
            m_vars.dist_mu = mm->distToPrevMuon(p.time, p.pos);

            auto byTime = mm->closestMuonByTime(p.time, p.pos);
            m_vars.dt_mu_time = byTime.dt;
            m_vars.dist_track_time = byTime.dist_track;
            m_vars.ntracks_time = byTime.ntracks;

            auto byDist = mm->closestMuonByDist(p.time, p.pos);
            m_vars.dt_mu_dist = byDist.dt;
            m_vars.dist_track_dist = byDist.dist_track;
            m_vars.ntracks_dist = byDist.ntracks;
        }

        // Prompt CalibStats.
        {
            const auto& c = p.calib;
            m_vars.nFired_p = c.nFired;
            m_vars.totalPE_p = c.totalPE;
            m_vars.max_pmt_PE_p = c.max_pmt_PE;
            m_vars.second_max_pmt_PE_p = c.second_max_pmt_PE;
            m_vars.charge_ratio_p = c.charge_ratio;
            m_vars.is_flasher_p = c.is_flasher;
            m_vars.is_lowEMuon_p = c.is_lowEMuon;
            m_vars.ntq_mean_p = c.ntq_mean;
            m_vars.ntq_std_p = c.ntq_std;
            m_vars.hit_t_mean_p = c.hit_t_mean;
            m_vars.hit_t_std_p = c.hit_t_std;
            m_vars.hit_q_mean_p = c.hit_q_mean;
            m_vars.hit_q_std_p = c.hit_q_std;
        }

        // Isolation counters (from Candidate::isolation, set by StandardPairRule).
        m_vars.iso_before = p.isolation.iso_before;
        m_vars.iso_between = p.isolation.iso_between;
        m_vars.iso_after = p.isolation.iso_after;

        // Delayed CalibStats.
        {
            const auto& c = d.calib;
            m_vars.nFired_d = c.nFired;
            m_vars.totalPE_d = c.totalPE;
            m_vars.max_pmt_PE_d = c.max_pmt_PE;
            m_vars.second_max_pmt_PE_d = c.second_max_pmt_PE;
            m_vars.charge_ratio_d = c.charge_ratio;
            m_vars.is_flasher_d = c.is_flasher;
            m_vars.is_lowEMuon_d = c.is_lowEMuon;
            m_vars.ntq_mean_d = c.ntq_mean;
            m_vars.ntq_std_d = c.ntq_std;
            m_vars.hit_t_mean_d = c.hit_t_mean;
            m_vars.hit_t_std_d = c.hit_t_std;
            m_vars.hit_q_mean_d = c.hit_q_mean;
            m_vars.hit_q_std_d = c.hit_q_std;
        }
        
        tree->Fill();
    }
    
    // Fill a single-event entry (used by CategoryTagRule for diagnostics).
    // Uses only the prompt-side branches.
    void OutputManager::fillSingle(const std::string& treeName, const Candidate& c, const MuonManager* mm) {
        auto it = m_trees.find(treeName);
        if (it == m_trees.end() || !it->second) return;
        TTree* tree = it->second;
        
        ensureBranches(tree, false);
        m_vars.reset();
        
        m_vars.t_p = c.time;
        m_vars.E_p = c.energy;
        m_vars.x_p = c.pos.X();
        m_vars.y_p = c.pos.Y();
        m_vars.z_p = c.pos.Z();
        m_vars.tags_p.clear();
        for (size_t i = 0; i < c.tagCounts.size(); ++i) {
            if (c.tagCounts[i] > 0) m_vars.tags_p.push_back(i);
        }
        
        if (mm) {
            m_vars.dt_mu = mm->dtToPrevMuon(c.time);
            m_vars.dist_mu = mm->distToPrevMuon(c.time, c.pos);
        }
        
        // CalibStats.
        {
            const auto& cs = c.calib;
            m_vars.nFired_p = cs.nFired;
            m_vars.totalPE_p = cs.totalPE;
            m_vars.max_pmt_PE_p = cs.max_pmt_PE;
            m_vars.second_max_pmt_PE_p = cs.second_max_pmt_PE;
            m_vars.charge_ratio_p = cs.charge_ratio;
            m_vars.is_flasher_p = cs.is_flasher;
            m_vars.is_lowEMuon_p = cs.is_lowEMuon;
            m_vars.ntq_mean_p = cs.ntq_mean;
            m_vars.ntq_std_p = cs.ntq_std;
            m_vars.hit_t_mean_p = cs.hit_t_mean;
            m_vars.hit_t_std_p = cs.hit_t_std;
            m_vars.hit_q_mean_p = cs.hit_q_mean;
            m_vars.hit_q_std_p = cs.hit_q_std;
        }

        tree->Fill();
    }

}

// Metadata persistence (saveConfig, saveTagMap) is implemented in a
// separate translation unit section because it depends on TFile,
// TObjString, and TMap headers that are not needed by the fill logic.

#include "OutputManager.h"
#include "TFile.h"
#include "OutputManager.h"
#include "TFile.h"
#include "TTree.h"

namespace Orsa {

    // Write the configuration and tag map to a "UserMetadata" TTree.
    // This allows them to be read as native dictionaries in uproot (via TTree::arrays).
    void OutputManager::saveMetadata(const std::string& config, const std::map<std::string, int>& tagMap) {
        TFile* f = nullptr;
        if (m_defaultTree) {
            f = m_defaultTree->GetCurrentFile();
        } else if (!m_trees.empty()) {
            for (auto const& [name, tree] : m_trees) {
                if (tree && tree->GetCurrentFile()) {
                    f = tree->GetCurrentFile();
                    break;
                }
            }
        }
        
        if (!f) return;
        
        f->cd();
        TTree* meta = new TTree("UserMetadata", "User Metadata");
        
        // We need local copies to bind the branches.
        std::string configCopy = config;
        std::map<std::string, int> tagMapCopy = tagMap;
        
        meta->Branch("ProductionConfig", &configCopy);
        meta->Branch("TagMap", &tagMapCopy);
        
        meta->Fill();
        meta->Write();
        meta->ResetBranchAddresses(); // Disconnect from stack variables
        // The TTree is now owned by the file.
    }

}
