#!/usr/bin/env python3
"""
spectrum_utils.py — Shared utilities for get_spectrum.py and merge_spectrum.py.

Provides:
    SOURCES           dict  canonical calibration source table
    resolve_source()        look up (energy_MeV, description) for a source name
    fit_source()            dispatch to the correct fit_peaks module

All actual fitting logic lives in fit_peaks_ge68.py / fit_peaks_cs137.py.
This module is the single source of truth for source energies and the
dispatcher that routes a source name to the right fitter.
"""

import numpy as np

try:
    import ROOT
except ImportError:
    raise ImportError("ROOT (PyROOT) is required by spectrum_utils — "
                      "make sure it is in your PYTHONPATH before importing this module.")


# =============================================================================
# CALIBRATION SOURCE TABLE
# Energies from arXiv:2204.03256, Table 1 (TAO CDR), unless noted.
# =============================================================================

SOURCES = {
    # ── Positron sources ──────────────────────────────────────────────────────
    'Ge68':     (1.022,  'Ge-68 e⁺ annihilation (1.022 MeV)'),
    # ── γ sources ─────────────────────────────────────────────────────────────
    'Cs137':    (0.662,  'Cs-137 γ (0.662 MeV)'),
    'Mn54':     (0.835,  'Mn-54 γ (0.835 MeV)'),
    'K40':      (1.461,  'K-40 γ (1.461 MeV)'),
    'Co60':     (2.506,  'Co-60 γ sum (1.173 + 1.333 MeV = 2.506 MeV)'),
    'Co60_low': (1.173,  'Co-60 γ low line (1.173 MeV)'),
    'Co60_high':(1.333,  'Co-60 γ high line (1.333 MeV)'),
    # ── Neutron capture sources ───────────────────────────────────────────────
    'AmC_nH':   (2.223,  'AmC n+H capture γ (2.223 MeV)'),
    'AmC_O16':  (6.130,  'AmC ¹⁶O* de-excitation γ (6.130 MeV)'),
}

_SOURCES_LC = {k.lower(): (k, v) for k, v in SOURCES.items()}


# =============================================================================
# SOURCE RESOLVER
# =============================================================================

def resolve_source(source_name):
    """Return (energy_MeV, description) for a named calibration source.

    Returns (None, None) if source_name is None or empty.
    Raises ValueError if source_name is non-empty but unknown.
    """
    if source_name is None or source_name.strip() == '':
        return None, None

    key = source_name.strip().lower()
    if key not in _SOURCES_LC:
        known = ', '.join(sorted(SOURCES.keys()))
        raise ValueError(f"Unknown source '{source_name}'. Known sources: {known}")

    _, (energy_mev, description) = _SOURCES_LC[key]
    return energy_mev, description


# =============================================================================
# HISTOGRAM → NUMPY HELPER
# =============================================================================

def hist_to_arrays(hist):
    """Extract (bin_centers, counts) numpy arrays from a ROOT TH1."""
    n = hist.GetNbinsX()
    cx = np.array([hist.GetBinCenter(b)  for b in range(1, n + 1)])
    cy = np.array([hist.GetBinContent(b) for b in range(1, n + 1)])
    return cx, cy


# =============================================================================
# FIT DISPATCHER — routes to the right fit_peaks module
# =============================================================================

def fit_source(hist, source_name, dark_noise_pe, method_name="PE", printf=print):
    """
    Dispatch fitting to the correct fit_peaks module based on source_name.

    For Ge-68 and Cs-137 dedicated physics-model fitters are used.
    For all other sources a generic Gaussian + pol3 fit is performed.

    Parameters
    ----------
    hist : ROOT.TH1
        Filled histogram to fit.
    source_name : str
        Calibration source key (e.g. 'Ge68', 'Cs137').
    dark_noise_pe : float
        Dark-noise PE correction for resolution denominator.
    method_name : str
        Label for log messages (e.g. 'PEcontin', 'Discrete_PE', 'nHit').
    printf : callable
        Print function for logging.

    Returns
    -------
    (simple_result, physics_result) : tuple of (dict or None, dict or None)
        simple_result  — Gaussian + pol3 fit (always attempted).
        physics_result — Full physics model (Ge68/Cs137 only; None for others).
        Each dict has keys:
            peak, sigma, peak_error, sigma_error,
            resolution, resolution_error,
            resolution_error_stat, resolution_error_sys,
            peak_error_stat, peak_error_sys,
            sigma_error_stat, sigma_error_sys,
            chi2ndf, status, method
    """
    if hist is None or hist.GetEntries() < 50:
        printf(f"  {method_name}: histogram empty or too few entries — skipping")
        return None, None

    energy_mev, desc = resolve_source(source_name)
    if energy_mev is None:
        return None, None

    cx, cy = hist_to_arrays(hist)
    key = source_name.strip().lower()

    if key == 'ge68':
        from fit_peaks_ge68 import fit_from_arrays
        return fit_from_arrays(cx, cy, dark_noise_pe,
                               source_energy_mev=energy_mev,
                               method_name=method_name, printf=printf)

    elif key == 'cs137':
        from fit_peaks_cs137 import fit_from_arrays
        return fit_from_arrays(cx, cy, dark_noise_pe,
                               source_energy_mev=energy_mev,
                               method_name=method_name, printf=printf)

    else:
        # Generic fit for all other sources
        simple = _generic_gauss_pol3(cx, cy, dark_noise_pe,
                                      source_energy_mev=energy_mev,
                                      method_name=method_name, printf=printf)
        return simple, None


# =============================================================================
# GENERIC GAUSSIAN + POL3 FIT (for sources without dedicated fitters)
# =============================================================================

def _gauss_pol3(x, N, mu, sigma, p0, p1, p2, p3):
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)


def _generic_gauss_pol3(cx, cy, dark_noise_pe, source_energy_mev=1.0,
                         method_name="PE", printf=print):
    """
    Data-driven Gaussian + pol3 fit. Peak found at max-counts bin.
    Includes systematic study (3 windows × 3 poly degrees).
    """
    from scipy.optimize import curve_fit

    printf(f"\n{method_name} — fitting {source_energy_mev:.3f} MeV peak (generic gauss+pol3):")

    # ── Data-driven peak finding ──────────────────────────────────────────────
    # Search in the upper half of the histogram (skip pedestal / dark noise)
    mid = len(cx) // 4
    search_cy = cy[mid:]
    search_cx = cx[mid:]
    if search_cy.max() < 10:
        search_cy = cy
        search_cx = cx

    idx_max = np.argmax(search_cy)
    mu_init = float(search_cx[idx_max])
    amp_init = float(search_cy[idx_max])

    if amp_init < 50:
        printf(f"  ERROR: peak too low ({amp_init:.0f} counts) — skipping")
        return None

    printf(f"  Found peak at {mu_init:.0f} PE  (height {amp_init:.0f} counts)")

    sig_init = mu_init * 0.03
    fit_min = mu_init - 7.0 * sig_init
    fit_max = mu_init + 6.0 * sig_init
    mask = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 8:
        printf(f"  ERROR: fit window too narrow")
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
        printf(f"  ERROR: curve_fit failed: {exc}")
        return None

    mu_fit = float(popt[1])
    sigma_fit = abs(float(popt[2]))
    mu_err = float(perr[1])
    sig_err = float(perr[2])

    denom = mu_fit - dark_noise_pe
    if denom <= 0:
        printf(f"  WARNING: μ−DN ≤ 0 ({mu_fit:.1f}−{dark_noise_pe:.1f}); using μ")
        denom = mu_fit

    resolution = sigma_fit / denom
    res_err = resolution * np.sqrt((sig_err / sigma_fit) ** 2 + (mu_err / denom) ** 2)

    y_pred = _gauss_pol3(cx_fit, *popt)
    chi2 = float(np.sum(((cy_fit - y_pred) ** 2) / np.where(cy_fit > 1, cy_fit, 1)))
    ndf = max(len(cx_fit) - len(popt), 1)

    # ── Systematic study ──────────────────────────────────────────────────────
    sys_mu, sys_sig, sys_res = _systematic_study_generic(
        cx, cy, mu_fit, sigma_fit, dark_noise_pe)

    mu_err_tot = float(np.sqrt(mu_err ** 2 + sys_mu ** 2))
    sig_err_tot = float(np.sqrt(sig_err ** 2 + sys_sig ** 2))
    res_err_tot = float(np.sqrt(res_err ** 2 + (sys_res / 100.0) ** 2))

    printf(f"  RESULTS (gauss+pol3):")
    printf(f"    μ  = {mu_fit:.2f} ± {mu_err_tot:.2f} PE")
    printf(f"    σ  = {sigma_fit:.2f} ± {sig_err_tot:.2f} PE")
    printf(f"    Res = {resolution*100:.3f} ± {res_err_tot*100:.3f} %")
    printf(f"    χ²/ndf = {chi2/ndf:.2f}")

    return dict(
        peak=mu_fit, sigma=sigma_fit,
        peak_error=mu_err_tot, sigma_error=sig_err_tot,
        peak_error_stat=mu_err, peak_error_sys=float(sys_mu),
        sigma_error_stat=sig_err, sigma_error_sys=float(sys_sig),
        resolution=resolution, resolution_error=res_err_tot,
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100.0),
        chi2ndf=chi2 / ndf, status=True,
        method='gauss+pol3',
    )


def _systematic_study_generic(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """3 windows × 3 poly degrees → systematic spread."""
    from scipy.optimize import curve_fit

    range_configs = [(5, 4), (7, 6), (10, 8)]
    poly_degrees = [1, 2, 3]
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
