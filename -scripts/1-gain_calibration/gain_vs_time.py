#!/usr/bin/env python3
"""
gain_vs_time.py  –  Gain and intercept stability monitoring over time

Reads a directory of CHARGE ROOT files (output of extract_charge_calib.py),
fits each file (or merged batch) with the same ROOT multi-Gaussian workflow as
gain_calibration_stable.py, and produces gain / intercept vs time plots.

Model
-----
  multigauss   Plain multi-Gaussian (ROOT TF1, same as gain_calibration_stable)

Adaptive batch groupings
────────────────────────
  n_files <  30  →  N=1,  N=10        (skip N=10 if n_files < 10)
  30 ≤ n_files < 300 →  N=10, N=50    (skip N=50 if n_files < 50)
  n_files ≥ 300  →  N=50, N=100       (skip N=100 if n_files < 100)
  Each batch size is only used if batch_size < n_files.

Two plot variants per grouping
──────────────────────────────
  a)  average only  – per-time-step mean ± error bar
  b)  average + per-channel – thin channel lines + thick average line

Panels per figure
─────────────────
  row 0 – Gain vs time
  row 1 – Intercept vs time

Output files
────────────
  gain_intercept_multigauss_N{X}_avg.png
  gain_intercept_multigauss_N{X}_full.png
  gain_vs_time_summary.csv

Usage
─────
  python gain_vs_time.py /path/to/charge_files/ output_dir run_name
  python gain_vs_time.py /path/to/charge_files/ output_dir run_name \\
        --use-raw --time-per-file 60 --n-workers 8
  python gain_vs_time.py /path/to/charge_files/ output_dir run_name \\
        --timestamps timestamps.txt

Author: G. Ferrante  (adapted from gain_calibration_stable.py)
"""

import argparse
import logging
import os
import sys
import glob
import re
from multiprocessing import Pool, cpu_count

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        return it

# ── Import core fitting machinery from gain_calibration_stable ────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

try:
    from gain_calibration_stable import (
        BIN_CENTERS,
        BIN_WIDTH,
        N_BINS,
        EXPECTED_GAIN_MIN,
        EXPECTED_GAIN_MAX,
        CHI2_MAX,
        LINEAR_R2_MIN,
        process_channel_root,
    )
except ImportError as _e:
    print(f"ERROR: Could not import from gain_calibration_stable.py: {_e}")
    print("       Make sure gain_calibration_stable.py is in the same directory.")
    sys.exit(1)

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s: %(message)s")

# ── Model constants (single model: multigauss from stable) ───────────────────
MODEL_NAMES  = ['multigauss']
MODEL_LABELS = {'multigauss': 'Multi-Gauss (stable)'}
MODEL_COLORS = {'multigauss': '#1f77b4'}
MODEL_COLORS_LIGHT = {'multigauss': '#aec7e8'}

# ─────────────────────────────────────────────────────────────────────────────
# File discovery & timestamp helpers
# ─────────────────────────────────────────────────────────────────────────────

_CHARGE_GLOB = "CHARGE_single_*.root"
_FILE_NUM_RE  = re.compile(r"CHARGE_single_RUN\d+_(\d+).*\.root$", re.IGNORECASE)


def _discover_charge_files(directory: str) -> list:
    """Return list of CHARGE ROOT files sorted by embedded file number."""
    pattern = os.path.join(directory, _CHARGE_GLOB)
    files   = sorted(glob.glob(pattern))
    if not files:
        files = sorted(glob.glob(os.path.join(directory, "*.root")))
    return files


def _file_index(fname: str) -> int:
    """Extract numeric file index from CHARGE filename."""
    m = _FILE_NUM_RE.search(os.path.basename(fname))
    return int(m.group(1)) if m else 0


def _load_timestamps(ts_file: str) -> dict:
    """
    Load explicit timestamps from a text file.
    Format (one line per file):  file_number   unix_timestamp_seconds
    Returns dict {file_index: unix_ts}.
    """
    ts = {}
    with open(ts_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    ts[int(parts[0])] = float(parts[1])
                except ValueError:
                    continue
    return ts


def build_time_axis(files: list, time_per_file: float,
                    ts_map: dict) -> np.ndarray:
    """
    Build a 1-D array of time values (seconds) for each file.

    Priority:
      1. ts_map[file_index] if available
      2. file_index * time_per_file
    """
    times = []
    for fpath in files:
        fidx = _file_index(fpath)
        if fidx in ts_map:
            times.append(ts_map[fidx])
        else:
            times.append(fidx * time_per_file)
    return np.array(times, dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# Histogram loading & merging
# ─────────────────────────────────────────────────────────────────────────────

def load_histograms(root_file: str, use_raw: bool = False) -> dict:
    """
    Load all per-channel ADC histograms from a CHARGE ROOT file.
    Returns {ch_id: np.ndarray (same binning as BIN_CENTERS)}.
    """
    prefix = "H_adcraw_" if use_raw else "H_adcClean_"
    out    = {}

    try:
        f = ROOT.TFile.Open(root_file, "READ")
        if not f or f.IsZombie():
            return out

        for key in f.GetListOfKeys():
            name = key.GetName()
            if not name.startswith(prefix):
                continue
            try:
                ch_id = int(name.replace(prefix, ""))
            except ValueError:
                continue

            h = f.Get(name)
            if not h:
                continue

            nbins = h.GetNbinsX()
            buf = h.GetArray()
            arr_full = np.array([buf[i] for i in range(1, nbins + 1)],
                                dtype=np.float64)

            if nbins == len(BIN_CENTERS):
                out[ch_id] = arr_full
            else:
                arr = np.zeros(len(BIN_CENTERS))
                for i, bc in enumerate(BIN_CENTERS):
                    b = h.FindBin(bc)
                    if 1 <= b <= nbins:
                        arr[i] = h.GetBinContent(b)
                out[ch_id] = arr

        f.Close()
    except Exception as e:
        logging.warning(f"Could not load {root_file}: {e}")
    return out


def merge_histogram_dicts(hist_list: list) -> dict:
    """Sum histograms from multiple files channel-by-channel."""
    merged = {}
    for hd in hist_list:
        for ch_id, arr in hd.items():
            if ch_id in merged:
                merged[ch_id] += arr
            else:
                merged[ch_id] = arr.copy()
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Per-channel fitting
# ─────────────────────────────────────────────────────────────────────────────

def _fit_one(args):
    """
    Multiprocessing worker wrapper.
    Calls gain_calibration_stable.process_channel_root and returns
    (ch_id, result_dict).
    """
    ch_id, hist = args
    result = process_channel_root(ch_id, hist)
    return ch_id, result


def fit_histogram_dict(hist_dict: dict, n_workers: int = 4,
                       pool=None) -> dict:
    """
    Fit all channels in hist_dict using ROOT multi-Gaussian.

    Returns {ch_id: result_dict} where result_dict has the same keys
    as gain_calibration_stable.process_channel_root.
    """
    items = list(hist_dict.items())
    all_results = {}

    if pool is not None:
        for ch_id, result in pool.imap(_fit_one, items, chunksize=8):
            all_results[ch_id] = result
    else:
        with Pool(n_workers) as tmp_pool:
            for ch_id, result in tmp_pool.imap(_fit_one, items, chunksize=8):
                all_results[ch_id] = result
    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Per-batch summarisation
# ─────────────────────────────────────────────────────────────────────────────

def summarise_results(all_results: dict,
                      gain_min: float,
                      gain_max: float) -> dict:
    """
    From {ch_id: result_dict}, compute summary statistics.

    Returns summary_dict or None if no good fits.

    Result dict keys from gain_calibration_stable:
      fit_status, gain, gain_error, intercept, intercept_error,
      chi2_dof, linear_r2, n_peaks, ...
    """
    good_gains  = []
    good_ints   = []
    good_chids  = []

    for ch_id, r in all_results.items():
        if r.get('fit_status', -1) != 1:
            continue
        if r.get('n_peaks', 0) < 3:
            continue
        if not (0 <= r.get('chi2_dof', -1) <= CHI2_MAX):
            continue
        if r.get('linear_r2', 0.0) < LINEAR_R2_MIN:
            continue
        gain_val = r.get('gain', 0.0)
        if not (gain_min <= gain_val <= gain_max):
            continue

        good_gains.append(gain_val)
        good_ints.append(r.get('intercept', np.nan))
        good_chids.append(ch_id)

    if not good_gains:
        return None

    gains = np.array(good_gains)
    ints  = np.array(good_ints)
    chids = np.array(good_chids)
    n     = len(gains)

    return {
        "n_ch"     : n,
        "mean_gain": float(gains.mean()),
        "std_gain" : float(gains.std()),
        "err_gain" : float(gains.std() / np.sqrt(n)),
        "mean_int" : float(np.nanmean(ints)),
        "std_int"  : float(np.nanstd(ints)),
        "err_int"  : float(np.nanstd(ints) / np.sqrt(n)),
        "ch_ids"   : chids,
        "ch_gains" : gains,
        "ch_ints"  : ints,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Batch processing
# ─────────────────────────────────────────────────────────────────────────────

def process_batches(files: list, times: np.ndarray,
                    batch_size: int, use_raw: bool,
                    n_workers: int,
                    gain_min: float, gain_max: float) -> tuple:
    """
    Merge files in groups of batch_size, fit each group, summarise.

    Returns
    -------
    (batch_times, summaries_list)
      batch_times    – 1-D array of representative times (batch midpoint)
      summaries_list – [summary_dict | None, ...]
    """
    n_files   = len(files)
    n_batches = n_files // batch_size
    if n_batches == 0:
        return np.array([]), []

    batch_times = []
    summaries   = []

    with Pool(n_workers) as pool:
        for b in tqdm(range(n_batches), desc=f"  Batches N={batch_size}"):
            idx_lo      = b * batch_size
            idx_hi      = idx_lo + batch_size
            batch_files = files[idx_lo:idx_hi]
            batch_t     = float(times[idx_lo:idx_hi].mean())

            hist_list = [load_histograms(fp, use_raw) for fp in batch_files]
            merged    = merge_histogram_dicts(hist_list)

            all_results = fit_histogram_dict(merged, n_workers, pool=pool)
            s = summarise_results(all_results, gain_min, gain_max)

            batch_times.append(batch_t)
            summaries.append(s)

    return np.array(batch_times), summaries


# ─────────────────────────────────────────────────────────────────────────────
# Adaptive batch sizes
# ─────────────────────────────────────────────────────────────────────────────

def get_batch_sizes(n_files: int) -> list:
    """
    Return the list of batch sizes to use, based on the number of RTRAW files.

      n_files <  30  →  [1, 10]
      30 <= n_files < 300  →  [10, 50]
      n_files >= 300  →  [50, 100]

    Each batch size is only kept if it is strictly less than n_files.
    """
    if n_files < 30:
        candidates = [1, 10]
    elif n_files < 300:
        candidates = [10, 50]
    else:
        candidates = [50, 100]

    return [N for N in candidates if N < n_files]


# ─────────────────────────────────────────────────────────────────────────────
# Plotting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dt_rescaled(dt: np.ndarray) -> tuple:
    """Rescale dt array to best-fit unit. Returns (rescaled_array, xlabel)."""
    span = dt[-1] - dt[0] if len(dt) > 1 else 0
    if span > 7200:
        return dt / 3600.0, "Elapsed time [h]"
    if span > 120:
        return dt / 60.0, "Elapsed time [min]"
    return dt, "Elapsed time [s]"


def _infobox_text(mean: float, std: float, label: str) -> str:
    return (f"<{label}> = {mean:.4g}\n"
            f"sigma = {std:.4g}")


def _add_ref_lines(ax, mean: float, std: float, color: str = "#444444"):
    ax.axhline(mean,       color=color, ls="--", lw=1.2, alpha=0.8)
    ax.axhline(mean + std, color=color, ls=":",  lw=0.9, alpha=0.6)
    ax.axhline(mean - std, color=color, ls=":",  lw=0.9, alpha=0.6)


def _make_panel(ax, x, y, yerr, y_ch,
                mean_val, std_val,
                show_channels: bool,
                ylabel: str,
                color_avg: str, color_ch: str,
                title: str):
    """
    Draw one time-series panel (gain or intercept).

    x        : time axis (rescaled, 1-D)
    y        : average values per batch (1-D)
    yerr     : error on average per batch (1-D)
    y_ch     : per-channel value array (2-D [n_batches, n_channels]) or None
    """
    if show_channels and y_ch is not None and y_ch.ndim == 2:
        for col in range(y_ch.shape[1]):
            col_data = y_ch[:, col]
            valid    = np.isfinite(col_data)
            if valid.sum() >= 2:
                ax.plot(x[valid], col_data[valid],
                        color=color_ch, lw=0.4, alpha=0.25)

    ax.errorbar(x, y, yerr=yerr,
                fmt="o-", color=color_avg,
                lw=2.5, ms=5, capsize=3, zorder=5, label="Mean")

    _add_ref_lines(ax, mean_val, std_val, color=color_avg)

    info = _infobox_text(mean_val, std_val, ylabel.split("[")[0].strip())
    ax.text(0.98, 0.97, info,
            transform=ax.transAxes, va="top", ha="right",
            fontsize=8, family="monospace",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.85))

    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)


def _build_channel_matrix(sums_ok: list, key: str) -> np.ndarray:
    """
    Build a (n_batches x n_channels) matrix for a per-channel array key.
    NaN-pads missing channels.
    """
    arrays = [s.get(key, np.array([])) for s in sums_ok]
    max_n  = max((len(a) for a in arrays), default=0)
    if max_n == 0:
        return None
    mat = np.full((len(sums_ok), max_n), np.nan)
    for bi, arr in enumerate(arrays):
        n = len(arr)
        if n > 0:
            mat[bi, :n] = arr
    return mat


def make_gain_vs_time_figure(batch_times: np.ndarray,
                              summaries: list,
                              batch_size: int,
                              run_name: str,
                              show_channels: bool,
                              output_path: str):
    """
    Build and save a 2-row figure:
      row 0  – Gain vs time
      row 1  – Intercept vs time
    """
    valid_mask = np.array([s is not None for s in summaries])
    if valid_mask.sum() < 2:
        logging.warning(f"  N={batch_size}: < 2 valid batches – skipping.")
        return

    t0   = batch_times[valid_mask][0]
    dt   = batch_times[valid_mask] - t0
    dt_r, xlabel = _dt_rescaled(dt)

    sums_ok = [s for s, v in zip(summaries, valid_mask) if v]

    gains  = np.array([s["mean_gain"] for s in sums_ok])
    ints   = np.array([s["mean_int"]  for s in sums_ok])
    eg     = np.array([s["err_gain"]  for s in sums_ok])
    ei     = np.array([s["err_int"]   for s in sums_ok])

    t_mean_g = float(gains.mean());  t_std_g = float(gains.std())
    t_mean_i = float(ints.mean());   t_std_i = float(ints.std())

    col_avg = MODEL_COLORS['multigauss']
    col_ch  = MODEL_COLORS_LIGHT['multigauss']

    # Per-channel matrices
    if show_channels:
        mat_g = _build_channel_matrix(sums_ok, "ch_gains")
        mat_i = _build_channel_matrix(sums_ok, "ch_ints")
    else:
        mat_g = mat_i = None

    variant_lbl = "avg+channels" if show_channels else "avg"
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    fig.suptitle(f"Gain & Intercept vs Time  |  {run_name}  "
                 f"|  Multi-Gauss  |  N={batch_size}  |  {variant_lbl}",
                 fontsize=11)

    _make_panel(
        axes[0], dt_r, gains, eg, mat_g,
        t_mean_g, t_std_g, show_channels,
        "Gain [ADC/PE]",
        col_avg, col_ch,
        f"Gain vs Time  (N={batch_size})")

    _make_panel(
        axes[1], dt_r, ints, ei, mat_i,
        t_mean_i, t_std_i, show_channels,
        "Intercept [ADC]",
        col_avg, col_ch,
        f"Intercept vs Time  (N={batch_size})")

    axes[-1].set_xlabel(xlabel, fontsize=10)
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logging.info(f"  Saved: {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# CSV summary
# ─────────────────────────────────────────────────────────────────────────────

def save_summary_csv(all_batch_results: dict, output_path: str):
    """
    Save a CSV with one row per (batch_size, batch_index).

    all_batch_results: {N: (batch_times, [summary|None, ...])}
    """
    rows = []
    for N, (btimes, sums) in sorted(all_batch_results.items()):
        for bi, (t, s) in enumerate(zip(btimes, sums)):
            if s is None:
                continue
            rows.append({
                "model"      : "multigauss",
                "batch_size" : N,
                "batch_idx"  : bi,
                "time_s"     : float(t),
                "n_channels" : s["n_ch"],
                "mean_gain"  : s["mean_gain"],
                "std_gain"   : s["std_gain"],
                "err_gain"   : s["err_gain"],
                "mean_int"   : s["mean_int"],
                "std_int"    : s["std_int"],
                "err_int"    : s["err_int"],
            })

    if rows:
        pd.DataFrame(rows).to_csv(output_path, index=False)
        logging.info(f"Saved summary CSV: {output_path}")
    else:
        logging.warning("No valid batch results to write to CSV.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gain and intercept stability vs time (multigauss, ROOT)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  # Default (auto batch sizes based on n_files)
  python gain_vs_time.py /path/to/charge_dir/ output/ RUN1295

  # Specify duration per file (seconds)
  python gain_vs_time.py /path/to/charge_dir/ output/ RUN1295 \\
        --time-per-file 45

  # Explicit Unix timestamps (format: file_number  unix_ts)
  python gain_vs_time.py /path/to/charge_dir/ output/ RUN1295 \\
        --timestamps my_timestamps.txt

  # Raw histograms, limit workers
  python gain_vs_time.py /path/to/charge_dir/ output/ RUN1295 \\
        --use-raw --n-workers 4
""")

    parser.add_argument("charge_dir",  help="Directory containing CHARGE ROOT files")
    parser.add_argument("output_dir",  help="Output directory for plots and CSV")
    parser.add_argument("run_name",    help="Run label (used in plot titles)")

    parser.add_argument("--use-raw", action="store_true",
                        help="Use H_adcraw (non-vetoed) histograms instead of H_adcClean")
    parser.add_argument("--time-per-file", type=float, default=60.0,
                        help="Approx duration of one RTRAW file in seconds "
                             "(used when explicit timestamps not provided; default: 60)")
    parser.add_argument("--timestamps", default=None, metavar="FILE",
                        help="Text file with explicit timestamps: "
                             "'file_number unix_ts_seconds' per line")
    parser.add_argument("--n-workers", type=int,
                        default=max(1, min(8, cpu_count() - 1)),
                        help="Parallel worker processes (default: min(8, nCPU-1))")
    parser.add_argument("--gain-min", type=float, default=EXPECTED_GAIN_MIN,
                        help=f"Minimum valid gain [ADC/PE] (default: {EXPECTED_GAIN_MIN})")
    parser.add_argument("--gain-max", type=float, default=EXPECTED_GAIN_MAX,
                        help=f"Maximum valid gain [ADC/PE] (default: {EXPECTED_GAIN_MAX})")

    args = parser.parse_args()

    # ── Discover files ────────────────────────────────────────────────────────
    files = _discover_charge_files(args.charge_dir)
    if not files:
        logging.error(f"No CHARGE ROOT files found in {args.charge_dir}")
        sys.exit(1)
    n_files = len(files)
    logging.info(f"Found {n_files} CHARGE ROOT files in {args.charge_dir}")

    os.makedirs(args.output_dir, exist_ok=True)

    # ── Build time axis ───────────────────────────────────────────────────────
    ts_map = {}
    if args.timestamps:
        if not os.path.exists(args.timestamps):
            logging.error(f"Timestamps file not found: {args.timestamps}")
            sys.exit(1)
        ts_map = _load_timestamps(args.timestamps)
        logging.info(f"  Loaded {len(ts_map)} explicit timestamps")

    times = build_time_axis(files, args.time_per_file, ts_map)
    span  = times[-1] - times[0] if len(times) > 1 else 0
    dt_mean = span / (len(times) - 1) if len(times) > 1 else 0
    logging.info(f"  Time span: {times[0]:.0f} – {times[-1]:.0f} s "
                 f"(dt ~ {dt_mean:.1f} s/file)")

    # ── Adaptive batch sizes ─────────────────────────────────────────────────
    active_batches = get_batch_sizes(n_files)
    if not active_batches:
        logging.error("Not enough files for any batch size (need >= 2)")
        sys.exit(1)

    logging.info(f"  n_files = {n_files} -> batch sizes: {active_batches}")

    # ── Process each batch size ───────────────────────────────────────────────
    all_batch_results = {}

    for N in active_batches:
        n_batches = n_files // N
        logging.info(f"\nProcessing batch size N={N} "
                     f"({n_batches} batches x {N} file(s) each)...")
        btimes, sums = process_batches(
            files, times, N,
            use_raw=args.use_raw,
            n_workers=args.n_workers,
            gain_min=args.gain_min,
            gain_max=args.gain_max,
        )
        all_batch_results[N] = (btimes, sums)

        valid_n = sum(1 for s in sums if s is not None)
        logging.info(f"  {valid_n}/{n_batches} batches fitted successfully")

    # ── Generate plots ────────────────────────────────────────────────────────
    logging.info("\nGenerating plots...")

    for N, (btimes, sums) in sorted(all_batch_results.items()):
        if len(btimes) < 2:
            logging.info(f"  N={N}: not enough batches to plot – skipping")
            continue

        valid_n = sum(1 for s in sums if s is not None)
        if valid_n < 2:
            logging.info(f"  N={N}: < 2 valid batches – skipping plots")
            continue

        for variant, show_ch in [("avg", False), ("full", True)]:
            out_png = os.path.join(
                args.output_dir,
                f"gain_intercept_multigauss_N{N}_{variant}.png"
            )
            make_gain_vs_time_figure(
                btimes, sums, N,
                run_name=args.run_name,
                show_channels=show_ch,
                output_path=out_png,
            )

    # ── Save CSV summary ──────────────────────────────────────────────────────
    csv_path = os.path.join(args.output_dir, "gain_vs_time_summary.csv")
    save_summary_csv(all_batch_results, csv_path)

    logging.info(f"\nDone.  Output written to: {args.output_dir}")
    logging.info(f"  Batch sizes: {active_batches}")
    n_plots = sum(2 for N, (bt, _) in all_batch_results.items() if len(bt) >= 2)
    logging.info(f"  PNG files written (max): {n_plots}")


if __name__ == "__main__":
    main()
