#!/usr/bin/env python3
"""
fit_peaks_ge68.py  —  Two-stage peak fitting for Ge-68 spectra

Stage 1: Gaussian + pol3  (robust, data-driven initialization)
Stage 2: Full physics model (Compton + secondary γ + 14C pileup + pol3)

Both results are returned so that callers (get_spectrum.py, merge_spectrum.py)
can log and store both in the energy_info.

Entry points:
    fit_from_arrays()   — called by spectrum_utils.fit_source() with numpy arrays
    fit_ge68()          — standalone: reads ROOT file, returns physics-model result
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
E_SEC_MEV     = 1.08       # secondary γ background line
DN_PE_DEFAULT = 134.0


# ─────────────────────────────────────────────────────────────────────────────
# Model components
# ─────────────────────────────────────────────────────────────────────────────

def _gauss(x, N, mu, sigma):
    return N * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    """Simple Gaussian + cubic polynomial."""
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)


def _compton_shape(x, mu):
    """Approximate Compton continuum for 511 keV γ pair."""
    x_norm = x / mu
    shape  = (1.0 - np.exp(-x_norm / 0.6)) * np.exp(-x_norm / 0.4)
    shape  = np.where(x_norm < 1.0, shape, 0.0)
    return np.clip(shape, 0, None)


def _c14_pileup(x, E0):
    return np.where(x < E0, x / E0, 0.0)


def _model_ge68(x, N_gaus, mu, sigma_k,
                N_compton, N_sec, sigma_sec_rel,
                N_c14, E0_c14, p0, p1, p2, p3):
    """Full Ge-68 spectral model."""
    sigma     = sigma_k * np.sqrt(mu)
    mu_sec    = mu * (E_SEC_MEV / E_GE68_MEV)
    sigma_sec = sigma_sec_rel * np.sqrt(mu_sec)
    peak    = _gauss(x, N_gaus, mu, sigma)
    compton = N_compton * _compton_shape(x, mu)
    sec_gam = _gauss(x, N_sec, mu_sec, sigma_sec)
    pileup  = N_c14 * _c14_pileup(x, E0_c14)
    bkg     = p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3
    return peak + compton + sec_gam + pileup + bkg


# ─────────────────────────────────────────────────────────────────────────────
# DATA-DRIVEN PEAK FINDER
# ─────────────────────────────────────────────────────────────────────────────

def _find_peak(cx, cy, printf=print):
    """
    Find peak position using the bin with maximum counts.
    Searches in the upper 75% of the histogram range to skip pedestal/DN.
    """
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
# SYSTEMATIC STUDY (3 windows × 3 poly degrees)
# ─────────────────────────────────────────────────────────────────────────────

def _systematic_study(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """Return (sys_mu, sys_sigma, sys_resolution_pct)."""
    range_configs = [(5, 4), (7, 6), (10, 8)]
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
            def trial(x, N, mu, sig, *bp):
                peak = N * np.exp(-0.5 * ((x - mu) / sig) ** 2)
                poly = sum(bp[i] * x ** i for i in range(len(bp)))
                return peak + poly

            bkg_p = [cy_w.mean()] + [0.0] * deg
            p0 = [cy_w.max(), mu_nom, sigma_nom] + bkg_p
            try:
                popt, _ = curve_fit(
                    trial, cx_w, cy_w, p0=p0, maxfev=5000,
                    bounds=(
                        [0, mu_nom * 0.7, sigma_nom * 0.1] + [-np.inf] * (deg + 1),
                        [np.inf, mu_nom * 1.3, sigma_nom * 5.0] + [np.inf] * (deg + 1),
                    ),
                )
                m, s = popt[1], abs(popt[2])
                d = m - dark_noise_pe
                if d > 0 and s > 0:
                    results.append(dict(mean=m, sigma=s, resolution=(s / d) * 100.0))
            except Exception:
                pass

    if len(results) < 2:
        return 0.0, 0.0, 0.0

    return (float(np.std([r['mean']       for r in results])),
            float(np.std([r['sigma']      for r in results])),
            float(np.std([r['resolution'] for r in results])))


# ─────────────────────────────────────────────────────────────────────────────
# RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(mu, sigma, mu_err, sig_err, dark_noise_pe,
                  chi2, ndf, sys_mu, sys_sig, sys_res_pct, method,
                  fit_params=None, source_energy_mev=E_GE68_MEV):
    """Build a standard result dict from fit parameters."""
    denom = mu - dark_noise_pe
    if denom <= 0:
        denom = mu  # fallback

    resolution = sigma / denom
    res_err = resolution * np.sqrt(
        (sig_err / sigma) ** 2 + (mu_err / denom) ** 2) if sigma > 0 else 0.0

    mu_err_tot  = float(np.sqrt(mu_err ** 2  + sys_mu ** 2))
    sig_err_tot = float(np.sqrt(sig_err ** 2 + sys_sig ** 2))
    res_err_tot = float(np.sqrt(res_err ** 2 + (sys_res_pct / 100.0) ** 2))

    LY = denom / source_energy_mev

    return dict(
        peak=float(mu), sigma=float(sigma),
        peak_error=mu_err_tot, sigma_error=sig_err_tot,
        peak_error_stat=float(mu_err), peak_error_sys=float(sys_mu),
        sigma_error_stat=float(sig_err), sigma_error_sys=float(sys_sig),
        resolution=float(resolution), resolution_error=res_err_tot,
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res_pct / 100.0),
        chi2ndf=float(chi2 / ndf) if ndf > 0 else -1.0,
        chi2=float(chi2), ndf=int(ndf),
        LY_PE_per_MeV=float(LY),
        LY_PE_per_MeV_err=float(mu_err_tot / source_energy_mev),
        dark_noise_PE=float(dark_noise_pe),
        status=True, method=method,
        _fit_params=fit_params,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1: Gaussian + pol3 fit
# ─────────────────────────────────────────────────────────────────────────────

def _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                     source_energy_mev=E_GE68_MEV, printf=print):
    """Gaussian + pol3 fit with data-driven initialization."""
    sig_init = mu_init * 0.03   # 3% resolution seed

    fit_min = mu_init - 7.0 * sig_init
    fit_max = mu_init + 6.0 * sig_init
    mask = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 8:
        printf(f"  gauss+pol3: fit window too narrow ({mask.sum()} bins)")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]

    p0_init = [amp_init, mu_init, sig_init,
               float(cy_fit.min()) + 1.0, 0.0, 0.0, 0.0]
    lo = [0, mu_init * 0.70, sig_init * 0.10,
          -np.inf, -np.inf, -np.inf, -np.inf]
    hi = [amp_init * 20, mu_init * 1.30, sig_init * 5.0,
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
        printf(f"  gauss+pol3: curve_fit failed: {exc}")
        return None

    mu_fit = float(popt[1])
    sigma_fit = abs(float(popt[2]))
    mu_err = float(perr[1])
    sig_err = float(perr[2])

    if sigma_fit <= 0 or (mu_fit - dark_noise_pe) <= 0:
        printf(f"  gauss+pol3: unphysical result (μ={mu_fit:.0f}, σ={sigma_fit:.0f})")
        return None

    y_pred = _gauss_pol3(cx_fit, *popt)
    chi2 = float(np.sum(((cy_fit - y_pred) ** 2) / np.where(cy_fit > 1, cy_fit, 1)))
    ndf = max(len(cx_fit) - len(popt), 1)

    # Systematic study
    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, mu_fit, sigma_fit, dark_noise_pe)

    result = _build_result(mu_fit, sigma_fit, mu_err, sig_err, dark_noise_pe,
                           chi2, ndf, sys_mu, sys_sig, sys_res, 'gauss+pol3',
                           popt.tolist(), source_energy_mev)

    printf(f"  STAGE 1 (gauss+pol3):")
    printf(f"    μ  = {mu_fit:.2f} ± {result['peak_error']:.2f} PE")
    printf(f"    σ  = {sigma_fit:.2f} ± {result['sigma_error']:.2f} PE")
    printf(f"    Res = {result['resolution']*100:.3f} ± {result['resolution_error']*100:.3f} %")
    printf(f"    LY  = {result['LY_PE_per_MeV']:.0f} PE/MeV")
    printf(f"    χ²/ndf = {result['chi2ndf']:.2f}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: Full physics model fit (seeded from Stage 1)
# ─────────────────────────────────────────────────────────────────────────────

def _fit_physics(cx, cy, dark_noise_pe, simple_result,
                  source_energy_mev=E_GE68_MEV, printf=print):
    """Full physics model, seeded from gauss+pol3 result."""
    mu_init = simple_result['peak']
    sigma_init = simple_result['sigma']
    sig_init = mu_init * 0.03

    fit_min = mu_init - 7.0 * sig_init
    fit_max = mu_init + 6.0 * sig_init
    mask = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 15:
        printf(f"  physics: fit window too narrow ({mask.sum()} bins)")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]
    amp_init = float(cy_fit.max())

    def wrapped(x, N_gaus, mu, sigma_k,
                N_compton, N_sec, sigma_sec_rel,
                N_c14, E0_c14, p0, p1, p2, p3):
        return _model_ge68(x, N_gaus, mu, sigma_k,
                           N_compton, N_sec, sigma_sec_rel,
                           N_c14, E0_c14, p0, p1, p2, p3)

    sigma_k_init = sigma_init / np.sqrt(mu_init) if mu_init > 0 else 2.0

    p0_init = [
        amp_init,               # N_gaus
        mu_init,                # mu
        sigma_k_init,           # sigma_k
        amp_init * 0.3,         # N_compton
        amp_init * 0.05,        # N_sec
        0.06,                   # sigma_sec_rel
        amp_init * 0.1,         # N_c14
        mu_init * 0.15,         # E0_c14
        cy_fit.min() + 1,       # p0
        0.0, 0.0, 0.0,          # p1..p3
    ]

    lo = [0, mu_init * 0.8, 0.01,
          0, 0, 0.01,
          0, 1,
          0, -np.inf, -np.inf, -np.inf]
    hi = [amp_init * 20, mu_init * 1.2, 10.0,
          amp_init * 5, amp_init * 2, 0.15,
          amp_init * 5, mu_init * 0.5,
          cy_fit.max() * 5, np.inf, np.inf, np.inf]

    try:
        popt, pcov = curve_fit(
            wrapped, cx_fit, cy_fit,
            p0=p0_init, bounds=(lo, hi), maxfev=20000,
            sigma=np.sqrt(np.where(cy_fit > 1, cy_fit, 1)),
            absolute_sigma=True,
        )
        perr = np.sqrt(np.diag(pcov))
    except Exception as exc:
        printf(f"  physics: curve_fit failed: {exc}")
        return None

    mu       = popt[1]
    sigma_k  = popt[2]
    sigma    = sigma_k * np.sqrt(mu)
    mu_err   = perr[1]
    sig_err  = np.sqrt((perr[2] * np.sqrt(mu)) ** 2
                        + (sigma_k / (2 * np.sqrt(mu)) * mu_err) ** 2)

    if sigma <= 0 or (mu - dark_noise_pe) <= 0:
        printf(f"  physics: unphysical result (μ={mu:.0f}, σ={sigma:.0f})")
        return None

    y_pred = wrapped(cx_fit, *popt)
    chi2 = float(np.sum((cy_fit - y_pred) ** 2
                        / np.where(cy_fit > 1, cy_fit, 1)))
    ndf = max(mask.sum() - len(p0_init), 1)

    sys_mu, sys_sig, sys_res = _systematic_study(cx, cy, float(mu), float(sigma), dark_noise_pe)

    result = _build_result(float(mu), float(sigma), float(mu_err), float(sig_err),
                           dark_noise_pe, chi2, ndf, sys_mu, sys_sig, sys_res,
                           'physics', popt.tolist(), source_energy_mev)

    printf(f"  STAGE 2 (physics model):")
    printf(f"    μ  = {mu:.2f} ± {result['peak_error']:.2f} PE")
    printf(f"    σ  = {sigma:.2f} ± {result['sigma_error']:.2f} PE")
    printf(f"    Res = {result['resolution']*100:.3f} ± {result['resolution_error']*100:.3f} %")
    printf(f"    LY  = {result['LY_PE_per_MeV']:.0f} PE/MeV")
    printf(f"    χ²/ndf = {result['chi2ndf']:.2f}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT (called from spectrum_utils.fit_source)
# ─────────────────────────────────────────────────────────────────────────────

def fit_from_arrays(cx, cy, dark_noise_pe,
                     source_energy_mev=E_GE68_MEV,
                     method_name="PE", printf=print):
    """
    Two-stage Ge-68 fit from numpy arrays.

    Parameters
    ----------
    cx, cy : numpy arrays
        Bin centers and counts.
    dark_noise_pe : float
        Dark-noise PE (pass 0.0 for nHit).
    source_energy_mev : float
        Photopeak energy in MeV.
    method_name : str
        Label for log messages.
    printf : callable
        Print function.

    Returns
    -------
    (simple_result, physics_result) : tuple of (dict or None, dict or None)
    """
    printf(f"\n{method_name} — Ge-68 two-stage fit ({source_energy_mev:.3f} MeV):")

    if cy.sum() < 100:
        printf(f"  ERROR: too few counts ({cy.sum():.0f}) — skipping")
        return None, None

    mu_init, amp_init = _find_peak(cx, cy, printf)
    if amp_init < 50:
        printf(f"  ERROR: peak too low ({amp_init:.0f} counts)")
        return None, None

    # Stage 1: Gaussian + pol3
    simple = _fit_gauss_pol3(cx, cy, dark_noise_pe, mu_init, amp_init,
                              source_energy_mev, printf)

    # Stage 2: Physics model (seeded from Stage 1)
    physics = None
    if simple is not None:
        physics = _fit_physics(cx, cy, dark_noise_pe, simple,
                                source_energy_mev, printf)
    else:
        printf(f"  Skipping physics model (Stage 1 failed)")

    return simple, physics


# ─────────────────────────────────────────────────────────────────────────────
# FILE-BASED ENTRY POINT (standalone usage / CLI)
# ─────────────────────────────────────────────────────────────────────────────

def load_spectrum(root_path):
    """Load PE histogram from ROOT file. Returns (centers, counts, dark_noise_pe)."""
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


def fit_ge68(root_path, verbose=False, dark_noise_pe_override=None):
    """Fit Ge-68 spectrum from a ROOT file. Returns (simple, physics) tuple."""
    try:
        cx, cy, dn = load_spectrum(root_path)
    except RuntimeError as e:
        print(f"  ERROR: {e}")
        return None, None

    dark_noise_pe = dark_noise_pe_override if dark_noise_pe_override is not None else dn
    pf = print if verbose else (lambda *a, **k: None)

    return fit_from_arrays(cx, cy, dark_noise_pe,
                            source_energy_mev=E_GE68_MEV,
                            method_name="Ge68", printf=pf)


# ─────────────────────────────────────────────────────────────────────────────
# PLOTTING
# ─────────────────────────────────────────────────────────────────────────────

def plot_ge68_fit(root_path, simple_result, physics_result, output_path, label=""):
    """Plot Ge-68 spectrum with both fit stages."""
    if not HAS_MPL:
        return
    try:
        cx, cy, dn = load_spectrum(root_path)
    except RuntimeError:
        return

    # Use best available result for window
    result = physics_result if physics_result else simple_result
    if result is None:
        return

    mu, sigma = result['peak'], result['sigma']

    fig, axes = plt.subplots(2, 1, figsize=(10, 7),
                             gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    ax, ax_res = axes

    win = (cx > mu - 8 * sigma) & (cx < mu + 8 * sigma)
    if win.sum() < 2:
        win = np.ones(len(cx), dtype=bool)
    if win.sum() < 2:
        plt.close(fig)
        return

    bw = float(cx[1] - cx[0]) if len(cx) > 1 else 1.0
    ax.step(cx[win], cy[win], where="mid", color="k", lw=1, label="Data")

    x_fine = np.linspace(float(cx[win].min()), float(cx[win].max()), 1000)

    # Plot simple fit
    if simple_result and simple_result.get('_fit_params'):
        sp = simple_result['_fit_params']
        y_simple = _gauss_pol3(x_fine, *sp)
        ax.plot(x_fine, y_simple, "b--", lw=1.5, alpha=0.7, label="Gauss+pol3")

    # Plot physics fit
    if physics_result and physics_result.get('_fit_params'):
        pp = physics_result['_fit_params']
        y_phys = _model_ge68(x_fine, *pp)
        ax.plot(x_fine, y_phys, "r-", lw=2, label="Physics model")

    ax.set_ylabel("Events / bin", fontsize=10)
    ax.set_title(f"Ge-68 fit   {label}", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", framealpha=0.85)
    ax.set_yscale("log")

    # Info box
    info_lines = [f"μ = {result['peak']:.1f} ± {result['peak_error']:.1f} PE",
                  f"σ = {result['sigma']:.1f} ± {result['sigma_error']:.1f} PE",
                  f"Res = {result['resolution']*100:.2f} ± {result['resolution_error']*100:.2f} %",
                  f"LY = {result['LY_PE_per_MeV']:.0f} PE/MeV",
                  f"χ²/ndf = {result['chi2ndf']:.2f}",
                  f"DN = {result['dark_noise_PE']:.0f} PE",
                  f"Method: {result['method']}"]
    ax.text(0.975, 0.975, "\n".join(info_lines),
            transform=ax.transAxes, fontsize=8.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="0.6", alpha=0.92))

    # Residuals
    pars = result['_fit_params']
    if result['method'] == 'physics' and pars:
        y_pred = _model_ge68(cx[win], *pars)
    elif result['method'] == 'gauss+pol3' and pars:
        y_pred = _gauss_pol3(cx[win], *pars)
    else:
        y_pred = cy[win]

    pull = (cy[win] - y_pred) / np.sqrt(np.where(cy[win] > 1, cy[win], 1))
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
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Two-stage Ge-68 spectrum fitting")
    parser.add_argument("input", help="Spectrum ROOT file or directory")
    parser.add_argument("--output-dir", default="ge68_fits")
    parser.add_argument("--scan", action="store_true")
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
        simple, physics = fit_ge68(fpath, verbose=True)

        best = physics if physics else simple
        if best is None:
            print(f"  FAILED")
            continue

        result_save = {k: v for k, v in best.items() if k != "_fit_params"}
        if simple:
            result_save['simple_method'] = {k: v for k, v in simple.items() if k != "_fit_params"}

        json_path = os.path.join(args.output_dir, f"{stem}_ge68_fit.json")
        with open(json_path, "w") as jf:
            json.dump(result_save, jf, indent=2)

        png_path = os.path.join(args.output_dir, f"{stem}_ge68_fit.png")
        plot_ge68_fit(fpath, simple, physics, png_path, label=stem)

        all_results[stem] = result_save

    summary_path = os.path.join(args.output_dir, "ge68_fit_summary.json")
    with open(summary_path, "w") as jf:
        json.dump(all_results, jf, indent=2)
    print(f"\nSummary: {summary_path}")
    print(f"Done — {len(all_results)}/{len(files)} fits succeeded.")


if __name__ == "__main__":
    main()
