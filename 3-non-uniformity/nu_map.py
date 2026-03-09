#!/usr/bin/env python3
"""
nu_map.py  —  TAO non-uniformity maps, radial shells, and cross-checks

Reads the g(r,θ) data produced by ly_extractor.py (g_r_theta.npz or .csv)
and produces:

  1. r-z scatter map     : g(r,θ) colour-coded, with ACU (on-axis) and CLS
                           (off-axis) points overlaid
  2. 2-D interpolated map: g on a regular (r, θ) grid using scipy griddata
  3. Radial shells        : ⟨g(r)⟩ and σ(g(r)) averaged in radial bins,
                           ACU + CLS combined
  4. g vs z              : on-axis (θ≈0 and θ≈π) ACU profile
  5. g vs r (CLS)        : off-axis CLS profile with multiple θ slices
  6. Data / Simulation comparison bar chart : uses the g_real/g_sim ratios
                           stored in a secondary NPZ if present
  7. Non-uniformity deviation map : (g - 1) × 100 in % as function of r

All outputs go to --output-dir.

Usage:
  python nu_map.py \\
      --g-npz     ly_output/g_r_theta.npz \\
      --output-dir nu_maps/

  # With simulation reference (optional, for data/sim ratio plots):
  python nu_map.py \\
      --g-npz     ly_output/g_r_theta.npz \\
      --sim-npz   sim/g_r_theta_sim.npz \\
      --output-dir nu_maps/

Author: G. Ferrante
"""

import argparse
import csv
import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import MultipleLocator
from scipy.interpolate import griddata

# ─────────────────────────────────────────────────────────────────────────────
# Style
# ─────────────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 12,
    "axes.labelsize": 13,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "figure.dpi": 150,
})

R_MAX_MM      = 900.0    # TAO inner vessel radius [mm]
N_BINS_SHELLS = 18       # number of radial shells
CMAP_G        = "RdYlGn"  # colourmap for g maps (green=1, red=low)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_g_data(npz_path=None, csv_path=None):
    """
    Load g(r,θ) data.  Returns dict with arrays:
        r_mm, theta_rad, g, g_err, source  (ACU / CLS)
    """
    if npz_path and os.path.exists(npz_path):
        d = np.load(npz_path, allow_pickle=True)
        return {
            "r_mm":      d["r_mm"],
            "theta_rad": d["theta_rad"],
            "g":         d["g"],
            "g_err":     d["g_err"],
            "source":    d["source"].astype(str),
        }

    if csv_path and os.path.exists(csv_path):
        r, th, g, ge, src = [], [], [], [], []
        with open(csv_path, newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    r.append(float(row["r_mm"]))
                    th.append(float(row["theta_rad"]))
                    g.append(float(row["g"]))
                    ge.append(float(row["g_err"]))
                    src.append(row["source"])
                except (KeyError, ValueError):
                    pass
        return {
            "r_mm":      np.array(r),
            "theta_rad": np.array(th),
            "g":         np.array(g),
            "g_err":     np.array(ge),
            "source":    np.array(src),
        }

    raise FileNotFoundError(
        f"Cannot find g(r,θ) data: npz={npz_path}, csv={csv_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 1: r-z scatter  (colour = g value)
# ─────────────────────────────────────────────────────────────────────────────

def plot_rz_scatter(data, output_path):
    """
    Plot g(r, z) as a scatter map.
    For ACU: z = r_mm × sign(π − θ), x = 0 (on-axis).
    For CLS: z = r·cos(θ), r_perp = r·sin(θ).
    Colour = g value.
    """
    r   = data["r_mm"]
    th  = data["theta_rad"]
    g   = data["g"]
    src = data["source"]

    z_all    = r * np.cos(th)
    rperp_all = r * np.sin(th)

    vmin = max(0.85, g.min() - 0.01)
    vmax = min(1.05, g.max() + 0.01)
    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=1.0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(8, 9))

    # CLS (off-axis) – filled circles
    mask_cls = src == "CLS"
    if mask_cls.sum() > 0:
        sc_cls = ax.scatter(rperp_all[mask_cls], z_all[mask_cls],
                            c=g[mask_cls], cmap=CMAP_G, norm=norm,
                            s=60, marker="s", edgecolors="k", linewidths=0.4,
                            zorder=3, label="CLS (Cs-137)")

    # ACU (on-axis) – stars on the z axis
    mask_acu = src == "ACU"
    if mask_acu.sum() > 0:
        ax.scatter(np.zeros(mask_acu.sum()), z_all[mask_acu],
                   c=g[mask_acu], cmap=CMAP_G, norm=norm,
                   s=100, marker="*", edgecolors="k", linewidths=0.5,
                   zorder=4, label="ACU (Ge-68)")

    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=CMAP_G),
                        ax=ax, label="$g(r, \\theta)$", shrink=0.75)
    cbar.ax.axhline(1.0, color="k", lw=1)

    # Vessel boundary
    theta_v = np.linspace(0, 2 * np.pi, 360)
    ax.plot(R_MAX_MM * np.sin(theta_v), R_MAX_MM * np.cos(theta_v),
            "k--", lw=0.8, alpha=0.4, label="Vessel boundary")

    ax.set_xlabel("$r_{\\perp}$ [mm]  (off-axis)")
    ax.set_ylabel("$z$ [mm]  (along beam / ACU axis)")
    ax.set_title("Non-uniformity $g(r, \\theta)$  —  data scatter")
    ax.set_aspect("equal")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 2: 2-D interpolated map on (r, θ) grid
# ─────────────────────────────────────────────────────────────────────────────

def plot_2d_interpolated(data, output_path):
    r   = data["r_mm"]
    th  = data["theta_rad"]
    g   = data["g"]

    # Reflect ACU points to fill full θ range (they lie at θ=0 and π)
    r_aug  = np.concatenate([r,  r,  r])
    th_aug = np.concatenate([th, np.pi - th, 2 * np.pi - th])
    g_aug  = np.concatenate([g,  g,  g])

    r_grid  = np.linspace(0, R_MAX_MM, 100)
    th_grid = np.linspace(0, np.pi, 90)     # 0 to π (exploit azimuthal symmetry)
    Rg, Thg = np.meshgrid(r_grid, th_grid)

    g_interp = griddata(
        (r_aug, th_aug), g_aug,
        (Rg, Thg), method="cubic",
    )

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 7))
    # In polar projection: azimuthal angle = θ, radial = r
    im = ax.pcolormesh(Thg, Rg, g_interp,
                       cmap=CMAP_G,
                       vmin=max(0.85, g.min() - 0.01),
                       vmax=min(1.05, g.max() + 0.01),
                       shading="auto")
    fig.colorbar(im, ax=ax, label="$g(r, \\theta)$",
                 shrink=0.65, pad=0.08)
    ax.set_title("$g(r, \\theta)$ interpolated map\n(azimuthal symmetry assumed)",
                 pad=18)
    ax.set_theta_zero_location("N")
    ax.set_rlabel_position(22.5)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 3: Radial shells  ⟨g(r)⟩
# ─────────────────────────────────────────────────────────────────────────────

def plot_radial_shells(data, output_path, n_bins=N_BINS_SHELLS):
    r   = data["r_mm"]
    g   = data["g"]
    ge  = data["g_err"]
    src = data["source"]

    r_edges = np.linspace(0, R_MAX_MM, n_bins + 1)
    r_cent  = 0.5 * (r_edges[:-1] + r_edges[1:])
    g_mean, g_std, g_npts = [], [], []

    for i in range(n_bins):
        mask = (r >= r_edges[i]) & (r < r_edges[i + 1])
        if mask.sum() == 0:
            g_mean.append(np.nan); g_std.append(np.nan); g_npts.append(0)
            continue
        weights  = 1.0 / np.where(ge[mask] > 0, ge[mask] ** 2, 1.0)
        g_w      = np.average(g[mask], weights=weights)
        g_w_std  = np.sqrt(1.0 / weights.sum())   # weighted mean error
        g_spread = float(np.std(g[mask]))
        g_mean.append(g_w)
        g_std.append(float(np.sqrt(g_w_std ** 2 + g_spread ** 2)))
        g_npts.append(int(mask.sum()))

    g_mean = np.array(g_mean, dtype=float)
    g_std  = np.array(g_std,  dtype=float)

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.2]})
    ax, ax_dev = axes

    # Raw scatter
    col = {"ACU": "#1f77b4", "CLS": "#d62728"}
    for s in ("ACU", "CLS"):
        mk = src == s
        if mk.sum() > 0:
            ax.errorbar(r[mk], g[mk], yerr=ge[mk],
                        fmt=("o" if s == "ACU" else "s"),
                        color=col[s], ms=4, lw=0, elinewidth=0.8,
                        capsize=2, alpha=0.6, label=f"{s} individual")

    # Shell averages
    ok = np.isfinite(g_mean)
    ax.errorbar(r_cent[ok], g_mean[ok], yerr=g_std[ok],
                fmt="D-", color="k", ms=7, lw=2, capsize=4,
                label="Shell average (weighted)")

    ax.axhline(1.0, color="grey", lw=1, ls="--")
    ax.axhline(0.99, color="lightgrey", lw=0.8, ls=":")
    ax.axhline(1.01, color="lightgrey", lw=0.8, ls=":")
    ax.set_ylabel("$g(r)$")
    ax.set_title("TAO non-uniformity: radial shells  $\\langle g(r) \\rangle$")
    ax.legend(ncol=2)
    ax.grid(alpha=0.3)
    ax.set_ylim(0.88, 1.04)

    # Deviation from 1 in %
    dev = (g_mean - 1.0) * 100.0
    ax_dev.bar(r_cent[ok], dev[ok], width=(r_edges[1] - r_edges[0]) * 0.8,
               color=["#d62728" if d < 0 else "#2ca02c" for d in dev[ok]],
               alpha=0.75)
    ax_dev.axhline(0, color="k", lw=0.8)
    ax_dev.set_ylabel("$(g-1)$ [%]")
    ax_dev.set_xlabel("Radial distance $r$ [mm]")
    ax_dev.grid(alpha=0.25)
    ax_dev.yaxis.set_major_locator(MultipleLocator(1))

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 4: g vs z  (ACU on-axis)
# ─────────────────────────────────────────────────────────────────────────────

def plot_g_vs_z(data, output_path):
    src = data["source"]
    r   = data["r_mm"]
    th  = data["theta_rad"]
    g   = data["g"]
    ge  = data["g_err"]

    mask_acu = src == "ACU"
    if mask_acu.sum() == 0:
        print("  SKIP g-vs-z: no ACU data")
        return

    z_acu  = r[mask_acu] * np.cos(th[mask_acu])
    g_acu  = g[mask_acu]
    ge_acu = ge[mask_acu]

    # sort by z
    order = np.argsort(z_acu)
    z_acu  = z_acu[order]
    g_acu  = g_acu[order]
    ge_acu = ge_acu[order]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.errorbar(z_acu, g_acu, yerr=ge_acu,
                fmt="o-", color="#1f77b4", ms=6, lw=1.8,
                capsize=3, capthick=1.5, label="ACU Ge-68")
    ax.axhline(1.0, color="grey", lw=1, ls="--")
    ax.axvline(0, color="grey", lw=0.7, ls=":", alpha=0.5)
    ax.fill_between(z_acu, 0.99, 1.01, color="lightgrey", alpha=0.3, label="±1%")

    ax.set_xlabel("ACU z-position [mm]")
    ax.set_ylabel("$g(r, \\theta) = $ LY(z) / LY(0)")
    ax.set_title("Non-uniformity on-axis (ACU Ge-68): $g$ vs $z$")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 5: g vs r (CLS), multiple theta slices
# ─────────────────────────────────────────────────────────────────────────────

def plot_g_vs_r_cls(data, output_path, n_theta_slices=4):
    src = data["source"]
    r   = data["r_mm"]
    th  = data["theta_rad"]
    g   = data["g"]
    ge  = data["g_err"]

    mask_cls = src == "CLS"
    if mask_cls.sum() == 0:
        print("  SKIP g-vs-r CLS: no CLS data")
        return

    r_cls  = r[mask_cls]
    th_cls = th[mask_cls]
    g_cls  = g[mask_cls]
    ge_cls = ge[mask_cls]

    # partition into theta slices
    th_edges = np.linspace(th_cls.min() - 0.01, th_cls.max() + 0.01,
                           n_theta_slices + 1)
    colours  = plt.cm.plasma(np.linspace(0.1, 0.9, n_theta_slices))

    fig, ax = plt.subplots(figsize=(10, 5))

    for i in range(n_theta_slices):
        mask = (th_cls >= th_edges[i]) & (th_cls < th_edges[i + 1])
        if mask.sum() < 2:
            continue
        th_lab = np.rad2deg(np.median(th_cls[mask]))
        order  = np.argsort(r_cls[mask])
        ax.errorbar(r_cls[mask][order], g_cls[mask][order],
                    yerr=ge_cls[mask][order],
                    fmt="o-", color=colours[i], ms=4, lw=1.3,
                    capsize=2, label=f"θ ≈ {th_lab:.0f}°")

    ax.axhline(1.0, color="grey", lw=1, ls="--")
    ax.fill_between([0, R_MAX_MM], 0.99, 1.01,
                    color="lightgrey", alpha=0.3, label="±1%")
    ax.set_xlabel("Radial distance $r$ [mm]")
    ax.set_ylabel("$g(r, \\theta)$")
    ax.set_title("Non-uniformity off-axis (CLS Cs-137): $g$ vs $r$")
    ax.legend(ncol=2, fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlim(left=0)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 6: Data / simulation ratio
# ─────────────────────────────────────────────────────────────────────────────

def plot_data_sim_ratio(data_g, sim_data, output_path):
    """
    Compute point-wise ratio g_data / g_sim interpolated onto the data points.
    sim_data: dict with r_mm, theta_rad, g arrays (from --sim-npz).
    """
    r_d   = data_g["r_mm"]
    th_d  = data_g["theta_rad"]
    g_d   = data_g["g"]
    ge_d  = data_g["g_err"]
    src_d = data_g["source"]

    r_s  = sim_data["r_mm"]
    th_s = sim_data["theta_rad"]
    g_s  = sim_data["g"]

    # Interpolate simulation onto data points
    g_sim_at_data = griddata(
        (r_s, th_s), g_s,
        (r_d, th_d), method="linear",
        fill_value=np.nan,
    )

    ratio     = g_d / g_sim_at_data
    ratio_err = ge_d / g_sim_at_data

    fig, ax = plt.subplots(figsize=(10, 5))
    cols = {"ACU": "#1f77b4", "CLS": "#d62728"}
    for s in ("ACU", "CLS"):
        mk = src_d == s
        if mk.sum() == 0:
            continue
        order = np.argsort(r_d[mk])
        ax.errorbar(r_d[mk][order], ratio[mk][order],
                    yerr=ratio_err[mk][order],
                    fmt=("o" if s == "ACU" else "s"),
                    color=cols[s], ms=5, lw=1.2, capsize=3,
                    label=s)

    ax.axhline(1.0, color="k", lw=1, ls="--", label="data = sim")
    ax.fill_between([0, R_MAX_MM], 0.99, 1.01,
                    color="lightgrey", alpha=0.3, label="±1%")
    ax.set_xlabel("Radial distance $r$ [mm]")
    ax.set_ylabel("$g_{\\mathrm{data}} / g_{\\mathrm{sim}}$")
    ax.set_title("Non-uniformity: data / simulation ratio")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_ylim(0.92, 1.08)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot 7: (g-1) deviation map in %
# ─────────────────────────────────────────────────────────────────────────────

def plot_deviation_map(data, output_path):
    r   = data["r_mm"]
    th  = data["theta_rad"]
    g   = data["g"]

    dev_pct = (g - 1.0) * 100.0

    r_grid  = np.linspace(0, R_MAX_MM, 120)
    th_grid = np.linspace(0, np.pi, 90)
    Rg, Thg = np.meshgrid(r_grid, th_grid)

    # Augment for symmetry
    r_aug  = np.concatenate([r,  r,  r])
    th_aug = np.concatenate([th, np.pi - th, 2 * np.pi - th])
    d_aug  = np.concatenate([dev_pct, dev_pct, dev_pct])

    dev_interp = griddata((r_aug, th_aug), d_aug, (Rg, Thg), method="cubic")

    lim = max(4.0, np.nanpercentile(np.abs(dev_pct), 95))

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 7))
    im = ax.pcolormesh(Thg, Rg, dev_interp,
                       cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
    fig.colorbar(im, ax=ax, label="$(g-1)$ [%]", shrink=0.65, pad=0.08)
    ax.set_title("Non-uniformity deviation $(g-1)$ [%]\n(azimuthal symmetry assumed)",
                 pad=18)
    ax.set_theta_zero_location("N")
    ax.set_rlabel_position(22.5)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(data, output_dir):
    r   = data["r_mm"]
    g   = data["g"]
    src = data["source"]

    print("\n  Non-uniformity summary:")
    for s in ("ACU", "CLS", "all"):
        if s == "all":
            mk = np.ones(len(r), dtype=bool)
        else:
            mk = src == s

        if mk.sum() == 0:
            continue

        g_s = g[mk]
        r_s = r[mk]
        print(f"    {s:4s}: n={mk.sum():3d}  "
              f"g=[{g_s.min():.4f}, {g_s.max():.4f}]  "
              f"mean={g_s.mean():.4f}  rms={(g_s-1).std()*100:.2f}%  "
              f"r=[{r_s.min():.0f},{r_s.max():.0f}] mm")

    # Save summary to text file
    summary_path = os.path.join(output_dir, "nu_map_summary.txt")
    with open(summary_path, "w") as fh:
        for s in ("ACU", "CLS"):
            mk = src == s
            if mk.sum() == 0:
                continue
            g_s = g[mk]
            fh.write(f"[{s}]  n={mk.sum()}  "
                     f"g_min={g_s.min():.4f}  g_max={g_s.max():.4f}  "
                     f"mean={g_s.mean():.4f}  rms={(g_s-1).std()*100:.2f}%\n")
    print(f"\n  ✓  summary → {summary_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="TAO non-uniformity r-z maps, radial shells, cross-checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--g-npz",      default=None,
                        help="Path to g_r_theta.npz from ly_extractor.py")
    parser.add_argument("--g-csv",      default=None,
                        help="Fallback: path to g_r_theta.csv")
    parser.add_argument("--sim-npz",    default=None,
                        help="Optional: simulated g_r_theta.npz for data/sim ratio")
    parser.add_argument("--output-dir", default="nu_maps",
                        help="Output directory (default: nu_maps)")
    parser.add_argument("--n-shells",   type=int, default=N_BINS_SHELLS,
                        help=f"Number of radial shells (default: {N_BINS_SHELLS})")
    parser.add_argument("--n-theta-slices", type=int, default=4,
                        help="Number of θ slices for g-vs-r CLS plot (default: 4)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load data
    try:
        data = load_g_data(args.g_npz, args.g_csv)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("  Provide --g-npz or --g-csv (output of ly_extractor.py)")
        return

    print(f"\n  Loaded {len(data['r_mm'])} g(r,θ) points")
    print(f"    ACU: {(data['source']=='ACU').sum()}")
    print(f"    CLS: {(data['source']=='CLS').sum()}")

    # Load simulation if provided
    sim_data = None
    if args.sim_npz and os.path.exists(args.sim_npz):
        sim_data = np.load(args.sim_npz, allow_pickle=True)
        sim_data = {k: sim_data[k] for k in sim_data.files}
        print(f"  Loaded simulation: {len(sim_data['r_mm'])} points")

    # Generate all plots
    print(f"\n  Generating plots → {args.output_dir}")

    plot_rz_scatter(data,
                    os.path.join(args.output_dir, "g_rz_scatter.png"))

    if len(data["r_mm"]) > 5:
        plot_2d_interpolated(data,
                             os.path.join(args.output_dir, "g_2d_interp.png"))
        plot_deviation_map(data,
                           os.path.join(args.output_dir, "g_deviation_map.png"))

    plot_radial_shells(data,
                       os.path.join(args.output_dir, "g_radial_shells.png"),
                       n_bins=args.n_shells)

    plot_g_vs_z(data, os.path.join(args.output_dir, "g_vs_z.png"))

    plot_g_vs_r_cls(data,
                    os.path.join(args.output_dir, "g_vs_r_cls.png"),
                    n_theta_slices=args.n_theta_slices)

    if sim_data is not None:
        plot_data_sim_ratio(data, sim_data,
                            os.path.join(args.output_dir, "g_data_sim_ratio.png"))

    print_summary(data, args.output_dir)

    total = sum(1 for f in os.listdir(args.output_dir) if f.endswith(".png"))
    print(f"\n  Done — {total} plots in {args.output_dir}")


if __name__ == "__main__":
    main()
