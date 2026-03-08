#!/usr/bin/env python3
"""
fit_peaks_cs137.py  —  Physics-model peak fitting for Cs-137 spectra

Fits the TAO Cs-137 (661.7 keV gamma) PE-sum spectrum with:

  f(PE) = N_gaus · G(PE; μ, σ=σ_k·√μ)          # photo-peak
        + N_compton · ComptonEdge(PE; μ)          # Compton continuum + edge
        + N_c14 · Ramp(PE; E0_c14)               # 14C pile-up (low energy)
        + p0 + p1·PE + p2·PE²                    # smooth polynomial bkg

Compton edge position:  E_c = E_γ · 2α/(1+2α),  α = E_γ/(m_e c²)
For Cs-137: E_c/E_γ ≈ 0.720 → E_c ≈ 477 keV → ~2050 PE at 4300 PE/MeV

Output identical in structure to fit_peaks_ge68.py so that ly_extractor.py
can consume both without branching.

Usage:
  python fit_peaks_cs137.py spectrum_RUN1344_pos05.root --output-dir fits/
  python fit_peaks_cs137.py /path/to/cls_merged/ --output-dir fits/ --scan

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
    import ROOT
    ROOT.gROOT.SetBatch(True)
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False

# ─────────────────────────────────────────────────────────────────────────────
# Physical parameters
# ─────────────────────────────────────────────────────────────────────────────
E_CS137_MEV   = 0.6617   # Cs-137 gamma energy [MeV]
M_E_MEV       = 0.511    # electron rest mass [MeV]
_ALPHA        = E_CS137_MEV / M_E_MEV                  # ≈ 1.295
E_COMPTON_MEV = E_CS137_MEV * 2 * _ALPHA / (1 + 2 * _ALPHA)  # ≈ 0.4774 MeV
LY_NOMINAL    = 4300.0   # PE/MeV
DN_PE_DEFAULT = 90.0     # dark-noise PE for a typical Cs-137 run (shorter events)

FIT_WINDOW_SIGMA_LO = 6.0
FIT_WINDOW_SIGMA_HI = 5.0


# ─────────────────────────────────────────────────────────────────────────────
# Model components
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


def _compton_cs137(x, mu_peak):
    """
    Approximate Compton continuum for Cs-137 661.7 keV gamma.

    Shape:
      - Nearly flat for  x < E_c
      - Falls sharply at the Compton edge  E_c ≈ 0.72 · E_γ  →  0.72 · μ_peak
      - Zero above E_c (photon continues with reduced energy)

    We model it as a smooth step using an error-function edge.
    """
    mu_c    = mu_peak * (E_COMPTON_MEV / E_CS137_MEV)   # Compton edge in PE
    sigma_c = mu_c * 0.03                                # edge smearing ~3%
    # flat plateau below edge, falling above
    plateau = 0.5 * (1.0 - np.tanh((x - mu_c) / sigma_c))
    return np.clip(plateau, 0, None)


def _c14_pileup(x, E0):
    return np.where((x > 0) & (x < E0), x / E0, 0.0)


def _model_cs137(x, N_gaus, mu, sigma_k,
                 N_compton, N_c14, E0_c14,
                 p0, p1, p2):
    """
    Full Cs-137 spectral model in PE units.
    """
    sigma   = sigma_k * np.sqrt(mu)
    peak    = _gauss(x, N_gaus, mu, sigma)
    compton = N_compton * _compton_cs137(x, mu)
    pileup  = N_c14 * _c14_pileup(x, E0_c14)
    bkg     = p0 + p1 * x + p2 * x ** 2
    return peak + compton + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# Systematic study
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    range_configs = [(5, 4), (6, 5), (8, 6)]
    poly_degrees  = [1, 2, 3]
    results       = []

    from scipy.optimize import curve_fit

    for (lo, hi) in range_configs:
        fit_min = mu_nom - lo * sigma_nom
        fit_max = mu_nom + hi * sigma_nom
        mask    = (cx >= fit_min) & (cx <= fit_max)
        if mask.sum() < 10:
            continue
        cx_w, cy_w = cx[mask], cy[mask]

        for deg in poly_degrees:
            def trial_model(x, N, mu, sk, *bp):
                sig  = sk * np.sqrt(mu)
                peak = N * np.exp(-0.5 * ((x - mu) / sig) ** 2)
                poly = sum(bp[i] * x ** i for i in range(len(bp)))
                return peak + poly

            bkg_p = [cy_w.mean()] + [0.0] * deg
            p0    = [cy_w.max(), mu_nom, sigma_nom / np.sqrt(mu_nom)] + bkg_p
            try:
                popt, _ = curve_fit(
                    trial_model, cx_w, cy_w, p0=p0, maxfev=5000,
                    bounds=(
                        [0, mu_nom * 0.7, 0.005] + [-np.inf] * (deg + 1),
                        [np.inf, mu_nom * 1.3, 10.0] + [np.inf] * (deg + 1),
                    ),
                )
                m_fit  = popt[1]
                s_fit  = abs(popt[2]) * np.sqrt(m_fit)
                denom  = m_fit - dark_noise_pe
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
# Histogram reader (shared with fit_peaks_ge68)
# ─────────────────────────────────────────────────────────────────────────────

def load_spectrum(root_path):
    cx = cy = None
    dark_noise_pe = DN_PE_DEFAULT

    if HAS_UPROOT:
        with uproot.open(root_path) as f:
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
# Main fit
# ─────────────────────────────────────────────────────────────────────────────

def fit_cs137(root_path, verbose=False):
    """
    Fit the Cs-137 spectrum.  Returns dict identical in structure to
    fit_ge68() output, or None on failure.
    """
    try:
        cx, cy, dark_noise_pe = load_spectrum(root_path)
    except RuntimeError as e:
        print(f"  ERROR: {e}")
        return None

    mu_nom     = LY_NOMINAL * E_CS137_MEV + dark_noise_pe
    win_search = (cx > mu_nom * 0.5) & (cx < mu_nom * 1.5)
    if win_search.sum() < 5 or cy[win_search].sum() < 10:
        print(f"  ERROR: peak search region empty in {os.path.basename(root_path)}")
        return None

    mu_init  = cx[win_search][np.argmax(cy[win_search])]
    sig_init = mu_init * 0.040   # Cs-137 ~4% resolution

    fit_min = mu_init - FIT_WINDOW_SIGMA_LO * sig_init
    fit_max = mu_init + FIT_WINDOW_SIGMA_HI * sig_init
    mask    = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 15:
        print(f"  ERROR: fit window too narrow in {os.path.basename(root_path)}")
        return None

    cx_fit = cx[mask]
    cy_fit = cy[mask]

    from scipy.optimize import curve_fit

    def wrapped(x, N_gaus, mu, sigma_k, N_compton, N_c14, E0_c14, p0, p1, p2):
        return _model_cs137(x, N_gaus, mu, sigma_k, N_compton, N_c14, E0_c14, p0, p1, p2)

    amp_init = cy_fit.max()
    p0_init  = [
        amp_init,
        mu_init,
        sig_init / np.sqrt(mu_init),
        amp_init * 0.5,
        amp_init * 0.05,
        mu_init * 0.10,
        cy_fit.min() + 1,
        0.0, 0.0,
    ]
    # sigma_k is defined as sigma = sigma_k * sqrt(mu).
    # For Cs-137 at TAO (mu ~ 2850 PE, 4 % resolution): sigma_k ~ 0.04*sqrt(mu) ~ 2.1.
    # The old upper bound of 0.20 caused every fit to fail. Fixed to 10.0.
    lo = [0, mu_init*0.7, 0.005,  0, 0, 1,      0, -np.inf, -np.inf]
    hi = [amp_init*20, mu_init*1.3, 10.0, amp_init*10, amp_init*3, mu_init*0.5,
          cy_fit.max()*5, np.inf, np.inf]

    try:
        popt, pcov = curve_fit(
            wrapped, cx_fit, cy_fit,
            p0=p0_init, bounds=(lo, hi), maxfev=20000,
            sigma=np.sqrt(np.where(cy_fit > 1, cy_fit, 1)),
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

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu, sigma, dark_noise_pe)

    mu_err_tot  = float(np.sqrt(mu_err ** 2  + sys_mu ** 2))
    sig_err_tot = float(np.sqrt(sig_err ** 2 + sys_sig ** 2))
    res_err_tot = float(np.sqrt(resolution_err ** 2 + (sys_res / 100.0) ** 2))

    y_pred = wrapped(cx_fit, *popt)
    chi2   = float(np.sum((cy_fit - y_pred) ** 2
                          / np.where(cy_fit > 1, cy_fit, 1)))
    ndf    = mask.sum() - len(p0_init)

    LY     = denom / E_CS137_MEV
    LY_err = mu_err_tot / E_CS137_MEV

    if verbose:
        print(f"  Cs-137 fit: μ={mu:.1f}±{mu_err_tot:.1f} PE  "
              f"σ={sigma:.1f}±{sig_err_tot:.1f} PE  "
              f"res={100*resolution:.3f}%±{100*res_err_tot:.3f}%  "
              f"LY={LY:.0f}±{LY_err:.0f} PE/MeV  "
              f"χ²/ndf={chi2/ndf:.2f}")

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

def plot_cs137_fit(root_path, result, output_path, label=""):
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

    # ── robust window: try ±8σ, fall back to ±40% of μ, then whole histogram ──
    win = (cx > mu - 8 * sigma) & (cx < mu + 8 * sigma)
    if win.sum() < 2:
        win = (cx > mu * 0.60) & (cx < mu * 1.40)
    if win.sum() < 2:
        win = np.ones(len(cx), dtype=bool)
    if win.sum() < 2:
        print(f"  WARN: cannot plot {os.path.basename(output_path)} – empty histogram")
        plt.close(fig)
        return

    bw = float(cx[1] - cx[0]) if len(cx) > 1 else 1.0
    ax.step(cx[win], cy[win], where="mid", color="k", lw=1, label="Data")

    x_fine  = np.linspace(float(cx[win].min()), float(cx[win].max()), 1000)
    y_model = _model_cs137(x_fine, *pars)
    ax.plot(x_fine, y_model, "r-", lw=2, label="Full model (physics)")

    sigma_val = pars[2] * np.sqrt(mu)
    ax.fill_between(x_fine, _gauss(x_fine, pars[0], mu, sigma_val),
                    alpha=0.25, color="steelblue", label="Signal peak")
    ax.fill_between(x_fine, pars[3] * _compton_cs137(x_fine, mu),
                    alpha=0.20, color="green", label="Compton continuum")

    mu_c = mu * (E_COMPTON_MEV / E_CS137_MEV)
    ax.axvline(mu_c, color="green", lw=1, ls="--",
               label=f"Compton edge ≈{mu_c:.0f} PE")
    ax.axvline(dn, color="grey", lw=1, ls="--")

    ax.set_ylabel("Events / bin", fontsize=10)
    ax.set_title(f"Cs-137 physics-model fit   {label}", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.85)
    ax.set_yscale("log")

    # ── custom info box – top-right corner ────────────────────────────────────
    _res_str  = f"{result['resolution_pct']:.2f} ± {result.get('resolution_pct_err', 0):.2f}"
    _mean_str = f"{mu:.1f} ± {result.get('mean_PE_err', 0):.1f}"
    _sig_str  = f"{sigma:.1f} ± {result.get('sigma_PE_err', 0):.1f}"
    _ly_str   = f"{result['LY_PE_per_MeV']:.0f} ± {result.get('LY_PE_per_MeV_err', 0):.0f}"
    info_lines = [
        r"$\bf{Cs\text{-}137\ physics\ model}$",
        f"μ  =  {_mean_str}  PE",
        f"σ  =  {_sig_str}  PE",
        f"Res =  {_res_str}  %",
        f"LY  =  {_ly_str}  PE/MeV",
        f"χ²/ndf = {result['chi2_ndf']:.2f}",
        f"DN  =  {dn:.0f}  PE",
    ]
    ax.text(0.975, 0.975, "\n".join(info_lines),
            transform=ax.transAxes, fontsize=8.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="0.6", alpha=0.92))

    # ── residual panel ────────────────────────────────────────────────────────
    y_data = cy[win]
    y_pred = _model_cs137(cx[win], *pars)
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

def _gauss_pol3_cs(x, N, mu, sigma, p0, p1, p2, p3):
    """Gaussian + cubic polynomial background."""
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)


def fit_cs137_simple(root_path, dark_noise_pe_override=None):
    """
    Fit the Cs-137 PE spectrum with a simple Gaussian + pol3 model.
    Replicates the legacy get_spectrum.py fit for direct comparison.
    Returns a dict with the same key names as fit_cs137(), or None on failure.
    """
    from scipy.optimize import curve_fit

    try:
        cx, cy, dn = load_spectrum(root_path)
    except RuntimeError as e:
        print(f"  ERROR (simple): {e}")
        return None

    dark_noise_pe = dark_noise_pe_override if dark_noise_pe_override is not None else dn

    # ── locate peak ───────────────────────────────────────────────────────────
    mu_nom     = LY_NOMINAL * E_CS137_MEV + dark_noise_pe
    win_search = (cx > mu_nom * 0.40) & (cx < mu_nom * 1.60)
    if win_search.sum() < 5 or cy[win_search].sum() < 10:
        win_search = np.ones(len(cx), dtype=bool)
    if win_search.sum() < 5:
        return None

    mu_init  = float(cx[win_search][np.argmax(cy[win_search])])
    sig_init = mu_init * 0.05

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
            _gauss_pol3_cs, cx_fit, cy_fit,
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
    LY           = denom / E_CS137_MEV
    res_err      = np.sqrt((sig_err / sigma_fit) ** 2 + (mu_err / denom) ** 2) * resolution
    LY_err       = mu_err / E_CS137_MEV

    y_pred = _gauss_pol3_cs(cx_fit, *popt)
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


def plot_cs137_simple(root_path, result, output_path, label=""):
    """Plot Cs-137 spectrum with Gauss+pol3 fit (legacy method)."""
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

    x_fine  = np.linspace(float(cx[win].min()), float(cx[win].max()), 1000)
    y_full  = _gauss_pol3_cs(x_fine, *pars)
    y_gauss = pars[0] * np.exp(-0.5 * ((x_fine - mu) / sigma) ** 2)
    y_bkg   = pars[3] + pars[4]*x_fine + pars[5]*x_fine**2 + pars[6]*x_fine**3

    ax.plot(x_fine, y_full,  "r-",  lw=2,   label="Gauss + pol3")
    ax.plot(x_fine, y_bkg,   "m--", lw=1.2, label="pol3 background", alpha=0.7)
    ax.fill_between(x_fine, y_gauss, alpha=0.25, color="steelblue", label="Gaussian")
    ax.axvline(result["dark_noise_PE"], color="grey", lw=1, ls="--")

    ax.set_ylabel("Events / bin", fontsize=10)
    ax.set_title(f"Cs-137 Gauss+pol3 fit   {label}", fontsize=11)
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
    y_pred = _gauss_pol3_cs(cx[win], *pars)
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
        description="Physics-model Cs-137 spectrum fitting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input",
                        help="Spectrum ROOT file or directory of merged spectra")
    parser.add_argument("--output-dir", default="cs137_fits",
                        help="Directory for PNG and JSON output (default: cs137_fits)")
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
        result = fit_cs137(fpath, verbose=args.verbose)
        if result is None:
            print("  FAILED")
            continue

        result_save = {k: v for k, v in result.items() if k != "_fit_params"}
        json_path = os.path.join(args.output_dir, f"{stem}_cs137_fit.json")
        with open(json_path, "w") as jf:
            json.dump(result_save, jf, indent=2)

        png_path = os.path.join(args.output_dir, f"{stem}_cs137_fit.png")
        plot_cs137_fit(fpath, result, png_path, label=stem)

        all_results[stem] = result_save

    summary_path = os.path.join(args.output_dir, "cs137_fit_summary.json")
    with open(summary_path, "w") as jf:
        json.dump(all_results, jf, indent=2)
    print(f"\nSummary: {summary_path}")
    print(f"Done — {len(all_results)}/{len(files)} fits succeeded.")


if __name__ == "__main__":
    main()
