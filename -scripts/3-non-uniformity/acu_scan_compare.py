#!/usr/bin/env python3
"""
acu_scan_compare.py  –  ACU Ge-68 z-scan pipeline comparison

Produces plots of energy resolution / mean / sigma
  • vs ACU z-position [mm]

Five pipeline combinations (a–e) × 3 metrics = 15 PNG files.

Run list (Ge-68 on ACU, z-axis scan):
  RUN1296  – Ge-68 centre  (power-off, z=0 mm)
  RUN1297  – Ge-68 at +880 mm  (power-on)
  ...
  RUN1341  – Ge-68 at -880 mm  (power-on)

Pipeline keys:
  rtraw_default  – RTRAW with default calibration
  rtraw_custom   – RTRAW with custom calibration (RUN1319 as reference)
  esd_pesum      – ESD noradialcut pesumbasic
  esd_pesumg     – ESD noradialcut pesumg

Each pipeline directory is named:
  {run}_{pipeline}_Ge68_{timestamp}
and the latest timestamp is selected automatically.

Usage:
  python acu_scan_compare.py \\
      --base-dir   /path/to/energy_resolution \\
      --output-dir ./acu_scan_output

Optional:
  --merged-dir   /path/to/cached/merged/spectra   (default: <output-dir>/merged_spectra)
  --calib-run    1319                              (run used for rtraw_custom, default 1319)
  --verbose-fit        print gaus+pol3 fit results for every run
  --force-refit        re-merge and re-fit even if cached files exist

Fit model:
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
import glob
import os
import shutil
import subprocess
import tempfile

ROOT.gROOT.SetBatch(True)

# ============================================================================
# ACU run list: run_number → (z_position_mm, label, power_on)
# ============================================================================
ACU_RUNS = {
    1296: (   0, 'centre (power-off)', False),
    1297: ( 880, '+880 mm', True),
    1298: ( 840, '+840 mm', True),
    1299: ( 800, '+800 mm', True),
    1300: ( 760, '+760 mm', True),
    1301: ( 720, '+720 mm', True),
    1302: ( 680, '+680 mm', True),
    1303: ( 640, '+640 mm', True),
    1304: ( 600, '+600 mm', True),
    1305: ( 560, '+560 mm', True),
    1306: ( 520, '+520 mm', True),
    1307: ( 480, '+480 mm', True),
    1308: ( 440, '+440 mm', True),
    1309: ( 400, '+400 mm', True),
    1310: ( 360, '+360 mm', True),
    1311: ( 320, '+320 mm', True),
    1312: ( 280, '+280 mm', True),
    1313: ( 240, '+240 mm', True),
    1314: ( 200, '+200 mm', True),
    1315: ( 160, '+160 mm', True),
    1316: ( 120, '+120 mm', True),
    1317: (  80, '+80 mm', True),
    1318: (  40, '+40 mm', True),
    1319: (   0, '0 mm (power-on)', True),
    1320: ( -40, '-40 mm', True),
    1321: ( -80, '-80 mm', True),
    1322: (-120, '-120 mm', True),
    1323: (-160, '-160 mm', True),
    1324: (-200, '-200 mm', True),
    1325: (-240, '-240 mm', True),
    1326: (-280, '-280 mm', True),
    1327: (-320, '-320 mm', True),
    1328: (-360, '-360 mm', True),
    1329: (-400, '-400 mm', True),
    1330: (-440, '-440 mm', True),
    1331: (-480, '-480 mm', True),
    1332: (-520, '-520 mm', True),
    1333: (-560, '-560 mm', True),
    1334: (-600, '-600 mm', True),
    1335: (-640, '-640 mm', True),
    1336: (-680, '-680 mm', True),
    1337: (-720, '-720 mm', True),
    1338: (-760, '-760 mm', True),
    1339: (-800, '-800 mm', True),
    1340: (-840, '-840 mm', True),
    1341: (-880, '-880 mm', True),
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
        'pattern': 'rtraw_run{calib_run}',
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
# Gaussian + polynomial background fitting on ROOT TH1
# ============================================================================

def _systematic_fit_study(hist, method_name, dark_noise_pe):
    """
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
            fname   = f"f_acu_{safe_name}_{lo}_{hi}_pol{deg}"
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
        'sigma_sys':      float(np.std(sigmas,      ddof=1)),
        'mean_sys':       float(np.std(means,        ddof=1)),
        'resolution_sys': float(np.std(resolutions,  ddof=1)),
        'n_fits':         len(results),
    }


def _fit_gaus_pol3(hist, dark_noise_pe, verbose=False):
    """
    Fit Gaussian + pol3 background on a ROOT TH1.
    Returns a metrics dict or None on failure.
    """
    if hist is None or hist.GetEntries() < 10:
        return None

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
    sigma_estimate = max(sigma_estimate, 10.0)

    fit_min = peak_center - 7.0 * sigma_estimate
    fit_max = peak_center + 6.0 * sigma_estimate

    fname = f"f_acu_main_{id(hist)}"
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

    resolution     = sigma / denom
    resolution_err = resolution * np.sqrt(
        (sigma_err / sigma) ** 2 + (mean_err / denom) ** 2
    )

    if verbose:
        print(f"        gaus+pol3 fit: mean={mean:.1f}±{mean_err:.1f}  "
              f"sigma={sigma:.1f}±{sigma_err:.1f}  "
              f"res={100*resolution:.3f}%  DN={dark_noise_pe:.1f}")

    sys = _systematic_fit_study(hist, fname, dark_noise_pe)
    sys_res_frac = sys.get('resolution_sys', 0.0) / 100.0
    sys_mu       = sys.get('mean_sys',       0.0)
    sys_sig      = sys.get('sigma_sys',      0.0)

    res_tot   = float(np.sqrt(resolution_err**2  + sys_res_frac**2))
    mu_tot    = float(np.sqrt(mean_err**2         + sys_mu**2))
    sigma_tot = float(np.sqrt(sigma_err**2        + sys_sig**2))

    return dict(
        resolution_val      = resolution * 100.0,
        resolution_err      = res_tot    * 100.0,
        resolution_err_stat = resolution_err * 100.0,
        resolution_err_sys  = sys_res_frac   * 100.0,
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
    Open a spectrum ROOT file and return a metric dict.

    Step 1 – read pre-computed values from energy_info TNamed (fast path).
    Step 2 – if all stored values are ≤ 0, fit gaus+pol3 on h_PEdiscrete
             (or h_PEcontin as fallback) + run systematic study.

    Returns dict or None on failure.
    """
    try:
        f = ROOT.TFile.Open(root_file, "READ")
        if not f or f.IsZombie():
            return None

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

        dn_obj = f.Get("dark_noise_pe")
        dark_noise_pe = 0.0
        if dn_obj:
            try:
                dark_noise_pe = float(dn_obj.GetTitle())
            except Exception:
                dark_noise_pe = raw.get('DARK_NOISE_PE', 0.0)
        else:
            dark_noise_pe = raw.get('DARK_NOISE_PE', 0.0)

        res_stored = raw.get('RES_PE', -1.0)
        if res_stored > 0:
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

        # Fallback: re-fit from histogram
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

        hist_clone = hist.Clone(f"h_fit_acu_{id(hist)}")
        hist_clone.SetDirectory(0)
        f.Close()

        return _fit_gaus_pol3(hist_clone, dark_noise_pe, verbose=verbose)

    except Exception as e:
        print(f"      ERROR in extract_metrics({os.path.basename(root_file)}): {e}")
        return None


# ============================================================================
# Utility: find pipeline directory (latest timestamp wins)
# ============================================================================

def find_pipeline_dir(base_dir, run, pattern):
    """
    Find the latest directory matching:
        {base_dir}/RUN{run}/{run}_{pattern}_Ge68_*
    Returns the path string or None.
    """
    hits = sorted(
        glob.glob(os.path.join(base_dir, f"RUN{run}", f"{run}_{pattern}_Ge68_*")),
        reverse=True,
    )
    return hits[0] if hits else None


def find_spectrum_files(pipeline_dir, run):
    """
    Return all spectrum ROOT files inside pipeline_dir for the given run.
    """
    return sorted(glob.glob(
        os.path.join(pipeline_dir, f"spectrum_RUN{run}-*.root")
    ))


# ============================================================================
# Merging (with caching)
# ============================================================================

def merge_spectra(input_files, output_file, force_refit=False):
    """
    Merge multiple spectrum ROOT files with hadd (or merge_spectrum.py).
    If output_file already exists it is reused (cached) unless force_refit.
    Returns True on success.
    """
    if os.path.exists(output_file) and not force_refit:
        return True

    if not input_files:
        return False

    if len(input_files) == 1:
        shutil.copy2(input_files[0], output_file)
        return os.path.exists(output_file)

    # Try merge_spectrum.py first
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

    # Fallback: hadd
    try:
        subprocess.run(
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

def build_scan_data(base_dir, merged_dir, calib_run=1319,
                    verbose=False, force_refit=False):
    """
    For every pipeline × every ACU run:
      1. Locate spectrum ROOT file(s) in the pipeline directory.
      2. Merge if needed (single-file → plain copy; cached in merged_dir).
      3. Extract / fit metrics.

    Returns:
        {pipe_key: {run: {resolution_val, resolution_err,
                          mean_val,       mean_err,
                          sigma_val,      sigma_err, z_mm}}}
    """
    os.makedirs(merged_dir, exist_ok=True)
    scan_data = {pk: {} for pk in PIPELINES}

    for pipe_key, pipe_cfg in PIPELINES.items():
        pat_tmpl = pipe_cfg['pattern'].replace('{calib_run}', str(calib_run))

        print(f"\n  Pipeline: {pipe_key}")

        n_ok = 0
        for run in sorted(ACU_RUNS.keys()):
            z_mm, lbl, power_on = ACU_RUNS[run]

            pipe_dir = find_pipeline_dir(base_dir, run, pat_tmpl)
            if pipe_dir is None:
                print(f"    RUN{run} ({lbl:>18s}): [SKIP] no directory matching "
                      f"RUN{run}/{run}_{pat_tmpl}_Ge68_*")
                continue

            ind_files = find_spectrum_files(pipe_dir, run)
            if not ind_files:
                print(f"    RUN{run} ({lbl:>18s}): no spectrum files in "
                      f"{os.path.basename(pipe_dir)}")
                continue

            # Cached merged / single-file output path
            safe_pat  = pat_tmpl.replace('/', '_')
            fname     = f"spectrum_RUN{run}_{safe_pat}.root"
            merged_fp = os.path.join(merged_dir, fname)

            ok = merge_spectra(ind_files, merged_fp, force_refit=force_refit)
            if not ok:
                print(f"    RUN{run} ({lbl:>18s}): merge FAILED")
                continue

            metrics = extract_metrics(merged_fp, verbose=verbose)
            if metrics is None:
                print(f"    RUN{run} ({lbl:>18s}): fit FAILED")
                continue

            metrics['z_mm']     = z_mm
            metrics['power_on'] = power_on
            scan_data[pipe_key][run] = metrics
            n_ok += 1

            if verbose:
                print(f"    RUN{run} ({lbl:>18s}): "
                      f"res={metrics['resolution_val']:.3f}%"
                      f"±{metrics['resolution_err']:.3f}%  "
                      f"mean={metrics['mean_val']:.1f}  "
                      f"sigma={metrics['sigma_val']:.1f}")

        print(f"    → {n_ok}/{len(ACU_RUNS)} runs fitted successfully")

    return scan_data


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


def _plot_single(combo_keys, scan_data, metric, title, out_path):
    """
    Plot one metric vs z-position for the given pipeline combination.
    Only power-on runs are shown (RUN1296 power-off is excluded).
    """
    fig, ax = plt.subplots()
    has_data = False

    for pipe_key in combo_keys:
        pdata = scan_data.get(pipe_key, {})
        sty   = PIPE_STYLE[pipe_key]
        lbl   = PIPELINES[pipe_key]['label']

        xs, ys, es = [], [], []

        for run in sorted(pdata, key=lambda r: pdata[r]['z_mm']):
            m = pdata[run]
            if not m.get('power_on', True):
                continue          # skip power-off run (RUN1296)
            val = m.get(f'{metric}_val', -1.0)
            err = m.get(f'{metric}_err',  0.0)
            if val <= 0:
                continue
            xs.append(m['z_mm']); ys.append(val); es.append(err)

        if xs:
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

    ax.set_xlabel('ACU z-position [mm]',   fontsize=12, fontweight='bold')
    ax.set_ylabel(METRIC_YLABEL[metric],    fontsize=12, fontweight='bold')
    ax.set_title(title,                     fontsize=13, fontweight='bold')
    ax.axvline(0, color='grey', lw=0.8, ls=':', alpha=0.6, label='z = 0')
    ax.legend(loc='best', frameon=True, fancybox=True, shadow=True)
    ax.grid(alpha=0.35)
    plt.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"    ✓  {os.path.basename(out_path)}")


def produce_all_plots(scan_data, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for combo_name, combo_desc, combo_keys in COMBOS:
        print(f"\n  Combo [{combo_name}]: {combo_desc}")

        for metric in ('resolution', 'mean', 'sigma'):
            metric_title = metric.capitalize()

            _plot_single(
                combo_keys, scan_data, metric,
                title    = (f"ACU Ge-68 z-Scan — {combo_desc}\n"
                            f"{metric_title} vs z-position"),
                out_path = os.path.join(
                    output_dir,
                    f"{combo_name}_{metric}_vs_z.png"),
            )


# ============================================================================
# Results table (written to log via stdout)
# ============================================================================

def print_scan_table(scan_data):
    """
    Print a per-pipeline results table to stdout (captured by the log file).

    Rows   = ACU runs, ordered by z-position (most positive first).
    Columns (12 values + z_mm + run label):
      mean_val   mean_err   mean_err_stat   mean_err_sys
      sigma_val  sigma_err  sigma_err_stat  sigma_err_sys
      res_val    res_err    res_err_stat    res_err_sys

    Final row = average over all runs with valid fits.
    """
    import numpy as _np

    W_RUN  = 16   # "RUN1297 +880mm"
    W_VAL  = 10
    W_ERR  = 10
    SEP    = "  "

    def _hdr(label):
        return (f"{label+' val':>{W_VAL}}{SEP}"
                f"{'tot err':>{W_ERR}}{SEP}"
                f"{'stat err':>{W_ERR}}{SEP}"
                f"{'sys err':>{W_ERR}}")

    header = (f"{'run / z':>{W_RUN}}{SEP}"
              + _hdr("mean [PE]") + SEP
              + _hdr("sigma [PE]") + SEP
              + _hdr("res [%]"))
    divider = "-" * len(header)

    for pipe_key in PIPELINES:
        pdata = scan_data.get(pipe_key, {})
        if not pdata:
            continue

        print()
        print("=" * len(header))
        label = PIPELINES[pipe_key]['label']
        print(f"  Pipeline: {pipe_key}  ({label})")
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

        # sort runs by z_mm descending (+880 → -880)
        sorted_runs = sorted(
            ACU_RUNS.keys(),
            key=lambda r: ACU_RUNS[r][0],
            reverse=True,
        )

        for run in sorted_runs:
            z_mm, lbl, _ = ACU_RUNS[run]
            row_label = f"RUN{run} {z_mm:+d}mm"

            m = pdata.get(run)
            if m is None or m.get('resolution_val', -1) <= 0:
                print(f"{row_label:>{W_RUN}}{SEP}"
                      + (f"{'---':>{W_VAL}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}{'---':>{W_ERR}}{SEP}" * 3).rstrip(SEP))
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

            print(f"{row_label:>{W_RUN}}{SEP}"
                  f"{mv:>{W_VAL}.2f}{SEP}{me:>{W_ERR}.3f}{SEP}{mes:>{W_ERR}.3f}{SEP}{mey:>{W_ERR}.3f}{SEP}"
                  f"{sv:>{W_VAL}.2f}{SEP}{se:>{W_ERR}.3f}{SEP}{ses:>{W_ERR}.3f}{SEP}{sey:>{W_ERR}.3f}{SEP}"
                  f"{rv:>{W_VAL}.4f}{SEP}{re:>{W_ERR}.4f}{SEP}{res:>{W_ERR}.4f}{SEP}{rey:>{W_ERR}.4f}")

        # average row
        if acc['mean_val']:
            print(divider)
            print(f"{'AVERAGE':>{W_RUN}}{SEP}"
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
            print("=" * len(header))
            print(f"  n_runs = {len(acc['mean_val'])}")

    print()


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ACU Ge-68 z-scan pipeline comparison',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--base-dir',    required=True,
                        help='Directory containing RUN{run}/ sub-folders '
                             '(i.e. .../energy_resolution)')
    parser.add_argument('--output-dir',  required=True,
                        help='Directory for PNG output plots')
    parser.add_argument('--merged-dir',  default=None,
                        help='Cache directory for merged per-run spectra '
                             '(default: <output-dir>/merged_spectra)')
    parser.add_argument('--calib-run',   type=int, default=1319,
                        help='Run number used for rtraw_custom calibration '
                             '(default: 1319, i.e. Ge-68 at z=0 power-on)')
    parser.add_argument('--verbose-fit', action='store_true',
                        help='Print fit results for every run')
    parser.add_argument('--force-refit', action='store_true',
                        help='Re-merge and re-fit even if cached files exist')
    args = parser.parse_args()

    merged_dir = (args.merged_dir
                  or os.path.join(args.output_dir, 'merged_spectra'))

    print("=" * 70)
    print("  ACU Ge-68 Z-SCAN COMPARISON")
    print("=" * 70)
    print(f"  base-dir    : {args.base_dir}")
    print(f"  output-dir  : {args.output_dir}")
    print(f"  merged-dir  : {merged_dir}  (cached; safe to delete to re-merge)")
    print(f"  calib-run   : {args.calib_run}  (rtraw_custom reference)")
    print(f"  verbose-fit : {args.verbose_fit}")
    print(f"  force-refit : {args.force_refit}")
    print(f"  runs        : {len(ACU_RUNS)}  (RUN1296–RUN1341)")
    print()

    print("Loading / fitting per-run spectra ...")
    scan_data = build_scan_data(
        base_dir    = args.base_dir,
        merged_dir  = merged_dir,
        calib_run   = args.calib_run,
        verbose     = args.verbose_fit,
        force_refit = args.force_refit,
    )

    print("\nFit summary:")
    for pk in PIPELINES:
        n_good = sum(
            1 for m in scan_data.get(pk, {}).values()
            if m.get('resolution_val', -1) > 0
        )
        print(f"  {pk:20s}: {n_good}/{len(ACU_RUNS)} runs")

    print("\nResults table (mean / sigma / resolution  x  val / tot-err / stat-err / sys-err):")
    print_scan_table(scan_data)

    print("\nGenerating plots ...")
    produce_all_plots(
        scan_data  = scan_data,
        output_dir = args.output_dir,
    )

    total = sum(1 for f in os.listdir(args.output_dir) if f.endswith('.png'))
    print()
    print("=" * 70)
    print(f"  DONE — {total} plots written to {args.output_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()
