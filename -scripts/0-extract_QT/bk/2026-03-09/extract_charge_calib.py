#!/usr/bin/env python3
"""
extract_charge_calib.py - Extract ADC histograms with multi-detector veto.
Simplified for gain calibration on RTRAW files:
  - No radial/spatial cut (requires reconstruction, not available on RTRAW)
  - No ChargeTree, no TDC histograms
  - Per-channel ADC upper cut at 1e5 ADC rejects most muon/flasher events
    before the event-level MAX_ADC_PER_CHANNEL check (which stays at 1.7e7
    as a catch-all for truly saturated channels). The 1e5 cut effectively
    removes the high-ADC tail that muons deposit in individual channels
    while keeping Ge-68 photon hits (max expected ~60 000 ADC for 7 PE).
  - Veto hierarchy (from file:28 and get_spectrum.py, deduped):
      1. Per-channel ADC > ADC_HIT_MAX  → drop that channel's hits (flasher)
      2. Event total ADC > MAX_TOTAL_ADC → outlier (redundant with muon tag
         for CD-only but kept as safety net for incomplete WT/TVT coverage)
      3. nHit out of [MIN_NHIT, MAX_NHIT] → outlier
      4. Multi-detector muon tag (CD + WT + TVT) → muon veto
      5. After-muon window → muon tail veto
      6. After-pulse window → AP veto
      7. (CALIB2 only) per-hit TDC window and per-hit ADC window applied
         when filling histograms.

NOTE on duplicate-free design:
  - MAX_TOTAL_ADC (8e8) and MUON_THRESHOLD_CD (8e8) are intentionally equal
    for CALIB mode: a CD muon tags the event AND fires the outlier cut.
    The muon flag triggers the veto window; the outlier cut just drops the
    event counts from the clean histogram.  No double-counting occurs
    because veto_flag is set once per event in priority order.
  - ADC_HIT_MAX (1e5 for CALIB2, else 1.7e7) is the per-channel hit-level
    cut; MAX_ADC_PER_CHANNEL (1.7e7) is the per-channel flasher guard at
    the event-level loop — they operate on different objects and do not
    overlap: ADC_HIT_MAX filters individual hits, MAX_ADC_PER_CHANNEL
    flags the entire channel and skips it from event-level totals.
"""

import sys
import os
import re
import argparse
import numpy as np
from collections import Counter

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)


def file_exists_or_accessible(path):
    if path.startswith("root://"):
        return True
    return os.path.exists(path)


# =============================================================================
# VETO PARAMETERS (mode-dependent)
# All ADC thresholds in ADC counts; all time thresholds in nanoseconds.
# =============================================================================

PARAMS_CALIB = {
    # ── event-level ──────────────────────────────────────────────────────────
    "MUON_THRESHOLD_CD":  8e8,   # CD total ADC muon tag
    "MUON_THRESHOLD_WT":  5,     # WT fired-channel count muon tag
    "MUON_THRESHOLD_TVT": 3,     # TVT fired-channel count muon tag
    "AFTER_MU":           1000e3, # 1000 µs after-muon veto window (ns)
    "AFTER_PULSE":        5e3,    # 5 µs after-pulse veto window (ns)
    "MAX_TOTAL_ADC":      8e8,    # event total ADC outlier cut
    "MAX_ADC_PER_CHANNEL":1.7e7,  # per-channel flasher guard
    "MIN_NHIT":           2000,
    "MAX_NHIT":           7000,
    # ── per-hit (None = no cut) ───────────────────────────────────────────────
    "TDC_HIT_MIN": None,
    "TDC_HIT_MAX": None,
    "ADC_HIT_MIN": None,
    "ADC_HIT_MAX": 1e5,   # reject likely-muon single-channel deposits
}

PARAMS_PHYSICS = {
    "MUON_THRESHOLD_CD":  5.4e8,
    "MUON_THRESHOLD_WT":  15,
    "MUON_THRESHOLD_TVT": 4,
    "AFTER_MU":           1000e3,
    "AFTER_PULSE":        5e3,
    "MAX_TOTAL_ADC":      8e8,
    "MAX_ADC_PER_CHANNEL":1.7e7,
    "MIN_NHIT":           100,
    "MAX_NHIT":           5500,
    "TDC_HIT_MIN": None,
    "TDC_HIT_MAX": None,
    "ADC_HIT_MIN": None,
    "ADC_HIT_MAX": 1e5,
}

PARAMS_IBD = {
    "MUON_THRESHOLD_CD":  8e8,
    "MUON_THRESHOLD_WT":  11,
    "MUON_THRESHOLD_TVT": 4,
    "AFTER_MU":           100e3,
    "AFTER_PULSE":        2.5e3,
    "MAX_TOTAL_ADC":      5e8,
    "MAX_ADC_PER_CHANNEL":1.68e7,
    "MIN_NHIT":           500,
    "MAX_NHIT":           7000,
    "TDC_HIT_MIN": None,
    "TDC_HIT_MAX": None,
    "ADC_HIT_MIN": None,
    "ADC_HIT_MAX": 1e5,
}

# CALIB2: same event-level veto as CALIB + per-hit TDC window.
# ADC_HIT_MAX stays 1e5 (same reason as CALIB; the tighter 60 000 upper
# bound from the old PARAMS_CALIB2 is superseded by the physics argument
# that the 7-PE tail only reaches ~42 000 ADC and we want to keep it fully).
PARAMS_CALIB2 = {
    "MUON_THRESHOLD_CD":  8e8,
    "MUON_THRESHOLD_WT":  5,
    "MUON_THRESHOLD_TVT": 3,
    "AFTER_MU":           1000e3,
    "AFTER_PULSE":        5e3,
    "MAX_TOTAL_ADC":      8e8,
    "MAX_ADC_PER_CHANNEL":1.7e7,
    "MIN_NHIT":           2000,
    "MAX_NHIT":           7000,
    # per-hit TDC window selects prompt Ge-68 photons, rejects dark noise
    "TDC_HIT_MIN": 240.0,   # ns
    "TDC_HIT_MAX": 440.0,   # ns
    "ADC_HIT_MIN": 1_000.0, # remove baseline noise
    "ADC_HIT_MAX": 1e5,     # same muon-rejection upper bound as other modes
}

PARAMS_MAP = {
    "calib":  PARAMS_CALIB,
    "calib2": PARAMS_CALIB2,
    "physics":PARAMS_PHYSICS,
    "ibd":    PARAMS_IBD,
}


# =============================================================================
# MAIN EXTRACTION FUNCTION
# =============================================================================

def extract_charge_data(rtraw_file, output_dir, mode="calib2"):
    """
    Extract per-channel ADC histograms (raw + clean) from one RTRAW file.
    No spatial/radial cut — not applicable to RTRAW without prior reconstruction.
    """
    if not file_exists_or_accessible(rtraw_file):
        print(f"ERROR: File not found: {rtraw_file}")
        sys.exit(1)

    params = PARAMS_MAP.get(mode)
    if params is None:
        raise ValueError(f"Unknown mode: {mode}. Choose from {list(PARAMS_MAP)}")

    MUON_THRESHOLD_CD  = params["MUON_THRESHOLD_CD"]
    MUON_THRESHOLD_WT  = params["MUON_THRESHOLD_WT"]
    MUON_THRESHOLD_TVT = params["MUON_THRESHOLD_TVT"]
    AFTER_MU           = params["AFTER_MU"]
    AFTER_PULSE        = params["AFTER_PULSE"]
    MAX_TOTAL_ADC      = params["MAX_TOTAL_ADC"]
    MAX_ADC_PER_CHANNEL= params["MAX_ADC_PER_CHANNEL"]
    MIN_NHIT           = params["MIN_NHIT"]
    MAX_NHIT           = params["MAX_NHIT"]
    TDC_HIT_MIN        = params["TDC_HIT_MIN"]
    TDC_HIT_MAX        = params["TDC_HIT_MAX"]
    ADC_HIT_MIN        = params["ADC_HIT_MIN"]
    ADC_HIT_MAX        = params["ADC_HIT_MAX"]
    USE_HIT_CUTS       = (TDC_HIT_MIN is not None) or (ADC_HIT_MIN is not None) or (ADC_HIT_MAX is not None)

    # Parse RUN and file number from TAO DAQ filename
    basename   = os.path.basename(rtraw_file)
    run_match  = re.search(r'RUN\.(\d+)\.', basename)
    run_number = run_match.group(1) if run_match else "UNKNOWN"
    file_match = re.search(r'\.(\d{3})_T\d+\.\d+\.\d+.*\.rtraw', basename)
    file_number= file_match.group(1) if file_match else "000"

    print("=" * 60)
    print(f"extract_charge_calib  mode={mode}")
    print(f"Input  : {rtraw_file}")
    print(f"RUN    : {run_number}   File: {file_number}")
    print("=" * 60)
    print(f"  CD muon threshold      : {MUON_THRESHOLD_CD:.1e} ADC")
    print(f"  WT muon threshold      : {MUON_THRESHOLD_WT} channels")
    print(f"  TVT muon threshold     : {MUON_THRESHOLD_TVT} channels")
    print(f"  After-muon veto        : {AFTER_MU/1e3:.0f} µs")
    print(f"  After-pulse veto       : {AFTER_PULSE/1e3:.1f} µs")
    print(f"  Max total ADC (outlier): {MAX_TOTAL_ADC:.1e}")
    print(f"  Max ADC/ch (flasher)   : {MAX_ADC_PER_CHANNEL:.1e}")
    print(f"  Per-hit ADC upper cut  : {ADC_HIT_MAX:.1e}  ← muon-deposit rejection")
    print(f"  nHit range             : [{MIN_NHIT}, {MAX_NHIT}]")
    if USE_HIT_CUTS:
        print(f"  Per-hit TDC window     : [{TDC_HIT_MIN}, {TDC_HIT_MAX}] ns")
        print(f"  Per-hit ADC window     : [{ADC_HIT_MIN}, {ADC_HIT_MAX}]")
    print()

    # Open RTRAW
    frtraw = ROOT.TFile.Open(rtraw_file, "READ")
    if not frtraw or frtraw.IsZombie():
        print("ERROR: Cannot open RTRAW file")
        sys.exit(1)

    cd_elec_tree = frtraw.Get("Event/Elec/CdElecEvt")
    cd_trig_tree = frtraw.Get("Event/Trig/CdTrigEvt")
    if not cd_elec_tree or not cd_trig_tree:
        print("ERROR: Cannot find CD trees")
        frtraw.Close()
        sys.exit(1)

    nentries = cd_elec_tree.GetEntries()
    print(f"Found {nentries} CD events")

    # WT (optional)
    has_wt = False
    try:
        wt_elec_tree = frtraw.Get("Event/Wt/Elec/WtElecEvt")
        wt_trig_tree = frtraw.Get("Event/Wt/Trig/WtTrigEvt")
        if (wt_elec_tree and wt_trig_tree
                and hasattr(wt_elec_tree, 'GetEntries')
                and hasattr(wt_trig_tree, 'GetEntries')):
            print(f"WT detector available ({wt_elec_tree.GetEntries()} events)")
            has_wt = True
        else:
            wt_elec_tree = wt_trig_tree = None
    except Exception:
        wt_elec_tree = wt_trig_tree = None
    if not has_wt:
        print("WT detector NOT AVAILABLE")

    # TVT (optional)
    has_tvt = False
    try:
        tvt_elec_tree = frtraw.Get("Event/Tvt/Elec/TvtElecEvt")
        tvt_trig_tree = frtraw.Get("Event/Tvt/Trig/TvtTrigEvt")
        if (tvt_elec_tree and tvt_trig_tree
                and hasattr(tvt_elec_tree, 'GetEntries')
                and hasattr(tvt_trig_tree, 'GetEntries')):
            print(f"TVT detector available ({tvt_elec_tree.GetEntries()} events)")
            has_tvt = True
        else:
            tvt_elec_tree = tvt_trig_tree = None
    except Exception:
        tvt_elec_tree = tvt_trig_tree = None
    if not has_tvt:
        print("TVT detector NOT AVAILABLE")
    print()

    # ── Histogram setup ─────────────────────────────────────────────────────
    N_CHANNELS = 8048
    NBINS      = 500
    XMIN       = 0.0
    XMAX       = 60000.0  # covers up to 7 PE @6000 ADC/PE with margin

    print(f"Creating {N_CHANNELS} ADC histograms (raw + clean)...")
    hists_adc_raw   = [ROOT.TH1F(f"H_adcraw_{ch}",   f"H_adcraw_{ch}",
                                  NBINS, XMIN, XMAX) for ch in range(N_CHANNELS)]
    hists_adc_clean = [ROOT.TH1F(f"H_adcClean_{ch}", f"H_adcClean_{ch}",
                                  NBINS, XMIN, XMAX) for ch in range(N_CHANNELS)]
    for h in hists_adc_raw + hists_adc_clean:
        h.SetDirectory(0)

    hists_adc_oor_raw   = {}
    hists_adc_oor_clean = {}

    # TDC vs ADC 2D histograms (clean events, selected channels only)
    TDC_NBINS, TDC_MIN, TDC_MAX = 200, 0.0, 2000.0
    ADC_NBINS2D = 100   # coarser ADC axis for 2D to keep file size small
    tdc_adc_ch_ids = list(range(min(tdc_adc_channels, N_CHANNELS)))
    hists_tdc_adc = {}
    
    if save_tdc_adc:
        print(f"Creating TDC-vs-ADC 2D histograms for {len(tdc_adc_ch_ids)} channels ...")
        for ch in tdc_adc_ch_ids:
            h2 = ROOT.TH2F(
                f"H_tdcAdc_{ch}",
                f"TDC vs ADC ch{ch};TDC sample [ns];ADC sample [counts]",
                TDC_NBINS, TDC_MIN, TDC_MAX,
                ADC_NBINS2D, XMIN, XMAX,
            )
            h2.SetDirectory(0)
            hists_tdc_adc[ch] = h2

    # ── Output file ─────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir,
        f"CHARGE_single_RUN{run_number}_{file_number}.root")
    fout = ROOT.TFile(output_file, "RECREATE")

    # ── Branch setup ─────────────────────────────────────────────────────────
    cd_elec_evt = ROOT.Tao.CdElecEvt()
    cd_trig_evt = ROOT.Tao.CdTrigEvt()
    cd_elec_tree.SetBranchAddress("CdElecEvt", cd_elec_evt)
    cd_trig_tree.SetBranchAddress("CdTrigEvt", cd_trig_evt)

    if has_wt:
        wt_elec_evt = ROOT.Tao.WtElecEvt()
        wt_trig_evt = ROOT.Tao.WtTrigEvt()
        wt_elec_tree.SetBranchAddress("WtElecEvt", wt_elec_evt)
        wt_trig_tree.SetBranchAddress("WtTrigEvt", wt_trig_evt)

    if has_tvt:
        tvt_elec_evt = ROOT.Tao.TvtElecEvt()
        tvt_trig_evt = ROOT.Tao.TvtTrigEvt()
        tvt_elec_tree.SetBranchAddress("TvtElecEvt", tvt_elec_evt)
        tvt_trig_tree.SetBranchAddress("TvtTrigEvt", tvt_trig_evt)

    # ── Event loop ───────────────────────────────────────────────────────────
    print(f"Processing {nentries} events...")
    out_of_range_channels = Counter()
    total_hits = 0

    sec_prev = nsec_prev = 0
    sec_mu   = nsec_mu   = 0
    is_after_muon = False

    n_muons = n_muons_cd = n_muons_wt = n_muons_tvt = 0
    n_after_muon = n_after_pulse = n_outlier = n_clean = 0

    for i in range(nentries):
        if (i + 1) % 10000 == 0:
            print(f"\rEvent {i+1}/{nentries}...", end='', flush=True)

        cd_elec_tree.GetEntry(i)
        cd_trig_tree.GetEntry(i)
        if has_wt:
            wt_elec_tree.GetEntry(i)
            wt_trig_tree.GetEntry(i)
        if has_tvt:
            tvt_elec_tree.GetEntry(i)
            tvt_trig_tree.GetEntry(i)

        trig_time = cd_trig_evt.getTrigTime()
        sec  = trig_time.GetSec()
        nsec = trig_time.GetNanoSec()

        # After-muon veto bookkeeping
        if is_after_muon:
            if (sec - sec_mu) * 1e9 + (nsec - nsec_mu) > AFTER_MU:
                is_after_muon = False

        # After-pulse veto
        if i > 0:
            diff = (sec - sec_prev) * 1e9 + (nsec - nsec_prev)
            is_after_pulse = (diff < AFTER_PULSE)
        else:
            is_after_pulse = False

        # ── Per-channel loop: build event totals ─────────────────────────────
        channels      = cd_elec_evt.GetElecChannels()
        n_fired       = channels.size()
        tot_adc_event = 0.0
        event_channel_data = []
        has_flasher   = False

        for j in range(n_fired):
            channel = channels[j]
            chid    = channel.getChannelID()
            adcs    = channel.getADCs()
            tdcs    = channel.getTDCs()

            # Sum all ADC hits for this channel (event-level flasher check)
            adcs_list     = [adcs[k] for k in range(adcs.size())]
            ch_total_adc  = sum(adcs_list)

            # Event-level per-channel flasher guard
            if ch_total_adc > MAX_ADC_PER_CHANNEL:
                has_flasher = True
                continue
            if not adcs_list:
                continue

            tot_adc_event += ch_total_adc
            total_hits    += len(adcs_list)

            n_hits = min(adcs.size(), tdcs.size())
            hits   = [(float(adcs[k]), float(tdcs[k])) for k in range(n_hits)]
            for k in range(n_hits, adcs.size()):
                hits.append((float(adcs[k]), -1.0))

            event_channel_data.append({
                'chid':         chid,
                'hits':         hits,
                'ch_total_adc': ch_total_adc,
            })

        n_hit_channels = len(event_channel_data)

        # ── Muon tagging ─────────────────────────────────────────────────────
        is_muon_cd  = (tot_adc_event > MUON_THRESHOLD_CD)
        is_muon_wt  = False
        is_muon_tvt = False
        if has_wt:
            is_muon_wt  = (wt_elec_evt.GetElecChannels().size() >= MUON_THRESHOLD_WT)
        if has_tvt:
            is_muon_tvt = (tvt_elec_evt.GetElecChannels().size() >= MUON_THRESHOLD_TVT)
        is_muon = is_muon_cd or is_muon_wt or is_muon_tvt

        # ── Outlier checks ───────────────────────────────────────────────────
        passes_outlier = (tot_adc_event <= MAX_TOTAL_ADC
                          and MIN_NHIT <= n_hit_channels <= MAX_NHIT
                          and not has_flasher)

        # ── Assign veto flag (priority order) ────────────────────────────────
        if not passes_outlier:
            veto_flag = 4   # outlier
            n_outlier += 1
        elif is_after_muon:
            veto_flag = 2   # after-muon
            n_after_muon += 1
        elif is_after_pulse:
            veto_flag = 1   # after-pulse
            n_after_pulse += 1
        else:
            veto_flag = 0   # clean
            n_clean += 1

        # ── Fill TIER 1 (Raw) — all non-flasher events ───────────────────────
        for ch_data in event_channel_data:
            chid = ch_data['chid']
            hits = ch_data['hits']
            is_oor = not (0 <= chid < N_CHANNELS)

            if is_oor:
                if chid not in hists_adc_oor_raw:
                    h = ROOT.TH1F(f"H_adcraw_{chid}", f"ADC raw {chid} (OOR)",
                                  NBINS, XMIN, XMAX)
                    h.SetDirectory(0)
                    hists_adc_oor_raw[chid] = h
                out_of_range_channels[chid] += 1
                target = hists_adc_oor_raw[chid]
            else:
                target = hists_adc_raw[chid]

            for adc_val, tdc_val in hits:
                # Per-hit ADC upper cut (muon rejection) — applied in all modes
                if ADC_HIT_MAX is not None and adc_val > ADC_HIT_MAX:
                    continue
                if USE_HIT_CUTS:
                    if ADC_HIT_MIN is not None and adc_val < ADC_HIT_MIN:
                        continue
                    if TDC_HIT_MIN is not None and not (TDC_HIT_MIN <= tdc_val <= TDC_HIT_MAX):
                        continue
                target.Fill(adc_val)

        # ── Fill TIER 2 (Clean) ───────────────────────────────────────────────
        if veto_flag == 0:
            for ch_data in event_channel_data:
                chid = ch_data['chid']
                hits = ch_data['hits']
                is_oor = not (0 <= chid < N_CHANNELS)

                if is_oor:
                    if chid not in hists_adc_oor_clean:
                        h = ROOT.TH1F(f"H_adcClean_{chid}", f"ADC Clean {chid} (OOR)",
                                      NBINS, XMIN, XMAX)
                        h.SetDirectory(0)
                        hists_adc_oor_clean[chid] = h
                    target = hists_adc_oor_clean[chid]
                else:
                    target = hists_adc_clean[chid]

                for adc_val, tdc_val in hits:
                    if ADC_HIT_MAX is not None and adc_val > ADC_HIT_MAX:
                        continue
                    if USE_HIT_CUTS:
                        if ADC_HIT_MIN is not None and adc_val < ADC_HIT_MIN:
                            continue
                        if TDC_HIT_MIN is not None and not (TDC_HIT_MIN <= tdc_val <= TDC_HIT_MAX):
                            continue
                    target.Fill(adc_val)

        # ── Muon bookkeeping ─────────────────────────────────────────────────
        if is_muon:
            is_after_muon = True
            sec_mu = sec; nsec_mu = nsec
            n_muons += 1
            n_muons_cd  += int(is_muon_cd)
            n_muons_wt  += int(is_muon_wt)
            n_muons_tvt += int(is_muon_tvt)

        sec_prev = sec; nsec_prev = nsec

    print(f"\rEvent {nentries}/{nentries}... Done!")

    # ── Statistics ───────────────────────────────────────────────────────────
    print()
    print("Veto Statistics:")
    print(f"  Muon events (total)       : {n_muons}")
    print(f"    Tagged by CD            : {n_muons_cd}")
    if has_wt:  print(f"    Tagged by WT            : {n_muons_wt}")
    if has_tvt: print(f"    Tagged by TVT           : {n_muons_tvt}")
    print(f"  Vetoed (after-muon)       : {n_after_muon}")
    print(f"  Vetoed (after-pulse)      : {n_after_pulse}")
    print(f"  Vetoed (outlier/flasher)  : {n_outlier}")
    print(f"  Clean events              : {n_clean}")
    print(f"  Clean fraction            : {100*n_clean/max(nentries,1):.1f}%")
    print(f"  Out-of-range channels     : {len(out_of_range_channels)}")
    print()

    # ── Save ─────────────────────────────────────────────────────────────────
    print(f"Saving to {output_file}")
    fout.cd()
    for h in hists_adc_raw:   h.Write()
    for h in hists_adc_oor_raw.values():   h.Write()
    for h in hists_adc_clean: h.Write()
    for h in hists_adc_oor_clean.values(): h.Write()

    meta = (
        f"MODE={mode};"
        f"MUON_THRESHOLD_CD={MUON_THRESHOLD_CD};"
        f"MUON_THRESHOLD_WT={MUON_THRESHOLD_WT};"
        f"MUON_THRESHOLD_TVT={MUON_THRESHOLD_TVT};"
        f"AFTER_MU={AFTER_MU};"
        f"AFTER_PULSE={AFTER_PULSE};"
        f"MAX_TOTAL_ADC={MAX_TOTAL_ADC};"
        f"MAX_ADC_PER_CHANNEL={MAX_ADC_PER_CHANNEL};"
        f"ADC_HIT_MAX={ADC_HIT_MAX};"
        f"MIN_NHIT={MIN_NHIT};"
        f"MAX_NHIT={MAX_NHIT};"
        f"TDC_HIT_MIN={TDC_HIT_MIN};"
        f"TDC_HIT_MAX={TDC_HIT_MAX};"
        f"ADC_HIT_MIN={ADC_HIT_MIN};"
        f"N_MUONS={n_muons};"
        f"N_AFTER_MUON={n_after_muon};"
        f"N_AFTER_PULSE={n_after_pulse};"
        f"N_OUTLIER={n_outlier};"
        f"N_CLEAN={n_clean};"
        f"HAS_WT={int(has_wt)};"
        f"HAS_TVT={int(has_tvt)};"
        f"SPATIAL_CUT_ENABLED=0"
    )
    ROOT.TNamed("veto_info", meta).Write()

    fout.Close()
    frtraw.Close()
    print()
    print("=" * 60)
    print("SUCCESS")
    print(f"Output: {output_file}")
    print("=" * 60)
    return output_file


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract ADC histograms for gain calibration (no spatial cut)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_charge_calib.py /path/RUN.1295.xxx.rtraw /path/output --mode calib2
  python extract_charge_calib.py /path/RUN.1410.xxx.rtraw /path/output --mode calib
""")
    parser.add_argument("rtraw_file",  help="Path to RTRAW file")
    parser.add_argument("output_dir",  help="Output directory")
    parser.add_argument('--save-tdc-adc', action='store_true',
                       help='Save per-channel TDC vs ADC 2D histograms (clean events) '
                            'under TdcAdc/ directory in the output ROOT file.')
    parser.add_argument('--tdc-adc-channels', type=int, default=100,
                       help='Number of channels for TDC-ADC 2D histograms (default: 100)')
    parser.add_argument("--mode",
        choices=list(PARAMS_MAP), default="calib2",
        help="Analysis mode (default: calib2 — adds per-hit TDC window)")
    args = parser.parse_args()
    extract_charge_data(args.rtraw_file, args.output_dir, mode=args.mode)
