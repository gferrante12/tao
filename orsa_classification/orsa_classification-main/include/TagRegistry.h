#ifndef ORSACLASSIFICATION_TAGREGISTRY_H
#define ORSACLASSIFICATION_TAGREGISTRY_H

// TagRegistry.h
//
// Establishes a comprehensive, immutable bidirectional mapping bridging descriptive
// human-readable nomenclature strings with highly optimized scalar integer
// identifiers. This centralized dictionary allocates numeric indices monotonically,
// structurally enforcing deterministic O(1) constant-time query complexity during
// all subsequent candidate property evaluations.
//
// Furthermore, the registry silently integrates cumulative categorization statistics,
// aggregating definitive population metrics across all identified phenomenological
// classes for rigorous validation during the execution termination phase.
// Synchronized parallel access is inherently omitted, structurally conforming to
// the underlying single-threaded deterministic sequence model.

#include <string>
#include <unordered_map>
#include <map>
#include <vector>
#include <iostream>

namespace Orsa {

    class TagRegistry {
    public:
        TagRegistry() {}

        // Look up the integer ID for a tag name.  If the name has not
        // been seen before, a new ID is allocated and returned.
        int getID(const std::string& name) {
            auto it = m_nameToId.find(name);
            if (it != m_nameToId.end()) return it->second;
            int id = m_nextId++;
            m_nameToId[name] = id;
            m_idToName[id] = name;
            m_counts[id] = 0;
            return id;
        }

        // Reverse lookup: return the name for a given ID, or "UNKNOWN".
        std::string getName(int id) const {
            auto it = m_idToName.find(id);
            return (it != m_idToName.end()) ? it->second : "UNKNOWN";
        }

        // Increment the event counter for a given tag.
        void incrementCount(int id) { m_counts[id]++; }

        // Return the cumulative count for a tag.
        long long getCount(int id) const {
            auto it = m_counts.find(id);
            return (it != m_counts.end()) ? it->second : 0;
        }

        // Return the full (id -> name) map, ordered by ID for stable output.
        std::map<int, std::string> getAllTags() const {
            return m_idToName;
        }

        // Direct access to the name->id map (used for saving metadata).
        const std::unordered_map<std::string, int>& getTagMap() const {
            return m_nameToId;
        }

    private:
        std::unordered_map<std::string, int> m_nameToId;
        std::map<int, std::string> m_idToName;     // std::map gives ordered iteration
        std::unordered_map<int, long long> m_counts;
        int m_nextId = 0;
    };

}

#endif // ORSACLASSIFICATION_TAGREGISTRY_H
