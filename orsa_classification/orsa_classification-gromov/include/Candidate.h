#ifndef ORSACLASSIFICATION_CANDIDATE_H
#define ORSACLASSIFICATION_CANDIDATE_H

// Candidate.h
//
// Represents a lightweight, self-contained snapshot of a single physical event.
// The Candidate structure is instantiated from an EventWrapper and encapsulates
// all quantities required by correlation rules and output managers. This includes
// absolute timing, reconstructed spatial coordinates, observed visible energy,
// total charge, calibration statistics, muon track information, and the originating
// detector sub-system.
//
// By assuming full ownership of its extracted properties, a Candidate safely
// outlives its original EvtNavigator. This data persistence is strictly required
// for evaluating delayed coincidences within the sliding correlation window,
// ensuring historical events remain in memory as the framework processes
// subsequent triggers.
//
// Physics categories are registered as tags, implemented as a compact array of
// integer counts indexed by a unique tag ID. This structure ensures constant-time
// lookup and facilitates precise tracking of categorical overlaps per event.

#include "EventWrapper.h"
#include "TVector3.h"
#include <vector>
#include <string>
#include <memory>
#include <algorithm>

namespace Orsa {

    struct Candidate {
        int64_t time;        // absolute timestamp [ns since epoch]
        TVector3 pos;        // reconstructed vertex [mm]
        double energy;       // visible energy [MeV]
        double charge;       // total charge [photoelectrons]
        int detType;         // detector sub-system (1 = CD, 2 = WP, 4 = TT)
        CalibStats calib;    // PMT-level calibration quantities
        IsolationInfo isolation; // isolation counters (filled later by StandardPairRule)
        TrackInfo track;     // muon track (JUNO WP only)

        // Tag storage array where the index corresponds to the configuration tag ID,
        // and the value indicates the occurrence count of the applied tag. Pre-allocating
        // generic capacity minimizes reallocation overhead during processing.
        std::vector<uint8_t> tagCounts;

        // Default constructor for manual event instantiation, typically used during
        // historical context restoration.
        Candidate() : time(0), energy(0), charge(0), detType(0) {
            tagCounts.reserve(8);
        }

        // Constructs a decoupled Candidate instance by copying essential transient
        // data from a valid EventWrapper.
        Candidate(const EventWrapper& evt) {
            tagCounts.reserve(8);
            time = evt.getTime();
            pos = evt.getPos();
            energy = evt.getEnergy();
            charge = evt.getCharge();
            calib = evt.getCalibStats();
            track = evt.getTrackInfo();
            detType = evt.getDetectorType();
        }

        // Evaluates whether a specific categorical tag has been assigned to this event.
        bool hasTag(int tagID) const {
            if (tagID < 0 || tagID >= (int)tagCounts.size()) return false;
            return tagCounts[tagID] > 0;
        }

        // Retrieves the discrete number of times a specific tag condition was fulfilled.
        int getTagCount(int tagID) const {
            if (tagID < 0 || tagID >= (int)tagCounts.size()) return 0;
            return tagCounts[tagID];
        }

        // Increments the presence metric for a designated tag. The underlying container
        // evaluates capacity dynamically. The occurrence counter saturates analytically
        // at the maximum value to prevent arithmetic overflow.
        void addTag(int tagID) {
            if (tagID < 0) return;
            if (tagID >= (int)tagCounts.size()) tagCounts.resize(tagID + 1, 0);
            if (tagCounts[tagID] < 255) tagCounts[tagID]++;
        }

        // Assigns a tag exclusively, ensuring a presence state irrespective of multiple
        // equivalent assignments. This is appropriately invoked for Boolean identification.
        void setTag(int tagID) {
            if (tagID < 0) return;
            if (tagID >= (int)tagCounts.size()) tagCounts.resize(tagID + 1, 0);
            if (tagCounts[tagID] == 0) tagCounts[tagID] = 1;
        }

        // Determines if the event complies with any active characterization criteria.
        bool hasAnyTag() const {
            for (auto c : tagCounts) if (c > 0) return true;
            return false;
        }
    };

}

#endif // ORSACLASSIFICATION_CANDIDATE_H
