#!/usr/bin/env python3
"""
fit_peaks_cs137.py  —  Two-stage peak fitting for Cs-137 spectra

Stage 1: Gaussian + pol3  (robust, data-driven)
Stage 2: Physics model — v1 or v2:
    v1: Compton edge (tanh) + 14C pileup + pol2  (original, 9 params)
    v2: Compton edge (FD) + backscatter peak + 14C + pol2  (improved, 11 params)

All fits use ROOT TF1 (no scipy).
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
    raise ImportError("ROOT (PyROOT) is required for fitting in fit_peaks_cs137.py")


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


# ─────────────────────────────────────────────────────────────────────────────
# ROOT fitting helper  (shared with fit_peaks_ge68.py pattern)
# ─────────────────────────────────────────────────────────────────────────────

_fit_counter = 0


def _root_curve_fit(model_func, cx_fit, cy_fit, p0, bounds_lo, bounds_hi):
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

    hname = f"_h_cs137_{uid}"
    h = ROOT.TH1D(hname, "", n_bins, xmin, xmax)
    ROOT.SetOwnership(h, True)
    for i in range(n_bins):
        v = float(cy_fit[i])
        h.SetBinContent(i + 1, v)
        h.SetBinError(i + 1, max(1.0, float(np.sqrt(abs(v)))))

    _f  = model_func
    _np = n_params

    def _cb(x, p):
        try:
            params = [float(p[i]) for i in range(_np)]
            y = _f(np.array([x[0]]), *params)
            return float(y[0])
        except Exception:
            return 0.0

    fname = f"_tf1_cs137_{uid}"
    tf1 = ROOT.TF1(fname, _cb, float(cx_fit[0]), float(cx_fit[-1]), n_params)
    ROOT.SetOwnership(tf1, True)

    for i in range(n_params):
        tf1.SetParameter(i, float(p0[i]))
        lo_i = float(bounds_lo[i]) if bounds_lo is not None else -1e30
        hi_i = float(bounds_hi[i]) if bounds_hi is not None else  1e30
        if lo_i != hi_i:
            tf1.SetParLimits(i, lo_i, hi_i)

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
# Shared model components
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)

def _c14_pileup(x, E0):
    return np.where((x > 0) & (x < E0), x / E0, 0.0)

def _compton_cs137_v1(x, mu_peak):
    mu_c    = mu_peak * RATIO_COMPTON
    sigma_c = mu_c * 0.03
    plateau = 0.5 * (1.0 - np.tanh((x - mu_c) / max(sigma_c, 1.0)))
    return np.clip(plateau, 0, None)

def _compton_cs137_v2(x, mu_peak, sigma_c_rel):
    mu_c    = mu_peak * RATIO_COMPTON
    sigma_c = mu_c * max(sigma_c_rel, 0.005)
    arg     = np.clip((x - mu_c) / sigma_c, -500, 500)
    return np.clip(1.0 / (1.0 + np.exp(arg)), 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V1  (9 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_cs137_v1(x, N_gaus, mu, sigma_k,
                    N_compton, N_c14, E0_c14, p0, p1, p2):
    sigma   = sigma_k * np.sqrt(max(mu, 1.0))
    peak    = _gauss(x, N_gaus, mu, sigma)
    compton = N_compton * _compton_cs137_v1(x, mu)
    pileup  = N_c14 * _c14_pileup(x, E0_c14)
    bkg     = p0 + p1 * x + p2 * x ** 2
    return peak + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V2  (11 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_cs137_v2(x, N_peak, mu, sigma_k,
                    N_compton, sigma_c_rel,
                    N_bscat, sigma_bs_rel,
                    N_c14, E0_c14,
                    p0, p1):
    sigma    = sigma_k * np.sqrt(max(mu, 1.0))
    mu_bs    = mu * RATIO_BSCAT
    sigma_bs = sigma_bs_rel * np.sqrt(max(mu_bs, 1.0))
    peak     = _gauss(x, N_peak, mu, sigma)
    compton  = N_compton * _compton_cs137_v2(x, mu, sigma_c_rel)
    bscat    = _gauss(x, N_bscat, mu_bs, sigma_bs)
    pileup   = N_c14 * _c14_pileup(x, E0_c14)
    bkg      = p0 + p1 * x
    return peak + compton + bscat + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# Peak finder
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
# Systematic study  (ROOT-based)
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    configs   = [(5, 4), (6, 5), (8, 6)]
    poly_degs = [1, 2, 3]
    results   = []

    for (lo, hi) in configs:
        fmin = mu_nom - lo * sigma_nom
        fmax = mu_nom + hi * sigma_nom
        mask = (cx >= fmin) & (cx <= fmax)
        if mask.sum() < 10:
            continue
        cxw, cyw = cx[mask], cy[mask]

        for deg in poly_degs:
            def _trial_factory(ndeg):
                def _trial(x, N, mu, sk, *bp):
                    sig = sk * np.sqrt(np.maximum(mu, 1.0))
                    return (N * np.exp(-0.5 * ((x - mu) / np.maximum(sig, 1.0)) ** 2)
                            + sum(bp[i] * x ** i for i in range(len(bp))))
                return _trial

            trial_func = _trial_factory(deg)
            n_p = 3 + (deg + 1)
            bkg_p = [float(cyw.mean())] + [0.0] * deg
            p0_t  = [float(cyw.max()), float(mu_nom),
                     float(sigma_nom / np.sqrt(max(mu_nom, 1.0)))] + bkg_p
            lo_b  = [0.0, mu_nom * 0.7, 0.01] + [-1e30] * (deg + 1)
            hi_b  = [float(cyw.max()) * 20, mu_nom * 1.3, 10.0] + [1e30] * (deg + 1)

            try:
                popt, perr, _, chi2, ndf = _root_curve_fit(
                    trial_func, cxw, cyw, p0_t, lo_b, hi_b)
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
    return (float(np.std([r[0] for r in results])),
            float(np.std([r[1] for r in results])),
            float(np.std([r[2] for r in results]) * 100))


# ─────────────────────────────────────────────────────────────────────────────
# Result builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(mu, sigma, mu_err, sig_err, dn, chi2, ndf,
                  sys_mu, sys_sig, sys_res, method, E_src, popt):
    denom = mu - dn
    if denom <= 0:
        return None
    res     = sigma / denom
    res_err = res * np.sqrt((sig_err / sigma) ** 2 + (mu_err / denom) ** 2) if sigma > 0 else 0.0
    LY      = denom / E_src
    return dict(
        method=method,
        peak=float(mu), sigma=float(sigma),
        peak_error=float(np.sqrt(mu_err ** 2 + sys_mu ** 2)),
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error=float(np.sqrt(sig_err ** 2 + sys_sig ** 2)),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(res),
        resolution_error=float(np.sqrt(res_err ** 2 + (sys_res / 100) ** 2)),
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100),
        resolution_pct=float(res * 100),
        resolution_pct_err=float(np.sqrt(res_err ** 2 + (sys_res / 100) ** 2) * 100),
        resolution_pct_err_stat=float(res_err * 100),
        resolution_pct_err_sys=float(sys_res),
        LY_PE_per_MeV=float(LY), LY_PE_per_MeV_err=float(mu_err / E_src),
        dark_noise_PE=float(dn),
        chi2=float(chi2), ndf=int(ndf),
        chi2_ndf=float(chi2 / ndf) if ndf > 0 else -1,
        status=True,
        _fit_params=popt.tolist() if hasattr(popt, 'tolist') else list(popt),
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1: Gaussian + pol3  (ROOT TF1)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_gauss_pol3(cx, cy, dn, mu_init, amp_init,
                    E_src=E_CS137_MEV, printf=print):
    sig_init = mu_init * 0.04
    fmin = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fmax = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask = (cx >= fmin) & (cx <= fmax)
    if mask.sum() < 8:
        printf(f"  gauss+pol3: too narrow ({mask.sum()} bins)")
        return None
    cxf, cyf = cx[mask], cy[mask]

    p0 = [amp_init, mu_init, sig_init, float(cyf.min()) + 1, 0.0, 0.0, 0.0]
    lo = [0.0, mu_init * 0.7, sig_init * 0.1, -1e30, -1e30, -1e30, -1e30]
    hi = [amp_init * 20, mu_init * 1.3, sig_init * 5.0, 1e30, 1e30, 1e30, 1e30]

    try:
        popt, perr, _, chi2, ndf = _root_curve_fit(_gauss_pol3, cxf, cyf, p0, lo, hi)
    except Exception as exc:
        printf(f"  gauss+pol3 ROOT fit failed: {exc}")
        return None

    mu    = float(popt[1])
    sigma = abs(float(popt[2]))
    if sigma <= 0 or (mu - dn) <= 0:
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dn)
    return _build_result(mu, sigma, float(perr[1]), float(perr[2]), dn,
                         chi2, ndf, sys_mu, sys_sig, sys_res,
                         'gauss+pol3', E_src, popt)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: Physics model  (ROOT TF1)
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
    sk   = sigma_init / np.sqrt(max(mu_init, 1.0))

    if model_version == 1:
        p0 = [amp, mu_init, sk,
              amp * 0.3, amp * 0.05, mu_init * 0.1,
              float(cyf.min()) + 1, 0.0, 0.0]
        lo = [0.0, mu_init * 0.8, 0.01,
              0.0, 0.0, 1.0,
              0.0, -1e30, -1e30]
        hi = [amp * 20, mu_init * 1.2, 10.0,
              amp * 5, amp * 3, mu_init * 0.4,
              cyf.max() * 5, 1e30, 1e30]
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
              amp * 5, 0.08,
              amp * 2, 0.15,
              amp * 3, mu_init * 0.35,
              cyf.max() * 5, 1e30]
        model_fn = _model_cs137_v2
        mname    = 'physics_v2'

    try:
        popt, perr, _, chi2, ndf = _root_curve_fit(model_fn, cxf, cyf, p0, lo, hi)
    except Exception as exc:
        printf(f"  {mname}: ROOT fit failed: {exc}")
        return None

    mu      = float(popt[1])
    sk_fit  = float(popt[2])
    sigma   = sk_fit * np.sqrt(max(mu, 1.0))
    mu_err  = float(perr[1])
    sig_err = float(np.sqrt((perr[2] * np.sqrt(mu)) ** 2
                            + (sk_fit / (2 * np.sqrt(max(mu, 1.0))) * mu_err) ** 2))

    if sigma <= 0 or (mu - dn) <= 0:
        return None

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dn)
    result = _build_result(mu, sigma, mu_err, sig_err, dn,
                           chi2, ndf, sys_mu, sys_sig, sys_res,
                           mname, E_src, popt)

    if result and model_version == 2:
        result['compton_edge_smearing'] = float(popt[4])
        result['backscatter_fraction']  = float(popt[5] / popt[0]) if popt[0] > 0 else 0.0

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def fit_from_arrays(cx, cy, dn, source_energy_mev=E_CS137_MEV,
                    method_name="PE", printf=print, model_version=2):
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
