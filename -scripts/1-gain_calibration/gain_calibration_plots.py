#!/usr/bin/env python3
"""
gain_calibration_plots.py
=========================
Plotting helpers for the TAO SiPM gain calibration pipeline.

Provides:
  classify()         — classify a fit result as 'good' / 'bad' / 'failed'
  _make_plot_dirs()  — create output directory tree
  plot_fit()         — per-channel ADC-fit PNG (with residuals) + linear-gain PNG
  plot_overview()    — per-model gain / chi² / R² distribution histograms

Plot style follows gain_calibration_old.py:
  · Data drawn as a black step line (not a bar chart)
  · Log y-axis, range [0.5, y_max × 200]
  · Colour-coded dashed vertical lines for each fitted PE peak
  · Info box (STATUS / quality / chi²/ndf) in the top-left corner
  · Residuals panel below the ADC-fit panel (same PNG)
  · Linear-gain plot saved as a separate PNG
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import gridspec

# ── Import shared names from the fit-models module ───────────────────────────
from gain_fit_models import MODEL_LABELS, peak_mu

# ── Histogram grid (must match gain_calibration.py) ──────────────────────────
BIN_WIDTH = 100
BIN_MAX   = 50_000
BINS      = np.arange(0, BIN_MAX + BIN_WIDTH, BIN_WIDTH)
BIN_CTRS  = (BINS[:-1] + BINS[1:]) / 2.0
N_BINS    = len(BIN_CTRS)

# ── Plot colours ──────────────────────────────────────────────────────────────
MODEL_COLORS = {
    'multigauss':    '#1f77b4',
    'multigauss_ct': '#9467bd',
    'multigauss_ap': '#ff7f0e',
    'emg':           '#2ca02c',
    'emg_ap':        '#d62728',
}

# Distinct colours for individual PE-peak dashed lines (up to 8 peaks)
PEAK_COLORS = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45',
]


# =============================================================================
# CLASSIFICATION  (thresholds are passed in so callers can override them)
# =============================================================================

def classify(r, gain_min, gain_max, chi2_max=100.0, r2_min=0.90):
    """
    Return 'good', 'bad', or 'failed' for a fit-result dict.

    Parameters
    ----------
    r        : result dict returned by fit_channel()
    gain_min / gain_max : expected gain window [ADC/PE]
    chi2_max : maximum χ²/ndf to be classified 'good'
    r2_min   : minimum linear R² to be classified 'good'
    """
    if not r.get('success') or r.get('gain', 0) <= 0:
        return 'failed'
    g = r['gain']
    if (gain_min <= g <= gain_max
            and r['chi2_dof'] <= chi2_max
            and r['r2_linear'] >= r2_min):
        return 'good'
    return 'bad'


# =============================================================================
# DIRECTORY SETUP
# =============================================================================

def _make_plot_dirs(out_dir, models):
    """Create plots/good|bad|failed/<model>/ subdirectory tree."""
    dirs = {}
    for cat in ('good', 'bad', 'failed'):
        for m in models:
            p = os.path.join(out_dir, 'plots', cat, m)
            os.makedirs(p, exist_ok=True)
            dirs[(cat, m)] = p
    return dirs


# =============================================================================
# PER-CHANNEL PLOTS
# =============================================================================

def plot_fit(ch_id, hist, model_results, detected_peaks,
             plot_dirs, gain_min, gain_max,
             chi2_max=100.0, r2_min=0.90):
    """
    Save two PNG files per (channel, model):

    ch_XXXXX_fit.png
        Top panel  : ADC histogram (step line) + model curve + coloured PE lines
        Bottom panel: residuals (data − fit)
    ch_XXXXX_linear.png
        μ_n vs n scatter + weighted linear fit + info box
    """
    for mname, r in model_results.items():
        cat  = classify(r, gain_min, gain_max, chi2_max, r2_min)
        base = os.path.join(plot_dirs[(cat, mname)], f'ch_{ch_id:05d}')

        fit_quality = cat.upper()
        title_color = {'good': 'green', 'bad': 'orange', 'failed': 'red'}.get(cat, 'red')
        model_lbl   = MODEL_LABELS.get(mname, mname)
        fit_color   = MODEL_COLORS.get(mname, 'steelblue')

        # ── 1) ADC-fit + residuals PNG ─────────────────────────────────────
        fig = plt.figure(figsize=(10, 7))
        gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)
        ax     = fig.add_subplot(gs[0])
        ax_res = fig.add_subplot(gs[1], sharex=ax)

        fig.suptitle(
            f'Channel {ch_id}  ({model_lbl}) — {fit_quality} Fit',
            fontsize=12, color=title_color, fontweight='bold',
        )

        # y-range: same as old code
        pos_mask  = (BIN_CTRS > 0) & (hist > 0)
        y_max_dat = float(np.max(hist[pos_mask])) if np.any(pos_mask) else 1.0
        y_floor   = 0.5

        # Data as black step line
        ax.step(BIN_CTRS, hist, where='mid', color='black',
                linewidth=0.6, alpha=0.85, label='Data')
        ax.set_yscale('log')
        ax.set_ylim(y_floor, y_max_dat * 200)
        ax.set_ylabel('Counts', fontsize=11)
        ax.set_xlim(0, BIN_MAX)
        ax.grid(True, alpha=0.25)

        if r.get('success') and r.get('y_fit') is not None:
            x_d = r.get('_x_data')
            y_m = r['y_fit']
            pf  = r.get('_par_fit', {})

            if x_d is not None and len(x_d) == len(y_m):
                # ── Fit curve ────────────────────────────────────────────
                fit_lbl = (
                    f"{model_lbl}\n"
                    f"Gain={r['gain']:.0f}±{r['gain_err']:.0f} ADC/PE\n"
                    f"χ²/ndf={r['chi2_dof']:.2f}  R²={r['r2_linear']:.3f}"
                )
                ax.plot(x_d, y_m, color=fit_color, lw=1.8, label=fit_lbl, zorder=3)

                # ── Coloured dashed PE-peak lines ─────────────────────────
                mu1_f  = pf.get('mu1', 0.0)
                gain_f = pf.get('gain', r['gain'])
                n_pk   = r['n_peaks']
                for i in range(n_pk):
                    mu_i = peak_mu(i + 1, mu1_f, gain_f)
                    c_i  = PEAK_COLORS[i % len(PEAK_COLORS)]
                    ax.axvline(mu_i, color=c_i, linestyle='--', linewidth=1.2,
                               alpha=0.75,
                               label=f'{i+1} PE: μ={mu_i:.0f}, σ={_peak_sigma_str(pf, i+1)}'
                               if i < 4 else f'{i+1} PE: μ={mu_i:.0f}')

                # ── Info box ──────────────────────────────────────────────
                info_text = (
                    f"STATUS: SUCCESS\n"
                    f"Method: {mname}\n"
                    f"Quality: {fit_quality}\n"
                    f"{'─'*20}\n"
                    f"Total Events: {int(np.sum(hist))}\n"
                    f"1 PE Used in Fit: Yes\n"
                    f"{'─'*20}\n"
                    f"Multi-Gauss χ²/ndf: {r['chi2_dof']:.2f}\n"
                )
                bbox_fc = 'lightgreen' if cat == 'good' else ('lightyellow' if cat == 'bad' else 'lightcoral')
                ax.text(0.02, 0.98, info_text,
                        transform=ax.transAxes,
                        va='top', ha='left', fontsize=8, family='monospace',
                        bbox=dict(boxstyle='round', facecolor=bbox_fc, alpha=0.75))

                # ── Residuals ─────────────────────────────────────────────
                fit_mask = (BIN_CTRS >= x_d[0]) & (BIN_CTRS <= x_d[-1])
                y_dw = hist[fit_mask]
                if len(y_dw) == len(y_m):
                    res = y_dw - y_m
                    ax_res.bar(x_d, res, width=BIN_WIDTH * 0.9,
                               color=fit_color, alpha=0.55)
                    ax_res.axhline(0, color='k', lw=0.8)
                    ax_res.grid(True, alpha=0.25)
        else:
            # Failed fit
            info_text = (
                f"STATUS: FAILED\n"
                f"Method: {mname}\n"
                f"Quality: {fit_quality}\n"
                f"{'─'*20}\n"
                f"Total Events: {int(np.sum(hist))}\n"
                f"Detected Peaks: {len(detected_peaks)}\n"
            )
            ax.text(0.02, 0.98, info_text,
                    transform=ax.transAxes,
                    va='top', ha='left', fontsize=8, family='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.75))
            ax.text(0.5, 0.5, 'FIT FAILED',
                    transform=ax.transAxes, ha='center', va='center',
                    color='red', fontsize=16, fontweight='bold')

        ax.legend(fontsize=7, ncol=2, loc='upper right')
        plt.setp(ax.get_xticklabels(), visible=False)
        ax_res.set_xlabel('ADC [counts]', fontsize=11)
        ax_res.set_ylabel('Residual',     fontsize=11)

        fig.savefig(base + '_fit.png', dpi=100, bbox_inches='tight')
        plt.close(fig)

        # ── 2) Linear gain PNG ─────────────────────────────────────────────
        if r.get('success') and r.get('n_peaks', 0) >= 2:
            pf    = r.get('_par_fit', {})
            mu1_f = pf.get('mu1', 0.0)
            gf    = pf.get('gain', r['gain'])
            n_pk  = r['n_peaks']
            ns_arr = np.arange(1, n_pk + 1)
            mu_arr = np.array([peak_mu(int(ni), mu1_f, gf) for ni in ns_arr])

            fig2, ax2 = plt.subplots(figsize=(7, 5))
            ax2.scatter(ns_arr, mu_arr, color='blue', zorder=3, s=60, label='Fitted Means')

            x_line = np.linspace(0.5, n_pk + 0.5, 200)
            y_line = r['intercept'] + r['gain'] * x_line
            ax2.plot(x_line, y_line, 'r-', lw=2.0,
                     label=f"μ = {r['intercept']:.0f} + {r['gain']:.0f}·n")

            lin_c2 = r.get('linear_chi2_dof', -1.0)
            gain_info = (
                f"μ = {r['intercept']:.0f} + {r['gain']:.0f}·n\n"
                f"{'─'*20}\n"
                f"Gain: {r['gain']:.0f} ± {r['gain_err']:.0f} ADC/PE\n"
                f"Intercept: {r['intercept']:.0f} ± {r['intercept_err']:.0f}\n"
                f"{'─'*20}\n"
                f"Linear R²: {r['r2_linear']:.3f}\n"
                f"Linear χ²/dof: {lin_c2:.2f}\n"
            )
            ax2.text(0.05, 0.97, gain_info,
                     transform=ax2.transAxes, va='top', ha='left',
                     fontsize=9, family='monospace',
                     bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.85))

            ax2.set_xlabel('Peak Number (PE)', fontsize=11)
            ax2.set_ylabel('ADC Value',        fontsize=11)
            ax2.set_title(
                f'Channel {ch_id}  {model_lbl} — Gain Calculation',
                fontsize=11, fontweight='bold',
            )
            ax2.legend(loc='lower right', fontsize=9)
            ax2.grid(True, alpha=0.3)
            plt.tight_layout()
            fig2.savefig(base + '_linear.png', dpi=100, bbox_inches='tight')
            plt.close(fig2)


def _peak_sigma_str(pf, n):
    """Format σ_n string from fit-param dict (best-effort)."""
    sp = pf.get('sigma_pe',   0.0)
    sb = pf.get('sigma_base', 0.0)
    if sp > 0:
        import math
        s = math.sqrt(max(n * sp**2 + sb**2, 1.0))
        return f'{s:.0f}'
    return '?'


# =============================================================================
# OVERVIEW DISTRIBUTION PLOTS  (one per model)
# =============================================================================

def plot_overview(all_results, models, out_dir, run_name,
                  gain_min, gain_max, chi2_max=100.0, r2_min=0.90):
    """
    Save per-model summary plots (2 rows × 4 columns):
      Row 0 – good channels: gain | χ²/ndf | R² | linear χ²/ndf
      Row 1 – bad  channels: same

    Style follows gain_calibration_old.py create_summary_plots().
    """
    ov_dir = os.path.join(out_dir, 'plots', 'overview')
    os.makedirs(ov_dir, exist_ok=True)

    for mname in models:
        good_res, bad_res = [], []
        for ch_id, mres in all_results.items():
            r   = mres.get(mname, {})
            cat = classify(r, gain_min, gain_max, chi2_max, r2_min)
            if cat == 'good':
                good_res.append(r)
            elif cat == 'bad':
                bad_res.append(r)

        fig, axes = plt.subplots(2, 4, figsize=(20, 10))
        n_good = len(good_res)
        n_bad  = len(bad_res)
        n_tot  = n_good + n_bad + sum(
            1 for mres in all_results.values()
            if classify(mres.get(mname, {}), gain_min, gain_max, chi2_max, r2_min) == 'failed'
        )

        pct_good = 100 * n_good / max(n_tot, 1)
        pct_bad  = 100 * n_bad  / max(n_tot, 1)

        col = MODEL_COLORS.get(mname, 'steelblue')
        fig.suptitle(f"{MODEL_LABELS.get(mname, mname)} — Run {run_name}",
                     fontsize=14, fontweight='bold')

        # ── Row 0: good ───────────────────────────────────────────────────────
        _ov_gain(axes[0,0], good_res,
                 f'Good Fits: Gain  (n={n_good}, {pct_good:.1f}%)',
                 'green', gain_min, gain_max)
        _ov_chi2(axes[0,1], good_res,
                 f'Good Fits: Multi-Gauss χ²/ndf', 'blue',
                 chi2_max)
        _ov_r2  (axes[0,2], good_res,
                 f'Good Fits: Linear R²', 'purple', r2_min)
        _ov_lin_chi2(axes[0,3], good_res,
                     f'Good Fits: Linear χ²/ndf', 'orange')

        # ── Row 1: bad ────────────────────────────────────────────────────────
        _ov_gain(axes[1,0], bad_res,
                 f'Bad Fits: Gain  (n={n_bad}, {pct_bad:.1f}%)',
                 'red', gain_min, gain_max)
        _ov_chi2(axes[1,1], bad_res,
                 f'Bad Fits: Multi-Gauss χ²/ndf', 'blue', chi2_max)
        _ov_r2  (axes[1,2], bad_res,
                 f'Bad Fits: Linear R²', 'purple', r2_min)
        _ov_lin_chi2(axes[1,3], bad_res,
                     f'Bad Fits: Linear χ²/ndf', 'orange')

        plt.tight_layout()
        out_path = os.path.join(ov_dir, f'{run_name}_{mname}_overview.png')
        fig.savefig(out_path, dpi=120, bbox_inches='tight')
        plt.close(fig)


# ── helpers for overview subplots ─────────────────────────────────────────────

def _finite(vals):
    return [v for v in vals if np.isfinite(v) and v > 0]


def _ov_gain(ax, rlist, title, color, gain_min, gain_max):
    g = _finite([r.get('gain', np.nan) for r in rlist])
    if g:
        mu, med, std = np.mean(g), np.median(g), np.std(g)
        lo = max(0, mu - 3*std); hi = mu + 3*std
        n_out = sum(1 for v in g if v < lo or v > hi)
        ax.hist(g, bins=50, range=(lo, hi), color=color, alpha=0.7, edgecolor='k')
        ax.axvline(mu,  color='red',    ls='--', lw=2, label=f'Mean {mu:.0f}')
        ax.axvline(med, color='orange', ls='--', lw=2, label=f'Med {med:.0f}')
        ax.axvline(gain_min, color='grey', ls=':', lw=1.5)
        ax.axvline(gain_max, color='grey', ls=':', lw=1.5)
        ax.set_yscale('log')
        ax.legend(fontsize=8)
        if n_out:
            ax.text(0.02, 0.97, f'Outside μ±3σ: {n_out}',
                    transform=ax.transAxes, va='top', fontsize=8,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel('Gain [ADC/PE]'); ax.set_ylabel('Channels')
    ax.grid(True, alpha=0.3)


def _ov_chi2(ax, rlist, title, color, chi2_max):
    c = _finite([r.get('chi2_dof', np.nan) for r in rlist])
    if c:
        mu, std = np.mean(c), np.std(c)
        hi = min(mu + 4*std, chi2_max * 1.5)
        n_out = sum(1 for v in c if v > hi)
        ax.hist(c, bins=50, range=(0, hi), color=color, alpha=0.7, edgecolor='k')
        ax.axvline(chi2_max, color='red', ls='--', lw=1.5, label=f'Cut={chi2_max}')
        ax.set_yscale('log')
        ax.legend(fontsize=8)
        if n_out:
            ax.text(0.98, 0.97, f'χ²/ndf > {hi:.0f}: {n_out}',
                    transform=ax.transAxes, va='top', ha='right', fontsize=8,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel('χ²/ndf'); ax.set_ylabel('Channels')
    ax.grid(True, alpha=0.3)


def _ov_r2(ax, rlist, title, color, r2_min):
    r2 = [r.get('r2_linear', np.nan) for r in rlist]
    r2 = [v for v in r2 if np.isfinite(v)]
    if r2:
        lo = max(0.0, min(r2) - 0.02)
        n_out = sum(1 for v in r2 if v < lo)
        ax.hist(r2, bins=50, range=(lo, 1.0), color=color, alpha=0.7, edgecolor='k')
        ax.axvline(r2_min, color='red', ls='--', lw=1.5, label=f'Cut={r2_min}')
        ax.set_yscale('log')
        ax.legend(fontsize=8)
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel('R²'); ax.set_ylabel('Channels')
    ax.grid(True, alpha=0.3)


def _ov_lin_chi2(ax, rlist, title, color):
    c = _finite([r.get('linear_chi2_dof', np.nan) for r in rlist])
    if c:
        mu, std = np.mean(c), np.std(c)
        hi = mu + 4*std
        n_out = sum(1 for v in c if v > hi)
        ax.hist(c, bins=50, range=(0, hi), color=color, alpha=0.7, edgecolor='k')
        ax.set_yscale('log')
        if n_out:
            ax.text(0.98, 0.97, f'> {hi:.0f}: {n_out}',
                    transform=ax.transAxes, va='top', ha='right', fontsize=8,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(title, fontweight='bold')
    ax.set_xlabel('Linear χ²/ndf'); ax.set_ylabel('Channels')
    ax.grid(True, alpha=0.3)
