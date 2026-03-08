#!/usr/bin/env python3

"""
plot_tdc_from_rtraw.py - TDC analysis from RTRAW files

Features:
- Extract TDC histograms from RTRAW files
- Save all histograms to ROOT file
- Generate PNG plots for sample channels (100, 1000, 2000, 5000, 7000) and summed TDC
- Merge mode: combine TDC histograms from multiple ROOT files
"""

import sys
import os
import argparse
import glob
import numpy as np

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# =============================================================================
# CONSTANTS
# =============================================================================
TDC_CUT_LOW = 0  # ns
TDC_CUT_UP = 1000   # ns
SAMPLE_CHANNELS = [100, 1000, 2000, 5000, 7000]  # Channels to save as PNG
TDC_NBINS = 500
TDC_MIN = 0.0
TDC_MAX = 1000.0

# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================
def plot_tdc_channel(h_tdc, output_path, channel_id, tdc_min=None, tdc_max=None):
    """Plot single channel TDC with optional dashed red TDC cut lines"""
    if h_tdc.GetEntries() == 0:
        return False

    nbins = h_tdc.GetNbinsX()
    tdc_vals = np.array([h_tdc.GetBinCenter(i) for i in range(1, nbins + 1)])
    counts = np.array([h_tdc.GetBinContent(i) for i in range(1, nbins + 1)])

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.step(tdc_vals, counts, where='mid', color='blue', linewidth=1.0, label='TDC Data')

    # Add TDC cut lines if provided
    if tdc_min is not None and tdc_max is not None:
        ax.axvline(tdc_min, color='red', linestyle='--', linewidth=2,
                   label=f'TDC cut: [{tdc_min:.0f}, {tdc_max:.0f}] ns')
        ax.axvline(tdc_max, color='red', linestyle='--', linewidth=2)

    ax.set_xlabel('TDC [ns]', fontsize=12)
    ax.set_ylabel('Counts', fontsize=12)
    ax.set_title(f'TDC Distribution - Channel {channel_id}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right')

    # Statistics box
    mean = h_tdc.GetMean()
    rms = h_tdc.GetRMS()
    entries = int(h_tdc.GetEntries())
    stats_text = f'Entries: {entries}\nMean: {mean:.2f} ns\nRMS: {rms:.2f} ns'
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            fontsize=10, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return True

def plot_tdc_sum(h_tdc_sum, output_path, tdc_min=None, tdc_max=None, run_label=""):
    """Plot sum TDC with optional dashed red TDC cut lines"""
    if h_tdc_sum.GetEntries() == 0:
        return False

    nbins = h_tdc_sum.GetNbinsX()
    tdc_vals = np.array([h_tdc_sum.GetBinCenter(i) for i in range(1, nbins + 1)])
    counts = np.array([h_tdc_sum.GetBinContent(i) for i in range(1, nbins + 1)])

    fig, ax = plt.subplots(1, 1, figsize=(14, 7))
    ax.step(tdc_vals, counts, where='mid', color='darkblue', linewidth=1.5,
            label='Sum over all channels')

    # Add TDC cut lines if provided
    if tdc_min is not None and tdc_max is not None:
        ax.axvline(tdc_min, color='red', linestyle='--', linewidth=2,
                   label=f'TDC cut: [{tdc_min:.0f}, {tdc_max:.0f}] ns')
        ax.axvline(tdc_max, color='red', linestyle='--', linewidth=2)

    ax.set_xlabel('TDC [ns]', fontsize=14)
    ax.set_ylabel('Counts', fontsize=14)
    title = 'TDC Distribution - Sum Over All Channels'
    if run_label:
        title += f' ({run_label})'
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=12)

    # Statistics box
    mean = h_tdc_sum.GetMean()
    rms = h_tdc_sum.GetRMS()
    entries = int(h_tdc_sum.GetEntries())
    stats_text = f'Total Entries: {entries:,}\nMean: {mean:.2f} ns\nRMS: {rms:.2f} ns'
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            fontsize=11, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return True

# =============================================================================
# PROCESS RTRAW FILE
# =============================================================================
def process_rtraw_file(rtraw_file, output_root, output_png_dir, sample_channels=SAMPLE_CHANNELS):
    """Process a single RTRAW file and extract TDC histograms"""
    print(f"\nProcessing: {os.path.basename(rtraw_file)}")

    fin = ROOT.TFile.Open(rtraw_file, "READ")
    if not fin or fin.IsZombie():
        print(f"  ERROR: Cannot open file")
        return None

    # Get electronics event tree
    elec_tree = fin.Get("Event/Elec/CdElecEvt")
    if not elec_tree or not elec_tree.InheritsFrom("TTree"):
        print(f"  ERROR: Cannot find CdElecEvt tree")
        fin.Close()
        return None

    n_events = elec_tree.GetEntries()
    print(f"  Events: {n_events}")

    # Create TDC histograms (one per channel + sum)
    tdc_histograms = {}
    h_tdc_sum = ROOT.TH1F("H_tdc_sum", "TDC Sum;TDC [ns];Counts", 
                          TDC_NBINS, TDC_MIN, TDC_MAX)
    h_tdc_sum.SetDirectory(0)

    # Process events
    for i in range(n_events):
        elec_tree.GetEntry(i)
        if (i + 1) % 5000 == 0:
            progress = 100.0 * (i + 1) / n_events
            print(f"\r  Progress: {i+1}/{n_events} ({progress:.1f}%)", end='', flush=True)

        elec_evt = elec_tree.CdElecEvt
        channels = elec_evt.GetElecChannels()

        for ch in channels:
            chid = ch.getChannelID()
            tdcs = ch.getTDCs()

            if len(tdcs) == 0:
                continue

            chtdc = tdcs[0]

            # Create histogram for this channel if needed
            if chid not in tdc_histograms:
                h_name = f"H_tdc_{chid}"
                h_title = f"TDC Channel {chid};TDC [ns];Counts"
                tdc_histograms[chid] = ROOT.TH1F(h_name, h_title, 
                                                 TDC_NBINS, TDC_MIN, TDC_MAX)
                tdc_histograms[chid].SetDirectory(0)

            # Fill histograms
            tdc_histograms[chid].Fill(chtdc)
            h_tdc_sum.Fill(chtdc)

    print(f"\r  Completed: {n_events} events")
    print(f"  Found {len(tdc_histograms)} channels with TDC data")

    fin.Close()

    # Save ROOT file with all histograms
    print(f"\n  Saving ROOT file: {output_root}")
    fout = ROOT.TFile(output_root, "RECREATE")
    h_tdc_sum.Write()
    for chid in sorted(tdc_histograms.keys()):
        tdc_histograms[chid].Write()
    fout.Close()

    # Save PNG plots for sample channels and sum
    if output_png_dir:
        os.makedirs(output_png_dir, exist_ok=True)
        print(f"\n  Creating PNG plots in: {output_png_dir}")

        # Plot sample channels
        for chid in sample_channels:
            if chid in tdc_histograms:
                png_path = os.path.join(output_png_dir, f"tdc_ch{chid:04d}.png")
                if plot_tdc_channel(tdc_histograms[chid], png_path, chid, 
                                   TDC_CUT_LOW, TDC_CUT_UP):
                    print(f"    ✓ Channel {chid}")
                else:
                    print(f"    ✗ Channel {chid} (empty)")
            else:
                print(f"    ✗ Channel {chid} (not found)")

        # Plot sum
        png_sum_path = os.path.join(output_png_dir, "tdc_sum.png")
        if plot_tdc_sum(h_tdc_sum, png_sum_path, TDC_CUT_LOW, TDC_CUT_UP):
            print(f"    ✓ Sum plot")
        else:
            print(f"    ✗ Sum plot (empty)")

    return {
        'n_channels': len(tdc_histograms),
        'n_events': n_events,
        'histograms': tdc_histograms,
        'sum': h_tdc_sum
    }

# =============================================================================
# MERGE TDC ROOT FILES
# =============================================================================
def merge_tdc_files(input_pattern, output_root, output_png_dir, sample_channels=SAMPLE_CHANNELS):
    """Merge TDC histograms from multiple ROOT files"""
    print(f"\n{'='*60}")
    print("MERGE MODE: Combining TDC histograms")
    print(f"{'='*60}\n")

    # Find input files
    input_files = sorted(glob.glob(input_pattern))
    if not input_files:
        print(f"ERROR: No files match pattern: {input_pattern}")
        return 1

    print(f"Found {len(input_files)} ROOT files to merge:")
    for i, f in enumerate(input_files[:5], 1):
        print(f"  {i}. {os.path.basename(f)}")
    if len(input_files) > 5:
        print(f"  ... and {len(input_files) - 5} more")
    print()

    # Merged histograms
    merged_histograms = {}
    h_tdc_sum_merged = None

    # Process each file
    for idx, input_file in enumerate(input_files, 1):
        print(f"[{idx}/{len(input_files)}] {os.path.basename(input_file)}")

        fin = ROOT.TFile.Open(input_file, "READ")
        if not fin or fin.IsZombie():
            print(f"  ERROR: Cannot open file, skipping...")
            continue

        # Get all TDC histograms
        keys = fin.GetListOfKeys()
        for key in keys:
            h = key.ReadObj()
            if not h.InheritsFrom("TH1"):
                continue

            h_name = h.GetName()

            # Handle sum histogram
            if h_name == "H_tdc_sum":
                if h_tdc_sum_merged is None:
                    h_tdc_sum_merged = h.Clone()
                    h_tdc_sum_merged.SetDirectory(0)
                else:
                    h_tdc_sum_merged.Add(h)

            # Handle channel histograms
            elif h_name.startswith("H_tdc_"):
                if h_name not in merged_histograms:
                    merged_histograms[h_name] = h.Clone()
                    merged_histograms[h_name].SetDirectory(0)
                else:
                    merged_histograms[h_name].Add(h)

        fin.Close()
        print(f"  Added {len(merged_histograms)} channel histograms")

    print(f"\nTotal merged: {len(merged_histograms)} channels")

    # Save merged ROOT file
    print(f"\nSaving merged ROOT file: {output_root}")
    fout = ROOT.TFile(output_root, "RECREATE")
    if h_tdc_sum_merged:
        h_tdc_sum_merged.Write()
    for h_name in sorted(merged_histograms.keys()):
        merged_histograms[h_name].Write()
    fout.Close()
    print("  ✓ Saved")

    # Save PNG plots for sample channels and sum
    if output_png_dir:
        os.makedirs(output_png_dir, exist_ok=True)
        print(f"\nCreating PNG plots in: {output_png_dir}")

        # Plot sample channels
        for chid in sample_channels:
            h_name = f"H_tdc_{chid}"
            if h_name in merged_histograms:
                png_path = os.path.join(output_png_dir, f"tdc_ch{chid:04d}_merged.png")
                if plot_tdc_channel(merged_histograms[h_name], png_path, chid,
                                   TDC_CUT_LOW, TDC_CUT_UP):
                    print(f"  ✓ Channel {chid}")
                else:
                    print(f"  ✗ Channel {chid} (empty)")
            else:
                print(f"  ✗ Channel {chid} (not found)")

        # Plot sum
        if h_tdc_sum_merged:
            png_sum_path = os.path.join(output_png_dir, "tdc_sum_merged.png")
            if plot_tdc_sum(h_tdc_sum_merged, png_sum_path, TDC_CUT_LOW, TDC_CUT_UP,
                          f"Merged from {len(input_files)} files"):
                print(f"  ✓ Sum plot")
            else:
                print(f"  ✗ Sum plot (empty)")

    print(f"\n{'='*60}")
    print("MERGE COMPLETE")
    print(f"{'='*60}")
    return 0

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract and analyze TDC histograms from RTRAW files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single RTRAW file:
  python plot_tdc_from_rtraw.py input.rtraw output.root --png-dir plots/

  # Merge multiple TDC ROOT files:
  python plot_tdc_from_rtraw.py --merge "tdc_RUN*.root" merged.root --png-dir plots_merged/
"""
    )

    parser.add_argument('input', help='Input RTRAW file or pattern for merge mode')
    parser.add_argument('output_root', help='Output ROOT file')
    parser.add_argument('--png-dir', default=None, 
                       help='Directory for PNG plots (sample channels + sum)')
    parser.add_argument('--merge', action='store_true',
                       help='Merge mode: combine TDC histograms from multiple ROOT files')
    parser.add_argument('--sample-channels', default='100,1000,2000,5000,7000',
                       help='Comma-separated channel IDs to plot as PNG')

    args = parser.parse_args()

    # Parse sample channels
    sample_channels = [int(c.strip()) for c in args.sample_channels.split(',')]

    print("="*60)
    print("TDC ANALYSIS FROM RTRAW")
    print("="*60)
    print(f"TDC cut window: [{TDC_CUT_LOW}, {TDC_CUT_UP}] ns")
    print(f"Sample channels for PNG: {sample_channels}")
    print()

    if args.merge:
        # Merge mode
        sys.exit(merge_tdc_files(args.input, args.output_root, args.png_dir, sample_channels))
    else:
        # Single file processing mode
        result = process_rtraw_file(args.input, args.output_root, args.png_dir, sample_channels)
        if result is None:
            sys.exit(1)

        print(f"\n{'='*60}")
        print("SUCCESS")
        print(f"{'='*60}")
        print(f"Processed: {result['n_events']} events")
        print(f"Channels: {result['n_channels']}")
        print(f"Output ROOT: {args.output_root}")
        if args.png_dir:
            print(f"PNG plots: {args.png_dir}/")
        print("="*60)
        sys.exit(0)
