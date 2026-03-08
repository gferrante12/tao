#!/usr/bin/env python3
"""
compare_run_groups.py - v3.4 - Continuous PE combos + spectra plots + Cs-137 x-axis fix

Major updates from v3.3:
- Added METRIC_KEYS_CONTIN for continuous PE (PEcontin) metrics for RTRAW pipelines
- Added 6 new pipeline combinations per analysis (mixing contin. and discrete PE RTRAW
  with ESD results) for ge68 OV scan, ge68 specific runs, and Cs-137
- Added PE spectra plots for every combination in all three analyses
  (ge68 OV scan x-lim 1000–10800; ge68 specific x-lim 2000–7000; Cs-137 x-lim 1000–7000)
- Fixed Cs-137 x-axis order: RUN1112 full → RUN1344 full → RUN1112 pos-60 → RUN1344 pos-60
- All RTRAW spectra use discrete PE (hist_PE); contin PE variants use hist_PEcontin
- plot_superimposed_spectra accepts optional per-label hist_key_override dict
- New plot_multi_run_spectra function for multi-run spectra overlays

Works on both CNAF and IHEP clusters.
"""

import ROOT
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import argparse
import sys
import os
import glob
import re
import subprocess
import shutil
import tempfile
from collections import OrderedDict

# Cluster detection
def detect_cluster():
    """Detect which cluster we're running on"""
    if os.path.isdir("/storage/gpfs_data/juno"):
        return "CNAF"
    elif os.path.isdir("/junofs/users/gferrante"):
        return "IHEP"
    else:
        return "UNKNOWN"

CLUSTER = detect_cluster()
print(f"Running on cluster: {CLUSTER}")

# Set matplotlib style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (12, 7)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 10

# OV values for runs
OV_MAP = {
    1253: 2.5,
    1257: 3.0,
    1259: 3.5,
    1260: 4.0,
    1261: 4.5,
    1262: 5.0,
    1263: 5.5,
}


def sort_key_pesum_order(label):
    """
    Sort key to order peSum before peSum_g
    Returns: (pipeline_type, pesum_type, radial_cut, other)
    where:
        pipeline_type: 0=RTRAW, 1=ESD
        pesum_type: 0=peSum, 1=peSum_g
        radial_cut: 0=no cut, 1=r<150mm
    """
    # RTRAW comes first
    if 'RTRAW' in label:
        return (0, 0, 0, label)
    
    # ESD comes second, with peSum before peSum_g
    # Within each peSum type, no cut before r<150mm
    pesum_type = 1 if 'peSum_g' in label else 0
    radial_cut = 1 if 'r<150mm' in label or 'r150' in label else 0
    
    return (1, pesum_type, radial_cut, label)


def extract_pipeline_info(filepath):
    """
    Extract pipeline information from directory path
    
    Returns dict with: type (rtraw/esd), calib_run, radial_cut, pesum_method
    """
    path_parts = filepath.split('/')
    
    # Find the directory with pipeline info (e.g., "1157_rtraw_default_2026-02-09...")
    pipeline_dir = None
    for part in path_parts:
        if re.match(r'\d{4}_(rtraw|esd)_', part):
            pipeline_dir = part
            break
    
    if not pipeline_dir:
        return {'type': 'unknown', 'label': 'Unknown Pipeline'}
    
    info = {}
    
    # Detect RTRAW vs ESD
    if '_rtraw_' in pipeline_dir:
        info['type'] = 'rtraw'
        
        # Extract calibration info
        if '_default' in pipeline_dir:
            info['calib_run'] = 'default'
            info['label'] = 'RTRAW (default calib)'
        elif re.search(r'_run(\d{4})', pipeline_dir):
            run_match = re.search(r'_run(\d{4})', pipeline_dir)
            info['calib_run'] = run_match.group(1)
            info['label'] = f'RTRAW (RUN{info["calib_run"]} calib)'
        else:
            info['calib_run'] = 'unknown'
            info['label'] = 'RTRAW'
    
    elif '_esd_' in pipeline_dir:
        info['type'] = 'esd'
        
        # Detect radial cut
        if 'noradialcut' in pipeline_dir:
            info['radial_cut'] = 'none'
            radial_label = 'no cut'
        elif 'offsrc_rcut' in pipeline_dir:
            info['radial_cut'] = '150mm_offaxis'
            radial_label = 'r<150mm (off-axis)'
        elif 'rcut150' in pipeline_dir or 'rcut' in pipeline_dir:
            info['radial_cut'] = '150mm'
            radial_label = 'r<150mm'
        else:
            info['radial_cut'] = 'unknown'
            radial_label = 'radial cut'
        
        # Detect peSum method
        if 'pesumbasic' in pipeline_dir:
            info['pesum_method'] = 'peSum'
            pesum_label = 'peSum'
        elif 'pesumg' in pipeline_dir:
            info['pesum_method'] = 'peSum_g'
            pesum_label = 'peSum_g'
        else:
            info['pesum_method'] = 'unknown'
            pesum_label = 'peSum'
        
        info['label'] = f'ESD ({pesum_label}, {radial_label})'
    
    else:
        info['type'] = 'unknown'
        info['label'] = 'Unknown Pipeline'
    
    return info


def extract_spectrum_info(rootfile):
    """Extract spectrum and resolution info from ROOT file with pipeline info"""
    print(f"\nReading: {os.path.basename(rootfile)}")
    
    try:
        f = ROOT.TFile.Open(rootfile, "READ")
        if not f or f.IsZombie():
            print(f"ERROR: Cannot open {rootfile}")
            return None
    except:
        print(f"ERROR: Failed to open {rootfile}")
        return None
    
    # Get energy_info TNamed
    info = f.Get("energy_info")
    if not info:
        print(f"ERROR: energy_info not found in {rootfile}")
        f.Close()
        return None
    
    # Parse info string
    data = {'filename': os.path.basename(rootfile), 'filepath': rootfile}
    for item in info.GetTitle().split(';'):
        if '=' in item:
            key, val = item.split('=', 1)
            try:
                data[key] = float(val)
            except:
                data[key] = val
    
    # Extract pipeline info from filepath
    pipeline_info = extract_pipeline_info(rootfile)
    data.update(pipeline_info)
    
    # Get dark noise
    dn = f.Get("dark_noise_pe")
    data['DN'] = float(dn.GetTitle()) if dn else 0.0
    
    # Get histograms
    h_npe = f.Get("h_PEcontin")
    h_pe = f.Get("h_PEdiscrete")
    
    if h_npe:
        data['hist_PEcontin'] = h_npe.Clone(f"h_PEcontin_{id(data)}")
        data['hist_PEcontin'].SetDirectory(0)
    if h_pe:
        data['hist_PE'] = h_pe.Clone(f"h_PE_{id(data)}")
        data['hist_PE'].SetDirectory(0)
    
    # Extract metrics
    data['resolution_pecontin'] = data.get('RES_PEcontin', -1) * 100 if data.get('RES_PEcontin', -1) > 0 else -1
    data['resolution_pecontin_err'] = data.get('RES_PEcontin_ERR', 0) * 100 if data.get('RES_PEcontin_ERR', 0) > 0 else 0
    data['resolution_pe'] = data.get('RES_PE', -1) * 100 if data.get('RES_PE', -1) > 0 else -1
    data['resolution_pe_err'] = data.get('RES_PE_ERR', 0) * 100 if data.get('RES_PE_ERR', 0) > 0 else 0
    
    data['mean_pecontin'] = data.get('MEAN_PEcontin', -1)
    data['mean_pecontin_err'] = data.get('MEAN_PEcontin_ERR', 0)
    data['mean_pe'] = data.get('MEAN_PE', -1)
    data['mean_pe_err'] = data.get('MEAN_PE_ERR', 0)
    
    data['sigma_pecontin'] = data.get('SIGMA_PEcontin', -1)
    data['sigma_pecontin_err'] = data.get('SIGMA_PEcontin_ERR', 0)
    data['sigma_pe'] = data.get('SIGMA_PE', -1)
    data['sigma_pe_err'] = data.get('SIGMA_PE_ERR', 0)
    
    f.Close()
    
    print(f"  Pipeline: {data['label']}")
    print(f"  DN: {data['DN']:.4f} PE")
    if data['resolution_pecontin'] > 0:
        print(f"  Resolution (PEcontin): {data['resolution_pecontin']:.3f} ± {data['resolution_pecontin_err']:.3f} %")
        print(f"  Mean (PEcontin): {data['mean_pecontin']:.1f} ± {data['mean_pecontin_err']:.1f} PE")
    
    return data


def hist_to_arrays(hist):
    """Convert ROOT histogram to numpy arrays"""
    nbins = hist.GetNbinsX()
    x = np.array([hist.GetBinCenter(i) for i in range(1, nbins+1)])
    y = np.array([hist.GetBinContent(i) for i in range(1, nbins+1)])
    return x, y


def save_plot_dual_format(fig, output_file, root_histograms=None):
    """
    Save plot in both PNG and ROOT formats
    
    Args:
        fig: matplotlib figure
        output_file: output filename (with .png extension)
        root_histograms: optional dict of ROOT histograms to save {name: TH1}
    """
    # Save PNG
    fig.savefig(output_file, bbox_inches='tight', dpi=300)
    print(f"  ✓ Saved PNG: {output_file}")
    
    # Save ROOT file
    root_file = output_file.replace('.png', '.root')
    
    try:
        # Create ROOT file
        rf = ROOT.TFile.Open(root_file, "RECREATE")
        
        # Save ROOT histograms if provided
        if root_histograms:
            for name, hist in root_histograms.items():
                if hist:
                    hist_clone = hist.Clone(name)
                    hist_clone.Write()
        
        # Save matplotlib plot as TCanvas
        # Create a TCanvas and save the matplotlib figure to it
        canvas_name = os.path.basename(output_file).replace('.png', '_canvas')
        c = ROOT.TCanvas(canvas_name, canvas_name, 1200, 700)
        
        # Save matplotlib figure to a temporary PNG, then load into ROOT
        temp_png = output_file + ".temp.png"
        fig.savefig(temp_png, bbox_inches='tight', dpi=150)
        
        # Note: ROOT can't directly import PNG, so we save the canvas info
        # as a TNamed object with metadata
        info = ROOT.TNamed("plot_info", 
                          f"matplotlib_plot;png_file={os.path.basename(output_file)}")
        info.Write()
        
        # Clean up temp file
        if os.path.exists(temp_png):
            os.remove(temp_png)
        
        c.Write()
        rf.Close()
        print(f"  ✓ Saved ROOT: {root_file}")
        
    except Exception as e:
        print(f"  ⚠ Warning: Could not save ROOT file: {e}")
    
    plt.close(fig)


def plot_superimposed_spectra(data_dict, output_file, title, xlim=(1000, 11000), use_pe=True,
                              normalize=False, hist_key_override=None):
    """
    Plot superimposed spectra as histograms.

    Args:
        data_dict: dict with labels as keys and data dicts as values
        output_file: output filename
        title: plot title
        xlim: tuple (xmin, xmax), default (1000, 11000)
        use_pe: True → default to discrete PE ('hist_PE'), False → 'hist_PEcontin'
        normalize: False for absolute counts (default), True for normalized
        hist_key_override: optional dict {label: 'hist_PE' | 'hist_PEcontin'} to override
                           the PE type per label (takes precedence over use_pe).
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    sorted_items = sorted(data_dict.items(), key=lambda x: sort_key_pesum_order(x[0]))
    colors = plt.cm.tab10(np.linspace(0, 0.9, max(len(sorted_items), 1)))
    root_histograms = {}

    for i, (label, data) in enumerate(sorted_items):
        # Determine which histogram to use
        if hist_key_override and label in hist_key_override:
            hist_key = hist_key_override[label]
        else:
            hist_key = 'hist_PE' if use_pe else 'hist_PEcontin'

        if hist_key in data and data[hist_key]:
            x, y = hist_to_arrays(data[hist_key])
            y_plot = y / np.max(y) if (normalize and np.max(y) > 0) else y
            ax.step(x, y_plot, where='mid', label=label, color=colors[i], linewidth=2, alpha=0.8)
            safe_label = label.replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').replace('/', '_')
            root_histograms[f"h_{safe_label}"] = data[hist_key]

    xlabel = 'PE (DN-corrected)'
    ax.set_xlabel(xlabel, fontsize=13, fontweight='bold')
    ylabel = 'Normalized Counts' if normalize else 'Counts'
    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlim(xlim)
    plt.tight_layout()
    save_plot_dual_format(fig, output_file, root_histograms)


def plot_multi_run_spectra(all_hist_data, combo_keys, output_file, title, xlim,
                           run_label_map, hist_key_map=None):
    """
    Plot superimposed PE spectra for multiple runs and multiple pipelines.

    Each curve corresponds to one (pipe_key, run) combination.
    Pipelines are distinguished by color; runs by line style.

    Args:
        all_hist_data: dict {pipe_key: {run: data_dict_from_extract_spectrum_info}}
        combo_keys:    list of pipe_keys to include
        output_file:   output PNG path
        title:         plot title
        xlim:          (xmin, xmax) for x-axis
        run_label_map: dict {run: label_string} e.g. {1253: 'OV 2.5V', ...}
        hist_key_map:  dict {pipe_key: 'hist_PE'|'hist_PEcontin'} — defaults to 'hist_PE'
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    if hist_key_map is None:
        hist_key_map = {}

    # Assign colors to pipeline keys, line styles to runs
    pipe_colors = plt.cm.tab10(np.linspace(0, 0.9, max(len(combo_keys), 1)))
    run_order   = sorted(run_label_map.keys())
    line_styles = ['-', '--', ':', '-.', (0, (5, 1)), (0, (3, 1, 1, 1))]

    root_histograms = {}
    has_data = False

    for pi, pipe_key in enumerate(combo_keys):
        if pipe_key not in all_hist_data:
            continue
        color   = pipe_colors[pi]
        hk      = hist_key_map.get(pipe_key, 'hist_PE')
        pipe_label_shown = False

        for ri, run in enumerate(run_order):
            if run not in all_hist_data[pipe_key]:
                continue
            run_data = all_hist_data[pipe_key][run]
            hist = run_data.get(hk)
            if hist is None:
                continue

            x, y = hist_to_arrays(hist)
            # mask to xlim for auto-scaling y
            mask = (x >= xlim[0]) & (x <= xlim[1])

            pipe_lbl = run_data.get('label', pipe_key)
            run_lbl  = run_label_map[run]
            pe_type  = 'PEcontin' if hk == 'hist_PEcontin' else 'PE'
            curve_label = f"{pipe_lbl} [{pe_type}] — {run_lbl}"

            ax.step(x, y, where='mid',
                    label=curve_label,
                    color=color,
                    linestyle=line_styles[ri % len(line_styles)],
                    linewidth=1.8, alpha=0.85)
            has_data = True

            safe = curve_label.replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').replace('/', '_').replace('[', '').replace(']', '')
            root_histograms[f"h_{safe[:60]}"] = hist

    if not has_data:
        print(f"  WARNING: no spectra data for '{title}' — skipping")
        plt.close(fig)
        return

    ax.set_xlabel('PE (DN-corrected)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Counts', fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlim(xlim)
    ax.grid(alpha=0.3)
    ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True,
              fontsize=7, ncol=2)
    plt.tight_layout()
    save_plot_dual_format(fig, output_file, root_histograms)


def _pick_keys(data, metric):
    """
    Per-entry key selection for a given metric ('resolution', 'mean', 'sigma').

    Each pipeline stores both *_pe (discrete) and *_pecontin (continuous) keys.
    Prefer discrete PE (_pe); fall back to _pecontin if _pe is missing or <= 0.
    This replaces the old global use_pe flag which caused silent zeroes when
    a mixed data_dict contained pipelines with only one variant populated.
    """
    pe_key  = f'{metric}_pe'
    pc_key  = f'{metric}_pecontin'
    pe_err  = f'{metric}_pe_err'
    pc_err  = f'{metric}_pecontin_err'
    val_pe  = data.get(pe_key, -1)
    val_pc  = data.get(pc_key, -1)
    # Use discrete PE if it is valid; otherwise fall back to continuous
    if val_pe is not None and val_pe > 0:
        return pe_key, pe_err
    elif val_pc is not None and val_pc > 0:
        return pc_key, pc_err
    else:
        return pe_key, pe_err  # default (will return 0 from .get)


def plot_resolution_bars(data_dict, output_file, title):
    """
    Plot bar chart of energy resolutions.

    Key selection is per-entry via _pick_keys(): discrete PE is preferred,
    falling back to PEcontin if discrete is not available.
    The old global use_pe parameter is removed.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    labels = list(data_dict.keys())
    resolutions = []
    errors = []

    for label in labels:
        data = data_dict[label]
        res_key, err_key = _pick_keys(data, 'resolution')
        res = data.get(res_key, 0)
        err = data.get(err_key, 0)
        resolutions.append(res if res > 0 else 0)
        errors.append(err if err > 0 else 0)

    colors = plt.cm.tab10(np.linspace(0, 0.9, len(labels)))
    x_pos = np.arange(len(labels))

    bars = ax.bar(x_pos, resolutions, yerr=errors, color=colors,
                   alpha=0.8, edgecolor='black', linewidth=1.5,
                   error_kw={'elinewidth': 2, 'capsize': 5, 'capthick': 2})

    for i, (bar, res, err) in enumerate(zip(bars, resolutions, errors)):
        if res > 0:
            height = bar.get_height()
            label_y = height + err + 0.05
            ax.text(bar.get_x() + bar.get_width()/2., label_y,
                   f'{res:.3f}±{err:.3f}%',
                   ha='center', va='bottom', fontweight='bold', fontsize=8)

    ylabel = 'Energy Resolution σ/(μ-DN) [%]'
    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=9, rotation=20, ha='right')
    ax.set_ylim(0, max(resolutions) * 1.2 if max(resolutions) > 0 else 5)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    root_histograms = {}
    nbins = len(labels)
    h_resolution = ROOT.TH1F("h_resolution", title, nbins, 0, nbins)
    for i, (label, res, err) in enumerate(zip(labels, resolutions, errors)):
        h_resolution.SetBinContent(i+1, res)
        h_resolution.SetBinError(i+1, err)
        h_resolution.GetXaxis().SetBinLabel(i+1, label)
    h_resolution.SetYTitle("Energy Resolution [%]")
    root_histograms["h_resolution"] = h_resolution

    save_plot_dual_format(fig, output_file, root_histograms)


def plot_metric_bars(data_dict, output_file, title, metric='mean'):
    """
    Plot bar chart of mean, sigma, or resolution.

    Key selection is per-entry via _pick_keys(): discrete PE is preferred,
    falling back to PEcontin if discrete is not available.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    sorted_items = sorted(data_dict.items(), key=lambda x: sort_key_pesum_order(x[0]))
    labels = [item[0] for item in sorted_items]
    sorted_dict = OrderedDict(sorted_items)

    if metric == 'mean':
        ylabel = 'Peak Mean (μ-DN) [PE]'
    elif metric == 'sigma':
        ylabel = 'Peak Sigma (σ) [PE]'
    elif metric == 'resolution':
        ylabel = 'Energy Resolution σ/(μ-DN) [%]'
    else:
        return

    values = []
    errors = []
    for label in labels:
        data = sorted_dict[label]
        val_key, err_key = _pick_keys(data, metric)
        val = data.get(val_key, 0)
        err = data.get(err_key, 0)
        values.append(val if val > 0 else 0)
        errors.append(err if err > 0 else 0)

    colors = plt.cm.tab10(np.linspace(0, 0.9, len(labels)))
    x_pos = np.arange(len(labels))

    bars = ax.bar(x_pos, values, yerr=errors, color=colors,
                   alpha=0.8, edgecolor='black', linewidth=1.5,
                   error_kw={'elinewidth': 2, 'capsize': 5, 'capthick': 2})

    for i, (bar, val, err) in enumerate(zip(bars, values, errors)):
        if val > 0:
            height = bar.get_height()
            label_y = height + err + max(values) * 0.02
            if metric == 'resolution':
                ax.text(bar.get_x() + bar.get_width()/2., label_y,
                       f'{val:.3f}±{err:.3f}%',
                       ha='center', va='bottom', fontweight='bold', fontsize=8)
            else:
                ax.text(bar.get_x() + bar.get_width()/2., label_y,
                       f'{val:.1f}±{err:.1f}',
                       ha='center', va='bottom', fontweight='bold', fontsize=8)

    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=9, rotation=20, ha='right')
    ax.set_ylim(0, max(values) * 1.2 if max(values) > 0 else 100)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    root_histograms = {}
    nbins = len(labels)
    h_metric = ROOT.TH1F(f"h_{metric}", title, nbins, 0, nbins)
    for i, (label, val, err) in enumerate(zip(labels, values, errors)):
        h_metric.SetBinContent(i+1, val)
        h_metric.SetBinError(i+1, err)
        h_metric.GetXaxis().SetBinLabel(i+1, label)
    h_metric.SetYTitle(ylabel)
    root_histograms[f"h_{metric}"] = h_metric

    save_plot_dual_format(fig, output_file, root_histograms)



def plot_ov_scan(run_data_dict, output_prefix, metric='resolution', pesum_method='peSum_g'):
    """
    Plot metric vs OV for OV scan runs
    
    Args:
        run_data_dict: dict with run numbers as keys
        output_prefix: output file prefix
        metric: 'resolution', 'mean', or 'sigma'
        pesum_method: 'peSum_g' or 'peSum'
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ovs = []
    values = []
    errors = []
    run_labels = []
    
    if metric == 'resolution':
        ylabel = 'Energy Resolution σ/(μ-DN) [%]'
        title_metric = 'Energy Resolution'
    elif metric == 'mean':
        ylabel = 'Peak Mean (μ-DN) [PE]'
        title_metric = 'Peak Mean'
    elif metric == 'sigma':
        ylabel = 'Peak Sigma (σ) [PE]'
        title_metric = 'Peak Sigma'
    else:
        ylabel = 'Energy Resolution σ/(μ-DN) [%]'
        title_metric = 'Energy Resolution'
        metric = 'resolution'
    
    # Key selection is per-entry via _pick_keys()
    for run, data in sorted(run_data_dict.items()):
        if run in OV_MAP:
            ovs.append(OV_MAP[run])
            val_key, err_key = _pick_keys(data, metric)
            val = data.get(val_key, -1)
            err = data.get(err_key, 0)
            values.append(val if val > 0 else 0)
            errors.append(err if err > 0 else 0)
            run_labels.append(f'RUN{run}')
    
    if not ovs:
        print(f"  WARNING: No valid OV data for {metric} ({pesum_method})")
        plt.close(fig)
        return
    
    # Plot with error bars
    color = '#2E86AB' if pesum_method == 'peSum_g' else '#A23B72'
    ax.errorbar(ovs, values, yerr=errors, fmt='o-', 
                color=color, markersize=8, linewidth=2,
                capsize=5, capthick=2, label=pesum_method)
    
    # Add run labels
    for ov, val, run_label in zip(ovs, values, run_labels):
        if val > 0:
            ax.annotate(run_label, xy=(ov, val), xytext=(0, 10),
                       textcoords='offset points', ha='center', fontsize=8)
    
    ax.set_xlabel('Overvoltage (OV) [V]', fontsize=13, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_title(f'{title_metric} vs OV - {pesum_method}', fontsize=14, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    # Create ROOT TGraphErrors for the OV scan
    root_histograms = {}
    n_points = len(ovs)
    graph = ROOT.TGraphErrors(n_points)
    graph.SetName(f"g_ov_{metric}_{pesum_method.lower().replace('_', '')}")
    graph.SetTitle(f"{title_metric} vs OV - {pesum_method}")
    for i, (ov, val, err) in enumerate(zip(ovs, values, errors)):
        graph.SetPoint(i, ov, val)
        graph.SetPointError(i, 0, err)
    graph.GetXaxis().SetTitle("Overvoltage (OV) [V]")
    graph.GetYaxis().SetTitle(ylabel)
    root_histograms["graph_ov_scan"] = graph
    
    output_file = f"{output_prefix}_ov_{metric}_{pesum_method.lower().replace('_', '')}.png"
    save_plot_dual_format(fig, output_file, root_histograms)




# ─────────────────────────────────────────────────────────────────────────────
# CONSISTENT PIPELINE STYLING
# ─────────────────────────────────────────────────────────────────────────────

_PIPELINE_STYLES = [
    # (color, marker, linestyle, zorder)
    ('#1f77b4', 'o',  '-',  4),   # idx 0 – RTRAW default (discrete PE)       – blue circle solid
    ('#ff7f0e', 's',  '-',  4),   # idx 1 – RTRAW custom  (discrete PE)       – orange square solid
    ('#d62728', '^',  '--', 3),   # idx 2 – ESD peSum nocut                   – red up-tri dashed
    ('#9467bd', 'v',  '--', 3),   # idx 3 – ESD peSum_g nocut                 – purple down-tri dashed
    ('#2ca02c', 'D',  ':',  2),   # idx 4 – ESD peSum rcut                    – green diamond dotted
    ('#17becf', '*',  ':',  2),   # idx 5 – ESD peSum_g rcut                  – cyan star dotted
    ('#aec7e8', 'o',  '--', 4),   # idx 6 – RTRAW default (PEcontin)          – light blue circle dashed
    ('#ffd700', 's',  '--', 4),   # idx 7 – RTRAW custom  (PEcontin)          – yellow square dashed
    ('#8c564b', 'P',  '-.',  2),  # idx 8 – extra
    ('#e377c2', 'X',  '-.',  2),  # idx 9 – extra
]


def get_pipeline_style(label, index=None):
    """Return (color, marker, linestyle, zorder) for a pipeline label."""
    if index is not None:
        s = _PIPELINE_STYLES[index % len(_PIPELINE_STYLES)]
        return {'color': s[0], 'marker': s[1], 'ls': s[2], 'zorder': s[3]}
    # Heuristic from label text
    is_rtraw   = 'RTRAW' in label
    is_contin  = 'PEcontin' in label
    is_default = 'default' in label
    is_pesumg  = 'peSum_g' in label
    is_rcut    = 'r<150mm' in label or 'rcut' in label
    if is_rtraw and is_contin and is_default:
        idx = 6   # light blue dashed  – RTRAW (PEcontin, default calib)
    elif is_rtraw and is_contin:
        idx = 7   # yellow dashed      – RTRAW (PEcontin, custom calib)
    elif is_rtraw and is_default:
        idx = 0   # blue solid         – RTRAW (discrete PE, default calib)
    elif is_rtraw:
        idx = 1   # orange solid       – RTRAW (discrete PE, custom calib)
    elif not is_pesumg and not is_rcut:
        idx = 2
    elif is_pesumg and not is_rcut:
        idx = 3
    elif not is_pesumg and is_rcut:
        idx = 4
    else:
        idx = 5
    s = _PIPELINE_STYLES[idx]
    return {'color': s[0], 'marker': s[1], 'ls': s[2], 'zorder': s[3]}


def plot_multiline_scan(pipelines_data, output_file, title, xlabel, metric='resolution',
                        x_ticklabels=None):
    """
    Plot multiple pipelines on a single scan plot (data points + error bars).

    Args:
        pipelines_data: OrderedDict {label: {'x': [...], 'y': [...], 'yerr': [...]}}
        output_file:    output PNG path
        title:          plot title
        xlabel:         x-axis label
        metric:         'resolution' | 'mean' | 'sigma'
        x_ticklabels:   optional list of tick labels (if x is integer positions)
    """
    METRIC_META = {
        'resolution': ('Energy Resolution σ/(μ-DN) [%]', '.3f', '%'),
        'mean':       ('Peak Mean (μ-DN) [PE]',           '.1f',  ''),
        'sigma':      ('Peak Sigma (σ) [PE]',             '.1f',  ''),
    }
    ylabel, fmt, unit = METRIC_META.get(metric, (metric, '.3f', ''))

    fig, ax = plt.subplots(figsize=(12, 7))
    has_data = False
    root_graphs = {}

    sorted_items = sorted(pipelines_data.items(), key=lambda kv: sort_key_pesum_order(kv[0]))

    for i, (label, pipe_data) in enumerate(sorted_items):
        x    = pipe_data.get('x', [])
        y    = pipe_data.get('y', [])
        yerr = pipe_data.get('yerr', [])

        # Filter out invalid points
        valid = [(xi, yi, ei) for xi, yi, ei in zip(x, y, yerr) if yi > 0]
        if not valid:
            continue

        xv, yv, ev = zip(*valid)
        style = get_pipeline_style(label)

        ax.errorbar(list(xv), list(yv), yerr=list(ev),
                    label=label,
                    fmt=style['marker'],
                    linestyle=style['ls'],
                    color=style['color'],
                    markersize=8, linewidth=2,
                    capsize=5, capthick=2,
                    zorder=style['zorder'])
        has_data = True

        # ROOT TGraphErrors
        g = ROOT.TGraphErrors(len(xv))
        safe = label.replace(' ', '_').replace('(','').replace(')','').replace(',','').replace('/','_')
        g.SetName(f"g_{safe}_{metric}")
        for j, (xi, yi, ei) in enumerate(zip(xv, yv, ev)):
            g.SetPoint(j, xi, yi)
            g.SetPointError(j, 0, ei)
        root_graphs[g.GetName()] = g

    if not has_data:
        print(f"  WARNING: no data for plot '{title}' — skipping")
        plt.close(fig)
        return

    ax.set_xlabel(xlabel, fontsize=13, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='best', frameon=True, fancybox=True, shadow=True, fontsize=10)
    ax.grid(alpha=0.3)

    if x_ticklabels:
        all_x = sorted(set(xi for pd in pipelines_data.values() for xi in pd.get('x', [])))
        ax.set_xticks(all_x)
        ax.set_xticklabels(x_ticklabels[:len(all_x)], rotation=20, ha='right')

    plt.tight_layout()
    save_plot_dual_format(fig, output_file, root_graphs)


def _collect_ov_pipe_data(base_dir, runs, pattern, metric_keys):
    """
    Collect OV-scan data for one pipeline pattern.
    Returns dict {label: {x (OV), y, yerr}} or None if no data.
    """
    val_key, err_key = metric_keys
    xs, ys, es = [], [], []
    label = None
    for run in runs:
        files = find_spectrum_files(base_dir, run, pattern)
        if not files:
            continue
        data = extract_spectrum_info(files[0])
        if data is None or run not in OV_MAP:
            continue
        v = data.get(val_key, -1)
        e = data.get(err_key, 0)
        if v > 0:
            xs.append(OV_MAP[run])
            ys.append(v)
            es.append(e)
            if label is None:
                label = data.get('label', pattern)
    if not xs:
        return None
    return label, {'x': xs, 'y': ys, 'yerr': es}


def _collect_specific_pipe_data(base_dir, runs, pattern, metric_keys):
    """
    Collect specific-run data for one pipeline pattern.
    Returns (label, {x: run_positions, y, yerr, run_labels}) or None.
    """
    val_key, err_key = metric_keys
    xs, ys, es, rlabels = [], [], [], []
    label = None
    for i, run in enumerate(runs):
        # For RTRAW custom, pattern is run-specific
        actual_pattern = pattern.replace('{run}', str(run))
        files = find_spectrum_files(base_dir, run, actual_pattern)
        if not files:
            ys.append(-1)
            es.append(0)
        else:
            data = extract_spectrum_info(files[0])
            if data is None:
                ys.append(-1)
                es.append(0)
            else:
                v = data.get(val_key, -1)
                e = data.get(err_key, 0)
                ys.append(v if v > 0 else -1)
                es.append(e)
                if label is None:
                    label = data.get('label', actual_pattern)
        xs.append(i)
        rlabels.append(f'RUN{run}')

    if label is None or all(y <= 0 for y in ys):
        return None
    return label, {'x': xs, 'y': ys, 'yerr': es, 'run_labels': rlabels}


METRIC_KEYS = {
    'resolution': ('resolution_pe', 'resolution_pe_err'),
    'mean':       ('mean_pe',       'mean_pe_err'),
    'sigma':      ('sigma_pe',      'sigma_pe_err'),
}

# Continuous PE metrics (for RTRAW contin PE variants)
METRIC_KEYS_CONTIN = {
    'resolution': ('resolution_pecontin', 'resolution_pecontin_err'),
    'mean':       ('mean_pecontin',       'mean_pecontin_err'),
    'sigma':      ('sigma_pecontin',      'sigma_pecontin_err'),
}

# Pipeline keys that use continuous PE (for histogram selection)
CONTIN_PIPE_KEYS = {'rtraw_default_contin', 'rtraw_custom_contin'}

# Maps pipeline key → which histogram key to use for spectra plots
PIPE_HIST_KEY_MAP = {
    'rtraw_default_contin': 'hist_PEcontin',
    'rtraw_custom_contin':  'hist_PEcontin',
    'rtraw_default':        'hist_PE',
    'rtraw_custom':         'hist_PE',
    'esd_pesum_nocut':      'hist_PE',
    'esd_pesumg_nocut':     'hist_PE',
    'esd_pesum_rcut':       'hist_PE',
    'esd_pesumg_rcut':      'hist_PE',
    # Cs-137 off-axis variants
    'esd_pesum_offsrc_rcut':    'hist_PE',
    'esd_pesumg_offsrc_rcut':   'hist_PE',
}

# Canonical human-readable label for each pipeline key.
# Used to fix "Unknown Pipeline" labels on merged pos-60 files whose path
# does not contain the pattern that extract_pipeline_info() expects.
# For rtraw_custom the {run} placeholder is filled at load time.
PIPE_KEY_LABEL = {
    'rtraw_default':            'RTRAW (default calib)',
    'rtraw_custom':             'RTRAW (RUN{run} calib)',
    'rtraw_default_contin':     'RTRAW (PEcontin, default calib)',
    'rtraw_custom_contin':      'RTRAW (PEcontin, RUN{run} calib)',
    'esd_pesum_nocut':          'ESD (peSum, no cut)',
    'esd_pesumg_nocut':         'ESD (peSum_g, no cut)',
    'esd_pesum_rcut':           'ESD (peSum, r<150mm)',
    'esd_pesumg_rcut':          'ESD (peSum_g, r<150mm)',
    'esd_pesum_offsrc_rcut':    'ESD (peSum, r<150mm off-axis)',
    'esd_pesumg_offsrc_rcut':   'ESD (peSum_g, r<150mm off-axis)',
}

def _canonical_label(pipe_key, run=None):
    """Return the canonical display label for pipe_key, substituting run if needed."""
    tmpl = PIPE_KEY_LABEL.get(pipe_key, pipe_key)
    if '{run}' in tmpl and run is not None:
        return tmpl.replace('{run}', str(run))
    return tmpl


def find_spectrum_files(base_dir, run, pattern_hint=''):
    """
    Find spectrum files for a given run with optional pattern hint
    
    Args:
        base_dir: base directory (should already include energy_resolution path)
        run: run number
        pattern_hint: optional hint like 'rtraw_default', 'esd_rcut150_pesumg', etc.
    
    Returns:
        list of matching file paths
    """
    # Pattern: RUN{run}/{run}_{pattern_hint}*/spectrum_RUN{run}-MERGED.root
    # Note: base_dir from shell scripts already includes /energy_resolution/
    if pattern_hint:
        search_pattern = f"{base_dir}/RUN{run}/{run}_{pattern_hint}*/spectrum_RUN{run}-MERGED.root"
    else:
        search_pattern = f"{base_dir}/RUN{run}/{run}_*/spectrum_RUN{run}-MERGED.root"
    
    files = glob.glob(search_pattern)
    
    # Sort by timestamp (most recent first)
    files = sorted(files, reverse=True)
    
    return files


def compare_multi_pipeline_run(base_dir, run, output_dir, pipeline_patterns, title_prefix):
    """
    Compare multiple pipelines for a single run
    
    Args:
        base_dir: base directory
        run: run number
        output_dir: output directory
        pipeline_patterns: list of pattern hints (e.g., ['rtraw_default', 'esd_rcut150_pesumg'])
        title_prefix: prefix for plot titles (e.g., 'Ge-68 RUN1253')
    """
    print(f"\n{'='*80}")
    print(f"MULTI-PIPELINE COMPARISON: {title_prefix}")
    print(f"{'='*80}")
    
    data_all = {}
    
    for pattern in pipeline_patterns:
        files = find_spectrum_files(base_dir, run, pattern)
        if files:
            # Take most recent file
            data = extract_spectrum_info(files[0])
            if data:
                # Use pipeline label as key
                data_all[data['label']] = data
        else:
            print(f"  WARNING: No files found for pattern '{pattern}'")
    
    if len(data_all) < 2:
        print(f"ERROR: Not enough pipelines found (need at least 2, found {len(data_all)})")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Separate data into RTRAW and ESD pipelines
    data_rtraw = {k: v for k, v in data_all.items() if v.get('type') == 'rtraw'}
    data_esd = {k: v for k, v in data_all.items() if v.get('type') == 'esd'}
    
    # 1a. Superimposed spectra - RTRAW only (if available)
    if len(data_rtraw) >= 1:
        output = f"{output_dir}/{title_prefix.replace(' ', '_').lower()}_spectra_rtraw.png"
        title = f"{title_prefix} - PE Spectra (RTRAW Pipelines)"
        plot_superimposed_spectra(data_rtraw, output, title, xlim=(1000, 11000), normalize=False)
    
    # 1b. Superimposed spectra - ESD only (if available)
    if len(data_esd) >= 1:
        output = f"{output_dir}/{title_prefix.replace(' ', '_').lower()}_spectra_esd.png"
        title = f"{title_prefix} - PE Spectra (ESD Pipelines)"
        plot_superimposed_spectra(data_esd, output, title, xlim=(1000, 11000), normalize=False)
    
    # 1c. Superimposed spectra - ALL (combined, for reference)
    output = f"{output_dir}/{title_prefix.replace(' ', '_').lower()}_spectra_all.png"
    title = f"{title_prefix} - PE Spectra Comparison (All Pipelines)"
    plot_superimposed_spectra(data_all, output, title, xlim=(1000, 11000), normalize=False)
    
    # 2. Resolution bar chart
    output = f"{output_dir}/{title_prefix.replace(' ', '_').lower()}_resolution.png"
    title = f"{title_prefix} - Energy Resolution"
    plot_metric_bars(data_all, output, title, metric='resolution')
    
    # 3. Mean bar chart
    output = f"{output_dir}/{title_prefix.replace(' ', '_').lower()}_mean.png"
    title = f"{title_prefix} - Peak Mean"
    plot_metric_bars(data_all, output, title, metric='mean')
    
    # 4. Sigma bar chart
    output = f"{output_dir}/{title_prefix.replace(' ', '_').lower()}_sigma.png"
    title = f"{title_prefix} - Peak Sigma"
    plot_metric_bars(data_all, output, title, metric='sigma')
    
    print(f"\n✓ Multi-pipeline comparison complete for {title_prefix}")


def compare_cs137_runs_1112_1344(base_dir, output_dir, source='rtraw'):
    """
    Compare Cs-137 runs 1112 vs 1344 (legacy function, kept for compatibility)
    """
    print("\n" + "="*80)
    print(f"COMPARING Cs-137: RUN 1112 vs RUN 1344 ({source.upper()})")
    print("="*80)
    
    # This is now handled by individual multi-pipeline comparisons
    print("Use compare_multi_pipeline_run() for detailed comparisons")


def compare_ge68_ov_scan(base_dir, output_dir):
    """
    Compare Ge-68 OV scan: runs 1253-1263.
    Produces resolution / mean / sigma vs OV plots for all pipeline combinations,
    plus PE spectra plots for each combination.
    """
    print("\n" + "="*80)
    print("COMPARING Ge-68: OV SCAN (RUNS 1253-1263)")
    print("="*80)

    runs = [1253, 1257, 1259, 1260, 1261, 1262, 1263]
    SPEC_XLIM = (1000, 10800)
    os.makedirs(output_dir, exist_ok=True)

    # ── Pipeline patterns ─────────────────────────────────────────────────────
    # key → search pattern; contin PE variants share the same pattern as their
    # discrete counterpart but use METRIC_KEYS_CONTIN at load time.
    OV_PATTERNS = {
        'rtraw_default':          'rtraw_default',
        'rtraw_custom':           'rtraw_run{run}',
        'rtraw_default_contin':   'rtraw_default',          # same files, contin PE
        'rtraw_custom_contin':    'rtraw_run{run}',         # same files, contin PE
        'esd_pesum_nocut':        'esd_noradialcut_pesumbasic',
        'esd_pesumg_nocut':       'esd_noradialcut_pesumg',
        'esd_pesum_rcut':         'esd_rcut150_pesumbasic',
        'esd_pesumg_rcut':        'esd_rcut150_pesumg',
    }

    # ── Load all available data ───────────────────────────────────────────────
    all_pipe_data = {}   # {pipe_key: {label, metrics: {metric: {x,y,yerr}}}}
    all_hist_data  = {}  # {pipe_key: {run: data_dict}}

    for pipe_key, pattern_tmpl in OV_PATTERNS.items():
        use_contin  = pipe_key in CONTIN_PIPE_KEYS
        keys_to_use = METRIC_KEYS_CONTIN if use_contin else METRIC_KEYS

        for metric, mkeys in keys_to_use.items():
            xs, ys, es = [], [], []
            label = None
            for run in runs:
                actual_pattern = pattern_tmpl.replace('{run}', str(run))
                files = find_spectrum_files(base_dir, run, actual_pattern)
                if not files or run not in OV_MAP:
                    continue
                data = extract_spectrum_info(files[0])
                if data is None:
                    continue

                # Cache histogram data (once per pipe_key × run)
                if pipe_key not in all_hist_data:
                    all_hist_data[pipe_key] = {}
                if run not in all_hist_data[pipe_key]:
                    all_hist_data[pipe_key][run] = data

                v = data.get(mkeys[0], -1)
                e = data.get(mkeys[1], 0)
                if v > 0:
                    xs.append(OV_MAP[run])
                    ys.append(v)
                    es.append(e)
                    if label is None:
                        base_lbl = data.get('label', pipe_key)
                        label = (base_lbl.replace('RTRAW (', 'RTRAW (PEcontin, ')
                                 if use_contin else base_lbl)

            if xs and label:
                if pipe_key not in all_pipe_data:
                    all_pipe_data[pipe_key] = {'label': label, 'metrics': {}}
                all_pipe_data[pipe_key]['metrics'][metric] = {'x': xs, 'y': ys, 'yerr': es}

    run_label_map = {run: f"OV {OV_MAP[run]}V (RUN{run})" for run in runs if run in OV_MAP}

    def build_pipes(keys):
        d = {}
        for k in keys:
            if k in all_pipe_data:
                entry = all_pipe_data[k]
                d[entry['label']] = entry['metrics']
        return d

    # ── OV_spectra subfolder: overview plots (all 7 runs, one colour per run) ─
    ov_spectra_dir = os.path.join(output_dir, 'OV_spectra')
    os.makedirs(ov_spectra_dir, exist_ok=True)

    # Line-style cycle for distinguishing multiple pipelines inside one overview plot
    _LS = ['-', '--', ':', '-.', (0, (5, 1)), (0, (3, 1, 1, 1))]

    def _ov_multi_pipe_overview(pipe_specs, out_name, main_title):
        """
        Produce one overview PE-spectra plot where:
          - colour   = OV run (rainbow palette, one per run)
          - linestyle = pipeline (cycled from _LS)

        pipe_specs: list of (pipe_key, hist_key)  e.g.
                    [('esd_pesum_nocut', 'hist_PE'), ('esd_pesum_rcut', 'hist_PE')]

        A legend block for OV colours is placed at upper right; a second block
        for pipeline linestyles is placed at upper left (if >1 pipeline).
        """
        run_list = [r for r in runs if r in OV_MAP]
        fig, ax = plt.subplots(figsize=(16, 8))
        colors = plt.cm.rainbow(np.linspace(0, 1, len(run_list)))
        root_histograms = {}
        y_max = 0.0
        has_data = False

        for pi, (pipe_key, hist_key) in enumerate(pipe_specs):
            ls = _LS[pi % len(_LS)]
            if pipe_key not in all_hist_data:
                continue
            for ri, run in enumerate(run_list):
                if run not in all_hist_data[pipe_key]:
                    continue
                d    = all_hist_data[pipe_key][run]
                hist = d.get(hist_key)
                if hist is None:
                    continue
                x, y = hist_to_arrays(hist)
                ov   = OV_MAP[run]
                # Label: colour legend (run) shown on first pipe only to avoid duplicates
                curve_lbl = f"OV {ov}V (RUN{run})" if pi == 0 else f"_nolegend_{run}_{pi}"
                ax.step(x, y, where='mid', label=curve_lbl,
                        color=colors[ri], linestyle=ls, linewidth=1.8, alpha=0.85)
                root_histograms[f"h_{pipe_key}_RUN{run}"] = hist
                has_data = True
                mask = (x >= SPEC_XLIM[0]) & (x <= SPEC_XLIM[1])
                if np.any(mask):
                    y_max = max(y_max, np.max(y[mask]))

        if not has_data:
            plt.close(fig)
            print(f"  SKIP {out_name}: no data")
            return

        ax.set_xlabel('PE', fontsize=13, fontweight='bold')
        ax.set_ylabel('Counts', fontsize=13, fontweight='bold')
        ax.set_title(main_title, fontsize=14, fontweight='bold')
        ax.set_xlim(SPEC_XLIM)
        if y_max > 0:
            ax.set_ylim(0, y_max * 1.15)
        ax.grid(alpha=0.3)

        # Legend block 1: OV run colours (only labelled entries)
        run_handles = [plt.Line2D([0], [0], color=colors[ri], linewidth=2,
                                   label=f"OV {OV_MAP[run]}V (RUN{run})")
                       for ri, run in enumerate(run_list)]
        leg1 = ax.legend(handles=run_handles, loc='upper right',
                         frameon=True, fancybox=True, shadow=True,
                         fontsize=8, title='OV run', ncol=1)
        ax.add_artist(leg1)

        # Legend block 2: pipeline linestyles (only if >1 pipeline)
        if len(pipe_specs) > 1:
            pipe_handles = []
            for pi, (pipe_key, _) in enumerate(pipe_specs):
                lbl = _canonical_label(pipe_key)
                pipe_handles.append(plt.Line2D([0], [0], color='black',
                                                linestyle=_LS[pi % len(_LS)],
                                                linewidth=2, label=lbl))
            ax.legend(handles=pipe_handles, loc='upper left',
                      frameon=True, fancybox=True, shadow=True,
                      fontsize=8, title='Pipeline')

        plt.tight_layout()
        out = os.path.join(ov_spectra_dir, out_name)
        save_plot_dual_format(fig, out, root_histograms)
        print(f"  ✓ OV overview spectra: {out_name}")

    def save_combination(combo_pipes, combo_name, combo_title):
        pipes = build_pipes(combo_pipes)
        if len(pipes) < 1:
            print(f"  SKIP {combo_name}: no data available")
            return
        for metric in ('resolution', 'mean', 'sigma'):
            pipe_metric = {lbl: {'x': md[metric]['x'],
                                  'y': md[metric]['y'],
                                  'yerr': md[metric]['yerr']}
                           for lbl, md in pipes.items()
                           if metric in md and md[metric]['x']}
            if not pipe_metric:
                continue
            out = f"{output_dir}/ge68_ov_{combo_name}_{metric}.png"
            title = f"Ge-68 OV Scan \u2014 {combo_title}\n{metric.capitalize()}"
            plot_multiline_scan(pipe_metric, out, title,
                                'Overvoltage (OV) [V]', metric=metric)

        # Per-run spectra in RUN{run}/ subfolders
        hkmap = {k: PIPE_HIST_KEY_MAP.get(k, 'hist_PE') for k in combo_pipes}
        for run in runs:
            run_dir = os.path.join(output_dir, f"RUN{run}")
            os.makedirs(run_dir, exist_ok=True)
            data_for_run = {}
            hko = {}
            for pk in combo_pipes:
                if pk not in all_hist_data or run not in all_hist_data[pk]:
                    continue
                d   = all_hist_data[pk][run]
                lbl = d.get('label', pk)
                hk  = hkmap.get(pk, 'hist_PE')
                if d.get(hk) is not None:
                    data_for_run[lbl] = d
                    hko[lbl] = hk
            if not data_for_run:
                continue
            ov_str = f"OV {OV_MAP.get(run, '?')}V"
            out    = os.path.join(run_dir, f"RUN{run}_{combo_name}_spectra.png")
            title  = f"Ge-68 OV Scan \u2014 {combo_title}\nRUN{run} ({ov_str})"
            plot_superimposed_spectra(data_for_run, out, title, xlim=SPEC_XLIM,
                                      hist_key_override=hko)

    # ── Pipeline combinations ─────────────────────────────────────────────────
    COMBOS = [
        (['rtraw_default', 'rtraw_custom'],
         'rtraw_only',
         'RTRAW (default + custom gain)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_rcut', 'esd_pesum_nocut'],
         'rtraw_esd_pesum',
         'RTRAW (default + custom) + ESD peSum (with & without radial cut)'),

        (['esd_pesum_nocut', 'esd_pesumg_nocut', 'esd_pesum_rcut', 'esd_pesumg_rcut'],
         'esd_all',
         'ESD \u2014 all peSum variants'),

        (['rtraw_custom', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_custom_esd_nocut',
         'RTRAW (custom gain) vs ESD peSum & peSum_g (no radial cut)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_all_esd_nocut',
         'RTRAW (default + custom) vs ESD peSum & peSum_g (no radial cut)'),

        (['rtraw_custom', 'esd_pesum_rcut', 'esd_pesumg_rcut'],
         'rtraw_custom_esd_rcut',
         'RTRAW (custom gain) vs ESD peSum & peSum_g (r<150 mm)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_rcut', 'esd_pesumg_rcut'],
         'rtraw_all_esd_rcut',
         'RTRAW (default + custom) vs ESD peSum & peSum_g (r<150 mm)'),

        # Continuous PE combos
        (['rtraw_default_contin', 'rtraw_custom_contin', 'rtraw_default', 'rtraw_custom'],
         'rtraw_contin_vs_discrete',
         'RTRAW (contin. PE; default + custom gain) + RTRAW (discrete PE; default + custom gain)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_nocut'],
         'rtraw_custom_both_pe_esd_nocut',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (no radial cut)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_rcut'],
         'rtraw_custom_both_pe_esd_rcut',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (with radial cut)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_nocut', 'esd_pesum_rcut'],
         'rtraw_custom_both_pe_esd_both',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (with & without radial cut)'),

        (['rtraw_default_contin', 'rtraw_custom_contin', 'esd_pesum_rcut', 'esd_pesumg_rcut'],
         'rtraw_contin_esd_rcut',
         'RTRAW (contin. PE; default + custom gain) + ESD peSum & peSum_g (r<150mm)'),

        (['rtraw_default_contin', 'rtraw_custom_contin', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_contin_esd_nocut',
         'RTRAW (contin. PE; default + custom gain) + ESD peSum & peSum_g (no radial cut)'),
    ]

    for keys, name, title in COMBOS:
        print(f"\n  Combination: {name}")
        save_combination(keys, name, title)

    # ── OV_spectra/ overview plots: one colour per OV run ────────────────────
    print("\n  Generating OV_spectra/ overview plots...")

    # 1. RTRAW custom only — single pipeline, 7 coloured curves
    _ov_multi_pipe_overview(
        [('rtraw_custom', 'hist_PE')],
        'ge68_ov_rtraw_only_spectra.png',
        'Ge-68 OV Scan \u2014 RTRAW (custom gain): all OV runs\nPE Spectra overview'
    )

    # 2. ESD peSum (basic) — no cut vs r<150mm
    _ov_multi_pipe_overview(
        [('esd_pesum_nocut', 'hist_PE'), ('esd_pesum_rcut', 'hist_PE')],
        'ge68_ov_esd_pesumbasic_spectra.png',
        'Ge-68 OV Scan \u2014 ESD peSum (basic): no cut vs r<150mm\nPE Spectra overview'
    )

    # 3. ESD peSum_g — no cut vs r<150mm
    _ov_multi_pipe_overview(
        [('esd_pesumg_nocut', 'hist_PE'), ('esd_pesumg_rcut', 'hist_PE')],
        'ge68_ov_esd_pesumg_spectra.png',
        'Ge-68 OV Scan \u2014 ESD peSum_g: no cut vs r<150mm\nPE Spectra overview'
    )

    # 4. ESD no radial cut — peSum vs peSum_g
    _ov_multi_pipe_overview(
        [('esd_pesum_nocut', 'hist_PE'), ('esd_pesumg_nocut', 'hist_PE')],
        'ge68_ov_esd_noradial_spectra.png',
        'Ge-68 OV Scan \u2014 ESD (no radial cut): peSum vs peSum_g\nPE Spectra overview'
    )

    # 5. ESD r<150mm — peSum vs peSum_g
    _ov_multi_pipe_overview(
        [('esd_pesum_rcut', 'hist_PE'), ('esd_pesumg_rcut', 'hist_PE')],
        'ge68_ov_esd_rcut150_spectra.png',
        'Ge-68 OV Scan \u2014 ESD (r<150mm): peSum vs peSum_g\nPE Spectra overview'
    )

    # 6. RTRAW custom (discrete PE) vs ESD peSum (no cut)
    _ov_multi_pipe_overview(
        [('rtraw_custom', 'hist_PE'), ('esd_pesum_nocut', 'hist_PE')],
        'ge68_ov_rtraw_esd_pesumbasic_spectra.png',
        'Ge-68 OV Scan \u2014 RTRAW (custom, discrete PE) vs ESD peSum (no cut)\nPE Spectra overview'
    )

    # 7. RTRAW custom (discrete PE) vs ESD peSum_g (no cut)
    _ov_multi_pipe_overview(
        [('rtraw_custom', 'hist_PE'), ('esd_pesumg_nocut', 'hist_PE')],
        'ge68_ov_rtraw_esd_pesumg_spectra.png',
        'Ge-68 OV Scan \u2014 RTRAW (custom, discrete PE) vs ESD peSum_g (no cut)\nPE Spectra overview'
    )

    print("\n\u2713 Ge-68 OV scan comparison complete")

def merge_center_subset(base_dir, run, rtraw_basenames, pipeline_pattern, output_dir, label_suffix="center"):
    """
    Merge specific individual spectrum files into a center-only subset
    
    Args:
        base_dir: base directory
        run: run number
        rtraw_basenames: list of RTRAW file basenames (e.g., ['174', '175', '176'])
        pipeline_pattern: pipeline pattern to search in (e.g., 'rtraw_default')
        output_dir: where to save merged file
        label_suffix: suffix for output label (e.g., 'center')
    
    Returns:
        Path to merged file or None if merge failed
    """
    print(f"\n{'='*80}")
    print(f"MERGING CENTER SUBSET: RUN {run} ({pipeline_pattern})")
    print(f"{'='*80}")
    
    # Find the pipeline directory
    # Note: base_dir from shell scripts already includes /energy_resolution/
    pipeline_dirs = glob.glob(f"{base_dir}/RUN{run}/{run}_{pipeline_pattern}*")
    
    if not pipeline_dirs:
        print(f"ERROR: No pipeline directory found for pattern: {pipeline_pattern}")
        return None
    
    # Use most recent directory
    pipeline_dir = sorted(pipeline_dirs, reverse=True)[0]
    print(f"Pipeline directory: {os.path.basename(pipeline_dir)}")
    
    # Find spectrum files corresponding to these RTRAW files
    # Pattern: spectrum_RUN{run}-{filenum}.root where filenum matches RTRAW basenames
    
    spectrum_files = []
    
    for basename in rtraw_basenames:
        # Look for individual spectrum file with this number
        # Pattern: spectrum_RUN1112-174.root
        pattern = f"{pipeline_dir}/spectrum_RUN{run}-{basename}.root"
        files = glob.glob(pattern)
        
        if files:
            spectrum_files.append(files[0])
            print(f"  ✓ Found: {os.path.basename(files[0])}")
        else:
            print(f"  ✗ NOT FOUND: spectrum_RUN{run}-{basename}.root")
    
    if not spectrum_files:
        print(f"ERROR: No spectrum files found for RTRAW basenames: {rtraw_basenames}")
        return None
    
    if len(spectrum_files) != len(rtraw_basenames):
        print(f"WARNING: Found {len(spectrum_files)}/{len(rtraw_basenames)} files")
    
    print(f"\nTotal files to merge: {len(spectrum_files)}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Output merged file
    merged_file = f"{output_dir}/spectrum_RUN{run}-{label_suffix}.root"
    
    # Create temporary directory with files
    temp_dir = tempfile.mkdtemp()
    
    # Copy files to temp directory with simple pattern
    for i, src in enumerate(spectrum_files):
        dest = f"{temp_dir}/spectrum_{i:03d}.root"
        shutil.copy2(src, dest)
    
    # Merge using the pattern
    pattern = f"{temp_dir}/spectrum_*.root"
    
    print(f"\nMerging {len(spectrum_files)} files...")
    print(f"Output: {merged_file}")
    
    # Find merge_spectrum.py
    merge_script = None
    search_paths = [
        os.path.join(os.path.dirname(__file__), 'merge_spectrum.py'),
        os.path.join(os.path.dirname(base_dir), 'merge_spectrum.py'),
        os.path.join(base_dir, '..', 'merge_spectrum.py'),
        'merge_spectrum.py'  # Current directory
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            merge_script = path
            break
    
    if not merge_script:
        print(f"ERROR: merge_spectrum.py not found in search paths")
        print(f"Searched: {search_paths}")
        shutil.rmtree(temp_dir)
        return None
    
    print(f"Using merge script: {merge_script}")
    
    cmd = ['python', merge_script, pattern, merged_file]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        print(f"\n✓ Center subset merged successfully: {merged_file}")
        return merged_file
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Merge failed")
        print(e.stderr)
        shutil.rmtree(temp_dir)
        return None


def compare_ge68_specific_runs(base_dir, output_dir):
    """
    Compare Ge-68 specific runs: 1157, 1236, 1295, 1296, 1319.
    x-axis = run position index. Produces resolution/mean/sigma + PE spectra
    for all pipeline combinations (original 10 + 6 new contin PE combos).
    """
    print("\n" + "="*80)
    print("COMPARING Ge-68: RUNS 1157, 1236, 1295, 1296, 1319")
    print("="*80)

    runs       = [1157, 1236, 1295, 1296, 1319]
    x_pos      = list(range(len(runs)))
    run_labels = [f"RUN{r}" for r in runs]
    SPEC_XLIM  = (2000, 7000)

    os.makedirs(output_dir, exist_ok=True)

    SPEC_PATTERNS = {
        'rtraw_default':          'rtraw_default',
        'rtraw_custom':           'rtraw_run{run}',
        'rtraw_default_contin':   'rtraw_default',       # contin PE variant
        'rtraw_custom_contin':    'rtraw_run{run}',      # contin PE variant
        'esd_pesum_nocut':        'esd_noradialcut_pesumbasic',
        'esd_pesumg_nocut':       'esd_noradialcut_pesumg',
        'esd_pesum_rcut':         'esd_rcut150_pesumbasic',
        'esd_pesumg_rcut':        'esd_rcut150_pesumg',
    }

    # Load all data
    all_pipe_data = {}
    all_hist_data  = {}  # {pipe_key: {run: data_dict}}

    for pipe_key, pattern_tmpl in SPEC_PATTERNS.items():
        use_contin  = pipe_key in CONTIN_PIPE_KEYS
        keys_to_use = METRIC_KEYS_CONTIN if use_contin else METRIC_KEYS

        for metric, mkeys in keys_to_use.items():
            ys, es = [], []
            label  = None
            for run in runs:
                actual = pattern_tmpl.replace('{run}', str(run))
                files  = find_spectrum_files(base_dir, run, actual)
                if not files:
                    ys.append(-1); es.append(0); continue
                data = extract_spectrum_info(files[0])
                if data is None:
                    ys.append(-1); es.append(0); continue

                # Cache histogram data
                if pipe_key not in all_hist_data:
                    all_hist_data[pipe_key] = {}
                if run not in all_hist_data[pipe_key]:
                    all_hist_data[pipe_key][run] = data

                v = data.get(mkeys[0], -1)
                e = data.get(mkeys[1], 0)
                ys.append(v if v > 0 else -1)
                es.append(e)
                if label is None:
                    base_lbl = data.get('label', pipe_key)
                    label = (base_lbl.replace('RTRAW (', 'RTRAW (PEcontin, ')
                             if use_contin else base_lbl)

            if label is None:
                continue
            if pipe_key not in all_pipe_data:
                all_pipe_data[pipe_key] = {'label': label, 'metrics': {}}
            all_pipe_data[pipe_key]['metrics'][metric] = {
                'x': x_pos, 'y': ys, 'yerr': es
            }

    run_label_map = {run: f"RUN{run}" for run in runs}

    def build_for_metric(keys, metric):
        d = {}
        for k in keys:
            if k in all_pipe_data and metric in all_pipe_data[k]['metrics']:
                lbl = all_pipe_data[k]['label']
                md  = all_pipe_data[k]['metrics'][metric]
                d[lbl] = {'x': md['x'], 'y': md['y'], 'yerr': md['yerr']}
        return d

    def save_combo(keys, name, desc):
        for metric in ('resolution', 'mean', 'sigma'):
            pipes = build_for_metric(keys, metric)
            if not pipes:
                return
            out   = f"{output_dir}/ge68_specific_{name}_{metric}.png"
            title = f"Ge-68 Specific Runs \u2014 {desc}\n{metric.capitalize()}"
            plot_multiline_scan(pipes, out, title,
                                'Run', metric=metric,
                                x_ticklabels=run_labels)

        # Spectra plot for this combo
        hkmap = {k: PIPE_HIST_KEY_MAP.get(k, 'hist_PE') for k in keys}
        out_s = f"{output_dir}/ge68_specific_{name}_spectra.png"
        title_s = f"Ge-68 Specific Runs \u2014 {desc}\nPE Spectra"
        plot_multi_run_spectra(all_hist_data, keys, out_s, title_s,
                               SPEC_XLIM, run_label_map, hist_key_map=hkmap)

    COMBOS = [
        # Original combos
        (['rtraw_default', 'rtraw_custom'],
         'rtraw_only',
         'RTRAW (default + custom gain)'),

        (['esd_pesum_nocut', 'esd_pesumg_nocut'],
         'esd_nocut',
         'ESD peSum & peSum_g (no radial cut)'),

        (['esd_pesum_rcut', 'esd_pesumg_rcut'],
         'esd_rcut',
         'ESD peSum & peSum_g (r<150 mm)'),

        (['rtraw_custom', 'esd_pesum_nocut'],
         'rtraw_custom_vs_pesum_nocut',
         'RTRAW custom vs ESD peSum (no radial cut)'),

        (['rtraw_custom', 'esd_pesum_rcut'],
         'rtraw_custom_vs_pesum_rcut',
         'RTRAW custom vs ESD peSum (r<150 mm)'),

        (['rtraw_custom', 'esd_pesumg_nocut'],
         'rtraw_custom_vs_pesumg_nocut',
         'RTRAW custom vs ESD peSum_g (no radial cut)'),

        (['rtraw_custom', 'esd_pesumg_rcut'],
         'rtraw_custom_vs_pesumg_rcut',
         'RTRAW custom vs ESD peSum_g (r<150 mm)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_rcut', 'esd_pesum_nocut'],
         'rtraw_all_pesum_both',
         'RTRAW (default+custom) + ESD peSum (with & without radial cut)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesumg_rcut', 'esd_pesumg_nocut'],
         'rtraw_all_pesumg_both',
         'RTRAW (default+custom) + ESD peSum_g (with & without radial cut)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_rcut', 'esd_pesumg_rcut'],
         'rtraw_all_esd_rcut',
         'RTRAW (default+custom) + ESD peSum & peSum_g (r<150 mm)'),

        # New 6 combos with continuous PE
        (['rtraw_default_contin', 'rtraw_custom_contin', 'rtraw_default', 'rtraw_custom'],
         'rtraw_contin_vs_discrete',
         'RTRAW (contin. PE; default + custom gain) + RTRAW (discrete PE; default + custom gain)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_nocut'],
         'rtraw_custom_both_pe_esd_nocut',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (no radial cut)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_rcut'],
         'rtraw_custom_both_pe_esd_rcut',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (with radial cut)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_nocut', 'esd_pesum_rcut'],
         'rtraw_custom_both_pe_esd_both',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (with & without radial cut)'),

        (['rtraw_default_contin', 'rtraw_custom_contin', 'esd_pesum_rcut', 'esd_pesumg_rcut'],
         'rtraw_contin_esd_rcut',
         'RTRAW (contin. PE; default + custom gain) + ESD peSum & peSum_g (r<150mm)'),

        (['rtraw_default_contin', 'rtraw_custom_contin', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_contin_esd_nocut',
         'RTRAW (contin. PE; default + custom gain) + ESD peSum & peSum_g (no radial cut)'),
    ]

    for keys, name, desc in COMBOS:
        print(f"\n  Combo: {name}")
        save_combo(keys, name, desc)

    print("\n\u2713 Ge-68 specific runs comparison complete")



def compare_cs137_pipelines(base_dir, output_dir,
                             pos60_files_1112=None, pos60_files_1344=None):
    """
    Cs-137 CLS multi-sample comparison.

    x-axis (4 samples in order):
      0  RUN1112  full CLS spectrum
      1  RUN1112  CLS position 60  (3 RTRAW timestamped files merged)
      2  RUN1344  full CLS spectrum
      3  RUN1344  CLS position 60  (3 RTRAW timestamped files merged)

    8 pipeline combinations x 3 metrics (resolution / mean / sigma).

    Non-origin radial cut (around CLS source position):
    ─────────────────────────────────────────────────────────────────────────
    The ESD radial cut in get_spectrum.py currently computes r = sqrt(x²+y²+z²).
    For Cs-137 CLS the source sits at (-23.1093, -188.278, 37.3801) mm, not at
    the detector origin.  In CCRec.cc the reconstructed position is available
    through rec_evt->x(), rec_evt->y(), rec_evt->z() (CdRecEvt). A cut around
    the actual source position can be implemented by replacing

        double r = sqrt(x*x + y*y + z*z);

    with

        const double SRC_X = -23.1093, SRC_Y = -188.278, SRC_Z = 37.3801; // mm
        double dx = x - SRC_X, dy = y - SRC_Y, dz = z - SRC_Z;
        double r  = sqrt(dx*dx + dy*dy + dz*dz);

    in the execute() method, before the if (r > m_radialCut) continue; guard.
    The same arithmetic applies identically in get_spectrum.py's ESD loop.

    Args:
        base_dir:           base directory containing RUN folders
        output_dir:         where to save plots
        pos60_files_1112:   list of RTRAW file basenames for CLS pos-60 in RUN1112
                            e.g. ['174', '175', '176']   ← fill in actual values
        pos60_files_1344:   list of RTRAW file basenames for CLS pos-60 in RUN1344
                            e.g. ['098', '099', '100']   ← fill in actual values
    """
    print("\n" + "="*80)
    print("Cs-137 CLS PIPELINE COMPARISON (RUN1112 + RUN1344, full + pos-60)")
    print("="*80)

    os.makedirs(output_dir, exist_ok=True)

    # ── CLS pipeline patterns ─────────────────────────────────────────────────
    # NOTE: For Cs-137 (RUN 1112 / 1344) the ESD radial cut is always the
    # OFF-AXIS cut centred on the CLS source position (-23.1, -188.3, 37.4) mm,
    # produced by launch_get_spectrum.sh with the 'offaxis' flag.
    # These folders are named  …_esd_offsrc_rcut150_pesumbasic/pesumg_…
    # The on-axis rcut150 folders are NOT used for Cs-137.
    CLS_PATTERNS = {
        'rtraw_default':           'rtraw_default',
        'rtraw_custom':            'rtraw_run{run}',
        'rtraw_default_contin':    'rtraw_default',       # same files, contin PE
        'rtraw_custom_contin':     'rtraw_run{run}',      # same files, contin PE
        'esd_pesum_nocut':         'esd_noradialcut_pesumbasic',
        'esd_pesumg_nocut':        'esd_noradialcut_pesumg',
        # Off-axis radial cut (source at CLS position, not detector origin)
        'esd_pesum_offsrc_rcut':   'esd_offsrc_rcut150_pesumbasic',
        'esd_pesumg_offsrc_rcut':  'esd_offsrc_rcut150_pesumg',
    }

    # ── x-axis sample definitions ─────────────────────────────────────────────
    # Each sample: (run, sample_key, label, pos60_files_or_None)
    SAMPLES = [
        (1112, 'full',  'RUN1112 full CLS',   None),
        (1344, 'full',  'RUN1344 full CLS',   None),
        (1112, 'pos60', 'RUN1112 pos-60',     pos60_files_1112),
        (1344, 'pos60', 'RUN1344 pos-60',     pos60_files_1344),
    ]
    x_pos       = list(range(len(SAMPLES)))
    x_ticklabels = [s[2] for s in SAMPLES]

    # ── Merge pos-60 subsets (RTRAW + ESD) ───────────────────────────────────
    # Results cached in output_dir/cls_pos60/
    pos60_dir = os.path.join(output_dir, 'cls_pos60_merged')
    os.makedirs(pos60_dir, exist_ok=True)

    def _ensure_pos60_merged(run, basenames):
        """Merge the 3 pos-60 files for all pipelines of `run`."""
        if basenames is None:
            print(f"  WARNING: pos60_files for RUN{run} not configured; skipping pos-60 sample")
            return

        print(f"\n  Merging pos-60 subset for RUN{run} ({basenames})...")

        # RTRAW pipelines
        for pat in ['rtraw_default', f'rtraw_run{run}']:
            merge_center_subset(base_dir, run, basenames, pat,
                                pos60_dir, label_suffix=f"pos60_run{run}_{pat}")

        # ESD pipelines — includes on-axis and off-axis (Cs-137) radial-cut variants
        esd_pats = [
            'esd_noradialcut_pesumbasic',    'esd_noradialcut_pesumg',
            'esd_rcut150_pesumbasic',        'esd_rcut150_pesumg',
            'esd_offsrc_rcut150_pesumbasic', 'esd_offsrc_rcut150_pesumg',
        ]
        for pat in esd_pats:
            pipeline_dirs = glob.glob(f"{base_dir}/RUN{run}/{run}_{pat}*")
            if not pipeline_dirs:
                continue
            pipeline_dir = sorted(pipeline_dirs, reverse=True)[0]
            spec_files = []
            for bn in basenames:
                f = glob.glob(f"{pipeline_dir}/spectrum_RUN{run}-{bn}.root")
                if f:
                    spec_files.append(f[0])
            if len(spec_files) != len(basenames):
                print(f"    WARNING: only {len(spec_files)}/{len(basenames)} files for {pat}")
                continue

            merged = f"{pos60_dir}/spectrum_RUN{run}-pos60_{pat}.root"
            if os.path.exists(merged):
                print(f"    already exists: {os.path.basename(merged)}")
                continue

            import tempfile, shutil, subprocess
            td = tempfile.mkdtemp()
            for i, src in enumerate(spec_files):
                shutil.copy2(src, f"{td}/spectrum_{i:03d}.root")
            merge_script = next(
                (p for p in [
                    os.path.join(os.path.dirname(__file__), 'merge_spectrum.py'),
                    os.path.join(base_dir, '..', 'merge_spectrum.py'),
                    'merge_spectrum.py',
                ] if os.path.exists(p)), None)
            if not merge_script:
                print(f"    ERROR: merge_spectrum.py not found"); shutil.rmtree(td); continue
            try:
                subprocess.run(['python', merge_script, f"{td}/spectrum_*.root", merged],
                               check=True, capture_output=True, text=True)
                print(f"    merged: {os.path.basename(merged)}")
            except subprocess.CalledProcessError as ex:
                print(f"    ERROR merging {pat}: {ex.stderr[:200]}")
            finally:
                shutil.rmtree(td)

    _ensure_pos60_merged(1112, pos60_files_1112)
    _ensure_pos60_merged(1344, pos60_files_1344)

    # ── PNG spectra for all merged pos-60 ROOT files ──────────────────────────
    # Mapping from the pattern suffix in the filename to a canonical label.
    # This avoids "Unknown Pipeline" caused by extract_pipeline_info not being
    # able to parse paths inside cls_pos60_merged/.
    _POS60_FNAME_LABEL = {
        'rtraw_default':                'RTRAW (default calib)',
        f'rtraw_run{1112}':             f'RTRAW (RUN1112 calib)',
        f'rtraw_run{1344}':             f'RTRAW (RUN1344 calib)',
        'esd_noradialcut_pesumbasic':   'ESD (peSum, no cut)',
        'esd_noradialcut_pesumg':       'ESD (peSum_g, no cut)',
        'esd_rcut150_pesumbasic':       'ESD (peSum, r<150mm)',
        'esd_rcut150_pesumg':           'ESD (peSum_g, r<150mm)',
        'esd_offsrc_rcut150_pesumbasic':'ESD (peSum, r<150mm off-axis)',
        'esd_offsrc_rcut150_pesumg':    'ESD (peSum_g, r<150mm off-axis)',
    }

    def _label_from_pos60_file(fpath, run):
        """Derive a canonical label from the merged pos-60 filename."""
        base   = os.path.basename(fpath)
        # Remove prefix: spectrum_RUN{run}-pos60_
        suffix = base.replace(f'spectrum_RUN{run}-pos60_', '').replace('.root', '')
        return _POS60_FNAME_LABEL.get(suffix, suffix)

    def _save_pos60_spectra():
        """Produce cls_pos60_merged/RUN{run}_pos60_spectra.png for each run."""
        merged_files = sorted(glob.glob(f"{pos60_dir}/spectrum_RUN*.root"))
        if not merged_files:
            print("  No merged pos-60 ROOT files — skipping pos60 spectra PNGs")
            return
        by_run = {}
        for fp in merged_files:
            m = re.search(r'spectrum_RUN(\d+)-', os.path.basename(fp))
            if m:
                by_run.setdefault(int(m.group(1)), []).append(fp)

        for run, files in sorted(by_run.items()):
            data_dict = {}
            hko       = {}
            for fp in sorted(files):
                d = extract_spectrum_info(fp)
                if d is None:
                    continue
                # Override label using filename-based mapping
                lbl = _label_from_pos60_file(fp, run)
                # Ensure unique key
                base_lbl, n = lbl, 0
                while lbl in data_dict:
                    n  += 1
                    lbl = f"{base_lbl} #{n}"
                d['label'] = lbl  # also fix the stored label
                hk = 'hist_PEcontin' if (d.get('hist_PE') is None and
                                          d.get('hist_PEcontin') is not None) else 'hist_PE'
                data_dict[lbl] = d
                hko[lbl]       = hk
            if not data_dict:
                continue
            out   = os.path.join(pos60_dir, f"RUN{run}_pos60_spectra.png")
            title = f"Cs-137 CLS pos-60 \u2014 RUN{run}: all pipelines\nMerged PE Spectra"
            plot_superimposed_spectra(data_dict, out, title,
                                      xlim=(1000, 7000), hist_key_override=hko)
            print(f"  ✓ pos-60 spectra PNG: {os.path.basename(out)}")

    _save_pos60_spectra()

    # ── Data loading: for every pipe_key × metric × sample → (value, error) ──
    # Structure: all_pipe_data[pipe_key][metric] = {'x':[], 'y':[], 'yerr':[]}

    all_pipe_data = {}
    all_hist_data  = {}  # {pipe_key: {(run, sample_key): data_dict}}

    def _load_full(run, pipe_key, pattern_tmpl):
        pat   = pattern_tmpl.replace('{run}', str(run))
        files = find_spectrum_files(base_dir, run, pat)
        if not files:
            return None
        return extract_spectrum_info(files[0])

    def _load_pos60(run, pipe_key, pattern_tmpl):
        pat      = pattern_tmpl.replace('{run}', str(run))
        explicit = f"{pos60_dir}/spectrum_RUN{run}-pos60_{pat}.root"
        if os.path.exists(explicit):
            data = extract_spectrum_info(explicit)
        else:
            # Fallback: search for any file matching the pattern
            fallback = glob.glob(f"{pos60_dir}/spectrum_RUN{run}-*{pat}*.root")
            if fallback:
                data = extract_spectrum_info(sorted(fallback)[0])
            else:
                return None
        if data is None:
            return None
        # Fix "Unknown Pipeline" label: merged files live outside the normal
        # directory tree, so extract_pipeline_info cannot parse them.
        if data.get('label', 'Unknown Pipeline') in ('Unknown Pipeline', ''):
            data['label'] = _canonical_label(pipe_key, run=run)
        return data

    for pipe_key, pattern_tmpl in CLS_PATTERNS.items():
        use_contin  = pipe_key in CONTIN_PIPE_KEYS
        keys_to_use = METRIC_KEYS_CONTIN if use_contin else METRIC_KEYS

        for metric, mkeys in keys_to_use.items():
            ys, es = [], []
            label  = None

            for run, sample_key, sample_label, pos60_files in SAMPLES:
                if sample_key == 'full':
                    data = _load_full(run, pipe_key, pattern_tmpl)
                else:
                    data = _load_pos60(run, pipe_key, pattern_tmpl)

                if data is None:
                    ys.append(-1); es.append(0); continue

                # Ensure the label is always the canonical one (never "Unknown Pipeline")
                if data.get('label', 'Unknown Pipeline') in ('Unknown Pipeline', ''):
                    data['label'] = _canonical_label(pipe_key, run=run)

                # Cache histogram data (once per pipe_key × run × sample_key)
                hcache_key = (run, sample_key)
                if pipe_key not in all_hist_data:
                    all_hist_data[pipe_key] = {}
                if hcache_key not in all_hist_data[pipe_key]:
                    all_hist_data[pipe_key][hcache_key] = data

                v = data.get(mkeys[0], -1)
                e = data.get(mkeys[1], 0)
                ys.append(v if v > 0 else -1)
                es.append(e)
                if label is None:
                    base_lbl = data.get('label', _canonical_label(pipe_key, run=run))
                    label = (base_lbl.replace('RTRAW (', 'RTRAW (PEcontin, ')
                             if use_contin else base_lbl)

            if label is None:
                continue
            if pipe_key not in all_pipe_data:
                all_pipe_data[pipe_key] = {'label': label, 'metrics': {}}
            all_pipe_data[pipe_key]['metrics'][metric] = {
                'x': x_pos, 'y': ys, 'yerr': es
            }

    # sample label map for spectra plots: key = (run, sample_key)
    cs_sample_label_map = {(run, sk): sl for run, sk, sl, _ in SAMPLES}

    # ── Helper ────────────────────────────────────────────────────────────────
    def build_for_metric(keys, metric):
        d = {}
        for k in keys:
            if k in all_pipe_data and metric in all_pipe_data[k]['metrics']:
                lbl = all_pipe_data[k]['label']
                md  = all_pipe_data[k]['metrics'][metric]
                d[lbl] = {'x': md['x'], 'y': md['y'], 'yerr': md['yerr']}
        return d

    def save_combo(keys, name, desc):
        for metric in ('resolution', 'mean', 'sigma'):
            pipes = build_for_metric(keys, metric)
            if not pipes:
                return
            out   = f"{output_dir}/cs137_{name}_{metric}.png"
            title = f"Cs-137 CLS \u2014 {desc}\n{metric.capitalize()}"
            plot_multiline_scan(pipes, out, title,
                                'Sample', metric=metric,
                                x_ticklabels=x_ticklabels)

        # Per-sample spectra in RUN{run}_{sample_key}/ subfolders
        hkmap = {k: PIPE_HIST_KEY_MAP.get(k, 'hist_PE') for k in keys}
        for run, sample_key, sample_label, _ in SAMPLES:
            cache_key  = (run, sample_key)
            folder_key = f"RUN{run}_{sample_key}"
            sample_dir = os.path.join(output_dir, folder_key)
            os.makedirs(sample_dir, exist_ok=True)
            data_for_sample = {}
            hko = {}
            for pk in keys:
                if pk not in all_hist_data or cache_key not in all_hist_data[pk]:
                    continue
                d   = all_hist_data[pk][cache_key]
                lbl = d.get('label', _canonical_label(pk, run=run))
                hk  = hkmap.get(pk, 'hist_PE')
                if d.get(hk) is not None:
                    data_for_sample[lbl] = d
                    hko[lbl] = hk
            if not data_for_sample:
                continue
            out_s   = os.path.join(sample_dir, f"{folder_key}_{name}_spectra.png")
            title_s = f"Cs-137 CLS \u2014 {desc}\n{sample_label}"
            plot_superimposed_spectra(data_for_sample, out_s, title_s,
                                      xlim=(1000, 7000), hist_key_override=hko)

    # ── Pipeline combinations ─────────────────────────────────────────────────
    COMBOS = [
        # Original 8  (rcut now means off-axis for Cs-137)
        (['rtraw_default', 'rtraw_custom'],
         'rtraw_only',
         'RTRAW (default + custom gain)'),

        (['rtraw_custom', 'esd_pesum_nocut'],
         'rtraw_custom_pesum_nocut',
         'RTRAW custom + ESD peSum (no radial cut)'),

        (['rtraw_custom', 'esd_pesum_offsrc_rcut', 'esd_pesum_nocut'],
         'rtraw_custom_pesum_both',
         'RTRAW custom + ESD peSum (off-axis r<150mm + no radial cut)'),

        (['esd_pesum_nocut', 'esd_pesumg_nocut', 'esd_pesum_offsrc_rcut', 'esd_pesumg_offsrc_rcut'],
         'esd_all',
         'ESD peSum & peSum_g (no radial cut) + ESD peSum & peSum_g (off-axis r<150mm)'),

        (['rtraw_custom', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_custom_esd_nocut',
         'RTRAW custom vs ESD peSum & peSum_g (no radial cut)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_all_esd_nocut',
         'RTRAW (default+custom) vs ESD peSum & peSum_g (no radial cut)'),

        (['rtraw_custom', 'esd_pesum_offsrc_rcut', 'esd_pesumg_offsrc_rcut'],
         'rtraw_custom_esd_rcut',
         'RTRAW custom vs ESD peSum & peSum_g (off-axis r<150mm)'),

        (['rtraw_default', 'rtraw_custom', 'esd_pesum_offsrc_rcut', 'esd_pesumg_offsrc_rcut'],
         'rtraw_all_esd_rcut',
         'RTRAW (default+custom) vs ESD peSum & peSum_g (off-axis r<150mm)'),

        # New 6 combos with continuous PE
        (['rtraw_default_contin', 'rtraw_custom_contin', 'rtraw_default', 'rtraw_custom'],
         'rtraw_contin_vs_discrete',
         'RTRAW (contin. PE; default + custom gain) + RTRAW (discrete PE; default + custom gain)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_nocut'],
         'rtraw_custom_both_pe_esd_nocut',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (no radial cut)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_offsrc_rcut'],
         'rtraw_custom_both_pe_esd_rcut',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (off-axis r<150mm)'),

        (['rtraw_custom_contin', 'rtraw_custom', 'esd_pesum_nocut', 'esd_pesum_offsrc_rcut'],
         'rtraw_custom_both_pe_esd_both',
         'RTRAW (contin.+discrete PE; custom gain) + ESD peSum (no cut + off-axis r<150mm)'),

        (['rtraw_default_contin', 'rtraw_custom_contin', 'esd_pesum_offsrc_rcut', 'esd_pesumg_offsrc_rcut'],
         'rtraw_contin_esd_rcut',
         'RTRAW (contin. PE; default + custom gain) + ESD peSum & peSum_g (off-axis r<150mm)'),

        (['rtraw_default_contin', 'rtraw_custom_contin', 'esd_pesum_nocut', 'esd_pesumg_nocut'],
         'rtraw_contin_esd_nocut',
         'RTRAW (contin. PE; default + custom gain) + ESD peSum & peSum_g (no radial cut)'),
    ]

    for keys, name, desc in COMBOS:
        print(f"\n  Combo: {name}")
        save_combo(keys, name, desc)

    print("\n\u2713 Cs-137 CLS pipeline comparison complete")


def main():

    parser = argparse.ArgumentParser(
        description="Compare run groups for Cs-137 and Ge-68 analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comparison modes:
  --cs137         Cs-137 CLS: RUN1112 + RUN1344, full + pos-60 (14 combinations)
  --ov-scan       Ge-68 OV scan runs 1253-1263 (13 combinations)
  --ge68-specific Ge-68 specific runs 1157, 1236, 1295, 1296, 1319 (16 combinations)
  --all           Run all comparisons

Optional for Cs-137 pos-60 subsets:
  --pos60-1112 f1 f2 f3    RTRAW file basenames for CLS pos-60 in RUN1112
  --pos60-1344 f1 f2 f3    RTRAW file basenames for CLS pos-60 in RUN1344

Examples:
  python compare_run_groups.py --cs137 --base-dir /path/to/spectra --output-dir ./output \
      --pos60-1112 174 175 176 --pos60-1344 098 099 100

  python compare_run_groups.py --ov-scan --base-dir /path/to/spectra --output-dir ./output

  python compare_run_groups.py --all --base-dir /path/to/spectra --output-dir ./output \
      --pos60-1112 174 175 176 --pos60-1344 098 099 100
"""
    )

    parser.add_argument('--base-dir',    required=True,
                        help='Base directory containing RUN folders')
    parser.add_argument('--output-dir',  required=True,
                        help='Output directory for plots')
    parser.add_argument('--cs137',       action='store_true',
                        help='Cs-137 CLS pipeline comparison (RUN1112 + RUN1344)')
    parser.add_argument('--ov-scan',     action='store_true',
                        help='Ge-68 OV scan (runs 1253-1263)')
    parser.add_argument('--ge68-specific', action='store_true',
                        help='Ge-68 specific runs 1157, 1236, 1295, 1296, 1319')
    parser.add_argument('--all',         action='store_true',
                        help='Run all comparisons')

    # Cs-137 pos-60 file lists (3 basenames each)
    parser.add_argument('--pos60-1112',  nargs=3, metavar='FILE',
                        default=None,
                        help='3 RTRAW file basenames for CLS pos-60 in RUN1112')
    parser.add_argument('--pos60-1344',  nargs=3, metavar='FILE',
                        default=None,
                        help='3 RTRAW file basenames for CLS pos-60 in RUN1344')

    args = parser.parse_args()

    if not any([args.cs137, args.ov_scan, args.ge68_specific, args.all]):
        parser.error("At least one comparison mode must be specified")

    # ── Cs-137 CLS ────────────────────────────────────────────────────────────
    if args.cs137 or args.all:
        compare_cs137_pipelines(
            args.base_dir,
            os.path.join(args.output_dir, 'cs137_pipelines'),
            pos60_files_1112 = args.pos60_1112,
            pos60_files_1344 = args.pos60_1344,
        )

    # ── Ge-68 OV scan ─────────────────────────────────────────────────────────
    if args.ov_scan or args.all:
        compare_ge68_ov_scan(args.base_dir,
                             os.path.join(args.output_dir, 'ge68_ov_scan'))

    # ── Ge-68 specific runs ───────────────────────────────────────────────────
    if args.ge68_specific or args.all:
        compare_ge68_specific_runs(args.base_dir,
                                   os.path.join(args.output_dir, 'ge68_specific'))

    print("\n" + "="*80)
    print("ALL COMPARISONS COMPLETE")
    print(f"Output directory: {args.output_dir}")
    print("="*80)


if __name__ == '__main__':
    main()
