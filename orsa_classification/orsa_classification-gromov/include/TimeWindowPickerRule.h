#ifndef TIME_WINDOW_PICKER_RULE_H
#define TIME_WINDOW_PICKER_RULE_H

#include "Candidate.h"
#include "CorrelationEngine.h"
#include "OutputManager.h"
#include "TTree.h"
#include <vector>
#include <deque>
#include <list>
#include <string>
#include <algorithm>
#include <iostream>

namespace Orsa {

    // Systematically extracts all sequential occurrences encompassed by a defined
    // asymmetrical temporal boundary [T - window_before, T + window_after] surrounding
    // a predetermined sequence of critical interaction timestamps T.
    class TimeWindowPickerRule : public CorrelationRule {
    public:
        TimeWindowPickerRule(const std::string& name, 
                             const std::vector<int64_t>& timestamps,
                             double window_before, // ns (input as double from config)
                             double window_after)  // ns
            : m_name(name),
              m_targets(timestamps),
              m_active_windows(),
              m_current_target_idx(0),
              m_tree(nullptr)
        {
            // Convert double inputs to int64_t for internal precision
            m_window_before = (int64_t)window_before;
            m_window_after = (int64_t)window_after;
            
            // Ensure targets are sorted for efficient sequential matching
            std::sort(m_targets.begin(), m_targets.end());
        }

        virtual ~TimeWindowPickerRule() {}
        
        virtual bool wantsUntagged(int64_t time) const override {
            // Check if 'time' is within [target - window_before, target + window_after] for any target.
            // Equivalent to: target in [time - window_after, time + window_before]
            int64_t look_min = time - m_window_after;
            int64_t look_max = time + m_window_before;

            auto it = std::lower_bound(m_targets.begin(), m_targets.end(), look_min);
            if (it != m_targets.end()) {
                if (*it <= look_max) return true;
            }
            return false;
        }

        virtual bool check(Candidate& curr, std::deque<Candidate>& window, CorrelationEngine& engine) override {
            (void)engine;
            
            // 1. Check for new triggers
            while (m_current_target_idx < m_targets.size()) {
                int64_t t_target = m_targets[m_current_target_idx];
                
                // Trigger if we reached or passed the target time
                if (curr.time >= t_target) {
                    int id = (int)m_current_target_idx;
                    int64_t t_end = t_target + m_window_after;
                    
                    // Add to active windows
                    m_active_windows.push_back({id, t_end});
                    
                    // Backfill from window (search for events in [t_target - window_before, curr.time))
                    int64_t t_start = t_target - m_window_before;
                    
                    auto it = std::lower_bound(window.begin(), window.end(), t_start, 
                        [](const Candidate& c, int64_t val){ return c.time < val; });
                    
                    for (; it != window.end(); ++it) {
                        const Candidate& past = *it;
                        if (past.time >= t_start && past.time <= t_end) {
                             fillTree(past, id);
                        }
                    }
                    
                    m_current_target_idx++;
                } else {
                    break; // Not reached next target yet
                }
            }
            
            // 2. Check active windows for the CURRENT candidate
            for (auto it = m_active_windows.begin(); it != m_active_windows.end(); ) {
                int id = it->first;
                int64_t t_end = it->second;
                
                if (curr.time <= t_end) {
                    fillTree(curr, id);
                    ++it;
                } else {
                    // Window expired
                    it = m_active_windows.erase(it);
                }
            }
            
            return false; // We don't consume the event
        }

        virtual std::string name() const override { return m_name; }

        // Vital for the engine to know how much history to keep in 'window'
        virtual int64_t maxNeededWindow() const { 
            return m_window_before; 
        }
        
        // Helper to register variables
        void registerOutput(OutputManager* om) {
           m_tree = om->getOrBookTree(m_name, "Picked Events");
           m_tree->Branch("TriggerID", &m_branch_trigger_id, "TriggerID/I");
           m_tree->Branch("EvtID", &m_branch_evt_id, "EvtID/L");
           m_tree->Branch("Time", &m_branch_time, "Time/D");
           m_tree->Branch("Energy", &m_branch_energy, "Energy/D");
           m_tree->Branch("X", &m_branch_x, "X/D");
           m_tree->Branch("Y", &m_branch_y, "Y/D");
           m_tree->Branch("Z", &m_branch_z, "Z/D");
           m_tree->Branch("Det", &m_branch_det, "Det/I");
        }

    private:
       void fillTree(const Candidate& c, int triggerID) {
           if(!m_tree) return;
           m_branch_trigger_id = triggerID;
           m_branch_evt_id = (long long)c.time; 
           m_branch_time = (double)c.time;
           m_branch_energy = c.energy;
           m_branch_x = c.pos.x();
           m_branch_y = c.pos.y();
           m_branch_z = c.pos.z();
           m_branch_det = c.detType;
           m_tree->Fill();
       }

       std::string m_name;
       std::vector<int64_t> m_targets;
       int64_t m_window_before;
       int64_t m_window_after;
       
       std::list<std::pair<int, int64_t>> m_active_windows; // ID, EndTime
       size_t m_current_target_idx;
       
       TTree* m_tree;
       // Branch variables
       int m_branch_trigger_id;
       long long m_branch_evt_id;
       double m_branch_time;
       double m_branch_energy;
       double m_branch_x;
       double m_branch_y;
       double m_branch_z;
       int m_branch_det;
    };
}

#endif
