#!/usr/bin/env python3
# Force ROOT batch mode before any import can trigger display initialisation.
# This must be the very first executable code in the file.
import os as _os
_os.environ.setdefault("DISPLAY", "")          # no X11
_os.environ["ROOT_BATCH"] = "1"               # ROOT batch env flag
try:
    import ROOT as _ROOT
    _ROOT.gROOT.SetBatch(True)
    _ROOT.gROOT.ProcessLine("gErrorIgnoreLevel = kError;")
except Exception:
    pass

"""
tao_nu_pipeline.py  —  TAO Non-Uniformity Master Pipeline

Chains all analysis steps in one call:

  Step 1  channel_qt_plots.py   — TDC-ADC diagnostic plots (optional, slow)
  Step 2  acu_scan_compare.py   — ACU Ge-68 z-scan pipeline comparison
          (15 PNG: 5 combos × 3 metrics)
  Step 3  cls_scan_compare.py   — CLS Cs-137 scan pipeline comparison
          (30 PNG: 5 combos × 3 metrics × 2 axes)
  Step 4  fit_peaks_ge68.py     — Physics-model Ge-68 fits on merged spectra
  Step 5  fit_peaks_cs137.py    — Physics-model Cs-137 fits on merged spectra
  Step 6  ly_extractor.py       — Light-yield extraction → g(r,θ) table
  Step 7  nu_map.py             — Non-uniformity maps, shells, deviation plots

Each step saves its outputs under --output-root/<step_name>/
and produces a log file.  A step is skipped if its primary output
already exists (use --force to override).

Usage (typical run on CNAF or IHEP):
  python tao_nu_pipeline.py \\
      --base-dir   /path/to/energy_resolution \\
      --coords-csv /path/to/InitialP_meanQEdepP_gamma.csv \\
      --output-root /path/to/pipeline_output

Cluster path defaults are auto-detected (same logic as launch_*.sh).

Author: G. Ferrante
"""

import argparse
import csv
import importlib.util
import json
import os
import subprocess
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.interpolate import griddata

# ─────────────────────────────────────────────────────────────────────────────
# Cluster detection & default paths
# ─────────────────────────────────────────────────────────────────────────────

def _detect_cluster():
    if os.path.isdir("/storage/gpfs_data/juno"):
        return "CNAF"
    if os.path.isdir("/junofs/users/gferrante"):
        return "IHEP"
    return "LOCAL"


_CLUSTER_DEFAULTS = {
    "CNAF": {
        "scripts_base": "/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum",
        "base_dir": "/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/energy_resolution",
        "output_root": "/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/pipeline_output",
        "coords_csv": "/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/ACU_CLS/InitialP_meanQEdepP_gamma.csv",
    },
    "IHEP": {
        "scripts_base": "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum",
        "base_dir": "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/energy_resolution",
        "output_root": "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/pipeline_output",
        "coords_csv": "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/ACU_CLS/InitialP_meanQEdepP_gamma.csv",
    },
    "LOCAL": {
        "scripts_base": os.path.dirname(os.path.abspath(__file__)),
        "base_dir": "./energy_resolution",
        "output_root": "./pipeline_output",
        "coords_csv": "./InitialP_meanQEdepP_gamma.csv",
    },
}

# ACU and CLS run configuration
ACU_CALIB_RUN = 1319   # Ge-68 z=0 power-on reference
CLS_RUN       = 1344   # Cs-137 CLS scan run


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log(msg, indent=0):
    prefix = "  " * indent
    print(f"{prefix}{msg}", flush=True)


def _section(title):
    bar = "=" * 62
    print()
    print(bar)
    print(f"  {title}")
    print(bar)


def _find_script(script_name, scripts_base):
    """Find a script file relative to this file or scripts_base."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name),
        os.path.join(scripts_base, script_name),
        script_name,
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _import_module(script_path, module_name):
    """
    Import a Python script as a module by path.
    Uses a path-derived unique name so that a stale version already loaded by
    the JUNO environment (e.g. an older acu_scan_compare in sys.modules) can
    never shadow the file we actually want to import.
    """
    import sys
    unique_name = "_pipeline_{}_{}".format(module_name, abs(hash(script_path)))
    sys.modules.pop(unique_name, None)   # drop any stale cached version
    spec   = importlib.util.spec_from_file_location(unique_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module    # register before exec (handles circular refs)
    spec.loader.exec_module(module)
    return module


def _run_step(step_name, func, args_dict, primary_output, force=False):
    """
    Run one pipeline step.  Skips if primary_output exists and not force.
    Measures wall time.  Returns True on success, False on failure.
    """
    _section(f"STEP: {step_name}")
    if os.path.exists(primary_output) and not force:
        _log(f"OUTPUT EXISTS — skipping  ({primary_output})")
        _log("Use --force to re-run this step.", 1)
        return True

    t0 = time.time()
    try:
        func(**args_dict)
        elapsed = time.time() - t0
        _log(f"✓  Done in {elapsed:.0f}s")
        return True
    except SystemExit as e:
        if e.code == 0:
            return True
        _log(f"✗  Step failed (SystemExit {e.code})")
        return False
    except Exception as exc:
        import traceback
        _log(f"✗  Step failed: {exc}")
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Individual step wrappers
# ─────────────────────────────────────────────────────────────────────────────

def step_acu_scan_compare(scripts_base, base_dir, output_dir,
                          merged_dir, calib_run, force_refit=False, verbose=False):
    script = _find_script("acu_scan_compare.py", scripts_base)
    if script is None:
        raise FileNotFoundError("acu_scan_compare.py not found")

    mod = _import_module(script, "acu_scan_compare")
    scan_data = mod.build_scan_data(
        base_dir    = base_dir,
        merged_dir  = merged_dir,
        calib_run   = calib_run,
        verbose     = verbose,
        force_refit = force_refit,
    )
    if hasattr(mod, 'print_scan_table'):
        mod.print_scan_table(scan_data)
    mod.produce_all_plots(scan_data=scan_data, output_dir=output_dir)

    # Save scan_data as JSON for downstream steps
    json_path = os.path.join(output_dir, "acu_scan_data.json")
    serialisable = {}
    for pk, pdata in scan_data.items():
        serialisable[pk] = {str(run): v for run, v in pdata.items()}
    with open(json_path, "w") as jf:
        json.dump(serialisable, jf, indent=2)
    _log(f"Scan data cached → {json_path}", 1)


def step_cls_scan_compare(scripts_base, base_dir, output_dir,
                          merged_dir, run, coords_csv, verbose=False):
    script = _find_script("cls_scan_compare.py", scripts_base)
    if script is None:
        raise FileNotFoundError("cls_scan_compare.py not found")

    mod = _import_module(script, "cls_scan_compare")
    pos_radial = mod.load_cls_coordinates(coords_csv)
    scan_data  = mod.build_scan_data(
        base_dir   = base_dir,
        run        = run,
        merged_dir = merged_dir,
        verbose    = verbose,
    )
    if hasattr(mod, 'print_scan_table'):
        mod.print_scan_table(scan_data, pos_radial=pos_radial, run=run)
    mod.produce_all_plots(scan_data=scan_data, output_dir=output_dir,
                          pos_radial=pos_radial, run=run)

    json_path = os.path.join(output_dir, "cls_scan_data.json")
    with open(json_path, "w") as jf:
        json.dump({pk: {str(p): v for p, v in pd.items()}
                   for pk, pd in scan_data.items()}, jf, indent=2)
    _log(f"Scan data cached → {json_path}", 1)


# ─────────────────────────────────────────────────────────────────────────────
# ACU run → z_mm lookup (mirrors acu_scan_compare.py)
# ─────────────────────────────────────────────────────────────────────────────
ACU_Z_MAP = {
    1296: 0,    1297: 880,  1298: 840,  1299: 800,  1300: 760,
    1301: 720,  1302: 680,  1303: 640,  1304: 600,  1305: 560,
    1306: 520,  1307: 480,  1308: 440,  1309: 400,  1310: 360,
    1311: 320,  1312: 280,  1313: 240,  1314: 200,  1315: 160,
    1316: 120,  1317: 80,   1318: 40,   1319: 0,    1320: -40,
    1321: -80,  1322: -120, 1323: -160, 1324: -200, 1325: -240,
    1326: -280, 1327: -320, 1328: -360, 1329: -400, 1330: -440,
    1331: -480, 1332: -520, 1333: -560, 1334: -600, 1335: -640,
    1336: -680, 1337: -720, 1338: -760, 1339: -800, 1340: -840,
    1341: -880,
}
E_GE68_MEV  = 1.022
E_CS137_MEV = 0.6617

# Preferred pipeline order for the summary colormaps
_PIPE_PREFERENCE = ["esd_pesum", "rtraw_default", "rtraw_custom", "esd_pesumg"]


def _pick_pipeline(scan_data):
    """Return the best available pipeline key from scan_data."""
    for pk in _PIPE_PREFERENCE:
        if scan_data.get(pk):
            return pk
    available = [pk for pk, v in scan_data.items() if v]
    return available[0] if available else None


def _ly_from_metrics(m, e_mev):
    """
    Derive light yield [PE/MeV] from a scan-data metrics dict.
    Uses the identity: mean_net = sigma / (resolution/100)
    (exact from the definition res = sigma/(mean-DN) × 100)
    so LY = mean_net / E_MeV, with no need for DN.
    """
    res = m.get("resolution_val", 0.0)
    sig = m.get("sigma_val",      0.0)
    if res <= 0 or sig <= 0:
        return 0.0, 0.0
    mean_net  = sig / (res / 100.0)
    ly        = mean_net / e_mev

    res_err = m.get("resolution_err", 0.0)
    sig_err = m.get("sigma_err",      0.0)
    ly_err  = ly * np.sqrt((sig_err / sig) ** 2 + (res_err / res) ** 2) if ly > 0 else 0.0
    return ly, ly_err


def _load_cls_coords(coords_csv):
    """Return dict: pos_index → (r_mm, theta_rad)"""
    coords = {}
    if not coords_csv or not os.path.exists(coords_csv):
        return coords
    with open(coords_csv, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                idx   = int(row["PointIndex"])
                x, y, z = float(row["initX"]), float(row["initY"]), float(row["initZ"])
                r     = float(np.sqrt(x**2 + y**2 + z**2))
                theta = float(np.arccos(z / r)) if r > 0 else 0.0
                coords[idx] = (r, theta)
            except (KeyError, ValueError, ZeroDivisionError):
                pass
    return coords


# ─── plotting helpers ──────────────────────────────────────────────────────

_METRIC_LABELS = {
    "mean":       r"Peak Mean $(\mu - \mathrm{DN})$ [PE]",
    "sigma":      r"Peak Sigma $\sigma$ [PE]",
    "resolution": r"Energy Resolution $\sigma/(\mu-\mathrm{DN})$ [%]",
    "ly":         r"Light Yield [PE/MeV]",
}
_METRIC_CMAPS = {
    "mean":       "viridis",
    "sigma":      "plasma",
    "resolution": "RdYlGn_r",
    "ly":         "RdYlGn",
}


def _plot_metric_vs_z(zs, vals, errs, metric, pipe_label, output_path, e_src="Ge-68"):
    """LY or mean/sigma/resolution vs z (ACU on-axis)."""
    order = np.argsort(zs)
    zs, vals, errs = zs[order], vals[order], errs[order]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.errorbar(zs, vals, yerr=errs, fmt="o-", color="#1f77b4",
                ms=5, lw=1.8, capsize=3, capthick=1.5)
    ax.set_xlabel("ACU z-position [mm]", fontsize=12, fontweight="bold")
    ax.set_ylabel(_METRIC_LABELS[metric], fontsize=12, fontweight="bold")
    ax.set_title(f"ACU {e_src} z-scan — {_METRIC_LABELS[metric]}\n"
                 f"pipeline: {pipe_label}", fontsize=12)
    ax.axvline(0, color="grey", lw=0.8, ls=":", alpha=0.6)
    ax.grid(alpha=0.35)
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    ✓  {os.path.basename(output_path)}")


def _plot_metric_vs_radius(rs, vals, errs, metric, pipe_label, output_path, e_src="Cs-137"):
    """LY or mean/sigma/resolution vs radial distance (CLS)."""
    order = np.argsort(rs)
    rs, vals, errs = rs[order], vals[order], errs[order]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.errorbar(rs, vals, yerr=errs, fmt="s-", color="#d62728",
                ms=5, lw=1.8, capsize=3, capthick=1.5)
    ax.set_xlabel("Radial distance from centre [mm]", fontsize=12, fontweight="bold")
    ax.set_ylabel(_METRIC_LABELS[metric], fontsize=12, fontweight="bold")
    ax.set_title(f"CLS {e_src} scan — {_METRIC_LABELS[metric]}\n"
                 f"pipeline: {pipe_label}", fontsize=12)
    ax.grid(alpha=0.35)
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    ✓  {os.path.basename(output_path)}")


def _plot_2d_colormap(r_acu, z_acu, v_acu,
                      r_cls, th_cls, v_cls,
                      metric, pipe_label, output_path):
    """
    2D scatter + interpolated colormap in (r_perp, z) Cartesian space,
    combining ACU (on-axis) and CLS (off-axis) points.
    """
    # Convert to Cartesian (r_perp, z)
    z_cls    = r_cls * np.cos(th_cls)
    rperp_cls = r_cls * np.sin(th_cls)

    # Combine
    all_rperp = np.concatenate([np.zeros(len(r_acu)), rperp_cls])
    all_z     = np.concatenate([z_acu,                z_cls])
    all_v     = np.concatenate([v_acu,                v_cls])

    ok = all_v > 0
    if ok.sum() < 3:
        return

    rperp_ok = all_rperp[ok]
    z_ok     = all_z[ok]
    v_ok     = all_v[ok]

    # Interpolated grid
    R_MAX = 900.0
    rp_g  = np.linspace(0, R_MAX, 120)
    z_g   = np.linspace(-R_MAX, R_MAX, 200)
    Rg, Zg = np.meshgrid(rp_g, z_g)

    # Mirror: exploit azimuthal symmetry → add negative rperp
    rperp_m = np.concatenate([rperp_ok, -rperp_ok])
    z_m     = np.concatenate([z_ok,      z_ok])
    v_m     = np.concatenate([v_ok,      v_ok])

    v_interp = griddata((rperp_m, z_m), v_m, (Rg, Zg), method="cubic")

    # Mask outside vessel sphere
    outside = np.sqrt(Rg**2 + Zg**2) > R_MAX
    v_interp[outside] = np.nan

    cmap = _METRIC_CMAPS.get(metric, "viridis")
    vlo  = np.nanpercentile(v_ok, 2)
    vhi  = np.nanpercentile(v_ok, 98)
    if metric in ("resolution",):
        norm = mcolors.Normalize(vmin=vlo, vmax=vhi)
    elif metric == "ly":
        vcen = np.nanmedian(v_ok)
        norm = mcolors.TwoSlopeNorm(vmin=max(vlo, vcen*0.92),
                                    vcenter=vcen,
                                    vmax=min(vhi, vcen*1.04))
    else:
        norm = mcolors.Normalize(vmin=vlo, vmax=vhi)

    fig, ax = plt.subplots(figsize=(7, 10))
    im = ax.pcolormesh(Rg, Zg, v_interp, cmap=cmap, norm=norm, shading="auto")
    fig.colorbar(im, ax=ax, label=_METRIC_LABELS[metric], shrink=0.6, pad=0.02)

    # Overlay data points
    sc = ax.scatter(rperp_cls, z_cls, c=v_cls, cmap=cmap, norm=norm,
                    s=30, marker="s", edgecolors="k", linewidths=0.3,
                    zorder=4, label="CLS")
    ax.scatter(np.zeros(len(z_acu)), z_acu, c=v_acu, cmap=cmap, norm=norm,
               s=60, marker="*", edgecolors="k", linewidths=0.4,
               zorder=5, label="ACU")

    # Vessel boundary
    theta_v = np.linspace(0, 2*np.pi, 360)
    ax.plot(R_MAX * np.sin(theta_v), R_MAX * np.cos(theta_v),
            "k--", lw=0.8, alpha=0.4)

    ax.set_xlabel(r"$r_\perp$ [mm]", fontsize=12, fontweight="bold")
    ax.set_ylabel("z [mm]", fontsize=12, fontweight="bold")
    ax.set_title(f"{_METRIC_LABELS[metric]}\n{pipe_label}", fontsize=11)
    ax.set_aspect("equal")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.2)
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"    ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 3b: extra plots (LY + 2D colormaps) from scan-data JSONs
# ─────────────────────────────────────────────────────────────────────────────

def step_scan_extra_plots(acu_json_path, cls_json_path, coords_csv, output_dir):
    """
    Produces plots NOT generated by acu/cls_scan_compare.py:
      • LY vs z           (ACU, all pipelines + reference pipeline)
      • LY vs radius      (CLS, all pipelines + reference pipeline)
      • mean / sigma / resolution / LY vs z  (reference pipeline)
      • 2D (r_perp, z) colormaps of mean / sigma / resolution / LY
        combining ACU on-axis + CLS off-axis points
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load JSONs
    acu_data = {}
    if os.path.exists(acu_json_path):
        with open(acu_json_path) as jf:
            raw = json.load(jf)
        # keys are pipeline → {run_str → metric_dict}
        for pk, pdata in raw.items():
            acu_data[pk] = {}
            for run_str, m in pdata.items():
                run  = int(run_str)
                z_mm = m.get("z_mm", ACU_Z_MAP.get(run))
                if z_mm is None:
                    continue
                m["z_mm"] = z_mm
                acu_data[pk][run] = m

    cls_data = {}
    if os.path.exists(cls_json_path):
        with open(cls_json_path) as jf:
            raw = json.load(jf)
        for pk, pdata in raw.items():
            cls_data[pk] = {int(p): m for p, m in pdata.items()}

    coords = _load_cls_coords(coords_csv)

    if not acu_data and not cls_data:
        _log("  WARNING: no scan-data JSONs found — skipping extra plots", 1)
        return

    pipe_key = _pick_pipeline(acu_data) or _pick_pipeline(cls_data)
    if pipe_key is None:
        _log("  WARNING: all pipelines empty — skipping extra plots", 1)
        return

    pipe_label = pipe_key.replace("_", " ")
    _log(f"  Extra plots using reference pipeline: {pipe_key}", 1)

    # ── ACU: all metrics including LY vs z ────────────────────────────────
    for pk, pdata in acu_data.items():
        if not pdata:
            continue
        runs   = sorted(pdata.keys(), key=lambda r: pdata[r]["z_mm"])
        zs     = np.array([pdata[r]["z_mm"]         for r in runs], dtype=float)

        for metric in ("mean", "sigma", "resolution"):
            vals = np.array([pdata[r].get(f"{metric}_val", 0.0) for r in runs])
            errs = np.array([pdata[r].get(f"{metric}_err", 0.0) for r in runs])
            ok   = vals > 0
            if ok.sum() < 2:
                continue
            out = os.path.join(output_dir, f"acu_{pk}_{metric}_vs_z.png")
            _plot_metric_vs_z(zs[ok], vals[ok], errs[ok],
                              metric, pk.replace("_", " "), out)

        # LY
        ly_vals = np.array([_ly_from_metrics(pdata[r], E_GE68_MEV)[0] for r in runs])
        ly_errs = np.array([_ly_from_metrics(pdata[r], E_GE68_MEV)[1] for r in runs])
        ok = ly_vals > 0
        if ok.sum() >= 2:
            out = os.path.join(output_dir, f"acu_{pk}_ly_vs_z.png")
            _plot_metric_vs_z(zs[ok], ly_vals[ok], ly_errs[ok],
                              "ly", pk.replace("_", " "), out)

    # ── CLS: all metrics including LY vs radius ───────────────────────────
    for pk, pdata in cls_data.items():
        if not pdata:
            continue
        positions = sorted(pdata.keys())
        rs        = np.array([coords[p][0] if p in coords else 0.0
                              for p in positions], dtype=float)
        ok_coord  = rs > 0

        for metric in ("mean", "sigma", "resolution"):
            vals = np.array([pdata[p].get(f"{metric}_val", 0.0) for p in positions])
            errs = np.array([pdata[p].get(f"{metric}_err", 0.0) for p in positions])
            ok   = ok_coord & (vals > 0)
            if ok.sum() < 2:
                continue
            out = os.path.join(output_dir, f"cls_{pk}_{metric}_vs_radius.png")
            _plot_metric_vs_radius(rs[ok], vals[ok], errs[ok],
                                   metric, pk.replace("_", " "), out)

        ly_vals = np.array([_ly_from_metrics(pdata[p], E_CS137_MEV)[0] for p in positions])
        ly_errs = np.array([_ly_from_metrics(pdata[p], E_CS137_MEV)[1] for p in positions])
        ok = ok_coord & (ly_vals > 0)
        if ok.sum() >= 2:
            out = os.path.join(output_dir, f"cls_{pk}_ly_vs_radius.png")
            _plot_metric_vs_radius(rs[ok], ly_vals[ok], ly_errs[ok],
                                   "ly", pk.replace("_", " "), out)

    # ── 2D colormaps (reference pipeline, all 4 metrics) ──────────────────
    acu_ref = acu_data.get(pipe_key, {})
    cls_ref = cls_data.get(pipe_key, {})

    # ACU arrays for 2D map
    acu_runs  = sorted(acu_ref.keys(), key=lambda r: acu_ref[r]["z_mm"])
    r_acu     = np.array([abs(acu_ref[r]["z_mm"]) for r in acu_runs], dtype=float)
    z_acu     = np.array([float(acu_ref[r]["z_mm"]) for r in acu_runs], dtype=float)

    # CLS arrays for 2D map
    cls_positions = [p for p in sorted(cls_ref.keys()) if p in coords]
    r_cls  = np.array([coords[p][0] for p in cls_positions], dtype=float)
    th_cls = np.array([coords[p][1] for p in cls_positions], dtype=float)

    for metric in ("mean", "sigma", "resolution", "ly"):
        if metric == "ly":
            v_acu = np.array([_ly_from_metrics(acu_ref[r], E_GE68_MEV)[0]
                               for r in acu_runs], dtype=float)
            v_cls = np.array([_ly_from_metrics(cls_ref[p], E_CS137_MEV)[0]
                               for p in cls_positions], dtype=float)
        else:
            v_acu = np.array([acu_ref[r].get(f"{metric}_val", 0.0)
                               for r in acu_runs], dtype=float)
            v_cls = np.array([cls_ref[p].get(f"{metric}_val", 0.0)
                               for p in cls_positions], dtype=float)

        if (v_acu > 0).sum() + (v_cls > 0).sum() < 3:
            continue

        out = os.path.join(output_dir, f"2d_colormap_{metric}.png")
        _plot_2d_colormap(r_acu, z_acu, v_acu,
                          r_cls, th_cls, v_cls,
                          metric, pipe_label, out)

    n_png = sum(1 for f in os.listdir(output_dir) if f.endswith(".png"))
    _log(f"  Extra plots: {n_png} PNG → {output_dir}", 1)


def step_fit_ge68(scripts_base, merged_dir, output_dir, verbose=False):
    script = _find_script("fit_peaks_ge68.py", scripts_base)
    if script is None:
        raise FileNotFoundError("fit_peaks_ge68.py not found")

    import glob
    mod   = _import_module(script, "fit_peaks_ge68")
    files = sorted(glob.glob(os.path.join(merged_dir, "spectrum_RUN*_rtraw_default*.root")))
    if not files:
        files = sorted(glob.glob(os.path.join(merged_dir, "*.root")))
    if not files:
        raise FileNotFoundError(f"No merged spectrum files in {merged_dir}")

    _log(f"Fitting {len(files)} ACU Ge-68 spectra ...", 1)
    os.makedirs(output_dir, exist_ok=True)
    all_results        = {}
    all_simple_results = {}

    for fpath in files:
        stem   = os.path.splitext(os.path.basename(fpath))[0]

        # ── physics-model fit ─────────────────────────────────────────────────
        result = mod.fit_ge68(fpath, verbose=verbose)
        if result is None:
            continue
        result_save = {k: v for k, v in result.items() if k != "_fit_params"}
        json_p = os.path.join(output_dir, f"{stem}_ge68_fit.json")
        with open(json_p, "w") as jf:
            json.dump(result_save, jf, indent=2)
        png_p = os.path.join(output_dir, f"{stem}_ge68_fit.png")
        mod.plot_ge68_fit(fpath, result, png_p, label=stem)
        all_results[stem] = result_save

        # ── Gauss+pol3 simple fit ─────────────────────────────────────────────
        try:
            r_simple = mod.fit_ge68_simple(fpath)
            if r_simple is not None:
                r_simple_save = {k: v for k, v in r_simple.items() if k != "_fit_params"}
                json_sp = os.path.join(output_dir, f"{stem}_ge68_simple_fit.json")
                with open(json_sp, "w") as jf:
                    json.dump(r_simple_save, jf, indent=2)
                png_sp = os.path.join(output_dir, f"{stem}_ge68_simple_fit.png")
                mod.plot_ge68_simple(fpath, r_simple, png_sp, label=stem)
                all_simple_results[stem] = r_simple_save
        except Exception as exc:
            _log(f"  WARN: simple fit failed for {stem}: {exc}", 1)

    summary_path = os.path.join(output_dir, "ge68_fit_summary.json")
    with open(summary_path, "w") as jf:
        json.dump(all_results, jf, indent=2)
    _log(f"{len(all_results)}/{len(files)} fits succeeded", 1)
    _log(f"Summary → {summary_path}", 1)

    simple_summary_path = os.path.join(output_dir, "ge68_simple_fit_summary.json")
    with open(simple_summary_path, "w") as jf:
        json.dump(all_simple_results, jf, indent=2)
    _log(f"{len(all_simple_results)}/{len(files)} simple fits succeeded", 1)


def step_fit_cs137(scripts_base, merged_dir, output_dir, verbose=False):
    script = _find_script("fit_peaks_cs137.py", scripts_base)
    if script is None:
        raise FileNotFoundError("fit_peaks_cs137.py not found")

    import glob
    mod   = _import_module(script, "fit_peaks_cs137")
    files = sorted(glob.glob(os.path.join(merged_dir, "spectrum_RUN*pos*.root")))
    if not files:
        files = sorted(glob.glob(os.path.join(merged_dir, "*.root")))
    if not files:
        raise FileNotFoundError(f"No merged spectrum files in {merged_dir}")

    _log(f"Fitting {len(files)} CLS Cs-137 spectra ...", 1)
    os.makedirs(output_dir, exist_ok=True)
    all_results        = {}
    all_simple_results = {}

    for fpath in files:
        stem   = os.path.splitext(os.path.basename(fpath))[0]

        # ── physics-model fit ─────────────────────────────────────────────────
        result = mod.fit_cs137(fpath, verbose=verbose)
        if result is None:
            continue
        result_save = {k: v for k, v in result.items() if k != "_fit_params"}
        json_p = os.path.join(output_dir, f"{stem}_cs137_fit.json")
        with open(json_p, "w") as jf:
            json.dump(result_save, jf, indent=2)
        png_p = os.path.join(output_dir, f"{stem}_cs137_fit.png")
        mod.plot_cs137_fit(fpath, result, png_p, label=stem)
        all_results[stem] = result_save

        # ── Gauss+pol3 simple fit ─────────────────────────────────────────────
        try:
            r_simple = mod.fit_cs137_simple(fpath)
            if r_simple is not None:
                r_simple_save = {k: v for k, v in r_simple.items() if k != "_fit_params"}
                json_sp = os.path.join(output_dir, f"{stem}_cs137_simple_fit.json")
                with open(json_sp, "w") as jf:
                    json.dump(r_simple_save, jf, indent=2)
                png_sp = os.path.join(output_dir, f"{stem}_cs137_simple_fit.png")
                mod.plot_cs137_simple(fpath, r_simple, png_sp, label=stem)
                all_simple_results[stem] = r_simple_save
        except Exception as exc:
            _log(f"  WARN: simple fit failed for {stem}: {exc}", 1)

    summary_path = os.path.join(output_dir, "cs137_fit_summary.json")
    with open(summary_path, "w") as jf:
        json.dump(all_results, jf, indent=2)
    _log(f"{len(all_results)}/{len(files)} fits succeeded", 1)

    simple_summary_path = os.path.join(output_dir, "cs137_simple_fit_summary.json")
    with open(simple_summary_path, "w") as jf:
        json.dump(all_simple_results, jf, indent=2)
    _log(f"{len(all_simple_results)}/{len(files)} simple fits succeeded", 1)


def step_bias_plots(scripts_base, ge68_fit_dir, cs137_fit_dir,
                    acu_merged_dir, cls_merged_dir,
                    acu_scan_json, coords_csv, output_dir):
    """
    Generate physics-model vs Gauss+pol3 bias plots for ACU and CLS positions.
    Uses pre-computed *_simple_fit_summary.json if available, otherwise
    delegates on-the-fly simple fits to plot_bias_comparison.py.
    """
    script = _find_script("plot_bias_comparison.py", scripts_base)
    if script is None:
        _log("  SKIP bias plots: plot_bias_comparison.py not found", 1)
        return

    mod = _import_module(script, "plot_bias_comparison")
    os.makedirs(output_dir, exist_ok=True)

    # ── load physics summaries ────────────────────────────────────────────────
    def _load(p):
        if p and os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        return {}

    phys_ge68  = _load(os.path.join(ge68_fit_dir,  "ge68_fit_summary.json"))
    phys_cs137 = _load(os.path.join(cs137_fit_dir, "cs137_fit_summary.json"))
    simp_ge68  = _load(os.path.join(ge68_fit_dir,  "ge68_simple_fit_summary.json"))
    simp_cs137 = _load(os.path.join(cs137_fit_dir, "cs137_simple_fit_summary.json"))
    acu_scan   = _load(acu_scan_json)

    # ── run simple fits if summaries missing ──────────────────────────────────
    if phys_ge68 and not simp_ge68 and acu_merged_dir:
        _log("  Running Gauss+pol3 simple fits on Ge-68 spectra …", 1)
        ge68_script = _find_script("fit_peaks_ge68.py", scripts_base)
        if ge68_script:
            mod_ge = _import_module(ge68_script, "fit_peaks_ge68")
            simp_ge68 = mod._build_simple_summary(
                acu_merged_dir,
                mod_ge.fit_ge68_simple,
                stem_filter=lambda s: "rtraw_default" in s,
            )
            with open(os.path.join(ge68_fit_dir, "ge68_simple_fit_summary.json"), "w") as f:
                json.dump(simp_ge68, f, indent=2)

    if phys_cs137 and not simp_cs137 and cls_merged_dir:
        _log("  Running Gauss+pol3 simple fits on Cs-137 spectra …", 1)
        cs137_script = _find_script("fit_peaks_cs137.py", scripts_base)
        if cs137_script:
            mod_cs = _import_module(cs137_script, "fit_peaks_cs137")
            simp_cs137 = mod._build_simple_summary(
                cls_merged_dir,
                mod_cs.fit_cs137_simple,
                stem_filter=lambda s: "rtraw_default" in s,
            )
            with open(os.path.join(cs137_fit_dir, "cs137_simple_fit_summary.json"), "w") as f:
                json.dump(simp_cs137, f, indent=2)

    # ── build z_map for ACU ───────────────────────────────────────────────────
    acu_z_map = {}
    for stem in phys_ge68:
        rn = mod._run_number_from_stem(stem)
        if rn and acu_scan:
            z = mod._acu_z_from_scan_json(acu_scan, rn)
            if z is not None:
                acu_z_map[rn] = z

    # ── generate individual metric bias plots ─────────────────────────────────
    if phys_ge68 and simp_ge68:
        mod.make_acu_bias_plots(phys_ge68, simp_ge68, acu_scan,
                                output_dir, z_map=acu_z_map)
    if phys_cs137 and simp_cs137:
        mod.make_cls_bias_plots(phys_cs137, simp_cs137, output_dir,
                                coords_csv=coords_csv)

    # ── combined summary 2×4 figure ───────────────────────────────────────────
    if (phys_ge68 and simp_ge68) or (phys_cs137 and simp_cs137):
        mod.make_summary_figure(phys_ge68, simp_ge68,
                                phys_cs137, simp_cs137,
                                acu_z_map, output_dir)

    n_png = sum(1 for f in os.listdir(output_dir) if f.endswith(".png"))
    _log(f"  Bias plots: {n_png} PNG → {output_dir}", 1)


def step_ly_extractor(scripts_base, ge68_json, cs137_json,
                      coords_csv, output_dir, acu_z_csv=None,
                      centre_run=ACU_CALIB_RUN):
    script = _find_script("ly_extractor.py", scripts_base)
    if script is None:
        raise FileNotFoundError("ly_extractor.py not found")

    mod = _import_module(script, "ly_extractor")

    _ge68  = {}
    if ge68_json and os.path.exists(ge68_json):
        with open(ge68_json) as jf:
            _ge68 = json.load(jf)
    _cs137 = {}
    if cs137_json and os.path.exists(cs137_json):
        with open(cs137_json) as jf:
            _cs137 = json.load(jf)

    z_map  = mod.load_acu_z_csv(acu_z_csv)
    coords = mod.load_cls_coordinates(coords_csv)

    acu_rows = mod.build_acu_table(_ge68,  z_map)
    cls_rows = mod.build_cls_table(_cs137, coords)
    g_points = mod.compute_g_map(acu_rows, cls_rows, centre_run=centre_run)

    mod.save_tables(acu_rows, cls_rows, g_points, output_dir)
    mod.plot_ly_vs_z(acu_rows,  os.path.join(output_dir, "ly_vs_z.png"))
    mod.plot_ly_vs_radius(cls_rows, os.path.join(output_dir, "ly_vs_radius.png"))
    mod.plot_g_scatter(g_points, os.path.join(output_dir, "g_r_theta_scatter.png"))

    _log(f"g(r,θ) points: {len(g_points)}", 1)


def step_nu_map(scripts_base, g_npz, output_dir, sim_npz=None, n_shells=18):
    script = _find_script("nu_map.py", scripts_base)
    if script is None:
        raise FileNotFoundError("nu_map.py not found")

    mod  = _import_module(script, "nu_map")
    data = mod.load_g_data(g_npz)

    sim_data = None
    if sim_npz and os.path.exists(sim_npz):
        import numpy as np
        sim_data = dict(np.load(sim_npz, allow_pickle=True))

    os.makedirs(output_dir, exist_ok=True)
    mod.plot_rz_scatter(data, os.path.join(output_dir, "g_rz_scatter.png"))
    if len(data["r_mm"]) > 5:
        mod.plot_2d_interpolated(data, os.path.join(output_dir, "g_2d_interp.png"))
        mod.plot_deviation_map(data, os.path.join(output_dir, "g_deviation_map.png"))
    mod.plot_radial_shells(data, os.path.join(output_dir, "g_radial_shells.png"),
                           n_bins=n_shells)
    mod.plot_g_vs_z(data, os.path.join(output_dir, "g_vs_z.png"))
    mod.plot_g_vs_r_cls(data, os.path.join(output_dir, "g_vs_r_cls.png"))
    if sim_data:
        mod.plot_data_sim_ratio(data, sim_data,
                                os.path.join(output_dir, "g_data_sim_ratio.png"))
    mod.print_summary(data, output_dir)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    cluster  = _detect_cluster()
    defaults = _CLUSTER_DEFAULTS[cluster]

    parser = argparse.ArgumentParser(
        description="TAO non-uniformity master pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--base-dir",    default=defaults["base_dir"],
                        help="Directory with RUN*/ sub-folders (energy_resolution)")
    parser.add_argument("--coords-csv",  default=defaults["coords_csv"],
                        help="InitialP_meanQEdepP_gamma.csv (CLS positions)")
    parser.add_argument("--output-root", default=defaults["output_root"],
                        help="Root directory for all outputs")
    parser.add_argument("--scripts-base", default=defaults["scripts_base"],
                        help="Directory containing analysis scripts")
    parser.add_argument("--sim-npz",     default=None,
                        help="Optional: simulated g_r_theta.npz for data/sim ratio")
    parser.add_argument("--acu-calib-run", type=int, default=ACU_CALIB_RUN,
                        help=f"ACU reference run for rtraw_custom (default: {ACU_CALIB_RUN})")
    parser.add_argument("--cls-run",     type=int, default=CLS_RUN,
                        help=f"CLS run number (default: {CLS_RUN})")
    parser.add_argument("--force",       action="store_true",
                        help="Re-run all steps even if outputs exist")
    parser.add_argument("--verbose",     action="store_true",
                        help="Print verbose fit output")
    parser.add_argument("--skip-scan",   action="store_true",
                        help="Skip ACU/CLS pipeline comparison scans (steps 2-3)")
    parser.add_argument("--skip-fits",   action="store_true",
                        help="Skip Ge-68/Cs-137 peak fits (steps 4-5)")
    parser.add_argument("--only-maps",   action="store_true",
                        help="Only run steps 6-7 (LY extraction + nu maps)")
    args = parser.parse_args()

    ts = time.strftime("%Y%m%d_%H%M%S")

    # Output directories per step.
    # acu_scan / cls_scan use a stable name so that:
    #   (a) the cached scan JSON is always found at a fixed path by extra_plots,
    #   (b) --force correctly re-runs the same directory.
    dirs = {
        "acu_scan":    os.path.join(args.output_root, "acu_scan"),
        "cls_scan":    os.path.join(args.output_root, "cls_scan"),
        "extra_plots": os.path.join(args.output_root, "extra_plots"),
        "ge68_fits":   os.path.join(args.output_root, "ge68_fits"),
        "cs137_fits":  os.path.join(args.output_root, "cs137_fits"),
        "ly":          os.path.join(args.output_root, "ly_output"),
        "nu_maps":     os.path.join(args.output_root, "nu_maps"),
        # shared merged spectrum caches
        "acu_merged":  os.path.join(args.output_root, "acu_merged_spectra"),
        "cls_merged":  os.path.join(args.output_root, "cls_merged_spectra"),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    _section("TAO NON-UNIFORMITY PIPELINE")
    print(f"  Cluster     : {cluster}")
    print(f"  base-dir    : {args.base_dir}")
    print(f"  output-root : {args.output_root}")
    print(f"  timestamp   : {ts}")
    print(f"  force       : {args.force}")
    if args.skip_scan:
        print(f"  SKIP        : ACU/CLS scan comparisons (steps 2-3)")
    if args.skip_fits:
        print(f"  SKIP        : Ge-68/Cs-137 peak fits (steps 4-5)")
    if args.only_maps:
        print(f"  MODE        : only-maps (steps 6-7 only)")

    status = {}
    t_pipeline_start = time.time()

    # ── Step 2: ACU scan compare ──────────────────────────────────────────
    if not args.skip_scan and not args.only_maps:
        primary = os.path.join(dirs["acu_scan"], "a_all4_resolution_vs_z.png")
        ok = _run_step(
            "ACU Ge-68 z-scan comparison",
            step_acu_scan_compare,
            dict(
                scripts_base = args.scripts_base,
                base_dir     = args.base_dir,
                output_dir   = dirs["acu_scan"],
                merged_dir   = dirs["acu_merged"],
                calib_run    = args.acu_calib_run,
                force_refit  = args.force,
                verbose      = args.verbose,
            ),
            primary_output = primary,
            force = args.force,
        )
        status["acu_scan"] = ok

    # ── Step 3: CLS scan compare ──────────────────────────────────────────
    if not args.skip_scan and not args.only_maps:
        primary = os.path.join(dirs["cls_scan"],
                               "a_all4_resolution_vs_position.png")
        ok = _run_step(
            f"CLS Cs-137 scan comparison (RUN {args.cls_run})",
            step_cls_scan_compare,
            dict(
                scripts_base = args.scripts_base,
                base_dir     = args.base_dir,
                output_dir   = dirs["cls_scan"],
                merged_dir   = dirs["cls_merged"],
                run          = args.cls_run,
                coords_csv   = args.coords_csv,
                verbose      = args.verbose,
            ),
            primary_output = primary,
            force = args.force,
        )
        status["cls_scan"] = ok

    # ── Step 3b: Extra plots — LY + 2D colormaps ─────────────────────────
    # Runs whenever scan JSONs exist (after steps 2-3, or from a previous run)
    acu_json = os.path.join(dirs["acu_scan"], "acu_scan_data.json")
    cls_json = os.path.join(dirs["cls_scan"], "cls_scan_data.json")
    if not args.only_maps and (os.path.exists(acu_json) or os.path.exists(cls_json)):
        primary_extra = os.path.join(dirs["extra_plots"], "2d_colormap_ly.png")
        ok = _run_step(
            "Extra plots: LY vs z/r + 2D colormaps",
            step_scan_extra_plots,
            dict(
                acu_json_path = acu_json,
                cls_json_path = cls_json,
                coords_csv    = args.coords_csv,
                output_dir    = dirs["extra_plots"],
            ),
            primary_output = primary_extra,
            force = args.force,
        )
        status["extra_plots"] = ok

    # ── Step 4: Ge-68 physics fits ────────────────────────────────────────
    if not args.skip_fits and not args.only_maps:
        primary = os.path.join(dirs["ge68_fits"], "ge68_fit_summary.json")
        ok = _run_step(
            "Ge-68 physics-model peak fits",
            step_fit_ge68,
            dict(
                scripts_base = args.scripts_base,
                merged_dir   = dirs["acu_merged"],
                output_dir   = dirs["ge68_fits"],
                verbose      = args.verbose,
            ),
            primary_output = primary,
            force = args.force,
        )
        status["ge68_fits"] = ok

    # ── Step 5: Cs-137 physics fits ───────────────────────────────────────
    if not args.skip_fits and not args.only_maps:
        primary = os.path.join(dirs["cs137_fits"], "cs137_fit_summary.json")
        ok = _run_step(
            "Cs-137 physics-model peak fits",
            step_fit_cs137,
            dict(
                scripts_base = args.scripts_base,
                merged_dir   = dirs["cls_merged"],
                output_dir   = dirs["cs137_fits"],
                verbose      = args.verbose,
            ),
            primary_output = primary,
            force = args.force,
        )
        status["cs137_fits"] = ok

    # ── Step 5b: Fit-method bias plots ────────────────────────────────────
    if not args.skip_fits and not args.only_maps:
        bias_dir = os.path.join(args.output_root, "bias_plots")
        dirs["bias_plots"] = bias_dir
        os.makedirs(bias_dir, exist_ok=True)
        ok = _run_step(
            "Fit-method bias plots (physics model vs Gauss+pol3)",
            step_bias_plots,
            dict(
                scripts_base  = args.scripts_base,
                ge68_fit_dir  = dirs["ge68_fits"],
                cs137_fit_dir = dirs["cs137_fits"],
                acu_merged_dir= dirs["acu_merged"],
                cls_merged_dir= dirs["cls_merged"],
                acu_scan_json = os.path.join(dirs["acu_scan"], "acu_scan_data.json"),
                coords_csv    = args.coords_csv,
                output_dir    = bias_dir,
            ),
            primary_output = os.path.join(bias_dir, "bias_summary.png"),
            force = args.force,
        )
        status["bias_plots"] = ok

    # ── Step 6: LY extraction + g(r,θ) ───────────────────────────────────
    ge68_json_path  = os.path.join(dirs["ge68_fits"],  "ge68_fit_summary.json")
    cs137_json_path = os.path.join(dirs["cs137_fits"], "cs137_fit_summary.json")
    g_npz_path      = os.path.join(dirs["ly"],         "g_r_theta.npz")

    ge68_ready  = os.path.exists(ge68_json_path)
    cs137_ready = os.path.exists(cs137_json_path)

    if not ge68_ready and not cs137_ready:
        _section("STEP: Light-yield extraction → g(r,θ)")
        _log("SKIP: no fit JSONs found.")
        _log("  ge68_fit_summary.json  : NOT FOUND", 1)
        _log("  cs137_fit_summary.json : NOT FOUND", 1)
        _log("  → Run without --only-maps / --skip-fits first to produce them.", 1)
        status["ly"] = False
    else:
        ok = _run_step(
            "Light-yield extraction → g(r,θ)",
            step_ly_extractor,
            dict(
                scripts_base = args.scripts_base,
                ge68_json    = ge68_json_path  if ge68_ready  else None,
                cs137_json   = cs137_json_path if cs137_ready else None,
                coords_csv   = args.coords_csv,
                output_dir   = dirs["ly"],
                centre_run   = args.acu_calib_run,
            ),
            primary_output = g_npz_path,
            force = args.force,
        )
        status["ly"] = ok

    # ── Step 7: Non-uniformity maps ───────────────────────────────────────
    if os.path.exists(g_npz_path):
        ok = _run_step(
            "Non-uniformity maps + shells",
            step_nu_map,
            dict(
                scripts_base = args.scripts_base,
                g_npz        = g_npz_path,
                output_dir   = dirs["nu_maps"],
                sim_npz      = args.sim_npz,
            ),
            primary_output = os.path.join(dirs["nu_maps"], "g_radial_shells.png"),
            force = args.force,
        )
        status["nu_maps"] = ok
    else:
        _log("SKIP nu_map: g_r_theta.npz not yet available.")

    # ── Final summary ─────────────────────────────────────────────────────
    elapsed = time.time() - t_pipeline_start
    _section(f"PIPELINE DONE  ({elapsed:.0f}s)")

    for step, ok in status.items():
        symbol = "✓" if ok else "✗"
        print(f"  {symbol}  {step}")

    print()
    print("  Output root:", args.output_root)
    total_png = sum(
        sum(1 for f in os.listdir(d) if f.endswith(".png"))
        for d in dirs.values()
        if os.path.isdir(d)
    )
    print(f"  Total PNG files: {total_png}")

    failed = [s for s, ok in status.items() if not ok]
    if failed:
        print(f"\n  FAILURES: {', '.join(failed)}")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
