#!/usr/bin/env python3
"""
merge_charge.py - Merge per-file ADC histogram ROOT files for gain calibration.

Merges CHARGE_single_RUN{N}_NNN.root files produced by extract_charge_calib.py
into a single CHARGE_RUN{N}_merged.root file.  Two histogram tiers are merged:
  TIER 1  H_adcraw_*    — all non-flasher events
  TIER 2  H_adcClean_*  — events that passed the full veto hierarchy

No spatial cut: extract_charge_calib.py works on RTRAW files which have no
reconstructed vertex position; spatial selection is not possible here and is
not needed for gain calibration.
"""

import sys
import os
import glob

try:
    import ROOT
except ImportError:
    print("ERROR: ROOT not available!")
    sys.exit(1)

ROOT.gROOT.SetBatch(True)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        return it

DEFAULT_AFTER_MU    = 1000e3
DEFAULT_AFTER_PULSE = 5e3


def merge_charge_data(run_number, inputdir, outputdir):
    """Merge ADC histograms (TIER 1 raw + TIER 2 clean) for one run."""

    pattern     = os.path.join(inputdir, f"CHARGE_single_RUN{run_number}_*.root")
    input_files = sorted(f for f in glob.glob(pattern)
                         if "_spatial_cut.root" not in f)

    if not input_files:
        print(f"ERROR: No input files found matching: {pattern}")
        sys.exit(1)

    print("=" * 60)
    print(f"Merging charge data for RUN {run_number}")
    print("=" * 60)
    print(f"Found {len(input_files)} input files")
    print(f"First : {os.path.basename(input_files[0])}")
    print(f"Last  : {os.path.basename(input_files[-1])}")
    print()

    # ── Read veto parameters from first file ─────────────────────────────────
    veto_params = {}
    f0 = ROOT.TFile.Open(input_files[0], "READ")
    if f0 and not f0.IsZombie():
        vi = f0.Get("veto_info")
        if vi:
            for item in vi.GetTitle().split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    veto_params[k] = v
        f0.Close()

    try:
        AFTER_MU    = float(veto_params.get("AFTER_MU",    DEFAULT_AFTER_MU))
        AFTER_PULSE = float(veto_params.get("AFTER_PULSE", DEFAULT_AFTER_PULSE))
    except (ValueError, TypeError):
        AFTER_MU, AFTER_PULSE = DEFAULT_AFTER_MU, DEFAULT_AFTER_PULSE
        print(f"WARNING: Could not parse timing windows from metadata, using defaults.")

    print(f"Veto timing (from extraction metadata):")
    print(f"  AFTER_MU    : {AFTER_MU/1e3:.0f} µs")
    print(f"  AFTER_PULSE : {AFTER_PULSE/1e3:.1f} µs")
    print()

    NCHANNELS = 8048

    # ── Auto-detect histogram limits from first input file ────────────────────
    # Hardcoding XMAX here caused a mismatch (50000 vs 60000 from extraction).
    # Instead we read the limits from the actual data so merging never fails.
    NBINS = 500; XMIN = 0.0; XMAX = 60000.0   # safe defaults
    try:
        f_probe = ROOT.TFile.Open(input_files[0], "READ")
        if f_probe and not f_probe.IsZombie():
            h_probe = f_probe.Get("H_adcraw_0")
            if h_probe:
                NBINS = h_probe.GetNbinsX()
                XMIN  = h_probe.GetXaxis().GetXmin()
                XMAX  = h_probe.GetXaxis().GetXmax()
            f_probe.Close()
    except Exception:
        pass
    print(f"Histogram limits (auto-detected): NBINS={NBINS}, XMIN={XMIN}, XMAX={XMAX}")

    # ── Discover all channel IDs (including OOR) ──────────────────────────────
    print(f"Discovering channel IDs across {len(input_files)} files…")
    all_channel_ids = set(range(NCHANNELS))
    for fpath in tqdm(input_files, desc="Scanning"):
        try:
            f = ROOT.TFile.Open(fpath, "READ")
            if not f or f.IsZombie():
                continue
            for key in f.GetListOfKeys():
                name = key.GetName()
                if name.startswith("H_adcraw_") or name.startswith("H_adcClean_"):
                    try:
                        all_channel_ids.add(int(name.split("_")[-1]))
                    except ValueError:
                        pass
            f.Close()
        except Exception as e:
            print(f"  Error scanning {fpath}: {e}")

    standard_ch = [c for c in all_channel_ids if 0 <= c < NCHANNELS]
    oor_ch      = [c for c in all_channel_ids if c < 0 or c >= NCHANNELS]
    print(f"  Standard channels (0–{NCHANNELS-1}) : {len(standard_ch)}")
    print(f"  Out-of-range channels               : {len(oor_ch)}")
    print()

    # ── Initialise merged histograms ──────────────────────────────────────────
    print(f"Creating {NCHANNELS} merged histograms (raw + clean)…")
    hraw   = [ROOT.TH1F(f"H_adcraw_{c}",   f"Merged ADC RAW {c}   RUN{run_number}",
                        NBINS, XMIN, XMAX) for c in range(NCHANNELS)]
    hclean = [ROOT.TH1F(f"H_adcClean_{c}", f"Merged ADC Clean {c} RUN{run_number}",
                        NBINS, XMIN, XMAX) for c in range(NCHANNELS)]
    for h in hraw + hclean:
        h.SetDirectory(0)

    hraw_oor   = {}
    hclean_oor = {}
    for c in oor_ch:
        hr = ROOT.TH1F(f"H_adcraw_{c}",   f"Merged ADC RAW {c} (OOR)",   NBINS, XMIN, XMAX); hr.SetDirectory(0)
        hc = ROOT.TH1F(f"H_adcClean_{c}", f"Merged ADC Clean {c} (OOR)", NBINS, XMIN, XMAX); hc.SetDirectory(0)
        hraw_oor[c] = hr; hclean_oor[c] = hc

    # ── Merge ─────────────────────────────────────────────────────────────────
    n_muons = n_after_muon = n_after_pulse = n_outlier = n_clean = 0

    print(f"Merging {len(input_files)} files…")
    for fpath in tqdm(input_files, desc="Merging"):
        try:
            f = ROOT.TFile.Open(fpath, "READ")
            if not f or f.IsZombie():
                continue

            for c in range(NCHANNELS):
                h = f.Get(f"H_adcraw_{c}")
                if h: hraw[c].Add(h)
                h = f.Get(f"H_adcClean_{c}")
                if h: hclean[c].Add(h)

            for c in oor_ch:
                h = f.Get(f"H_adcraw_{c}")
                if h: hraw_oor[c].Add(h)
                h = f.Get(f"H_adcClean_{c}")
                if h: hclean_oor[c].Add(h)

            # Accumulate veto counts from metadata
            vi = f.Get("veto_info")
            if vi:
                info = dict(item.split("=", 1) for item in vi.GetTitle().split(";") if "=" in item)
                try: n_muons      += int(info.get("N_MUONS",       0))
                except ValueError: pass
                try: n_after_muon += int(info.get("N_AFTER_MUON",  0))
                except ValueError: pass
                try: n_after_pulse+= int(info.get("N_AFTER_PULSE", 0))
                except ValueError: pass
                try: n_outlier    += int(info.get("N_OUTLIER",     0))
                except ValueError: pass
                try: n_clean      += int(info.get("N_CLEAN",       0))
                except ValueError: pass

            f.Close()
        except Exception as e:
            print(f"  Error merging {fpath}: {e}")

    print("\n-- END OF MERGE LOOP --\n")

    # ── Write output file ─────────────────────────────────────────────────────
    os.makedirs(outputdir, exist_ok=True)
    outpath = os.path.join(outputdir, f"CHARGE_RUN{run_number}_merged.root")
    print(f"Writing {outpath}…")
    fout = ROOT.TFile(outpath, "RECREATE")
    fout.cd()

    n_raw_nonempty = n_clean_nonempty = 0
    for c in tqdm(range(NCHANNELS), desc="Writing raw"):
        if hraw[c].GetEntries() > 0: n_raw_nonempty += 1
        hraw[c].Write()
    for c in tqdm(range(NCHANNELS), desc="Writing clean"):
        if hclean[c].GetEntries() > 0: n_clean_nonempty += 1
        hclean[c].Write()
    for c, h in hraw_oor.items():   h.Write()
    for c, h in hclean_oor.items(): h.Write()

    # Metadata: propagate veto parameters + merged counts
    veto_info_str = (
        f"MUON_THRESHOLD_CD={veto_params.get('MUON_THRESHOLD_CD', 0)};"
        f"MUON_THRESHOLD_WT={veto_params.get('MUON_THRESHOLD_WT', 0)};"
        f"MUON_THRESHOLD_TVT={veto_params.get('MUON_THRESHOLD_TVT', 0)};"
        f"AFTER_MU={AFTER_MU};"
        f"AFTER_PULSE={AFTER_PULSE};"
        f"MAX_TOTAL_ADC={veto_params.get('MAX_TOTAL_ADC', 0)};"
        f"MAX_ADC_PER_CHANNEL={veto_params.get('MAX_ADC_PER_CHANNEL', 0)};"
        f"ADC_HIT_MAX={veto_params.get('ADC_HIT_MAX', 0)};"
        f"TDC_HIT_MIN={veto_params.get('TDC_HIT_MIN', 'None')};"
        f"TDC_HIT_MAX={veto_params.get('TDC_HIT_MAX', 'None')};"
        f"MIN_NHIT={veto_params.get('MIN_NHIT', 0)};"
        f"MAX_NHIT={veto_params.get('MAX_NHIT', 0)};"
        f"N_MUONS={n_muons};"
        f"N_AFTER_MUON={n_after_muon};"
        f"N_AFTER_PULSE={n_after_pulse};"
        f"N_OUTLIER={n_outlier};"
        f"N_CLEAN={n_clean};"
        f"HAS_WT={veto_params.get('HAS_WT', 0)};"
        f"HAS_TVT={veto_params.get('HAS_TVT', 0)};"
        f"SPATIAL_CUT_ENABLED=0"
    )
    ROOT.TNamed("veto_info", veto_info_str).Write("veto_info", ROOT.TObject.kOverwrite)
    if oor_ch:
        oor_list = ",".join(str(c) for c in sorted(oor_ch)[:100])
        ROOT.TNamed("merged_out_of_range_info",
                    f"OOR_COUNT={len(oor_ch)};OOR_CHANNELS={oor_list}").Write(
                    "merged_out_of_range_info", ROOT.TObject.kOverwrite)

    fout.Write(); fout.Close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)
    print(f"Non-empty channels — raw:  {n_raw_nonempty}   clean: {n_clean_nonempty}")
    print(f"Merged veto statistics:")
    print(f"  Muon events         : {n_muons}")
    print(f"  After-muon vetoed   : {n_after_muon}")
    print(f"  After-pulse vetoed  : {n_after_pulse}")
    print(f"  Outlier vetoed      : {n_outlier}")
    print(f"  Clean events        : {n_clean}")
    print(f"Output: {outpath}")
    print("=" * 60)
    return outpath


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python merge_charge.py <run_number> <inputdir> <outputdir>")
        print()
        print("Example:")
        print("  python merge_charge.py 1295 /path/to/single_charge /path/to/merged_charge")
        sys.exit(1)

    run_number = sys.argv[1]
    inputdir   = sys.argv[2]
    outputdir  = sys.argv[3]

    if not os.path.isdir(inputdir):
        print(f"ERROR: Input directory does not exist: {inputdir}")
        sys.exit(1)

    merge_charge_data(run_number, inputdir, outputdir)
