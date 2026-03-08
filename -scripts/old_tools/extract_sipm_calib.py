#!/usr/bin/env python3
"""
extract_sipm_calib.py - Extract SiPM calibration parameters from ROOT file

Extracts gain, mean0, gain_dyn, mean0_dyn, timeoffset, baseline, and dcr
for all 8048 channels and saves them in columnar text format.
"""

import sys
import os
import argparse

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT (PyROOT) not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

def extract_calibration_parameters(root_file_path, output_txt_path):
    """Extract calibration parameters from ROOT file to text file."""
    
    print("=" * 70)
    print("EXTRACT SIPM CALIBRATION PARAMETERS")
    print("=" * 70)
    print(f"Input ROOT file: {root_file_path}")
    print(f"Output TXT file: {output_txt_path}")
    print()
    
    # Open ROOT file
    fin = ROOT.TFile.Open(root_file_path, "READ")
    if not fin or fin.IsZombie():
        print(f"ERROR: Cannot open ROOT file: {root_file_path}")
        return 1
    
    # Get TTree
    tree = fin.Get("myevt")
    if not tree or not tree.InheritsFrom("TTree"):
        print("ERROR: Cannot find 'myevt' tree in ROOT file!")
        fin.Close()
        return 1
    
    n_entries = tree.GetEntries()
    print(f"Found tree 'myevt' with {n_entries} entry(ies)")
    
    if n_entries == 0:
        print("ERROR: Tree is empty!")
        fin.Close()
        return 1
    
    # Get the single entry
    tree.GetEntry(0)
    
    # Access branches (arrays of 8048 elements)
    branches = ['gain', 'mean0', 'gain_dyn', 'mean0_dyn', 'timeoffset', 'baseline', 'dcr']
    
    # Get array size from first branch
    n_channels = len(getattr(tree, branches[0]))
    print(f"Number of channels: {n_channels}")
    print(f"Branches: {', '.join(branches)}")
    print()
    
    # Extract data from all branches
    data = {}
    for branch_name in branches:
        branch_data = getattr(tree, branch_name)
        data[branch_name] = [branch_data[i] for i in range(n_channels)]
        print(f" Extracted {branch_name}: {n_channels} values")
    
    fin.Close()
    
    # Write to text file
    print()
    print(f"Writing to: {output_txt_path}")
    
    with open(output_txt_path, 'w') as fout:
        # Write header
        header = "# SiPM Calibration Parameters\n"
        header += f"# Source: {os.path.basename(root_file_path)}\n"
        header += "# Columns: channel_id  gain  mean0  gain_dyn  mean0_dyn  timeoffset  baseline  dcr\n"
        fout.write(header)
        
        # Write data (one row per channel)
        for ch in range(n_channels):
            line = f"{ch:5d}"
            for branch_name in branches:
                value = data[branch_name][ch]
                line += f"  {value:12.6f}"
            line += "\n"
            fout.write(line)
    
    print(f"Successfully wrote {n_channels} channels to {output_txt_path}")
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Channels extracted: {n_channels}")
    print(f"Parameters per channel: {len(branches)}")
    print(f"Output file: {output_txt_path}")
    print("=" * 70)
    print()
    print("SUCCESS")
    
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Extract SiPM calibration parameters from ROOT file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract calibration parameters
  python extract_sipm_calib.py input.root output.txt
  
  # Using the CVMFS file directly
  python extract_sipm_calib.py /cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Calibration/Calib.CD.SiPM.Param/TAO_SiPM_calib_par_1768003200.root sipm_calib.txt
"""
    )
    
    parser.add_argument('input_root', help='Input ROOT file with calibration parameters')
    parser.add_argument('output_txt', help='Output text file (columnar format)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_root):
        print(f"ERROR: Input file not found: {args.input_root}")
        return 1
    
    return extract_calibration_parameters(args.input_root, args.output_txt)

if __name__ == "__main__":
    sys.exit(main())
