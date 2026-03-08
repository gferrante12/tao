#!/usr/bin/env python3

"""
plot_energy_resolution.py - Create diagnostic plots from energy spectrum ROOT file

Generates:
- Comparison plots: NPE vs Discrete PE (separate from nHit)
- Individual method plots with Gaussian fits
- Individual method plots with extended range
- MeV spectra with Ge-68 peak fits
- Resolution comparison bar chart
- Valley diagnostic plots (if available)

Usage:
python plot_energy_resolution.py energy_spectrum_RUN1065.root RUN1065 --output-dir plots/
"""

import sys
import os
import re
import argparse
import math
import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)

# Dark Noise values (in PE) for time window 200 - 450 ns, for different runs
DN_VALUES = {
    1053: 138,
    1054: 110,
    1055: 81,
    1056: 165,
    1057: 197,
    1058: 236
}

def compute_resolution_error(run_name, sigma, sigma_error, mean, mean_error):
    """
    Compute error on resolution using error propagation.
    Resolution R = sigma / mean
    Error: δR = R * sqrt((δσ/σ)^2 + (δμ/μ)^2)
    """
    if sigma <= 0 or mean <= 0:
        return -1

    # Extract run number from runname
    match = re.search(r'(\d+)', run_name)
    run_num = int(match.group(1)) if match else None
    
    # Apply DN correction
    DN = DN_VALUES.get(run_num, 0)  # Get DN for this run, default to 0
    corrected_mean = mean - DN

    resolution = sigma / corrected_mean
    rel_sigma_error = sigma_error / sigma if sigma > 0 else 0
    rel_mean_error = mean_error / corrected_mean if corrected_mean > 0 else 0
    resolution_error = resolution * math.sqrt(rel_sigma_error**2 + rel_mean_error**2)

    return resolution_error

def create_comparison_plot_split(h1, h2, h3, output_dir, run_name, fit_results=None):
    """Create TWO comparison plots: (1) NPE + Discrete PE, (2) nHit alone

    Args:
        fit_results: dict with keys 'NPE' and 'Discrete PE', each containing
                    {'mean': value, 'sigma': value, 'mean_err': value, 'sigma_err': value}
    """
    # PLOT 1: NPE + Discrete PE
    c1 = ROOT.TCanvas("c1", "NPE vs Discrete PE", 1200, 800)
    c1.SetLogy()
    c1.SetLeftMargin(0.12)
    c1.SetRightMargin(0.05)
    c1.SetTopMargin(0.08)
    c1.SetBottomMargin(0.12)

    h1draw = h1.Clone(f"{h1.GetName()}_draw")
    h2draw = h2.Clone(f"{h2.GetName()}_draw")
    h1draw.SetDirectory(0)
    h2draw.SetDirectory(0)

    h1draw.SetLineColor(ROOT.kBlue)
    h1draw.SetLineWidth(3)
    h2draw.SetLineColor(ROOT.kRed)
    h2draw.SetLineWidth(3)

    h1draw.SetTitle(f"Energy Spectrum Comparison - {run_name}")
    h1draw.GetXaxis().SetTitle("PE")
    h1draw.GetYaxis().SetTitle("Counts")

    maxval = max(h1draw.GetMaximum(), h2draw.GetMaximum())
    h1draw.SetMaximum(maxval * 2.5)

    h1draw.Draw("HIST")
    h2draw.Draw("HIST SAME")

    legend1 = ROOT.TLegend(0.50, 0.65, 0.93, 0.92)
    legend1.SetBorderSize(1)
    legend1.SetFillStyle(1001)
    legend1.SetFillColor(ROOT.kWhite)
    legend1.SetTextSize(0.028)

    # Use fitted values if available, otherwise histogram mean
    if fit_results and 'NPE' in fit_results:
        npe_mean = fit_results['NPE']['mean']
        npe_sigma = fit_results['NPE']['sigma']
        npe_mean_err = fit_results['NPE']['mean_err']
        npe_sigma_err = fit_results['NPE']['sigma_err']
        legend1.AddEntry(h1draw, "NPE (Ge-68 peak)", "l")
        legend1.AddEntry(ROOT.nullptr, f"  Mean: {npe_mean:.1f} #pm {npe_mean_err:.1f} PE", "")
        legend1.AddEntry(ROOT.nullptr, f"  Sigma: {npe_sigma:.1f} #pm {npe_sigma_err:.1f} PE", "")
    else:
        legend1.AddEntry(h1draw, f"NPE (Mean: {h1.GetMean():.1f})", "l")

    if fit_results and 'Discrete PE' in fit_results:
        pe_mean = fit_results['Discrete PE']['mean']
        pe_sigma = fit_results['Discrete PE']['sigma']
        pe_mean_err = fit_results['Discrete PE']['mean_err']
        pe_sigma_err = fit_results['Discrete PE']['sigma_err']
        legend1.AddEntry(h2draw, "Discrete PE (Ge-68 peak)", "l")
        legend1.AddEntry(ROOT.nullptr, f"  Mean: {pe_mean:.1f} #pm {pe_mean_err:.1f} PE", "")
        legend1.AddEntry(ROOT.nullptr, f"  Sigma: {pe_sigma:.1f} #pm {pe_sigma_err:.1f} PE", "")
    else:
        legend1.AddEntry(h2draw, f"Discrete PE (Mean: {h2.GetMean():.1f})", "l")

    legend1.Draw()

    c1.Update()
    output1 = os.path.join(output_dir, f"comparison_NPE_PE_{run_name}.png")
    c1.SaveAs(output1)
    print(f"✓ Saved: {output1}")

    # PLOT 2: nHit alone (unchanged)
    c2 = ROOT.TCanvas("c2", "nHit", 1200, 800)
    c2.SetLogy()
    c2.SetLeftMargin(0.12)
    c2.SetRightMargin(0.05)
    c2.SetTopMargin(0.08)
    c2.SetBottomMargin(0.12)

    h3draw = h3.Clone(f"{h3.GetName()}_draw")
    h3draw.SetDirectory(0)

    h3draw.SetLineColor(ROOT.kGreen+2)
    h3draw.SetLineWidth(3)

    h3draw.SetTitle(f"nHit Spectrum - {run_name}")
    h3draw.GetXaxis().SetTitle("nHit (Number of Fired Channels)")
    h3draw.GetYaxis().SetTitle("Counts")

    h3draw.Draw("HIST")

    legend2 = ROOT.TLegend(0.15, 0.85, 0.45, 0.92)
    legend2.SetBorderSize(1)
    legend2.SetFillStyle(1001)
    legend2.SetFillColor(ROOT.kWhite)
    legend2.SetTextSize(0.030)
    legend2.AddEntry(h3draw, f"nHit (Mean: {h3.GetMean():.1f})", "l")
    legend2.Draw()

    c2.Update()
    output2 = os.path.join(output_dir, f"comparison_nHit_{run_name}.png")
    c2.SaveAs(output2)
    print(f"✓ Saved: {output2}")

    return c1, c2

def systematic_fit_study(hist, method_name, run_name):
    """
    Perform systematic study varying fit range and background model.
    Returns: dict with systematic uncertainty estimates
    """
    print(f"  Running systematic study for {method_name}...")
    
    # Find peak
    expected_peak = hist.GetMean()
    search_window = expected_peak * 0.7
    search_min = expected_peak - search_window
    search_max = expected_peak + search_window
    
    bin_min = hist.FindBin(search_min)
    bin_max = hist.FindBin(search_max)
    
    max_bin = bin_min
    max_content = hist.GetBinContent(bin_min)
    for b in range(bin_min, bin_max + 1):
        content = hist.GetBinContent(b)
        if content > max_content:
            max_content = content
            max_bin = b
    
    peak_center = hist.GetBinCenter(max_bin)
    sigma_estimate = peak_center * 0.03
    
    # Configurations to test
    range_factors = [
        (5, 4),   # Narrow range
        (7, 6),   # Default range
        (10, 8),  # Wide range
    ]
    
    poly_degrees = [1, 2, 3]  # pol1, pol2, pol3
    
    results = []
    
    for (low_factor, high_factor) in range_factors:
        for poly_deg in poly_degrees:
            fit_min = peak_center - low_factor * sigma_estimate
            fit_max = peak_center + high_factor * sigma_estimate
            
            # Create fit function
            if poly_deg == 1:
                fit_func = ROOT.TF1(f"f_sys_{method_name}_{low_factor}_{high_factor}_pol{poly_deg}", 
                                   "gaus(0) + pol1(3)", fit_min, fit_max)
                fit_func.SetParameters(max_content, peak_center, sigma_estimate, 100, 0)
            elif poly_deg == 2:
                fit_func = ROOT.TF1(f"f_sys_{method_name}_{low_factor}_{high_factor}_pol{poly_deg}", 
                                   "gaus(0) + pol2(3)", fit_min, fit_max)
                fit_func.SetParameters(max_content, peak_center, sigma_estimate, 100, 0, 0)
            else:  # poly_deg == 3
                fit_func = ROOT.TF1(f"f_sys_{method_name}_{low_factor}_{high_factor}_pol{poly_deg}", 
                                   "gaus(0) + pol3(3)", fit_min, fit_max)
                fit_func.SetParameters(max_content, peak_center, sigma_estimate, 100, 0, 0, 0)
            
            # Set parameter limits
            fit_func.SetParLimits(0, 0.1 * max_content, 10 * max_content)
            fit_func.SetParLimits(1, fit_min, fit_max)
            fit_func.SetParLimits(2, 0.3 * sigma_estimate, 3.0 * sigma_estimate)
            
            # Perform fit
            fit_result = hist.Fit(fit_func, "RSQN")
            
            if fit_result.Status() == 0:  # Successful fit
                fitted_mean = fit_func.GetParameter(1)
                fitted_sigma = fit_func.GetParameter(2)
                
                # Apply DN correction
                match = re.search(r'(\d+)', run_name)
                run_num = int(match.group(1)) if match else None
                DN = DN_VALUES.get(run_num, 0)
                corrected_mean = fitted_mean - DN
                
                resolution = (fitted_sigma / corrected_mean) * 100 if corrected_mean > 0 else -1
                
                if resolution > 0:
                    results.append({
                        'range': f"{low_factor}-{high_factor}σ",
                        'poly': poly_deg,
                        'mean': fitted_mean,
                        'sigma': fitted_sigma,
                        'resolution': resolution
                    })
    
    if len(results) < 2:
        print(f"    WARNING: Not enough successful fits ({len(results)}) for systematic study")
        return {'sigma_sys': 0, 'mean_sys': 0, 'resolution_sys': 0}
    
    # Calculate spread (RMS) of results
    import numpy as np
    
    means = [r['mean'] for r in results]
    sigmas = [r['sigma'] for r in results]
    resolutions = [r['resolution'] for r in results]
    
    mean_sys = np.std(means, ddof=1)
    sigma_sys = np.std(sigmas, ddof=1)
    resolution_sys = np.std(resolutions, ddof=1)
    
    print(f"    Systematic study: {len(results)} successful fits")
    print(f"    σ(mean) = {mean_sys:.2f} PE")
    print(f"    σ(sigma) = {sigma_sys:.2f} PE")
    print(f"    σ(resolution) = {resolution_sys:.4f}%")
    
    return {
        'sigma_sys': sigma_sys,
        'mean_sys': mean_sys,
        'resolution_sys': resolution_sys,
        'n_fits': len(results)
    }


def fit_and_plot_individual(hist, method_name, run_name, output_dir, show_fit=True, extend_range=False):
    """
    Plot individual method with optional Gaussian fit.

    Returns:
        If show_fit=True and fit succeeds: (canvas, fit_results_dict)
        Otherwise: (canvas, None)
    """
    suffix = "_fit" if show_fit else "_ext" if extend_range else ""
    canvas_name = f"c_{method_name.replace(' ', '_')}{suffix}"
    c = ROOT.TCanvas(canvas_name, method_name, 1200, 800)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.08)
    c.SetBottomMargin(0.12)

    hdraw = hist.Clone(f"{hist.GetName()}_individual")
    hdraw.SetDirectory(0)

    # Set color based on method
    if "NPE" in method_name and "Discrete" not in method_name:
        hdraw.SetLineColor(ROOT.kBlue)
    elif "Discrete" in method_name:
        hdraw.SetLineColor(ROOT.kRed)
    elif "nHit" in method_name:
        hdraw.SetLineColor(ROOT.kGreen+2)
    else:
        hdraw.SetLineColor(ROOT.kBlack)

    hdraw.SetLineWidth(3)
    hdraw.SetTitle(f"{method_name} Spectrum - {run_name}")
    hdraw.GetXaxis().SetTitle("PE" if "nHit" not in method_name else "nHit")
    hdraw.GetYaxis().SetTitle("Counts")

    # MODIFIED: Extend x-range if requested - PE spectra to 30000 minimum
    if extend_range:
        c.SetLogy()
        xmax = hdraw.GetXaxis().GetXmax()
        actual_max = xmax
        for i in range(hdraw.GetNbinsX(), 0, -1):
            if hdraw.GetBinContent(i) > 0:
                actual_max = hdraw.GetBinCenter(i)
                break
        # For PE spectra, extend to at least 30000 PE
        if "nHit" not in method_name:
            hdraw.GetXaxis().SetRangeUser(0, max(30000, 2 * actual_max))
        else:
            hdraw.GetXaxis().SetRangeUser(0, max(2 * actual_max, 2 * xmax))

    # === Draw BEFORE setting axis limits for fits ===
    hdraw.Draw("HIST")

    # Fit Gaussian if requested
    fit_results = None
    if show_fit:
        # Search for peak in FULL histogram (not restricted range)
        expected_peak = hist.GetMean()
        search_window = expected_peak * 0.7
        search_min = expected_peak - search_window
        search_max = expected_peak + search_window
        bin_min = hist.FindBin(search_min)
        bin_max = hist.FindBin(search_max)

        max_bin = bin_min
        max_content = hist.GetBinContent(bin_min)
        for b in range(bin_min, bin_max + 1):
            content = hist.GetBinContent(b)
            if content > max_content:
                max_content = content
                max_bin = b

        peak_center = hist.GetBinCenter(max_bin)
        sigma_estimate = peak_center * 0.03  # Initial sigma estimate ~3% of peak

        # === EXTENDED FIT RANGE ===
        fit_min = peak_center - 7 * sigma_estimate
        fit_max = peak_center + 6 * sigma_estimate

        # Create fit function: Gaussian + polynomial background
        fitfunc = ROOT.TF1(f"fit_{method_name}", "gaus(0) + pol3(3)", fit_min, fit_max)
        fitfunc.SetParameters(max_content, peak_center, sigma_estimate, 100, 0, 0, 0)
        fitfunc.SetParNames("Amplitude", "Mean", "Sigma", "p0", "p1", "p2", "p3")

        # Parameter limits
        fitfunc.SetParLimits(0, 0.1 * max_content, 10 * max_content)
        fitfunc.SetParLimits(1, fit_min, fit_max)
        fitfunc.SetParLimits(2, 0.3 * sigma_estimate, 3.0 * sigma_estimate)

        # Fit on original histogram
        fit_result = hist.Fit(fitfunc, "RSQN")

        fitted_peak = fitfunc.GetParameter(1)
        fitted_sigma = fitfunc.GetParameter(2)
        peak_error = fitfunc.GetParError(1)
        sigma_error = fitfunc.GetParError(2)

        # Polynomial parameters
        p0 = fitfunc.GetParameter(3)
        p1 = fitfunc.GetParameter(4)
        p2 = fitfunc.GetParameter(5)
        p3 = fitfunc.GetParameter(6)
        p0_err = fitfunc.GetParError(3)
        p1_err = fitfunc.GetParError(4)
        p2_err = fitfunc.GetParError(5)
        p3_err = fitfunc.GetParError(6)

        # Extract run number from runname
        match = re.search(r'(\d+)', run_name)
        run_num = int(match.group(1)) if match else None
        
        # Apply DN correction
        DN = DN_VALUES.get(run_num, 0)  # Get DN for this run, default to 0
        corrected_mean = fitted_peak - DN
        
        # Calculate resolution with DN correction
        resolution = (fitted_sigma / corrected_mean * 100) if corrected_mean > 0 else -1
        resolution_error_frac = compute_resolution_error(run_name, fitted_sigma, sigma_error, corrected_mean, peak_error)
        resolution_error = resolution_error_frac * 100
        chi2ndf = fitfunc.GetChisquare() / fitfunc.GetNDF() if fitfunc.GetNDF() > 0 else -1

        # Perform systematic study
        sys_study = systematic_fit_study(hist, method_name, run_name)

        # Combine statistical and systematic errors in quadrature
        if sys_study['resolution_sys'] > 0:
            resolution_error_total = math.sqrt(resolution_error**2 + sys_study['resolution_sys']**2)
            sigma_error_total = math.sqrt(sigma_error**2 + sys_study['sigma_sys']**2)
            peak_error_total = math.sqrt(peak_error**2 + sys_study['mean_sys']**2)
            
            print(f"    Total error (stat ⊕ sys): {resolution_error_total:.4f}%")
            if sys_study['n_fits'] < 6:  # Less than 6/9 successful
                print(f"    WARNING: Only {sys_study['n_fits']}/9 systematic fits successful!")
        else:
            resolution_error_total = resolution_error
            sigma_error_total = sigma_error
            peak_error_total = peak_error

        # Draw fit BEFORE setting axis limits
        fitfunc.SetLineColor(ROOT.kBlack)
        fitfunc.SetLineWidth(2)
        fitfunc.Draw("SAME")

        # === NOW set axis limits AFTER drawing fit ===
        if "nHit" in method_name:
            hdraw.GetXaxis().SetRangeUser(1000, 6000)
        else:  # NPE or Discrete PE
            hdraw.GetXaxis().SetRangeUser(1000, 8000)

        c.Update()  # Critical: update canvas after changing axis

        info_box = ROOT.TPaveText(0.2, 0.50, 0.46, 0.92, "NDC")
        info_box.SetFillColor(ROOT.kWhite)
        info_box.SetFillStyle(1001)
        info_box.SetBorderSize(1)
        info_box.SetTextAlign(12)
        info_box.SetTextSize(0.024)

        info_box.AddText("Peak: 1.022 MeV (Ge-68 e^{+}e^{-})")
        info_box.AddText("")
        info_box.AddText(f"Dark Noise: {DN:.1f} PE")
        info_box.AddText(f"Corrected Mean: {corrected_mean:.1f} #pm {peak_error_total:.1f} PE")
        info_box.AddText(f"Sigma: {fitted_sigma:.1f} #pm {sigma_error_total:.1f} PE")
        info_box.AddText(f"Resolution: {resolution:.2f} #pm {resolution_error_total:.2f}%")
        if sys_study['resolution_sys'] > 0:
            info_box.AddText(f"  (stat: {resolution_error:.2f}%, sys: {sys_study['resolution_sys']:.2f}%)")
        info_box.AddText(f"#chi^{{2}}/ndf: {chi2ndf:.2f}")
        info_box.AddText("")
        info_box.AddText("Background: p_{0} + p_{1}x + p_{2}x^{2} + p_{3}x^{3}")
        info_box.AddText(f"p_{{0}}: {p0:.2e} #pm {p0_err:.2e}")
        info_box.AddText(f"p_{{1}}: {p1:.2e} #pm {p1_err:.2e}")
        info_box.AddText(f"p_{{2}}: {p2:.2e} #pm {p2_err:.2e}")
        info_box.AddText(f"p_{{3}}: {p3:.2e} #pm {p3_err:.2e}")

        c.Update()  # Update before drawing info box
        info_box.Draw()
        c.Update()  # Final update after info box

        # Store fit results
        fit_results = {
            'mean': corrected_mean,
            'sigma': fitted_sigma,
            'mean_err': peak_error_total,
            'sigma_err': sigma_error_total,
            'resolution': resolution / 100,
            'resolution_err': resolution_error_total / 100,
            'resolution_stat': resolution_error / 100,
            'resolution_sys': sys_study['resolution_sys'] / 100 
        }

        #if fit_result.Status() != 0:
            # FIT FAILED - return empty dict instead of None
        #    fit_results = {
        #        'mean': -1,
        #        'sigma': -1,
        #        'mean_err': 0,
        #        'sigma_err': 0,
        #        'resolution': -1,
        #        'resolution_err': 0
        #    }

        # Fit failed - still set axis limits
        if "nHit" in method_name:
            hdraw.GetXaxis().SetRangeUser(1000, 6000)
        else:
            hdraw.GetXaxis().SetRangeUser(1000, 8000)
        c.Update()

    # Generate filename
    suffix = "_withfit" if show_fit else "_extended" if extend_range else ""
    safe_name = method_name.replace(" ", "_").replace("→", "to")
    output = os.path.join(output_dir, f"{safe_name}_{run_name}{suffix}.png")
    c.SaveAs(output)
    print(f"✓ Saved: {output}")

    # Return canvas and fit results
    return c, fit_results
    

def create_mev_comparison(h1, h2, output_dir, run_name):
    """Create MeV comparison with 1.022 MeV reference line"""

    c = ROOT.TCanvas("c_mev", "MeV Comparison", 1200, 800)
    c.SetLogy()
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.08)
    c.SetBottomMargin(0.12)

    h1draw = h1.Clone(f"{h1.GetName()}_draw")
    h2draw = h2.Clone(f"{h2.GetName()}_draw")
    h1draw.SetDirectory(0)
    h2draw.SetDirectory(0)

    h1draw.SetLineColor(ROOT.kBlue)
    h1draw.SetLineWidth(3)
    h2draw.SetLineColor(ROOT.kRed)
    h2draw.SetLineWidth(3)

    h1draw.SetTitle(f"Energy Spectrum (MeV) - {run_name}")
    h1draw.GetXaxis().SetTitle("Energy [MeV]")
    h1draw.GetYaxis().SetTitle("Counts")
    h1draw.GetXaxis().SetRangeUser(0, 5)

    maxval = max(h1draw.GetMaximum(), h2draw.GetMaximum())
    h1draw.SetMaximum(maxval * 2.5)

    h1draw.Draw("HIST")
    h2draw.Draw("HIST SAME")

    # 1.022 MeV reference line
    refline = ROOT.TLine(1.022, 0, 1.022, maxval * 2.5)
    refline.SetLineColor(ROOT.kGreen+2)
    refline.SetLineWidth(3)
    refline.SetLineStyle(2)
    refline.Draw()

    # Legend
    legend = ROOT.TLegend(0.54, 0.70, 0.94, 0.94)
    legend.SetBorderSize(1)
    legend.SetFillStyle(1001)
    legend.SetFillColor(ROOT.kWhite)
    legend.SetTextSize(0.028)

    legend.AddEntry(h1draw, f"nPE #rightarrow MeV; Entries: {int(h1.GetEntries())}", "l")
    legend.AddEntry(h2draw, f"Discrete PE #rightarrow MeV; Entries: {int(h2.GetEntries())}", "l")
    legend.AddEntry(refline, "1.022 MeV (e^{+}e^{-})", "l")
    legend.AddEntry(ROOT.nullptr, f"Mean (nPE): {h1.GetMean():.3f} MeV", "")
    legend.AddEntry(ROOT.nullptr, f"Mean (Discrete PE): {h2.GetMean():.3f} MeV", "")

    legend.Draw()

    c.Update()
    output = os.path.join(output_dir, f"comparison_MeV_{run_name}.png")
    c.SaveAs(output)
    print(f"✓ Saved: {output}")

    return c

def create_resolution_comparison(resolutions, resolution_errors, output_dir, run_name):
    """Create bar chart comparing resolutions WITH ERROR BARS"""

    c = ROOT.TCanvas("c_res", "Resolution Comparison", 1200, 800)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.08)
    c.SetBottomMargin(0.15)
    c.SetGridy()

    methods = list(resolutions.keys())
    nmethods = len(methods)

    hres = ROOT.TH1F("h_resolution",
                      f"Energy Resolution Comparison - {run_name};;Resolution (%)",
                      nmethods, 0, nmethods)
    hres.SetDirectory(0)
    hres.SetFillColor(ROOT.kAzure-9)
    hres.SetLineColor(ROOT.kBlack)
    hres.SetLineWidth(2)
    hres.SetStats(0)

    for i, method in enumerate(methods):
        hres.SetBinContent(i+1, resolutions[method] * 100)
        hres.SetBinError(i+1, resolution_errors.get(method, 0) * 100)
        hres.GetXaxis().SetBinLabel(i+1, method)

    hres.GetYaxis().SetRangeUser(0, max(resolutions.values()) * 120)
    hres.Draw("BAR")
    hres.Draw("E1 SAME")

    # Add value labels on bars
    text = ROOT.TText()
    text.SetTextSize(0.035)
    text.SetTextAlign(21)  # Center alignment
    text.SetTextFont(42)    # Helvetica font
    for i, method in enumerate(methods):
        resval = resolutions[method] * 100
        reserr = resolution_errors.get(method, 0) * 100
        text.DrawText(i + 0.5, resval + 0.20, f"{resval:.2f} +/- {reserr:.2f}%")

    c.Update()
    output = os.path.join(output_dir, f"resolution_comparison_{run_name}.png")
    c.SaveAs(output)
    print(f"✓ Saved: {output}")

    return c

def create_resolution_comparison_with_mev(resolutions, resolution_errors, output_dir, run_name):
    """
    Create resolution comparison INCLUDING MeV-converted resolutions
    NEW: Convert NPE and Discrete PE resolutions to MeV units
    """

    c = ROOT.TCanvas("c_res_mev", "Resolution Comparison with MeV", 1400, 800)
    c.SetLeftMargin(0.10)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.08)
    c.SetBottomMargin(0.15)
    c.SetGridy()

    # Extract PE-based resolutions and compute MeV equivalents
    res_npe_pe = resolutions.get('NPE', 0)
    res_discrete_pe = resolutions.get('Discrete PE', 0)
    res_nhit = resolutions.get('nHit', 0)

    res_npe_pe_err = resolution_errors.get('NPE', 0)
    res_discrete_pe_err = resolution_errors.get('Discrete PE', 0)
    res_nhit_err = resolution_errors.get('nHit', 0)

    # Convert PE resolutions to MeV using σ/μ relationship
    # Resolution is independent of units if conversion is linear: R_MeV = R_PE
    res_npe_mev_converted = res_npe_pe
    res_discrete_mev_converted = res_discrete_pe

    res_npe_mev_converted_err = res_npe_pe_err
    res_discrete_mev_converted_err = res_discrete_pe_err

    # Create histogram with 5 columns
    methods = ['NPE', 'Discrete PE', 'nHit', 
               f'NPE ($\rightarrow MeV)', 'Discrete PE ($\rightarrow MeV)']

    nmethods = len(methods)

    hres = ROOT.TH1F("h_resolution_with_mev",
                      f"Energy Resolution Comparison - {run_name};;Resolution (%)",
                      nmethods, 0, nmethods)
    hres.SetDirectory(0)
    hres.SetFillColor(ROOT.kAzure-9)
    hres.SetLineColor(ROOT.kBlack)
    hres.SetLineWidth(2)
    hres.SetStats(0)

    # Fill histogram
    res_values = [res_npe_pe, res_discrete_pe, res_nhit, 
                  res_npe_mev_converted, res_discrete_mev_converted]
    res_errors = [res_npe_pe_err, res_discrete_pe_err, res_nhit_err,
                  res_npe_mev_converted_err, res_discrete_mev_converted_err]

    for i, (method, res, err) in enumerate(zip(methods, res_values, res_errors)):
        hres.SetBinContent(i+1, res * 100)
        hres.SetBinError(i+1, err * 100)
        hres.GetXaxis().SetBinLabel(i+1, method)

    hres.GetYaxis().SetRangeUser(0, max(res_values) * 120)
    hres.Draw("BAR")
    hres.Draw("E1 SAME")

    # Add value labels
    text = ROOT.TText()
    text.SetTextSize(0.030)
    text.SetTextAlign(21)  # Center alignment
    text.SetTextFont(42)    # Helvetica font

    for i, (res, err) in enumerate(zip(res_values, res_errors)):
        res_val = res * 100
        res_err = err * 100
        text.DrawText(i + 0.5, res_val + 0.20, f"{res_val:.2f} +/- {res_err:.2f}%")


    # Add explanation text
    #note = ROOT.TPaveText(0.15, 0.92, 0.85, 0.96, "NDC")
    #note.SetFillColor(ROOT.kWhite)
    #note.SetBorderSize(1)
    #note.SetTextSize(0.025)
    #note.AddText("Note: (→MeV) columns show resolution from PE-based methods converted using fitted 1.022 MeV peak position")
    #note.Draw()

    c.Update()
    output = os.path.join(output_dir, f"resolution_comparison_with_mev_{run_name}.png")
    c.SaveAs(output)
    print(f"✓ Saved: {output}")

    return c

def create_resolution_comparison_PE(resolutions, resolution_errors, output_dir, run_name):
    """Create bar chart comparing resolutions (PE methods only)"""

    c = ROOT.TCanvas("c_res_PE", "Resolution Comparison", 1200, 800)
    c.SetLeftMargin(0.12)
    c.SetRightMargin(0.05)
    c.SetTopMargin(0.08)
    c.SetBottomMargin(0.15)
    c.SetGridy()

    # Filter out MeV methods
    pe_methods = [method for method in resolutions.keys()
                  if '→' not in method and 'MeV' not in method]

    n_methods = len(pe_methods)

    h_res = ROOT.TH1F("h_resolution",
                       f"Energy Resolution Comparison - {run_name};;Resolution (%)",
                       n_methods, 0, n_methods)
    h_res.SetDirectory(0)
    h_res.SetFillColor(ROOT.kAzure-9)
    h_res.SetLineColor(ROOT.kBlack)
    h_res.SetLineWidth(2)
    h_res.SetStats(0)

    for i, method in enumerate(pe_methods):
        h_res.SetBinContent(i+1, resolutions[method] * 100)
        h_res.SetBinError(i+1, resolution_errors.get(method, 0) * 100)
        h_res.GetXaxis().SetBinLabel(i+1, method)

    h_res.GetYaxis().SetRangeUser(0, max(resolutions[m] for m in pe_methods) * 120)
    h_res.Draw("BAR")
    h_res.Draw("E1 SAME")

    # Add value labels
    text = ROOT.TText()
    text.SetTextSize(0.035)
    text.SetTextAlign(21)  # Center alignment
    text.SetTextFont(42)    # Helvetica font
    for i, method in enumerate(pe_methods):
        res_val = resolutions[method] * 100
        res_err = resolution_errors.get(method, 0) * 100
        text.DrawText(i + 0.5, res_val + 0.20, f"{res_val:.2f} +/- {res_err:.2f}%")

    c.Update()
    output = os.path.join(output_dir, f"resolution_comparison_{run_name}.png")
    c.SaveAs(output)
    print(f" ✓ Saved: {output}")

    return c

def plot_diagnostics(input_file, run_name, output_dir, convert_to_mev=False):
    """Generate all diagnostic plots"""

    print("="*60)
    print(f"Creating Diagnostic Plots - {run_name}")
    print("="*60)

    # Open input file
    fin = ROOT.TFile.Open(input_file, "READ")
    if not fin or fin.IsZombie():
        print(f"ERROR: Cannot open {input_file}")
        sys.exit(1)

    # Get histograms
    h_npe = fin.Get("h_NPE")
    h_pe = fin.Get("h_PEdiscrete")
    h_nhit = fin.Get("h_nHit")
    # Get MeV histograms only if convert_to_mev is enabled
    if convert_to_mev:
        h_npe_mev = None
        h_pe_mev = None
        h_npe_mev = fin.Get("h_NPE_MeV")
        h_pe_mev = fin.Get("h_PEdiscrete_MeV")

    if not all([h_npe, h_pe, h_nhit]):
        print("\n⚠️ Expected histograms not found. Listing file contents:")
        print("-" * 60)
        keys = fin.GetListOfKeys()
        for key in keys:
            obj = key.ReadObj()
            print(f" {key.GetName():<30} {obj.ClassName()}")
        print("-" * 60)
        print("\nERROR: Cannot find required histograms")
        fin.Close()
        sys.exit(1)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # 1. Individual plots WITH fits
    print("\n2. Creating individual plots with Gaussian fits...")
    c_npe_fit, fit_npe = fit_and_plot_individual(h_npe, "NPE", run_name, output_dir, show_fit=True)
    c_pe_fit, fit_pe = fit_and_plot_individual(h_pe, "Discrete PE", run_name, output_dir, show_fit=True)
    c_nhit_fit, fit_nhit = fit_and_plot_individual(h_nhit, "nHit", run_name, output_dir, show_fit=True)

    # 2. Individual plots extended range
    print("\n2. Creating individual plots with extended range...")
    c_npe_ext, _ = fit_and_plot_individual(h_npe, "NPE", run_name, output_dir, show_fit=False, extend_range=True)
    c_pe_ext, _ = fit_and_plot_individual(h_pe, "Discrete PE", run_name, output_dir, show_fit=False, extend_range=True)
    c_nhit_ext, _ = fit_and_plot_individual(h_nhit, "nHit", run_name, output_dir, show_fit=False, extend_range=True)

    # Get resolution info
    # Build resolutions dict from fitresults
    resolutions = {}
    resolution_errors = {}

    if fit_npe and fit_npe['resolution'] > 0:
        resolutions["NPE"] = fit_npe['resolution']
        resolution_errors["NPE"] = fit_npe['resolution_err']

    if fit_pe and fit_pe['resolution'] > 0:
        resolutions["Discrete PE"] = fit_pe['resolution']
        resolution_errors["Discrete PE"] = fit_pe['resolution_err']
    if fit_nhit and fit_nhit['resolution'] > 0:
        resolutions["nHit"] = fit_nhit['resolution']
        resolution_errors["nHit"] = fit_nhit['resolution_err']

    # 3. Split comparison plots
    print("\n3. Creating split comparison plots...")
    fit_results_dict = {"NPE": fit_npe, "Discrete PE": fit_pe}
    c1, c2 = create_comparison_plot_split(h_npe, h_pe, h_nhit, output_dir, run_name, fit_results=fit_results_dict)

    # 4. MeV comparison
    if convert_to_mev and h_npe_mev and h_pe_mev:
        c_mev = None
        print("\n4. Creating MeV comparison plot...")
        c_mev = create_mev_comparison(h_npe_mev, h_pe_mev, output_dir, run_name)

    # 5. Resolution comparison (BOTH versions)
    if resolutions:
        print("\n5. Creating resolution comparison plots...")
        c_res_PE = create_resolution_comparison_PE(resolutions, resolution_errors, output_dir, run_name)

        # Resolution comparison with MeV columns
        if convert_to_mev:
            c_res_mev = None
            print("\n6. Creating resolution comparison with MeV conversions...")
            c_res_mev = create_resolution_comparison_with_mev(resolutions, resolution_errors, output_dir, run_name)

    # 6. Save to ROOT file
    print("\n7. Saving plots to ROOT file...")
    fout = ROOT.TFile(os.path.join(output_dir, f"diagnostic_plots_{run_name}.root"), "RECREATE")
    c1.Write()
    c2.Write()
    c_npe_fit.Write()
    c_pe_fit.Write()
    c_nhit_fit.Write()
    c_npe_ext.Write()
    c_pe_ext.Write()
    c_nhit_ext.Write()
    
    if convert_to_mev:
        c_mev.Write()

    if resolutions:
        c_res_PE.Write()
        if convert_to_mev:
            c_res_mev.Write()

    h_npe.Write()
    h_pe.Write()
    h_nhit.Write()
    if convert_to_mev:
        h_npe_mev.Write()
        h_pe_mev.Write()

    # ======== CREATE AND WRITE ENERGY_INFO ========
    info_str = ""
    
    # NPE data
    if fit_npe and fit_npe['mean'] > 0:
        info_str += f"RES_NPE={fit_npe['resolution']:.6f};"
        info_str += f"RES_NPE_ERR={fit_npe['resolution_err']:.6f};"
        info_str += f"MEAN_NPE={fit_npe['mean']:.4f};"
        info_str += f"MEAN_NPE_ERR={fit_npe['mean_err']:.4f};"
        info_str += f"SIGMA_NPE={fit_npe['sigma']:.4f};"
        info_str += f"SIGMA_NPE_ERR={fit_npe['sigma_err']:.4f};"
        match = re.search(r'(\d+)', run_name)
        run_num = int(match.group(1)) if match else None
        DN = DN_VALUES.get(run_num, 0)
        info_str += f"DN_NPE={DN:.1f};"

    # Discrete PE data
    if fit_pe and fit_pe['mean'] > 0:
        info_str += f"RES_PE={fit_pe['resolution']:.6f};"
        info_str += f"RES_PE_ERR={fit_pe['resolution_err']:.6f};"
        info_str += f"MEAN_PE={fit_pe['mean']:.4f};"
        info_str += f"MEAN_PE_ERR={fit_pe['mean_err']:.4f};"
        info_str += f"SIGMA_PE={fit_pe['sigma']:.4f};"
        info_str += f"SIGMA_PE_ERR={fit_pe['sigma_err']:.4f};"
        match = re.search(r'(\d+)', run_name)
        run_num = int(match.group(1)) if match else None
        DN = DN_VALUES.get(run_num, 0)
        info_str += f"DN_NPE={DN:.1f};"
    
    # nHit data
    if fit_nhit and fit_nhit['mean'] > 0:
        info_str += f"RES_NHIT={fit_nhit['resolution']:.6f};"
        info_str += f"RES_NHIT_ERR={fit_nhit['resolution_err']:.6f};"
        info_str += f"MEAN_NHIT={fit_nhit['mean']:.4f};"
        info_str += f"MEAN_NHIT_ERR={fit_nhit['mean_err']:.4f};"
        info_str += f"SIGMA_NHIT={fit_nhit['sigma']:.4f};"
        info_str += f"SIGMA_NHIT_ERR={fit_nhit['sigma_err']:.4f};"

    # Create and write TNamed object
    energy_info = ROOT.TNamed("energy_info", info_str)
    energy_info.Write()
    # ====================================================

    fout.Close()

    fin.Close()

    print("="*60)
    print(f"✅ All plots saved to {output_dir}/")
    print(f" - comparison_NPE_PE_{run_name}.png")
    print(f" - comparison_nHit_{run_name}.png")
    print(f" - NPE_{run_name}_withfit.png (UPDATED: extended fit, polynomial params)")
    print(f" - Discrete_PE_{run_name}_withfit.png (UPDATED: extended fit, polynomial params)")
    print(f" - nHit_{run_name}_withfit.png (UPDATED: extended fit, polynomial params)")
    print(f" - NPE_{run_name}_extended.png")
    print(f" - Discrete_PE_{run_name}_extended.png")
    print(f" - nHit_{run_name}_extended.png")
    print(f" - resolution_comparison_{run_name}.png")
    if convert_to_mev:
        print(f" - comparison_MeV_{run_name}.png")
        print(f" - resolution_comparison_with_mev_{run_name}.png")
    print(f" - diagnostic_plots_{run_name}.root")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Create diagnostic plots from energy spectrum ROOT file'
    )

    parser.add_argument('input_file', help='Energy spectrum ROOT file')
    parser.add_argument('run_name', help='Run name (e.g., RUN1065)')
    parser.add_argument('--output-dir', default='plots/', help='Output directory for plots')
    parser.add_argument('--convert-to-mev', action='store_true', default=False,
                        help='Enable MeV conversion and related plots (default: False)')

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"ERROR: File not found: {args.input_file}")
        sys.exit(1)

    plot_diagnostics(args.input_file, args.run_name, args.output_dir, args.convert_to_mev)
