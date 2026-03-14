#!/usr/bin/env python3
"""
spectrum_utils.py — Shared utilities for get_spectrum.py and merge_spectrum.py.

Provides:
    SOURCES           dict  canonical calibration source table
    resolve_source()        look up (energy_MeV, description) for a source name
    fit_source()            dispatch to the correct fit_peaks module

All fits use ROOT TF1 (no scipy).
"""

import numpy as np

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False
    raise ImportError("ROOT (PyROOT) is required by spectrum_utils — "
                      "make sure it is in your PYTHONPATH before importing this module.")


# =============================================================================
# CALIBRATION SOURCE TABLE
# =============================================================================

SOURCES = {
    'Ge68':      (1.022,  'Ge-68 e⁺ annihilation (1.022 MeV)'),
    'Cs137':     (0.662,  'Cs-137 γ (0.662 MeV)'),
    'Mn54':      (0.835,  'Mn-54 γ (0.835 MeV)'),
    'K40':       (1.461,  'K-40 γ (1.461 MeV)'),
    'Co60':      (2.506,  'Co-60 γ sum (1.173 + 1.333 MeV = 2.506 MeV)'),
    'Co60_low':  (1.173,  'Co-60 γ low line (1.173 MeV)'),
    'Co60_high': (1.333,  'Co-60 γ high line (1.333 MeV)'),
    'AmC_nH':    (2.223,  'AmC n+H capture γ (2.223 MeV)'),
    'AmC_O16':   (6.130,  'AmC ¹⁶O* de-excitation γ (6.130 MeV)'),
}

_SOURCES_LC = {k.lower(): (k, v) for k, v in SOURCES.items()}


# =============================================================================
# SOURCE RESOLVER
# =============================================================================

def resolve_source(source_name):
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
    n  = hist.GetNbinsX()
    cx = np.array([hist.GetBinCenter(b)  for b in range(1, n + 1)])
    cy = np.array([hist.GetBinContent(b) for b in range(1, n + 1)])
    return cx, cy


# =============================================================================
# ROOT-BASED CURVE FIT HELPER (replaces scipy.optimize.curve_fit)
# =============================================================================

_fit_counter = 0


def _root_curve_fit(model_func, cx_fit, cy_fit, p0, bounds_lo, bounds_hi):
    """
    ROOT TF1-based curve fitting.
    model_func: callable, signature f(x_array, *params) -> y_array.
    Returns (popt, perr, chi2, ndf).
    """
    global _fit_counter
    _fit_counter += 1
    uid = _fit_counter

    n_params = len(p0)
    n_bins   = len(cx_fit)
    if n_bins < 2:
        raise RuntimeError("Too few bins")

    bw   = float(cx_fit[1] - cx_fit[0])
    xmin = float(cx_fit[0]  - bw / 2)
    xmax = float(cx_fit[-1] + bw / 2)

    h = ROOT.TH1D(f"_hsu_{uid}", "", n_bins, xmin, xmax)
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

    tf1 = ROOT.TF1(f"_tf1su_{uid}", _cb, float(cx_fit[0]), float(cx_fit[-1]), n_params)
    ROOT.SetOwnership(tf1, True)

    for i in range(n_params):
        tf1.SetParameter(i, float(p0[i]))
        lo_i = float(bounds_lo[i]) if bounds_lo is not None else -1e30
        hi_i = float(bounds_hi[i]) if bounds_hi is not None else  1e30
        if lo_i != hi_i:
            tf1.SetParLimits(i, lo_i, hi_i)

    fr   = h.Fit(tf1, "SNQR")
    popt = np.array([tf1.GetParameter(i) for i in range(n_params)], dtype=float)
    perr = np.array([tf1.GetParError(i)  for i in range(n_params)], dtype=float)
    chi2 = float(tf1.GetChisquare())
    ndf  = int(tf1.GetNDF())

    h.Delete()
    tf1.Delete()
    return popt, perr, chi2, ndf


# =============================================================================
# FIT DISPATCHER
# =============================================================================

def fit_source(hist, source_name, dark_noise_pe, method_name="PE", printf=print):
    """
    Dispatch fitting to the correct fit_peaks module based on source_name.

    Returns (simple_result, physics_result).
    """
    if hist is None or hist.GetEntries() < 50:
        printf(f"  {method_name}: histogram empty or too few entries — skipping")
        return None, None

    energy_mev, desc = resolve_source(source_name)
    if energy_mev is None:
        return None, None

    cx, cy = hist_to_arrays(hist)
    key    = source_name.strip().lower()

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
        simple = _generic_gauss_pol3(cx, cy, dark_noise_pe,
                                     source_energy_mev=energy_mev,
                                     method_name=method_name, printf=printf)
        return simple, None


# =============================================================================
# GENERIC GAUSSIAN + POL3 FIT (ROOT TF1, for sources without dedicated fitters)
# =============================================================================

def _gauss_pol3_func(x, N, mu, sigma, p0, p1, p2, p3):
    return (N * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)


def _generic_gauss_pol3(cx, cy, dark_noise_pe, source_energy_mev=1.0,
                        method_name="PE", printf=print):
    """
    Data-driven Gaussian + pol3 fit via ROOT TF1.
    Includes systematic study (3 windows × 3 poly degrees).
    """
    printf(f"\n{method_name} — fitting {source_energy_mev:.3f} MeV peak (generic gauss+pol3):")

    mid       = len(cx) // 4
    search_cy = cy[mid:]
    search_cx = cx[mid:]
    if search_cy.max() < 10:
        search_cy = cy
        search_cx = cx

    idx_max  = np.argmax(search_cy)
    mu_init  = float(search_cx[idx_max])
    amp_init = float(search_cy[idx_max])

    if amp_init < 50:
        printf(f"  ERROR: peak too low ({amp_init:.0f} counts) — skipping")
        return None

    printf(f"  Found peak at {mu_init:.0f} PE  (height {amp_init:.0f} counts)")

    sig_init = mu_init * 0.03
    fit_min  = mu_init - 7.0 * sig_init
    fit_max  = mu_init + 6.0 * sig_init
    mask     = (cx >= fit_min) & (cx <= fit_max)
    if mask.sum() < 8:
        printf("  ERROR: fit window too narrow")
        return None

    cx_fit, cy_fit = cx[mask], cy[mask]

    p0_init = [amp_init, mu_init, sig_init,
               float(cy_fit.min()) + 1.0, 0.0, 0.0, 0.0]
    lo = [0.0, mu_init * 0.70, sig_init * 0.10, -1e30, -1e30, -1e30, -1e30]
    hi = [amp_init * 20, mu_init * 1.30, sig_init * 5.0,  1e30,  1e30,  1e30,  1e30]

    try:
        popt, perr, chi2, ndf = _root_curve_fit(
            _gauss_pol3_func, cx_fit, cy_fit, p0_init, lo, hi)
    except Exception as exc:
        printf(f"  ERROR: ROOT fit failed: {exc}")
        return None

    mu_fit    = float(popt[1])
    sigma_fit = abs(float(popt[2]))
    mu_err    = float(perr[1])
    sig_err   = float(perr[2])

    denom = mu_fit - dark_noise_pe
    if denom <= 0:
        printf(f"  WARNING: μ−DN ≤ 0 ({mu_fit:.1f}−{dark_noise_pe:.1f}); using μ")
        denom = mu_fit

    resolution = sigma_fit / denom
    res_err    = resolution * np.sqrt((sig_err / sigma_fit) ** 2 + (mu_err / denom) ** 2)

    c2ndf = chi2 / ndf if ndf > 0 else -1.0

    sys_mu, sys_sig, sys_res = _systematic_study_generic(
        cx, cy, mu_fit, sigma_fit, dark_noise_pe)

    mu_err_tot  = float(np.sqrt(mu_err ** 2 + sys_mu ** 2))
    sig_err_tot = float(np.sqrt(sig_err ** 2 + sys_sig ** 2))
    res_err_tot = float(np.sqrt(res_err ** 2 + (sys_res / 100.0) ** 2))

    printf("  RESULTS (gauss+pol3):")
    printf(f"    μ  = {mu_fit:.2f} ± {mu_err_tot:.2f} PE")
    printf(f"    σ  = {sigma_fit:.2f} ± {sig_err_tot:.2f} PE")
    printf(f"    Res = {resolution * 100:.3f} ± {res_err_tot * 100:.3f} %")
    printf(f"    χ²/ndf = {c2ndf:.2f}")

    return dict(
        peak=mu_fit, sigma=sigma_fit,
        peak_error=mu_err_tot, sigma_error=sig_err_tot,
        peak_error_stat=mu_err, peak_error_sys=float(sys_mu),
        sigma_error_stat=sig_err, sigma_error_sys=float(sys_sig),
        resolution=resolution, resolution_error=res_err_tot,
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100.0),
        chi2ndf=c2ndf, status=True,
        method='gauss+pol3',
    )


def _generic_trial_factory(deg):
    """Build a generic Gauss + poly-deg model callable."""
    def _trial(x, N, mu, sig, *bp):
        peak = N * np.exp(-0.5 * ((x - mu) / np.maximum(sig, 1.0)) ** 2)
        poly = sum(bp[i] * x ** i for i in range(len(bp)))
        return peak + poly
    return _trial


def _systematic_study_generic(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """3 windows × 3 poly degrees → systematic spread, ROOT TF1 fits."""
    range_configs = [(5, 4), (7, 6), (10, 8)]
    poly_degrees  = [1, 2, 3]
    results = []

    for (lo, hi) in range_configs:
        fit_min = mu_nom - lo * sigma_nom
        fit_max = mu_nom + hi * sigma_nom
        mask    = (cx >= fit_min) & (cx <= fit_max)
        if mask.sum() < 10:
            continue
        cx_w, cy_w = cx[mask], cy[mask]

        for deg in poly_degrees:
            trial_func = _generic_trial_factory(deg)
            n_p = 3 + (deg + 1)
            bkg_p = [float(cy_w.mean())] + [0.0] * deg
            p0_t  = [float(cy_w.max()), float(mu_nom), float(sigma_nom)] + bkg_p
            lo_b  = [0.0, mu_nom * 0.7, sigma_nom * 0.1] + [-1e30] * (deg + 1)
            hi_b  = [float(cy_w.max()) * 20, mu_nom * 1.3, sigma_nom * 5.0] + [1e30] * (deg + 1)

            try:
                popt, perr, chi2, ndf = _root_curve_fit(
                    trial_func, cx_w, cy_w, p0_t, lo_b, hi_b)
                m = float(popt[1])
                s = abs(float(popt[2]))
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
