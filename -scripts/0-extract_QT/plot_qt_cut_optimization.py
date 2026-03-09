#!/usr/bin/env python3
"""
plot_qt_cut_optimization.py — Visualize ADC vs TDC distributions for cut optimization

PURPOSE:
  Generate diagnostic plots from QT2D ROOT files to help determine optimal
  ADC and TDC cuts for rejecting high-energy events.

OUTPUT PLOTS:
  1. Per-channel TDC vs ADC 2D scatter (with cut lines)
  2. ADC distribution comparison (below/above threshold)
  3. TDC window optimization
  4. Cut efficiency summary

USAGE:
  python plot_qt_cut_optimization.py QT2D_RUN1295_001.root --output-dir plots/
  python plot_qt_cut_optimization.py QT2D_RUN1295_001.root --channel 42 --save-png

Author: G. Ferrante
"""

import argparse
import os
import sys
import numpy as np

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    print("WARNING: ROOT not available, using uproot")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("ERROR: matplotlib required for plotting")
    sys.exit(1)

try:
    import uproot
    HAS_UPROOT = True
except ImportError:
    HAS_UPROOT = False


# Default cut values (should match extract_qt_2d.py)
ADC_HIT_MAX_DEFAULT = 1e5
TDC_HIT_MIN_DEFAULT = 240.0
TDC_HIT_MAX_DEFAULT = 440.0


def load_histogram_root(filepath, histname):
    """Load histogram using ROOT."""
    f = ROOT.TFile.Open(filepath, "READ")
    h = f.Get(histname)
    if not h:
        f.Close()
        return None, None, None
    
    # Extract data
    if isinstance(h, ROOT.TH2):
        nx = h.GetNbinsX()
        ny = h.GetNbinsY()
        data = np.zeros((ny, nx))
        for i in range(1, nx+1):
            for j in range(1, ny+1):
                data[j-1, i-1] = h.GetBinContent(i, j)
        x_edges = np.array([h.GetXaxis().GetBinLowEdge(i) for i in range(1, nx+2)])
        y_edges = np.array([h.GetYaxis().GetBinLowEdge(i) for i in range(1, ny+2)])
        f.Close()
        return data, x_edges, y_edges
    elif isinstance(h, ROOT.TH1):
        nbins = h.GetNbinsX()
        data = np.array([h.GetBinContent(i) for i in range(1, nbins+1)])
        edges = np.array([h.GetXaxis().GetBinLowEdge(i) for i in range(1, nbins+2)])
        f.Close()
        return data, edges, None
    
    f.Close()
    return None, None, None


def load_histogram_uproot(filepath, histname):
    """Load histogram using uproot."""
    with uproot.open(filepath) as f:
        try:
            h = f[histname]
            data = h.values()
            if hasattr(h, 'axis'):
                # 1D
                edges = h.axis().edges()
                return data, edges, None
            else:
                # 2D
                x_edges = h.axes[0].edges()
                y_edges = h.axes[1].edges()
                return data.T, x_edges, y_edges
        except:
            return None, None, None


def load_histogram(filepath, histname):
    """Load histogram using available backend."""
    if HAS_UPROOT:
        return load_histogram_uproot(filepath, histname)
    elif HAS_ROOT:
        return load_histogram_root(filepath, histname)
    else:
        raise RuntimeError("Neither ROOT nor uproot available")


def plot_qt_2d_scatter(filepath, channel, output_dir,
                        adc_cut=ADC_HIT_MAX_DEFAULT,
                        tdc_min=TDC_HIT_MIN_DEFAULT,
                        tdc_max=TDC_HIT_MAX_DEFAULT):
    """
    Plot TDC vs ADC 2D scatter for a single channel with cut lines.
    """
    
    # Load both all and clean histograms
    data_all, x_edges, y_edges = load_histogram(filepath, f"QT2D/H_qt_2d_{channel}")
    data_clean, _, _ = load_histogram(filepath, f"QT2D/H_qt_2d_clean_{channel}")
    
    if data_all is None:
        print(f"WARNING: Could not load H_qt_2d_{channel}")
        return None
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Common plot settings
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    
    for ax, data, title in [(axes[0], data_all, f"Channel {channel} - All Hits"),
                             (axes[1], data_clean, f"Channel {channel} - Clean Events")]:
        
        # Plot 2D histogram
        mask = data > 0
        if np.any(mask):
            im = ax.pcolormesh(x_edges, y_edges, data,
                               norm=LogNorm(vmin=0.5, vmax=data.max()),
                               cmap='viridis')
            plt.colorbar(im, ax=ax, label='Counts')
        
        # Draw cut lines
        ax.axvline(tdc_min, color='red', linestyle='--', linewidth=1.5,
                   label=f'TDC min = {tdc_min:.0f} ns')
        ax.axvline(tdc_max, color='red', linestyle='--', linewidth=1.5,
                   label=f'TDC max = {tdc_max:.0f} ns')
        ax.axhline(adc_cut, color='orange', linestyle='--', linewidth=1.5,
                   label=f'ADC cut = {adc_cut:.0e}')
        
        # Shade accepted region
        ax.axvspan(tdc_min, tdc_max, alpha=0.1, color='green')
        ax.axhspan(0, adc_cut, alpha=0.1, color='green')
        
        ax.set_xlabel('TDC [ns]')
        ax.set_ylabel('ADC [counts]')
        ax.set_title(title)
        ax.legend(loc='upper right', fontsize=8)
        ax.set_xlim(x_edges[0], x_edges[-1])
        ax.set_ylim(y_edges[0], min(y_edges[-1], 2e5))  # Focus on region near cut
    
    plt.tight_layout()
    
    # Save
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, f"qt_2d_ch{channel:05d}.png")
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {outpath}")
    return outpath


def plot_adc_cut_comparison(filepath, output_dir, adc_cut=ADC_HIT_MAX_DEFAULT):
    """
    Plot ADC distribution comparison: below vs above threshold.
    """
    
    data_below, edges_below, _ = load_histogram(filepath, "H_adc_below_cut")
    data_above, edges_above, _ = load_histogram(filepath, "H_adc_above_cut")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Full ADC range (log scale)
    ax = axes[0]
    if data_below is not None:
        centers = (edges_below[:-1] + edges_below[1:]) / 2
        ax.step(centers, data_below, where='mid', color='blue',
                label=f'ADC < {adc_cut:.0e}', linewidth=0.8)
    if data_above is not None:
        centers = (edges_above[:-1] + edges_above[1:]) / 2
        ax.step(centers, data_above, where='mid', color='red',
                label=f'ADC ≥ {adc_cut:.0e}', linewidth=0.8)
    
    ax.axvline(adc_cut, color='orange', linestyle='--', linewidth=2,
               label=f'Cut = {adc_cut:.0e}')
    ax.set_xlabel('ADC [counts]')
    ax.set_ylabel('Hits')
    ax.set_yscale('log')
    ax.set_xlim(0, 2e6)
    ax.legend()
    ax.set_title('ADC Distribution: Below vs Above Cut')
    
    # Right: Zoom on transition region
    ax = axes[1]
    if data_below is not None:
        centers = (edges_below[:-1] + edges_below[1:]) / 2
        mask = centers > adc_cut * 0.3
        ax.step(centers[mask], data_below[mask], where='mid', color='blue',
                label='Below cut', linewidth=1)
    
    ax.axvline(adc_cut, color='orange', linestyle='--', linewidth=2)
    ax.set_xlabel('ADC [counts]')
    ax.set_ylabel('Hits')
    ax.set_yscale('log')
    ax.set_xlim(adc_cut * 0.3, adc_cut * 1.5)
    ax.set_title('Zoom: Transition Region')
    
    # Add annotation about expected PE range
    gain = 6000  # ADC/PE
    ax.axvline(7 * gain, color='green', linestyle=':', linewidth=1.5,
               label=f'7 PE = {7*gain:.0f} ADC')
    ax.legend()
    
    plt.tight_layout()
    
    outpath = os.path.join(output_dir, "adc_cut_comparison.png")
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {outpath}")
    return outpath


def plot_tdc_window_optimization(filepath, output_dir,
                                  tdc_min=TDC_HIT_MIN_DEFAULT,
                                  tdc_max=TDC_HIT_MAX_DEFAULT):
    """
    Plot TDC distributions to optimize the time window.
    """
    
    # Load a few representative channels
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    channels = [0, 10, 50, 100]  # Sample channels
    
    for ax, ch in zip(axes.flat, channels):
        data_all, edges, _ = load_histogram(filepath, f"TDC/H_tdc_{ch}")
        data_clean, _, _ = load_histogram(filepath, f"TDC/H_tdc_clean_{ch}")
        
        if data_all is not None:
            centers = (edges[:-1] + edges[1:]) / 2
            ax.step(centers, data_all, where='mid', color='gray', alpha=0.5,
                    label='All hits', linewidth=0.8)
        
        if data_clean is not None:
            ax.step(centers, data_clean, where='mid', color='blue',
                    label='Clean events', linewidth=1)
        
        # Draw window
        ax.axvline(tdc_min, color='red', linestyle='--', linewidth=1.5)
        ax.axvline(tdc_max, color='red', linestyle='--', linewidth=1.5)
        ax.axvspan(tdc_min, tdc_max, alpha=0.2, color='green',
                   label=f'Window [{tdc_min:.0f}, {tdc_max:.0f}] ns')
        
        ax.set_xlabel('TDC [ns]')
        ax.set_ylabel('Hits')
        ax.set_title(f'Channel {ch}')
        ax.legend(fontsize=8)
        ax.set_xlim(0, 1000)
    
    plt.suptitle('TDC Window Optimization', fontsize=14)
    plt.tight_layout()
    
    outpath = os.path.join(output_dir, "tdc_window_optimization.png")
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {outpath}")
    return outpath


def plot_event_summary(filepath, output_dir):
    """
    Plot event-level summary distributions.
    """
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Total ADC
    ax = axes[0, 0]
    data_all, edges, _ = load_histogram(filepath, "H_totalADC_all")
    data_clean, _, _ = load_histogram(filepath, "H_totalADC_clean")
    
    if data_all is not None:
        centers = (edges[:-1] + edges[1:]) / 2
        ax.step(centers, data_all, where='mid', color='gray', alpha=0.5,
                label='All events')
    if data_clean is not None:
        ax.step(centers, data_clean, where='mid', color='blue',
                label='Clean events')
    
    ax.axvline(8e8, color='red', linestyle='--', label='Muon threshold')
    ax.set_xlabel('Total ADC [counts]')
    ax.set_ylabel('Events')
    ax.set_yscale('log')
    ax.legend()
    ax.set_title('Event Total ADC')
    
    # nHit
    ax = axes[0, 1]
    data_all, edges, _ = load_histogram(filepath, "H_nHit_all")
    data_clean, _, _ = load_histogram(filepath, "H_nHit_clean")
    
    if data_all is not None:
        centers = (edges[:-1] + edges[1:]) / 2
        ax.step(centers, data_all, where='mid', color='gray', alpha=0.5,
                label='All events')
    if data_clean is not None:
        ax.step(centers, data_clean, where='mid', color='blue',
                label='Clean events')
    
    ax.axvline(2000, color='red', linestyle='--', label='nHit min')
    ax.axvline(7000, color='red', linestyle='--', label='nHit max')
    ax.set_xlabel('Number of hit channels')
    ax.set_ylabel('Events')
    ax.set_yscale('log')
    ax.legend()
    ax.set_title('Event nHit')
    
    # Channels above threshold
    ax = axes[1, 0]
    data, edges, _ = load_histogram(filepath, "H_nChannelsAbove")
    
    if data is not None:
        centers = (edges[:-1] + edges[1:]) / 2
        ax.bar(centers, data, width=edges[1]-edges[0], color='orange', alpha=0.7)
    
    ax.set_xlabel(f'Channels with ADC > {ADC_HIT_MAX_DEFAULT:.0e}')
    ax.set_ylabel('Events')
    ax.set_yscale('log')
    ax.set_title('High-ADC Channels per Event')
    
    # Veto efficiency pie chart
    ax = axes[1, 1]
    
    # Try to read metadata
    if HAS_ROOT:
        f = ROOT.TFile.Open(filepath, "READ")
        info = f.Get("extraction_info")
        if info:
            meta = dict(item.split('=') for item in info.GetTitle().split(';'))
            n_events = int(meta.get('N_EVENTS', 0))
            n_clean = int(meta.get('N_CLEAN', 0))
            n_muons = int(meta.get('N_MUONS', 0))
            n_outlier = int(meta.get('N_OUTLIER', 0))
            
            n_other = n_events - n_clean - n_muons - n_outlier
            
            sizes = [n_clean, n_muons, n_outlier, max(0, n_other)]
            labels = [f'Clean ({n_clean})',
                      f'Muon ({n_muons})',
                      f'Outlier ({n_outlier})',
                      f'Other ({max(0, n_other)})']
            colors = ['green', 'red', 'orange', 'gray']
            
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%')
            ax.set_title('Event Classification')
        f.Close()
    else:
        ax.text(0.5, 0.5, 'Metadata not available\n(requires ROOT)',
                ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    
    outpath = os.path.join(output_dir, "event_summary.png")
    plt.savefig(outpath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Saved: {outpath}")
    return outpath


def main():
    parser = argparse.ArgumentParser(
        description="Plot QT distributions for cut optimization"
    )
    parser.add_argument("input_file", help="QT2D ROOT file from extract_qt_2d.py")
    parser.add_argument("--output-dir", default="./qt_plots",
                        help="Output directory for plots")
    parser.add_argument("--channel", type=int, default=None,
                        help="Single channel for 2D scatter (default: all available)")
    parser.add_argument("--adc-cut", type=float, default=ADC_HIT_MAX_DEFAULT,
                        help=f"ADC cut value for visualization (default: {ADC_HIT_MAX_DEFAULT:.0e})")
    parser.add_argument("--tdc-min", type=float, default=TDC_HIT_MIN_DEFAULT,
                        help=f"TDC window minimum (default: {TDC_HIT_MIN_DEFAULT})")
    parser.add_argument("--tdc-max", type=float, default=TDC_HIT_MAX_DEFAULT,
                        help=f"TDC window maximum (default: {TDC_HIT_MAX_DEFAULT})")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"ERROR: Input file not found: {args.input_file}")
        sys.exit(1)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("=" * 60)
    print("QT Cut Optimization Plots")
    print("=" * 60)
    print(f"Input:  {args.input_file}")
    print(f"Output: {args.output_dir}")
    print()
    
    # Event summary
    print("Generating event summary...")
    plot_event_summary(args.input_file, args.output_dir)
    
    # ADC cut comparison
    print("Generating ADC cut comparison...")
    plot_adc_cut_comparison(args.input_file, args.output_dir, args.adc_cut)
    
    # TDC window
    print("Generating TDC window optimization...")
    plot_tdc_window_optimization(args.input_file, args.output_dir,
                                  args.tdc_min, args.tdc_max)
    
    # 2D scatter plots
    if args.channel is not None:
        print(f"Generating 2D scatter for channel {args.channel}...")
        plot_qt_2d_scatter(args.input_file, args.channel, args.output_dir,
                           args.adc_cut, args.tdc_min, args.tdc_max)
    else:
        print("Generating 2D scatter plots for all available channels...")
        # Find available channels
        if HAS_ROOT:
            f = ROOT.TFile.Open(args.input_file, "READ")
            qt2d_dir = f.Get("QT2D")
            if qt2d_dir:
                channels = []
                for key in qt2d_dir.GetListOfKeys():
                    name = key.GetName()
                    if name.startswith("H_qt_2d_") and "_clean" not in name:
                        try:
                            ch = int(name.split("_")[-1])
                            channels.append(ch)
                        except ValueError:
                            pass
                f.Close()
                
                for ch in sorted(channels)[:20]:  # Limit to first 20
                    plot_qt_2d_scatter(args.input_file, ch, args.output_dir,
                                       args.adc_cut, args.tdc_min, args.tdc_max)
    
    print()
    print("=" * 60)
    print("Done! Plots saved to:", args.output_dir)
    print("=" * 60)


if __name__ == "__main__":
    main()
