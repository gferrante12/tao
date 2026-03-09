#!/usr/bin/env python3
"""
extract_qt_2d.py — Comprehensive QT extraction with ADC vs TDC 2D histograms

PURPOSE:
  Extract per-channel ADC, TDC, and ADC-vs-TDC 2D histograms from RTRAW files.
  Designed to help determine optimal ADC and TDC cuts for rejecting high-energy
  events (muons, cosmogenics) while preserving calibration signals (Ge-68, Cs-137).

OUTPUT HISTOGRAMS PER CHANNEL:
  - H_adc_{ch}        : 1D ADC distribution (all hits)
  - H_adc_clean_{ch}  : 1D ADC distribution (after vetoes)
  - H_tdc_{ch}        : 1D TDC distribution (all hits)
  - H_tdc_clean_{ch}  : 1D TDC distribution (after vetoes)
  - H_qt_2d_{ch}      : 2D TDC vs ADC (all hits)
  - H_qt_2d_clean_{ch}: 2D TDC vs ADC (after vetoes)

SUMMARY HISTOGRAMS:
  - H_totalADC        : Total event ADC distribution
  - H_nHit            : Number of fired channels per event
  - H_nChannelsAboveThreshold : Channels with ADC > ADC_HIT_MAX per event
  - H_eventTime       : Event time profile for veto debugging

PHYSICS CONTEXT:
  TAO detector:
    - 8048 SiPM channels
    - Average gain: ~6000 ADC/PE
    - Light yield: ~4300 PE/MeV
    
  Cut guidelines:
    - Per-channel ADC cut at 1e5 ADC ≈ 17 PE (rejects muon deposits)
    - Event total ADC cut at 4e8 ADC ≈ 15 MeV (rejects high-energy events)
    - TDC window [240, 440] ns selects prompt scintillation light

USAGE:
  python extract_qt_2d.py /path/to/RUN.XXXX.rtraw /output/dir [--mode calib2]
  python extract_qt_2d.py /path/to/RUN.XXXX.rtraw /output/dir --n-channels 100

Author: Based on TAOsw 25.7.1 and existing extract_charge_calib.py
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

# =============================================================================
# VETO PARAMETERS (aligned with extract_charge_calib.py CALIB2)
# =============================================================================

# Per-hit cuts
ADC_HIT_MIN = 1000.0    # ADC - remove baseline noise
ADC_HIT_MAX = 1e5       # ADC - reject muon deposits
TDC_HIT_MIN = 240.0     # ns - prompt window start
TDC_HIT_MAX = 440.0     # ns - prompt window end

# Event-level cuts
MUON_THRESHOLD_CD = 8e8     # ADC total
MUON_THRESHOLD_WT = 5       # channels
MUON_THRESHOLD_TVT = 3      # channels
AFTER_MU = 1000e3           # ns (1000 µs)
AFTER_PULSE = 5e3           # ns (5 µs)
MAX_TOTAL_ADC = 8e8         # ADC
MAX_ADC_PER_CHANNEL = 1.7e7 # ADC
MIN_NHIT = 2000
MAX_NHIT = 7000

# Histogram settings
N_CHANNELS = 8048
ADC_NBINS, ADC_MIN, ADC_MAX = 500, 0.0, 150000.0  # Extended range for 2D
TDC_NBINS, TDC_MIN, TDC_MAX = 200, 0.0, 2000.0
ADC_NBINS_2D = 150  # Coarser for 2D to limit file size
TDC_NBINS_2D = 100


def file_exists_or_accessible(path):
    """Check file existence (XRootD URLs always pass)."""
    if path.startswith("root://"):
        return True
    return os.path.exists(path)


def extract_qt_2d(rtraw_file, output_dir, n_channels=100, mode="calib2"):
    """
    Extract comprehensive QT (charge-time) data from RTRAW file.
    
    Args:
        rtraw_file: Path to RTRAW file
        output_dir: Output directory
        n_channels: Number of channels for full 2D histograms (0-N)
        mode: Analysis mode (calib, calib2, physics)
    """
    
    if not file_exists_or_accessible(rtraw_file):
        print(f"ERROR: File not found: {rtraw_file}")
        sys.exit(1)
    
    # Parse run/file info
    basename = os.path.basename(rtraw_file)
    run_match = re.search(r'RUN\.(\d+)\.', basename)
    run_number = run_match.group(1) if run_match else "UNKNOWN"
    file_match = re.search(r'\.(\d{3})_T\d+\.\d+\.\d+.*\.rtraw', basename)
    file_number = file_match.group(1) if file_match else "000"
    
    print("=" * 70)
    print(f"QT 2D Extraction  mode={mode}")
    print("=" * 70)
    print(f"Input  : {rtraw_file}")
    print(f"RUN    : {run_number}   File: {file_number}")
    print(f"Channels for 2D: 0-{n_channels-1}")
    print()
    print(f"Cut parameters:")
    print(f"  ADC per-hit window    : [{ADC_HIT_MIN:.0f}, {ADC_HIT_MAX:.0e}] ADC")
    print(f"  TDC per-hit window    : [{TDC_HIT_MIN:.0f}, {TDC_HIT_MAX:.0f}] ns")
    print(f"  Muon threshold (CD)   : {MUON_THRESHOLD_CD:.1e} ADC")
    print(f"  Max total ADC         : {MAX_TOTAL_ADC:.1e} ADC")
    print(f"  After-muon veto       : {AFTER_MU/1e3:.0f} µs")
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
    
    # Check for WT/TVT detectors
    has_wt, has_tvt = False, False
    wt_elec_tree = wt_trig_tree = None
    tvt_elec_tree = tvt_trig_tree = None
    
    try:
        wt_elec_tree = frtraw.Get("Event/Wt/Elec/WtElecEvt")
        wt_trig_tree = frtraw.Get("Event/Wt/Trig/WtTrigEvt")
        if wt_elec_tree and wt_trig_tree:
            has_wt = True
            print(f"WT detector available ({wt_elec_tree.GetEntries()} events)")
    except:
        pass
    
    try:
        tvt_elec_tree = frtraw.Get("Event/Tvt/Elec/TvtElecEvt")
        tvt_trig_tree = frtraw.Get("Event/Tvt/Trig/TvtTrigEvt")
        if tvt_elec_tree and tvt_trig_tree:
            has_tvt = True
            print(f"TVT detector available ({tvt_elec_tree.GetEntries()} events)")
    except:
        pass
    print()
    
    # ==========================================================================
    # Create histograms
    # ==========================================================================
    
    print("Creating histograms...")
    
    # Per-channel 1D histograms (all channels)
    h_adc_all = []
    h_adc_clean = []
    h_tdc_all = []
    h_tdc_clean = []
    
    for ch in range(N_CHANNELS):
        h_adc_all.append(ROOT.TH1F(f"H_adc_{ch}", f"ADC ch{ch} (all)",
                                    ADC_NBINS, ADC_MIN, ADC_MAX))
        h_adc_clean.append(ROOT.TH1F(f"H_adc_clean_{ch}", f"ADC ch{ch} (clean)",
                                      ADC_NBINS, ADC_MIN, ADC_MAX))
        h_tdc_all.append(ROOT.TH1F(f"H_tdc_{ch}", f"TDC ch{ch} (all)",
                                    TDC_NBINS, TDC_MIN, TDC_MAX))
        h_tdc_clean.append(ROOT.TH1F(f"H_tdc_clean_{ch}", f"TDC ch{ch} (clean)",
                                      TDC_NBINS, TDC_MIN, TDC_MAX))
    
    for h in h_adc_all + h_adc_clean + h_tdc_all + h_tdc_clean:
        h.SetDirectory(0)
    
    # Per-channel 2D histograms (selected channels only)
    h_qt_2d_all = {}
    h_qt_2d_clean = {}
    for ch in range(min(n_channels, N_CHANNELS)):
        h_qt_2d_all[ch] = ROOT.TH2F(
            f"H_qt_2d_{ch}",
            f"TDC vs ADC ch{ch} (all);TDC [ns];ADC [counts]",
            TDC_NBINS_2D, TDC_MIN, TDC_MAX,
            ADC_NBINS_2D, ADC_MIN, ADC_MAX
        )
        h_qt_2d_clean[ch] = ROOT.TH2F(
            f"H_qt_2d_clean_{ch}",
            f"TDC vs ADC ch{ch} (clean);TDC [ns];ADC [counts]",
            TDC_NBINS_2D, TDC_MIN, TDC_MAX,
            ADC_NBINS_2D, ADC_MIN, ADC_MAX
        )
        h_qt_2d_all[ch].SetDirectory(0)
        h_qt_2d_clean[ch].SetDirectory(0)
    
    # Summary histograms
    h_totalADC_all = ROOT.TH1F("H_totalADC_all", "Total event ADC (all)",
                                500, 0, 2e9)
    h_totalADC_clean = ROOT.TH1F("H_totalADC_clean", "Total event ADC (clean)",
                                  500, 0, 2e9)
    h_nHit_all = ROOT.TH1F("H_nHit_all", "nHit per event (all)", 500, 0, 8048)
    h_nHit_clean = ROOT.TH1F("H_nHit_clean", "nHit per event (clean)", 500, 0, 8048)
    h_nChannelsAbove = ROOT.TH1F("H_nChannelsAbove", 
                                  f"Channels with ADC > {ADC_HIT_MAX:.0e}",
                                  100, 0, 100)
    
    # ADC distribution split by cut threshold (for visual cut optimization)
    h_adc_below_cut = ROOT.TH1F("H_adc_below_cut",
                                 f"ADC < {ADC_HIT_MAX:.0e} (all channels)",
                                 500, 0, ADC_HIT_MAX)
    h_adc_above_cut = ROOT.TH1F("H_adc_above_cut",
                                 f"ADC >= {ADC_HIT_MAX:.0e} (all channels)",
                                 200, ADC_HIT_MAX, 2e6)
    
    for h in [h_totalADC_all, h_totalADC_clean, h_nHit_all, h_nHit_clean,
              h_nChannelsAbove, h_adc_below_cut, h_adc_above_cut]:
        h.SetDirectory(0)
    
    print(f"  Created {N_CHANNELS} × 4 per-channel 1D histograms")
    print(f"  Created {n_channels} × 2 per-channel 2D histograms")
    print(f"  Created 7 summary histograms")
    print()
    
    # ==========================================================================
    # Branch setup
    # ==========================================================================
    
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
    
    # ==========================================================================
    # Event loop
    # ==========================================================================
    
    # Statistics
    n_muons = n_muons_cd = n_muons_wt = n_muons_tvt = 0
    n_after_muon = n_after_pulse = n_outlier = n_clean = 0
    total_hits = 0
    
    # Muon tracking
    sec_prev = nsec_prev = 0
    sec_mu = nsec_mu = 0
    is_after_muon = False
    
    print(f"Processing {nentries} events...")
    
    for i in range(nentries):
        if (i + 1) % 10000 == 0:
            print(f"\r  Event {i+1}/{nentries}...", end='', flush=True)
        
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
            dt = (sec - sec_mu) * 1e9 + (nsec - nsec_mu)
            if dt > AFTER_MU:
                is_after_muon = False
        
        # After-pulse flag
        is_after_pulse = False
        if i > 0:
            dt = (sec - sec_prev) * 1e9 + (nsec - nsec_prev)
            if dt < AFTER_PULSE:
                is_after_pulse = True
        
        # Collect channel data
        channels = cd_elec_evt.GetElecChannels()
        tot_adc = 0.0
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
                total_hits += 1
                
                # Check flasher (per-channel saturation)
                if adc_val > MAX_ADC_PER_CHANNEL:
                    has_flasher = True
                
                # Count channels above ADC threshold
                if adc_val >= ADC_HIT_MAX:
                    n_channels_above += 1
                
                tot_adc += adc_val
                n_hit_channels += 1
        
        # Fill ALL histograms (before any cuts)
        h_totalADC_all.Fill(tot_adc)
        h_nHit_all.Fill(n_hit_channels)
        h_nChannelsAbove.Fill(n_channels_above)
        
        for chid, adc_val, tdc_val in event_hits:
            if 0 <= chid < N_CHANNELS:
                h_adc_all[chid].Fill(adc_val)
                h_tdc_all[chid].Fill(tdc_val)
                
                # Fill 2D for selected channels
                if chid in h_qt_2d_all:
                    h_qt_2d_all[chid].Fill(tdc_val, adc_val)
                
                # Global ADC distribution split
                if adc_val < ADC_HIT_MAX:
                    h_adc_below_cut.Fill(adc_val)
                else:
                    h_adc_above_cut.Fill(adc_val)
        
        # =======================================================================
        # Apply veto hierarchy
        # =======================================================================
        
        # Muon tagging
        is_muon = False
        is_muon_cd = tot_adc > MUON_THRESHOLD_CD
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
        
        # Determine veto flag
        veto_flag = None
        
        if has_flasher or tot_adc > MAX_TOTAL_ADC:
            veto_flag = 'outlier'
            n_outlier += 1
        elif n_hit_channels < MIN_NHIT or n_hit_channels > MAX_NHIT:
            veto_flag = 'outlier'
            n_outlier += 1
        elif is_muon:
            veto_flag = 'muon'
        elif is_after_muon:
            veto_flag = 'after_muon'
            n_after_muon += 1
        elif is_after_pulse:
            veto_flag = 'after_pulse'
            n_after_pulse += 1
        else:
            veto_flag = 'clean'
            n_clean += 1
        
        # Fill CLEAN histograms (vetoed events excluded)
        if veto_flag == 'clean':
            h_totalADC_clean.Fill(tot_adc)
            h_nHit_clean.Fill(n_hit_channels)
            
            for chid, adc_val, tdc_val in event_hits:
                if 0 <= chid < N_CHANNELS:
                    h_adc_clean[chid].Fill(adc_val)
                    h_tdc_clean[chid].Fill(tdc_val)
                    
                    if chid in h_qt_2d_clean:
                        h_qt_2d_clean[chid].Fill(tdc_val, adc_val)
        
        # Update muon tracking
        if is_muon:
            is_after_muon = True
            sec_mu = sec
            nsec_mu = nsec
            n_muons += 1
            if is_muon_cd: n_muons_cd += 1
            if is_muon_wt: n_muons_wt += 1
            if is_muon_tvt: n_muons_tvt += 1
        
        sec_prev = sec
        nsec_prev = nsec
    
    print(f"\r  Completed {nentries} events" + " " * 30)
    
    # ==========================================================================
    # Statistics
    # ==========================================================================
    
    print()
    print("=" * 70)
    print("Statistics")
    print("=" * 70)
    print(f"  Total hits processed  : {total_hits:,}")
    print(f"  Muon events (total)   : {n_muons:,}")
    print(f"    - Tagged by CD      : {n_muons_cd:,}")
    if has_wt:
        print(f"    - Tagged by WT      : {n_muons_wt:,}")
    if has_tvt:
        print(f"    - Tagged by TVT     : {n_muons_tvt:,}")
    print(f"  Events after-muon     : {n_after_muon:,}")
    print(f"  Events after-pulse    : {n_after_pulse:,}")
    print(f"  Events outlier        : {n_outlier:,}")
    print(f"  Clean events          : {n_clean:,} ({100*n_clean/nentries:.1f}%)")
    print()
    
    # ==========================================================================
    # Save output
    # ==========================================================================
    
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir,
                                f"QT2D_RUN{run_number}_{file_number}.root")
    
    print(f"Saving to {output_file}")
    fout = ROOT.TFile(output_file, "RECREATE")
    
    # Per-channel 1D histograms
    adc_dir = fout.mkdir("ADC")
    adc_dir.cd()
    for h in h_adc_all:
        h.Write()
    for h in h_adc_clean:
        h.Write()
    
    tdc_dir = fout.mkdir("TDC")
    tdc_dir.cd()
    for h in h_tdc_all:
        h.Write()
    for h in h_tdc_clean:
        h.Write()
    
    # Per-channel 2D histograms
    qt2d_dir = fout.mkdir("QT2D")
    qt2d_dir.cd()
    for h in h_qt_2d_all.values():
        h.Write()
    for h in h_qt_2d_clean.values():
        h.Write()
    
    # Summary histograms
    fout.cd()
    h_totalADC_all.Write()
    h_totalADC_clean.Write()
    h_nHit_all.Write()
    h_nHit_clean.Write()
    h_nChannelsAbove.Write()
    h_adc_below_cut.Write()
    h_adc_above_cut.Write()
    
    # Metadata
    meta = (
        f"RUN={run_number};"
        f"FILE={file_number};"
        f"MODE={mode};"
        f"ADC_HIT_MIN={ADC_HIT_MIN};"
        f"ADC_HIT_MAX={ADC_HIT_MAX};"
        f"TDC_HIT_MIN={TDC_HIT_MIN};"
        f"TDC_HIT_MAX={TDC_HIT_MAX};"
        f"N_EVENTS={nentries};"
        f"N_CLEAN={n_clean};"
        f"N_MUONS={n_muons};"
        f"N_OUTLIER={n_outlier}"
    )
    ROOT.TNamed("extraction_info", meta).Write()
    
    fout.Close()
    frtraw.Close()
    
    print()
    print("=" * 70)
    print("SUCCESS")
    print(f"Output: {output_file}")
    print("=" * 70)
    
    return output_file


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract QT (charge-time) 2D histograms from RTRAW files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full extraction (first 100 channels for 2D)
  python extract_qt_2d.py /path/RUN.1295.xxx.rtraw /output/dir

  # Extended 2D coverage (first 500 channels)
  python extract_qt_2d.py /path/RUN.1295.xxx.rtraw /output/dir --n-channels 500
  
  # Use physics mode parameters
  python extract_qt_2d.py /path/RUN.1295.xxx.rtraw /output/dir --mode physics

Output ROOT file structure:
  /ADC/H_adc_{ch}          - 1D ADC (all hits)
  /ADC/H_adc_clean_{ch}    - 1D ADC (after vetoes)
  /TDC/H_tdc_{ch}          - 1D TDC (all hits)
  /TDC/H_tdc_clean_{ch}    - 1D TDC (after vetoes)
  /QT2D/H_qt_2d_{ch}       - 2D TDC vs ADC (all hits)
  /QT2D/H_qt_2d_clean_{ch} - 2D TDC vs ADC (after vetoes)
  H_totalADC_all/clean     - Event total ADC
  H_nHit_all/clean         - Fired channels per event
  H_nChannelsAbove         - Channels above ADC threshold
  H_adc_below/above_cut    - ADC distribution split by cut
"""
    )
    
    parser.add_argument("rtraw_file", help="Path to RTRAW file")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--n-channels", type=int, default=100,
                        help="Number of channels for 2D histograms (default: 100)")
    parser.add_argument("--mode", choices=["calib", "calib2", "physics"],
                        default="calib2",
                        help="Analysis mode (default: calib2)")
    
    args = parser.parse_args()
    
    extract_qt_2d(args.rtraw_file, args.output_dir,
                  n_channels=args.n_channels, mode=args.mode)
