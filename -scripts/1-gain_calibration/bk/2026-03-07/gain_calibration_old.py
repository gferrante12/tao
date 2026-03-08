
#!/usr/bin/env python3
"""
Gain calibration with dual workflows:
1. TSpectrum peak detection → ROOT TF1 fit
2. SciPy peak detection → SciPy curve_fit

# DEFAULT: ROOT workflow, vetoed (clean) histograms, all channel plots saved
python gain_calibration.py input.root output_dir run_name

# SciPy only / both workflows
python gain_calibration.py input.root output_dir run_name --workflow scipy
python gain_calibration.py input.root output_dir run_name --workflow both

# Use raw (non-vetoed) histograms instead of clean ones
python gain_calibration.py input.root output_dir run_name --use-raw

# Channel fit plots  (PNGs are sorted into good/, bad/, failed/ subfolders)
python gain_calibration.py input.root output_dir run_name --plots sample   # up to 100 per category
python gain_calibration.py input.root output_dir run_name --plots all      # every channel
"""

import argparse
import logging
import os
import sys
from multiprocessing import Pool, cpu_count
import random

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d
from tqdm import tqdm

try:
    import ROOT
except ImportError:
    ROOT = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Constants
BIN_WIDTH = 100
BINS = np.arange(0, 50000 + BIN_WIDTH, BIN_WIDTH)
BIN_CENTERS = (BINS[:-1] + BINS[1:]) / 2

#CHI2_MIN = 0.25
CHI2_MAX = 160.0
PEAK_WIDTH = 1200.0
LINEAR_R2_MIN = 0.90

# DEFAULT constraints
FIRST_PEAK_MIN = 1500
FIRST_PEAK_MAX = 9000
MAX_ADC_SEARCH = 48000
MAX_PEAKS = 8
MAX_SIGMA = 3000.0

# Expected gain range (ADC/PE)
EXPECTED_GAIN_MIN = 3200
EXPECTED_GAIN_MAX = 8500
EXPECTED_GAIN_DEFAULT = 6000  # Initial guess

# Fit options
USE_FIRST_PEAK = True
REFINE_FIT = False  # Enable refinement to adapt to detected gain

# Gaussian functions
def gaussian(x, A, mu, sigma):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

def multi_gauss(x, *params):
    result = np.zeros_like(x)
    n_peaks = len(params) // 3
    for i in range(n_peaks):
        result += gaussian(x, params[3*i], params[3*i+1], params[3*i+2])
    return result

# ============================================================
# ADAPTIVE GAIN-BASED CONSTRAINTS
# ============================================================

def get_adaptive_constraints(estimated_gain):
    """
    Adapt constraints based on estimated gain value
    
    For gain = 4000-7000 ADC/PE, scale constraints accordingly
    """
    # Base constraints at 5000 ADC/PE
    base_gain = EXPECTED_GAIN_DEFAULT
    gain_ratio = estimated_gain / base_gain
    
    constraints = {
        'min_spacing': int(EXPECTED_GAIN_MIN * gain_ratio),      # Scale with gain
        'max_spacing': int(EXPECTED_GAIN_MAX * gain_ratio),
        'first_peak_min': int(FIRST_PEAK_MIN * gain_ratio),
        'first_peak_max': int(FIRST_PEAK_MAX * gain_ratio),
        'peak_width': PEAK_WIDTH * gain_ratio,                  # Scale sigma estimates
        'fit_margin': 3.0 * gain_ratio,                         # Fit range margins
    }
    
    logging.debug(f"Adaptive constraints for gain≈{estimated_gain:.0f}: "
                 f"spacing=[{constraints['min_spacing']}, {constraints['max_spacing']}], "
                 f"first_peak=[{constraints['first_peak_min']}, {constraints['first_peak_max']}]")
    
    return constraints

def estimate_gain_from_peaks(peaks):
    """
    Estimate gain from detected peaks (assuming they are 1, 2, 3... PE)
    """
    if len(peaks) < 2:
        return -1
    
    # Calculate spacing between consecutive peaks
    spacings = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
    
    # Use median spacing as gain estimate
    estimated_gain = np.median(spacings)
    
    # Clamp to expected range
    estimated_gain = np.clip(estimated_gain, EXPECTED_GAIN_MIN, EXPECTED_GAIN_MAX)
    
    return estimated_gain

# ============================================================
# PEAK DETECTION
# ============================================================

def detect_peaks(hist, bin_centers, estimated_gain=EXPECTED_GAIN_DEFAULT):
    """
    Peak detection with gain-adaptive constraints
    """
    if np.sum(hist) < 100:
        return []
    
    # Get adaptive constraints
    constraints = get_adaptive_constraints(estimated_gain)
    
    # Strategy 1: Smooth and find peaks
    hist_smooth = gaussian_filter1d(hist, sigma=3)
    
    # Adaptive thresholds
    max_val = np.max(hist_smooth)
    total_counts = np.sum(hist_smooth)
    
    # More lenient thresholds
    if total_counts < 5000:
        min_prominence = 0.003 * max_val
        min_height = 0.001 * max_val
    elif total_counts < 20000:
        min_prominence = 0.005 * max_val
        min_height = 0.002 * max_val
    else:
        min_prominence = 0.008 * max_val
        min_height = 0.003 * max_val
    
    min_distance = int(constraints['min_spacing'] / BIN_WIDTH)
    
    peaks_indices, properties = find_peaks(
        hist_smooth,
        prominence=min_prominence,
        height=min_height,
        distance=min_distance,
        width=1
    )
    
    detected_peaks = bin_centers[peaks_indices].tolist()
    
    # Strategy 2: If too few peaks, try expected positions based on estimated gain
    if len(detected_peaks) < 2:
        # Generate expected positions: 1*gain, 2*gain, 3*gain...
        expected_positions = [estimated_gain * (i+1) for i in range(8)]
        search_window = 0.4 * estimated_gain  # ±40% of gain
        
        detected_peaks = []
        for expected_pos in expected_positions:
            if expected_pos > MAX_ADC_SEARCH:
                break
            
            # Search in window
            mask = (bin_centers >= expected_pos - search_window) & \
                   (bin_centers <= expected_pos + search_window)
            
            if np.sum(mask) == 0:
                continue
                
            window_hist = hist[mask]
            if np.sum(window_hist) < 10:
                continue
                
            window_centers = bin_centers[mask]
            peak_idx = np.argmax(window_hist)
            
            if window_hist[peak_idx] > 0.001 * max_val:
                detected_peaks.append(window_centers[peak_idx])
    
    # Filter peaks with adaptive constraints
    peaks = filter_peaks_adaptive(detected_peaks, hist, constraints)
    
    return peaks

def filter_peaks_adaptive(peaks, hist_data, constraints):
    """
    ADAPTIVE peak filtering with decreasing height constraint
    Uses gain-adaptive constraints
    """
    if len(peaks) == 0:
        return []
    
    # Filter by ADC range
    peaks = [p for p in peaks if p <= MAX_ADC_SEARCH]
    
    if len(peaks) == 0:
        return []
    
    # Sort peaks by position
    peaks = sorted(peaks)
    
    # Find first peak in valid range
    first_peak_candidates = [p for p in peaks if 
                            constraints['first_peak_min'] <= p <= constraints['first_peak_max']]
    
    if len(first_peak_candidates) == 0:
        reasonable_peaks = [p for p in peaks if p > 1000 and p < 10000]
        if reasonable_peaks:
            first_peak = reasonable_peaks[0]
        else:
            return []
    else:
        first_peak_heights = []
        for p in first_peak_candidates:
            idx = np.abs(BIN_CENTERS - p).argmin()
            first_peak_heights.append(hist_data[idx])
        
        first_peak_idx = np.argmax(first_peak_heights)
        first_peak = first_peak_candidates[first_peak_idx]
    
    # Build valid peak list with STRICTER spacing
    valid_peaks = [first_peak]
    
    for p in peaks:
        if p <= first_peak:
            continue
        
        # Check spacing constraint - STRICTER: must be > min_spacing (not >=)
        spacing = p - valid_peaks[-1]
        
        # Lower bound check
        if spacing > constraints['min_spacing'] and spacing <= constraints['max_spacing']:
            valid_peaks.append(p)
            
            if len(valid_peaks) >= MAX_PEAKS:
                break
    
    # Need at least 2 peaks
    if len(valid_peaks) < 2:
        return []
    
    # Enforce decreasing height constraint with stricter tolerance
    peak_heights = []
    for p in valid_peaks:
        idx = np.abs(BIN_CENTERS - p).argmin()
        peak_heights.append(hist_data[idx])
    
    # Height check (5% tolerance)
    for i in range(len(peak_heights) - 1):
        if peak_heights[i+1] > peak_heights[i] * 1.05:  # 5% tolerance
            valid_peaks = valid_peaks[:i+1]
            break
    
    # Need at least 2 peaks after filtering
    if len(valid_peaks) < 2:
        return []
    
    return valid_peaks

# ============================================================
# PARAMETER ESTIMATION
# ============================================================

def estimate_peak_parameters(hist, bin_centers, peak_positions, estimated_gain):
    """
    Better parameter estimation with sqrt(n) scaling and gain-adaptive bounds
    """
    parameters = []
    
    # Get adaptive constraints
    constraints = get_adaptive_constraints(estimated_gain)
    
    # Estimate base width from first peak
    first_peak_pos = peak_positions[0]
    first_peak_idx = np.abs(bin_centers - first_peak_pos).argmin()
    first_amplitude = hist[first_peak_idx]
    
    # Find FWHM
    half_max = first_amplitude / 2.0
    left_idx = first_peak_idx
    while left_idx > 0 and hist[left_idx] > half_max:
        left_idx -= 1
    
    right_idx = first_peak_idx
    while right_idx < len(hist) - 1 and hist[right_idx] > half_max:
        right_idx += 1
    
    fwhm = bin_centers[right_idx] - bin_centers[left_idx]
    base_sigma = fwhm / 2.355 if fwhm > 0 else constraints['peak_width']
    base_sigma = np.clip(base_sigma, 0.15 * estimated_gain, 0.4 * estimated_gain)  # Scale with gain
    
    # Set parameters for all peaks
    for i, peak_pos in enumerate(peak_positions):
        peak_idx = np.abs(bin_centers - peak_pos).argmin()
        amplitude = hist[peak_idx] * 1.5
        
        # sqrt(n) scaling for sigma
        pe_number = i + 1
        sigma = base_sigma * np.sqrt(pe_number)
        sigma = np.clip(sigma, 0.1 * estimated_gain, 0.7 * estimated_gain)  # Scale with gain
        
        parameters.append((amplitude, peak_pos, sigma))
    
    return parameters

# ============================================================
# SCIPY WORKFLOW
# ============================================================

def process_channel_scipy(ch_id, hist_data, refine_params=None):
    """
    SciPy workflow with gain-adaptive constraints
    """
    result = {
        'channel_id': ch_id,
        'method': 'scipy',
        'gain': 0.0,
        'gain_error': 0.0,
        'intercept': 0.0,
        'intercept_error': 0.0,
        'fit_status': -1,
        'chi2_dof': -1.0,
        'n_peaks': 0,
        'hist': hist_data,
        'detected_peaks': [],
        'linear_r2': 0.0,
        'linear_chi2_dof': -1.0,
    }
    
    if np.sum(hist_data) < 500:
        return result
    
    # Estimate gain from refinement or use default
    if refine_params is not None and 'gain' in refine_params and refine_params['gain'] > 0:
        estimated_gain = refine_params['gain']
        logging.debug(f"Channel {ch_id}: Using refined gain estimate = {estimated_gain:.0f}")
    else:
        estimated_gain = EXPECTED_GAIN_DEFAULT
    
    # Get adaptive constraints
    constraints = get_adaptive_constraints(estimated_gain)
    
    # Detect peaks with adaptive constraints
    peaks = detect_peaks(hist_data, BIN_CENTERS, estimated_gain)
    
    if len(peaks) < 2:
        return result
    
    # Update gain estimate based on detected peaks
    estimated_gain = estimate_gain_from_peaks(peaks)
    constraints = get_adaptive_constraints(estimated_gain)
    
    result['detected_peaks'] = peaks
    result['n_peaks'] = len(peaks)
    
    # Decide which peaks to use
    if USE_FIRST_PEAK or len(peaks) == 2:
        fit_peaks = peaks
        first_peak_number = 1
    else:
        fit_peaks = peaks[1:]
        first_peak_number = 2
    
    if len(fit_peaks) < 2:
        return result
    
    # Define fit range with adaptive margins
    fit_min = fit_peaks[0] - constraints['peak_width'] * constraints['fit_margin']
    fit_max = fit_peaks[-1] + constraints['peak_width'] * constraints['fit_margin']
    
    fit_mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
    fit_x = BIN_CENTERS[fit_mask]
    fit_y = hist_data[fit_mask]
    
    n_fit_peaks = len(fit_peaks)
    
    # Parameter initialization
    if refine_params is not None and 'fit_params' in refine_params:
        initial_params = refine_params['fit_params']
        
        # Check if we have enough parameters from previous fit
        n_prev_peaks = len(initial_params) // 3
        
        if n_prev_peaks >= n_fit_peaks:
            # We can reuse parameters from previous fit
            initial_params = initial_params[:3*n_fit_peaks]
            bounds_low = []
            bounds_high = []
            
            for j in range(n_fit_peaks):
                A = initial_params[3*j]
                mu = initial_params[3*j + 1]
                sigma = initial_params[3*j + 2]

                # Sigma should be reasonable fraction of gain
                if sigma < 0.05 * estimated_gain or sigma > 0.8 * estimated_gain:
                    logging.debug(f"Channel {ch_id}: Invalid sigma={sigma:.0f} for gain≈{estimated_gain:.0f}, skipping fit")
                    return result
                
                # Peak positions should be reasonably spaced
                if j > 0:
                    prev_mu = initial_params[3*(j-1) + 1]
                    if mu - prev_mu < 0.5 * constraints['min_spacing']:
                        logging.debug(f"Channel {ch_id}: Peaks too close (Δ={mu-prev_mu:.0f}), skipping fit")
                        return result
                
                # Gain-adaptive bounds (wider for higher gain)
                mu_tol = 0.25 * estimated_gain
                bounds_low.extend([0.05 * A, mu - mu_tol, 0.3 * sigma])
                bounds_high.extend([20.0 * A, mu + mu_tol, 3.0 * sigma])
        else:
            # Previous fit had fewer peaks - fall back to new parameter estimation
            logging.debug(f"Channel {ch_id}: Previous fit had {n_prev_peaks} peaks, "
                        f"current detection has {n_fit_peaks} peaks. Using new parameter estimation.")
            refine_params = None  # Fall through to else block
            
    if refine_params is None or 'fit_params' not in refine_params:
        param_estimates = estimate_peak_parameters(
            hist_data, BIN_CENTERS, fit_peaks, estimated_gain
        )
        
        initial_params = []
        bounds_low = []
        bounds_high = []
        
        for j, (A, mu, sigma) in enumerate(param_estimates):
            pe_number = first_peak_number + j
            sigma_scaled = param_estimates[0][2] * np.sqrt(pe_number / first_peak_number)
            
            # Gain-adaptive bounds
            mu_tol = 0.3 * estimated_gain
            initial_params.extend([A, mu, sigma_scaled])
            bounds_low.extend([0.05 * A, mu - mu_tol, 0.3 * sigma_scaled])
            
            # Limit sigma
            sigma_upper = min(3.0 * sigma_scaled, MAX_SIGMA)
            bounds_high.extend([20.0 * A, mu + mu_tol, sigma_upper])
    
    # Weighted fitting
    weights = np.sqrt(np.maximum(fit_y, 1))
    
    try:
        popt, pcov = curve_fit(
            lambda x, *params: multi_gauss(x, *params),
            fit_x,
            fit_y,
            p0=initial_params,
            bounds=(bounds_low, bounds_high),
            sigma=1.0/weights,
            absolute_sigma=False,
            maxfev=10000,
            method='trf'
        )
        
        result['fit_status'] = 1
        result['fit_params'] = popt
        
        # Calculate chi2/dof
        y_fit = multi_gauss(fit_x, *popt)
        residuals = fit_y - y_fit
        
        chi2 = np.sum((residuals * weights)**2)
        dof = len(fit_x) - len(popt)
        result['chi2_dof'] = chi2 / dof if dof > 0 else -1
        
        # Extract peak means and errors
        mu_values = [popt[3*i + 1] for i in range(n_fit_peaks)]
        mu_indices = [3*i + 1 for i in range(n_fit_peaks)]
        mu_errors = np.sqrt(np.diag(pcov)[mu_indices])
        
        # Linear fit
        peak_numbers = np.arange(first_peak_number, first_peak_number + n_fit_peaks)
        weights_lin = 1.0 / (mu_errors**2)
        
        W = np.diag(weights_lin)
        X = np.column_stack([np.ones(n_fit_peaks), peak_numbers])
        Y = np.array(mu_values)
        
        XtWX = X.T @ W @ X
        cov_beta = np.linalg.inv(XtWX)
        beta = cov_beta @ (X.T @ W @ Y)
        
        result['intercept'] = beta[0]
        result['gain'] = beta[1]
        result['intercept_error'] = np.sqrt(cov_beta[0, 0])
        result['gain_error'] = np.sqrt(cov_beta[1, 1])
        
        # R² and chi2/dof
        y_pred = result['intercept'] + result['gain'] * peak_numbers
        residuals_lin = Y - y_pred
        
        y_mean = np.mean(Y)
        ss_tot = np.sum((Y - y_mean)**2)
        ss_res = np.sum(residuals_lin**2)
        result['linear_r2'] = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        chi2_linear = residuals_lin.T @ W @ residuals_lin
        dof_linear = n_fit_peaks - 2
        result['linear_chi2_dof'] = chi2_linear / dof_linear if dof_linear > 0 else -1
        
    except Exception as e:
        logging.debug(f"Channel {ch_id}: Fit failed - {str(e)}")
        return result
    
    return result

# ============================================================
# ROOT WORKFLOW
# ============================================================

def process_channel_root(ch_id, hist_data, refine_params=None):
    """
    ROOT workflow with gain-adaptive constraints
    """
    result = {
        'channel_id': ch_id,
        'method': 'root_tspectrum',
        'gain': 0.0,
        'gain_error': 0.0,
        'intercept': 0.0,
        'intercept_error': 0.0,
        'fit_status': -1,
        'chi2_dof': -1.0,
        'n_peaks': 0,
        'hist': hist_data,
        'detected_peaks': [],
        'linear_r2': 0.0,
        'linear_chi2_dof': -1.0,
    }
    
    if np.sum(hist_data) < 1000:
        return result
    
    # Estimate gain from refinement or use default
    if refine_params is not None and 'gain' in refine_params and refine_params['gain'] > 0:
        estimated_gain = refine_params['gain']
        logging.debug(f"Channel {ch_id}: Using refined gain estimate = {estimated_gain:.0f}")
    else:
        estimated_gain = EXPECTED_GAIN_DEFAULT
    
    # Get adaptive constraints
    constraints = get_adaptive_constraints(estimated_gain)
    
    # Convert to ROOT histogram
    nbins = len(hist_data)
    xmin = BIN_CENTERS[0] - BIN_WIDTH/2
    xmax = BIN_CENTERS[-1] + BIN_WIDTH/2
    
    h = ROOT.TH1D(f"h_{ch_id}", "", nbins, xmin, xmax)
    for i, val in enumerate(hist_data):
        h.SetBinContent(i+1, val)
    
    # TSpectrum with adaptive sigma (scale with gain)
    #h.Smooth(0)
    spectrum = ROOT.TSpectrum(MAX_PEAKS + 2)
    
    # Adaptive sigma: smaller for low gain, larger for high gain
    # tspectrum_sigma = 2.0 * (estimated_gain / 5000.0)
    # tspectrum_sigma = np.clip(tspectrum_sigma, 1.5, 4.0)
    
    n_found = spectrum.Search(h, 4.0, "", 0.0005)
    
    if n_found < 2:
        del h
        return result
    
    # Extract peaks
    xpeaks = spectrum.GetPositionX()
    peaks = sorted([xpeaks[i] for i in range(n_found)])
    
    # Update gain estimate from detected peaks
    if len(peaks) >= 2:
        estimated_gain = estimate_gain_from_peaks(peaks)
        constraints = get_adaptive_constraints(estimated_gain)
    
    # Filter peaks with adaptive constraints
    peaks = filter_peaks_adaptive(peaks, hist_data, constraints)
    
    if len(peaks) < 2:
        del h
        return result
    
    result['detected_peaks'] = peaks
    result['n_peaks'] = len(peaks)
    
    # Decide which peaks to use
    if USE_FIRST_PEAK or len(peaks) == 2:
        fit_peaks = peaks
        first_peak_number = 1
    else:
        fit_peaks = peaks[1:]
        first_peak_number = 2
    
    if len(fit_peaks) < 2:
        del h
        return result
    
    # Define fit range with adaptive margins
    fit_min = fit_peaks[0] - constraints['peak_width'] * constraints['fit_margin']
    fit_max = fit_peaks[-1] + constraints['peak_width'] * constraints['fit_margin']
    
    n_fit_peaks = len(fit_peaks)
    
    # Build formula
    formula_parts = []
    for i in range(n_fit_peaks):
        amp_idx = 3*i
        mean_idx = 3*i + 1
        sigma_idx = 3*i + 2
        gauss = f"[{amp_idx}]*exp(-0.5*((x-[{mean_idx}])/[{sigma_idx}])^2)"
        formula_parts.append(gauss)
    
    formula = "+".join(formula_parts)
    f1 = ROOT.TF1(f"fit_{ch_id}", formula, fit_min, fit_max)
    
    # Estimate base sigma
    bin_idx = h.FindBin(fit_peaks[0])
    amplitude_estimate = h.GetBinContent(bin_idx)
    
    half_max = amplitude_estimate / 2.0
    left_bin = bin_idx
    right_bin = bin_idx
    
    while left_bin > 1 and h.GetBinContent(left_bin) > half_max:
        left_bin -= 1
    while right_bin < h.GetNbinsX() and h.GetBinContent(right_bin) > half_max:
        right_bin += 1
    
    fwhm = h.GetBinCenter(right_bin) - h.GetBinCenter(left_bin)
    base_sigma = fwhm / 2.355 if fwhm > 0 else constraints['peak_width']
    base_sigma = np.clip(base_sigma, 0.15 * estimated_gain, 0.4 * estimated_gain)
    
    # Set parameters
    for j, peak_pos in enumerate(fit_peaks):
        bin_idx = h.FindBin(peak_pos)
        amplitude_estimate = h.GetBinContent(bin_idx)
        
        pe_number = first_peak_number + j
        sigma_estimate = base_sigma * np.sqrt(pe_number / first_peak_number)
        
        # Check if refinement params are available and have enough peaks
        if (refine_params and 'fit_params' in refine_params and 
            len(refine_params['fit_params']) >= 3*(j+1)):
            f1.SetParameter(3*j, refine_params['fit_params'][3*j])
            f1.SetParameter(3*j + 1, refine_params['fit_params'][3*j + 1])
            f1.SetParameter(3*j + 2, refine_params['fit_params'][3*j + 2])
        else:
            f1.SetParameter(3*j, amplitude_estimate)
            f1.SetParameter(3*j + 1, peak_pos)
            f1.SetParameter(3*j + 2, sigma_estimate)
        
        # Gain-adaptive limits
        mu_tol = 0.3 * estimated_gain
        f1.SetParLimits(3*j, 0.05*amplitude_estimate, 20*amplitude_estimate)
        f1.SetParLimits(3*j + 1, peak_pos - mu_tol, peak_pos + mu_tol)
        
        # Limit sigma to MAX_SIGMA
        sigma_upper = min(4.0 * sigma_estimate, MAX_SIGMA)
        f1.SetParLimits(3*j + 2, 0.2*sigma_estimate, sigma_upper)
    
    # Perform fit
    fit_result = h.Fit(f1, "SRBQ", "", fit_min, fit_max)
    
    if not fit_result or int(fit_result) != 0:
        del h, f1
        return result
    
    result['fit_status'] = 1
    
    # Store parameters
    fit_params = []
    for j in range(n_fit_peaks):
        fit_params.append(fit_result.Parameter(3*j))
        fit_params.append(fit_result.Parameter(3*j + 1))
        fit_params.append(fit_result.Parameter(3*j + 2))
    result['fit_params'] = fit_params
    
    # Chi2/dof
    chi2 = fit_result.Chi2()
    ndf = fit_result.Ndf()
    result['chi2_dof'] = chi2 / ndf if ndf > 0 else -1
    
    # Extract means and errors
    mu_values = []
    mu_errors = []
    
    for j in range(n_fit_peaks):
        mu = fit_result.Parameter(3*j + 1)
        mu_err = fit_result.ParError(3*j + 1)
        mu_values.append(mu)
        mu_errors.append(mu_err)
    
    # Linear fit
    peak_numbers = np.arange(first_peak_number, first_peak_number + n_fit_peaks)
    
    gr = ROOT.TGraphErrors(n_fit_peaks)
    for j in range(n_fit_peaks):
        gr.SetPoint(j, peak_numbers[j], mu_values[j])
        gr.SetPointError(j, 0.0, mu_errors[j])
    
    linear_fit = ROOT.TF1(f"linear_fit_{ch_id}", "pol1", 
                          first_peak_number, first_peak_number + n_fit_peaks - 1)
    
    linear_result = gr.Fit(linear_fit, "SRQ")
    
    if linear_result and int(linear_result) == 0:
        result['intercept'] = linear_result.Parameter(0)
        result['intercept_error'] = linear_result.ParError(0)
        result['gain'] = linear_result.Parameter(1)
        result['gain_error'] = linear_result.ParError(1)
        
        linear_chi2 = linear_result.Chi2()
        linear_ndf = linear_result.Ndf()
        result['linear_chi2_dof'] = linear_chi2 / linear_ndf if linear_ndf > 0 else -1
        
        # R²
        y_mean = np.mean(mu_values)
        ss_tot = np.sum((np.array(mu_values) - y_mean)**2)
        y_pred = [result['intercept'] + result['gain'] * pn for pn in peak_numbers]
        ss_res = np.sum((np.array(mu_values) - np.array(y_pred))**2)
        result['linear_r2'] = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    del h, f1, gr, linear_fit
    return result

# ============================================================
# MAIN PROCESSING 
# ============================================================

def process_channel(args):
    """Process channel with selected workflow"""
    ch_id, hist_data, workflow, refine_params = args
    
    if workflow == 'root':
        result_root = process_channel_root(ch_id, hist_data, refine_params)
        return (result_root, None)
    elif workflow == 'scipy':
        result_scipy = process_channel_scipy(ch_id, hist_data, refine_params)
        return (None, result_scipy)
    else:  # both
        result_root = process_channel_root(ch_id, hist_data, refine_params)
        result_scipy = process_channel_scipy(ch_id, hist_data, refine_params)
        return (result_root, result_scipy)

def plot_channel_fit(result, output_dir, label):
    """Generate plot for a single channel"""
    ch_id = result['channel_id']
    method = result['method']
    hist = result['hist']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Determine fit quality
    if (result['fit_status'] == 1 and result['chi2_dof'] <= CHI2_MAX and result['linear_r2'] >= LINEAR_R2_MIN
    and (EXPECTED_GAIN_MIN <= result['gain'] <= EXPECTED_GAIN_MAX)):
        fit_quality = "GOOD"
        color = 'green'
    elif (result['fit_status'] == 1 and result['chi2_dof'] > CHI2_MAX or result['linear_r2'] < LINEAR_R2_MIN
        or result['gain'] < EXPECTED_GAIN_MIN or result['gain'] > EXPECTED_GAIN_MAX):
        fit_quality = "BAD"
        color = 'orange'
    else:
        fit_quality = "FAILED"
        color = 'red'
    
    plt.suptitle(f"Channel {ch_id} ({method.upper()}) - {fit_quality} Fit", 
                 fontsize=12, color=color, fontweight='bold')
    
    # Plot 1: Histogram + Multi-Gaussian
    ax1.step(BIN_CENTERS, hist, where='mid', color='black', 
             linewidth=0.5, alpha=0.8, label='Data')
    
    if result['fit_status'] == 1 and len(result['detected_peaks']) > 0:
        peaks = result['detected_peaks']
        
        # Show all detected peaks with correct PE labels
        for i, peak in enumerate(peaks):
            idx = np.abs(BIN_CENTERS - peak).argmin()
            peak_height = hist[idx]
            pe_label = f'{i+1} PE'  # 1 PE, 2 PE, 3 PE, etc.
            ax1.plot(peak, peak_height, 'ro', markersize=5, 
                    markeredgecolor='darkred', markeredgewidth=1.0,
                    label=f'Detected: {pe_label}' if i < 3 else '')
        
        # Determine which peaks were used in fit
        if USE_FIRST_PEAK:
            fit_peaks = peaks
            first_pe_used = 1
        else:
            fit_peaks = peaks[1:]
            first_pe_used = 2
        
        fit_min = fit_peaks[0] - PEAK_WIDTH
        fit_max = fit_peaks[-1] + PEAK_WIDTH
        
        # Plot multi-gaussian fit
        fit_mask = (BIN_CENTERS >= fit_min) & (BIN_CENTERS <= fit_max)
        x_fit = BIN_CENTERS[fit_mask]
        
        if 'fit_params' in result and len(result['fit_params']) > 0:
            y_fit = multi_gauss(x_fit, *result['fit_params'])
            ax1.plot(x_fit, y_fit, 'b-', linewidth=1.5, alpha=0.8, label='Multi-Gauss fit')

            # Show fitted means and sigmas
            n_fitted_peaks = len(result['fit_params']) // 3
            for i in range(n_fitted_peaks):
                mu = result['fit_params'][3*i + 1]
                sigma = result['fit_params'][3*i + 2]
                pe_num = first_pe_used + i
                ax1.axvline(mu, color=f'C{i}', linestyle='--', linewidth=1.5, 
                           alpha=0.7, label=f'{pe_num} PE: μ={mu:.0f}, σ={sigma:.0f}')
    
    ax1.set_xlabel('ADC Value', fontsize=11)
    ax1.set_ylabel('Counts', fontsize=11)
    ax1.set_yscale('log')
    
    y_max = hist.max()
    ax1.set_ylim(0.5, y_max * 200)
    
    ax1.legend(fontsize=7, ncol=2, loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Info Box
    status_text = "SUCCESS" if result['fit_status'] == 1 else "FAILED"
    
    if result['fit_status'] == 1:
        info_text = (
            f"STATUS: {status_text}\n"
            f"Method: {method}\n"
            f"Quality: {fit_quality}\n"
            f"────────────────────\n"
            f"Total Events: {int(np.sum(hist))}\n"
            #f"Detected Peaks: {result['n_peaks']}\n"
            #f"Used in Fit: {len(result['fit_params'])//3}\n"
            f"1 PE Used in Fit: {'Yes' if USE_FIRST_PEAK else 'No'}\n"
            f"────────────────────\n"
            f"Multi-Gauss χ²/dof: {result['chi2_dof']:.2f}\n"
        )
    else:
        info_text = (
            f"STATUS: {status_text}\n"
            f"Method: {method}\n"
            f"Quality: {fit_quality}\n"
            f"────────────────────\n"
            f"Total Events: {int(np.sum(hist))}\n"
            f"Detected Peaks: {len(result['detected_peaks'])}\n"
        )
    
    bbox_color = 'lightgreen' if fit_quality == "GOOD" else 'lightcoral'
    ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, 
            verticalalignment='top', horizontalalignment='left', 
            fontsize=8, family='monospace',
            bbox=dict(boxstyle='round', facecolor=bbox_color, alpha=0.7))
    
    # Plot 2: Linear fit
    if result['fit_status'] == 1 and result['gain'] > 0:
        n_fit_peaks = len(result['fit_params']) // 3 if 'fit_params' in result else 0
        
        if n_fit_peaks >= 2:
            first_pe_used = 1 if USE_FIRST_PEAK else 2
            peak_nums = list(range(first_pe_used, first_pe_used + n_fit_peaks))
            
            if 'fit_params' in result and len(result['fit_params']) >= 3*n_fit_peaks:
                mu_vals = [result['fit_params'][3*i + 1] for i in range(n_fit_peaks)]
            else:
                # Use detected peaks if fit_params not available
                if USE_FIRST_PEAK:
                    mu_vals = result['detected_peaks'][:n_fit_peaks]
                else:
                    mu_vals = result['detected_peaks'][1:n_fit_peaks+1]
            
            ax2.plot(peak_nums, mu_vals, 'o', color='blue', 
                    markersize=8, label='Fitted Means')
            
            x_fit = np.array([first_pe_used, first_pe_used + n_fit_peaks - 1])
            y_fit = result['intercept'] + result['gain'] * x_fit
            ax2.plot(x_fit, y_fit, 'r-', lw=2.5, 
                    label=f'μ = {result["intercept"]:.0f} + {result["gain"]:.0f}·n')
            
            ax2.set_xlabel('Peak Number (PE)', fontsize=11)
            ax2.set_ylabel('ADC Value', fontsize=11)
            ax2.grid(True, alpha=0.3)
            ax2.set_title('Gain Calculation', fontsize=12, fontweight='bold')
            ax2.legend(loc='lower right', fontsize=9)
            
            # Gain info box
            gain_info = (
                f"μ = {result['intercept']:.0f} + {result['gain']:.0f}·n\n"
                f"────────────────────\n"
                f"Gain: {result['gain']:.0f} ± {result['gain_error']:.0f} ADC/PE\n"
                f"Intercept: {result['intercept']:.0f} ± {result['intercept_error']:.0f}\n"
                f"────────────────────\n"
                f"Linear R²: {result['linear_r2']:.3f}\n"
                f"Linear χ²/dof: {result['linear_chi2_dof']:.2f}\n"
            )
            
            ax2.text(0.05, 0.97, gain_info, transform=ax2.transAxes, 
                    verticalalignment='top', horizontalalignment='left', 
                    fontsize=9, family='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.85))
    else:
        ax2.text(0.5, 0.5, 'No successful fit', 
                transform=ax2.transAxes, ha='center', va='center', 
                fontsize=12, color='red')
        ax2.set_title('Gain Calculation', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    quality_subdir = os.path.join(output_dir, fit_quality.lower())
    os.makedirs(quality_subdir, exist_ok=True)
    plot_file = os.path.join(quality_subdir, f"ch{ch_id:04d}_{label}.png")
    fig.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close(fig)


def create_summary_plots(results, method_name, output_dir):
    """Create comprehensive summary plots (2x4 layout) with log scale and DYNAMIC ranges"""
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    
    max_channels = len(results)
    
    # Classification
    good_fits = [r for r in results if r['fit_status'] == 1 and 
             (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN) and
             (EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX)]  
    
    bad_fits = [r for r in results if r['fit_status'] == 1 and 
            (r['chi2_dof'] > CHI2_MAX or r['linear_r2'] < LINEAR_R2_MIN or
             r['gain'] < EXPECTED_GAIN_MIN or r['gain'] > EXPECTED_GAIN_MAX)]
    
    failed_fits = [r for r in results if r['fit_status'] != 1]
    
    n_good = len(good_fits)
    n_bad = len(bad_fits)
    n_failed = len(failed_fits)
    
    pct_good = 100 * n_good / max_channels
    pct_bad = 100 * n_bad / max_channels
    pct_failed = 100 * n_failed / max_channels
    
    logging.info(f"\n{method_name} Classification:")
    logging.info(f"  Good fits: {n_good} ({pct_good:.1f}%)")
    logging.info(f"  Bad fits: {n_bad} ({pct_bad:.1f}%)")
    logging.info(f"  Failed fits: {n_failed} ({pct_failed:.1f}%)")
    
    # =========================================================================
    # Row 1: Good Fits
    # =========================================================================
    
    # Col 1: Gain Distribution
    ax = axes[0, 0]
    if good_fits:
        g = [r['gain'] for r in good_fits]
        mu, med, std = np.mean(g), np.median(g), np.std(g)
        
        # Dynamic range: mean ± 3σ
        hist_range = (max(0, mu - 3*std), mu + 3*std)
        n_outside = sum(1 for val in g if val < hist_range[0] or val > hist_range[1])
        
        legend_text = (f'Good: {n_good} ({pct_good:.1f}%)\n'
                      f'Mean: {mu:.1f}\n'
                      f'Median: {med:.1f}\n'
                      f'Std.Dev.: {std:.1f}')
        
        ax.hist(g, bins=50, range=hist_range, color='green', alpha=0.7, edgecolor='k')
        ax.axvline(mu, c='red', ls='--', lw=2)
        ax.axvline(med, c='orange', ls='--', lw=2)
        ax.set_yscale('log')
        ax.text(0.65, 0.97, legend_text, transform=ax.transAxes, 
               va='top', fontsize=9, family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        if n_outside > 0:
            ax.text(0.02, 0.97, f'Outside μ±3σ: {n_outside}', transform=ax.transAxes,
                   va='top', ha='left', fontsize=9, family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Good Fits: Gain Distribution', fontweight='bold')
    ax.set_xlabel('Gain (ADC/PE)')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)

    # Col 2: Multi-Gauss Chi2/dof Distribution
    ax = axes[0, 1]
    if good_fits:
        chi2_vals = [r['chi2_dof'] for r in good_fits if r['chi2_dof'] > 0]
        if chi2_vals:
            mu_chi2 = np.mean(chi2_vals)
            std_chi2 = np.std(chi2_vals)
            hist_range = (0, min(CHI2_MAX, mu_chi2 + 3*std_chi2))
            n_outside = sum(1 for val in chi2_vals if val > hist_range[1])
            
            ax.hist(chi2_vals, bins=50, range=hist_range, color='blue', alpha=0.7, edgecolor='k')
            ax.set_yscale('log')
            
            if n_outside > 0:
                ax.text(0.98, 0.97, f'χ²/dof > {hist_range[1]:.1f}: {n_outside}', 
                       transform=ax.transAxes, va='top', ha='right', fontsize=9, 
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Good Fits: Multi-Gauss χ²/dof', fontweight='bold')
    ax.set_xlabel('χ²/dof')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)

    # Col 3: R² Distribution
    ax = axes[0, 2]
    if good_fits:
        r2_vals = [r['linear_r2'] for r in good_fits]
        if r2_vals:
            min_r2 = np.min(r2_vals)
            hist_range = (max(0.90, min_r2 - 0.01), 1.0)
            n_outside = sum(1 for val in r2_vals if val < hist_range[0])
            
            ax.hist(r2_vals, bins=50, range=hist_range, color='purple', alpha=0.7, edgecolor='k')
            ax.set_yscale('log')
            
            if n_outside > 0:
                ax.text(0.02, 0.97, f'R² < {hist_range[0]:.2f}: {n_outside}', 
                       transform=ax.transAxes, va='top', ha='left', fontsize=9, 
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Good Fits: Linear R² Distribution', fontweight='bold')
    ax.set_xlabel('R²')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)
    
    # Col 4: Linear Chi2/dof Distribution
    ax = axes[0, 3]
    if good_fits:
        lin_chi2_vals = [r['linear_chi2_dof'] for r in good_fits if r['linear_chi2_dof'] > 0]
        if lin_chi2_vals:
            mu_lin = np.mean(lin_chi2_vals)
            std_lin = np.std(lin_chi2_vals)
            hist_range = (0, mu_lin + 3*std_lin)
            n_outside = sum(1 for val in lin_chi2_vals if val > hist_range[1])
            
            ax.hist(lin_chi2_vals, bins=50, range=hist_range, color='orange', alpha=0.7, edgecolor='k')
            ax.set_yscale('log')
            
            if n_outside > 0:
                ax.text(0.98, 0.97, f'χ²/dof > {hist_range[1]:.1f}: {n_outside}', 
                       transform=ax.transAxes, va='top', ha='right', fontsize=9, 
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Good Fits: Linear χ²/dof', fontweight='bold')
    ax.set_xlabel('χ²/dof')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)

    # =========================================================================
    # Row 2: Bad Fits
    # =========================================================================
    
    # Col 1: Gain Distribution
    ax = axes[1, 0]
    bad_nonzero = [r for r in bad_fits if r['gain'] > 0]
    if bad_nonzero:
        g = [r['gain'] for r in bad_nonzero]
        mu, med, std = np.mean(g), np.median(g), np.std(g)
        
        # Dynamic range for bad fits
        hist_range = (max(0, mu - 3*std), mu + 3*std)
        n_outside = sum(1 for val in g if val < hist_range[0] or val > hist_range[1])

        legend_text = (f'Bad: {n_bad} ({pct_bad:.1f}%)\n'
                      f'Failed fit: {n_failed} ({pct_failed:.1f}%)\n'
                      f'Mean: {mu:.1f}\n'
                      f'Median: {med:.1f}\n'
                      f'Std.Dev.: {std:.1f}')

        ax.hist(g, bins=50, range=hist_range, color='red', alpha=0.6, edgecolor='k')
        ax.axvline(mu, c='darkred', ls='--', lw=2)
        ax.axvline(med, c='orange', ls='--', lw=2)
        ax.set_yscale('log')
        ax.text(0.65, 0.97, legend_text, transform=ax.transAxes, 
               va='top', fontsize=9, family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
        
        if n_outside > 0:
            ax.text(0.02, 0.97, f'Outside μ±3σ: {n_outside}', transform=ax.transAxes,
                   va='top', ha='left', fontsize=9, family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Bad Fits: Gain Distribution', fontweight='bold')
    ax.set_xlabel('Gain (ADC/PE)')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)

    # Col 2: Multi-Gauss Chi2/dof Distribution
    ax = axes[1, 1]
    if bad_nonzero:
        chi2_vals = [r['chi2_dof'] for r in bad_nonzero if r['chi2_dof'] > 0]
        if chi2_vals:
            mu_chi2 = np.mean(chi2_vals)
            std_chi2 = np.std(chi2_vals)
            hist_range = (0, mu_chi2 + 3*std_chi2)
            n_outside = sum(1 for val in chi2_vals if val > hist_range[1])
            
            ax.hist(chi2_vals, bins=50, range=hist_range, color='blue', alpha=0.6, edgecolor='k')
            ax.set_yscale('log')
            
            if n_outside > 0:
                ax.text(0.98, 0.97, f'χ²/dof > {hist_range[1]:.1f}: {n_outside}', 
                       transform=ax.transAxes, va='top', ha='right', fontsize=9, 
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Bad Fits: Multi-Gauss χ²/dof', fontweight='bold')
    ax.set_xlabel('χ²/dof')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)

    # Col 3: R² Distribution
    ax = axes[1, 2]
    if bad_nonzero:
        r2_vals = [r['linear_r2'] for r in bad_nonzero if r['linear_r2'] > 0]
        if r2_vals:
            min_r2 = max(0, np.min(r2_vals) - 0.05)
            hist_range = (min_r2, 1.0)
            n_outside = sum(1 for val in r2_vals if val < hist_range[0] or val > hist_range[1])
            
            ax.hist(r2_vals, bins=50, range=hist_range, color='purple', alpha=0.6, edgecolor='k')
            ax.set_yscale('log')
            
            if n_outside > 0:
                ax.text(0.02, 0.97, f'Outside [{hist_range[0]:.2f}, {hist_range[1]:.2f}]: {n_outside}', 
                       transform=ax.transAxes, va='top', ha='left', fontsize=9, 
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Bad Fits: Linear R² Distribution', fontweight='bold')
    ax.set_xlabel('R²')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)
    
    # Col 4: Linear Chi2/dof Distribution
    ax = axes[1, 3]
    if bad_nonzero:
        lin_chi2_vals = [r['linear_chi2_dof'] for r in bad_nonzero if r['linear_chi2_dof'] > 0]
        if lin_chi2_vals:
            mu_lin = np.mean(lin_chi2_vals)
            std_lin = np.std(lin_chi2_vals)
            hist_range = (0, mu_lin + 3*std_lin)
            n_outside = sum(1 for val in lin_chi2_vals if val > hist_range[1])
            
            ax.hist(lin_chi2_vals, bins=50, range=hist_range, color='orange', alpha=0.6, edgecolor='k')
            ax.set_yscale('log')
            
            if n_outside > 0:
                ax.text(0.98, 0.97, f'χ²/dof > {hist_range[1]:.1f}: {n_outside}', 
                       transform=ax.transAxes, va='top', ha='right', fontsize=9, 
                       family='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title(f'Bad Fits: Linear χ²/dof', fontweight='bold')
    ax.set_xlabel('χ²/dof')
    ax.set_ylabel('Counts')
    ax.grid(True, alpha=0.3)

    plt.suptitle(f"{method_name} Calibration Summary", fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    save_path = os.path.join(output_dir, f'summary_plots_{method_name.lower().replace(" ", "_")}.png')
    plt.savefig(save_path, dpi=150)
    plt.close()
    logging.info(f"Saved {save_path}")

def create_gain_intercept_distributions(results, method_name, output_dir):
    """
    Create separate detailed plots for gain and intercept distributions
    Shows mean, median, and sigma with clear legends
    Creates separate plots for GOOD fits and BAD fits
    """
       
    # Classify results
    good_fits = [r for r in results if r['fit_status'] == 1 and 
             (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN) and
             (EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX)]  
    
    bad_fits = [r for r in results if r['fit_status'] == 1 and 
            (r['chi2_dof'] > CHI2_MAX or r['linear_r2'] < LINEAR_R2_MIN or
             r['gain'] < EXPECTED_GAIN_MIN or r['gain'] > EXPECTED_GAIN_MAX)]
    
    #=========================================================================
    #GOOD FITS PLOT
    #=========================================================================
    if len(good_fits) == 0:
        logging.warning(f"No good fits found for {method_name} - skipping good fits distribution plots")
    else:
        #Extract gain and intercept values
        gains = np.array([r['gain'] for r in good_fits if r['gain'] > 0])
        intercepts = np.array([r['intercept'] for r in good_fits])
        
        if len(gains) == 0:
            logging.warning(f"No valid gain values for {method_name} - skipping good fits distribution plots")
        else:
            #Create figure with 2 subplots
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    
    # =========================================================================
    # LEFT PLOT: GAIN DISTRIBUTION
    # =========================================================================
    ax = axes[0]
    
    # Calculate statistics
    gain_mean = np.mean(gains)
    gain_median = np.median(gains)
    gain_std = np.std(gains)
    
    # Dynamic range: mean ± 3σ
    #hist_range = (max(0, gain_mean - 3*gain_std), gain_mean + 3*gain_std)

    # NO DYNAMIC RANGE - use full data range
    hist_range = (gains.min(), gains.max())

    # Histogram
    n, bins, patches = ax.hist(gains, bins=60, range=hist_range, 
                                color='steelblue', alpha=0.7, edgecolor='black',
                                label=f'Good fits (n={len(gains)})')
    
    # Add vertical lines for mean, median, ±1σ
    y_max = ax.get_ylim()[1]
    
    ax.axvline(gain_mean, color='red', linestyle='--', linewidth=2.5, 
              label=f'Mean = {gain_mean:.1f} ADC/PE')
    ax.axvline(gain_median, color='orange', linestyle='--', linewidth=2.5,
              label=f'Median = {gain_median:.1f} ADC/PE')
    
    # ±1σ lines
    ax.axvline(gain_mean - gain_std, color='green', linestyle=':', linewidth=2,
              label=f'±1σ = {gain_std:.1f} ADC/PE')
    ax.axvline(gain_mean + gain_std, color='green', linestyle=':', linewidth=2)
    
    # Shaded ±1σ region
    # ax.axvspan(gain_mean - gain_std, gain_mean + gain_std, 
    #          alpha=0.2, color='green', label='±1σ region')
    
    # Labels and formatting
    ax.set_xlabel('Gain (ADC/PE)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Channels', fontsize=13, fontweight='bold')
    ax.set_title(f'Gain Distribution (Good Fits) - {method_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
    
    # Statistics box
    stats_text = (
        f"Statistics:\n"
        f"{'─'*25}\n"
        f"N channels: {len(gains)}\n"
        f"Mean:   {gain_mean:.2f} ADC/PE\n"
        f"Median: {gain_median:.2f} ADC/PE\n"
        f"Std Dev: {gain_std:.2f} ADC/PE\n"
        f"Min:    {gains.min():.2f} ADC/PE\n"
        f"Max:    {gains.max():.2f} ADC/PE\n"
        f"{'─'*25}\n"
        f"Rel. Std Dev: {100*gain_std/gain_mean:.2f}%"
    )
    
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes,
           fontsize=10, family='monospace', verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, pad=0.8))
    
    # =========================================================================
    # RIGHT PLOT: INTERCEPT DISTRIBUTION
    # =========================================================================
    ax = axes[1]
    
    # Calculate statistics
    int_mean = np.mean(intercepts)
    int_median = np.median(intercepts)
    int_std = np.std(intercepts)
    
    # Dynamic range: mean ± 3σ (but allow negative values)
    #hist_range = (int_mean - 3*int_std, int_mean + 3*int_std)

    # NO DYNAMIC RANGE - use full data range
    hist_range = (intercepts.min(), intercepts.max())

    # Histogram
    n, bins, patches = ax.hist(intercepts, bins=60, range=hist_range,
                                color='coral', alpha=0.7, edgecolor='black',
                                label=f'Good fits (n={len(intercepts)})')
    
    # Add vertical lines
    y_max = ax.get_ylim()[1]
    
    ax.axvline(int_mean, color='red', linestyle='--', linewidth=2.5,
              label=f'Mean = {int_mean:.1f} ADC')
    ax.axvline(int_median, color='orange', linestyle='--', linewidth=2.5,
              label=f'Median = {int_median:.1f} ADC')
    
    # ±1σ lines
    ax.axvline(int_mean - int_std, color='green', linestyle=':', linewidth=2,
              label=f'±1σ = {int_std:.1f} ADC')
    ax.axvline(int_mean + int_std, color='green', linestyle=':', linewidth=2)
    
    # Shaded ±1σ region
    ax.axvspan(int_mean - int_std, int_mean + int_std,
              alpha=0.2, color='green', label='±1σ region')
    
    # Add zero line (physical reference)
    #ax.axvline(0, color='black', linestyle='-', linewidth=1.5, alpha=0.5,
    #          label='Zero (ideal)')
    
    # Labels and formatting
    ax.set_xlabel('Intercept (ADC)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Channels', fontsize=13, fontweight='bold')
    ax.set_title(f'Intercept Distribution (Good Fits) - {method_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
    
    # Statistics box
    stats_text = (
        f"Statistics:\n"
        f"{'─'*25}\n"
        f"N channels: {len(intercepts)}\n"
        f"Mean:   {int_mean:.2f} ADC\n"
        f"Median: {int_median:.2f} ADC\n"
        f"Std Dev: {int_std:.2f} ADC\n"
        f"Min:    {intercepts.min():.2f} ADC\n"
        f"Max:    {intercepts.max():.2f} ADC\n"
        f"{'─'*25}\n"
     #   f"Mean offset from 0: {abs(int_mean):.2f} ADC"
    )
    
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes,
           fontsize=10, family='monospace', verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.9, pad=0.8))
    
    # =========================================================================
    # SAVE FIGURE
    # =========================================================================
    plt.tight_layout()
    
    save_path = os.path.join(output_dir, 
                            f'gain_intercept_distributions_good_{method_name.lower().replace(" ", "_")}.png')
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    logging.info(f"Saved good fits gain/intercept distributions: {save_path}")

    # =========================================================================
    # BAD FITS PLOT
    # =========================================================================
    if len(bad_fits) == 0:
        logging.warning(f"No bad fits found for {method_name} - skipping bad fits distribution plots")
    else:
        # Extract gain and intercept values for bad fits
        bad_gains = np.array([r['gain'] for r in bad_fits if r['gain'] > 0])
        bad_intercepts = np.array([r['intercept'] for r in bad_fits])
        
        if len(bad_gains) == 0:
            logging.warning(f"No valid gain values for bad fits in {method_name} - skipping bad fits distribution plots")
        else:
            # Create figure with 2 subplots
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # =========================================================================
    # LEFT PLOT: GAIN DISTRIBUTION (BAD FITS)
    # =========================================================================
    ax = axes[0]
    
    # Calculate statistics
    gain_mean = np.mean(bad_gains)
    gain_median = np.median(bad_gains)
    gain_std = np.std(bad_gains)
    
    # NO DYNAMIC RANGE - use full data range
    hist_range = (bad_gains.min(), bad_gains.max())
    
    # Histogram
    n, bins, patches = ax.hist(bad_gains, bins=60, range=hist_range, 
                                color='indianred', alpha=0.7, edgecolor='black',
                                label=f'Bad fits (n={len(bad_gains)})')
    
    # Add vertical lines for mean, median, ±1σ
    y_max = ax.get_ylim()[1]
    
    ax.axvline(gain_mean, color='darkred', linestyle='--', linewidth=2.5, 
                label=f'Mean = {gain_mean:.1f} ADC/PE')
    ax.axvline(gain_median, color='orange', linestyle='--', linewidth=2.5,
                label=f'Median = {gain_median:.1f} ADC/PE')
    
    # ±1σ lines
    ax.axvline(gain_mean - gain_std, color='green', linestyle=':', linewidth=2,
                label=f'±1σ = {gain_std:.1f} ADC/PE')
    ax.axvline(gain_mean + gain_std, color='green', linestyle=':', linewidth=2)
    
    # Shaded ±1σ region
    # ax.axvspan(gain_mean - gain_std, gain_mean + gain_std, 
    #          alpha=0.2, color='green', label='±1σ region')
    
    # Labels and formatting
    ax.set_xlabel('Gain (ADC/PE)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Channels', fontsize=13, fontweight='bold')
    ax.set_title(f'Gain Distribution (Bad Fits) - {method_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
    
    # Statistics box
    stats_text = (
        f"Statistics:\n"
        f"{'─'*25}\n"
        f"N channels: {len(bad_gains)}\n"
        f"Mean:   {gain_mean:.2f} ADC/PE\n"
        f"Median: {gain_median:.2f} ADC/PE\n"
        f"Std Dev: {gain_std:.2f} ADC/PE\n"
        f"Min:    {bad_gains.min():.2f} ADC/PE\n"
        f"Max:    {bad_gains.max():.2f} ADC/PE\n"
        f"{'─'*25}\n"
        f"Rel. Std Dev: {100*gain_std/gain_mean:.2f}%"
    )
    
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes,
            fontsize=10, family='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, pad=0.8))
    
    # =========================================================================
    # RIGHT PLOT: INTERCEPT DISTRIBUTION (BAD FITS)
    # =========================================================================
    ax = axes[1]
    
    # Calculate statistics
    int_mean = np.mean(bad_intercepts)
    int_median = np.median(bad_intercepts)
    int_std = np.std(bad_intercepts)
    
    # NO DYNAMIC RANGE - use full data range
    hist_range = (bad_intercepts.min(), bad_intercepts.max())
    
    # Histogram
    n, bins, patches = ax.hist(bad_intercepts, bins=60, range=hist_range,
                                color='lightsalmon', alpha=0.7, edgecolor='black',
                                label=f'Bad fits (n={len(bad_intercepts)})')
    
    # Add vertical lines
    y_max = ax.get_ylim()[1]
    
    ax.axvline(int_mean, color='darkred', linestyle='--', linewidth=2.5,
                label=f'Mean = {int_mean:.1f} ADC')
    ax.axvline(int_median, color='orange', linestyle='--', linewidth=2.5,
                label=f'Median = {int_median:.1f} ADC')
    
    # ±1σ lines
    ax.axvline(int_mean - int_std, color='green', linestyle=':', linewidth=2,
                label=f'±1σ = {int_std:.1f} ADC')
    ax.axvline(int_mean + int_std, color='green', linestyle=':', linewidth=2)
    
    # Shaded ±1σ region
    #ax.axvspan(int_mean - int_std, int_mean + int_std,
    #          alpha=0.2, color='green', label='±1σ region')
    
    # Add zero line (physical reference)
    #ax.axvline(0, color='black', linestyle='-', linewidth=1.5, alpha=0.5,
    #          label='Zero (ideal)')
    
    # Labels and formatting
    ax.set_xlabel('Intercept (ADC)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Channels', fontsize=13, fontweight='bold')
    ax.set_title(f'Intercept Distribution (Bad Fits) - {method_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
    
    # Statistics box
    stats_text = (
        f"Statistics:\n"
        f"{'─'*25}\n"
        f"N channels: {len(bad_intercepts)}\n"
        f"Mean:   {int_mean:.2f} ADC\n"
        f"Median: {int_median:.2f} ADC\n"
        f"Std Dev: {int_std:.2f} ADC\n"
        f"Min:    {bad_intercepts.min():.2f} ADC\n"
        f"Max:    {bad_intercepts.max():.2f} ADC\n"
        f"{'─'*25}\n"
    #   f"Mean offset from 0: {abs(int_mean):.2f} ADC"
    )
    
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes,
            fontsize=10, family='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.9, pad=0.8))
    
    # =========================================================================
    # SAVE BAD FITS FIGURE
    # =========================================================================
    plt.tight_layout()
    
    save_path = os.path.join(output_dir, 
                            f'gain_intercept_distributions_bad_{method_name.lower().replace(" ", "_")}.png')
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    logging.info(f"Saved bad fits gain/intercept distributions: {save_path}")

def create_fit_quality_piechart(results, method_name, output_dir):
    """
    Create a pie chart showing the distribution of good, bad, and failed fits
    """
    # Classify results
    good_fits = [r for r in results if r['fit_status'] == 1 and 
             (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN) and
             (EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX)]  
    
    bad_fits = [r for r in results if r['fit_status'] == 1 and 
            (r['chi2_dof'] > CHI2_MAX or r['linear_r2'] < LINEAR_R2_MIN or
             r['gain'] < EXPECTED_GAIN_MIN or r['gain'] > EXPECTED_GAIN_MAX)]
    
    failed_fits = [r for r in results if r['fit_status'] != 1]
    
    n_good = len(good_fits)
    n_bad = len(bad_fits)
    n_failed = len(failed_fits)
    n_total = len(results)
    
    pct_good = 100 * n_good / n_total if n_total > 0 else 0
    pct_bad = 100 * n_bad / n_total if n_total > 0 else 0
    pct_failed = 100 * n_failed / n_total if n_total > 0 else 0
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Data for pie chart
    sizes = [n_good, n_bad, n_failed]
    labels = [
        f'Good Fits\n{n_good} ({pct_good:.1f}%)',
        f'Bad Fits\n{n_bad} ({pct_bad:.1f}%)',
        f'Failed Fits\n{n_failed} ({pct_failed:.1f}%)'
    ]
    colors = ['#90EE90', '#FFA07A', '#FFB6C6']  # Fixed: Added # prefix
    explode = (0.05, 0.05, 0.05)  # Slightly separate all slices
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                                        autopct='', startangle=90, textprops=dict(fontsize=13, fontweight='bold'))
    
    # Enhance text
    for text in texts:
        text.set_fontsize(14)
        text.set_fontweight('bold')
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.axis('equal')
    
    # Title
    plt.title(f'Fit Quality Distribution - {method_name}\nTotal Channels: {n_total}',
             fontsize=16, fontweight='bold', pad=20)
    
    # Add legend with detailed statistics
    legend_labels = [
        f'Good Fits: {n_good} channels ({pct_good:.1f}%)',
        f'Bad Fits: {n_bad} channels ({pct_bad:.1f}%)',
        f'Failed Fits: {n_failed} channels ({pct_failed:.1f}%)'
    ]
    ax.legend(legend_labels, loc='upper left', bbox_to_anchor=(0.85, 0.95),
             fontsize=11, framealpha=0.95)
    
    plt.tight_layout()
    
    # Save figure
    save_path = os.path.join(output_dir, 
                             f'fit_quality_piechart_{method_name.lower().replace(" ", "_")}.png')
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    logging.info(f"Saved fit quality pie chart: {save_path}")

def create_statistics_summary(results, method_name, output_dir, run_name):
    """Create two separate summary PNGs: one for Metrics, one for Peak Statistics"""
    
    title_fontsize = 20
    text_fontsize = 14
    
    # =========================================================================
    # HELPER FUNCTIONS
    # =========================================================================
    def get_statistics(results):
        """Calculate statistics for good, bad, and failed fits"""
        good = [r for r in results if r['fit_status'] == 1 and 
             (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN) and
             (EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX)]  
        
        bad = [r for r in results if r['fit_status'] == 1 and 
            (r['chi2_dof'] > CHI2_MAX or r['linear_r2'] < LINEAR_R2_MIN or
             r['gain'] < EXPECTED_GAIN_MIN or r['gain'] > EXPECTED_GAIN_MAX)]
        
        failed = [r for r in results if r['fit_status'] != 1]
        
        # Count channels by number of detected peaks (before fitting)
        n_only_1pe_all = sum(1 for r in results if r['n_peaks'] == 1)
        n_only_2pe_all = sum(1 for r in results if r['n_peaks'] == 2)
        n_more_than_3pe_all = sum(1 for r in results if r['n_peaks'] > 2)
        
        def calc_stats(fit_list):
            if not fit_list:
                return {
                    'n_channels': 0,
                    'mean_gain': 0.0,
                    'median_gain': 0.0,
                    'mean_gain_error': 0.0,
                    'mean_charge_res': 0.0,
                    'n_only_1pe': 0,
                    'n_only_2pe': 0,
                    'n_more_than_3pe': 0,
                }
            
            gains = [r['gain'] for r in fit_list if r['gain'] > 0]
            gain_errors = [r['gain_error'] for r in fit_list if r['gain'] > 0]
            
            charge_res_list = []
            for r in fit_list:
                if 'fit_params' in r and r['gain'] > 0 and len(r['fit_params']) > 2:
                    sigma_1pe = r['fit_params'][2]
                    charge_res = sigma_1pe / r['gain']
                    if 0 < charge_res < 2:
                        charge_res_list.append(charge_res)
            
            # Count channels by number of detected peaks
            n_only_1pe = sum(1 for r in fit_list if r['n_peaks'] == 1)
            n_only_2pe = sum(1 for r in fit_list if r['n_peaks'] == 2)
            n_more_than_3pe = sum(1 for r in fit_list if r['n_peaks'] > 2)
            
            return {
                'n_channels': len(fit_list),
                'mean_gain': np.mean(gains) if gains else 0.0,
                'median_gain': np.median(gains) if gains else 0.0,
                'mean_gain_error': np.mean(gain_errors) if gain_errors else 0.0,
                'mean_charge_res': np.mean(charge_res_list) if charge_res_list else 0.0,
                'n_only_1pe': n_only_1pe,
                'n_only_2pe': n_only_2pe,
                'n_more_than_3pe': n_more_than_3pe,
            }
        
        stats_good = calc_stats(good)
        stats_bad = calc_stats(bad)
        stats_failed = calc_stats(failed)
        
        # Add total stats
        stats_total = {
            'n_channels': len(results),
            'mean_gain': 0.0,
            'median_gain': 0.0,
            'mean_gain_error': 0.0,
            'mean_charge_res': 0.0,
            'n_only_1pe': n_only_1pe_all,
            'n_only_2pe': n_only_2pe_all,
            'n_more_than_3pe': n_more_than_3pe_all,
        }
        
        return stats_good, stats_bad, stats_failed, stats_total

    def get_peak_statistics(results):
        """Extract mu and sigma values for peaks 2, 3, 4"""
        # Store arrays for mean calculations
        mu2_all, sigma2_all = [], []
        mu3_all, sigma3_all = [], []
        mu4_all, sigma4_all = [], []
        
        # Store specific channel values
        specific_channels = {}
        channels_to_track = [1000, 2500, 4000, 5500, 7000]
        
        for r in results:
            if r['fit_status'] == 1 and 'fit_params' in r:
                n_peaks = r['n_peaks']
                
                # Peak 2 (index 0 in fit_params since we skip first detected peak)
                if n_peaks >= 1 and len(r['fit_params']) > 2:
                    mu2_all.append(r['fit_params'][1])
                    sigma2_all.append(r['fit_params'][2])
                    if r['channel_id'] in channels_to_track:
                        if r['channel_id'] not in specific_channels:
                            specific_channels[r['channel_id']] = {}
                        specific_channels[r['channel_id']]['mu2'] = r['fit_params'][1]
                        specific_channels[r['channel_id']]['sigma2'] = r['fit_params'][2]
                
                # Peak 3
                if n_peaks >= 2 and len(r['fit_params']) > 5:
                    mu3_all.append(r['fit_params'][4])
                    sigma3_all.append(r['fit_params'][5])
                    if r['channel_id'] in channels_to_track:
                        if r['channel_id'] not in specific_channels:
                            specific_channels[r['channel_id']] = {}
                        specific_channels[r['channel_id']]['mu3'] = r['fit_params'][4]
                        specific_channels[r['channel_id']]['sigma3'] = r['fit_params'][5]
                
                # Peak 4
                if n_peaks >= 3 and len(r['fit_params']) > 8:
                    mu4_all.append(r['fit_params'][7])
                    sigma4_all.append(r['fit_params'][8])
                    if r['channel_id'] in channels_to_track:
                        if r['channel_id'] not in specific_channels:
                            specific_channels[r['channel_id']] = {}
                        specific_channels[r['channel_id']]['mu4'] = r['fit_params'][7]
                        specific_channels[r['channel_id']]['sigma4'] = r['fit_params'][8]
        
        return {
            'mean_mu2': np.mean(mu2_all) if mu2_all else 0.0,
            'mean_sigma2': np.mean(sigma2_all) if sigma2_all else 0.0,
            'mean_mu3': np.mean(mu3_all) if mu3_all else 0.0,
            'mean_sigma3': np.mean(sigma3_all) if sigma3_all else 0.0,
            'mean_mu4': np.mean(mu4_all) if mu4_all else 0.0,
            'mean_sigma4': np.mean(sigma4_all) if sigma4_all else 0.0,
            'specific_channels': specific_channels,
        }

    # =========================================================================
    # IMAGE 1: RUN STATISTICS (METRICS)
    # =========================================================================

    stats_good, stats_bad, stats_failed, stats_total = get_statistics(results)

    fig1 = plt.figure(figsize=(20, 8))
    ax1 = fig1.add_subplot(111)
    ax1.axis('off')

    pct_good = 100 * stats_good['n_channels'] / len(results)
    pct_bad = 100 * stats_bad['n_channels'] / len(results)
    pct_failed = 100 * stats_failed['n_channels'] / len(results)
    pct_total = 100 * stats_total['n_channels'] / len(results)

    text1 = f"RUN STATISTICS: {run_name} - {method_name}\n"
    text1 += "=" * 150 + "\n\n"

    text1 += f"{'Metric':<40} {'Good Fits':<30} {'Bad Fits':<30} {'Failed fits':<30} {'TOTAL':<30}\n"
    text1 += "-" * 150 + "\n"
    text1 += f"{'Number of Channels':<40} {stats_good['n_channels']:<10} ({pct_good:>6.1f}%) {stats_bad['n_channels']:<10} ({pct_bad:>6.1f}%) {stats_failed['n_channels']:<10} ({pct_failed:>6.1f}%) {stats_total['n_channels']:<10} ({pct_total:>6.1f}%)\n"

    # Peak detection statistics (using TOTAL column values)
    pct_1pe_good = 100 * stats_good['n_only_1pe'] / stats_good['n_channels'] if stats_good['n_channels'] > 0 else 0
    pct_1pe_bad = 100 * stats_bad['n_only_1pe'] / stats_bad['n_channels'] if stats_bad['n_channels'] > 0 else 0
    pct_1pe_failed = 100 * stats_failed['n_only_1pe'] / stats_failed['n_channels'] if stats_failed['n_channels'] > 0 else 0
    pct_1pe_total = 100 * stats_total['n_only_1pe'] / stats_total['n_channels'] if stats_total['n_channels'] > 0 else 0

    pct_2pe_good = 100 * stats_good['n_only_2pe'] / stats_good['n_channels'] if stats_good['n_channels'] > 0 else 0
    pct_2pe_bad = 100 * stats_bad['n_only_2pe'] / stats_bad['n_channels'] if stats_bad['n_channels'] > 0 else 0
    pct_2pe_failed = 100 * stats_failed['n_only_2pe'] / stats_failed['n_channels'] if stats_failed['n_channels'] > 0 else 0
    pct_2pe_total = 100 * stats_total['n_only_2pe'] / stats_total['n_channels'] if stats_total['n_channels'] > 0 else 0

    pct_3pe_good = 100 * stats_good['n_more_than_3pe'] / stats_good['n_channels'] if stats_good['n_channels'] > 0 else 0
    pct_3pe_bad = 100 * stats_bad['n_more_than_3pe'] / stats_bad['n_channels'] if stats_bad['n_channels'] > 0 else 0
    pct_3pe_failed = 100 * stats_failed['n_more_than_3pe'] / stats_failed['n_channels'] if stats_failed['n_channels'] > 0 else 0
    pct_3pe_total = 100 * stats_total['n_more_than_3pe'] / stats_total['n_channels'] if stats_total['n_channels'] > 0 else 0

    text1 += f"{'Channels with only 1 PE':<40} {stats_good['n_only_1pe']:<10} ({pct_1pe_good:>6.1f}%) {stats_bad['n_only_1pe']:<10} ({pct_1pe_bad:>6.1f}%) {stats_failed['n_only_1pe']:<10} ({pct_1pe_failed:>6.1f}%) {stats_total['n_only_1pe']:<10} ({pct_1pe_total:>6.1f}%)\n"
    text1 += f"{'Channels with only 2 PE':<40} {stats_good['n_only_2pe']:<10} ({pct_2pe_good:>6.1f}%) {stats_bad['n_only_2pe']:<10} ({pct_2pe_bad:>6.1f}%) {stats_failed['n_only_2pe']:<10} ({pct_2pe_failed:>6.1f}%) {stats_total['n_only_2pe']:<10} ({pct_2pe_total:>6.1f}%)\n"
    text1 += f"{'Channels with > 2 PE':<40} {stats_good['n_more_than_3pe']:<10} ({pct_3pe_good:>6.1f}%) {stats_bad['n_more_than_3pe']:<10} ({pct_3pe_bad:>6.1f}%) {stats_failed['n_more_than_3pe']:<10} ({pct_3pe_failed:>6.1f}%) {stats_total['n_more_than_3pe']:<10} ({pct_3pe_total:>6.1f}%)\n"
    text1 += "-" * 150 + "\n"

    text1 += f"{'Mean Gain (ADC/PE)':<40} {stats_good['mean_gain']:<30.2f} {stats_bad['mean_gain']:<30.2f} {stats_failed['mean_gain']:<30.2f} {'N/A':<30}\n"
    text1 += f"{'Median Gain (ADC/PE)':<40} {stats_good['median_gain']:<30.2f} {stats_bad['median_gain']:<30.2f} {stats_failed['median_gain']:<30.2f} {'N/A':<30}\n"
    text1 += f"{'Mean Gain Error (ADC/PE)':<40} {stats_good['mean_gain_error']:<30.2f} {stats_bad['mean_gain_error']:<30.2f} {stats_failed['mean_gain_error']:<30.2f} {'N/A':<30}\n"

    # Calculate relative gain error percentage
    rel_err_good = 100 * stats_good['mean_gain_error'] / stats_good['mean_gain'] if stats_good['mean_gain'] > 0 else 0
    rel_err_bad = 100 * stats_bad['mean_gain_error'] / stats_bad['mean_gain'] if stats_bad['mean_gain'] > 0 else 0
    rel_err_failed = 100 * stats_failed['mean_gain_error'] / stats_failed['mean_gain'] if stats_failed['mean_gain'] > 0 else 0

    text1 += f"{'Mean Relative Gain Error (%)':<40} {rel_err_good:<30.2f} {rel_err_bad:<30.2f} {rel_err_failed:<30.2f} {'N/A':<30}\n"
    text1 += f"{'Mean Charge Resolution (σ₁/g)':<40} {stats_good['mean_charge_res']:<30.3f} {stats_bad['mean_charge_res']:<30.3f} {stats_failed['mean_charge_res']:<30.3f} {'N/A':<30}\n"
    
    ax1.text(0.02, 0.98, text1, transform=ax1.transAxes,
            fontsize=text_fontsize, family='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5, pad=1))

    plt.tight_layout()
    save_path1 = os.path.join(output_dir, f'statistics_metrics_{method_name.lower().replace(" ", "_")}_{run_name}.png')
    fig1.savefig(save_path1, dpi=150, bbox_inches='tight')
    plt.close(fig1)
    logging.info(f"Saved metrics summary: {save_path1}")

    # =========================================================================
    # IMAGE 2: PEAK MU AND SIGMA STATISTICS
    # =========================================================================
    
    peak_stats = get_peak_statistics(results)
    
    fig2 = plt.figure(figsize=(18, 7))  # Changed from 10 to 7
    ax2 = fig2.add_subplot(111)
    ax2.axis('off')
    
    text2 = f"PEAK STATISTICS (μ and σ): {run_name} - {method_name}\n"
    text2 += "=" * 90 + "\n\n"
    
    # Mean values
    text2 += "MEAN VALUES (ALL FITTED CHANNELS):\n"
    text2 += "-" * 90 + "\n"
    text2 += f"{'Peak':<15} {'Mean μ (ADC)':<25} {'Mean σ (ADC)':<25}\n"
    text2 += "-" * 90 + "\n"
    
    # Adjust peak labels based on USE_FIRST_PEAK
    if USE_FIRST_PEAK:
        text2 += f"{'1st Peak (1 PE)':<15} {peak_stats['mean_mu2']:<25.2f} {peak_stats['mean_sigma2']:<25.2f}\n"
        text2 += f"{'2nd Peak (2 PE)':<15} {peak_stats['mean_mu3']:<25.2f} {peak_stats['mean_sigma3']:<25.2f}\n"
        text2 += f"{'3rd Peak (3 PE)':<15} {peak_stats['mean_mu4']:<25.2f} {peak_stats['mean_sigma4']:<25.2f}\n"
    else:
        text2 += f"{'2nd Peak (2 PE)':<15} {peak_stats['mean_mu2']:<25.2f} {peak_stats['mean_sigma2']:<25.2f}\n"
        text2 += f"{'3rd Peak (3 PE)':<15} {peak_stats['mean_mu3']:<25.2f} {peak_stats['mean_sigma3']:<25.2f}\n"
        text2 += f"{'4th Peak (4 PE)':<15} {peak_stats['mean_mu4']:<25.2f} {peak_stats['mean_sigma4']:<25.2f}\n"
    text2 += "\n"
    
    # Specific channels
    text2 += "SPECIFIC CHANNEL VALUES:\n"
    text2 += "-" * 90 + "\n"
    text2 += f"{'Channel':<12} {'Peak':<20} {'μ (ADC)':<20} {'σ (ADC)':<20}\n"
    text2 += "-" * 90 + "\n"
    
    def format_value(val):
        return f"{val:.2f}" if val is not None else "N/A"
    
    def get_peak_label(key):
        if USE_FIRST_PEAK:
            labels = {'mu2': '1st (1 PE)', 'mu3': '2nd (2 PE)', 'mu4': '3rd (3 PE)'}
        else:
            labels = {'mu2': '2nd (2 PE)', 'mu3': '3rd (3 PE)', 'mu4': '4th (4 PE)'}
        return labels.get(key, key)
    
    for ch_id in sorted(peak_stats['specific_channels'].keys()):
        ch_data = peak_stats['specific_channels'][ch_id]
        if 'mu2' in ch_data:
            text2 += f"{ch_id:<12} {get_peak_label('mu2'):<20} {format_value(ch_data['mu2']):<20} {format_value(ch_data['sigma2']):<20}\n"
        if 'mu3' in ch_data:
            text2 += f"{ch_id:<12} {get_peak_label('mu3'):<20} {format_value(ch_data['mu3']):<20} {format_value(ch_data['sigma3']):<20}\n"
        if 'mu4' in ch_data:
            text2 += f"{ch_id:<12} {get_peak_label('mu4'):<20} {format_value(ch_data['mu4']):<20} {format_value(ch_data['sigma4']):<20}\n"
    
    ax2.text(0.02, 0.98, text2, transform=ax2.transAxes,
             fontsize=text_fontsize, family='monospace', verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5, pad=1))

    plt.tight_layout()
    save_path2 = os.path.join(output_dir, f'statistics_sigmas_{method_name.lower().replace(" ", "_")}_{run_name}.png')
    fig2.savefig(save_path2, dpi=150, bbox_inches='tight')
    plt.close(fig2)
    logging.info(f"Saved sigma summary: {save_path2}")

def main():
    parser = argparse.ArgumentParser(description='Dual workflow gain calibration')
    parser.add_argument('input_root', help='Input ROOT file with ADC histograms')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('run_name', help='Run name')
    parser.add_argument('--use-raw', action='store_true',
                       help='Use raw (non-vetoed) histograms instead of clean (default: clean)')
    parser.add_argument('--workflow', choices=['scipy', 'root', 'both'], default='root',
                       help='Choose workflow: scipy, root (default), or both')
    parser.add_argument('--plots', choices=['none', 'sample', 'all'], default='all',
                       help='Save channel fit plots: none, sample (up to 100 per category), all (default). '
                            'PNGs are organised into good/, bad/, failed/ subfolders.')
    
    args = parser.parse_args()
    
    # Check ROOT availability if needed
    if args.workflow in ['root', 'both'] and ROOT is None:
        logging.error("ROOT not available but required for selected workflow")
        sys.exit(1)
    
    if not os.path.exists(args.input_root):
        logging.error(f"Input file not found: {args.input_root}")
        sys.exit(1)
    
    os.makedirs(args.output_dir, exist_ok=True)
    plot_dir = os.path.join(args.output_dir, f"plots_{args.run_name}")
    os.makedirs(plot_dir, exist_ok=True)
    for _sub in ['good', 'bad', 'failed']:
        os.makedirs(os.path.join(plot_dir, _sub), exist_ok=True)
    
    logging.info(f"Loading histograms from {args.input_root}...")
    logging.info(f"Selected workflow: {args.workflow}")
    
    # ========================================================================
    # Dynamic channel discovery to handle out-of-range channels
    # ========================================================================

    f = ROOT.TFile.Open(args.input_root, "READ")
    
    # Get all histogram names from the file
    keys = f.GetListOfKeys()
    channel_ids = []

    # Decide which histogram type to use based on args.use_raw
    prefix_to_find = "H_adcraw_" if args.use_raw else "H_adcClean_"

    for key in keys:
        name = key.GetName()
        # Only look for the histogram type we want to use
        if name.startswith(prefix_to_find):
            try:
                # Extract channel ID by removing the prefix
                ch_id = int(name.replace(prefix_to_find, ""))
                channel_ids.append(ch_id)
            except ValueError:
                continue

    channel_ids.sort()  # Sort for consistent processing

    if not channel_ids:
        logging.error("No ADC histograms found in input file!")
        f.Close()
        sys.exit(1)

    logging.info(f"Found {len(channel_ids)} channels in input file")

    # Count standard vs out-of-range channels
    standard_channels = [ch for ch in channel_ids if 0 <= ch < 8048]
    oor_channels = [ch for ch in channel_ids if ch < 0 or ch >= 8048]

    logging.info(f"  Standard channels (0-8047): {len(standard_channels)}")
    if oor_channels:
        logging.info(f"  Out-of-range channels: {len(oor_channels)}")
        logging.info(f"    Range: [{min(oor_channels)}, {max(oor_channels)}]")

    # Load all histograms (both standard and out-of-range)
    channel_data = []
    for ch in channel_ids:
        if args.use_raw:
            hist_name = f"H_adcraw_{ch}" 
        else:
            hist_name = f"H_adcClean_{ch}" 
        
        h = f.Get(hist_name)
        if h:
            hist_array = np.zeros(len(BIN_CENTERS))
            for i, bc in enumerate(BIN_CENTERS):
                bin_orig = h.FindBin(bc)
                if 1 <= bin_orig <= h.GetNbinsX():
                    hist_array[i] = h.GetBinContent(bin_orig)
            channel_data.append((ch, hist_array, args.workflow))
        else:
            # Histogram exists in keys but can't be loaded
            logging.warning(f"Could not load histogram for channel {ch}")
            channel_data.append((ch, np.zeros(len(BIN_CENTERS)), args.workflow))

    
    f.Close()
    # ========================================================================
    
    logging.info(f"Processing {len(channel_data)} channels with {args.workflow} workflow...")
    
    # First pass: initial fits
    n_workers = min(8, cpu_count() - 1)
    
    # Prepare arguments without refine_params for first pass
    first_pass_args = [(ch, hist, args.workflow, None) for ch, hist, _ in channel_data]
    
    with Pool(n_workers) as pool:
        dual_results = list(tqdm(pool.imap(process_channel, first_pass_args), 
                                total=len(channel_data), desc="First pass fitting"))
    
    # Second pass: refine fits if enabled
    if REFINE_FIT:
        logging.info("Performing refinement pass with initial fit results...")
        
        # Prepare refine parameters from first pass
        refine_args = []
        for i, (ch, hist, _) in enumerate(channel_data):
            result_root, result_scipy = dual_results[i]
            
            # Prepare refine params based on workflow
            if args.workflow == 'root' and result_root is not None:
                refine_params = None
                if result_root['fit_status'] == 1:
                    refine_params = {
                        'fit_params': result_root.get('fit_params', []),
                        'intercept': result_root.get('intercept', 0),
                        'gain': result_root.get('gain', 0)
                    }
                refine_args.append((ch, hist, args.workflow, refine_params))
                
            elif args.workflow == 'scipy' and result_scipy is not None:
                refine_params = None
                if result_scipy['fit_status'] == 1:
                    refine_params = {
                        'fit_params': result_scipy.get('fit_params', []),
                        'intercept': result_scipy.get('intercept', 0),
                        'gain': result_scipy.get('gain', 0)
                    }
                refine_args.append((ch, hist, args.workflow, refine_params))
                
            else:  # both
                refine_params_root = None
                if result_root is not None and result_root['fit_status'] == 1:
                    refine_params_root = {
                        'fit_params': result_root.get('fit_params', []),
                        'intercept': result_root.get('intercept', 0),
                        'gain': result_root.get('gain', 0)
                    }
                    
                refine_params_scipy = None
                if result_scipy is not None and result_scipy['fit_status'] == 1:
                    refine_params_scipy = {
                        'fit_params': result_scipy.get('fit_params', []),
                        'intercept': result_scipy.get('intercept', 0),
                        'gain': result_scipy.get('gain', 0)
                    }
                
                # For 'both' workflow, we need separate refinement
                # For simplicity, use the first successful result
                refine_params = refine_params_root if refine_params_root else refine_params_scipy
                refine_args.append((ch, hist, args.workflow, refine_params))
        
        with Pool(n_workers) as pool:
            dual_results = list(tqdm(pool.imap(process_channel, refine_args), 
                                    total=len(channel_data), desc="Refinement pass"))

    # Separate results based on workflow
    results_root = [r[0] for r in dual_results if r[0] is not None]
    results_scipy = [r[1] for r in dual_results if r[1] is not None]
    
    # Classify and process results for each workflow
    def process_workflow_results(results, method_name):
        if not results:
            return [], [], []
        good = [r for r in results if r['fit_status'] == 1 and 
             (r['chi2_dof'] <= CHI2_MAX and r['linear_r2'] >= LINEAR_R2_MIN) and
             (EXPECTED_GAIN_MIN <= r['gain'] <= EXPECTED_GAIN_MAX)]  
        
        bad = [r for r in results if r['fit_status'] == 1 and 
            (r['chi2_dof'] > CHI2_MAX or r['linear_r2'] < LINEAR_R2_MIN or
             r['gain'] < EXPECTED_GAIN_MIN or r['gain'] > EXPECTED_GAIN_MAX)]
        
        failed_fit = [r for r in results if r['fit_status'] != 1]
        
        logging.info(f"\n{'='*60}")
        logging.info(f"{method_name} Results:")
        logging.info(f"  Good fits: {len(good)}")
        logging.info(f"  Bad fits: {len(bad)}")
        logging.info(f"  Failed fits: {len(failed_fit)}")
        logging.info(f"{'='*60}\n")
        
        # Save CSV files
        def save_csv(result_list, filename):
            df = pd.DataFrame([{
                'channel_id': r['channel_id'],
                'gain': r['gain'],
                'gain_error': r['gain_error'],
                'intercept': r['intercept'],
                'intercept_error': r['intercept_error'],
                'n_peaks': r['n_peaks'],
                'chi2_dof': r['chi2_dof'],
                'linear_r2': r['linear_r2'],
                'linear_chi2_dof': r['linear_chi2_dof']
            } for r in result_list])
            
            csv_path = os.path.join(args.output_dir, filename)
            df.to_csv(csv_path, index=False)
            logging.info(f"Saved {filename}: {len(result_list)} channels")
            
            # Save formatted TXT
            txt_filename = filename.replace('.csv', '.txt')
            txt_path = os.path.join(args.output_dir, txt_filename)
            with open(txt_path, 'w') as f:
                f.write(f"{'Channel':<10} {'Gain':<12} {'Gain_Err':<12} {'Intercept':<14} "
                       f"{'Int_Err':<12} {'N_Peaks':<10} {'Chi2/dof':<12} {'R2':<8} "
                       f"{'Lin_Chi2':<12} {'Mu1_PE':<12} {'Sigma1_PE':<12} "
                       f"{'Mu2_PE':<12} {'Sigma2_PE':<12}\n")
                f.write("=" * 142 + "\n")
                for r in result_list:
                    fp = r.get('fit_params', [])
                    mu1    = fp[1]  if len(fp) > 2 else 0.0
                    sig1   = fp[2]  if len(fp) > 2 else 0.0
                    mu2    = fp[4]  if len(fp) > 5 else 0.0
                    sig2   = fp[5]  if len(fp) > 5 else 0.0
                    f.write(f"{r['channel_id']:<10} {r['gain']:<12.2f} {r['gain_error']:<12.2f} "
                           f"{r['intercept']:<14.2f} {r['intercept_error']:<12.2f} "
                           f"{r['n_peaks']:<10} {r['chi2_dof']:<12.3f} "
                           f"{r['linear_r2']:<8.4f} {r['linear_chi2_dof']:<12.3f} "
                           f"{mu1:<12.2f} {sig1:<12.2f} {mu2:<12.2f} {sig2:<12.2f}\n")
            logging.info(f"Saved {txt_filename}")
        
        prefix = method_name.lower().replace(' ', '_')
        save_csv(good, f'{prefix}_good_{args.run_name}.csv')
        save_csv(bad, f'{prefix}_bad_{args.run_name}.csv')
        save_csv(failed_fit, f'{prefix}_failed_{args.run_name}.csv')
        
        # Create summary plots
        logging.info(f"\nCreating summary plots for {method_name}...")
        create_summary_plots(results, method_name, args.output_dir)

        # CREATE GAIN/INTERCEPT DISTRIBUTIONS
        logging.info(f"\nCreating gain/intercept distribution plots for {method_name}...")
        create_gain_intercept_distributions(results, method_name, args.output_dir)
        
        # CREATE FIT QUALITY PIE CHART
        logging.info(f"\nCreating fit quality pie chart for {method_name}...")
        create_fit_quality_piechart(results, method_name, args.output_dir)

        # Create statistics summary (PNG output disabled)
        # logging.info(f"\nCreating statistics summary for {method_name}...")
        # create_statistics_summary(results, method_name, args.output_dir, args.run_name)
        
        # Return classified results for plotting
        return good, bad, failed_fit
    
    # Process results and collect for consistent plotting
    workflow_data = {}
    
    if args.workflow == 'scipy' or args.workflow == 'both':
        good_scipy, bad_scipy, failed_scipy = process_workflow_results(results_scipy, 'SciPy Workflow')
        workflow_data['scipy'] = {'good': good_scipy, 'bad': bad_scipy, 'failed': failed_scipy}
    
    if args.workflow == 'root' or args.workflow == 'both':
        good_root, bad_root, failed_root = process_workflow_results(results_root, 'ROOT TSpectrum')
        workflow_data['root'] = {'good': good_root, 'bad': bad_root, 'failed': failed_root}
    
    # Generate channel fit plots according to --plots flag
    if args.plots == 'none':
        logging.info("\nSkipping channel fit plots (use --plots sample or --plots all to enable).")
    else:
        logging.info(f"\nGenerating channel fit plots (mode: {args.plots})...")

        if args.workflow == 'both':
            # Find common channel IDs for consistent plotting
            scipy_good_ids = set(r['channel_id'] for r in workflow_data['scipy']['good'])
            root_good_ids = set(r['channel_id'] for r in workflow_data['root']['good'])
            common_good_ids = list(scipy_good_ids & root_good_ids)
            
            scipy_bad_ids = set(r['channel_id'] for r in workflow_data['scipy']['bad'])
            root_bad_ids = set(r['channel_id'] for r in workflow_data['root']['bad'])
            common_bad_ids = list(scipy_bad_ids & root_bad_ids)
            
            scipy_failed_ids = set(r['channel_id'] for r in workflow_data['scipy']['failed'])
            root_failed_ids = set(r['channel_id'] for r in workflow_data['root']['failed'])
            common_failed_ids = list(scipy_failed_ids & root_failed_ids)
            
            if args.plots == 'sample':
                selected_good_ids   = random.sample(common_good_ids,   min(100, len(common_good_ids)))   if common_good_ids   else []
                selected_bad_ids    = random.sample(common_bad_ids,    min(100, len(common_bad_ids)))    if common_bad_ids    else []
                selected_failed_ids = random.sample(common_failed_ids, min(100, len(common_failed_ids))) if common_failed_ids else []
            else:  # all
                selected_good_ids   = common_good_ids
                selected_bad_ids    = common_bad_ids
                selected_failed_ids = common_failed_ids
            
            # Plot both workflows for same channels
            for ch_id in tqdm(selected_good_ids, desc="Plotting good fits"):
                r_scipy = next(r for r in workflow_data['scipy']['good'] if r['channel_id'] == ch_id)
                r_root  = next(r for r in workflow_data['root']['good']  if r['channel_id'] == ch_id)
                plot_channel_fit(r_scipy, plot_dir, 'scipy_good')
                plot_channel_fit(r_root,  plot_dir, 'root_tspectrum_good')
            
            for ch_id in tqdm(selected_bad_ids, desc="Plotting bad fits"):
                r_scipy = next(r for r in workflow_data['scipy']['bad'] if r['channel_id'] == ch_id)
                r_root  = next(r for r in workflow_data['root']['bad']  if r['channel_id'] == ch_id)
                plot_channel_fit(r_scipy, plot_dir, 'scipy_bad')
                plot_channel_fit(r_root,  plot_dir, 'root_tspectrum_bad')
            
            for ch_id in tqdm(selected_failed_ids, desc="Plotting failed fits"):
                r_scipy = next(r for r in workflow_data['scipy']['failed'] if r['channel_id'] == ch_id)
                r_root  = next(r for r in workflow_data['root']['failed']  if r['channel_id'] == ch_id)
                plot_channel_fit(r_scipy, plot_dir, 'scipy_failed')
                plot_channel_fit(r_root,  plot_dir, 'root_tspectrum_failed')
        
        else:
            # Single workflow
            workflow_name = 'scipy' if args.workflow == 'scipy' else 'root'
            prefix        = 'scipy' if args.workflow == 'scipy' else 'root_tspectrum'
            
            good   = workflow_data[workflow_name]['good']
            bad    = workflow_data[workflow_name]['bad']
            failed = workflow_data[workflow_name]['failed']
            
            if args.plots == 'sample':
                selected_good   = random.sample(good,   min(100, len(good)))   if good   else []
                selected_bad    = random.sample(bad,    min(100, len(bad)))    if bad    else []
                selected_failed = random.sample(failed, min(100, len(failed))) if failed else []
            else:  # all
                selected_good, selected_bad, selected_failed = good, bad, failed
            
            for r in tqdm(selected_good,   desc="Plotting good fits"):
                plot_channel_fit(r, plot_dir, f'{prefix}_good')
            for r in tqdm(selected_bad,    desc="Plotting bad fits"):
                plot_channel_fit(r, plot_dir, f'{prefix}_bad')
            for r in tqdm(selected_failed, desc="Plotting failed fits"):
                plot_channel_fit(r, plot_dir, f'{prefix}_failed')
    
    logging.info(f"\nDone! Results saved to {args.output_dir}")
    logging.info(f"Plots saved to {plot_dir}")

if __name__ == "__main__":
    main()