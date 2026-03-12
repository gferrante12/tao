#ifndef ORSACLASSIFICATION_HISTORYMANAGER_H
#define ORSACLASSIFICATION_HISTORYMANAGER_H

// HistoryManager.h
//
// Facilitates extended long-baseline temporal persistence for complex correlation
// analysis necessitating macro-scale contextual lookback windows, fundamentally
// distinct from the short-term volatile correlation engine sequence.
//
// The core physics objective addresses the identification of cosmogenic isotopes
// induced by parent spallation reactions, representing delayed signatures occurring
// at significant temporal offsets. To successfully constrain these backgrounds, the
// structure queries expansive spatiotemporal conditions surrounding identified muon 
// precursor traversals and subsequent neutron cascade interactions.
//
// State preservation employs a chronologically ordered array coupled with a robust
// two-dimensional spatial discretization grid. This binning strategy maps generic
// property combinations to precise index regions, algorithmically suppressing 
// extensive full-volume iterations down to sparse, localized neighborhood queries.
// The characteristic grid granularity defines the resolving efficiency during execution.
// Periodic systematic pruning systematically removes stale parameters while intermittent
// full-scale rebuild sequences maintain optimal spatial coordinate indexing against the
// dynamic underlying sequence.

#include "TVector3.h"
#include <vector>
#include <unordered_map>
#include <deque>
#include <cmath>
#include <tuple>
#include <algorithm>

namespace Orsa {

    class HistoryManager {
    public:
        // maxWindow  retention time [ns] — entries older than this are pruned
        // cellSize   spatial grid cell width [mm]
        HistoryManager(int64_t maxWindow = 60000000000LL, double cellSize = 500.0)
            : m_maxWindow(maxWindow), m_cellSize(cellSize) {}

        // Record a tagged event into the history.
        void add(int tagID, int64_t time, const TVector3& pos) {
            m_entries.push_back({tagID, time, pos, gridCoord(pos)});
            insertIntoGrid(m_entries.size() - 1);
        }

        // Purges chronologically obsolescent records exceeding the retention threshold from
        // the active sequence. Execution overhead dynamically scales with candidate expiry volume.
        void cleanDeques(int64_t current_time) {
            int64_t cutoff = current_time - m_maxWindow;
            while (!m_entries.empty() && m_entries.front().time < cutoff)
                m_entries.pop_front();
        }

        // Initiates a rigorous reconstruction of the comprehensive multi-variable spatial index.
        // Intermittently invoked succeeding significant cumulative data ingestion to maintain
        // reference alignment against the continuously modified primary queue.
        void rebuildIndices() {
            m_grid.clear();
            for (size_t i = 0; i < m_entries.size(); ++i) {
                insertIntoGrid(i);
            }
        }

        // Evaluates boolean presence of isolated characteristic signatures encompassed by
        // simultaneous strict temporal and spatial thresholds. Employs the internal discretization
        // mesh to optimize topological searches.
        bool hasAny(int tagID, int64_t tMin, int64_t tMax,
                    const TVector3& pos, double radius) const {
            auto gc = gridCoord(pos);
            int nCells = (int)std::ceil(radius / m_cellSize);
            double r2 = radius * radius;

            // Scan all grid cells within the bounding box of the search radius.
            for (int dx = -nCells; dx <= nCells; ++dx) {
                for (int dy = -nCells; dy <= nCells; ++dy) {
                    GridKey key{tagID, gc.first + dx, gc.second + dy};
                    auto it = m_grid.find(key);
                    if (it == m_grid.end()) continue;
                    for (size_t idx : it->second) {
                        if (idx >= m_entries.size()) continue;
                        const auto& e = m_entries[idx];
                        if (e.time < tMin || e.time > tMax) continue;
                        if ((pos - e.pos).Mag2() <= r2) return true;
                    }
                }
            }
            return false;
        }

        // Count how many matching entries exist (same interface as hasAny).
        int countNearby(int tagID, int64_t tMin, int64_t tMax,
                        const TVector3& pos, double radius) const {
            auto gc = gridCoord(pos);
            int nCells = (int)std::ceil(radius / m_cellSize);
            double r2 = radius * radius;
            int count = 0;

            for (int dx = -nCells; dx <= nCells; ++dx) {
                for (int dy = -nCells; dy <= nCells; ++dy) {
                    GridKey key{tagID, gc.first + dx, gc.second + dy};
                    auto it = m_grid.find(key);
                    if (it == m_grid.end()) continue;
                    for (size_t idx : it->second) {
                        if (idx >= m_entries.size()) continue;
                        const auto& e = m_entries[idx];
                        if (e.time < tMin || e.time > tMax) continue;
                        if ((pos - e.pos).Mag2() <= r2) count++;
                    }
                }
            }
            return count;
        }


        // Iteratively determines the singular proximate match respecting spatial constraints within
        // the allowable chronological bound. Detected coordinates transfer via indirect parameter references.
        // Valid query resolution confirms through a definitive boolean indication.
        bool getNearest(int tagID, int64_t tMin, int64_t tMax,
                        const TVector3& pos, double radius,
                        int64_t& matchTime, TVector3& matchPos) const {
            auto gc = gridCoord(pos);
            int nCells = (int)std::ceil(radius / m_cellSize);
            double r2Min = radius * radius;
            bool found = false;

            // Scan grid cells
            for (int dx = -nCells; dx <= nCells; ++dx) {
                for (int dy = -nCells; dy <= nCells; ++dy) {
                    GridKey key{tagID, gc.first + dx, gc.second + dy};
                    auto it = m_grid.find(key);
                    if (it == m_grid.end()) continue;
                    for (size_t idx : it->second) {
                        if (idx >= m_entries.size()) continue;
                        const auto& e = m_entries[idx];
                        if (e.time < tMin || e.time > tMax) continue;
                        
                        double r2 = (pos - e.pos).Mag2();
                        if (r2 <= r2Min) {
                            r2Min = r2;
                            matchTime = e.time;
                            matchPos = e.pos;
                            found = true;
                        }
                    }
                }
            }
            return found;
        }

    private:
        struct Entry {
            int tagID;
            int64_t time;
            TVector3 pos;
            std::pair<int,int> gc;  // precomputed grid coordinates
        };

        // Grid key: (tagID, ix, iy).  Hashed by combining the three
        // integers with prime multipliers to reduce collisions.
        struct GridKey {
            int tag, ix, iy;
            bool operator==(const GridKey& o) const {
                return tag == o.tag && ix == o.ix && iy == o.iy;
            }
        };
        struct GridKeyHash {
            size_t operator()(const GridKey& k) const {
                size_t h = std::hash<int>()(k.tag);
                h ^= std::hash<int>()(k.ix) * 2654435761ULL;
                h ^= std::hash<int>()(k.iy) * 40503ULL;
                return h;
            }
        };

        std::deque<Entry> m_entries;
        int64_t m_maxWindow;
        double m_cellSize;

        // Spatial index: maps (tag, cell_x, cell_y) → list of entry indices.
        std::unordered_map<GridKey, std::vector<size_t>, GridKeyHash> m_grid;

        // Compute the 2D grid cell for a given 3D position (x, y projected).
        std::pair<int,int> gridCoord(const TVector3& pos) const {
            return {(int)std::floor(pos.X() / m_cellSize),
                    (int)std::floor(pos.Y() / m_cellSize)};
        }

        void insertIntoGrid(size_t idx) {
            const auto& e = m_entries[idx];
            m_grid[{e.tagID, e.gc.first, e.gc.second}].push_back(idx);
        }
    };

}

#endif // ORSACLASSIFICATION_HISTORYMANAGER_H
