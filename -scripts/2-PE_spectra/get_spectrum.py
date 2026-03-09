#!/usr/bin/env python3
"""
get_spectrum.py - UPDATED VERSION with synchronized TDC window

CHANGES FROM ORIGINAL:
  1. TDC window changed from [200, 450] to [240, 440] ns (aligned with CALIB2)
  2. Import centralized parameters from veto_params.py

This file shows the key sections that need to be modified. 
Apply these changes to your existing get_spectrum.py.
"""

# =============================================================================
# CHANGE 1: Update the constants section (around line 50-60)
# =============================================================================

# BEFORE (OLD):
# TDC_CUT_LOW = 200.0   # ns
# TDC_CUT_UP = 450.0    # ns
# TDC_WINDOW_ANALYSIS = TDC_CUT_UP - TDC_CUT_LOW  # 250 ns

# AFTER (NEW):
TDC_CUT_LOW = 240.0   # ns  — aligned with CALIB2 window in extract_charge_calib.py
TDC_CUT_UP  = 440.0   # ns  — aligned with CALIB2 window in extract_charge_calib.py
TDC_WINDOW_ANALYSIS = TDC_CUT_UP - TDC_CUT_LOW  # 200 ns

# =============================================================================
# CHANGE 2: (Optional) Import from veto_params.py instead of hardcoding
# =============================================================================

# Add at top of file:
# try:
#     from veto_params import TDC_WINDOW, PARAMS_CALIB2
#     TDC_CUT_LOW = TDC_WINDOW.min_ns
#     TDC_CUT_UP = TDC_WINDOW.max_ns
#     TDC_WINDOW_ANALYSIS = TDC_WINDOW.width_ns
# except ImportError:
#     # Fallback to hardcoded values
#     TDC_CUT_LOW = 240.0
#     TDC_CUT_UP = 440.0
#     TDC_WINDOW_ANALYSIS = 200.0

# =============================================================================
# SUMMARY OF IMPACT:
# =============================================================================
#
# The TDC window change affects:
#   1. Dark noise calculation (narrower window = less dark noise)
#   2. Hit selection in RTRAW processing
#   3. Resolution calculation (same denominator formula)
#
# Old window [200, 450] = 250 ns:
#   - DN_TOT = Σ DCR_ch × 250e-9 s
#   - Includes more pre-trigger noise (200-240 ns)
#   - Includes more late hits (440-450 ns)
#
# New window [240, 440] = 200 ns:
#   - DN_TOT = Σ DCR_ch × 200e-9 s  (20% less dark noise)
#   - Better alignment with Ge-68 prompt scintillation
#   - Consistent with extract_charge_calib.py CALIB2 mode
#
# =============================================================================
