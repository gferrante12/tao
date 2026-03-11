#!/usr/bin/env python3
"""
gain_calibration_stable.py
==========================
Stable gain calibration: ROOT-only, multi-Gaussian fit with TSpectrum peak detection.
Uses ROOT integrated statistics (fit_result.Chi2(), fit_result.Ndf(), etc.).

Three classification methods:
  A) Standard:  chi2/ndf + R2 + gain range  (original)
  B) Relaxed:   bad fits reclassified as good if R2 >= 0.98 AND gain in range
  C) R2-only:   good if R2 >= 0.98 (ignore chi2 and gain range)

Three classification labels (all methods):
  good        — passes all quality criteria AND n_peaks >= 3
  bad         — fit succeeded but quality criteria not met OR n_peaks < 3
  failed      — fit did not converge / insufficient data

Outputs per method:
  - RUNXXXX_fit_quality_piechart_METHOD.png
  - RUNXXXX_summary_plots_METHOD.png          (2 rows: good / bad)
  - RUNXXXX_{METHOD}_{good|bad|failed}.csv/.txt
  - RUNXXXX_classification_comparison.txt

Usage:
  python gain_calibration_stable.py input.root output_dir RUN1295
  python gain_calibration_stable.py input.root output_dir RUN1295 --use-raw
  python gain_calibration_stable.py input.root output_dir RUN1295 --no-plots

Channel fit plots (default behaviour):
  - Good:   random sample of 100 channels
  - Bad:    all channels
  - Failed: only channels with non-zero histogram entries
"""

import argparse
import logging
import os
import sys
import random
from multiprocessing import Pool, cpu_count

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        return it

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kWarning
except ImportError:
    print("ERROR: ROOT (PyROOT) is required for this script.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# =============================================================================
# CONSTANTS
# =============================================================================
BIN_WIDTH  = 100
BIN_MAX    = 50000
BINS       = np.arange(0, BIN_MAX + BIN_WIDTH, BIN_WIDTH)
BIN_CENTERS = (BINS[:-1] + BINS[1:]) / 2.0
N_BINS     = len(BIN_CENTERS)

# Fit quality thresholds
CHI2_MAX           = 160.0
LINEAR_R2_MIN      = 0.99
R2_RELAXED_MIN     = 0.99     # Method B & C threshold

# Peak detection
MAX_PEAKS          = 8
MAX_ADC_SEARCH     = 50000
PEAK_WIDTH         = 1200.0
MAX_SIGMA          = 3000.0

# First peak range
FIRST_PEAK_MIN     = 1500
FIRST_PEAK_MAX     = 9000

# Expected gain
EXPECTED_GAIN_MIN     = 3000
EXPECTED_GAIN_MAX     = 9000
EXPECTED_GAIN_DEFAULT = 6000

USE_FIRST_PEAK = True

# Gaussian helper (numpy)
def gaussian(x, A, mu, sigma):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

def multi_gauss(x, *params):
    y = np.zeros_like(x, dtype=float)
    for i in range(len(params) // 3):
        y += gaussian(x, params[3*i], params[3*i+1], params[3*i+2])
    return y

# =============================================================================
# ADAPTIVE GAIN CONSTRAINTS
# =============================================================================
def get_adaptive_constraints(estimated_gain):
    base_gain = EXPECTED_GAIN_DEFAULT
    ratio = estimated_gain / base_gain
    return {
        'min_spacing':    int(EXPECTED_GAIN_MIN * ratio),
        'max_spacing':    int(EXPECTED_GAIN_MAX * ratio),
        'first_peak_min': int(FIRST_PEAK_MIN * ratio),
        'first_peak_max': int(FIRST_PEAK_MAX * ratio),
        'peak_width':     PEAK_WIDTH * ratio,
        'fit_margin':     3.0 * ratio,
    }

def estimate_gain_from_peaks(peaks):
    if len(peaks) < 2:
        return -1
    spacings = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
    return np.clip(np.median(spacings), EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX)

# =============================================================================
# PEAK FILTERING
# =============================================================================
def filter_peaks_adaptive(peaks, hist_data, constraints):
    if not peaks:
        return []
    peaks = sorted([p for p in peaks if p <= MAX_ADC_SEARCH])
    if not peaks:
        return []

    # Find first peak in valid range
    candidates = [p for p in peaks if constraints['first_peak_min'] <= p <= constraints['first_peak_max']]
    if not candidates:
        reasonable = [p for p in peaks if 1000 < p < 10000]
        if reasonable:
            first_peak = reasonable[0]
        else:
            return []
    else:
        heights = [hist_data[np.abs(BIN_CENTERS - p).argmin()] for p in candidates]
        first_peak = candidates[int(np.argmax(heights))]

    valid = [first_peak]
    for p in peaks:
        if p <= first_peak:
            continue
        spacing = p - valid[-1]
        if constraints['min_spacing'] < spacing <= constraints['max_spacing']:
            valid.append(p)
            if len(valid) >= MAX_PEAKS:
                break

    if len(valid) < 2:
        return []

    # Enforce decreasing height (5% tolerance)
    heights = [hist_data[np.abs(BIN_CENTERS - p).argmin()] for p in valid]
    for i in range(len(heights) - 1):
        if heights[i+1] > heights[i] * 1.05:
            valid = valid[:i+1]
            break

    return valid if len(valid) >= 2 else []

# =============================================================================
# ROOT CHANNEL FITTING (multi-Gaussian via TF1 + TSpectrum)
# =============================================================================
def process_channel_root(ch_id, hist_data):
    """Fit one channel using ROOT TSpectrum + TF1 multi-Gaussian."""
    result = {
        'channel_id': ch_id, 'method': 'root_multigauss',
        'gain': 0.0, 'gain_error': 0.0,
        'intercept': 0.0, 'intercept_error': 0.0,
        'fit_status': -1, 'chi2_dof': -1.0,
        'n_peaks': 0, 'hist': hist_data,
        'detected_peaks': [], 'fit_params': [],
        'linear_r2': 0.0, 'linear_chi2_dof': -1.0,
    }

    if np.sum(hist_data) < 1000:
        return result

    estimated_gain = EXPECTED_GAIN_DEFAULT
    constraints = get_adaptive_constraints(estimated_gain)

    # Build ROOT histogram
    nbins = len(hist_data)
    xmin = BIN_CENTERS[0] - BIN_WIDTH / 2
    xmax = BIN_CENTERS[-1] + BIN_WIDTH / 2
    h = ROOT.TH1D(f"h_stable_{ch_id}", "", nbins, xmin, xmax)
    for i, val in enumerate(hist_data):
        h.SetBinContent(i + 1, val)

    # TSpectrum peak search
    spectrum = ROOT.TSpectrum(MAX_PEAKS + 2)
    n_found = spectrum.Search(h, 4.0, "", 0.0005)
    if n_found < 2:
        del h
        return result

    xpeaks = spectrum.GetPositionX()
    peaks = sorted([xpeaks[i] for i in range(n_found)])

    # Update gain estimate
    if len(peaks) >= 2:
        estimated_gain = estimate_gain_from_peaks(peaks)
        constraints = get_adaptive_constraints(estimated_gain)

    peaks = filter_peaks_adaptive(peaks, hist_data, constraints)
    if len(peaks) < 2:
        del h
        return result

    result['detected_peaks'] = peaks
    result['n_peaks'] = len(peaks)

    fit_peaks = peaks
    first_peak_number = 1
    n_fit_peaks = len(fit_peaks)

    # Fit range
    fit_min = fit_peaks[0] - constraints['peak_width'] * constraints['fit_margin']
    fit_max = fit_peaks[-1] + constraints['peak_width'] * constraints['fit_margin']

    # Build ROOT TF1 formula
    parts = []
    for i in range(n_fit_peaks):
        a, m, s = 3*i, 3*i+1, 3*i+2
        parts.append(f"[{a}]*exp(-0.5*((x-[{m}])/[{s}])^2)")
    formula = "+".join(parts)
    f1 = ROOT.TF1(f"fit_stable_{ch_id}", formula, fit_min, fit_max)

    # Estimate base sigma via FWHM
    bin0 = h.FindBin(fit_peaks[0])
    amp0 = h.GetBinContent(bin0)
    hm = amp0 / 2.0
    lb, rb = bin0, bin0
    while lb > 1 and h.GetBinContent(lb) > hm:
        lb -= 1
    while rb < h.GetNbinsX() and h.GetBinContent(rb) > hm:
        rb += 1
    fwhm = h.GetBinCenter(rb) - h.GetBinCenter(lb)
    base_sigma = fwhm / 2.355 if fwhm > 0 else constraints['peak_width']
    base_sigma = np.clip(base_sigma, 0.15 * estimated_gain, 0.4 * estimated_gain)

    # Set initial parameters and limits
    for j, pk in enumerate(fit_peaks):
        bidx = h.FindBin(pk)
        amp_est = h.GetBinContent(bidx)
        pe_num = first_peak_number + j
        sig_est = base_sigma * np.sqrt(pe_num / first_peak_number)
        mu_tol = 0.3 * estimated_gain

        f1.SetParameter(3*j,     amp_est)
        f1.SetParameter(3*j + 1, pk)
        f1.SetParameter(3*j + 2, sig_est)
        f1.SetParLimits(3*j,     0.05 * amp_est, 20 * amp_est)
        f1.SetParLimits(3*j + 1, pk - mu_tol, pk + mu_tol)
        f1.SetParLimits(3*j + 2, 0.2 * sig_est, min(4.0 * sig_est, MAX_SIGMA))

    # Fit using ROOT (S=return result, R=range, B=use par limits, Q=quiet)
    fit_result = h.Fit(f1, "SRBQ", "", fit_min, fit_max)
    if not fit_result or int(fit_result) != 0:
        del h, f1
        return result

    result['fit_status'] = 1

    # Extract parameters from ROOT fit_result
    fp = []
    for j in range(n_fit_peaks):
        fp.extend([fit_result.Parameter(3*j),
                   fit_result.Parameter(3*j + 1),
                   fit_result.Parameter(3*j + 2)])
    result['fit_params'] = fp

    # Chi2/ndf from ROOT integrated statistics
    chi2 = fit_result.Chi2()
    ndf  = fit_result.Ndf()
    result['chi2_dof'] = chi2 / ndf if ndf > 0 else -1.0

    # Extract peak means and errors
    mu_vals = [fit_result.Parameter(3*j + 1) for j in range(n_fit_peaks)]
    mu_errs = [fit_result.ParError(3*j + 1)  for j in range(n_fit_peaks)]

    # Linear fit: mu_n = intercept + gain * n  (ROOT TGraphErrors)
    peak_numbers = np.arange(first_peak_number, first_peak_number + n_fit_peaks)
    gr = ROOT.TGraphErrors(n_fit_peaks)
    for j in range(n_fit_peaks):
        gr.SetPoint(j, float(peak_numbers[j]), mu_vals[j])
        gr.SetPointError(j, 0.0, mu_errs[j])

    lin_f = ROOT.TF1(f"lin_stable_{ch_id}", "pol1",
                      float(first_peak_number), float(first_peak_number + n_fit_peaks - 1))
    lin_res = gr.Fit(lin_f, "SRQ")

    if lin_res and int(lin_res) == 0:
        result['intercept']       = lin_res.Parameter(0)
        result['intercept_error'] = lin_res.ParError(0)
        result['gain']            = lin_res.Parameter(1)
        result['gain_error']      = lin_res.ParError(1)
        lc2 = lin_res.Chi2()
        lndf = lin_res.Ndf()
        result['linear_chi2_dof'] = lc2 / lndf if lndf > 0 else -1.0

        # R2
        y_mean = np.mean(mu_vals)
        ss_tot = np.sum((np.array(mu_vals) - y_mean)**2)
        y_pred = [result['intercept'] + result['gain'] * pn for pn in peak_numbers]
        ss_res = np.sum((np.array(mu_vals) - np.array(y_pred))**2)
        result['linear_r2'] = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    del h, f1, gr, lin_f
    return result

# =============================================================================
# CLASSIFICATION METHODS
# =============================================================================
def classify_A(r):
    """Method A: chi2/ndf + R2 + gain range (standard).
    Requires n_peaks >= 3 for 'good'; n_peaks < 3 -> 'bad'."""
    if r['fit_status'] != 1:
        return 'failed'
    if r['n_peaks'] < 3:
        return 'bad'
    if (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN
            and EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX):
        return 'good'
    return 'bad'

def classify_B(r):
    """Method B: same as A, but bad fits reclassified as good if R2 >= 0.98 AND gain in range.
    Requires n_peaks >= 3 for 'good'; n_peaks < 3 -> 'bad'."""
    if r['fit_status'] != 1:
        return 'failed'
    if r['n_peaks'] < 3:
        return 'bad'
    # First check standard
    if (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN
            and EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX):
        return 'good'
    # Relaxed: reclassify bad -> good if R2 >= 0.98 AND gain in range
    if r['linear_r2'] >= R2_RELAXED_MIN and EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX:
        return 'good'
    return 'bad'

def classify_C(r):
    """Method C: R2-only (good if R2 >= 0.98, ignore chi2 and gain range).
    Requires n_peaks >= 3 for 'good'; n_peaks < 3 -> 'bad'."""
    if r['fit_status'] != 1:
        return 'failed'
    if r['n_peaks'] < 3:
        return 'bad'
    if r['linear_r2'] >= R2_RELAXED_MIN:
        return 'good'
    return 'bad'

CLASSIFIERS = {
    'A_standard':    classify_A,
    'B_relaxed_r2':  classify_B,
    'C_r2_only':     classify_C,
}

METHOD_LABELS = {
    'A_standard':    'Method A: chi2/ndf + R2 + gain range  [good>=3pk / bad / failed]',
    'B_relaxed_r2':  'Method B: A + reclassify if R2>=0.98 & gain OK  [good>=3pk / bad / failed]',
    'C_r2_only':     'Method C: R2>=0.98 only  [good>=3pk / bad / failed]',
}

def split_results(results, classifier_fn):
    """Split results into good, bad, failed using the given classifier."""
    good, bad, failed = [], [], []
    for r in results:
        label = classifier_fn(r)
        if label == 'good':
            good.append(r)
        elif label == 'bad':
            bad.append(r)
        else:
            failed.append(r)
    return good, bad, failed

# =============================================================================
# HELPER: distribution statistics
# =============================================================================
def dist_stats(values):
    """Return min, max, mean, RMS (std) for a list of values."""
    if not values:
        return {'min': 0, 'max': 0, 'mean': 0, 'rms': 0, 'n': 0}
    a = np.array(values)
    return {'min': float(a.min()), 'max': float(a.max()),
            'mean': float(a.mean()), 'rms': float(a.std()), 'n': len(a)}

# =============================================================================
# PLOTTING: Pie chart per method
# =============================================================================
def plot_piechart(good, bad, failed, method_key, run_name, out_dir):
    n_g, n_b, n_f = len(good), len(bad), len(failed)
    n_tot = n_g + n_b + n_f
    if n_tot == 0:
        return
    pct = lambda n: 100.0 * n / n_tot

    fig, ax = plt.subplots(figsize=(10, 8))
    sizes  = [n_g,  n_b,  n_f]
    labels = [
        f'Good (>=3 peaks)\n{n_g} ({pct(n_g):.1f}%)',
        f'Bad\n{n_b} ({pct(n_b):.1f}%)',
        f'Failed\n{n_f} ({pct(n_f):.1f}%)',
    ]
    colors  = ['#90EE90', '#FFA07A', '#FFB6C6']
    # Explode small slices more to separate overlapping labels
    explode = [0.05 if s / n_tot > 0.10 else 0.15 for s in sizes]

    # Hide slices with 0 count to keep the chart clean
    nonzero = [(s, l, c, e) for s, l, c, e in zip(sizes, labels, colors, explode) if s > 0]
    if nonzero:
        sizes_, labels_, colors_, explode_ = zip(*nonzero)
    else:
        sizes_, labels_, colors_, explode_ = sizes, labels, colors, explode

    wedges, texts = ax.pie(sizes_, explode=explode_, labels=labels_, colors=colors_,
                           startangle=90, labeldistance=1.15,
                           textprops=dict(fontsize=11, fontweight='bold'))

    # Nudge labels apart when two adjacent slices are both small
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            pos_i = texts[i].get_position()
            pos_j = texts[j].get_position()
            dy = abs(pos_i[1] - pos_j[1])
            dx = abs(pos_i[0] - pos_j[0])
            if dy < 0.25 and dx < 0.6:
                # Push them apart vertically
                shift = (0.25 - dy) / 2 + 0.05
                if pos_i[1] >= pos_j[1]:
                    texts[i].set_position((pos_i[0], pos_i[1] + shift))
                    texts[j].set_position((pos_j[0], pos_j[1] - shift))
                else:
                    texts[i].set_position((pos_i[0], pos_i[1] - shift))
                    texts[j].set_position((pos_j[0], pos_j[1] + shift))

    # Pull the "Failed" label ~2 cm closer to the pie.
    # Figure is 10x8 in, data span ~3 units -> 2 cm ~ 0.24 data-units.
    for txt in texts:
        if txt.get_text().startswith('Failed'):
            x0, y0 = txt.get_position()
            # Move towards centre (sign of y0 tells which hemisphere)
            shift = 0.24 if y0 < 0 else -0.24
            txt.set_position((x0, y0 + shift))

    ax.axis('equal')
    plt.title(f'{run_name} — {METHOD_LABELS[method_key]}\nTotal: {n_tot}',
              fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    path = os.path.join(out_dir, f'{run_name}_fit_quality_piechart_{method_key}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"Saved {path}")

# =============================================================================
# PLOTTING: Summary plots per method (2x4 grid: good row, bad row)
# =============================================================================
def _auto_range(vals):
    """Return (lo, hi) that shows every entry: min*0.9 .. max*1.1."""
    vmin, vmax = np.min(vals), np.max(vals)
    lo = vmin * 0.9 if vmin > 0 else vmin - 0.1 * abs(vmax - vmin)
    hi = vmax * 1.1 if vmax > 0 else vmax + 0.1 * abs(vmax - vmin)
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    return (lo, hi)


def _plot_dist_row(axes, fits, row, category, gain_min, gain_max, is_good=False):
    """Plot one row (4 columns: gain, intercept, chi2/ndf, R2) for a category."""
    if 'Bad' in category:
        color_main = 'red'
    else:
        color_main = 'green'

    # Col 0: Gain
    ax = axes[row, 0]
    vals = [r['gain'] for r in fits if r['gain'] > 0]
    if vals:
        mu, std = np.mean(vals), np.std(vals)
        rng = _auto_range(vals)
        ax.hist(vals, bins=50, range=rng, color=color_main, alpha=0.7, edgecolor='k')
        ax.axvline(mu, c='red', ls='--', lw=2)
        ax.set_yscale('log')
        ax.text(0.65, 0.97, f'N={len(vals)}\nmu={mu:.1f}\nsigma={std:.1f}',
                transform=ax.transAxes, va='top', fontsize=8, family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'{category}: Gain', fontweight='bold', fontsize=10)
    ax.set_xlabel('Gain (ADC/PE)')
    ax.grid(True, alpha=0.3)

    # Col 1: Intercept
    ax = axes[row, 1]
    vals = [r['intercept'] for r in fits]
    if vals:
        mu_i, std_i = np.mean(vals), np.std(vals)
        rng = _auto_range(vals)
        ax.hist(vals, bins=50, range=rng, color=color_main, alpha=0.7, edgecolor='k')
        ax.axvline(mu_i, c='red', ls='--', lw=2)
        ax.set_yscale('log')
        ax.text(0.65, 0.97, f'N={len(vals)}\nmu={mu_i:.1f}\nsigma={std_i:.1f}',
                transform=ax.transAxes, va='top', fontsize=8, family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'{category}: Intercept', fontweight='bold', fontsize=10)
    ax.set_xlabel('Intercept (ADC)')
    ax.grid(True, alpha=0.3)

    # Col 2: chi2/ndf
    ax = axes[row, 2]
    vals = [r['chi2_dof'] for r in fits if r['chi2_dof'] > 0]
    if vals:
        rng = _auto_range(vals)
        ax.hist(vals, bins=50, range=rng, color='blue', alpha=0.7, edgecolor='k')
        ax.set_yscale('log')
    ax.set_title(f'{category}: chi2/ndf', fontweight='bold', fontsize=10)
    ax.set_xlabel('chi2/ndf')
    ax.grid(True, alpha=0.3)

    # Col 3: R2
    ax = axes[row, 3]
    vals = [r['linear_r2'] for r in fits if r['linear_r2'] > 0]
    if vals:
        rng = _auto_range(vals)
        # Good fits: force lower limit to 0.989 for readability
        if is_good:
            rng = (0.989, rng[1])
        ax.hist(vals, bins=50, range=rng, color='purple', alpha=0.7, edgecolor='k')
        ax.set_yscale('log')
    ax.set_title(f'{category}: R2', fontweight='bold', fontsize=10)
    ax.set_xlabel('R2')
    ax.grid(True, alpha=0.3)


def plot_summary(good, bad, method_key, run_name, out_dir):
    # Strip the "[good>=3pk / bad / failed]" suffix from the label
    method_lbl = METHOD_LABELS[method_key].split('[')[0].strip()

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    _plot_dist_row(axes, good, 0, 'Good (>=3 peaks)', EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX, is_good=True)
    _plot_dist_row(axes, bad,  1, 'Bad',               EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX, is_good=False)
    plt.suptitle(f'{run_name} — {method_lbl}', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(out_dir, f'{run_name}_summary_plots_{method_key}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"Saved {path}")

# =============================================================================
# PLOTTING: per-channel fit
# =============================================================================
def plot_channel_fit(result, plot_dir, quality_label):
    ch_id = result['channel_id']
    hist  = result['hist']

    color_map = {
        'good':   'green',
        'bad':    'orange',
        'failed': 'red',
    }
    q_sub         = quality_label.replace('root_multigauss_', '')
    color         = color_map.get(q_sub, 'gray')
    quality_upper = q_sub.upper()

    # ── FAILED: single panel (no linear-fit panel) ────────────────────────────
    if q_sub == 'failed':
        fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
        fig.suptitle(f"Channel {ch_id} (ROOT Multi-Gauss) — {quality_upper}",
                     fontsize=14, color=color, fontweight='bold')

        ax1.step(BIN_CENTERS, hist, where='mid', color='black',
                 linewidth=0.8, label='Data')
        ax1.set_xlabel('ADC', fontsize=12)
        ax1.set_ylabel('Counts', fontsize=12)
        ax1.set_yscale('log')
        y_max = hist.max()
        if y_max > 0:
            ax1.set_ylim(0.5, y_max * 5)
        ax1.set_xlim(0, BIN_MAX)
        ax1.legend(fontsize=9, loc='upper right')
        ax1.grid(True, alpha=0.3)

        info = f"STATUS: FAILED\nEvents: {int(np.sum(hist))}"
        ax1.text(0.02, 0.98, info, transform=ax1.transAxes, va='top', fontsize=9,
                 family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))

        plt.tight_layout()
        q_dir = os.path.join(plot_dir, q_sub)
        os.makedirs(q_dir, exist_ok=True)
        fig.savefig(os.path.join(q_dir, f"ch{ch_id:04d}_{quality_label}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)
        return

    # ── GOOD / BAD: two panels (ADC histogram + linear fit) ──────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"Channel {ch_id} (ROOT Multi-Gauss) — {quality_upper}",
                 fontsize=12, color=color, fontweight='bold')

    # Left: ADC histogram + fit
    ax1.step(BIN_CENTERS, hist, where='mid', color='black', linewidth=0.5, alpha=0.8, label='Data')

    if result['fit_status'] == 1 and result['detected_peaks']:
        peaks = result['detected_peaks']
        for i, pk in enumerate(peaks):
            idx = np.abs(BIN_CENTERS - pk).argmin()
            ax1.plot(pk, hist[idx], 'ro', markersize=5, markeredgecolor='darkred',
                     label=f'{i+1} PE' if i < 3 else '')

        if result['fit_params']:
            n_fp = len(result['fit_params']) // 3
            fp_peaks = peaks[:n_fp] if USE_FIRST_PEAK else peaks[1:n_fp+1]
            fit_min = fp_peaks[0] - PEAK_WIDTH
            fit_max = fp_peaks[-1] + PEAK_WIDTH
            mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
            x_fit = BIN_CENTERS[mask]
            y_fit = multi_gauss(x_fit, *result['fit_params'])
            ax1.plot(x_fit, y_fit, 'b-', linewidth=1.5, alpha=0.8, label='Multi-Gauss fit')

            for i in range(n_fp):
                mu_i = result['fit_params'][3*i + 1]
                sig_i = result['fit_params'][3*i + 2]
                pe = i + 1
                ax1.axvline(mu_i, color=f'C{i}', ls='--', lw=1.2, alpha=0.7,
                            label=f'{pe} PE: mu={mu_i:.0f}, sigma={sig_i:.0f}')

    ax1.set_xlabel('ADC'); ax1.set_ylabel('Counts')
    ax1.set_yscale('log')
    y_max = hist.max()
    if y_max > 0:
        ax1.set_ylim(0.5, y_max * 200)
    ax1.legend(fontsize=7, ncol=2, loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Info box
    if result['fit_status'] == 1:
        info = (f"STATUS: SUCCESS\nQuality: {quality_upper}\n"
                f"Events: {int(np.sum(hist))}\n"
                f"Peaks used: {result['n_peaks']}\n"
                f"chi2/ndf: {result['chi2_dof']:.2f}")
    else:
        info = f"STATUS: FAILED\nEvents: {int(np.sum(hist))}"
    bbox_c = 'lightgreen' if q_sub == 'good' else ('lightyellow' if q_sub == 'bad' else 'lightcoral')
    ax1.text(0.02, 0.98, info, transform=ax1.transAxes, va='top', fontsize=8,
             family='monospace', bbox=dict(boxstyle='round', facecolor=bbox_c, alpha=0.7))

    # Right: linear fit
    if result['fit_status'] == 1 and result['gain'] > 0 and result['fit_params']:
        n_fp = len(result['fit_params']) // 3
        if n_fp >= 2:
            pns = list(range(1, n_fp + 1))
            mus = [result['fit_params'][3*i + 1] for i in range(n_fp)]
            ax2.plot(pns, mus, 'o', color='blue', markersize=8, label='Fitted Means')
            x_l = np.array([1, n_fp])
            y_l = result['intercept'] + result['gain'] * x_l
            ax2.plot(x_l, y_l, 'r-', lw=2.5,
                     label=f"mu = {result['intercept']:.0f} + {result['gain']:.0f}*n")
            ax2.set_xlabel('Peak Number (PE)'); ax2.set_ylabel('ADC')
            ax2.set_title('Gain Calculation', fontweight='bold')
            ax2.legend(loc='lower right', fontsize=9)
            ax2.grid(True, alpha=0.3)
            gain_info = (f"Gain: {result['gain']:.0f} +/- {result['gain_error']:.0f} ADC/PE\n"
                         f"R2: {result['linear_r2']:.4f}\n"
                         f"Lin chi2/ndf: {result['linear_chi2_dof']:.2f}")
            ax2.text(0.05, 0.97, gain_info, transform=ax2.transAxes, va='top',
                     fontsize=9, family='monospace',
                     bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.85))
    else:
        ax2.text(0.5, 0.5, 'No successful fit', transform=ax2.transAxes,
                 ha='center', va='center', fontsize=12, color='red')

    plt.tight_layout()
    q_dir = os.path.join(plot_dir, q_sub)
    os.makedirs(q_dir, exist_ok=True)
    fig.savefig(os.path.join(q_dir, f"ch{ch_id:04d}_{quality_label}.png"),
                dpi=150, bbox_inches='tight')
    plt.close(fig)

# =============================================================================
# COMPARISON TXT
# =============================================================================
def write_comparison_txt(results, run_name, out_dir):
    """Write a TXT file comparing all three classification methods."""
    n_total = len(results)
    path = os.path.join(out_dir, f'{run_name}_classification_comparison.txt')

    with open(path, 'w') as f:
        f.write(f"{'='*110}\n")
        f.write(f"CLASSIFICATION COMPARISON — {run_name}\n")
        f.write(f"Total channels analysed: {n_total}\n")
        f.write(f"NOTE: 'good' requires n_peaks >= 3; channels with n_peaks < 3 are classified as 'bad'\n")
        f.write(f"{'='*110}\n\n")

        # Summary header
        f.write(f"{'Method':<50} {'Good>=3pk':<16} {'Bad':<14} {'Failed':<14}\n")
        f.write(f"{'-'*110}\n")

        method_splits = {}
        for mk, cfn in CLASSIFIERS.items():
            g, b, fl = split_results(results, cfn)
            method_splits[mk] = (g, b, fl)
            ng, nb, nf = len(g), len(b), len(fl)
            pg  = 100*ng  / n_total if n_total else 0
            pb  = 100*nb  / n_total if n_total else 0
            pf  = 100*nf  / n_total if n_total else 0
            f.write(f"{METHOD_LABELS[mk]:<50} "
                    f"{ng:>5} ({pg:>5.1f}%)  "
                    f"{nb:>5} ({pb:>5.1f}%)  "
                    f"{nf:>5} ({pf:>5.1f}%)\n")

        f.write(f"\n{'='*110}\n")
        f.write(f"DETAILED STATISTICS PER METHOD\n")
        f.write(f"{'='*110}\n")

        for mk in CLASSIFIERS:
            g, b, fl = method_splits[mk]
            f.write(f"\n{'─'*110}\n")
            f.write(f"{METHOD_LABELS[mk]}\n")
            f.write(f"{'─'*110}\n")

            for cat_name, cat_list in [('GOOD FITS (>=3 peaks)', g),
                                        ('BAD FITS', b)]:
                f.write(f"\n  {cat_name} ({len(cat_list)} channels):\n")
                if not cat_list:
                    f.write(f"    (none)\n")
                    continue

                # Zero / non-zero histogram breakdown (for bad and failed)
                if 'BAD' in cat_name:
                    n_nz = sum(1 for r in cat_list if np.sum(r['hist']) > 0)
                    n_z  = len(cat_list) - n_nz
                    f.write(f"    Histogram entries:      non-zero = {n_nz},  zero (empty) = {n_z}\n")

                gains      = [r['gain']       for r in cat_list if r['gain'] > 0]
                intercepts = [r['intercept']  for r in cat_list]
                chi2s      = [r['chi2_dof']   for r in cat_list if r['chi2_dof'] > 0]
                r2s        = [r['linear_r2']  for r in cat_list if r['linear_r2'] > 0]

                for dist_name, vals in [('Gain (ADC/PE)', gains),
                                         ('Intercept (ADC)', intercepts),
                                         ('chi2/ndf', chi2s),
                                         ('R2', r2s)]:
                    s = dist_stats(vals)
                    f.write(f"    {dist_name:<25} N={s['n']:>5}  "
                            f"min={s['min']:>10.3f}  max={s['max']:>10.3f}  "
                            f"mean={s['mean']:>10.3f}  RMS={s['rms']:>10.3f}\n")

            # Failed fits: always report zero/non-zero breakdown
            f.write(f"\n  FAILED FITS ({len(fl)} channels):\n")
            if fl:
                n_nz = sum(1 for r in fl if np.sum(r['hist']) > 0)
                n_z  = len(fl) - n_nz
                f.write(f"    Histogram entries:      non-zero = {n_nz},  zero (empty) = {n_z}\n")
            else:
                f.write(f"    (none)\n")

        f.write(f"\n{'='*110}\n")
        f.write(f"END OF COMPARISON\n")
        f.write(f"{'='*110}\n")

    logging.info(f"Saved comparison: {path}")

# =============================================================================
# CSV / TXT output
# =============================================================================
def save_results_csv_txt(result_list, filepath_base):
    """Save results as both CSV-like TXT and machine-readable TXT."""
    import csv
    csv_path = filepath_base + '.csv'
    txt_path = filepath_base + '.txt'

    fieldnames = ['channel_id', 'gain', 'gain_error', 'intercept', 'intercept_error',
                  'n_peaks', 'chi2_dof', 'linear_r2', 'linear_chi2_dof']

    with open(csv_path, 'w', newline='') as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in result_list:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    with open(txt_path, 'w') as tf:
        tf.write(f"{'Channel':<10} {'Gain':<12} {'Gain_Err':<12} {'Intercept':<14} "
                 f"{'Int_Err':<12} {'N_Peaks':<10} {'Chi2/ndf':<12} {'R2':<10} "
                 f"{'Lin_Chi2':<12}\n")
        tf.write("=" * 104 + "\n")
        for r in result_list:
            tf.write(f"{r['channel_id']:<10} {r['gain']:<12.2f} {r['gain_error']:<12.2f} "
                     f"{r['intercept']:<14.2f} {r['intercept_error']:<12.2f} "
                     f"{r['n_peaks']:<10} {r['chi2_dof']:<12.3f} "
                     f"{r['linear_r2']:<10.4f} {r['linear_chi2_dof']:<12.3f}\n")

    logging.info(f"Saved {csv_path} and {txt_path}")

# =============================================================================
# WORKER for multiprocessing
# =============================================================================
def _worker(args):
    ch_id, hist_data = args
    return process_channel_root(ch_id, hist_data)

# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='Stable multi-Gaussian gain calibration (ROOT only, 3 classification methods).\n'
                    'Plots: good=sample100, bad=all, failed=non-zero only.')
    parser.add_argument('input_root', help='Input ROOT file with ADC histograms')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('run_name',   help='Run name (e.g. RUN1295)')
    parser.add_argument('--use-raw', action='store_true',
                        help='Use raw (H_adcraw_*) instead of clean (H_adcClean_*)')
    parser.add_argument('--no-plots', action='store_true',
                        help='Skip channel fit plot generation')
    args = parser.parse_args()

    if not os.path.exists(args.input_root):
        logging.error(f"Input file not found: {args.input_root}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    plot_dir = os.path.join(args.output_dir, f"plots_{args.run_name}")
    os.makedirs(plot_dir, exist_ok=True)
    for sub in ['good', 'bad', 'failed']:
        os.makedirs(os.path.join(plot_dir, sub), exist_ok=True)

    # ── Load histograms ──────────────────────────────────────────────────────
    logging.info(f"Loading histograms from {args.input_root} ...")
    prefix = "H_adcraw_" if args.use_raw else "H_adcClean_"

    f = ROOT.TFile.Open(args.input_root, "READ")
    if not f or f.IsZombie():
        logging.error("Cannot open ROOT file"); sys.exit(1)

    channel_ids = []
    for key in f.GetListOfKeys():
        name = key.GetName()
        if name.startswith(prefix):
            try:
                channel_ids.append(int(name.replace(prefix, "")))
            except ValueError:
                continue
    channel_ids.sort()

    if not channel_ids:
        logging.error("No ADC histograms found!"); f.Close(); sys.exit(1)

    logging.info(f"Found {len(channel_ids)} channels")

    channel_data = []
    for ch in channel_ids:
        h = f.Get(f"{prefix}{ch}")
        if h:
            arr = np.zeros(N_BINS)
            for i, bc in enumerate(BIN_CENTERS):
                bidx = h.FindBin(bc)
                if 1 <= bidx <= h.GetNbinsX():
                    arr[i] = h.GetBinContent(bidx)
            channel_data.append((ch, arr))
        else:
            channel_data.append((ch, np.zeros(N_BINS)))
    f.Close()

    # ── Fit all channels ─────────────────────────────────────────────────────
    n_workers = min(8, max(1, cpu_count() - 1))
    logging.info(f"Fitting {len(channel_data)} channels ({n_workers} workers) ...")

    with Pool(n_workers) as pool:
        results = list(tqdm(pool.imap(_worker, channel_data),
                            total=len(channel_data), desc="Fitting"))

    # ── For each method: classify, plot, save ────────────────────────────────
    for mk, cfn in CLASSIFIERS.items():
        logging.info(f"\n{'='*60}")
        logging.info(f"Classification: {METHOD_LABELS[mk]}")
        good, bad, failed = split_results(results, cfn)
        ng, nb, nf = len(good), len(bad), len(failed)
        logging.info(f"  Good (>=3 peaks): {ng}   Bad: {nb}   Failed: {nf}")

        # Save CSV/TXT per category
        save_results_csv_txt(good,   os.path.join(args.output_dir, f'{args.run_name}_{mk}_good'))
        save_results_csv_txt(bad,    os.path.join(args.output_dir, f'{args.run_name}_{mk}_bad'))
        save_results_csv_txt(failed, os.path.join(args.output_dir, f'{args.run_name}_{mk}_failed'))

        # Pie chart
        plot_piechart(good, bad, failed, mk, args.run_name, args.output_dir)

        # Summary plots
        plot_summary(good, bad, mk, args.run_name, args.output_dir)

    # ── Comparison TXT ───────────────────────────────────────────────────────
    write_comparison_txt(results, args.run_name, args.output_dir)

    # ── Channel fit plots (method A classification for folder sorting) ───────
    if not args.no_plots:
        logging.info(f"\nGenerating channel fit plots ...")
        good_A, bad_A, failed_A = split_results(results, classify_A)

        # Good: always sample <=100
        good_sample = random.sample(good_A, min(100, len(good_A))) if good_A else []
        logging.info(f"  Good: plotting {len(good_sample)}/{len(good_A)} (sampled)")

        # Bad: always plot all
        logging.info(f"  Bad: plotting all {len(bad_A)}")

        # Failed: plot only channels with non-zero histogram entries
        failed_nonzero = [r for r in failed_A if np.sum(r['hist']) > 0]
        failed_zero    = [r for r in failed_A if np.sum(r['hist']) == 0]
        logging.info(f"  Failed: plotting {len(failed_nonzero)}/{len(failed_A)} "
                     f"(non-zero entries; {len(failed_zero)} empty)")

        for r in tqdm(good_sample,    desc="Good plots (sample)"):
            plot_channel_fit(r, plot_dir, 'root_multigauss_good')
        for r in tqdm(bad_A,          desc="Bad plots (all)"):
            plot_channel_fit(r, plot_dir, 'root_multigauss_bad')
        for r in tqdm(failed_nonzero, desc="Failed plots (non-zero)"):
            plot_channel_fit(r, plot_dir, 'root_multigauss_failed')

    logging.info(f"\nDone! Results in {args.output_dir}")

if __name__ == "__main__":
    main()
