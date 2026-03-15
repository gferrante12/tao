#!/usr/bin/env python3
"""
merge_spectrum.py - Merge individual spectrum ROOT files into combined file

Merges histograms from per-file ROOT outputs of get_spectrum.py and
re-fits the combined statistics using fit_peaks_ge68.py / fit_peaks_cs137.py
via spectrum_utils.fit_source().

Two-stage fit:
  Stage 1 : Gaussian + pol3 (robust, data-driven peak finding)
  Stage 2 : Full physics model (source-specific)
  Both results are stored in the energy_info TNamed.

After merging, a plain-text summary table is written:
  {outfile_stem}_fit_results.txt

  Columns: file | mean [PE] | sigma [PE] | DN [PE] | resolution (mu/sigma) | corr_resolution (sigma/(mu-DN))
  Row 0  : merged spectrum
  Rows 1+: one row per individual input file (fit performed on each file's histogram)

Usage:
  python merge_spectrum.py "spectrum_RUN1055-*.root" spectrum_RUN1055-MERGED.root --source-name Ge68
  python merge_spectrum.py "spectrum_RUN1344-*.root" spectrum_RUN1344-MERGED.root --source-name Cs137
  python merge_spectrum.py "spectrum_RUN1345-*.root" spectrum_RUN1345-MERGED.root   # no source = no fit
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

try:
    from spectrum_utils import resolve_source, SOURCES, fit_source
except ImportError as _e:
    print(f"ERROR: Cannot import spectrum_utils: {_e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Summary table helpers  (internal energy_info representation)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_row(label, result):
    if result:
        mean_s  = f"{result['peak']:.1f} +/- {result['peak_error']:.1f}"
        sigma_s = f"{result['sigma']:.1f} +/- {result['sigma_error']:.1f}"
        res_tot = result['resolution_error'] * 100.0
        res_stat= result.get('resolution_error_stat', res_tot / 100.0) * 100.0
        res_sys = result.get('resolution_error_sys', 0.0) * 100.0
        res_s   = (f"{result['resolution']*100:.3f} +/- {res_tot:.3f} % "
                   f"(stat {res_stat:.3f}  sys {res_sys:.3f})")
        chi_s   = f"{result.get('chi2ndf', float('nan')):.2f}"
        method  = result.get('method', '')
        return f"{label:<20} {mean_s:<26} {sigma_s:<26} {res_s:<50} {chi_s:<10} {method:<10} {'PASS':<6}"
    return f"{label:<20} {'---':<26} {'---':<26} {'---':<50} {'---':<10} {'---':<10} {'FAIL':<6}"


def _append_result(parts, prefix, result):
    if result:
        parts += [
            f"RES_{prefix}={result['resolution']:.6f}",
            f"RES_{prefix}_ERR={result['resolution_error']:.6f}",
            f"RES_{prefix}_ERR_STAT={result.get('resolution_error_stat', result['resolution_error']):.6f}",
            f"RES_{prefix}_ERR_SYS={result.get('resolution_error_sys', 0.0):.6f}",
            f"MEAN_{prefix}={result['peak']:.6f}",
            f"MEAN_{prefix}_ERR={result['peak_error']:.6f}",
            f"MEAN_{prefix}_ERR_STAT={result.get('peak_error_stat', result['peak_error']):.6f}",
            f"MEAN_{prefix}_ERR_SYS={result.get('peak_error_sys', 0.0):.6f}",
            f"SIGMA_{prefix}={result['sigma']:.6f}",
            f"SIGMA_{prefix}_ERR={result['sigma_error']:.6f}",
            f"SIGMA_{prefix}_ERR_STAT={result.get('sigma_error_stat', result['sigma_error']):.6f}",
            f"SIGMA_{prefix}_ERR_SYS={result.get('sigma_error_sys', 0.0):.6f}",
            f"CHI2NDF_{prefix}={result.get('chi2ndf', -1):.4f}",
            f"METHOD_{prefix}={result.get('method', 'unknown')}",
        ]
    else:
        for key in ('RES', 'MEAN', 'SIGMA'):
            parts += [f"{key}_{prefix}=-1", f"{key}_{prefix}_ERR=0",
                      f"{key}_{prefix}_ERR_STAT=0", f"{key}_{prefix}_ERR_SYS=0"]
        parts += [f"CHI2NDF_{prefix}=-1", f"METHOD_{prefix}=none"]


# ─────────────────────────────────────────────────────────────────────────────
# Best result picker
# ─────────────────────────────────────────────────────────────────────────────

def _best(simple, physics):
    """Return physics result if available, else simple."""
    return physics if physics else simple


def _extract_dn(root_file):
    """Read dark_noise_pe value from a ROOT file's TNamed or return 0."""
    fin = ROOT.TFile.Open(root_file, "READ")
    if not fin or fin.IsZombie():
        return 0.0
    dn = 0.0
    dn_named = fin.Get("dark_noise_pe")
    if dn_named:
        try:
            dn = float(dn_named.GetTitle())
        except (ValueError, TypeError):
            pass
    fin.Close()
    return dn


# ─────────────────────────────────────────────────────────────────────────────
# Fit result → table row dict
# ─────────────────────────────────────────────────────────────────────────────

def _result_to_row_dict(label, result, dark_noise_pe):
    """
    Build a row dict for the txt summary table.

    Columns:
      file                  : label (filename or 'MERGED')
      mean_PE               : fitted peak mean [PE]
      sigma_PE              : fitted sigma [PE]
      dark_noise_PE         : dark noise [PE]
      resolution            : mu / sigma  (SNR)
      corrected_resolution  : sigma / (mu - DN)
    """
    if result is None:
        return dict(file=label, mean_PE='---', sigma_PE='---',
                    dark_noise_PE=f'{dark_noise_pe:.4f}',
                    resolution='---', corrected_resolution='---',
                    chi2ndf='---', method='FAILED')

    mu  = result.get('peak',  float('nan'))
    sig = result.get('sigma', float('nan'))
    dn  = dark_noise_pe

    # resolution = mu / sigma  (as requested)
    res = mu / sig if sig > 0 else float('nan')

    # corrected resolution = sigma / (mu - DN)
    denom = mu - dn
    corr_res = sig / denom if denom > 0 else float('nan')

    chi2 = result.get('chi2ndf', float('nan'))
    meth = result.get('method', '')

    return dict(
        file=label,
        mean_PE=f"{mu:.3f}",
        sigma_PE=f"{sig:.3f}",
        dark_noise_PE=f"{dn:.4f}",
        resolution=f"{res:.5f}" if np.isfinite(res) else '---',
        corrected_resolution=f"{corr_res:.5f}" if np.isfinite(corr_res) else '---',
        chi2ndf=f"{chi2:.3f}" if np.isfinite(chi2) else '---',
        method=meth,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Write txt summary table
# ─────────────────────────────────────────────────────────────────────────────

def _write_txt_table(txt_path, rows, source_name, method_label="PEcontin"):
    """
    Write a plain-text table with fit results.

    Row 0   : merged spectrum
    Rows 1+ : individual input files

    Columns: file | mean [PE] | sigma [PE] | DN [PE] | resolution (mu/sigma) | corr_resolution (sigma/(mu-DN))
    """
    COL_W = [40, 14, 14, 14, 18, 22, 12, 20]
    COLS  = ['file', 'mean_PE', 'sigma_PE', 'dark_noise_PE',
             'resolution', 'corrected_resolution', 'chi2ndf', 'method']
    HDR   = ['file / source', 'mean [PE]', 'sigma [PE]', 'DN [PE]',
             'res (mu/sigma)', 'corr.res (sig/(mu-DN))', 'chi2/ndf', 'fit method']
    SEP   = '-' * sum(COL_W) + '\n'

    with open(txt_path, 'w') as fout:
        fout.write(f"# TAO PE Spectrum Fit Results\n")
        fout.write(f"# Method: {method_label}   Source: {source_name or 'none'}\n")
        fout.write(f"# resolution         = mu / sigma\n")
        fout.write(f"# corr. resolution   = sigma / (mu - dark_noise)\n")
        fout.write("#\n")
        fout.write(SEP)
        # header row
        hdr_line = ''.join(h.ljust(COL_W[i]) for i, h in enumerate(HDR)) + '\n'
        fout.write(hdr_line)
        fout.write(SEP)
        for row in rows:
            line = ''.join(str(row.get(c, '')).ljust(COL_W[i])
                           for i, c in enumerate(COLS)) + '\n'
            fout.write(line)
        fout.write(SEP)

    print(f"  Fit results table written: {txt_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Fit a single file's histograms
# ─────────────────────────────────────────────────────────────────────────────

def _fit_single_file(infile, source_name, dark_noise_pe):
    """
    Open infile, fit h_PEcontin, return (label, result_dict, dn).
    Returns (label, None, dn) on failure.
    """
    label = os.path.basename(infile)
    fin   = ROOT.TFile.Open(infile, "READ")
    if not fin or fin.IsZombie():
        return label, None, dark_noise_pe

    # Try to get per-file dark noise
    dn_named = fin.Get("dark_noise_pe")
    if dn_named:
        try:
            dn = float(dn_named.GetTitle())
        except (ValueError, TypeError):
            dn = dark_noise_pe
    else:
        dn = dark_noise_pe

    h_cont = fin.Get("h_PEcontin")
    if not h_cont or h_cont.GetEntries() < 50 or source_name is None:
        fin.Close()
        return label, None, dn

    # Clone so we can close the file
    h_clone = h_cont.Clone(f"h_clone_{abs(hash(infile))}")
    h_clone.SetDirectory(0)
    fin.Close()

    try:
        simple, physics = fit_source(h_clone, source_name, dn,
                                     method_name="PEcontin_single")
    except Exception as exc:
        print(f"  WARNING: fit failed for {label}: {exc}")
        simple, physics = None, None

    h_clone.Delete()
    result = _best(simple, physics)
    return label, result, dn


# ─────────────────────────────────────────────────────────────────────────────
# Main merge function
# ─────────────────────────────────────────────────────────────────────────────

def merge_spectrum_files(input_pattern, outfile, source_name=None, dark_noise_pe=0.0):
    print("=" * 70)
    print("MERGE_SPECTRUM - Combine Individual ROOT Files")
    print("=" * 70)

    source_energy_mev, source_desc = resolve_source(source_name)
    if source_energy_mev is None:
        print("WARNING: No source specified — no fit will be performed.")
    else:
        print(f"Calibration source : {source_desc}  ({source_energy_mev:.3f} MeV)")

    input_files = sorted(glob.glob(input_pattern))
    if not input_files:
        print(f"ERROR: No files found matching: {input_pattern}")
        return 1

    print(f"\nFound {len(input_files)} ROOT files to merge")
    for i, f in enumerate(input_files[:5], 1):
        print(f"  {i}. {os.path.basename(f)}")
    if len(input_files) > 5:
        print(f"  ... and {len(input_files) - 5} more")
    print(f"\nOutput: {outfile}\n")

    # ── Merge histograms ──────────────────────────────────────────────────────
    h_cont_m = h_disc_m = h_nhit_m = None
    pe_cut, pe_method, n_events, n_merged = -1, "unknown", 0, 0

    print("Merging histograms...")
    for i, infile in enumerate(input_files, 1):
        print(f"\r  Processing file {i}/{len(input_files)}", end='', flush=True)
        fin = ROOT.TFile.Open(infile, "READ")
        if not fin or fin.IsZombie():
            continue
        h_c, h_d, h_n = fin.Get("h_PEcontin"), fin.Get("h_PEdiscrete"), fin.Get("h_nHit")
        if not h_c or not h_d or not h_n:
            fin.Close(); continue

        ei = fin.Get("energy_info")
        if ei:
            for part in ei.GetTitle().split(';'):
                if part.startswith('PE_CUT=') and n_merged == 0:
                    try: pe_cut = int(part.split('=', 1)[1])
                    except ValueError: pass
                elif part.startswith('PE_METHOD=') and n_merged == 0:
                    pe_method = part.split('=', 1)[1]
                elif part.startswith('N_EVENTS='):
                    try: n_events += int(part.split('=', 1)[1])
                    except ValueError: pass

        if n_merged == 0:
            h_cont_m = h_c.Clone("h_PEcontin");   h_cont_m.SetDirectory(0)
            h_disc_m = h_d.Clone("h_PEdiscrete");  h_disc_m.SetDirectory(0)
            h_nhit_m = h_n.Clone("h_nHit");        h_nhit_m.SetDirectory(0)
        else:
            h_cont_m.Add(h_c); h_disc_m.Add(h_d); h_nhit_m.Add(h_n)

        fin.Close()
        n_merged += 1

    print(f"\r  Merged {n_merged}/{len(input_files)} files successfully")
    print()

    if h_cont_m is None:
        print("ERROR: No valid files could be merged.")
        return 1

    # ── Average dark noise ────────────────────────────────────────────────────
    dn_values = []
    for infile in input_files:
        fin_dn = ROOT.TFile.Open(infile, "READ")
        if not fin_dn or fin_dn.IsZombie(): continue
        dn_named = fin_dn.Get("dark_noise_pe")
        if dn_named:
            try:
                v = float(dn_named.GetTitle())
                if v > 0: dn_values.append(v)
            except (ValueError, TypeError): pass
        fin_dn.Close()

    if dark_noise_pe > 0:
        effective_dn, dn_std = dark_noise_pe, 0.0
        print(f"Dark noise: {effective_dn:.4f} PE  (manual override)")
    elif dn_values:
        effective_dn = float(np.mean(dn_values))
        dn_std       = float(np.std(dn_values))
        print(f"Dark noise: {effective_dn:.4f} +/- {dn_std:.4f} PE  "
              f"(averaged over {len(dn_values)} files)")
    else:
        effective_dn, dn_std = 0.0, 0.0
        print("Dark noise: not found — resolution will be sigma/mu")

    # ── Fit merged spectra ────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("FITTING MERGED SPECTRA  (Stage 1: gauss+pol3, Stage 2: physics, ROOT TF1)")
    print("=" * 70)

    if source_energy_mev is None:
        print("Skipping fit (no source specified).")
        result_pe_cont = result_pe = result_nhit = None
        simple_cont = simple_pe = simple_nhit = None
        phys_cont = phys_pe = phys_nhit = None
    else:
        print(f"Source : {source_desc}  ({source_energy_mev:.3f} MeV)")
        simple_cont, phys_cont = fit_source(h_cont_m, source_name, effective_dn, method_name="PEcontin")
        simple_pe,   phys_pe   = fit_source(h_disc_m, source_name, effective_dn, method_name="Discrete_PE")
        simple_nhit, phys_nhit = fit_source(h_nhit_m, source_name, 0.0,          method_name="nHit")

        result_pe_cont = _best(simple_cont, phys_cont)
        result_pe      = _best(simple_pe,   phys_pe)
        result_nhit    = _best(simple_nhit, phys_nhit)

    # ── Fit individual files (for txt table) ──────────────────────────────────
    txt_rows = []

    # Row 0: merged spectrum
    txt_rows.append(_result_to_row_dict('MERGED', result_pe_cont, effective_dn))

    # Rows 1+: per-file fits (only if source is known)
    if source_name:
        print()
        print("=" * 70)
        print("FITTING INDIVIDUAL FILES (for per-file txt table)")
        print("=" * 70)
        for i, infile in enumerate(input_files, 1):
            print(f"\r  Fitting file {i}/{len(input_files)}: {os.path.basename(infile)}", end='', flush=True)
            label, result, dn_f = _fit_single_file(infile, source_name, effective_dn)
            txt_rows.append(_result_to_row_dict(label, result, dn_f))
        print()

    # ── Build energy_info ─────────────────────────────────────────────────────
    info_parts = [
        f"PE_CUT={pe_cut}", f"PE_METHOD={pe_method}",
        f"N_FILES={n_merged}", f"N_EVENTS={n_events}", f"MERGED=True",
        f"SOURCE_NAME={source_name or 'none'}",
        f"DARK_NOISE_PE={effective_dn:.6f}", f"DARK_NOISE_PE_STD={dn_std:.6f}",
        f"DARK_NOISE_N_FILES={len(dn_values)}",
    ]
    if source_energy_mev is not None:
        info_parts.append(f"SOURCE_ENERGY_MEV={source_energy_mev:.4f}")

    _append_result(info_parts, "PEcontin", result_pe_cont)
    _append_result(info_parts, "PE",       result_pe)
    _append_result(info_parts, "NHIT",     result_nhit)

    if source_name:
        _append_result(info_parts, "PEcontin_SIMPLE", simple_cont)
        _append_result(info_parts, "PE_SIMPLE",       simple_pe)
        _append_result(info_parts, "NHIT_SIMPLE",     simple_nhit)
        _append_result(info_parts, "PEcontin_PHYS",   phys_cont)
        _append_result(info_parts, "PE_PHYS",         phys_pe)
        _append_result(info_parts, "NHIT_PHYS",       phys_nhit)

    energy_info = ROOT.TNamed("energy_info", ";".join(info_parts))

    # ── Save ROOT file ────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("SAVING MERGED OUTPUT")
    print("=" * 70)

    fout = ROOT.TFile(outfile, "RECREATE")
    h_cont_m.Write(); h_disc_m.Write(); h_nhit_m.Write()
    energy_info.Write()
    if effective_dn > 0:
        ROOT.TNamed("dark_noise_pe", f"{effective_dn:.6f}").Write()
        ROOT.TNamed("dark_noise_info",
                    f"avg={effective_dn:.6f};std={dn_std:.6f};n_files={len(dn_values)}").Write()
    fout.Close()
    print(f"Merged ROOT file saved: {outfile}")

    # ── Write txt table ───────────────────────────────────────────────────────
    stem    = os.path.splitext(outfile)[0]
    txt_path = stem + "_fit_results.txt"
    _write_txt_table(txt_path, txt_rows, source_name, method_label="PEcontin")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 150)
    print("MERGE SUMMARY")
    print("=" * 150)
    print(f"Files merged    : {n_merged}/{len(input_files)}")
    print(f"Events total    : {n_events}")
    print(f"PE cut mode     : {pe_method} ({pe_cut} PE/ch)")
    if effective_dn > 0:
        print(f"Dark noise      : {effective_dn:.4f} +/- {dn_std:.4f} PE  "
              f"(from {len(dn_values)}/{len(input_files)} files)")
    else:
        print("Dark noise      : not available")
    print(f"Source          : {source_desc if source_energy_mev else 'none'}")
    print()
    print(f"{'Method':<20} {'Mean [PE]':<26} {'Sigma [PE]':<26} "
          f"{'Resolution (tot +/- stat  sys)':<52} {'chi2/ndf':<10} {'Fit model':<10} {'Status':<6}")
    print("-" * 150)
    print(_fmt_row("Continuous PE", result_pe_cont))
    print(_fmt_row("Discrete PE",   result_pe))
    print(_fmt_row("nHit",          result_nhit))
    print("-" * 150)
    print()
    print("SUCCESS")
    print("=" * 150)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge individual spectrum ROOT files into combined file")
    parser.add_argument("input_pattern", help="Glob pattern for input ROOT files")
    parser.add_argument("outfile", help="Output merged ROOT file path")
    known = ', '.join(sorted(SOURCES.keys()))
    parser.add_argument("--source-name", type=str, default=None, metavar="SOURCE",
                        help=f"Calibration source. Known: {known}")
    parser.add_argument("--dark-noise-pe", type=float, default=0.0,
                        help="Override dark noise in PE (default: auto from input files)")
    args = parser.parse_args()

    if args.source_name:
        try:
            resolve_source(args.source_name)
        except ValueError as e:
            print(f"ERROR: {e}"); sys.exit(1)

    sys.exit(merge_spectrum_files(args.input_pattern, args.outfile,
                                  source_name=args.source_name,
                                  dark_noise_pe=args.dark_noise_pe))
