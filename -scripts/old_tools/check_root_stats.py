#!/usr/bin/env python3
import sys
import ROOT

if len(sys.argv) < 2:
    print("Usage: python check_root_stats.py <spectrum_file.root>")
    sys.exit(1)

rootfile = sys.argv[1]

print("="*60)
print(f"Checking ROOT file: {rootfile}")
print("="*60)

f = ROOT.TFile.Open(rootfile, "READ")
if not f or f.IsZombie():
    print(f"ERROR: Cannot open {rootfile}")
    sys.exit(1)

# Get histograms
h_NPE = f.Get("h_NPE")
h_PEdiscrete = f.Get("h_PEdiscrete")
h_nHit = f.Get("h_nHit")

print("\nHistogram Statistics:")
print("-"*60)

if h_NPE:
    print(f"h_NPE:")
    print(f"  Entries:  {h_NPE.GetEntries():.0f}")
    print(f"  Integral: {h_NPE.Integral():.0f}")
    print(f"  Mean:     {h_NPE.GetMean():.1f}")
    print(f"  RMS:      {h_NPE.GetRMS():.1f}")
else:
    print("h_NPE: NOT FOUND")

print()

if h_PEdiscrete:
    print(f"h_PEdiscrete:")
    print(f"  Entries:  {h_PEdiscrete.GetEntries():.0f}")
    print(f"  Integral: {h_PEdiscrete.Integral():.0f}")
    print(f"  Mean:     {h_PEdiscrete.GetMean():.1f}")
    print(f"  RMS:      {h_PEdiscrete.GetRMS():.1f}")
else:
    print("h_PEdiscrete: NOT FOUND")

print()

if h_nHit:
    print(f"h_nHit:")
    print(f"  Entries:  {h_nHit.GetEntries():.0f}")
    print(f"  Integral: {h_nHit.Integral():.0f}")
    print(f"  Mean:     {h_nHit.GetMean():.1f}")
    print(f"  RMS:      {h_nHit.GetRMS():.1f}")
else:
    print("h_nHit: NOT FOUND")

print()

# Check energy_info
energy_info = f.Get("energy_info")
if energy_info:
    print("energy_info TNamed:")
    print("-"*60)
    infostr = energy_info.GetTitle()
    for item in infostr.split("|"):
        if "=" in item:
            key, value = item.split("=", 1)
            print(f"  {key.strip()}: {value.strip()}")
else:
    print("energy_info: NOT FOUND")

f.Close()

print("="*60)
