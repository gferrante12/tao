#!/usr/bin/env python3
"""
cls_plots.py  —  CLS scan visualisation

Produces for each observable (mean, sigma, resolution, LY):
  (b.i)   2D colormap in the (r, θ) plane
  (b.ii)  2D colormap in the (φ, θ) plane
  (b.iii) 3D surface with observable on z-axis, xy = (r, θ) or (φ, θ)
  (b.iv)  3D scatter in (r, θ, φ) space with observable as colormap

CLS deploys ¹³⁷Cs (0.662 MeV) at 77 off-axis positions.

Author: G. Ferrante (INFN-MiB / UniMiB)
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata

from data_loader import ScanDataset
from scan_config import ACRYLIC_INNER_RADIUS_MM, FV_RADIUS_MM


# =============================================================================
# STYLE
# =============================================================================

def _apply_style():
    plt.rcParams.update({
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 13,
        'figure.dpi': 150,
        'savefig.dpi': 200,
        'savefig.bbox': 'tight',
    })


# =============================================================================
# PARAMETER LOOKUP
# =============================================================================

_PARAM_CONFIG = {
    'mean':       ('Mean PE',           r'$\mu$ [PE]',            'mean_array',       'mean_err_array',       'viridis'),
    'sigma':      ('Sigma PE',          r'$\sigma$ [PE]',         'sigma_array',      'sigma_err_array',      'plasma'),
    'resolution': ('Resolution',        r'Resolution [%]',        'resolution_array', 'resolution_err_array', 'inferno'),
    'ly':         ('Light Yield',       'LY [PE/MeV]',            'ly_array',         'ly_err_array',         'cividis'),
    'g':          ('Relative LY g',     'g(r,θ)',                  'g_array',          None,                   'RdYlGn'),
}


def _get_param_data(ds, parameter):
    cfg = _PARAM_CONFIG[parameter]
    val = getattr(ds, cfg[2])()
    err = getattr(ds, cfg[3])() if cfg[3] else np.zeros_like(val)
    return cfg[0], cfg[1], val, err, cfg[4]


# =============================================================================
# (b.i) 2D COLORMAP IN (r, θ) PLANE
# =============================================================================

def plot_cls_2d_r_theta(ds: ScanDataset, parameter: str,
                         output_path: str, label: str = "",
                         interpolate: bool = True,
                         n_grid: int = 100):
    """
    2D colormap of a CLS observable in the (r, θ) plane.
    
    Points are plotted as scatter markers over an optional interpolated background.
    """
    _apply_style()
    title_base, cbar_label, val, err, cmap_name = _get_param_data(ds, parameter)
    
    r     = ds.r_array()
    theta = ds.theta_array()
    
    fig, ax = plt.subplots(figsize=(9, 6.5))
    
    if interpolate and len(r) >= 4:
        # Interpolate on a regular grid
        r_grid     = np.linspace(r.min() * 0.9, r.max() * 1.1, n_grid)
        theta_grid = np.linspace(theta.min() - 5, theta.max() + 5, n_grid)
        R_g, Th_g  = np.meshgrid(r_grid, theta_grid)
        
        V_g = griddata((r, theta), val, (R_g, Th_g), method='cubic')
        
        im = ax.pcolormesh(r_grid, theta_grid, V_g, cmap=cmap_name,
                           shading='auto', alpha=0.85)
    else:
        im = None
    
    # Scatter data points on top
    sc = ax.scatter(r, theta, c=val, cmap=cmap_name, s=60, edgecolors='k',
                    linewidths=0.8, zorder=5)
    
    cbar = fig.colorbar(sc if im is None else im, ax=ax, pad=0.02)
    cbar.set_label(cbar_label)
    
    # FV boundary arc
    fv_theta = np.linspace(0, 180, 200)
    ax.plot(np.full_like(fv_theta, FV_RADIUS_MM), fv_theta,
            'r--', lw=1.5, alpha=0.6, label='FV boundary')
    
    ax.set_xlabel('r [mm]')
    ax.set_ylabel(r'$\theta$ [deg]')
    ax.set_title(f'CLS {title_base} — (r, θ) plane — {ds.source}' +
                 (f'\n{label}' if label else ''))
    ax.legend(loc='upper right', fontsize=9)
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# (b.ii) 2D COLORMAP IN (φ, θ) PLANE
# =============================================================================

def plot_cls_2d_phi_theta(ds: ScanDataset, parameter: str,
                           output_path: str, label: str = "",
                           interpolate: bool = True):
    """
    2D colormap of a CLS observable in the (φ, θ) plane.
    
    Note: CLS is typically in a single half-plane (fixed φ), so this
    plot may show limited φ variation. With multiple CLS cables or
    azimuthal symmetry assumptions, the coverage can be extended.
    """
    _apply_style()
    title_base, cbar_label, val, err, cmap_name = _get_param_data(ds, parameter)
    
    phi   = ds.phi_array()
    theta = ds.theta_array()
    
    fig, ax = plt.subplots(figsize=(9, 6.5))
    
    # Check if we have meaningful φ variation
    phi_range = phi.max() - phi.min()
    
    if phi_range > 5 and interpolate and len(phi) >= 4:
        n_grid = 80
        phi_grid   = np.linspace(phi.min() - 5, phi.max() + 5, n_grid)
        theta_grid = np.linspace(theta.min() - 5, theta.max() + 5, n_grid)
        P_g, Th_g  = np.meshgrid(phi_grid, theta_grid)
        V_g = griddata((phi, theta), val, (P_g, Th_g), method='cubic')
        
        im = ax.pcolormesh(phi_grid, theta_grid, V_g, cmap=cmap_name,
                           shading='auto', alpha=0.85)
        cbar = fig.colorbar(im, ax=ax, pad=0.02)
    else:
        cbar = None
    
    sc = ax.scatter(phi, theta, c=val, cmap=cmap_name, s=60, edgecolors='k',
                    linewidths=0.8, zorder=5)
    
    if cbar is None:
        cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label(cbar_label)
    
    if phi_range < 5:
        ax.text(0.5, 0.02,
                f'Note: CLS in single half-plane (φ ≈ {phi.mean():.0f}°)',
                transform=ax.transAxes, ha='center', fontsize=9,
                style='italic', color='gray')
    
    ax.set_xlabel(r'$\phi$ [deg]')
    ax.set_ylabel(r'$\theta$ [deg]')
    ax.set_title(f'CLS {title_base} — (φ, θ) plane — {ds.source}' +
                 (f'\n{label}' if label else ''))
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# (b.iii) 3D SURFACE PLOT
# =============================================================================

def plot_cls_3d_surface(ds: ScanDataset, parameter: str,
                         output_path: str, xy_plane: str = "r_theta",
                         label: str = "", elev: float = 25, azim: float = -60):
    """
    3D surface plot with observable on z-axis.
    
    Args:
        xy_plane: "r_theta" or "phi_theta"
        elev, azim: 3D view angles
    """
    _apply_style()
    title_base, zbar_label, val, err, cmap_name = _get_param_data(ds, parameter)
    
    if xy_plane == "r_theta":
        x = ds.r_array()
        y = ds.theta_array()
        xlabel = 'r [mm]'
        ylabel = r'$\theta$ [deg]'
    elif xy_plane == "phi_theta":
        x = ds.phi_array()
        y = ds.theta_array()
        xlabel = r'$\phi$ [deg]'
        ylabel = r'$\theta$ [deg]'
    else:
        raise ValueError(f"Unknown xy_plane '{xy_plane}'")
    
    fig = plt.figure(figsize=(11, 7.5))
    ax = fig.add_subplot(111, projection='3d')
    
    # Attempt triangulated surface
    try:
        from matplotlib.tri import Triangulation
        tri = Triangulation(x, y)
        ax.plot_trisurf(x, y, val, triangles=tri.triangles,
                        cmap=cmap_name, alpha=0.7, edgecolor='none')
    except Exception:
        pass
    
    # Scatter points on top
    sc = ax.scatter(x, y, val, c=val, cmap=cmap_name, s=40,
                    edgecolors='k', linewidths=0.5, zorder=5)
    
    cbar = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.1)
    cbar.set_label(zbar_label)
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_zlabel(zbar_label)
    ax.view_init(elev=elev, azim=azim)
    
    ax.set_title(f'CLS {title_base} — 3D ({xy_plane.replace("_", ", ")}) — {ds.source}' +
                 (f'\n{label}' if label else ''))
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# (b.iv) 3D SCATTER IN (r, θ, φ) SPACE WITH COLOR
# =============================================================================

def plot_cls_3d_scatter(ds: ScanDataset, parameter: str,
                         output_path: str, label: str = "",
                         elev: float = 20, azim: float = -50):
    """
    3D scatter plot in (r, θ, φ) space with observable as color.
    """
    _apply_style()
    title_base, cbar_label, val, err, cmap_name = _get_param_data(ds, parameter)
    
    r     = ds.r_array()
    theta = ds.theta_array()
    phi   = ds.phi_array()
    
    fig = plt.figure(figsize=(11, 7.5))
    ax = fig.add_subplot(111, projection='3d')
    
    sc = ax.scatter(r, theta, phi, c=val, cmap=cmap_name, s=50,
                    edgecolors='k', linewidths=0.5, alpha=0.9)
    
    cbar = fig.colorbar(sc, ax=ax, shrink=0.6, pad=0.1)
    cbar.set_label(cbar_label)
    
    ax.set_xlabel('r [mm]')
    ax.set_ylabel(r'$\theta$ [deg]')
    ax.set_zlabel(r'$\phi$ [deg]')
    ax.view_init(elev=elev, azim=azim)
    
    ax.set_title(f'CLS {title_base} — 3D (r, θ, φ) — {ds.source}' +
                 (f'\n{label}' if label else ''))
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# COMBINED OVERVIEW: 4-panel 2D colormaps
# =============================================================================

def plot_cls_scan_overview_2d(ds: ScanDataset, output_path: str,
                               label: str = "", plane: str = "r_theta"):
    """
    4-panel overview: 2D colormaps of (mean, sigma, resolution, LY)
    in either the (r, θ) or (φ, θ) plane.
    """
    _apply_style()
    
    if plane == "r_theta":
        x = ds.r_array()
        y = ds.theta_array()
        xlabel = 'r [mm]'
        ylabel = r'$\theta$ [deg]'
    else:
        x = ds.phi_array()
        y = ds.theta_array()
        xlabel = r'$\phi$ [deg]'
        ylabel = r'$\theta$ [deg]'
    
    params = ['mean', 'sigma', 'resolution', 'ly']
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for ax, param in zip(axes, params):
        title_base, cbar_label, val, err, cmap_name = _get_param_data(ds, param)
        
        sc = ax.scatter(x, y, c=val, cmap=cmap_name, s=50, edgecolors='k',
                        linewidths=0.5)
        cbar = fig.colorbar(sc, ax=ax, pad=0.02)
        cbar.set_label(cbar_label, fontsize=9)
        
        if plane == "r_theta":
            ax.axvline(FV_RADIUS_MM, color='red', ls='--', alpha=0.5, lw=1)
        
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title_base, fontsize=11)
    
    sup = f'CLS Scan Overview — ({plane.replace("_", ", ")}) — {ds.source}'
    if label:
        sup += f'\n{label}'
    fig.suptitle(sup, fontsize=13, y=1.02)
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")


# =============================================================================
# COMBINED OVERVIEW: 4-panel 3D surfaces
# =============================================================================

def plot_cls_scan_overview_3d(ds: ScanDataset, output_path: str,
                               label: str = "", xy_plane: str = "r_theta"):
    """
    4-panel overview: 3D surface plots of (mean, sigma, resolution, LY).
    """
    _apply_style()
    
    if xy_plane == "r_theta":
        x = ds.r_array()
        y = ds.theta_array()
        xlabel = 'r [mm]'
        ylabel = r'$\theta$ [deg]'
    else:
        x = ds.phi_array()
        y = ds.theta_array()
        xlabel = r'$\phi$ [deg]'
        ylabel = r'$\theta$ [deg]'
    
    params = ['mean', 'sigma', 'resolution', 'ly']
    
    fig = plt.figure(figsize=(16, 12))
    
    for i, param in enumerate(params):
        ax = fig.add_subplot(2, 2, i + 1, projection='3d')
        title_base, zbar_label, val, err, cmap_name = _get_param_data(ds, param)
        
        sc = ax.scatter(x, y, val, c=val, cmap=cmap_name, s=35,
                        edgecolors='k', linewidths=0.4, alpha=0.9)
        
        # Try triangulated surface
        try:
            from matplotlib.tri import Triangulation
            tri = Triangulation(x, y)
            ax.plot_trisurf(x, y, val, triangles=tri.triangles,
                            cmap=cmap_name, alpha=0.5, edgecolor='none')
        except Exception:
            pass
        
        cbar = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.08)
        cbar.set_label(zbar_label, fontsize=8)
        
        ax.set_xlabel(xlabel, fontsize=9)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_zlabel(zbar_label, fontsize=8)
        ax.set_title(title_base, fontsize=10)
        ax.view_init(elev=25, azim=-60)
    
    sup = f'CLS 3D Overview — ({xy_plane.replace("_", ", ")}) — {ds.source}'
    if label:
        sup += f'\n{label}'
    fig.suptitle(sup, fontsize=13, y=1.01)
    
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    print(f"  ✓ {os.path.basename(output_path)}")
