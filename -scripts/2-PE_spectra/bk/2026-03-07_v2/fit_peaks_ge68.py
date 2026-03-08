#!/usr/bin/env python3
"""
fit_peaks_ge68.py  —  Physics-model peak fitting for Ge-68 spectra

Fits the TAO Ge-68 (two 511 keV positron-annihilation gammas, E_vis = 1.022 MeV)
PE-sum spectrum with a multi-component model:

  f(PE) = N_gaus · G(PE; μ, σ=σ_k·√μ)          # signal peak
        + N_compton · Compton(PE; μ)             # Compton continuum
        + N_sec · G(PE; μ_sec, σ_sec)            # 1.08 MeV secondary γ bkg
        + N_c14 · Ramp(PE; E0_c14)               # 14C pileup
        + p0 + p1·PE + p2·PE² + p3·PE³           # smooth polynomial bkg

The energy scale is set so that μ (peak mean in PE) corresponds to 1.022 MeV,
giving the preliminary light yield as LY = (μ − DN) / 1.022 [PE/MeV].

Produces:
  • PNG fit plot
  • JSON result with  mean_PE, sigma_PE, resolution_%, LY_PE_per_MeV,
    stat/sys errors, chi2/ndf

Usage (single file):
  python fit_peaks_ge68.py spectrum.root --output-dir fits/

Usage (directory of merged spectra):
  python fit_peaks_ge68.py /path/to/merged_dir/ --output-dir fits/ --scan

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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import uproot
    HAS_UPROOT = True
except ImportError:
    HAS_UPROOT = False

try:
    from iminuit import Minuit
    from iminuit.cost import UnbinnedNLL, ExtendedUnbinnedNLL
    HAS_IMINUIT = True
except ImportError:
    HAS_IMINUIT = False

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False

# ─────────────────────────────────────────────────────────────────────────────
# Physical constants / detector defaults
# ─────────────────────────────────────────────────────────────────────────────
E_GE68_MEV    = 1.022    # total visible energy in MeV (two 511 keV)
E_SEC_MEV     = 1.08     # secondary gamma background (e.g. 208Tl → 2.6 MeV, but
                          # in calibration runs a 1.08 MeV line can appear)
LY_NOMINAL    = 4300.0   # PE/MeV (TAO design)
DN_PE_DEFAULT = 134.0    # expected dark-noise PE for a typical Ge-68 run

# Fit window: ±N sigma around peak estimate
FIT_WINDOW_SIGMA_LO = 7.0
FIT_WINDOW_SIGMA_HI = 6.0


# ─────────────────────────────────────────────────────────────────────────────
# Physics model components (in PE units)
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


def _compton_shape(x, mu):
    """
    Approximate Compton continuum for a pair of 511 keV gammas.
    Falls from ~0 at 0 PE to edge just below the photo-peak.
    Uses a simple (1 - exp) × exp shape (empirical).
    """
    x_norm = x / mu
    shape  = (1.0 - np.exp(-x_norm / 0.6)) * np.exp(-x_norm / 0.4)
    shape  = np.where(x_norm < 1.0, shape, 0.0)
    return np.clip(shape, 0, None)


def _c14_pileup(x, E0):
    """14C pile-up: linear ramp from 0 to E0, zero above."""
    return np.where(x < E0, x / E0, 0.0)


def _model_ge68(x, N_gaus, mu, sigma_k,
                N_compton, N_sec, sigma_sec_rel,
                N_c14, E0_c14,
                p0, p1, p2, p3):
    """
    Full Ge-68 spectral model in PE units.

    Parameters
    ----------
    x          : array of PE bin centres
    N_gaus     : signal peak amplitude  [counts / bin]
    mu         : peak mean [PE]
    sigma_k    : relative resolution  σ = σ_k · √μ
    N_compton  : Compton continuum normalisation
    N_sec      : secondary γ amplitude
    sigma_sec_rel : secondary γ relative resolution
    N_c14      : 14C pileup normalisation
    E0_c14     : 14C pileup end-point [PE]
    p0..p3     : smooth background polynomial
    """
    sigma     = sigma_k * np.sqrt(mu)
    mu_sec    = mu * (E_SEC_MEV / E_GE68_MEV)
    sigma_sec = sigma_sec_rel * np.sqrt(mu_sec)

    peak       = _gauss(x, N_gaus, mu, sigma)
    compton    = N_compton * _compton_shape(x, mu)
    sec_gamma  = _gauss(x, N_sec, mu_sec, sigma_sec)
    pileup     = N_c14 * _c14_pileup(x, E0_c14)
    bkg        = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3

    return peak + compton + sec_gamma + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# Systematic study: vary fit window + background degree
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe,
                      n_configs=9):
    """
    Run n_configs = 3 window widths × 3 poly degrees fits.
    Returns std of {mean, sigma, resolution} as systematic errors.
    """
    range_configs = [(6, 5), (7, 6), (9, 7)]
    poly_degrees  = [1, 2, 3]
    results       = []

    for (lo, hi) in range_configs:
        fit_min = mu_nom - lo * sigma_nom
        fit_max = mu_nom + hi * sigma_nom
        mask    = (cx >= fit_min) & (cx <= fit_max)
        if mask.sum() < 10:
            continue
        cx_w, cy_w = cx[mask], cy[mask]

        for deg in poly_degrees:
            # Build simple gauss + poly model for this systematic trial
            def trial_model(x, N, mu, sk, *bkg_pars):
                sig  = sk * np.sqrt(mu)
                peak = N * np.exp(-0.5 * ((x - mu) / sig) ** 2)
                poly = sum(bkg_pars[i] * x ** i for i in range(len(bkg_pars)))
                return peak + poly

            bkg_p0 = [cy_w.mean()] + [0.0] * deg
            p0_all = [cy_w.max(), mu_nom, sigma_nom / np.sqrt(mu_nom)] + bkg_p0

            try:
                from scipy.optimize import curve_fit
                popt, pcov = curve_fit(
                    trial_model, cx_w, cy_w, p0=p0_all, maxfev=5000,
                    bounds=(
                        [0, mu_nom * 0.7, 0.01] + [-np.inf] * (deg + 1),
                        [np.inf, mu_nom * 1.3, 10.0] + [np.inf] * (deg + 1),
                    ),
                )
                m_fit = popt[1]
                s_fit = abs(popt[2]) * np.sqrt(m_fit)
                denom = m_fit - dark_noise_pe
                if denom > 0 and s_fit > 0:
                    results.append({
                        "mean": m_fit,
                        "sigma": s_fit,
                        "resolution": (s_fit / denom) * 100.0,
                    })
            except Exception:
                pass

    if len(results) < 2:
        return 0.0, 0.0, 0.0

    means = np.array([r["mean"]       for r in results])
    sigs  = np.array([r["sigma"]      for r in results])
    ress  = np.array([r["resolution"] for r in results])
    return float(np.std(means)), float(np.std(sigs)), float(np.std(ress))


# ─────────────────────────────────────────────────────────────────────────────
# Histogram reader
# ─────────────────────────────────────────────────────────────────────────────

def load_spectrum(root_path):
    """
    Load PE-sum histogram from a spectrum ROOT file.
    Returns (centers, counts, dark_noise_pe) or raises RuntimeError.
    """
    cx = cy = None
    dark_noise_pe = DN_PE_DEFAULT

    if HAS_UPROOT:
        with uproot.open(root_path) as f:
            # read dark noise
            try:
                dark_noise_pe = float(f["dark_noise_pe"].title)
            except Exception:
                pass
            for name in ("h_PEdiscrete", "h_PEcontin"):
                try:
                    h  = f[name]
                    cy = h.values()
                    ed = h.axis().edges()
                    cx = 0.5 * (ed[:-1] + ed[1:])
                    if cy.sum() > 0:
                        break
                except Exception:
                    pass

    if cx is None and HAS_ROOT:
        tf = ROOT.TFile.Open(root_path, "READ")
        if tf and not tf.IsZombie():
            dn = tf.Get("dark_noise_pe")
            if dn:
                try:
                    dark_noise_pe = float(dn.GetTitle())
                except Exception:
                    pass
            for name in ("h_PEdiscrete", "h_PEcontin"):
                h = tf.Get(name)
                if h and h.GetEntries() > 0:
                    n  = h.GetNbinsX()
                    ed = np.array([h.GetBinLowEdge(b) for b in range(1, n + 2)])
                    cx = 0.5 * (ed[:-1] + ed[1:])
                    cy = np.array([h.GetBinContent(b) for b in range(1, n + 1)])
                    break
            tf.Close()

    if cx is None:
        raise RuntimeError(f"Cannot read PE histogram from {root_path}")

    return cx, cy, dark_noise_pe


# ─────────────────────────────────────────────────────────────────────────────
# Main fit routine
# ─────────────────────────────────────────────────────────────────────────────

def fit_ge68(root_path, verbose=False):
    """
    Fit the Ge-68 spectrum in root_path.

    Returns a dict with keys:
        mean_PE, mean_PE_err, mean_PE_err_stat, mean_PE_err_sys
        sigma_PE, sigma_PE_err, sigma_PE_err_stat, sigma_PE_err_sys
        resolution_pct, resolution_pct_err, resolution_pct_err_stat, resolution_pct_err_sys
        LY_PE_per_MeV, LY_PE_per_MeV_err
        dark_noise_PE
        chi2, ndf, chi2_ndf
    or None on failure.
    """
    try:
        cx, cy, dark_noise_pe = load_spectrum(root_path)
    except RuntimeError as e:
        print(f"  ERROR: {e}")
        return None

    # Locate peak
    mu_nom     = LY_NOMINAL * E_GE68_MEV + dark_noise_pe
    win_search = (cx > mu_nom * 0.5) & (cx < mu_nom * 1.5)
    if win_search.sum() < 5 or cy[win_search].sum() < 10:
        print(f"  ERROR: peak search region empty in {os.path.basename(root_path)}")
        return None

    mu_init  = cx[win_search][np.argmax(cy[win_search])]
    sig_init = mu_init * 0.030    # 3% initial guess

    # Fit window
    fit_min = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fit_max = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask    = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 15:
        print(f"  ERROR: fit window too narrow in {os.path.basename(root_path)}")
        return None

    cx_fit = cx[mask]
    cy_fit = cy[mask]
    bw     = cx[1] - cx[0] if len(cx) > 1 else 1.0

    # scipy least-squares (fast, robust)
    from scipy.optimize import curve_fit

    def wrapped(x, N_gaus, mu, sigma_k,
                N_compton, N_sec, sigma_sec_rel,
                N_c14, E0_c14, p0, p1, p2, p3):
        return _model_ge68(x, N_gaus, mu, sigma_k,
                           N_compton, N_sec, sigma_sec_rel,
                           N_c14, E0_c14, p0, p1, p2, p3)

    amp_init = cy_fit.max()
    p0_init  = [
        amp_init,           # N_gaus
        mu_init,            # mu
        sig_init / np.sqrt(mu_init),  # sigma_k
        amp_init * 0.3,     # N_compton
        amp_init * 0.05,    # N_sec
        0.06,               # sigma_sec_rel
        amp_init * 0.1,     # N_c14
        mu_init * 0.15,     # E0_c14
        cy_fit.min() + 1,   # p0
        0.0, 0.0, 0.0,      # p1..p3
    ]

    # sigma_k is defined as sigma = sigma_k * sqrt(mu).
    # For TAO (LY ~ 4300 PE/MeV, 3 % resolution): sigma_k ~ 0.03*sqrt(mu) ~ 2.0.
    # The old upper bound of 0.20 was 10× too tight and caused every fit to fail
    # with "Initial guess is outside of provided bounds". Fixed to 10.0.
    lo_bounds = [0, mu_init * 0.8, 0.01,
                 0, 0, 0.01,
                 0, 1,
                 0, -np.inf, -np.inf, -np.inf]
    hi_bounds = [amp_init * 20, mu_init * 1.2, 10.0,
                 amp_init * 5, amp_init * 2, 0.15,
                 amp_init * 5, mu_init * 0.5,
                 cy_fit.max() * 5, np.inf, np.inf, np.inf]

    try:
        popt, pcov = curve_fit(
            wrapped, cx_fit, cy_fit,
            p0=p0_init, bounds=(lo_bounds, hi_bounds),
            maxfev=20000, sigma=np.sqrt(np.where(cy_fit > 1, cy_fit, 1)),
            absolute_sigma=True,
        )
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        print(f"  WARN: curve_fit failed for {os.path.basename(root_path)}: {exc}")
        return None

    mu       = popt[1]
    sigma_k  = popt[2]
    sigma    = sigma_k * np.sqrt(mu)
    mu_err   = perr[1]
    sig_err  = np.sqrt((perr[2] * np.sqrt(mu)) ** 2
                        + (sigma_k / (2 * np.sqrt(mu)) * mu_err) ** 2)

    denom = mu - dark_noise_pe
    if denom <= 0 or sigma <= 0:
        return None

    resolution     = sigma / denom
    resolution_err = resolution * np.sqrt(
        (sig_err / sigma) ** 2 + (mu_err / denom) ** 2
    )

    # Systematic study
    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dark_noise_pe)

    mu_err_tot  = float(np.sqrt(mu_err ** 2  + sys_mu ** 2))
    sig_err_tot = float(np.sqrt(sig_err ** 2 + sys_sig ** 2))
    res_err_tot = float(np.sqrt(resolution_err ** 2 + (sys_res / 100.0) ** 2))

    # chi2
    y_pred = wrapped(cx_fit, *popt)
    chi2   = float(np.sum((cy_fit - y_pred) ** 2
                          / np.where(cy_fit > 1, cy_fit, 1)))
    ndf    = mask.sum() - len(p0_init)

    LY     = denom / E_GE68_MEV
    LY_err = mu_err_tot / E_GE68_MEV

    if verbose:
        print(f"  Ge-68 fit: μ={mu:.1f}±{mu_err_tot:.1f} PE  "
              f"σ={sigma:.1f}±{sig_err_tot:.1f} PE  "
              f"res={100*resolution:.3f}%±{100*res_err_tot:.3f}%  "
              f"LY={LY:.0f}±{LY_err:.0f} PE/MeV  "
              f"χ²/ndf={chi2/ndf:.2f} ({chi2:.1f}/{ndf})")

    return dict(
        mean_PE                  = float(mu),
        mean_PE_err              = mu_err_tot,
        mean_PE_err_stat         = float(mu_err),
        mean_PE_err_sys          = float(sys_mu),
        sigma_PE                 = float(sigma),
        sigma_PE_err             = sig_err_tot,
        sigma_PE_err_stat        = float(sig_err),
        sigma_PE_err_sys         = float(sys_sig),
        resolution_pct           = float(resolution * 100.0),
        resolution_pct_err       = float(res_err_tot * 100.0),
        resolution_pct_err_stat  = float(resolution_err * 100.0),
        resolution_pct_err_sys   = float(sys_res),
        LY_PE_per_MeV            = float(LY),
        LY_PE_per_MeV_err        = float(LY_err),
        dark_noise_PE            = float(dark_noise_pe),
        chi2                     = chi2,
        ndf                      = int(ndf),
        chi2_ndf                 = float(chi2 / ndf) if ndf > 0 else -1.0,
        _fit_params              = popt.tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Plot
# ─────────────────────────────────────────────────────────────────────────────

def plot_ge68_fit(root_path, result, output_path, label=""):
    try:
        cx, cy, dn = load_spectrum(root_path)
    except RuntimeError:
        return

    mu     = result["mean_PE"]
    sigma  = result["sigma_PE"]
    pars   = result["_fit_params"]

    fig, axes = plt.subplots(2, 1, figsize=(10, 7),
                             gridspec_kw={"height_ratios": [3, 1]},
                             sharex=True)
    ax, ax_res = axes

    # ── robust window: try ±8σ, fall back to ±40% of μ, then whole histogram ──
    win = (cx > mu - 8 * sigma) & (cx < mu + 8 * sigma)
    if win.sum() < 2:
        win = (cx > mu * 0.60) & (cx < mu * 1.40)
    if win.sum() < 2:
        win = np.ones(len(cx), dtype=bool)   # full range fallback
    if win.sum() < 2:
        print(f"  WARN: cannot plot {os.path.basename(output_path)} – empty histogram")
        plt.close(fig)
        return

    bw = float(cx[1] - cx[0]) if len(cx) > 1 else 1.0
    ax.step(cx[win], cy[win], where="mid", color="k", lw=1, label="Data")

    x_fine  = np.linspace(float(cx[win].min()), float(cx[win].max()), 1000)
    y_model = _model_ge68(x_fine, *pars)
    ax.plot(x_fine, y_model, "r-", lw=2, label="Full model (physics)")

    sigma_k   = pars[2]
    sigma_val = sigma_k * np.sqrt(mu)
    ax.fill_between(x_fine, _gauss(x_fine, pars[0], mu, sigma_val),
                    alpha=0.25, color="steelblue", label="Signal peak")
    ax.fill_between(x_fine, pars[3] * _compton_shape(x_fine, mu),
                    alpha=0.20, color="green", label="Compton continuum")

    ax.axvline(result["dark_noise_PE"], color="grey", lw=1, ls="--")

    ax.set_ylabel("Events / bin", fontsize=10)
    ax.set_title(f"Ge-68 physics-model fit   {label}", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.85)
    ax.set_yscale("log")

    # ── custom info box – top-right corner, away from histogram peak ──────────
    _res_str  = f"{result['resolution_pct']:.2f} ± {result.get('resolution_pct_err', 0):.2f}"
    _mean_str = f"{mu:.1f} ± {result.get('mean_PE_err', 0):.1f}"
    _sig_str  = f"{sigma:.1f} ± {result.get('sigma_PE_err', 0):.1f}"
    _ly_str   = f"{result['LY_PE_per_MeV']:.0f} ± {result.get('LY_PE_per_MeV_err', 0):.0f}"
    info_lines = [
        r"$\bf{Ge\text{-}68\ physics\ model}$",
        f"μ  =  {_mean_str}  PE",
        f"σ  =  {_sig_str}  PE",
        f"Res =  {_res_str}  %",
        f"LY  =  {_ly_str}  PE/MeV",
        f"χ²/ndf = {result['chi2_ndf']:.2f}",
        f"DN  =  {result['dark_noise_PE']:.0f}  PE",
    ]
    ax.text(0.975, 0.975, "\n".join(info_lines),
            transform=ax.transAxes, fontsize=8.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="0.6", alpha=0.92))

    # ── residual panel ────────────────────────────────────────────────────────
    y_data = cy[win]
    y_pred = _model_ge68(cx[win], *pars)
    pull   = (y_data - y_pred) / np.sqrt(np.where(y_data > 1, y_data, 1))
    ax_res.bar(cx[win], pull, width=bw, color="steelblue", alpha=0.6, edgecolor="none")
    ax_res.axhline(0, color="k", lw=0.8)
    ax_res.set_ylabel("Pull", fontsize=9)
    ax_res.set_xlabel("Total PE / event", fontsize=10)
    ax_res.set_ylim(-5, 5)

    fig.tight_layout(h_pad=0.3)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Simple Gauss + pol3 fit  (legacy / comparison method)
# ─────────────────────────────────────────────────────────────────────────────

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    """Gaussian + cubic polynomial background."""
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)


def fit_ge68_simple(root_path, dark_noise_pe_override=None):
    """
    Fit the Ge-68 PE spectrum with a simple Gaussian + pol3 model.
    This replicates the fit method used in get_spectrum.py / acu_scan_compare.py
    for direct comparison with the physics-model fit.

    Returns a dict with the same key names as fit_ge68(), or None on failure.
    """
    from scipy.optimize import curve_fit

    try:
        cx, cy, dn = load_spectrum(root_path)
    except RuntimeError as e:
        print(f"  ERROR (simple): {e}")
        return None

    dark_noise_pe = dark_noise_pe_override if dark_noise_pe_override is not None else dn

    # ── locate peak ───────────────────────────────────────────────────────────
    mu_nom     = LY_NOMINAL * E_GE68_MEV + dark_noise_pe
    win_search = (cx > mu_nom * 0.40) & (cx < mu_nom * 1.60)
    if win_search.sum() < 5 or cy[win_search].sum() < 10:
        win_search = np.ones(len(cx), dtype=bool)
    if win_search.sum() < 5:
        return None

    mu_init  = float(cx[win_search][np.argmax(cy[win_search])])
    sig_init = mu_init * 0.04

    # ── fit window: −5σ to +4σ (matching get_spectrum systematic_fit_study) ──
    fit_min = mu_init - 5.0 * sig_init
    fit_max = mu_init + 4.0 * sig_init
    mask    = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 8:
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]
    amp_init = float(cy_fit.max())

    p0_init = [amp_init, mu_init, sig_init,
               float(cy_fit.min()) + 1.0, 0.0, 0.0, 0.0]

    lo = [0,        mu_init * 0.70, sig_init * 0.20,
          -np.inf, -np.inf, -np.inf, -np.inf]
    hi = [amp_init * 20, mu_init * 1.30, sig_init * 3.0,
          np.inf, np.inf, np.inf, np.inf]

    try:
        popt, pcov = curve_fit(
            _gauss_pol3, cx_fit, cy_fit,
            p0=p0_init, bounds=(lo, hi), maxfev=15000,
            sigma=np.sqrt(np.where(cy_fit > 1, cy_fit, 1)),
            absolute_sigma=True,
        )
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        print(f"  WARN (simple): curve_fit failed: {exc}")
        return None

    mu_fit    = float(popt[1])
    sigma_fit = abs(float(popt[2]))
    mu_err    = float(perr[1])
    sig_err   = float(perr[2])

    denom = mu_fit - dark_noise_pe
    if denom <= 0:
        return None

    resolution   = sigma_fit / denom
    LY           = denom / E_GE68_MEV
    res_err      = np.sqrt((sig_err / sigma_fit) ** 2 + (mu_err / denom) ** 2) * resolution
    LY_err       = mu_err / E_GE68_MEV

    y_pred = _gauss_pol3(cx_fit, *popt)
    chi2   = float(np.sum(((cy_fit - y_pred) ** 2) / np.where(cy_fit > 1, cy_fit, 1)))
    ndf    = max(len(cx_fit) - len(popt), 1)

    return dict(
        method                  = "gauss+pol3",
        mean_PE                 = mu_fit,
        mean_PE_err             = mu_err,
        mean_PE_err_stat        = mu_err,
        mean_PE_err_sys         = 0.0,
        sigma_PE                = sigma_fit,
        sigma_PE_err            = sig_err,
        sigma_PE_err_stat       = sig_err,
        sigma_PE_err_sys        = 0.0,
        resolution_pct          = float(resolution * 100.0),
        resolution_pct_err      = float(res_err * 100.0),
        resolution_pct_err_stat = float(res_err * 100.0),
        resolution_pct_err_sys  = 0.0,
        LY_PE_per_MeV           = float(LY),
        LY_PE_per_MeV_err       = float(LY_err),
        dark_noise_PE           = float(dark_noise_pe),
        chi2                    = chi2,
        ndf                     = ndf,
        chi2_ndf                = chi2 / ndf,
        _fit_params             = popt.tolist(),
    )


def plot_ge68_simple(root_path, result, output_path, label=""):
    """Plot Ge-68 spectrum with Gauss+pol3 fit (legacy method)."""
    try:
        cx, cy, dn = load_spectrum(root_path)
    except RuntimeError:
        return

    mu    = result["mean_PE"]
    sigma = result["sigma_PE"]
    pars  = result["_fit_params"]

    fig, axes = plt.subplots(2, 1, figsize=(10, 7),
                             gridspec_kw={"height_ratios": [3, 1]},
                             sharex=True)
    ax, ax_res = axes

    win = (cx > mu - 8 * sigma) & (cx < mu + 8 * sigma)
    if win.sum() < 2:
        win = (cx > mu * 0.60) & (cx < mu * 1.40)
    if win.sum() < 2:
        win = np.ones(len(cx), dtype=bool)
    if win.sum() < 2:
        plt.close(fig)
        return

    bw = float(cx[1] - cx[0]) if len(cx) > 1 else 1.0
    ax.step(cx[win], cy[win], where="mid", color="k", lw=1, label="Data")

    x_fine   = np.linspace(float(cx[win].min()), float(cx[win].max()), 1000)
    y_full   = _gauss_pol3(x_fine, *pars)
    y_gauss  = pars[0] * np.exp(-0.5 * ((x_fine - mu) / sigma) ** 2)
    y_bkg    = pars[3] + pars[4]*x_fine + pars[5]*x_fine**2 + pars[6]*x_fine**3

    ax.plot(x_fine, y_full,  "r-", lw=2,  label="Gauss + pol3")
    ax.plot(x_fine, y_bkg,   "m--", lw=1.2, label="pol3 background", alpha=0.7)
    ax.fill_between(x_fine, y_gauss, alpha=0.25, color="steelblue", label="Gaussian")
    ax.axvline(result["dark_noise_PE"], color="grey", lw=1, ls="--")

    ax.set_ylabel("Events / bin", fontsize=10)
    ax.set_title(f"Ge-68 Gauss+pol3 fit   {label}", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.85)
    ax.set_yscale("log")

    _res_str  = f"{result['resolution_pct']:.2f} ± {result.get('resolution_pct_err', 0):.2f}"
    _mean_str = f"{mu:.1f} ± {result.get('mean_PE_err', 0):.1f}"
    _sig_str  = f"{sigma:.1f} ± {result.get('sigma_PE_err', 0):.1f}"
    _ly_str   = f"{result['LY_PE_per_MeV']:.0f} ± {result.get('LY_PE_per_MeV_err', 0):.0f}"
    info_lines = [
        r"$\bf{Gauss+pol3\ (legacy)}$",
        f"μ  =  {_mean_str}  PE",
        f"σ  =  {_sig_str}  PE",
        f"Res =  {_res_str}  %",
        f"LY  =  {_ly_str}  PE/MeV",
        f"χ²/ndf = {result['chi2_ndf']:.2f}",
        f"DN  =  {result['dark_noise_PE']:.0f}  PE",
    ]
    ax.text(0.975, 0.975, "\n".join(info_lines),
            transform=ax.transAxes, fontsize=8.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="0.6", alpha=0.92))

    y_data = cy[win]
    y_pred = _gauss_pol3(cx[win], *pars)
    pull   = (y_data - y_pred) / np.sqrt(np.where(y_data > 1, y_data, 1))
    ax_res.bar(cx[win], pull, width=bw, color="orange", alpha=0.6, edgecolor="none")
    ax_res.axhline(0, color="k", lw=0.8)
    ax_res.set_ylabel("Pull", fontsize=9)
    ax_res.set_xlabel("Total PE / event", fontsize=10)
    ax_res.set_ylim(-5, 5)

    fig.tight_layout(h_pad=0.3)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Physics-model Ge-68 spectrum fitting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input",
                        help="Spectrum ROOT file or directory of merged spectra")
    parser.add_argument("--output-dir", default="ge68_fits",
                        help="Directory for PNG and JSON output (default: ge68_fits)")
    parser.add_argument("--scan", action="store_true",
                        help="Process all *.root files in the input directory")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.scan or os.path.isdir(args.input):
        files = sorted(glob.glob(os.path.join(args.input, "*.root")))
    else:
        files = [args.input]

    if not files:
        sys.exit(f"ERROR: no ROOT files found in {args.input}")

    all_results = {}
    for fpath in files:
        stem = os.path.splitext(os.path.basename(fpath))[0]
        print(f"\nFitting {stem} ...")
        result = fit_ge68(fpath, verbose=args.verbose)
        if result is None:
            print(f"  FAILED")
            continue

        # save JSON
        result_save = {k: v for k, v in result.items() if k != "_fit_params"}
        json_path = os.path.join(args.output_dir, f"{stem}_ge68_fit.json")
        with open(json_path, "w") as jf:
            json.dump(result_save, jf, indent=2)

        # save plot
        png_path = os.path.join(args.output_dir, f"{stem}_ge68_fit.png")
        plot_ge68_fit(fpath, result, png_path, label=stem)

        all_results[stem] = result_save

    # combined JSON
    summary_path = os.path.join(args.output_dir, "ge68_fit_summary.json")
    with open(summary_path, "w") as jf:
        json.dump(all_results, jf, indent=2)
    print(f"\nSummary: {summary_path}")
    print(f"Done — {len(all_results)}/{len(files)} fits succeeded.")


if __name__ == "__main__":
    main()
