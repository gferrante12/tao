#!/usr/bin/env python3
"""
gain_vs_time.py  –  Gain and intercept stability monitoring over time

Reads a directory of CHARGE ROOT files (output of extract_charge_calib.py),
fits each file (or merged batch) with the same custom-BFGS workflow as
gain_calibration.py, and produces gain / intercept vs time plots for ALL
five physics-motivated fit models defined in gain_fit_models.py.

Models
------
  multigauss      Plain multi-Gaussian (baseline)
  multigauss_ct   Multi-Gaussian + binomial optical crosstalk
  multigauss_ap   Multi-Gaussian + geometric afterpulse (SYSU/TAO)
  emg             Exponential Modified Gaussian (continuous CT tail)
  emg_ap          EMG peaks + geometric afterpulse (combined)

Three groupings
───────────────
  N=1  : fit each CHARGE file independently (always produced)
  N=10 : merge 10 consecutive files, then fit  (skipped if < 10 files)
  N=50 : merge 50 consecutive files, then fit  (skipped if < 50 files)

Two plot variants per grouping per model
────────────────────────────────────────
  a)  average only  – per-time-step mean ± error bar
  b)  average + per-channel – thin channel lines + thick average line

Panels per figure
─────────────────
  All models  : row 0 – Gain vs time
                row 1 – Intercept vs time
  multigauss_ct  : +row  – CT probability p_ct
  multigauss_ap  : +row  – AP probability α
                   +row  – Relative AP charge Q_ap/Gain
  emg            : +row  – CT probability τ/Gain
  emg_ap         : +row  – CT probability τ/Gain
                   +row  – AP probability α

Output files
────────────
  gain_intercept_{model}_N1_avg.png    per-model / N=1 average-only
  gain_intercept_{model}_N1_full.png   per-model / N=1 + per-channel
  gain_intercept_{model}_N10_avg.png   (if ≥ 10 files)
  ...
  gain_vs_time_summary.csv             per-batch mean/std for every model

Usage
─────
  python gain_vs_time.py /path/to/charge_files/ output_dir run_name
  python gain_vs_time.py /path/to/charge_files/ output_dir run_name \\
        --models multigauss,emg --use-raw --time-per-file 60 --n-workers 8
  python gain_vs_time.py /path/to/charge_files/ output_dir run_name \\
        --timestamps timestamps.txt

Author: G. Ferrante  (adapted from gain_calibration.py)

CHANGELOG
---------
BUG FIXES vs previous version:
  1. ImportError: 'BIN_CENTERS' → correct name is 'BIN_CTRS'
  2. ImportError: 'EXPECTED_GAIN_MIN/MAX' → 'GAIN_MIN_DEF/MAX_DEF'
  3. ImportError: 'LINEAR_R2_MIN' → 'R2_MIN'
  4. ImportError: 'process_channel_root' does not exist → use '_worker'
  5. _fit_one: bizarre `result_root, _ = (call(), None)` tuple syntax fixed
  6. summarise_results: accessed 'fit_status' → should be 'success'
  7. summarise_results: accessed 'linear_r2' → correct key is 'r2_linear'
  8. summarise_results: accessed 'channel_id' → ch_id is separate from result dict
  9. fit_histogram_dict: returned flat list incompatible with _worker's return type
  10. gain_calibration.py plot_fit residuals: np.isin(float_arr, float_arr) gives
      unreliable matches due to float equality; fixed with index-based lookup.

NEW FEATURES:
  - All 5 fit models produced independently (--models flag)
  - Per-model extra-physics panels (p_ct, alpha, q_ap_rel, tau/G)
  - --gain-min / --gain-max thresholds forwarded to _worker
  - --n-peaks / --coti flags forwarded to _worker
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
from tqdm import tqdm

# ── Import core fitting machinery from gain_calibration ──────────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

try:
    import gain_calibration as _gc
    from gain_calibration import (
        BIN_CTRS  as BIN_CENTERS,   # BUG-FIX 1: was 'BIN_CENTERS'
        BIN_WIDTH,
        GAIN_MIN_DEF as EXPECTED_GAIN_MIN,   # BUG-FIX 2
        GAIN_MAX_DEF as EXPECTED_GAIN_MAX,   # BUG-FIX 2
        CHI2_MAX,
        R2_MIN   as LINEAR_R2_MIN,  # BUG-FIX 3
        _worker  as _gain_worker,   # BUG-FIX 4: was 'process_channel_root'
        _WORKER_ARGS,
        classify,
    )
except ImportError as _e:
    print(f"ERROR: Could not import from gain_calibration.py: {_e}")
    print("       Make sure gain_calibration.py is in the same directory.")
    sys.exit(1)

try:
    from gain_fit_models import MODEL_NAMES, MODEL_LABELS
except ImportError as _e:
    print(f"ERROR: Could not import from gain_fit_models.py: {_e}")
    sys.exit(1)

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s: %(message)s")

# ── Model colours (consistent with gain_calibration.py) ──────────────────────
MODEL_COLORS = {
    'multigauss':    '#1f77b4',
    'multigauss_ct': '#9467bd',
    'multigauss_ap': '#ff7f0e',
    'emg':           '#2ca02c',
    'emg_ap':        '#d62728',
}
MODEL_COLORS_LIGHT = {
    'multigauss':    '#aec7e8',
    'multigauss_ct': '#c5b0d5',
    'multigauss_ap': '#ffbb78',
    'emg':           '#98df8a',
    'emg_ap':        '#f4a582',
}

# ── Extra physics panels per model ────────────────────────────────────────────
# Each entry: (extra_dict_key, summary_key_prefix, panel_ylabel, unit)
MODEL_EXTRA_PANELS = {
    'multigauss':    [],
    'multigauss_ct': [
        ('p_ct',     'p_ct',     'CT prob. p_ct',   ''),
    ],
    'multigauss_ap': [
        ('alpha',    'alpha',    'AP prob. α',       ''),
        ('q_ap_rel', 'q_ap_rel', 'Q_ap / Gain',      ''),
    ],
    'emg': [
        ('p_ct_emg', 'p_ct_emg', 'CT prob. τ/Gain',  ''),
    ],
    'emg_ap': [
        ('p_ct_emg', 'p_ct_emg', 'CT prob. τ/Gain',  ''),
        ('alpha',    'alpha',    'AP prob. α',        ''),
    ],
}

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

            arr = np.zeros(len(BIN_CENTERS))
            for i, bc in enumerate(BIN_CENTERS):
                b = h.FindBin(bc)
                if 1 <= b <= h.GetNbinsX():
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
    Calls gain_calibration._worker and returns (ch_id, model_results_dict).

    BUG-FIX 4+5: previously called non-existent 'process_channel_root' via
    a confusing 2-tuple unpacking idiom.
    """
    ch_id, hist = args
    ch_id_out, mres = _gain_worker((ch_id, hist))   # returns (ch_id, {model: result})
    return ch_id_out, mres


def fit_histogram_dict(hist_dict: dict, n_workers: int = 4) -> dict:
    """
    Fit all channels in hist_dict using all requested models.

    Returns {ch_id: {model_name: result_dict}} – same nested structure as
    gain_calibration.py's all_results.

    BUG-FIX 9: previously returned a flat list incompatible with _worker's
    actual (ch_id, {model: result}) return type.
    """
    items = list(hist_dict.items())
    all_results = {}
    with Pool(n_workers) as pool:
        for ch_id, mres in pool.imap(_fit_one, items, chunksize=8):
            all_results[ch_id] = mres
    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Per-batch summarisation — one summary dict per model
# ─────────────────────────────────────────────────────────────────────────────

def summarise_results_per_model(all_results: dict,
                                 models: list,
                                 gain_min: float,
                                 gain_max: float) -> dict:
    """
    From {ch_id: {model: result_dict}}, compute summary statistics for each
    requested model.

    Returns {model_name: summary_dict | None}

    Summary dict keys
    -----------------
    n_ch, mean_gain, std_gain, err_gain,
    mean_int,  std_int,  err_int,
    ch_ids, ch_gains, ch_ints,
    + model-specific physics parameter means/stds (see MODEL_EXTRA_PANELS).

    BUG-FIX 6: was accessing r['fit_status']  → correct key is r['success']
    BUG-FIX 7: was accessing r['linear_r2']   → correct key is r['r2_linear']
    BUG-FIX 8: was accessing r['channel_id']  → ch_id is the dict key, not in result
    """
    summaries = {}
    for mname in models:
        good_gains  = []
        good_ints   = []
        good_chids  = []
        extra_vals  = {ep[1]: [] for ep in MODEL_EXTRA_PANELS.get(mname, [])}

        for ch_id, mres in all_results.items():
            r = mres.get(mname, {})
            # BUG-FIX 6: r.get('success') not r['fit_status']
            if not r.get('success', False):
                continue
            # BUG-FIX 7: r['r2_linear'] not r['linear_r2']
            if not (CHI2_MAX >= r.get('chi2_dof', -1) >= 0):
                continue
            if r.get('r2_linear', 0.0) < LINEAR_R2_MIN:
                continue
            gain_val = r.get('gain', 0.0)
            if not (gain_min <= gain_val <= gain_max):
                continue

            # BUG-FIX 8: use loop variable ch_id, not r['channel_id']
            good_gains.append(gain_val)
            good_ints.append(r.get('intercept', np.nan))
            good_chids.append(ch_id)

            # Collect model-specific physics parameters
            extra = r.get('extra', {})
            for ext_key, sum_key, *_ in MODEL_EXTRA_PANELS.get(mname, []):
                v = extra.get(ext_key, np.nan)
                extra_vals[sum_key].append(v)

        if not good_gains:
            summaries[mname] = None
            continue

        gains = np.array(good_gains)
        ints  = np.array(good_ints)
        chids = np.array(good_chids)
        n     = len(gains)

        s = {
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

        # Add per-model physics parameters
        for ext_key, sum_key, *_ in MODEL_EXTRA_PANELS.get(mname, []):
            vals = np.array([v for v in extra_vals[sum_key]
                             if np.isfinite(v)])
            if len(vals) > 0:
                s[f"mean_{sum_key}"] = float(vals.mean())
                s[f"std_{sum_key}"]  = float(vals.std())
                s[f"err_{sum_key}"]  = float(vals.std() / np.sqrt(len(vals)))
                s[f"ch_{sum_key}"]   = vals
            else:
                s[f"mean_{sum_key}"] = np.nan
                s[f"std_{sum_key}"]  = np.nan
                s[f"err_{sum_key}"]  = np.nan
                s[f"ch_{sum_key}"]   = np.array([])

        summaries[mname] = s

    return summaries


# ─────────────────────────────────────────────────────────────────────────────
# Batch processing
# ─────────────────────────────────────────────────────────────────────────────

def process_batches(files: list, times: np.ndarray,
                    batch_size: int, use_raw: bool,
                    n_workers: int, models: list,
                    gain_min: float, gain_max: float) -> tuple:
    """
    Merge files in groups of batch_size, fit each group, summarise per model.

    Returns
    -------
    (batch_times, per_model_summaries)
      batch_times          – 1-D array of representative times (batch midpoint)
      per_model_summaries  – {model_name: [summary_dict | None, ...]}
    """
    n_files   = len(files)
    n_batches = n_files // batch_size
    if n_batches == 0:
        return np.array([]), {m: [] for m in models}

    batch_times         = []
    per_model_summaries = {m: [] for m in models}

    for b in tqdm(range(n_batches), desc=f"  Batches N={batch_size}"):
        idx_lo      = b * batch_size
        idx_hi      = idx_lo + batch_size
        batch_files = files[idx_lo:idx_hi]
        batch_t     = float(times[idx_lo:idx_hi].mean())

        hist_list = [load_histograms(fp, use_raw) for fp in batch_files]
        merged    = merge_histogram_dicts(hist_list)

        all_results = fit_histogram_dict(merged, n_workers)
        model_sums  = summarise_results_per_model(all_results, models,
                                                   gain_min, gain_max)

        batch_times.append(batch_t)
        for m in models:
            per_model_summaries[m].append(model_sums[m])

    return np.array(batch_times), per_model_summaries


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
    return (f"⟨{label}⟩ = {mean:.4g}\n"
            f"σ = {std:.4g}")


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
    Draw one time-series panel (gain, intercept, or physics parameter).

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
    Build a (n_batches × n_channels) matrix for a per-channel array key
    from a list of summary dicts.  NaN-pads missing channels.
    """
    # Collect all ch arrays (may differ in length between batches)
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
                              model_name: str,
                              run_name: str,
                              show_channels: bool,
                              output_path: str):
    """
    Build and save a multi-row figure for one model:
      row 0  – Gain vs time
      row 1  – Intercept vs time
      row 2+ – Model-specific physics parameters (if any)

    Parameters
    ----------
    batch_times  : time of each batch (seconds)
    summaries    : list of per-model summary dicts (None = failed batch)
    batch_size   : N  (for title label)
    model_name   : model identifier
    run_name     : RUN label
    show_channels: True → also draw thin per-channel lines
    output_path  : output PNG path
    """
    valid_mask = np.array([s is not None for s in summaries])
    if valid_mask.sum() < 2:
        logging.warning(f"  [{model_name}] N={batch_size}: < 2 valid batches – skipping.")
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

    extra_panels = MODEL_EXTRA_PANELS.get(model_name, [])
    n_rows  = 2 + len(extra_panels)
    col_avg = MODEL_COLORS.get(model_name, "#1f77b4")
    col_ch  = MODEL_COLORS_LIGHT.get(model_name, "#aec7e8")

    # Per-channel matrices
    if show_channels:
        mat_g = _build_channel_matrix(sums_ok, "ch_gains")
        mat_i = _build_channel_matrix(sums_ok, "ch_ints")
    else:
        mat_g = mat_i = None

    variant_lbl = "avg+channels" if show_channels else "avg"
    fig, axes = plt.subplots(n_rows, 1, figsize=(12, 4 * n_rows), sharex=True)
    if n_rows == 1:
        axes = [axes]

    model_lbl = MODEL_LABELS.get(model_name, model_name)
    fig.suptitle(f"Gain & Parameters vs Time  |  {run_name}  "
                 f"|  {model_lbl}  |  N={batch_size}  |  {variant_lbl}",
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

    # Extra physics-parameter panels
    for row_idx, (ext_key, sum_key, panel_ylabel, unit) in enumerate(extra_panels, start=2):
        vals_mean = np.array([s.get(f"mean_{sum_key}", np.nan) for s in sums_ok])
        vals_err  = np.array([s.get(f"err_{sum_key}",  np.nan) for s in sums_ok])
        t_mean_ep = float(np.nanmean(vals_mean))
        t_std_ep  = float(np.nanstd(vals_mean))

        if show_channels:
            mat_ep = _build_channel_matrix(sums_ok, f"ch_{sum_key}")
        else:
            mat_ep = None

        y_lbl = f"{panel_ylabel} [{unit}]" if unit else panel_ylabel
        _make_panel(
            axes[row_idx], dt_r, vals_mean, vals_err, mat_ep,
            t_mean_ep, t_std_ep, show_channels,
            y_lbl,
            col_avg, col_ch,
            f"{panel_ylabel} vs Time  (N={batch_size})")

    axes[-1].set_xlabel(xlabel, fontsize=10)
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logging.info(f"  Saved: {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# CSV summary
# ─────────────────────────────────────────────────────────────────────────────

def save_summary_csv(all_batch_results: dict, models: list, output_path: str):
    """
    Save a CSV with one row per (model, batch_size, batch_index).

    all_batch_results: {N: (batch_times, {model: [summary|None, ...]})}
    """
    rows = []
    for N, (btimes, per_model_sums) in sorted(all_batch_results.items()):
        for mname in models:
            sums = per_model_sums.get(mname, [])
            for bi, (t, s) in enumerate(zip(btimes, sums)):
                if s is None:
                    continue
                row = {
                    "model"      : mname,
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
                }
                # Append model-specific physics parameter columns
                for _, sum_key, panel_ylabel, _ in MODEL_EXTRA_PANELS.get(mname, []):
                    row[f"mean_{sum_key}"] = s.get(f"mean_{sum_key}", np.nan)
                    row[f"std_{sum_key}"]  = s.get(f"std_{sum_key}",  np.nan)
                    row[f"err_{sum_key}"]  = s.get(f"err_{sum_key}",  np.nan)
                rows.append(row)

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
        description="Gain and parameter stability vs time – all fit models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  # All 5 models, default time axis (file_idx × 60 s)
  python gain_vs_time.py /path/to/charge_dir/ output/ RUN1295

  # Select specific models
  python gain_vs_time.py /path/to/charge_dir/ output/ RUN1295 \\
        --models multigauss,multigauss_ct,emg

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

    parser.add_argument("--models", default="all",
                        help=f"Comma-separated model list or 'all' "
                             f"[default: all]. Choices: {','.join(MODEL_NAMES)}")
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
    parser.add_argument("--n-peaks", type=int, default=None,
                        help="Force fixed number of PE peaks [default: auto 2–8]")
    parser.add_argument("--coti", action="store_true",
                        help="Apply COTI threshold erf correction to 1PE peak")

    args = parser.parse_args()

    # ── Model selection ───────────────────────────────────────────────────────
    if args.models == "all":
        models = list(MODEL_NAMES)
    else:
        models = [m.strip() for m in args.models.split(",")]
        bad = [m for m in models if m not in MODEL_NAMES]
        if bad:
            logging.error(f"Unknown model(s): {bad}. Valid: {list(MODEL_NAMES)}")
            sys.exit(1)
    logging.info(f"Models: {models}")

    # ── Inject global worker config BEFORE creating the Pool (fork-safe) ──────
    _WORKER_ARGS.update(
        models=models,
        n_peaks_forced=args.n_peaks,
        apply_coti=args.coti,
        gain_min=args.gain_min,
        gain_max=args.gain_max,
    )

    # ── Discover files ────────────────────────────────────────────────────────
    files = _discover_charge_files(args.charge_dir)
    if not files:
        logging.error(f"No CHARGE ROOT files found in {args.charge_dir}")
        sys.exit(1)
    logging.info(f"Found {len(files)} CHARGE ROOT files in {args.charge_dir}")

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
                 f"(Δt ≈ {dt_mean:.1f} s/file)")

    # ── Define batch sizes ────────────────────────────────────────────────────
    BATCH_SIZES = [1, 10, 50]
    active_batches = sorted(N for N in BATCH_SIZES if len(files) >= N)
    if len(files) < 10:
        logging.info("  < 10 files: only N=1 grouping will be produced")
    elif len(files) < 50:
        logging.info("  < 50 files: N=50 grouping skipped")

    # ── Process each batch size ───────────────────────────────────────────────
    all_batch_results = {}

    for N in active_batches:
        n_batches = len(files) // N
        logging.info(f"\nProcessing batch size N={N} "
                     f"({n_batches} batches × {N} file(s) each)…")
        btimes, per_model_sums = process_batches(
            files, times, N,
            use_raw=args.use_raw,
            n_workers=args.n_workers,
            models=models,
            gain_min=args.gain_min,
            gain_max=args.gain_max,
        )
        all_batch_results[N] = (btimes, per_model_sums)

        for m in models:
            valid_n = sum(1 for s in per_model_sums[m] if s is not None)
            logging.info(f"  [{m}] {valid_n}/{n_batches} batches fitted successfully")

    # ── Generate plots ────────────────────────────────────────────────────────
    logging.info("\nGenerating plots…")

    for N, (btimes, per_model_sums) in sorted(all_batch_results.items()):
        if len(btimes) < 2:
            logging.info(f"  N={N}: not enough batches to plot – skipping")
            continue

        for mname in models:
            sums = per_model_sums[mname]
            valid_n = sum(1 for s in sums if s is not None)
            if valid_n < 2:
                logging.info(f"  [{mname}] N={N}: < 2 valid batches – skipping plots")
                continue

            for variant, show_ch in [("avg", False), ("full", True)]:
                out_png = os.path.join(
                    args.output_dir,
                    f"gain_intercept_{mname}_N{N}_{variant}.png"
                )
                make_gain_vs_time_figure(
                    btimes, sums, N,
                    model_name=mname,
                    run_name=args.run_name,
                    show_channels=show_ch,
                    output_path=out_png,
                )

    # ── Save CSV summary ──────────────────────────────────────────────────────
    csv_path = os.path.join(args.output_dir, "gain_vs_time_summary.csv")
    save_summary_csv(all_batch_results, models, csv_path)

    logging.info(f"\nDone.  Output written to: {args.output_dir}")
    logging.info(f"  Models processed: {models}")
    logging.info(f"  Batch sizes: {active_batches}")
    expected_plots = (len(models) * len(active_batches) *
                      2 * sum(1 for N, (bt, _) in all_batch_results.items()
                              if len(bt) >= 2))
    logging.info(f"  PNG files written (max): {len(models) * len(active_batches) * 2}")


if __name__ == "__main__":
    main()
