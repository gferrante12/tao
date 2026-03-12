#ifndef ORSACLASSIFICATION_SELECTOR_H
#define ORSACLASSIFICATION_SELECTOR_H

// Selector.h
//
// Defines isolated, event-centric predicate evaluators forming the foundational
// classification logic. A Selector systematically interrogates the generic
// EventWrapper properties yielding a strict boolean classification. These independent
// modules collectively synthesize comprehensive event categories, whereupon a successful
// cascading evaluation results in explicit tag assignment.
//
// The inheritance topology originates from a pure virtual interface, diversifying
// into explicit parameter range bounding criteria, complex inter-detector coincidence
// requirements, and nested topological operators achieving intricate composite
// combinatorics including intersection, union, and absolute negation.

#include "EventWrapper.h"
#include <string>
#include <vector>
#include <memory>
#include <functional>

namespace Orsa {

    // Abstract base class for all single-event selectors.
    class Selector {
    public:
        virtual ~Selector() {}

        // Evaluate this selector on the given event.
        virtual bool pass(const EventWrapper& evt) const = 0;

        // Human-readable name (used in logging and diagnostics).
        virtual std::string name() const = 0;

        void setTagID(int id) { m_tagID = id; }
        int getTagID() const { return m_tagID; }

    protected:
        int m_tagID = -1;  // tag ID assigned when this selector passes
    };

    // Checks whether a scalar quantity lies within [min, max].
    // The quantity is extracted from the EventWrapper by a configurable
    // accessor function (e.g. energy, charge, fiducial radius, ...).
    class RangeSelector : public Selector {
    public:
        // Accessor signature: takes (EventWrapper, source_hint) and returns the value.
        using Accessor = std::function<double(const EventWrapper&, const std::string&)>;

        RangeSelector(const std::string& name, Accessor acc, double min, double max, const std::string& source = "")
            : m_name(name), m_acc(acc), m_min(min), m_max(max), m_source(source) {}

        bool pass(const EventWrapper& evt) const override {
            double val = m_acc(evt, m_source);
            return val >= m_min && val <= m_max;
        }

        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        Accessor m_acc;
        double m_min;
        double m_max;
        std::string m_source;  // forwarded to the accessor (e.g. "OEC", "RecHeader")
    };

    // Passes if the event has a coincident hit in another sub-detector
    // within a given time window and above a minimum charge.
    // Delegates to EventWrapper::hasCoincidence().
    class CoincidenceSelector : public Selector {
    public:
        CoincidenceSelector(const std::string& name, int targetDet, double dt_min, double dt_max, double minQ)
            : m_name(name), m_det(targetDet), m_dtMin(dt_min), m_dtMax(dt_max), m_minQ(minQ) {}

        bool pass(const EventWrapper& evt) const override {
            return evt.hasCoincidence(m_det, m_dtMin, m_dtMax, m_minQ);
        }

        std::string name() const override { return m_name; }
    
    private:
        std::string m_name;
        int m_det;         // target detector type (1=CD, 2=WP, 4=TT)
        double m_dtMin;    // minimum coincidence time [ns]
        double m_dtMax;    // maximum coincidence time [ns]
        double m_minQ;     // minimum charge threshold [PE]
    };

    // Logical NOT: inverts the result of a child selector.
    class NotSelector : public Selector {
    public:
        NotSelector(const std::string& name, std::shared_ptr<Selector> child)
            : m_name(name), m_child(child) {}

        bool pass(const EventWrapper& evt) const override {
            return !m_child->pass(evt);
        }
        std::string name() const override { return m_name; }
    private:
        std::string m_name;
        std::shared_ptr<Selector> m_child;
    };

    // Composite selector combining children with AND or OR logic.
    // AND: passes only if ALL children pass (returns true for empty children).
    // OR:  passes if ANY child passes (returns false for empty children).
    class CompositeSelector : public Selector {
    public:
        enum Op { AND, OR };

        CompositeSelector(const std::string& name, Op op) 
            : m_name(name), m_op(op) {}

        void add(std::shared_ptr<Selector> sel) {
            m_children.push_back(sel);
        }

        bool pass(const EventWrapper& evt) const override {
            if (m_op == AND) {
                if (m_children.empty()) return true;
                for (const auto& sel : m_children) {
                    if (!sel->pass(evt)) return false;
                }
                return true;
            } else { // OR
                if (m_children.empty()) return false;
                for (const auto& sel : m_children) {
                    if (sel->pass(evt)) return true;
                }
                return false;
            }
        }
        
        std::string name() const override { return m_name; }

    private:
        std::string m_name;
        Op m_op;
        std::vector<std::shared_ptr<Selector>> m_children;
    };

}

#endif // ORSACLASSIFICATION_SELECTOR_H
