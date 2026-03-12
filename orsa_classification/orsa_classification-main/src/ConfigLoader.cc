// ConfigLoader.cc
//
// ConfigLoader.cc
//
// Implements the foundational deterministic interpretation algorithm transforming
// external parameterization arrays into integrated logical topologies defining
// analysis hierarchies. The module directs dual structural pathways encompassing
// isolated event classification configuration and comprehensive multi-dimensional
// temporal correlation assembly.
//
// The recursive interpretation methodology successfully processes both simplistic
// linear limit constraints and intricate branched boolean combinatorics dynamically.
// Furthermore, string-based dispatching directly instantiates explicit mathematical
// rule constructs varying from basic spatial coincidences to long-baseline tracking
// architectures based strictly on runtime configuration inputs. Execution inherently
// normalizes memory allocation retention boundaries optimally across aggregated
// rule requirements.

#include "ConfigLoader.h"
#include "SniperKernel/SniperJSON.h"
#include "SniperKernel/SniperLog.h"
#include "CorrelationRules.h"
#include "IsolationBurstRule.h"
#include <fstream>
#include <iostream>

namespace Orsa {

    ConfigLoader::ConfigLoader() {}
    ConfigLoader::~ConfigLoader() {}

    bool ConfigLoader::load(const std::string& jsonPath, 
                            std::vector<std::shared_ptr<Selector>>& selectors,
                            std::shared_ptr<CorrelationEngine> engine,
                            std::shared_ptr<TagRegistry> registry) 
    {
        std::ifstream ifs(jsonPath);
        if (!ifs.good()) {
            LogError << "Failed to open config file: " << jsonPath << std::endl;
            return false;
        }
        
        SniperJSON root = SniperJSON::load(ifs);
        
        // --- Parse event categories (single-event tag definitions) ---
        // Each category defines a set of cuts; events passing all cuts
        // receive the category's tag.
        auto categories = root.find("Categories");
        if (categories != root.map_end()) {
             const SniperJSON& catList = categories->second;
             for (auto it = catList.map_begin(); it != catList.map_end(); ++it) {
                 const SniperJSON& catNode = it->second;
                 auto sel = parseCategory((void*)&catNode, registry);
                 if (sel) selectors.push_back(sel);
             }
        }

        // --- Parse correlation rules ---
        // Rules are evaluated in the order they appear in the JSON.
        // The engine's window is set to the maximum lookback required
        // by any StandardPairRule (including accidental windows).
        auto rules = root.find("Rules");
        int64_t maxReqWindow = 1000000000LL; // default 1 s
        
        if (rules != root.map_end()) {
            const SniperJSON& ruleNodeList = rules->second;
            if (ruleNodeList.isVector()) {
                // Array format: rules are ordered, names come from "name" fields.
                for (auto it = ruleNodeList.vec_begin(); it != ruleNodeList.vec_end(); ++it) {
                    auto rule = parseRule((void*)&(*it), registry, engine->getOutputManager());
                    if (rule) {
                        engine->addRule(rule);
                        // Track the largest window needed for proper sizing.
                        auto spPair = std::dynamic_pointer_cast<StandardPairRule>(rule);
                        if (spPair && spPair->maxNeededWindow() > maxReqWindow) maxReqWindow = spPair->maxNeededWindow();
                        auto picker = std::dynamic_pointer_cast<TimeWindowPickerRule>(rule);
                        if (picker && picker->maxNeededWindow() > maxReqWindow) maxReqWindow = picker->maxNeededWindow();
                    }
                }
            } else {
                // Map format: rule names come from the map keys.
                for (auto it = ruleNodeList.map_begin(); it != ruleNodeList.map_end(); ++it) {
                    auto rule = parseRule((void*)&it->second, registry, engine->getOutputManager(), it->first);
                    if (rule) {
                        engine->addRule(rule);
                        auto spPair = std::dynamic_pointer_cast<StandardPairRule>(rule);
                        if (spPair && spPair->maxNeededWindow() > maxReqWindow) maxReqWindow = spPair->maxNeededWindow();
                        auto picker = std::dynamic_pointer_cast<TimeWindowPickerRule>(rule);
                        if (picker && picker->maxNeededWindow() > maxReqWindow) maxReqWindow = picker->maxNeededWindow();

                    }
                }
            }
        }
        
        engine->setWindow(maxReqWindow);
        return true;
    }

    // Parse a recursive selector definition used inside "logic" blocks.
    // Supports AND, OR, NOT, Range, and Coincidence node types.
    // This allows arbitrarily nested boolean logic for category definitions.
    std::shared_ptr<Selector> ConfigLoader::parseSelector(void* nodePtr, const std::string& namePrfx, std::shared_ptr<TagRegistry> reg, const std::string& defaultSource) {
        const SniperJSON& node = *(const SniperJSON*)nodePtr;
        std::string type = "AND"; 
        if (node.find("type") != node.map_end()) type = node["type"].get<std::string>();
        
        std::shared_ptr<Selector> res = nullptr;
        if (type == "AND" || type == "OR") {
            CompositeSelector::Op op = (type == "AND") ? CompositeSelector::AND : CompositeSelector::OR;
            auto comp = std::make_shared<CompositeSelector>(namePrfx + "_" + type, op);
            
            if (node.find("children") != node.map_end()) {
                const SniperJSON& children = node["children"];
                int idx = 0;
                for (auto it = children.vec_begin(); it != children.vec_end(); ++it) {
                     auto child = parseSelector((void*)&(*it), namePrfx + "_" + std::to_string(idx++), reg, defaultSource);
                     if (child) comp->add(child);
                }
            }
            return comp;
        } 
        else if (type == "NOT") {
            if (node.find("child") != node.map_end()) {
                auto child = parseSelector((void*)&node["child"], namePrfx + "_NOT", reg, defaultSource);
                if (child) res = std::make_shared<NotSelector>(namePrfx + "_NOT", child);
            }
        }
        else if (type == "Range") {
            // Build a RangeSelector for a named variable with min/max bounds.
            std::string var = "";
            if (node.find("variable") != node.map_end()) var = node["variable"].get<std::string>();
            else if (node.find("var") != node.map_end()) var = node["var"].get<std::string>();
            double min = -1e20;
            if (node.find("min") != node.map_end()) min = node["min"].get<double>();
            double max = 1e20;
            if (node.find("max") != node.map_end()) max = node["max"].get<double>();
            
            std::string src = defaultSource;
            if (node.find("source") != node.map_end()) src = node["source"].get<std::string>();

            // Map variable name to the appropriate EventWrapper accessor.
            if (var == "energy") {
                res = std::make_shared<RangeSelector>(namePrfx + "_E", 
                    [](const EventWrapper& e, const std::string& s){ return e.getEnergy(s); }, min, max, src);
            } else if (var == "charge") {
                res = std::make_shared<RangeSelector>(namePrfx + "_Q", 
                    [](const EventWrapper& e, const std::string& /*s*/){ return e.getCharge(); }, min, max, src);
            } else if (var == "detector") {
                 std::string detStr = "";
                 if (node.find("det_name") != node.map_end()) detStr = node["det_name"].get<std::string>();
                 int detID = 0;
                 if (detStr == "CD") detID = 1;
                 else if (detStr == "WP" || detStr == "WT") detID = 2;
                 else if (detStr == "TT" || detStr == "TVT") detID = 4;
                 // Use a narrow range around the integer ID to emulate equality.
                 res = std::make_shared<RangeSelector>(namePrfx + "_Det", 
                        [](const EventWrapper& e, const std::string& /*s*/){ return (double)e.getDetectorType(); }, 
                        (double)detID - 0.1, (double)detID + 0.1, src);
            } else if (var == "radius") {
                  res = std::make_shared<RangeSelector>(namePrfx + "_R", 
                      [](const EventWrapper& e, const std::string& s){ return e.getPos(s).Mag(); }, min, max, src);
            } else if (var == "nfired") {
                  res = std::make_shared<RangeSelector>(namePrfx + "_NFired", 
                      [](const EventWrapper& e, const std::string& s){ return (double)e.getNFired(s); }, min, max, src);
            } else if (var == "dt_prev") {
                  res = std::make_shared<RangeSelector>(namePrfx + "_DTPrev", 
                      [](const EventWrapper& e, const std::string& /*s*/){ return e.getDTPrev(); }, min, max, src);
            } else if (var == "hit_t_std" || var == "sigma_t") {
                  res = std::make_shared<RangeSelector>(namePrfx + "_HitTStd", 
                      [](const EventWrapper& e, const std::string& /*s*/){ return e.getCalibStats().hit_t_std; }, min, max, src);
            } else if (var == "hit_t_mean") {
                  res = std::make_shared<RangeSelector>(namePrfx + "_HitTMean", 
                      [](const EventWrapper& e, const std::string& /*s*/){ return e.getCalibStats().hit_t_mean; }, min, max, src);
            }
        }
        else if (type == "Coincidence") {
             std::string target = node["target_det"].get<std::string>();
             int tDet = (target == "CD") ? 1 : (target == "WP" ? 2 : 0);
             double dt_min = node["dt_min"].get<double>();
             double dt_max = node["dt_max"].get<double>();
             double minQ = 0;
             if (node.find("min_q") != node.map_end()) minQ = node["min_q"].get<double>();
             
             res = std::make_shared<CoincidenceSelector>(namePrfx + "_Coinc", tDet, dt_min, dt_max, minQ);
        }
        
        return res;
    }

    // Parse a single category from the "Categories" section.
    // Two formats are supported:
    //   1. A "logic" block containing a recursive selector tree.
    //   2. A flat "cuts" block where each recognized key (energy_min,
    //      radius_max, detector, nfired_min, etc.) becomes a RangeSelector
    //      in an implicit AND-composite.
    std::shared_ptr<Selector> ConfigLoader::parseCategory(void* nodePtr, std::shared_ptr<TagRegistry> reg) {
        const SniperJSON& node = *(const SniperJSON*)nodePtr;
        std::string name = "unknown";
        if (node.find("name") != node.map_end()) name = node["name"].get<std::string>();
        int id = reg->getID(name);

        std::string source = "default";
        if (node.find("reco_source") != node.map_end()) {
            source = node["reco_source"].get<std::string>();
        }

        // Recursive "logic" block: delegate to parseSelector().
        if (node.find("logic") != node.map_end()) {
             const SniperJSON& logic = node["logic"];
             auto sel = parseSelector((void*)&logic, name, reg, source);
             if (sel) sel->setTagID(id);
             return sel;
        }

        // Flat "cuts" block: build an AND-composite from recognized keys.
        auto comp = std::make_shared<CompositeSelector>(name, CompositeSelector::AND);
        comp->setTagID(id);

        auto cuts = node.find("cuts");
        if (cuts != node.map_end()) {
            const SniperJSON& c = cuts->second;
            
            // Energy window [MeV].
            if (c.find("energy_min") != c.map_end() || c.find("energy_max") != c.map_end()) {
                double min = -1e20;
                if (c.find("energy_min") != c.map_end()) min = c["energy_min"].get<double>();
                double max = 1e20;
                if (c.find("energy_max") != c.map_end()) max = c["energy_max"].get<double>();
                
                comp->add(std::make_shared<RangeSelector>(name + "_E", 
                    [](const EventWrapper& e, const std::string& s){ return e.getEnergy(s); }, min, max, source));
            }
            // Charge window [photoelectrons].
            if (c.find("charge_min") != c.map_end()) {
                 double min = c["charge_min"].get<double>();
                 double max = 1e20;
                 if (c.find("charge_max") != c.map_end()) max = c["charge_max"].get<double>();
                 
                 comp->add(std::make_shared<RangeSelector>(name + "_Q", 
                    [](const EventWrapper& e, const std::string& /*s*/){ return e.getCharge(); }, min, max, source));
            }

            // Detector type (CD / WP / WT / TT / TVT).
            if (c.find("detector") != c.map_end()) {
                std::string det = c["detector"].get<std::string>();
                int detID = 0;
                if (det == "CD") detID = 1; 
                else if (det == "WP" || det == "WT") detID = 2; 
                else if (det == "TT" || det == "TVT") detID = 4;
                if (detID > 0) {
                     comp->add(std::make_shared<RangeSelector>(name + "_Det",
                        [](const EventWrapper& e, const std::string& /*s*/){ return (double)e.getDetectorType(); }, 
                        (double)detID - 0.1, (double)detID + 0.1, source)); 
                }
            }
            // Fiducial radius [mm].
            if (c.find("radius_max") != c.map_end()) {
                double max = c["radius_max"].get<double>();
                comp->add(std::make_shared<RangeSelector>(name + "_R", 
                    [](const EventWrapper& e, const std::string& s){ return e.getPos(s).Mag(); }, -1e20, max, source));
            }
            // Channel multiplicity (fired PMTs).
            if (c.find("nfired_min") != c.map_end() || c.find("nfired_max") != c.map_end()) {
                double min = -1e20;
                if (c.find("nfired_min") != c.map_end()) min = c["nfired_min"].get<double>();
                double max = 1e20;
                if (c.find("nfired_max") != c.map_end()) max = c["nfired_max"].get<double>();
                
                comp->add(std::make_shared<RangeSelector>(name + "_NFired", 
                    [](const EventWrapper& e, const std::string& s){ return (double)e.getNFired(s); }, min, max, source));
            }
            // FEC multiplicity (fired Modules).
            if (c.find("nfecs_min") != c.map_end() || c.find("nfecs_max") != c.map_end()) {
                double min = -1e20;
                if (c.find("nfecs_min") != c.map_end()) min = c["nfecs_min"].get<double>();
                double max = 1e20;
                if (c.find("nfecs_max") != c.map_end()) max = c["nfecs_max"].get<double>();
                
                comp->add(std::make_shared<RangeSelector>(name + "_NFECs", 
                    [](const EventWrapper& e, const std::string& s){ return (double)e.getNFECs(s); }, min, max, source));
            }
            // Hit time standard deviation ("hit_t_std") [ns]
            if (c.find("hit_t_std_min") != c.map_end() || c.find("hit_t_std_max") != c.map_end()) {
                double min = (c.find("hit_t_std_min") != c.map_end()) ? c["hit_t_std_min"].get<double>() : -1e20;
                double max = (c.find("hit_t_std_max") != c.map_end()) ? c["hit_t_std_max"].get<double>() : 1e20;
                comp->add(std::make_shared<RangeSelector>(name + "_HitTStd", 
                     [](const EventWrapper& e, const std::string& /*s*/){ return (double)e.getCalibStats().hit_t_std; }, min, max, source));
            }

            // Hit time mean ("hit_t_mean") [ns]
            if (c.find("hit_t_mean_min") != c.map_end() || c.find("hit_t_mean_max") != c.map_end()) {
                double min = (c.find("hit_t_mean_min") != c.map_end()) ? c["hit_t_mean_min"].get<double>() : -1e20;
                double max = (c.find("hit_t_mean_max") != c.map_end()) ? c["hit_t_mean_max"].get<double>() : 1e20;
                comp->add(std::make_shared<RangeSelector>(name + "_HitTMean", 
                     [](const EventWrapper& e, const std::string& /*s*/){ return (double)e.getCalibStats().hit_t_mean; }, min, max, source));
            }
        }
        return comp;
    }

    // Parse a single correlation rule from the "Rules" section.
    // Dispatches on the "type" field to construct the appropriate rule.
    std::shared_ptr<CorrelationRule> ConfigLoader::parseRule(void* nodePtr, std::shared_ptr<TagRegistry> reg, std::shared_ptr<OutputManager> om, const std::string& fallbackName) {
        const SniperJSON& node = *(const SniperJSON*)nodePtr;
        if (node.find("type") == node.map_end()) return nullptr;
        std::string type = node["type"].get<std::string>();

        std::string name = fallbackName;
        if (node.find("name") != node.map_end()) {
            name = node["name"].get<std::string>();
        }
        
        if (name.empty()) {
            LogWarn << "Rule of type '" << type << "' has no name, skipping." << std::endl;
            return nullptr;
        }
 
        LogDebug << "Parsing rule: " << name << " of type " << type << std::endl;
        std::shared_ptr<CorrelationRule> rule = nullptr;

        // --- Compound rules (OR / AND of sub-rules) ---
        if (type == "OR" || type == "AND" || type == "Compound") {
            if (node.find("children") == node.map_end()) {
                LogWarn << "Compound rule '" << name << "' has no children, skipping." << std::endl;
                return nullptr;
            }
            const SniperJSON& children = node["children"];
            std::vector<std::shared_ptr<CorrelationRule>> subRules;
            for (auto it = children.vec_begin(); it != children.vec_end(); ++it) {
                if (it->isScalar()) {
                    // String child: treat as a category name lookup.
                    std::string catName = it->get<std::string>();
                    subRules.push_back(std::make_shared<CategoryTagRule>(catName, reg->getID(catName), -1));
                } else {
                    // Object child: recursively parse as a rule.
                    auto child = parseRule((void*)&(*it), reg, om);
                    if (child) subRules.push_back(child);
                }
            }
            if (subRules.empty()) return nullptr;

            bool isOR = (type == "OR");
            if (type == "Compound") {
                if (node.find("operation") != node.map_end()) {
                    std::string op = node["operation"].get<std::string>();
                    isOR = (op == "OR");
                }
            }
            
            int rTag = -1;
            if (node.find("result_tag") != node.map_end()) {
                rTag = reg->getID(node["result_tag"].get<std::string>());
            }

            auto compoundRule = std::make_shared<CompoundRule>(name, std::move(subRules), isOR, rTag);
            rule = compoundRule;

        // --- Pair rule (delayed coincidence / IBD search) ---
        } else if (type == "Pair") {
            if (node.find("prompt") == node.map_end() || node.find("delayed") == node.map_end()) return nullptr;
            std::string pTagStr = node["prompt"].get<std::string>();
            std::string dTagStr = node["delayed"].get<std::string>();
            int64_t dt_min = 0;
            if (node.find("dt_min") != node.map_end()) dt_min = (int64_t)node["dt_min"].get<double>();
            int64_t dt_max = 1000000;
            if (node.find("dt_max") != node.map_end()) dt_max = (int64_t)node["dt_max"].get<double>();
            double dr_max = 5000.0;
            if (node.find("dr_max") != node.map_end()) dr_max = node["dr_max"].get<double>();
            
            int pTag = reg->getID(pTagStr);
            int dTag = reg->getID(dTagStr);

            int newTag = -1;
            if (node.find("new_tag") != node.map_end()) newTag = reg->getID(node["new_tag"].get<std::string>());

            // Isolation configuration: defines which tag to count and the
            // time windows before/after the pair for isolation counters.
            int isoTag = -1;
            int64_t iso_window_before = 1000000; 
            int64_t iso_window_after = 1000000;
            int iso_before_max = -1;
            int iso_between_max = -1;
            int iso_after_max = -1;
            
            auto isoNode = node.find("isolation");
            if (isoNode != node.map_end()) {
                const SniperJSON& iso = isoNode->second;
                if (iso.find("tag") != iso.map_end()) isoTag = reg->getID(iso["tag"].get<std::string>());
                if (iso.find("window_before") != iso.map_end()) iso_window_before = (int64_t)iso["window_before"].get<double>();
                if (iso.find("window_after") != iso.map_end()) iso_window_after = (int64_t)iso["window_after"].get<double>();
                if (iso.find("iso_before_max") != iso.map_end()) iso_before_max = iso["iso_before_max"].get<int>();
                if (iso.find("iso_between_max") != iso.map_end()) iso_between_max = iso["iso_between_max"].get<int>();
                if (iso.find("iso_after_max") != iso.map_end()) iso_after_max = iso["iso_after_max"].get<int>();
            }

            // Global and per-leg tag requirements.
            int requiresTag = -1;
            bool negateRequiresTag = false;
            if (node.find("requires_tag") != node.map_end()) requiresTag = reg->getID(node["requires_tag"].get<std::string>());
            if (node.find("requires_tag_negate") != node.map_end()) negateRequiresTag = node["requires_tag_negate"].get<bool>();

            int reqTagPrompt = -1;
            bool negReqTagPrompt = false;
            if (node.find("requires_tag_prompt") != node.map_end()) reqTagPrompt = reg->getID(node["requires_tag_prompt"].get<std::string>());
            if (node.find("requires_tag_prompt_negate") != node.map_end()) negReqTagPrompt = node["requires_tag_prompt_negate"].get<bool>();

            int reqTagDelayed = -1;
            bool negReqTagDelayed = false;
            if (node.find("requires_tag_delayed") != node.map_end()) reqTagDelayed = reg->getID(node["requires_tag_delayed"].get<std::string>());
            if (node.find("requires_tag_delayed_negate") != node.map_end()) negReqTagDelayed = node["requires_tag_delayed_negate"].get<bool>();


            rule = std::make_shared<StandardPairRule>(name, pTag, dTag, dt_min, dt_max, dr_max, 
                                                           newTag, isoTag, iso_window_before, iso_window_after, 
                                                           requiresTag, negateRequiresTag,
                                                           reqTagPrompt, negReqTagPrompt,
                                                           reqTagDelayed, negReqTagDelayed,
                                                           iso_before_max, iso_between_max, iso_after_max);

            if (node.find("acc_n_windows") != node.map_end()) {
                int n_win = node["acc_n_windows"].get<int>();
                TVector3 off(0,0,0);
                int64_t shift = 0;
                if (node.find("acc_window_shift") != node.map_end()) shift = (int64_t)node["acc_window_shift"].get<double>();
                
                if (node.find("acc_offset") != node.map_end()) {
                    const SniperJSON& vecNode = node["acc_offset"];
                    std::vector<double> vals;
                    for (auto it = vecNode.vec_begin(); it != vecNode.vec_end(); ++it) {
                        vals.push_back(it->get<double>());
                    }
                    if (vals.size() >= 3) {
                        off.SetXYZ(vals[0], vals[1], vals[2]);
                    }
                }

                auto spRule = std::dynamic_pointer_cast<StandardPairRule>(rule);
                if (spRule) spRule->setAccidentalConfig(n_win, shift, off);
            }

        } else if (type == "TimeWindowPicker") {
            double win_before = node["window_before"].get<double>();
            double win_after = node["window_after"].get<double>();

            std::vector<int64_t> timestamps;
            if (node.find("timestamp_file") != node.map_end()) {
                std::string path = node["timestamp_file"].get<std::string>();
                std::ifstream ifs(path);
                if (ifs.is_open()) {
                    int64_t ts;
                    while (ifs >> ts) {
                        timestamps.push_back(ts);
                    }
                } else {
                    LogError << "Could not open timestamp file: " << path << std::endl;
                }
            }
            std::string tkey = (node.find("targets") != node.map_end()) ? "targets" : "timestamps";
            if (node.find(tkey) != node.map_end()) {
                const SniperJSON& arr = node[tkey];
                for (auto it = arr.vec_begin(); it != arr.vec_end(); ++it) {
                    try {
                        if (it->isScalar()) {
                             // Try to get as string first (for LL precision)
                             try {
                                 std::string tsStr = it->get<std::string>();
                                 timestamps.push_back(std::stoll(tsStr));
                             } catch (...) {
                                 // Fallback to double if it's a number
                                 timestamps.push_back((int64_t)it->get<double>());
                             }
                        }
                    } catch (...) {
                        LogError << "Failed to parse timestamp from JSON" << std::endl;
                    }
                }
            }

            auto pickerRule = std::make_shared<TimeWindowPickerRule>(name, timestamps, win_before, win_after);
            rule = pickerRule;


        } else if (type == "IsolationBurst") {

        // --- Muon veto rule ---
        } else if (type == "MuonVeto") {
            int64_t time = 1000000;
            if (node.find("veto_time") != node.map_end()) time = (int64_t)node["veto_time"].get<double>();
            int vetoTag = reg->getID("MuonVetoed"); 
            if (node.find("veto_tag") != node.map_end()) vetoTag = reg->getID(node["veto_tag"].get<std::string>());
            int muonTag = -1;
            if (node.find("muon_tag") != node.map_end()) muonTag = reg->getID(node["muon_tag"].get<std::string>());
            
            // Optional extended veto when the muon produced neutrons.
            int nTagID = -1;
            int64_t vTimeWithN = -1;
            if (node.find("n_tag") != node.map_end()) nTagID = reg->getID(node["n_tag"].get<std::string>());
            if (node.find("veto_time_with_n") != node.map_end()) vTimeWithN = (int64_t)node["veto_time_with_n"].get<double>();

            rule = std::make_shared<MuonVetoRule>(name, time, vetoTag, muonTag, nTagID, vTimeWithN);

        // --- Muon-neutron tagging (retroactive muon classification) ---
        } else if (type == "MuonNeutron") {
            if (node.find("muon_tag") == node.map_end() || node.find("neutron_tag") == node.map_end() || node.find("result_tag") == node.map_end()) return nullptr;
            int mID = reg->getID(node["muon_tag"].get<std::string>());
            int nID = reg->getID(node["neutron_tag"].get<std::string>());
            int64_t dtMax = 1000000;
            if (node.find("dt_max") != node.map_end()) dtMax = (int64_t)node["dt_max"].get<double>();
            int resID = reg->getID(node["result_tag"].get<std::string>());
            rule = std::make_shared<MuonNeutronRule>(name, mID, nID, dtMax, resID);

        // --- Spallation correlation (time + space to muon) ---
        } else if (type == "Spallation") {
             int64_t time = 1000000;
             if (node.find("time_window") != node.map_end()) time = (int64_t)node["time_window"].get<double>();
             double rad = 5000.0;
             if (node.find("radius") != node.map_end()) rad = node["radius"].get<double>();
             int sTag = reg->getID("SpallationMuon");
             int tTag = -1;
             if (node.find("target_tag") != node.map_end()) tTag = reg->getID(node["target_tag"].get<std::string>());
             if (node.find("new_tag") != node.map_end()) sTag = reg->getID(node["new_tag"].get<std::string>());
             
             rule = std::make_shared<SpallationRule>(name, time, rad, sTag, tTag);

        // --- Generalized spatial veto (e.g. Neutron Veto) ---
        } else if (type == "SpatialVeto") {
             int64_t time = 1200000000; // default 1.2s
             if (node.find("time_window") != node.map_end()) time = (int64_t)node["time_window"].get<double>();
             double rad = 4000.0;
             if (node.find("radius") != node.map_end()) rad = node["radius"].get<double>();
             int vTag = reg->getID("SpatialVetoed");
             if (node.find("veto_tag") != node.map_end()) vTag = reg->getID(node["veto_tag"].get<std::string>());
             int tTag = -1;
             if (node.find("target_tag") != node.map_end()) tTag = reg->getID(node["target_tag"].get<std::string>());
             
             rule = std::make_shared<SpatialVetoRule>(name, time, rad, vTag, tTag);

        // --- Long-term history lookup (cosmogenic isotopes) ---
        } else if (type == "LongHistory" || type == "Triple") {
             if ((node.find("current_tag") == node.map_end() && node.find("candidate_tag") == node.map_end()) || 
                 node.find("history_tag") == node.map_end()) return nullptr;
             
             std::string candTag = "";
             if (node.find("candidate_tag") != node.map_end()) candTag = node["candidate_tag"].get<std::string>();
             else candTag = node["current_tag"].get<std::string>();

             std::string histTag = node["history_tag"].get<std::string>();
             int resTag = reg->getID("Triple_Coincidence");
             
             if (node.find("result_tag") != node.map_end()) resTag = reg->getID(node["result_tag"].get<std::string>());
             else if (node.find("new_tag") != node.map_end()) resTag = reg->getID(node["new_tag"].get<std::string>());
             
             int64_t minWin = 0;
             if (node.find("min_window") != node.map_end()) minWin = (int64_t)node["min_window"].get<double>();
             else if (node.find("dt_min") != node.map_end()) minWin = (int64_t)node["dt_min"].get<double>();
             
             int64_t maxWin = 1000000;
             if (node.find("max_window") != node.map_end()) maxWin = (int64_t)node["max_window"].get<double>();
             else if (node.find("dt_max") != node.map_end()) maxWin = (int64_t)node["dt_max"].get<double>();
             
             double radius = 5000.0;
             if (node.find("radius") != node.map_end()) radius = node["radius"].get<double>();
             else if (node.find("dr_max") != node.map_end()) radius = node["dr_max"].get<double>();
             
             rule = std::make_shared<LongHistoryRule>(name, reg->getID(candTag), reg->getID(histTag), minWin, maxWin, radius, resTag);
        } else if (type == "Coincidence") {
             if (node.find("tag_1") == node.map_end() || node.find("tag_2") == node.map_end() || node.find("new_tag") == node.map_end()) return nullptr;
             std::string t1Str = node["tag_1"].get<std::string>();
             std::string t2Str = node["tag_2"].get<std::string>();
             std::string nStr = node["new_tag"].get<std::string>();
             double window = 1000.0;
             if (node.find("window") != node.map_end()) window = node["window"].get<double>();
             int64_t w_ns = (int64_t)window; 
             
             rule = std::make_shared<CoincidenceRule>(name, reg->getID(t1Str), reg->getID(t2Str), w_ns, reg->getID(nStr));
        
        // --- Burst / multiplicity cluster detection ---
        } else if (type == "IsolationBurst" || type == "Multiplicity") {
             std::string cTag = node["count_tag"].get<std::string>();
             int minCount = node["min_count"].get<int>();
             double win = node["time_window"].get<double>();
             std::string rTag = node["result_tag"].get<std::string>();
             int64_t w_ns = (int64_t)win;
             rule = std::make_shared<IsolationBurstRule>(name, reg->getID(cTag), minCount, w_ns, reg->getID(rTag));
             
        // --- Data quality / gap detection ---
        } else if (type == "DataQuality") {
             int64_t wpGap = (int64_t)node["wp_gap_threshold"].get<double>();
             int64_t cdGap = (int64_t)node["cd_gap_threshold"].get<double>();
             int64_t dead = (int64_t)node["gap_dead_time"].get<double>();
             bool jobStart = node["job_start_veto"].get<bool>();
             int vTag = reg->getID("DataQualityVetoed");
             
             rule = std::make_shared<DataQualityRule>(name, wpGap, cdGap, dead, jobStart, vTag);

        // --- Post-pairing isolation quality cut ---
        } else if (type == "IsolationQuality") {
             std::string reqTag = node["requires_tag"].get<std::string>();
             std::string newTagStr = node["new_tag"].get<std::string>();
             
             int maxBefore = -1, maxBetween = -1, maxAfter = -1;
             if (node.find("conditions") != node.map_end()) {
                 const SniperJSON& cond = node["conditions"];
                 if (cond.find("iso_before_max") != cond.map_end()) maxBefore = cond["iso_before_max"].get<int>();
                 if (cond.find("iso_between_max") != cond.map_end()) maxBetween = cond["iso_between_max"].get<int>();
                 if (cond.find("iso_after_max") != cond.map_end()) maxAfter = cond["iso_after_max"].get<int>();
             }
             
             rule = std::make_shared<IsolationQualityRule>(name, reg->getID(reqTag), reg->getID(newTagStr), maxBefore, maxBetween, maxAfter);

        // --- Category promotion (single-event tag → rule-level tag) ---
        } else if (type == "Category") {
             std::string catName = node["category"].get<std::string>();
             std::string newTagStr = node["new_tag"].get<std::string>();
             int reqTag = -1;
             bool negate = false;
             if (node.find("requires_tag") != node.map_end()) reqTag = reg->getID(node["requires_tag"].get<std::string>());
             if (node.find("requires_tag_negate") != node.map_end()) negate = node["requires_tag_negate"].get<bool>();
             
             rule = std::make_shared<CategoryTagRule>(name, reg->getID(catName), reg->getID(newTagStr), reqTag, negate);

        } else {
             LogWarn << "Unknown rule type '" << type << "' for rule '" << name << "', skipping." << std::endl;
        }

        // Apply veto tags if configured (common to all rule types).
        if (rule && node.find("vetoes") != node.map_end()) {
             const SniperJSON& vetoList = node["vetoes"];
             if (vetoList.isVector()) {
                 std::vector<int> vetoIDs;
                 for (auto it = vetoList.vec_begin(); it != vetoList.vec_end(); ++it) {
                     std::string vTag = it->get<std::string>();
                     vetoIDs.push_back(reg->getID(vTag));
                 }
                 rule->setVetoTags(vetoIDs);
             }
        }
        
        // Configure output trees for rules that produce output.
        if (node.find("output") != node.map_end() && om) {
            const SniperJSON& outNode = node["output"];
            OutputSettings s;
            if (outNode.find("path") != outNode.map_end()) s.path = outNode["path"].get<std::string>();
            if (outNode.find("save_muon_info") != outNode.map_end()) s.saveMuonInfo = outNode["save_muon_info"].get<bool>();
            if (outNode.find("save_calib_info") != outNode.map_end()) s.saveCalibInfo = outNode["save_calib_info"].get<bool>();
            if (outNode.find("save_tags") != outNode.map_end()) s.saveTags = outNode["save_tags"].get<bool>();
            om->setTreeSettings(name, s);
            
            // Also create settings for the accidental tree if configured.
            OutputSettings sAcc = s;
            if (s.path.length() > 0) sAcc.path = s.path + "_acc"; 
            om->setTreeSettings(name + "_Acc", sAcc);

            auto picker = std::dynamic_pointer_cast<TimeWindowPickerRule>(rule);
            if (picker) {
                picker->registerOutput(om.get());
            } else {
                om->getOrBookTree(name, "Signal Pairs for " + name);
                if (node.find("acc_n_windows") != node.map_end()) {
                    om->getOrBookTree(name + "_Acc", "Accidentals for " + name);
                }
            }
        }
        
        return rule;
    }

}
