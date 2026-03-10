#!/usr/bin/env python3
"""
scan_config.py  —  TAO ACU/CLS scan configuration and detector geometry

Defines:
  - TAO detector geometry constants (sphere radius, FV radius, etc.)
  - ACU scan positions: 44 z-axis positions using ⁶⁸Ge (1.022 MeV)
  - CLS scan positions: 77 off-axis positions using ¹³⁷Cs (0.662 MeV)
  - Run-number ↔ position mapping for real data

References:
  - arxiv:2204.03256  "Calibration Strategy of the JUNO-TAO Experiment"
  - arxiv:2005.08745  "TAO Conceptual Design Report"
  - TAOsw T25.7.1     RecQMLEAlg / RecChargeCenterAlg

Author: G. Ferrante (INFN-MiB / UniMiB)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

# =============================================================================
# DETECTOR GEOMETRY
# =============================================================================

ACRYLIC_INNER_RADIUS_MM  = 900.0     # inner radius of acrylic vessel [mm]
SIPM_RADIUS_MM           = 939.515   # SiPM shell radius [mm] (from QMLERec.h)
FV_RADIUS_MM             = 650.0     # fiducial volume cut: 25 cm from edge
                                      # i.e. 900 - 250 = 650 mm
DETECTOR_CENTER_MM       = np.array([0.0, 0.0, 0.0])

# Source energies [MeV]
E_GE68_MEV  = 1.022   # two 511 keV γ from positron annihilation
E_CS137_MEV = 0.662    # single 662 keV γ

# Nominal light yield
LY_NOMINAL_PE_PER_MEV = 4300.0

# Dark noise default (typical for Ge-68 runs)
DN_PE_DEFAULT = 134.0

# =============================================================================
# ACU SCAN POSITIONS
# =============================================================================
# ACU deploys ⁶⁸Ge along the central z-axis.
# Per arxiv:2204.03256 §4:
#   - every 100 mm for |z| ≤ 500 mm  → 11 positions (0, ±100, ..., ±500)
#   - every  50 mm for 500 < |z| ≤ 850 mm → 14 positions per side
# Plus boundary: ±850 mm.
# Total: 44 positions (including z=0).
#
# In TAOsw MC, ACU is simulated from z = -850 to +850 mm,
# but in real data the ACU only deploys downward (z ≤ 0 in detector coords).
# The mapping below uses the convention z > 0 = top (chimney side).

def _generate_acu_z_positions():
    """Generate the 44 ACU z positions in mm (sorted)."""
    positions = set()
    # Central region: every 100 mm
    for z in range(-500, 501, 100):
        positions.add(z)
    # Boundary region: every 50 mm, both sides
    for z in range(550, 851, 50):
        positions.add(z)
        positions.add(-z)
    return np.array(sorted(positions), dtype=float)

ACU_Z_POSITIONS_MM = _generate_acu_z_positions()  # shape (44,)
ACU_R_POSITIONS_MM = np.abs(ACU_Z_POSITIONS_MM)    # radius from center for ACU = |z|
ACU_THETA_DEG      = np.where(ACU_Z_POSITIONS_MM >= 0, 0.0, 180.0)  # θ = 0 top, 180 bottom
ACU_SOURCE         = "Ge68"
ACU_SOURCE_ENERGY  = E_GE68_MEV

# Compute (r, θ) for each ACU position in detector spherical coords
# For ACU on the z-axis: r = |z|, θ = 0° (top) or 180° (bottom), φ = undefined
def acu_positions_r_theta():
    """Return ACU positions as arrays (r_mm, theta_deg)."""
    r     = np.abs(ACU_Z_POSITIONS_MM)
    theta = np.where(ACU_Z_POSITIONS_MM >= 0, 0.0, 180.0)
    # Special case: z=0 → r=0, θ is arbitrary (set to 90)
    mask_center = (ACU_Z_POSITIONS_MM == 0)
    theta[mask_center] = 90.0  # convention: center is at θ=90
    return r, theta


# =============================================================================
# CLS SCAN POSITIONS
# =============================================================================
# CLS deploys ¹³⁷Cs on a cable loop in an off-axis half-plane.
# Per arxiv:2204.03256 §4: 77 positions (+ center overlap with ACU).
# The cable passes through two acrylic anchors on the vessel surface.
#
# CLS source position for the n=60 calibration point (used in get_spectrum.py):
CLS_CS137_SOURCE_POS_MM = np.array([-23.1093, -188.278, 37.3801])
#
# The full set of 77 CLS positions is typically stored in a configuration
# file from TAOsw or extracted from the ESD metadata. Below we provide
# the design positions from the MC (arxiv:2204.03256 Fig. 6a).
#
# In the (r, θ) plane, CLS covers a half-plane from anchor-to-anchor.
# The cable follows a specific path in the detector; φ is approximately
# constant along the cable (single half-plane), but there is a slight
# variation depending on anchor positions.

@dataclass
class ScanPoint:
    """A single calibration scan point."""
    index: int              # sequential index (0-based)
    r_mm: float             # radial distance from center [mm]
    theta_deg: float        # polar angle [degrees, 0=top]
    phi_deg: float          # azimuthal angle [degrees]
    z_mm: float             # z coordinate [mm]
    x_mm: float = 0.0      # x coordinate [mm]
    y_mm: float = 0.0      # y coordinate [mm]
    source: str = "Cs137"
    run_number: Optional[int] = None

    @property
    def r_norm(self):
        """Radius normalised to acrylic inner radius."""
        return self.r_mm / ACRYLIC_INNER_RADIUS_MM

    @property
    def theta_rad(self):
        return np.deg2rad(self.theta_deg)

    @property
    def phi_rad(self):
        return np.deg2rad(self.phi_deg)


def _generate_cls_design_positions():
    """
    Generate the 77 CLS design positions from the TAO calibration paper.
    
    The CLS cable path is parametrised in the (r, θ) plane.
    Anchor A is near the top (θ ~ 30°) and anchor B near the bottom (θ ~ 150°).
    The cable follows a curved path through the GdLS volume.
    
    These are the DESIGN (MC) positions. Real data positions may differ slightly
    and should be loaded from the run database or ESD metadata.
    
    Returns list of ScanPoint objects.
    """
    # Approximate CLS positions from the calibration paper (Fig. 6a).
    # These cover the (r, θ) half-plane with φ ≈ const (cable plane).
    # More calibration points where |∇g| is larger (near boundary).
    #
    # Format: (r_mm, theta_deg) — φ is approximately 270° (cable plane)
    # These are approximate; real positions come from run configuration.
    
    cable_phi_deg = 270.0  # approximate φ of CLS cable plane
    
    # Build representative positions along the cable path
    # The cable traces a path from anchor A (~top, θ≈30°) to anchor B (~bottom, θ≈150°)
    # passing through the interior at varying radii.
    cls_rt = []
    
    # Near top anchor: high r, small θ
    for r in [850, 800, 750, 700, 650]:
        cls_rt.append((r, 25.0 + (850 - r) * 0.06))
    
    # Descending through upper hemisphere
    for theta in np.arange(35, 90, 5):
        # r decreases as we move away from boundary toward center
        r = max(50, 850 - (theta - 25) * 8.5)
        cls_rt.append((r, theta))
    
    # Near equator: closest approach to center
    for theta in np.arange(80, 105, 3):
        r = max(50, 200 + abs(theta - 90) * 15)
        cls_rt.append((r, theta))
    
    # Descending through lower hemisphere
    for theta in np.arange(100, 160, 5):
        r = max(50, 850 - (155 - theta) * 8.5)
        cls_rt.append((r, theta))
    
    # Near bottom anchor: high r, large θ
    for r in [650, 700, 750, 800, 850]:
        cls_rt.append((r, 155.0 - (850 - r) * 0.06))
    
    # Deduplicate and trim to ~77 points
    seen = set()
    unique = []
    for (r, th) in cls_rt:
        key = (round(r, 0), round(th, 1))
        if key not in seen:
            seen.add(key)
            unique.append((r, th))
    
    # Trim or pad to exactly 77
    unique = unique[:77]
    while len(unique) < 77:
        # Add intermediate points
        idx = len(unique)
        r = 400 + (idx % 10) * 50
        th = 40 + idx * 1.5
        unique.append((r, min(th, 155)))
    
    points = []
    for i, (r, theta) in enumerate(unique):
        z = r * np.cos(np.deg2rad(theta))
        x = r * np.sin(np.deg2rad(theta)) * np.cos(np.deg2rad(cable_phi_deg))
        y = r * np.sin(np.deg2rad(theta)) * np.sin(np.deg2rad(cable_phi_deg))
        points.append(ScanPoint(
            index=i, r_mm=r, theta_deg=theta, phi_deg=cable_phi_deg,
            z_mm=z, x_mm=x, y_mm=y, source="Cs137"
        ))
    
    return points


CLS_DESIGN_POSITIONS = _generate_cls_design_positions()


# =============================================================================
# RUN ↔ POSITION MAPPING
# =============================================================================
# In real data, each calibration run corresponds to a specific scan position.
# This mapping is typically provided by the run database or an external CSV.
# Below is a placeholder structure; fill from your actual run list.

@dataclass
class RunPositionMap:
    """Maps run numbers to scan positions for a complete calibration campaign."""
    campaign_label: str
    acu_runs: Dict[int, float] = field(default_factory=dict)
        # run_number → z_mm
    cls_runs: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)
        # run_number → (r_mm, theta_deg, phi_deg)

    def get_acu_position(self, run: int):
        """Return (r_mm, theta_deg) for an ACU run."""
        z = self.acu_runs.get(run)
        if z is None:
            return None
        r = abs(z)
        theta = 0.0 if z >= 0 else 180.0
        if z == 0:
            theta = 90.0
        return r, theta

    def get_cls_position(self, run: int):
        """Return (r_mm, theta_deg, phi_deg) for a CLS run."""
        return self.cls_runs.get(run)


# Example: placeholder campaign (fill with real run numbers)
EXAMPLE_CAMPAIGN = RunPositionMap(
    campaign_label="2026_Jan_commissioning",
    acu_runs={
        # run_number: z_mm
        # 1295: 0.0,  # center
        # 1296: -100.0,
        # ...
    },
    cls_runs={
        # run_number: (r_mm, theta_deg, phi_deg)
        # 1344: (190.0, 100.0, 270.0),
        # ...
    },
)


# =============================================================================
# HELPER: Load positions from external CSV
# =============================================================================

def load_run_position_map(csv_path: str) -> RunPositionMap:
    """
    Load run-to-position mapping from a CSV file.
    
    Expected CSV format:
        run,system,z_mm,r_mm,theta_deg,phi_deg,source
        1295,ACU,0.0,0.0,90.0,0.0,Ge68
        1344,CLS,,190.0,100.0,270.0,Cs137
        ...
    """
    import csv
    rpm = RunPositionMap(campaign_label=csv_path)
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            run = int(row['run'])
            system = row['system'].strip().upper()
            if system == 'ACU':
                rpm.acu_runs[run] = float(row['z_mm'])
            elif system == 'CLS':
                rpm.cls_runs[run] = (
                    float(row['r_mm']),
                    float(row['theta_deg']),
                    float(row['phi_deg']),
                )
    return rpm
