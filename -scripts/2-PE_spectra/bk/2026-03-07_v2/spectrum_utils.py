#!/usr/bin/env python3
"""
spectrum_utils.py — Shared utilities for get_spectrum.py and merge_spectrum.py.

Provides:
    SOURCES           dict  canonical calibration source table
    resolve_source()        look up (energy_MeV, description) for a source name
    fit_calibration_peak()  Gaussian + pol3 photopeak fitter with DN correction

This module is the single source of truth for source energies and fit logic.
Both get_spectrum.py and merge_spectrum.py import from here so that any
change to the fitter or the energy table is automatically shared.

NOTE: merge_spectrum.py carries its own copy of fit_calibration_peak and
systematic_fit_study for historical self-containedness; their implementations
must stay identical to the versions here.
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
#
# Each entry: 'NAME': (energy_MeV, human_readable_description)
# =============================================================================

SOURCES = {
    # ── Positron sources ──────────────────────────────────────────────────────
    'Ge68':     (1.022,  'Ge-68 e⁺ annihilation (1.022 MeV)'),

    # ── γ sources ─────────────────────────────────────────────────────────────
    'Cs137':    (0.662,  'Cs-137 γ (0.662 MeV)'),
    'Mn54':     (0.835,  'Mn-54 γ (0.835 MeV)'),
    'K40':      (1.461,  'K-40 γ (1.461 MeV)'),

    # Co-60: summed peak (both γ detected simultaneously) and individual lines
    'Co60':     (2.506,  'Co-60 γ sum (1.173 + 1.333 MeV = 2.506 MeV)'),
    'Co60_low': (1.173,  'Co-60 γ low line (1.173 MeV)'),
    'Co60_high':(1.333,  'Co-60 γ high line (1.333 MeV)'),

    # ── Neutron capture sources ───────────────────────────────────────────────
    'AmC_nH':   (2.223,  'AmC n+H capture γ (2.223 MeV)'),
    'AmC_O16':  (6.130,  'AmC ¹⁶O* de-excitation γ (6.130 MeV)'),
}

# Lower-case alias lookup for case-insensitive matching
_SOURCES_LC = {k.lower(): (k, v) for k, v in SOURCES.items()}


# =============================================================================
# SOURCE RESOLVER
# =============================================================================

def resolve_source(source_name):
    """Return (energy_MeV, description) for a named calibration source.

    Parameters
    ----------
    source_name : str or None
        Source name as used in the launcher / argparse (e.g. 'Ge68', 'Cs137').
        Case-insensitive.  Pass None to indicate "no source — skip fit".

    Returns
    -------
    (energy_MeV, description) : (float, str)   if source_name is known
    (None, None)               : if source_name is None or empty string
    raises ValueError          : if source_name is non-empty but not in SOURCES
    """
    if source_name is None or source_name.strip() == '':
        return None, None

    key = source_name.strip().lower()
    if key not in _SOURCES_LC:
        known = ', '.join(sorted(SOURCES.keys()))
        raise ValueError(
            f"Unknown source '{source_name}'. "
            f"Known sources: {known}"
        )

    _, (energy_mev, description) = _SOURCES_LC[key]
    return energy_mev, description


# =============================================================================
# PE SEARCH FLOOR
# Hard lower bound for the peak-search window, regardless of OV or source.
# Should be safely below any real photopeak (>1000 PE margin for all sources).
# =============================================================================

PE_SEARCH_FLOOR = 1500.0   # PE — tune if detector response changes drastically


# =============================================================================
# PRIMARY FITTER: Gaussian + pol3 background
# =============================================================================

def fit_calibration_peak(hist, method_name, dark_noise_pe,
                         expected_light_yield=4500.0,
                         source_energy_mev=1.022,
                         printf=None):
    """
    Fit a Gaussian + pol3 background to a calibration-source photopeak.

    Works for any source in SOURCES (Ge-68, Cs-137, Co-60, …) and for nHit
    histograms (pass dark_noise_pe=0.0, expected_light_yield~3800).

    Resolution is calculated as:  σ / (μ − DN)

    Parameters
    ----------
    hist : ROOT.TH1
        Histogram to fit.  Must already be filled.
    method_name : str
        Label for printout and TF1 name (e.g. "Discrete_PE", "nHit").
    dark_noise_pe : float
        Dark-noise PE correction subtracted from the resolution denominator.
        Pass 0.0 for nHit spectra where no DN correction applies.
    expected_light_yield : float
        Approximate light yield in PE/MeV at nominal OV (default 4500).
        Used ONLY to initialise the peak-search window; not a hard constraint.
        Typical values:
            PE spectra : 4500 PE/MeV
            nHit       : 3800 channels/MeV
    source_energy_mev : float
        Photopeak energy in MeV (default 1.022 for Ge-68).
    printf : callable or None
        Print function (default: built-in print).  Passing get_spectrum.py's
        local printf() keeps output in the same log stream.

    Peak-finding strategy
    ─────────────────────
    1.  Physics estimate : expected_peak = expected_light_yield × source_energy_mev
    2.  Search window    : [max(PE_SEARCH_FLOOR, 0.50 × expected_peak),
                            2.00 × expected_peak]
        • Lower bound is the MAX of PE_SEARCH_FLOOR and 50 % of expected peak.
          PE_SEARCH_FLOOR prevents the search from landing in the dark-noise /
          pedestal pile-up near bin 0, regardless of OV or source.
        • Upper bound at 2× expected_peak covers ~85 % OV upshift.
    3.  Peak center is the ACTUAL maximum bin in the window — never
        expected_peak or hist.GetMean() (both unreliable near tails).
    4.  Sigma seed : 3 % of peak_center.
    5.  Fit window : [peak_center − 7σ, peak_center + 6σ]  (asymmetric because
        the Compton shoulder sits on the low-PE side).
    6.  Background model : pol3 (4 free parameters).
    7.  Sanity check : warn if found peak deviates > 50 % from expected_peak.

    Returns
    -------
    dict with keys:
        peak            fitted Gaussian mean [PE]
        sigma           fitted Gaussian sigma [PE]
        peak_error      uncertainty on mean from covariance matrix [PE]
        sigma_error     uncertainty on sigma from covariance matrix [PE]
        resolution      σ / (μ − DN)  [fraction]
        resolution_error  propagated statistical uncertainty [fraction]
        chi2ndf         χ²/ndf of the primary fit
        status          True (fit converged)
    or None if the fit failed or statistics were insufficient.
    """
    if printf is None:
        printf = print

    printf(f"\n{method_name} — fitting {source_energy_mev:.3f} MeV peak:")

    if hist is None or hist.GetEntries() < 50:
        printf(f"  ERROR: histogram empty or too few entries "
               f"({int(hist.GetEntries()) if hist else 0}) — skipping fit")
        return None

    # ── Step 1: physics estimate ──────────────────────────────────────────────
    expected_peak = expected_light_yield * source_energy_mev

    # ── Step 2: search window ─────────────────────────────────────────────────
    search_min = max(PE_SEARCH_FLOOR, expected_peak * 0.50)
    search_max = expected_peak * 2.00

    bin_min = max(1,                hist.FindBin(search_min))
    bin_max = min(hist.GetNbinsX(), hist.FindBin(search_max))

    if bin_min >= bin_max:
        printf(f"  ERROR: search window [{search_min:.0f}, {search_max:.0f}] is "
               f"outside the histogram range — check expected_light_yield and "
               f"source_energy_mev")
        return None

    # ── Step 3: find actual peak in window ────────────────────────────────────
    max_bin     = bin_min
    max_content = hist.GetBinContent(bin_min)
    for b in range(bin_min, bin_max + 1):
        c = hist.GetBinContent(b)
        if c > max_content:
            max_content = c
            max_bin     = b

    peak_center = hist.GetBinCenter(max_bin)

    printf(f"  Source energy            : {source_energy_mev:.3f} MeV")
    printf(f"  Expected peak (physics)  : {expected_peak:.0f} PE")
    printf(f"  Search window            : [{search_min:.0f}, {search_max:.0f}] PE")
    printf(f"  Found max at bin {max_bin:<5d}  : {peak_center:.0f} PE  "
           f"(height {max_content:.0f} counts)")
    printf(f"  hist.GetMean()           : {hist.GetMean():.0f} PE  (informational only)")

    # ── Sanity check: warn if peak deviates > 50 % from expectation ───────────
    deviation = abs(peak_center - expected_peak) / max(expected_peak, 1e-9)
    if deviation > 0.50:
        printf(f"  WARNING: found peak ({peak_center:.0f} PE) deviates "
               f"{deviation*100:.0f}% from physics expectation "
               f"({expected_peak:.0f} PE). "
               f"OV may have changed — verify χ²/ndf.")

    # ── Minimum statistics guard ──────────────────────────────────────────────
    if max_content < 100:
        printf(f"  ERROR: peak too low ({max_content:.0f} < 100 counts) — skipping fit")
        return None

    # ── Step 4+5: sigma seed and fit window ───────────────────────────────────
    sigma_estimate = peak_center * 0.03          # 3 % energy resolution seed
    fit_min = peak_center - 7.0 * sigma_estimate
    fit_max = peak_center + 6.0 * sigma_estimate

    # ── Step 6: build TF1 (Gaussian + pol3 background) ───────────────────────
    safe_name = method_name.replace(' ', '_').replace('.', '_').replace('/', '_')
    fit_func  = ROOT.TF1(f"fit_{safe_name}",
                         "gaus(0) + pol3(3)", fit_min, fit_max)

    fit_func.SetParameters(max_content, peak_center, sigma_estimate,
                           100.0, 0.0, 0.0, 0.0)
    fit_func.SetParNames("Amplitude", "Mean", "Sigma",
                         "BG_p0", "BG_p1", "BG_p2", "BG_p3")

    # Parameter limits — keep Gaussian physical
    fit_func.SetParLimits(0, 0.01 * max_content, 20.0 * max_content)
    fit_func.SetParLimits(1, fit_min, fit_max)
    # Sigma: lower at 0.3 % of peak_center (avoid zero), upper at 10 × seed
    fit_func.SetParLimits(2, 0.003 * peak_center, 10.0 * sigma_estimate)

    # "RSQN": Range, chi²-improved (S), Quiet (Q), No-draw (N)
    fit_status = hist.Fit(fit_func, "RSQN")

    # ── Step 7: extract and validate results ──────────────────────────────────
    if fit_status != 0:
        printf(f"  ERROR: fit failed (Minuit status {fit_status})")
        return None

    fitted_peak  = fit_func.GetParameter(1)
    fitted_sigma = abs(fit_func.GetParameter(2))
    peak_error   = fit_func.GetParError(1)
    sigma_error  = abs(fit_func.GetParError(2))
    chi2ndf      = (fit_func.GetChisquare() /
                    max(1, fit_func.GetNDF()))

    # Resolution: σ / (μ − DN)
    denom = fitted_peak - dark_noise_pe
    if denom <= 0:
        printf(f"  WARNING: fitted_peak − DN ≤ 0 "
               f"({fitted_peak:.1f} − {dark_noise_pe:.1f}); "
               f"using σ/μ instead (DN correction not applied)")
        denom = fitted_peak

    resolution       = fitted_sigma / denom
    rel_sigma_error  = sigma_error / fitted_sigma if fitted_sigma > 0 else 0.0
    rel_denom_error  = peak_error  / denom        if denom        > 0 else 0.0
    resolution_error = resolution * float(
        np.sqrt(rel_sigma_error**2 + rel_denom_error**2))

    printf("  RESULTS:")
    printf(f"    Source energy          : {source_energy_mev:.3f} MeV")
    printf(f"    Dark noise (DN)        : {dark_noise_pe:.3f} PE")
    printf(f"    Peak (μ)               : {fitted_peak:.2f} ± {peak_error:.2f} PE")
    printf(f"    Peak − DN (μ−DN)       : {denom:.2f} PE")
    printf(f"    Sigma (σ)              : {fitted_sigma:.2f} ± {sigma_error:.2f} PE")
    printf(f"    Resolution σ/(μ−DN)    : {resolution*100:.3f} "
           f"± {resolution_error*100:.3f} %  (stat only)")
    printf(f"    χ²/ndf                 : {chi2ndf:.2f}")

    return {
        'peak':             fitted_peak,
        'sigma':            fitted_sigma,
        'peak_error':       peak_error,
        'sigma_error':      sigma_error,
        'resolution':       resolution,
        'resolution_error': resolution_error,
        'chi2ndf':          chi2ndf,
        'status':           True,
    }
