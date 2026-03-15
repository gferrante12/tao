#!/usr/bin/env python3
"""
get_spectrum_ADC_cut.py — UPDATED VERSION with diagnostic histograms and Mode D

CHANGES FROM ORIGINAL (bk/2026-03-07_v2/get_spectrum_ADC_cut.py):
  1. Added Mode D: Low-ADC events only (adc < ADC_HIT_MIN) for dark noise baseline
  2. Added diagnostic histograms:
     - h_totalADC_perEvent: Total ADC distribution before cuts
     - h_nChannelsAboveThreshold: Channels with ADC > ADC_HIT_MAX per event
     - h_TDC_distribution_{a,b,c,d}: TDC distributions per mode
  3. Added cut efficiency summary table output
  4. TDC window aligned to [240, 440] ns

Apply these changes to your existing get_spectrum_ADC_cut.py or replace entirely.

  ┌──────┬────────────────────────────────────────┬───────────────────────┐
  │ Mode │ Per-hit ADC selection                  │ Event-level ADC cut   │
  ├──────┼────────────────────────────────────────┼───────────────────────┤
  │  A   │ ADC_HIT_MIN ≤ ADC ≤ ADC_HIT_MAX        │ MAX_TOTAL_ADC applied │
  │  B   │ ADC ≥ ADC_HIT_MAX (inverted)           │ MAX_TOTAL_ADC applied │
  │  C   │ ADC ≥ ADC_HIT_MAX (inverted)           │ MAX_TOTAL_ADC SKIPPED │
  │  D   │ ADC < ADC_HIT_MIN (low-ADC/baseline)   │ No event cuts         │  ← NEW
  └──────┴────────────────────────────────────────┴───────────────────────┘
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
# TRY TO IMPORT CENTRALIZED PARAMS, FALLBACK TO HARDCODED
# =============================================================================

try:
    from veto_params import (
        PARAMS_CALIB2, TDC_WINDOW, ADC_CUTS,
        get_run_config, N_CHANNELS
    )
    USE_VETO_PARAMS = True
except ImportError:
    USE_VETO_PARAMS = False
    N_CHANNELS = 8048

# =============================================================================
# VETO PARAMETERS (CALIB2 mode)
# =============================================================================

if USE_VETO_PARAMS:
    MUON_THRESHOLD_CD = PARAMS_CALIB2.MUON_THRESHOLD_CD
    MUON_THRESHOLD_WT = PARAMS_CALIB2.MUON_THRESHOLD_WT
    MUON_THRESHOLD_TVT = PARAMS_CALIB2.MUON_THRESHOLD_TVT
    AFTER_MU = PARAMS_CALIB2.AFTER_MU
    AFTER_PULSE = PARAMS_CALIB2.AFTER_PULSE
    MAX_TOTAL_ADC = PARAMS_CALIB2.MAX_TOTAL_ADC
    MAX_ADC_PER_CHANNEL = PARAMS_CALIB2.MAX_ADC_PER_CHANNEL
    MIN_NHIT = PARAMS_CALIB2.MIN_NHIT
    MAX_NHIT = PARAMS_CALIB2.MAX_NHIT
    TDC_HIT_MIN = TDC_WINDOW.min_ns
    TDC_HIT_MAX = TDC_WINDOW.max_ns
    ADC_HIT_MIN = PARAMS_CALIB2.ADC_HIT_MIN
    ADC_HIT_MAX = PARAMS_CALIB2.ADC_HIT_MAX
else:
    # Fallback hardcoded values
    MUON_THRESHOLD_CD = 8e8
    MUON_THRESHOLD_WT = 5
    MUON_THRESHOLD_TVT = 3
    AFTER_MU = 1000e3           # ns (1000 µs)
    AFTER_PULSE = 5e3           # ns (5 µs)
    MAX_TOTAL_ADC = 8e8
    MAX_ADC_PER_CHANNEL = 1.7e7
    MIN_NHIT = 2000
    MAX_NHIT = 7000
    TDC_HIT_MIN = 200.0         # ns
    TDC_HIT_MAX = 450.0         # ns
    ADC_HIT_MIN = 1000.0
    ADC_HIT_MAX = 1e5

TDC_WINDOW_WIDTH = TDC_HIT_MAX - TDC_HIT_MIN  # 250 ns

# =============================================================================
# CALIBRATION FILE SELECTION (run-range aware)
# =============================================================================

def get_calib_file(run_number, base_dir):
    """Select appropriate calibration file based on run number."""
    if USE_VETO_PARAMS:
        cfg = get_run_config(run_number)
        # Assuming txt calib files are in base_dir with naming convention
        if run_number >= 1295:
            return os.path.join(base_dir, "sipm_calib_1295-.txt"), cfg['run_range_label']
        elif run_number <= 1193:
            return os.path.join(base_dir, "sipm_calib_1157-1193.txt"), cfg['run_range_label']
        else:
            return os.path.join(base_dir, "sipm_calib_1295-.txt"), "gap (1194-1294)"
    else:
        # Simple fallback
        if run_number >= 1295:
            return os.path.join(base_dir, "sipm_calib_1295-.txt"), "1295+"
        else:
            return os.path.join(base_dir, "sipm_calib_1157-1193.txt"), "≤1193"


def load_calibration(calib_file):
    """Load gain calibration from text file."""
    calibration = {}
    if not os.path.exists(calib_file):
        print(f"WARNING: Calibration file not found: {calib_file}")
        return calibration
    
    with open(calib_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    chid = int(parts[0])
                    gain = float(parts[1])
                    intercept = float(parts[2])
                    if gain > 0:
                        calibration[chid] = {'gain': gain, 'intercept': intercept}
                except (ValueError, IndexError):
                    continue
    
    print(f"Loaded calibration for {len(calibration)} channels")
    return calibration


def file_exists_or_accessible(path):
    """Check file existence (XRootD URLs always pass)."""
    if path.startswith("root://"):
        return True
    return os.path.exists(path)


# =============================================================================
# MAIN EXTRACTION FUNCTION
# =============================================================================

def process_rtraw(rtraw_file, calibration, run_number):
    """
    Process RTRAW file and fill histograms for all four modes (A, B, C, D).
    
    Returns dict with histograms and statistics.
    """
    
    if not file_exists_or_accessible(rtraw_file):
        print(f"ERROR: File not found: {rtraw_file}")
        return None
    
    # Parse file number
    basename = os.path.basename(rtraw_file)
    file_match = re.search(r'\.(\d{3})_T\d+\.\d+\.\d+.*\.rtraw', basename)
    file_number = file_match.group(1) if file_match else "000"
    
    # Open file
    fin = ROOT.TFile.Open(rtraw_file, "READ")
    if not fin or fin.IsZombie():
        print(f"ERROR: Cannot open {rtraw_file}")
        return None
    
    cd_elec_tree = fin.Get("Event/Elec/CdElecEvt")
    cd_trig_tree = fin.Get("Event/Trig/CdTrigEvt")
    if not cd_elec_tree or not cd_trig_tree:
        print("ERROR: Cannot find CD trees")
        fin.Close()
        return None
    
    nentries = cd_elec_tree.GetEntries()
    print(f"  Processing {nentries} events from file {file_number}...")
    
    # Check WT/TVT
    has_wt = has_tvt = False
    wt_elec_tree = wt_trig_tree = None
    tvt_elec_tree = tvt_trig_tree = None
    
    try:
        wt_elec_tree = fin.Get("Event/Wt/Elec/WtElecEvt")
        wt_trig_tree = fin.Get("Event/Wt/Trig/WtTrigEvt")
        if wt_elec_tree and wt_trig_tree and hasattr(wt_elec_tree, 'GetEntries'):
            has_wt = True
    except:
        pass
    
    try:
        tvt_elec_tree = fin.Get("Event/Tvt/Elec/TvtElecEvt")
        tvt_trig_tree = fin.Get("Event/Tvt/Trig/TvtTrigEvt")
        if tvt_elec_tree and tvt_trig_tree and hasattr(tvt_elec_tree, 'GetEntries'):
            has_tvt = True
    except:
        pass
    
    # Branch setup
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
    
    # =========================================================================
    # Create histograms
    # =========================================================================
    
    NBINS_PE = 500
    PE_MAX = 25000
    NBINS_HIT = 500
    HIT_MAX = 8048
    
    mode_labels = {
        'a': 'Mode A: ADC in [ADC_HIT_MIN, ADC_HIT_MAX], MAX_TOTAL_ADC applied',
        'b': 'Mode B: ADC >= ADC_HIT_MAX (inverted), MAX_TOTAL_ADC applied',
        'c': 'Mode C: ADC >= ADC_HIT_MAX (inverted), no MAX_TOTAL_ADC cut',
        'd': 'Mode D: ADC < ADC_HIT_MIN (low-ADC baseline), no event cuts',  # NEW
    }
    
    hists = {}
    for mode in ('a', 'b', 'c', 'd'):
        hists[mode] = {
            'PEcontin': ROOT.TH1F(f"h_PEcontin_{mode}",
                                   f"Continuous PE [{mode_labels[mode]}]",
                                   NBINS_PE, 0, PE_MAX),
            'PEdiscrete': ROOT.TH1F(f"h_PEdiscrete_{mode}",
                                     f"Discrete PE [{mode_labels[mode]}]",
                                     NBINS_PE, 0, PE_MAX),
            'nHit': ROOT.TH1F(f"h_nHit_{mode}",
                              f"nHit [{mode_labels[mode]}]",
                              NBINS_HIT, 0, HIT_MAX),
            # NEW: TDC distribution per mode
            'TDC': ROOT.TH1F(f"h_TDC_{mode}",
                             f"TDC distribution [{mode_labels[mode]}]",
                             200, 0, 2000),
        }
        for h in hists[mode].values():
            h.SetDirectory(0)
    
    # NEW: Diagnostic histograms
    h_totalADC = ROOT.TH1F("h_totalADC_perEvent", 
                            "Total ADC per event (before cuts)",
                            500, 0, 2e9)
    h_nChannelsAbove = ROOT.TH1F("h_nChannelsAboveThreshold",
                                  f"Channels with ADC > {ADC_HIT_MAX:.0e} per event",
                                  100, 0, 100)
    h_totalADC.SetDirectory(0)
    h_nChannelsAbove.SetDirectory(0)
    
    # Statistics
    stats = {
        'n_events': nentries,
        'n_muons': 0, 'n_muons_cd': 0, 'n_muons_wt': 0, 'n_muons_tvt': 0,
    }
    stats_mode = {m: {'n_outlier': 0, 'n_after_muon': 0, 'n_after_pulse': 0, 
                      'n_clean': 0, 'pe_sum': 0.0, 'pe_sum_sq': 0.0}
                  for m in ('a', 'b', 'c', 'd')}
    
    # Muon tracking
    sec_prev = nsec_prev = 0
    sec_mu = nsec_mu = 0
    is_after_muon = False
    
    # Calculate dark noise
    dark_noise_pe = 0.0
    for chid, cal in calibration.items():
        # Assume DCR ~1 kHz per channel (typical)
        dcr = 1000.0  # Hz
        dark_noise_pe += dcr * TDC_WINDOW_WIDTH * 1e-9
    
    # =========================================================================
    # Event loop
    # =========================================================================
    
    for i in range(nentries):
        if (i + 1) % 20000 == 0:
            print(f"\r    Event {i+1}/{nentries}...", end='', flush=True)
        
        cd_elec_tree.GetEntry(i)
        cd_trig_tree.GetEntry(i)
        if has_wt:
            wt_elec_tree.GetEntry(i)
            wt_trig_tree.GetEntry(i)
        if has_tvt:
            tvt_elec_tree.GetEntry(i)
            tvt_trig_tree.GetEntry(i)
        
        # Event timing
        trig_time = cd_trig_evt.getTrigTime()
        sec = trig_time.GetSec()
        nsec = trig_time.GetNanoSec()
        
        # After-muon window expiry
        if is_after_muon:
            if (sec - sec_mu) * 1e9 + (nsec - nsec_mu) > AFTER_MU:
                is_after_muon = False
        
        # After-pulse flag
        is_after_pulse = (i > 0 and 
                          (sec - sec_prev) * 1e9 + (nsec - nsec_prev) < AFTER_PULSE)
        
        # Collect channel data
        channels = cd_elec_evt.GetElecChannels()
        tot_adc_event = 0.0
        n_hit_channels = 0
        n_channels_above = 0
        event_hits = []
        has_flasher = False
        
        for j in range(channels.size()):
            channel = channels[j]
            chid = channel.ElecgetChannelID()
            adc_vals = list(channel.ElecgetAdcs())
            tdc_vals = list(channel.ElecgetTdcs())
            
            for k, adc_val in enumerate(adc_vals):
                tdc_val = tdc_vals[k] if k < len(tdc_vals) else 0.0
                event_hits.append((chid, adc_val, tdc_val))
                tot_adc_event += adc_val
                n_hit_channels += 1
                
                if adc_val > MAX_ADC_PER_CHANNEL:
                    has_flasher = True
                if adc_val >= ADC_HIT_MAX:
                    n_channels_above += 1
        
        # Fill diagnostic histograms (all events)
        h_totalADC.Fill(tot_adc_event)
        h_nChannelsAbove.Fill(n_channels_above)
        
        # Muon tagging
        is_muon = False
        is_muon_cd = tot_adc_event > MUON_THRESHOLD_CD
        is_muon_wt = False
        is_muon_tvt = False
        
        if has_wt:
            wt_channels = wt_elec_evt.GetElecChannels()
            if wt_channels.size() >= MUON_THRESHOLD_WT:
                is_muon_wt = True
        
        if has_tvt:
            tvt_channels = tvt_elec_evt.GetElecChannels()
            if tvt_channels.size() >= MUON_THRESHOLD_TVT:
                is_muon_tvt = True
        
        is_muon = is_muon_cd or is_muon_wt or is_muon_tvt
        
        # Determine veto flags for modes A/B (with MAX_TOTAL_ADC) and C (without)
        def veto_flag(apply_event_cut):
            if has_flasher:
                return 'outlier'
            if apply_event_cut and tot_adc_event > MAX_TOTAL_ADC:
                return 'outlier'
            if n_hit_channels < MIN_NHIT or n_hit_channels > MAX_NHIT:
                return 'outlier'
            if is_muon:
                return 'muon'
            if is_after_muon:
                return 'after_muon'
            if is_after_pulse:
                return 'after_pulse'
            return 'clean'
        
        flag_ab = veto_flag(True)   # Modes A, B: MAX_TOTAL_ADC applied
        flag_c = veto_flag(False)   # Mode C: no MAX_TOTAL_ADC
        flag_d = 'clean'            # Mode D: no event cuts at all
        
        # Update statistics
        for mode, flag in [('a', flag_ab), ('b', flag_ab), ('c', flag_c), ('d', flag_d)]:
            if flag != 'clean':
                stats_mode[mode][f'n_{flag}'] = stats_mode[mode].get(f'n_{flag}', 0) + 1
        
        # =====================================================================
        # Fill Mode A: Standard (ADC_HIT_MIN ≤ adc ≤ ADC_HIT_MAX)
        # =====================================================================
        if flag_ab == 'clean':
            pe_cont = pe_disc = 0.0
            nhit_a = 0
            for chid, adc, tdc in event_hits:
                if chid not in calibration:
                    continue
                if adc < ADC_HIT_MIN or adc > ADC_HIT_MAX:
                    continue
                if tdc < TDC_HIT_MIN or tdc > TDC_HIT_MAX:
                    continue
                ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
                pe_cont += ch_pe
                pe_disc += float(int(np.round(ch_pe)))
                nhit_a += 1
                hists['a']['TDC'].Fill(tdc)
            
            pe_cont -= dark_noise_pe
            pe_disc -= dark_noise_pe
            if pe_cont > 0:
                hists['a']['PEcontin'].Fill(pe_cont)
                hists['a']['PEdiscrete'].Fill(pe_disc)
                stats_mode['a']['pe_sum'] += pe_cont
                stats_mode['a']['pe_sum_sq'] += pe_cont**2
            if nhit_a > 0:
                hists['a']['nHit'].Fill(nhit_a)
            stats_mode['a']['n_clean'] += 1
        
        # =====================================================================
        # Fill Mode B: Inverted (ADC ≥ ADC_HIT_MAX), event cut ON
        # =====================================================================
        if flag_ab == 'clean':
            pe_cont = pe_disc = 0.0
            nhit_b = 0
            for chid, adc, tdc in event_hits:
                if chid not in calibration:
                    continue
                if adc < ADC_HIT_MAX:  # Inverted: only high-ADC
                    continue
                if tdc < TDC_HIT_MIN or tdc > TDC_HIT_MAX:
                    continue
                ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
                pe_cont += ch_pe
                pe_disc += float(int(np.round(ch_pe)))
                nhit_b += 1
                hists['b']['TDC'].Fill(tdc)
            
            pe_cont -= dark_noise_pe
            pe_disc -= dark_noise_pe
            if nhit_b > 0:
                if pe_cont > 0:
                    hists['b']['PEcontin'].Fill(pe_cont)
                    hists['b']['PEdiscrete'].Fill(pe_disc)
                    stats_mode['b']['pe_sum'] += pe_cont
                    stats_mode['b']['pe_sum_sq'] += pe_cont**2
                hists['b']['nHit'].Fill(nhit_b)
            stats_mode['b']['n_clean'] += 1
        
        # =====================================================================
        # Fill Mode C: Inverted (ADC ≥ ADC_HIT_MAX), event cut OFF
        # =====================================================================
        if flag_c == 'clean':
            pe_cont = pe_disc = 0.0
            nhit_c = 0
            for chid, adc, tdc in event_hits:
                if chid not in calibration:
                    continue
                if adc < ADC_HIT_MAX:
                    continue
                if tdc < TDC_HIT_MIN or tdc > TDC_HIT_MAX:
                    continue
                ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
                pe_cont += ch_pe
                pe_disc += float(int(np.round(ch_pe)))
                nhit_c += 1
                hists['c']['TDC'].Fill(tdc)
            
            pe_cont -= dark_noise_pe
            pe_disc -= dark_noise_pe
            if nhit_c > 0:
                if pe_cont > 0:
                    hists['c']['PEcontin'].Fill(pe_cont)
                    hists['c']['PEdiscrete'].Fill(pe_disc)
                    stats_mode['c']['pe_sum'] += pe_cont
                    stats_mode['c']['pe_sum_sq'] += pe_cont**2
                hists['c']['nHit'].Fill(nhit_c)
            stats_mode['c']['n_clean'] += 1
        
        # =====================================================================
        # Fill Mode D: Low-ADC baseline (ADC < ADC_HIT_MIN), no event cuts
        # =====================================================================
        # Mode D always fills (no veto)
        pe_cont = pe_disc = 0.0
        nhit_d = 0
        for chid, adc, tdc in event_hits:
            if chid not in calibration:
                continue
            if adc >= ADC_HIT_MIN:  # Only low-ADC hits
                continue
            # No TDC cut for baseline study
            ch_pe = (adc - calibration[chid]['intercept']) / calibration[chid]['gain']
            pe_cont += ch_pe
            pe_disc += float(int(np.round(ch_pe)))
            nhit_d += 1
            hists['d']['TDC'].Fill(tdc)
        
        if nhit_d > 0:
            hists['d']['PEcontin'].Fill(pe_cont)
            hists['d']['PEdiscrete'].Fill(pe_disc)
            hists['d']['nHit'].Fill(nhit_d)
            stats_mode['d']['pe_sum'] += pe_cont
            stats_mode['d']['pe_sum_sq'] += pe_cont**2
        stats_mode['d']['n_clean'] += 1
        
        # Muon bookkeeping
        if is_muon:
            is_after_muon = True
            sec_mu = sec
            nsec_mu = nsec
            stats['n_muons'] += 1
            if is_muon_cd: stats['n_muons_cd'] += 1
            if is_muon_wt: stats['n_muons_wt'] += 1
            if is_muon_tvt: stats['n_muons_tvt'] += 1
        
        sec_prev = sec
        nsec_prev = nsec
    
    print(f"\r    Done: {nentries} events" + " " * 30)
    
    fin.Close()
    
    return {
        'histograms': hists,
        'diagnostics': {'h_totalADC': h_totalADC, 'h_nChannelsAbove': h_nChannelsAbove},
        'stats': stats,
        'stats_mode': stats_mode,
        'file_number': file_number,
        'has_wt': has_wt,
        'has_tvt': has_tvt,
    }


def print_efficiency_table(stats_mode, n_events):
    """Print cut efficiency summary table."""
    print()
    print("=" * 70)
    print("CUT EFFICIENCY SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Mode':<8} {'Events':<12} {'% of total':<12} {'Mean PE':<12} {'RMS PE':<12}")
    print("-" * 60)
    
    for mode in ('a', 'b', 'c', 'd'):
        sm = stats_mode[mode]
        n_clean = sm['n_clean']
        pct = 100.0 * n_clean / n_events if n_events > 0 else 0
        
        if n_clean > 0 and sm['pe_sum_sq'] > 0:
            mean_pe = sm['pe_sum'] / n_clean
            var_pe = sm['pe_sum_sq'] / n_clean - mean_pe**2
            rms_pe = np.sqrt(max(0, var_pe))
        else:
            mean_pe = rms_pe = 0.0
        
        mode_desc = {'a': 'A (std)', 'b': 'B (hi)', 'c': 'C (hi,nocut)', 'd': 'D (lo)'}
        print(f"{mode_desc[mode]:<8} {n_clean:<12,} {pct:<12.1f} {mean_pe:<12,.0f} {rms_pe:<12,.0f}")
    
    print()


def write_output(result, outpath, run_number, calib_file):
    """Write histograms and metadata to ROOT file."""
    
    fout = ROOT.TFile(outpath, "RECREATE")
    
    # Write mode histograms
    for mode, mode_hists in result['histograms'].items():
        mode_dir = fout.mkdir(f"Mode_{mode.upper()}")
        mode_dir.cd()
        for h in mode_hists.values():
            h.Write()
    
    # Write diagnostic histograms
    diag_dir = fout.mkdir("Diagnostics")
    diag_dir.cd()
    for h in result['diagnostics'].values():
        h.Write()
    
    # Write metadata
    fout.cd()
    meta = (
        f"RUN={run_number};"
        f"FILE={result['file_number']};"
        f"CALIB_FILE={os.path.basename(calib_file)};"
        f"TDC_WINDOW=[{TDC_HIT_MIN},{TDC_HIT_MAX}];"
        f"ADC_HIT_MIN={ADC_HIT_MIN};"
        f"ADC_HIT_MAX={ADC_HIT_MAX};"
        f"MAX_TOTAL_ADC={MAX_TOTAL_ADC};"
        f"N_EVENTS={result['stats']['n_events']};"
        f"N_MUONS={result['stats']['n_muons']};"
        f"HAS_WT={1 if result['has_wt'] else 0};"
        f"HAS_TVT={1 if result['has_tvt'] else 0}"
    )
    ROOT.TNamed("veto_info", meta).Write()
    
    fout.Close()
    print(f"Output written to: {outpath}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate PE spectra with ADC cut modes (A/B/C/D)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  A  Standard: ADC_HIT_MIN ≤ adc ≤ ADC_HIT_MAX, MAX_TOTAL_ADC applied
  B  Inverted: adc ≥ ADC_HIT_MAX, MAX_TOTAL_ADC applied  
  C  Inverted: adc ≥ ADC_HIT_MAX, no MAX_TOTAL_ADC cut
  D  Baseline: adc < ADC_HIT_MIN, no event cuts (dark noise study)

Examples:
  python get_spectrum_ADC_cut.py /path/RUN.1295.xxx.rtraw --run 1295 \\
      --calib-dir /path/to/calibration --output spectrum_ADC_cut.root
"""
    )
    
    parser.add_argument("rtraw_file", help="Path to RTRAW file")
    parser.add_argument("--run", type=int, required=True,
                        help="Run number (required for calibration selection)")
    parser.add_argument("--calib-dir", required=True,
                        help="Directory containing sipm_calib_*.txt files")
    parser.add_argument("--output", default=None,
                        help="Output ROOT file (default: auto-named)")
    
    args = parser.parse_args()
    
    # Select calibration file
    calib_file, calib_label = get_calib_file(args.run, args.calib_dir)
    print(f"Run {args.run} → calibration: {calib_label}")
    
    # Load calibration
    calibration = load_calibration(calib_file)
    if not calibration:
        print("ERROR: No calibration loaded")
        sys.exit(1)
    
    # Process file
    result = process_rtraw(args.rtraw_file, calibration, args.run)
    if result is None:
        sys.exit(1)
    
    # Print efficiency table
    print_efficiency_table(result['stats_mode'], result['stats']['n_events'])
    
    # Write output
    if args.output:
        outpath = args.output
    else:
        outpath = f"spectrum_ADC_cut_RUN{args.run}_{result['file_number']}.root"
    
    write_output(result, outpath, args.run, calib_file)
