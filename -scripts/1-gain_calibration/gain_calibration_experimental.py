#!/usr/bin/env python3
"""
gain_calibration_experimental.py
================================
Experimental gain calibration with multiple physics-based fit models.
Uses ROOT integrated statistics (fit_result.Chi2(), Ndf(), etc.) as primary.
Hand-written Poisson chi2 as secondary comparison.

Models:
  1. multigauss     — baseline multi-Gaussian (same as stable script)
  2. emg            — Exponential Modified Gaussian (continuous CT tail)
                      f(x) = A/(2τ) exp[(μ-x)/τ + σ²/(2τ²)] · erfc[...]
                      Adds 1 param: τ  (τ/Gain ≈ p_ct)
                      Ref: Kowalski & Bhatt; arXiv:1409.4564
  3. multigauss_ap  — Multi-Gauss + geometric afterpulse (SYSU/Ziang Li)
                      f_n = A_n · Σ_i (1-nα)(nα)^i · G(μ_n + i·Q_ap, σ_n)
                      Adds 2 params: α (AP prob), Q_ap (AP charge)
                      Ref: Ziang Li slides, TAO JAN 2026

Processes ALL channels (multiprocessing).  One classification method (Method A
from gain_calibration_stable.py) applied independently to each fit model.

Outputs per model:
  - RUNXXXX_{model}_{good|bad|failed}.csv / .txt
  - RUNXXXX_fit_quality_piechart_{model}.png
  - RUNXXXX_summary_plots_{model}.png      (2 rows: good / bad)
  - plots_RUNXXXX/{good|bad|failed}/ch{XXXX}_{model}_fit.png
  - plots_RUNXXXX/{good|bad|failed}/ch{XXXX}_{model}_linear.png

Global:
  - RUNXXXX_classification_comparison.txt  (cross-model table)

Usage:
  python gain_calibration_experimental.py input.root output_dir RUN1295
  python gain_calibration_experimental.py input.root output_dir RUN1295 --use-raw
  python gain_calibration_experimental.py input.root output_dir RUN1295 --no-plots
"""

import argparse
import csv
import logging
import math
import os
import random
import sys
from multiprocessing import Pool, cpu_count

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import gridspec

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
    print("ERROR: ROOT (PyROOT) is required."); sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# =============================================================================
# CONSTANTS (same grid as stable script)
# =============================================================================
BIN_WIDTH   = 100
BIN_MAX     = 50000
BINS        = np.arange(0, BIN_MAX + BIN_WIDTH, BIN_WIDTH)
BIN_CENTERS = (BINS[:-1] + BINS[1:]) / 2.0
N_BINS      = len(BIN_CENTERS)

MAX_PEAKS          = 8
MAX_ADC_SEARCH     = 48000
PEAK_WIDTH         = 1200.0
MAX_SIGMA          = 3000.0
FIRST_PEAK_MIN     = 1500
FIRST_PEAK_MAX     = 9000
EXPECTED_GAIN_MIN  = 3000
EXPECTED_GAIN_MAX  = 9000
EXPECTED_GAIN_DEFAULT = 6000
CHI2_MAX           = 160.0
LINEAR_R2_MIN      = 0.99

MODEL_NAMES  = ['multigauss', 'emg', 'multigauss_ap']
MODEL_LABELS = {
    'multigauss':    'Multi-Gauss',
    'emg':           'EMG (CT tail)',
    'multigauss_ap': 'Multi-Gauss + AP',
}
MODEL_COLORS = {
    'multigauss':    '#1f77b4',
    'emg':           '#2ca02c',
    'multigauss_ap': '#ff7f0e',
}
PEAK_COLORS = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45',
]

N_AP = 4  # max afterpulse order (used in multigauss_ap)

# =============================================================================
# NUMPY HELPER FUNCTIONS
# =============================================================================
def gaussian_np(x, A, mu, sigma):
    s = max(abs(sigma), 1.0)
    return A * np.exp(-0.5 * ((x - mu) / s)**2)

def multi_gauss_np(x, *params):
    y = np.zeros_like(x, dtype=float)
    for i in range(len(params) // 3):
        y += gaussian_np(x, params[3*i], params[3*i+1], params[3*i+2])
    return y

def emg_single_np(x, A, mu, sigma, tau):
    """Single EMG peak (right-tail, area parametrisation)."""
    tau = max(abs(tau), 0.1)
    sigma = max(abs(sigma), 0.1)
    exp_arg = np.clip((mu - x)/tau + sigma**2/(2.0*tau**2), -500.0, 300.0)
    erfc_arg = sigma/(tau*math.sqrt(2.0)) - (x - mu)/(sigma*math.sqrt(2.0))
    erfc_vals = np.array([math.erfc(float(z)) for z in np.atleast_1d(erfc_arg)])
    return (A / (2.0*tau)) * np.exp(exp_arg) * erfc_vals

def peak_mu(n, mu1, gain):
    return mu1 + (n - 1) * gain

def peak_sigma(n, sigma_pe, sigma_base):
    return math.sqrt(max(n * sigma_pe**2 + sigma_base**2, 1.0))

# =============================================================================
# SECONDARY: hand-written Poisson chi2
# =============================================================================
def chi2_poisson_manual(y_obs, y_pred):
    """Poisson-weighted chi2: sum (y_obs - y_pred)^2 / max(y_obs, 1)."""
    w = 1.0 / np.maximum(y_obs, 1.0)
    return float(np.sum(w * (y_obs - y_pred)**2))

# =============================================================================
# ADAPTIVE CONSTRAINTS + PEAK FILTERING (same as stable)
# =============================================================================
def get_adaptive_constraints(est_gain):
    ratio = est_gain / EXPECTED_GAIN_DEFAULT
    return {
        'min_spacing': int(EXPECTED_GAIN_MIN * ratio),
        'max_spacing': int(EXPECTED_GAIN_MAX * ratio),
        'first_peak_min': int(FIRST_PEAK_MIN * ratio),
        'first_peak_max': int(FIRST_PEAK_MAX * ratio),
        'peak_width': PEAK_WIDTH * ratio,
        'fit_margin': 3.0 * ratio,
    }

def estimate_gain_from_peaks(peaks):
    if len(peaks) < 2:
        return -1
    sp = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
    return np.clip(np.median(sp), EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX)

def filter_peaks_adaptive(peaks, hist_data, constraints):
    if not peaks:
        return []
    peaks = sorted([p for p in peaks if p <= MAX_ADC_SEARCH])
    if not peaks:
        return []
    cands = [p for p in peaks if constraints['first_peak_min'] <= p <= constraints['first_peak_max']]
    if not cands:
        reas = [p for p in peaks if 1000 < p < 10000]
        if reas:
            fp = reas[0]
        else:
            return []
    else:
        hts = [hist_data[np.abs(BIN_CENTERS - p).argmin()] for p in cands]
        fp = cands[int(np.argmax(hts))]
    valid = [fp]
    for p in peaks:
        if p <= fp:
            continue
        s = p - valid[-1]
        if constraints['min_spacing'] < s <= constraints['max_spacing']:
            valid.append(p)
            if len(valid) >= MAX_PEAKS:
                break
    if len(valid) < 2:
        return []
    hts = [hist_data[np.abs(BIN_CENTERS - p).argmin()] for p in valid]
    for i in range(len(hts)-1):
        if hts[i+1] > hts[i]*1.05:
            valid = valid[:i+1]
            break
    return valid if len(valid) >= 2 else []

# =============================================================================
# PEAK DETECTION (TSpectrum)
# =============================================================================
def detect_peaks_tspectrum(hist_data, est_gain=EXPECTED_GAIN_DEFAULT):
    """Use ROOT TSpectrum to find peaks, then apply adaptive filtering."""
    nbins = len(hist_data)
    xmin = BIN_CENTERS[0] - BIN_WIDTH/2
    xmax = BIN_CENTERS[-1] + BIN_WIDTH/2
    h = ROOT.TH1D("htmp", "", nbins, xmin, xmax)
    for i, v in enumerate(hist_data):
        h.SetBinContent(i+1, v)

    spec = ROOT.TSpectrum(MAX_PEAKS + 2)
    nf = spec.Search(h, 4.0, "", 0.0005)
    if nf < 2:
        del h
        return []

    xp = spec.GetPositionX()
    pks = sorted([xp[i] for i in range(nf)])
    del h

    if len(pks) >= 2:
        est_gain = estimate_gain_from_peaks(pks)
    constraints = get_adaptive_constraints(est_gain)
    return filter_peaks_adaptive(pks, hist_data, constraints)

# =============================================================================
# MODEL 1: MULTIGAUSS (ROOT TF1)
# =============================================================================
def fit_multigauss_root(ch_id, hist_data, peaks, est_gain):
    """Standard multi-Gaussian fit using ROOT TF1."""
    n_peaks = len(peaks)
    constraints = get_adaptive_constraints(est_gain)

    nbins = len(hist_data)
    xmin = BIN_CENTERS[0] - BIN_WIDTH/2
    xmax = BIN_CENTERS[-1] + BIN_WIDTH/2
    h = ROOT.TH1D(f"h_mg_{ch_id}", "", nbins, xmin, xmax)
    for i, v in enumerate(hist_data):
        h.SetBinContent(i+1, v)

    fit_min = peaks[0] - constraints['peak_width'] * constraints['fit_margin']
    fit_max = peaks[-1] + constraints['peak_width'] * constraints['fit_margin']

    # Build formula
    parts = []
    for i in range(n_peaks):
        a, m, s = 3*i, 3*i+1, 3*i+2
        parts.append(f"[{a}]*exp(-0.5*((x-[{m}])/[{s}])^2)")
    f1 = ROOT.TF1(f"fmg_{ch_id}", "+".join(parts), fit_min, fit_max)

    # Estimate base sigma
    b0 = h.FindBin(peaks[0])
    a0 = h.GetBinContent(b0)
    hm = a0 / 2.0
    lb, rb = b0, b0
    while lb > 1 and h.GetBinContent(lb) > hm: lb -= 1
    while rb < h.GetNbinsX() and h.GetBinContent(rb) > hm: rb += 1
    fwhm = h.GetBinCenter(rb) - h.GetBinCenter(lb)
    base_sig = fwhm / 2.355 if fwhm > 0 else constraints['peak_width']
    base_sig = np.clip(base_sig, 0.15*est_gain, 0.4*est_gain)

    for j, pk in enumerate(peaks):
        amp = h.GetBinContent(h.FindBin(pk))
        sig = base_sig * math.sqrt((j+1))
        mu_tol = 0.3 * est_gain
        f1.SetParameter(3*j, amp); f1.SetParameter(3*j+1, pk); f1.SetParameter(3*j+2, sig)
        f1.SetParLimits(3*j, 0.05*amp, 20*amp)
        f1.SetParLimits(3*j+1, pk-mu_tol, pk+mu_tol)
        f1.SetParLimits(3*j+2, 0.2*sig, min(4*sig, MAX_SIGMA))

    fr = h.Fit(f1, "SRBQ", "", fit_min, fit_max)
    if not fr or int(fr) != 0:
        del h, f1
        return None

    chi2_root = fr.Chi2()
    ndf_root  = fr.Ndf()
    chi2_ndf  = chi2_root / ndf_root if ndf_root > 0 else -1

    params = [fr.Parameter(i) for i in range(3*n_peaks)]
    param_errs = [fr.ParError(i) for i in range(3*n_peaks)]

    mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
    x_d = BIN_CENTERS[mask]
    y_d = hist_data[mask]
    y_pred = multi_gauss_np(x_d, *params)
    chi2_manual = chi2_poisson_manual(y_d, y_pred)
    ndf_manual = len(x_d) - 3*n_peaks
    chi2_ndf_manual = chi2_manual / ndf_manual if ndf_manual > 0 else -1

    del h, f1
    return {
        'model': 'multigauss', 'params': params, 'param_errs': param_errs,
        'chi2_root': chi2_root, 'ndf_root': ndf_root, 'chi2_ndf_root': chi2_ndf,
        'chi2_manual': chi2_manual, 'ndf_manual': ndf_manual, 'chi2_ndf_manual': chi2_ndf_manual,
        'fit_min': fit_min, 'fit_max': fit_max,
    }

# =============================================================================
# MODEL 2: EMG (ROOT TF1 with custom formula)
# =============================================================================
def fit_emg_root(ch_id, hist_data, peaks, est_gain, mg_params=None):
    """
    EMG fit: each peak is an Exponential Modified Gaussian.
    Parameters: [A_1, mu_1, sigma_pe, sigma_base, gain, tau, A_2, A_3, ...]
    Total: 6 + (n_peaks - 1) free amplitudes
    """
    n_peaks = len(peaks)
    constraints = get_adaptive_constraints(est_gain)

    nbins = len(hist_data)
    xmin = BIN_CENTERS[0] - BIN_WIDTH/2
    xmax = BIN_CENTERS[-1] + BIN_WIDTH/2
    h = ROOT.TH1D(f"h_emg_{ch_id}", "", nbins, xmin, xmax)
    for i, v in enumerate(hist_data):
        h.SetBinContent(i+1, v)

    fit_min = peaks[0] - constraints['peak_width'] * constraints['fit_margin']
    fit_max = peaks[-1] + constraints['peak_width'] * constraints['fit_margin']

    n_par = 6 + (n_peaks - 1)

    cpp_code = f"""
    double emg_model_{ch_id}(double *x, double *p) {{
        int n_peaks = {n_peaks};
        double val = 0.0;
        double mu1 = p[1], gain = p[4], sp = p[2], sb = p[3], tau = p[5];
        if (tau < 0.1) tau = 0.1;

        for (int n = 1; n <= n_peaks; n++) {{
            double An = (n == 1) ? p[0] : p[5 + n - 1];
            if (An < 0) An = 0;
            double mu_n = mu1 + (n - 1) * gain;
            double sig_n = sqrt(fmax(n * sp*sp + sb*sb, 1.0));

            double exp_arg = (mu_n - x[0]) / tau + sig_n*sig_n / (2.0*tau*tau);
            if (exp_arg > 300) exp_arg = 300;
            if (exp_arg < -500) exp_arg = -500;
            double erfc_arg = sig_n / (tau * 1.41421356) - (x[0] - mu_n) / (sig_n * 1.41421356);
            val += (An / (2.0 * tau)) * exp(exp_arg) * TMath::Erfc(erfc_arg);
        }}
        return val;
    }}
    """
    ROOT.gInterpreter.Declare(cpp_code)
    f1 = ROOT.TF1(f"femg_{ch_id}",
                   getattr(ROOT, f"emg_model_{ch_id}"),
                   fit_min, fit_max, n_par)

    if mg_params:
        mu1_init = mg_params[1]
        gain_init = est_gain
        sig_pe_init = mg_params[2]
        sig_base_init = 100.0
    else:
        mu1_init = peaks[0]
        gain_init = est_gain
        sig_pe_init = constraints['peak_width']
        sig_base_init = 100.0

    tau_init = 0.05 * gain_init

    f1.SetParameter(0, h.GetBinContent(h.FindBin(peaks[0])))
    f1.SetParameter(1, mu1_init)
    f1.SetParameter(2, sig_pe_init)
    f1.SetParameter(3, sig_base_init)
    f1.SetParameter(4, gain_init)
    f1.SetParameter(5, tau_init)

    f1.SetParLimits(0, 1, 1e7)
    f1.SetParLimits(1, mu1_init - 0.3*est_gain, mu1_init + 0.3*est_gain)
    f1.SetParLimits(2, 100, 0.5*est_gain)
    f1.SetParLimits(3, 10, 0.3*est_gain)
    f1.SetParLimits(4, EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX)
    f1.SetParLimits(5, 10, 0.5*est_gain)

    for j in range(1, n_peaks):
        amp = h.GetBinContent(h.FindBin(peaks[j]))
        f1.SetParameter(5 + j, amp)
        f1.SetParLimits(5 + j, 1, 1e7)

    fr = h.Fit(f1, "SRBQ", "", fit_min, fit_max)
    if not fr or int(fr) != 0:
        del h, f1
        return None

    chi2_root = fr.Chi2()
    ndf_root = fr.Ndf()
    params = [fr.Parameter(i) for i in range(n_par)]
    param_errs = [fr.ParError(i) for i in range(n_par)]

    tau_fit = params[5]
    gain_fit = params[4]
    p_ct_est = tau_fit / gain_fit if gain_fit > 0 else 0

    mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
    x_d = BIN_CENTERS[mask]
    y_d = hist_data[mask]
    y_pred = np.zeros_like(x_d)
    for n in range(1, n_peaks + 1):
        An = params[0] if n == 1 else params[5 + n - 1]
        mu_n = params[1] + (n-1)*params[4]
        sig_n = peak_sigma(n, params[2], params[3])
        y_pred += emg_single_np(x_d, An, mu_n, sig_n, params[5])
    chi2_m = chi2_poisson_manual(y_d, y_pred)
    ndf_m = len(x_d) - n_par

    del h, f1
    return {
        'model': 'emg', 'params': params, 'param_errs': param_errs,
        'chi2_root': chi2_root, 'ndf_root': ndf_root,
        'chi2_ndf_root': chi2_root/ndf_root if ndf_root > 0 else -1,
        'chi2_manual': chi2_m, 'ndf_manual': ndf_m,
        'chi2_ndf_manual': chi2_m/ndf_m if ndf_m > 0 else -1,
        'fit_min': fit_min, 'fit_max': fit_max,
        'extra': {'tau': tau_fit, 'p_ct_est': p_ct_est},
    }

# =============================================================================
# MODEL 3: MULTIGAUSS + AFTERPULSE (ROOT TF1 with C++ functor)
# =============================================================================
def fit_multigauss_ap_root(ch_id, hist_data, peaks, est_gain, mg_params=None):
    """
    Multi-Gauss + geometric afterpulse (SYSU model).
    Parameters: [A1, mu1, sigma_pe, sigma_base, gain, alpha, Q_ap, A2, A3, ...]
    Total: 7 + (n_peaks - 1)
    """
    n_peaks = len(peaks)
    constraints = get_adaptive_constraints(est_gain)

    nbins = len(hist_data)
    xmin = BIN_CENTERS[0] - BIN_WIDTH/2
    xmax = BIN_CENTERS[-1] + BIN_WIDTH/2
    h = ROOT.TH1D(f"h_ap_{ch_id}", "", nbins, xmin, xmax)
    for i, v in enumerate(hist_data):
        h.SetBinContent(i+1, v)

    fit_min = peaks[0] - constraints['peak_width'] * constraints['fit_margin']
    fit_max = peaks[-1] + constraints['peak_width'] * constraints['fit_margin']

    n_par = 7 + (n_peaks - 1)

    cpp_code = f"""
    double ap_model_{ch_id}(double *x, double *p) {{
        int n_peaks = {n_peaks};
        int N_AP = {N_AP};
        double val = 0.0;
        double mu1=p[1], gain=p[4], sp=p[2], sb=p[3];
        double alpha = fmax(0.0, fmin(p[5], 0.99 / fmax(n_peaks, 1)));
        double qap   = fmax(0.0, fmin(p[6], 0.95 * fabs(gain)));

        for (int n = 1; n <= n_peaks; n++) {{
            double An = (n == 1) ? p[0] : p[6 + n - 1];
            if (An < 0) An = 0;
            double mu_n = mu1 + (n - 1) * gain;
            double sig_n = sqrt(fmax(n * sp*sp + sb*sb, 1.0));
            double na = n * alpha;

            double comp = 0.0;
            for (int i = 0; i <= N_AP; i++) {{
                double wi = (1.0 - na) * pow(na, i);
                if (wi < 1e-12) break;
                double mu_i = mu_n + i * qap;
                comp += wi * exp(-0.5 * pow((x[0] - mu_i) / sig_n, 2));
            }}
            val += An * comp;
        }}
        return val;
    }}
    """
    ROOT.gInterpreter.Declare(cpp_code)
    f1 = ROOT.TF1(f"fap_{ch_id}",
                   getattr(ROOT, f"ap_model_{ch_id}"),
                   fit_min, fit_max, n_par)

    mu1_init = mg_params[1] if mg_params else peaks[0]
    sig_pe_init = mg_params[2] if mg_params else constraints['peak_width']
    gain_init = est_gain

    f1.SetParameter(0, h.GetBinContent(h.FindBin(peaks[0])))
    f1.SetParameter(1, mu1_init)
    f1.SetParameter(2, sig_pe_init)
    f1.SetParameter(3, 100.0)
    f1.SetParameter(4, gain_init)
    f1.SetParameter(5, 0.03)
    f1.SetParameter(6, 0.25 * gain_init)

    f1.SetParLimits(0, 1, 1e7)
    f1.SetParLimits(1, mu1_init - 0.3*est_gain, mu1_init + 0.3*est_gain)
    f1.SetParLimits(2, 100, 0.5*est_gain)
    f1.SetParLimits(3, 10, 0.3*est_gain)
    f1.SetParLimits(4, EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX)
    f1.SetParLimits(5, 0.001, 0.15)
    f1.SetParLimits(6, 0.05*est_gain, 0.5*est_gain)

    for j in range(1, n_peaks):
        amp = h.GetBinContent(h.FindBin(peaks[j]))
        f1.SetParameter(6 + j, amp)
        f1.SetParLimits(6 + j, 1, 1e7)

    fr = h.Fit(f1, "SRBQ", "", fit_min, fit_max)
    if not fr or int(fr) != 0:
        del h, f1
        return None

    chi2_root = fr.Chi2()
    ndf_root = fr.Ndf()
    params = [fr.Parameter(i) for i in range(n_par)]
    param_errs = [fr.ParError(i) for i in range(n_par)]

    mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
    x_d = BIN_CENTERS[mask]
    y_d = hist_data[mask]
    y_pred = np.zeros_like(x_d)
    alpha_fit = max(0, min(params[5], 0.99/max(n_peaks, 1)))
    qap_fit   = max(0, min(params[6], 0.95*abs(params[4])))
    for n in range(1, n_peaks+1):
        An = params[0] if n == 1 else params[6 + n - 1]
        mu_n = params[1] + (n-1)*params[4]
        sig_n = peak_sigma(n, params[2], params[3])
        na = n * alpha_fit
        for i in range(N_AP + 1):
            wi = (1.0 - na) * (na**i)
            if wi < 1e-12:
                break
            y_pred += An * wi * gaussian_np(x_d, 1.0, mu_n + i*qap_fit, sig_n)
    chi2_m = chi2_poisson_manual(y_d, y_pred)
    ndf_m = len(x_d) - n_par

    del h, f1
    return {
        'model': 'multigauss_ap', 'params': params, 'param_errs': param_errs,
        'chi2_root': chi2_root, 'ndf_root': ndf_root,
        'chi2_ndf_root': chi2_root/ndf_root if ndf_root > 0 else -1,
        'chi2_manual': chi2_m, 'ndf_manual': ndf_m,
        'chi2_ndf_manual': chi2_m/ndf_m if ndf_m > 0 else -1,
        'fit_min': fit_min, 'fit_max': fit_max,
        'extra': {'alpha': alpha_fit, 'Q_ap': qap_fit,
                  'Q_ap_rel': qap_fit/params[4] if params[4] > 0 else 0},
    }

# =============================================================================
# LINEAR FIT (gain extraction from peak means)
# =============================================================================
def linear_fit_gain(n_peaks, params, model_name):
    """Extract peak means from fitted parameters, do linear fit for gain."""
    if model_name == 'multigauss':
        mus = [params[3*j + 1] for j in range(n_peaks)]
        mu_errs = [50.0] * n_peaks
    elif model_name == 'emg':
        mu1, gain = params[1], params[4]
        mus = [mu1 + (n-1)*gain for n in range(1, n_peaks+1)]
        mu_errs = [50.0] * n_peaks
    elif model_name == 'multigauss_ap':
        mu1, gain = params[1], params[4]
        mus = [mu1 + (n-1)*gain for n in range(1, n_peaks+1)]
        mu_errs = [50.0] * n_peaks
    else:
        return None

    ns = np.arange(1, n_peaks + 1, dtype=float)
    Y = np.array(mus, dtype=float)
    w = 1.0 / np.array(mu_errs, dtype=float)**2
    W = np.diag(w)
    X = np.column_stack([np.ones(n_peaks), ns])
    try:
        Cov = np.linalg.inv(X.T @ W @ X)
    except np.linalg.LinAlgError:
        return None
    beta = Cov @ X.T @ W @ Y
    icept, gain_lin = beta[0], beta[1]
    Y_pred = X @ beta
    ss_res = float(np.sum((Y - Y_pred)**2))
    ss_tot = float(np.sum((Y - Y.mean())**2))
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 0 else 0

    resid = Y - Y_pred
    chi2_lin = float(np.sum(w * resid**2))
    ndf_lin = n_peaks - 2
    chi2_dof_lin = chi2_lin / ndf_lin if ndf_lin > 0 else -1.0

    return {'gain': gain_lin, 'gain_err': math.sqrt(max(Cov[1,1], 0)),
            'intercept': icept, 'intercept_err': math.sqrt(max(Cov[0,0], 0)),
            'r2': r2, 'linear_chi2_dof': chi2_dof_lin}

# =============================================================================
# MODEL PREDICTION (numpy, for plotting)
# =============================================================================
def model_predict_np(model_name, x, params, n_peaks):
    """Evaluate the model on x given fitted params."""
    if model_name == 'multigauss':
        return multi_gauss_np(x, *params)
    elif model_name == 'emg':
        y = np.zeros_like(x)
        for n in range(1, n_peaks+1):
            An = params[0] if n == 1 else params[5 + n - 1]
            mu_n = params[1] + (n-1)*params[4]
            sig_n = peak_sigma(n, params[2], params[3])
            y += emg_single_np(x, An, mu_n, sig_n, params[5])
        return y
    elif model_name == 'multigauss_ap':
        y = np.zeros_like(x)
        alpha = max(0, min(params[5], 0.99/max(n_peaks,1)))
        qap   = max(0, min(params[6], 0.95*abs(params[4])))
        for n in range(1, n_peaks+1):
            An = params[0] if n == 1 else params[6 + n - 1]
            mu_n = params[1] + (n-1)*params[4]
            sig_n = peak_sigma(n, params[2], params[3])
            na = n * alpha
            for i in range(N_AP + 1):
                wi = (1.0 - na) * (na**i)
                if wi < 1e-12: break
                y += An * wi * gaussian_np(x, 1.0, mu_n + i*qap, sig_n)
        return y
    return np.zeros_like(x)

# =============================================================================
# PROCESS ONE CHANNEL (all 3 models)
# =============================================================================
def process_channel(ch_id, hist_data):
    """
    Fit all three models on one channel.
    Returns a dict with per-model sub-dicts compatible with stable classification.
    """
    base = {
        'channel_id': ch_id,
        'hist': hist_data,
        'n_peaks': 0,
        'detected_peaks': [],
    }

    # Per-model results
    model_results = {}
    for mname in MODEL_NAMES:
        model_results[mname] = {
            'fit_status': -1,
            'gain': 0.0, 'gain_error': 0.0,
            'intercept': 0.0, 'intercept_error': 0.0,
            'chi2_dof': -1.0, 'linear_r2': 0.0, 'linear_chi2_dof': -1.0,
            'n_peaks': 0,
            'fit_params': None, 'fit_min': 0, 'fit_max': 0,
            'extra': {},
        }

    if np.sum(hist_data) < 1000:
        base['model_results'] = model_results
        return base

    peaks = detect_peaks_tspectrum(hist_data)
    if len(peaks) < 2:
        base['model_results'] = model_results
        return base

    est_gain = estimate_gain_from_peaks(peaks)
    base['detected_peaks'] = peaks
    base['n_peaks'] = len(peaks)

    def _fill(mr, raw, mname):
        """Populate model_results dict from raw fit output."""
        if raw is None:
            return
        lin = linear_fit_gain(len(peaks), raw['params'], mname)
        mr['fit_status'] = 1
        mr['n_peaks'] = len(peaks)
        mr['chi2_dof'] = raw['chi2_ndf_root']
        mr['chi2_ndf_manual'] = raw.get('chi2_ndf_manual', -1)
        mr['fit_params'] = raw['params']
        mr['fit_min'] = raw['fit_min']
        mr['fit_max'] = raw['fit_max']
        mr['extra'] = raw.get('extra', {})
        if lin:
            mr['gain'] = lin['gain']
            mr['gain_error'] = lin['gain_err']
            mr['intercept'] = lin['intercept']
            mr['intercept_error'] = lin['intercept_err']
            mr['linear_r2'] = lin['r2']
            mr['linear_chi2_dof'] = lin['linear_chi2_dof']

    # Model 1: multigauss
    r1 = fit_multigauss_root(ch_id, hist_data, peaks, est_gain)
    mg_seed = r1['params'] if r1 else None
    _fill(model_results['multigauss'], r1, 'multigauss')

    # Model 2: EMG
    r2 = fit_emg_root(ch_id, hist_data, peaks, est_gain, mg_seed)
    _fill(model_results['emg'], r2, 'emg')

    # Model 3: multigauss_ap
    r3 = fit_multigauss_ap_root(ch_id, hist_data, peaks, est_gain, mg_seed)
    _fill(model_results['multigauss_ap'], r3, 'multigauss_ap')

    base['model_results'] = model_results
    return base


def _worker(args):
    ch_id, hist_data = args
    return process_channel(ch_id, hist_data)


# =============================================================================
# CLASSIFICATION — Method A only (chi2/ndf + R2 + gain range + n_peaks >= 3)
# =============================================================================
def classify_A(mr):
    """Classify a single per-model result dict."""
    if mr['fit_status'] != 1:
        return 'failed'
    if mr['n_peaks'] < 3:
        return 'bad'
    if (mr['chi2_dof'] <= CHI2_MAX
            and mr['linear_r2'] >= LINEAR_R2_MIN
            and EXPECTED_GAIN_MIN <= mr['gain'] <= EXPECTED_GAIN_MAX):
        return 'good'
    return 'bad'


def split_by_model(all_results, model_name):
    """Split channel results into good / bad / failed for one model."""
    good, bad, failed = [], [], []
    for res in all_results:
        mr = res['model_results'][model_name]
        # Attach channel-level info for CSV/plot convenience
        row = dict(mr)
        row['channel_id'] = res['channel_id']
        row['hist'] = res['hist']
        row['detected_peaks'] = res['detected_peaks']

        cat = classify_A(mr)
        if cat == 'good':
            good.append(row)
        elif cat == 'bad':
            bad.append(row)
        else:
            failed.append(row)
    return good, bad, failed


# =============================================================================
# HELPER: distribution statistics (same as stable)
# =============================================================================
def dist_stats(values):
    if not values:
        return {'min': 0, 'max': 0, 'mean': 0, 'rms': 0, 'n': 0}
    a = np.array(values)
    return {'min': float(a.min()), 'max': float(a.max()),
            'mean': float(a.mean()), 'rms': float(a.std()), 'n': len(a)}


# =============================================================================
# CSV / TXT OUTPUT (same format as stable)
# =============================================================================
def save_results_csv_txt(result_list, filepath_base):
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
                     f"{r['linear_r2']:<10.4f} {r.get('linear_chi2_dof', -1):<12.3f}\n")

    logging.info(f"Saved {csv_path} and {txt_path}")


# =============================================================================
# PLOT: Pie chart per model
# =============================================================================
def plot_piechart(good, bad, failed, model_name, run_name, out_dir):
    n_g, n_b, n_f = len(good), len(bad), len(failed)
    n_tot = n_g + n_b + n_f
    if n_tot == 0:
        return
    pct = lambda n: 100.0 * n / n_tot

    fig, ax = plt.subplots(figsize=(10, 8))
    sizes  = [n_g, n_b, n_f]
    labels = [
        f'Good (>=3 peaks)\n{n_g} ({pct(n_g):.1f}%)',
        f'Bad\n{n_b} ({pct(n_b):.1f}%)',
        f'Failed\n{n_f} ({pct(n_f):.1f}%)',
    ]
    colors  = ['#90EE90', '#FFA07A', '#FFB6C6']
    explode = [0.05 if s / n_tot > 0.10 else 0.15 for s in sizes]

    nonzero = [(s, l, c, e) for s, l, c, e in zip(sizes, labels, colors, explode) if s > 0]
    if nonzero:
        sizes_, labels_, colors_, explode_ = zip(*nonzero)
    else:
        sizes_, labels_, colors_, explode_ = sizes, labels, colors, explode

    wedges, texts = ax.pie(sizes_, explode=explode_, labels=labels_, colors=colors_,
                           startangle=90, labeldistance=1.15,
                           textprops=dict(fontsize=11, fontweight='bold'))

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            pos_i = texts[i].get_position()
            pos_j = texts[j].get_position()
            dy = abs(pos_i[1] - pos_j[1])
            dx = abs(pos_i[0] - pos_j[0])
            if dy < 0.25 and dx < 0.6:
                shift = (0.25 - dy) / 2 + 0.05
                if pos_i[1] >= pos_j[1]:
                    texts[i].set_position((pos_i[0], pos_i[1] + shift))
                    texts[j].set_position((pos_j[0], pos_j[1] - shift))
                else:
                    texts[i].set_position((pos_i[0], pos_i[1] - shift))
                    texts[j].set_position((pos_j[0], pos_j[1] + shift))

    # Pull the "Failed" label ~2 cm closer to the pie.
    # Figure is 10×8 in → 8 in height; data span ≈ 3 units → 2 cm ≈ 0.24 data-units.
    for txt in texts:
        if txt.get_text().startswith('Failed'):
            x0, y0 = txt.get_position()
            # Move towards centre (sign of y0 tells which hemisphere)
            shift = 0.24 if y0 < 0 else -0.24
            txt.set_position((x0, y0 + shift))

    ax.axis('equal')
    mlbl = MODEL_LABELS.get(model_name, model_name)
    plt.title(f'{run_name} — {mlbl}\nTotal: {n_tot}',
              fontsize=13, fontweight='bold', pad=20)
    plt.tight_layout()
    path = os.path.join(out_dir, f'{run_name}_fit_quality_piechart_{model_name}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"Saved {path}")


# =============================================================================
# PLOT: Summary distributions (2x4: good row, bad row) — per model
# =============================================================================
def _auto_range(vals):
    """Return (lo, hi) that shows every entry: min*0.9 .. max*1.1."""
    vmin, vmax = np.min(vals), np.max(vals)
    lo = vmin * 0.9 if vmin > 0 else vmin - 0.1 * abs(vmax - vmin)
    hi = vmax * 1.1 if vmax > 0 else vmax + 0.1 * abs(vmax - vmin)
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    return (lo, hi)


def _plot_dist_row(axes, fits, row, category, is_good=False):
    color_main = 'red' if 'Bad' in category else 'green'

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
        if is_good:
            rng = (0.989, rng[1])
        ax.hist(vals, bins=50, range=rng, color='purple', alpha=0.7, edgecolor='k')
        ax.set_yscale('log')
    ax.set_title(f'{category}: R2', fontweight='bold', fontsize=10)
    ax.set_xlabel('R2')
    ax.grid(True, alpha=0.3)


def plot_summary(good, bad, model_name, run_name, out_dir):
    mlbl = MODEL_LABELS.get(model_name, model_name)
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    _plot_dist_row(axes, good, 0, 'Good (>=3 peaks)', is_good=True)
    _plot_dist_row(axes, bad,  1, 'Bad',               is_good=False)
    plt.suptitle(f'{run_name} — {mlbl}', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(out_dir, f'{run_name}_summary_plots_{model_name}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"Saved {path}")


# =============================================================================
# PLOT: Per-channel fit (ADC + residuals) and linear gain — per model
# =============================================================================
def plot_channel_fit(row, model_name, plot_dir, quality):
    """
    Save two PNGs per (channel, model):
      plots_RUNXXXX/{quality}/ch{XXXX}_{model}_fit.png
      plots_RUNXXXX/{quality}/ch{XXXX}_{model}_linear.png
    """
    ch_id = row['channel_id']
    hist  = row['hist']
    peaks = row['detected_peaks']
    n_peaks = row['n_peaks']

    title_color = {'good': 'green', 'bad': 'orange', 'failed': 'red'}.get(quality, 'red')
    mlbl = MODEL_LABELS.get(model_name, model_name)
    fit_color = MODEL_COLORS.get(model_name, 'steelblue')

    q_dir = os.path.join(plot_dir, quality)
    os.makedirs(q_dir, exist_ok=True)
    base = os.path.join(q_dir, f'ch{ch_id:04d}_{model_name}')

    # ── 1) ADC fit + residuals ─────────────────────────────────────────────
    fig = plt.figure(figsize=(10, 7))
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)
    ax     = fig.add_subplot(gs[0])
    ax_res = fig.add_subplot(gs[1], sharex=ax)

    fig.suptitle(f'Channel {ch_id}  ({mlbl}) — {quality.upper()} Fit',
                 fontsize=12, color=title_color, fontweight='bold')

    pos_mask  = (BIN_CENTERS > 0) & (hist > 0)
    y_max_dat = float(np.max(hist[pos_mask])) if np.any(pos_mask) else 1.0

    ax.step(BIN_CENTERS, hist, where='mid', color='black',
            linewidth=0.6, alpha=0.85, label='Data')
    ax.set_yscale('log')
    ax.set_ylim(0.5, y_max_dat * 200)
    ax.set_ylabel('Counts', fontsize=11)
    ax.set_xlim(0, BIN_MAX)
    ax.grid(True, alpha=0.25)

    if row['fit_status'] == 1 and row['fit_params'] is not None:
        fit_min = row['fit_min']
        fit_max = row['fit_max']
        mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
        x_d = BIN_CENTERS[mask]
        y_m = model_predict_np(model_name, x_d, row['fit_params'], n_peaks)

        fit_lbl = (
            f"{mlbl}\n"
            f"Gain={row['gain']:.0f}+/-{row['gain_error']:.0f} ADC/PE\n"
            f"chi2/ndf={row['chi2_dof']:.2f}  R2={row['linear_r2']:.3f}"
        )
        ax.plot(x_d, y_m, color=fit_color, lw=1.8, label=fit_lbl, zorder=3)

        # Coloured dashed PE-peak lines
        if model_name == 'multigauss':
            for i in range(n_peaks):
                mu_i = row['fit_params'][3*i + 1]
                sig_i = row['fit_params'][3*i + 2]
                c_i = PEAK_COLORS[i % len(PEAK_COLORS)]
                lbl = f'{i+1} PE: mu={mu_i:.0f}, sigma={sig_i:.0f}' if i < 4 else f'{i+1} PE: mu={mu_i:.0f}'
                ax.axvline(mu_i, color=c_i, linestyle='--', linewidth=1.2, alpha=0.75, label=lbl)
        else:
            mu1_f = row['fit_params'][1]
            gain_f = row['fit_params'][4]
            sp = row['fit_params'][2]
            sb = row['fit_params'][3]
            for i in range(n_peaks):
                mu_i = mu1_f + i * gain_f
                sig_i = peak_sigma(i+1, sp, sb)
                c_i = PEAK_COLORS[i % len(PEAK_COLORS)]
                lbl = f'{i+1} PE: mu={mu_i:.0f}, sigma={sig_i:.0f}' if i < 4 else f'{i+1} PE: mu={mu_i:.0f}'
                ax.axvline(mu_i, color=c_i, linestyle='--', linewidth=1.2, alpha=0.75, label=lbl)

        bbox_fc = 'lightgreen' if quality == 'good' else ('lightyellow' if quality == 'bad' else 'lightcoral')
        extra_lines = ""
        ex = row.get('extra', {})
        if 'p_ct_est' in ex:
            extra_lines += f"p_ct ~ {ex['p_ct_est']:.3f}\n"
        if 'alpha' in ex:
            extra_lines += f"alpha = {ex['alpha']:.4f}, Q_ap/G = {ex.get('Q_ap_rel',0):.3f}\n"

        info_text = (
            f"STATUS: SUCCESS\n"
            f"Method: {model_name}\n"
            f"Quality: {quality.upper()}\n"
            f"{'─'*20}\n"
            f"Total Events: {int(np.sum(hist))}\n"
            f"Peaks: {n_peaks}\n"
            f"{'─'*20}\n"
            f"chi2/ndf: {row['chi2_dof']:.2f}\n"
            f"{extra_lines}"
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                va='top', ha='left', fontsize=8, family='monospace',
                bbox=dict(boxstyle='round', facecolor=bbox_fc, alpha=0.75))

        # Residuals
        fit_mask = (BIN_CENTERS >= x_d[0]) & (BIN_CENTERS <= x_d[-1])
        y_dw = hist[fit_mask]
        if len(y_dw) == len(y_m):
            res = y_dw - y_m
            ax_res.bar(x_d, res, width=BIN_WIDTH * 0.9, color=fit_color, alpha=0.55)
            ax_res.axhline(0, color='k', lw=0.8)
            ax_res.grid(True, alpha=0.25)
    else:
        info_text = (
            f"STATUS: FAILED\n"
            f"Method: {model_name}\n"
            f"Quality: {quality.upper()}\n"
            f"{'─'*20}\n"
            f"Total Events: {int(np.sum(hist))}\n"
            f"Detected Peaks: {len(peaks)}\n"
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                va='top', ha='left', fontsize=8, family='monospace',
                bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.75))
        ax.text(0.5, 0.5, 'FIT FAILED', transform=ax.transAxes,
                ha='center', va='center', color='red', fontsize=16, fontweight='bold')

    ax.legend(fontsize=7, ncol=2, loc='upper right')
    plt.setp(ax.get_xticklabels(), visible=False)
    ax_res.set_xlabel('ADC [counts]', fontsize=11)
    ax_res.set_ylabel('Residual', fontsize=11)

    fig.savefig(base + '_fit.png', dpi=100, bbox_inches='tight')
    plt.close(fig)

    # ── 2) Linear gain PNG ─────────────────────────────────────────────────
    if row['fit_status'] == 1 and row['gain'] > 0 and n_peaks >= 2:
        if model_name == 'multigauss':
            ns_arr = np.arange(1, n_peaks + 1)
            mu_arr = np.array([row['fit_params'][3*i + 1] for i in range(n_peaks)])
        else:
            mu1_f = row['fit_params'][1]
            gf = row['fit_params'][4]
            ns_arr = np.arange(1, n_peaks + 1)
            mu_arr = np.array([mu1_f + (n-1)*gf for n in ns_arr])

        fig2, ax2 = plt.subplots(figsize=(7, 5))
        ax2.scatter(ns_arr, mu_arr, color='blue', zorder=3, s=60, label='Fitted Means')

        x_line = np.linspace(0.5, n_peaks + 0.5, 200)
        y_line = row['intercept'] + row['gain'] * x_line
        ax2.plot(x_line, y_line, 'r-', lw=2.0,
                 label=f"mu = {row['intercept']:.0f} + {row['gain']:.0f}*n")

        lin_c2 = row.get('linear_chi2_dof', -1.0)
        gain_info = (
            f"mu = {row['intercept']:.0f} + {row['gain']:.0f}*n\n"
            f"{'─'*20}\n"
            f"Gain: {row['gain']:.0f} +/- {row['gain_error']:.0f} ADC/PE\n"
            f"Intercept: {row['intercept']:.0f} +/- {row['intercept_error']:.0f}\n"
            f"{'─'*20}\n"
            f"Linear R2: {row['linear_r2']:.3f}\n"
            f"Linear chi2/dof: {lin_c2:.2f}\n"
        )
        ax2.text(0.05, 0.97, gain_info, transform=ax2.transAxes,
                 va='top', ha='left', fontsize=9, family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.85))

        ax2.set_xlabel('Peak Number (PE)', fontsize=11)
        ax2.set_ylabel('ADC Value', fontsize=11)
        ax2.set_title(f'Channel {ch_id}  {mlbl} — Gain Calculation',
                       fontsize=11, fontweight='bold')
        ax2.legend(loc='lower right', fontsize=9)
        ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        fig2.savefig(base + '_linear.png', dpi=100, bbox_inches='tight')
        plt.close(fig2)


# =============================================================================
# CLASSIFICATION COMPARISON TXT (cross-model)
# =============================================================================
def write_comparison_txt(all_results, run_name, out_dir):
    n_total = len(all_results)
    path = os.path.join(out_dir, f'{run_name}_classification_comparison.txt')

    with open(path, 'w') as f:
        f.write(f"{'='*110}\n")
        f.write(f"CLASSIFICATION COMPARISON — {run_name}\n")
        f.write(f"Total channels analysed: {n_total}\n")
        f.write(f"Classification: Method A (chi2/ndf <= {CHI2_MAX}, R2 >= {LINEAR_R2_MIN}, "
                f"gain in [{EXPECTED_GAIN_MIN}, {EXPECTED_GAIN_MAX}], n_peaks >= 3)\n")
        f.write(f"{'='*110}\n\n")

        f.write(f"{'Model':<30} {'Good>=3pk':<16} {'Bad':<14} {'Failed':<14}\n")
        f.write(f"{'-'*110}\n")

        model_splits = {}
        for mname in MODEL_NAMES:
            g, b, fl = split_by_model(all_results, mname)
            model_splits[mname] = (g, b, fl)
            ng, nb, nf = len(g), len(b), len(fl)
            pg = 100*ng / n_total if n_total else 0
            pb = 100*nb / n_total if n_total else 0
            pf = 100*nf / n_total if n_total else 0
            mlbl = MODEL_LABELS.get(mname, mname)
            f.write(f"{mlbl:<30} "
                    f"{ng:>5} ({pg:>5.1f}%)  "
                    f"{nb:>5} ({pb:>5.1f}%)  "
                    f"{nf:>5} ({pf:>5.1f}%)\n")

        f.write(f"\n{'='*110}\n")
        f.write(f"DETAILED STATISTICS PER MODEL\n")
        f.write(f"{'='*110}\n")

        for mname in MODEL_NAMES:
            g, b, fl = model_splits[mname]
            mlbl = MODEL_LABELS.get(mname, mname)
            f.write(f"\n{'─'*110}\n")
            f.write(f"{mlbl}\n")
            f.write(f"{'─'*110}\n")

            for cat_name, cat_list in [('GOOD FITS (>=3 peaks)', g),
                                        ('BAD FITS', b)]:
                f.write(f"\n  {cat_name} ({len(cat_list)} channels):\n")
                if not cat_list:
                    f.write(f"    (none)\n")
                    continue

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

            f.write(f"\n  FAILED FITS ({len(fl)} channels):\n")
            if fl:
                n_nz = sum(1 for r in fl if np.sum(r['hist']) > 0)
                n_z  = len(fl) - n_nz
                f.write(f"    Histogram entries:      non-zero = {n_nz},  zero (empty) = {n_z}\n")
            else:
                f.write(f"    (none)\n")

        f.write(f"\n{'='*110}\n")
        f.write("PHYSICS NOTES\n")
        f.write(f"{'='*110}\n")
        f.write("EMG (Exponential Modified Gaussian):\n")
        f.write("  f(x) = A/(2t) exp[(mu-x)/t + s^2/(2t^2)] * erfc[s/(t*sqrt2) - (x-mu)/(s*sqrt2)]\n")
        f.write("  tau/Gain ~ p_ct (optical crosstalk probability)\n")
        f.write("  Ref: arXiv:1409.4564, Kowalski & Bhatt (EMG)\n\n")
        f.write("Multi-Gauss + Afterpulse (SYSU geometric model):\n")
        f.write("  f_n = A_n * Sum_{i=0}^{N_ap} (1-n*alpha)*(n*alpha)^i * G(mu_n + i*Q_ap, sigma_n)\n")
        f.write("  alpha = afterpulse probability per fired cell\n")
        f.write("  Q_ap = charge deposited by single AP avalanche\n")
        f.write("  Ref: Ziang Li, TAO group JAN 2026\n\n")
        f.write("Note: Generalized Poisson model NOT used — external CT dominates\n")
        f.write("      at TAO with Ge-68 source, making GP priors unreliable\n")
        f.write("      (Ziang Li backup slide 24).\n")
        f.write(f"{'='*110}\n")

    logging.info(f"Saved comparison: {path}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='Experimental multi-model gain calibration (ROOT, all channels).\n'
                    'Fit models: multigauss, EMG, multigauss_ap.\n'
                    'Classification: Method A only.\n'
                    'Plots: good=sample100, bad=all, failed=non-zero only.')
    parser.add_argument('input_root', help='Input ROOT file with ADC histograms')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('run_name',   help='Run name (e.g. RUN1295)')
    parser.add_argument('--use-raw', action='store_true',
                        help='Use raw (H_adcraw_*) instead of clean (H_adcClean_*)')
    parser.add_argument('--no-plots', action='store_true',
                        help='Skip per-channel fit plot generation')
    args = parser.parse_args()

    if not os.path.exists(args.input_root):
        logging.error(f"Input file not found: {args.input_root}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    plot_dir = os.path.join(args.output_dir, f"plots_{args.run_name}")
    os.makedirs(plot_dir, exist_ok=True)
    for sub in ['good', 'bad', 'failed']:
        os.makedirs(os.path.join(plot_dir, sub), exist_ok=True)

    # ── Load histograms ─────────────────────────────────────────────────────
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

    # ── Fit all channels (multiprocessing) ──────────────────────────────────
    n_workers = min(8, max(1, cpu_count() - 1))
    logging.info(f"Fitting {len(channel_data)} channels x 3 models ({n_workers} workers) ...")

    with Pool(n_workers) as pool:
        all_results = list(tqdm(pool.imap(_worker, channel_data),
                                total=len(channel_data), desc="Fitting"))

    # ── Per-model: classify -> CSV/TXT -> pie chart -> summary plots ────────
    for mname in MODEL_NAMES:
        logging.info(f"\n{'='*60}")
        logging.info(f"Model: {MODEL_LABELS[mname]}")
        good, bad, failed = split_by_model(all_results, mname)
        ng, nb, nf = len(good), len(bad), len(failed)
        logging.info(f"  Good (>=3 peaks): {ng}   Bad: {nb}   Failed: {nf}")

        save_results_csv_txt(good,   os.path.join(args.output_dir, f'{args.run_name}_{mname}_good'))
        save_results_csv_txt(bad,    os.path.join(args.output_dir, f'{args.run_name}_{mname}_bad'))
        save_results_csv_txt(failed, os.path.join(args.output_dir, f'{args.run_name}_{mname}_failed'))

        plot_piechart(good, bad, failed, mname, args.run_name, args.output_dir)
        plot_summary(good, bad, mname, args.run_name, args.output_dir)

    # ── Comparison TXT ──────────────────────────────────────────────────────
    write_comparison_txt(all_results, args.run_name, args.output_dir)

    # ── Per-channel fit plots (per model, same sampling as stable) ──────────
    if not args.no_plots:
        logging.info(f"\nGenerating per-channel fit plots ...")
        for mname in MODEL_NAMES:
            good, bad, failed = split_by_model(all_results, mname)

            good_sample = random.sample(good, min(100, len(good))) if good else []
            logging.info(f"  {MODEL_LABELS[mname]}:  Good {len(good_sample)}/{len(good)} (sampled), "
                         f"Bad {len(bad)} (all)")

            failed_nonzero = [r for r in failed if np.sum(r['hist']) > 0]
            failed_zero    = [r for r in failed if np.sum(r['hist']) == 0]
            logging.info(f"    Failed {len(failed_nonzero)}/{len(failed)} "
                         f"(non-zero; {len(failed_zero)} empty)")

            for r in tqdm(good_sample, desc=f"  {mname} good (sample)"):
                plot_channel_fit(r, mname, plot_dir, 'good')
            for r in tqdm(bad, desc=f"  {mname} bad (all)"):
                plot_channel_fit(r, mname, plot_dir, 'bad')
            for r in tqdm(failed_nonzero, desc=f"  {mname} failed (non-zero)"):
                plot_channel_fit(r, mname, plot_dir, 'failed')

    logging.info(f"\nDone! Results in {args.output_dir}")


if __name__ == "__main__":
    main()
