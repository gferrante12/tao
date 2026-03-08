#!/usr/bin/env python3
"""
gain_calibration_v3.py
======================
TAO SiPM gain calibration pipeline — plotting, I/O, summary statistics.
No scipy, no ROOT TSpectrum.  Minimization via custom BFGS in gain_fit_models.py

Usage
-----
python gain_calibration_v3.py input.root output_dir run_name [options]

Options
  --use-raw          Use raw (non-vetoed) histograms [default: clean]
  --plots {none,sample,all}
                     none   : skip per-channel plots
                     sample : 50 random per category [default]
                     all    : every channel
  --models M1,M2,…  Comma-separated model list [default: all 5]
                     Choices: multigauss multigauss_ct multigauss_ap emg emg_ap
  --n-peaks INT      Force fixed number of PE peaks [default: auto 2–8]
  --workers INT      Parallel worker processes [default: CPU count]
  --gain-min FLOAT   Minimum gain for "good" [default: 3200]
  --gain-max FLOAT   Maximum gain for "good" [default: 8500]
  --coti             Apply COTI threshold erf correction to 1PE peak

Output (inside output_dir/)
  {run}_multigauss_good.csv  / bad.csv / failed.csv
  {run}_multigauss_ct_good.csv  ...  (one set per model)
  plots/good/{model}/ch_XXXXX_fit.png   + ch_XXXXX_linear.png
  plots/bad/{model}/...
  plots/failed/{model}/...
  summary_{run}.txt

Classification
  good   : GAIN_MIN ≤ gain ≤ GAIN_MAX  AND  chi²/ndf ≤ CHI2_MAX  AND  R² ≥ R2_MIN
  bad    : fit converged but outside good criteria
  failed : fit did not converge (f_min > 1e14 or no peaks found)
"""

import argparse
import logging
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from multiprocessing import Pool, cpu_count

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kw):
        desc = kw.get('desc', '')
        items = list(iterable)
        n = len(items)
        for i, x in enumerate(items):
            if i % max(1, n // 20) == 0:
                log.info(f'{desc}: {i}/{n}')
            yield x

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gain_fit_models import (
    MODEL_NAMES, MODEL_LABELS, fit_channel, eval_model,
    linear_fit_gain, peak_mu
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# ── Histogram grid (matches extract_charge_calib.py output) ──────────────────
BIN_WIDTH = 100
BIN_MAX   = 50_000
BINS      = np.arange(0, BIN_MAX + BIN_WIDTH, BIN_WIDTH)
BIN_CTRS  = (BINS[:-1] + BINS[1:]) / 2.0
N_BINS    = len(BIN_CTRS)

# ── Fit-quality thresholds ────────────────────────────────────────────────────
CHI2_MAX       = 15.0
R2_MIN         = 0.90
GAIN_MIN_DEF   = 3_200
GAIN_MAX_DEF   = 8_500
GAIN_DEFAULT   = 6_000
MIN_ENTRIES    = 2_000
SAMPLE_N       = 50    # plots per category when --plots sample

MODEL_COLORS = {
    'multigauss':    '#1f77b4',
    'multigauss_ct': '#9467bd',
    'multigauss_ap': '#ff7f0e',
    'emg':           '#2ca02c',
    'emg_ap':        '#d62728',
}


# =============================================================================
# PEAK DETECTION  (no TSpectrum / scipy)
# =============================================================================

def _gauss_kernel(half_width, sigma_bins):
    k = np.arange(-half_width, half_width + 1, dtype=float)
    w = np.exp(-0.5 * (k / sigma_bins)**2)
    return w / w.sum()

def smooth_hist(hist, sigma_bins=3.0):
    """Gaussian kernel smoothing with edge padding."""
    hw     = max(1, int(3.5 * sigma_bins))
    kernel = _gauss_kernel(hw, sigma_bins)
    padded = np.pad(hist.astype(float), hw, mode='edge')
    return np.convolve(padded, kernel, mode='valid')[:len(hist)]

def local_maxima(arr, min_dist):
    """Local maxima separated by at least min_dist bins."""
    cands = [i for i in range(1, len(arr)-1)
             if arr[i] > arr[i-1] and arr[i] > arr[i+1]]
    if not cands:
        return []
    sel = [cands[0]]
    for idx in cands[1:]:
        if idx - sel[-1] >= min_dist:
            sel.append(idx)
        elif arr[idx] > arr[sel[-1]]:
            sel[-1] = idx
    return sel

def detect_peaks(hist, gain_est=GAIN_DEFAULT):
    """
    Detect PE peaks in ADC histogram without TSpectrum.

    Algorithm
    ---------
    1. Gaussian smooth (σ ≈ gain/10 bins).
    2. Find all local maxima with minimum separation = 0.5·gain.
    3. Prominence filter: height above surrounding minimum > 0.5% of max.
    4. Keep only peaks whose spacing from the previous peak lies in [0.5g, 1.5g].
    5. Enforce roughly decreasing heights (20% tolerance).
    6. Return up to 8 peaks.
    """
    if np.sum(hist) < MIN_ENTRIES:
        return []

    sigma_s  = max(1.0, gain_est / BIN_WIDTH / 10.0)
    min_sep  = max(2, int(0.5 * gain_est / BIN_WIDTH))
    smoothed = smooth_hist(hist, sigma_s)
    idxs     = local_maxima(smoothed, min_sep)
    if len(idxs) < 2:
        return []

    # Prominence
    win = max(2, int(2.0 * gain_est / BIN_WIDTH))
    proms = []
    for i in idxs:
        lo = max(0, i-win); hi = min(len(smoothed), i+win+1)
        bg = min(smoothed[lo:i].min() if i > lo else smoothed[i],
                 smoothed[i+1:hi].min() if i+1 < hi else smoothed[i])
        proms.append(smoothed[i] - bg)
    min_prom = max(max(proms) * 0.005, 3.0)
    idxs     = [i for i, p in zip(idxs, proms) if p >= min_prom]
    if len(idxs) < 2:
        return []

    peaks = sorted(float(BIN_CTRS[i]) for i in idxs)

    # First peak range
    cands = [p for p in peaks if gain_est/3 <= p <= gain_est*3] or \
            [p for p in peaks if 300 <= p <= 25_000]
    if not cands:
        return []
    # tallest among candidates
    h0 = [hist[int(np.argmin(np.abs(BIN_CTRS - p)))] for p in cands]
    fp = cands[int(np.argmax(h0))]

    # Build chain
    chain = [fp]
    for p in peaks:
        if p <= fp:
            continue
        sp = p - chain[-1]
        if 0.5*gain_est <= sp <= 1.5*gain_est:
            chain.append(p)
        if len(chain) >= 8:
            break

    # Monotone-decreasing heights
    heights = [hist[int(np.argmin(np.abs(BIN_CTRS - p)))] for p in chain]
    cut = len(chain)
    for i in range(len(heights)-1):
        if heights[i+1] > heights[i] * 1.20:
            cut = i+1; break
    chain = chain[:cut]
    return chain if len(chain) >= 2 else []


# =============================================================================
# ROOT HISTOGRAM READER
# =============================================================================

def load_histograms(root_file, use_raw=False):
    """
    Read per-channel ADC histograms produced by extract_charge_calib.py.
    Tries uproot first, falls back to PyROOT.
    Returns {channel_id: hist_array(N_BINS)}.
    """
    prefix = 'H_adc' + ('raw' if use_raw else 'Clean') + '_'
    histograms = {}

    # ── uproot path ──────────────────────────────────────────────────────────
    try:
        import uproot
        with uproot.open(root_file) as f:
            for key in f.keys():
                name = key.split(';')[0]
                if not name.startswith(prefix):
                    continue
                try:
                    ch_id = int(name[len(prefix):])
                except ValueError:
                    continue
                h = f[key]
                vals, edges = h.to_numpy()
                ctrs = 0.5 * (edges[:-1] + edges[1:])
                out  = np.zeros(N_BINS, dtype=float)
                for c, v in zip(ctrs, vals):
                    bi = int(np.argmin(np.abs(BIN_CTRS - c)))
                    out[bi] += v
                histograms[ch_id] = out
        log.info(f"[uproot] Loaded {len(histograms)} histograms from {root_file}")
        return histograms
    except ImportError:
        pass
    except Exception as exc:
        log.warning(f"uproot failed ({exc}), trying PyROOT…")

    # ── PyROOT fallback ──────────────────────────────────────────────────────
    try:
        import ROOT
        ROOT.gROOT.SetBatch(True)
        f = ROOT.TFile.Open(root_file, 'READ')
        if not f or f.IsZombie():
            raise IOError(f"Cannot open {root_file}")
        for key in f.GetListOfKeys():
            name = key.GetName()
            if not name.startswith(prefix):
                continue
            try:
                ch_id = int(name[len(prefix):])
            except ValueError:
                continue
            h   = f.Get(name)
            if not h:
                continue
            nb  = h.GetNbinsX()
            ctrs_ = np.array([h.GetBinCenter(b) for b in range(1, nb+1)])
            vals_ = np.array([h.GetBinContent(b) for b in range(1, nb+1)])
            out   = np.zeros(N_BINS, dtype=float)
            for c, v in zip(ctrs_, vals_):
                bi = int(np.argmin(np.abs(BIN_CTRS - c)))
                out[bi] += v
            histograms[ch_id] = out
        f.Close()
        log.info(f"[PyROOT] Loaded {len(histograms)} histograms from {root_file}")
        return histograms
    except ImportError:
        raise RuntimeError("Neither uproot nor PyROOT available.")


# =============================================================================
# PER-CHANNEL FIT WORKER  (called in parallel)
# =============================================================================

_WORKER_ARGS = {}   # global config injected before Pool

def _worker(args):
    """Multiprocessing worker: fit all models for one channel."""
    ch_id, hist = args
    models      = _WORKER_ARGS['models']
    n_pk_forced = _WORKER_ARGS['n_peaks_forced']
    apply_coti  = _WORKER_ARGS['apply_coti']
    gain_min    = _WORKER_ARGS['gain_min']
    gain_max    = _WORKER_ARGS['gain_max']

    EMPTY = {m: dict(success=False, gain=0.0, gain_err=np.inf,
                     chi2_dof=-1.0, r2_linear=0.0, n_peaks=0,
                     y_fit=None, extra={}, _par_fit={}, _x_data=None,
                     param_names=[], popt=None)
             for m in models}

    if np.sum(hist) < MIN_ENTRIES:
        return ch_id, EMPTY

    # ── Peak detection ────────────────────────────────────────────────────────
    gain_est = float(np.clip(GAIN_DEFAULT, gain_min, gain_max))
    peaks    = detect_peaks(hist, gain_est=gain_est)
    if len(peaks) < 2:
        return ch_id, EMPTY

    spacings = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
    gain_est = float(np.clip(np.median(spacings), gain_min, gain_max))
    n_peaks  = int(np.clip(n_pk_forced if n_pk_forced else len(peaks), 2, 8))
    peaks_fit = peaks[:n_peaks]

    # ── Fit window ────────────────────────────────────────────────────────────
    # Left margin: 0.5×gain is enough to capture the 1PE left tail without
    # pulling in the pedestal (which sits well below the first PE peak and
    # is not modelled by any of the fit functions).
    # Right margin: 1.2×gain to capture the right tail / last-peak shoulder.
    fit_min  = max(peaks_fit[0] - 0.5 * gain_est, BIN_CTRS[0])
    fit_max  = peaks_fit[-1] + 1.2 * gain_est
    mask     = (BIN_CTRS >= fit_min) & (BIN_CTRS <= fit_max)
    x_fit    = BIN_CTRS[mask]
    y_fit    = hist[mask]

    if len(x_fit) < 5 or np.sum(y_fit) < 100:
        return ch_id, EMPTY

    results = {}
    for mname in models:
        results[mname] = fit_channel(
            x_fit, y_fit, n_peaks, peaks_fit, gain_est,
            mname, apply_coti=apply_coti)

    return ch_id, results


# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify(r, gain_min, gain_max):
    """Return 'good', 'bad', or 'failed' for a fit result dict."""
    if not r.get('success') or r['gain'] <= 0:
        return 'failed'
    g = r['gain']
    if (gain_min <= g <= gain_max and
            r['chi2_dof'] <= CHI2_MAX and
            r['r2_linear'] >= R2_MIN):
        return 'good'
    return 'bad'


# =============================================================================
# PLOTTING
# =============================================================================

def _make_plot_dirs(out_dir, models):
    dirs = {}
    for cat in ('good', 'bad', 'failed'):
        for m in models:
            p = os.path.join(out_dir, 'plots', cat, m)
            os.makedirs(p, exist_ok=True)
            dirs[(cat, m)] = p
    return dirs


def plot_fit(ch_id, hist, model_results, detected_peaks,
             plot_dirs, gain_min, gain_max):
    """
    Save two PNG files per model per channel:
      ch_XXXXX_fit.png    — ADC histogram + model curve + residuals
      ch_XXXXX_linear.png — μ_n vs n with linear fit (gain extraction)
    """
    for mname, r in model_results.items():
        cat = classify(r, gain_min, gain_max)
        base = os.path.join(plot_dirs[(cat, mname)], f'ch_{ch_id:05d}')

        # ── Fit plot ─────────────────────────────────────────────────────────
        fig, (ax, ax_res) = plt.subplots(
            2, 1, figsize=(10, 7),
            gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
        fig.suptitle(f'Channel {ch_id}  |  {MODEL_LABELS[mname]}', fontsize=12)

        # Full histogram (bar)
        ax.bar(BIN_CTRS, hist, width=BIN_WIDTH*0.9,
               color='steelblue', alpha=0.35, label='Data', zorder=1)
        ax.set_yscale('log')
        ax.set_ylabel('Counts'); ax.set_xlim(0, BIN_MAX)

        # Detected peaks
        for p in detected_peaks:
            ax.axvline(p, color='grey', lw=0.7, ls=':', alpha=0.5)

        if r.get('success') and r.get('y_fit') is not None:
            x_d = r.get('_x_data')
            y_m = r['y_fit']
            if x_d is not None and len(x_d) == len(y_m):
                col = MODEL_COLORS.get(mname, 'red')
                lbl = (f"{MODEL_LABELS[mname]}\n"
                       f"Gain={r['gain']:.0f}±{r['gain_err']:.0f} ADC/PE\n"
                       f"χ²/ndf={r['chi2_dof']:.2f}  R²={r['r2_linear']:.3f}")
                ax.plot(x_d, y_m, color=col, lw=1.8, label=lbl, zorder=3)

                # Afterpulse / CT sub-peaks annotation
                pf = r.get('_par_fit', {})
                if 'q_ap' in pf and 'alpha' in pf:
                    ax.annotate(f"Q_ap={pf['q_ap']:.0f} α={pf['alpha']:.3f}",
                                xy=(0.65, 0.85), xycoords='axes fraction', fontsize=8)
                if 'p_ct' in pf:
                    ax.annotate(f"p_ct={pf['p_ct']:.3f}",
                                xy=(0.65, 0.80), xycoords='axes fraction', fontsize=8)
                if 'tau' in pf:
                    p_ct_emg = pf.get('tau', 0) / r['gain'] if r['gain'] > 0 else 0
                    ax.annotate(f"τ={pf['tau']:.0f}  p_ct≈{p_ct_emg:.3f}",
                                xy=(0.65, 0.75), xycoords='axes fraction', fontsize=8)

                # Residuals — rebuild fit-window mask from bounds (np.isin fails on floats)
                fit_mask = (BIN_CTRS >= x_d[0]) & (BIN_CTRS <= x_d[-1])
                y_data_w = hist[fit_mask]
                if len(y_data_w) == len(y_m):
                    res = y_data_w - y_m
                    ax_res.bar(x_d, res, width=BIN_WIDTH*0.9,
                               color=col, alpha=0.5)
                    ax_res.axhline(0, color='k', lw=0.8)
        else:
            ax.text(0.5, 0.5, 'FIT FAILED', transform=ax.transAxes,
                    ha='center', va='center', color='red', fontsize=14)

        ax.legend(fontsize=8, loc='upper right')
        ax_res.set_xlabel('ADC [counts]')
        ax_res.set_ylabel('Residual')
        plt.tight_layout()
        plt.savefig(base + '_fit.png', dpi=100)
        plt.close(fig)

        # ── Linear gain plot ──────────────────────────────────────────────────
        if r.get('success') and r['n_peaks'] >= 2:
            fig2, ax2 = plt.subplots(figsize=(6, 5))
            mu1_f  = r.get('_par_fit', {}).get('mu1', 0.0)
            gain_f = r.get('_par_fit', {}).get('gain', r['gain'])
            n_pk   = r['n_peaks']
            ns_arr = np.arange(1, n_pk+1)
            mu_arr = np.array([peak_mu(int(ni), mu1_f, gain_f) for ni in ns_arr])

            ax2.scatter(ns_arr, mu_arr, color='navy', zorder=3, label='Peak means')
            # Linear fit line
            x_line = np.linspace(0.5, n_pk + 0.5, 100)
            y_line = r['intercept'] + r['gain'] * x_line
            ax2.plot(x_line, y_line, 'r-',
                     label=(f"Gain={r['gain']:.1f}±{r['gain_err']:.1f} ADC/PE\n"
                            f"Intercept={r['intercept']:.1f}  R²={r['r2_linear']:.4f}"))
            ax2.set_xlabel('PE peak number n')
            ax2.set_ylabel('μ_n [ADC]')
            ax2.set_title(f'Ch {ch_id}  {MODEL_LABELS[mname]} — Gain extraction')
            ax2.legend(fontsize=9)
            plt.tight_layout()
            plt.savefig(base + '_linear.png', dpi=100)
            plt.close(fig2)


# =============================================================================
# CSV BUILDER
# =============================================================================

RESULT_COLS = [
    'channel_id', 'n_peaks', 'gain', 'gain_err',
    'intercept', 'intercept_err', 'chi2_dof', 'r2_linear',
    'sigma_pe', 'sigma_base',
    'tau', 'tau_err', 'p_ct_emg',
    'p_ct', 'p_ct_err',
    'q_ap', 'q_ap_rel', 'alpha', 'alpha_err',
]

def result_to_row(ch_id, r):
    extra = r.get('extra', {})
    return {
        'channel_id':   ch_id,
        'n_peaks':      r.get('n_peaks', 0),
        'gain':         r.get('gain', np.nan),
        'gain_err':     r.get('gain_err', np.nan),
        'intercept':    r.get('intercept', np.nan),
        'intercept_err': r.get('intercept_err', np.nan),
        'chi2_dof':     r.get('chi2_dof', np.nan),
        'r2_linear':    r.get('r2_linear', np.nan),
        'sigma_pe':     extra.get('sigma_pe',   np.nan),
        'sigma_base':   extra.get('sigma_base', np.nan),
        'tau':          extra.get('tau',         np.nan),
        'tau_err':      extra.get('tau_err',     np.nan),
        'p_ct_emg':     extra.get('p_ct_emg',   np.nan),
        'p_ct':         extra.get('p_ct',        np.nan),
        'p_ct_err':     extra.get('p_ct_err',   np.nan),
        'q_ap':         extra.get('q_ap',        np.nan),
        'q_ap_rel':     extra.get('q_ap_rel',   np.nan),
        'alpha':        extra.get('alpha',       np.nan),
        'alpha_err':    extra.get('alpha_err',   np.nan),
    }


def save_csvs(all_results, models, out_dir, run_name, gain_min, gain_max):
    """Write good/bad/failed CSV files for each model."""
    csv_paths = {}
    for mname in models:
        rows = defaultdict(list)
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max)
            rows[cat].append(result_to_row(ch_id, r))

        for cat in ('good', 'bad', 'failed'):
            fname = os.path.join(out_dir, f'{run_name}_{mname}_{cat}.csv')
            pd.DataFrame(rows[cat], columns=RESULT_COLS).to_csv(fname, index=False)
            csv_paths[(mname, cat)] = fname
            log.info(f"  → {fname}  ({len(rows[cat])} channels)")
    return csv_paths


# =============================================================================
# SUMMARY TXT
# =============================================================================

def _stats(arr):
    a = np.array([x for x in arr if np.isfinite(x)])
    if len(a) == 0:
        return dict(n=0, mean=np.nan, std=np.nan, median=np.nan,
                    p16=np.nan, p84=np.nan, p5=np.nan, p95=np.nan)
    return dict(n=len(a), mean=float(np.mean(a)), std=float(np.std(a)),
                median=float(np.median(a)),
                p16=float(np.percentile(a, 16)), p84=float(np.percentile(a, 84)),
                p5=float(np.percentile(a,  5)), p95=float(np.percentile(a, 95)))

def write_summary(all_results, models, out_dir, run_name, gain_min, gain_max):
    """Write summary_{run_name}.txt with statistics per model."""
    fname = os.path.join(out_dir, f'summary_{run_name}.txt')
    lines = []
    W     = 78

    def hdr(s):
        lines.append('=' * W)
        lines.append(f'  {s}')
        lines.append('=' * W)
    def sub(s):
        lines.append('-' * W)
        lines.append(f'  {s}')
        lines.append('-' * W)
    def fmt_stats(label, s):
        lines.append(
            f"    {label:<20s}  n={s['n']:5d}  "
            f"mean={s['mean']:10.3f}  std={s['std']:9.3f}  "
            f"median={s['median']:10.3f}  "
            f"[{s['p16']:.3f}, {s['p84']:.3f}] (68%)")

    hdr(f'TAO GAIN CALIBRATION SUMMARY')
    lines.append(f'  Run: {run_name}')
    lines.append(f'  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'  Gain classification: [{gain_min:.0f}, {gain_max:.0f}] ADC/PE')
    lines.append(f'  Quality cuts: chi2/ndf ≤ {CHI2_MAX}  R² ≥ {R2_MIN}')
    lines.append(f'  Total channels: {len(all_results)}')
    lines.append('')

    for mname in models:
        sub(f'MODEL: {MODEL_LABELS[mname]}  ({mname})')

        cats = {'good': [], 'bad': [], 'failed': []}
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max)
            cats[cat].append(r)

        ng, nb, nf = len(cats['good']), len(cats['bad']), len(cats['failed'])
        tot = ng + nb + nf
        lines.append(f'  Channels:  good={ng} ({100*ng/tot:.1f}%)  '
                     f'bad={nb} ({100*nb/tot:.1f}%)  '
                     f'failed={nf} ({100*nf/tot:.1f}%)  '
                     f'total={tot}')
        lines.append('')

        for catname, rlist in [('GOOD', cats['good']), ('BAD', cats['bad'])]:
            if not rlist:
                continue
            lines.append(f'  ── {catname} channels ({len(rlist)}) ──')
            gains    = [r.get('gain',     np.nan) for r in rlist]
            chi2s    = [r.get('chi2_dof', np.nan) for r in rlist]
            r2s      = [r.get('r2_linear',np.nan) for r in rlist]
            fmt_stats('Gain [ADC/PE]', _stats(gains))
            fmt_stats('chi2/ndf',       _stats(chi2s))
            fmt_stats('R² (linear)',    _stats(r2s))

            # Model-specific physics parameters
            if mname in ('emg', 'emg_ap'):
                taus  = [r.get('extra', {}).get('tau',     np.nan) for r in rlist]
                pcts  = [r.get('extra', {}).get('p_ct_emg',np.nan) for r in rlist]
                fmt_stats('τ [ADC]',     _stats(taus))
                fmt_stats('p_ct (τ/G)',  _stats(pcts))
            if mname == 'multigauss_ct':
                pcts  = [r.get('extra', {}).get('p_ct',    np.nan) for r in rlist]
                fmt_stats('p_ct (binom)', _stats(pcts))
            if mname in ('multigauss_ap', 'emg_ap'):
                alphs = [r.get('extra', {}).get('alpha',   np.nan) for r in rlist]
                qaps  = [r.get('extra', {}).get('q_ap_rel',np.nan) for r in rlist]
                fmt_stats('α (AP prob)',  _stats(alphs))
                fmt_stats('Q_ap/Gain',   _stats(qaps))
            lines.append('')

    lines.append('=' * W)
    lines.append('END OF SUMMARY')
    lines.append('=' * W)

    with open(fname, 'w') as fout:
        fout.write('\n'.join(lines) + '\n')
    log.info(f'Summary written to {fname}')
    return fname


# =============================================================================
# OVERVIEW PLOTS  (distributions across all channels for each model)
# =============================================================================

def plot_overview(all_results, models, out_dir, run_name, gain_min, gain_max):
    """Save gain / chi2 / R² distribution plots per model."""
    ov_dir = os.path.join(out_dir, 'plots', 'overview')
    os.makedirs(ov_dir, exist_ok=True)

    for mname in models:
        gains_g, chi2s_g, r2s_g = [], [], []
        gains_b, chi2s_b = [], []
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max)
            if cat == 'good':
                gains_g.append(r.get('gain', np.nan))
                chi2s_g.append(r.get('chi2_dof', np.nan))
                r2s_g.append(r.get('r2_linear', np.nan))
            elif cat == 'bad':
                gains_b.append(r.get('gain', np.nan))
                chi2s_b.append(r.get('chi2_dof', np.nan))

        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        fig.suptitle(f'{MODEL_LABELS[mname]} — Run {run_name}', fontsize=12)

        gains_g = np.array([x for x in gains_g if np.isfinite(x)])
        chi2s_g = np.array([x for x in chi2s_g if np.isfinite(x) and x > 0])
        r2s_g   = np.array([x for x in r2s_g   if np.isfinite(x)])

        if len(gains_g):
            axes[0].hist(gains_g, bins=60, color=MODEL_COLORS[mname], alpha=0.7)
            axes[0].axvline(np.mean(gains_g), color='red', lw=1.5,
                            label=f'μ={np.mean(gains_g):.0f}')
            axes[0].set_xlabel('Gain [ADC/PE]'); axes[0].set_ylabel('Channels')
            axes[0].set_title('Gain distribution (good)'); axes[0].legend(fontsize=8)

        if len(chi2s_g):
            axes[1].hist(chi2s_g, bins=50, range=(0, min(chi2s_g.max(), 15)),
                         color=MODEL_COLORS[mname], alpha=0.7)
            axes[1].set_xlabel('χ²/ndf'); axes[1].set_title('χ²/ndf (good)')

        if len(r2s_g):
            axes[2].hist(r2s_g, bins=50, range=(0.5, 1.01),
                         color=MODEL_COLORS[mname], alpha=0.7)
            axes[2].set_xlabel('R²'); axes[2].set_title('Linear R² (good)')

        plt.tight_layout()
        plt.savefig(os.path.join(ov_dir, f'{run_name}_{mname}_overview.png'), dpi=100)
        plt.close(fig)
    log.info(f'Overview plots saved to {ov_dir}')


# =============================================================================
# MAIN
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(description='TAO gain calibration')
    p.add_argument('input_root',  help='Input ROOT file with ADC histograms')
    p.add_argument('output_dir',  help='Output directory')
    p.add_argument('run_name',    help='Run identifier string (used in filenames)')
    p.add_argument('--use-raw',   action='store_true',
                   help='Use raw (non-vetoed) histograms')
    p.add_argument('--plots',     choices=('none','sample','all'), default='sample',
                   help='Plot mode [default: sample (50 per category)]')
    p.add_argument('--models',    default='all',
                   help='Comma-separated model list or "all" [default: all]')
    p.add_argument('--n-peaks',   type=int, default=None,
                   help='Force fixed number of PE peaks [default: auto]')
    p.add_argument('--workers',   type=int, default=max(1, cpu_count()-1),
                   help='Parallel workers [default: CPU count - 1]')
    p.add_argument('--gain-min',  type=float, default=GAIN_MIN_DEF)
    p.add_argument('--gain-max',  type=float, default=GAIN_MAX_DEF)
    p.add_argument('--coti',      action='store_true',
                   help='Apply COTI threshold erf correction to 1PE peak')
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # ── Model selection ────────────────────────────────────────────────────────
    if args.models == 'all':
        models = list(MODEL_NAMES)
    else:
        models = [m.strip() for m in args.models.split(',')]
        for m in models:
            if m not in MODEL_NAMES:
                log.error(f"Unknown model '{m}'. Valid: {MODEL_NAMES}")
                sys.exit(1)
    log.info(f'Models: {models}')

    # ── Load histograms ────────────────────────────────────────────────────────
    log.info(f'Loading histograms from {args.input_root}')
    histograms = load_histograms(args.input_root, use_raw=args.use_raw)
    log.info(f'Total channels loaded: {len(histograms)}')

    # ── Inject global config for workers ──────────────────────────────────────
    global _WORKER_ARGS
    _WORKER_ARGS.update(
        models=models,
        n_peaks_forced=args.n_peaks,
        apply_coti=args.coti,
        gain_min=args.gain_min,
        gain_max=args.gain_max,
    )

    # ── Run fits in parallel ──────────────────────────────────────────────────
    log.info(f'Fitting {len(histograms)} channels with {args.workers} workers…')
    work_items = [(ch_id, hist) for ch_id, hist in histograms.items()]
    all_results = {}

    if args.workers > 1:
        with Pool(processes=args.workers,
                  initializer=lambda: None) as pool:
            for ch_id, mres in tqdm(
                    pool.imap_unordered(_worker, work_items, chunksize=4),
                    total=len(work_items), desc='Fitting'):
                all_results[ch_id] = mres
    else:
        for item in tqdm(work_items, desc='Fitting'):
            ch_id, mres = _worker(item)
            all_results[ch_id] = mres

    # ── Save CSVs ─────────────────────────────────────────────────────────────
    log.info('Saving CSV results…')
    save_csvs(all_results, models, args.output_dir, args.run_name,
              args.gain_min, args.gain_max)

    # ── Plots ─────────────────────────────────────────────────────────────────
    if args.plots != 'none':
        log.info(f'Generating plots (mode={args.plots})…')
        plot_dirs = _make_plot_dirs(args.output_dir, models)

        # Build per-category channel lists (one per model)
        to_plot = {}
        for mname in models:
            cats = defaultdict(list)
            for ch_id, mres in all_results.items():
                r   = mres.get(mname, {})
                cat = classify(r, args.gain_min, args.gain_max)
                cats[cat].append(ch_id)
            if args.plots == 'sample':
                sel = {}
                for cat, chs in cats.items():
                    rng = random.Random(42)
                    sel[cat] = rng.sample(chs, min(SAMPLE_N, len(chs)))
                to_plot[mname] = sel
            else:   # all
                to_plot[mname] = dict(cats)

        # Identify which channels need plotting at all
        plot_set = set()
        for mname, sel in to_plot.items():
            for ch_list in sel.values():
                plot_set.update(ch_list)

        log.info(f'  {len(plot_set)} unique channels to plot')
        for ch_id in tqdm(sorted(plot_set), desc='Plotting'):
            hist   = histograms.get(ch_id, np.zeros(N_BINS))
            mres   = all_results.get(ch_id, {})
            peaks  = detect_peaks(hist)
            # Only plot models for which this channel is in the selected set
            subset = {m: mres.get(m, {}) for m in models
                      if ch_id in to_plot.get(m, {}).get(
                          classify(mres.get(m, {}), args.gain_min, args.gain_max), [])}
            if subset:
                plot_fit(ch_id, hist, subset, peaks, plot_dirs,
                         args.gain_min, args.gain_max)

        # Overview distributions
        plot_overview(all_results, models, args.output_dir, args.run_name,
                      args.gain_min, args.gain_max)

    # ── Summary ───────────────────────────────────────────────────────────────
    write_summary(all_results, models, args.output_dir, args.run_name,
                  args.gain_min, args.gain_max)

    # ── Quick console summary ─────────────────────────────────────────────────
    print('\n' + '='*60)
    print(f'  GAIN CALIBRATION COMPLETE  —  Run {args.run_name}')
    print('='*60)
    for mname in models:
        ng = nb = nf = 0
        gains = []
        for mres in all_results.values():
            r = mres.get(mname, {})
            cat = classify(r, args.gain_min, args.gain_max)
            if cat == 'good':
                ng += 1; gains.append(r['gain'])
            elif cat == 'bad':
                nb += 1
            else:
                nf += 1
        g_str = (f"{np.mean(gains):.0f} ± {np.std(gains):.0f}"
                 if gains else 'n/a')
        print(f"  {mname:<18s}  good={ng:5d}  bad={nb:5d}  "
              f"fail={nf:5d}  <gain>={g_str}")
    print('='*60 + '\n')


if __name__ == '__main__':
    main()
