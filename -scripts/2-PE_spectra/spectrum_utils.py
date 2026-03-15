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

Fitting uses ROOT TF1 (Minuit MIGRAD) throughout — no scipy.
"""

import numpy as np

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
except ImportError:
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

# Global counter for unique ROOT object names
_SU_COUNTER = 0


def _unique_name(prefix="su"):
    global _SU_COUNTER
    _SU_COUNTER += 1
    return f"{prefix}_{_SU_COUNTER}"


# =============================================================================
# SOURCE RESOLVER
# =============================================================================

def resolve_source(source_name):
    """Return (energy_MeV, description) for a named calibration source."""
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
    n  = hist.GetNbinsX()
    cx = np.array([hist.GetBinCenter(b)  for b in range(1, n + 1)])
    cy = np.array([hist.GetBinContent(b) for b in range(1, n + 1)])
    return cx, cy


# =============================================================================
# FIT DISPATCHER
# =============================================================================

def fit_source(hist, source_name, dark_noise_pe, method_name="PE", printf=print):
    """
    Dispatch fitting to the correct fit_peaks module based on source_name.

    For Ge-68 and Cs-137 dedicated physics-model fitters are used.
    For all other sources a generic Gaussian + pol3 fit (ROOT TF1) is performed.

    Returns
    -------
    (simple_result, physics_result) : tuple of (dict or None, dict or None)
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
        simple = _generic_gauss_pol3_root(cx, cy, dark_noise_pe,
                                          source_energy_mev=energy_mev,
                                          method_name=method_name, printf=printf)
        return simple, None


# =============================================================================
# ROOT TF1 HELPERS (internal)
# =============================================================================

def _arrays_to_th1d(cx, cy, name=None):
    """Convert bin-centre / count arrays to ROOT TH1D."""
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
    """ROOT TF1 fit. Returns (popt, perr, chi2, ndf, ok)."""
    n_par     = len(p0)
    rcallable = _RootCallable(model_fn, n_par)
    tf1_name  = _unique_name("tf1_su")
    h_name    = _unique_name("h_su")

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


# =============================================================================
# GENERIC GAUSSIAN + POL3 FIT  (ROOT TF1, for sources without dedicated fitters)
# =============================================================================

def _gauss_pol3_model(x, N, mu, sigma, p0, p1, p2, p3):
    s = max(abs(sigma), 1e-6)
    return (N * np.exp(-0.5 * ((x - mu) / s) ** 2)
            + p0 + p1 * x + p2 * x ** 2 + p3 * x ** 3)


def _generic_gauss_pol3_root(cx, cy, dark_noise_pe, source_energy_mev=1.0,
                               method_name="PE", printf=print):
    """
    Data-driven Gaussian + pol3 fit using ROOT TF1.
    Peak found at max-counts bin (skipping lower 25%).
    Includes systematic study (3 windows × 3 poly degrees).
    """
    printf(f"\n{method_name} — fitting {source_energy_mev:.3f} MeV peak (generic gauss+pol3, ROOT TF1):")

    mid = len(cx) // 4
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
    lo = [0.0,       mu_init * 0.70, sig_init * 0.10, -1e30, -1e30, -1e30, -1e30]
    hi = [amp_init * 20, mu_init * 1.30, sig_init * 5.0,  1e30,  1e30,  1e30,  1e30]

    popt, perr, chi2, ndf, ok = _root_fit(
        _gauss_pol3_model, cx_fit, cy_fit, p0_init, lo, hi,
        float(cx_fit[0]), float(cx_fit[-1]))

    if popt is None:
        printf("  ERROR: ROOT TF1 fit returned None")
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
    res_err    = resolution * np.sqrt((sig_err / sigma_fit)**2 + (mu_err / denom)**2) if sigma_fit > 0 else 0.0

    chi2_ndf = float(chi2 / ndf) if ndf > 0 else -1.0

    sys_mu, sys_sig, sys_res = _systematic_study_generic_root(
        cx, cy, mu_fit, sigma_fit, dark_noise_pe)

    mu_err_tot  = float(np.sqrt(mu_err**2  + sys_mu**2))
    sig_err_tot = float(np.sqrt(sig_err**2 + sys_sig**2))
    res_err_tot = float(np.sqrt(res_err**2 + (sys_res / 100.0)**2))

    printf(f"  RESULTS (gauss+pol3, ROOT TF1):")
    printf(f"    μ  = {mu_fit:.2f} ± {mu_err_tot:.2f} PE")
    printf(f"    σ  = {sigma_fit:.2f} ± {sig_err_tot:.2f} PE")
    printf(f"    Res = {resolution * 100:.3f} ± {res_err_tot * 100:.3f} %")
    printf(f"    χ²/ndf = {chi2_ndf:.2f}")

    return dict(
        peak=mu_fit, sigma=sigma_fit,
        peak_error=mu_err_tot, sigma_error=sig_err_tot,
        peak_error_stat=mu_err, peak_error_sys=float(sys_mu),
        sigma_error_stat=sig_err, sigma_error_sys=float(sys_sig),
        resolution=resolution, resolution_error=res_err_tot,
        resolution_error_stat=float(res_err),
        resolution_error_sys=float(sys_res / 100.0),
        chi2ndf=chi2_ndf, status=True,
        method='gauss+pol3',
    )


def _gauss_poly_trial(x_sc, N, mu, sk, *bp):
    """Gaussian + polynomial (variable degree). Used in systematic study."""
    sig  = sk * np.sqrt(max(abs(mu), 1.0))
    g    = N * np.exp(-0.5 * ((x_sc - mu) / max(sig, 1e-6))**2)
    poly = sum(bp[k] * x_sc**k for k in range(len(bp)))
    return float(g + poly)


def _systematic_study_generic_root(cx, cy, mu_nom, sigma_nom, dark_noise_pe):
    """
    Systematic study using ROOT TF1 fits with 3 window sizes × 3 poly degrees.
    Returns (sys_mu, sys_sigma, sys_res_pct).
    """
    range_configs = [(5, 4), (7, 6), (10, 8)]
    poly_degrees  = [1, 2, 3]
    results       = []

    for (lo_sig, hi_sig) in range_configs:
        fit_min = mu_nom - lo_sig * sigma_nom
        fit_max = mu_nom + hi_sig * sigma_nom
        mask = (cx >= fit_min) & (cx <= fit_max)
        if mask.sum() < 10:
            continue
        cx_w, cy_w = cx[mask], cy[mask]

        for deg in poly_degrees:
            n_poly = deg + 1
            sk_init = sigma_nom / max(np.sqrt(mu_nom), 1.0)

            def _trial(x_sc, *args):
                return _gauss_poly_trial(x_sc, *args)

            bkg_p0 = [float(cy_w.mean())] + [0.0] * deg
            p0_t   = [float(cy_w.max()), mu_nom, sk_init] + bkg_p0
            lo_t   = [0.0, mu_nom * 0.7, 0.01] + [-1e30] * n_poly
            hi_t   = [float(cy_w.max()) * 20, mu_nom * 1.3, 10.0] + [1e30] * n_poly

            popt, perr, chi2, ndf, ok = _root_fit(
                _trial, cx_w, cy_w, p0_t, lo_t, hi_t,
                float(cx_w[0]), float(cx_w[-1]))

            if popt is None or not ok:
                continue

            m    = popt[1]
            s    = popt[2] * np.sqrt(max(abs(m), 1.0))
            d    = m - dark_noise_pe
            if d > 0 and s > 0:
                results.append(dict(mean=m, sigma=s, resolution=(s / d) * 100.0))

    if len(results) < 2:
        return 0.0, 0.0, 0.0

    return (float(np.std([r['mean']       for r in results])),
            float(np.std([r['sigma']      for r in results])),
            float(np.std([r['resolution'] for r in results])))
