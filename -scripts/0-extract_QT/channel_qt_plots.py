#!/usr/bin/env python3
"""
channel_qt_plots.py  —  Channel-wise TDC vs ADC scatter / 2-D histogram plots
                        for TAO RUN 1295 (hardcoded)

Primary output: per-channel TDC vs ADC 2-D histogram (scatter density plot)
                + 3-panel summary (mean ADC in prompt window, hit rate, median TDC)

File-path resolution is fully automatic and site-aware:
  CNAF  → POSIX filesystem access
  IHEP  → EOS CLI  (eos ls)  for discovery + XRootD URL for ROOT I/O
  LOCAL → paths must be supplied via --rtraw-file / --spectrum-file

The EOS helper functions mirror those in launch_extract_charge_calib.sh.

Usage (no arguments needed – paths resolved automatically):
  python channel_qt_plots.py [--n-channels N] [--max-events M] ...

Author: G. Ferrante
"""

import argparse
import os
import subprocess
import sys
import tempfile
import warnings
warnings.filterwarnings("ignore")

# ── Performance / environment fixes (applied before any heavy import) ────────
#
# 1. Matplotlib cache: AFS home dirs are often read-only for cache writes.
#    Redirect to a private /tmp dir to avoid the slow AFS probe + warning.
if not os.environ.get("MPLCONFIGDIR"):
    _mpl_tmp = tempfile.mkdtemp(prefix="mplcfg_")
    os.environ["MPLCONFIGDIR"] = _mpl_tmp
else:
    _mpl_tmp = None   # already set externally (e.g. by the shell wrapper)

# 2. XRootD / seckrb5: plugin version mismatch causes repeated Kerberos
#    auth failures before falling back to unix/gsi, adding several seconds
#    per TFile::Open().  Skip krb5 unless the caller has already set a protocol.
if not os.environ.get("XrdSecPROTOCOL"):
    os.environ["XrdSecPROTOCOL"]    = "unix,gsi"
    os.environ["XrdSecDISABLEKRB5"] = "1"

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import uproot
    HAS_UPROOT = True
except ImportError:
    HAS_UPROOT = False

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    HAS_ROOT = True
except ImportError:
    HAS_ROOT = False


# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded RUN configuration
# ─────────────────────────────────────────────────────────────────────────────

RUN_NUMBER = 1295
RUN_LABEL  = f"RUN{RUN_NUMBER}"

# ─────────────────────────────────────────────────────────────────────────────
# Site configuration  (mirrors launch_extract_charge_calib.sh)
# ─────────────────────────────────────────────────────────────────────────────

SITE_PATHS = {
    "CNAF": {
        "rtraw_base":  "/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw",
        "junofs_root": "/storage/gpfs_data/juno/junofs",
        "logs_root":   ("/storage/gpfs_data/juno/junofs/users/gferrante/TAO/"
                        "data_analysis/energy_spectrum/qt_plots"),
        "use_eos_cli": False,
        "eos_server":  "",
    },
    "IHEP": {
        "rtraw_base":  "/eos/juno/tao-rtraw",
        "junofs_root": "/junofs",
        "logs_root":   ("/junofs/users/gferrante/TAO/"
                        "data_analysis/energy_spectrum/qt_plots"),
        "use_eos_cli": True,
        "eos_server":  "root://junoeos01.ihep.ac.cn",
    },
}

# Spectrum file path relative to junofs_root
_SPECTRUM_REL = (
    "users/gferrante/TAO/data_analysis/energy_spectrum/"
    "energy_resolution/RUN1295/"
    "1295_rtraw_run1295_Ge68_2026-02-23_03-16-42/"
    "spectrum_RUN1295-001.root"
)


# ─────────────────────────────────────────────────────────────────────────────
# EOS helper functions  (Python ports of the bash functions)
# ─────────────────────────────────────────────────────────────────────────────

def _eos_available() -> bool:
    """Return True if the 'eos' command is found in PATH."""
    try:
        subprocess.run(["eos", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def detect_site() -> str:
    """
    Return 'CNAF', 'IHEP', or 'LOCAL'.
    Mirrors detect_cluster() in launch_extract_charge_calib.sh:
      CNAF  → /storage/gpfs_data/juno exists
      IHEP  → 'eos' command available  AND  /junofs/users/gferrante exists
    """
    if os.path.isdir("/storage/gpfs_data/juno"):
        return "CNAF"
    if _eos_available() and os.path.isdir("/junofs/users/gferrante"):
        return "IHEP"
    return "LOCAL"


def eos_ls(eos_dir: str) -> list:
    """
    List entries in an EOS directory via 'eos ls'.
    Returns a list of bare entry names; empty list on any failure.
    """
    try:
        result = subprocess.run(
            ["eos", "ls", eos_dir],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def eos_dir_exists(eos_dir: str) -> bool:
    """Return True if 'eos ls <eos_dir>' exits with code 0."""
    try:
        result = subprocess.run(
            ["eos", "ls", eos_dir],
            capture_output=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def eos_find_run(rtraw_base: str, run: int, use_eos_cli: bool) -> str:
    """
    Locate the directory that holds RTRAW files for *run*.

    Mirrors eos_find_run() in launch_extract_charge_calib.sh:
      Structure:  <base>/<TAO-version>/<stream>/<group8>/<subgroup8>/<run>/
      group_prefix  = (run // 1000) * 1000  → 8-digit zero-padded
      run_prefix    = (run //  100) *  100  → 8-digit zero-padded

    Returns the full EOS/POSIX directory path, or '' if not found.
    """
    run_prefix   = f"{(run //  100) *  100:08d}"   # e.g. 00001200
    group_prefix = f"{(run // 1000) * 1000:08d}"   # e.g. 00001000

    if use_eos_cli:
        # Get available TAO versions, newest first (mirrors bash: sort -V -r)
        tao_versions = sorted(
            [v for v in eos_ls(rtraw_base)
             if v.startswith("T") and v.count(".") == 2],
            reverse=True,
        )
        print(f"  [EOS] available TAO versions: {tao_versions}")

        for version in tao_versions:
            for stream in ("mix_stream", "TVT", "WT_TVT"):
                test_path = (f"{rtraw_base}/{version}/{stream}/"
                             f"{group_prefix}/{run_prefix}/{run}")
                if eos_dir_exists(test_path):
                    print(f"  [EOS] run directory found: {test_path}")
                    return test_path

    else:
        # CNAF: standard POSIX glob
        import glob
        for pattern in (
            f"{rtraw_base}/*/*/{group_prefix}/{run_prefix}/{run}",
            f"{rtraw_base}/*/{group_prefix}/{run_prefix}/{run}",
            f"{rtraw_base}/*/*/*/*/{run}",
        ):
            hits = sorted(glob.glob(pattern))
            if hits:
                return hits[0]

    return ""


def list_rtraw_files(run_dir: str, use_eos_cli: bool) -> list:
    """
    Return a sorted list of full EOS paths to .rtraw files inside *run_dir*.
    On IHEP these are EOS paths (to be converted to XRootD URLs before use).
    """
    if use_eos_cli:
        entries = eos_ls(run_dir)
        names   = sorted(f for f in entries if f.endswith(".rtraw"))
        return [f"{run_dir}/{f}" for f in names]
    else:
        import glob
        return sorted(glob.glob(os.path.join(run_dir, "*.rtraw")))


def to_xrootd_url(eos_path: str, eos_server: str) -> str:
    """
    Convert an EOS path to an XRootD URL.
    Mirrors to_xrootd_url() in launch_extract_charge_calib.sh.
    """
    if eos_server:
        return f"{eos_server}/{eos_path}"
    return eos_path


def file_exists_or_accessible(path: str, use_eos_cli: bool = False) -> bool:
    """
    Check whether a file is accessible.
    XRootD URLs: always True (ROOT handles errors).
    IHEP EOS paths: probe via 'eos ls' on the parent directory.
    POSIX: os.path.exists().
    """
    if path.startswith("root://"):
        return True
    if use_eos_cli:
        parent  = os.path.dirname(path)
        fname   = os.path.basename(path)
        return fname in eos_ls(parent)
    return os.path.exists(path)


# ─────────────────────────────────────────────────────────────────────────────
# High-level path resolution
# ─────────────────────────────────────────────────────────────────────────────

def resolve_rtraw_first(site: str, override: str = "") -> str:
    """
    Discover and return the XRootD URL / POSIX path of the FIRST .rtraw file
    for RUN1295.  Uses eos_find_run() + list_rtraw_files(), exactly as the
    bash launcher does.
    """
    if override:
        return override
    if site == "LOCAL":
        return ""

    cfg        = SITE_PATHS[site]
    use_eos    = cfg["use_eos_cli"]
    rtraw_base = cfg["rtraw_base"]
    eos_server = cfg["eos_server"]

    print(f"  Searching for {RUN_LABEL} under {rtraw_base} ...")
    run_dir = eos_find_run(rtraw_base, RUN_NUMBER, use_eos)

    if not run_dir:
        print(f"  WARNING: could not locate run directory for {RUN_LABEL}")
        return ""

    files = list_rtraw_files(run_dir, use_eos)
    if not files:
        print(f"  WARNING: no .rtraw files found in {run_dir}")
        return ""

    print(f"  Found {len(files)} RTRAW file(s); using the first:")
    first = files[0]
    url   = to_xrootd_url(first, eos_server) if use_eos else first
    print(f"    {url}")
    return url


def resolve_spectrum(site: str, override: str = "") -> str:
    """Return the spectrum ROOT file path for RUN1295."""
    if override:
        return override
    if site == "LOCAL":
        return ""
    return os.path.join(SITE_PATHS[site]["junofs_root"], _SPECTRUM_REL)


# ─────────────────────────────────────────────────────────────────────────────
# Plot style
# ─────────────────────────────────────────────────────────────────────────────

plt.rcParams.update({
    "figure.figsize": (10, 4),
    "font.size":      11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
})

# TDC_WINDOW kept for back-compat; canonical thresholds now in plot functions
TDC_WINDOW = (200, 450)


# ─────────────────────────────────────────────────────────────────────────────
# TDC vs ADC data collection from RTRAW
# ─────────────────────────────────────────────────────────────────────────────

def collect_tdc_adc_from_rtraw(rtraw_path, n_channels=2,
                                max_events=50_000,
                                tdc_lo=0.0, tdc_hi=600.0):
    """
    Read a TAO RTRAW file (requires PyROOT + TAO environment) and collect
    per-channel (TDC [ns], ADC [counts]) pairs from CdElecEvt.

    Returns
    -------
    dict : { ch_id (int) → { "tdc": np.ndarray, "adc": np.ndarray } }
    """
    if not HAS_ROOT:
        raise RuntimeError("PyROOT not available – cannot read RTRAW file")

    frtraw = ROOT.TFile.Open(rtraw_path, "READ")
    if not frtraw or frtraw.IsZombie():
        raise RuntimeError(f"Cannot open RTRAW file: {rtraw_path}")

    cd_elec_tree = frtraw.Get("Event/Elec/CdElecEvt")
    if not cd_elec_tree:
        frtraw.Close()
        raise RuntimeError("Cannot find CdElecEvt tree in RTRAW file")

    nentries = min(cd_elec_tree.GetEntries(), max_events)
    print(f"  Reading {nentries} events from {RUN_LABEL} ...")

    ch_data = {}

    cd_elec_evt = ROOT.Tao.CdElecEvt()
    cd_elec_tree.SetBranchAddress("CdElecEvt", cd_elec_evt)

    # Early-stop: once we have n_channels channels each with enough hits,
    # there is no need to keep reading the file.  This is the main speed-up
    # for sample/diagnostic runs with small --max-events on XRootD.
    MIN_HITS_PER_CHANNEL = 200

    for i in range(nentries):
        if (i + 1) % 1_000 == 0:
            ready = sum(
                1 for d in ch_data.values()
                if len(d["tdc"]) >= MIN_HITS_PER_CHANNEL
            )
            print(f"    event {i+1}/{nentries}  "
                  f"({ready}/{n_channels} channels ready) ...", flush=True)
            if ready >= n_channels:
                print(f"    → early stop: {n_channels} channels collected.",
                      flush=True)
                break

        cd_elec_tree.GetEntry(i)
        channels = cd_elec_evt.GetElecChannels()

        for j in range(channels.size()):
            ch     = channels[j]
            chid   = ch.getChannelID()
            adcs   = ch.getADCs()
            tdcs   = ch.getTDCs()
            n_hits = min(adcs.size(), tdcs.size())
            if n_hits == 0:
                continue

            if chid not in ch_data:
                ch_data[chid] = {"tdc": [], "adc": []}

            for k in range(n_hits):
                tdc_ns = float(tdcs[k])
                adc_v  = float(adcs[k])
                if tdc_lo <= tdc_ns <= tdc_hi:
                    ch_data[chid]["tdc"].append(tdc_ns)
                    ch_data[chid]["adc"].append(adc_v)

    frtraw.Close()

    result       = {}
    sorted_chids = sorted(ch_data.keys())[:n_channels]
    for chid in sorted_chids:
        tdc_arr = np.array(ch_data[chid]["tdc"], dtype=float)
        adc_arr = np.array(ch_data[chid]["adc"], dtype=float)
        if len(tdc_arr) >= 10:
            result[chid] = {"tdc": tdc_arr, "adc": adc_arr}

    print(f"  Collected TDC/ADC data for {len(result)} channels")
    return result



# ─────────────────────────────────────────────────────────────────────────────
# Threshold definitions (plots + summary txt)
# ─────────────────────────────────────────────────────────────────────────────

TDC_WIN_WIDE   = (200, 450)   # ns – broad prompt window
TDC_WIN_NARROW = (240, 400)   # ns – tight prompt window

ADC_THR_01  = 0.10e6          # 100 000 counts
ADC_THR_015 = 0.15e6          # 150 000 counts
ADC_THR_18  = 1.80e6          # 1 800 000 counts
ADC_LOG_MIN = 100.0           # lower edge when ADC axis is logarithmic

C_TDC_WIDE   = "cyan"
C_TDC_NARROW = "darkorange"
C_ADC_01     = "limegreen"
C_ADC_015    = "red"
C_ADC_18     = "magenta"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _adc_bins_and_range(lo, hi, n_bins, adc_log):
    """
    Return (bin_edges, plot_lo, plot_hi) for a histogram over [lo, hi].

    adc_log=True  → logspace edges, lo clamped to ADC_LOG_MIN
    adc_log=False → linspace edges (uniform bins)
    """
    if adc_log:
        lo = max(lo, ADC_LOG_MIN)
        edges = np.logspace(np.log10(lo), np.log10(hi), n_bins + 1)
    else:
        edges = np.linspace(lo, hi, n_bins + 1)
    return edges, edges[0], edges[-1]


def _draw_adc_thresholds_h(ax, adc_log):
    """Draw horizontal ADC threshold lines on a 2-D scatter axes."""
    for val, col in ((ADC_THR_01, C_ADC_01), (ADC_THR_015, C_ADC_015),
                     (ADC_THR_18, C_ADC_18)):
        ylim = ax.get_ylim()
        if ylim[0] < val < ylim[1] * 10:   # draw even if slightly outside current view
            ax.axhline(val, color=col, lw=1.2, ls="--")


def _draw_adc_thresholds_v(ax, lo, hi):
    """Draw vertical ADC threshold lines on an ADC-projection axes."""
    for val, col in ((ADC_THR_01, C_ADC_01), (ADC_THR_015, C_ADC_015),
                     (ADC_THR_18, C_ADC_18)):
        if lo < val < hi:
            ax.axvline(val, color=col, lw=1.2, ls="--")


# ─────────────────────────────────────────────────────────────────────────────
# Per-channel TDC vs ADC 2-D scatter + TDC projection
# ─────────────────────────────────────────────────────────────────────────────

def plot_tdc_adc_2d_channel(ch_id, tdc_arr, adc_arr, output_path,
                             tdc_bins=100, adc_bins=80, adc_log=False):
    """
    Two-panel figure per channel:
      Left  – 2-D scatter density (plasma) with TDC/ADC threshold lines.
      Right – 1-D TDC projection (1 ns/bin) with both TDC windows highlighted.

    adc_log=False → linear ADC axis, uniform bins, adc_lo = 0
    adc_log=True  → log    ADC axis, logspace bins, adc_lo = ADC_LOG_MIN (10)

    No legend labels on threshold lines.
    """
    if len(tdc_arr) < 5:
        return

    # ADC range
    adc_hi_raw = float(np.percentile(adc_arr, 99.9)) * 1.05
    if adc_log:
        adc_lo = ADC_LOG_MIN
    else:
        adc_lo = 0.0
    adc_hi = max(adc_hi_raw, adc_lo * 2)

    tdc_lo = 0.0
    tdc_hi = float(tdc_arr.max())

    # Build 2-D histogram
    tdc_edges = np.linspace(tdc_lo, tdc_hi, tdc_bins + 1)
    adc_edges, _, _ = _adc_bins_and_range(adc_lo, adc_hi, adc_bins, adc_log)

    h, xedge, yedge = np.histogram2d(
        tdc_arr, adc_arr,
        bins=[tdc_edges, adc_edges],
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ── left: 2-D scatter density ─────────────────────────────────────────────
    ax2d = axes[0]
    im = ax2d.pcolormesh(
        xedge, yedge, h.T,
        cmap="plasma",
        norm=matplotlib.colors.LogNorm(vmin=1),
    )
    fig.colorbar(im, ax=ax2d, label="Hits / bin")

    # TDC vertical thresholds
    for x in TDC_WIN_WIDE:
        ax2d.axvline(x, color=C_TDC_WIDE,   lw=1.2, ls="--")
    for x in TDC_WIN_NARROW:
        ax2d.axvline(x, color=C_TDC_NARROW, lw=1.2, ls="--")

    # ADC horizontal thresholds
    for val, col in ((ADC_THR_01, C_ADC_01), (ADC_THR_015, C_ADC_015),
                     (ADC_THR_18, C_ADC_18)):
        ax2d.axhline(val, color=col, lw=1.2, ls="--")

    ax2d.set_xlabel("TDC [ns]")
    ax2d.set_ylabel("ADC [counts]")
    if adc_log:
        ax2d.set_yscale("log")
        ax2d.set_ylim(bottom=ADC_LOG_MIN)
    else:
        ax2d.set_ylim(bottom=0)
    ax2d.set_title(f"Channel {ch_id}  —  TDC vs ADC  |  {RUN_LABEL}")

    # ── right: 1-D TDC projection (1 ns/bin) ─────────────────────────────────
    ax1d = axes[1]
    n_tdc_bins = max(1, int(round(tdc_hi - tdc_lo)))
    tdc_counts, tdc_edges2 = np.histogram(tdc_arr, bins=n_tdc_bins,
                                           range=[tdc_lo, tdc_hi])
    tdc_centres = 0.5 * (tdc_edges2[:-1] + tdc_edges2[1:])

    in_wide   = (tdc_centres >= TDC_WIN_WIDE[0])   & (tdc_centres <= TDC_WIN_WIDE[1])
    in_narrow = (tdc_centres >= TDC_WIN_NARROW[0]) & (tdc_centres <= TDC_WIN_NARROW[1])

    ax1d.step(tdc_centres, tdc_counts, where="mid", color="k", lw=0.8)
    ax1d.fill_between(tdc_centres, tdc_counts,
                      where=in_wide,   step="mid", color=C_TDC_WIDE,   alpha=0.25)
    ax1d.fill_between(tdc_centres, tdc_counts,
                      where=in_narrow, step="mid", color=C_TDC_NARROW, alpha=0.35)
    for x in TDC_WIN_WIDE:
        ax1d.axvline(x, color=C_TDC_WIDE,   lw=1.0, ls="--")
    for x in TDC_WIN_NARROW:
        ax1d.axvline(x, color=C_TDC_NARROW, lw=1.0, ls="--")

    ax1d.set_xlabel("TDC [ns]")
    ax1d.set_ylabel("Hits / bin  (1 ns bins)")
    ax1d.set_title(f"Channel {ch_id}  —  TDC projection")
    ax1d.set_yscale("log")
    ax1d.set_ylim(bottom=0.5)

    suffix = "_ADC_log" if adc_log else ""
    fig.suptitle(
        f"TDC vs ADC{' [ADC log]' if adc_log else ''}  |  Channel {ch_id}  |  {RUN_LABEL}",
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# ADC projection – 3-panel separate figure
# ─────────────────────────────────────────────────────────────────────────────

def plot_adc_projections(ch_id, adc_arr, output_path, adc_log=False):
    """
    Three-panel ADC spectrum (y always log-scale):
      a) bin = 1 000 ADC,  range [0 or 10, adc_max]
      b) bin =   100 ADC,  range [0 or 10, 50 000]
      c) bin =    25 ADC,  range [0 or 10, 15 000]

    adc_log=True  → x log scale, logspace bins, x_lo = ADC_LOG_MIN (10)
    adc_log=False → x linear,    linspace bins, x_lo = 0
    """
    if len(adc_arr) < 5:
        return

    adc_max = float(adc_arr.max())
    x_lo = ADC_LOG_MIN if adc_log else 0.0

    panels = [
        {"bsize": 1000, "lo": x_lo, "hi": adc_max,  "label": "bin = 1 000 ADC"},
        {"bsize":  100, "lo": x_lo, "hi": 50_000.0, "label": "bin = 100 ADC"},
        {"bsize":   25, "lo": x_lo, "hi": 15_000.0, "label": "bin = 25 ADC"},
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, p in zip(axes, panels):
        lo, hi = p["lo"], p["hi"]
        n_bins = max(1, int(round((hi - lo) / p["bsize"])))
        edges, plot_lo, plot_hi = _adc_bins_and_range(lo, hi, n_bins, adc_log)

        counts, _ = np.histogram(adc_arr, bins=edges)
        centres   = 0.5 * (edges[:-1] + edges[1:])

        ax.step(centres, np.maximum(counts, 0.1), where="mid",
                color="#1f77b4", lw=1.0)
        ax.fill_between(centres, np.maximum(counts, 0.1), step="mid",
                        color="#1f77b4", alpha=0.3)

        _draw_adc_thresholds_v(ax, plot_lo, plot_hi)

        ax.set_xlabel("ADC [counts]")
        ax.set_ylabel("Hits / bin")
        ax.set_title(f"Ch {ch_id}  |  {p['label']}  |  {RUN_LABEL}")
        ax.set_yscale("log")
        ax.set_ylim(bottom=0.5)
        ax.set_xlim(plot_lo, plot_hi)
        if adc_log:
            ax.set_xscale("log")
        ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Hit-count summary text file
# ─────────────────────────────────────────────────────────────────────────────

def write_hit_summary(ch_data, output_path):
    tdc_windows = [
        ("TDC [200–450 ns]", 200.0, 450.0),
        ("TDC [240–400 ns]", 240.0, 400.0),
    ]
    adc_bands = [
        ("ADC [0 – 0.05e6]",        0.0,    0.05e6),
        ("ADC [0.05e6 – 0.10e6]", 0.05e6,   0.10e6),
        ("ADC [0.10e6 – 0.15e6]", 0.10e6,   0.15e6),
        ("ADC [0.15e6 – 1.80e6]", 0.15e6,   1.80e6),
        ("ADC > 1.80e6",           1.80e6,  np.inf),
    ]

    lines = [
        f"Hit-count summary  |  {RUN_LABEL}",
        "=" * 72,
        "",
    ]

    for chid, arrays in sorted(ch_data.items()):
        tdc_a = arrays["tdc"]
        adc_a = arrays["adc"]
        lines.append(f"Channel {chid}   (total collected hits: {len(tdc_a)})")
        lines.append("-" * 72)

        for tdc_label, t_lo, t_hi in tdc_windows:
            tdc_mask = (tdc_a >= t_lo) & (tdc_a <= t_hi)
            lines.append(f"  {tdc_label}")
            for adc_label, a_lo, a_hi in adc_bands:
                adc_mask = (adc_a >= a_lo) if np.isinf(a_hi) else \
                           (adc_a >= a_lo) & (adc_a < a_hi)
                n = int((tdc_mask & adc_mask).sum())
                lines.append(f"    {adc_label:<30s}  {n:>8d} hits")
            lines.append("")

        lines.append("")

    with open(output_path, "w") as fout:
        fout.write("\n".join(lines))
    print(f"  ✓  hit_summary.txt")


# ─────────────────────────────────────────────────────────────────────────────
# Multi-channel 3-panel summary scatter
# ─────────────────────────────────────────────────────────────────────────────

def plot_tdc_adc_summary(ch_data, output_path, tdc_window=TDC_WIN_WIDE,
                          adc_log=False):
    ch_ids      = sorted(ch_data.keys())
    mean_adcs, hit_fracs, median_tdcs = [], [], []

    for chid in ch_ids:
        tdc_a = ch_data[chid]["tdc"]
        adc_a = ch_data[chid]["adc"]
        win   = (tdc_a >= tdc_window[0]) & (tdc_a <= tdc_window[1])
        if win.sum() > 0:
            mean_adcs.append(float(adc_a[win].mean()))
            hit_fracs.append(float(win.sum()) / max(len(tdc_a), 1))
            median_tdcs.append(float(np.median(tdc_a[win])))
        else:
            mean_adcs.append(0.0); hit_fracs.append(0.0); median_tdcs.append(0.0)

    ch_ids    = np.array(ch_ids)
    mean_adcs = np.array(mean_adcs)
    hit_fracs = np.array(hit_fracs)
    med_tdcs  = np.array(median_tdcs)
    ok        = mean_adcs > 0

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    axes[0].scatter(ch_ids[ok], mean_adcs[ok], s=18, color="#1f77b4", alpha=0.8)
    if ok.sum() > 0:
        axes[0].axhline(np.median(mean_adcs[ok]), color="r", lw=1, ls="--",
                        label=f"Median = {np.median(mean_adcs[ok]):.0f}")
    axes[0].set_ylabel("Mean ADC in prompt window")
    axes[0].set_title(
        f"TDC–ADC summary{' [ADC log]' if adc_log else ''}  |  {RUN_LABEL}  "
        f"(prompt window {tdc_window[0]}–{tdc_window[1]} ns)"
    )
    if adc_log and ok.sum() > 0 and mean_adcs[ok].min() > 0:
        axes[0].set_yscale("log")
        axes[0].set_ylim(bottom=ADC_LOG_MIN)
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)

    axes[1].scatter(ch_ids[ok], hit_fracs[ok], s=18, color="#ff7f0e", alpha=0.8)
    if ok.sum() > 0:
        axes[1].axhline(np.median(hit_fracs[ok]), color="r", lw=1, ls="--",
                        label=f"Median = {np.median(hit_fracs[ok]):.3f}")
    axes[1].set_ylabel("Prompt hit fraction")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)

    axes[2].scatter(ch_ids[ok], med_tdcs[ok], s=18, color="#2ca02c", alpha=0.8)
    if ok.sum() > 0:
        axes[2].axhline(np.median(med_tdcs[ok]), color="r", lw=1, ls="--",
                        label=f"Median = {np.median(med_tdcs[ok]):.1f} ns")
    axes[2].set_ylabel("Median TDC in window [ns]")
    axes[2].set_xlabel("Channel ID")
    axes[2].legend(fontsize=8); axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {os.path.basename(output_path)}")
    if ok.sum() > 0:
        print(f"     channels with prompt hits : {ok.sum()}/{len(ch_ids)}")
        print(f"     median prompt ADC         : {np.median(mean_adcs[ok]):.0f}")
        print(f"     median prompt TDC         : {np.median(med_tdcs[ok]):.1f} ns")


# ─────────────────────────────────────────────────────────────────────────────
# Main RTRAW driver
# ─────────────────────────────────────────────────────────────────────────────

def process_rtraw_tdc_adc(rtraw_path, output_base,
                           n_channels=2, max_events=50_000,
                           tdc_lo=0.0, tdc_hi=600.0):
    """
    Collect TDC/ADC data from RTRAW then produce all plots inside a
    timestamped subdirectory:

        <output_base>/RUN1295/<YYYYMMDD_HHMMSS>/

    For each channel:
        tdc_adc_ch<NNNN>.png          – 2-D scatter + TDC projection (ADC linear)
        tdc_adc_ch<NNNN>_ADC_log.png  – same with ADC log axis / logspace bins
        adc_projections_ch<NNNN>.png         – 3-panel ADC spectrum (ADC linear)
        adc_projections_ch<NNNN>_ADC_log.png – same with ADC log axis / logspace bins

    Global outputs:
        tdc_adc_summary.png          – 3-panel channel summary (ADC linear)
        tdc_adc_summary_ADC_log.png  – same with mean-ADC panel log scaled
        hit_summary.txt
    """
    import datetime
    ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(output_base, f"RUN{RUN_NUMBER}", ts)
    os.makedirs(output_dir, exist_ok=True)
    print(f"  Output directory: {output_dir}")

    ch_data = collect_tdc_adc_from_rtraw(
        rtraw_path, n_channels=n_channels,
        max_events=max_events, tdc_lo=tdc_lo, tdc_hi=tdc_hi,
    )

    if not ch_data:
        print(f"  WARNING: no TDC/ADC data collected from {rtraw_path}")
        return

    print(f"\n  Generating {len(ch_data)} per-channel plots (linear + log) ...")
    for chid, arrays in sorted(ch_data.items()):
        tdc_a, adc_a = arrays["tdc"], arrays["adc"]

        # ── TDC vs ADC 2-D scatter ──────────────────────────────────────────
        plot_tdc_adc_2d_channel(
            chid, tdc_a, adc_a,
            os.path.join(output_dir, f"tdc_adc_ch{chid:04d}.png"),
            adc_log=False,
        )
        plot_tdc_adc_2d_channel(
            chid, tdc_a, adc_a,
            os.path.join(output_dir, f"tdc_adc_ch{chid:04d}_ADC_log.png"),
            adc_log=True,
        )

        # ── ADC projections ─────────────────────────────────────────────────
        plot_adc_projections(
            chid, adc_a,
            os.path.join(output_dir, f"adc_projections_ch{chid:04d}.png"),
            adc_log=False,
        )
        plot_adc_projections(
            chid, adc_a,
            os.path.join(output_dir, f"adc_projections_ch{chid:04d}_ADC_log.png"),
            adc_log=True,
        )

    # ── Summary scatter ──────────────────────────────────────────────────────
    plot_tdc_adc_summary(
        ch_data,
        os.path.join(output_dir, "tdc_adc_summary.png"),
        adc_log=False,
    )
    plot_tdc_adc_summary(
        ch_data,
        os.path.join(output_dir, "tdc_adc_summary_ADC_log.png"),
        adc_log=True,
    )

    # ── Hit-count text file ──────────────────────────────────────────────────
    write_hit_summary(ch_data, os.path.join(output_dir, "hit_summary.txt"))

    n_png = sum(1 for f in os.listdir(output_dir) if f.endswith(".png"))
    print(f"\n  Done – {n_png} PNG files + hit_summary.txt in:\n  {output_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# Spectrum helper (optional --spectrum mode)
# ─────────────────────────────────────────────────────────────────────────────

def _read_root_histogram_uproot(f, name):
    try:
        h       = f[name]
        counts  = h.values()
        edges   = h.axis().edges()
        centers = 0.5 * (edges[:-1] + edges[1:])
        return centers, counts, edges
    except Exception:
        return None, None, None


def _read_root_histogram_pyroot(tfile, name):
    h = tfile.Get(name)
    if not h or h.GetEntries() == 0:
        return None, None, None
    n       = h.GetNbinsX()
    edges   = np.array([h.GetBinLowEdge(b) for b in range(1, n + 2)])
    counts  = np.array([h.GetBinContent(b) for b in range(1, n + 1)])
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, counts, edges


def plot_global_spectrum(root_path, output_path, dark_noise_pe=0.0):
    if HAS_UPROOT:
        with uproot.open(root_path) as f:
            for name in ("h_PEdiscrete", "h_PEcontin"):
                cx, cy, _ = _read_root_histogram_uproot(f, name)
                if cx is not None and cy.sum() > 0:
                    break
    elif HAS_ROOT:
        tf = ROOT.TFile.Open(root_path, "READ")
        cx = cy = None
        for name in ("h_PEdiscrete", "h_PEcontin"):
            cx, cy, _ = _read_root_histogram_pyroot(tf, name)
            if cx is not None:
                break
        tf.Close()
    else:
        print("  [SKIP] neither uproot nor PyROOT available for global spectrum")
        return

    if cx is None:
        print("  [SKIP] no PE histogram found")
        return

    fig, ax = plt.subplots()
    ax.step(cx, cy, where="mid", color="#2ca02c", lw=1.5)
    ax.fill_between(cx, cy, step="mid", alpha=0.3, color="#2ca02c")
    if dark_noise_pe > 0:
        ax.axvline(dark_noise_pe, color="grey", lw=1, ls=":",
                   label=f"DN = {dark_noise_pe:.1f} PE")
    ax.set_xlabel("Total PE per event")
    ax.set_ylabel("Events / bin")
    ax.set_title(f"Global PE-sum spectrum  |  {RUN_LABEL}")
    ax.set_yscale("log"); ax.set_ylim(bottom=0.5)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  global spectrum → {os.path.basename(output_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    site    = detect_site()
    cfg     = SITE_PATHS.get(site, {})
    use_eos = cfg.get("use_eos_cli", False)
    print(f"  Detected site: {site}")

    parser = argparse.ArgumentParser(
        description=(
            f"TDC-ADC diagnostic plots per SiPM channel  |  {RUN_LABEL}\n"
            "RTRAW path is auto-discovered via EOS CLI (IHEP) or POSIX glob (CNAF).\n"
            "All path arguments are optional overrides.\n\n"
            "Output: <output-dir>/RUN1295/<TIMESTAMP>/\n"
            "  tdc_adc_ch<NNNN>.png / _ADC_log.png\n"
            "  adc_projections_ch<NNNN>.png / _ADC_log.png\n"
            "  tdc_adc_summary.png / _ADC_log.png\n"
            "  hit_summary.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--rtraw-file",    default="",
                        help="Override RTRAW file / XRootD URL")
    parser.add_argument("--spectrum-file", default="",
                        help="Override spectrum ROOT file path")
    parser.add_argument("--output-dir",    default="",
                        help="Output base dir (RUN1295/<TS>/ appended automatically)")

    mode_grp = parser.add_mutually_exclusive_group()
    mode_grp.add_argument("--from-rtraw", action="store_true", default=True,
                          help="[DEFAULT] TDC vs ADC scatter plots from RTRAW")
    mode_grp.add_argument("--spectrum",   action="store_true",
                          help="Plot global PE-sum spectrum from a spectrum ROOT file")

    parser.add_argument("--n-channels",  type=int,   default=2,
                        help="Number of sample channels to plot (default: 2)")
    parser.add_argument("--max-events",  type=int,   default=50_000,
                        help="Max events to read from RTRAW (default: 50000)")
    parser.add_argument("--tdc-lo",      type=float, default=0.0,
                        help="TDC lower edge [ns] (default: 0)")
    parser.add_argument("--tdc-hi",      type=float, default=600.0,
                        help="TDC upper edge [ns] (default: 600)")

    args = parser.parse_args()

    # ── output base directory (timestamp subdir added inside process_rtraw_tdc_adc)
    if args.output_dir:
        output_base = args.output_dir
    elif site != "LOCAL":
        output_base = cfg["logs_root"]
    else:
        output_base = "./qt_plots"

    # ── dispatch ──────────────────────────────────────────────────────────────
    if args.spectrum:
        import datetime
        ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_base, f"RUN{RUN_NUMBER}", ts)
        os.makedirs(output_dir, exist_ok=True)
        spec_path  = resolve_spectrum(site, args.spectrum_file)
        if not file_exists_or_accessible(spec_path, use_eos):
            sys.exit(f"ERROR: spectrum file not found: {spec_path}")
        print(f"Plotting global spectrum from: {spec_path}")
        dark_noise_pe = 0.0
        if HAS_UPROOT:
            with uproot.open(spec_path) as f:
                try:
                    dark_noise_pe = float(f["dark_noise_pe"].title)
                except Exception:
                    pass
        plot_global_spectrum(spec_path,
                             os.path.join(output_dir, "global_spectrum.png"),
                             dark_noise_pe=dark_noise_pe)
        print(f"\nDone.  Output in: {output_dir}")

    else:
        rtraw_path = resolve_rtraw_first(site, args.rtraw_file)
        if not rtraw_path:
            sys.exit(
                "ERROR: could not resolve RTRAW path.\n"
                f"  Supply --rtraw-file, or check site detection (site={site})."
            )
        if not file_exists_or_accessible(rtraw_path, use_eos):
            sys.exit(f"ERROR: RTRAW file not found / not accessible: {rtraw_path}")

        print(f"\nProcessing RTRAW for TDC-ADC scatter plots:")
        print(f"  file       : {rtraw_path}")
        print(f"  n_channels : {args.n_channels}  (sample)")
        print(f"  max_events : {args.max_events}")
        print(f"  TDC range  : [{args.tdc_lo}, {args.tdc_hi}] ns")
        print()

        process_rtraw_tdc_adc(
            rtraw_path, output_base,
            n_channels=args.n_channels,
            max_events=args.max_events,
            tdc_lo=args.tdc_lo,
            tdc_hi=args.tdc_hi,
        )

    # Clean up per-job matplotlib cache dir
    if _mpl_tmp and os.path.isdir(_mpl_tmp):
        import shutil
        shutil.rmtree(_mpl_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
