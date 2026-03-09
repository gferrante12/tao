#!/usr/bin/env python3

"""
get_spectrum.py - Generate energy spectra from RTRAW/ESD with Gaussian fits

Generates Continuous PE, Discrete PE, and nHit spectra with Gaussian fits
Computes veto cuts on-the-fly: muon threshold, after-muon, after-pulse, TDC

FEATURES:
- Supports both RTRAW and ESD files
- Merged mode: saves individual + merged ROOT files
- Veto cuts with TDC statistics tracking
- Dark noise calculation from DCR calibration
- Discrete PE method: ROUNDING ONLY (threshold method removed)
- RTRAW dark-noise subtraction: DN_TOT = Σ_ch DCR_ch × W  (W = 250 × 10⁻⁹ s)
  summed over all good channels from the calibration file, then subtracted
  once per event from the total PE sum (not channel-by-channel).
- Resolution calculation: σ/(μ-DN_TOT)
- Full error budget: statistical (fit covariance) ⊕ systematic (fit-model
  variation study with 3 range widths × 3 background polynomials = 9 fits).
  Stored in energy_info as *_ERR (total), *_ERR_STAT, *_ERR_SYS.
- Radial cut for ESD files (origin-based or off-axis source position)
- Off-axis radial cut: r computed relative to a user-specified source position
  instead of the detector origin (use --source-pos X Y Z in mm).
  For Cs-137 on CLS the source sits at (-23.1093, -188.278, 37.3801) mm.
"""

import sys
import os
import glob
import argparse
import numpy as np

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

def file_exists_or_accessible(file_path):
    """
    Check if file exists (works for both local paths and XRootD URLs)
    For XRootD URLs, we skip the check and let ROOT handle it
    """
    if file_path.startswith("root://"):
        # For XRootD URLs, skip existence check - ROOT will handle it
        return True
    else:
        # Local file - check normally
        return os.path.exists(file_path)

# =====================================================
# Constants
# =====================================================

TDC_CUT_LOW = 240.0   # ns  — aligned with CALIB2 window in extract_charge_calib.py
TDC_CUT_UP  = 440.0   # ns  — aligned with CALIB2 window in extract_charge_calib.py
TDC_WINDOW_ANALYSIS = TDC_CUT_UP - TDC_CUT_LOW  # 200 ns

MUON_THRESHOLD = 4e8          # Total ADC threshold for muon events
AFTER_MUON_WINDOW = 200e3     # Time window (ns) after muon: 200 μs
AFTER_PULSE_WINDOW = 2.5e3    # Time window (ns) after any event: 2.5 μs

DEFAULT_RADIAL_CUT = 150.0   # mm - Default radial cut for ESD files

# Source position for Cs-137 CLS calibration source (mm), corresponding to n=60.
# Used for the off-axis radial cut (--source-pos / offaxis mode in launch script).
CLS_CS137_SOURCE_POS = (-23.1093, -188.278, 37.3801)  # (X, Y, Z) in mm

# Base directory for calibration txt files
_CALIB_RESULTS_BASE_CNAF = "/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/calibration_results"
_CALIB_RESULTS_BASE_IHEP = "/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/calibration_results"

# Run-range calibration txt files (extracted from official cvmfs ROOT files)
#   sipm_calib_1157-1193.txt  <- from TAO_SiPM_calib_par_1768003200.root
#   sipm_calib_1295-.txt      <- from TAO_SiPM_calib_par_1770336000.root
_CALIB_FILE_1157_1193 = "sipm_calib_1157-1193.txt"
_CALIB_FILE_1295_PLUS = "sipm_calib_1295-.txt"


def _detect_calib_base():
    if os.path.isdir(_CALIB_RESULTS_BASE_IHEP):
        return _CALIB_RESULTS_BASE_IHEP
    elif os.path.isdir(_CALIB_RESULTS_BASE_CNAF):
        return _CALIB_RESULTS_BASE_CNAF
    return _CALIB_RESULTS_BASE_IHEP


def get_default_calib_file(run_number=None):
    """Return (path, warning_or_None) for the correct calibration txt file.

    Run ranges:
        run <= 1193  ->  sipm_calib_1157-1193.txt  (TAO_SiPM_calib_par_1768003200.root)
        run >= 1295  ->  sipm_calib_1295-.txt       (TAO_SiPM_calib_par_1770336000.root)
        1194-1294    ->  WARNING + use 1295- file as best guess
        None         ->  WARNING + fall back to legacy file
    """
    base = _detect_calib_base()

    if run_number is None:
        warn = ("--run not provided: cannot select run-specific calibration file. "
                f"Falling back to legacy {repr(_CALIB_FILE_1295_PLUS)}. "
                "Pass --run <RUN> to use the correct file.")
        return os.path.join(base, _CALIB_FILE_1295_PLUS), warn

    if run_number <= 1193:
        warn = None
        if run_number < 1157:
            warn = (f"WARNING: Run {run_number} is below the officially calibrated range "
                    f"(1157-1193). Using {repr(_CALIB_FILE_1157_1193)} as the closest "
                    f"available default gain calibration — verify this is appropriate "
                    f"for your run.")
        return os.path.join(base, _CALIB_FILE_1157_1193), warn

    if run_number >= 1295:
        warn = None
        if run_number < 1295:  # never true, but explicit for future gaps
            pass
        return os.path.join(base, _CALIB_FILE_1295_PLUS), None

    # Gap: 1194-1294
    warn = (f"Run {run_number} is in the gap range 1194-1294 with no dedicated "
            f"calibration file. Using {repr(_CALIB_FILE_1295_PLUS)} as best guess. "
            "Verify this is appropriate for your run.")
    return os.path.join(base, _CALIB_FILE_1295_PLUS), warn


# Legacy constant kept for backwards compatibility
DEFAULT_CALIB_FILE = os.path.join(_detect_calib_base(), _CALIB_FILE_1295_PLUS)

# =============================================================================
# RUN-RANGE CONFIGURATION
# Maps run number ranges to the correct official files on cvmfs.
#
# SiPM parameters:
#   RUN 1295+  : TAO_SiPM_calib_par_1770336000.root
#   RUN 1157-1193: TAO_SiPM_calib_par_1768003200.root
# Rec parameters (CCRec non-uniformity + curve params, RUN 1157-1193 only):
#   curve_params_StaticBaseline_T25.6.4_260114.csv
#   Energy_nonUniformityMap_StaticBaseline_T25.6.4_260114.txt
# Bad channel lists:
#   RUN 1295+  : badch_T25.7.1_fixed.txt / badch_T25.7.1_dyn.txt
#   RUN 1157-1193: ALLBad_channels_20260112_1053_st.txt / ..._1039_dy.txt
# =============================================================================

_CVMFS_SIPM   = "/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Calibration/Calib.CD.SiPM.Param"
_CVMFS_BADCH  = "/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Reconstruction/Badchannellist"
_CVMFS_REC    = "/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Reconstruction/CCRec"
_TAOSW_J271   = "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/Reconstruction/RecChargeCenterAlg/script"

def get_run_config(run_number):
    """Return run-range-appropriate cvmfs paths for a given run number.

    Returns a dict with keys:
        sipm_calib_root   - official SiPM calibration ROOT file
        bad_channel_st    - bad channel list (static/fixed baseline)
        bad_channel_dyn   - bad channel list (dynamic baseline)
        curve_params      - CCRec curve params CSV (None if not applicable)
        nonuniformity_map - CCRec non-uniformity map TXT (None if not applicable)
        run_range_label   - human-readable range string
    """
    if run_number >= 1295:
        return {
            'sipm_calib_root':   f"{_CVMFS_SIPM}/TAO_SiPM_calib_par_1770336000.root",
            'bad_channel_st':    f"{_CVMFS_BADCH}/badch_T25.7.1_fixed.txt",
            'bad_channel_dyn':   f"{_CVMFS_BADCH}/badch_T25.7.1_dyn.txt",
            'curve_params':      None,
            'nonuniformity_map': None,
            'run_range_label':   '1295+',
        }
    elif run_number <= 1193:
        # Covers the official 1157-1193 range AND earlier runs (< 1157).
        # Runs before 1157 use the same calibration files as the closest known
        # range; a warning is printed so the user can verify this is appropriate.
        if run_number < 1157:
            printf(f"WARNING: Run {run_number} is below the officially calibrated range "
                   f"(1157-1193). Using 1157-1193 cvmfs paths "
                   f"(TAO_SiPM_calib_par_1768003200.root, T25.6.4 bad-channel lists) "
                   f"as the closest available configuration.")
        return {
            'sipm_calib_root':   f"{_CVMFS_SIPM}/TAO_SiPM_calib_par_1768003200.root",
            'bad_channel_st':    f"{_TAOSW_J271}/ALLBad_channels_20260112_1053_st.txt",
            'bad_channel_dyn':   f"{_TAOSW_J271}/ALLBad_channels_20260112_1039_dy.txt",
            'curve_params':      f"{_CVMFS_REC}/curve_params_StaticBaseline_T25.6.4_260114.csv",
            'nonuniformity_map': f"{_CVMFS_REC}/Energy_nonUniformityMap_StaticBaseline_T25.6.4_260114.txt",
            'run_range_label':   ('1157-1193' if run_number >= 1157
                                  else f'{run_number} (<1157, using 1157-1193 config)'),
        }
    else:
        # Gap: 1194-1294 — no dedicated calibration, use 1295+ as best guess.
        printf(f"WARNING: Run {run_number} is in the gap range 1194-1294 with no dedicated "
               f"calibration. Defaulting to 1295+ paths as best guess.")
        return {
            'sipm_calib_root':   f"{_CVMFS_SIPM}/TAO_SiPM_calib_par_1770336000.root",
            'bad_channel_st':    f"{_CVMFS_BADCH}/badch_T25.7.1_fixed.txt",
            'bad_channel_dyn':   f"{_CVMFS_BADCH}/badch_T25.7.1_dyn.txt",
            'curve_params':      None,
            'nonuniformity_map': None,
            'run_range_label':   f'{run_number} (gap 1194-1294, defaulting to 1295+ config)',
        }


def printf(msg, end='\n', flush=False):
    """Helper print function"""
    print(msg, end=end, flush=flush)


def count_channels(bad_channel_file, baseline_type="Unknown"):
    """Count good and bad channels for a given baseline type"""
    printf("=" * 60)
    printf(f"BASELINE TYPE: {baseline_type.upper()}")
    printf("=" * 60)
    
    try:
        with open(bad_channel_file, 'r') as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        n_bad = len(lines)
        n_total = 8048  # Main detector channels
        n_good = n_total - n_bad
        
        printf(f"Bad channel file: {os.path.basename(bad_channel_file)}")
        printf(f"Total detector channels: {n_total}")
        printf(f"Bad channels:            {n_bad:4d} ({100.0*n_bad/n_total:5.2f}%)")
        printf(f"Good channels:           {n_good:4d} ({100.0*n_good/n_total:5.2f}%)")
        printf("")
        return n_good, n_bad
    except FileNotFoundError:
        printf(f"ERROR: Bad channel file not found!")
        printf(f"Path: {bad_channel_file}")
        printf("")
        return 8048, 0


def print_channel_statistics(run_config):
    """Print bad channel statistics for a given run's config dict.
    Called at runtime (inside get_spectrum) once the run number is known.
    """
    bad_ch_st  = run_config['bad_channel_st']
    bad_ch_dyn = run_config['bad_channel_dyn']
    label      = run_config['run_range_label']

    printf("")
    printf("#" * 60)
    printf(f"## CHANNEL STATISTICS  (run range: {label})")
    printf("#" * 60)
    printf("")

    n_good_st,  n_bad_st  = count_channels(bad_ch_st,  baseline_type="STATIC")
    n_good_dyn, n_bad_dyn = count_channels(bad_ch_dyn, baseline_type="DYNAMIC")

    printf("=" * 60)
    printf("COMPARISON: STATIC vs DYNAMIC BASELINE")
    printf("=" * 60)
    printf(f"{'Metric':<30} {'Static':>12} {'Dynamic':>12}")
    printf("-" * 60)
    printf(f"{'Bad channels':<30} {n_bad_st:>12d} {n_bad_dyn:>12d}")
    printf(f"{'Good channels':<30} {n_good_st:>12d} {n_good_dyn:>12d}")
    printf(f"{'Difference (Static - Dynamic)':<30} {n_bad_st - n_bad_dyn:>12d}")
    printf("")

    if n_bad_st > n_bad_dyn:
        printf(f"→ Static baseline has {n_bad_st - n_bad_dyn} MORE bad channels than dynamic")
    elif n_bad_dyn > n_bad_st:
        printf(f"→ Dynamic baseline has {n_bad_dyn - n_bad_st} MORE bad channels than static")
    else:
        printf(f"→ Both baseline types have the same number of bad channels")
    printf("")
    return n_good_st, n_bad_st, n_good_dyn, n_bad_dyn


# =============================================================================
# LOAD CALIBRATION FROM TXT FILE
# =============================================================================

def load_calibration(calib_file):
    """Load channel calibration from text file (supports both old and new formats)
    
    Returns:
        calibration: dict - channel calibration data
        dark_noise_pe: float - calculated dark noise in PE
        has_dcr: bool - whether DCR data was loaded from this file
    """
    calibration = {}

    if not file_exists_or_accessible(calib_file):
        printf(f"ERROR: Cannot open calibration file: {calib_file}")
        return calibration, 0.0, False

    printf(f"Loading calibration from: {calib_file}")

    with open(calib_file, 'r') as fin:
        lines = fin.readlines()

    # Detect format by checking header
    is_new_format = False
    header_line = 0
    for i, line in enumerate(lines):
        if line.startswith('#'):
            if 'dcr' in line.lower():
                is_new_format = True
                header_line = i + 1
        elif line.strip() and not line.startswith('#'):
            break

    printf(f"  Format: {'NEW (with DCR)' if is_new_format else 'OLD (TSpectrum)'}")

    loaded = 0
    total_dcr = 0.0  # Sum of DCR values (Hz)
    dcr_count = 0

    if is_new_format:
        # New format: channel_id gain mean0 gain_dyn mean0_dyn timeoffset baseline dcr
        for line in lines[header_line:]:
            parts = line.strip().split()
            if len(parts) < 8:
                continue

            try:
                ch_id = int(parts[0])
                gain = float(parts[1])
                intercept = float(parts[2])  # mean0
                dcr = float(parts[7])

                # Skip bad channels (huge gain value)
                if gain > 1e6:
                    continue

                calibration[ch_id] = {
                    'gain': gain,
                    'intercept': intercept,
                    'dcr': dcr
                }
                loaded += 1

                # Sum DCR (skip channels with DCR = 0)
                if dcr > 0.0:
                    total_dcr += dcr
                    dcr_count += 1

            except (ValueError, IndexError):
                continue
    else:
        # Old format: Channel Gain Gain_Err Intercept Int_Err ... (no DCR)
        for line in lines[header_line:]:
            parts = line.strip().split()
            if len(parts) < 4:
                continue

            try:
                ch_id = int(parts[0])
                gain = float(parts[1])
                intercept = float(parts[3])  # Column 4 is Intercept

                calibration[ch_id] = {
                    'gain': gain,
                    'intercept': intercept,
                    'dcr': 0.0  # No DCR in old format - will be loaded separately
                }
                loaded += 1

            except (ValueError, IndexError):
                continue

    printf(f"  Loaded {loaded} good channels")

    # Calculate mean gain
    if loaded > 0:
        mean_gain = np.mean([cal['gain'] for cal in calibration.values()])
        printf(f"  Mean gain: {mean_gain:.2f} ADC/PE")

    # Calculate Dark Noise
    dark_noise_pe = 0.0
    if is_new_format and total_dcr > 0:
        # DN = sum(DCR) * (TDC_window) * 1e-9
        tdc_window_ns = TDC_CUT_UP - TDC_CUT_LOW
        dark_noise_pe = total_dcr * tdc_window_ns * 1e-9
        printf(f"\n  DARK NOISE CALCULATION:")
        printf(f"    Total DCR (sum of {dcr_count} channels): {total_dcr:.2f} Hz")
        printf(f"    TDC window: {tdc_window_ns:.1f} ns")
        printf(f"    Dark Noise (DN): {dark_noise_pe:.3f} PE")
    else:
        printf(f"\n  Dark Noise: Not in this file (will load from default calibration)")

    return calibration, dark_noise_pe, is_new_format


def load_dcr_from_default(calibration, default_calib_file=DEFAULT_CALIB_FILE):
    """Load DCR data from default calibration file and merge with existing calibration
    
    Args:
        calibration: dict - existing calibration with gain/intercept but no DCR
        default_calib_file: str - path to default calibration file with DCR
        
    Returns:
        dark_noise_pe: float - calculated dark noise in PE
    """
    if not file_exists_or_accessible(default_calib_file):
        printf(f"\n  WARNING: Default calibration file not found: {default_calib_file}")
        printf(f"  Dark Noise: Not available")
        return 0.0
    
    printf(f"\nLoading DCR from default calibration: {default_calib_file}")
    
    with open(default_calib_file, 'r') as fin:
        lines = fin.readlines()
    
    # Skip header
    header_line = 0
    for i, line in enumerate(lines):
        if line.startswith('#'):
            header_line = i + 1
        elif line.strip() and not line.startswith('#'):
            break
    
    total_dcr = 0.0
    dcr_count = 0
    dcr_merged = 0
    
    # Load DCR values: channel_id gain mean0 gain_dyn mean0_dyn timeoffset baseline dcr
    for line in lines[header_line:]:
        parts = line.strip().split()
        if len(parts) < 8:
            continue
        
        try:
            ch_id = int(parts[0])
            dcr = float(parts[7])
            
            # If this channel exists in our calibration, add DCR to it
            if ch_id in calibration:
                calibration[ch_id]['dcr'] = dcr
                if dcr > 0.0:
                    total_dcr += dcr
                    dcr_count += 1
                    dcr_merged += 1
                    
        except (ValueError, IndexError):
            continue
    
    printf(f"  Merged DCR for {dcr_merged} channels (from {len(calibration)} total)")
    
    # Calculate Dark Noise
    dark_noise_pe = 0.0
    if total_dcr > 0:
        tdc_window_ns = TDC_CUT_UP - TDC_CUT_LOW
        dark_noise_pe = total_dcr * tdc_window_ns * 1e-9
        printf(f"\n  DARK NOISE CALCULATION:")
        printf(f"    Total DCR (sum of {dcr_count} channels): {total_dcr:.2f} Hz")
        printf(f"    TDC window: {tdc_window_ns:.1f} ns")
        printf(f"    Dark Noise (DN): {dark_noise_pe:.3f} PE")
    else:
        printf(f"\n  WARNING: No valid DCR data found")
        printf(f"  Dark Noise: Not available")
    
    return dark_noise_pe


# =============================================================================
# LOAD PER-CHANNEL CROSSTALK PROBABILITIES (from gain_calibration EMG output)
# =============================================================================

def load_crosstalk(pct_file):
    """
    Load per-channel optical crosstalk probabilities from a gain_calibration
    CSV/TXT output file (produced with --fit-model emg).

    Expects a file with at least columns: channel_id, p_ct
    (the CSV columns produced by gain_calibration.py with EMG model).

    Returns dict {ch_id: p_ct_value}.  Falls back to 0.0 for missing channels.
    """
    if not pct_file or not file_exists_or_accessible(pct_file):
        return {}

    printf(f"Loading per-channel P_ct from: {pct_file}")
    pct = {}

    with open(pct_file) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    if not lines:
        return {}

    # Auto-detect CSV vs space-separated; find 'channel_id' and 'p_ct' columns
    header = lines[0].replace(',', ' ').split()
    if 'channel_id' in header and 'p_ct' in header:
        ci_idx  = header.index('channel_id')
        pct_idx = header.index('p_ct')
        for line in lines[1:]:
            parts = line.replace(',', ' ').split()
            try:
                ch_id = int(parts[ci_idx])
                p_ct  = float(parts[pct_idx])
                if 0.0 <= p_ct < 1.0:          # sanity guard
                    pct[ch_id] = p_ct
            except (ValueError, IndexError):
                continue
    else:
        printf("  WARNING: Could not find 'channel_id'/'p_ct' columns – crosstalk not loaded")
        return {}

    if pct:
        vals = list(pct.values())
        printf(f"  Loaded P_ct for {len(pct)} channels "
               f"(mean={float(sum(vals)/len(vals)):.3f}, "
               f"min={min(vals):.3f}, max={max(vals):.3f})")
    return pct


def load_rpde(rpde_file):
    """
    Load per-channel relative PDE from a text/CSV file.

    Expected columns: channel_id  rPDE
    rPDE is normalised so the mean across good channels = 1.0.
    Values significantly below 1.0 (e.g. 0.5) indicate hardware-degraded SiPMs
    that see only a fraction of the photons hitting their surface.

    Physical meaning and correction:
    ---------------------------------
    After gain calibration, ch_pe_raw = (ADC - intercept) / gain.
    This gives the number of FIRED cells, not the number of incident photons.
    The SiPM detection efficiency (PDE) converts photon flux → fired cells:
        PE_true = PE_raw / rPDE
    Without the correction, a channel with rPDE = 0.5 contributes half the
    true PE to the event sum, artificially degrading energy resolution.

    Source: "Calibration of Channel-level Parameters at TAO" (Wuhan group,
    Jan 2026, file:29 of 2026-01_Calibration..._at_TAO.pdf).
    Std of rPDE across channels ≈ 6 %; outlier channels reach rPDE ≈ 0.5.

    Returns dict {ch_id: rPDE_value}.
    Missing channels default to 1.0 (identity — no bias on good channels).
    """
    if not rpde_file or not file_exists_or_accessible(rpde_file):
        return {}

    printf(f"Loading per-channel relative PDE from: {rpde_file}")
    rpde = {}

    with open(rpde_file) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    if not lines:
        return {}

    header = lines[0].replace(',', ' ').split()
    if 'channel_id' in header and 'rPDE' in header:
        ci  = header.index('channel_id')
        ri  = header.index('rPDE')
        for line in lines[1:]:
            parts = line.replace(',', ' ').split()
            try:
                ch_id = int(parts[ci])
                val   = float(parts[ri])
                if val > 0.0:   # guard: never divide by zero or negative
                    rpde[ch_id] = val
            except (ValueError, IndexError):
                continue
    else:
        printf("  WARNING: Could not find 'channel_id'/'rPDE' columns – rPDE not loaded")
        return {}

    if rpde:
        vals = list(rpde.values())
        printf(f"  Loaded rPDE for {len(rpde)} channels "
               f"(mean={float(sum(vals)/len(vals)):.4f}, "
               f"std={float(np.std(vals)):.4f}, "
               f"min={min(vals):.4f}, max={max(vals):.4f})")
    return rpde


# =============================================================================
# FIT GAUSSIAN + BACKGROUND WITH DN-CORRECTED RESOLUTION
# Provided by spectrum_utils.py (shared with merge_spectrum.py)
# =============================================================================

try:
    from spectrum_utils import resolve_source, SOURCES, fit_source
except ImportError as _e:
    print(f"ERROR: Cannot import spectrum_utils: {_e}")
    print("       Make sure spectrum_utils.py is in the same directory as get_spectrum.py")
    import sys as _sys; _sys.exit(1)


# =============================================================================
# PROCESS SINGLE RTRAW FILE
# =============================================================================

def process_single_rtraw(rtraw_file, calibration, dark_noise_pe, max_pe_per_channel=-1, pct_map=None, rpde_map=None):
    """Process a single RTRAW file and return histograms + statistics"""
    printf(f"\n  Processing: {os.path.basename(rtraw_file)}")

    fin = ROOT.TFile.Open(rtraw_file, "READ")
    if not fin or fin.IsZombie():
        printf(f"    ERROR: Cannot open file, skipping...")
        return None

    # Get electronics event tree
    elec_tree = fin.Get("Event/Elec/CdElecEvt")
    if not elec_tree or not elec_tree.InheritsFrom("TTree"):
        printf(f"    ERROR: Cannot find CdElecEvt tree, skipping...")
        fin.Close()
        return None

    # Get trigger tree
    trig_tree = fin.Get("Event/Trig/CdTrigEvt")
    if not trig_tree or not trig_tree.InheritsFrom("TTree"):
        printf(f"    ERROR: Cannot find CdTrigEvt tree, skipping...")
        fin.Close()
        return None

    n_events = elec_tree.GetEntries()
    printf(f"    Events: {n_events}")

    # Create histograms for this file
    h_PEcontin = ROOT.TH1F("h_PEcontin_temp", "Continuous PE Spectrum", 500, 0, 25000)
    h_PEcontin.SetDirectory(0)
    h_PEdiscrete = ROOT.TH1F("h_PEdiscrete_temp", "Discrete PE Spectrum (rounding)", 500, 0, 25000)
    h_PEdiscrete.SetDirectory(0)
    h_nHit = ROOT.TH1F("h_nHit_temp", "nHit Spectrum", 500, 0, 8048)
    h_nHit.SetDirectory(0)

    # Statistics counters
    stats = {
        'events_processed': 0,
        'events_vetoed_muon': 0,
        'events_vetoed_aftermuon': 0,
        'events_vetoed_afterpulse': 0,
        'events_clean': 0,
        'events_tdc_affected': 0,
        'channels_tdc_rejected': 0
    }

    # Veto tracking
    last_muon_time = 0
    last_event_time = 0

    for i in range(n_events):
        elec_tree.GetEntry(i)
        trig_tree.GetEntry(i)

        stats['events_processed'] += 1
        if stats['events_processed'] % 5000 == 0:
            progress = 100.0 * stats['events_processed'] / n_events
            printf(f"\r    Progress: {stats['events_processed']}/{n_events} ({progress:.1f}%)", end='', flush=True)

        # Get event objects
        elec_evt = elec_tree.CdElecEvt
        trig_evt = trig_tree.CdTrigEvt

        # Get channels
        channels = elec_evt.GetElecChannels()
        nch = len(channels)
        if nch == 0:
            continue

        # Get trigger time
        trig_time = trig_evt.getTrigTime()
        current_time = trig_time.GetSec() * 1e9 + trig_time.GetNanoSec()

        # Calculate total ADC for muon check
        total_adc = 0.0
        for ch in channels:
            adcs = ch.getADCs()
            if len(adcs) > 0:
                total_adc += adcs[0]

        # VETO: Muon event
        is_muon = (total_adc > MUON_THRESHOLD)
        if is_muon:
            stats['events_vetoed_muon'] += 1
            last_muon_time = current_time
            last_event_time = current_time
            continue

        # VETO: After-muon window
        if last_muon_time > 0 and (current_time - last_muon_time) < AFTER_MUON_WINDOW:
            stats['events_vetoed_aftermuon'] += 1
            last_event_time = current_time
            continue

        # VETO: After-pulse window
        if last_event_time > 0 and (current_time - last_event_time) < AFTER_PULSE_WINDOW:
            stats['events_vetoed_afterpulse'] += 1
            last_event_time = current_time
            continue

        # Update last event time
        last_event_time = current_time

        # EVENT PASSED VETO - Process channels
        total_pe_cont = 0.0
        total_pe_discrete = 0.0
        nhit = 0
        tdc_rejected_this_event = 0

        for ch in channels:
            chid = ch.getChannelID()
            if chid not in calibration:
                continue

            adcs = ch.getADCs()
            tdcs = ch.getTDCs()
            if len(adcs) == 0 or len(tdcs) == 0:
                continue

            chadc = adcs[0]
            chtdc = tdcs[0]

            # Apply TDC cut
            if chtdc < TDC_CUT_LOW or chtdc > TDC_CUT_UP:
                tdc_rejected_this_event += 1
                stats['channels_tdc_rejected'] += 1
                continue

            nhit += 1
            gain      = calibration[chid]['gain']
            intercept = calibration[chid]['intercept']

            # Raw calibrated PE for this channel (no per-channel DN here)
            ch_pe_raw = (chadc - intercept) / gain

            # Optional max-PE-per-channel cut (applied on raw value)
            if max_pe_per_channel > 0 and ch_pe_raw > max_pe_per_channel:
                continue

            # ----------------------------------------------------------------
            # Optical-crosstalk correction (SiPM physics).
            # The EMG fit gives P_ct = tau/gain ≈ fraction of ADC from CT.
            # The mean measured PE is inflated by the factor (1 + P_ct), so we
            # divide to recover the true photon count.
            # Effect: ~5-20% correction per channel, applied before rounding.
            # If no pct_map is provided, correction is identity (p_ct = 0).
            # ----------------------------------------------------------------
            if pct_map:
                p_ct = pct_map.get(chid, 0.0)
                if p_ct > 0.0:
                    ch_pe_raw /= (1.0 + p_ct)

            # ----------------------------------------------------------------
            # Relative-PDE correction.
            # rPDE is normalised so mean = 1.0 across good channels.
            # Channels with rPDE < 1 see fewer photons (degraded SiPM surface):
            #   PE_true = PE_raw / rPDE
            # Without this, a channel with rPDE = 0.5 contributes half the true
            # photon count, degrading energy resolution artificially.
            # Source: Wuhan group, TAO channel-level calibration (Jan 2026).
            # Missing channels default to rPDE = 1.0 (no correction).
            # ----------------------------------------------------------------
            if rpde_map:
                r_pde = rpde_map.get(chid, 1.0)
                if r_pde > 0.0:
                    ch_pe_raw /= r_pde

            # ----------------------------------------------------------------
            # Accumulate PE sums.
            # Continuous: plain float sum.
            # Discrete: round per channel first (matching CCRec order).
            # DN_TOT is subtracted once at event level below.
            # ----------------------------------------------------------------
            total_pe_cont     += ch_pe_raw
            total_pe_discrete += float(int(np.round(ch_pe_raw)))

        # ----------------------------------------------------------------
        # Subtract average detector dark noise (DN_TOT) once per event.
        # DN_TOT = Σ_ch DCR_ch × W,  W = 250 × 10⁻⁹ s
        # (computed in load_calibration / load_dcr_from_default and passed in
        #  as dark_noise_pe).  This matches the definition used in fit resolution:
        #  R = σ / (μ − DN_TOT).
        # ----------------------------------------------------------------
        pe_cont_corr     = total_pe_cont     - dark_noise_pe
        pe_discrete_corr = total_pe_discrete - dark_noise_pe

        if pe_cont_corr > 0:
            h_PEcontin.Fill(pe_cont_corr)
            stats['events_clean'] += 1

        if pe_discrete_corr > 0:
            h_PEdiscrete.Fill(pe_discrete_corr)
        
        h_nHit.Fill(nhit)

        # Track TDC-affected events
        if tdc_rejected_this_event > 0:
            stats['events_tdc_affected'] += 1

    printf(f"\r    Completed: {stats['events_processed']} events")

    fin.Close()

    return {
        'histograms': {
            'PEcontin': h_PEcontin,
            'PEdiscrete': h_PEdiscrete,
            'nHit': h_nHit
        },
        'stats': stats
    }


# =============================================================================
# PROCESS SINGLE ESD FILE
# =============================================================================

def process_single_esd(esd_file, dark_noise_pe, radial_cut=DEFAULT_RADIAL_CUT, pe_type='pesum_g',
                        source_pos=None):
    """
    Process a single ESD file and return histograms + statistics

    Args:
        esd_file:    path to the ESD file
        dark_noise_pe: dark noise in PE (from calibration)
        radial_cut:  radial cut radius in mm (0 = disabled)
        pe_type:     'pesum_g' (geometry corrected, default) or 'pesum_basic'
        source_pos:  None  → origin-based radial cut r = sqrt(x²+y²+z²)
                     (sx, sy, sz) tuple → off-axis cut
                       r = sqrt((x-sx)²+(y-sy)²+(z-sz)²)
                     Typical value for Cs-137 CLS: CLS_CS137_SOURCE_POS
    """
    printf(f">> Processing ESD: {os.path.basename(esd_file)}")
    printf(f">> PE Type: {pe_type}")
    if radial_cut > 0:
        if source_pos is not None:
            sx, sy, sz = source_pos
            printf(f">> Radial cut: r < {radial_cut:.0f} mm  [OFF-AXIS: source=({sx:.4f}, {sy:.4f}, {sz:.4f}) mm]")
        else:
            printf(f">> Radial cut: r < {radial_cut:.0f} mm  [origin-based]")
    fin = ROOT.TFile.Open(esd_file, "READ")
    if not fin or fin.IsZombie():
        printf("ERROR: Cannot open file, skipping...")
        return None

    # Get reconstructed event tree
    rec_tree = fin.Get("/Event/Rec/ChargeCenterAlg/CdVertexRecEvt")
    if not rec_tree or not rec_tree.InheritsFrom("TTree"):
        printf("ERROR: Cannot find CdVertexRecEvt tree, skipping...")
        fin.Close()
        return None

    # Get calibrated event tree for nHit
    calib_tree = fin.Get("Event/Calib/CdCalibEvt")
    has_calib = calib_tree and calib_tree.InheritsFrom("TTree")

    n_events = rec_tree.GetEntries()
    printf(f">> Events: {n_events}")

    # Create histograms
    h_PEcontin = ROOT.TH1F("h_PEcontin_temp", "Continuous PE Spectrum from ESD", 500, 0, 25000)
    h_PEcontin.SetDirectory(0)
    h_PEdiscrete = ROOT.TH1F("h_PEdiscrete_temp", "Discrete PE Spectrum from ESD (rounding)", 500, 0, 25000)
    h_PEdiscrete.SetDirectory(0)
    h_nHit = ROOT.TH1F("h_nHit_temp", "nHit Spectrum from ESD", 500, 0, 8048)
    h_nHit.SetDirectory(0)

    # Statistics
    stats = {
        'events_processed': 0,
        'events_vetoed_muon': 0,
        'events_vetoed_aftermuon': 0,
        'events_vetoed_afterpulse': 0,
        'events_clean': 0,
        'events_tdc_affected': 0,
        'channels_tdc_rejected': 0,
        'events_radial_cut': 0  # NEW: Track radial cut rejections
    }

    for i in range(n_events):
        rec_tree.GetEntry(i)
        rec_evt = rec_tree.CdVertexRecEvt

        pe_basic = rec_evt.peSum()
        pe_geom = rec_evt.PESum_g()

        # Diagnostic output (first 100 events)
        if i < 100:
            printf(f"Event {i}:")
            printf(f"  peSum():    {pe_basic:.1f} PE (good channels only)")
            printf(f"  PESum_g():  {pe_geom:.1f} PE (good+bad corrected, geom corrected)")
            printf(f"  Ratio:      {pe_geom/pe_basic:.4f}")

        stats['events_processed'] += 1
        if stats['events_processed'] % 5000 == 0:
            progress = 100.0 * stats['events_processed'] / n_events
            printf(f"\r    Progress: {stats['events_processed']}/{n_events} ({progress:.1f}%)", end='', flush=True)

        if not rec_evt:
            continue

        # =====================================================
        # Select PE type
        # =====================================================
        if pe_type == 'pesum_g':
            npe_total = rec_evt.PESum_g()  # Geometry-corrected (default)
            printf(f">> Using PESum_g (geometry corrected)")
        else:  # pesum_basic
            npe_total = rec_evt.peSum()     # Basic correction
            printf(f">> Using peSum (basic correction)")

        # Apply radial cut
        if radial_cut > 0:
            x = rec_evt.x()
            y = rec_evt.y()
            z = rec_evt.z()

            # Off-axis radial cut: compute r relative to source position if provided
            if source_pos is not None:
                sx, sy, sz = source_pos
                r = np.sqrt((x - sx)**2 + (y - sy)**2 + (z - sz)**2)
            else:
                r = np.sqrt(x*x + y*y + z*z)

            # MUON TAGGING: Reconstruction sets position to (2000, 2000, 2000) for muons
            if r > 1900:  # Likely muon-tagged event
                stats['events_vetoed_muon'] += 1
                continue

            # Apply radial cut (if enabled)
            if r > radial_cut:
                stats['events_radial_cut'] += 1
                continue

        # Get nHit from CdCalibEvt
        if has_calib:
            calib_tree.GetEntry(i)
            calib_evt = calib_tree.CdCalibEvt
            if calib_evt:
                nhit = len(calib_evt.GetCalibChannels())
            else:
                nhit = 0
        else:
            nhit = 0

        # Fill histograms
        # ESD: channel-level DN subtraction already done by CCRec (CalibSvc).
        # npe_total from peSum()/PESum_g() is a continuous float.
        # For discrete PE we round at event level (best possible from ESD output).
        if npe_total > 0:
            h_PEcontin.Fill(npe_total)
            h_PEdiscrete.Fill(float(int(np.round(npe_total))))
            stats['events_clean'] += 1

        if nhit > 0:
            h_nHit.Fill(nhit)

    printf(f"\r    Completed: {stats['events_processed']} events")

    fin.Close()

    return {
        'histograms': {
            'PEcontin': h_PEcontin,
            'PEdiscrete': h_PEdiscrete,
            'nHit': h_nHit
        },
        'stats': stats
    }


# =============================================================================
# FIT LOGIC delegated to fit_peaks_ge68.py / fit_peaks_cs137.py via
# spectrum_utils.fit_source().  No fit code in get_spectrum.py.
# =============================================================================


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def get_spectrum(input_file, calib_file, out_file, merged_dir=None, file_type='rtraw',
                   radial_cut=DEFAULT_RADIAL_CUT, max_pe_per_channel=-1, esd_pe_type='pesum_g',
                   run_number=None,
    pct_file=None, rpde_file=None, source_pos=None, source_name=None):
    """
    Extract energy spectra from RTRAW/ESD file(s)

    Args:
        input_file: Path to input file (or None if using merged_dir)
        calib_file: Path to calibration file
        out_file: Output ROOT file path
        merged_dir: Directory containing multiple files (merged mode)
        file_type: 'rtraw' or 'esd'
        radial_cut: Radial cut in mm (ESD only, 0 = disabled)
        max_pe_per_channel: Max PE/channel cut (RTRAW only, -1 = disabled)
        esd_pe_type: 'pesum_g' or 'pesum_basic' (ESD only)
        run_number: Integer run number used to select the correct cvmfs files
                    (bad channel lists, SiPM calib ROOT, rec parameters).
                    If None, a warning is printed and default (1157-1193) paths are used.
        source_pos: None → origin-based radial cut.
                    (sx, sy, sz) tuple in mm → off-axis radial cut, r computed
                    relative to the specified source position. Use CLS_CS137_SOURCE_POS
                    for Cs-137 on the CLS arm:  (-23.1093, -188.278, 37.3801) mm.
    """

    printf("=" * 60)
    printf("GET_SPECTRUM - Energy Spectrum from RTRAW/ESD")
    printf("=" * 60)

    # -------------------------------------------------------------------------
    # Resolve run-range-dependent cvmfs paths
    # -------------------------------------------------------------------------
    if run_number is None:
        printf("WARNING: --run not provided. Cannot select run-specific cvmfs files.")
        printf("         Defaulting to 1157-1193 paths. Pass --run <RUN> to fix this.")
        run_number = 1157  # fall back to oldest known range

    run_config = get_run_config(run_number)
    printf(f"Run config: range={run_config['run_range_label']}")
    printf(f"  SiPM calib ROOT : {run_config['sipm_calib_root']}")
    printf(f"  Bad ch (static) : {run_config['bad_channel_st']}")
    printf(f"  Bad ch (dynamic): {run_config['bad_channel_dyn']}")
    if run_config['curve_params']:
        printf(f"  Curve params    : {run_config['curve_params']}")
        printf(f"  Non-unif. map   : {run_config['nonuniformity_map']}")
    printf("")

    # Print bad channel statistics for this run
    print_channel_statistics(run_config)

    # Validate parameters per file type
    if file_type == "rtraw":
        if radial_cut > 0:
            printf("WARNING: Radial cut not available for RTRAW, ignoring...")
            radial_cut = 0.0
    else:  # ESD
        if max_pe_per_channel > 0:
            printf("WARNING: Max PE/channel cut not applicable to ESD, ignoring...")
            maxpeperchannel = -1

    # Determine mode
    if merged_dir:
        printf(f"MODE: MERGED (all {file_type.upper()} files in directory)")
        printf(f"Input directory: {merged_dir}")

        # Find all files
        if file_type == 'esd':
            file_pattern = os.path.join(merged_dir, "*.esd")
        else:
            file_pattern = os.path.join(merged_dir, "*.rtraw")

        input_files = sorted(glob.glob(file_pattern))
        if not input_files:
            printf(f"ERROR: No {file_type.upper()} files found in {merged_dir}")
            return 1

        printf(f"Found {len(input_files)} {file_type.upper()} files")
        for i, f in enumerate(input_files[:5], 1):
            printf(f"  {i}. {os.path.basename(f)}")
        if len(input_files) > 5:
            printf(f"  ... and {len(input_files) - 5} more")
    else:
        printf(f"MODE: SINGLE FILE ({file_type.upper()})")
        printf(f"Input: {input_file}")
        input_files = [input_file]

    printf(f"Calibration: {calib_file}")
    printf(f"Output: {out_file}")
    printf("")
    printf("Configuration:")

    if file_type == 'rtraw':
        printf(f"  File type:            RTRAW")
        printf(f"  Muon threshold:      {MUON_THRESHOLD:.0e} ADC")
        printf(f"  After-muon window:   {AFTER_MUON_WINDOW/1e3:.1f} μs")
        printf(f"  After-pulse window:  {AFTER_PULSE_WINDOW/1e3:.1f} μs")
        printf(f"  TDC cut:             [{TDC_CUT_LOW}, {TDC_CUT_UP}] ns")
        if args.max_pe_per_channel > 0:
            printf(f"  Max PE/channel:    {args.max_pe_per_channel:.1f}")
        printf(f"  Discrete PE method")
    else:   # ESD
        printf(f"  File type:  ESD") 
        printf(f"  PE type:    {esd_pe_type}")
        if radial_cut > 0:
            if source_pos is not None:
                sx, sy, sz = source_pos
                printf(f"  Radial cut: {radial_cut:.0f} mm  [OFF-AXIS source: ({sx:.4f}, {sy:.4f}, {sz:.4f}) mm]")
            else:
                printf(f"  Radial cut: {radial_cut:.0f} mm  [origin-based]")
        else:
            printf(f"  Radial cut: NONE")
    printf("")

    # Load calibration
    # -------------------------------------------------------------------------
    # For RTRAW: if the caller passed a run-specific custom calib file, use it.
    # If not (i.e. the file came from the default path), silently upgrade to the
    # run-aware file so DCR values match the correct SiPM parameter ROOT file.
    # -------------------------------------------------------------------------
    if file_type == 'rtraw':
        run_aware_calib, calib_warn = get_default_calib_file(run_number)
        if calib_warn:
            printf(f"WARNING (calibration file): {calib_warn}")

        # Use run-aware file when the caller provided the legacy default or nothing
        legacy_path = os.path.join(_detect_calib_base(), _CALIB_FILE_1295_PLUS)
        if calib_file in (legacy_path, DEFAULT_CALIB_FILE, None, "/dev/null"):
            if calib_file != run_aware_calib:
                printf(f"  Upgrading calibration file to run-aware path:")
                printf(f"    was: {calib_file}")
                printf(f"    now: {run_aware_calib}")
            calib_file = run_aware_calib

    calibration, dark_noise_pe, has_dcr = load_calibration(calib_file)

    # Optical crosstalk correction (optional; from EMG gain_calibration output)
    pct_map = load_crosstalk(pct_file) if pct_file else {}
    if pct_map:
        printf(f"\nCrosstalk correction enabled: {len(pct_map)} channels loaded.")
        printf(f"  Mean P_ct = {sum(pct_map.values())/len(pct_map):.3f}")
    else:
        printf("\nCrosstalk correction: disabled (no --pct-file provided).")

    # Relative-PDE correction (optional; from Wuhan group channel-level calibration)
    rpde_map = load_rpde(rpde_file) if rpde_file else {}
    if rpde_map:
        printf(f"\nRelative-PDE correction enabled: {len(rpde_map)} channels loaded.")
        printf(f"  Mean rPDE = {sum(rpde_map.values())/len(rpde_map):.4f}")
    else:
        printf("\nRelative-PDE correction: disabled (no --rpde-file provided).")

    #dark_noise_pe = 0.0
    #printf("  >>> DARK NOISE CORRECTION DISABLED (forced to 0.0 PE) <<<")

    if dark_noise_pe > 0:
        printf(f"  DARK NOISE: {dark_noise_pe:.3f} PE (will be applied in resolution calculation)")
    else:
        printf("  WARNING: No DN data available, resolution will be σ/μ")

    if not calibration and file_type == 'rtraw':
        printf("ERROR: No calibration data loaded (required for RTRAW)!")
        return 1

    # If no DCR in the loaded file, fall back to the run-aware default
    if not has_dcr and file_type == 'rtraw':
        run_aware_calib_dcr, _ = get_default_calib_file(run_number)
        dark_noise_pe = load_dcr_from_default(calibration, run_aware_calib_dcr)

    printf(f"\nProcessing {file_type.upper()} files...")

    # Create output histograms
    h_PEcontin = ROOT.TH1F("h_PEcontin", "Continous PE Spectrum;Continous PE;Counts", 500, 0, 25000)
    h_PEcontin.SetDirectory(0)
    h_PEdiscrete = ROOT.TH1F("h_PEdiscrete", "Discrete PE Spectrum (rounding);Discrete PE;Counts", 500, 0, 25000)
    h_PEdiscrete.SetDirectory(0)
    h_nHit = ROOT.TH1F("h_nHit", "nHit Spectrum;Number of Fired Channels;Counts", 500, 0, 8048)
    h_nHit.SetDirectory(0)

    # Global statistics
    total_events_processed = 0
    total_events_vetoed_muon = 0
    total_events_vetoed_aftermuon = 0
    total_events_vetoed_afterpulse = 0
    total_events_clean = 0
    total_events_tdc_affected = 0
    total_channels_tdc_rejected = 0
    total_events_radial_cut = 0

    # Process each file
    for file_idx, input_file in enumerate(input_files, 1):
        printf(f"\n[{file_idx}/{len(input_files)}] {os.path.basename(input_file)}")

        if file_type == 'esd':
            result = process_single_esd(input_file, dark_noise_pe, radial_cut, esd_pe_type,
                                        source_pos=source_pos)
        else: #RTRAW
            result = process_single_rtraw(input_file, calibration, dark_noise_pe, max_pe_per_channel, pct_map=pct_map, rpde_map=rpde_map)

        if result is None:
            continue

        # Accumulate histograms
        h_PEcontin.Add(result['histograms']['PEcontin'])
        h_PEdiscrete.Add(result['histograms']['PEdiscrete'])
        h_nHit.Add(result['histograms']['nHit'])

        # Accumulate statistics
        stats = result['stats']
        total_events_processed += stats['events_processed']
        total_events_vetoed_muon += stats['events_vetoed_muon']
        total_events_vetoed_aftermuon += stats['events_vetoed_aftermuon']
        total_events_vetoed_afterpulse += stats['events_vetoed_afterpulse']
        total_events_clean += stats['events_clean']
        total_events_tdc_affected += stats['events_tdc_affected']
        total_channels_tdc_rejected += stats['channels_tdc_rejected']
        if 'events_radial_cut' in stats:
            total_events_radial_cut += stats['events_radial_cut']

        # Print per-file statistics
        if file_type == 'rtraw':
            printf(f"    Vetoed (muon): {stats['events_vetoed_muon']} ({100.0*stats['events_vetoed_muon']/stats['events_processed']:.1f}%)")
            printf(f"    Vetoed (after-muon): {stats['events_vetoed_aftermuon']} ({100.0*stats['events_vetoed_aftermuon']/stats['events_processed']:.1f}%)")
            printf(f"    Vetoed (after-pulse): {stats['events_vetoed_afterpulse']} ({100.0*stats['events_vetoed_afterpulse']/stats['events_processed']:.1f}%)")
            printf(f"    TDC-affected events: {stats['events_tdc_affected']} ({100.0*stats['events_tdc_affected']/stats['events_processed']:.1f}%)")
            printf(f"    TDC-rejected channels: {stats['channels_tdc_rejected']}")
        else:
            if 'events_radial_cut' in stats and stats['events_radial_cut'] > 0:
                printf(f"    Radial cut rejected: {stats['events_radial_cut']} ({100.0*stats['events_radial_cut']/stats['events_processed']:.1f}%)")
        printf(f"    Clean events: {stats['events_clean']} ({100.0*stats['events_clean']/stats['events_processed']:.1f}%)")

        # Save individual ROOT file in merged mode
        if merged_dir:
            basename = os.path.basename(input_file)
            file_num = basename.split('.')[-2] if '.' in basename else str(file_idx).zfill(3)
            outdir = os.path.dirname(out_file)
            outbase = os.path.basename(out_file).replace('-MERGED.root', '')
            individual_out_file = os.path.join(outdir, f"{outbase}-{file_num}.root")

            printf(f"    Saving individual file: {individual_out_file}")
            fout_individual = ROOT.TFile(individual_out_file, "RECREATE")
            result['histograms']['PEcontin'].SetName("h_PEcontin")
            result['histograms']['PEdiscrete'].SetName("h_PEdiscrete")
            result['histograms']['nHit'].SetName("h_nHit")
            result['histograms']['PEcontin'].Write()
            result['histograms']['PEdiscrete'].Write()
            result['histograms']['nHit'].Write()

            # Save dark noise in individual file too
            if dark_noise_pe > 0:
                dn_info = ROOT.TNamed("dark_noise_pe", f"{dark_noise_pe:.6f}")
                dn_info.Write()

                if file_type == 'esd':
                    # Calculate DN values for ESD
                    TDC_WINDOW_ESD = 1440.0
                    TDC_WINDOW_ANALYSIS = TDC_CUT_UP - TDC_CUT_LOW
                    dn_1440ns = dark_noise_pe * (TDC_WINDOW_ESD / TDC_WINDOW_ANALYSIS)
                    dn_adjustment = dn_1440ns - dark_noise_pe
                    
                    dn_esd_info = ROOT.TNamed("dark_noise_esd_info", 
                        f"DN_250ns={dark_noise_pe:.6f};DN_1440ns={dn_1440ns:.6f};DN_adjustment={dn_adjustment:.6f}")
                    dn_esd_info.Write()

            fout_individual.Close()

    printf("")
    printf("=" * 60)
    printf("MERGED STATISTICS")
    printf("=" * 60)
    printf(f"  Total files processed: {len(input_files)}")
    printf(f"  Total events: {total_events_processed}")

    if file_type == 'rtraw':
        printf(f"  Vetoed (muon): {total_events_vetoed_muon} ({100.0*total_events_vetoed_muon/total_events_processed:.1f}%)")
        printf(f"  Vetoed (after-muon): {total_events_vetoed_aftermuon} ({100.0*total_events_vetoed_aftermuon/total_events_processed:.1f}%)")
        printf(f"  Vetoed (after-pulse): {total_events_vetoed_afterpulse} ({100.0*total_events_vetoed_afterpulse/total_events_processed:.1f}%)")
        printf(f"  TDC-affected events: {total_events_tdc_affected} ({100.0*total_events_tdc_affected/total_events_processed:.1f}%)")
        printf(f"  TDC-rejected channels: {total_channels_tdc_rejected}")
    else:
        if total_events_radial_cut > 0:
            printf(f"  Radial cut rejected: {total_events_radial_cut} ({100.0*total_events_radial_cut/total_events_processed:.1f}%)")

    printf(f"  Clean events with contin PE > 0: {total_events_clean} ({100.0*total_events_clean/total_events_processed:.1f}%)")

    if dark_noise_pe > 0:
        printf(f"\n  DARK NOISE: {dark_noise_pe:.3f} PE")
    printf("")

    # Fit calibration source peak (source-aware)
    printf("=" * 60)
    source_energy_mev, source_desc = resolve_source(source_name)
    if source_energy_mev is None:
        printf("WARNING: No calibration source specified (--source-name not provided).")
        printf("         Histogram files will be saved but NO PEAK FIT will be performed.")
        printf("=" * 60)
        result_pe_cont = None
        result_pe      = None
        result_nhit    = None
    else:
        printf(f"FITTING {source_desc} PEAK ({source_energy_mev:.3f} MeV)")
        printf(f"  Using fit_source() dispatcher → fit_peaks modules")
        printf("=" * 60)

        # fit_source returns (simple_result, physics_result) for each histogram
        simple_cont, phys_cont = fit_source(
            h_PEcontin, source_name, dark_noise_pe,
            method_name="PEcontin", printf=printf)
        simple_pe, phys_pe = fit_source(
            h_PEdiscrete, source_name, dark_noise_pe,
            method_name="Discrete_PE", printf=printf)
        simple_nhit, phys_nhit = fit_source(
            h_nHit, source_name, 0.0,
            method_name="nHit", printf=printf)

        # Use best available result (physics if available, else simple)
        result_pe_cont = phys_cont if phys_cont else simple_cont
        result_pe      = phys_pe   if phys_pe   else simple_pe
        result_nhit    = phys_nhit if phys_nhit  else simple_nhit

        # Also keep simple results for dual reporting in energy_info
        simple_results = {
            'PEcontin': simple_cont,
            'PE': simple_pe,
            'NHIT': simple_nhit,
        }
        phys_results = {
            'PEcontin': phys_cont,
            'PE': phys_pe,
            'NHIT': phys_nhit,
        }

    # Create TNamed with results
    info_parts = [f"FILE_TYPE={file_type.upper()}"]
    info_parts.append(f"PE_METHOD=rounding")
    info_parts.append(f"N_FILES={len(input_files)}")
    info_parts.append(f"N_EVENTS={total_events_processed}")
    info_parts.append(f"TDC_CUT_LOW={TDC_CUT_LOW}")
    info_parts.append(f"TDC_CUT_UP={TDC_CUT_UP}")
    info_parts.append(f"DARK_NOISE_PE={dark_noise_pe:.6f}")
    info_parts.append(f"MAX_PE_PER_CHANNEL={max_pe_per_channel}")
    info_parts.append(f"SOURCE_NAME={source_name or 'none'}")
    if source_name:
        info_parts.append(f"SOURCE_ENERGY_MEV={resolve_source(source_name)[0]:.4f}")

    if file_type == 'esd':
        info_parts.append(f"RADIAL_CUT_APPLIED={radial_cut:.1f}")
        info_parts.append(f"N_RADIAL_CUT={total_events_radial_cut}")

    if file_type == 'rtraw':
        info_parts.append(f"N_TDC_AFFECTED={total_events_tdc_affected}")
        info_parts.append(f"N_TDC_CHANNELS_REJECTED={total_channels_tdc_rejected}")        

    # ── Helper to write fit results to energy_info ──────────────────────────
    def _append_info(parts, prefix, result):
        """Write one fit result to info_parts with standard key names."""
        if result:
            parts.append(f"RES_{prefix}={result['resolution']:.6f}")
            parts.append(f"RES_{prefix}_ERR={result['resolution_error']:.6f}")
            parts.append(f"RES_{prefix}_ERR_STAT={result.get('resolution_error_stat', result['resolution_error']):.6f}")
            parts.append(f"RES_{prefix}_ERR_SYS={result.get('resolution_error_sys', 0.0):.6f}")
            parts.append(f"MEAN_{prefix}={result['peak']:.6f}")
            parts.append(f"MEAN_{prefix}_ERR={result['peak_error']:.6f}")
            parts.append(f"MEAN_{prefix}_ERR_STAT={result.get('peak_error_stat', result['peak_error']):.6f}")
            parts.append(f"MEAN_{prefix}_ERR_SYS={result.get('peak_error_sys', 0.0):.6f}")
            parts.append(f"SIGMA_{prefix}={result['sigma']:.6f}")
            parts.append(f"SIGMA_{prefix}_ERR={result['sigma_error']:.6f}")
            parts.append(f"SIGMA_{prefix}_ERR_STAT={result.get('sigma_error_stat', result['sigma_error']):.6f}")
            parts.append(f"SIGMA_{prefix}_ERR_SYS={result.get('sigma_error_sys', 0.0):.6f}")
            parts.append(f"CHI2NDF_{prefix}={result.get('chi2ndf', -1):.4f}")
            parts.append(f"METHOD_{prefix}={result.get('method', 'unknown')}")
        else:
            for key in ('RES', 'MEAN', 'SIGMA'):
                parts.append(f"{key}_{prefix}=-1")
                parts.append(f"{key}_{prefix}_ERR=0")
                parts.append(f"{key}_{prefix}_ERR_STAT=0")
                parts.append(f"{key}_{prefix}_ERR_SYS=0")
            parts.append(f"CHI2NDF_{prefix}=-1")
            parts.append(f"METHOD_{prefix}=none")

    # Best results (physics if available, else simple gauss+pol3)
    _append_info(info_parts, "PEcontin", result_pe_cont)
    _append_info(info_parts, "PE",       result_pe)
    _append_info(info_parts, "NHIT",     result_nhit)

    # Also store simple gauss+pol3 results separately (for comparison)
    if source_name:
        _append_info(info_parts, "PEcontin_SIMPLE", simple_results.get('PEcontin'))
        _append_info(info_parts, "PE_SIMPLE",       simple_results.get('PE'))
        _append_info(info_parts, "NHIT_SIMPLE",     simple_results.get('NHIT'))
        # Physics model results separately (may be None if not Ge68/Cs137)
        _append_info(info_parts, "PEcontin_PHYS",   phys_results.get('PEcontin'))
        _append_info(info_parts, "PE_PHYS",         phys_results.get('PE'))
        _append_info(info_parts, "NHIT_PHYS",       phys_results.get('NHIT'))

    info_str = ";".join(info_parts)
    energy_info = ROOT.TNamed("energy_info", info_str)

    # Save output
    printf("")
    printf("=" * 60)
    printf("SAVING OUTPUT")
    printf("=" * 60)

    fout = ROOT.TFile(out_file, "RECREATE")
    h_PEcontin.Write()
    h_PEdiscrete.Write()
    h_nHit.Write()
    energy_info.Write()

    # Also save dark noise as separate TNamed for easy retrieval
    if dark_noise_pe > 0:
        dn_info = ROOT.TNamed("dark_noise_pe", f"{dark_noise_pe:.6f}")
        dn_info.Write()

    fout.Close()

    printf(f"Output saved to: {out_file}")
    if merged_dir:
        printf(f"Individual files also saved in: {os.path.dirname(out_file)}")
    printf("")

    # Print summary
    printf("=" * 60)
    printf("ENERGY RESOLUTION SUMMARY")
    printf("=" * 60)
    printf(f"File type: {file_type.upper()}")
    printf(f"PE Method: Rounding (discrete PE)")
    if len(input_files) > 1:
        printf(f"Merged: {len(input_files)} files")

    if file_type == 'esd' and dark_noise_pe > 0:
        printf(f"   Dark Noise (250 ns): {dark_noise_pe:.3f} PE")
        if 'dn_1440ns' in locals():  # Only print if defined (merged mode)
            printf(f"   Dark Noise (1440 ns, ESD): {dn_1440ns:.3f} PE")
            printf(f"   DN Adjustment: {dn_adjustment:.3f} PE")
        printf("Resolution: σ/(μ-DN)")
    elif file_type == 'rtraw' and dark_noise_pe > 0:                    
        printf(f"Dark Noise: {dark_noise_pe:.3f} PE")
        printf(f"Resolution: σ/(μ-DN)")
    else:
        printf(f"Resolution: σ/μ")
    printf("-" * 80)
    print(f"{'Method':<20} {'Mean':<22} {'Sigma':<22} {'Resolution':<22} {'Status':<10}")
    printf("-" * 80)

    # ================= CONTINUOUS PE =================
    if result_pe_cont:
        print(
            f"{'Continuous PE':<20}"
            f"{result_pe_cont['peak']:.1f} ± {result_pe_cont['peak_error']:.1f:<15}"
            f"{result_pe_cont['sigma']:.1f} ± {result_pe_cont['sigma_error']:.1f:<15}"
            f"{result_pe_cont['resolution']*100:.2f}% ± {result_pe_cont['resolution_error']*100:.2f}%<15"
            f"{'PASS':<10}"
        )
    else:
        print(f"{'Continuous PE':<20}{'---':<22}{'---':<22}{'---':<22}{'FAIL':<10}")

    # ================= DISCRETE PE =================
    if result_pe:
        print(
            f"{'Discrete PE':<20}"
            f"{result_pe['peak']:.1f} ± {result_pe['peak_error']:.1f:<15}"
            f"{result_pe['sigma']:.1f} ± {result_pe['sigma_error']:.1f:<15}"
            f"{result_pe['resolution']*100:.2f}% ± {result_pe['resolution_error']*100:.2f}%<15"
            f"{'PASS':<10}"
        )
    else:
        print(f"{'Discrete PE':<20}{'---':<22}{'---':<22}{'---':<22}{'FAIL':<10}")

    # ================= nHit =================
    if result_nhit:
        print(
            f"{'nHit':<20}"
            f"{result_nhit['peak']:.1f} ± {result_nhit['peak_error']:.1f:<15}"
            f"{result_nhit['sigma']:.1f} ± {result_nhit['sigma_error']:.1f:<15}"
            f"{result_nhit['resolution']*100:.2f}% ± {result_nhit['resolution_error']*100:.2f}%<15"
            f"{'PASS':<10}"
        )
    else:
        print(f"{'nHit':<20}{'---':<22}{'---':<22}{'---':<22}{'FAIL':<10}")

    printf("-" * 80)
    printf("")
    printf("SUCCESS")
    printf("=" * 80)

    return 0


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate energy spectra from RTRAW/ESD with Gaussian fits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single RTRAW file
  python get_spectrum.py input.rtraw calib.txt output.root

  # Single ESD file (origin-based radial cut)
  python get_spectrum.py input.esd calib.txt output.root --esd

  # Single ESD file (off-axis radial cut for Cs-137 CLS source)
  python get_spectrum.py input.esd calib.txt output.root --esd \\
      --source-pos -23.1093 -188.278 37.3801

  # Merged mode (all RTRAW files)
  python get_spectrum.py --merged /path/to/rtraw/dir calib.txt output_merged.root

  # Merged mode (all ESD files, off-axis cut)
  python get_spectrum.py --merged /path/to/esd/dir calib.txt output_merged.root --esd \\
      --source-pos -23.1093 -188.278 37.3801
"""
    )

    parser.add_argument("input_file", nargs='?', help="Path to RTRAW/ESD file (or use --merged)")
    parser.add_argument("calib_file", help="Path to calibration file")
    parser.add_argument("out_file", help="Output ROOT file path")
    parser.add_argument("--merged", metavar="DIR",
                        help="Process all files in directory (merged mode)")
    parser.add_argument("--max-pe-per-channel", type=float, default=-1,
                        help="Max PE/channel cut for RTRAW (default: -1, no cut)")
    parser.add_argument("--esd", action='store_true',
                        help="Input is ESD file (default: RTRAW)")
    parser.add_argument('--esd-pe-type', type=str, choices=['pesum_g', 'pesum_basic'], 
                    default='pesum_g',
                    help='PE type for ESD: pesum_g (geometry corrected, default) or pesum_basic')
    
    parser.add_argument("--radial-cut", type=float, default=DEFAULT_RADIAL_CUT,
                      help="Radial cut in mm for ESD (default: 150.0)")
    parser.add_argument("--no-radial-cut", action='store_true',
                        help="Disable radial cut for ESD")
    parser.add_argument("--source-pos", type=float, nargs=3, metavar=('X', 'Y', 'Z'),
                        default=None,
                        help="Off-axis source position in mm (X Y Z) for ESD radial cut. "
                             "When provided, r is computed relative to (X,Y,Z) instead of "
                             "the detector origin.  For Cs-137 CLS: "
                             f"--source-pos {CLS_CS137_SOURCE_POS[0]} "
                             f"{CLS_CS137_SOURCE_POS[1]} {CLS_CS137_SOURCE_POS[2]}")
    parser.add_argument("--run", type=int, default=None,
                        help="Run number (required to select correct bad-channel list, "
                             "SiPM calib ROOT and rec parameters from cvmfs). "
                             "Ranges: 1157-1193 → T25.6.4 files; 1295+ → T25.7.1 files.")

    known = ', '.join(sorted(__import__('spectrum_utils').SOURCES.keys()))
    parser.add_argument("--pct-file", type=str, default=None,
                        help="CSV file with per-channel P_ct from gain_calibration EMG output. "
                             "When provided, applies crosstalk correction: PE_corr = PE_raw / (1+P_ct).")
    parser.add_argument("--rpde-file", type=str, default=None,
                        help="CSV/TXT file with per-channel relative PDE (columns: channel_id rPDE). "
                             "rPDE is normalised so mean=1.0; channels with rPDE<1 see fewer photons. "
                             "Correction: PE_true = PE_raw / rPDE (applied per channel, before summing). "
                             "Source: Wuhan group TAO channel-level calibration (Jan 2026).")
    parser.add_argument("--source-name", type=str, default=None, metavar="SOURCE",
                        help=f"Calibration source to fit. Known sources: {known}. "
                             "If omitted, histograms are saved but no peak fit is performed.")

    # =====================================================
    # Validate arguments
    # =====================================================
    args = parser.parse_args()

    if not args.merged and not args.input_file:
        parser.error("Either provide input_file or use --merged DIR")

    if args.run is None:
        printf("WARNING: --run not specified. Run-range-specific cvmfs files "
               "(bad channels, SiPM calib ROOT) will default to 1157-1193 paths.")

    file_type = "esd" if args.esd else "rtraw"

    # Validate calibration file requirement
    if file_type == "rtraw":
        if not args.calib_file:
            parser.error("Calibration file is REQUIRED for RTRAW analysis")
        if not file_exists_or_accessible(args.calib_file):
            printf(f"ERROR: Calibration file not found: {args.calib_file}")
            sys.exit(1)
    else:  # ESD
        if args.calib_file:
            printf("NOTE: Calibration file provided but not used for ESD (already applied in reconstruction)")
        # Use dummy path - won't be loaded anyway
        args.calib_file = args.calib_file or "/dev/null"

    # Validate file-type specific options
    if file_type == "rtraw":
        if args.no_radial_cut or args.radial_cut != DEFAULT_RADIAL_CUT:
            printf("WARNING: Radial cut options ignored for RTRAW (not available)")
        if args.esd_pe_type != 'pesum_g':
            printf("WARNING: --esd-pe-type ignored for RTRAW (not applicable)")
        if args.source_pos is not None:
            printf("WARNING: --source-pos ignored for RTRAW (not applicable)")
        
        radial_cut = 0.0
        esd_pe_type = 'pesum_g'
        source_pos = None
    else:  # ESD
        if args.max_pe_per_channel != -1:
            printf("WARNING: --max-pe-per-channel ignored for ESD (use for RTRAW only)")
        
        radial_cut = 0.0 if args.no_radial_cut else args.radial_cut
        esd_pe_type = args.esd_pe_type
        source_pos = tuple(args.source_pos) if args.source_pos is not None else None

        if source_pos is not None and radial_cut == 0.0:
            printf("WARNING: --source-pos provided but radial cut is disabled (--no-radial-cut). "
                   "Source position will be ignored.")
            source_pos = None

    # =====================================================
    # Call get_spectrum - calibration loading happens INSIDE
    # =====================================================
    sys.exit(get_spectrum(
        args.input_file,
        args.calib_file,
        args.out_file,
        args.merged,
        file_type,
        radial_cut,
        args.max_pe_per_channel if file_type == "rtraw" else -1,
        esd_pe_type if file_type == "esd" else 'pesum_g',
        run_number=args.run,
        source_pos=source_pos,
        source_name=args.source_name,
        pct_file=args.pct_file,
        rpde_file=args.rpde_file,
    ))