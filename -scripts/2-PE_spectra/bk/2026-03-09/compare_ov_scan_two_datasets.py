#!/usr/bin/env python3
"""
compare_ov_scan_two_datasets.py

Compare RTRAW custom-gain energy resolution (and peak mean / sigma)
vs overvoltage for two Ge-68 OV-scan datasets:

  Dataset A  (runs 1253-1263, newer)
    RUN1253 → OV 2.5 V
    RUN1257 → OV 3.0 V
    RUN1259 → OV 3.5 V
    RUN1260 → OV 4.0 V
    RUN1261 → OV 4.5 V
    RUN1262 → OV 5.0 V
    RUN1263 → OV 5.5 V

  Dataset B  (runs 1053-1058, older, center position)
    RUN1055 → OV 2.5 V
    RUN1054 → OV 3.0 V
    RUN1053 → OV 3.5 V
    RUN1056 → OV 4.0 V
    RUN1057 → OV 4.5 V
    RUN1058 → OV 5.0 V

For each of the three metrics (resolution / mean / sigma) one figure is produced
containing four data series:
  ● Dataset A  – continuous PE   (hist_PEcontin, keys *_pecontin)
  ○ Dataset A  – discrete PE     (hist_PE,       keys *_pe)
  ■ Dataset B  – continuous PE
  □ Dataset B  – discrete PE

Usage:
  python compare_ov_scan_two_datasets.py \\
      --base-dir  /path/to/energy_resolution \\
      --output-dir ./output_ov_comparison
"""

import ROOT
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import argparse
import os
import glob

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams.update({
    'figure.figsize': (11, 7),
    'font.size': 11,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'legend.fontsize': 10,
})

# ---------------------------------------------------------------------------
# Dataset definitions
# ---------------------------------------------------------------------------

# Dataset A: newer OV scan (runs 1253-1263)
DATASET_A = {
    'label': 'Dataset A (RUN 1253-1263)',
    'runs':  [1253, 1257, 1259, 1260, 1261, 1262, 1263],
    'ov_map': {
        1253: 2.5,
        1257: 3.0,
        1259: 3.5,
        1260: 4.0,
        1261: 4.5,
        1262: 5.0,
        1263: 5.5,
    },
}

# Dataset B: older OV scan (runs 1053-1058, Ge-68 at center)
DATASET_B = {
    'label': 'Dataset B (RUN 1053-1058)',
    'runs':  [1055, 1054, 1053, 1056, 1057, 1058],
    'ov_map': {
        1055: 2.5,
        1054: 3.0,
        1053: 3.5,
        1056: 4.0,
        1057: 4.5,
        1058: 5.0,
    },
}

# ---------------------------------------------------------------------------
# Visual style for the four series
# ---------------------------------------------------------------------------
# (color, marker, linestyle, label suffix)
SERIES_STYLES = {
    ('A', 'contin'):  dict(color='#1f77b4', marker='o', ls='-',  label='Continuous PE'),
    ('A', 'discrete'): dict(color='#1f77b4', marker='s', ls='--', label='Discrete PE'),
    ('B', 'contin'):  dict(color='#d62728', marker='o', ls='-',  label='Continuous PE'),
    ('B', 'discrete'): dict(color='#d62728', marker='s', ls='--', label='Discrete PE'),
}

# ---------------------------------------------------------------------------
# Metric metadata
# ---------------------------------------------------------------------------
METRICS = {
    'resolution': {
        'val_key': 'resolution_pecontin',   # overridden per PE type below
        'err_key': 'resolution_pecontin_err',
        'val_key_disc': 'resolution_pe',
        'err_key_disc': 'resolution_pe_err',
        'ylabel': 'Energy Resolution  σ / (μ − DN)  [%]',
        'title':  'Energy Resolution vs OV — RTRAW Custom Gain',
        'fmt':    '.3f',
        'unit':   '%',
    },
    'mean': {
        'val_key': 'mean_pecontin',
        'err_key': 'mean_pecontin_err',
        'val_key_disc': 'mean_pe',
        'err_key_disc': 'mean_pe_err',
        'ylabel': 'Peak Mean  (μ − DN)  [PE]',
        'title':  'Peak Mean vs OV — RTRAW Custom Gain',
        'fmt':    '.1f',
        'unit':   'PE',
    },
    'sigma': {
        'val_key': 'sigma_pecontin',
        'err_key': 'sigma_pecontin_err',
        'val_key_disc': 'sigma_pe',
        'err_key_disc': 'sigma_pe_err',
        'ylabel': 'Peak Sigma  (σ)  [PE]',
        'title':  'Peak Sigma vs OV — RTRAW Custom Gain',
        'fmt':    '.1f',
        'unit':   'PE',
    },
}

# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_rtraw_custom_file(base_dir, run):
    """
    Return the most-recent spectrum_RUN{run}-MERGED.root file produced by the
    RTRAW custom-gain pipeline (folder pattern: {run}_rtraw_run{run}*).
    Returns None if not found.
    """
    pattern = f"{base_dir}/RUN{run}/{run}_rtraw_run{run}*/spectrum_RUN{run}-MERGED.root"
    files = sorted(glob.glob(pattern), reverse=True)   # most recent first
    if not files:
        print(f"  [WARN] No RTRAW-custom file found for RUN{run}  (pattern: {pattern})")
        return None
    print(f"  [OK]  RUN{run}: {os.path.relpath(files[0], base_dir)}")
    return files[0]

# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def extract_metrics(rootfile):
    """
    Open a spectrum ROOT file and return a dict with all scalar metrics
    (resolution, mean, sigma for both continuous and discrete PE).
    Returns None on failure.
    """
    try:
        f = ROOT.TFile.Open(rootfile, "READ")
        if not f or f.IsZombie():
            print(f"  [ERR] Cannot open {rootfile}")
            return None
    except Exception as exc:
        print(f"  [ERR] {exc}")
        return None

    info_obj = f.Get("energy_info")
    if not info_obj:
        print(f"  [ERR] energy_info not found in {rootfile}")
        f.Close()
        return None

    raw = {}
    for token in info_obj.GetTitle().split(';'):
        if '=' in token:
            k, v = token.split('=', 1)
            try:
                raw[k] = float(v)
            except ValueError:
                raw[k] = v

    f.Close()

    def _get(key, scale=1.0):
        v = raw.get(key, -1)
        return float(v) * scale if (v is not None and float(v) > 0) else -1.0

    def _err(key, scale=1.0):
        v = raw.get(key, 0)
        return float(v) * scale if (v is not None and float(v) > 0) else 0.0

    return {
        # Continuous PE
        'resolution_pecontin':     _get('RES_PEcontin', 100.0),
        'resolution_pecontin_err': _err('RES_PEcontin_ERR', 100.0),
        'mean_pecontin':           _get('MEAN_PEcontin'),
        'mean_pecontin_err':       _err('MEAN_PEcontin_ERR'),
        'sigma_pecontin':          _get('SIGMA_PEcontin'),
        'sigma_pecontin_err':      _err('SIGMA_PEcontin_ERR'),
        # Discrete PE
        'resolution_pe':           _get('RES_PE', 100.0),
        'resolution_pe_err':       _err('RES_PE_ERR', 100.0),
        'mean_pe':                 _get('MEAN_PE'),
        'mean_pe_err':             _err('MEAN_PE_ERR'),
        'sigma_pe':                _get('SIGMA_PE'),
        'sigma_pe_err':            _err('SIGMA_PE_ERR'),
    }

# ---------------------------------------------------------------------------
# Load a full dataset
# ---------------------------------------------------------------------------

def load_dataset(base_dir, dataset):
    """
    For every run in *dataset*, find and read the RTRAW-custom file.
    Returns two sorted lists:
        ovs          – list of OV values (float)
        metrics_list – list of metric dicts (or None if run missing)
    Only entries where the file was found are included.
    """
    ov_map = dataset['ov_map']
    entries = []  # (ov, metrics_dict)

    for run in dataset['runs']:
        ov = ov_map.get(run)
        if ov is None:
            print(f"  [WARN] RUN{run} has no OV mapping — skipped")
            continue
        rootfile = find_rtraw_custom_file(base_dir, run)
        if rootfile is None:
            continue
        m = extract_metrics(rootfile)
        if m is None:
            continue
        entries.append((ov, m))

    entries.sort(key=lambda x: x[0])   # sort by OV
    if not entries:
        return [], []
    ovs, mets = zip(*entries)
    return list(ovs), list(mets)

# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_metric(metric_name, data_A, data_B, output_path):
    """
    Produce one comparison plot for *metric_name*.

    data_A / data_B : (ovs, metrics_list) tuples from load_dataset()
    """
    meta = METRICS[metric_name]
    fig, ax = plt.subplots()

    def _plot_series(ovs, mets, dataset_key, pe_type):
        """Draw one errorbar series, skip points with value <= 0."""
        val_key = meta['val_key'] if pe_type == 'contin' else meta['val_key_disc']
        err_key = meta['err_key'] if pe_type == 'contin' else meta['err_key_disc']
        style   = SERIES_STYLES[(dataset_key, pe_type)]

        xs, ys, yes = [], [], []
        for ov, m in zip(ovs, mets):
            v = m.get(val_key, -1)
            e = m.get(err_key, 0)
            if v > 0:
                xs.append(ov)
                ys.append(v)
                yes.append(e)

        if not xs:
            print(f"  [WARN] No valid data for Dataset {dataset_key}, {pe_type} PE, metric={metric_name}")
            return

        ax.errorbar(
            xs, ys, yerr=yes,
            fmt=style['marker'],
            linestyle=style['ls'],
            color=style['color'],
            markersize=8, linewidth=2,
            capsize=5, capthick=2,
            label=f"Dataset {'A' if dataset_key == 'A' else 'B'} — {style['label']}",
        )

    ovs_A, mets_A = data_A
    ovs_B, mets_B = data_B

    _plot_series(ovs_A, mets_A, 'A', 'contin')
    _plot_series(ovs_A, mets_A, 'A', 'discrete')
    _plot_series(ovs_B, mets_B, 'B', 'contin')
    _plot_series(ovs_B, mets_B, 'B', 'discrete')

    ax.set_xlabel('Overvoltage (OV)  [V]', fontsize=13, fontweight='bold')
    ax.set_ylabel(meta['ylabel'],           fontsize=13, fontweight='bold')
    ax.set_title(meta['title'],             fontsize=14, fontweight='bold', pad=12)

    # ── Legend: two columns, one per dataset ──────────────────────────────
    # Manual legend entries to group by dataset and pe type clearly
    legend_elements = [
        # Dataset A header (invisible line, just label)
        mlines.Line2D([], [], color='none', label='── Dataset A (RUN 1253-1263) ──'),
        mlines.Line2D([], [], color=SERIES_STYLES[('A','contin')]['color'],
                      marker='o', ls='-',  linewidth=2, markersize=7,
                      label='Continuous PE'),
        mlines.Line2D([], [], color=SERIES_STYLES[('A','discrete')]['color'],
                      marker='s', ls='--', linewidth=2, markersize=7,
                      label='Discrete PE'),
        # Dataset B
        mlines.Line2D([], [], color='none', label='── Dataset B (RUN 1053-1058) ──'),
        mlines.Line2D([], [], color=SERIES_STYLES[('B','contin')]['color'],
                      marker='o', ls='-',  linewidth=2, markersize=7,
                      label='Continuous PE'),
        mlines.Line2D([], [], color=SERIES_STYLES[('B','discrete')]['color'],
                      marker='s', ls='--', linewidth=2, markersize=7,
                      label='Discrete PE'),
    ]
    ax.legend(handles=legend_elements, loc='best',
              frameon=True, fancybox=True, shadow=True, fontsize=10)

    ax.grid(alpha=0.35)
    plt.tight_layout()
    fig.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved: {output_path}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare RTRAW custom-gain OV scans for two Ge-68 datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--base-dir',    required=True,
                        help='Base directory containing RUN* folders '
                             '(energy_resolution level, same as in compare_run_groups.py)')
    parser.add_argument('--output-dir',  required=True,
                        help='Directory where PNG plots will be saved')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("\n" + "="*70)
    print("Loading Dataset A (RUN 1253-1263)")
    print("="*70)
    data_A = load_dataset(args.base_dir, DATASET_A)

    print("\n" + "="*70)
    print("Loading Dataset B (RUN 1053-1058)")
    print("="*70)
    data_B = load_dataset(args.base_dir, DATASET_B)

    if not data_A[0] and not data_B[0]:
        print("\n[ERROR] No data found for either dataset. Check --base-dir.")
        return 1

    print("\n" + "="*70)
    print("Generating plots")
    print("="*70)
    for metric in ('resolution', 'mean', 'sigma'):
        out = os.path.join(args.output_dir, f"ge68_ov_comparison_{metric}.png")
        print(f"\n  Plotting {metric}...")
        plot_metric(metric, data_A, data_B, out)

    print("\n" + "="*70)
    print("Done. Plots saved to:", args.output_dir)
    print("="*70 + "\n")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
