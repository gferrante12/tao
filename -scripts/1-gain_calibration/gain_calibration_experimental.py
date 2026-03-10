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

TEST MODE: Only processes the first 3 channels to verify the fit pipeline.

Usage:
  python gain_calibration_experimental.py input.root output_dir RUN1295
  python gain_calibration_experimental.py input.root output_dir RUN1295 --n-channels 10
"""

import argparse
import logging
import os
import sys
import math

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
LINEAR_R2_MIN      = 0.90

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
    """Poisson-weighted χ²: Σ (y_obs - y_pred)² / max(y_obs, 1)."""
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

    # ROOT integrated chi2
    chi2_root = fr.Chi2()
    ndf_root  = fr.Ndf()
    chi2_ndf  = chi2_root / ndf_root if ndf_root > 0 else -1

    params = [fr.Parameter(i) for i in range(3*n_peaks)]
    param_errs = [fr.ParError(i) for i in range(3*n_peaks)]

    # Secondary: manual Poisson chi2
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
    Uses ROOT TF1 with a C++ functor defined inline.

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

    # Parameters: [A1, mu1, sigma_pe, sigma_base, gain, tau, A2, A3, ..., A_n]
    n_par = 6 + (n_peaks - 1)

    # Define C++ functor for EMG
    cpp_code = f"""
    double emg_model_{ch_id}(double *x, double *p) {{
        // p[0]=A1, p[1]=mu1, p[2]=sigma_pe, p[3]=sigma_base, p[4]=gain, p[5]=tau
        // p[6..]=A2, A3, ...
        int n_peaks = {n_peaks};
        double val = 0.0;
        double mu1 = p[1], gain = p[4], sp = p[2], sb = p[3], tau = p[5];
        if (tau < 0.1) tau = 0.1;

        for (int n = 1; n <= n_peaks; n++) {{
            double An = (n == 1) ? p[0] : p[5 + n - 1];
            if (An < 0) An = 0;
            double mu_n = mu1 + (n - 1) * gain;
            double sig_n = sqrt(fmax(n * sp*sp + sb*sb, 1.0));

            // EMG: A/(2*tau) * exp((mu-x)/tau + sig^2/(2*tau^2)) * erfc(sig/(tau*sqrt2) - (x-mu)/(sig*sqrt2))
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
    # Use the C++ function pointer (not a TFormula expression string).
    # The 5-arg TF1(name, string, ..., npar) constructor interprets the 2nd arg
    # as a TFormula expression where "p" is not a valid token.
    # Instead, retrieve the compiled function via getattr(ROOT, ...) and pass
    # the pointer directly.
    f1 = ROOT.TF1(f"femg_{ch_id}",
                   getattr(ROOT, f"emg_model_{ch_id}"),
                   fit_min, fit_max, n_par)

    # Initial values from multigauss fit or from peaks
    if mg_params:
        # Use multigauss result to seed EMG
        mu1_init = mg_params[1]
        gain_init = est_gain
        sig_pe_init = mg_params[2]  # sigma of 1PE peak
        sig_base_init = 100.0
    else:
        mu1_init = peaks[0]
        gain_init = est_gain
        sig_pe_init = constraints['peak_width']
        sig_base_init = 100.0

    tau_init = 0.05 * gain_init  # ~5% of gain as initial CT tau

    f1.SetParameter(0, h.GetBinContent(h.FindBin(peaks[0])))  # A1
    f1.SetParameter(1, mu1_init)
    f1.SetParameter(2, sig_pe_init)
    f1.SetParameter(3, sig_base_init)
    f1.SetParameter(4, gain_init)
    f1.SetParameter(5, tau_init)

    # Limits
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

    # Compute p_ct estimate: tau / gain
    tau_fit = params[5]
    gain_fit = params[4]
    p_ct_est = tau_fit / gain_fit if gain_fit > 0 else 0

    # Manual Poisson chi2
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
    f_n = A_n * Σ_{i=0}^{N_ap} (1-n*alpha)*(n*alpha)^i * G(mu_n + i*Q_ap, sigma_n)

    Parameters: [A1, mu1, sigma_pe, sigma_base, gain, alpha, Q_ap, A2, A3, ...]
    Total: 7 + (n_peaks - 1)
    """
    n_peaks = len(peaks)
    constraints = get_adaptive_constraints(est_gain)
    N_AP = 4  # max afterpulse order

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
        // p[0]=A1, p[1]=mu1, p[2]=sigma_pe, p[3]=sigma_base, p[4]=gain
        // p[5]=alpha, p[6]=Q_ap, p[7..]=A2, A3, ...
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
    # Use the C++ function pointer — same fix as EMG above.
    # Passing f"ap_model_{ch_id}" as a string makes ROOT parse it as a
    # TFormula expression, which resolves to a function pointer type
    # (double(*)(double*,double*)) instead of a double → Cling type error.
    f1 = ROOT.TF1(f"fap_{ch_id}",
                   getattr(ROOT, f"ap_model_{ch_id}"),
                   fit_min, fit_max, n_par)

    # Initial values
    mu1_init = mg_params[1] if mg_params else peaks[0]
    sig_pe_init = mg_params[2] if mg_params else constraints['peak_width']
    gain_init = est_gain

    f1.SetParameter(0, h.GetBinContent(h.FindBin(peaks[0])))
    f1.SetParameter(1, mu1_init)
    f1.SetParameter(2, sig_pe_init)
    f1.SetParameter(3, 100.0)
    f1.SetParameter(4, gain_init)
    f1.SetParameter(5, 0.03)  # alpha ~ 3% afterpulse
    f1.SetParameter(6, 0.25 * gain_init)  # Q_ap ~ 25% of gain

    f1.SetParLimits(0, 1, 1e7)
    f1.SetParLimits(1, mu1_init - 0.3*est_gain, mu1_init + 0.3*est_gain)
    f1.SetParLimits(2, 100, 0.5*est_gain)
    f1.SetParLimits(3, 10, 0.3*est_gain)
    f1.SetParLimits(4, EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX)
    f1.SetParLimits(5, 0.001, 0.15)  # alpha
    f1.SetParLimits(6, 0.05*est_gain, 0.5*est_gain)  # Q_ap

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

    # Manual chi2
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
        mu_errs = [50.0] * n_peaks  # approx
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

    return {'gain': gain_lin, 'gain_err': math.sqrt(max(Cov[1,1], 0)),
            'intercept': icept, 'intercept_err': math.sqrt(max(Cov[0,0], 0)),
            'r2': r2}

# =============================================================================
# PLOTTING: comparison of models for one channel
# =============================================================================
def plot_channel_comparison(ch_id, hist_data, peaks, fit_results, out_dir, run_name):
    """Plot ADC histogram with overlaid fits from all models."""
    n_models = len(fit_results)
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
    ax_main = axes[0]
    ax_res  = axes[1]

    ax_main.step(BIN_CENTERS, hist_data, where='mid', color='black', lw=0.8, label='Data')

    # Mark peaks
    for i, pk in enumerate(peaks):
        idx = np.abs(BIN_CENTERS - pk).argmin()
        ax_main.plot(pk, hist_data[idx], 'rv', markersize=8,
                     label=f'{i+1} PE' if i == 0 else '')

    model_colors = {'multigauss': '#1f77b4', 'emg': '#2ca02c', 'multigauss_ap': '#ff7f0e'}
    model_labels = {'multigauss': 'Multi-Gauss', 'emg': 'EMG (CT tail)',
                    'multigauss_ap': 'Multi-Gauss + AP'}

    for mname, fr in fit_results.items():
        if fr is None:
            continue
        mask = (BIN_CENTERS >= fr['fit_min']) & (BIN_CENTERS <= fr['fit_max'])
        x_d = BIN_CENTERS[mask]
        y_d = hist_data[mask]

        # Compute model prediction
        if mname == 'multigauss':
            y_pred = multi_gauss_np(x_d, *fr['params'])
        elif mname == 'emg':
            y_pred = np.zeros_like(x_d)
            n_pk = len(peaks)
            for n in range(1, n_pk+1):
                An = fr['params'][0] if n == 1 else fr['params'][5 + n - 1]
                mu_n = fr['params'][1] + (n-1)*fr['params'][4]
                sig_n = peak_sigma(n, fr['params'][2], fr['params'][3])
                y_pred += emg_single_np(x_d, An, mu_n, sig_n, fr['params'][5])
        elif mname == 'multigauss_ap':
            y_pred = np.zeros_like(x_d)
            n_pk = len(peaks)
            alpha = max(0, min(fr['params'][5], 0.99/max(n_pk,1)))
            qap   = max(0, min(fr['params'][6], 0.95*abs(fr['params'][4])))
            for n in range(1, n_pk+1):
                An = fr['params'][0] if n == 1 else fr['params'][6 + n - 1]
                mu_n = fr['params'][1] + (n-1)*fr['params'][4]
                sig_n = peak_sigma(n, fr['params'][2], fr['params'][3])
                na = n * alpha
                for i in range(5):
                    wi = (1.0 - na) * (na**i)
                    if wi < 1e-12: break
                    y_pred += An * wi * gaussian_np(x_d, 1.0, mu_n + i*qap, sig_n)
        else:
            continue

        c2r = fr['chi2_ndf_root']
        c2m = fr['chi2_ndf_manual']
        lbl = f"{model_labels[mname]}: χ²/ndf(ROOT)={c2r:.2f}, χ²/ndf(Poisson)={c2m:.2f}"
        ax_main.plot(x_d, y_pred, '-', color=model_colors[mname], lw=1.8, alpha=0.85, label=lbl)

        # Residuals
        residual = (y_d - y_pred) / np.sqrt(np.maximum(y_d, 1))
        ax_res.plot(x_d, residual, '.', color=model_colors[mname], markersize=2, alpha=0.5)

    ax_main.set_yscale('log')
    ymax = hist_data.max()
    if ymax > 0:
        ax_main.set_ylim(0.5, ymax * 200)
    ax_main.set_ylabel('Counts')
    ax_main.set_title(f'{run_name} — Channel {ch_id}: Model Comparison', fontsize=14, fontweight='bold')
    ax_main.legend(fontsize=9, loc='upper right')
    ax_main.grid(True, alpha=0.3)

    ax_res.axhline(0, color='gray', lw=1)
    ax_res.set_xlabel('ADC')
    ax_res.set_ylabel('Pull (data−fit)/√data')
    ax_res.set_ylim(-5, 5)
    ax_res.grid(True, alpha=0.3)

    # Info box with extra parameters
    info_lines = []
    for mname, fr in fit_results.items():
        if fr is None:
            info_lines.append(f"{model_labels[mname]}: FAILED")
            continue
        line = f"{model_labels[mname]}: χ²/ndf = {fr['chi2_ndf_root']:.2f}"
        if 'extra' in fr and fr['extra']:
            ex = fr['extra']
            if 'p_ct_est' in ex:
                line += f", p_ct ≈ {ex['p_ct_est']:.3f}"
            if 'alpha' in ex:
                line += f", α = {ex['alpha']:.4f}, Q_ap/G = {ex.get('Q_ap_rel',0):.3f}"
        info_lines.append(line)

    ax_main.text(0.02, 0.02, "\n".join(info_lines), transform=ax_main.transAxes,
                 va='bottom', fontsize=8, family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    path = os.path.join(out_dir, f'{run_name}_ch{ch_id:04d}_model_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logging.info(f"Saved {path}")

# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='Experimental multi-model gain calibration (ROOT, first N channels)')
    parser.add_argument('input_root', help='Input ROOT file')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('run_name',   help='Run name')
    parser.add_argument('--use-raw', action='store_true')
    parser.add_argument('--n-channels', type=int, default=3,
                        help='Number of channels to process (default: 3)')
    args = parser.parse_args()

    if not os.path.exists(args.input_root):
        logging.error(f"Not found: {args.input_root}"); sys.exit(1)
    os.makedirs(args.output_dir, exist_ok=True)

    # Load histograms
    prefix = "H_adcraw_" if args.use_raw else "H_adcClean_"
    f = ROOT.TFile.Open(args.input_root, "READ")
    if not f or f.IsZombie():
        logging.error("Cannot open file"); sys.exit(1)

    channel_ids = []
    for key in f.GetListOfKeys():
        name = key.GetName()
        if name.startswith(prefix):
            try:
                channel_ids.append(int(name.replace(prefix, "")))
            except ValueError:
                continue
    channel_ids.sort()

    n_proc = min(args.n_channels, len(channel_ids))
    logging.info(f"Found {len(channel_ids)} channels, processing first {n_proc}")
    channel_ids = channel_ids[:n_proc]

    channels = {}
    for ch in channel_ids:
        h = f.Get(f"{prefix}{ch}")
        if h:
            arr = np.zeros(N_BINS)
            for i, bc in enumerate(BIN_CENTERS):
                bidx = h.FindBin(bc)
                if 1 <= bidx <= h.GetNbinsX():
                    arr[i] = h.GetBinContent(bidx)
            channels[ch] = arr
    f.Close()

    # Process each channel
    summary_lines = []
    summary_lines.append(f"{'='*120}")
    summary_lines.append(f"EXPERIMENTAL FIT COMPARISON — {args.run_name} — {n_proc} channels")
    summary_lines.append(f"{'='*120}")
    summary_lines.append("")
    summary_lines.append(f"{'Channel':<10} {'Model':<18} {'χ²/ndf(ROOT)':<16} {'χ²/ndf(Poisson)':<18} "
                         f"{'Gain':<12} {'R²':<10} {'Extra':<30}")
    summary_lines.append("-" * 120)

    for ch_id, hist_data in channels.items():
        logging.info(f"\n{'='*60}")
        logging.info(f"Channel {ch_id}")

        if np.sum(hist_data) < 1000:
            logging.warning(f"  Too few counts ({np.sum(hist_data):.0f}), skipping")
            continue

        # Peak detection
        peaks = detect_peaks_tspectrum(hist_data)
        if len(peaks) < 2:
            logging.warning(f"  Only {len(peaks)} peaks found, skipping")
            continue

        est_gain = estimate_gain_from_peaks(peaks)
        logging.info(f"  Detected {len(peaks)} peaks, est. gain = {est_gain:.0f} ADC/PE")

        fit_results = {}

        # Model 1: multigauss
        logging.info(f"  Fitting: multigauss ...")
        r1 = fit_multigauss_root(ch_id, hist_data, peaks, est_gain)
        fit_results['multigauss'] = r1
        if r1:
            lin = linear_fit_gain(len(peaks), r1['params'], 'multigauss')
            g_val = lin['gain'] if lin else 0
            r2_val = lin['r2'] if lin else 0
            logging.info(f"    ROOT χ²/ndf = {r1['chi2_ndf_root']:.3f}, "
                         f"Poisson χ²/ndf = {r1['chi2_ndf_manual']:.3f}")
            summary_lines.append(
                f"{ch_id:<10} {'multigauss':<18} {r1['chi2_ndf_root']:<16.3f} "
                f"{r1['chi2_ndf_manual']:<18.3f} {g_val:<12.1f} {r2_val:<10.4f} {'—':<30}")
            mg_seed = r1['params']
        else:
            logging.warning(f"    multigauss FAILED")
            summary_lines.append(f"{ch_id:<10} {'multigauss':<18} {'FAILED':<16}")
            mg_seed = None

        # Model 2: EMG
        logging.info(f"  Fitting: EMG ...")
        r2 = fit_emg_root(ch_id, hist_data, peaks, est_gain, mg_seed)
        fit_results['emg'] = r2
        if r2:
            lin = linear_fit_gain(len(peaks), r2['params'], 'emg')
            g_val = lin['gain'] if lin else r2['params'][4]
            r2_val = lin['r2'] if lin else 0
            extra = f"τ={r2['extra']['tau']:.1f}, p_ct≈{r2['extra']['p_ct_est']:.3f}"
            logging.info(f"    ROOT χ²/ndf = {r2['chi2_ndf_root']:.3f}, {extra}")
            summary_lines.append(
                f"{ch_id:<10} {'emg':<18} {r2['chi2_ndf_root']:<16.3f} "
                f"{r2['chi2_ndf_manual']:<18.3f} {g_val:<12.1f} {r2_val:<10.4f} {extra:<30}")
        else:
            logging.warning(f"    EMG FAILED")
            summary_lines.append(f"{ch_id:<10} {'emg':<18} {'FAILED':<16}")

        # Model 3: multigauss + afterpulse
        logging.info(f"  Fitting: multigauss_ap ...")
        r3 = fit_multigauss_ap_root(ch_id, hist_data, peaks, est_gain, mg_seed)
        fit_results['multigauss_ap'] = r3
        if r3:
            lin = linear_fit_gain(len(peaks), r3['params'], 'multigauss_ap')
            g_val = lin['gain'] if lin else r3['params'][4]
            r2_val = lin['r2'] if lin else 0
            extra = f"α={r3['extra']['alpha']:.4f}, Q_ap/G={r3['extra']['Q_ap_rel']:.3f}"
            logging.info(f"    ROOT χ²/ndf = {r3['chi2_ndf_root']:.3f}, {extra}")
            summary_lines.append(
                f"{ch_id:<10} {'multigauss_ap':<18} {r3['chi2_ndf_root']:<16.3f} "
                f"{r3['chi2_ndf_manual']:<18.3f} {g_val:<12.1f} {r2_val:<10.4f} {extra:<30}")
        else:
            logging.warning(f"    multigauss_ap FAILED")
            summary_lines.append(f"{ch_id:<10} {'multigauss_ap':<18} {'FAILED':<16}")

        # Plot comparison
        plot_channel_comparison(ch_id, hist_data, peaks, fit_results, args.output_dir, args.run_name)

    # Write summary TXT
    summary_lines.append("")
    summary_lines.append("=" * 120)
    summary_lines.append("PHYSICS NOTES")
    summary_lines.append("=" * 120)
    summary_lines.append("EMG (Exponential Modified Gaussian):")
    summary_lines.append("  f(x) = A/(2τ) exp[(μ-x)/τ + σ²/(2τ²)] · erfc[σ/(τ√2) - (x-μ)/(σ√2)]")
    summary_lines.append("  τ/Gain ≈ p_ct (optical crosstalk probability)")
    summary_lines.append("  Ref: arXiv:1409.4564, Kowalski & Bhatt (EMG)")
    summary_lines.append("")
    summary_lines.append("Multi-Gauss + Afterpulse (SYSU geometric model):")
    summary_lines.append("  f_n = A_n · Σ_{i=0}^{N_ap} (1-nα)(nα)^i · G(μ_n + i·Q_ap, σ_n)")
    summary_lines.append("  α = afterpulse probability per fired cell")
    summary_lines.append("  Q_ap = charge deposited by single AP avalanche")
    summary_lines.append("  Ref: Ziang Li, TAO group JAN 2026")
    summary_lines.append("")
    summary_lines.append("Note: Generalized Poisson model NOT used — external CT dominates")
    summary_lines.append("      at TAO with Ge-68 source, making GP priors unreliable")
    summary_lines.append("      (Ziang Li backup slide 24).")
    summary_lines.append("=" * 120)

    txt_path = os.path.join(args.output_dir, f'{args.run_name}_experimental_comparison.txt')
    with open(txt_path, 'w') as tf:
        tf.write("\n".join(summary_lines) + "\n")
    logging.info(f"\nSaved summary: {txt_path}")
    logging.info(f"Done! Results in {args.output_dir}")

if __name__ == "__main__":
    main()
