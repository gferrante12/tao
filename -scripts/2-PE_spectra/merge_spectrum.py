#!/usr/bin/env python3
"""
merge_spectrum.py - Merge individual spectrum ROOT files into combined file

Merges histograms from per-file ROOT outputs of get_spectrum.py and
re-fits the combined statistics using fit_peaks_ge68.py / fit_peaks_cs137.py
via spectrum_utils.fit_source().

Two-stage fit:
  Stage 1 : Gaussian + pol3 (robust, data-driven peak finding)
  Stage 2 : Full physics model (source-specific)

An additional plain-text table is written:
  {outfile_stem}_fit_results.txt
  Columns: file | mean | sigma | dark_noise | resolution | corrected_resolution
  First row = merged spectrum; subsequent rows = per-file spectra.

Usage:
  python merge_spectrum.py "spectrum_RUN1055-*.root" spectrum_RUN1055-MERGED.root --source-name Ge68
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
# Summary table helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_row(label, result):
    if result:
        mean_s  = f"{result['peak']:.1f} +/- {result['peak_error']:.1f}"
        sigma_s = f"{result['sigma']:.1f} +/- {result['sigma_error']:.1f}"
        res_tot = result['resolution_error'] * 100.0
        res_s   = f"{result['resolution']*100:.3f} +/- {res_tot:.3f} %"
        chi_s   = f"{result.get('chi2ndf', float('nan')):.2f}"
        method  = result.get('method', '')
        return f"{label:<20} {mean_s:<26} {sigma_s:<26} {res_s:<40} {chi_s:<10} {method:<10} {'PASS':<6}"
    return f"{label:<20} {'---':<26} {'---':<26} {'---':<40} {'---':<10} {'---':<10} {'FAIL':<6}"


def _append_result(parts, prefix, result):
    if result:
        parts += [
            f"RES_{prefix}={result['resolution']:.6f}",
            f"RES_{prefix}_ERR={result['resolution_error']:.6f}",
            f"MEAN_{prefix}={result['peak']:.6f}",
            f"MEAN_{prefix}_ERR={result['peak_error']:.6f}",
            f"SIGMA_{prefix}={result['sigma']:.6f}",
            f"SIGMA_{prefix}_ERR={result['sigma_error']:.6f}",
            f"CHI2NDF_{prefix}={result.get('chi2ndf', -1):.4f}",
            f"METHOD_{prefix}={result.get('method', 'unknown')}",
        ]
    else:
        for key in ('RES', 'MEAN', 'SIGMA'):
            parts += [f"{key}_{prefix}=-1", f"{key}_{prefix}_ERR=0"]
        parts += [f"CHI2NDF_{prefix}=-1", f"METHOD_{prefix}=none"]


def _best_result(simple, physics):
    """Return physics result if available, else simple."""
    return physics if physics else simple


# ─────────────────────────────────────────────────────────────────────────────
# Fit a single-file histogram and extract key quantities
# ─────────────────────────────────────────────────────────────────────────────

def _fit_single_file(infile, source_name, method_key="PEcontin"):
    """
    Open one spectrum ROOT file, fit it, and return a result dict with:
    mean, sigma, dark_noise, resolution (mu/sigma), corrected_resolution (sigma/(mu-DN)).
    Returns None if fit fails.
    method_key: histogram name key: 'PEcontin', 'PEdiscrete', or 'nHit'.
    """
    h_names = {'PEcontin': 'h_PEcontin', 'PEdiscrete': 'h_PEdiscrete', 'nHit': 'h_nHit'}
    hname   = h_names.get(method_key, 'h_PEcontin')

    fin = ROOT.TFile.Open(infile, "READ")
    if not fin or fin.IsZombie():
        return None

    h = fin.Get(hname)
    if not h:
        fin.Close()
        return None

    h_clone = h.Clone(f"_htmp_{os.path.basename(infile)}_{method_key}")
    h_clone.SetDirectory(0)

    dn = 0.0
    dn_obj = fin.Get("dark_noise_pe")
    if dn_obj:
        try:
            dn = float(dn_obj.GetTitle())
        except Exception:
            pass
    fin.Close()

    if h_clone.GetEntries() < 50:
        h_clone.Delete()
        return None

    simple, physics = fit_source(h_clone, source_name, dn,
                                 method_name=method_key, printf=lambda *a: None)
    h_clone.Delete()

    res = _best_result(simple, physics)
    if res is None:
        return None

    mu    = res['peak']
    sigma = res['sigma']
    denom = mu - dn

    raw_res  = sigma / mu if mu > 0 else float('nan')          # sigma / mu
    corr_res = sigma / denom if denom > 0 else float('nan')    # sigma / (mu - DN)

    return dict(
        mean=mu,
        mean_err=res['peak_error'],
        sigma=sigma,
        sigma_err=res['sigma_error'],
        dark_noise=dn,
        resolution=raw_res,
        corrected_resolution=corr_res,
        chi2ndf=res.get('chi2ndf', float('nan')),
        method=res.get('method', '?'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Write fit-results txt table
# ─────────────────────────────────────────────────────────────────────────────

def _write_fit_results_txt(outfile_path, source_name,
                            merged_result_cont, merged_dn,
                            per_file_results):
    """
    Write {outfile_stem}_fit_results.txt with columns:
      file | mean | sigma | dark_noise (DN) | resolution (mu/sigma) | corrected_resolution (sigma/(mu-DN))

    First row = merged spectrum; subsequent rows = per-file (sorted by filename).
    """
    stem     = os.path.splitext(outfile_path)[0]
    txt_path = stem + "_fit_results.txt"

    W = 140
    col_w = [40, 14, 14, 12, 22, 26]

    def _pad(fields):
        return ''.join(str(f).ljust(w) for f, w in zip(fields, col_w))

    hdr_fields = ['File', 'Mean [PE]', 'Sigma [PE]', 'DN [PE]',
                  'Res (sigma/mu)', 'CorrRes (sigma/(mu-DN))']

    def _row(label, r):
        if r is None:
            return _pad([label, 'FAILED', '', '', '', ''])
        return _pad([
            label,
            f"{r['mean']:.3f} ± {r['mean_err']:.3f}",
            f"{r['sigma']:.3f} ± {r['sigma_err']:.3f}",
            f"{r['dark_noise']:.3f}",
            f"{r['resolution']:.5f}",
            f"{r['corrected_resolution']:.5f}",
        ])

    with open(txt_path, 'w') as fout:
        fout.write(f"# Fit Results Table — Source: {source_name or 'none'}\n")
        fout.write(f"# Method: PEcontin (continuous PE spectrum)\n")
        fout.write(f"# Columns: file | mean [PE] | sigma [PE] | dark_noise [PE] "
                   f"| resolution (sigma/mu) | corrected_resolution (sigma/(mu-DN))\n")
        fout.write("=" * W + "\n")
        fout.write(_pad(hdr_fields) + "\n")
        fout.write("-" * W + "\n")

        # First row: merged spectrum
        fout.write(_row("MERGED", merged_result_cont) + "\n")
        fout.write("-" * W + "\n")

        # Per-file rows
        for label, r in sorted(per_file_results, key=lambda x: x[0]):
            fout.write(_row(label, r) + "\n")

        fout.write("=" * W + "\n")

    print(f"Fit results table written: {txt_path}")
    return txt_path


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
        h_c = fin.Get("h_PEcontin")
        h_d = fin.Get("h_PEdiscrete")
        h_n = fin.Get("h_nHit")
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

    print(f"\r  Merged {n_merged}/{len(input_files)} files successfully\n")

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
            except Exception: pass
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
    print("FITTING MERGED SPECTRA")
    print("=" * 70)

    if source_energy_mev is None:
        result_pe_cont = result_pe = result_nhit = None
        simple_cont = simple_pe = simple_nhit = None
        phys_cont = phys_pe = phys_nhit = None
    else:
        simple_cont, phys_cont = fit_source(h_cont_m, source_name, effective_dn, method_name="PEcontin")
        simple_pe,   phys_pe   = fit_source(h_disc_m, source_name, effective_dn, method_name="Discrete_PE")
        simple_nhit, phys_nhit = fit_source(h_nhit_m, source_name, 0.0,          method_name="nHit")

        result_pe_cont = phys_cont if phys_cont else simple_cont
        result_pe      = phys_pe   if phys_pe   else simple_pe
        result_nhit    = phys_nhit if phys_nhit else simple_nhit

    # ── Per-file fits for the txt table ───────────────────────────────────────
    per_file_fit_results = []   # list of (basename, result_dict_or_None)
    if source_name is not None:
        print()
        print("=" * 70)
        print("FITTING PER-FILE SPECTRA (for txt table)")
        print("=" * 70)
        for i, infile in enumerate(input_files, 1):
            bname = os.path.basename(infile)
            print(f"  [{i}/{len(input_files)}] {bname}")
            r_single = _fit_single_file(infile, source_name, method_key="PEcontin")
            per_file_fit_results.append((bname, r_single))

    # ── Build merged result dict for txt table ────────────────────────────────
    merged_txt_result = None
    if result_pe_cont is not None:
        mu    = result_pe_cont['peak']
        sigma = result_pe_cont['sigma']
        denom = mu - effective_dn
        merged_txt_result = dict(
            mean=mu,
            mean_err=result_pe_cont['peak_error'],
            sigma=sigma,
            sigma_err=result_pe_cont['sigma_error'],
            dark_noise=effective_dn,
            resolution=sigma / mu if mu > 0 else float('nan'),
            corrected_resolution=sigma / denom if denom > 0 else float('nan'),
            chi2ndf=result_pe_cont.get('chi2ndf', float('nan')),
            method=result_pe_cont.get('method', '?'),
        )

    # ── Write txt table ───────────────────────────────────────────────────────
    if source_name is not None:
        _write_fit_results_txt(
            outfile, source_name,
            merged_txt_result, effective_dn,
            per_file_fit_results)

    # ── Build energy_info TNamed ──────────────────────────────────────────────
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

    # ── Save ROOT output ──────────────────────────────────────────────────────
    print()
    print("SAVING MERGED OUTPUT")
    fout = ROOT.TFile(outfile, "RECREATE")
    h_cont_m.Write(); h_disc_m.Write(); h_nhit_m.Write()
    energy_info.Write()
    if effective_dn > 0:
        ROOT.TNamed("dark_noise_pe", f"{effective_dn:.6f}").Write()
        ROOT.TNamed("dark_noise_info",
                    f"avg={effective_dn:.6f};std={dn_std:.6f};n_files={len(dn_values)}").Write()
    fout.Close()

    print(f"Merged file saved: {outfile}")

    # ── Console summary ───────────────────────────────────────────────────────
    print()
    print("=" * 150)
    print("MERGE SUMMARY")
    print("=" * 150)
    print(f"Files merged    : {n_merged}/{len(input_files)}")
    print(f"Events total    : {n_events}")
    print(f"Source          : {source_desc if source_energy_mev else 'none'}")
    if effective_dn > 0:
        print(f"Dark noise      : {effective_dn:.4f} +/- {dn_std:.4f} PE")
    print()
    print(f"{'Method':<20} {'Mean [PE]':<26} {'Sigma [PE]':<26} "
          f"{'Resolution':<42} {'chi2/ndf':<10} {'Fit model':<10} {'Status':<6}")
    print("-" * 140)
    print(_fmt_row("Continuous PE", result_pe_cont))
    print(_fmt_row("Discrete PE",   result_pe))
    print(_fmt_row("nHit",          result_nhit))
    print("-" * 140)
    print()
    print("SUCCESS")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge individual spectrum ROOT files into combined file")
    parser.add_argument("input_pattern", help="Glob pattern for input ROOT files")
    parser.add_argument("outfile",       help="Output merged ROOT file path")
    known = ', '.join(sorted(SOURCES.keys()))
    parser.add_argument("--source-name", type=str, default=None, metavar="SOURCE",
                        help=f"Calibration source. Known: {known}")
    parser.add_argument("--dark-noise-pe", type=float, default=0.0,
                        help="Override dark noise in PE")
    args = parser.parse_args()

    if args.source_name:
        try:
            resolve_source(args.source_name)
        except ValueError as e:
            print(f"ERROR: {e}"); sys.exit(1)

    sys.exit(merge_spectrum_files(args.input_pattern, args.outfile,
                                  source_name=args.source_name,
                                  dark_noise_pe=args.dark_noise_pe))
