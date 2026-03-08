#!/usr/bin/env python3
"""
ly_extractor.py  —  Light-yield extraction & non-uniformity function g(r, θ)

Takes the per-position fit results from:
  • fit_peaks_ge68.py  (ACU z-scan,  z-axis positions)
  • fit_peaks_cs137.py (CLS scan,    off-axis positions)

and builds the 2D relative light-yield map:

    g(r, θ) = (μ_meas(r,θ) − DN) / (μ_meas(0,0) − DN) · LY_correction

where:
  • μ_meas  = measured peak mean [PE] from the spectrum fit
  • DN      = dark-noise PE (per-run value from the ROOT file)
  • LY_correction = accounts for the different energies of Ge-68 and Cs-137
                    so that g is normalised to 1 at the centre for both sources

The reference centre value is taken from the ACU run at z = 0 mm (power-on,
RUN 1319 by default).

Outputs
-------
  g_r_theta.npz          — array of (r, theta, g, g_err) data points
  g_r_theta.csv          — same as CSV
  ly_acu.csv             — per-run ACU light-yield table
  ly_cls.csv             — per-position CLS light-yield table
  ly_vs_z.png            — ACU light-yield vs z-position
  ly_vs_radius.png       — CLS light-yield vs radial distance
  g_r_theta_scatter.png  — scatter plot of g(r,θ) coloured by value

Usage
-----
  python ly_extractor.py \\
      --ge68-json  /path/to/ge68_fit_summary.json \\
      --cs137-json /path/to/cs137_fit_summary.json \\
      --coords-csv /path/to/InitialP_meanQEdepP_gamma.csv \\
      --acu-z-csv  /path/to/acu_z_positions.csv \\
      --output-dir ly_output/

The ge68 / cs137 summary JSONs are produced by fit_peaks_ge68.py /
fit_peaks_cs137.py with --scan.  Each key is the stem of the merged ROOT
file name, from which run number and CLS position index are parsed.

Alternatively, pass --ge68-dir / --cs137-dir to auto-run the fits.

Author: G. Ferrante
"""

import argparse
import csv
import json
import os
import re
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────────────────────────────────────
# Physical parameters
# ─────────────────────────────────────────────────────────────────────────────
E_GE68_MEV  = 1.022
E_CS137_MEV = 0.6617

# ACU run list: run → z_mm  (subset; full table in acu_scan_compare.py)
ACU_Z_MAP = {
    1296: 0, 1297: 880, 1298: 840, 1299: 800, 1300: 760, 1301: 720,
    1302: 680, 1303: 640, 1304: 600, 1305: 560, 1306: 520, 1307: 480,
    1308: 440, 1309: 400, 1310: 360, 1311: 320, 1312: 280, 1313: 240,
    1314: 200, 1315: 160, 1316: 120, 1317: 80,  1318: 40,  1319: 0,
    1320: -40, 1321: -80, 1322: -120, 1323: -160, 1324: -200, 1325: -240,
    1326: -280, 1327: -320, 1328: -360, 1329: -400, 1330: -440, 1331: -480,
    1332: -520, 1333: -560, 1334: -600, 1335: -640, 1336: -680, 1337: -720,
    1338: -760, 1339: -800, 1340: -840, 1341: -880,
}
ACU_CENTRE_RUN = 1319   # z=0 power-on (reference)


# ─────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_run_from_stem(stem):
    """Extract run number from a file stem like spectrum_RUN1319_centre."""
    m = re.search(r"RUN(\d+)", stem, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_pos_from_stem(stem):
    """Extract CLS position index from a file stem like spectrum_RUN1344_pos05_..."""
    m = re.search(r"pos(\d+)", stem, re.IGNORECASE)
    return int(m.group(1)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# Load coordinates
# ─────────────────────────────────────────────────────────────────────────────

def load_cls_coordinates(csv_path):
    """
    Return dict: pos_index → (r_mm, theta_rad, x, y, z)
    CSV columns: PointIndex, initX, initY, initZ  [mm]
    """
    coords = {}
    if not csv_path or not os.path.exists(csv_path):
        print(f"  WARNING: coords CSV not found: {csv_path}")
        return coords

    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                idx = int(row["PointIndex"])
                x   = float(row["initX"])
                y   = float(row["initY"])
                z   = float(row["initZ"])
                r   = float(np.sqrt(x ** 2 + y ** 2 + z ** 2))
                theta = float(np.arccos(z / r)) if r > 0 else 0.0
                coords[idx] = dict(r=r, theta=theta, x=x, y=y, z=z)
            except (KeyError, ValueError, ZeroDivisionError):
                pass

    print(f"  Loaded coordinates for {len(coords)} CLS positions")
    return coords


def load_acu_z_csv(csv_path):
    """
    Optional: override default ACU_Z_MAP from an external CSV.
    Columns: run, z_mm
    """
    if not csv_path or not os.path.exists(csv_path):
        return dict(ACU_Z_MAP)

    z_map = {}
    with open(csv_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                z_map[int(row["run"])] = int(float(row["z_mm"]))
            except (KeyError, ValueError):
                pass
    print(f"  Loaded {len(z_map)} ACU z-positions from {csv_path}")
    return z_map


# ─────────────────────────────────────────────────────────────────────────────
# Build per-source light-yield tables
# ─────────────────────────────────────────────────────────────────────────────

def build_acu_table(ge68_json, z_map):
    """
    Returns list of dicts: {run, z_mm, r_mm, theta_rad, mu_pe, dn_pe,
                             mu_net, mu_net_err, LY_PE_MeV, LY_PE_MeV_err}
    sorted by z ascending.
    """
    rows = []
    for stem, res in ge68_json.items():
        run = _parse_run_from_stem(stem)
        if run is None:
            continue
        z_mm = z_map.get(run)
        if z_mm is None:
            continue

        mu_pe  = res.get("mean_PE", -1.0)
        dn_pe  = res.get("dark_noise_PE", 0.0)
        mu_net = mu_pe - dn_pe
        if mu_net <= 0 or mu_pe <= 0:
            continue

        mu_err = res.get("mean_PE_err", 0.0)

        # On-axis: r = |z_mm|, theta = 0 (top) or pi (bottom)
        r_mm     = abs(z_mm)
        theta_rad = 0.0 if z_mm >= 0 else np.pi

        rows.append(dict(
            run=run, z_mm=z_mm, r_mm=r_mm, theta_rad=theta_rad,
            mu_pe=mu_pe, dn_pe=dn_pe,
            mu_net=mu_net, mu_net_err=mu_err,
            LY_PE_MeV=res.get("LY_PE_per_MeV", mu_net / E_GE68_MEV),
            LY_PE_MeV_err=res.get("LY_PE_per_MeV_err", mu_err / E_GE68_MEV),
        ))

    rows.sort(key=lambda d: d["z_mm"])
    return rows


def build_cls_table(cs137_json, coords):
    """
    Returns list of dicts: {pos, r_mm, theta_rad, x, y, z,
                             mu_pe, dn_pe, mu_net, mu_net_err, ...}
    """
    rows = []
    for stem, res in cs137_json.items():
        pos = _parse_pos_from_stem(stem)
        if pos is None:
            continue
        coord = coords.get(pos)
        if coord is None:
            continue

        mu_pe  = res.get("mean_PE", -1.0)
        dn_pe  = res.get("dark_noise_PE", 0.0)
        mu_net = mu_pe - dn_pe
        if mu_net <= 0:
            continue
        mu_err = res.get("mean_PE_err", 0.0)

        rows.append(dict(
            pos=pos,
            r_mm=coord["r"], theta_rad=coord["theta"],
            x=coord["x"], y=coord["y"], z=coord["z"],
            mu_pe=mu_pe, dn_pe=dn_pe,
            mu_net=mu_net, mu_net_err=mu_err,
            LY_PE_MeV=res.get("LY_PE_per_MeV", mu_net / E_CS137_MEV),
            LY_PE_MeV_err=res.get("LY_PE_per_MeV_err", mu_err / E_CS137_MEV),
        ))

    rows.sort(key=lambda d: d["r_mm"])
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Compute g(r, θ)
# ─────────────────────────────────────────────────────────────────────────────

def compute_g_map(acu_rows, cls_rows, centre_run=ACU_CENTRE_RUN):
    """
    Compute the relative light-yield non-uniformity function g(r, θ).

    Reference: ACU centre position (z=0 power-on).

    Strategy:
      1. Find μ_net_ref from ACU table for run == centre_run (z=0).
      2. For each ACU point:  g = μ_net / μ_net_ref   (Ge-68 scale)
      3. For each CLS point:  g = (μ_net / μ_net_ref) · (E_Ge68 / E_Cs137)⁻¹ ·
                                   (μ_net_ref_cs / μ_net_ref_ge)
         Instead of that complex cross-calibration, we normalise CLS separately
         to a Cs-137 centre reference (interpolated from ACU z=0 assuming
         LY_Cs = LY_Ge · NL_ratio, where NL_ratio comes from the non-linearity).

    Simplified approach (matching doc-15890):
      - Build LY_PE_MeV for both sources at each point.
      - g(pos) = LY_PE_MeV(pos) / LY_PE_MeV_ref
      - where LY_PE_MeV_ref = LY_PE_MeV of the ACU z=0 run.
      - This removes the E-scale difference between Ge-68 and Cs-137
        implicitly (they should give the same LY if non-linearity is flat).

    Returns list of dicts: {r_mm, theta_rad, g, g_err, source}
    """
    # Find reference LY from ACU centre run
    ref_rows = [r for r in acu_rows if r["run"] == centre_run]
    if not ref_rows:
        # fall back to minimum r
        ref_rows = sorted(acu_rows, key=lambda d: d["r_mm"])[:1]
    if not ref_rows:
        print("  ERROR: no ACU reference row found")
        return []

    LY_ref     = ref_rows[0]["LY_PE_MeV"]
    LY_ref_err = ref_rows[0]["LY_PE_MeV_err"]
    print(f"  Reference LY (run {ref_rows[0].get('run','?')} z={ref_rows[0]['z_mm']} mm): "
          f"{LY_ref:.0f} ± {LY_ref_err:.0f} PE/MeV")

    g_points = []

    # ACU points (Ge-68)
    for row in acu_rows:
        LY     = row["LY_PE_MeV"]
        LY_err = row["LY_PE_MeV_err"]
        g      = LY / LY_ref
        g_err  = g * np.sqrt((LY_err / LY) ** 2 + (LY_ref_err / LY_ref) ** 2)
        g_points.append(dict(
            r_mm=row["r_mm"], theta_rad=row["theta_rad"], z_mm=row["z_mm"],
            g=g, g_err=g_err, source="ACU",
            run=row.get("run", 0), pos=None,
        ))

    # CLS points (Cs-137): same formula, g is relative to the Ge-68 reference
    # The CLS LY is in PE/MeV computed with E_Cs137, so it's directly comparable
    for row in cls_rows:
        LY     = row["LY_PE_MeV"]
        LY_err = row["LY_PE_MeV_err"]
        g      = LY / LY_ref
        g_err  = g * np.sqrt((LY_err / LY) ** 2 + (LY_ref_err / LY_ref) ** 2)
        g_points.append(dict(
            r_mm=row["r_mm"], theta_rad=row["theta_rad"], z_mm=None,
            g=g, g_err=g_err, source="CLS",
            run=None, pos=row.get("pos", 0),
        ))

    return g_points


# ─────────────────────────────────────────────────────────────────────────────
# Save outputs
# ─────────────────────────────────────────────────────────────────────────────

def save_tables(acu_rows, cls_rows, g_points, output_dir):
    """Save CSV and NPZ files."""
    os.makedirs(output_dir, exist_ok=True)

    # ACU CSV
    acu_csv = os.path.join(output_dir, "ly_acu.csv")
    if acu_rows:
        keys = list(acu_rows[0].keys())
        with open(acu_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(acu_rows)
        print(f"  ✓  {acu_csv}")

    # CLS CSV
    cls_csv = os.path.join(output_dir, "ly_cls.csv")
    if cls_rows:
        keys = list(cls_rows[0].keys())
        with open(cls_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(cls_rows)
        print(f"  ✓  {cls_csv}")

    # g(r,θ) CSV and NPZ
    if g_points:
        g_csv = os.path.join(output_dir, "g_r_theta.csv")
        keys  = ["r_mm", "theta_rad", "g", "g_err", "source", "run", "pos"]
        with open(g_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for pt in g_points:
                w.writerow({k: pt.get(k, "") for k in keys})
        print(f"  ✓  {g_csv}")

        r_arr   = np.array([pt["r_mm"]      for pt in g_points])
        th_arr  = np.array([pt["theta_rad"] for pt in g_points])
        g_arr   = np.array([pt["g"]         for pt in g_points])
        ge_arr  = np.array([pt["g_err"]     for pt in g_points])
        src_arr = np.array([pt["source"]    for pt in g_points])

        npz_path = os.path.join(output_dir, "g_r_theta.npz")
        np.savez(npz_path, r_mm=r_arr, theta_rad=th_arr,
                 g=g_arr, g_err=ge_arr, source=src_arr)
        print(f"  ✓  {npz_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────

def plot_ly_vs_z(acu_rows, output_path):
    if not acu_rows:
        return
    zs  = np.array([r["z_mm"]         for r in acu_rows])
    lys = np.array([r["LY_PE_MeV"]    for r in acu_rows])
    les = np.array([r["LY_PE_MeV_err"] for r in acu_rows])

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.errorbar(zs, lys, yerr=les, fmt="o-", color="#1f77b4",
                markersize=5, capsize=3, lw=1.5, label="ACU (Ge-68)")
    ax.axhline(np.median(lys), color="r", lw=1, ls="--",
               label=f"Median={np.median(lys):.0f} PE/MeV")
    ax.set_xlabel("ACU z-position [mm]")
    ax.set_ylabel("Light yield [PE/MeV]")
    ax.set_title("ACU Ge-68 z-scan: Light yield vs z-position")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


def plot_ly_vs_radius(cls_rows, output_path):
    if not cls_rows:
        return
    rs  = np.array([r["r_mm"]          for r in cls_rows])
    lys = np.array([r["LY_PE_MeV"]     for r in cls_rows])
    les = np.array([r["LY_PE_MeV_err"] for r in cls_rows])

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.errorbar(rs, lys, yerr=les, fmt="s-", color="#d62728",
                markersize=5, capsize=3, lw=1.5, label="CLS (Cs-137)")
    ax.axhline(np.median(lys), color="r", lw=1, ls="--",
               label=f"Median={np.median(lys):.0f} PE/MeV")
    ax.set_xlabel("Radial distance from centre [mm]")
    ax.set_ylabel("Light yield [PE/MeV]")
    ax.set_title("CLS Cs-137 scan: Light yield vs radial distance")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


def plot_g_scatter(g_points, output_path):
    if not g_points:
        return

    acu = [p for p in g_points if p["source"] == "ACU"]
    cls = [p for p in g_points if p["source"] == "CLS"]

    fig, ax = plt.subplots(figsize=(10, 5))

    if acu:
        r_a = np.array([p["r_mm"] for p in acu])
        g_a = np.array([p["g"]    for p in acu])
        e_a = np.array([p["g_err"] for p in acu])
        ax.errorbar(r_a, g_a, yerr=e_a, fmt="o", color="#1f77b4",
                    markersize=6, capsize=3, lw=1.5, label="ACU (Ge-68)")

    if cls:
        r_c = np.array([p["r_mm"] for p in cls])
        g_c = np.array([p["g"]    for p in cls])
        e_c = np.array([p["g_err"] for p in cls])
        ax.errorbar(r_c, g_c, yerr=e_c, fmt="s", color="#d62728",
                    markersize=5, capsize=3, lw=1, alpha=0.8, label="CLS (Cs-137)")

    ax.axhline(1.0, color="k", lw=1, ls="--", label="g = 1 (reference)")
    ax.axhline(0.99, color="grey", lw=0.8, ls=":", alpha=0.7)
    ax.axhline(1.01, color="grey", lw=0.8, ls=":", alpha=0.7)

    ax.set_xlabel("Radial distance from centre [mm]")
    ax.set_ylabel("$g(r, \\theta) = $ LY(pos) / LY(centre)")
    ax.set_title("TAO Non-uniformity:  $g(r, \\theta)$ vs radial distance")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_ylim(0.80, 1.06)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Light-yield extraction and g(r,θ) non-uniformity map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ge68-json",   default=None,
                        help="ge68_fit_summary.json from fit_peaks_ge68.py")
    parser.add_argument("--cs137-json",  default=None,
                        help="cs137_fit_summary.json from fit_peaks_cs137.py")
    parser.add_argument("--coords-csv",  default=None,
                        help="InitialP_meanQEdepP_gamma.csv with CLS positions")
    parser.add_argument("--acu-z-csv",   default=None,
                        help="Optional CSV with run→z_mm mapping")
    parser.add_argument("--centre-run",  type=int, default=ACU_CENTRE_RUN,
                        help=f"ACU run used as g=1 reference (default: {ACU_CENTRE_RUN})")
    parser.add_argument("--output-dir",  default="ly_output",
                        help="Output directory (default: ly_output)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load JSONs
    ge68_json, cs137_json = {}, {}
    if args.ge68_json and os.path.exists(args.ge68_json):
        with open(args.ge68_json) as jf:
            ge68_json = json.load(jf)
        print(f"  Loaded {len(ge68_json)} Ge-68 fit results")
    else:
        print("  WARNING: --ge68-json not provided or not found; ACU table will be empty")

    if args.cs137_json and os.path.exists(args.cs137_json):
        with open(args.cs137_json) as jf:
            cs137_json = json.load(jf)
        print(f"  Loaded {len(cs137_json)} Cs-137 fit results")
    else:
        print("  WARNING: --cs137-json not provided or not found; CLS table will be empty")

    z_map  = load_acu_z_csv(args.acu_z_csv)
    coords = load_cls_coordinates(args.coords_csv)

    acu_rows = build_acu_table(ge68_json,  z_map)
    cls_rows = build_cls_table(cs137_json, coords)

    print(f"\n  ACU points : {len(acu_rows)}")
    print(f"  CLS points : {len(cls_rows)}")

    g_points = compute_g_map(acu_rows, cls_rows, centre_run=args.centre_run)
    print(f"  g(r,θ) points: {len(g_points)}")

    save_tables(acu_rows, cls_rows, g_points, args.output_dir)

    plot_ly_vs_z(acu_rows,
                 os.path.join(args.output_dir, "ly_vs_z.png"))
    plot_ly_vs_radius(cls_rows,
                      os.path.join(args.output_dir, "ly_vs_radius.png"))
    plot_g_scatter(g_points,
                   os.path.join(args.output_dir, "g_r_theta_scatter.png"))

    print(f"\nDone. Output in: {args.output_dir}")


if __name__ == "__main__":
    main()
