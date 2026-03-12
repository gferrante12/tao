#ifndef ORSACLASSIFICATION_MUONMANAGER_H
#define ORSACLASSIFICATION_MUONMANAGER_H

// MuonManager.h
//
// Constitutes a rigorously time-ordered preservation buffer specifically isolating
// muon candidates designated for subsequent veto and spallation correlation. The
// central algorithm systematically introduces positively identified candidates while
// deterministically expiring historical entries exceeding the globally defined
// retention threshold, ensuring memory footprint stabilization during extensive
// background integration windows.
//
// The management architecture exposes a comprehensive suite of topological and
// chronological queries, including proximity evaluations by time or spatial distance,
// and expansive iterative functions for continuous window tracking. Spatial
// calculations inherently support dynamic resolution switching between basic
// point-to-point vector analysis and complex point-to-line projection matching
// where primary trajectory reconstruction is available.

#include "Candidate.h"
#include <deque>
#include <cmath>
#include <limits>

namespace Orsa {

    class MuonManager {
    public:
        // Add a muon to the buffer and evict any that have expired.
        void addMuon(const Candidate& muon) {
            m_muons.push_back(muon);
            cleanOld(muon.time);
        }

        // Remove muons older than (current_time - m_maxWindow).
        void cleanOld(int64_t current_time) {
            while (!m_muons.empty() && (current_time - m_muons.front().time > m_maxWindow))
                m_muons.pop_front();
        }

        // Set the retention window [ns].
        void setWindow(int64_t nanoseconds) { m_maxWindow = nanoseconds; }

        // Binary search: first muon with time >= t.
        std::deque<Candidate>::const_iterator findFirstAfterOrAt(int64_t t) const {
            return std::lower_bound(m_muons.begin(), m_muons.end(), t,
                [](const Candidate& c, int64_t val){ return c.time < val; });
        }

        // Return a pointer to the most recent muon strictly before time t.
        // Returns nullptr if no such muon exists.
        const Candidate* closestInTime(int64_t t) const {
            if (m_muons.empty()) return nullptr;
            auto it = findFirstAfterOrAt(t);
            if (it == m_muons.begin()) return nullptr;
            return &(*std::prev(it));
        }

        // Non-const overload (needed by MuonNeutronRule, which modifies the muon's tags).
        Candidate* closestInTime(int64_t t) {
            if (m_muons.empty()) return nullptr;
            auto it = std::lower_bound(m_muons.begin(), m_muons.end(), t,
                [](const Candidate& c, int64_t val){ return c.time < val; });
            if (it == m_muons.begin()) return nullptr;
            return &(*std::prev(it));
        }

        // Iterate backwards over muons preceding t_end, up to max_lookback ns.
        // The callback receives each muon and should return true to continue
        // or false to stop early.
        template<typename Func>
        void forEachMuon(int64_t t_end, int64_t max_lookback, Func callback) const {
            if (m_muons.empty()) return;
            auto it = findFirstAfterOrAt(t_end);
            auto rit = std::make_reverse_iterator(it);
            for (; rit != m_muons.rend(); ++rit) {
                int64_t dt = t_end - rit->time;
                if (dt > max_lookback) break;
                if (!callback(*rit)) return;
            }
        }

        // Time difference [ns] from the current event to the closest preceding muon.
        // Returns -1 if no muon is found.
        int64_t dtToPrevMuon(int64_t t) const {
            const Candidate* mu = closestInTime(t);
            return mu ? (t - mu->time) : -1;
        }

        // Perpendicular distance from a vertex to a track segment defined
        // by (start, end).  Uses the cross-product formula:
        //   d = |trackVec x (vertex - start)| / |trackVec|
        // Returns 1e6 if the track has zero length (degenerate case).
        static double pointToTrackDist(const TVector3& vertex,
                                        const TVector3& start, const TVector3& end) {
            TVector3 trackVec = end - start;
            double trackLen = trackVec.Mag();
            if (trackLen == 0) return 1e6;
            return trackVec.Cross(vertex - start).Mag() / trackLen;
        }

        // Distance from a vertex to a muon candidate.
        // Uses track-vertex distance if the muon has a reconstructed WP track,
        // otherwise falls back to simple point-to-point distance.
        static double distToMuon(const TVector3& vertex, const Candidate& mu) {
            if (mu.track.exists)
                return pointToTrackDist(vertex, mu.track.start, mu.track.end);
            return (vertex - mu.pos).Mag();
        }

        // Squared point-to-point distance [mm²] to the closest preceding muon.
        double distSqToPrevMuon(int64_t t, const TVector3& pos) const {
            const Candidate* mu = closestInTime(t);
            if (!mu) return -1.0;
            return (pos - mu->pos).Mag2();
        }

        // Distance [mm] to the closest preceding muon (uses track if available).
        double distToPrevMuon(int64_t t, const TVector3& pos) const {
            const Candidate* mu = closestInTime(t);
            if (!mu) return -1.0;
            return distToMuon(pos, *mu);
        }

        // Detailed result from a muon search: time offset, track distance,
        // muon type, and number of WP tracks.
        struct MuonDistResult {
            int64_t dt = -1;
            double dist_track = 1e12;
            int mu_type = 0;       // detector type of the muon (1=CD, 2=WP, 4=TT)
            int ntracks = 0;
        };

        // Find the closest muon by time and compute its track distance
        // to the given vertex.  Searches within max_lookback [ns].
        MuonDistResult closestMuonByTime(int64_t t, const TVector3& pos,
                                          int64_t max_lookback = 20000000000LL) const {
            MuonDistResult result;
            forEachMuon(t, max_lookback, [&](const Candidate& mu) {
                int64_t dt = t - mu.time;
                if (result.dt < 0 || dt < result.dt) {
                    result.dt = dt;
                    result.dist_track = distToMuon(pos, mu);
                    result.mu_type = mu.detType;
                    result.ntracks = mu.track.ntracks;
                }
                return true;
            });
            return result;
        }

        // Find the muon with the smallest track distance to the given vertex
        // within max_lookback [ns].
        MuonDistResult closestMuonByDist(int64_t t, const TVector3& pos,
                                          int64_t max_lookback = 20000000000LL) const {
            MuonDistResult result;
            forEachMuon(t, max_lookback, [&](const Candidate& mu) {
                double d = distToMuon(pos, mu);
                if (d < result.dist_track) {
                    result.dt = t - mu.time;
                    result.dist_track = d;
                    result.mu_type = mu.detType;
                    result.ntracks = mu.track.ntracks;
                }
                return true;
            });
            return result;
        }

    private:
        std::deque<Candidate> m_muons;
        int64_t m_maxWindow = 20000000000LL; // default 20 seconds [ns]
    };

}

#endif // ORSACLASSIFICATION_MUONMANAGER_H
