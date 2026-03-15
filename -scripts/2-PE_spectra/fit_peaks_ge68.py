#!/usr/bin/env python3
"""
fit_peaks_ge68.py  —  Two-stage peak fitting for Ge-68 spectra (ROOT TF1 version)

Stage 1: Gaussian + pol3  (robust, data-driven initialization)
Stage 2: Full physics model — v1 or v2:
    v1: Compton + secondary γ + 14C pileup + pol3  (original)
    v2: Single-escape + Compton + 14C pileup + pol3  (improved for TAO 1.8m)

All fits performed with ROOT TF1 (MIGRAD via Minuit2). No scipy.

Entry points:
    fit_from_arrays()   — called by spectrum_utils.fit_source() with numpy arrays
    fit_ge68()          — standalone: reads ROOT file
    main()              — CLI entry point

Author: G. Ferrante
"""

import argparse
import glob
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    import uproot
    HAS_UPROOT = True
except ImportError:
    HAS_UPROOT = False

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    raise RuntimeError("ROOT (PyROOT) is required for fit_peaks_ge68.")


# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
E_GE68_MEV    = 1.022
E_SEC_MEV     = 1.08
M_E_MEV       = 0.511
DN_PE_DEFAULT = 134.0

FIT_WINDOW_SIGMA_LO = 7.0
FIT_WINDOW_SIGMA_HI = 6.0

_ALPHA_511      = M_E_MEV / M_E_MEV
E_COMPTON_511   = M_E_MEV * 2 * _ALPHA_511 / (1 + 2 * _ALPHA_511)   # ≈ 0.340 MeV

# Global counter for unique ROOT object names
_FIT_COUNTER = 0


# ─────────────────────────────────────────────────────────────────────────────
# ROOT helpers
# ─────────────────────────────────────────────────────────────────────────────

def _unique_name(prefix="f"):
    global _FIT_COUNTER
    _FIT_COUNTER += 1
    return f"{prefix}_{_FIT_COUNTER}"


def _arrays_to_th1d(cx, cy, name=None):
    """Convert numpy bin-centre/count arrays to a ROOT TH1D."""
    name = name or _unique_name("h")
    n    = len(cx)
    if n < 2:
        return None
    dx   = (cx[-1] - cx[0]) / max(n - 1, 1)
    xlo  = float(cx[0]  - 0.5 * dx)
    xhi  = float(cx[-1] + 0.5 * dx)
    h    = ROOT.TH1D(name, "", n, xlo, xhi)
    h.SetDirectory(0)
    for i in range(n):
        v = float(cy[i])
        h.SetBinContent(i + 1, v)
        h.SetBinError(i + 1, float(max(1.0, np.sqrt(max(v, 1.0)))))
    return h


class _RootCallable:
    """
    Wrap a numpy model function so ROOT TF1 can call it.
    Keeps a strong reference to prevent garbage collection.
    """
    def __init__(self, fn, n_par):
        self.fn    = fn
        self.n_par = n_par

    def __call__(self, x, par):
        params = [par[i] for i in range(self.n_par)]
        try:
            return float(self.fn(float(x[0]), *params))
        except Exception:
            return 0.0


def _root_fit(model_fn, cx_fit, cy_fit, p0, lo, hi, xmin, xmax):
    """
    Fit model_fn to data using ROOT TF1 + Minuit (MIGRAD).

    Parameters
    ----------
    model_fn : callable(x_scalar, *params) → float
    cx_fit, cy_fit : numpy arrays of bin centres and counts
    p0  : initial parameter values (list/array)
    lo, hi : parameter lower/upper bounds (lists; use ±1e30 for unconstrained)
    xmin, xmax : fit range

    Returns
    -------
    popt  : ndarray of fitted values
    perr  : ndarray of parameter errors
    chi2  : float
    ndf   : int
    ok    : bool  (True if MIGRAD converged)
    """
    n_par    = len(p0)
    rcallable = _RootCallable(model_fn, n_par)
    tf1_name  = _unique_name("tf1")
    h_name    = _unique_name("h_fit")

    tf1 = ROOT.TF1(tf1_name, rcallable, xmin, xmax, n_par)
    tf1.SetNpx(1000)

    for i in range(n_par):
        tf1.SetParameter(i, float(p0[i]))
        lo_i = float(lo[i])
        hi_i = float(hi[i])
        if lo_i > -1e29 and hi_i < 1e29:
            tf1.SetParLimits(i, lo_i, hi_i)

    h = _arrays_to_th1d(cx_fit, cy_fit, h_name)
    if h is None:
        return None, None, -1.0, 0, False

    # Q=quiet, N=no draw, S=save result, R=use function range
    fit_result = h.Fit(tf1, "Q N S R")
    ok = (int(fit_result) == 0)

    popt = np.array([tf1.GetParameter(i) for i in range(n_par)])
    perr = np.array([tf1.GetParError(i)  for i in range(n_par)])
    chi2 = float(tf1.GetChisquare())
    ndf  = int(tf1.GetNDF())

    # Cleanup ROOT objects to avoid name collisions
    ROOT.gROOT.DeleteAll() if False else None   # don't nuke everything
    h.Delete()
    tf1.Delete()

    return popt, perr, chi2, ndf, ok


# ─────────────────────────────────────────────────────────────────────────────
# Model components (shared, numpy-based — work with scalar x too)
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    s = max(abs(sigma), 1e-6)
    return N * np.exp(-0.5 * ((x - mu) / s) ** 2) / (s * np.sqrt(2 * np.pi))

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    """Simple Gaussian + cubic polynomial (Stage 1)."""
    s = max(abs(sigma), 1e-6)
    return (N * np.exp(-0.5 * ((x - mu) / s) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)

def _c14_pileup(x, E0):
    E0 = max(abs(E0), 1e-6)
    return np.where(x < E0, x / E0, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# V1 Compton shape
# ─────────────────────────────────────────────────────────────────────────────

def _compton_shape_v1(x, mu):
    x_norm = x / max(abs(mu), 1e-6)
    shape  = (1.0 - np.exp(-x_norm / 0.6)) * np.exp(-x_norm / 0.4)
    shape  = np.where(x_norm < 1.0, shape, 0.0)
    return np.clip(shape, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# V2 Compton shape
# ─────────────────────────────────────────────────────────────────────────────

def _compton_shape_v2(x, mu, sigma_c_rel=0.04):
    mu_c    = mu * (E_COMPTON_511 / E_GE68_MEV)
    sigma_c = max(sigma_c_rel, 0.001) * mu_c
    plateau = 1.0 / (1.0 + np.exp((x - mu_c) / max(sigma_c, 1.0)))
    rise    = np.where(x > 0, 1.0 - np.exp(-x / (0.15 * max(abs(mu), 1.0))), 0.0)
    return np.clip(plateau * rise, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V1 (12 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_ge68_v1(x, N_gaus, mu, sigma_k,
                   N_compton, N_sec, sigma_sec_rel,
                   N_c14, E0_c14, p0, p1, p2, p3):
    sigma     = sigma_k * np.sqrt(max(abs(mu), 1.0))
    mu_sec    = mu * (E_SEC_MEV / E_GE68_MEV)
    sigma_sec = sigma_sec_rel * np.sqrt(max(abs(mu_sec), 1.0))
    peak      = _gauss(x, N_gaus,  mu,     sigma)
    compton   = N_compton * _compton_shape_v1(x, mu)
    sec_gamma = _gauss(x, N_sec, mu_sec, sigma_sec)
    pileup    = N_c14 * _c14_pileup(x, E0_c14)
    bkg       = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3
    return peak + compton + sec_gamma + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V2 (13 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_ge68_v2(x, N_full, mu, sigma_k,
                   N_1esc, mu_esc_ratio,
                   N_compton, sigma_c_rel,
                   N_c14, E0_c14,
                   p0, p1, p2, p3):
    sigma_full = sigma_k * np.sqrt(max(abs(mu), 1.0))
    mu_esc     = mu * mu_esc_ratio
    sigma_esc  = sigma_k * np.sqrt(max(abs(mu_esc), 1.0))
    peak       = _gauss(x, N_full,  mu,     sigma_full)
    escape     = _gauss(x, N_1esc,  mu_esc, sigma_esc)
    compton    = N_compton * _compton_shape_v2(x, mu, sigma_c_rel)
    pileup     = N_c14 * _c14_pileup(x, E0_c14)
    bkg        = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3
    return peak + escape + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# PEAK FINDER
# ─────────────────────────────────────────────────────────────────────────────

def _find_peak(cx, cy, printf=print):
    mid = len(cx) // 4
    search_cx, search_cy = cx[mid:], cy[mid:]
    if search_cy.max() < 10:
        search_cx, search_cy = cx, cy
    idx      = np.argmax(search_cy)
    mu_init  = float(search_cx[idx])
    amp_init = float(search_cy[idx])
    printf(f"  Peak found at {mu_init:.0f} PE  (height {amp_init:.0f} counts)")
    return mu_init, amp_init


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEMATIC STUDY (ROOT-based)
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """
    Vary fit window and polynomial degree to estimate systematic uncertainty.
    Uses ROOT TF1 fits (gauss + polynomial) for each variation.
    Returns (sys_mu, sys_sigma, sys_res_pct).
    """
    range_configs = [(5, 4), (6, 5), (8, 6)]
    poly_degrees  = [1, 2, 3]
    results       = []

    for (lo_sig, hi_sig) in range_configs:
        fit_min = mu_nom - lo_sig * sigma_nom
        fit_max = mu_nom + hi_sig * sigma_nom
        mask = (cx >= fit_min) & (cx <= fit_max)
        if mask.sum() < 10:
            continue
        cx_w, cy_w = cx[mask], cy[mask]

        for deg in poly_degrees:
            # Build gauss + poly-deg model
            n_poly = deg + 1

            def _trial_model(x_sc, *args):
                # args: [N, mu, sk, b0, b1, ..., b_deg]
                N_v, mu_v, sk_v = args[0], args[1], args[2]
                bp = args[3:]
                sig_v = sk_v * np.sqrt(max(abs(mu_v), 1.0))
                g_v   = N_v * np.exp(-0.5 * ((x_sc - mu_v) / max(sig_v, 1e-6))**2)
                poly  = sum(bp[k] * x_sc**k for k in range(len(bp)))
                return float(g_v + poly)

            n_par_t = 3 + n_poly
            bkg_p0  = [float(cy_w.mean())] + [0.0] * deg
            p0_t    = [float(cy_w.max()), mu_nom,
                       sigma_nom / max(np.sqrt(mu_nom), 1.0)] + bkg_p0
            lo_t    = [0, mu_nom * 0.7, 0.01] + [-1e30] * n_poly
            hi_t    = [float(cy_w.max()) * 20, mu_nom * 1.3, 10.0] + [1e30] * n_poly

            popt, perr, chi2, ndf, ok = _root_fit(
                _trial_model, cx_w, cy_w, p0_t, lo_t, hi_t,
                float(cx_w[0]), float(cx_w[-1]))

            if popt is None or not ok:
                continue

            mu_i  = popt[1]
            sk_i  = popt[2]
            sig_i = sk_i * np.sqrt(max(abs(mu_i), 1.0))
            denom = mu_i - dark_noise_pe
            if denom > 0 and sig_i > 0:
                results.append((mu_i, sig_i, sig_i / denom))

    if len(results) < 2:
        return 0.0, 0.0, 0.0

    mus  = [r[0] for r in results]
    sigs = [r[1] for r in results]
    ress = [r[2] for r in results]
    return float(np.std(mus)), float(np.std(sigs)), float(np.std(ress) * 100)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe, chi2, ndf,
                  sys_mu, sys_sig, sys_res, method, source_energy_mev, popt):
    denom = mu - dark_noise_pe
    if denom <= 0:
        return None
    resolution = sigma / denom
    res_err = (resolution * np.sqrt((sig_err / sigma)**2 + (mu_err / denom)**2)
               if sigma > 0 else 0.0)
    LY     = denom / source_energy_mev
    LY_err = mu_err / source_energy_mev

    return dict(
        method=method,
        peak=float(mu), sigma=float(sigma),
        peak_error=float(np.sqrt(mu_err**2 + sys_mu**2)),
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error=float(np.sqrt(sig_err**2 + sys_sig**2)),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(resolution),
        resolution_error=float(np.sqrt(res_err**2 + (sys_res / 100)**2)),
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100),
        resolution_pct=float(resolution * 100),
        resolution_pct_err=float(np.sqrt(res_err**2 + (sys_res / 100)**2) * 100),
        resolution_pct_err_stat=float(res_err * 100),
        resolution_pct_err_sys=float(sys_res),
        LY_PE_per_MeV=float(LY), LY_PE_per_MeV_err=float(LY_err),
        dark_noise_PE=float(dark_noise_pe),
        chi2=float(chi2), ndf=int(ndf),
        chi2_ndf=float(chi2 / ndf) if ndf > 0 else -1.0,
        status=True,
        _fit_params=popt.tolist() if hasattr(popt, 'tolist') else list(popt),
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1: Gaussian + pol3  (ROOT TF1)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                    source_energy_mev=E_GE68_MEV, printf=print):
    sig_init = mu_init * 0.03
    fit_min  = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fit_max  = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask     = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 8:
        printf(f"  gauss+pol3: window too narrow ({mask.sum()} bins)")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]
    p0_init = [amp_init, mu_init, sig_init, float(cy_fit.min()) + 1, 0.0, 0.0, 0.0]
    lo      = [0.0,          mu_init * 0.7, sig_init * 0.1, -1e30, -1e30, -1e30, -1e30]
    hi      = [amp_init * 20, mu_init * 1.3, sig_init * 5.0,  1e30,  1e30,  1e30,  1e30]

    popt, perr, chi2, ndf, ok = _root_fit(
        _gauss_pol3, cx_fit, cy_fit, p0_init, lo, hi,
        float(cx_fit[0]), float(cx_fit[-1]))

    if popt is None:
        printf("  gauss+pol3: ROOT fit returned None")
        return None
    if not ok:
        printf("  gauss+pol3: MIGRAD did not fully converge (using result anyway)")

    mu_fit    = float(popt[1])
    sigma_fit = abs(float(popt[2]))
    mu_err    = float(perr[1])
    sig_err   = float(perr[2])

    if sigma_fit <= 0 or (mu_fit - dark_noise_pe) <= 0:
        printf(f"  gauss+pol3: unphysical (μ={mu_fit:.0f}, σ={sigma_fit:.0f})")
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu_fit, sigma_fit, dark_noise_pe)
    return _build_result(mu_fit, sigma_fit, mu_err, sig_err, dark_noise_pe,
                         chi2, ndf, sys_mu, sys_sig, sys_res, 'gauss+pol3',
                         source_energy_mev, popt)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: Physics model  (ROOT TF1)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_physics(cx, cy, dark_noise_pe, simple_result,
                 source_energy_mev=E_GE68_MEV, model_version=2, printf=print):
    if simple_result is None:
        return None

    mu_init    = simple_result['peak']
    sigma_init = simple_result['sigma']
    sig_init   = mu_init * 0.03

    fit_min = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fit_max = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask    = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 15:
        printf(f"  physics v{model_version}: window too narrow ({mask.sum()} bins)")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]
    amp_init   = float(cy_fit.max())
    sigma_k_0  = sigma_init / np.sqrt(max(mu_init, 1.0))

    if model_version == 1:
        p0 = [amp_init, mu_init, sigma_k_0,
              amp_init * 0.3, amp_init * 0.05, 0.06,
              amp_init * 0.1, mu_init * 0.15,
              float(cy_fit.min()) + 1, 0.0, 0.0, 0.0]
        lo = [0.0,       mu_init * 0.8, 0.01,
              0.0, 0.0, 0.01,
              0.0, 1.0,
              0.0, -1e30, -1e30, -1e30]
        hi = [amp_init * 20, mu_init * 1.2, 10.0,
              amp_init * 5,  amp_init * 2,  0.15,
              amp_init * 5,  mu_init * 0.5,
              float(cy_fit.max()) * 5, 1e30, 1e30, 1e30]
        model_fn  = _model_ge68_v1
        meth_name = 'physics_v1'
    else:
        p0 = [amp_init, mu_init, sigma_k_0,
              amp_init * 0.15, 0.50,
              amp_init * 0.2,  0.04,
              amp_init * 0.05, mu_init * 0.15,
              float(cy_fit.min()) + 1, 0.0, 0.0, 0.0]
        lo = [0.0,       mu_init * 0.8, 0.01,
              0.0, 0.40,
              0.0, 0.01,
              0.0, 1.0,
              0.0, -1e30, -1e30, -1e30]
        hi = [amp_init * 20, mu_init * 1.2, 10.0,
              amp_init * 5,  0.60,
              amp_init * 5,  0.10,
              amp_init * 5,  mu_init * 0.35,
              float(cy_fit.max()) * 5, 1e30, 1e30, 1e30]
        model_fn  = _model_ge68_v2
        meth_name = 'physics_v2'

    popt, perr, chi2, ndf, ok = _root_fit(
        model_fn, cx_fit, cy_fit, p0, lo, hi,
        float(cx_fit[0]), float(cx_fit[-1]))

    if popt is None:
        printf(f"  {meth_name}: ROOT fit returned None")
        return None
    if not ok:
        printf(f"  {meth_name}: MIGRAD did not fully converge")

    mu       = popt[1]
    sigma_k  = popt[2]
    sigma    = sigma_k * np.sqrt(max(abs(mu), 1.0))
    mu_err   = float(perr[1])
    sig_err  = float(np.sqrt((perr[2] * np.sqrt(max(abs(mu), 1.0)))**2
                              + (sigma_k / (2.0 * max(np.sqrt(abs(mu)), 1e-6)) * mu_err)**2))

    if sigma <= 0 or (mu - dark_noise_pe) <= 0:
        printf(f"  {meth_name}: unphysical (μ={mu:.0f}, σ={sigma:.0f})")
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dark_noise_pe)
    result = _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe,
                           chi2, ndf, sys_mu, sys_sig, sys_res,
                           meth_name, source_energy_mev, popt)

    if result is not None and model_version == 2:
        result['escape_fraction']  = float(popt[3] / popt[0]) if popt[0] > 0 else 0.0
        result['escape_peak_ratio'] = float(popt[4])

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API: fit_from_arrays (called by spectrum_utils)
# ─────────────────────────────────────────────────────────────────────────────

def fit_from_arrays(cx, cy, dark_noise_pe, source_energy_mev=E_GE68_MEV,
                    method_name="PE", printf=print, model_version=2):
    """
    Full two-stage Ge-68 fit from numpy arrays.

    Returns (simple_result, physics_result).
    Fitting uses ROOT TF1 (Minuit MIGRAD) — no scipy.
    """
    printf(f"\n  ── Ge-68 fit ({method_name}) ──")

    mu_init, amp_init = _find_peak(cx, cy, printf)
    if mu_init <= 0 or amp_init < 10:
        printf("  No peak found")
        return None, None

    # Stage 1
    simple = _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                             source_energy_mev, printf)
    if simple:
        printf(f"  gauss+pol3: μ={simple['peak']:.1f}, σ={simple['sigma']:.1f}, "
               f"res={simple['resolution_pct']:.2f}%, χ²/ndf={simple['chi2_ndf']:.2f}")

    # Stage 2
    physics = _fit_physics(cx, cy, dark_noise_pe, simple,
                           source_energy_mev, model_version, printf)
    if physics:
        printf(f"  {physics['method']}: μ={physics['peak']:.1f}, σ={physics['sigma']:.1f}, "
               f"res={physics['resolution_pct']:.2f}%, χ²/ndf={physics['chi2_ndf']:.2f}")
        if 'escape_fraction' in physics:
            printf(f"    escape fraction: {physics['escape_fraction']:.3f}, "
                   f"μ_esc/μ = {physics['escape_peak_ratio']:.3f}")

    return simple, physics


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE
# ─────────────────────────────────────────────────────────────────────────────

def load_spectrum(root_path):
    """Load spectrum histogram and dark noise from ROOT file."""
    if HAS_UPROOT:
        with uproot.open(root_path) as f:
            for key in ['h_pe_cont', 'h_pe_discrete', 'h_pe']:
                if key in f:
                    h     = f[key]
                    vals, edges = h.to_numpy()
                    cx    = 0.5 * (edges[:-1] + edges[1:])
                    cy    = vals
                    break
            else:
                raise RuntimeError(f"No PE histogram found in {root_path}")
            dn = DN_PE_DEFAULT
            try:
                dn_obj = f['dark_noise_pe']
                dn = float(str(dn_obj))
            except Exception:
                pass
        return cx, cy, dn

    f = ROOT.TFile.Open(root_path, "READ")
    if not f or f.IsZombie():
        raise RuntimeError(f"Cannot open {root_path}")
    h = None
    for key in ['h_pe_cont', 'h_pe_discrete', 'h_pe']:
        h = f.Get(key)
        if h:
            break
    if not h:
        f.Close()
        raise RuntimeError(f"No PE histogram in {root_path}")
    n  = h.GetNbinsX()
    cx = np.array([h.GetBinCenter(b)  for b in range(1, n + 1)])
    cy = np.array([h.GetBinContent(b) for b in range(1, n + 1)])
    dn = DN_PE_DEFAULT
    dn_obj = f.Get("dark_noise_pe")
    if dn_obj:
        try:
            dn = float(dn_obj.GetTitle())
        except Exception:
            pass
    f.Close()
    return cx, cy, dn


def fit_ge68(root_path, model_version=2, printf=print):
    cx, cy, dn = load_spectrum(root_path)
    return fit_from_arrays(cx, cy, dn, model_version=model_version, printf=printf)


def main():
    parser = argparse.ArgumentParser(description='Ge-68 peak fitting (ROOT TF1)')
    parser.add_argument('input', help='ROOT file or directory')
    parser.add_argument('--output-dir', default='fits')
    parser.add_argument('--model-version', type=int, default=2, choices=[1, 2])
    parser.add_argument('--scan', action='store_true')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.scan and os.path.isdir(args.input):
        files = sorted(glob.glob(os.path.join(args.input, '*.root')))
    else:
        files = [args.input]

    for fpath in files:
        print(f"\n{'='*60}")
        print(f"Processing: {os.path.basename(fpath)}")
        simple, physics = fit_ge68(fpath, model_version=args.model_version)

        basename  = os.path.splitext(os.path.basename(fpath))[0]
        json_path = os.path.join(args.output_dir, f'{basename}_ge68_fit.json')
        result    = {}
        if simple:
            result['simple'] = simple
        if physics:
            result['physics'] = physics
        with open(json_path, 'w') as jf:
            json.dump(result, jf, indent=2)
        print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
