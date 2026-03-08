#!/usr/bin/env python3
"""
extract_charge_calib.py - Extract ADC histograms with multi-detector veto
Simplified for gain calibration: No ChargeTree, no TDC histograms

Implements veto logic with multi-detector muon tagging:
- CD: Total ADC > threshold
- WT: Number of fired PMTs > threshold  
- TVT: Number of fired channels > threshold
- After-muon veto: configurable
- After-pulse veto: configurable
- Outlier removal: total ADC, nHit, flasher cuts
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

def file_exists_or_accessible(file_path):
    """
    Check if file exists (works for both local paths and XRootD URLs)
    For XRootD URLs, we skip the check and let ROOT handle it
    """
    if file_path.startswith("root://"):
        # For XRootD URLs, skip existence check - ROOT will handle it
        return True
    else:
        # Local file - check normally
        return os.path.exists(file_path)

# =============================================================================
# VETO PARAMETERS (mode-dependent)
# =============================================================================
PARAMS_CALIB = {
    "MUON_THRESHOLD_CD": 8e8,
    "MUON_THRESHOLD_WT": 5,
    "MUON_THRESHOLD_TVT": 3,
    "AFTER_MU": 1000e3,  # 1000 µs
    "AFTER_PULSE": 5e3,  # 5 µs
    "MAX_TOTAL_ADC": 8e8,
    "MAX_ADC_PER_CHANNEL": 1.7e7,
    "MIN_NHIT": 2000,
    "MAX_NHIT": 7000,
}

PARAMS_PHYSICS = {
    "MUON_THRESHOLD_CD": 5.4e8,
    "MUON_THRESHOLD_WT": 15,
    "MUON_THRESHOLD_TVT": 4,
    "AFTER_MU": 1000e3,
    "AFTER_PULSE": 5e3,
    "MAX_TOTAL_ADC": 8e8,
    "MAX_ADC_PER_CHANNEL": 1.7e7,
    "MIN_NHIT": 100,
    "MAX_NHIT": 5500,
}

PARAMS_IBD = {
    "MUON_THRESHOLD_CD": 8e8,
    "MUON_THRESHOLD_WT": 11,
    "MUON_THRESHOLD_TVT": 4,
    "AFTER_MU": 100e3,
    "AFTER_PULSE": 2.5e3,
    "MAX_TOTAL_ADC": 5e8,
    "MAX_ADC_PER_CHANNEL": 1.68e7,
    "MIN_NHIT": 500,
    "MAX_NHIT": 7000,
}

DEFAULT_RADIAL_CUT_MM = 200.0

# =============================================================================
# LOAD RECONSTRUCTION POSITIONS
# =============================================================================
def load_reconstruction_positions(rec_file):
    """Load reconstructed positions from quick_reco output"""
    if not file_exists_or_accessible(rec_file):
        print(f"ERROR: Reconstruction file does not exist: {rec_file}")
        sys.exit(1)

    print(f"Loading reconstruction positions from {rec_file}")
    frec = ROOT.TFile.Open(rec_file, "READ")
    if not frec or frec.IsZombie():
        print(f"ERROR: Cannot open reconstruction file")
        sys.exit(1)

    tree_rec = frec.Get("RecEvt")
    if not tree_rec:
        tree_rec = frec.Get("RECEVT/RecEvt")
    if not tree_rec:
        print(f"ERROR: Cannot find RecEvt tree")
        frec.Close()
        sys.exit(1)

    nrec_entries = tree_rec.GetEntries()
    print(f"Found {nrec_entries} reconstructed events")

    evtID = np.zeros(1, dtype=int)
    fCCRecX = np.zeros(1, dtype=float)
    fCCRecY = np.zeros(1, dtype=float)
    fCCRecZ = np.zeros(1, dtype=float)
    fCCRecR = np.zeros(1, dtype=float)

    tree_rec.SetBranchAddress("evtID", evtID)
    tree_rec.SetBranchAddress("fCCRecX", fCCRecX)
    tree_rec.SetBranchAddress("fCCRecY", fCCRecY)
    tree_rec.SetBranchAddress("fCCRecZ", fCCRecZ)
    tree_rec.SetBranchAddress("fCCRecR", fCCRecR)

    positions = {}
    for i in range(nrec_entries):
        tree_rec.GetEntry(i)
        positions[evtID[0]] = {
            'x': fCCRecX[0],
            'y': fCCRecY[0],
            'z': fCCRecZ[0],
            'r': fCCRecR[0]
        }

    frec.Close()
    print(f"Loaded positions for {len(positions)} events")
    return positions

# =============================================================================
# MAIN EXTRACTION FUNCTION
# =============================================================================
def extract_charge_data(rtraw_file, output_dir, 
                       apply_spatial_cut=False, 
                       rec_file=None, 
                       radial_cut=DEFAULT_RADIAL_CUT_MM,
                       mode="calib",
                       save_tdc_adc=False,
                       tdc_adc_channels=40):
    """
    Extract ADC histograms with multi-detector veto and outlier removal.
    Simplified: outputs only ADC histograms needed for gain calibration.
    """

    if not file_exists_or_accessible(rtraw_file):
        print(f"ERROR: Input file does not exist: {rtraw_file}")
        sys.exit(1)

    # Load parameters based on mode
    if mode == "calib":
        params = PARAMS_CALIB
    elif mode == "physics":
        params = PARAMS_PHYSICS
    elif mode == "ibd":
        params = PARAMS_IBD
    else:
        raise ValueError(f"Unknown mode: {mode}")

    MUON_THRESHOLD_CD = params["MUON_THRESHOLD_CD"]
    MUON_THRESHOLD_WT = params["MUON_THRESHOLD_WT"]
    MUON_THRESHOLD_TVT = params["MUON_THRESHOLD_TVT"]
    AFTER_MU = params["AFTER_MU"]
    AFTER_PULSE = params["AFTER_PULSE"]
    MAX_TOTAL_ADC = params["MAX_TOTAL_ADC"]
    MAX_ADC_PER_CHANNEL = params["MAX_ADC_PER_CHANNEL"]
    MIN_NHIT = params["MIN_NHIT"]
    MAX_NHIT = params["MAX_NHIT"]

    # Load reconstruction positions if needed
    if apply_spatial_cut:
        if not rec_file:
            print(f"ERROR: --rec-file required with --apply-spatial-cut")
            sys.exit(1)
        positions = load_reconstruction_positions(rec_file)
    else:
        positions = None

    # Extract RUN number and file number from TAO DAQ format
    # Format: RUN.NNNN.TAODAQ.TEST.ds-0.mix_stream.TIMESTAMP.FFF_VERSION.rtraw
    basename = os.path.basename(rtraw_file)

    # Extract RUN number (after RUN. and before next dot)
    run_match = re.search(r'RUN\.(\d+)\.', basename)
    if run_match:
        run_number = run_match.group(1)
    else:
        print(f"WARNING: Could not parse RUN number from: {basename}")
        run_number = "UNKNOWN"

    # Extract file number - handle both T25.6.4 and T25.7.1 formats
    # Format 1: .001_T25.6.4.rtraw
    # Format 2: .001_T25.7.1_T25.7.1.rtraw
    file_match = re.search(r'\.(\d{3})_T\d+\.\d+\.\d+.*\.rtraw', basename)

    if file_match:
        file_number = file_match.group(1)
    else:
        print(f"WARNING: Could not parse file number from: {basename}")
        file_number = "000"

    print("=" * 60)
    print(f"Extracting charge data with veto & outlier removal")
    if apply_spatial_cut:
        print(f"SPATIAL CUT ENABLED (Calibration mode)")
    print("=" * 60)
    print(f"Input: {rtraw_file}")
    print(f"RUN: {run_number}, File: {file_number}")
    print("=" * 60)
    print("Veto parameters:")
    print(f"  CD muon threshold: {MUON_THRESHOLD_CD:.0e} ADC")
    print(f"  WT muon threshold: {MUON_THRESHOLD_WT} PMTs")
    print(f"  TVT muon threshold: {MUON_THRESHOLD_TVT} channels")
    print(f"  After-muon veto: {AFTER_MU/1e3:.1f} µs")
    print(f"  After-pulse veto: {AFTER_PULSE/1e3:.1f} µs")
    print("Outlier removal cuts:")
    print(f"  Max total ADC: {MAX_TOTAL_ADC:.1e}")
    print(f"  Max ADC/channel: {MAX_ADC_PER_CHANNEL:.0f}")
    print(f"  nHit range: {MIN_NHIT} - {MAX_NHIT}")
    if apply_spatial_cut:
        print("Spatial cut:")
        print(f"  Radial cut: R < {radial_cut} mm")
    print()

    # Open RTRAW file
    frtraw = ROOT.TFile.Open(rtraw_file, "READ")
    if not frtraw or frtraw.IsZombie():
        print(f"ERROR: Cannot open RTRAW file")
        sys.exit(1)

    # CD (required)
    cd_elec_tree = frtraw.Get("Event/Elec/CdElecEvt")
    cd_trig_tree = frtraw.Get("Event/Trig/CdTrigEvt")

    if not cd_elec_tree or not cd_trig_tree:
        print("ERROR: Cannot find CD trees")
        frtraw.Close()
        sys.exit(1)

    nentries = cd_elec_tree.GetEntries()
    print(f"Found {nentries} CD events")

    # WT (optional)
    try:
        wt_elec_tree = frtraw.Get("Event/Wt/Elec/WtElecEvt")
        wt_trig_tree = frtraw.Get("Event/Wt/Trig/WtTrigEvt")
        if (wt_elec_tree and wt_trig_tree and 
            hasattr(wt_elec_tree, 'GetEntries') and hasattr(wt_trig_tree, 'GetEntries')):
            nwt = wt_elec_tree.GetEntries()
            print(f"WT detector available ({nwt} events)")
            has_wt = True
        else:
            has_wt = False
            wt_elec_tree = None
            wt_trig_tree = None
    except:
        has_wt = False
        wt_elec_tree = None
        wt_trig_tree = None

    if not has_wt:
        print("WT detector NOT AVAILABLE")

    # TVT (optional)
    try:
        tvt_elec_tree = frtraw.Get("Event/Tvt/Elec/TvtElecEvt")
        tvt_trig_tree = frtraw.Get("Event/Tvt/Trig/TvtTrigEvt")
        if (tvt_elec_tree and tvt_trig_tree and 
            hasattr(tvt_elec_tree, 'GetEntries') and hasattr(tvt_trig_tree, 'GetEntries')):
            ntvt = tvt_elec_tree.GetEntries()
            print(f"TVT detector available ({ntvt} events)")
            has_tvt = True
        else:
            has_tvt = False
            tvt_elec_tree = None
            tvt_trig_tree = None
    except:
        has_tvt = False
        tvt_elec_tree = None
        tvt_trig_tree = None

    if not has_tvt:
        print("TVT detector NOT AVAILABLE")
    print()

    # =============================================================================
    # Configuration
    # =============================================================================
    N_CHANNELS = 8048
    NBINS = 500
    XMIN = 0.0
    XMAX = 50000.0

    # Create ADC histograms (2 tiers: Raw, Clean)
    print(f"Creating {N_CHANNELS} ADC histograms (raw + clean)...")
    hists_adc_raw = [ROOT.TH1F(f"H_adcraw_{ch}", f"H_adcraw_{ch}", NBINS, XMIN, XMAX) 
                     for ch in range(N_CHANNELS)]
    hists_adc_clean = [ROOT.TH1F(f"H_adcClean_{ch}", f"H_adcClean_{ch}", NBINS, XMIN, XMAX) 
                       for ch in range(N_CHANNELS)]

    for h in hists_adc_raw + hists_adc_clean:
        h.SetDirectory(0)

    # TDC vs ADC 2D histograms (clean events, selected channels only)
    # Axes: X = TDC sample [ns], Y = ADC sample [counts]
    # TDC window 0–2000 ns covers prompt + delayed hits; ADC 0–50000 ADC counts.
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

    # Out-of-range channels
    hists_adc_oor_raw = {}
    hists_adc_oor_clean = {}

    # Spatial cut histograms (diagnostic only)
    if apply_spatial_cut:
        h_r_all = ROOT.TH1F("h_fCCRecR_all", 
                           f"Reconstructed Radius (All);R (mm);Events", 
                           200, 0, 1000)
        h_r_selected = ROOT.TH1F("h_fCCRecR_selected", 
                                f"Reconstructed Radius (R<{radial_cut}mm);R (mm);Events", 
                                200, 0, 1000)
        for h in [h_r_all, h_r_selected]:
            h.SetDirectory(0)

    # =============================================================================
    # Create output
    # =============================================================================
    os.makedirs(output_dir, exist_ok=True)
    suffix = "_spatial_cut" if apply_spatial_cut else ""
    output_file = os.path.join(output_dir, 
                              f"CHARGE_single_RUN{run_number}_{file_number}{suffix}.root")
    fout = ROOT.TFile(output_file, "RECREATE")

    # =============================================================================
    # Setup reading
    # =============================================================================
    cd_elec_evt = ROOT.Tao.CdElecEvt()
    cd_trig_evt = ROOT.Tao.CdTrigEvt()
    cd_elec_tree.SetBranchAddress("CdElecEvt", cd_elec_evt)
    cd_trig_tree.SetBranchAddress("CdTrigEvt", cd_trig_evt)

    if has_wt:
        wt_elec_evt = ROOT.Tao.WtElecEvt()
        wt_trig_evt = ROOT.Tao.WtTrigEvt()
        wt_elec_tree.SetBranchAddress("WtElecEvt", wt_elec_evt)
        wt_trig_tree.SetBranchAddress("WtTrigEvt", wt_trig_evt)
    else:
        wt_elec_evt = None
        wt_trig_evt = None

    if has_tvt:
        tvt_elec_evt = ROOT.Tao.TvtElecEvt()
        tvt_trig_evt = ROOT.Tao.TvtTrigEvt()
        tvt_elec_tree.SetBranchAddress("TvtElecEvt", tvt_elec_evt)
        tvt_trig_tree.SetBranchAddress("TvtTrigEvt", tvt_trig_evt)
    else:
        tvt_elec_evt = None
        tvt_trig_evt = None

    # =============================================================================
    # Process events
    # =============================================================================
    print(f"Processing {nentries} events...")

    # Counters
    out_of_range_channels = Counter()
    total_hits = 0

    # Veto tracking
    sec_prev = nsec_prev = 0
    sec_mu = nsec_mu = 0
    is_after_muon = is_after_pulse = False

    # Statistics
    n_muons = n_muons_cd = n_muons_wt = n_muons_tvt = 0
    n_after_muon = n_after_pulse = n_outlier = n_spatial_cut = n_clean = 0

    for i in range(nentries):
        if (i + 1) % 1000 == 0:
            print(f"\rEvent {i+1}/{nentries}...", end='', flush=True)

        # Read all detector events
        cd_elec_tree.GetEntry(i)
        cd_trig_tree.GetEntry(i)
        if has_wt:
            wt_elec_tree.GetEntry(i)
            wt_trig_tree.GetEntry(i)
        if has_tvt:
            tvt_elec_tree.GetEntry(i)
            tvt_trig_tree.GetEntry(i)

        # Get trigger time (use CD)
        trig_time = cd_trig_evt.getTrigTime()
        sec = trig_time.GetSec()
        nsec = trig_time.GetNanoSec()

        # Check after-muon veto
        if is_after_muon:
            diff_mu = (sec - sec_mu) * 1e9 + (nsec - nsec_mu)
            if diff_mu > AFTER_MU:
                is_after_muon = False

        # Check after-pulse veto
        if i > 0:
            diff = (sec - sec_prev) * 1e9 + (nsec - nsec_prev)
            is_after_pulse = (diff < AFTER_PULSE)
        else:
            is_after_pulse = False

        # Check spatial cut
        passes_spatial_cut = True
        event_r = 0.0
        if apply_spatial_cut:
            if i in positions:
                event_r = positions[i]['r']
                if event_r > 0:
                    h_r_all.Fill(event_r)
                    if event_r < radial_cut:
                        h_r_selected.Fill(event_r)
                        passes_spatial_cut = True
                    else:
                        passes_spatial_cut = False
                else:
                    passes_spatial_cut = False
            else:
                passes_spatial_cut = False

        # Process CD channels
        channels = cd_elec_evt.GetElecChannels()
        n_fired = channels.size()
        tot_adc_event = 0.0
        event_channel_data = []

        has_flasher = False
        for j in range(n_fired):
            channel = channels[j]
            chid = channel.getChannelID()
            adcs = channel.getADCs()

            # Collect ADC values
            adcs_list = [adcs[k] for k in range(adcs.size())]
            ch_total_adc = sum(adcs_list)

            # Per-channel flasher check
            if ch_total_adc > MAX_ADC_PER_CHANNEL:
                has_flasher = True
                continue

            if len(adcs_list) == 0:
                continue

            tot_adc_event += ch_total_adc
            total_hits += len(adcs_list)

            # Collect TDC samples aligned with ADC samples (ns from trig)
            tdc_list = []
            if save_tdc_adc and chid in hists_tdc_adc:
                try:
                    tdcs = channel.getTDCs()
                    tdc_list = [tdcs[k] for k in range(tdcs.size())]
                except Exception:
                    tdc_list = []

            event_channel_data.append({
                'chid': chid,
                'adcs_list': adcs_list,
                'ch_total_adc': ch_total_adc,
                'tdc_list': tdc_list,
            })

        n_hit_channels = len(event_channel_data)

        # Check muon tags
        is_muon_cd = (tot_adc_event > MUON_THRESHOLD_CD)
        is_muon_wt = False
        is_muon_tvt = False

        if has_wt:
            wt_channels = wt_elec_evt.GetElecChannels()
            is_muon_wt = (wt_channels.size() >= MUON_THRESHOLD_WT)

        if has_tvt:
            tvt_channels = tvt_elec_evt.GetElecChannels()
            is_muon_tvt = (tvt_channels.size() >= MUON_THRESHOLD_TVT)

        is_muon = is_muon_cd or is_muon_wt or is_muon_tvt

        # Outlier checks
        passes_total_adc = (tot_adc_event <= MAX_TOTAL_ADC)
        passes_nhit = (MIN_NHIT <= n_hit_channels <= MAX_NHIT)
        passes_flasher = (not has_flasher)
        passes_outlier_cut = passes_total_adc and passes_nhit and passes_flasher

        # Determine veto flag
        if not passes_outlier_cut:
            veto_flag = 4  # Outlier
            n_outlier += 1
        elif not passes_spatial_cut and apply_spatial_cut:
            veto_flag = 3  # Spatial cut
            n_spatial_cut += 1
        elif is_after_muon:
            veto_flag = 2  # After-muon
            n_after_muon += 1
        elif is_after_pulse:
            veto_flag = 1  # After-pulse
            n_after_pulse += 1
        else:
            veto_flag = 0  # Clean
            n_clean += 1

        # Fill TIER 1 (Raw) - all events
        for ch_data in event_channel_data:
            chid = ch_data['chid']
            adcs_list = ch_data['adcs_list']
            is_oor = (chid < 0 or chid >= N_CHANNELS)

            if is_oor:
                if chid not in hists_adc_oor_raw:
                    h_raw = ROOT.TH1F(f"H_adcraw_{chid}", f"ADC raw {chid} (OOR)", 
                                     NBINS, XMIN, XMAX)
                    h_raw.SetDirectory(0)
                    hists_adc_oor_raw[chid] = h_raw
                    out_of_range_channels[chid] += 1

                for adc_val in adcs_list:
                    hists_adc_oor_raw[chid].Fill(adc_val)
            else:
                if 0 <= chid < N_CHANNELS:
                    for adc_val in adcs_list:
                        hists_adc_raw[chid].Fill(adc_val)

        # Fill TIER 2 (Clean) - only clean events
        if veto_flag == 0:
            for ch_data in event_channel_data:
                chid = ch_data['chid']
                adcs_list = ch_data['adcs_list']
                is_oor = (chid < 0 or chid >= N_CHANNELS)

                if is_oor:
                    if chid not in hists_adc_oor_clean:
                        h_clean = ROOT.TH1F(f"H_adcClean_{chid}", f"ADC Clean {chid} (OOR)", 
                                           NBINS, XMIN, XMAX)
                        h_clean.SetDirectory(0)
                        hists_adc_oor_clean[chid] = h_clean

                    for adc_val in adcs_list:
                        hists_adc_oor_clean[chid].Fill(adc_val)
                else:
                    if 0 <= chid < N_CHANNELS:
                        for adc_val in adcs_list:
                            hists_adc_clean[chid].Fill(adc_val)

                # Fill TDC-ADC 2D (clean events, monitored channels only)
                if save_tdc_adc and chid in hists_tdc_adc:
                    tdc_list  = ch_data.get('tdc_list', [])
                    # Pair each ADC sample with the corresponding TDC sample.
                    # If TDC list is shorter or absent, use 0 as placeholder.
                    for k, adc_val in enumerate(adcs_list):
                        tdc_val = tdc_list[k] if k < len(tdc_list) else 0.0
                        hists_tdc_adc[chid].Fill(float(tdc_val), float(adc_val))

        # Update muon flag
        if is_muon:
            is_after_muon = True
            sec_mu = sec
            nsec_mu = nsec
            n_muons += 1
            if is_muon_cd:
                n_muons_cd += 1
            if is_muon_wt:
                n_muons_wt += 1
            if is_muon_tvt:
                n_muons_tvt += 1

        sec_prev = sec
        nsec_prev = nsec

    print(f"\rEvent {nentries}/{nentries}... Done!")

    # =============================================================================
    # Statistics
    # =============================================================================
    print()
    print(f"Statistics:")
    print(f"  Total hits: {total_hits}")
    print(f"  Out-of-range channels: {len(out_of_range_channels)}")
    print("Veto Statistics:")
    print(f"  Muon events (total): {n_muons}")
    print(f"    - Tagged by CD: {n_muons_cd}")
    if has_wt:
        print(f"    - Tagged by WT: {n_muons_wt}")
    if has_tvt:
        print(f"    - Tagged by TVT: {n_muons_tvt}")
    print(f"  Events vetoed (after muon): {n_after_muon}")
    print(f"  Events vetoed (after pulse): {n_after_pulse}")
    print(f"  Events vetoed (outliers): {n_outlier}")
    if apply_spatial_cut:
        print(f"  Events vetoed (spatial cut): {n_spatial_cut}")
    print(f"  Clean events: {n_clean}")
    print(f"  Clean fraction: {100*n_clean/nentries:.1f}%")
    print()

    # =============================================================================
    # Save output
    # =============================================================================
    print(f"Saving to {output_file}")
    fout.cd()

    # Write TIER 1 (Raw) histograms
    for h in hists_adc_raw:
        h.Write()
    for h in hists_adc_oor_raw.values():
        h.Write()

    # Write TIER 2 (Clean) histograms
    for h in hists_adc_clean:
        h.Write()
    for h in hists_adc_oor_clean.values():
        h.Write()

    # Write TDC-ADC 2D histograms (if requested)
    if save_tdc_adc and hists_tdc_adc:
        tdc_dir = fout.mkdir("TdcAdc")
        tdc_dir.cd()
        for h2 in hists_tdc_adc.values():
            h2.Write()
        fout.cd()
        print(f"  TDC-ADC 2D histograms: {len(hists_tdc_adc)} channels → TdcAdc/")

    # Write spatial cut histograms (diagnostic only)
    if apply_spatial_cut:
        h_r_all.Write()
        h_r_selected.Write()

    # Save metadata
    veto_info_str = (
        f"MUON_THRESHOLD_CD={MUON_THRESHOLD_CD};"
        f"MUON_THRESHOLD_WT={MUON_THRESHOLD_WT};"
        f"MUON_THRESHOLD_TVT={MUON_THRESHOLD_TVT};"
        f"AFTER_MU={AFTER_MU};"
        f"AFTER_PULSE={AFTER_PULSE};"
        f"MAX_TOTAL_ADC={MAX_TOTAL_ADC};"
        f"MAX_ADC_PER_CHANNEL={MAX_ADC_PER_CHANNEL};"
        f"MIN_NHIT={MIN_NHIT};"
        f"MAX_NHIT={MAX_NHIT};"
        f"N_MUONS={n_muons};"
        f"N_MUONS_CD={n_muons_cd};"
        f"N_MUONS_WT={n_muons_wt};"
        f"N_MUONS_TVT={n_muons_tvt};"
        f"N_AFTER_MUON={n_after_muon};"
        f"N_AFTER_PULSE={n_after_pulse};"
        f"N_OUTLIER={n_outlier};"
        f"N_CLEAN={n_clean};"
        f"HAS_WT={1 if has_wt else 0};"
        f"HAS_TVT={1 if has_tvt else 0}"
    )

    if apply_spatial_cut:
        veto_info_str += f";SPATIAL_CUT_ENABLED=1;RADIAL_CUT={radial_cut};N_SPATIAL_CUT={n_spatial_cut}"
    else:
        veto_info_str += ";SPATIAL_CUT_ENABLED=0"

    ROOT.TNamed("veto_info", veto_info_str).Write()

    if apply_spatial_cut:
        selection_efficiency = 100.0 * n_clean / nentries if nentries > 0 else 0
        ROOT.TNamed("spatial_cut_info", 
                   f"RADIAL_CUT={radial_cut};N_TOTAL={nentries};N_SELECTED={n_clean};EFFICIENCY={selection_efficiency:.4f}").Write()

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
        description="Extract ADC histograms with multi-detector veto and outlier removal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regular run (no spatial cut):
  python extract_charge_veto.py /path/to/RUN.1065.rtraw /path/to/output

  # Calibration run with spatial cut:
  python extract_charge_veto.py /path/to/RUN.1065.rtraw /path/to/output \
      --apply-spatial-cut --rec-file /path/to/user-ana-output.root --radial-cut 200
"""
    )

    parser.add_argument('rtraw_file', help='Path to RTRAW file')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--apply-spatial-cut', action='store_true',
                       help='Enable spatial cut for calibration runs')
    parser.add_argument('--rec-file', 
                       help='Reconstruction file (required with --apply-spatial-cut)')
    parser.add_argument('--radial-cut', type=float, default=DEFAULT_RADIAL_CUT_MM,
                       help=f'Radial cut in mm (default: {DEFAULT_RADIAL_CUT_MM})')
    parser.add_argument('--mode', choices=['calib', 'physics', 'ibd'], default='calib',
                       help='Analysis mode: calib, physics, or ibd')
    parser.add_argument('--save-tdc-adc', action='store_true',
                       help='Save per-channel TDC vs ADC 2D histograms (clean events) '
                            'under TdcAdc/ directory in the output ROOT file. '
                            'Use channel_qt_plots.py --tdc-adc to visualise them.')
    parser.add_argument('--tdc-adc-channels', type=int, default=40,
                       help='Number of channels for TDC-ADC 2D histograms (default: 40)')

    args = parser.parse_args()

    if args.apply_spatial_cut and not args.rec_file:
        parser.error("--rec-file is required when --apply-spatial-cut is enabled")

    extract_charge_data(args.rtraw_file, args.output_dir, 
                       apply_spatial_cut=args.apply_spatial_cut,
                       rec_file=args.rec_file,
                       radial_cut=args.radial_cut,
                       mode=args.mode,
                       save_tdc_adc=args.save_tdc_adc,
                       tdc_adc_channels=args.tdc_adc_channels)
