#!/usr/bin/env python3
"""
gain_fit_functions.py
=====================
All fit model definitions and MIGRAD-based minimization helpers for SiPM ADC gain calibration.
Four models:
  1. MULTI_GAUSS     - standard multi-Gaussian (baseline)
  2. GAUSS_CT        - Multi-Gaussian with binomial internal optical crosstalk (IOCT) conv.
  3. EMG             - Exponential Modified Gaussian per peak (right-tail asymmetry)
  4. GEN_POISSON     - Generalized-Poisson weighted Gaussian (Vinogradov 2012, arXiv:2512.15264)

After-pulse (AP) component (Hanwen/MSU formulation) can be added to any model.
All chi^2 minimizations use ROOT.Math.Minimizer (MIGRAD/Minuit2).
NO scipy, NO TSpectrum, NO ready fitters.
"""

import ROOT
import numpy as np
import math
from array import array

ROOT.Math.MinimizerOptions.SetDefaultMinimizer("Minuit2", "Migrad")
ROOT.Math.MinimizerOptions.SetDefaultMaxFunctionCalls(100000)
ROOT.Math.MinimizerOptions.SetDefaultTolerance(1e-6)

# ─────────────────────────────────────────────────────────────────
# Basic building blocks (all in ADC units, numpy-vectorized)
# ─────────────────────────────────────────────────────────────────

def gauss(x, A, mu, sigma):
    """Standard Gaussian."""
    return A * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def emg_peak(x, A, mu, sigma, tau):
    """
    Exponential Modified Gaussian (EMG) — right-tail version.
    tau > 0 shifts weight to the right (crosstalk / afterpulse tail).

    f(x) = A/(2*tau) * exp[(sigma^2 - 2*tau*(x-mu)) / (2*tau^2)]
           * erfc[(sigma^2 - tau*(x-mu)) / (sqrt(2)*sigma*tau)]

    Refs: journals.vsu.ru (EMG); used by IHEP group for asymmetric peaks.
    """
    if tau <= 0:
        return gauss(x, A, mu, sigma)
    z = (sigma**2 - tau * (x - mu)) / (np.sqrt(2.0) * sigma * tau)
    # use ROOT TMath::Erfc via vectorised numpy path (erfc from math module for scalar)
    erfc_val = np.array([math.erfc(float(zi)) for zi in np.atleast_1d(z)], dtype=float)
    if np.ndim(x) == 0:
        erfc_val = erfc_val[0]
    val = (A / (2.0 * tau)) * np.exp(
        (sigma**2 - 2.0 * tau * (x - mu)) / (2.0 * tau**2)
    ) * erfc_val
    return val


def afterpulse_component(x, A1, mu1, Qap, sigma_ap):
    """
    After-pulse (AP) shape following Hanwen/MSU formulation (file:28):
        f_AP(x) = sum_{s=1}^{S} A1 * (1 - s) * Gauss(mu1 + s*Qap, sqrt(s)*sigma_ap)
    Here s=1..3 is sufficient; Qap = charge shift of AP relative to 1PE mean.
    sigma_ap is independent sigma for AP contribution.
    This is an additive term to the main multi-Gaussian model.
    """
    result = np.zeros_like(np.asarray(x, dtype=float))
    for s in range(1, 4):
        A_s = A1 * (1.0 - s) * 0.15  # small amplitude relative to main peak
        mu_s = mu1 + s * Qap
        sig_s = np.sqrt(float(s)) * sigma_ap
        result += gauss(x, A_s, mu_s, sig_s)
    return result


# ─────────────────────────────────────────────────────────────────
# Model 1: Multi-Gaussian (no physics corrections)
# ─────────────────────────────────────────────────────────────────

def model_multigauss(x, params, n_peaks):
    """
    params = [A1, mu1, G, sigma_spe, sigma_base]
      mu_n = mu1 + (n-1)*G
      sigma_n = sqrt(n*sigma_spe^2 + sigma_base^2)
    """
    A1, mu1, G, sigma_spe, sigma_base = params[:5]
    result = np.zeros_like(np.asarray(x, dtype=float))
    for n in range(1, n_peaks + 1):
        A_n = A1 * np.exp(-(n - 1)) if n > 1 else A1
        mu_n = mu1 + (n - 1) * G
        sig_n = np.sqrt(n * sigma_spe**2 + sigma_base**2)
        sig_n = max(sig_n, 1.0)
        result += gauss(x, A_n, mu_n, sig_n)
    return result


# ─────────────────────────────────────────────────────────────────
# Model 2: Multi-Gaussian + IOCT (binomial crosstalk convolution)
# ─────────────────────────────────────────────────────────────────
# Based on arXiv:1409.4564 and arXiv:2512.15264 (Generalized Poisson / binomial CT).
# Each observed n-PE peak = sum_{k=0}^{K} C(n+k-1, k)*P_ct^k*(1-P_ct)^n * Gauss(mu_{n+k}, sigma)
# For efficiency K=2 is used (2 CT generations max).

def binom_ct_weight(n, k, P_ct):
    """Binomial weight for k CT photons added to n primary photons."""
    from math import comb
    if P_ct <= 0:
        return 1.0 if k == 0 else 0.0
    if P_ct >= 1:
        return 0.0
    return comb(n + k - 1, k) * (P_ct ** k) * ((1.0 - P_ct) ** n)


def model_gauss_ct(x, params, n_peaks, K_ct=2):
    """
    params = [A1, mu1, G, sigma_spe, sigma_base, P_ct]
    K_ct = max number of CT generations (2 sufficient per arXiv:1409.4564)
    """
    A1, mu1, G, sigma_spe, sigma_base, P_ct = params[:6]
    P_ct = max(0.0, min(0.95, P_ct))
    result = np.zeros_like(np.asarray(x, dtype=float))
    for n in range(1, n_peaks + 1):
        A_n = A1 * np.exp(-(n - 1)) if n > 1 else A1
        for k in range(0, K_ct + 1):
            w = binom_ct_weight(n, k, P_ct)
            if w < 1e-10:
                continue
            mu_nk = mu1 + (n + k - 1) * G
            sig_nk = np.sqrt((n + k) * sigma_spe**2 + sigma_base**2)
            sig_nk = max(sig_nk, 1.0)
            result += A_n * w * gauss(x, 1.0, mu_nk, sig_nk)
    return result


# ─────────────────────────────────────────────────────────────────
# Model 3: EMG per peak (asymmetric tails)
# ─────────────────────────────────────────────────────────────────
# Used by IHEP group; tau is global across all peaks (CAEN characterization doc).

def model_emg(x, params, n_peaks):
    """
    params = [A1, mu1, G, sigma_spe, sigma_base, tau]
    tau: global exponential tail constant (same for all peaks, motivated by
         constant P_ct per primary — arXiv:1409.4564 §3)
    """
    A1, mu1, G, sigma_spe, sigma_base, tau = params[:6]
    tau = max(tau, 0.0)
    result = np.zeros_like(np.asarray(x, dtype=float))
    for n in range(1, n_peaks + 1):
        A_n = A1 * np.exp(-(n - 1)) if n > 1 else A1
        mu_n = mu1 + (n - 1) * G
        sig_n = np.sqrt(n * sigma_spe**2 + sigma_base**2)
        sig_n = max(sig_n, 1.0)
        result += emg_peak(x, A_n, mu_n, sig_n, tau)
    return result


# ─────────────────────────────────────────────────────────────────
# Model 4: Generalized Poisson (Vinogradov / arXiv:2512.15264 §5.2.2)
# ─────────────────────────────────────────────────────────────────
# GP(k, mu, lambda) = mu * (mu + lambda*k)^(k-1) * exp(-mu - lambda*k) / k!
# Each GP(k) peak is a Gaussian at position mu_k = mu1 + (k-1)*G
# lambda = IOCT branching Poisson parameter

def gen_poisson_weight(k, mu_gp, lam):
    """
    Generalized Poisson probability for k total pulses from mu_gp primary,
    with branching IOCT parameter lam.
    """
    if k < 1:
        return 0.0
    lam = max(0.0, min(lam, 0.9))
    mu_gp = max(1e-9, mu_gp)
    log_w = (np.log(mu_gp) + (k - 1) * np.log(mu_gp + lam * k)
             - (mu_gp + lam * k)
             - sum(np.log(i) for i in range(1, k + 1)))
    return np.exp(log_w)


def model_gen_poisson(x, params, n_peaks):
    """
    params = [A_total, mu1, G, sigma_spe, sigma_base, mu_gp, lam]
    mu_gp: mean number of primary dark/signal pulses (sets relative peak heights)
    lam: IOCT branching Poisson parameter (arXiv:2512.15264 eq.5.5)
    """
    A_total, mu1, G, sigma_spe, sigma_base, mu_gp, lam = params[:7]
    lam = max(0.0, min(lam, 0.9))
    mu_gp = max(0.1, mu_gp)
    result = np.zeros_like(np.asarray(x, dtype=float))
    for k in range(1, n_peaks + 1):
        w = gen_poisson_weight(k, mu_gp, lam)
        mu_k = mu1 + (k - 1) * G
        sig_k = np.sqrt(k * sigma_spe**2 + sigma_base**2)
        sig_k = max(sig_k, 1.0)
        result += A_total * w * gauss(x, 1.0, mu_k, sig_k)
    return result


# ─────────────────────────────────────────────────────────────────
# Error-function threshold on 1PE peak (COTI low threshold effect)
# Multiplies model value at the 1PE peak to account for partial truncation.
# SYSU group (file:28): multiply 1PE Gaussian by erf((x - x_thresh)/sigma_thr)
# ─────────────────────────────────────────────────────────────────

def apply_erf_threshold(model_vals, x, x_thresh, sigma_thr):
    """
    Multiplies the full model by the erf threshold function.
    x_thresh: ADC cut threshold (COTI)
    sigma_thr: transition width
    """
    if x_thresh is None:
        return model_vals
    erf_vals = np.array([0.5 * (1.0 + math.erf((float(xi) - x_thresh) / (np.sqrt(2) * sigma_thr)))
                         for xi in np.atleast_1d(x)], dtype=float)
    return model_vals * erf_vals


# ─────────────────────────────────────────────────────────────────
# Chi2 and NDF computation (hand-written, no external fitter)
# ─────────────────────────────────────────────────────────────────

def compute_chi2_ndf(x_data, y_data, y_err, model_func, params):
    """
    Pearson chi2 = sum( (y_i - f_i)^2 / max(y_err_i^2, 1) )
    NDF = n_bins_used - n_params
    """
    f = model_func(x_data, params)
    err2 = np.maximum(y_err**2, 1.0)
    chi2 = float(np.sum((y_data - f) ** 2 / err2))
    ndf = int(np.sum(y_data > 0)) - len(params)
    return chi2, max(ndf, 1)


def neg_log_likelihood(x_data, y_data, model_func, params):
    """
    Binned Poisson negative log-likelihood (extended):
    -2*lnL = 2 * sum( f_i - y_i + y_i*ln(y_i/f_i) )  [y_i > 0 bins only]
    Used as alternative to chi2 for low-statistics bins.
    """
    f = np.maximum(model_func(x_data, params), 1e-10)
    mask = y_data > 0
    nll = 2.0 * float(np.sum(f[mask] - y_data[mask] + y_data[mask] * np.log(y_data[mask] / f[mask])))
    return nll


# ─────────────────────────────────────────────────────────────────
# MIGRAD minimizer wrapper (ROOT Minuit2)
# ─────────────────────────────────────────────────────────────────

class MigradFitter:
    """
    Wrapper around ROOT.Math.Minimizer for chi2 minimization.
    Calls MIGRAD (Minuit2) — no scipy, no TSpectrum.
    """
    def __init__(self, x_data, y_data, model_func, param_names,
                 init_vals, step_sizes, lower_bounds, upper_bounds,
                 use_likelihood=False):
        self.x = np.asarray(x_data, dtype=float)
        self.y = np.asarray(y_data, dtype=float)
        self.y_err = np.sqrt(np.maximum(self.y, 1.0))
        self.model_func = model_func
        self.param_names = param_names
        self.init_vals = list(init_vals)
        self.step_sizes = list(step_sizes)
        self.lower = list(lower_bounds)
        self.upper = list(upper_bounds)
        self.n_params = len(param_names)
        self.use_likelihood = use_likelihood
        self._result = None
        self._errors = None
        self._chi2 = None
        self._ndf = None
        self._status = "NOT_RUN"

    def _objective(self, *args):
        params = list(args)
        if self.use_likelihood:
            return neg_log_likelihood(self.x, self.y, self.model_func, params)
        chi2, _ = compute_chi2_ndf(self.x, self.y, self.y_err, self.model_func, params)
        return chi2

    def fit(self):
        minimizer = ROOT.Math.Factory.CreateMinimizer("Minuit2", "Migrad")
        minimizer.SetMaxFunctionCalls(100000)
        minimizer.SetTolerance(1e-5)
        minimizer.SetPrintLevel(-1)

        func = ROOT.Math.Functor(self._objective, self.n_params)
        minimizer.SetFunction(func)

        for i, (name, val, step, lo, hi) in enumerate(zip(
                self.param_names, self.init_vals, self.step_sizes,
                self.lower, self.upper)):
            if lo < hi:
                minimizer.SetLimitedVariable(i, name, val, step, lo, hi)
            else:
                minimizer.SetVariable(i, name, val, step)

        success = minimizer.Minimize()
        xs = minimizer.X()
        errs = minimizer.Errors()
        self._result = [xs[i] for i in range(self.n_params)]
        self._errors = [errs[i] for i in range(self.n_params)]
        self._chi2, self._ndf = compute_chi2_ndf(
            self.x, self.y, self.y_err,
            self.model_func, self._result)
        if success and self._chi2 / max(self._ndf, 1) < 50:
            self._status = "SUCCESS"
        elif not success:
            self._status = "FAILED"
        else:
            self._status = "BAD"
        return self._status

    @property
    def result(self): return self._result
    @property
    def errors(self): return self._errors
    @property
    def chi2(self): return self._chi2
    @property
    def ndf(self): return self._ndf
    @property
    def chi2ndf(self): return self._chi2 / max(self._ndf, 1)
    @property
    def status(self): return self._status


# ─────────────────────────────────────────────────────────────────
# Peak finding (hand-written, no TSpectrum)
# ─────────────────────────────────────────────────────────────────

def find_peaks_manual(x_arr, y_arr, min_prominence=0.05, min_dist_adc=None):
    """
    Simple prominence-based peak finder on a 1D histogram.
    Returns list of (peak_index, peak_x, peak_y).
    min_prominence: fraction of global max required.
    min_dist_adc: minimum ADC distance between peaks.
    """
    if min_dist_adc is None:
        # estimate from x spacing
        dx = x_arr[1] - x_arr[0] if len(x_arr) > 1 else 1.0
        min_dist_adc = 10 * dx

    threshold = max(y_arr) * min_prominence
    peaks = []
    n = len(y_arr)
    for i in range(1, n - 1):
        if y_arr[i] > threshold and y_arr[i] >= y_arr[i-1] and y_arr[i] >= y_arr[i+1]:
            # local max in window
            half_w = max(1, int(min_dist_adc / (x_arr[1] - x_arr[0]) / 2))
            lo = max(0, i - half_w)
            hi = min(n - 1, i + half_w)
            if y_arr[i] == max(y_arr[lo:hi+1]):
                peaks.append((i, x_arr[i], y_arr[i]))

    # merge peaks closer than min_dist_adc
    merged = []
    for pk in sorted(peaks, key=lambda p: -p[2]):
        if not merged or abs(pk[1] - merged[-1][1]) > min_dist_adc:
            merged.append(pk)
    merged = sorted(merged, key=lambda p: p[1])
    return merged


# ─────────────────────────────────────────────────────────────────
# Linear gain fit (from peak positions vs PE number)
# ─────────────────────────────────────────────────────────────────

def linear_gain_fit(peak_numbers, peak_means, peak_mean_errors=None):
    """
    Fit mu_n = offset + Gain * n using hand-written weighted least squares.
    Returns (Gain, Gain_err, Offset, Offset_err, chi2, ndf, R2).
    """
    n_arr = np.array(peak_numbers, dtype=float)
    mu_arr = np.array(peak_means, dtype=float)
    if peak_mean_errors is None or np.any(np.array(peak_mean_errors) <= 0):
        w_arr = np.ones(len(n_arr))
    else:
        w_arr = 1.0 / np.array(peak_mean_errors, dtype=float)**2

    S = np.sum(w_arr)
    Sn = np.sum(w_arr * n_arr)
    Smu = np.sum(w_arr * mu_arr)
    Sn2 = np.sum(w_arr * n_arr**2)
    Snmu = np.sum(w_arr * n_arr * mu_arr)
    Delta = S * Sn2 - Sn**2

    Gain = (S * Snmu - Sn * Smu) / Delta
    Offset = (Smu * Sn2 - Sn * Snmu) / Delta

    residuals = mu_arr - (Offset + Gain * n_arr)
    chi2 = float(np.sum(w_arr * residuals**2))
    ndf = max(len(n_arr) - 2, 1)

    var_Gain = S / Delta
    var_Offset = Sn2 / Delta
    Gain_err = np.sqrt(var_Gain)
    Offset_err = np.sqrt(var_Offset)

    # R^2
    mu_mean = np.mean(mu_arr)
    ss_tot = np.sum((mu_arr - mu_mean)**2)
    ss_res = np.sum(residuals**2)
    R2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return Gain, Gain_err, Offset, Offset_err, chi2, ndf, R2


# ─────────────────────────────────────────────────────────────────
# Initial parameter estimation from histogram + found peaks
# ─────────────────────────────────────────────────────────────────

def estimate_initial_params(peaks, model_name, x_arr, y_arr):
    """
    Given a list of found peaks (sorted by x), estimate starting parameters
    for each model.
    Returns dict with init_vals, step_sizes, lower_bounds, upper_bounds, param_names.
    """
    if len(peaks) < 2:
        return None

    A1 = peaks[0][2]
    mu1 = peaks[0][1]
    dx = peaks[1][1] - peaks[0][1]
    G_init = float(np.median([peaks[i+1][1] - peaks[i][1] for i in range(len(peaks)-1)]))
    sigma_spe = G_init * 0.12
    sigma_base = G_init * 0.05

    if model_name == "MULTI_GAUSS":
        names = ["A1", "mu1", "G", "sigma_spe", "sigma_base"]
        vals  = [A1, mu1, G_init, sigma_spe, sigma_base]
        steps = [A1*0.1, G_init*0.05, G_init*0.02, sigma_spe*0.1, sigma_base*0.1]
        lows  = [0, mu1 - G_init, G_init*0.5, 1.0, 1.0]
        highs = [A1*10, mu1 + G_init, G_init*2.0, G_init*0.5, G_init*0.3]

    elif model_name == "GAUSS_CT":
        names = ["A1", "mu1", "G", "sigma_spe", "sigma_base", "P_ct"]
        vals  = [A1, mu1, G_init, sigma_spe, sigma_base, 0.08]
        steps = [A1*0.1, G_init*0.05, G_init*0.02, sigma_spe*0.1, sigma_base*0.1, 0.01]
        lows  = [0, mu1 - G_init, G_init*0.5, 1.0, 1.0, 0.0]
        highs = [A1*10, mu1 + G_init, G_init*2.0, G_init*0.5, G_init*0.3, 0.5]

    elif model_name == "EMG":
        tau_init = sigma_spe * 0.3
        names = ["A1", "mu1", "G", "sigma_spe", "sigma_base", "tau"]
        vals  = [A1, mu1, G_init, sigma_spe, sigma_base, tau_init]
        steps = [A1*0.1, G_init*0.05, G_init*0.02, sigma_spe*0.1, sigma_base*0.1, tau_init*0.1]
        lows  = [0, mu1 - G_init, G_init*0.5, 1.0, 1.0, 0.0]
        highs = [A1*10, mu1 + G_init, G_init*2.0, G_init*0.5, G_init*0.3, G_init*0.5]

    elif model_name == "GEN_POISSON":
        n_peaks_found = len(peaks)
        mu_gp_init = max(0.5, float(n_peaks_found) * 0.3)
        lam_init = 0.10
        names = ["A_total", "mu1", "G", "sigma_spe", "sigma_base", "mu_gp", "lam"]
        vals  = [A1 * n_peaks_found, mu1, G_init, sigma_spe, sigma_base, mu_gp_init, lam_init]
        steps = [A1, G_init*0.05, G_init*0.02, sigma_spe*0.1, sigma_base*0.1, 0.1, 0.01]
        lows  = [0, mu1 - G_init, G_init*0.5, 1.0, 1.0, 0.1, 0.0]
        highs = [A1*50, mu1 + G_init, G_init*2.0, G_init*0.5, G_init*0.3, 20.0, 0.9]
    else:
        return None

    return dict(param_names=names, init_vals=vals, step_sizes=steps,
                lower_bounds=lows, upper_bounds=highs)


# ─────────────────────────────────────────────────────────────────
# Model registry
# ─────────────────────────────────────────────────────────────────

MODEL_NAMES = ["MULTI_GAUSS", "GAUSS_CT", "EMG", "GEN_POISSON"]

def get_model_func(model_name, n_peaks):
    """Returns a closure f(x, params) for the given model and n_peaks."""
    if model_name == "MULTI_GAUSS":
        return lambda x, p: model_multigauss(x, p, n_peaks)
    elif model_name == "GAUSS_CT":
        return lambda x, p: model_gauss_ct(x, p, n_peaks)
    elif model_name == "EMG":
        return lambda x, p: model_emg(x, p, n_peaks)
    elif model_name == "GEN_POISSON":
        return lambda x, p: model_gen_poisson(x, p, n_peaks)
    else:
        raise ValueError(f"Unknown model: {model_name}")


def extract_gain_and_sigma_from_fit(model_name, fit_params, n_peaks,
                                    peak_numbers=None, peak_means_from_fit=None,
                                    peak_mean_errors=None):
    """
    Extract Gain (and its error) from fitted parameters.
    For all models except GEN_POISSON: Gain = params['G'] directly.
    Also perform linear fit on extracted mu_n for cross-check.
    Returns dict with gain, gain_err, linear_gain, linear_R2, etc.
    """
    # Direct gain from fit parameter
    param_names_model = {
        "MULTI_GAUSS": ["A1", "mu1", "G", "sigma_spe", "sigma_base"],
        "GAUSS_CT":    ["A1", "mu1", "G", "sigma_spe", "sigma_base", "P_ct"],
        "EMG":         ["A1", "mu1", "G", "sigma_spe", "sigma_base", "tau"],
        "GEN_POISSON": ["A_total", "mu1", "G", "sigma_spe", "sigma_base", "mu_gp", "lam"],
    }
    names = param_names_model[model_name]
    p = dict(zip(names, fit_params))

    result = {
        "gain_direct": p["G"],
        "mu1": p["mu1"],
        "sigma_spe": p.get("sigma_spe", None),
        "P_ct":  p.get("P_ct", None),
        "tau":   p.get("tau", None),
        "lam":   p.get("lam", None),
        "mu_gp": p.get("mu_gp", None),
    }

    # Linear fit cross-check
    if peak_numbers is not None and peak_means_from_fit is not None:
        G_lin, G_lin_err, off, off_err, chi2_lin, ndf_lin, R2 = linear_gain_fit(
            peak_numbers, peak_means_from_fit, peak_mean_errors)
        result.update({
            "gain_linear": G_lin,
            "gain_linear_err": G_lin_err,
            "offset_linear": off,
            "R2_linear": R2,
            "chi2_linear": chi2_lin,
            "ndf_linear": ndf_lin,
        })
    return result
