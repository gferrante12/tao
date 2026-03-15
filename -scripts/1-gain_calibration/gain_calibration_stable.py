#!/usr/bin/env python3
"""
gain_calibration_stable.py
===================
TAO SiPM gain calibration pipeline — main entry point.

Delegates plotting to gain_calibration_plots.py and fitting to gain_fit_models.py.

Usage
-----
python gain_calibration_stable.py input.root output_dir run_name [options]

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
  --chi2-max FLOAT   Maximum chi2/ndf for "good" [default: 100]
  --r2-min FLOAT     Minimum linear R2 for "good" [default: 0.90]
  --coti             Apply COTI threshold erf correction to 1PE peak

NOTE: gain_min / gain_max thresholds are no longer used for classification.

Output (inside output_dir/)
  {run}_{model}_good.csv / bad.csv / failed.csv / good_1pe_issue.csv
  {run}_{model}_good.txt / bad.txt / failed.txt / good_1pe_issue.txt
  {run}_{model}_good_channels_features.txt
  plots/good/{model}/           plots/good_1pe_issue/{model}/
  plots/bad/{model}/            plots/failed/{model}/
  plots/overview/{run}_{model}_overview.png
  summary_{run}.txt

Classification
  good            : chi2/ndf <= CHI2_MAX  AND  R2 >= R2_MIN
                    AND  1PE peak bin >= 2PE peak bin in raw histogram
  good_1pe_issue  : chi2/ndf <= CHI2_MAX  AND  R2 >= R2_MIN
                    BUT  1PE peak bin < 2PE peak bin in raw histogram
  bad             : fit converged but outside quality cuts
  failed          : fit did not converge / no peaks found
"""

import argparse
import logging
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from itertools import combinations
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
    BIN_WIDTH, BIN_MAX, BIN_CTRS, N_BINS, ALL_CATS,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# ── Default quality thresholds (gain range removed) ──────────────────────────
CHI2_MAX     = 100.0
R2_MIN       = 0.90
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
    """
    Detect PE peaks in ADC histogram.

    Returns a list of peak positions (ADC values) sorted ascending.
    The monotone-decreasing height check is intentionally NOT enforced here —
    channels where 1PE bin < 2PE bin are still returned and later flagged.
    """
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
        lo = max(0, i - win); hi = min(len(smoothed), i + win + 1)
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

    # NOTE: no monotone-height cut here (1PE-issue flagged separately)
    return chain if len(chain) >= 2 else []


def _check_1pe_issue(hist, peaks):
    """Return True if the 1PE peak bin has fewer raw counts than the 2PE peak bin."""
    if len(peaks) < 2:
        return False
    h1 = hist[int(np.argmin(np.abs(BIN_CTRS - peaks[0])))]
    h2 = hist[int(np.argmin(np.abs(BIN_CTRS - peaks[1])))]
    return bool(h1 < h2)


# =============================================================================
# ROOT HISTOGRAM READER
# =============================================================================

def load_histograms(root_file, use_raw=False):
    prefix     = 'H_adc' + ('raw' if use_raw else 'Clean') + '_'
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
        log.warning(f"uproot failed ({exc}), trying PyROOT...")

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
            h = f.Get(name)
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
    """Multiprocessing worker: fit all models for one channel."""
    ch_id, hist = args
    models      = _WORKER_ARGS['models']
    n_pk_forced = _WORKER_ARGS['n_peaks_forced']
    apply_coti  = _WORKER_ARGS['apply_coti']

    EMPTY = {m: dict(success=False, gain=0.0, gain_err=np.inf,
                     chi2_dof=-1.0, r2_linear=0.0, n_peaks=0,
                     linear_chi2_dof=-1.0, has_1pe_issue=False,
                     y_fit=None, extra={}, _par_fit={}, _x_data=None,
                     param_names=[], popt=None)
             for m in models}

    if np.sum(hist) < MIN_ENTRIES:
        return ch_id, EMPTY

    peaks = detect_peaks(hist, gain_est=GAIN_DEFAULT)
    if len(peaks) < 2:
        return ch_id, EMPTY

    # ── 1PE issue flag (computed once, from raw histogram) ────────────────────
    has_1pe_issue = _check_1pe_issue(hist, peaks)

    spacings = [peaks[i + 1] - peaks[i] for i in range(len(peaks) - 1)]
    gain_est = float(np.clip(np.median(spacings), 100.0, 50_000.0))
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
        r = fit_channel(
            x_fit, y_fit, n_peaks, peaks_fit, gain_est,
            mname, apply_coti=apply_coti)
        # Stamp the 1PE issue flag onto every model result
        r['has_1pe_issue'] = has_1pe_issue
        results[mname] = r

    return ch_id, results


# =============================================================================
# CSV / TXT OUTPUT
# =============================================================================

RESULT_COLS = [
    'channel_id', 'n_peaks', 'gain', 'gain_err',
    'intercept', 'intercept_err', 'chi2_dof', 'r2_linear', 'linear_chi2_dof',
    'has_1pe_issue',
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
        'gain':            r.get('gain',      np.nan),
        'gain_err':        r.get('gain_err',  np.nan),
        'intercept':       r.get('intercept', np.nan),
        'intercept_err':   r.get('intercept_err', np.nan),
        'chi2_dof':        r.get('chi2_dof',  np.nan),
        'r2_linear':       r.get('r2_linear', np.nan),
        'linear_chi2_dof': r.get('linear_chi2_dof', np.nan),
        'has_1pe_issue':   int(r.get('has_1pe_issue', False)),
        'sigma_pe':        extra.get('sigma_pe',   np.nan),
        'sigma_base':      extra.get('sigma_base', np.nan),
        'tau':             extra.get('tau',         np.nan),
        'tau_err':         extra.get('tau_err',     np.nan),
        'p_ct_emg':        extra.get('p_ct_emg',   np.nan),
        'p_ct':            extra.get('p_ct',        np.nan),
        'p_ct_err':        extra.get('p_ct_err',   np.nan),
        'q_ap':            extra.get('q_ap',        np.nan),
        'q_ap_rel':        extra.get('q_ap_rel',   np.nan),
        'alpha':           extra.get('alpha',       np.nan),
        'alpha_err':       extra.get('alpha_err',  np.nan),
    }


def save_csvs(all_results, models, out_dir, run_name, chi2_max, r2_min):
    csv_paths = {}
    for mname in models:
        rows = defaultdict(list)
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, chi2_max=chi2_max, r2_min=r2_min)
            rows[cat].append(_result_to_row(ch_id, r))
        for cat in ALL_CATS:
            fname = os.path.join(out_dir, f'{run_name}_{mname}_{cat}.csv')
            pd.DataFrame(rows[cat], columns=RESULT_COLS).to_csv(fname, index=False)
            csv_paths[(mname, cat)] = fname
            log.info(f"  -> {fname}  ({len(rows[cat])} channels)")
    return csv_paths


def save_txts(all_results, models, out_dir, run_name, chi2_max, r2_min):
    HDR = (f"{'Channel':<10} {'Gain':<12} {'Gain_Err':<12} {'Intercept':<14} "
           f"{'Int_Err':<12} {'N_Peaks':<10} {'Chi2/ndf':<12} {'R2':<10} "
           f"{'Lin_Chi2':<12} {'1PE_issue':<12} {'Mu1[ADC]':<12} "
           f"{'Sigma_PE':<12} {'Sigma_Base':<12}\n")
    SEP = '=' * 150 + '\n'

    txt_paths = {}
    for mname in models:
        rows_by_cat = defaultdict(list)
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, chi2_max=chi2_max, r2_min=r2_min)
            rows_by_cat[cat].append((ch_id, r))

        for cat in ALL_CATS:
            fname = os.path.join(out_dir, f'{run_name}_{mname}_{cat}.txt')
            with open(fname, 'w') as fout:
                fout.write(f"# TAO Gain Calibration  --  model={mname}  cat={cat}\n")
                fout.write(f"# Run: {run_name}   Generated: "
                           f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                fout.write(f"# Quality cuts: chi2/ndf<={chi2_max}  R2>={r2_min}\n")
                fout.write(SEP)
                fout.write(HDR)
                fout.write(SEP)
                for ch_id, r in sorted(rows_by_cat[cat], key=lambda x: x[0]):
                    pf    = r.get('_par_fit', {})
                    extra = r.get('extra', {})
                    mu1   = pf.get('mu1',          0.0)
                    spe   = extra.get('sigma_pe',   0.0)
                    sbase = extra.get('sigma_base', 0.0)
                    issue = 'YES' if r.get('has_1pe_issue') else 'no'
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
                        f"{issue:<12} "
                        f"{mu1:<12.2f} "
                        f"{spe:<12.2f} "
                        f"{sbase:<12.2f}\n"
                    )
            txt_paths[(mname, cat)] = fname
            log.info(f"  -> {fname}  ({len(rows_by_cat[cat])} channels)")
    return txt_paths


# =============================================================================
# GOOD CHANNELS FEATURES TXT
# =============================================================================

def save_good_channels_features(all_results, models, out_dir, run_name,
                                  chi2_max, r2_min):
    """
    Write {run}_{model}_good_channels_features.txt for each model.

    Includes ALL channels that passed quality cuts ('good' + 'good_1pe_issue').

    File structure
    --------------
    SECTION 0  — Category definitions (legend)
    CHANNEL TABLE — per-channel yes/no flags for all categories
    SECTION 1  — Count summary: all combinations of G x I x 1PE_issue
    SECTION 2  — Channel ID lists for exceptional features:
                 G_out, I_out, I_posit, 1PE_issue, and ALL combinations
                 (including same-quantity combos e.g. I_out & I_posit)
    """
    G_CATS  = ['G1', 'G2', 'G3', 'G_out']
    I_CATS  = ['I1', 'I2', 'I3', 'I_out', 'I_posit']
    # Features tracked in section 2 (channel ID lists)
    SPECIAL = ['G_out', 'I_out', 'I_posit', '1PE_issue']

    SEP   = '-' * 140 + '\n'
    THICK = '=' * 140 + '\n'

    for mname in models:
        # ── collect channels that passed quality cuts ─────────────────────
        good_rows = []
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, chi2_max=chi2_max, r2_min=r2_min)
            if cat in ('good', 'good_1pe_issue'):
                good_rows.append((ch_id, r))

        if not good_rows:
            log.info(f"  No good channels for model {mname} — skipping features file")
            continue

        gains  = np.array([r.get('gain',      np.nan) for _, r in good_rows])
        icepts = np.array([r.get('intercept', np.nan) for _, r in good_rows])

        gains_ok  = gains [np.isfinite(gains)]
        icepts_ok = icepts[np.isfinite(icepts)]
        mu_g  = float(np.mean(gains_ok))  if len(gains_ok)  > 0 else 0.0
        sig_g = float(np.std(gains_ok))   if len(gains_ok)  > 1 else 1.0
        mu_i  = float(np.mean(icepts_ok)) if len(icepts_ok) > 0 else 0.0
        sig_i = float(np.std(icepts_ok))  if len(icepts_ok) > 1 else 1.0

        def _gc(g):
            if not np.isfinite(g): return 'G_out'
            d = abs(g - mu_g)
            if d <= sig_g:        return 'G1'
            if d <= 2.0 * sig_g:  return 'G2'
            if d <= 3.0 * sig_g:  return 'G3'
            return 'G_out'

        def _ic(ic):
            if not np.isfinite(ic): return 'I_out'
            d = abs(ic - mu_i)
            if d <= sig_i:        return 'I1'
            if d <= 2.0 * sig_i:  return 'I2'
            if d <= 3.0 * sig_i:  return 'I3'
            return 'I_out'

        cfs = []
        for ch_id, r in good_rows:
            g  = r.get('gain',      np.nan)
            ic = r.get('intercept', np.nan)
            cfs.append(dict(
                ch_id    = ch_id,
                gain     = g,
                intercept= ic,
                gc       = _gc(g),
                icc      = _ic(ic),
                i_posit  = (np.isfinite(ic) and ic > 0),
                pe_issue = bool(r.get('has_1pe_issue', False)),
            ))

        # ── helper predicates ─────────────────────────────────────────────
        def _has(cf, feat):
            if feat == 'G_out':     return cf['gc']  == 'G_out'
            if feat == 'I_out':     return cf['icc'] == 'I_out'
            if feat == 'I_posit':   return cf['i_posit']
            if feat == '1PE_issue': return cf['pe_issue']
            raise ValueError(feat)

        def _count(feat_list):
            return sum(1 for cf in cfs if all(_has(cf, f) for f in feat_list))

        def _ids(feat_list):
            return sorted(cf['ch_id'] for cf in cfs
                          if all(_has(cf, f) for f in feat_list))

        # ── write ─────────────────────────────────────────────────────────
        fname = os.path.join(out_dir,
                             f'{run_name}_{mname}_good_channels_features.txt')

        with open(fname, 'w') as fout:

            # ─────────────── SECTION 0: definitions ──────────────────────
            fout.write(THICK)
            fout.write("# TAO Gain Calibration — Good Channels Feature Table\n")
            fout.write(f"# Run: {run_name}   Model: {mname}\n")
            fout.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            fout.write(f"# Channels included: 'good' + 'good_1pe_issue'  "
                       f"total = {len(cfs)}\n")
            fout.write(f"# Gain distribution  :  mu_g  = {mu_g:.2f},  "
                       f"sig_g = {sig_g:.2f} ADC/PE\n")
            fout.write(f"# Intercept distrib. :  mu_i  = {mu_i:.2f},  "
                       f"sig_i = {sig_i:.2f} ADC\n")
            fout.write(THICK)
            fout.write("# SECTION 0 - Category definitions\n")
            fout.write("#\n")
            fout.write("# Gain categories  (mu_g, sig_g computed over all good channels)\n")
            fout.write("#   G1       : gain in  [mu_g - sig_g  ; mu_g + sig_g]\n")
            fout.write("#   G2       : gain in  [mu_g - 2*sig_g; mu_g + 2*sig_g]"
                       "  but outside G1\n")
            fout.write("#   G3       : gain in  [mu_g - 3*sig_g; mu_g + 3*sig_g]"
                       "  but outside G2\n")
            fout.write("#   G_out    : gain outside [mu_g - 3*sig_g; mu_g + 3*sig_g]\n")
            fout.write("#\n")
            fout.write("# Intercept categories  (mu_i, sig_i computed over all good channels)\n")
            fout.write("#   I1       : intercept in  [mu_i - sig_i  ; mu_i + sig_i]\n")
            fout.write("#   I2       : intercept in  [mu_i - 2*sig_i; mu_i + 2*sig_i]"
                       "  but outside I1\n")
            fout.write("#   I3       : intercept in  [mu_i - 3*sig_i; mu_i + 3*sig_i]"
                       "  but outside I2\n")
            fout.write("#   I_out    : intercept outside [mu_i - 3*sig_i; mu_i + 3*sig_i]\n")
            fout.write("#   I_posit  : intercept > 0\n")
            fout.write("#\n")
            fout.write("# Additional flag\n")
            fout.write("#   1PE_issue : 1PE peak bin count < 2PE peak bin count"
                       " in the raw ADC histogram\n")
            fout.write("#               Fit is still performed; channel classified"
                       " as 'good_1pe_issue'\n")
            fout.write(THICK)

            # ─────────────── Per-channel table ───────────────────────────
            fout.write("# CHANNEL TABLE  (yes/no flags for each category)\n")
            hdr = (f"{'Channel':<10} {'Gain':>12} {'Intercept':>12} "
                   f"{'G1':>5} {'G2':>5} {'G3':>5} {'G_out':>7} "
                   f"{'I1':>5} {'I2':>5} {'I3':>5} {'I_out':>7} "
                   f"{'I_posit':>9} {'1PE_issue':>11}\n")
            fout.write(SEP)
            fout.write(hdr)
            fout.write(SEP)
            for cf in sorted(cfs, key=lambda x: x['ch_id']):
                g_s  = (f"{cf['gain']:.2f}"      if np.isfinite(cf['gain'])
                        else 'nan')
                ic_s = (f"{cf['intercept']:.2f}" if np.isfinite(cf['intercept'])
                        else 'nan')
                fout.write(
                    f"{cf['ch_id']:<10} {g_s:>12} {ic_s:>12} "
                    f"{'yes' if cf['gc']  == 'G1'    else 'no':>5} "
                    f"{'yes' if cf['gc']  == 'G2'    else 'no':>5} "
                    f"{'yes' if cf['gc']  == 'G3'    else 'no':>5} "
                    f"{'yes' if cf['gc']  == 'G_out' else 'no':>7} "
                    f"{'yes' if cf['icc'] == 'I1'    else 'no':>5} "
                    f"{'yes' if cf['icc'] == 'I2'    else 'no':>5} "
                    f"{'yes' if cf['icc'] == 'I3'    else 'no':>5} "
                    f"{'yes' if cf['icc'] == 'I_out' else 'no':>7} "
                    f"{'yes' if cf['i_posit']         else 'no':>9} "
                    f"{'yes' if cf['pe_issue']         else 'no':>11}\n"
                )
            fout.write(SEP)

            # ─────────────── SECTION 1: count summary ────────────────────
            fout.write("\n")
            fout.write(THICK)
            fout.write("# SECTION 1 - Channel count summary\n")
            fout.write(f"# Total good channels: {len(cfs)}\n")
            fout.write("#\n")

            # Single G categories
            for gc in G_CATS:
                n = sum(1 for cf in cfs if cf['gc'] == gc)
                fout.write(f"$ {gc:<12} = {n} CHN\n")
            fout.write("#\n")

            # G x I combinations
            for gc in G_CATS:
                for ic in I_CATS:
                    if ic == 'I_posit':
                        n = sum(1 for cf in cfs
                                if cf['gc'] == gc and cf['i_posit'])
                    else:
                        n = sum(1 for cf in cfs
                                if cf['gc'] == gc and cf['icc'] == ic)
                    fout.write(f"$ {gc:<7} & {ic:<12} = {n} CHN\n")
                fout.write("#\n")

            # Single I categories
            for ic in I_CATS:
                if ic == 'I_posit':
                    n = sum(1 for cf in cfs if cf['i_posit'])
                else:
                    n = sum(1 for cf in cfs if cf['icc'] == ic)
                fout.write(f"$ {ic:<12} = {n} CHN\n")
            fout.write("#\n")

            # 1PE_issue alone
            n_iss = sum(1 for cf in cfs if cf['pe_issue'])
            fout.write(f"$ {'1PE_issue':<12} = {n_iss} CHN\n")
            fout.write("#\n")

            # 1PE_issue x G
            for gc in G_CATS:
                n = sum(1 for cf in cfs if cf['pe_issue'] and cf['gc'] == gc)
                fout.write(f"$ {'1PE_issue':<7} & {gc:<12} = {n} CHN\n")
            fout.write("#\n")

            # 1PE_issue x I
            for ic in I_CATS:
                if ic == 'I_posit':
                    n = sum(1 for cf in cfs if cf['pe_issue'] and cf['i_posit'])
                else:
                    n = sum(1 for cf in cfs
                            if cf['pe_issue'] and cf['icc'] == ic)
                fout.write(f"$ {'1PE_issue':<7} & {ic:<12} = {n} CHN\n")
            fout.write(THICK)

            # ─────────────── SECTION 2: channel ID lists ─────────────────
            fout.write("# SECTION 2 - Channel ID lists for exceptional features\n")
            fout.write("#   Features: G_out, I_out, I_posit, 1PE_issue\n")
            fout.write("#   All subsets of size 1..4 are listed.\n")
            fout.write("#   Same-quantity combinations (e.g. I_out & I_posit)"
                       " are included.\n")
            fout.write("#\n")

            for size in range(1, len(SPECIAL) + 1):
                for combo in combinations(SPECIAL, size):
                    label = ' & '.join(combo)
                    ids   = _ids(list(combo))
                    fout.write(f"# {label}  ({len(ids)} CHN):\n")
                    if not ids:
                        fout.write("#   (none)\n")
                    else:
                        for k in range(0, len(ids), 10):
                            chunk = ids[k:k + 10]
                            fout.write(
                                "#   " + ', '.join(str(c) for c in chunk) + '\n')
                    fout.write("#\n")

            fout.write(THICK)

        log.info(f"  -> {fname}  ({len(cfs)} good channels)")


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
                p16=float(np.percentile(a, 16)),
                p84=float(np.percentile(a, 84)))


def write_summary(all_results, models, out_dir, run_name, chi2_max, r2_min):
    fname = os.path.join(out_dir, f'summary_{run_name}.txt')
    lines = []
    W     = 78

    def hdr(s):
        lines.append('=' * W); lines.append(f'  {s}'); lines.append('=' * W)

    def sub(s):
        lines.append('-' * W); lines.append(f'  {s}'); lines.append('-' * W)

    def fmt_stats(label, s):
        lines.append(
            f"    {label:<20s}  n={s['n']:5d}  "
            f"mean={s['mean']:10.3f}  std={s['std']:9.3f}  "
            f"median={s['median']:10.3f}  "
            f"[{s['p16']:.3f}, {s['p84']:.3f}] (68%)")

    hdr('TAO GAIN CALIBRATION SUMMARY')
    lines.append(f'  Run: {run_name}')
    lines.append(f'  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'  Quality cuts: chi2/ndf <= {chi2_max}  R2 >= {r2_min}')
    lines.append(f'  (Gain range removed from classification)')
    lines.append(f'  Total channels: {len(all_results)}')
    lines.append('')

    for mname in models:
        sub(f'MODEL: {MODEL_LABELS.get(mname, mname)}  ({mname})')
        cats = {c: [] for c in ALL_CATS}
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, chi2_max=chi2_max, r2_min=r2_min)
            cats[cat].append(r)

        ng  = len(cats['good'])
        ni  = len(cats['good_1pe_issue'])
        nb  = len(cats['bad'])
        nf  = len(cats['failed'])
        tot = ng + ni + nb + nf
        lines.append(f'  Channels:  good={ng} ({100*ng/tot:.1f}%)  '
                     f'1PE_issue={ni} ({100*ni/tot:.1f}%)  '
                     f'bad={nb} ({100*nb/tot:.1f}%)  '
                     f'failed={nf} ({100*nf/tot:.1f}%)  total={tot}')
        lines.append('')

        for catname, rlist in [('GOOD', cats['good']),
                                ('GOOD_1PE_ISSUE', cats['good_1pe_issue']),
                                ('BAD', cats['bad'])]:
            if not rlist:
                continue
            lines.append(f'  -- {catname} channels ({len(rlist)}) --')
            fmt_stats('Gain [ADC/PE]',
                      _stats([r.get('gain',      np.nan) for r in rlist]))
            fmt_stats('chi2/ndf',
                      _stats([r.get('chi2_dof',  np.nan) for r in rlist]))
            fmt_stats('R2 (linear)',
                      _stats([r.get('r2_linear', np.nan) for r in rlist]))
            fmt_stats('Lin chi2/ndf',
                      _stats([r.get('linear_chi2_dof', np.nan) for r in rlist]))
            if mname in ('emg', 'emg_ap'):
                fmt_stats('tau [ADC]',
                          _stats([r.get('extra', {}).get('tau',      np.nan)
                                  for r in rlist]))
                fmt_stats('p_ct (tau/G)',
                          _stats([r.get('extra', {}).get('p_ct_emg', np.nan)
                                  for r in rlist]))
            if mname == 'multigauss_ct':
                fmt_stats('p_ct (binom)',
                          _stats([r.get('extra', {}).get('p_ct',     np.nan)
                                  for r in rlist]))
            if mname in ('multigauss_ap', 'emg_ap'):
                fmt_stats('alpha (AP)',
                          _stats([r.get('extra', {}).get('alpha',    np.nan)
                                  for r in rlist]))
                fmt_stats('Q_ap/Gain',
                          _stats([r.get('extra', {}).get('q_ap_rel', np.nan)
                                  for r in rlist]))
            lines.append('')

    lines += ['=' * W, 'END OF SUMMARY', '=' * W]
    with open(fname, 'w') as fout:
        fout.write('\n'.join(lines) + '\n')
    log.info(f'Summary written to {fname}')
    return fname


# =============================================================================
# MAIN
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(description='TAO SiPM gain calibration')
    p.add_argument('input_root', help='Input ROOT file with ADC histograms')
    p.add_argument('output_dir', help='Output directory')
    p.add_argument('run_name',   help='Run identifier string (used in filenames)')
    p.add_argument('--use-raw',  action='store_true',
                   help='Use raw (non-vetoed) histograms')
    p.add_argument('--plots',    choices=('none', 'sample', 'all'), default='all',
                   help='Plot mode [default: all (every channel)]')
    p.add_argument('--models',   default='all',
                   help='Comma-separated model list or "all" [default: all]')
    p.add_argument('--n-peaks',  type=int, default=None,
                   help='Force fixed number of PE peaks [default: auto]')
    p.add_argument('--workers',  type=int, default=max(1, cpu_count() - 1),
                   help='Parallel workers [default: CPU count - 1]')
    p.add_argument('--chi2-max', type=float, default=CHI2_MAX,
                   help=f'Maximum chi2/ndf for "good" [default: {CHI2_MAX}]')
    p.add_argument('--r2-min',   type=float, default=R2_MIN,
                   help=f'Minimum linear R2 for "good" [default: {R2_MIN}]')
    p.add_argument('--coti',     action='store_true',
                   help='Apply COTI threshold erf correction to 1PE peak')
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # ── Model selection ───────────────────────────────────────────────────────
    if args.models == 'all':
        models = list(MODEL_NAMES)
    else:
        models = [m.strip() for m in args.models.split(',')]
        for m in models:
            if m not in MODEL_NAMES:
                log.error(f"Unknown model '{m}'. Valid: {list(MODEL_NAMES)}")
                sys.exit(1)
    log.info(f'Models: {models}')
    log.info(f'Quality cuts: chi2/ndf<={args.chi2_max}  R2>={args.r2_min}  '
             f'(no gain range cut)')

    # ── Load histograms ───────────────────────────────────────────────────────
    log.info(f'Loading histograms from {args.input_root}')
    histograms = load_histograms(args.input_root, use_raw=args.use_raw)
    log.info(f'Total channels loaded: {len(histograms)}')

    # ── Inject config for workers ─────────────────────────────────────────────
    global _WORKER_ARGS
    _WORKER_ARGS.update(
        models=models,
        n_peaks_forced=args.n_peaks,
        apply_coti=args.coti,
    )

    # ── Run fits in parallel ──────────────────────────────────────────────────
    log.info(f'Fitting {len(histograms)} channels with {args.workers} worker(s)...')
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

    # ── Save outputs ──────────────────────────────────────────────────────────
    log.info('Saving CSV results...')
    save_csvs(all_results, models, args.output_dir, args.run_name,
              args.chi2_max, args.r2_min)

    log.info('Saving TXT tables...')
    save_txts(all_results, models, args.output_dir, args.run_name,
              args.chi2_max, args.r2_min)

    log.info('Saving good-channels features TXT...')
    save_good_channels_features(
        all_results, models, args.output_dir, args.run_name,
        args.chi2_max, args.r2_min)

    # ── Plots ─────────────────────────────────────────────────────────────────
    if args.plots != 'none':
        log.info(f'Generating plots (mode={args.plots})...')
        plot_dirs = _make_plot_dirs(args.output_dir, models)

        to_plot = {}
        for mname in models:
            cats = defaultdict(list)
            for ch_id, mres in all_results.items():
                r   = mres.get(mname, {})
                cat = classify(r, chi2_max=args.chi2_max, r2_min=args.r2_min)
                cats[cat].append(ch_id)
            if args.plots == 'sample':
                sel = {}
                rng = random.Random(42)
                for cat, chs in cats.items():
                    sel[cat] = rng.sample(chs, min(SAMPLE_N, len(chs)))
                to_plot[mname] = sel
            else:
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
            subset  = {
                m: mres.get(m, {}) for m in models
                if ch_id in to_plot.get(m, {}).get(
                    classify(mres.get(m, {}),
                             chi2_max=args.chi2_max, r2_min=args.r2_min), [])
            }
            if subset:
                plot_fit(ch_id, hist_ch, subset, peaks, plot_dirs,
                         chi2_max=args.chi2_max, r2_min=args.r2_min)

        plot_overview(all_results, models, args.output_dir, args.run_name,
                      chi2_max=args.chi2_max, r2_min=args.r2_min)

    # ── Summary ───────────────────────────────────────────────────────────────
    write_summary(all_results, models, args.output_dir, args.run_name,
                  args.chi2_max, args.r2_min)

    # ── Console ───────────────────────────────────────────────────────────────
    print('\n' + '=' * 72)
    print(f'  GAIN CALIBRATION COMPLETE  --  Run {args.run_name}')
    print('=' * 72)
    for mname in models:
        ng = ni = nb = nf = 0
        gains = []
        for mres in all_results.values():
            r   = mres.get(mname, {})
            cat = classify(r, chi2_max=args.chi2_max, r2_min=args.r2_min)
            if cat == 'good':
                ng += 1; gains.append(r['gain'])
            elif cat == 'good_1pe_issue':
                ni += 1; gains.append(r['gain'])
            elif cat == 'bad':
                nb += 1
            else:
                nf += 1
        g_str = (f"{np.mean(gains):.0f} +/- {np.std(gains):.0f}"
                 if gains else 'n/a')
        print(f"  {mname:<20s}  good={ng:5d}  1PE_iss={ni:5d}  "
              f"bad={nb:5d}  fail={nf:5d}  <gain>={g_str}")
    print('=' * 72 + '\n')


if __name__ == '__main__':
    main()
