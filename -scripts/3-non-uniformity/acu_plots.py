#!/usr/bin/env python3
"""
acu_plots.py  —  ACU scan visualisation

Produces 1D plots of calibration observables vs z-axis position:
  (a) Mean PE  vs z
  (b) Sigma PE vs z
  (c) Resolution [%] vs z
  (d) Light Yield [PE/MeV] vs z

ACU deploys ⁶⁸Ge (1.022 MeV) along the central z-axis of the TAO detector.

Author: G. Ferrante (INFN-MiB / UniMiB)
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

from data_loader import ScanDataset
from scan_config import ACRYLIC_INNER_RADIUS_MM, FV_RADIUS_MM


# =============================================================================
# STYLE
# =============================================================================

def _apply_style():
    plt.rcParams.update({
        'font.size': 12,
        'axes.labelsize': 13,
        'axes.titlesize': 14,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'legend.fontsize': 10,
        'figure.dpi': 150,
        'savefig.dpi': 200,
        'savefig.bbox': 'tight',
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
    })


# =============================================================================
# INDIVIDUAL PARAMETER PLOTS
# =============================================================================

def plot_acu_parameter(ds: ScanDataset, parameter: str,
                        output_path: str, label: str = "",
                        show_fv: bool = True):
    """
    Plot a single ACU scan parameter vs z-position.
    
    Args:
        ds: ACU scan dataset
        parameter: "mean", "sigma", "resolution", "ly", or "g"
        output_path: path for output PNG
        label: additional label for title
        show_fv: draw fiducial volume boundaries
    """
    _apply_style()
    
    z = ds.z_array()
    sort_idx = np.argsort(z)
    z = z[sort_idx]
    
    param_config = {
        'mean':       ('Mean PE',            'Mean PE [PE]',            ds.mean_array,       ds.mean_err_array),
        'sigma':      ('Sigma PE',           r'$\sigma$ [PE]',         ds.sigma_array,      ds.sigma_err_array),
        'resolution': ('Energy Resolution',  r'Resolution $\sigma/(\mu-DN)$ [%]', ds.resolution_array, ds.resolution_err_array),
        'ly':         ('Light Yield',        'LY [PE/MeV]',            ds.ly_array,         ds.ly_err_array),
        'g':          ('Relative LY g(z)',   'g(z) = LY(z)/LY(0)',     ds.g_array,          None),
    }
    
    if parameter not in param_config:
        raise ValueError(f"Unknown parameter '{parameter}'. Use: {list(param_config.keys())}")
    
    title_base, ylabel, val_fn, err_fn = param_config[parameter]
    
    val = val_fn()[sort_idx]
    err = err_fn()[sort_idx] if err_fn is not None else np.zeros_like(val)
    
    fig, ax = plt.subplots(figsize=(10, 5.5))
    
    # Data points with error bars
    ax.errorbar(z, val, yerr=err, fmt='o', markersize=5, capsize=3,
                color='#1f77b4', ecolor='#aec7e8', elinewidth=1.5,
                markeredgecolor='#1f77b4', markerfacecolor='#1f77b4',
                label=f'{ds.source} data', zorder=3)
    
    # Connect with line
    ax.plot(z, val, '-', color='#1f77b4', alpha=0.4, linewidth=1, zorder=2)
    
    # Fiducial volume boundaries
    if show_fv:
        for boundary in [-FV_RADIUS_MM, FV_RADIUS_MM]:
            ax.axvline(boundary, color='red', linestyle='--', alpha=0.5,
                       linewidth=1.2, label='FV boundary' if boundary == FV_RADIUS_MM else '')
    
    # Acrylic vessel boundaries
    for boundary in [-ACRYLIC_INNER_RADIUS_MM, ACRYLIC_INNER_RADIUS_MM]:
        ax.axvline(boundary, color='gray', linestyle=':', alpha=0.4,
                   linewidth=1.0, label='Vessel wall' if boundary == ACRYLIC_INNER_RADIUS_MM else '')
    
    # Center line
    ax.axvline(0, color='green', linestyle='-', alpha=0.3, linewidth=0.8)
    
    ax.set_xlabel('z position [mm]')
    ax.set_ylabel(ylabel)
    
    title = f'ACU {title_base} — {ds.source}'
    if label:
        title += f' — {label}'
    ax.set_title(title)
    
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.legend(loc='best', framealpha=0.8)
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# COMBINED 4-PANEL PLOT
# =============================================================================

def plot_acu_scan_overview(ds: ScanDataset, output_path: str,
                            label: str = "", show_fv: bool = True):
    """
    4-panel overview: mean, sigma, resolution, LY vs z.
    
    This is the primary ACU scan visualisation.
    """
    _apply_style()
    
    z = ds.z_array()
    sort_idx = np.argsort(z)
    z = z[sort_idx]
    
    panels = [
        ('Mean PE',       r'$\mu$ [PE]',                ds.mean_array()[sort_idx],       ds.mean_err_array()[sort_idx]),
        ('Sigma PE',      r'$\sigma$ [PE]',             ds.sigma_array()[sort_idx],      ds.sigma_err_array()[sort_idx]),
        ('Resolution',    r'$\sigma/(\mu-DN)$ [%]',     ds.resolution_array()[sort_idx], ds.resolution_err_array()[sort_idx]),
        ('Light Yield',   'LY [PE/MeV]',                ds.ly_array()[sort_idx],         ds.ly_err_array()[sort_idx]),
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    axes = axes.flatten()
    
    for ax, (title, ylabel, val, err) in zip(axes, panels):
        ax.errorbar(z, val, yerr=err, fmt='o-', markersize=4, capsize=2,
                    color='#1f77b4', ecolor='#aec7e8', elinewidth=1.2,
                    markeredgecolor='#1f77b4', linewidth=0.8, alpha=0.9)
        
        if show_fv:
            for bnd in [-FV_RADIUS_MM, FV_RADIUS_MM]:
                ax.axvline(bnd, color='red', ls='--', alpha=0.4, lw=1)
        for bnd in [-ACRYLIC_INNER_RADIUS_MM, ACRYLIC_INNER_RADIUS_MM]:
            ax.axvline(bnd, color='gray', ls=':', alpha=0.3, lw=0.8)
        ax.axvline(0, color='green', ls='-', alpha=0.2, lw=0.7)
        
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
    
    for ax in axes[2:]:
        ax.set_xlabel('z position [mm]')
    
    sup_title = f'ACU Scan Overview — {ds.source} ({ds.source_energy_mev:.3f} MeV)'
    if label:
        sup_title += f'\n{label}'
    fig.suptitle(sup_title, fontsize=14, y=1.02)
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# g(z) PLOT (relative light yield along z-axis)
# =============================================================================

def plot_acu_g_vs_r(ds: ScanDataset, output_path: str, label: str = ""):
    """
    Plot g(r) = LY(r)/LY(center) vs radius for ACU z-axis data.
    
    Since ACU is on-axis, r = |z|, and we fold top + bottom together.
    """
    _apply_style()
    
    ds.compute_g()
    
    r = ds.r_array()
    g = ds.g_array()
    z = ds.z_array()
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    
    # Left: g vs z (full axis)
    ax = axes[0]
    sort_z = np.argsort(z)
    ax.plot(z[sort_z], g[sort_z], 'o-', color='#1f77b4', markersize=5,
            linewidth=1, alpha=0.9, label='g(z)')
    ax.axhline(1.0, color='gray', ls='--', alpha=0.4)
    for bnd in [-FV_RADIUS_MM, FV_RADIUS_MM]:
        ax.axvline(bnd, color='red', ls='--', alpha=0.4, lw=1)
    ax.set_xlabel('z [mm]')
    ax.set_ylabel('g(z) = LY(z)/LY(0)')
    ax.set_title('Relative Light Yield vs z')
    ax.legend()
    
    # Right: g vs |z| (folded)
    ax = axes[1]
    # Top hemisphere (z ≥ 0) and bottom hemisphere (z < 0)
    mask_top = z >= 0
    mask_bot = z < 0
    
    if mask_top.sum() > 0:
        sort_t = np.argsort(r[mask_top])
        ax.plot(r[mask_top][sort_t], g[mask_top][sort_t], 'o-', color='#e74c3c',
                markersize=5, linewidth=1, alpha=0.8, label='Top (z ≥ 0)')
    if mask_bot.sum() > 0:
        sort_b = np.argsort(r[mask_bot])
        ax.plot(r[mask_bot][sort_b], g[mask_bot][sort_b], 's-', color='#2ecc71',
                markersize=5, linewidth=1, alpha=0.8, label='Bottom (z < 0)')
    
    ax.axhline(1.0, color='gray', ls='--', alpha=0.4)
    ax.axvline(FV_RADIUS_MM, color='red', ls='--', alpha=0.4, lw=1, label='FV boundary')
    ax.set_xlabel('r = |z| [mm]')
    ax.set_ylabel('g(r)')
    ax.set_title('Folded: Top vs Bottom')
    ax.legend()
    
    title = f'ACU g(z) — {ds.source}'
    if label:
        title += f' — {label}'
    fig.suptitle(title, fontsize=14, y=1.02)
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")
