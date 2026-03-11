#!/usr/bin/env python3
"""
compare_runs_gain.py
====================
Compare SiPM gain and intercept between two calibration runs.

Reads the Method-A "good" CSV files from the latest stable_* output of each RUN,
merges on channel_id (only channels classified as good in BOTH runs), and produces:

  1. Overlaid gain distributions  (two histograms)
  2. Overlaid intercept distributions
  3. Gain residuals:      Delta_G(ch) = G_run2(ch) - G_run1(ch)  vs channel ID
  4. Intercept residuals:  Delta_I(ch) = I_run2(ch) - I_run1(ch) vs channel ID
  5. Residual distributions (1-D histograms of Delta_G and Delta_I)
  6. Summary text file

Error bars on residuals use propagation of errors:
  sigma_Delta = sqrt( sigma_run1^2 + sigma_run2^2 )

Hardcoded runs: 1295 and 1410.

Usage:
  python compare_runs_gain.py [output_dir]

Author: G. Ferrante
"""

import glob
import logging
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# =============================================================================
# CONFIG — hardcoded runs and base path
# =============================================================================
RUN_1 = 1295
RUN_2 = 1410

BASE_DIR = "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/1-gain_calibration_results"

# Classification method to compare (Method A = standard)
METHOD = "A_standard"


# =============================================================================
# HELPERS
# =============================================================================

def find_latest_stable_dir(run_number: int) -> str:
    """
    Find the latest stable_* directory for a given RUN.
    Directories are named stable_YYYYMMDD_HHMMSS, so lexicographic sort
    on the timestamp suffix gives the most recent one.
    """
    run_dir = os.path.join(BASE_DIR, f"RUN{run_number}")
    if not os.path.isdir(run_dir):
        logging.error(f"RUN directory does not exist: {run_dir}")
        sys.exit(1)

    pattern = os.path.join(run_dir, "stable_*")
    candidates = sorted(glob.glob(pattern))
    # Keep only actual directories
    candidates = [d for d in candidates if os.path.isdir(d)]

    if not candidates:
        logging.error(f"No stable_* directories found in {run_dir}")
        sys.exit(1)

    latest = candidates[-1]
    logging.info(f"  RUN {run_number}: using {os.path.basename(latest)}")
    return latest


def load_good_csv(stable_dir: str, run_number: int) -> pd.DataFrame:
    """Load the Method-A good-channels CSV from a stable output directory."""
    csv_name = f"RUN{run_number}_{METHOD}_good.csv"
    csv_path = os.path.join(stable_dir, csv_name)

    if not os.path.isfile(csv_path):
        logging.error(f"CSV not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    logging.info(f"  Loaded {len(df)} good channels from {csv_name}")
    return df


# =============================================================================
# PLOTTING
# =============================================================================

def plot_distribution_comparison(df1, df2, col, xlabel, run1, run2, out_path):
    """Overlaid histograms of a column from each run."""
    v1, v2 = df1[col].values, df2[col].values

    lo = min(v1.min(), v2.min()) * 0.95
    hi = max(v1.max(), v2.max()) * 1.05

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(v1, bins=60, range=(lo, hi), alpha=0.6, edgecolor='k', linewidth=0.5,
            color='#1f77b4', label=f'RUN {run1}  (N={len(v1)}, mu={v1.mean():.1f}, sigma={v1.std():.1f})')
    ax.hist(v2, bins=60, range=(lo, hi), alpha=0.6, edgecolor='k', linewidth=0.5,
            color='#ff7f0e', label=f'RUN {run2}  (N={len(v2)}, mu={v2.mean():.1f}, sigma={v2.std():.1f})')

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Channels', fontsize=12)
    ax.set_title(f'{xlabel} Distribution Comparison', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"  Saved {os.path.basename(out_path)}")


def plot_residuals(merged, col, col_err, ylabel, run1, run2, out_path):
    """
    Channel-by-channel residual plot:
      Delta = val_run2 - val_run1
      sigma_Delta = sqrt(err_run1^2 + err_run2^2)
    x-axis = channel_id, y-axis = Delta with error bars.
    """
    ch_ids = merged['channel_id'].values
    v1     = merged[f'{col}_1'].values
    v2     = merged[f'{col}_2'].values
    e1     = merged[f'{col_err}_1'].values
    e2     = merged[f'{col_err}_2'].values

    delta   = v2 - v1
    sigma_d = np.sqrt(e1**2 + e2**2)

    # Statistics
    mean_d  = np.mean(delta)
    std_d   = np.std(delta)
    mean_sd = np.mean(sigma_d)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.errorbar(ch_ids, delta, yerr=sigma_d,
                fmt='.', ms=2, elinewidth=0.5, capsize=0,
                color='#2ca02c', alpha=0.7, label='Channel residuals')

    ax.axhline(0, color='black', lw=1.2, ls='-')
    ax.axhline(mean_d, color='red', lw=1.5, ls='--',
               label=f'Mean = {mean_d:.2f}')
    ax.axhline(mean_d + std_d, color='red', lw=1.0, ls=':', alpha=0.7)
    ax.axhline(mean_d - std_d, color='red', lw=1.0, ls=':', alpha=0.7,
               label=f'+/- sigma = {std_d:.2f}')

    ax.set_xlabel('Channel ID', fontsize=12)
    ax.set_ylabel(f'Delta {ylabel}  (RUN {run2} - RUN {run1})', fontsize=12)
    ax.set_title(f'{ylabel} Residuals:  RUN {run2} - RUN {run1}  '
                 f'({len(merged)} common good channels)',
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3)

    # Info box
    info = (
        f"N channels: {len(merged)}\n"
        f"Mean(Delta): {mean_d:.2f}\n"
        f"Std(Delta): {std_d:.2f}\n"
        f"Mean(sigma_Delta): {mean_sd:.2f}"
    )
    ax.text(0.02, 0.97, info, transform=ax.transAxes, va='top',
            fontsize=9, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.85))

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"  Saved {os.path.basename(out_path)}")


def plot_residual_distribution(merged, col, col_err, xlabel, run1, run2, out_path):
    """1-D histogram of the residuals Delta = run2 - run1."""
    v1    = merged[f'{col}_1'].values
    v2    = merged[f'{col}_2'].values
    delta = v2 - v1

    mean_d = np.mean(delta)
    std_d  = np.std(delta)

    fig, ax = plt.subplots(figsize=(10, 6))
    counts, bin_edges, _ = ax.hist(delta, bins=60, color='#2ca02c', alpha=0.7, edgecolor='k',
                                    linewidth=0.5)
    ax.axvline(mean_d, color='red', lw=2, ls='--',
               label=f'Mean = {mean_d:.2f}')
    ax.axvline(0, color='black', lw=1.2, ls='-', alpha=0.5)

    ax.set_xlabel(f'Delta {xlabel}  (RUN {run2} - RUN {run1})', fontsize=12)
    ax.set_ylabel('Channels', fontsize=12)
    ax.set_title(f'Distribution of {xlabel} Residuals  '
                 f'({len(merged)} common good channels)',
                 fontsize=13, fontweight='bold')

    info = (
        f"N = {len(delta)}\n"
        f"Mean = {mean_d:.2f}\n"
        f"Sigma = {std_d:.2f}"
    )
    ax.text(0.97, 0.97, info, transform=ax.transAxes, va='top', ha='right',
            fontsize=10, family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.85))

    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"  Saved {os.path.basename(out_path)}")


def plot_correlation(merged, col, xlabel, run1, run2, out_path):
    """Scatter plot of run2 vs run1 values with y=x reference line."""
    v1 = merged[f'{col}_1'].values
    v2 = merged[f'{col}_2'].values

    lo = min(v1.min(), v2.min()) * 0.98
    hi = max(v1.max(), v2.max()) * 1.02

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(v1, v2, s=4, alpha=0.4, c='#1f77b4', edgecolors='none')
    ax.plot([lo, hi], [lo, hi], 'r--', lw=1.5, label='y = x')

    ax.set_xlabel(f'{xlabel}  RUN {run1}', fontsize=12)
    ax.set_ylabel(f'{xlabel}  RUN {run2}', fontsize=12)
    ax.set_title(f'{xlabel} Correlation  ({len(merged)} channels)',
                 fontsize=13, fontweight='bold')
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect('equal')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"  Saved {os.path.basename(out_path)}")


def write_summary_txt(df1, df2, merged, run1, run2, dir1, dir2, out_path):
    """Write a human-readable summary text file."""
    v1_g = merged['gain_1'].values
    v2_g = merged['gain_2'].values
    v1_i = merged['intercept_1'].values
    v2_i = merged['intercept_2'].values

    dg = v2_g - v1_g
    di = v2_i - v1_i
    e1_g = merged['gain_error_1'].values
    e2_g = merged['gain_error_2'].values
    e1_i = merged['intercept_error_1'].values
    e2_i = merged['intercept_error_2'].values
    sdg = np.sqrt(e1_g**2 + e2_g**2)
    sdi = np.sqrt(e1_i**2 + e2_i**2)

    with open(out_path, 'w') as f:
        f.write(f"{'='*90}\n")
        f.write(f"GAIN CALIBRATION COMPARISON:  RUN {run1}  vs  RUN {run2}\n")
        f.write(f"{'='*90}\n\n")

        f.write(f"Source directories:\n")
        f.write(f"  RUN {run1}: {dir1}\n")
        f.write(f"  RUN {run2}: {dir2}\n\n")

        f.write(f"Classification: Method A ({METHOD})\n\n")

        f.write(f"{'─'*90}\n")
        f.write(f"CHANNEL COUNTS\n")
        f.write(f"{'─'*90}\n")
        f.write(f"  Good in RUN {run1}:           {len(df1):>6}\n")
        f.write(f"  Good in RUN {run2}:           {len(df2):>6}\n")
        f.write(f"  Good in BOTH (common):      {len(merged):>6}\n")
        only1 = set(df1['channel_id']) - set(df2['channel_id'])
        only2 = set(df2['channel_id']) - set(df1['channel_id'])
        f.write(f"  Good only in RUN {run1}:      {len(only1):>6}\n")
        f.write(f"  Good only in RUN {run2}:      {len(only2):>6}\n\n")

        f.write(f"{'─'*90}\n")
        f.write(f"GAIN [ADC/PE]\n")
        f.write(f"{'─'*90}\n")
        for lbl, vals in [(f'RUN {run1}', v1_g), (f'RUN {run2}', v2_g)]:
            f.write(f"  {lbl:<12}  N={len(vals):>5}  "
                    f"Mean={vals.mean():>8.2f}  Std={vals.std():>7.2f}  "
                    f"Min={vals.min():>8.2f}  Max={vals.max():>8.2f}\n")
        f.write(f"\n  Residuals (RUN {run2} - RUN {run1}):\n")
        f.write(f"    Mean(Delta_G)           = {dg.mean():>8.2f} ADC/PE\n")
        f.write(f"    Std(Delta_G)            = {dg.std():>8.2f} ADC/PE\n")
        f.write(f"    Mean(sigma_Delta_G)     = {sdg.mean():>8.2f} ADC/PE  (propagated)\n")
        f.write(f"    Relative shift          = {100*dg.mean()/v1_g.mean():>+7.3f} %\n\n")

        f.write(f"{'─'*90}\n")
        f.write(f"INTERCEPT [ADC]\n")
        f.write(f"{'─'*90}\n")
        for lbl, vals in [(f'RUN {run1}', v1_i), (f'RUN {run2}', v2_i)]:
            f.write(f"  {lbl:<12}  N={len(vals):>5}  "
                    f"Mean={vals.mean():>8.2f}  Std={vals.std():>7.2f}  "
                    f"Min={vals.min():>8.2f}  Max={vals.max():>8.2f}\n")
        f.write(f"\n  Residuals (RUN {run2} - RUN {run1}):\n")
        f.write(f"    Mean(Delta_I)           = {di.mean():>8.2f} ADC\n")
        f.write(f"    Std(Delta_I)            = {di.std():>8.2f} ADC\n")
        f.write(f"    Mean(sigma_Delta_I)     = {sdi.mean():>8.2f} ADC  (propagated)\n\n")

        f.write(f"{'='*90}\n")
        f.write(f"END OF COMPARISON\n")
        f.write(f"{'='*90}\n")

    logging.info(f"  Saved {os.path.basename(out_path)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description=f'Compare gain calibration between RUN {RUN_1} and RUN {RUN_2}')
    parser.add_argument('output_dir', nargs='?',
                        default=os.path.join(BASE_DIR, f"comparison_RUN{RUN_1}_vs_RUN{RUN_2}"),
                        help='Output directory (default: comparison_RUNxxxx_vs_RUNyyyy '
                             'inside the gain results base dir)')
    args = parser.parse_args()

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)

    logging.info(f"{'='*60}")
    logging.info(f"GAIN COMPARISON:  RUN {RUN_1}  vs  RUN {RUN_2}")
    logging.info(f"{'='*60}")

    # ── Find latest stable directories ──────────────────────────────────────
    dir1 = find_latest_stable_dir(RUN_1)
    dir2 = find_latest_stable_dir(RUN_2)

    # ── Load good-channels CSVs ─────────────────────────────────────────────
    df1 = load_good_csv(dir1, RUN_1)
    df2 = load_good_csv(dir2, RUN_2)

    # ── Merge on channel_id (inner join = common good channels) ─────────────
    merged = pd.merge(df1, df2, on='channel_id', suffixes=('_1', '_2'), how='inner')
    logging.info(f"  Common good channels: {len(merged)}")

    if len(merged) == 0:
        logging.error("No common good channels between the two runs!")
        sys.exit(1)

    # ── 1. Distribution comparisons ─────────────────────────────────────────
    logging.info("\nGenerating distribution comparison plots...")
    plot_distribution_comparison(
        df1, df2, 'gain', 'Gain [ADC/PE]', RUN_1, RUN_2,
        os.path.join(out_dir, f'gain_distribution_RUN{RUN_1}_vs_RUN{RUN_2}.png'))
    plot_distribution_comparison(
        df1, df2, 'intercept', 'Intercept [ADC]', RUN_1, RUN_2,
        os.path.join(out_dir, f'intercept_distribution_RUN{RUN_1}_vs_RUN{RUN_2}.png'))

    # ── 2. Correlation scatter plots ────────────────────────────────────────
    logging.info("Generating correlation plots...")
    plot_correlation(
        merged, 'gain', 'Gain [ADC/PE]', RUN_1, RUN_2,
        os.path.join(out_dir, f'gain_correlation_RUN{RUN_1}_vs_RUN{RUN_2}.png'))
    plot_correlation(
        merged, 'intercept', 'Intercept [ADC]', RUN_1, RUN_2,
        os.path.join(out_dir, f'intercept_correlation_RUN{RUN_1}_vs_RUN{RUN_2}.png'))

    # ── 3. Residual plots (channel-by-channel) ──────────────────────────────
    logging.info("Generating residual plots...")
    plot_residuals(
        merged, 'gain', 'gain_error', 'Gain [ADC/PE]', RUN_1, RUN_2,
        os.path.join(out_dir, f'gain_residuals_RUN{RUN_1}_vs_RUN{RUN_2}.png'))
    plot_residuals(
        merged, 'intercept', 'intercept_error', 'Intercept [ADC]', RUN_1, RUN_2,
        os.path.join(out_dir, f'intercept_residuals_RUN{RUN_1}_vs_RUN{RUN_2}.png'))

    # ── 4. Residual distributions ───────────────────────────────────────────
    logging.info("Generating residual distribution plots...")
    plot_residual_distribution(
        merged, 'gain', 'gain_error', 'Gain [ADC/PE]', RUN_1, RUN_2,
        os.path.join(out_dir, f'gain_residual_dist_RUN{RUN_1}_vs_RUN{RUN_2}.png'))
    plot_residual_distribution(
        merged, 'intercept', 'intercept_error', 'Intercept [ADC]', RUN_1, RUN_2,
        os.path.join(out_dir, f'intercept_residual_dist_RUN{RUN_1}_vs_RUN{RUN_2}.png'))

    # ── 5. Summary text ─────────────────────────────────────────────────────
    logging.info("Writing summary...")
    write_summary_txt(
        df1, df2, merged, RUN_1, RUN_2, dir1, dir2,
        os.path.join(out_dir, f'comparison_summary_RUN{RUN_1}_vs_RUN{RUN_2}.txt'))

    # ── 6. Save merged CSV for further analysis ─────────────────────────────
    merged_csv = os.path.join(out_dir, f'merged_good_channels_RUN{RUN_1}_vs_RUN{RUN_2}.csv')
    merged.to_csv(merged_csv, index=False)
    logging.info(f"  Saved merged CSV: {os.path.basename(merged_csv)}")

    logging.info(f"\nDone! All outputs in: {out_dir}")
    logging.info(f"  8 PNG plots + 1 TXT summary + 1 merged CSV")


if __name__ == "__main__":
    main()
