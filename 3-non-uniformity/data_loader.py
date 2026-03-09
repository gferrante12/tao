#!/usr/bin/env python3
"""
data_loader.py  —  Load fit results from JSON/ROOT for non-uniformity analysis

Reads the output of:
  - fit_peaks_ge68.py  (ACU ⁶⁸Ge fits)
  - fit_peaks_cs137.py (CLS ¹³⁷Cs fits)
  - get_spectrum.py    (inline Gaussian+pol3 fits)

Each scan position produces a JSON file with keys:
    mean_PE, sigma_PE, resolution_pct, LY_PE_per_MeV, dark_noise_PE,
    mean_PE_err, sigma_PE_err, resolution_pct_err, LY_PE_per_MeV_err,
    chi2_ndf, ...

Alternatively, reads ROOT files containing energy_info TTree/TNamed metadata.

Author: G. Ferrante (INFN-MiB / UniMiB)
"""

import os
import json
import glob
import re
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from scan_config import (
    E_GE68_MEV, E_CS137_MEV, DN_PE_DEFAULT,
    LY_NOMINAL_PE_PER_MEV, ACRYLIC_INNER_RADIUS_MM
)

# =============================================================================
# DATA CONTAINERS
# =============================================================================

@dataclass
class FitResult:
    """Fit result for a single calibration position."""
    # Position
    run_number: int = -1
    system: str = ""         # "ACU" or "CLS"
    z_mm: float = 0.0
    r_mm: float = 0.0
    theta_deg: float = 90.0
    phi_deg: float = 0.0
    source: str = ""
    source_energy_mev: float = 0.0

    # Fit parameters
    mean_pe: float = 0.0
    mean_pe_err: float = 0.0
    sigma_pe: float = 0.0
    sigma_pe_err: float = 0.0
    resolution_pct: float = 0.0
    resolution_pct_err: float = 0.0
    ly_pe_per_mev: float = 0.0
    ly_pe_per_mev_err: float = 0.0
    dark_noise_pe: float = 0.0
    chi2_ndf: float = -1.0
    n_events: int = 0

    # Derived
    @property
    def r_norm(self):
        return self.r_mm / ACRYLIC_INNER_RADIUS_MM

    @property
    def g_value(self):
        """Relative light yield g = LY(r,θ) / LY(center)."""
        # This must be set externally after normalising to center
        return getattr(self, '_g_value', None)

    @g_value.setter
    def g_value(self, val):
        self._g_value = val


@dataclass
class ScanDataset:
    """Complete dataset for one scan type (ACU or CLS)."""
    system: str          # "ACU" or "CLS"
    source: str
    source_energy_mev: float
    results: List[FitResult] = field(default_factory=list)

    def add(self, fr: FitResult):
        self.results.append(fr)

    @property
    def n_positions(self):
        return len(self.results)

    # Vectorised access
    def z_array(self):
        return np.array([r.z_mm for r in self.results])

    def r_array(self):
        return np.array([r.r_mm for r in self.results])

    def theta_array(self):
        return np.array([r.theta_deg for r in self.results])

    def phi_array(self):
        return np.array([r.phi_deg for r in self.results])

    def mean_array(self):
        return np.array([r.mean_pe for r in self.results])

    def mean_err_array(self):
        return np.array([r.mean_pe_err for r in self.results])

    def sigma_array(self):
        return np.array([r.sigma_pe for r in self.results])

    def sigma_err_array(self):
        return np.array([r.sigma_pe_err for r in self.results])

    def resolution_array(self):
        return np.array([r.resolution_pct for r in self.results])

    def resolution_err_array(self):
        return np.array([r.resolution_pct_err for r in self.results])

    def ly_array(self):
        return np.array([r.ly_pe_per_mev for r in self.results])

    def ly_err_array(self):
        return np.array([r.ly_pe_per_mev_err for r in self.results])

    def g_array(self):
        """Relative light yield array. Must call compute_g() first."""
        return np.array([r.g_value if r.g_value is not None else np.nan
                         for r in self.results])

    def compute_g(self, center_ly: Optional[float] = None):
        """
        Compute g(r,θ) = LY(r,θ) / LY(center) for all positions.
        
        If center_ly is None, use the position closest to r=0.
        """
        if center_ly is None:
            # Find center position (r closest to 0)
            r_arr = self.r_array()
            ly_arr = self.ly_array()
            if len(r_arr) == 0:
                return
            idx_center = np.argmin(r_arr)
            center_ly = ly_arr[idx_center]
            if center_ly <= 0:
                print(f"WARNING: center LY = {center_ly}, cannot normalise")
                return

        for fr in self.results:
            if center_ly > 0:
                fr.g_value = fr.ly_pe_per_mev / center_ly
            else:
                fr.g_value = np.nan


# =============================================================================
# JSON LOADER
# =============================================================================

def _parse_position_from_filename(filename: str):
    """
    Extract position info from fit result filename.
    
    Expected patterns:
        fit_Ge68_RUN1295_z0.json        → ACU, z=0
        fit_Ge68_RUN1296_z-100.json     → ACU, z=-100
        fit_Cs137_RUN1344_r190_th100.json → CLS, r=190, θ=100
        fit_Cs137_RUN1344.json           → CLS (position from metadata)
        
    Also handles directory-based naming:
        RUN1295/fit_result.json
    """
    basename = os.path.basename(filename)
    dirname  = os.path.basename(os.path.dirname(filename))

    info = {'run': -1, 'system': '', 'z': None, 'r': None, 'theta': None, 'phi': None}

    # Extract run number
    m = re.search(r'(?:RUN|run)(\d+)', basename) or re.search(r'(?:RUN|run)(\d+)', dirname)
    if m:
        info['run'] = int(m.group(1))

    # ACU z-position
    m = re.search(r'_z([+-]?\d+(?:\.\d+)?)', basename)
    if m:
        info['system'] = 'ACU'
        info['z'] = float(m.group(1))
        info['r'] = abs(info['z'])
        info['theta'] = 0.0 if info['z'] >= 0 else 180.0
        if info['z'] == 0:
            info['theta'] = 90.0

    # CLS r, theta
    m_r  = re.search(r'_r(\d+(?:\.\d+)?)', basename)
    m_th = re.search(r'_th(\d+(?:\.\d+)?)', basename)
    if m_r:
        info['system'] = 'CLS'
        info['r'] = float(m_r.group(1))
    if m_th:
        info['theta'] = float(m_th.group(1))

    # CLS phi
    m_phi = re.search(r'_phi(\d+(?:\.\d+)?)', basename)
    if m_phi:
        info['phi'] = float(m_phi.group(1))

    return info


def load_fit_json(json_path: str, position_info: Optional[dict] = None) -> Optional[FitResult]:
    """Load a single fit result from a JSON file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"WARNING: Cannot load {json_path}: {e}")
        return None

    if position_info is None:
        position_info = _parse_position_from_filename(json_path)

    # Determine source
    source = ""
    src_energy = 0.0
    for key in ['source', 'source_name']:
        if key in data:
            source = data[key]
            break
    if not source:
        bn = os.path.basename(json_path).lower()
        if 'ge68' in bn:
            source = 'Ge68'
        elif 'cs137' in bn:
            source = 'Cs137'

    if source.lower() in ('ge68', 'ge-68'):
        src_energy = E_GE68_MEV
    elif source.lower() in ('cs137', 'cs-137'):
        src_energy = E_CS137_MEV

    fr = FitResult(
        run_number=position_info.get('run', data.get('run', -1)),
        system=position_info.get('system', data.get('system', '')),
        z_mm=position_info.get('z', data.get('z_mm', 0.0)) or 0.0,
        r_mm=position_info.get('r', data.get('r_mm', 0.0)) or 0.0,
        theta_deg=position_info.get('theta', data.get('theta_deg', 90.0)) or 90.0,
        phi_deg=position_info.get('phi', data.get('phi_deg', 0.0)) or 0.0,
        source=source,
        source_energy_mev=src_energy,

        mean_pe=data.get('mean_PE', data.get('peak', 0.0)),
        mean_pe_err=data.get('mean_PE_err', data.get('peak_error', 0.0)),
        sigma_pe=data.get('sigma_PE', data.get('sigma', 0.0)),
        sigma_pe_err=data.get('sigma_PE_err', data.get('sigma_error', 0.0)),
        resolution_pct=data.get('resolution_pct', data.get('resolution', 0.0) * 100),
        resolution_pct_err=data.get('resolution_pct_err',
                                     data.get('resolution_error', 0.0) * 100),
        ly_pe_per_mev=data.get('LY_PE_per_MeV', 0.0),
        ly_pe_per_mev_err=data.get('LY_PE_per_MeV_err', 0.0),
        dark_noise_pe=data.get('dark_noise_PE', DN_PE_DEFAULT),
        chi2_ndf=data.get('chi2_ndf', data.get('chi2ndf', -1.0)),
    )

    # Compute LY if not stored
    if fr.ly_pe_per_mev == 0.0 and fr.mean_pe > 0 and fr.source_energy_mev > 0:
        denom = fr.mean_pe - fr.dark_noise_pe
        if denom > 0:
            fr.ly_pe_per_mev = denom / fr.source_energy_mev

    # If resolution was stored as fraction (0.03) instead of percent (3.0)
    if 0 < fr.resolution_pct < 1.0:
        fr.resolution_pct *= 100.0
        fr.resolution_pct_err *= 100.0

    return fr


def load_scan_directory(scan_dir: str, system: str = "auto",
                        pattern: str = "*.json") -> ScanDataset:
    """
    Load all fit results from a directory tree.
    
    Expects JSON files produced by fit_peaks_ge68.py or fit_peaks_cs137.py.
    
    Args:
        scan_dir: Path to directory containing JSON fit results
        system: "ACU", "CLS", or "auto" (detect from filenames)
        pattern: glob pattern for JSON files
    """
    json_files = sorted(glob.glob(os.path.join(scan_dir, "**", pattern), recursive=True))
    if not json_files:
        json_files = sorted(glob.glob(os.path.join(scan_dir, pattern)))

    if not json_files:
        print(f"WARNING: No JSON files found in {scan_dir}")
        return ScanDataset(system="UNKNOWN", source="", source_energy_mev=0.0)

    results = []
    for jf in json_files:
        fr = load_fit_json(jf)
        if fr is not None and fr.mean_pe > 0:
            results.append(fr)

    if not results:
        return ScanDataset(system="UNKNOWN", source="", source_energy_mev=0.0)

    # Auto-detect system
    if system == "auto":
        systems = set(r.system for r in results if r.system)
        if len(systems) == 1:
            system = systems.pop()
        elif any(r.source.lower() in ('ge68', 'ge-68') for r in results):
            system = "ACU"
        elif any(r.source.lower() in ('cs137', 'cs-137') for r in results):
            system = "CLS"
        else:
            system = "UNKNOWN"

    sources = set(r.source for r in results if r.source)
    source = sources.pop() if len(sources) == 1 else "/".join(sources)
    energies = set(r.source_energy_mev for r in results if r.source_energy_mev > 0)
    energy = energies.pop() if len(energies) == 1 else 0.0

    ds = ScanDataset(system=system, source=source, source_energy_mev=energy)
    for fr in results:
        ds.add(fr)

    return ds


# =============================================================================
# ROOT FILE LOADER (via uproot or PyROOT)
# =============================================================================

def load_fit_from_root(root_path: str, position_info: Optional[dict] = None) -> Optional[FitResult]:
    """
    Load fit result from a ROOT file produced by get_spectrum.py.
    
    Reads the energy_info TNamed/TTree stored alongside histograms.
    Falls back to re-fitting the histogram if metadata is missing.
    """
    try:
        import uproot
        f = uproot.open(root_path)
        
        # Try to read energy_info metadata
        info = {}
        for key in f.keys():
            obj = f[key]
            if hasattr(obj, 'title') and 'energy_info' in key.lower():
                # TNamed: title contains JSON
                try:
                    info = json.loads(obj.title)
                except:
                    pass
        
        if info:
            if position_info is None:
                position_info = _parse_position_from_filename(root_path)
            
            fr = FitResult(
                run_number=position_info.get('run', info.get('RUN', -1)),
                system=position_info.get('system', ''),
                z_mm=position_info.get('z', 0.0) or 0.0,
                r_mm=position_info.get('r', 0.0) or 0.0,
                theta_deg=position_info.get('theta', 90.0) or 90.0,
                phi_deg=position_info.get('phi', 0.0) or 0.0,
                source=info.get('SOURCE', ''),
                mean_pe=info.get('MEAN_PE', info.get('PEAK_PE', 0.0)),
                sigma_pe=info.get('SIGMA_PE', 0.0),
                resolution_pct=info.get('RESOLUTION_PCT', 0.0),
                ly_pe_per_mev=info.get('LY_PE_PER_MEV', 0.0),
                dark_noise_pe=info.get('DN_PE', DN_PE_DEFAULT),
                chi2_ndf=info.get('CHI2_NDF', -1.0),
            )
            return fr
    except ImportError:
        pass
    except Exception as e:
        print(f"WARNING: Cannot read {root_path}: {e}")

    return None


# =============================================================================
# DEMO / SYNTHETIC DATA
# =============================================================================

def generate_demo_acu_data(noise_level=0.02) -> ScanDataset:
    """
    Generate synthetic ACU scan data for testing plots.
    
    Models a realistic z-dependence:
    - LY is highest at center (~4300 PE/MeV)
    - Drops near boundaries due to solid angle + attenuation
    - Slight top-bottom asymmetry from chimney
    """
    from scan_config import ACU_Z_POSITIONS_MM
    
    ds = ScanDataset(system="ACU", source="Ge68", source_energy_mev=E_GE68_MEV)
    rng = np.random.default_rng(42)
    
    for z in ACU_Z_POSITIONS_MM:
        r = abs(z)
        r_norm = r / ACRYLIC_INNER_RADIUS_MM
        
        # Realistic LY model: parabolic decrease with boundary effects
        ly_base = 4300 * (1.0 - 0.15 * r_norm**2 - 0.08 * r_norm**4)
        # Slight top-bottom asymmetry (chimney effect)
        if z > 0:
            ly_base *= (1.0 - 0.02 * r_norm)
        
        ly = ly_base * (1.0 + rng.normal(0, noise_level))
        dn = DN_PE_DEFAULT
        
        mean_pe = ly * E_GE68_MEV + dn
        # Resolution model: σ/√(μ-DN) ≈ 3% for TAO
        sigma_pe = 0.03 * np.sqrt(mean_pe - dn) * (mean_pe - dn)**0.5
        # Slight degradation near boundary
        sigma_pe *= (1.0 + 0.1 * r_norm**2)
        
        resolution = sigma_pe / (mean_pe - dn) * 100  # percent
        
        fr = FitResult(
            system="ACU", source="Ge68", source_energy_mev=E_GE68_MEV,
            z_mm=z, r_mm=r,
            theta_deg=0.0 if z >= 0 else 180.0 if z < 0 else 90.0,
            mean_pe=mean_pe, mean_pe_err=mean_pe * 0.001,
            sigma_pe=sigma_pe, sigma_pe_err=sigma_pe * 0.01,
            resolution_pct=resolution, resolution_pct_err=resolution * 0.02,
            ly_pe_per_mev=ly, ly_pe_per_mev_err=ly * 0.002,
            dark_noise_pe=dn, chi2_ndf=0.8 + rng.normal(0, 0.3),
        )
        ds.add(fr)
    
    ds.compute_g()
    return ds


def generate_demo_cls_data(noise_level=0.02) -> ScanDataset:
    """
    Generate synthetic CLS scan data for testing plots.
    
    Models realistic off-axis light yield variation:
    - g(r,θ) decreases near boundaries
    - Slight θ-dependence from geometry (chimney at top, cable entries)
    """
    from scan_config import CLS_DESIGN_POSITIONS
    
    ds = ScanDataset(system="CLS", source="Cs137", source_energy_mev=E_CS137_MEV)
    rng = np.random.default_rng(123)
    
    for sp in CLS_DESIGN_POSITIONS:
        r_norm = sp.r_mm / ACRYLIC_INNER_RADIUS_MM
        
        # Realistic g(r,θ) model
        g_ideal = (1.0 - 0.12 * r_norm**2 - 0.06 * r_norm**4
                   - 0.03 * r_norm**2 * np.cos(np.deg2rad(sp.theta_deg)))
        
        ly_center = 4300.0
        ly = ly_center * g_ideal * (1.0 + rng.normal(0, noise_level))
        dn = DN_PE_DEFAULT
        
        mean_pe = ly * E_CS137_MEV + dn
        sigma_pe = 0.035 * np.sqrt(mean_pe - dn) * (mean_pe - dn)**0.5
        sigma_pe *= (1.0 + 0.15 * r_norm**2)
        
        resolution = sigma_pe / (mean_pe - dn) * 100 if (mean_pe - dn) > 0 else 0
        
        fr = FitResult(
            system="CLS", source="Cs137", source_energy_mev=E_CS137_MEV,
            z_mm=sp.z_mm, r_mm=sp.r_mm,
            theta_deg=sp.theta_deg, phi_deg=sp.phi_deg,
            mean_pe=mean_pe, mean_pe_err=mean_pe * 0.002,
            sigma_pe=sigma_pe, sigma_pe_err=sigma_pe * 0.02,
            resolution_pct=resolution, resolution_pct_err=resolution * 0.03,
            ly_pe_per_mev=ly, ly_pe_per_mev_err=ly * 0.003,
            dark_noise_pe=dn, chi2_ndf=0.9 + rng.normal(0, 0.2),
        )
        ds.add(fr)
    
    ds.compute_g()
    return ds
