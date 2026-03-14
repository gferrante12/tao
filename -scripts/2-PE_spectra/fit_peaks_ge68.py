#!/usr/bin/env python3
"""
fit_peaks_ge68.py  —  Two-stage peak fitting for Ge-68 spectra

Stage 1: Gaussian + pol3  (robust, data-driven initialization)
Stage 2: Full physics model — v1 or v2:
    v1: Compton + secondary γ + 14C pileup + pol3  (original)
    v2: Single-escape + Compton + 14C pileup + pol3  (improved for TAO 1.8m)

Both stage-1 and stage-2 results are returned.
All fits use ROOT TF1 (no scipy).

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
    raise ImportError("ROOT (PyROOT) is required for fitting in fit_peaks_ge68.py")


# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
E_GE68_MEV    = 1.022
E_SEC_MEV     = 1.08
M_E_MEV       = 0.511
DN_PE_DEFAULT = 134.0

FIT_WINDOW_SIGMA_LO = 7.0
FIT_WINDOW_SIGMA_HI = 6.0

_ALPHA_511    = M_E_MEV / M_E_MEV
E_COMPTON_511 = M_E_MEV * 2 * _ALPHA_511 / (1 + 2 * _ALPHA_511)


# ─────────────────────────────────────────────────────────────────────────────
# ROOT-based curve fitting helper
# ─────────────────────────────────────────────────────────────────────────────

_fit_counter = 0  # unique naming of ROOT objects


def _root_curve_fit(model_func, cx_fit, cy_fit, p0, bounds_lo, bounds_hi,
                    maxfev=20000):
    """
    ROOT TF1-based curve fitting replacing scipy.optimize.curve_fit.

    Parameters
    ----------
    model_func : callable, signature f(x_array, *params) -> y_array
    cx_fit     : x bin centres (numpy array)
    cy_fit     : y counts (numpy array)
    p0         : initial parameters (list/array)
    bounds_lo  : lower bounds (list/array)
    bounds_hi  : upper bounds (list/array)

    Returns
    -------
    popt  : np.ndarray of fitted parameters
    perr  : np.ndarray of parameter uncertainties
    pcov  : np.ndarray covariance matrix  (n x n)
    chi2  : float, chi-squared value
    ndf   : int, degrees of freedom
    """
    global _fit_counter
    _fit_counter += 1
    uid = _fit_counter

    n_params = len(p0)
    n_bins   = len(cx_fit)
    if n_bins < 2:
        raise RuntimeError("Too few bins for fitting")

    bw   = float(cx_fit[1] - cx_fit[0])
    xmin = float(cx_fit[0]  - bw / 2)
    xmax = float(cx_fit[-1] + bw / 2)

    # Build TH1D
    hname = f"_h_ge68_{uid}"
    h = ROOT.TH1D(hname, "", n_bins, xmin, xmax)
    ROOT.SetOwnership(h, True)
    for i in range(n_bins):
        v = float(cy_fit[i])
        h.SetBinContent(i + 1, v)
        h.SetBinError(i + 1, max(1.0, float(np.sqrt(abs(v)))))

    # TF1 callback wrapping numpy model
    _f  = model_func
    _np = n_params

    def _cb(x, p):
        try:
            params = [float(p[i]) for i in range(_np)]
            y = _f(np.array([x[0]]), *params)
            return float(y[0])
        except Exception:
            return 0.0

    fname = f"_tf1_ge68_{uid}"
    tf1 = ROOT.TF1(fname, _cb, float(cx_fit[0]), float(cx_fit[-1]), n_params)
    ROOT.SetOwnership(tf1, True)

    for i in range(n_params):
        tf1.SetParameter(i, float(p0[i]))
        lo_i = float(bounds_lo[i]) if bounds_lo is not None else -1e30
        hi_i = float(bounds_hi[i]) if bounds_hi is not None else  1e30
        if lo_i != hi_i:
            tf1.SetParLimits(i, lo_i, hi_i)

    # S = save result, N = no graphics, Q = quiet, R = use TF1 range
    fr = h.Fit(tf1, "SNQR")

    popt = np.array([tf1.GetParameter(i) for i in range(n_params)], dtype=float)
    perr = np.array([tf1.GetParError(i)  for i in range(n_params)], dtype=float)
    chi2 = float(tf1.GetChisquare())
    ndf  = int(tf1.GetNDF())

    pcov = np.diag(perr ** 2)
    try:
        cmat = fr.GetCovarianceMatrix()
        for i in range(n_params):
            for j in range(n_params):
                pcov[i, j] = float(cmat[i][j])
    except Exception:
        pass

    h.Delete()
    tf1.Delete()
    return popt, perr, pcov, chi2, ndf


# ─────────────────────────────────────────────────────────────────────────────
# Model components
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)

def _c14_pileup(x, E0):
    return np.where(x < E0, x / E0, 0.0)

def _compton_shape_v1(x, mu):
    x_norm = x / mu
    shape  = (1.0 - np.exp(-x_norm / 0.6)) * np.exp(-x_norm / 0.4)
    shape  = np.where(x_norm < 1.0, shape, 0.0)
    return np.clip(shape, 0, None)

def _compton_shape_v2(x, mu, sigma_c_rel=0.04):
    mu_c    = mu * (E_COMPTON_511 / E_GE68_MEV)
    sigma_c = sigma_c_rel * mu_c
    plateau = 1.0 / (1.0 + np.exp((x - mu_c) / max(sigma_c, 1.0)))
    rise    = np.where(x > 0, 1.0 - np.exp(-x / (0.15 * mu)), 0.0)
    return np.clip(plateau * rise, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V1  (12 free parameters)
# ─────────────────────────────────────────────────────────────────────────────

def _model_ge68_v1(x, N_gaus, mu, sigma_k,
                   N_compton, N_sec, sigma_sec_rel,
                   N_c14, E0_c14, p0, p1, p2, p3):
    sigma     = sigma_k * np.sqrt(mu)
    mu_sec    = mu * (E_SEC_MEV / E_GE68_MEV)
    sigma_sec = sigma_sec_rel * np.sqrt(mu_sec)
    peak      = _gauss(x, N_gaus, mu, sigma)
    compton   = N_compton * _compton_shape_v1(x, mu)
    sec_gamma = _gauss(x, N_sec, mu_sec, sigma_sec)
    pileup    = N_c14 * _c14_pileup(x, E0_c14)
    bkg       = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3
    return peak + compton + sec_gamma + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V2  (13 free parameters)
# ─────────────────────────────────────────────────────────────────────────────

def _model_ge68_v2(x, N_full, mu, sigma_k,
                   N_1esc, mu_esc_ratio,
                   N_compton, sigma_c_rel,
                   N_c14, E0_c14,
                   p0, p1, p2, p3):
    sigma_full = sigma_k * np.sqrt(mu)
    mu_esc     = mu * mu_esc_ratio
    sigma_esc  = sigma_k * np.sqrt(mu_esc)
    peak       = _gauss(x, N_full, mu, sigma_full)
    escape     = _gauss(x, N_1esc, mu_esc, sigma_esc)
    compton    = N_compton * _compton_shape_v2(x, mu, sigma_c_rel)
    pileup     = N_c14 * _c14_pileup(x, E0_c14)
    bkg        = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3
    return peak + escape + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# Peak finder
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
# Result builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe, chi2, ndf,
                  sys_mu, sys_sig, sys_res, method, source_energy_mev, popt):
    denom = mu - dark_noise_pe
    if denom <= 0:
        return None
    resolution = sigma / denom
    res_err = (resolution * np.sqrt((sig_err / sigma) ** 2 + (mu_err / denom) ** 2)
               if sigma > 0 else 0.0)
    LY      = denom / source_energy_mev
    LY_err  = mu_err / source_energy_mev

    return dict(
        method=method,
        peak=float(mu), sigma=float(sigma),
        peak_error=float(np.sqrt(mu_err ** 2 + sys_mu ** 2)),
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error=float(np.sqrt(sig_err ** 2 + sys_sig ** 2)),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(resolution),
        resolution_error=float(np.sqrt(res_err ** 2 + (sys_res / 100) ** 2)),
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100),
        resolution_pct=float(resolution * 100),
        resolution_pct_err=float(np.sqrt(res_err ** 2 + (sys_res / 100) ** 2) * 100),
        resolution_pct_err_stat=float(res_err * 100),
        resolution_pct_err_sys=float(sys_res),
        LY_PE_per_MeV=float(LY), LY_PE_per_MeV_err=float(LY_err),
        dark_noise_PE=float(dark_noise_pe),
        chi2=float(chi2), ndf=int(ndf),
        chi2_ndf=float(chi2 / ndf) if ndf > 0 else -1,
        status=True,
        _fit_params=popt.tolist() if hasattr(popt, 'tolist') else list(popt),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Systematic study  (ROOT-based)
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """3 windows × 3 poly degrees → systematic spread, all fits via ROOT TF1."""
    range_configs = [(5, 4), (6, 5), (8, 6)]
    poly_degrees  = [1, 2, 3]
    results = []

    for (lo, hi) in range_configs:
        fit_min = mu_nom - lo * sigma_nom
        fit_max = mu_nom + hi * sigma_nom
        mask = (cx >= fit_min) & (cx <= fit_max)
        if mask.sum() < 10:
            continue
        cx_w, cy_w = cx[mask], cy[mask]

        for deg in poly_degrees:
            n_poly = deg + 1  # number of poly coefficients

            # Build model: Gauss + poly of degree `deg`
            def _trial_factory(ndeg):
                def _trial(x, N, mu, sk, *bp):
                    sig = sk * np.sqrt(np.maximum(mu, 1.0))
                    peak = N * np.exp(-0.5 * ((x - mu) / np.maximum(sig, 1.0)) ** 2)
                    poly = sum(bp[i] * x ** i for i in range(len(bp)))
                    return peak + poly
                return _trial

            trial_func = _trial_factory(deg)
            n_params_trial = 3 + (deg + 1)  # N, mu, sk, b0, b1, ..., b_deg

            bkg_p = [float(cy_w.mean())] + [0.0] * deg
            p0_t  = [float(cy_w.max()), float(mu_nom),
                     float(sigma_nom / np.sqrt(max(mu_nom, 1.0)))] + bkg_p
            lo_b  = [0.0, mu_nom * 0.7, 0.01] + [-1e30] * (deg + 1)
            hi_b  = [float(cy_w.max()) * 20, mu_nom * 1.3, 10.0] + [1e30] * (deg + 1)

            try:
                popt, perr, _, chi2, ndf = _root_curve_fit(
                    trial_func, cx_w, cy_w, p0_t, lo_b, hi_b)
                mu_i  = float(popt[1])
                sk_i  = float(popt[2])
                sig_i = sk_i * np.sqrt(max(mu_i, 1.0))
                denom = mu_i - dark_noise_pe
                if denom > 0 and sig_i > 0:
                    results.append((mu_i, sig_i, sig_i / denom))
            except Exception:
                continue

    if len(results) < 2:
        return 0.0, 0.0, 0.0

    mus  = [r[0] for r in results]
    sigs = [r[1] for r in results]
    ress = [r[2] for r in results]
    return float(np.std(mus)), float(np.std(sigs)), float(np.std(ress) * 100)


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
    lo = [0.0, mu_init * 0.7, sig_init * 0.1, -1e30, -1e30, -1e30, -1e30]
    hi = [amp_init * 20, mu_init * 1.3, sig_init * 5.0,  1e30,  1e30,  1e30,  1e30]

    try:
        popt, perr, _, chi2, ndf = _root_curve_fit(
            _gauss_pol3, cx_fit, cy_fit, p0_init, lo, hi)
    except Exception as exc:
        printf(f"  gauss+pol3: ROOT fit failed: {exc}")
        return None

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
    amp_init  = float(cy_fit.max())
    sigma_k_init = sigma_init / np.sqrt(mu_init) if mu_init > 0 else 2.0

    if model_version == 1:
        p0 = [amp_init, mu_init, sigma_k_init,
              amp_init * 0.3, amp_init * 0.05, 0.06,
              amp_init * 0.1, mu_init * 0.15,
              float(cy_fit.min()) + 1, 0.0, 0.0, 0.0]
        lo = [0.0, mu_init * 0.8, 0.01,
              0.0, 0.0, 0.01,
              0.0, 1.0,
              0.0, -1e30, -1e30, -1e30]
        hi = [amp_init * 20, mu_init * 1.2, 10.0,
              amp_init * 5, amp_init * 2, 0.15,
              amp_init * 5, mu_init * 0.5,
              cy_fit.max() * 5, 1e30, 1e30, 1e30]
        model_fn  = _model_ge68_v1
        method_name = 'physics_v1'
    else:
        p0 = [amp_init, mu_init, sigma_k_init,
              amp_init * 0.15, 0.50,
              amp_init * 0.2, 0.04,
              amp_init * 0.05, mu_init * 0.15,
              float(cy_fit.min()) + 1, 0.0, 0.0, 0.0]
        lo = [0.0, mu_init * 0.8, 0.01,
              0.0, 0.40,
              0.0, 0.01,
              0.0, 1.0,
              0.0, -1e30, -1e30, -1e30]
        hi = [amp_init * 20, mu_init * 1.2, 10.0,
              amp_init * 5, 0.60,
              amp_init * 5, 0.10,
              amp_init * 5, mu_init * 0.35,
              cy_fit.max() * 5, 1e30, 1e30, 1e30]
        model_fn  = _model_ge68_v2
        method_name = 'physics_v2'

    try:
        popt, perr, _, chi2, ndf = _root_curve_fit(
            model_fn, cx_fit, cy_fit, p0, lo, hi)
    except Exception as exc:
        printf(f"  {method_name}: ROOT fit failed: {exc}")
        return None

    mu        = float(popt[1])
    sigma_k   = float(popt[2])
    sigma     = sigma_k * np.sqrt(max(mu, 1.0))
    mu_err    = float(perr[1])
    sig_err   = float(np.sqrt((perr[2] * np.sqrt(mu)) ** 2
                              + (sigma_k / (2 * np.sqrt(max(mu, 1.0))) * mu_err) ** 2))

    if sigma <= 0 or (mu - dark_noise_pe) <= 0:
        printf(f"  {method_name}: unphysical (μ={mu:.0f}, σ={sigma:.0f})")
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dark_noise_pe)
    result = _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe,
                           chi2, ndf, sys_mu, sys_sig, sys_res,
                           method_name, source_energy_mev, popt)

    if result is not None and model_version == 2:
        result['escape_fraction']   = float(popt[3] / popt[0]) if popt[0] > 0 else 0.0
        result['escape_peak_ratio'] = float(popt[4])

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def fit_from_arrays(cx, cy, dark_noise_pe, source_energy_mev=E_GE68_MEV,
                    method_name="PE", printf=print, model_version=2):
    """
    Full two-stage Ge-68 fit from numpy arrays (ROOT TF1).
    Returns (simple_result, physics_result).
    """
    printf(f"\n  ── Ge-68 fit ({method_name}) ──")

    mu_init, amp_init = _find_peak(cx, cy, printf)
    if mu_init <= 0 or amp_init < 10:
        printf("  No peak found")
        return None, None

    simple = _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                             source_energy_mev, printf)
    if simple:
        printf(f"  gauss+pol3: μ={simple['peak']:.1f}, σ={simple['sigma']:.1f}, "
               f"res={simple['resolution_pct']:.2f}%, χ²/ndf={simple['chi2_ndf']:.2f}")

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
# Standalone file loader
# ─────────────────────────────────────────────────────────────────────────────

def load_spectrum(root_path):
    if HAS_UPROOT:
        with uproot.open(root_path) as f:
            for key in ['h_pe_cont', 'h_pe_discrete', 'h_pe']:
                if key in f:
                    h = f[key]
                    vals, edges = h.to_numpy()
                    cx = 0.5 * (edges[:-1] + edges[1:])
                    cy = vals
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

    if HAS_ROOT:
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

    raise RuntimeError("Neither uproot nor ROOT available")


def fit_ge68(root_path, model_version=2, printf=print):
    cx, cy, dn = load_spectrum(root_path)
    return fit_from_arrays(cx, cy, dn, model_version=model_version, printf=printf)


def main():
    parser = argparse.ArgumentParser(description='Ge-68 peak fitting (ROOT TF1)')
    parser.add_argument('input', help='ROOT file or directory')
    parser.add_argument('--output-dir', default='fits')
    parser.add_argument('--model-version', type=int, default=2, choices=[1, 2])
    parser.add_argument('--scan', action='store_true',
                        help='Process all ROOT files in directory')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.scan and os.path.isdir(args.input):
        files = sorted(glob.glob(os.path.join(args.input, '*.root')))
    else:
        files = [args.input]

    for fpath in files:
        print(f"\n{'=' * 60}")
        print(f"Processing: {os.path.basename(fpath)}")
        simple, physics = fit_ge68(fpath, model_version=args.model_version)

        basename = os.path.splitext(os.path.basename(fpath))[0]
        json_path = os.path.join(args.output_dir, f'{basename}_ge68_fit.json')
        result = {}
        if simple:
            result['simple'] = simple
        if physics:
            result['physics'] = physics
        with open(json_path, 'w') as jf:
            json.dump(result, jf, indent=2)
        print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
