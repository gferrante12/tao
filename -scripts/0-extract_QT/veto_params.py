#!/usr/bin/env python3
"""
veto_params.py — Centralized veto parameters for TAO data analysis

This module provides a single source of truth for all veto and cut parameters
used across the TAO analysis scripts. Import from here instead of hardcoding
values in individual scripts.

USAGE:
    from veto_params import PARAMS_CALIB2, TDC_WINDOW, ADC_CUTS

PHYSICS CONTEXT:
    TAO detector characteristics:
      - 8048 SiPM channels
      - Average gain: ~6000 ADC/PE
      - Light yield: ~4300 PE/MeV
      - TDC resolution: 1 ns

    Cut derivations:
      - ADC_HIT_MAX = 1e5 ADC ≈ 17 PE (rejects muon single-channel deposits)
      - MAX_TOTAL_ADC = 4e8 ADC ≈ 15 MeV (rejects high-energy events)
      - TDC window [240, 440] ns selects prompt scintillation, rejects dark noise

Author: Based on TAOsw 25.7.1 Calibration and RecChargeCenterAlg
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

# =============================================================================
# DETECTOR CONSTANTS
# =============================================================================

N_CHANNELS = 8048           # Total SiPM channels
NOMINAL_GAIN = 6000.0       # ADC/PE (average)
NOMINAL_LY = 4300.0         # PE/MeV (light yield)

# =============================================================================
# TDC WINDOW (unified across all scripts)
# =============================================================================

@dataclass(frozen=True)
class TDCWindow:
    """TDC time window for hit selection."""
    min_ns: float = 240.0   # ns - prompt window start
    max_ns: float = 440.0   # ns - prompt window end
    
    @property
    def width_ns(self) -> float:
        return self.max_ns - self.min_ns
    
    @property
    def width_s(self) -> float:
        return self.width_ns * 1e-9

# Default TDC window (use this everywhere)
TDC_WINDOW = TDCWindow(min_ns=240.0, max_ns=440.0)

# Legacy windows (for reference only - DO NOT USE)
TDC_WINDOW_LEGACY_SPECTRUM = TDCWindow(min_ns=200.0, max_ns=450.0)  # Old get_spectrum.py
TDC_WINDOW_LEGACY_CCREC = TDCWindow(min_ns=200.0, max_ns=450.0)     # Old RecChargeCenterAlg

# =============================================================================
# ADC CUTS
# =============================================================================

@dataclass(frozen=True)
class ADCCuts:
    """ADC cut thresholds for hit and event selection."""
    # Per-hit cuts
    hit_min: float = 1000.0     # ADC - baseline noise rejection
    hit_max: float = 1e5        # ADC - muon deposit rejection (~17 PE)
    
    # Per-channel event-level cuts
    channel_max: float = 1.7e7  # ADC - flasher/saturation guard
    
    # Event total cuts
    event_max: float = 8e8      # ADC - outlier rejection
    muon_threshold: float = 8e8 # ADC - CD muon tagging (often = event_max)

# Default ADC cuts
ADC_CUTS = ADCCuts()

# Physics-derived limits (for reference)
ADC_CUTS_PHYSICS = ADCCuts(
    hit_min=1000.0,
    hit_max=1e5,
    channel_max=1.7e7,
    event_max=4e8,      # ~15 MeV rejection
    muon_threshold=5.4e8
)

# =============================================================================
# VETO PARAMETERS (mode-dependent)
# =============================================================================

@dataclass
class VetoParams:
    """Complete veto parameter set for a specific analysis mode."""
    
    # Event-level muon thresholds
    MUON_THRESHOLD_CD: float    # ADC counts (CD total)
    MUON_THRESHOLD_WT: int      # fired channels (WT)
    MUON_THRESHOLD_TVT: int     # fired channels (TVT)
    
    # Time windows (ns)
    AFTER_MU: float             # after-muon veto window
    AFTER_PULSE: float          # after-pulse veto window
    
    # Event outlier cuts
    MAX_TOTAL_ADC: float        # event total ADC
    MAX_ADC_PER_CHANNEL: float  # per-channel flasher guard
    MIN_NHIT: int               # minimum fired channels
    MAX_NHIT: int               # maximum fired channels
    
    # Per-hit cuts (None = disabled)
    TDC_HIT_MIN: Optional[float] = None
    TDC_HIT_MAX: Optional[float] = None
    ADC_HIT_MIN: Optional[float] = None
    ADC_HIT_MAX: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "MUON_THRESHOLD_CD": self.MUON_THRESHOLD_CD,
            "MUON_THRESHOLD_WT": self.MUON_THRESHOLD_WT,
            "MUON_THRESHOLD_TVT": self.MUON_THRESHOLD_TVT,
            "AFTER_MU": self.AFTER_MU,
            "AFTER_PULSE": self.AFTER_PULSE,
            "MAX_TOTAL_ADC": self.MAX_TOTAL_ADC,
            "MAX_ADC_PER_CHANNEL": self.MAX_ADC_PER_CHANNEL,
            "MIN_NHIT": self.MIN_NHIT,
            "MAX_NHIT": self.MAX_NHIT,
            "TDC_HIT_MIN": self.TDC_HIT_MIN,
            "TDC_HIT_MAX": self.TDC_HIT_MAX,
            "ADC_HIT_MIN": self.ADC_HIT_MIN,
            "ADC_HIT_MAX": self.ADC_HIT_MAX,
        }

# -----------------------------------------------------------------------------
# Standard analysis modes
# -----------------------------------------------------------------------------

PARAMS_CALIB = VetoParams(
    MUON_THRESHOLD_CD=8e8,
    MUON_THRESHOLD_WT=5,
    MUON_THRESHOLD_TVT=3,
    AFTER_MU=1000e3,        # 1000 µs
    AFTER_PULSE=5e3,        # 5 µs
    MAX_TOTAL_ADC=8e8,
    MAX_ADC_PER_CHANNEL=1.7e7,
    MIN_NHIT=2000,
    MAX_NHIT=7000,
    # No per-hit TDC/ADC cuts
    ADC_HIT_MAX=1e5,        # Only upper ADC cut
)

PARAMS_CALIB2 = VetoParams(
    MUON_THRESHOLD_CD=8e8,
    MUON_THRESHOLD_WT=5,
    MUON_THRESHOLD_TVT=3,
    AFTER_MU=1000e3,        # 1000 µs
    AFTER_PULSE=5e3,        # 5 µs
    MAX_TOTAL_ADC=8e8,
    MAX_ADC_PER_CHANNEL=1.7e7,
    MIN_NHIT=2000,
    MAX_NHIT=7000,
    # Full per-hit cuts (aligned with TDC_WINDOW)
    TDC_HIT_MIN=TDC_WINDOW.min_ns,  # 240 ns
    TDC_HIT_MAX=TDC_WINDOW.max_ns,  # 440 ns
    ADC_HIT_MIN=1000.0,
    ADC_HIT_MAX=1e5,
)

PARAMS_PHYSICS = VetoParams(
    MUON_THRESHOLD_CD=5.4e8,
    MUON_THRESHOLD_WT=15,
    MUON_THRESHOLD_TVT=4,
    AFTER_MU=1000e3,
    AFTER_PULSE=5e3,
    MAX_TOTAL_ADC=8e8,
    MAX_ADC_PER_CHANNEL=1.7e7,
    MIN_NHIT=100,
    MAX_NHIT=5500,
    ADC_HIT_MAX=1e5,
)

PARAMS_IBD = VetoParams(
    MUON_THRESHOLD_CD=8e8,
    MUON_THRESHOLD_WT=11,
    MUON_THRESHOLD_TVT=4,
    AFTER_MU=100e3,         # 100 µs (shorter for IBD)
    AFTER_PULSE=2.5e3,      # 2.5 µs
    MAX_TOTAL_ADC=5e8,
    MAX_ADC_PER_CHANNEL=1.68e7,
    MIN_NHIT=500,
    MAX_NHIT=7000,
    ADC_HIT_MAX=1e5,
)

# Parameter lookup map
PARAMS_MAP = {
    "calib": PARAMS_CALIB,
    "calib2": PARAMS_CALIB2,
    "physics": PARAMS_PHYSICS,
    "ibd": PARAMS_IBD,
}

# =============================================================================
# CALIBRATION FILE PATHS (run-range aware)
# =============================================================================

# cvmfs base paths
CVMFS_SIPM = "/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Calibration/Calib.CD.SiPM.Param"
CVMFS_BADCH = "/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Reconstruction/Badchannellist"
CVMFS_REC = "/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Reconstruction/CCRec"

def get_run_config(run_number: int) -> Dict[str, Any]:
    """
    Return run-range-appropriate cvmfs paths for a given run number.
    
    Returns dict with keys:
        sipm_calib_root   - official SiPM calibration ROOT file
        bad_channel_st    - bad channel list (static baseline)
        bad_channel_dyn   - bad channel list (dynamic baseline)
        run_range_label   - human-readable range string
    """
    if run_number >= 1295:
        return {
            'sipm_calib_root': f"{CVMFS_SIPM}/TAO_SiPM_calib_par_1770336000.root",
            'bad_channel_st': f"{CVMFS_BADCH}/badch_T25.7.1_fixed.txt",
            'bad_channel_dyn': f"{CVMFS_BADCH}/badch_T25.7.1_dyn.txt",
            'run_range_label': '1295+',
        }
    elif run_number <= 1193:
        return {
            'sipm_calib_root': f"{CVMFS_SIPM}/TAO_SiPM_calib_par_1768003200.root",
            'bad_channel_st': f"{CVMFS_BADCH}/ALLBad_channels_20260112_1053_st.txt",
            'bad_channel_dyn': f"{CVMFS_BADCH}/ALLBad_channels_20260112_1039_dy.txt",
            'run_range_label': '1157-1193',
        }
    else:
        # Gap range 1194-1294: use 1295+ as best guess
        return {
            'sipm_calib_root': f"{CVMFS_SIPM}/TAO_SiPM_calib_par_1770336000.root",
            'bad_channel_st': f"{CVMFS_BADCH}/badch_T25.7.1_fixed.txt",
            'bad_channel_dyn': f"{CVMFS_BADCH}/badch_T25.7.1_dyn.txt",
            'run_range_label': '1194-1294 (gap, using 1295+ defaults)',
        }

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_params(mode: str) -> VetoParams:
    """Get veto parameters for a given mode name."""
    if mode not in PARAMS_MAP:
        raise ValueError(f"Unknown mode: {mode}. Choose from {list(PARAMS_MAP.keys())}")
    return PARAMS_MAP[mode]


def energy_to_adc(energy_mev: float, gain: float = NOMINAL_GAIN, 
                  ly: float = NOMINAL_LY) -> float:
    """Convert energy in MeV to expected total ADC."""
    return energy_mev * ly * gain


def adc_to_energy(adc: float, gain: float = NOMINAL_GAIN,
                  ly: float = NOMINAL_LY) -> float:
    """Convert total ADC to approximate energy in MeV."""
    return adc / (ly * gain)


def adc_to_pe(adc: float, gain: float = NOMINAL_GAIN) -> float:
    """Convert ADC counts to photoelectrons."""
    return adc / gain


def pe_to_adc(pe: float, gain: float = NOMINAL_GAIN) -> float:
    """Convert photoelectrons to ADC counts."""
    return pe * gain


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TAO Veto Parameters Module")
    print("=" * 60)
    print()
    
    print("TDC Window:")
    print(f"  [{TDC_WINDOW.min_ns}, {TDC_WINDOW.max_ns}] ns")
    print(f"  Width: {TDC_WINDOW.width_ns} ns = {TDC_WINDOW.width_s*1e6:.1f} µs")
    print()
    
    print("ADC Cuts:")
    print(f"  Hit min:     {ADC_CUTS.hit_min:.0f} ADC")
    print(f"  Hit max:     {ADC_CUTS.hit_max:.0e} ADC = {adc_to_pe(ADC_CUTS.hit_max):.0f} PE")
    print(f"  Event max:   {ADC_CUTS.event_max:.0e} ADC = {adc_to_energy(ADC_CUTS.event_max):.1f} MeV")
    print()
    
    print("Available modes:", list(PARAMS_MAP.keys()))
    print()
    
    for mode, params in PARAMS_MAP.items():
        print(f"PARAMS_{mode.upper()}:")
        print(f"  Muon CD:     {params.MUON_THRESHOLD_CD:.1e} ADC")
        print(f"  After-muon:  {params.AFTER_MU/1e3:.0f} µs")
        print(f"  nHit range:  [{params.MIN_NHIT}, {params.MAX_NHIT}]")
        if params.TDC_HIT_MIN is not None:
            print(f"  TDC window:  [{params.TDC_HIT_MIN}, {params.TDC_HIT_MAX}] ns")
        print()
    
    print("Run config examples:")
    for run in [1157, 1250, 1295, 1400]:
        cfg = get_run_config(run)
        print(f"  RUN {run}: {cfg['run_range_label']}")
