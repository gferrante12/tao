#!/usr/bin/env python3
"""
gain_calibration.py
===================
Main script: reads ROOT histograms, runs all four fit models on up to 8 PE peaks,
saves plots (sorted good/bad/failed), and writes a summary TXT.

Usage:
    python gain_calibration.py --input <file.root> \
        [--hist_prefix "h_adc_ch"] \
        [--channels 0-8063]    \
        [--model MULTI_GAUSS,GAUSS_CT,EMG,GEN_POISSON] \
        [--n_peaks 6] \
        [--sample 50] \
        [--output_dir results] \
        [--erf_threshold None]

No scipy, no TSpectrum — all minimization via MIGRAD (Minuit2).
"""

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)

import os
import sys
import json
import argparse
import random
import numpy as np
import math
from collections import defaultdict

# Import our function library
from gain_fit_functions import (
    MODEL_NAMES, get_model_func, estimate_initial_params,
    MigradFitter, find_peaks_manual, linear_gain_fit,
    extract_gain_and_sigma_from_fit, apply_erf_threshold,
    afterpulse_component
)

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────
CHI2NDF_GOOD = 5.0    # chi2/ndf < this → GOOD
CHI2NDF_BAD  = 20.0   # < this → BAD, else FAILED
MIN_ENTRIES  = 5000   # minimum events per channel (from file:28)
MIN_PEAKS    = 3      # minimum peaks to attempt fit
MAX_PEAKS    = 8      # maximum PE peaks to fit

# ─────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",        required=True,
                        help="Input ROOT file with ADC histograms")
    parser.add_argument("--hist_prefix",  default="h_adc_ch",
                        help="Histogram name prefix (e.g. h_adc_ch0001)")
    parser.add_argument("--channels",     default=None,
                        help="Channel range string e.g. '0-8063' or '0,1,5'")
    parser.add_argument("--model",        default=",".join(MODEL_NAMES),
                        help="Comma-separated list of models to run")
    parser.add_argument("--n_peaks",      type=int, default=6,
                        help="Target number of PE peaks to fit (max 8)")
    parser.add_argument("--sample",       type=int, default=50,
                        help="Max channels per category (good/bad/failed) to plot")
    parser.add_argument("--output_dir",   default="gain_calib_results",
                        help="Output directory for plots and summary")
    parser.add_argument("--erf_threshold", type=float, default=None,
                        help="ADC threshold for COTI erf correction on 1PE peak")
    parser.add_argument("--erf_sigma",    type=float, default=None,
                        help="Sigma of erf threshold transition")
    parser.add_argument("--use_likelihood", action="store_true",
                        help="Use binned Poisson NLL instead of chi2")
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────
# Histogram loading
# ─────────────────────────────────────────────────────────────────

def load_channels(root_file, prefix, channel_list):
    """Load ADC histograms from ROOT file. Returns dict {ch_id: TH1}."""
    hists = {}
    for ch in channel_list:
        name = f"{prefix}{ch:04d}"
        h = root_file.Get(name)
        if h and isinstance(h, ROOT.TH1):
            if h.GetEntries() >= MIN_ENTRIES:
                hists[ch] = h
    return hists


def parse_channel_list(channels_str, root_file, prefix):
    """Parse channel string or auto-detect from ROOT file."""
    if channels_str is None:
        keys = [k.GetName() for k in root_file.GetListOfKeys()]
        chs = []
        for k in keys:
            if k.startswith(prefix):
                try:
                    chs.append(int(k[len(prefix):]))
                except ValueError:
                    pass
        return sorted(chs)
    if "-" in channels_str and "," not in channels_str:
        lo, hi = channels_str.split("-")
        return list(range(int(lo), int(hi)+1))
    return [int(x) for x in channels_str.split(",")]


# ─────────────────────────────────────────────────────────────────
# Extract arrays from TH1
# ─────────────────────────────────────────────────────────────────

def th1_to_arrays(h):
    """Convert TH1 to (x_centers, y_counts) numpy arrays, ignoring empty bins."""
    n = h.GetNbinsX()
    x = np.array([h.GetBinCenter(i) for i in range(1, n+1)])
    y = np.array([h.GetBinContent(i) for i in range(1, n+1)])
    return x, y


# ─────────────────────────────────────────────────────────────────
# Fit a single channel with a given model
# ─────────────────────────────────────────────────────────────────

def fit_channel(x, y, model_name, n_peaks_target,
                erf_threshold=None, erf_sigma=None,
                use_likelihood=False):
    """
    Run full fit pipeline for one channel / one model.
    Returns dict with all results, or None on failure.
    """
    # 1. Find peaks
    dx = x[1] - x[0] if len(x) > 1 else 1.0
    peaks = find_peaks_manual(x, y, min_prominence=0.03,
                              min_dist_adc=dx * 20)
    if len(peaks) < MIN_PEAKS:
        return {"status": "FAILED", "reason": "too_few_peaks",
                "n_peaks_found": len(peaks)}

    n_peaks = min(len(peaks), n_peaks_target, MAX_PEAKS)
    peaks = peaks[:n_peaks]

    # 2. Build model function (with optional erf threshold)
    raw_model = get_model_func(model_name, n_peaks)

    def model_func(xarr, params):
        val = raw_model(xarr, params)
        if erf_threshold is not None:
            sig_thr = erf_sigma if erf_sigma else (peaks[0][1] * 0.1)
            val = apply_erf_threshold(val, xarr, erf_threshold, sig_thr)
        return val

    # 3. Estimate initial parameters
    p0 = estimate_initial_params(peaks, model_name, x, y)
    if p0 is None:
        return {"status": "FAILED", "reason": "param_init_failed"}

    # 4. Restrict fit range: from left edge of 1PE to right edge of last found peak
    x_lo = max(x[0], peaks[0][1] - 3 * (peaks[0][1] * 0.15))
    x_hi = min(x[-1], peaks[-1][1] + 3 * (peaks[0][1] * 0.15))
    mask = (x >= x_lo) & (x <= x_hi) & (y > 0)
    if np.sum(mask) < 5:
        return {"status": "FAILED", "reason": "too_few_bins_in_range"}

    x_fit = x[mask]
    y_fit = y[mask]

    # 5. Run MIGRAD
    fitter = MigradFitter(
        x_fit, y_fit, model_func,
        p0["param_names"], p0["init_vals"],
        p0["step_sizes"], p0["lower_bounds"], p0["upper_bounds"],
        use_likelihood=use_likelihood
    )
    status = fitter.fit()

    if fitter.result is None:
        return {"status": "FAILED", "reason": "migrad_no_result"}

    # 6. Extract gain via linear fit on peak means
    fit_p = fitter.result
    G_direct = fit_p[2]  # "G" is always index 2 in all models
    mu1 = fit_p[1]
    peak_numbers = list(range(1, n_peaks + 1))
    peak_means_fit = [mu1 + (n - 1) * G_direct for n in peak_numbers]
    # Use peak finding to get observed mean errors (approximate as sigma/sqrt(N))
    sigma_spe_fit = abs(fit_p[3])
    peak_mean_errs = [sigma_spe_fit / max(math.sqrt(peaks[i][2]), 1.0)
                      for i in range(n_peaks)]

    gain_info = extract_gain_and_sigma_from_fit(
        model_name, fit_p, n_peaks,
        peak_numbers=peak_numbers,
        peak_means_from_fit=peak_means_fit,
        peak_mean_errors=peak_mean_errs
    )

    # 7. Classify quality
    chi2ndf = fitter.chi2ndf
    if status == "FAILED" or chi2ndf > CHI2NDF_BAD or G_direct <= 0:
        quality = "FAILED"
    elif chi2ndf > CHI2NDF_GOOD:
        quality = "BAD"
    else:
        quality = "GOOD"

    return {
        "status": status,
        "quality": quality,
        "model": model_name,
        "n_peaks": n_peaks,
        "peaks_found": [(float(p[1]), float(p[2])) for p in peaks],
        "fit_params": fit_p,
        "fit_errors": fitter.errors,
        "param_names": p0["param_names"],
        "chi2": fitter.chi2,
        "ndf": fitter.ndf,
        "chi2ndf": chi2ndf,
        "gain_direct": gain_info["gain_direct"],
        "gain_linear": gain_info.get("gain_linear"),
        "gain_linear_err": gain_info.get("gain_linear_err"),
        "R2_linear": gain_info.get("R2_linear"),
        "chi2_linear": gain_info.get("chi2_linear"),
        "ndf_linear": gain_info.get("ndf_linear"),
        "sigma_spe": gain_info["sigma_spe"],
        "P_ct": gain_info["P_ct"],
        "tau": gain_info["tau"],
        "lam": gain_info["lam"],
        "mu_gp": gain_info["mu_gp"],
        "x_fit": x_fit,
        "y_fit": y_fit,
        "fit_func": model_func,
    }


# ─────────────────────────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────────────────────────

COLORS = {
    "MULTI_GAUSS":  ROOT.kBlue + 1,
    "GAUSS_CT":     ROOT.kRed  + 1,
    "EMG":          ROOT.kGreen + 2,
    "GEN_POISSON":  ROOT.kMagenta + 1,
}


def make_output_dirs(base, models, categories):
    dirs = {}
    for model in models:
        for cat in categories:
            d = os.path.join(base, model, cat)
            os.makedirs(d, exist_ok=True)
            dirs[(model, cat)] = d
    return dirs


def plot_channel_fit(ch_id, h_root, result, out_path):
    """
    Two-panel plot: left = ADC histogram + fit overlay (log scale),
    right = linear gain fit.
    """
    if result is None or result.get("quality") == "FAILED":
        return

    c = ROOT.TCanvas(f"c_{ch_id}", f"Channel {ch_id}", 1400, 600)
    c.Divide(2, 1)

    # — Left: ADC spectrum + model overlay —
    c.cd(1)
    ROOT.gPad.SetLogy(1)
    ROOT.gPad.SetLeftMargin(0.12)

    h_root.SetLineColor(ROOT.kBlack)
    h_root.SetLineWidth(1)
    h_root.GetXaxis().SetTitle("ADC Value")
    h_root.GetYaxis().SetTitle("Counts")
    h_root.Draw("HIST")

    # Overlay fit curve using TF1 defined from numpy arrays
    x_fit = result["x_fit"]
    y_fit_model = result["fit_func"](x_fit, result["fit_params"])
    n_pts = len(x_fit)
    gr = ROOT.TGraph(n_pts,
                     array('d', x_fit.tolist()),
                     array('d', y_fit_model.tolist()))
    gr.SetLineColor(COLORS.get(result["model"], ROOT.kBlue))
    gr.SetLineWidth(2)
    gr.Draw("L SAME")

    # Mark peak positions
    for (mu_pk, A_pk) in result["peaks_found"]:
        line = ROOT.TLine(mu_pk, h_root.GetMinimum()*1.5, mu_pk, A_pk*1.1)
        line.SetLineColor(ROOT.kOrange+1)
        line.SetLineStyle(2)
        line.SetLineWidth(1)
        line.Draw()

    # Info box
    model = result["model"]
    chi2ndf = result["chi2ndf"]
    G = result["gain_direct"]
    quality = result["quality"]
    info_str = (f"Model: {model}  Quality: {quality}\n"
                f"Gain: {G:.1f} ADC/PE\n"
                f"chi2/ndf: {chi2ndf:.2f}")
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextSize(0.033)
    latex.DrawLatex(0.14, 0.88, info_str.split("\n")[0])
    latex.DrawLatex(0.14, 0.83, info_str.split("\n")[1])
    latex.DrawLatex(0.14, 0.78, info_str.split("\n")[2])
    if result.get("P_ct") is not None:
        latex.DrawLatex(0.14, 0.73, f"P_ct: {result['P_ct']:.3f}")
    elif result.get("tau") is not None:
        latex.DrawLatex(0.14, 0.73, f"tau: {result['tau']:.1f} ADC")
    elif result.get("lam") is not None:
        latex.DrawLatex(0.14, 0.73, f"lambda(IOCT): {result['lam']:.3f}")

    # — Right: linear gain fit —
    c.cd(2)
    ROOT.gPad.SetLeftMargin(0.14)
    n_peaks = result["n_peaks"]
    G_direct = result["gain_direct"]
    mu1 = result["fit_params"][1]
    peak_ns = list(range(1, n_peaks + 1))
    peak_mus = [mu1 + (n - 1) * G_direct for n in peak_ns]

    G_lin, G_lin_err, off, off_err, chi2_lin, ndf_lin, R2 = linear_gain_fit(peak_ns, peak_mus)

    gr_lin = ROOT.TGraph(n_peaks,
                         array('d', [float(n) for n in peak_ns]),
                         array('d', [float(m) for m in peak_mus]))
    gr_lin.SetMarkerStyle(20)
    gr_lin.SetMarkerColor(ROOT.kBlue+1)
    gr_lin.SetMarkerSize(1.2)
    gr_lin.SetTitle(f"Gain Calculation;Peak Number (PE);ADC Value")
    gr_lin.Draw("AP")

    # Linear fit line
    x_line = array('d', [0.5, float(n_peaks) + 0.5])
    y_line = array('d', [off + G_lin * 0.5, off + G_lin * (n_peaks + 0.5)])
    gr_fit = ROOT.TGraph(2, x_line, y_line)
    gr_fit.SetLineColor(ROOT.kRed+1)
    gr_fit.SetLineWidth(2)
    gr_fit.Draw("L SAME")

    latex2 = ROOT.TLatex()
    latex2.SetNDC()
    latex2.SetTextSize(0.035)
    latex2.DrawLatex(0.16, 0.88, f"#mu = {off:.0f} + {G_lin:.0f}#times n")
    latex2.DrawLatex(0.16, 0.83, f"Gain: {G_lin:.1f} #pm {G_lin_err:.1f} ADC/PE")
    latex2.DrawLatex(0.16, 0.78, f"R^{{2}}: {R2:.4f}   #chi^{{2}}/ndf: {chi2_lin/max(ndf_lin,1):.2f}")

    c.SaveAs(out_path)
    c.Close()


# ─────────────────────────────────────────────────────────────────
# Summary statistics
# ─────────────────────────────────────────────────────────────────

def compute_summary_stats(arr):
    arr = [v for v in arr if v is not None and np.isfinite(v)]
    if len(arr) == 0:
        return {"mean": None, "std": None, "n": 0}
    return {"mean": float(np.mean(arr)), "std": float(np.std(arr)), "n": len(arr)}


def write_summary(results_by_model, out_path, models):
    """
    Write a text summary file with gain distribution, chi2/ndf, R2, and physics params.
    """
    lines = []
    lines.append("=" * 72)
    lines.append("TAO SiPM GAIN CALIBRATION SUMMARY")
    lines.append("=" * 72)

    for model in models:
        results = results_by_model.get(model, {})
        lines.append(f"\n{'─'*60}")
        lines.append(f"  MODEL: {model}")
        lines.append(f"{'─'*60}")

        all_res = list(results.values())
        n_total  = len(all_res)
        n_good   = sum(1 for r in all_res if r.get("quality") == "GOOD")
        n_bad    = sum(1 for r in all_res if r.get("quality") == "BAD")
        n_failed = sum(1 for r in all_res if r.get("quality") == "FAILED")

        lines.append(f"  Total channels processed : {n_total}")
        lines.append(f"  GOOD  (chi2/ndf < {CHI2NDF_GOOD})   : {n_good}")
        lines.append(f"  BAD   (chi2/ndf < {CHI2NDF_BAD})  : {n_bad}")
        lines.append(f"  FAILED                   : {n_failed}")

        # Gain distribution (linear gain preferred, fallback direct)
        gains = [r.get("gain_linear") or r.get("gain_direct")
                 for r in all_res if r.get("quality") in ("GOOD", "BAD")]
        g_stats = compute_summary_stats(gains)
        lines.append(f"\n  Gain Distribution (GOOD+BAD channels):")
        lines.append(f"    Mean     : {g_stats['mean']:.2f} ADC/PE" if g_stats['mean'] else "    Mean: N/A")
        lines.append(f"    Std Dev  : {g_stats['std']:.2f} ADC/PE"  if g_stats['std']  else "    Std: N/A")
        lines.append(f"    N        : {g_stats['n']}")

        # Sigma SPE
        sigmas = [r.get("sigma_spe") for r in all_res if r.get("quality") in ("GOOD", "BAD")]
        s_stats = compute_summary_stats(sigmas)
        lines.append(f"\n  sigma_SPE Distribution:")
        lines.append(f"    Mean : {s_stats['mean']:.2f} ADC" if s_stats['mean'] else "    Mean: N/A")
        lines.append(f"    Std  : {s_stats['std']:.2f} ADC"  if s_stats['std']  else "    Std: N/A")

        # chi2/ndf
        chi2ndfs = [r.get("chi2ndf") for r in all_res if r.get("quality") in ("GOOD","BAD")]
        c_stats = compute_summary_stats(chi2ndfs)
        lines.append(f"\n  chi2/ndf Distribution (GOOD+BAD):")
        lines.append(f"    Mean : {c_stats['mean']:.3f}" if c_stats['mean'] else "    Mean: N/A")
        lines.append(f"    Std  : {c_stats['std']:.3f}"  if c_stats['std']  else "    Std: N/A")

        # R^2
        r2s = [r.get("R2_linear") for r in all_res if r.get("quality") in ("GOOD","BAD")]
        r2_stats = compute_summary_stats(r2s)
        lines.append(f"\n  Linear Gain R^2 Distribution:")
        lines.append(f"    Mean : {r2_stats['mean']:.5f}" if r2_stats['mean'] else "    Mean: N/A")
        lines.append(f"    Std  : {r2_stats['std']:.5f}"  if r2_stats['std']  else "    Std: N/A")

        # Physics-specific parameters
        if model == "GAUSS_CT":
            pcts = [r.get("P_ct") for r in all_res if r.get("quality") in ("GOOD","BAD") and r.get("P_ct") is not None]
            p_stats = compute_summary_stats(pcts)
            lines.append(f"\n  Crosstalk Probability P_ct:")
            lines.append(f"    Mean : {p_stats['mean']:.4f}" if p_stats['mean'] else "    Mean: N/A")
            lines.append(f"    Std  : {p_stats['std']:.4f}"  if p_stats['std']  else "    Std: N/A")

        elif model == "EMG":
            taus = [r.get("tau") for r in all_res if r.get("quality") in ("GOOD","BAD") and r.get("tau") is not None]
            t_stats = compute_summary_stats(taus)
            lines.append(f"\n  EMG tail constant tau (ADC):")
            lines.append(f"    Mean : {t_stats['mean']:.2f}" if t_stats['mean'] else "    Mean: N/A")
            lines.append(f"    Std  : {t_stats['std']:.2f}"  if t_stats['std']  else "    Std: N/A")

        elif model == "GEN_POISSON":
            lams = [r.get("lam") for r in all_res if r.get("quality") in ("GOOD","BAD") and r.get("lam") is not None]
            l_stats = compute_summary_stats(lams)
            lines.append(f"\n  IOCT branching Poisson lambda:")
            lines.append(f"    Mean : {l_stats['mean']:.4f}" if l_stats['mean'] else "    Mean: N/A")
            lines.append(f"    Std  : {l_stats['std']:.4f}"  if l_stats['std']  else "    Std: N/A")
            mu_gps = [r.get("mu_gp") for r in all_res if r.get("quality") in ("GOOD","BAD") and r.get("mu_gp") is not None]
            mg_stats = compute_summary_stats(mu_gps)
            lines.append(f"\n  Generalized Poisson primary rate mu_gp:")
            lines.append(f"    Mean : {mg_stats['mean']:.4f}" if mg_stats['mean'] else "    Mean: N/A")
            lines.append(f"    Std  : {mg_stats['std']:.4f}"  if mg_stats['std']  else "    Std: N/A")

    lines.append("\n" + "=" * 72)
    lines.append("END OF SUMMARY")
    lines.append("=" * 72)

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[Summary] Written to {out_path}")


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    n_peaks = min(args.n_peaks, MAX_PEAKS)
    models = [m.strip() for m in args.model.split(",") if m.strip() in MODEL_NAMES]
    if not models:
        print(f"No valid models. Choose from {MODEL_NAMES}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    categories = ["good", "bad", "failed"]
    out_dirs = make_output_dirs(args.output_dir, models, categories)

    # Open ROOT file
    rf = ROOT.TFile.Open(args.input, "READ")
    if not rf or rf.IsZombie():
        print(f"Cannot open {args.input}")
        sys.exit(1)

    channel_list = parse_channel_list(args.channels, rf, args.hist_prefix)
    print(f"[Info] Found {len(channel_list)} channels in {args.input}")

    hists = load_channels(rf, args.hist_prefix, channel_list)
    print(f"[Info] {len(hists)} channels pass MIN_ENTRIES >= {MIN_ENTRIES}")

    # Store results per model
    results_by_model = {m: {} for m in models}
    # Track channels per category per model for sampling
    cat_channels = {m: {"good": [], "bad": [], "failed": []} for m in models}

    for ch_id, h in hists.items():
        x_arr, y_arr = th1_to_arrays(h)
        for model in models:
            res = fit_channel(
                x_arr, y_arr, model, n_peaks,
                erf_threshold=args.erf_threshold,
                erf_sigma=args.erf_sigma,
                use_likelihood=args.use_likelihood
            )
            if res is None:
                res = {"quality": "FAILED", "reason": "exception"}
            results_by_model[model][ch_id] = res
            q = res.get("quality", "FAILED").lower()
            cat_channels[model][q].append(ch_id)
            print(f"  ch{ch_id:05d}  {model:15s}  {res.get('quality','?'):7s}"
                  f"  chi2/ndf={res.get('chi2ndf', float('nan')):.2f}"
                  f"  G={res.get('gain_direct', float('nan')):.1f}")

    # Plot — sample up to args.sample channels per category per model
    random.seed(42)
    for model in models:
        for cat in categories:
            chs_in_cat = cat_channels[model][cat]
            sample = random.sample(chs_in_cat, min(args.sample, len(chs_in_cat)))
            for ch_id in sample:
                res = results_by_model[model].get(ch_id)
                h = hists.get(ch_id)
                if h is None or res is None:
                    continue
                fname = f"ch{ch_id:05d}_{model}_{cat.upper()}.png"
                out_path = os.path.join(out_dirs[(model, cat)], fname)
                try:
                    plot_channel_fit(ch_id, h, res, out_path)
                except Exception as e:
                    print(f"  [Plot error] ch{ch_id} {model}: {e}")

    # Write summary
    summary_path = os.path.join(args.output_dir, "gain_calibration_summary.txt")
    write_summary(results_by_model, summary_path, models)

    # Save results as JSON (without numpy arrays for serialisation)
    def clean_for_json(r):
        out = {}
        for k, v in r.items():
            if isinstance(v, np.ndarray):
                continue
            elif callable(v):
                continue
            elif isinstance(v, (np.float32, np.float64)):
                out[k] = float(v)
            elif isinstance(v, (np.int32, np.int64)):
                out[k] = int(v)
            else:
                out[k] = v
        return out

    json_out = {}
    for model in models:
        json_out[model] = {str(ch): clean_for_json(r)
                           for ch, r in results_by_model[model].items()}
    json_path = os.path.join(args.output_dir, "gain_calibration_results.json")
    with open(json_path, "w") as f:
        json.dump(json_out, f, indent=2)
    print(f"[Done] JSON results saved to {json_path}")

    rf.Close()


if __name__ == "__main__":
    main()
