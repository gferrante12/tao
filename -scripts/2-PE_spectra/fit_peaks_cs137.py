#!/usr/bin/env python3
"""
fit_peaks_cs137.py  —  Two-stage peak fitting for Cs-137 spectra (ROOT TF1 version)

Stage 1: Gaussian + pol3  (robust, data-driven)
Stage 2: Physics model — v1 or v2:
    v1: Compton edge (tanh) + 14C pileup + pol2  (original, 9 params)
    v2: Compton edge (FD) + backscatter peak + 14C + pol2  (improved, 11 params)

All fits performed with ROOT TF1 (MIGRAD via Minuit2). No scipy.

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
    raise RuntimeError("ROOT (PyROOT) is required for fit_peaks_cs137.")


# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
E_CS137_MEV   = 0.6617
M_E_MEV       = 0.511
_ALPHA        = E_CS137_MEV / M_E_MEV
E_COMPTON_MEV = E_CS137_MEV * 2 * _ALPHA / (1 + 2 * _ALPHA)
E_BSCAT_MEV   = E_CS137_MEV - E_COMPTON_MEV
RATIO_COMPTON = E_COMPTON_MEV / E_CS137_MEV
RATIO_BSCAT   = E_BSCAT_MEV  / E_CS137_MEV
DN_PE_DEFAULT = 90.0

FIT_WINDOW_SIGMA_LO = 6.0
FIT_WINDOW_SIGMA_HI = 5.0

_FIT_COUNTER = 0


# ─────────────────────────────────────────────────────────────────────────────
# ROOT helpers  (same pattern as fit_peaks_ge68.py)
# ─────────────────────────────────────────────────────────────────────────────

def _unique_name(prefix="f"):
    global _FIT_COUNTER
    _FIT_COUNTER += 1
    return f"{prefix}_{_FIT_COUNTER}"


def _arrays_to_th1d(cx, cy, name=None):
    name = name or _unique_name("h")
    n    = len(cx)
    if n < 2:
        return None
    dx  = (cx[-1] - cx[0]) / max(n - 1, 1)
    xlo = float(cx[0]  - 0.5 * dx)
    xhi = float(cx[-1] + 0.5 * dx)
    h   = ROOT.TH1D(name, "", n, xlo, xhi)
    h.SetDirectory(0)
    for i in range(n):
        v = float(cy[i])
        h.SetBinContent(i + 1, v)
        h.SetBinError(i + 1, float(max(1.0, np.sqrt(max(v, 1.0)))))
    return h


class _RootCallable:
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
    """Fit model_fn with ROOT TF1 (Minuit MIGRAD). Returns (popt, perr, chi2, ndf, ok)."""
    n_par     = len(p0)
    rcallable = _RootCallable(model_fn, n_par)
    tf1_name  = _unique_name("tf1")
    h_name    = _unique_name("h_fit")

    tf1 = ROOT.TF1(tf1_name, rcallable, xmin, xmax, n_par)
    tf1.SetNpx(1000)

    for i in range(n_par):
        tf1.SetParameter(i, float(p0[i]))
        lo_i, hi_i = float(lo[i]), float(hi[i])
        if lo_i > -1e29 and hi_i < 1e29:
            tf1.SetParLimits(i, lo_i, hi_i)

    h = _arrays_to_th1d(cx_fit, cy_fit, h_name)
    if h is None:
        return None, None, -1.0, 0, False

    fit_result = h.Fit(tf1, "Q N S R")
    ok   = (int(fit_result) == 0)
    popt = np.array([tf1.GetParameter(i) for i in range(n_par)])
    perr = np.array([tf1.GetParError(i)  for i in range(n_par)])
    chi2 = float(tf1.GetChisquare())
    ndf  = int(tf1.GetNDF())

    h.Delete()
    tf1.Delete()
    return popt, perr, chi2, ndf, ok


# ─────────────────────────────────────────────────────────────────────────────
# Model components
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    s = max(abs(sigma), 1e-6)
    return N * np.exp(-0.5 * ((x - mu) / s)**2) / (s * np.sqrt(2 * np.pi))

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    s = max(abs(sigma), 1e-6)
    return (N * np.exp(-0.5 * ((x - mu) / s)**2)
            + p0 + p1 * x + p2 * x**2 + p3 * x**3)

def _c14_pileup(x, E0):
    E0 = max(abs(E0), 1e-6)
    return np.where((x > 0) & (x < E0), x / E0, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# V1 Compton edge (tanh)
# ─────────────────────────────────────────────────────────────────────────────

def _compton_cs137_v1(x, mu_peak):
    mu_c    = mu_peak * RATIO_COMPTON
    sigma_c = mu_c * 0.03
    plateau = 0.5 * (1.0 - np.tanh((x - mu_c) / max(sigma_c, 1.0)))
    return np.clip(plateau, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# V2 Compton edge (Fermi-Dirac)
# ─────────────────────────────────────────────────────────────────────────────

def _compton_cs137_v2(x, mu_peak, sigma_c_rel):
    mu_c    = mu_peak * RATIO_COMPTON
    sigma_c = max(sigma_c_rel, 0.005) * mu_c
    arg     = np.clip((x - mu_c) / max(sigma_c, 1e-6), -500, 500)
    plateau = 1.0 / (1.0 + np.exp(arg))
    return np.clip(plateau, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V1  (9 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_cs137_v1(x, N_gaus, mu, sigma_k,
                    N_compton, N_c14, E0_c14, p0, p1, p2):
    sigma   = sigma_k * np.sqrt(max(abs(mu), 1.0))
    peak    = _gauss(x, N_gaus, mu, sigma)
    compton = N_compton * _compton_cs137_v1(x, mu)
    pileup  = N_c14 * _c14_pileup(x, E0_c14)
    bkg     = p0 + p1 * x + p2 * x**2
    return peak + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V2  (11 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_cs137_v2(x, N_peak, mu, sigma_k,
                    N_compton, sigma_c_rel,
                    N_bscat, sigma_bs_rel,
                    N_c14, E0_c14,
                    p0, p1):
    sigma    = sigma_k * np.sqrt(max(abs(mu), 1.0))
    mu_bs    = mu * RATIO_BSCAT
    sigma_bs = sigma_bs_rel * np.sqrt(max(abs(mu_bs), 1.0))
    peak     = _gauss(x, N_peak,  mu,    sigma)
    compton  = N_compton * _compton_cs137_v2(x, mu, sigma_c_rel)
    bscat    = _gauss(x, N_bscat, mu_bs, sigma_bs)
    pileup   = N_c14 * _c14_pileup(x, E0_c14)
    bkg      = p0 + p1 * x
    return peak + compton + bscat + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# PEAK FINDER
# ─────────────────────────────────────────────────────────────────────────────

def _find_peak(cx, cy, printf=print):
    mid = len(cx) // 4
    scx, scy = cx[mid:], cy[mid:]
    if scy.max() < 10:
        scx, scy = cx, cy
    idx      = np.argmax(scy)
    mu_init  = float(scx[idx])
    amp_init = float(scy[idx])
    printf(f"  Peak found at {mu_init:.0f} PE  (height {amp_init:.0f})")
    return mu_init, amp_init


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEMATIC STUDY (ROOT-based)
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """Vary fit window and polynomial degree; return (sys_mu, sys_sigma, sys_res_pct)."""
    configs   = [(5, 4), (6, 5), (8, 6)]
    poly_degs = [1, 2, 3]
    results   = []

    for (lo_sig, hi_sig) in configs:
        fmin = mu_nom - lo_sig * sigma_nom
        fmax = mu_nom + hi_sig * sigma_nom
        mask = (cx >= fmin) & (cx <= fmax)
        if mask.sum() < 10:
            continue
        cxw, cyw = cx[mask], cy[mask]

        for deg in poly_degs:
            n_poly = deg + 1

            def _trial(x_sc, *args):
                N_v, mu_v, sk_v = args[0], args[1], args[2]
                bp = args[3:]
                sig_v = sk_v * np.sqrt(max(abs(mu_v), 1.0))
                g_v   = N_v * np.exp(-0.5 * ((x_sc - mu_v) / max(sig_v, 1e-6))**2)
                poly  = sum(bp[k] * x_sc**k for k in range(len(bp)))
                return float(g_v + poly)

            bkg_p0 = [float(cyw.mean())] + [0.0] * deg
            p0_t   = [float(cyw.max()), mu_nom,
                      sigma_nom / max(np.sqrt(mu_nom), 1.0)] + bkg_p0
            lo_t   = [0.0, mu_nom * 0.7, 0.01] + [-1e30] * n_poly
            hi_t   = [float(cyw.max()) * 20, mu_nom * 1.3, 10.0] + [1e30] * n_poly

            popt, perr, chi2, ndf, ok = _root_fit(
                _trial, cxw, cyw, p0_t, lo_t, hi_t,
                float(cxw[0]), float(cxw[-1]))

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
    return (float(np.std([r[0] for r in results])),
            float(np.std([r[1] for r in results])),
            float(np.std([r[2] for r in results]) * 100))


# ─────────────────────────────────────────────────────────────────────────────
# RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(mu, sigma, mu_err, sig_err, dn, chi2, ndf,
                  sys_mu, sys_sig, sys_res, method, E_src, popt):
    denom = mu - dn
    if denom <= 0:
        return None
    res     = sigma / denom
    res_err = (res * np.sqrt((sig_err / sigma)**2 + (mu_err / denom)**2)
               if sigma > 0 else 0.0)
    LY = denom / E_src
    return dict(
        method=method,
        peak=float(mu), sigma=float(sigma),
        peak_error=float(np.sqrt(mu_err**2 + sys_mu**2)),
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error=float(np.sqrt(sig_err**2 + sys_sig**2)),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(res),
        resolution_error=float(np.sqrt(res_err**2 + (sys_res / 100)**2)),
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100),
        resolution_pct=float(res * 100),
        resolution_pct_err=float(np.sqrt(res_err**2 + (sys_res / 100)**2) * 100),
        resolution_pct_err_stat=float(res_err * 100),
        resolution_pct_err_sys=float(sys_res),
        LY_PE_per_MeV=float(LY), LY_PE_per_MeV_err=float(mu_err / E_src),
        dark_noise_PE=float(dn),
        chi2=float(chi2), ndf=int(ndf),
        chi2_ndf=float(chi2 / ndf) if ndf > 0 else -1.0,
        status=True,
        _fit_params=popt.tolist() if hasattr(popt, 'tolist') else list(popt),
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1  (ROOT TF1)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_gauss_pol3(cx, cy, dn, mu_init, amp_init,
                    E_src=E_CS137_MEV, printf=print):
    sig_init = mu_init * 0.04
    fmin     = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fmax     = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask     = (cx >= fmin) & (cx <= fmax)
    if mask.sum() < 8:
        printf(f"  gauss+pol3: too narrow ({mask.sum()} bins)")
        return None

    cxf, cyf = cx[mask], cy[mask]
    p0 = [amp_init, mu_init, sig_init, float(cyf.min()) + 1, 0.0, 0.0, 0.0]
    lo = [0.0, mu_init * 0.7, sig_init * 0.1, -1e30, -1e30, -1e30, -1e30]
    hi = [amp_init * 20, mu_init * 1.3, sig_init * 5, 1e30, 1e30, 1e30, 1e30]

    popt, perr, chi2, ndf, ok = _root_fit(
        _gauss_pol3, cxf, cyf, p0, lo, hi,
        float(cxf[0]), float(cxf[-1]))

    if popt is None:
        printf("  gauss+pol3: ROOT fit returned None")
        return None

    mu, sigma = float(popt[1]), abs(float(popt[2]))
    if sigma <= 0 or (mu - dn) <= 0:
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dn)
    return _build_result(mu, sigma, float(perr[1]), float(perr[2]), dn,
                         chi2, ndf, sys_mu, sys_sig, sys_res,
                         'gauss+pol3', E_src, popt)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2  (ROOT TF1)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_physics(cx, cy, dn, simple, E_src=E_CS137_MEV,
                 model_version=2, printf=print):
    if simple is None:
        return None

    mu_init    = simple['peak']
    sigma_init = simple['sigma']
    sig_init   = mu_init * 0.04

    fmin = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fmax = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask = (cx >= fmin) & (cx <= fmax)
    if mask.sum() < 15:
        printf(f"  physics v{model_version}: too narrow ({mask.sum()} bins)")
        return None

    cxf, cyf = cx[mask], cy[mask]
    amp  = float(cyf.max())
    sk   = sigma_init / max(np.sqrt(mu_init), 1.0)

    if model_version == 1:
        p0 = [amp, mu_init, sk,
              amp * 0.3, amp * 0.05, mu_init * 0.1,
              float(cyf.min()) + 1, 0.0, 0.0]
        lo = [0.0, mu_init * 0.8, 0.01,
              0.0, 0.0, 1.0,
              0.0, -1e30, -1e30]
        hi = [amp * 20, mu_init * 1.2, 10.0,
              amp * 5,  amp * 3, mu_init * 0.4,
              float(cyf.max()) * 5, 1e30, 1e30]
        model_fn = _model_cs137_v1
        mname    = 'physics_v1'
    else:
        p0 = [amp, mu_init, sk,
              amp * 0.3, 0.03,
              amp * 0.05, 0.06,
              amp * 0.03, mu_init * 0.1,
              float(cyf.min()) + 1, 0.0]
        lo = [0.0, mu_init * 0.8, 0.01,
              0.0, 0.01,
              0.0, 0.02,
              0.0, 1.0,
              0.0, -1e30]
        hi = [amp * 20, mu_init * 1.2, 10.0,
              amp * 5,  0.08,
              amp * 2,  0.15,
              amp * 3,  mu_init * 0.35,
              float(cyf.max()) * 5, 1e30]
        model_fn = _model_cs137_v2
        mname    = 'physics_v2'

    popt, perr, chi2, ndf, ok = _root_fit(
        model_fn, cxf, cyf, p0, lo, hi,
        float(cxf[0]), float(cxf[-1]))

    if popt is None:
        printf(f"  {mname}: ROOT fit returned None")
        return None
    if not ok:
        printf(f"  {mname}: MIGRAD did not fully converge")

    mu      = popt[1]
    sk_fit  = popt[2]
    sigma   = sk_fit * np.sqrt(max(abs(mu), 1.0))
    mu_err  = float(perr[1])
    sig_err = float(np.sqrt((perr[2] * np.sqrt(max(abs(mu), 1.0)))**2
                             + (sk_fit / (2.0 * max(np.sqrt(abs(mu)), 1e-6)) * mu_err)**2))

    if sigma <= 0 or (mu - dn) <= 0:
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dn)
    result = _build_result(mu, sigma, mu_err, sig_err, dn,
                           chi2, ndf, sys_mu, sys_sig, sys_res,
                           mname, E_src, popt)

    if result and model_version == 2:
        result['compton_edge_smearing']  = float(popt[4])
        result['backscatter_fraction']   = float(popt[5] / popt[0]) if popt[0] > 0 else 0.0

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def fit_from_arrays(cx, cy, dn, source_energy_mev=E_CS137_MEV,
                    method_name="PE", printf=print, model_version=2):
    """
    Full two-stage Cs-137 fit from numpy arrays.
    Returns (simple_result, physics_result).
    Fitting uses ROOT TF1 (Minuit MIGRAD) — no scipy.
    """
    printf(f"\n  ── Cs-137 fit ({method_name}) ──")
    mu_init, amp_init = _find_peak(cx, cy, printf)
    if mu_init <= 0 or amp_init < 10:
        return None, None

    simple = _fit_gauss_pol3(cx, cy, dn, mu_init, amp_init, source_energy_mev, printf)
    if simple:
        printf(f"  gauss+pol3: μ={simple['peak']:.1f}, res={simple['resolution_pct']:.2f}%")

    physics = _fit_physics(cx, cy, dn, simple, source_energy_mev, model_version, printf)
    if physics:
        printf(f"  {physics['method']}: μ={physics['peak']:.1f}, "
               f"res={physics['resolution_pct']:.2f}%, χ²/ndf={physics['chi2_ndf']:.2f}")

    return simple, physics


def main():
    parser = argparse.ArgumentParser(description='Cs-137 peak fitting (ROOT TF1)')
    parser.add_argument('input', help='ROOT file or directory')
    parser.add_argument('--output-dir', default='fits')
    parser.add_argument('--model-version', type=int, default=2, choices=[1, 2])
    parser.add_argument('--scan', action='store_true')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("Use fit_from_arrays() via spectrum_utils.fit_source() for integrated pipeline.")


if __name__ == "__main__":
    main()
