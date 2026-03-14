#!/usr/bin/env python3
"""
gain_calibration.py
===================
TAO SiPM gain calibration pipeline — main entry point.

Delegates plotting to gain_calibration_plots.py and fitting to gain_fit_models.py.

Usage
-----
python gain_calibration.py input.root output_dir run_name [options]

Options
  --use-raw          Use raw (non-vetoed) histograms [default: clean]
  --plots {none,sample,all}
                     none   : skip per-channel plots
                     sample : 50 random per category
                     all    : every channel [default]
  --models M1,M2,…  Comma-separated model list [default: all]
                     Choices: multigauss multigauss_ct multigauss_ap emg emg_ap
  --n-peaks INT      Force fixed number of PE peaks [default: auto 2–8]
  --workers INT      Parallel worker processes [default: CPU count - 1]
  --gain-min FLOAT   Minimum gain for "good" [default: 3200]
  --gain-max FLOAT   Maximum gain for "good" [default: 8500]
  --chi2-max FLOAT   Maximum χ²/ndf for "good" [default: 100]
  --r2-min FLOAT     Minimum linear R² for "good" [default: 0.90]
  --coti             Apply COTI threshold erf correction to 1PE peak

Output (inside output_dir/)
  {run}_{model}_good.csv / bad.csv / failed.csv     (one set per model)
  {run}_{model}_good.txt / bad.txt / failed.txt     (formatted text tables)
  {run}_good_channels_features.txt                  (per-channel feature table)
  plots/good/{model}/ch_XXXXX_fit.png
  plots/good/{model}/ch_XXXXX_linear.png
  plots/overview/{run}_{model}_overview.png
  summary_{run}.txt

Classification
  good   : GAIN_MIN ≤ gain ≤ GAIN_MAX  AND  chi²/ndf ≤ CHI2_MAX  AND  R² ≥ R2_MIN
  bad    : fit converged but outside good criteria
  failed : fit did not converge / no peaks found
"""

import argparse
import logging
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from multiprocessing import Pool, cpu_count

import matplotlib
matplotlib.use('Agg')
import numpy as np
import pandas as pd

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kw):
        desc  = kw.get('desc', '')
        items = list(iterable)
        n     = len(items)
        log   = logging.getLogger(__name__)
        for i, x in enumerate(items):
            if i % max(1, n // 20) == 0:
                log.info(f'{desc}: {i}/{n}')
            yield x

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gain_fit_models import MODEL_NAMES, MODEL_LABELS, fit_channel, linear_fit_gain
from gain_calibration_plots import (
    classify, _make_plot_dirs, plot_fit, plot_overview,
    BIN_WIDTH, BIN_MAX, BIN_CTRS, N_BINS,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# ── Default thresholds ────────────────────────────────────────────────────────
CHI2_MAX     = 100.0
R2_MIN       = 0.90
GAIN_MIN_DEF = 3_200
GAIN_MAX_DEF = 8_500
GAIN_DEFAULT = 6_000
MIN_ENTRIES  = 2_000
SAMPLE_N     = 50


# =============================================================================
# PEAK DETECTION
# =============================================================================

def _gauss_kernel(half_width, sigma_bins):
    k = np.arange(-half_width, half_width + 1, dtype=float)
    w = np.exp(-0.5 * (k / sigma_bins)**2)
    return w / w.sum()


def smooth_hist(hist, sigma_bins=3.0):
    hw     = max(1, int(3.5 * sigma_bins))
    kernel = _gauss_kernel(hw, sigma_bins)
    padded = np.pad(hist.astype(float), hw, mode='edge')
    return np.convolve(padded, kernel, mode='valid')[:len(hist)]


def local_maxima(arr, min_dist):
    cands = [i for i in range(1, len(arr) - 1)
             if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]]
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
    if np.sum(hist) < MIN_ENTRIES:
        return []

    sigma_s  = max(1.0, gain_est / BIN_WIDTH / 10.0)
    min_sep  = max(2, int(0.5 * gain_est / BIN_WIDTH))
    smoothed = smooth_hist(hist, sigma_s)
    idxs     = local_maxima(smoothed, min_sep)
    if len(idxs) < 2:
        return []

    win   = max(2, int(2.0 * gain_est / BIN_WIDTH))
    proms = []
    for i in idxs:
        lo = max(0, i - win);  hi = min(len(smoothed), i + win + 1)
        bg = min(smoothed[lo:i].min() if i > lo else smoothed[i],
                 smoothed[i + 1:hi].min() if i + 1 < hi else smoothed[i])
        proms.append(smoothed[i] - bg)
    min_prom = max(max(proms) * 0.005, 3.0)
    idxs     = [i for i, p in zip(idxs, proms) if p >= min_prom]
    if len(idxs) < 2:
        return []

    peaks = sorted(float(BIN_CTRS[i]) for i in idxs)

    cands = ([p for p in peaks if gain_est / 3 <= p <= gain_est * 3]
             or [p for p in peaks if 300 <= p <= 25_000])
    if not cands:
        return []
    h0 = [hist[int(np.argmin(np.abs(BIN_CTRS - p)))] for p in cands]
    fp = cands[int(np.argmax(h0))]

    chain = [fp]
    for p in peaks:
        if p <= fp:
            continue
        sp = p - chain[-1]
        if 0.5 * gain_est <= sp <= 1.5 * gain_est:
            chain.append(p)
        if len(chain) >= 8:
            break

    heights = [hist[int(np.argmin(np.abs(BIN_CTRS - p)))] for p in chain]
    cut = len(chain)
    for i in range(len(heights) - 1):
        if heights[i + 1] > heights[i] * 1.20:
            cut = i + 1
            break
    chain = chain[:cut]
    return chain if len(chain) >= 2 else []


# =============================================================================
# ROOT HISTOGRAM READER
# =============================================================================

def load_histograms(root_file, use_raw=False):
    prefix = 'H_adc' + ('raw' if use_raw else 'Clean') + '_'
    histograms = {}

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
            nb    = h.GetNbinsX()
            ctrs_ = np.array([h.GetBinCenter(b)  for b in range(1, nb + 1)])
            vals_ = np.array([h.GetBinContent(b) for b in range(1, nb + 1)])
            out   = np.zeros(N_BINS, dtype=float)
            for c, v in zip(ctrs_, vals_):
                bi = int(np.argmin(np.abs(BIN_CTRS - c)))
                out[bi] += v
            histograms[ch_id] = out
        f.Close()
        log.info(f"[PyROOT] Loaded {len(histograms)} histograms from {root_file}")
        return histograms
    except ImportError:
        raise RuntimeError("Neither uproot nor PyROOT is available.")


# =============================================================================
# PER-CHANNEL FIT WORKER
# =============================================================================

_WORKER_ARGS = {}


def _worker(args):
    ch_id, hist = args
    models      = _WORKER_ARGS['models']
    n_pk_forced = _WORKER_ARGS['n_peaks_forced']
    apply_coti  = _WORKER_ARGS['apply_coti']
    gain_min    = _WORKER_ARGS['gain_min']
    gain_max    = _WORKER_ARGS['gain_max']

    EMPTY = {m: dict(success=False, gain=0.0, gain_err=np.inf,
                     chi2_dof=-1.0, r2_linear=0.0, n_peaks=0,
                     linear_chi2_dof=-1.0,
                     y_fit=None, extra={}, _par_fit={}, _x_data=None,
                     param_names=[], popt=None)
             for m in models}

    if np.sum(hist) < MIN_ENTRIES:
        return ch_id, EMPTY

    gain_est = float(np.clip(GAIN_DEFAULT, gain_min, gain_max))
    peaks    = detect_peaks(hist, gain_est=gain_est)
    if len(peaks) < 2:
        return ch_id, EMPTY

    spacings = [peaks[i + 1] - peaks[i] for i in range(len(peaks) - 1)]
    gain_est = float(np.clip(np.median(spacings), gain_min, gain_max))
    n_peaks  = int(np.clip(n_pk_forced if n_pk_forced else len(peaks), 2, 8))
    peaks_fit = peaks[:n_peaks]

    fit_min = max(peaks_fit[0] - 0.5 * gain_est, BIN_CTRS[0])
    fit_max = peaks_fit[-1] + 1.2 * gain_est
    mask    = (BIN_CTRS >= fit_min) & (BIN_CTRS <= fit_max)
    x_fit   = BIN_CTRS[mask]
    y_fit   = hist[mask]

    if len(x_fit) < 5 or np.sum(y_fit) < 100:
        return ch_id, EMPTY

    results = {}
    for mname in models:
        results[mname] = fit_channel(
            x_fit, y_fit, n_peaks, peaks_fit, gain_est,
            mname, apply_coti=apply_coti)

    return ch_id, results


# =============================================================================
# CSV OUTPUT
# =============================================================================

RESULT_COLS = [
    'channel_id', 'n_peaks', 'gain', 'gain_err',
    'intercept', 'intercept_err', 'chi2_dof', 'r2_linear', 'linear_chi2_dof',
    'sigma_pe', 'sigma_base',
    'tau', 'tau_err', 'p_ct_emg',
    'p_ct', 'p_ct_err',
    'q_ap', 'q_ap_rel', 'alpha', 'alpha_err',
]


def _result_to_row(ch_id, r):
    extra = r.get('extra', {})
    return {
        'channel_id':      ch_id,
        'n_peaks':         r.get('n_peaks', 0),
        'gain':            r.get('gain', np.nan),
        'gain_err':        r.get('gain_err', np.nan),
        'intercept':       r.get('intercept', np.nan),
        'intercept_err':   r.get('intercept_err', np.nan),
        'chi2_dof':        r.get('chi2_dof', np.nan),
        'r2_linear':       r.get('r2_linear', np.nan),
        'linear_chi2_dof': r.get('linear_chi2_dof', np.nan),
        'sigma_pe':        extra.get('sigma_pe',    np.nan),
        'sigma_base':      extra.get('sigma_base',  np.nan),
        'tau':             extra.get('tau',          np.nan),
        'tau_err':         extra.get('tau_err',      np.nan),
        'p_ct_emg':        extra.get('p_ct_emg',    np.nan),
        'p_ct':            extra.get('p_ct',         np.nan),
        'p_ct_err':        extra.get('p_ct_err',    np.nan),
        'q_ap':            extra.get('q_ap',         np.nan),
        'q_ap_rel':        extra.get('q_ap_rel',    np.nan),
        'alpha':           extra.get('alpha',        np.nan),
        'alpha_err':       extra.get('alpha_err',   np.nan),
    }


def save_csvs(all_results, models, out_dir, run_name, gain_min, gain_max,
              chi2_max, r2_min):
    csv_paths = {}
    for mname in models:
        rows = defaultdict(list)
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max, chi2_max, r2_min)
            rows[cat].append(_result_to_row(ch_id, r))
        for cat in ('good', 'bad', 'failed'):
            fname = os.path.join(out_dir, f'{run_name}_{mname}_{cat}.csv')
            pd.DataFrame(rows[cat], columns=RESULT_COLS).to_csv(fname, index=False)
            csv_paths[(mname, cat)] = fname
            log.info(f"  → {fname}  ({len(rows[cat])} channels)")
    return csv_paths


# =============================================================================
# TXT OUTPUT  (formatted table, one per model per category)
# =============================================================================

def save_txts(all_results, models, out_dir, run_name, gain_min, gain_max,
              chi2_max, r2_min):
    HDR = (f"{'Channel':<10} {'Gain':<12} {'Gain_Err':<12} {'Intercept':<14} "
           f"{'Int_Err':<12} {'N_Peaks':<10} {'Chi2/ndf':<12} {'R2':<10} "
           f"{'Lin_Chi2':<12} {'Mu1[ADC]':<12} {'Sigma_PE':<12} {'Sigma_Base':<12}\n")
    SEP = '=' * 138 + '\n'

    txt_paths = {}
    for mname in models:
        rows_by_cat = defaultdict(list)
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max, chi2_max, r2_min)
            rows_by_cat[cat].append((ch_id, r))

        for cat in ('good', 'bad', 'failed'):
            fname = os.path.join(out_dir, f'{run_name}_{mname}_{cat}.txt')
            with open(fname, 'w') as fout:
                fout.write(f"# TAO Gain Calibration  —  model={mname}  cat={cat}\n")
                fout.write(f"# Run: {run_name}   Generated: "
                           f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                fout.write(f"# Gain range: [{gain_min:.0f}, {gain_max:.0f}]  "
                           f"χ²/ndf≤{chi2_max}  R²≥{r2_min}\n")
                fout.write(SEP)
                fout.write(HDR)
                fout.write(SEP)
                for ch_id, r in sorted(rows_by_cat[cat], key=lambda x: x[0]):
                    pf     = r.get('_par_fit', {})
                    extra  = r.get('extra', {})
                    mu1    = pf.get('mu1',         0.0)
                    spe    = extra.get('sigma_pe',  0.0)
                    sbase  = extra.get('sigma_base',0.0)
                    fout.write(
                        f"{ch_id:<10} "
                        f"{r.get('gain',          0.0):<12.2f} "
                        f"{r.get('gain_err',       0.0):<12.2f} "
                        f"{r.get('intercept',      0.0):<14.2f} "
                        f"{r.get('intercept_err',  0.0):<12.2f} "
                        f"{r.get('n_peaks',           0):<10} "
                        f"{r.get('chi2_dof',       -1.0):<12.3f} "
                        f"{r.get('r2_linear',       0.0):<10.4f} "
                        f"{r.get('linear_chi2_dof',-1.0):<12.3f} "
                        f"{mu1:<12.2f} "
                        f"{spe:<12.2f} "
                        f"{sbase:<12.2f}\n"
                    )
            txt_paths[(mname, cat)] = fname
            log.info(f"  → {fname}  ({len(rows_by_cat[cat])} channels)")
    return txt_paths


# =============================================================================
# GOOD-CHANNELS FEATURES TXT
# =============================================================================

def write_good_channels_features_txt(all_results, models, out_dir, run_name,
                                     gain_min, gain_max, chi2_max, r2_min):
    """
    Write RUNXXXX_good_channels_features.txt.

    Uses the FIRST model that yields a 'good' result for each channel.
    Table columns:
      Channel | G1 | G2 | G3 | G_out | I1 | I2 | I3 | I_out | I_posit

    where the σ/μ bands are computed from the distribution of gain and
    intercept values across ALL good channels (using the best model per channel).

    After the table, a summary counts channels for every (G, I) combination.
    """
    # ── Collect good results (best model per channel) ─────────────────────────
    good_rows = []   # list of (ch_id, gain, intercept)
    for ch_id, mres in all_results.items():
        for mname in models:
            r = mres.get(mname, {})
            if classify(r, gain_min, gain_max, chi2_max, r2_min) == 'good':
                g  = r.get('gain',      np.nan)
                ic = r.get('intercept', np.nan)
                if np.isfinite(g) and np.isfinite(ic):
                    good_rows.append((ch_id, g, ic))
                break   # first good model wins

    if not good_rows:
        log.warning("No good channels found — skipping features file.")
        return None

    ch_ids   = np.array([r[0] for r in good_rows])
    gains    = np.array([r[1] for r in good_rows])
    icepts   = np.array([r[2] for r in good_rows])

    # ── Population statistics ─────────────────────────────────────────────────
    mu_g  = float(np.mean(gains));   sig_g = float(np.std(gains))
    mu_i  = float(np.mean(icepts));  sig_i = float(np.std(icepts))

    def _g_cat(g):
        if   abs(g - mu_g) <= sig_g:             return 'G1'
        elif abs(g - mu_g) <= 2*sig_g:           return 'G2'
        elif abs(g - mu_g) <= 3*sig_g:           return 'G3'
        else:                                      return 'G_out'

    def _i_cat(ic):
        if   abs(ic - mu_i) <= sig_i:            return 'I1'
        elif abs(ic - mu_i) <= 2*sig_i:          return 'I2'
        elif abs(ic - mu_i) <= 3*sig_i:          return 'I3'
        else:                                      return 'I_out'

    G_CATS = ['G1', 'G2', 'G3', 'G_out']
    I_CATS = ['I1', 'I2', 'I3', 'I_out', 'I_posit']

    # ── Build per-channel feature dict ────────────────────────────────────────
    rows_features = []
    for ch_id, g, ic in sorted(good_rows, key=lambda x: x[0]):
        gc = _g_cat(g)
        ic_cat = _i_cat(ic)
        row = {'Channel': ch_id}
        for c in G_CATS:
            row[c] = 'yes' if c == gc else 'no'
        for c in ['I1', 'I2', 'I3', 'I_out']:
            row[c] = 'yes' if c == ic_cat else 'no'
        row['I_posit'] = 'yes' if ic > 0 else 'no'
        rows_features.append(row)

    # ── Write file ────────────────────────────────────────────────────────────
    fname = os.path.join(out_dir, f'{run_name}_good_channels_features.txt')
    ALL_COLS = ['Channel'] + G_CATS + I_CATS

    W = 128

    with open(fname, 'w') as fout:
        fout.write(f"# TAO Gain Calibration — Good Channels Feature Table\n")
        fout.write(f"# Run: {run_name}   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fout.write(f"# Gain population: μ_G = {mu_g:.1f}  σ_G = {sig_g:.1f}\n")
        fout.write(f"# Intercept population: μ_I = {mu_i:.1f}  σ_I = {sig_i:.1f}\n")
        fout.write(f"#\n")
        fout.write(f"# G1      : gain in [μ_G - σ_G, μ_G + σ_G]\n")
        fout.write(f"# G2      : gain in [μ_G-2σ, μ_G+2σ] but outside [μ_G-σ, μ_G+σ]\n")
        fout.write(f"# G3      : gain in [μ_G-3σ, μ_G+3σ] but outside [μ_G-2σ, μ_G+2σ]\n")
        fout.write(f"# G_out   : gain outside [μ_G-3σ, μ_G+3σ]\n")
        fout.write(f"# I1      : intercept in [μ_I - σ_I, μ_I + σ_I]\n")
        fout.write(f"# I2      : intercept in [μ_I-2σ, μ_I+2σ] but outside [μ_I-σ, μ_I+σ]\n")
        fout.write(f"# I3      : intercept in [μ_I-3σ, μ_I+3σ] but outside [μ_I-2σ, μ_I+2σ]\n")
        fout.write(f"# I_out   : intercept outside [μ_I-3σ, μ_I+3σ]\n")
        fout.write(f"# I_posit : intercept > 0\n")
        fout.write('=' * W + '\n')

        # Header
        hdr_parts = [f"{'Channel':<12}"]
        for c in G_CATS + I_CATS:
            hdr_parts.append(f"{c:<10}")
        fout.write(''.join(hdr_parts) + '\n')
        fout.write('-' * W + '\n')

        # Data rows
        for row in rows_features:
            parts = [f"{row['Channel']:<12}"]
            for c in G_CATS + I_CATS:
                parts.append(f"{row[c]:<10}")
            fout.write(''.join(parts) + '\n')

        fout.write('=' * W + '\n')

        # ── Summary counts ────────────────────────────────────────────────────
        fout.write('\n# SUMMARY — Channel counts per (G, I) category combination\n')
        fout.write('#\n')

        def _count(g_cat, i_cat):
            return sum(
                1 for r in rows_features
                if r[g_cat] == 'yes' and r[i_cat] == 'yes'
            )

        def _count_g(g_cat):
            return sum(1 for r in rows_features if r[g_cat] == 'yes')

        def _count_i(i_cat):
            return sum(1 for r in rows_features if r[i_cat] == 'yes')

        fout.write(f"  Total good channels : {len(rows_features)}\n\n")

        # Single-category counts
        for gc in G_CATS:
            fout.write(f"  {gc} = {_count_g(gc)} CHN\n")
        fout.write('\n')
        for ic in I_CATS:
            fout.write(f"  {ic} = {_count_i(ic)} CHN\n")
        fout.write('\n')

        # Cross-category combinations (G × I)
        fout.write("  --- G × I combinations ---\n")
        for gc in G_CATS:
            for ic in I_CATS:
                n = _count(gc, ic)
                fout.write(f"  {gc} & {ic} = {n} CHN\n")
            fout.write('\n')

    log.info(f"Good-channels features: {fname}  ({len(rows_features)} channels)")
    return fname


# =============================================================================
# SUMMARY TXT
# =============================================================================

def _stats(arr):
    a = np.array([x for x in arr if np.isfinite(x)])
    if len(a) == 0:
        return dict(n=0, mean=np.nan, std=np.nan, median=np.nan,
                    p16=np.nan, p84=np.nan)
    return dict(n=len(a), mean=float(np.mean(a)), std=float(np.std(a)),
                median=float(np.median(a)),
                p16=float(np.percentile(a, 16)), p84=float(np.percentile(a, 84)))


def write_summary(all_results, models, out_dir, run_name,
                  gain_min, gain_max, chi2_max, r2_min):
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

    hdr('TAO GAIN CALIBRATION SUMMARY')
    lines.append(f'  Run: {run_name}')
    lines.append(f'  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'  Gain classification: [{gain_min:.0f}, {gain_max:.0f}] ADC/PE')
    lines.append(f'  Quality cuts: chi2/ndf ≤ {chi2_max}  R² ≥ {r2_min}')
    lines.append(f'  Total channels: {len(all_results)}')
    lines.append('')

    for mname in models:
        sub(f'MODEL: {MODEL_LABELS.get(mname, mname)}  ({mname})')

        cats = {'good': [], 'bad': [], 'failed': []}
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max, chi2_max, r2_min)
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
            fmt_stats('Gain [ADC/PE]', _stats([r.get('gain',      np.nan) for r in rlist]))
            fmt_stats('chi2/ndf',      _stats([r.get('chi2_dof',  np.nan) for r in rlist]))
            fmt_stats('R² (linear)',   _stats([r.get('r2_linear', np.nan) for r in rlist]))
            fmt_stats('Lin chi2/ndf',  _stats([r.get('linear_chi2_dof', np.nan) for r in rlist]))

            if mname in ('emg', 'emg_ap'):
                fmt_stats('τ [ADC]',    _stats([r.get('extra', {}).get('tau',     np.nan) for r in rlist]))
                fmt_stats('p_ct (τ/G)', _stats([r.get('extra', {}).get('p_ct_emg',np.nan) for r in rlist]))
            if mname == 'multigauss_ct':
                fmt_stats('p_ct (binom)',_stats([r.get('extra', {}).get('p_ct',   np.nan) for r in rlist]))
            if mname in ('multigauss_ap', 'emg_ap'):
                fmt_stats('α (AP prob)', _stats([r.get('extra', {}).get('alpha',  np.nan) for r in rlist]))
                fmt_stats('Q_ap/Gain',   _stats([r.get('extra', {}).get('q_ap_rel',np.nan) for r in rlist]))
            lines.append('')

    lines.append('=' * W)
    lines.append('END OF SUMMARY')
    lines.append('=' * W)

    with open(fname, 'w') as fout:
        fout.write('\n'.join(lines) + '\n')

    log.info(f'Summary written to {fname}')
    return fname


# =============================================================================
# MAIN
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(description='TAO SiPM gain calibration')
    p.add_argument('input_root',  help='Input ROOT file with ADC histograms')
    p.add_argument('output_dir',  help='Output directory')
    p.add_argument('run_name',    help='Run identifier string (used in filenames)')
    p.add_argument('--use-raw',   action='store_true',
                   help='Use raw (non-vetoed) histograms')
    p.add_argument('--plots',     choices=('none', 'sample', 'all'), default='all',
                   help='Plot mode [default: all]')
    p.add_argument('--models',    default='all',
                   help='Comma-separated model list or "all" [default: all]')
    p.add_argument('--n-peaks',   type=int, default=None,
                   help='Force fixed number of PE peaks [default: auto]')
    p.add_argument('--workers',   type=int, default=max(1, cpu_count() - 1),
                   help='Parallel workers [default: CPU count − 1]')
    p.add_argument('--gain-min',  type=float, default=GAIN_MIN_DEF)
    p.add_argument('--gain-max',  type=float, default=GAIN_MAX_DEF)
    p.add_argument('--chi2-max',  type=float, default=CHI2_MAX,
                   help=f'Maximum χ²/ndf for "good" [default: {CHI2_MAX}]')
    p.add_argument('--r2-min',    type=float, default=R2_MIN,
                   help=f'Minimum linear R² for "good" [default: {R2_MIN}]')
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
                log.error(f"Unknown model '{m}'. Valid: {list(MODEL_NAMES)}")
                sys.exit(1)
    log.info(f'Models: {models}')
    log.info(f'Quality cuts: chi2/ndf≤{args.chi2_max}  R²≥{args.r2_min}  '
             f'gain=[{args.gain_min}, {args.gain_max}]')

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
    log.info(f'Fitting {len(histograms)} channels with {args.workers} worker(s)…')
    work_items  = [(ch_id, hist) for ch_id, hist in histograms.items()]
    all_results = {}

    if args.workers > 1:
        with Pool(processes=args.workers, initializer=lambda: None) as pool:
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
              args.gain_min, args.gain_max, args.chi2_max, args.r2_min)

    # ── Save TXT tables ───────────────────────────────────────────────────────
    log.info('Saving TXT tables…')
    save_txts(all_results, models, args.output_dir, args.run_name,
              args.gain_min, args.gain_max, args.chi2_max, args.r2_min)

    # ── Save good-channels features TXT ───────────────────────────────────────
    log.info('Saving good-channels feature table…')
    write_good_channels_features_txt(
        all_results, models, args.output_dir, args.run_name,
        args.gain_min, args.gain_max, args.chi2_max, args.r2_min)

    # ── Plots ─────────────────────────────────────────────────────────────────
    if args.plots != 'none':
        log.info(f'Generating plots (mode={args.plots})…')
        plot_dirs = _make_plot_dirs(args.output_dir, models)

        to_plot = {}
        for mname in models:
            cats = defaultdict(list)
            for ch_id, mres in all_results.items():
                r   = mres.get(mname, {})
                cat = classify(r, args.gain_min, args.gain_max,
                               args.chi2_max, args.r2_min)
                cats[cat].append(ch_id)
            if args.plots == 'sample':
                sel = {}
                rng = random.Random(42)
                for cat, chs in cats.items():
                    sel[cat] = rng.sample(chs, min(SAMPLE_N, len(chs)))
                to_plot[mname] = sel
            else:   # all
                to_plot[mname] = dict(cats)

        plot_set = set()
        for mname, sel in to_plot.items():
            for ch_list in sel.values():
                plot_set.update(ch_list)

        log.info(f'  {len(plot_set)} unique channels to plot')
        for ch_id in tqdm(sorted(plot_set), desc='Plotting'):
            hist_ch = histograms.get(ch_id, np.zeros(N_BINS))
            mres    = all_results.get(ch_id, {})
            peaks   = detect_peaks(hist_ch)
            subset = {
                m: mres.get(m, {}) for m in models
                if ch_id in to_plot.get(m, {}).get(
                    classify(mres.get(m, {}), args.gain_min, args.gain_max,
                             args.chi2_max, args.r2_min), [])
            }
            if subset:
                plot_fit(ch_id, hist_ch, subset, peaks, plot_dirs,
                         args.gain_min, args.gain_max,
                         args.chi2_max, args.r2_min)

        plot_overview(all_results, models, args.output_dir, args.run_name,
                      args.gain_min, args.gain_max, args.chi2_max, args.r2_min)

    # ── Summary ───────────────────────────────────────────────────────────────
    write_summary(all_results, models, args.output_dir, args.run_name,
                  args.gain_min, args.gain_max, args.chi2_max, args.r2_min)

    # ── Console summary ───────────────────────────────────────────────────────
    print('\n' + '=' * 62)
    print(f'  GAIN CALIBRATION COMPLETE  —  Run {args.run_name}')
    print('=' * 62)
    for mname in models:
        ng = nb = nf = 0
        gains = []
        for mres in all_results.values():
            r   = mres.get(mname, {})
            cat = classify(r, args.gain_min, args.gain_max,
                           args.chi2_max, args.r2_min)
            if cat == 'good':
                ng += 1; gains.append(r['gain'])
            elif cat == 'bad':
                nb += 1
            else:
                nf += 1
        g_str = (f"{np.mean(gains):.0f} ± {np.std(gains):.0f}"
                 if gains else 'n/a')
        print(f"  {mname:<20s}  good={ng:5d}  bad={nb:5d}  "
              f"fail={nf:5d}  <gain>={g_str}")
    print('=' * 62 + '\n')


if __name__ == '__main__':
    main()
