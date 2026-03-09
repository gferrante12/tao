#!/usr/bin/env python3
"""
plot_bias_comparison.py — Bias between physics-model fits and Gauss+pol3 fits

For each ACU (Ge-68) and CLS (Cs-137) position, computes the difference
(bias) between the physics-model result and the simple Gauss+pol3 result
for: mean PE, sigma PE, energy resolution, and light yield.

The Gauss+pol3 fits are run on-the-fly on the same merged spectrum ROOT files
that the physics-model fits used, ensuring a strict apples-to-apples comparison
on identical data.

Outputs (in --output-dir):
  acu_bias_mean.png       ACU: Δ(mean PE)  vs  z [mm]
  acu_bias_sigma.png      ACU: Δ(sigma PE) vs  z [mm]
  acu_bias_resolution.png ACU: Δ(res %)    vs  z [mm]
  acu_bias_ly.png         ACU: Δ(LY PE/MeV) vs z [mm]
  cls_bias_mean.png       CLS: Δ(mean PE)  vs position index
  cls_bias_sigma.png      CLS: Δ(sigma PE) vs position index
  cls_bias_resolution.png CLS: Δ(res %)    vs position index
  cls_bias_ly.png         CLS: Δ(LY PE/MeV) vs position index

Usage:
  python plot_bias_comparison.py \\
      --ge68-summary   ge68_fits/ge68_fit_summary.json \\
      --cs137-summary  cs137_fits/cs137_fit_summary.json \\
      --ge68-merged    acu_merged_spectra/ \\
      --cs137-merged   cls_merged_spectra/ \\
      --acu-z-json     acu_scan/acu_scan_data.json \\
      --output-dir     bias_plots/

The script uses the *_simple summary JSON files if they already exist
(written by tao_nu_pipeline.py), otherwise runs fits from scratch.

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
import matplotlib.gridspec as gridspec


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_json(path):
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _run_number_from_stem(stem):
    """Extract integer run number from a stem like spectrum_RUN1302_rtraw_default."""
    for part in stem.split("_"):
        if part.startswith("RUN") and part[3:].isdigit():
            return int(part[3:])
    return None


def _pos_index_from_stem(stem):
    """Extract position index from a stem like spectrum_RUN1344_pos07_rtraw_default."""
    for part in stem.split("_"):
        if part.startswith("pos") and part[3:].isdigit():
            return int(part[3:])
    return None


def _acu_z_from_scan_json(scan_data, run_number):
    """Look up z [mm] for a run from acu_scan_data.json structure."""
    for pipeline_data in scan_data.values():
        for run_key, entry in pipeline_data.items():
            # run_key can be "RUN1302" or just "1302"
            key_num = int(run_key.lstrip("RUN")) if run_key.lstrip("RUN").isdigit() else None
            if key_num == run_number and "z_mm" in entry:
                return float(entry["z_mm"])
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Simple-fit runner (imports fit_peaks_ge68 / fit_peaks_cs137 dynamically)
# ─────────────────────────────────────────────────────────────────────────────

def _import_fit_module(script_path, module_name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_script(name, search_dirs):
    for d in search_dirs:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def _build_simple_summary(merged_dir, fit_func, stem_filter=None):
    """
    Run simple fit on every ROOT file in merged_dir.
    stem_filter: callable(stem) → bool, selects which files to process.
    Returns dict  stem → result_dict.
    """
    files  = sorted(glob.glob(os.path.join(merged_dir, "*.root")))
    result = {}
    for fpath in files:
        stem = os.path.splitext(os.path.basename(fpath))[0]
        if stem_filter and not stem_filter(stem):
            continue
        r = fit_func(fpath)
        if r is not None:
            result[stem] = {k: v for k, v in r.items() if k != "_fit_params"}
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Bias plot helper
# ─────────────────────────────────────────────────────────────────────────────

_METRIC_LABELS = {
    "mean":       ("Δ mean PE  (physics − Gauss+pol3)",       "PE"),
    "sigma":      ("Δ sigma PE  (physics − Gauss+pol3)",      "PE"),
    "resolution": ("Δ resolution  (physics − Gauss+pol3)",    "%-points"),
    "ly":         ("Δ LY  (physics − Gauss+pol3)",            "PE/MeV"),
}

_METRIC_KEYS = {
    "mean":       ("mean_PE",        "mean_PE"),
    "sigma":      ("sigma_PE",       "sigma_PE"),
    "resolution": ("resolution_pct", "resolution_pct"),
    "ly":         ("LY_PE_per_MeV",  "LY_PE_per_MeV"),
}

_METRIC_ERR_KEYS = {
    "mean":       ("mean_PE_err",        "mean_PE_err"),
    "sigma":      ("sigma_PE_err",       "sigma_PE_err"),
    "resolution": ("resolution_pct_err", "resolution_pct_err"),
    "ly":         ("LY_PE_per_MeV_err",  "LY_PE_per_MeV_err"),
}


def _bias_plot(x_vals, bias_vals, bias_errs, xlabel, metric, output_path,
               title_prefix="", x_ticks=None):
    """
    Single-panel bias plot with zero line and error bars.
    """
    fig, ax = plt.subplots(figsize=(11, 5))

    mask = np.isfinite(bias_vals)
    xp   = np.asarray(x_vals)[mask]
    bp   = bias_vals[mask]
    ep   = bias_errs[mask]

    # color by sign
    colors = np.where(bp >= 0, "steelblue", "tomato")

    ax.errorbar(xp, bp, yerr=ep, fmt="o", markersize=5,
                elinewidth=1.2, capsize=3, color="k", zorder=3, alpha=0.7)
    ax.scatter(xp, bp, c=colors, s=35, zorder=4)

    ax.axhline(0, color="k", lw=1.2, ls="--")

    # shaded ±1 RMS band
    rms = float(np.sqrt(np.mean(bp ** 2))) if len(bp) > 0 else 0
    ax.axhspan(-rms, rms, alpha=0.08, color="grey", label=f"RMS = {rms:.2f} {_METRIC_LABELS[metric][1]}")

    label_str, unit = _METRIC_LABELS[metric]
    ax.set_ylabel(f"{label_str}\n[{unit}]", fontsize=10)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_title(f"{title_prefix} — {label_str}", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    if x_ticks is not None:
        ax.set_xticks(x_ticks[0])
        ax.set_xticklabels(x_ticks[1], rotation=45, ha="right", fontsize=7)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# ACU bias plots
# ─────────────────────────────────────────────────────────────────────────────

def make_acu_bias_plots(physics_summary, simple_summary, acu_scan_data,
                        output_dir, z_map=None):
    """
    physics_summary / simple_summary:  stem → result_dict
    acu_scan_data: loaded acu_scan_data.json (may be None / empty)
    z_map: dict  run_number (int) → z_mm (float), optional override
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── build matched pairs (stem, z_mm) ──────────────────────────────────────
    rows = []   # (z_mm, phys_result, simp_result)

    for stem, phys in sorted(physics_summary.items()):
        simp = simple_summary.get(stem)
        if simp is None:
            continue

        run_num = _run_number_from_stem(stem)
        z_mm    = None

        # 1) user-supplied z_map dict
        if z_map and run_num in z_map:
            z_mm = float(z_map[run_num])

        # 2) scan JSON
        if z_mm is None and acu_scan_data and run_num is not None:
            z_mm = _acu_z_from_scan_json(acu_scan_data, run_num)

        # 3) fall back: use run number as proxy x-axis
        if z_mm is None:
            z_mm = float(run_num) if run_num is not None else float(len(rows))

        rows.append((z_mm, phys, simp))

    if not rows:
        print("  WARN: no matched ACU pairs found for bias plots")
        return

    rows.sort(key=lambda r: r[0])
    z_arr = np.array([r[0] for r in rows])

    for metric in ["mean", "sigma", "resolution", "ly"]:
        pk, sk   = _METRIC_KEYS[metric]
        pek, sek = _METRIC_ERR_KEYS[metric]

        bias = np.array([r[1].get(pk, np.nan) - r[2].get(sk, np.nan) for r in rows])
        # combined uncertainty: σ_bias = sqrt(σ_phys² + σ_simple²)
        err  = np.array([
            np.sqrt(r[1].get(pek, 0.0) ** 2 + r[2].get(sek, 0.0) ** 2)
            for r in rows
        ])

        out = os.path.join(output_dir, f"acu_bias_{metric}.png")
        _bias_plot(z_arr, bias, err,
                   xlabel="ACU source z position [mm]",
                   metric=metric,
                   output_path=out,
                   title_prefix="ACU Ge-68")


# ─────────────────────────────────────────────────────────────────────────────
# CLS bias plots
# ─────────────────────────────────────────────────────────────────────────────

def make_cls_bias_plots(physics_summary, simple_summary, output_dir,
                        coords_csv=None):
    """
    coords_csv: optional path to InitialP_meanQEdepP_gamma.csv for (r, θ) coords.
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── try to load radial coords ─────────────────────────────────────────────
    r_map = {}   # pos_index (int) → r_mm (float)
    if coords_csv and os.path.exists(coords_csv):
        try:
            data = np.genfromtxt(coords_csv, delimiter=",", names=True)
            for row in data:
                idx = int(row["pos"]) if "pos" in data.dtype.names else None
                r   = float(row["r"])  if "r"   in data.dtype.names else None
                if idx is not None and r is not None:
                    r_map[idx] = r
        except Exception:
            pass

    # ── build matched pairs ───────────────────────────────────────────────────
    rows = []   # (pos_idx, r_mm_or_None, phys, simp)

    for stem, phys in sorted(physics_summary.items()):
        simp = simple_summary.get(stem)
        if simp is None:
            continue
        pos_idx = _pos_index_from_stem(stem)
        r_mm    = r_map.get(pos_idx) if pos_idx is not None else None
        rows.append((pos_idx or 0, r_mm, phys, simp))

    if not rows:
        print("  WARN: no matched CLS pairs found for bias plots")
        return

    rows.sort(key=lambda r: r[0])
    pos_arr = np.array([r[0] for r in rows])
    r_arr   = np.array([r[1] if r[1] is not None else np.nan for r in rows])
    use_r   = np.isfinite(r_arr).sum() > len(rows) // 2

    x_vals  = r_arr  if use_r  else pos_arr
    xlabel  = "CLS source radius [mm]" if use_r else "CLS position index"

    for metric in ["mean", "sigma", "resolution", "ly"]:
        pk, sk   = _METRIC_KEYS[metric]
        pek, sek = _METRIC_ERR_KEYS[metric]

        bias = np.array([r[2].get(pk, np.nan) - r[3].get(sk, np.nan) for r in rows])
        err  = np.array([
            np.sqrt(r[2].get(pek, 0.0) ** 2 + r[3].get(sek, 0.0) ** 2)
            for r in rows
        ])

        out = os.path.join(output_dir, f"cls_bias_{metric}.png")
        _bias_plot(x_vals, bias, err,
                   xlabel=xlabel,
                   metric=metric,
                   output_path=out,
                   title_prefix="CLS Cs-137")


# ─────────────────────────────────────────────────────────────────────────────
# Summary 4-panel figure  (mean / sigma / res / LY in one page)
# ─────────────────────────────────────────────────────────────────────────────

def make_summary_figure(physics_acu, simple_acu, physics_cls, simple_cls,
                        acu_z_map, output_dir):
    """2×4 panel: rows=ACU/CLS, cols=mean/sigma/res/LY."""
    metrics = ["mean", "sigma", "resolution", "ly"]
    fig, axes = plt.subplots(2, 4, figsize=(22, 8))
    fig.suptitle("Fit-method bias: physics model  −  Gauss+pol3", fontsize=13, y=1.01)

    def _pair_data(phys_sum, simp_sum, key_func):
        rows = []
        for stem, phys in sorted(phys_sum.items()):
            simp = simp_sum.get(stem)
            if simp is None:
                continue
            rows.append((key_func(stem), phys, simp))
        rows.sort(key=lambda r: r[0] if r[0] is not None else 0)
        return rows

    # ACU rows
    def acu_key(stem):
        rn = _run_number_from_stem(stem)
        return acu_z_map.get(rn, rn) if acu_z_map else rn

    acu_rows = _pair_data(physics_acu, simple_acu, acu_key)
    cls_rows = _pair_data(physics_cls, simple_cls,
                          lambda s: _pos_index_from_stem(s) or 0)

    for col, metric in enumerate(metrics):
        pk, sk   = _METRIC_KEYS[metric]
        pek, sek = _METRIC_ERR_KEYS[metric]
        label, unit = _METRIC_LABELS[metric]

        for row_idx, (rows, src_label, xlabel) in enumerate([
            (acu_rows, "ACU Ge-68",  "z [mm]"),
            (cls_rows, "CLS Cs-137", "position"),
        ]):
            ax = axes[row_idx][col]
            if not rows:
                ax.set_visible(False)
                continue

            xs   = np.array([r[0] for r in rows], dtype=float)
            bias = np.array([r[1].get(pk, np.nan) - r[2].get(sk, np.nan)
                             for r in rows])
            errs = np.array([np.sqrt(r[1].get(pek, 0)**2 + r[2].get(sek, 0)**2)
                             for r in rows])
            mask = np.isfinite(bias)
            rms  = float(np.sqrt(np.mean(bias[mask]**2))) if mask.sum() > 0 else 0

            ax.errorbar(xs[mask], bias[mask], yerr=errs[mask],
                        fmt="o", ms=3, elinewidth=0.8, capsize=2,
                        color="steelblue" if row_idx == 0 else "tomato",
                        alpha=0.8, zorder=3)
            ax.axhline(0, color="k", lw=0.9, ls="--")
            ax.axhspan(-rms, rms, alpha=0.08, color="grey")
            ax.set_xlabel(xlabel, fontsize=8)
            ax.set_ylabel(f"Δ [{unit}]", fontsize=8)
            if row_idx == 0:
                ax.set_title(label.split("(")[0].strip(), fontsize=9, pad=3)
            ax.annotate(f"RMS={rms:.2f}", xy=(0.97, 0.97), xycoords="axes fraction",
                        ha="right", va="top", fontsize=7.5,
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.25)

        axes[0][col].set_title(label.split("(")[0].strip(), fontsize=9)

    # row labels
    for row_idx, lbl in enumerate(["ACU Ge-68", "CLS Cs-137"]):
        axes[row_idx][0].set_ylabel(f"{lbl}\n{axes[row_idx][0].get_ylabel()}", fontsize=8)

    fig.tight_layout()
    out = os.path.join(output_dir, "bias_summary.png")
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(out)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Bias plots: physics model vs Gauss+pol3 fit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--ge68-summary",
                    help="Path to ge68_fit_summary.json (physics model)")
    ap.add_argument("--ge68-simple-summary",
                    help="Path to ge68_simple_fit_summary.json (pre-computed, optional)")
    ap.add_argument("--cs137-summary",
                    help="Path to cs137_fit_summary.json (physics model)")
    ap.add_argument("--cs137-simple-summary",
                    help="Path to cs137_simple_fit_summary.json (pre-computed, optional)")
    ap.add_argument("--ge68-merged",
                    help="Dir with merged Ge-68 spectrum ROOT files (for on-the-fly simple fits)")
    ap.add_argument("--cs137-merged",
                    help="Dir with merged Cs-137 spectrum ROOT files")
    ap.add_argument("--acu-z-json",
                    help="acu_scan_data.json (provides z positions per run)")
    ap.add_argument("--coords-csv",
                    help="InitialP_meanQEdepP_gamma.csv (CLS radial coordinates)")
    ap.add_argument("--scripts-dir", default=".",
                    help="Directory containing fit_peaks_ge68.py and fit_peaks_cs137.py")
    ap.add_argument("--output-dir", default="bias_plots",
                    help="Output directory for bias PNG files")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # ── load physics summaries ────────────────────────────────────────────────
    phys_ge68  = _load_json(args.ge68_summary)
    phys_cs137 = _load_json(args.cs137_summary)

    if not phys_ge68 and not phys_cs137:
        sys.exit("ERROR: at least one physics summary JSON must be provided and non-empty")

    # ── load or compute simple summaries ──────────────────────────────────────
    simp_ge68  = _load_json(args.ge68_simple_summary)  if args.ge68_simple_summary  else {}
    simp_cs137 = _load_json(args.cs137_simple_summary) if args.cs137_simple_summary else {}

    search_dirs = [args.scripts_dir, os.path.dirname(os.path.abspath(__file__)), "."]

    # Ge-68 simple fits (if not pre-computed)
    if phys_ge68 and not simp_ge68 and args.ge68_merged:
        print("  Running Gauss+pol3 simple fits on Ge-68 merged spectra …")
        ge68_script = _find_script("fit_peaks_ge68.py", search_dirs)
        if ge68_script:
            mod_ge = _import_fit_module(ge68_script, "fit_peaks_ge68")
            simp_ge68 = _build_simple_summary(
                args.ge68_merged,
                mod_ge.fit_ge68_simple,
                stem_filter=lambda s: "rtraw_default" in s,
            )
            # cache for next run
            cache = os.path.join(args.output_dir, "ge68_simple_fit_summary.json")
            with open(cache, "w") as f:
                json.dump(simp_ge68, f, indent=2)
            print(f"  Cached simple fits → {cache}")
        else:
            print("  WARN: fit_peaks_ge68.py not found, cannot compute simple fits")

    # Cs-137 simple fits (if not pre-computed)
    if phys_cs137 and not simp_cs137 and args.cs137_merged:
        print("  Running Gauss+pol3 simple fits on Cs-137 merged spectra …")
        cs137_script = _find_script("fit_peaks_cs137.py", search_dirs)
        if cs137_script:
            mod_cs = _import_fit_module(cs137_script, "fit_peaks_cs137")
            simp_cs137 = _build_simple_summary(
                args.cs137_merged,
                mod_cs.fit_cs137_simple,
                stem_filter=lambda s: "rtraw_default" in s,
            )
            cache = os.path.join(args.output_dir, "cs137_simple_fit_summary.json")
            with open(cache, "w") as f:
                json.dump(simp_cs137, f, indent=2)
            print(f"  Cached simple fits → {cache}")
        else:
            print("  WARN: fit_peaks_cs137.py not found, cannot compute simple fits")

    # ── load z-position map for ACU ───────────────────────────────────────────
    acu_scan_data = _load_json(args.acu_z_json) if args.acu_z_json else {}

    # ── generate plots ────────────────────────────────────────────────────────
    acu_z_map = {}   # run_number → z_mm for summary figure

    if phys_ge68 and simp_ge68:
        print("\nGenerating ACU bias plots …")
        # build z_map for summary figure
        for stem in phys_ge68:
            rn = _run_number_from_stem(stem)
            if rn and acu_scan_data:
                z = _acu_z_from_scan_json(acu_scan_data, rn)
                if z is not None:
                    acu_z_map[rn] = z
        make_acu_bias_plots(phys_ge68, simp_ge68, acu_scan_data,
                            args.output_dir, z_map=acu_z_map)
    else:
        print("  SKIP: ACU bias plots (missing physics or simple summary)")

    if phys_cs137 and simp_cs137:
        print("\nGenerating CLS bias plots …")
        make_cls_bias_plots(phys_cs137, simp_cs137, args.output_dir,
                            coords_csv=args.coords_csv)
    else:
        print("  SKIP: CLS bias plots (missing physics or simple summary)")

    # ── combined summary figure ───────────────────────────────────────────────
    if (phys_ge68 and simp_ge68) or (phys_cs137 and simp_cs137):
        print("\nGenerating summary figure …")
        make_summary_figure(phys_ge68, simp_ge68,
                            phys_cs137, simp_cs137,
                            acu_z_map, args.output_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
