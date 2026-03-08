#!/usr/bin/env python3
"""
cls_scan_compare.py  –  CLS scan pipeline comparison for a single run

Produces plots of energy resolution / mean / sigma
  • vs CLS position index  (1 → 77)
  • vs radial distance from detector centre  (using initX/Y/Z from CSV)

Five pipeline combinations (a–e) × 3 metrics × 2 x-axes = 30 PNG files.

Key behaviour:
  – The merged ROOT files produced by hadd / merge_spectrum.py contain the
    histograms but their energy_info metrics are all -1 (fit not re-run).
  – This script fits a Gaussian directly on h_PEdiscrete (or h_PEcontin as
    fallback) of every merged file, and computes:
        mean   = Gaussian μ
        sigma  = Gaussian σ
        resolution = σ / (μ − DN)   [expressed in %]
    where DN is dark_noise_pe read from the same file.

Pipeline keys:
  rtraw_default  – RTRAW with default calibration
  rtraw_custom   – RTRAW with custom calibration (same run number)
  esd_pesum      – ESD noradialcut pesumbasic
  esd_pesumg     – ESD noradialcut pesumg

Usage:
  python cls_scan_compare.py \\
      --run        1344 \\
      --base-dir   /path/to/energy_resolution \\
      --output-dir ./cls_scan_output \\
      --coords-csv /path/to/InitialP_meanQEdepP_gamma.csv

Optional:
  --merged-dir   /path/to/cached/merged/spectra
  --verbose-fit        print gaus+pol3 fit results for every position
  --force-refit        re-merge and re-fit even if cached files exist

Fit model (fallback for hadd-merged files whose energy_info metrics are -1):
  Gaussian + pol3 background, with systematic study (3 fit-range widths ×
  3 background poly degrees = 9 configurations). Final errors are
  stat ⊕ systematic in quadrature, matching get_spectrum.py behaviour.
"""

import ROOT
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import argparse
import csv
import glob
import os
import shutil
import subprocess
import tempfile

ROOT.gROOT.SetBatch(True)

# ============================================================================
# CLS position → RTRAW file-number mapping  (RUN 1344, from timestamp analysis)
# Each entry lists the 2–3 RTRAW file indices overlapping with that CLS position.
# ============================================================================
CLS_POS_RTRAW_FILES = {
    1:  [1, 2],
    2:  [2, 3],
    3:  [3, 4, 5],
    4:  [5, 6, 7],
    5:  [7, 8, 9],
    6:  [9, 10],
    7:  [11, 12],
    8:  [12, 13, 14],
    9:  [14, 15, 16],
    10: [16, 17, 18],
    11: [18, 19, 20],
    12: [20, 21, 22],
    13: [22, 23, 24],
    14: [24, 25, 26],
    15: [26, 27, 28],
    16: [28, 29, 30],
    17: [30, 31, 32],
    18: [32, 33, 34],
    19: [34, 35, 36],
    20: [36, 37],
    21: [37, 38, 39],
    22: [39, 40, 41],
    23: [41, 42, 43],
    24: [43, 44],
    25: [44, 45, 46],
    26: [46, 47],
    27: [47, 48, 49],
    28: [49, 50, 51],
    29: [51, 52, 53],
    30: [53, 54, 55],
    31: [55, 56, 57],
    32: [57, 58, 59],
    33: [59, 60, 61],
    34: [61, 62, 63],
    35: [63, 64, 65],
    36: [65, 66, 67],
    37: [67, 68, 69],
    38: [69, 70],
    39: [70, 71, 72],
    40: [72, 73, 74],
    41: [74, 75, 76],
    42: [76, 77, 78],
    43: [78, 79, 80],
    44: [80, 81],
    45: [81, 82, 83],
    46: [83, 84, 85],
    47: [85, 86],
    48: [86, 87, 88],
    49: [88, 89, 90],
    50: [90, 91, 92],
    51: [92, 93, 94],
    52: [94, 95, 96],
    53: [96, 97, 98],
    54: [98, 99, 100],
    55: [100, 101, 102],
    56: [102, 103, 104],
    57: [104, 105, 106],
    58: [106, 107, 108],
    59: [108, 109, 110],
    60: [110, 111, 112],
    61: [112, 113, 114],
    62: [114, 115, 116],
    63: [116, 117, 118],
    64: [118, 119, 120],
    65: [120, 121, 122],
    66: [122, 123, 124],
    67: [124, 125, 126],
    68: [126, 127, 128],
    69: [128, 129, 130],
    70: [130, 131, 132],
    71: [132, 133, 134],
    72: [134, 135, 136],
    73: [136, 137],
    74: [137, 138, 139],
    75: [139, 140],
    76: [140, 141, 142],
    77: [142, 143],
}

# ============================================================================
# Pipeline definitions
# ============================================================================
PIPELINES = {
    'rtraw_default': {
        'pattern': 'rtraw_default',
        'label':   'RTRAW (default calib)',
    },
    'rtraw_custom': {
        'pattern': 'rtraw_run{run}',
        'label':   'RTRAW (custom calib)',
    },
    'esd_pesum': {
        'pattern': 'esd_noradialcut_pesumbasic',
        'label':   'ESD (peSum, no cut)',
    },
    'esd_pesumg': {
        'pattern': 'esd_noradialcut_pesumg',
        'label':   'ESD (peSum_g, no cut)',
    },
}

METRIC_YLABEL = {
    'resolution': r'Energy Resolution $\sigma/(\mu-\mathrm{DN})$ [%]',
    'mean':       r'Peak Mean $(\mu-\mathrm{DN})$ [PE]',
    'sigma':      r'Peak Sigma $\sigma$ [PE]',
}

# ============================================================================
# Plot combinations
# ============================================================================
COMBOS = [
    ('a_all4',
     'RTRAW default + custom  vs  ESD peSum + peSum_g',
     ['rtraw_default', 'rtraw_custom', 'esd_pesum', 'esd_pesumg']),

    ('b_rtraw_both_pesum',
     'RTRAW default + custom  vs  ESD peSum',
     ['rtraw_default', 'rtraw_custom', 'esd_pesum']),

    ('c_rtraw_both_pesumg',
     'RTRAW default + custom  vs  ESD peSum_g',
     ['rtraw_default', 'rtraw_custom', 'esd_pesumg']),

    ('d_default_vs_pesum',
     'RTRAW default  vs  ESD peSum',
     ['rtraw_default', 'esd_pesum']),

    ('e_custom_vs_pesum',
     'RTRAW custom  vs  ESD peSum',
     ['rtraw_custom', 'esd_pesum']),
]

PIPE_STYLE = {
    'rtraw_default': dict(color='#1f77b4', marker='o', ls='-',  zorder=4, ms=6),
    'rtraw_custom':  dict(color='#ff7f0e', marker='s', ls='-',  zorder=4, ms=6),
    'esd_pesum':     dict(color='#d62728', marker='^', ls='--', zorder=3, ms=6),
    'esd_pesumg':    dict(color='#9467bd', marker='v', ls='--', zorder=3, ms=6),
}

# ============================================================================
# Gaussian + polynomial background fitting on ROOT TH1  (fallback for files
# where energy_info metrics are still -1, e.g. hadd-merged spectra)
# ============================================================================

def _systematic_fit_study_cls(hist, method_name, dark_noise_pe):
    """
    Identical logic to get_spectrum.systematic_fit_study.
    3 range widths × 3 poly degrees = 9 configurations.
    Returns dict: sigma_sys, mean_sys, resolution_sys [%], n_fits.
    """
    _FAIL = {'sigma_sys': 0.0, 'mean_sys': 0.0, 'resolution_sys': 0.0, 'n_fits': 0}
    if hist is None or hist.GetEntries() < 100:
        return _FAIL

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
    sigma_estimate = peak_center * 0.03
    safe_name      = method_name.replace(' ', '_').replace('/', '_')

    range_configs = [(5, 4), (7, 6), (10, 8)]
    poly_degrees  = [1, 2, 3]
    results       = []

    for (lo, hi) in range_configs:
        for deg in poly_degrees:
            fit_min = peak_center - lo * sigma_estimate
            fit_max = peak_center + hi * sigma_estimate
            fname   = f"f_cls_{safe_name}_{lo}_{hi}_pol{deg}"
            if deg == 1:
                ff = ROOT.TF1(fname, "gaus(0)+pol1(3)", fit_min, fit_max)
                ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0)
            elif deg == 2:
                ff = ROOT.TF1(fname, "gaus(0)+pol2(3)", fit_min, fit_max)
                ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0, 0.0)
            else:
                ff = ROOT.TF1(fname, "gaus(0)+pol3(3)", fit_min, fit_max)
                ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0, 0.0, 0.0)
            ff.SetParLimits(0, 0.1 * max_content, 10.0 * max_content)
            ff.SetParLimits(1, fit_min, fit_max)
            ff.SetParLimits(2, 0.3 * sigma_estimate, 3.0 * sigma_estimate)
            try:
                fr = hist.Fit(fname, "RSQN")
                ok = (fr.Status() == 0)
            except Exception:
                ok = False
            if not ok:
                continue
            fm    = ff.GetParameter(1)
            fs    = abs(ff.GetParameter(2))
            denom = fm - dark_noise_pe
            if denom <= 0 or fs <= 0:
                continue
            results.append({'mean': fm, 'sigma': fs,
                            'resolution': (fs / denom) * 100.0})

    if len(results) < 2:
        return _FAIL

    means       = np.array([r['mean']       for r in results])
    sigmas      = np.array([r['sigma']      for r in results])
    resolutions = np.array([r['resolution'] for r in results])
    return {
        'sigma_sys':       float(np.std(sigmas,      ddof=1)),
        'mean_sys':        float(np.std(means,        ddof=1)),
        'resolution_sys':  float(np.std(resolutions,  ddof=1)),
        'n_fits':          len(results),
    }


def _fit_gaus_pol3(hist, dark_noise_pe, verbose=False):
    """
    Fit Gaussian + pol3 background on a ROOT TH1.
    Returns a metrics dict identical in structure to extract_metrics output,
    including _stat/_sys/_tot error keys.  Returns None on failure.
    """
    if hist is None or hist.GetEntries() < 10:
        return None

    # Locate peak
    expected_peak = hist.GetMean()
    search_window = expected_peak * 0.7
    bin_min = hist.FindBin(expected_peak - search_window)
    bin_max = hist.FindBin(expected_peak + search_window)
    max_bin = bin_min
    max_content = hist.GetBinContent(bin_min)
    for b in range(bin_min, bin_max + 1):
        c = hist.GetBinContent(b)
        if c > max_content:
            max_content = c
            max_bin     = b

    peak_center    = hist.GetBinCenter(max_bin)
    sigma_estimate = peak_center * 0.03
    sigma_estimate = max(sigma_estimate, 10.0)

    fit_min = peak_center - 7.0 * sigma_estimate
    fit_max = peak_center + 6.0 * sigma_estimate

    fname = f"f_cls_main_{id(hist)}"
    ff    = ROOT.TF1(fname, "gaus(0)+pol3(3)", fit_min, fit_max)
    ff.SetParameters(max_content, peak_center, sigma_estimate, 100.0, 0.0, 0.0, 0.0)
    ff.SetParLimits(0, 0.1 * max_content, 10.0 * max_content)
    ff.SetParLimits(1, fit_min, fit_max)
    ff.SetParLimits(2, 0.3 * sigma_estimate, 3.0 * sigma_estimate)

    try:
        fr = hist.Fit(fname, "RSQS")
        ok = (fr.Status() == 0)
    except Exception:
        ok = True  # older ROOT: just read params

    mean      = ff.GetParameter(1)
    mean_err  = ff.GetParError(1)
    sigma     = abs(ff.GetParameter(2))
    sigma_err = abs(ff.GetParError(2))

    if sigma <= 0 or mean <= 0:
        return None

    denom = mean - dark_noise_pe
    if denom <= 0:
        return None

    resolution     = sigma / denom              # fraction
    resolution_err = resolution * np.sqrt(
        (sigma_err / sigma) ** 2 + (mean_err / denom) ** 2
    )

    if verbose:
        print(f"        gaus+pol3 fit: mean={mean:.1f}±{mean_err:.1f}  "
              f"sigma={sigma:.1f}±{sigma_err:.1f}  "
              f"res={100*resolution:.3f}%  DN={dark_noise_pe:.1f}")

    # Systematic study
    sys = _systematic_fit_study_cls(hist, fname, dark_noise_pe)
    sys_res_frac = sys.get('resolution_sys', 0.0) / 100.0
    sys_mu       = sys.get('mean_sys',       0.0)
    sys_sig      = sys.get('sigma_sys',      0.0)

    res_tot   = float(np.sqrt(resolution_err**2  + sys_res_frac**2))
    mu_tot    = float(np.sqrt(mean_err**2         + sys_mu**2))
    sigma_tot = float(np.sqrt(sigma_err**2        + sys_sig**2))

    return dict(
        resolution_val      = resolution * 100.0,         # %
        resolution_err      = res_tot    * 100.0,          # % total
        resolution_err_stat = resolution_err * 100.0,      # % stat
        resolution_err_sys  = sys_res_frac   * 100.0,      # % sys
        mean_val            = mean,
        mean_err            = mu_tot,
        mean_err_stat       = mean_err,
        mean_err_sys        = sys_mu,
        sigma_val           = sigma,
        sigma_err           = sigma_tot,
        sigma_err_stat      = sigma_err,
        sigma_err_sys       = sys_sig,
    )


# ============================================================================
# Metric extraction from ROOT file
# ============================================================================

def extract_metrics(root_file, verbose=False):
    """
    Open a merged spectrum ROOT file and return a metric dict.

    Step 1 — read pre-computed values from energy_info TNamed (fast path):
        Uses RES_PE_ERR (total stat⊕sys) if present, else falls back to
        RES_PE_ERR for older files that only have the stat error stored.
        Also reads *_ERR_STAT and *_ERR_SYS if available.

    Step 2 — if all stored values are ≤ 0 (typical for hadd-merged files):
        Fits gaus+pol3 on h_PEdiscrete (or h_PEcontin) + runs systematic
        study.  Error budget identical to get_spectrum.

    Returns dict with keys:
        resolution_val,  resolution_err,  resolution_err_stat,  resolution_err_sys
        mean_val,        mean_err,        mean_err_stat,        mean_err_sys
        sigma_val,       sigma_err,       sigma_err_stat,       sigma_err_sys
    or None on complete failure.
    """
    try:
        f = ROOT.TFile.Open(root_file, "READ")
        if not f or f.IsZombie():
            return None

        # ── read energy_info ──────────────────────────────────────────────
        info_obj = f.Get("energy_info")
        raw = {}
        if info_obj:
            for item in info_obj.GetTitle().split(';'):
                if '=' in item:
                    k, v = item.split('=', 1)
                    try:
                        raw[k.strip()] = float(v.strip())
                    except ValueError:
                        pass

        # ── read dark noise ───────────────────────────────────────────────
        dn_obj = f.Get("dark_noise_pe")
        dark_noise_pe = 0.0
        if dn_obj:
            try:
                dark_noise_pe = float(dn_obj.GetTitle())
            except Exception:
                dark_noise_pe = raw.get('DARK_NOISE_PE', 0.0)
        else:
            dark_noise_pe = raw.get('DARK_NOISE_PE', 0.0)

        # ── check pre-computed values ─────────────────────────────────────
        res_stored = raw.get('RES_PE', -1.0)
        if res_stored > 0:
            # Prefer total error (_ERR = stat⊕sys from new get_spectrum);
            # fall back to whatever _ERR contains for older files.
            result = dict(
                resolution_val      = res_stored * 100.0,
                resolution_err      = abs(raw.get('RES_PE_ERR',      0.0)) * 100.0,
                resolution_err_stat = abs(raw.get('RES_PE_ERR_STAT', raw.get('RES_PE_ERR', 0.0))) * 100.0,
                resolution_err_sys  = abs(raw.get('RES_PE_ERR_SYS',  0.0)) * 100.0,
                mean_val            = raw.get('MEAN_PE', -1.0),
                mean_err            = abs(raw.get('MEAN_PE_ERR',      0.0)),
                mean_err_stat       = abs(raw.get('MEAN_PE_ERR_STAT', raw.get('MEAN_PE_ERR', 0.0))),
                mean_err_sys        = abs(raw.get('MEAN_PE_ERR_SYS',  0.0)),
                sigma_val           = raw.get('SIGMA_PE', -1.0),
                sigma_err           = abs(raw.get('SIGMA_PE_ERR',      0.0)),
                sigma_err_stat      = abs(raw.get('SIGMA_PE_ERR_STAT', raw.get('SIGMA_PE_ERR', 0.0))),
                sigma_err_sys       = abs(raw.get('SIGMA_PE_ERR_SYS',  0.0)),
            )
            f.Close()
            return result

        # ── fallback: re-fit from histogram ──────────────────────────────
        if verbose:
            print(f"      re-fitting {os.path.basename(root_file)} "
                  f"(stored metrics all ≤ 0)")

        hist_pe   = f.Get("h_PEdiscrete")
        hist_pc   = f.Get("h_PEcontin")
        hist = hist_pe if (hist_pe and hist_pe.GetEntries() > 0) else hist_pc

        if hist is None or hist.GetEntries() == 0:
            if verbose:
                print("      no usable histogram")
            f.Close()
            return None

        hist_clone = hist.Clone(f"h_fit_cls_{id(hist)}")
        hist_clone.SetDirectory(0)
        f.Close()

        return _fit_gaus_pol3(hist_clone, dark_noise_pe, verbose=verbose)

    except Exception as e:
        print(f"      ERROR in extract_metrics({os.path.basename(root_file)}): {e}")
        return None


# ============================================================================
# Utility: find files
# ============================================================================

def find_pipeline_dir(base_dir, run, pattern_tmpl):
    pat  = pattern_tmpl.replace('{run}', str(run))
    hits = sorted(
        glob.glob(os.path.join(base_dir, f"RUN{run}", f"{run}_{pat}*")),
        reverse=True,
    )
    return hits[0] if hits else None


def find_individual_spectrum(pipeline_dir, run, file_num):
    for fmt in (f"{file_num:03d}", str(file_num)):
        path = os.path.join(pipeline_dir, f"spectrum_RUN{run}-{fmt}.root")
        if os.path.exists(path):
            return path
    return None


# ============================================================================
# Merging (hadd with histogram-only merge; metrics re-fitted above)
# ============================================================================

def merge_spectra(input_files, output_file, force_refit=False):
    """
    Merge multiple individual spectrum ROOT files with hadd.
    If output_file already exists it is reused (cached) unless force_refit.
    Returns True on success.
    """
    if os.path.exists(output_file) and not force_refit:
        return True

    if not input_files:
        return False

    # Try merge_spectrum.py first (re-fits after merging)
    script_search = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'merge_spectrum.py'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'merge_spectrum.py'),
        'merge_spectrum.py',
    ]
    merge_script = next((p for p in script_search if os.path.exists(p)), None)

    if merge_script:
        td = tempfile.mkdtemp()
        try:
            for i, src in enumerate(input_files):
                shutil.copy2(src, os.path.join(td, f"spectrum_{i:03d}.root"))
            subprocess.run(
                ['python', merge_script,
                 os.path.join(td, "spectrum_*.root"), output_file],
                check=True, capture_output=True, text=True, timeout=180,
            )
            if os.path.exists(output_file):
                return True
        except Exception as e:
            print(f"      merge_spectrum.py failed ({e}); falling back to hadd")
        finally:
            shutil.rmtree(td, ignore_errors=True)

    # Fallback: hadd (merges histograms; metrics will be re-fitted by this script)
    try:
        r = subprocess.run(
            ['hadd', '-f', output_file] + list(input_files),
            check=True, capture_output=True, text=True, timeout=180,
        )
        return os.path.exists(output_file)
    except Exception as e:
        print(f"      hadd failed: {e}")
        return False


# ============================================================================
# Main data loader
# ============================================================================

def build_scan_data(base_dir, run, merged_dir, pos_map=None,
                    verbose=False):
    """
    For every pipeline × every CLS position:
      1. Locate 2–3 individual spectrum ROOT files.
      2. Merge them (cached in merged_dir).
      3. Fit Gaussian and extract metrics.

    Returns:
        {pipe_key: {pos: {resolution_val, resolution_err,
                          mean_val,       mean_err,
                          sigma_val,      sigma_err}}}
    """
    if pos_map is None:
        pos_map = CLS_POS_RTRAW_FILES
    os.makedirs(merged_dir, exist_ok=True)

    scan_data = {pk: {} for pk in PIPELINES}

    for pipe_key, pipe_cfg in PIPELINES.items():
        pat_tmpl = pipe_cfg['pattern']
        pipe_dir = find_pipeline_dir(base_dir, run, pat_tmpl)

        if pipe_dir is None:
            pat_str = pat_tmpl.replace('{run}', str(run))
            print(f"  [SKIP] {pipe_key}: no directory matching "
                  f"RUN{run}/{run}_{pat_str}*")
            continue

        print(f"\n  Pipeline: {pipe_key}"
              f"  →  {os.path.basename(pipe_dir)}")

        n_ok = 0
        for pos, file_nums in sorted(pos_map.items()):

            # Find individual files
            ind_files = []
            missing   = []
            for fn in file_nums:
                fp = find_individual_spectrum(pipe_dir, run, fn)
                if fp:
                    ind_files.append(fp)
                else:
                    missing.append(fn)
            if missing:
                print(f"    pos {pos:2d}: missing file(s) {missing}")
            if not ind_files:
                continue

            # Merged output path
            pat_str  = pat_tmpl.replace('{run}', str(run))
            safe_pat = pat_str.replace('/', '_')
            fname    = f"spectrum_RUN{run}_pos{pos:02d}_{safe_pat}.root"
            merged_fp = os.path.join(merged_dir, fname)

            ok = merge_spectra(ind_files, merged_fp)
            if not ok:
                print(f"    pos {pos:2d}: merge FAILED")
                continue

            # Extract / fit metrics
            metrics = extract_metrics(merged_fp, verbose=verbose)
            if metrics is None:
                print(f"    pos {pos:2d}: fit FAILED")
                continue

            scan_data[pipe_key][pos] = metrics
            n_ok += 1

            if verbose:
                print(f"    pos {pos:2d}: "
                      f"res={metrics['resolution_val']:.3f}%"
                      f"±{metrics['resolution_err']:.3f}%"
                      f"(stat={metrics.get('resolution_err_stat', 0):.3f}%"
                      f" sys={metrics.get('resolution_err_sys', 0):.3f}%)  "
                      f"mean={metrics['mean_val']:.1f}  "
                      f"sigma={metrics['sigma_val']:.1f}")

        frac = f"{n_ok}/{len(pos_map)}"
        print(f"    → {frac} positions fitted successfully")

    return scan_data


# ============================================================================
# Coordinates
# ============================================================================

def load_cls_coordinates(csv_path):
    pos_radial = {}
    if not csv_path:
        print("  INFO: --coords-csv not provided; "
              "radial-distance plots will be skipped")
        return pos_radial
    if not os.path.exists(csv_path):
        print(f"  WARNING: CSV not found: {csv_path}")
        return pos_radial

    with open(csv_path, newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                idx = int(row['PointIndex'])
                x   = float(row['initX'])
                y   = float(row['initY'])
                z   = float(row['initZ'])
                pos_radial[idx] = float(np.sqrt(x**2 + y**2 + z**2))
            except (KeyError, ValueError):
                pass

    print(f"  Loaded radial coordinates for {len(pos_radial)} positions")
    return pos_radial


# ============================================================================
# Plotting
# ============================================================================

plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams.update({
    'figure.figsize': (14, 6),
    'font.size':       11,
    'axes.labelsize':  12,
    'axes.titlesize':  13,
    'legend.fontsize': 10,
})


def _plot_single(combo_keys, scan_data, metric,
                 x_by_pos, xlabel, title, out_path):
    fig, ax = plt.subplots()
    has_data = False

    for pipe_key in combo_keys:
        pdata = scan_data.get(pipe_key, {})
        sty   = PIPE_STYLE[pipe_key]
        lbl   = PIPELINES[pipe_key]['label']

        xs, ys, es = [], [], []
        for pos in sorted(pdata):
            if pos not in x_by_pos:
                continue
            m   = pdata[pos]
            val = m.get(f'{metric}_val', -1.0)
            err = m.get(f'{metric}_err',  0.0)
            if val <= 0:
                continue
            xs.append(x_by_pos[pos])
            ys.append(val)
            es.append(err)

        if not xs:
            continue

        ax.errorbar(xs, ys, yerr=es,
                    label=lbl,
                    fmt=sty['marker'],
                    linestyle=sty['ls'],
                    color=sty['color'],
                    markersize=sty['ms'],
                    linewidth=1.8,
                    capsize=4, capthick=1.5,
                    zorder=sty['zorder'])
        has_data = True

    if not has_data:
        print(f"    SKIP (no data): {os.path.basename(out_path)}")
        plt.close(fig)
        return

    ax.set_xlabel(xlabel,                fontsize=12, fontweight='bold')
    ax.set_ylabel(METRIC_YLABEL[metric], fontsize=12, fontweight='bold')
    ax.set_title(title,                  fontsize=13, fontweight='bold')
    ax.legend(loc='best', frameon=True, fancybox=True, shadow=True)
    ax.grid(alpha=0.35)
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"    ✓  {os.path.basename(out_path)}")


def produce_all_plots(scan_data, output_dir, pos_radial, run=1344,
                      pos_map=None):
    os.makedirs(output_dir, exist_ok=True)
    if pos_map is None:
        pos_map = CLS_POS_RTRAW_FILES

    all_positions = sorted(pos_map.keys())
    x_by_pos_idx  = {p: p for p in all_positions}
    x_by_pos_rad  = {p: pos_radial[p]
                     for p in all_positions if p in pos_radial}

    for combo_name, combo_desc, combo_keys in COMBOS:
        print(f"\n  Combo [{combo_name}]: {combo_desc}")

        for metric in ('resolution', 'mean', 'sigma'):
            metric_title = metric.capitalize()

            _plot_single(
                combo_keys, scan_data, metric,
                x_by_pos_idx,
                xlabel   = 'CLS position index',
                title    = (f"RUN{run} CLS Scan — {combo_desc}\n"
                            f"{metric_title} vs CLS position"),
                out_path = os.path.join(
                    output_dir,
                    f"{combo_name}_{metric}_vs_position.png"),
            )

            if x_by_pos_rad:
                _plot_single(
                    combo_keys, scan_data, metric,
                    x_by_pos_rad,
                    xlabel   = 'Radial distance from detector centre [mm]',
                    title    = (f"RUN{run} CLS Scan — {combo_desc}\n"
                                f"{metric_title} vs radial distance"),
                    out_path = os.path.join(
                        output_dir,
                        f"{combo_name}_{metric}_vs_radius.png"),
                )


# ============================================================================
# Results table (written to log via stdout)
# ============================================================================

def print_scan_table(scan_data, pos_map=None, pos_radial=None, run=None):
    """
    Print a per-pipeline results table to stdout (captured by the log file).

    Columns (12 total):
      mean_val   mean_err   mean_err_stat   mean_err_sys
      sigma_val  sigma_err  sigma_err_stat  sigma_err_sys
      res_val    res_err    res_err_stat    res_err_sys

    Final row = average over all positions with valid fits.
    An optional 'radius [mm]' column is appended when pos_radial is supplied.
    """
    if pos_map is None:
        pos_map = CLS_POS_RTRAW_FILES

    # column widths
    W_POS  = 8
    W_VAL  = 10
    W_ERR  = 10
    SEP    = "  "

    # header pieces
    def _hdr(label):
        return (f"{label+' val':>{W_VAL}}{SEP}"
                f"{'tot err':>{W_ERR}}{SEP}"
                f"{'stat err':>{W_ERR}}{SEP}"
                f"{'sys err':>{W_ERR}}")

    header = (f"{'pos':>{W_POS}}{SEP}"
              + _hdr("mean [PE]") + SEP
              + _hdr("sigma [PE]") + SEP
              + _hdr("res [%]"))
    if pos_radial:
        header += f"{SEP}{'radius[mm]':>10}"

    divider = "-" * len(header)

    for pipe_key in PIPELINES:
        pdata = scan_data.get(pipe_key, {})
        if not pdata:
            continue

        print()
        print("=" * len(header))
        label = PIPELINES[pipe_key]['label']
        run_str = f"  RUN{run}" if run is not None else ""
        print(f"  Pipeline: {pipe_key}  ({label}){run_str}")
        print("=" * len(header))
        print(header)
        print(divider)

        # accumulators for average row
        acc = {k: [] for k in (
            'mean_val',  'mean_err',  'mean_err_stat',  'mean_err_sys',
            'sigma_val', 'sigma_err', 'sigma_err_stat', 'sigma_err_sys',
            'resolution_val', 'resolution_err',
            'resolution_err_stat', 'resolution_err_sys',
        )}

        for pos in sorted(pos_map.keys()):
            m = pdata.get(pos)
            if m is None or m.get('resolution_val', -1) <= 0:
                rad_str = ""
                if pos_radial:
                    r = pos_radial.get(pos)
                    rad_str = f"{SEP}{r:>10.1f}" if r is not None else f"{SEP}{'---':>10}"
                print(f"{'pos '+str(pos):>{W_POS}}{SEP}"
                      f"{'---':>{W_VAL}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}"
                      f"{'---':>{W_VAL}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}"
                      f"{'---':>{W_VAL}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}"
                      + rad_str)
                continue

            mv  = m.get('mean_val',           0.0)
            me  = m.get('mean_err',            0.0)
            mes = m.get('mean_err_stat',       me)
            mey = m.get('mean_err_sys',        0.0)
            sv  = m.get('sigma_val',           0.0)
            se  = m.get('sigma_err',           0.0)
            ses = m.get('sigma_err_stat',      se)
            sey = m.get('sigma_err_sys',       0.0)
            rv  = m.get('resolution_val',      0.0)
            re  = m.get('resolution_err',      0.0)
            res = m.get('resolution_err_stat', re)
            rey = m.get('resolution_err_sys',  0.0)

            for k, v in (('mean_val', mv), ('mean_err', me),
                         ('mean_err_stat', mes), ('mean_err_sys', mey),
                         ('sigma_val', sv), ('sigma_err', se),
                         ('sigma_err_stat', ses), ('sigma_err_sys', sey),
                         ('resolution_val', rv), ('resolution_err', re),
                         ('resolution_err_stat', res), ('resolution_err_sys', rey)):
                acc[k].append(v)

            row = (f"{'pos '+str(pos):>{W_POS}}{SEP}"
                   f"{mv:>{W_VAL}.2f}{SEP}{me:>{W_ERR}.3f}{SEP}{mes:>{W_ERR}.3f}{SEP}{mey:>{W_ERR}.3f}{SEP}"
                   f"{sv:>{W_VAL}.2f}{SEP}{se:>{W_ERR}.3f}{SEP}{ses:>{W_ERR}.3f}{SEP}{sey:>{W_ERR}.3f}{SEP}"
                   f"{rv:>{W_VAL}.4f}{SEP}{re:>{W_ERR}.4f}{SEP}{res:>{W_ERR}.4f}{SEP}{rey:>{W_ERR}.4f}")
            if pos_radial:
                r = pos_radial.get(pos)
                row += f"{SEP}{r:>10.1f}" if r is not None else f"{SEP}{'---':>10}"
            print(row)

        # average row
        if acc['mean_val']:
            import numpy as _np
            print(divider)
            avg_row = (f"{'AVERAGE':>{W_POS}}{SEP}"
                f"{_np.mean(acc['mean_val']):>{W_VAL}.2f}{SEP}"
                f"{_np.mean(acc['mean_err']):>{W_ERR}.3f}{SEP}"
                f"{_np.mean(acc['mean_err_stat']):>{W_ERR}.3f}{SEP}"
                f"{_np.mean(acc['mean_err_sys']):>{W_ERR}.3f}{SEP}"
                f"{_np.mean(acc['sigma_val']):>{W_VAL}.2f}{SEP}"
                f"{_np.mean(acc['sigma_err']):>{W_ERR}.3f}{SEP}"
                f"{_np.mean(acc['sigma_err_stat']):>{W_ERR}.3f}{SEP}"
                f"{_np.mean(acc['sigma_err_sys']):>{W_ERR}.3f}{SEP}"
                f"{_np.mean(acc['resolution_val']):>{W_VAL}.4f}{SEP}"
                f"{_np.mean(acc['resolution_err']):>{W_ERR}.4f}{SEP}"
                f"{_np.mean(acc['resolution_err_stat']):>{W_ERR}.4f}{SEP}"
                f"{_np.mean(acc['resolution_err_sys']):>{W_ERR}.4f}")
            print(avg_row)
            print("=" * len(header))
            print(f"  n_positions = {len(acc['mean_val'])}")

    print()


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='CLS scan pipeline comparison',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--run',            type=int,   default=1344)
    parser.add_argument('--base-dir',       required=True,
                        help='Directory containing RUN{run}/ sub-folders '
                             '(i.e. .../energy_resolution)')
    parser.add_argument('--output-dir',     required=True,
                        help='Directory for PNG output plots')
    parser.add_argument('--merged-dir',     default=None,
                        help='Cache directory for merged per-position spectra '
                             '(default: <output-dir>/merged_spectra)')
    parser.add_argument('--coords-csv',     default=None,
                        help='Path to InitialP_meanQEdepP_gamma.csv')
    parser.add_argument('--verbose-fit',    action='store_true',
                        help='Print fit results for every position')
    parser.add_argument('--force-refit',    action='store_true',
                        help='Re-merge and re-fit even if cached files exist')
    args = parser.parse_args()

    merged_dir = (args.merged_dir
                  or os.path.join(args.output_dir, 'merged_spectra'))

    print("=" * 70)
    print(f"  CLS SCAN COMPARISON   RUN {args.run}")
    print("=" * 70)
    print(f"  base-dir    : {args.base_dir}")
    print(f"  output-dir  : {args.output_dir}")
    print(f"  merged-dir  : {merged_dir}")
    print(f"  coords-csv  : {args.coords_csv or '(not provided)'}")
    print(f"  verbose-fit : {args.verbose_fit}")
    print()

    pos_radial = load_cls_coordinates(args.coords_csv)

    print("\nLoading / fitting per-position spectra ...")
    scan_data = build_scan_data(
        base_dir          = args.base_dir,
        run               = args.run,
        merged_dir        = merged_dir,
        verbose           = args.verbose_fit,
    )

    # Quick summary of fit success
    print("\nFit summary:")
    for pk in PIPELINES:
        n_good = sum(
            1 for m in scan_data.get(pk, {}).values()
            if m.get('resolution_val', -1) > 0
        )
        print(f"  {pk:20s}: {n_good}/{len(CLS_POS_RTRAW_FILES)} positions")

    print("\nResults table (mean / sigma / resolution  x  val / tot-err / stat-err / sys-err):")
    print_scan_table(
        scan_data  = scan_data,
        pos_map    = CLS_POS_RTRAW_FILES,
        pos_radial = pos_radial,
        run        = args.run,
    )

    print("\nGenerating plots ...")
    produce_all_plots(
        scan_data  = scan_data,
        output_dir = args.output_dir,
        pos_radial = pos_radial,
        run        = args.run,
    )

    total = sum(1 for f in os.listdir(args.output_dir) if f.endswith('.png'))
    print()
    print("=" * 70)
    print(f"  DONE — {total} plots written to {args.output_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()
