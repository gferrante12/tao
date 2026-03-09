#!/usr/bin/env python3
"""
fit_peaks_cs137.py  —  Two-stage peak fitting for Cs-137 spectra

Stage 1: Gaussian + pol3  (robust, data-driven)
Stage 2: Physics model — v1 or v2:
    v1: Compton edge (tanh) + 14C pileup + pol2  (original, 9 params)
    v2: Compton edge (FD) + backscatter peak + 14C + pol2  (improved, 11 params)

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

from scipy.optimize import curve_fit


# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
E_CS137_MEV   = 0.6617
M_E_MEV       = 0.511
_ALPHA        = E_CS137_MEV / M_E_MEV                         # ≈ 1.295
E_COMPTON_MEV = E_CS137_MEV * 2*_ALPHA / (1 + 2*_ALPHA)       # ≈ 0.4774 MeV
E_BSCAT_MEV   = E_CS137_MEV - E_COMPTON_MEV                   # ≈ 0.184 MeV
RATIO_COMPTON = E_COMPTON_MEV / E_CS137_MEV                   # ≈ 0.722
RATIO_BSCAT   = E_BSCAT_MEV  / E_CS137_MEV                   # ≈ 0.278
DN_PE_DEFAULT = 90.0

FIT_WINDOW_SIGMA_LO = 6.0
FIT_WINDOW_SIGMA_HI = 5.0


# ─────────────────────────────────────────────────────────────────────────────
# Shared components
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma)**2) / (sigma * np.sqrt(2*np.pi))

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    return (N * np.exp(-0.5 * ((x - mu) / sigma)**2)
            + p0 + p1*x + p2*x**2 + p3*x**3)

def _c14_pileup(x, E0):
    return np.where((x > 0) & (x < E0), x / E0, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# V1 Compton edge shape (tanh, original)
# ─────────────────────────────────────────────────────────────────────────────

def _compton_cs137_v1(x, mu_peak):
    mu_c    = mu_peak * RATIO_COMPTON
    sigma_c = mu_c * 0.03
    plateau = 0.5 * (1.0 - np.tanh((x - mu_c) / max(sigma_c, 1.0)))
    return np.clip(plateau, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# V2 Compton edge shape (Fermi-Dirac, with free smearing)
# ─────────────────────────────────────────────────────────────────────────────

def _compton_cs137_v2(x, mu_peak, sigma_c_rel):
    """
    Fermi-Dirac edge at 0.722·μ with free smearing parameter.
    More physical than tanh: FD is the standard detector physics shape
    for a smeared Compton edge.
    """
    mu_c = mu_peak * RATIO_COMPTON
    sigma_c = mu_c * max(sigma_c_rel, 0.005)
    # Fermi-Dirac shape
    arg = (x - mu_c) / sigma_c
    arg = np.clip(arg, -500, 500)
    plateau = 1.0 / (1.0 + np.exp(arg))
    return np.clip(plateau, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V1 (original, 9 params)
# ─────────────────────────────────────────────────────────────────────────────

def _model_cs137_v1(x, N_gaus, mu, sigma_k,
                    N_compton, N_c14, E0_c14, p0, p1, p2):
    sigma   = sigma_k * np.sqrt(mu)
    peak    = _gauss(x, N_gaus, mu, sigma)
    compton = N_compton * _compton_cs137_v1(x, mu)
    pileup  = N_c14 * _c14_pileup(x, E0_c14)
    bkg     = p0 + p1*x + p2*x**2
    return peak + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V2 (improved, 11 params: + backscatter peak + free Compton smearing)
#
# Physics: 662 keV γ Compton-scatters ~180° in surrounding copper shell,
# re-enters LS with ~184 keV. Creates broad backscatter peak at 0.278·μ.
# Significant in TAO because of copper thermal shield close to LS volume.
# ─────────────────────────────────────────────────────────────────────────────

def _model_cs137_v2(x, N_peak, mu, sigma_k,
                    N_compton, sigma_c_rel,
                    N_bscat, sigma_bs_rel,
                    N_c14, E0_c14,
                    p0, p1):
    """
    Improved Cs-137 model with backscatter peak and free Compton smearing.

    Parameters
    ----------
    N_peak      : photopeak amplitude
    mu          : photopeak mean [PE] (662 keV)
    sigma_k     : relative resolution σ = σ_k·√μ
    N_compton   : Compton continuum normalisation
    sigma_c_rel : Compton edge smearing (relative, typ. 0.02–0.06)
    N_bscat     : backscatter peak amplitude
    sigma_bs_rel: backscatter peak relative width
    N_c14       : 14C pileup normalisation
    E0_c14      : 14C end-point [PE]
    p0, p1      : linear background (pol1 — enough with explicit components)
    """
    sigma   = sigma_k * np.sqrt(mu)

    # Backscatter peak at ~0.278·μ
    mu_bs    = mu * RATIO_BSCAT
    sigma_bs = sigma_bs_rel * np.sqrt(mu_bs)

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
    idx = np.argmax(scy)
    mu_init = float(scx[idx])
    amp_init = float(scy[idx])
    printf(f"  Peak found at {mu_init:.0f} PE  (height {amp_init:.0f})")
    return mu_init, amp_init


# ─────────────────────────────────────────────────────────────────────────────
# Systematic study
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    configs = [(5, 4), (6, 5), (8, 6)]
    poly_degs = [1, 2, 3]
    results = []

    for (lo, hi) in configs:
        fmin = mu_nom - lo * sigma_nom
        fmax = mu_nom + hi * sigma_nom
        mask = (cx >= fmin) & (cx <= fmax)
        if mask.sum() < 10:
            continue
        cxw, cyw = cx[mask], cy[mask]

        for deg in poly_degs:
            def trial(x, N, mu, sk, *bp):
                sig = sk * np.sqrt(mu)
                return N * np.exp(-0.5*((x-mu)/sig)**2) + sum(bp[i]*x**i for i in range(len(bp)))

            bkg_p = [cyw.mean()] + [0.0]*deg
            p0 = [cyw.max(), mu_nom, sigma_nom/np.sqrt(mu_nom)] + bkg_p
            try:
                popt, _ = curve_fit(trial, cxw, cyw, p0=p0, maxfev=5000,
                                     bounds=([0, mu_nom*0.7, 0.01]+[-np.inf]*(deg+1),
                                             [np.inf, mu_nom*1.3, 10.0]+[np.inf]*(deg+1)),
                                     sigma=np.sqrt(np.where(cyw > 1, cyw, 1)),
                                     absolute_sigma=True)
                mu_i, sk_i = popt[1], popt[2]
                sig_i = sk_i * np.sqrt(mu_i)
                denom = mu_i - dark_noise_pe
                if denom > 0 and sig_i > 0:
                    results.append((mu_i, sig_i, sig_i/denom))
            except Exception:
                continue

    if len(results) < 2:
        return 0, 0, 0
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
    res = sigma / denom
    res_err = res * np.sqrt((sig_err/sigma)**2 + (mu_err/denom)**2) if sigma > 0 else 0
    LY = denom / E_src
    return dict(
        method=method,
        peak=float(mu), sigma=float(sigma),
        peak_error=float(np.sqrt(mu_err**2 + sys_mu**2)),
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error=float(np.sqrt(sig_err**2 + sys_sig**2)),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(res),
        resolution_error=float(np.sqrt(res_err**2 + (sys_res/100)**2)),
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res/100),
        resolution_pct=float(res*100),
        resolution_pct_err=float(np.sqrt(res_err**2 + (sys_res/100)**2)*100),
        resolution_pct_err_stat=float(res_err*100),
        resolution_pct_err_sys=float(sys_res),
        LY_PE_per_MeV=float(LY), LY_PE_per_MeV_err=float(mu_err/E_src),
        dark_noise_PE=float(dn),
        chi2=float(chi2), ndf=int(ndf),
        chi2_ndf=float(chi2/ndf) if ndf > 0 else -1,
        status=True,
        _fit_params=popt.tolist() if hasattr(popt, 'tolist') else list(popt),
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1
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

    p0 = [amp_init, mu_init, sig_init, float(cyf.min())+1, 0, 0, 0]
    lo = [0, mu_init*0.7, sig_init*0.1, -np.inf, -np.inf, -np.inf, -np.inf]
    hi = [amp_init*20, mu_init*1.3, sig_init*5, np.inf, np.inf, np.inf, np.inf]

    try:
        popt, pcov = curve_fit(_gauss_pol3, cxf, cyf, p0=p0, bounds=(lo, hi),
                                maxfev=15000,
                                sigma=np.sqrt(np.where(cyf > 1, cyf, 1)),
                                absolute_sigma=True)
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        printf(f"  gauss+pol3 failed: {exc}")
        return None

    mu, sigma = float(popt[1]), abs(float(popt[2]))
    if sigma <= 0 or (mu - dn) <= 0:
        return None

    y_pred = _gauss_pol3(cxf, *popt)
    chi2 = float(np.sum((cyf - y_pred)**2 / np.where(cyf > 1, cyf, 1)))
    ndf = max(len(cxf) - len(popt), 1)

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dn)
    return _build_result(mu, sigma, float(perr[1]), float(perr[2]), dn,
                         chi2, ndf, sys_mu, sys_sig, sys_res,
                         'gauss+pol3', E_src, popt)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2
# ─────────────────────────────────────────────────────────────────────────────

def _fit_physics(cx, cy, dn, simple, E_src=E_CS137_MEV,
                 model_version=2, printf=print):
    if simple is None:
        return None

    mu_init = simple['peak']
    sigma_init = simple['sigma']
    sig_init = mu_init * 0.04

    fmin = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fmax = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask = (cx >= fmin) & (cx <= fmax)
    if mask.sum() < 15:
        printf(f"  physics v{model_version}: too narrow ({mask.sum()} bins)")
        return None

    cxf, cyf = cx[mask], cy[mask]
    amp = float(cyf.max())
    sk = sigma_init / np.sqrt(mu_init) if mu_init > 0 else 2.0

    if model_version == 1:
        p0 = [amp, mu_init, sk,
              amp*0.3, amp*0.05, mu_init*0.1,
              cyf.min()+1, 0, 0]
        lo = [0, mu_init*0.8, 0.01,
              0, 0, 1,
              0, -np.inf, -np.inf]
        hi = [amp*20, mu_init*1.2, 10.0,
              amp*5, amp*3, mu_init*0.4,
              cyf.max()*5, np.inf, np.inf]
        model_fn = _model_cs137_v1
        mname = 'physics_v1'
    else:
        # V2: 11 params with backscatter + free Compton smearing
        p0 = [amp, mu_init, sk,             # photopeak
              amp*0.3, 0.03,                 # Compton + smearing (3%)
              amp*0.05, 0.06,                # backscatter + width
              amp*0.03, mu_init*0.1,         # C14
              cyf.min()+1, 0]                # pol1

        lo = [0, mu_init*0.8, 0.01,         # photopeak
              0, 0.01,                        # Compton smearing [1%, 8%]
              0, 0.02,                        # backscatter width [2%, 15%]
              0, 1,                            # C14
              0, -np.inf]                      # pol1

        hi = [amp*20, mu_init*1.2, 10.0,    # photopeak
              amp*5, 0.08,                    # Compton
              amp*2, 0.15,                    # backscatter (broad)
              amp*3, mu_init*0.35,            # C14 endpoint
              cyf.max()*5, np.inf]            # pol1
        model_fn = _model_cs137_v2
        mname = 'physics_v2'

    try:
        popt, pcov = curve_fit(model_fn, cxf, cyf, p0=p0, bounds=(lo, hi),
                                maxfev=20000,
                                sigma=np.sqrt(np.where(cyf > 1, cyf, 1)),
                                absolute_sigma=True)
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        printf(f"  {mname}: curve_fit failed: {exc}")
        return None

    mu = popt[1]
    sk_fit = popt[2]
    sigma = sk_fit * np.sqrt(mu)
    mu_err = perr[1]
    sig_err = np.sqrt((perr[2]*np.sqrt(mu))**2 + (sk_fit/(2*np.sqrt(mu))*mu_err)**2)

    if sigma <= 0 or (mu - dn) <= 0:
        return None

    y_pred = model_fn(cxf, *popt)
    chi2 = float(np.sum((cyf - y_pred)**2 / np.where(cyf > 1, cyf, 1)))
    ndf = max(len(cxf) - len(popt), 1)

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dn)
    result = _build_result(mu, sigma, mu_err, sig_err, dn,
                           chi2, ndf, sys_mu, sys_sig, sys_res,
                           mname, E_src, popt)

    if result and model_version == 2:
        result['compton_edge_smearing'] = float(popt[4])
        result['backscatter_fraction'] = float(popt[5] / popt[0]) if popt[0] > 0 else 0

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
        printf(f"  {physics['method']}: μ={physics['peak']:.1f}, res={physics['resolution_pct']:.2f}%, "
               f"χ²/ndf={physics['chi2_ndf']:.2f}")

    return simple, physics


def main():
    parser = argparse.ArgumentParser(description='Cs-137 peak fitting')
    parser.add_argument('input', help='ROOT file or directory')
    parser.add_argument('--output-dir', default='fits')
    parser.add_argument('--model-version', type=int, default=2, choices=[1, 2])
    parser.add_argument('--scan', action='store_true')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    # (load_spectrum and fit_cs137 logic similar to Ge-68 — omitted for brevity)
    print("Use fit_from_arrays() via spectrum_utils.fit_source() for integrated pipeline.")


if __name__ == "__main__":
    main()
