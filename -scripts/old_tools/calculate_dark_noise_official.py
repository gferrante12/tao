#!/usr/bin/env python3

"""
Calculate Dark Noise Official (DN_official) from SiPM calibration parameters

This script:
1. Reads DCR values from sipm_calib_parameters.txt (last column)
2. Filters out channels with DCR = 0 or absurdly high gain values (> 5e5)
3. Sums DCR values for all valid channels
4. Multiplies by 250e-9 to get DN_official
5. Rescales based on number of good channels in RUN1157
"""

import numpy as np
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description='Calculate DN_official from SiPM calibration parameters')
    parser.add_argument('--calib-file', type=str,
                        default='/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/calibration_results/sipm_calib_parameters.txt',
                        help='Path to SiPM calibration parameters file')
    parser.add_argument('--run1157-file', type=str,
                        default='/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/calibration_results/1157/root_tspectrum_good_RUN1157.txt',
                        help='Path to RUN1157 good channels file')
    parser.add_argument('--output', type=str, default=None,
                        help='Output file to save results (optional)')
    parser.add_argument('--max-gain', type=float, default=5e5,
                        help='Maximum acceptable gain value (default: 5e5)')
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.calib_file):
        print(f"ERROR: Calibration file not found: {args.calib_file}")
        return 1
    
    if not os.path.exists(args.run1157_file):
        print(f"ERROR: RUN1157 file not found: {args.run1157_file}")
        return 1
    
    print("="*60)
    print("Dark Noise Official Calculation")
    print("="*60)
    print()
    
    # Read SiPM calibration parameters
    print(f"Reading calibration file: {args.calib_file}")
    print(f"Maximum acceptable gain: {args.max_gain:.2e}")
    
    channels_calib = []
    dcr_values = []
    n_skipped_dcr = 0
    n_skipped_gain = 0
    
    with open(args.calib_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) >= 8:
                try:
                    channel = int(parts[0])
                    gain = float(parts[1])  # Gain is in column 1
                    dcr = float(parts[7])   # Last column is DCR
                    
                    # Skip channels with DCR = 0
                    if dcr == 0.0:
                        n_skipped_dcr += 1
                        continue
                    
                    # Skip channels with absurdly high gain values
                    if gain > args.max_gain:
                        n_skipped_gain += 1
                        print(f"  Skipping channel {channel}: gain = {gain:.2e} (> {args.max_gain:.2e})")
                        continue
                    
                    channels_calib.append(channel)
                    dcr_values.append(dcr)
                    
                except ValueError:
                    continue
    
    # Read RUN1157 good channels
    print(f"\nReading RUN1157 file: {args.run1157_file}")
    channels_run1157 = []
    with open(args.run1157_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('Channel') or line.startswith('-'):
                continue
            
            parts = line.split()
            if len(parts) > 0:
                try:
                    channel = int(parts[0])
                    channels_run1157.append(channel)
                except ValueError:
                    continue
    
    print()
    print("-"*60)
    print("Channel Statistics")
    print("-"*60)
    print(f"Channels skipped (DCR = 0): {n_skipped_dcr}")
    print(f"Channels skipped (gain > {args.max_gain:.2e}): {n_skipped_gain}")
    print(f"Channels in sipm_calib_parameters.txt (valid): {len(channels_calib)}")
    print(f"Channels in root_tspectrum_good_RUN1157.txt: {len(channels_run1157)}")
    print()
    
    if len(channels_calib) == 0:
        print("ERROR: No valid channels found after filtering!")
        return 1
    
    # Calculate DN_official
    dcr_sum = np.sum(dcr_values)
    print(f"Sum of DCR values: {dcr_sum:.2f} Hz")
    print()
    
    # DN_official = sum(DCR) * 250e-9
    DN_official_raw = dcr_sum * 250e-9
    
    print("-"*60)
    print("Dark Noise Calculation")
    print("-"*60)
    print(f"DN_official (raw) = {DN_official_raw:.6e}")
    print(f"                  = {DN_official_raw:.6f}")
    print()
    
    # Rescale by channel ratio
    rescale_factor = len(channels_run1157) / len(channels_calib)
    DN_official_rescaled = DN_official_raw * rescale_factor
    
    print(f"Rescaling factor = {len(channels_run1157)}/{len(channels_calib)} = {rescale_factor:.6f}")
    print(f"DN_official (rescaled) = {DN_official_rescaled:.6e}")
    print(f"                       = {DN_official_rescaled:.6f}")
    print()
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write("# Dark Noise Official Calculation Results\n")
            f.write(f"# Calibration file: {args.calib_file}\n")
            f.write(f"# RUN1157 file: {args.run1157_file}\n")
            f.write(f"# Max gain threshold: {args.max_gain:.2e}\n")
            f.write("\n")
            f.write(f"N_channels_calib = {len(channels_calib)}\n")
            f.write(f"N_channels_RUN1157 = {len(channels_run1157)}\n")
            f.write(f"N_skipped_dcr_zero = {n_skipped_dcr}\n")
            f.write(f"N_skipped_high_gain = {n_skipped_gain}\n")
            f.write(f"DCR_sum_Hz = {dcr_sum:.2f}\n")
            f.write(f"DN_official_raw = {DN_official_raw:.6e}\n")
            f.write(f"DN_official_rescaled = {DN_official_rescaled:.6e}\n")
            f.write(f"rescale_factor = {rescale_factor:.6f}\n")
        
        print(f"Results saved to: {args.output}")
        print()
    
    print("="*60)
    print("Calculation complete!")
    print("="*60)
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
