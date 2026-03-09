#!/usr/bin/env python3
"""
get_spectrum_exotic.py — Exotic tri-mode RTRAW energy spectrum.

Applies the full CALIB2 multi-detector veto hierarchy (identical to
extract_charge_calib.py) and fills THREE independent PE/nHit spectra per
file, each selecting hits by a different ADC criterion:

  ┌──────┬────────────────────────────────────────┬───────────────────────┐
  │ Mode │ Per-hit ADC selection                  │ Event-level ADC cut   │
  ├──────┼────────────────────────────────────────┼───────────────────────┤
  │  A   │ ADC_HIT_MIN ≤ ADC ≤ ADC_HIT_MAX        │ MAX_TOTAL_ADC applied │
  │      │ (standard CALIB2 upper limit)           │                       │
  ├──────┼────────────────────────────────────────┼───────────────────────┤
  │  B   │ ADC ≥ ADC_HIT_MAX                       │ MAX_TOTAL_ADC applied │
  │      │ (inverted: select high-ADC hits)        │                       │
  ├──────┼────────────────────────────────────────┼───────────────────────┤
  │  C   │ ADC ≥ ADC_HIT_MAX                       │ MAX_TOTAL_ADC SKIPPED │
  │      │ (inverted: select high-ADC hits)        │ (no event ADC cut)    │
  └──────┴────────────────────────────────────────┴───────────────────────┘

All three modes share:
  • CD + WT + TVT multi-detector muon tagging
  • After-muon (1000 µs) and after-pulse (5 µs) windows
  • nHit range [2000, 7000]
  • MAX_ADC_PER_CHANNEL per-channel flasher guard
  • TDC window [240, 440] ns

The gain calibration file is auto-selected from the hard-coded official path
based on the run number (pass --run; required):
  RUN ≤ 1193   →  sipm_calib_1157-1193.txt
  RUN ≥ 1295   →  sipm_calib_1295-.txt
  RUN 1194-1294 →  sipm_calib_1295-.txt  (with warning)

Output ROOT file contains per-mode histograms:
  h_PEcontin_{a,b,c}    continuous PE spectrum
  h_PEdiscrete_{a,b,c}  discrete PE spectrum (channel-level rounding)
  h_nHit_{a,b,c}        hit-channel count spectrum
  veto_info             TNamed with full metadata and statistics
"""

import sys
import os
import re
import argparse
import numpy as np

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        return it


# =============================================================================
# HARD-CODED OFFICIAL GAIN CALIBRATION PATHS
# Kept in sync with launch_get_spectrum.sh (CALIB_BASE) and
# launch_extract_charge_calib.sh (1-gain_calibration_results/).
# =============================================================================

_GAIN_CALIB_BASE = (
    "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
    "/1-gain_calibration_results"
)
_GAIN_CALIB_1157_1193 = os.path.join(_GAIN_CALIB_BASE, "sipm_calib_1157-1193.txt")
_GAIN_CALIB_1295_PLUS = os.path.join(_GAIN_CALIB_BASE, "sipm_calib_1295-.txt")


def get_official_calib_file(run_number):
    """Return (path, warning_or_None) for the correct official calibration file.

    Run ranges:
        run <= 1193  →  sipm_calib_1157-1193.txt  (TAO_SiPM_calib_par_1768003200)
        run >= 1295  →  sipm_calib_1295-.txt       (TAO_SiPM_calib_par_1770336000)
        1194-1294    →  warning + use 1295- as best guess
    """
    if run_number >= 1295:
        return _GAIN_CALIB_1295_PLUS, None

    if run_number <= 1193:
        warn = None
        if run_number < 1157:
            warn = (f"WARNING: RUN {run_number} is below the officially calibrated "
                    f"range (1157-1193). Using sipm_calib_1157-1193.txt as the "
                    f"closest available default — verify this is appropriate.")
        return _GAIN_CALIB_1157_1193, warn

    # Gap 1194-1294
    warn = (f"WARNING: RUN {run_number} is in the gap range 1194-1294 with no "
            f"dedicated calibration file. Using sipm_calib_1295-.txt as best "
            f"guess — verify before use.")
    return _GAIN_CALIB_1295_PLUS, warn


# =============================================================================
# CALIB2 VETO PARAMETERS
# Verbatim from extract_charge_calib.py — edit both files together.
# =============================================================================

PARAMS_CALIB2 = {
    # ── event-level ──────────────────────────────────────────────────────────
    "MUON_THRESHOLD_CD":   8e8,    # CD total ADC muon tag
    "MUON_THRESHOLD_WT":   5,      # WT fired-channel count muon tag
    "MUON_THRESHOLD_TVT":  3,      # TVT fired-channel count muon tag
    "AFTER_MU":            1000e3, # ns — 1000 µs after-muon veto window
    "AFTER_PULSE":         5e3,    # ns — 5 µs after-pulse veto window
    "MAX_TOTAL_ADC":       8e8,    # event total ADC outlier cut (modes A+B only)
    "MAX_ADC_PER_CHANNEL": 1.7e7,  # per-channel flasher guard
    "MIN_NHIT":            2000,
    "MAX_NHIT":            7000,
    # ── per-hit ───────────────────────────────────────────────────────────────
    "TDC_HIT_MIN":         240.0,  # ns — prompt Ge-68 photon window (CALIB2)
    "TDC_HIT_MAX":         440.0,  # ns
    "ADC_HIT_MIN":         1_000.0,# remove baseline noise
    "ADC_HIT_MAX":         1e5,    # upper (mode A) / lower (modes B,C) boundary
}

# TDC window width for dark-noise calculation
_TDC_WINDOW_NS = PARAMS_CALIB2["TDC_HIT_MAX"] - PARAMS_CALIB2["TDC_HIT_MIN"]


# =============================================================================
# LOAD CALIBRATION
# =============================================================================

def load_calibration(calib_file):
    """Load channel calibration (gain, intercept, DCR) from official TXT file.

    Supports both the old TSpectrum format (no DCR) and the new format with
    a DCR column.  Returns (calibration_dict, dark_noise_pe_float).

    calibration_dict: {ch_id: {'gain': float, 'intercept': float, 'dcr': float}}
    dark_noise_pe   : Σ_ch DCR_ch × TDC_window_ns × 1e-9  [PE]
    """
    if not os.path.exists(calib_file):
        print(f"ERROR: Calibration file not found: {calib_file}")
        sys.exit(1)

    print(f"Loading calibration from: {calib_file}")
    with open(calib_file) as fh:
        lines = fh.readlines()

    # Auto-detect format: new format has 'dcr' in a comment line
    is_new_format = any('dcr' in ln.lower() for ln in lines if ln.startswith('#'))
    # Find first data line
    data_start = 0
    for i, ln in enumerate(lines):
        if ln.startswith('#'):
            data_start = i + 1
        elif ln.strip():
            break

    calibration = {}
    total_dcr = 0.0
    dcr_count = 0

    for ln in lines[data_start:]:
        parts = ln.strip().split()
        if not parts:
            continue
        try:
            ch_id = int(parts[0])
            gain  = float(parts[1])
            if gain > 1e6:       # sentinel for bad/masked channels
                continue
            # New format: ch gain mean0 gain_dyn mean0_dyn timeoffset baseline dcr
            # Old format: ch gain gain_err intercept int_err ...
            if is_new_format:
                intercept = float(parts[2])
                dcr = float(parts[7]) if len(parts) >= 8 else 0.0
            else:
                intercept = float(parts[3])
                dcr = 0.0
            calibration[ch_id] = {'gain': gain, 'intercept': intercept, 'dcr': dcr}
            if dcr > 0.0:
                total_dcr += dcr
                dcr_count += 1
        except (ValueError, IndexError):
            continue

    n_loaded = len(calibration)
    if n_loaded == 0:
        print("ERROR: No channels loaded from calibration file!")
        sys.exit(1)

    mean_gain = float(np.mean([v['gain'] for v in calibration.values()]))
    print(f"  Format  : {'NEW (with DCR)' if is_new_format else 'OLD (TSpectrum)'}")
    print(f"  Channels: {n_loaded}   mean gain: {mean_gain:.2f} ADC/PE")

    dark_noise_pe = 0.0
    if total_dcr > 0:
        dark_noise_pe = total_dcr * _TDC_WINDOW_NS * 1e-9
        print(f"  Total DCR ({dcr_count} ch): {total_dcr:.2f} Hz")
        print(f"  Dark Noise ({_TDC_WINDOW_NS:.0f} ns TDC window): "
              f"{dark_noise_pe:.4f} PE")
    else:
        print("  Dark Noise: DCR not in this file — dark noise = 0 (ignored)")

    return calibration, dark_noise_pe


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_exotic_rtraw(rtraw_file, calibration, dark_noise_pe):
    """Process one RTRAW file; return tri-mode histograms and statistics.

    Returns
    -------
    dict with keys:
      'histograms'   : {'a': {'PEcontin', 'PEdiscrete', 'nHit'},
                        'b': {...}, 'c': {...}}
      'stats_shared' : muon / veto counters (identical for all modes)
      'stats_mode'   : per-mode {'n_outlier', 'n_after_muon',
                                  'n_after_pulse', 'n_clean'}
      'n_events'     : total entries in CD tree
      'has_wt', 'has_tvt'
    or None on file-open error.
    """
    P = PARAMS_CALIB2
    MUON_THRESHOLD_CD  = P["MUON_THRESHOLD_CD"]
    MUON_THRESHOLD_WT  = P["MUON_THRESHOLD_WT"]
    MUON_THRESHOLD_TVT = P["MUON_THRESHOLD_TVT"]
    AFTER_MU           = P["AFTER_MU"]
    AFTER_PULSE        = P["AFTER_PULSE"]
    MAX_TOTAL_ADC      = P["MAX_TOTAL_ADC"]
    MAX_ADC_PER_CHANNEL= P["MAX_ADC_PER_CHANNEL"]
    MIN_NHIT           = P["MIN_NHIT"]
    MAX_NHIT           = P["MAX_NHIT"]
    TDC_HIT_MIN        = P["TDC_HIT_MIN"]
    TDC_HIT_MAX        = P["TDC_HIT_MAX"]
    ADC_HIT_MIN        = P["ADC_HIT_MIN"]
    ADC_HIT_MAX        = P["ADC_HIT_MAX"]

    fin = ROOT.TFile.Open(rtraw_file, "READ")
    if not fin or fin.IsZombie():
        print(f"  ERROR: Cannot open {rtraw_file}")
        return None

    cd_elec_tree = fin.Get("Event/Elec/CdElecEvt")
    cd_trig_tree = fin.Get("Event/Trig/CdTrigEvt")
    if not cd_elec_tree or not cd_trig_tree:
        print("  ERROR: Cannot find CD trees")
        fin.Close()
        return None

    nentries = cd_elec_tree.GetEntries()
    print(f"  Events: {nentries}")

    # ── Optional detectors ────────────────────────────────────────────────────
    has_wt = False
    try:
        wt_elec_tree = fin.Get("Event/Wt/Elec/WtElecEvt")
        wt_trig_tree = fin.Get("Event/Wt/Trig/WtTrigEvt")
        if (wt_elec_tree and wt_trig_tree
                and hasattr(wt_elec_tree, 'GetEntries')
                and hasattr(wt_trig_tree, 'GetEntries')):
            print(f"  WT available  ({wt_elec_tree.GetEntries()} events)")
            has_wt = True
        else:
            wt_elec_tree = wt_trig_tree = None
    except Exception:
        wt_elec_tree = wt_trig_tree = None
    if not has_wt:
        print("  WT NOT AVAILABLE")

    has_tvt = False
    try:
        tvt_elec_tree = fin.Get("Event/Tvt/Elec/TvtElecEvt")
        tvt_trig_tree = fin.Get("Event/Tvt/Trig/TvtTrigEvt")
        if (tvt_elec_tree and tvt_trig_tree
                and hasattr(tvt_elec_tree, 'GetEntries')
                and hasattr(tvt_trig_tree, 'GetEntries')):
            print(f"  TVT available ({tvt_elec_tree.GetEntries()} events)")
            has_tvt = True
        else:
            tvt_elec_tree = tvt_trig_tree = None
    except Exception:
        tvt_elec_tree = tvt_trig_tree = None
    if not has_tvt:
        print("  TVT NOT AVAILABLE")

    # ── Branch objects ────────────────────────────────────────────────────────
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

    # ── Histograms ────────────────────────────────────────────────────────────
    NBINS_PE  = 500;  PE_MAX  = 25000
    NBINS_HIT = 500;  HIT_MAX = 8048
    hists = {}
    mode_labels = {
        'a': 'Mode A: ADC in [ADC_HIT_MIN, ADC_HIT_MAX], MAX_TOTAL_ADC applied',
        'b': 'Mode B: ADC >= ADC_HIT_MAX (inverted), MAX_TOTAL_ADC applied',
        'c': 'Mode C: ADC >= ADC_HIT_MAX (inverted), no MAX_TOTAL_ADC cut',
    }
    for mode in ('a', 'b', 'c'):
        hists[mode] = {
            'PEcontin':   ROOT.TH1F(f"h_PEcontin_{mode}",
                                    f"Continuous PE [{mode_labels[mode]}]",
                                    NBINS_PE, 0, PE_MAX),
            'PEdiscrete': ROOT.TH1F(f"h_PEdiscrete_{mode}",
                                    f"Discrete PE [{mode_labels[mode]}]",
                                    NBINS_PE, 0, PE_MAX),
            'nHit':       ROOT.TH1F(f"h_nHit_{mode}",
                                    f"nHit [{mode_labels[mode]}]",
                                    NBINS_HIT, 0, HIT_MAX),
        }
        for h in hists[mode].values():
            h.SetDirectory(0)

    # ── Statistics ────────────────────────────────────────────────────────────
    s = dict(n_muons=0, n_muons_cd=0, n_muons_wt=0, n_muons_tvt=0)
    sm = {m: dict(n_outlier=0, n_after_muon=0, n_after_pulse=0, n_clean=0)
          for m in ('a', 'b', 'c')}

    sec_prev = nsec_prev = 0
    sec_mu   = nsec_mu   = 0
    is_after_muon = False

    # ── Event loop ────────────────────────────────────────────────────────────
    print(f"  Processing {nentries} events...")
    for i in range(nentries):
        if (i + 1) % 20000 == 0:
            print(f"\r  Event {i+1}/{nentries}...", end='', flush=True)

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

        # ── After-muon window expiry ──────────────────────────────────────────
        if is_after_muon:
            if (sec - sec_mu) * 1e9 + (nsec - nsec_mu) > AFTER_MU:
                is_after_muon = False

        # ── After-pulse flag ──────────────────────────────────────────────────
        is_after_pulse = (i > 0 and
                          (sec - sec_prev) * 1e9 + (nsec - nsec_prev) < AFTER_PULSE)

        # ── Per-channel data collection ───────────────────────────────────────
        channels      = cd_elec_evt.GetElecChannels()
        tot_adc_event = 0.0
        event_hits    = []          # list of (chid, adc_val, tdc_val)
        has_flasher   = False
        n_hit_channels = 0

        for j in range(channels.size()):
            channel      = channels[j]
            chid         = channel.getChannelID()
            adcs         = channel.getADCs()
            tdcs         = channel.getTDCs()
            adcs_list    = [adcs[k] for k in range(adcs.size())]
            ch_total_adc = sum(adcs_list)

            # Per-channel flasher guard (event-level; marks event as flasher)
            if ch_total_adc > MAX_ADC_PER_CHANNEL:
                has_flasher = True
                continue
            if not adcs_list:
                continue

            tot_adc_event += ch_total_adc
            n_hit_channels += 1

            n_hits = min(adcs.size(), tdcs.size())
            for k in range(n_hits):
                event_hits.append((chid, float(adcs[k]), float(tdcs[k])))
            for k in range(n_hits, adcs.size()):
                event_hits.append((chid, float(adcs[k]), -1.0))   # TDC missing

        # ── Muon tagging ──────────────────────────────────────────────────────
        is_muon_cd  = (tot_adc_event > MUON_THRESHOLD_CD)
        is_muon_wt  = (has_wt  and
                       wt_elec_evt.GetElecChannels().size() >= MUON_THRESHOLD_WT)
        is_muon_tvt = (has_tvt and
                       tvt_elec_evt.GetElecChannels().size() >= MUON_THRESHOLD_TVT)
        is_muon = is_muon_cd or is_muon_wt or is_muon_tvt

        # ── Outlier checks (two flavours) ─────────────────────────────────────
        nhit_ok    = MIN_NHIT <= n_hit_channels <= MAX_NHIT
        # Modes A + B: standard outlier includes MAX_TOTAL_ADC
        passes_ab  = nhit_ok and (not has_flasher) and (tot_adc_event <= MAX_TOTAL_ADC)
        # Mode C: relaxed outlier — no MAX_TOTAL_ADC threshold
        passes_c   = nhit_ok and (not has_flasher)

        # ── Per-mode veto assignment ──────────────────────────────────────────
        # Priority (mirroring extract_charge_calib.py): outlier > after-muon
        #                                                > after-pulse > clean
        def veto_flag(passes_outlier):
            if not passes_outlier:  return 'outlier'
            if is_after_muon:       return 'after_muon'
            if is_after_pulse:      return 'after_pulse'
            return 'clean'

        flag_ab = veto_flag(passes_ab)
        flag_c  = veto_flag(passes_c)

        # ── Update per-mode counters ──────────────────────────────────────────
        for mode, flag in (('a', flag_ab), ('b', flag_ab), ('c', flag_c)):
            sm[mode][f'n_{flag}'] += 1

        # ── Fill mode A histograms (standard: ADC_HIT_MIN ≤ adc ≤ ADC_HIT_MAX) ──
        if flag_ab == 'clean':
            pe_cont = pe_disc = 0.0
            nhit_a = 0
            for chid, adc, tdc in event_hits:
                if chid not in calibration:
                    continue
                if adc < ADC_HIT_MIN or adc > ADC_HIT_MAX:
                    continue
                if tdc < 0 or tdc < TDC_HIT_MIN or tdc > TDC_HIT_MAX:
                    continue
                ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
                pe_cont += ch_pe
                pe_disc += float(int(np.round(ch_pe)))
                nhit_a  += 1
            pe_cont -= dark_noise_pe
            pe_disc -= dark_noise_pe
            if pe_cont > 0:
                hists['a']['PEcontin'].Fill(pe_cont)
                hists['a']['PEdiscrete'].Fill(pe_disc)
            if nhit_a > 0:
                hists['a']['nHit'].Fill(nhit_a)

        # ── Fill mode B histograms (inverted ADC ≥ ADC_HIT_MAX, event cut ON) ──
        if flag_ab == 'clean':
            pe_cont = pe_disc = 0.0
            nhit_b = 0
            for chid, adc, tdc in event_hits:
                if chid not in calibration:
                    continue
                if adc < ADC_HIT_MAX:                    # lower bound
                    continue
                # NOTE: TDC window still applied — high-ADC hits outside the
                # prompt window [240, 440] ns are excluded, consistent with the
                # "inherits all veto cuts" requirement.  If mode B/C histograms
                # are empty, consider relaxing this in post-analysis.
                if tdc < 0 or tdc < TDC_HIT_MIN or tdc > TDC_HIT_MAX:
                    continue
                ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
                pe_cont += ch_pe
                pe_disc += float(int(np.round(ch_pe)))
                nhit_b  += 1
            pe_cont -= dark_noise_pe
            pe_disc -= dark_noise_pe
            if nhit_b > 0:
                if pe_cont > 0:
                    hists['b']['PEcontin'].Fill(pe_cont)
                    hists['b']['PEdiscrete'].Fill(pe_disc)
                hists['b']['nHit'].Fill(nhit_b)

        # ── Fill mode C histograms (inverted ADC ≥ ADC_HIT_MAX, event cut OFF) ──
        if flag_c == 'clean':
            pe_cont = pe_disc = 0.0
            nhit_c = 0
            for chid, adc, tdc in event_hits:
                if chid not in calibration:
                    continue
                if adc < ADC_HIT_MAX:                    # lower bound
                    continue
                if tdc < 0 or tdc < TDC_HIT_MIN or tdc > TDC_HIT_MAX:
                    continue
                ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
                pe_cont += ch_pe
                pe_disc += float(int(np.round(ch_pe)))
                nhit_c  += 1
            pe_cont -= dark_noise_pe
            pe_disc -= dark_noise_pe
            if nhit_c > 0:
                if pe_cont > 0:
                    hists['c']['PEcontin'].Fill(pe_cont)
                    hists['c']['PEdiscrete'].Fill(pe_disc)
                hists['c']['nHit'].Fill(nhit_c)

        # ── Muon bookkeeping (unconditional — must happen AFTER veto assignment)
        # This mirrors extract_charge_calib.py: even an event that is already
        # labelled 'outlier' or 'after_muon' can itself BE a muon and arm the
        # after-muon window for subsequent events.
        if is_muon:
            is_after_muon = True
            sec_mu  = sec
            nsec_mu = nsec
            s['n_muons']     += 1
            s['n_muons_cd']  += int(is_muon_cd)
            s['n_muons_wt']  += int(is_muon_wt)
            s['n_muons_tvt'] += int(is_muon_tvt)

        sec_prev = sec
        nsec_prev = nsec

    print(f"\r  Done: {nentries} events processed" + " " * 30)
    fin.Close()

    return {
        'histograms':    hists,
        'stats_shared':  s,
        'stats_mode':    sm,
        'n_events':      nentries,
        'has_wt':        has_wt,
        'has_tvt':       has_tvt,
    }


# =============================================================================
# WRITE OUTPUT ROOT FILE
# =============================================================================

def write_output(result, outpath, run_number, file_number, calib_file):
    """Write histograms and metadata to a ROOT file."""
    P      = PARAMS_CALIB2
    hists  = result['histograms']
    s      = result['stats_shared']
    sm     = result['stats_mode']

    os.makedirs(os.path.dirname(outpath) or '.', exist_ok=True)
    fout = ROOT.TFile(outpath, "RECREATE")
    fout.cd()

    for mode in ('a', 'b', 'c'):
        for hname, h in hists[mode].items():
            h.Write()

    # ── Metadata ─────────────────────────────────────────────────────────────
    meta = (
        f"RUN={run_number};"
        f"FILE_NUM={file_number};"
        f"CALIB_FILE={os.path.basename(calib_file)};"
        # Veto parameters
        f"MUON_THRESHOLD_CD={P['MUON_THRESHOLD_CD']};"
        f"MUON_THRESHOLD_WT={P['MUON_THRESHOLD_WT']};"
        f"MUON_THRESHOLD_TVT={P['MUON_THRESHOLD_TVT']};"
        f"AFTER_MU={P['AFTER_MU']};"
        f"AFTER_PULSE={P['AFTER_PULSE']};"
        f"MAX_TOTAL_ADC={P['MAX_TOTAL_ADC']};"
        f"MAX_ADC_PER_CHANNEL={P['MAX_ADC_PER_CHANNEL']};"
        f"MIN_NHIT={P['MIN_NHIT']};"
        f"MAX_NHIT={P['MAX_NHIT']};"
        f"TDC_HIT_MIN={P['TDC_HIT_MIN']};"
        f"TDC_HIT_MAX={P['TDC_HIT_MAX']};"
        f"ADC_HIT_MIN={P['ADC_HIT_MIN']};"
        f"ADC_HIT_MAX={P['ADC_HIT_MAX']};"
        f"HAS_WT={int(result['has_wt'])};"
        f"HAS_TVT={int(result['has_tvt'])};"
        # Shared muon counts
        f"N_MUONS={s['n_muons']};"
        f"N_MUONS_CD={s['n_muons_cd']};"
        f"N_MUONS_WT={s['n_muons_wt']};"
        f"N_MUONS_TVT={s['n_muons_tvt']};"
        # Per-mode counts
        + "".join(
            f"N_OUTLIER_{m.upper()}={sm[m]['n_outlier']};"
            f"N_AFTER_MUON_{m.upper()}={sm[m]['n_after_muon']};"
            f"N_AFTER_PULSE_{m.upper()}={sm[m]['n_after_pulse']};"
            f"N_CLEAN_{m.upper()}={sm[m]['n_clean']};"
            for m in ('a', 'b', 'c')
        )
        # Mode descriptions
        f"MODE_A=ADC_HIT_MIN<=ADC<=ADC_HIT_MAX,MAX_TOTAL_ADC_ON;"
        f"MODE_B=ADC>=ADC_HIT_MAX(inverted),MAX_TOTAL_ADC_ON;"
        f"MODE_C=ADC>=ADC_HIT_MAX(inverted),MAX_TOTAL_ADC_OFF;"
        f"N_EVENTS={result['n_events']}"
    )
    ROOT.TNamed("veto_info", meta).Write("veto_info", ROOT.TObject.kOverwrite)

    fout.Write()
    fout.Close()


# =============================================================================
# MAIN
# =============================================================================

def run_exotic(rtraw_file, output_dir, run_number, calib_file_override=None):
    """Full pipeline: select calibration → load → process → save."""
    print("=" * 60)
    print("get_spectrum_exotic.py — tri-mode ADC spectrum")
    print("=" * 60)

    # ── Calibration selection ─────────────────────────────────────────────────
    if calib_file_override:
        calib_file = calib_file_override
        print(f"Using custom calibration file: {calib_file}")
    else:
        calib_file, warn = get_official_calib_file(run_number)
        if warn:
            print(warn)
        print(f"Official calibration: {os.path.basename(calib_file)}")

    print()
    calibration, dark_noise_pe = load_calibration(calib_file)
    print()

    # ── Print veto parameters ─────────────────────────────────────────────────
    P = PARAMS_CALIB2
    print("CALIB2 veto parameters (shared across all modes):")
    print(f"  CD muon threshold      : {P['MUON_THRESHOLD_CD']:.1e} ADC")
    print(f"  WT muon threshold      : {P['MUON_THRESHOLD_WT']} fired channels")
    print(f"  TVT muon threshold     : {P['MUON_THRESHOLD_TVT']} fired channels")
    print(f"  After-muon veto        : {P['AFTER_MU']/1e3:.0f} µs")
    print(f"  After-pulse veto       : {P['AFTER_PULSE']/1e3:.1f} µs")
    print(f"  Max ADC/ch (flasher)   : {P['MAX_ADC_PER_CHANNEL']:.1e}")
    print(f"  nHit range             : [{P['MIN_NHIT']}, {P['MAX_NHIT']}]")
    print(f"  TDC window             : [{P['TDC_HIT_MIN']}, {P['TDC_HIT_MAX']}] ns")
    print(f"  ADC_HIT_MIN            : {P['ADC_HIT_MIN']:.0f}")
    print(f"  ADC_HIT_MAX            : {P['ADC_HIT_MAX']:.1e}")
    print(f"  MAX_TOTAL_ADC          : {P['MAX_TOTAL_ADC']:.1e}  (modes A+B; SKIPPED in C)")
    print()
    print("Mode summary:")
    print("  A — ADC_HIT_MIN ≤ adc ≤ ADC_HIT_MAX + MAX_TOTAL_ADC event cut   [standard]")
    print("  B — adc ≥ ADC_HIT_MAX               + MAX_TOTAL_ADC event cut   [inverted ADC, event-cut ON]")
    print("  C — adc ≥ ADC_HIT_MAX               + no MAX_TOTAL_ADC cut      [inverted ADC, event-cut OFF]")
    print()

    # ── Parse file number from RTRAW name ─────────────────────────────────────
    basename   = os.path.basename(rtraw_file)
    run_match  = re.search(r'RUN\.(\d+)\.', basename)
    parsed_run = run_match.group(1) if run_match else str(run_number)
    file_match = re.search(r'\.(\d{3})_T\d+\.\d+\.\d+.*\.rtraw', basename)
    file_number = file_match.group(1) if file_match else "000"

    print(f"Input : {basename}")
    print(f"RUN   : {parsed_run}   File: {file_number}")
    print()

    # ── Process ───────────────────────────────────────────────────────────────
    result = process_exotic_rtraw(rtraw_file, calibration, dark_noise_pe)
    if result is None:
        print("ERROR: Processing failed.")
        return None

    # ── Statistics summary ────────────────────────────────────────────────────
    s  = result['stats_shared']
    sm = result['stats_mode']
    print()
    print("=" * 60)
    print("Veto statistics")
    print("=" * 60)
    print(f"  Muon events (total)  : {s['n_muons']}")
    print(f"    CD-tagged           : {s['n_muons_cd']}")
    if result['has_wt']:
        print(f"    WT-tagged           : {s['n_muons_wt']}")
    if result['has_tvt']:
        print(f"    TVT-tagged          : {s['n_muons_tvt']}")
    print()
    print(f"{'':4} {'Mode A':>12} {'Mode B':>12} {'Mode C':>12}")
    print(f"{'':4} {'(standard)':>12} {'(inv+cut)':>12} {'(inv-cut)':>12}")
    print("-" * 48)
    for key, label in [('n_outlier', 'Outlier'), ('n_after_muon', 'After-muon'),
                       ('n_after_pulse', 'After-pulse'), ('n_clean', 'CLEAN')]:
        row = f"  {label:<16}"
        for m in ('a', 'b', 'c'):
            row += f" {sm[m][key]:>12d}"
        print(row)
    print()

    # ── Write output ──────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir,
                           f"EXOTIC_spectrum_RUN{parsed_run}_{file_number}.root")
    write_output(result, outpath, parsed_run, file_number, calib_file)

    print("=" * 60)
    print("SUCCESS")
    print(f"Output: {outpath}")
    print("=" * 60)
    return outpath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Exotic tri-mode energy spectrum from RTRAW with full CALIB2 veto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes
-----
  A  standard    ADC_HIT_MIN <= adc <= ADC_HIT_MAX  +  MAX_TOTAL_ADC event cut
  B  inv+cut     adc >= ADC_HIT_MAX (inverted)       +  MAX_TOTAL_ADC event cut
  C  inv-cut     adc >= ADC_HIT_MAX (inverted)       +  NO event ADC cut

Examples
--------
  # Default calibration auto-selected from run number:
  python get_spectrum_exotic.py /path/RUN.1295.xxx.rtraw /path/output --run 1295

  # Override calibration file explicitly:
  python get_spectrum_exotic.py /path/RUN.1295.xxx.rtraw /path/output --run 1295 \\
      --calib-file /path/to/sipm_calib_1295-.txt
""")
    parser.add_argument("rtraw_file",   help="Path to RTRAW file (local or XRootD URL)")
    parser.add_argument("output_dir",   help="Output directory for ROOT file")
    parser.add_argument("--run",        type=int, required=True,
                        help="Run number — used to auto-select official gain calibration")
    parser.add_argument("--calib-file", default=None,
                        help="Override gain calibration TXT file (default: auto from --run)")
    args = parser.parse_args()

    # Allow XRootD URLs without local existence check
    if not args.rtraw_file.startswith("root://") and not os.path.exists(args.rtraw_file):
        print(f"ERROR: RTRAW file not found: {args.rtraw_file}")
        sys.exit(1)

    sys.exit(0 if run_exotic(args.rtraw_file, args.output_dir,
                             args.run, args.calib_file) else 1)
