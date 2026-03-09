#!/usr/bin/env python3
"""
fit_peaks_ge68.py  —  Two-stage peak fitting for Ge-68 spectra

Stage 1: Gaussian + pol3  (robust, data-driven initialization)
Stage 2: Full physics model — user selects v1 or v2:
    v1: Compton + secondary γ + 14C pileup + pol3  (original)
    v2: Single-escape + Compton + 14C pileup + pol3  (improved for TAO 1.8m)

Both stage-1 and stage-2 results are returned.

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

from scipy.optimize import curve_fit


# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
E_GE68_MEV    = 1.022
E_SEC_MEV     = 1.08       # secondary γ background line (v1 only)
M_E_MEV       = 0.511      # electron mass
DN_PE_DEFAULT = 134.0

FIT_WINDOW_SIGMA_LO = 7.0
FIT_WINDOW_SIGMA_HI = 6.0

# Compton edge for 511 keV gammas
_ALPHA_511      = M_E_MEV / M_E_MEV     # = 1.0
E_COMPTON_511   = M_E_MEV * 2 * _ALPHA_511 / (1 + 2 * _ALPHA_511)  # ≈ 0.340 MeV


# ─────────────────────────────────────────────────────────────────────────────
# Model components (shared)
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    """Simple Gaussian + cubic polynomial (Stage 1)."""
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)

def _c14_pileup(x, E0):
    """14C pile-up: linear ramp from 0 to E0, zero above."""
    return np.where(x < E0, x / E0, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# V1 Compton shape (original empirical)
# ─────────────────────────────────────────────────────────────────────────────

def _compton_shape_v1(x, mu):
    """Empirical Compton continuum for 511 keV γ pair. Zero above μ."""
    x_norm = x / mu
    shape  = (1.0 - np.exp(-x_norm / 0.6)) * np.exp(-x_norm / 0.4)
    shape  = np.where(x_norm < 1.0, shape, 0.0)
    return np.clip(shape, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# V2 Compton shape (improved: smeared Klein-Nishina-like edge)
# ─────────────────────────────────────────────────────────────────────────────

def _compton_shape_v2(x, mu, sigma_c_rel=0.04):
    """
    Smeared Compton continuum for 511 keV gammas.
    Flat below Compton edge, Fermi-Dirac falloff at edge.
    
    Compton edge for 511 keV: E_c = 340 keV → 0.333·μ (in PE units, since
    μ corresponds to 1.022 MeV → E_c/1.022 · μ ≈ 0.333·μ)
    """
    mu_c = mu * (E_COMPTON_511 / E_GE68_MEV)    # Compton edge in PE
    sigma_c = sigma_c_rel * mu_c                   # edge smearing
    # Fermi-Dirac shape: flat below edge, drops above
    plateau = 1.0 / (1.0 + np.exp((x - mu_c) / max(sigma_c, 1.0)))
    # Additional rise shape at low energy (photoelectron statistics)
    rise = np.where(x > 0, 1.0 - np.exp(-x / (0.15 * mu)), 0.0)
    return np.clip(plateau * rise, 0, None)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V1 (original): Compton + secondary γ + C14 + pol3
# 12 free parameters
# ─────────────────────────────────────────────────────────────────────────────

def _model_ge68_v1(x, N_gaus, mu, sigma_k,
                   N_compton, N_sec, sigma_sec_rel,
                   N_c14, E0_c14, p0, p1, p2, p3):
    sigma     = sigma_k * np.sqrt(mu)
    mu_sec    = mu * (E_SEC_MEV / E_GE68_MEV)
    sigma_sec = sigma_sec_rel * np.sqrt(mu_sec)
    peak       = _gauss(x, N_gaus, mu, sigma)
    compton    = N_compton * _compton_shape_v1(x, mu)
    sec_gamma  = _gauss(x, N_sec, mu_sec, sigma_sec)
    pileup     = N_c14 * _c14_pileup(x, E0_c14)
    bkg        = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3
    return peak + compton + sec_gamma + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# MODEL V2 (improved): full-energy + single-escape + Compton + C14 + pol3
# 13 free parameters
#
# Physics: Ge-68 → e+ annihilation → two 511 keV gammas (back-to-back).
# In TAO's 1.8m sphere, mean free path for 511 keV γ in LAB-LS is ~12 cm,
# so a significant fraction of events have one γ escaping:
#   - Full-energy peak: both γ fully absorbed → E_vis = 1.022 MeV
#   - Single-escape peak: one γ escapes → E_vis ≈ 0.511 MeV
#   - Compton continuum: partial energy deposits
#   - C14 pileup: low-energy accidental coincidences
# ─────────────────────────────────────────────────────────────────────────────

def _model_ge68_v2(x, N_full, mu, sigma_k,
                   N_1esc, mu_esc_ratio,
                   N_compton, sigma_c_rel,
                   N_c14, E0_c14,
                   p0, p1, p2, p3):
    """
    Improved Ge-68 model with explicit single-escape peak.

    Parameters
    ----------
    N_full      : full-energy peak amplitude
    mu          : full-energy peak mean [PE] (corresponds to 1.022 MeV)
    sigma_k     : relative resolution: σ = σ_k · √μ
    N_1esc      : single-escape peak amplitude
    mu_esc_ratio: escape peak position as fraction of μ (expect ~0.50)
    N_compton   : Compton continuum normalisation
    sigma_c_rel : Compton edge smearing (relative to edge position)
    N_c14       : 14C pileup normalisation
    E0_c14      : 14C pileup end-point [PE]
    p0..p3      : polynomial background
    """
    sigma_full = sigma_k * np.sqrt(mu)

    # Single-escape peak: one 511 keV γ escapes fully
    mu_esc     = mu * mu_esc_ratio
    sigma_esc  = sigma_k * np.sqrt(mu_esc)  # same σ_k scaling

    peak       = _gauss(x, N_full, mu, sigma_full)
    escape     = _gauss(x, N_1esc, mu_esc, sigma_esc)
    compton    = N_compton * _compton_shape_v2(x, mu, sigma_c_rel)
    pileup     = N_c14 * _c14_pileup(x, E0_c14)
    bkg        = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3

    return peak + escape + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# PEAK FINDER
# ─────────────────────────────────────────────────────────────────────────────

def _find_peak(cx, cy, printf=print):
    """Find peak at max-counts bin, skipping lower 25%."""
    mid = len(cx) // 4
    search_cx, search_cy = cx[mid:], cy[mid:]
    if search_cy.max() < 10:
        search_cx, search_cy = cx, cy
    idx = np.argmax(search_cy)
    mu_init = float(search_cx[idx])
    amp_init = float(search_cy[idx])
    printf(f"  Peak found at {mu_init:.0f} PE  (height {amp_init:.0f} counts)")
    return mu_init, amp_init


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEMATIC STUDY
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
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
            def trial(x, N, mu, sk, *bp):
                sig = sk * np.sqrt(mu)
                peak = N * np.exp(-0.5 * ((x - mu) / sig)**2)
                poly = sum(bp[i] * x**i for i in range(len(bp)))
                return peak + poly

            bkg_p = [cy_w.mean()] + [0.0] * deg
            p0 = [cy_w.max(), mu_nom, sigma_nom / np.sqrt(mu_nom)] + bkg_p
            try:
                popt, _ = curve_fit(trial, cx_w, cy_w, p0=p0, maxfev=5000,
                                     bounds=([0, mu_nom*0.7, 0.01] + [-np.inf]*(deg+1),
                                             [np.inf, mu_nom*1.3, 10.0] + [np.inf]*(deg+1)),
                                     sigma=np.sqrt(np.where(cy_w > 1, cy_w, 1)),
                                     absolute_sigma=True)
                mu_i = popt[1]
                sk_i = popt[2]
                sig_i = sk_i * np.sqrt(mu_i)
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
# RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe, chi2, ndf,
                  sys_mu, sys_sig, sys_res, method, source_energy_mev, popt):
    denom = mu - dark_noise_pe
    if denom <= 0:
        return None
    resolution = sigma / denom
    res_err = resolution * np.sqrt((sig_err/sigma)**2 + (mu_err/denom)**2) if sigma > 0 else 0
    LY = denom / source_energy_mev
    LY_err = mu_err / source_energy_mev

    return dict(
        method=method,
        peak=float(mu), sigma=float(sigma),
        peak_error=float(np.sqrt(mu_err**2 + sys_mu**2)),
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error=float(np.sqrt(sig_err**2 + sys_sig**2)),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(resolution),
        resolution_error=float(np.sqrt(res_err**2 + (sys_res/100)**2)),
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res/100),
        resolution_pct=float(resolution * 100),
        resolution_pct_err=float(np.sqrt(res_err**2 + (sys_res/100)**2) * 100),
        resolution_pct_err_stat=float(res_err * 100),
        resolution_pct_err_sys=float(sys_res),
        LY_PE_per_MeV=float(LY), LY_PE_per_MeV_err=float(LY_err),
        dark_noise_PE=float(dark_noise_pe),
        chi2=float(chi2), ndf=int(ndf),
        chi2_ndf=float(chi2/ndf) if ndf > 0 else -1,
        status=True,
        _fit_params=popt.tolist() if hasattr(popt, 'tolist') else list(popt),
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1: Gaussian + pol3
# ─────────────────────────────────────────────────────────────────────────────

def _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                    source_energy_mev=E_GE68_MEV, printf=print):
    sig_init = mu_init * 0.03
    fit_min = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fit_max = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 8:
        printf(f"  gauss+pol3: window too narrow ({mask.sum()} bins)")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]
    p0_init = [amp_init, mu_init, sig_init, float(cy_fit.min())+1, 0, 0, 0]
    lo = [0, mu_init*0.7, sig_init*0.1, -np.inf, -np.inf, -np.inf, -np.inf]
    hi = [amp_init*20, mu_init*1.3, sig_init*5, np.inf, np.inf, np.inf, np.inf]

    try:
        popt, pcov = curve_fit(_gauss_pol3, cx_fit, cy_fit, p0=p0_init,
                                bounds=(lo, hi), maxfev=15000,
                                sigma=np.sqrt(np.where(cy_fit > 1, cy_fit, 1)),
                                absolute_sigma=True)
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        printf(f"  gauss+pol3: curve_fit failed: {exc}")
        return None

    mu_fit, sigma_fit = float(popt[1]), abs(float(popt[2]))
    mu_err, sig_err = float(perr[1]), float(perr[2])

    if sigma_fit <= 0 or (mu_fit - dark_noise_pe) <= 0:
        printf(f"  gauss+pol3: unphysical (μ={mu_fit:.0f}, σ={sigma_fit:.0f})")
        return None

    y_pred = _gauss_pol3(cx_fit, *popt)
    chi2 = float(np.sum((cy_fit - y_pred)**2 / np.where(cy_fit > 1, cy_fit, 1)))
    ndf = max(len(cx_fit) - len(popt), 1)

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu_fit, sigma_fit, dark_noise_pe)

    return _build_result(mu_fit, sigma_fit, mu_err, sig_err, dark_noise_pe,
                         chi2, ndf, sys_mu, sys_sig, sys_res, 'gauss+pol3',
                         source_energy_mev, popt)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: Physics model (v1 or v2)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_physics(cx, cy, dark_noise_pe, simple_result,
                 source_energy_mev=E_GE68_MEV, model_version=2, printf=print):
    """
    Fit full physics model seeded from stage-1 result.
    
    model_version=1: original (Compton + sec γ + C14 + pol3)
    model_version=2: improved (full-energy + escape + Compton + C14 + pol3)
    """
    if simple_result is None:
        return None

    mu_init = simple_result['peak']
    sigma_init = simple_result['sigma']
    sig_init = mu_init * 0.03

    fit_min = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fit_max = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 15:
        printf(f"  physics v{model_version}: window too narrow ({mask.sum()} bins)")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]
    amp_init = float(cy_fit.max())
    sigma_k_init = sigma_init / np.sqrt(mu_init) if mu_init > 0 else 2.0

    if model_version == 1:
        # ── V1: original 12-parameter model ──
        p0 = [amp_init, mu_init, sigma_k_init,
              amp_init*0.3, amp_init*0.05, 0.06,
              amp_init*0.1, mu_init*0.15,
              cy_fit.min()+1, 0, 0, 0]
        lo = [0, mu_init*0.8, 0.01,
              0, 0, 0.01,
              0, 1,
              0, -np.inf, -np.inf, -np.inf]
        hi = [amp_init*20, mu_init*1.2, 10.0,
              amp_init*5, amp_init*2, 0.15,
              amp_init*5, mu_init*0.5,
              cy_fit.max()*5, np.inf, np.inf, np.inf]
        model_fn = _model_ge68_v1
        method_name = 'physics_v1'

    else:
        # ── V2: improved 13-parameter model with escape peak ──
        p0 = [amp_init, mu_init, sigma_k_init,           # full peak
              amp_init*0.15, 0.50,                         # escape peak (15% of full, at μ/2)
              amp_init*0.2, 0.04,                          # Compton + edge smearing
              amp_init*0.05, mu_init*0.15,                 # C14
              cy_fit.min()+1, 0, 0, 0]                     # pol3

        lo = [0, mu_init*0.8, 0.01,                        # full peak
              0, 0.40,                                      # escape: fraction [0.40, 0.60]
              0, 0.01,                                      # Compton
              0, 1,                                         # C14
              0, -np.inf, -np.inf, -np.inf]                 # pol3

        hi = [amp_init*20, mu_init*1.2, 10.0,             # full peak
              amp_init*5, 0.60,                             # escape: fraction (physics: ~0.50 ± 10%)
              amp_init*5, 0.10,                             # Compton smearing up to 10%
              amp_init*5, mu_init*0.35,                     # C14 endpoint
              cy_fit.max()*5, np.inf, np.inf, np.inf]       # pol3
        model_fn = _model_ge68_v2
        method_name = 'physics_v2'

    try:
        popt, pcov = curve_fit(model_fn, cx_fit, cy_fit, p0=p0,
                                bounds=(lo, hi), maxfev=20000,
                                sigma=np.sqrt(np.where(cy_fit > 1, cy_fit, 1)),
                                absolute_sigma=True)
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        printf(f"  {method_name}: curve_fit failed: {exc}")
        return None

    mu = popt[1]
    sigma_k = popt[2]
    sigma = sigma_k * np.sqrt(mu)
    mu_err = perr[1]
    sig_err = np.sqrt((perr[2] * np.sqrt(mu))**2 + (sigma_k / (2*np.sqrt(mu)) * mu_err)**2)

    if sigma <= 0 or (mu - dark_noise_pe) <= 0:
        printf(f"  {method_name}: unphysical (μ={mu:.0f}, σ={sigma:.0f})")
        return None

    y_pred = model_fn(cx_fit, *popt)
    chi2 = float(np.sum((cy_fit - y_pred)**2 / np.where(cy_fit > 1, cy_fit, 1)))
    ndf = max(len(cx_fit) - len(popt), 1)

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dark_noise_pe)

    result = _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe,
                           chi2, ndf, sys_mu, sys_sig, sys_res,
                           method_name, source_energy_mev, popt)

    if result is not None and model_version == 2:
        # Add escape fraction info
        result['escape_fraction'] = float(popt[3] / popt[0]) if popt[0] > 0 else 0
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
    """
    printf(f"\n  ── Ge-68 fit ({method_name}) ──")

    mu_init, amp_init = _find_peak(cx, cy, printf)
    if mu_init <= 0 or amp_init < 10:
        printf(f"  No peak found")
        return None, None

    # Stage 1: Gaussian + pol3
    simple = _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                             source_energy_mev, printf)
    if simple:
        printf(f"  gauss+pol3: μ={simple['peak']:.1f}, σ={simple['sigma']:.1f}, "
               f"res={simple['resolution_pct']:.2f}%, χ²/ndf={simple['chi2_ndf']:.2f}")

    # Stage 2: physics model
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
                    h = f[key]
                    vals, edges = h.to_numpy()
                    cx = 0.5 * (edges[:-1] + edges[1:])
                    cy = vals
                    break
            else:
                raise RuntimeError(f"No PE histogram found in {root_path}")
            # Try to get dark noise
            dn = DN_PE_DEFAULT
            try:
                dn_obj = f['dark_noise_pe']
                dn = float(str(dn_obj))
            except Exception:
                pass
        return cx, cy, dn
    elif HAS_ROOT:
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
        n = h.GetNbinsX()
        cx = np.array([h.GetBinCenter(b) for b in range(1, n+1)])
        cy = np.array([h.GetBinContent(b) for b in range(1, n+1)])
        dn = DN_PE_DEFAULT
        dn_obj = f.Get("dark_noise_pe")
        if dn_obj:
            try:
                dn = float(dn_obj.GetTitle())
            except Exception:
                pass
        f.Close()
        return cx, cy, dn
    else:
        raise RuntimeError("Neither uproot nor ROOT available")


def fit_ge68(root_path, model_version=2, printf=print):
    """Standalone entry: load + fit."""
    cx, cy, dn = load_spectrum(root_path)
    return fit_from_arrays(cx, cy, dn, model_version=model_version, printf=printf)


def main():
    parser = argparse.ArgumentParser(description='Ge-68 peak fitting')
    parser.add_argument('input', help='ROOT file or directory')
    parser.add_argument('--output-dir', default='fits')
    parser.add_argument('--model-version', type=int, default=2, choices=[1, 2],
                        help='Physics model version (1=original, 2=with escape peak)')
    parser.add_argument('--scan', action='store_true', help='Process all ROOT files in directory')
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
