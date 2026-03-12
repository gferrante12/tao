#ifndef ORSACLASSIFICATION_CONFIGLOADER_H
#define ORSACLASSIFICATION_CONFIGLOADER_H

// ConfigLoader.h
//
// Interprets a standardized JSON configuration parameterization to systematically
// initialize the analytical framework. The loader constructs Selector instances for
// defined event categories, instantiates CorrelationRule structures for all
// designated analysis chains, and synchronizes the global TagRegistry nomenclature.
// Additionally, it dynamically calibrates the CorrelationEngine's sliding retention
// window to accommodate the most extended historical requirement across all active
// rules, while concurrently configuring the OutputManager schema mapping.
//
// Supported parameterization encompasses both linear condition definitions utilizing
// strict property thresholds (e.g., energy limits, spatial containment) and complex
// recursive logic topologies representing composite boolean operations. Data handling
// is strictly delegated to the integrated SNiPER SniperJSON parser utility.

#include "Selector.h"
#include "CorrelationEngine.h"
#include "CorrelationRules.h"
#include "IsolationBurstRule.h"
#include "TagRegistry.h"
#include "OutputManager.h"
#include <string>
#include <vector>
#include <memory>

class SniperJSON;

namespace Orsa {

    class ConfigLoader {
    public:
        ConfigLoader();
        ~ConfigLoader();

        // Orchestrates the ingestion of the specified JSON parameterization file to
        // populate the isolated single-event Selector criteria array, register structural
        // rules within the centralized CorrelationEngine, and construct the unified global
        // property dictionary in the TagRegistry. A successful boolean return confirms
        // complete syntactic and semantic validity.
        bool load(const std::string& jsonPath,
                  std::vector<std::shared_ptr<Selector>>& selectors,
                  std::shared_ptr<CorrelationEngine> engine,
                  std::shared_ptr<TagRegistry> registry);

    private:
        // Parse a single category block and return the corresponding Selector.
        // Handles flat "cuts" (energy, charge, radius, nFired, detector) and
        // recursive "logic" blocks.
        std::shared_ptr<Selector> parseCategory(void* node, std::shared_ptr<TagRegistry> reg);

        // Parse a recursive selector definition (used inside "logic" blocks).
        // Supports AND, OR, NOT, Range, and Coincidence node types.
        std::shared_ptr<Selector> parseSelector(void* node, const std::string& namePrefix,
                                                 std::shared_ptr<TagRegistry> reg,
                                                 const std::string& defaultSource);

        // Parse a single rule block and return the corresponding CorrelationRule.
        // Dispatches on the "type" field to construct the appropriate rule class.
        // fallbackName is used when the rule node has no explicit "name" field.
        std::shared_ptr<CorrelationRule> parseRule(void* node, std::shared_ptr<TagRegistry> reg,
                                                    std::shared_ptr<OutputManager> om,
                                                    const std::string& fallbackName = "");
    };

}

#endif // ORSACLASSIFICATION_CONFIGLOADER_H
