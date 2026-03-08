#!/usr/bin/env python3
"""
merge_charge.py - Merge charge data files (SIMPLIFIED)
Only merges ADC histograms needed for gain calibration
"""

import sys
import os
import glob
from tqdm import tqdm

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

DEFAULT_AFTER_MU = 1000e3
DEFAULT_AFTER_PULSE = 5e3
DEFAULT_RADIAL_CUT_MM = 200.0


def merge_charge_data(run_number, inputdir, outputdir, spatial_cut=False):
    """Merge ADC histograms (2-TIER approach: raw + clean)."""

    # Build pattern
    if spatial_cut:
        pattern = os.path.join(inputdir, f"CHARGE_single_RUN{run_number}*_spatial_cut.root")
        output_suffix = "_spatial_cut"
    else:
        pattern = os.path.join(inputdir, f"CHARGE_single_RUN{run_number}_*.root")
        output_suffix = ""

    all_files = sorted(glob.glob(pattern))

    # Filter out spatial cut files if doing non-spatial merge
    if not spatial_cut:
        input_files = [f for f in all_files if "_spatial_cut.root" not in f]
    else:
        input_files = all_files

    if len(input_files) == 0:
        print(f"ERROR: No input files found: {pattern}")
        if not spatial_cut:
            print(f"  (excluding files with '_spatial_cut' suffix)")
        sys.exit(1)

    print("=" * 60)
    print(f"Merging charge data for RUN {run_number}")
    if spatial_cut:
        print(f"MODE: With spatial cut (calibration)")
    else:
        print(f"MODE: Without spatial cut")
    print("=" * 60)
    print(f"Found {len(input_files)} input files")
    print(f"First: {os.path.basename(input_files[0])}")
    print(f"Last: {os.path.basename(input_files[-1])}")
    print()

    # Extract veto parameters from first file
    veto_params_from_input = {}
    firstfile = ROOT.TFile.Open(input_files[0], "READ")
    if firstfile and not firstfile.IsZombie():
        veto_info_input = firstfile.Get("veto_info")
        if veto_info_input:
            info_str = veto_info_input.GetTitle()
            for item in info_str.split(";"):
                if "=" in item:
                    key, val = item.split("=")
                    veto_params_from_input[key] = val
        firstfile.Close()

    try:
        AFTER_MU = float(veto_params_from_input.get("AFTER_MU", DEFAULT_AFTER_MU))
        AFTER_PULSE = float(veto_params_from_input.get("AFTER_PULSE", DEFAULT_AFTER_PULSE))
    except (ValueError, TypeError):
        print("WARNING: Could not parse AFTER_MU/AFTER_PULSE from input files")
        print(f"  Using defaults: AFTER_MU={DEFAULT_AFTER_MU/1e3:.0f} µs, AFTER_PULSE={DEFAULT_AFTER_PULSE/1e3:.1f} µs")
        AFTER_MU = DEFAULT_AFTER_MU
        AFTER_PULSE = DEFAULT_AFTER_PULSE

    print(f"Veto timing windows (from extraction metadata):")
    print(f"  AFTER_MU: {AFTER_MU/1e3:.0f} µs")
    print(f"  AFTER_PULSE: {AFTER_PULSE/1e3:.1f} µs")
    print()

    NCHANNELS = 8048
    NBINS = 500
    XMIN = 0.0
    XMAX = 50000.0

    # === Discover all channel IDs ===
    print(f"Discovering all channel IDs across {len(input_files)} files...")
    all_channel_ids = set(range(NCHANNELS))

    for inputfile in tqdm(input_files, desc="Scanning files"):
        try:
            f = ROOT.TFile.Open(inputfile, "READ")
            if not f or f.IsZombie():
                print(f"  Cannot open {inputfile}")
                continue
            keys = f.GetListOfKeys()
            for key in keys:
                name = key.GetName()
                # Look for both H_adcraw_ and H_adcClean_
                if name.startswith("H_adcraw_") or name.startswith("H_adcClean_"):
                    try:
                        ch_id = int(name.replace("H_adcraw_", "").replace("H_adcClean_", ""))
                        all_channel_ids.add(ch_id)
                    except ValueError:
                        continue
            f.Close()
        except Exception as e:
            print(f"  Error scanning {inputfile}: {e}")
            continue

    print(f"  {len(all_channel_ids)} unique channel IDs")
    standard_channels = [ch for ch in all_channel_ids if 0 <= ch < NCHANNELS]
    oor_channels = [ch for ch in all_channel_ids if ch < 0 or ch >= NCHANNELS]
    print(f"  Standard channels (0-{NCHANNELS-1}): {len(standard_channels)}")
    print(f"  Out-of-range channels: {len(oor_channels)}")
    if oor_channels:
        print(f"    Range: [{min(oor_channels)}, {max(oor_channels)}]")
    print()

    # === Initialize TIER 1: Raw histograms (ALL events) ===
    print(f"Initializing {NCHANNELS} merged RAW histograms (all events)...")
    merged_hists_raw = []
    for ch in range(NCHANNELS):
        hist_name = f"H_adcraw_{ch}"
        hist_title = f"Merged ADC RAW Channel {ch} - RUN{run_number}"
        h = ROOT.TH1F(hist_name, hist_title, NBINS, XMIN, XMAX)
        h.SetDirectory(0)
        merged_hists_raw.append(h)

    # === Initialize TIER 2: Clean histograms (veto-passed events) ===
    print(f"Initializing {NCHANNELS} merged CLEAN histograms (veto-passed)...")
    merged_hists_clean = []
    for ch in range(NCHANNELS):
        hist_name = f"H_adcClean_{ch}"
        hist_title = f"Merged ADC Clean Channel {ch} - RUN{run_number}"
        h = ROOT.TH1F(hist_name, hist_title, NBINS, XMIN, XMAX)
        h.SetDirectory(0)
        merged_hists_clean.append(h)

    # === OOR histograms (2 tiers) ===
    merged_hists_oor_raw = {}
    merged_hists_oor_clean = {}
    if oor_channels:
        print(f"Initializing {len(oor_channels)} merged OOR histograms (2 tiers)...")
        for ch in oor_channels:
            # Tier 1: Raw
            h_raw = ROOT.TH1F(f"H_adcraw_{ch}", f"Merged ADC RAW {ch} (OOR)", NBINS, XMIN, XMAX)
            h_raw.SetDirectory(0)
            merged_hists_oor_raw[ch] = h_raw

            # Tier 2: Clean
            h_clean = ROOT.TH1F(f"H_adcClean_{ch}", f"Merged ADC Clean {ch} (OOR)", NBINS, XMIN, XMAX)
            h_clean.SetDirectory(0)
            merged_hists_oor_clean[ch] = h_clean
    print()

    # === Spatial cut histograms (if present) ===
    h_r_all_merged = None
    h_r_selected_merged = None
    if spatial_cut:
        print("Initializing spatial cut histograms...")
        h_r_all_merged = ROOT.TH1F("h_fCCRecR_all", 
                                   "Reconstructed Radius (All);R (mm);Events", 
                                   200, 0, 1000)
        h_r_all_merged.SetDirectory(0)
        h_r_selected_merged = ROOT.TH1F("h_fCCRecR_selected", 
                                        "Reconstructed Radius (Selected);R (mm);Events", 
                                        200, 0, 1000)
        h_r_selected_merged.SetDirectory(0)
        print()

    # === Merge histograms from all files ===
    print(f"Merging histograms from {len(input_files)} files...")
    total_n_muons = 0
    total_n_after_muon = 0
    total_n_after_pulse = 0
    total_n_outlier = 0
    total_n_spatial_cut = 0
    total_n_clean = 0

    for file_idx, inputfile in enumerate(tqdm(input_files, desc="Merging histograms")):
        try:
            f = ROOT.TFile.Open(inputfile, "READ")
            if not f or f.IsZombie():
                continue

            # === TIER 1: Merge raw histograms (all events) ===
            for ch in range(NCHANNELS):
                h_input_raw = f.Get(f"H_adcraw_{ch}")
                if h_input_raw:
                    merged_hists_raw[ch].Add(h_input_raw)

            # === TIER 2: Merge clean histograms (veto-passed) ===
            for ch in range(NCHANNELS):
                h_input_clean = f.Get(f"H_adcClean_{ch}")
                if h_input_clean:
                    merged_hists_clean[ch].Add(h_input_clean)

            # === OOR - 2 tiers ===
            for ch in oor_channels:
                # Raw
                h_input_raw = f.Get(f"H_adcraw_{ch}")
                if h_input_raw:
                    merged_hists_oor_raw[ch].Add(h_input_raw)

                # Clean
                h_input_clean = f.Get(f"H_adcClean_{ch}")
                if h_input_clean:
                    merged_hists_oor_clean[ch].Add(h_input_clean)

            # === Merge spatial cut histograms (if present) ===
            if spatial_cut:
                h_r_all = f.Get("h_fCCRecR_all")
                if h_r_all:
                    h_r_all_merged.Add(h_r_all)

                h_r_selected = f.Get("h_fCCRecR_selected")
                if h_r_selected:
                    h_r_selected_merged.Add(h_r_selected)

            # === Get veto statistics ===
            veto_info = f.Get("veto_info")
            if veto_info:
                info_str = veto_info.GetTitle()
                info_dict = dict(item.split("=") for item in info_str.split(";") if "=" in item)
                total_n_muons += int(info_dict.get("N_MUONS", 0))
                total_n_after_muon += int(info_dict.get("N_AFTER_MUON", 0))
                total_n_after_pulse += int(info_dict.get("N_AFTER_PULSE", 0))
                total_n_outlier += int(info_dict.get("N_OUTLIER", 0))
                total_n_spatial_cut += int(info_dict.get("N_SPATIAL_CUT", 0))
                total_n_clean += int(info_dict.get("N_CLEAN", 0))

            f.Close()
        except Exception as e:
            print(f"  Error processing {inputfile}: {e}")
            continue

    print("\n-- END OF MERGING LOOP --\n")

    # === Create output file ===
    os.makedirs(outputdir, exist_ok=True)
    outputfile = os.path.join(outputdir, f"CHARGE_RUN{run_number}_merged{output_suffix}.root")
    print(f"Saving merged data to {outputfile}")
    fout = ROOT.TFile(outputfile, "RECREATE")
    fout.cd()

    # === Write TIER 1: Raw histograms ===
    n_nonempty_raw = 0
    total_entries_raw = 0
    for ch in tqdm(range(NCHANNELS), desc="Writing raw histograms (all events)"):
        entries = merged_hists_raw[ch].GetEntries()
        if entries > 0:
            n_nonempty_raw += 1
            total_entries_raw += entries
        merged_hists_raw[ch].Write()

    # === Write TIER 2: Clean histograms ===
    n_nonempty_clean = 0
    total_entries_clean = 0
    for ch in tqdm(range(NCHANNELS), desc="Writing clean histograms (veto-passed)"):
        entries = merged_hists_clean[ch].GetEntries()
        if entries > 0:
            n_nonempty_clean += 1
            total_entries_clean += entries
        merged_hists_clean[ch].Write()

    # === Write OOR histograms - 2 tiers ===
    n_nonempty_oor_raw = 0
    total_entries_oor_raw = 0
    if merged_hists_oor_raw:
        print(f"Writing {len(merged_hists_oor_raw)} OOR RAW histograms (all events)...")
        for ch, h in merged_hists_oor_raw.items():
            entries = h.GetEntries()
            if entries > 0:
                n_nonempty_oor_raw += 1
                total_entries_oor_raw += entries
            h.Write()

    n_nonempty_oor_clean = 0
    total_entries_oor_clean = 0
    if merged_hists_oor_clean:
        print(f"Writing {len(merged_hists_oor_clean)} OOR CLEAN histograms (veto-passed)...")
        for ch, h in merged_hists_oor_clean.items():
            entries = h.GetEntries()
            if entries > 0:
                n_nonempty_oor_clean += 1
                total_entries_oor_clean += entries
            h.Write()

    # === Write spatial cut histograms ===
    if spatial_cut and h_r_all_merged and h_r_selected_merged:
        print("Writing spatial cut histograms...")
        h_r_all_merged.Write()
        h_r_selected_merged.Write()

    # === Write metadata ===
    print("\nWriting metadata...")

    # Extract veto parameters from first input file
    veto_params_from_input = {}
    firstfile = ROOT.TFile.Open(input_files[0], "READ")
    if firstfile and not firstfile.IsZombie():
        veto_info_input = firstfile.Get("veto_info")
        if veto_info_input:
            info_str = veto_info_input.GetTitle()
            for item in info_str.split(";"):
                if "=" in item:
                    key, val = item.split("=")
                    veto_params_from_input[key] = val
        firstfile.Close()

    # Build merged veto info string
    veto_info_str = (
        f"MUON_THRESHOLD_CD={veto_params_from_input.get('MUON_THRESHOLD_CD', 0)};"
        f"MUON_THRESHOLD_WT={veto_params_from_input.get('MUON_THRESHOLD_WT', 0)};"
        f"MUON_THRESHOLD_TVT={veto_params_from_input.get('MUON_THRESHOLD_TVT', 0)};"
        f"AFTER_MU={veto_params_from_input.get('AFTER_MU', 0)};"
        f"AFTER_PULSE={veto_params_from_input.get('AFTER_PULSE', 0)};"
        f"MAX_TOTAL_ADC={veto_params_from_input.get('MAX_TOTAL_ADC', 0)};"
        f"MAX_ADC_PER_CHANNEL={veto_params_from_input.get('MAX_ADC_PER_CHANNEL', 0)};"
        f"MIN_NHIT={veto_params_from_input.get('MIN_NHIT', 0)};"
        f"MAX_NHIT={veto_params_from_input.get('MAX_NHIT', 0)};"
        f"N_MUONS={total_n_muons};"
        f"N_MUONS_CD={veto_params_from_input.get('N_MUONS_CD', 0)};"
        f"N_MUONS_WT={veto_params_from_input.get('N_MUONS_WT', 0)};"
        f"N_MUONS_TVT={veto_params_from_input.get('N_MUONS_TVT', 0)};"
        f"N_AFTER_MUON={total_n_after_muon};"
        f"N_AFTER_PULSE={total_n_after_pulse};"
        f"N_OUTLIER={total_n_outlier};"
        f"N_CLEAN={total_n_clean};"
        f"HAS_WT={veto_params_from_input.get('HAS_WT', 0)};"
        f"HAS_TVT={veto_params_from_input.get('HAS_TVT', 0)}"
    )

    if spatial_cut:
        veto_info_str += f";SPATIAL_CUT_ENABLED=1;N_SPATIAL_CUT={total_n_spatial_cut}"
    else:
        veto_info_str += ";SPATIAL_CUT_ENABLED=0"

    fout.cd()
    veto_info = ROOT.TNamed("veto_info", veto_info_str)
    veto_info.Write("veto_info", ROOT.TObject.kOverwrite)
    print(f"  Wrote veto_info with {len(veto_info_str)} characters")

    # Spatial cut info (if applicable)
    if spatial_cut:
        spatial_info_input = firstfile.Get("spatial_cut_info")
        if spatial_info_input:
            info_str = spatial_info_input.GetTitle()
            # Update totals
            info_dict = dict(item.split("=") for item in info_str.split(";") if "=" in item)
            radial_cut = info_dict.get("RADIAL_CUT", DEFAULT_RADIAL_CUT_MM)

            spatial_info_str = (
                f"RADIAL_CUT={radial_cut};"
                f"N_TOTAL={sum([total_n_clean, total_n_spatial_cut, total_n_outlier, total_n_after_muon, total_n_after_pulse])};"
                f"N_SELECTED={total_n_clean}"
            )

            fout.cd()
            spatial_info = ROOT.TNamed("spatial_cut_info", spatial_info_str)
            spatial_info.Write("spatial_cut_info", ROOT.TObject.kOverwrite)
            print(f"  Wrote spatial_cut_info")

    # OOR info
    if oor_channels:
        oor_list = ",".join(str(ch) for ch in sorted(oor_channels)[:100])
        if len(oor_channels) > 100:
            oor_list += f",... ({len(oor_channels)-100} more)"
        fout.cd()
        oor_info = ROOT.TNamed("merged_out_of_range_info", 
                               f"OOR_COUNT={len(oor_channels)};OOR_CHANNELS={oor_list}")
        oor_info.Write("merged_out_of_range_info", ROOT.TObject.kOverwrite)

    # === Close file ===
    print("\nClosing file...")
    fout.Write()
    fout.Close()
    print(f"  File closed successfully")
    print()

    # === Print statistics ===
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)
    print(f"Total channels merged: {len(all_channel_ids)}")
    print(f"  Standard (0-{NCHANNELS-1}): {len(standard_channels)}")
    print(f"  Out-of-range: {len(oor_channels)}")
    print(f"Non-empty histograms:")
    print(f"  Standard raw (all events): {n_nonempty_raw}")
    print(f"  Standard clean (veto-passed): {n_nonempty_clean}")
    print(f"  Out-of-range raw: {n_nonempty_oor_raw}")
    print(f"  Out-of-range clean: {n_nonempty_oor_clean}")
    print(f"Total ADC histogram entries:")
    print(f"  Standard raw: {int(total_entries_raw)}")
    print(f"  Standard clean: {int(total_entries_clean)}")
    print(f"  Out-of-range raw: {int(total_entries_oor_raw)}")
    print(f"  Out-of-range clean: {int(total_entries_oor_clean)}")
    print(f"Merged veto statistics:")
    print(f"  Total muon events: {total_n_muons}")
    print(f"  Total after-muon vetoed: {total_n_after_muon}")
    print(f"  Total after-pulse vetoed: {total_n_after_pulse}")
    print(f"  Total outlier vetoed: {total_n_outlier}")
    if spatial_cut:
        print(f"  Total spatial cut vetoed: {total_n_spatial_cut}")
    print(f"  Total clean events: {total_n_clean}")
    print(f"Output: {outputfile}")
    print("=" * 60)

    return outputfile


if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python merge_charge.py <run_number> <inputdir> <outputdir> [--spatial-cut]")
        print()
        print("Examples:")
        print("  # Calibration run (no spatial cut)")
        print("  python merge_charge.py 1210 path/to/single_charge path/to/merged_charge")
        print()
        print("  # Physics run with spatial cut")
        print("  python merge_charge.py 871 path/to/single_charge path/to/merged_charge --spatial-cut")
        sys.exit(1)

    run_number = sys.argv[1]
    inputdir = sys.argv[2]
    outputdir = sys.argv[3]
    spatial_cut = (len(sys.argv) == 5 and sys.argv[4] == "--spatial-cut")

    if not os.path.isdir(inputdir):
        print(f"ERROR: Input directory does not exist: {inputdir}")
        sys.exit(1)

    merge_charge_data(run_number, inputdir, outputdir, spatial_cut=spatial_cut)
