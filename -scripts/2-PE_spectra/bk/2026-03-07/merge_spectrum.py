#!/usr/bin/env python3

"""
merge_spectrum.py - Merge individual spectrum ROOT files into combined file

Merges histograms from per-file ROOT outputs of get_spectrum.py and
re-fits the combined statistics with the FULL error budget matching
get_spectrum.py:
  • Primary fit  : Gaussian + pol3 background
  • Systematic   : 3 fit-range widths × 3 background poly degrees = 9 fits
                   RMS spread of results → systematic uncertainty
  • Total error  : stat ⊕ sys in quadrature
  • Stored keys  : *_ERR (total), *_ERR_STAT, *_ERR_SYS

The fit logic is self-contained (no spectrum_utils dependency for the fitter).
resolve_source() and the SOURCES table are still imported from spectrum_utils
so that the canonical source-energy mapping lives in one place.

Usage:
  python merge_spectrum.py "spectrum_RUN1055-*.root" spectrum_RUN1055-MERGED.root --source-name Ge68
  python merge_spectrum.py "spectrum_RUN1344-*.root" spectrum_RUN1344-MERGED.root --source-name Cs137
  python merge_spectrum.py "spectrum_RUN1345-*.root" spectrum_RUN1345-MERGED.root   # no source → no fit
"""

import sys
import os
import glob
import argparse
import numpy as np

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

# Source table imported from spectrum_utils (single source of truth for energies)
try:
    from spectrum_utils import resolve_source, SOURCES
except ImportError as _e:
    print(f"ERROR: Cannot import spectrum_utils: {_e}")
    print("       Make sure spectrum_utils.py is in the same directory as merge_spectrum.py")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# PE floor: hard lower bound for peak search regardless of OV or source.
# Keeps the fitter away from the dark-noise / pedestal pile-up near bin 0.
# Should be safely below any real photopeak (~1000 PE margin).
PE_SEARCH_FLOOR = 1500.0  # PE — tune if detector response changes drastically


# ─────────────────────────────────────────────────────────────────────────────
# Primary fit: Gaussian + pol3 background
# (matches get_spectrum.py primary fit model)
# ─────────────────────────────────────────────────────────────────────────────

def fit_calibration_peak(hist, method_name, dark_noise_pe,
                         expected_light_yield=4500.0,
                         source_energy_mev=1.022):
    """
    Fit Gaussian + pol3 background to a calibration source photopeak.
    Works for Ge-68 (1.022 MeV), Cs-137 (0.662 MeV), or any other source.

    Resolution is calculated as: σ / (μ − DN)

    Parameters
    ----------
    hist : TH1
        Histogram to fit.
    method_name : str
        Label for logging (e.g. "Discrete_PE", "nHit").
    dark_noise_pe : float
        Dark-noise PE correction subtracted from the resolution denominator.
    expected_light_yield : float
        Approximate light yield in PE/MeV at nominal OV (default: 4500).
        Used ONLY to define the search window — not as a hard constraint.
    source_energy_mev : float
        Photopeak energy of the calibration source in MeV.
        Ge-68 endpoint : 1.022 MeV  (default)
        Cs-137         : 0.662 MeV

    Peak-finding strategy
    ─────────────────────
    1.  Physics estimate:  expected_peak = expected_light_yield × source_energy_mev

    2.  Search window: [max(PE_SEARCH_FLOOR, 0.5 × expected_peak),
                        2.0 × expected_peak]
        - Lower bound is the MAX of PE_SEARCH_FLOOR and 50 % of expected peak.
          PE_SEARCH_FLOOR is a hard floor that keeps the search away from the
          dark-noise / pedestal pile-up near bin 0, regardless of OV or source.
        - Upper bound is 2 × expected_peak (catches ~85 % OV upshift).

    3.  Peak center is anchored to the ACTUAL maximum bin in the window —
        never to expected_peak or hist.GetMean() (both are unreliable).

    4.  Sigma estimate: 3 % of peak_center.

    5.  Fit window: [peak_center − 7σ, peak_center + 6σ] (asymmetric because
        the Compton shoulder is on the low-PE side).

    6.  Background model: pol3 (consistent with get_spectrum.py primary fit).

    7.  Sanity check: warn if found peak deviates > 50 % from expected_peak
        (OV probably changed), but always use the found position — never fall
        back to expected_peak.
    """
    print(f"\n{method_name} - Fitting {source_energy_mev:.3f} MeV peak:")

    # ── Step 1: physics estimate ──────────────────────────────────────────────
    expected_peak = expected_light_yield * source_energy_mev

    # ── Step 2: search window — decoupled lower bound ─────────────────────────
    search_min = max(PE_SEARCH_FLOOR, expected_peak * 0.50)
    search_max = expected_peak * 2.00

    bin_min = max(1,                   hist.FindBin(search_min))
    bin_max = min(hist.GetNbinsX(),    hist.FindBin(search_max))

    if bin_min >= bin_max:
        print(f"  ERROR: search window [{search_min:.0f}, {search_max:.0f}] PE is "
               f"outside histogram range — check expected_light_yield and source_energy_mev")
        return None

    max_bin, max_content = bin_min, hist.GetBinContent(bin_min)
    for b in range(bin_min, bin_max + 1):
        c = hist.GetBinContent(b)
        if c > max_content:
            max_content, max_bin = c, b

    peak_center = hist.GetBinCenter(max_bin)

    print(f"  Source energy            : {source_energy_mev:.3f} MeV")
    print(f"  Expected peak (physics)  : {expected_peak:.0f} PE")
    print(f"  Search window            : [{search_min:.0f}, {search_max:.0f}] PE")
    print(f"  Found max at bin {max_bin:<5d}  : {peak_center:.0f} PE  "
           f"(height {max_content:.0f} counts)")
    print(f"  hist.GetMean()           : {hist.GetMean():.0f} PE  (informational only)")

    # ── Step 3: sanity check ──────────────────────────────────────────────────
    deviation = abs(peak_center - expected_peak) / expected_peak
    if deviation > 0.50:
        print(f"  WARNING: found peak ({peak_center:.0f} PE) deviates "
               f"{deviation*100:.0f}% from physics expectation ({expected_peak:.0f} PE). "
               f"OV may have changed — verify fit quality from χ²/ndf.")

    # ── Step 4: minimum statistics guard ─────────────────────────────────────
    if max_content < 100:
        print(f"  ERROR: Peak too low ({max_content:.0f} < 100 counts) — skipping fit")
        return None

    # ── Step 5: sigma estimate and fit window ─────────────────────────────────
    sigma_estimate = peak_center * 0.03          # 3 % energy resolution seed
    fit_min = peak_center - 7.0 * sigma_estimate
    fit_max = peak_center + 6.0 * sigma_estimate

    # ── Step 6: build and run fit (pol3 background) ───────────────────────────
    safe_name = method_name.replace(' ', '_').replace('.', '_')
    fit_func  = ROOT.TF1(f"fit_{safe_name}", "gaus(0) + pol3(3)", fit_min, fit_max)

    fit_func.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0, 0.0, 0.0)
    fit_func.SetParNames("Amplitude", "Mean", "Sigma", "BG_p0", "BG_p1", "BG_p2", "BG_p3")
    fit_func.SetParLimits(0, 0.01 * max_content, 20.0 * max_content)
    fit_func.SetParLimits(1, fit_min, fit_max)
    # Sigma: lower at 0.3 % of peak (avoid zero), upper at 10 × estimate
    fit_func.SetParLimits(2, 0.003 * peak_center, 10.0 * sigma_estimate)

    fit_status = hist.Fit(fit_func, "RSQN")

    # ── Step 7: extract results ───────────────────────────────────────────────
    if fit_status == 0:
        fitted_peak  = fit_func.GetParameter(1)
        fitted_sigma = abs(fit_func.GetParameter(2))
        peak_error   = fit_func.GetParError(1)
        sigma_error  = abs(fit_func.GetParError(2))
        chi2ndf      = fit_func.GetChisquare() / max(1, fit_func.GetNDF())

        denom = fitted_peak - dark_noise_pe
        if denom <= 0:
            print(f"  WARNING: fitted_peak - DN <= 0 ({fitted_peak:.1f} - {dark_noise_pe:.1f}); "
                   f"using σ/μ instead")
            denom = fitted_peak

        resolution       = fitted_sigma / denom
        rel_sigma_error  = sigma_error / fitted_sigma if fitted_sigma > 0 else 0
        rel_denom_error  = peak_error  / denom        if denom        > 0 else 0
        resolution_error = resolution * np.sqrt(rel_sigma_error**2 + rel_denom_error**2)

        print("  RESULTS:")
        print(f"    Source energy          : {source_energy_mev:.3f} MeV")
        print(f"    Dark noise (DN)        : {dark_noise_pe:.3f} PE")
        print(f"    Peak (μ)               : {fitted_peak:.2f} ± {peak_error:.2f} PE")
        print(f"    Peak − DN (μ−DN)       : {denom:.2f} PE")
        print(f"    Sigma (σ)              : {fitted_sigma:.2f} ± {sigma_error:.2f} PE")
        print(f"    Resolution σ/(μ−DN)    : {resolution*100:.3f} ± {resolution_error*100:.3f} %  (stat only)")
        print(f"    χ²/ndf                 : {chi2ndf:.2f}")

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
    else:
        print(f"  ERROR: Fit failed (status {fit_status})")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Systematic study — identical logic to get_spectrum.systematic_fit_study()
# 3 range widths × 3 background poly degrees = 9 configurations
# ─────────────────────────────────────────────────────────────────────────────

def systematic_fit_study(hist, method_name, dark_noise_pe):
    """
    Assess fit-model systematic by repeating the Gaussian+background fit with
    3 fit-range widths × 3 background polynomial degrees = 9 configurations.
    The RMS spread across successful fits is the systematic uncertainty.

    Args:
        hist           ROOT TH1 to study (already filled, not modified)
        method_name    label for TF1 names (no spaces)
        dark_noise_pe  average detector dark noise in PE (DN_TOT);
                       pass 0.0 for nHit where no DN correction applies

    Returns dict:
        sigma_sys       RMS spread of fitted sigma values [PE]
        mean_sys        RMS spread of fitted (raw) mean values [PE]
        resolution_sys  RMS spread of resolution = σ/(μ−DN) values [%]
        n_fits          number of successful fit configurations
    """
    _FAIL = {'sigma_sys': 0.0, 'mean_sys': 0.0, 'resolution_sys': 0.0, 'n_fits': 0}

    if hist is None or hist.GetEntries() < 100:
        return _FAIL

    # Locate histogram peak in the central 70 % of the x-range
    expected_peak = hist.GetMean()
    search_window = expected_peak * 0.7
    bin_min = hist.FindBin(expected_peak - search_window)
    bin_max = hist.FindBin(expected_peak + search_window)

    max_bin     = bin_min
    max_content = hist.GetBinContent(bin_min)
    for b in range(bin_min, bin_max + 1):
        c = hist.GetBinContent(b)
        if c > max_content:
            max_content = c
            max_bin     = b

    peak_center    = hist.GetBinCenter(max_bin)
    sigma_estimate = peak_center * 0.03        # ~3 % initial sigma estimate

    # Sanitise method_name for ROOT TF1 object names
    safe_name = method_name.replace(' ', '_').replace('/', '_')

    # 3 × 3 = 9 configurations
    range_configs = [(5, 4), (7, 6), (10, 8)]   # (low_factor, high_factor) × σ_est
    poly_degrees  = [1, 2, 3]                    # pol1 / pol2 / pol3 background

    results = []

    for (lo, hi) in range_configs:
        for deg in poly_degrees:
            fit_min = peak_center - lo * sigma_estimate
            fit_max = peak_center + hi * sigma_estimate

            fname = f"f_sys_{safe_name}_{lo}_{hi}_pol{deg}"
            if deg == 1:
                ff = ROOT.TF1(fname, "gaus(0) + pol1(3)", fit_min, fit_max)
                ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0)
            elif deg == 2:
                ff = ROOT.TF1(fname, "gaus(0) + pol2(3)", fit_min, fit_max)
                ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0, 0.0)
            else:
                ff = ROOT.TF1(fname, "gaus(0) + pol3(3)", fit_min, fit_max)
                ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0, 0.0, 0.0)

            ff.SetParLimits(0, 0.1 * max_content, 10.0 * max_content)
            ff.SetParLimits(1, fit_min, fit_max)
            ff.SetParLimits(2, 0.3 * sigma_estimate, 3.0 * sigma_estimate)

            try:
                fit_result = hist.Fit(fname, "RSQN")
                status_ok  = (fit_result.Status() == 0)
            except Exception:
                status_ok  = False

            if not status_ok:
                continue

            fm = ff.GetParameter(1)
            fs = abs(ff.GetParameter(2))
            denom = fm - dark_noise_pe
            if denom <= 0 or fs <= 0:
                continue

            results.append({
                'mean':       fm,
                'sigma':      fs,
                'resolution': (fs / denom) * 100.0,   # in %
            })

    if len(results) < 2:
        print(f"    WARNING: systematic study '{method_name}': "
               f"only {len(results)} fits OK — systematic set to 0")
        return _FAIL

    means       = np.array([r['mean']       for r in results])
    sigmas      = np.array([r['sigma']      for r in results])
    resolutions = np.array([r['resolution'] for r in results])

    mean_sys       = float(np.std(means,       ddof=1))
    sigma_sys      = float(np.std(sigmas,      ddof=1))
    resolution_sys = float(np.std(resolutions, ddof=1))

    print(f"    Systematic study '{method_name}': {len(results)}/9 fits OK  |  "
           f"σ(mean)={mean_sys:.2f} PE  "
           f"σ(sigma)={sigma_sys:.2f} PE  "
           f"σ(res)={resolution_sys:.4f}%")

    return {
        'sigma_sys':       sigma_sys,
        'mean_sys':        mean_sys,
        'resolution_sys':  resolution_sys,
        'n_fits':          len(results),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Error budget — identical logic to get_spectrum._apply_error_budget()
# ─────────────────────────────────────────────────────────────────────────────

def _apply_error_budget(fit_result, sys_study):
    """
    Augment a fit_calibration_peak result dict with the full error budget.

    Adds keys:
        resolution_error_stat   statistical uncertainty from Gaussian fit
        resolution_error_sys    systematic uncertainty from fit-model variation [%]
        resolution_error        total = sqrt(stat² + sys²)  [overwrites original]
        peak_error_stat / peak_error_sys / peak_error   (same for mean)
        sigma_error_stat / sigma_error_sys / sigma_error (same for sigma)

    Note: resolution_error from fit_calibration_peak is in fractional units
    (e.g. 0.0234), while resolution_sys from systematic_fit_study is in % units
    (e.g. 0.50).  We keep resolution_error in fraction units for consistency,
    converting sys to fraction before combining.
    """
    out = dict(fit_result)

    stat_res_frac = fit_result.get('resolution_error', 0.0)   # fraction
    stat_mu       = fit_result.get('peak_error',       0.0)   # PE
    stat_sig      = fit_result.get('sigma_error',      0.0)   # PE

    sys_res_frac  = sys_study.get('resolution_sys', 0.0) / 100.0  # % → fraction
    sys_mu        = sys_study.get('mean_sys',        0.0)          # PE
    sys_sig       = sys_study.get('sigma_sys',       0.0)          # PE

    out['resolution_error_stat'] = stat_res_frac
    out['resolution_error_sys']  = sys_res_frac
    out['resolution_error']      = float(np.sqrt(stat_res_frac**2 + sys_res_frac**2))

    out['peak_error_stat']  = stat_mu
    out['peak_error_sys']   = sys_mu
    out['peak_error']       = float(np.sqrt(stat_mu**2  + sys_mu**2))

    out['sigma_error_stat'] = stat_sig
    out['sigma_error_sys']  = sys_sig
    out['sigma_error']      = float(np.sqrt(stat_sig**2 + sys_sig**2))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Summary table helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_row(label, result):
    """Format one summary table row (stat ± sys, χ²/ndf)."""
    if result:
        mean_s  = f"{result['peak']:.1f} ± {result['peak_error']:.1f}"
        sigma_s = f"{result['sigma']:.1f} ± {result['sigma_error']:.1f}"
        res_tot = result['resolution_error']          * 100.0   # total [%]
        res_stat= result.get('resolution_error_stat', res_tot / 100.0) * 100.0
        res_sys = result.get('resolution_error_sys',  0.0)      * 100.0
        res_s   = (f"{result['resolution']*100:.3f} "
                   f"± {res_tot:.3f} % "
                   f"(stat {res_stat:.3f}  sys {res_sys:.3f})")
        chi_s   = f"{result.get('chi2ndf', float('nan')):.2f}"
        return f"{label:<20} {mean_s:<26} {sigma_s:<26} {res_s:<50} {chi_s:<10} {'PASS':<6}"
    return f"{label:<20} {'---':<26} {'---':<26} {'---':<50} {'---':<10} {'FAIL':<6}"


# ─────────────────────────────────────────────────────────────────────────────
# info_parts builder helper — writes stat + sys + total keys
# ─────────────────────────────────────────────────────────────────────────────

def _append_result(parts, prefix, result):
    """
    Append fit result fields to info_parts list.
    Writes full error budget: *_ERR (total), *_ERR_STAT, *_ERR_SYS.
    Matches exactly the key names written by get_spectrum.py.
    """
    if result:
        parts += [
            f"RES_{prefix}={result['resolution']:.6f}",
            f"RES_{prefix}_ERR={result['resolution_error']:.6f}",
            f"RES_{prefix}_ERR_STAT={result.get('resolution_error_stat', result['resolution_error']):.6f}",
            f"RES_{prefix}_ERR_SYS={result.get('resolution_error_sys', 0.0):.6f}",
            f"MEAN_{prefix}={result['peak']:.6f}",
            f"MEAN_{prefix}_ERR={result['peak_error']:.6f}",
            f"MEAN_{prefix}_ERR_STAT={result.get('peak_error_stat', result['peak_error']):.6f}",
            f"MEAN_{prefix}_ERR_SYS={result.get('peak_error_sys', 0.0):.6f}",
            f"SIGMA_{prefix}={result['sigma']:.6f}",
            f"SIGMA_{prefix}_ERR={result['sigma_error']:.6f}",
            f"SIGMA_{prefix}_ERR_STAT={result.get('sigma_error_stat', result['sigma_error']):.6f}",
            f"SIGMA_{prefix}_ERR_SYS={result.get('sigma_error_sys', 0.0):.6f}",
            f"CHI2NDF_{prefix}={result.get('chi2ndf', -1):.4f}",
        ]
    else:
        parts += [
            f"RES_{prefix}=-1",       f"RES_{prefix}_ERR=0",
            f"RES_{prefix}_ERR_STAT=0", f"RES_{prefix}_ERR_SYS=0",
            f"MEAN_{prefix}=-1",      f"MEAN_{prefix}_ERR=0",
            f"MEAN_{prefix}_ERR_STAT=0", f"MEAN_{prefix}_ERR_SYS=0",
            f"SIGMA_{prefix}=-1",     f"SIGMA_{prefix}_ERR=0",
            f"SIGMA_{prefix}_ERR_STAT=0", f"SIGMA_{prefix}_ERR_SYS=0",
            f"CHI2NDF_{prefix}=-1",
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Main merge function
# ─────────────────────────────────────────────────────────────────────────────

def merge_spectrum_files(input_pattern, outfile, source_name=None, dark_noise_pe=0.0):
    """Merge individual spectrum ROOT files and re-fit the combined histogram
    with the full error budget (stat ⊕ sys), matching get_spectrum.py output.

    Parameters
    ----------
    input_pattern : str
        Glob pattern for input ROOT files (e.g. "spectrum_RUN1055-*.root").
    outfile : str
        Output path for the merged ROOT file.
    source_name : str or None
        Calibration source name (e.g. 'Ge68', 'Cs137'). If None, histograms
        are merged and saved but no peak fit is performed.
    dark_noise_pe : float
        Dark noise in PE to subtract in resolution denominator. If 0 (default),
        the value is averaged from the dark_noise_pe TNamed stored in each
        individual input file.
    """

    print("=" * 70)
    print("MERGE_SPECTRUM - Combine Individual ROOT Files")
    print("=" * 70)

    # ── Resolve source ────────────────────────────────────────────────────────
    source_energy_mev, source_desc = resolve_source(source_name)

    if source_energy_mev is None:
        print("WARNING: No calibration source specified (--source-name not provided).")
        print("         Histograms will be merged and saved, but NO PEAK FIT will run.")
    else:
        print(f"Calibration source : {source_desc}  ({source_energy_mev:.3f} MeV)")

    # ── Find files ────────────────────────────────────────────────────────────
    input_files = sorted(glob.glob(input_pattern))

    if not input_files:
        print(f"ERROR: No files found matching: {input_pattern}")
        return 1

    print(f"\nFound {len(input_files)} ROOT files to merge")
    for i, f in enumerate(input_files[:5], 1):
        print(f"  {i}. {os.path.basename(f)}")
    if len(input_files) > 5:
        print(f"  ... and {len(input_files) - 5} more")
    print(f"\nOutput: {outfile}")
    print()

    # ── Merge histograms ──────────────────────────────────────────────────────
    h_PEcontin_merged   = None
    h_PEdiscrete_merged = None
    h_nHit_merged       = None

    pe_cut    = -1
    pe_method = "unknown"
    n_events  = 0
    n_merged  = 0

    print("Merging histograms...")

    for i, infile in enumerate(input_files, 1):
        print(f"\r  Processing file {i}/{len(input_files)}", end='', flush=True)

        fin = ROOT.TFile.Open(infile, "READ")
        if not fin or fin.IsZombie():
            print(f"\n  WARNING: Cannot open {infile}, skipping...")
            continue

        h_cont = fin.Get("h_PEcontin")
        h_disc = fin.Get("h_PEdiscrete")
        h_nhit = fin.Get("h_nHit")

        if not h_cont or not h_disc or not h_nhit:
            print(f"\n  WARNING: Missing histograms in {infile}, skipping...")
            fin.Close()
            continue

        # Read per-file metadata (pe_cut and pe_method from first file; n_events summed from ALL)
        energy_info = fin.Get("energy_info")
        if energy_info:
            for part in energy_info.GetTitle().split(';'):
                if part.startswith('PE_CUT=') and n_merged == 0:
                    try:
                        pe_cut = int(part.split('=', 1)[1])
                    except ValueError:
                        pass
                elif part.startswith('PE_METHOD=') and n_merged == 0:
                    pe_method = part.split('=', 1)[1]
                elif part.startswith('N_EVENTS='):
                    # BUG FIX: accumulate from every file, not only the first
                    try:
                        n_events += int(part.split('=', 1)[1])
                    except ValueError:
                        pass

        if n_merged == 0:
            h_PEcontin_merged   = h_cont.Clone("h_PEcontin");   h_PEcontin_merged.SetDirectory(0)
            h_PEdiscrete_merged = h_disc.Clone("h_PEdiscrete"); h_PEdiscrete_merged.SetDirectory(0)
            h_nHit_merged       = h_nhit.Clone("h_nHit");       h_nHit_merged.SetDirectory(0)
        else:
            h_PEcontin_merged.Add(h_cont)
            h_PEdiscrete_merged.Add(h_disc)
            h_nHit_merged.Add(h_nhit)

        fin.Close()
        n_merged += 1

    print(f"\r  ✓ Merged {n_merged}/{len(input_files)} files successfully")
    print()

    if h_PEcontin_merged is None:
        print("ERROR: No valid files could be merged.")
        return 1

    # ── Average dark noise across ALL individual files ─────────────────────────
    dn_values = []
    for infile in input_files:
        fin_dn = ROOT.TFile.Open(infile, "READ")
        if not fin_dn or fin_dn.IsZombie():
            continue
        dn_named = fin_dn.Get("dark_noise_pe")
        if dn_named:
            try:
                v = float(dn_named.GetTitle())
                if v > 0:
                    dn_values.append(v)
            except (ValueError, TypeError):
                pass
        fin_dn.Close()

    if dark_noise_pe > 0:
        effective_dn = dark_noise_pe
        dn_std       = 0.0
        print(f"Dark noise: {effective_dn:.4f} PE  (manual override via --dark-noise-pe)")
    elif dn_values:
        effective_dn = float(np.mean(dn_values))
        dn_std       = float(np.std(dn_values))
        print(f"Dark noise: {effective_dn:.4f} ± {dn_std:.4f} PE  "
              f"(averaged over {len(dn_values)} files)")
        if len(set(round(v, 4) for v in dn_values)) > 1:
            print(f"  WARNING: DN varies across files "
                  f"(min={min(dn_values):.4f}, max={max(dn_values):.4f}) "
                  f"— check calibration consistency")
    else:
        effective_dn = 0.0
        dn_std       = 0.0
        print("Dark noise: not found in any input file — resolution will be σ/μ")

    # ── Fit merged histograms + systematic study ──────────────────────────────
    print()
    print("=" * 70)
    print("FITTING MERGED SPECTRA  (primary: gaus+pol3, systematic: 9 configs)")
    print("=" * 70)

    if source_energy_mev is None:
        print("Skipping fit (no source specified).")
        result_pe_cont = None
        result_pe      = None
        result_nhit    = None
    else:
        print(f"Source : {source_desc}  ({source_energy_mev:.3f} MeV)")

        # ── Continuous PE ─────────────────────────────────────────────────────
        raw_cont  = fit_calibration_peak(
            h_PEcontin_merged,   "PEcontin",    effective_dn,
            expected_light_yield=4500.0, source_energy_mev=source_energy_mev)
        if raw_cont is not None:
            print("  Running systematic study for PEcontin ...")
            sys_cont      = systematic_fit_study(h_PEcontin_merged, "PEcontin", effective_dn)
            result_pe_cont = _apply_error_budget(raw_cont, sys_cont)
        else:
            result_pe_cont = None

        # ── Discrete PE ───────────────────────────────────────────────────────
        raw_pe    = fit_calibration_peak(
            h_PEdiscrete_merged, "Discrete_PE", effective_dn,
            expected_light_yield=4500.0, source_energy_mev=source_energy_mev)
        if raw_pe is not None:
            print("  Running systematic study for Discrete_PE ...")
            sys_pe    = systematic_fit_study(h_PEdiscrete_merged, "Discrete_PE", effective_dn)
            result_pe  = _apply_error_budget(raw_pe, sys_pe)
        else:
            result_pe = None

        # ── nHit ──────────────────────────────────────────────────────────────
        raw_nhit  = fit_calibration_peak(
            h_nHit_merged,       "nHit",        0.0,
            expected_light_yield=3800.0, source_energy_mev=source_energy_mev)
        if raw_nhit is not None:
            print("  Running systematic study for nHit ...")
            sys_nhit  = systematic_fit_study(h_nHit_merged, "nHit", 0.0)
            result_nhit = _apply_error_budget(raw_nhit, sys_nhit)
        else:
            result_nhit = None

    # ── Build energy_info TNamed ──────────────────────────────────────────────
    info_parts = [
        f"PE_CUT={pe_cut}",
        f"PE_METHOD={pe_method}",
        f"N_FILES={n_merged}",
        f"N_EVENTS={n_events}",
        f"MERGED=True",
        f"SOURCE_NAME={source_name or 'none'}",
        f"DARK_NOISE_PE={effective_dn:.6f}",
        f"DARK_NOISE_PE_STD={dn_std:.6f}",
        f"DARK_NOISE_N_FILES={len(dn_values)}",
    ]
    if source_energy_mev is not None:
        info_parts.append(f"SOURCE_ENERGY_MEV={source_energy_mev:.4f}")

    _append_result(info_parts, "PEcontin", result_pe_cont)
    _append_result(info_parts, "PE",       result_pe)
    _append_result(info_parts, "NHIT",     result_nhit)

    energy_info = ROOT.TNamed("energy_info", ";".join(info_parts))

    # ── Save merged ROOT file ─────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("SAVING MERGED OUTPUT")
    print("=" * 70)

    fout = ROOT.TFile(outfile, "RECREATE")
    h_PEcontin_merged.Write()
    h_PEdiscrete_merged.Write()
    h_nHit_merged.Write()
    energy_info.Write()

    if effective_dn > 0:
        ROOT.TNamed("dark_noise_pe", f"{effective_dn:.6f}").Write()
        ROOT.TNamed(
            "dark_noise_info",
            f"avg={effective_dn:.6f};std={dn_std:.6f};n_files={len(dn_values)}"
        ).Write()

    fout.Close()

    print(f"✓ Merged file saved: {outfile}")

    # ── Summary table ─────────────────────────────────────────────────────────
    print()
    print("=" * 130)
    print("MERGE SUMMARY")
    print("=" * 130)
    print(f"Files merged    : {n_merged}/{len(input_files)}")
    print(f"Events total    : {n_events}")
    print(f"PE cut mode     : {pe_method} ({pe_cut} PE/ch)")
    if effective_dn > 0:
        print(f"Dark noise      : {effective_dn:.4f} ± {dn_std:.4f} PE  "
              f"(from {len(dn_values)}/{len(input_files)} files)")
    else:
        print("Dark noise      : not available in individual files")
    src_label = source_desc if source_energy_mev else "none (no fit performed)"
    print(f"Source          : {src_label}")
    print()
    print(f"{'Method':<20} {'Mean [PE]':<26} {'Sigma [PE]':<26} "
          f"{'Resolution (tot ± stat  sys)':<52} {'χ²/ndf':<10} {'Status':<6}")
    print("-" * 130)
    print(_fmt_row("Continuous PE",  result_pe_cont))
    print(_fmt_row("Discrete PE",    result_pe))
    print(_fmt_row("nHit",           result_nhit))
    print("-" * 130)
    print()
    print("SUCCESS")
    print("=" * 130)

    return 0


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge individual spectrum ROOT files into combined file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ge-68 source
  python merge_spectrum.py "spectrum_RUN1157-*.root" spectrum_RUN1157-MERGED.root --source-name Ge68

  # Cs-137 source (CLS arm)
  python merge_spectrum.py "spectrum_RUN1344-*.root" spectrum_RUN1344-MERGED.root --source-name Cs137

  # No source — merge histograms only, skip fit
  python merge_spectrum.py "spectrum_RUN1345-*.root" spectrum_RUN1345-MERGED.root

  # Override dark noise manually (e.g. if individual files predate DN logging)
  python merge_spectrum.py "spectrum_RUN1055-*.root" spectrum_RUN1055-MERGED.root \\
      --source-name Ge68 --dark-noise-pe 12.5
"""
    )

    parser.add_argument("input_pattern",
                        help="Glob pattern for input ROOT files (quote it to prevent shell expansion)")
    parser.add_argument("outfile",
                        help="Output merged ROOT file path")

    known = ', '.join(sorted(SOURCES.keys()))
    parser.add_argument("--source-name", type=str, default=None, metavar="SOURCE",
                        help=f"Calibration source for peak fit. Known sources: {known}. "
                             "If omitted, histograms are merged but no fit is performed.")
    parser.add_argument("--dark-noise-pe", type=float, default=0.0,
                        help="Override dark noise in PE (default: auto-averaged from input files).")

    args = parser.parse_args()

    # Validate source name early so we fail before doing any work
    if args.source_name:
        try:
            resolve_source(args.source_name)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    sys.exit(merge_spectrum_files(
        args.input_pattern,
        args.outfile,
        source_name=args.source_name,
        dark_noise_pe=args.dark_noise_pe,
    ))
