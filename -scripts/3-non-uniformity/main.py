#!/usr/bin/env python3
"""
main.py  —  TAO Non-Uniformity Analysis: Main Entry Point

Produces all non-uniformity plots from ACU and CLS calibration scan data.

Usage:
  # With real data (JSON fit results from fit_peaks_ge68.py / fit_peaks_cs137.py):
  python main.py --acu-dir /path/to/acu_fits --cls-dir /path/to/cls_fits \\
                 --output-dir ./plots --label "RUN 1295-1400"

  # Demo mode (synthetic data):
  python main.py --demo --output-dir ./plots_demo

  # With run-position CSV mapping:
  python main.py --acu-dir /path/to/fits --cls-dir /path/to/fits \\
                 --run-map positions.csv --output-dir ./plots

Plot inventory:
  ACU (a):
    acu_overview.png         — 4-panel: mean, sigma, resolution, LY vs z
    acu_mean.png             — Mean PE vs z
    acu_sigma.png            — Sigma PE vs z
    acu_resolution.png       — Resolution vs z
    acu_ly.png               — Light Yield vs z
    acu_g_vs_r.png           — g(z) relative LY, folded top/bottom

  CLS (b):
    cls_overview_2d_r_theta.png     — 4-panel 2D colormaps in (r, θ)
    cls_overview_2d_phi_theta.png   — 4-panel 2D colormaps in (φ, θ)
    cls_overview_3d_r_theta.png     — 4-panel 3D surfaces in (r, θ)
    cls_overview_3d_phi_theta.png   — 4-panel 3D surfaces in (φ, θ)
    cls_{param}_2d_r_theta.png      — individual 2D colormaps
    cls_{param}_2d_phi_theta.png    — individual 2D colormaps
    cls_{param}_3d_r_theta.png      — individual 3D surfaces
    cls_{param}_3d_phi_theta.png    — individual 3D surfaces
    cls_{param}_3d_scatter.png      — 3D scatter in (r, θ, φ) space

  Non-uniformity map:
    g_vs_radius_raw.png             — g(r, θ) vs r (data points only)
    g_colormap_raw.png              — g(r, θ) in (r, θ) plane (data only)
    g_map_interpolated_CT.png       — g(r, θ) Clough-Tocher interpolation
    g_map_residual.png              — g − g_ideal residual
    g_map_physics_model.png         — data vs solid-angle model comparison

Author: G. Ferrante (INFN-MiB / UniMiB)
"""

import argparse
import os
import sys
import time

from data_loader import (
    load_scan_directory, generate_demo_acu_data, generate_demo_cls_data,
    ScanDataset
)
from acu_plots import (
    plot_acu_scan_overview, plot_acu_parameter, plot_acu_g_vs_r
)
from cls_plots import (
    plot_cls_scan_overview_2d, plot_cls_scan_overview_3d,
    plot_cls_2d_r_theta, plot_cls_2d_phi_theta,
    plot_cls_3d_surface, plot_cls_3d_scatter
)
from nonuniformity_map import (
    plot_g_vs_radius, plot_g_colormap_raw,
    plot_g_map_interpolated, plot_g_map_residual,
    plot_g_map_physics_model
)


# =============================================================================
# MAIN DRIVER
# =============================================================================

def run_all_plots(acu_ds: ScanDataset, cls_ds: ScanDataset,
                   output_dir: str, label: str = ""):
    """Run the complete set of non-uniformity plots."""
    
    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()
    
    print("=" * 70)
    print("TAO NON-UNIFORMITY ANALYSIS")
    print("=" * 70)
    print(f"  ACU: {acu_ds.n_positions} positions ({acu_ds.source})")
    print(f"  CLS: {cls_ds.n_positions} positions ({cls_ds.source})")
    print(f"  Output: {output_dir}")
    if label:
        print(f"  Label: {label}")
    print()
    
    # ─── (a) ACU PLOTS ────────────────────────────────────────────────────
    print("─── ACU Plots ───")
    
    plot_acu_scan_overview(acu_ds, os.path.join(output_dir, "acu_overview.png"),
                            label=label)
    
    for param in ['mean', 'sigma', 'resolution', 'ly']:
        plot_acu_parameter(acu_ds, param,
                            os.path.join(output_dir, f"acu_{param}.png"),
                            label=label)
    
    plot_acu_g_vs_r(acu_ds, os.path.join(output_dir, "acu_g_vs_r.png"),
                     label=label)
    
    # ─── (b) CLS PLOTS ────────────────────────────────────────────────────
    print("\n─── CLS Plots ───")
    
    # (b.i) + (b.ii) Overview colormaps
    plot_cls_scan_overview_2d(cls_ds,
                               os.path.join(output_dir, "cls_overview_2d_r_theta.png"),
                               label=label, plane="r_theta")
    plot_cls_scan_overview_2d(cls_ds,
                               os.path.join(output_dir, "cls_overview_2d_phi_theta.png"),
                               label=label, plane="phi_theta")
    
    # (b.iii) Overview 3D surfaces
    plot_cls_scan_overview_3d(cls_ds,
                               os.path.join(output_dir, "cls_overview_3d_r_theta.png"),
                               label=label, xy_plane="r_theta")
    plot_cls_scan_overview_3d(cls_ds,
                               os.path.join(output_dir, "cls_overview_3d_phi_theta.png"),
                               label=label, xy_plane="phi_theta")
    
    # Individual parameter plots
    for param in ['mean', 'sigma', 'resolution', 'ly']:
        # (b.i) 2D in (r, θ)
        plot_cls_2d_r_theta(cls_ds, param,
                             os.path.join(output_dir, f"cls_{param}_2d_r_theta.png"),
                             label=label)
        # (b.ii) 2D in (φ, θ)
        plot_cls_2d_phi_theta(cls_ds, param,
                               os.path.join(output_dir, f"cls_{param}_2d_phi_theta.png"),
                               label=label)
        # (b.iii) 3D surface (r, θ)
        plot_cls_3d_surface(cls_ds, param,
                             os.path.join(output_dir, f"cls_{param}_3d_r_theta.png"),
                             xy_plane="r_theta", label=label)
        # (b.iii) 3D surface (φ, θ)
        plot_cls_3d_surface(cls_ds, param,
                             os.path.join(output_dir, f"cls_{param}_3d_phi_theta.png"),
                             xy_plane="phi_theta", label=label)
        # (b.iv) 3D scatter in (r, θ, φ)
        plot_cls_3d_scatter(cls_ds, param,
                             os.path.join(output_dir, f"cls_{param}_3d_scatter.png"),
                             label=label)
    
    # ─── NON-UNIFORMITY MAP ──────────────────────────────────────────────
    print("\n─── Non-Uniformity Map g(r, θ) ───")
    
    # (a.i) g(r, θ) vs radius — raw data
    plot_g_vs_radius(acu_ds, cls_ds,
                      os.path.join(output_dir, "g_vs_radius_raw.png"),
                      label=label)
    
    # (a.ii) g(r, θ) colour map — raw data points
    plot_g_colormap_raw(acu_ds, cls_ds,
                         os.path.join(output_dir, "g_colormap_raw.png"),
                         label=label)
    
    # (b) Clough-Tocher interpolated map
    plot_g_map_interpolated(acu_ds, cls_ds,
                             os.path.join(output_dir, "g_map_interpolated_CT.png"),
                             label=label, method="clough_tocher")
    
    # Residual: g − g_ideal
    plot_g_map_residual(acu_ds, cls_ds,
                         os.path.join(output_dir, "g_map_residual.png"),
                         label=label)
    
    # Physics model comparison
    plot_g_map_physics_model(acu_ds, cls_ds,
                              os.path.join(output_dir, "g_map_physics_model.png"),
                              label=label)
    
    # ─── SUMMARY ─────────────────────────────────────────────────────────
    dt = time.time() - t0
    n_plots = sum(1 for f in os.listdir(output_dir)
                  if f.endswith('.png') and os.path.isfile(os.path.join(output_dir, f)))
    print(f"\n{'=' * 70}")
    print(f"DONE: {n_plots} plots generated in {dt:.1f}s → {output_dir}")
    print(f"{'=' * 70}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="TAO Non-Uniformity Analysis — Generate all plots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo mode (synthetic data):
  python main.py --demo --output-dir ./plots_demo

  # Real data from JSON fit results:
  python main.py --acu-dir /path/to/acu_json/ \\
                 --cls-dir /path/to/cls_json/ \\
                 --output-dir ./plots \\
                 --label "Commissioning Jan 2026"

  # With run-position CSV:
  python main.py --acu-dir /path/to/fits \\
                 --cls-dir /path/to/fits \\
                 --run-map run_positions.csv \\
                 --output-dir ./plots
"""
    )
    
    parser.add_argument("--demo", action="store_true",
                        help="Run with synthetic demo data (no input files needed)")
    parser.add_argument("--acu-dir", type=str, default=None,
                        help="Directory with ACU fit result JSON files")
    parser.add_argument("--cls-dir", type=str, default=None,
                        help="Directory with CLS fit result JSON files")
    parser.add_argument("--run-map", type=str, default=None,
                        help="CSV file mapping run numbers to positions")
    parser.add_argument("--output-dir", type=str, default="./nonunif_plots",
                        help="Output directory for plots (default: ./nonunif_plots)")
    parser.add_argument("--label", type=str, default="",
                        help="Label for plot titles")
    
    args = parser.parse_args()
    
    if args.demo:
        print("Running in DEMO mode (synthetic data)...")
        acu_ds = generate_demo_acu_data()
        cls_ds = generate_demo_cls_data()
        label = args.label or "Demo (synthetic data)"
    
    elif args.acu_dir and args.cls_dir:
        print(f"Loading ACU data from: {args.acu_dir}")
        acu_ds = load_scan_directory(args.acu_dir, system="ACU")
        print(f"  → {acu_ds.n_positions} positions loaded")
        
        print(f"Loading CLS data from: {args.cls_dir}")
        cls_ds = load_scan_directory(args.cls_dir, system="CLS")
        print(f"  → {cls_ds.n_positions} positions loaded")
        
        if acu_ds.n_positions == 0 or cls_ds.n_positions == 0:
            print("ERROR: No data loaded. Check input directories.")
            sys.exit(1)
        
        label = args.label
    
    else:
        parser.error("Provide --demo or both --acu-dir and --cls-dir")
    
    run_all_plots(acu_ds, cls_ds, args.output_dir, label=label)


if __name__ == "__main__":
    main()
