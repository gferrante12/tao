#!/bin/bash
# =============================================================================
# gain_calibration_1295_test1ch.sh
# Minimal single-channel gain calibration test — RUN 1295, IHEP cluster.
# Purpose: diagnose queue/resource issues before submitting the full job.
#   - 1 CPU, 4 GB RAM  (minimal footprint, easy to schedule)
#   - fits only channel 0 with the simplest model (multigauss)
#   - no plots, no parallel workers
# Submit:
#   hep_sub gain_calibration_1295_test1ch.sh -g juno \
#       -o gain_calibration_1295_test1ch.out \
#       -e gain_calibration_1295_test1ch.err \
#       -cpu 1 -mem 4000
# =============================================================================

set -e

# ── Hard-coded configuration ──────────────────────────────────────────────────
RUN=1295
CHANNEL=0

MERGED_ROOT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/0-extract_QT_results/charge_merged/CHARGE_RUN1295_merged.root"
GAIN_SCRIPT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration/gain_calibration.py"
MODELS_SCRIPT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration/gain_fit_models.py"
OUTPUT_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/1-gain_calibration_results/1295/test1ch_$(date +%Y-%m-%d_%H-%M-%S)"
LOG_FILE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/RUN1295/1-gain_calibration/gain_calib_test1ch_$(date +%Y%m%d_%H%M%S).log"

JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4"
PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"

# ── Logging ───────────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_FILE")" "$OUTPUT_DIR"
exec > "$LOG_FILE" 2>&1

echo ""
echo "============================================================"
echo "  GAIN CALIBRATION TEST — 1 channel — RUN $RUN"
echo "============================================================"
echo "Host       : $(hostname)"
echo "Date       : $(date)"
echo "Input      : $MERGED_ROOT"
echo "Output     : $OUTPUT_DIR"
echo "Channel    : $CHANNEL"
echo "Log        : $LOG_FILE"
echo ""

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [ ! -f "$MERGED_ROOT" ]; then
    echo "ERROR: Merged ROOT file not found: $MERGED_ROOT"
    exit 1
fi

if [ ! -f "$GAIN_SCRIPT" ]; then
    echo "ERROR: gain_calibration.py not found: $GAIN_SCRIPT"
    exit 1
fi

echo "Input file size : $(du -h "$MERGED_ROOT" | cut -f1)"
echo ""

# ── Environment setup ─────────────────────────────────────────────────────────
echo "Setting up JUNO-TAO environment ($JUNO_RELEASE)..."
source "${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="${PYTHONPATH}"

echo "Activating Python virtual environment..."
source "${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"

echo "Python  : $(which python3) — $(python3 --version 2>&1)"
echo "ROOT    : $(python3 -c 'import ROOT; print(ROOT.__version__)' 2>/dev/null || echo 'not found via PyROOT')"
echo ""

# ── Ensure gain_fit_models.py is co-located ───────────────────────────────────
MODELS_DIR=$(dirname "$GAIN_SCRIPT")
if [ ! -f "${MODELS_DIR}/gain_fit_models.py" ]; then
    echo "Copying gain_fit_models.py into script directory..."
    cp "$MODELS_SCRIPT" "${MODELS_DIR}/gain_fit_models.py"
fi

# ── Write a tiny wrapper that loads only channel $CHANNEL then calls the fit ──
# This avoids loading all 8065 channels and spending time on the full run.
WRAPPER="${OUTPUT_DIR}/run_test1ch.py"

cat > "$WRAPPER" <<'PYEOF'
#!/usr/bin/env python3
"""
Minimal 1-channel gain calibration test.
Loads channel CHANNEL_ID from the ROOT file, runs multigauss fit, prints result.
"""
import sys, os, math
import numpy as np

# ── inject the script directory so gain_fit_models is importable ──────────────
SCRIPT_DIR = os.environ.get("GAIN_SCRIPT_DIR", ".")
sys.path.insert(0, SCRIPT_DIR)

INPUT_ROOT  = os.environ["TEST_INPUT_ROOT"]
OUTPUT_DIR  = os.environ["TEST_OUTPUT_DIR"]
CHANNEL_ID  = int(os.environ.get("TEST_CHANNEL", "0"))

# ── Histogram grid (must match extract_charge_calib.py) ──────────────────────
BIN_WIDTH = 100
BIN_MAX   = 50_000
BINS      = np.arange(0, BIN_MAX + BIN_WIDTH, BIN_WIDTH)
BIN_CTRS  = (BINS[:-1] + BINS[1:]) / 2.0
N_BINS    = len(BIN_CTRS)

print(f"\nLoading channel {CHANNEL_ID} from {INPUT_ROOT} ...")

# ── Load histogram ────────────────────────────────────────────────────────────
hist = None
try:
    import uproot
    with uproot.open(INPUT_ROOT) as f:
        key = f"H_adcClean_{CHANNEL_ID}"
        if key not in f:
            key = f"H_adcClean_{CHANNEL_ID};1"
        h = f[key]
        vals, edges = h.to_numpy()
        ctrs = 0.5 * (edges[:-1] + edges[1:])
        hist = np.zeros(N_BINS, dtype=float)
        for c, v in zip(ctrs, vals):
            bi = int(np.argmin(np.abs(BIN_CTRS - c)))
            hist[bi] += v
    print(f"Loaded via uproot. Entries: {int(np.sum(hist))}")
except Exception as e:
    print(f"uproot failed ({e}), trying PyROOT...")

if hist is None:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    f = ROOT.TFile.Open(INPUT_ROOT, "READ")
    if not f or f.IsZombie():
        print(f"ERROR: Cannot open {INPUT_ROOT}"); sys.exit(1)
    h = f.Get(f"H_adcClean_{CHANNEL_ID}")
    if not h:
        print(f"ERROR: H_adcClean_{CHANNEL_ID} not found in file"); sys.exit(1)
    nb = h.GetNbinsX()
    ctrs_ = np.array([h.GetBinCenter(b) for b in range(1, nb+1)])
    vals_ = np.array([h.GetBinContent(b) for b in range(1, nb+1)])
    hist  = np.zeros(N_BINS, dtype=float)
    for c, v in zip(ctrs_, vals_):
        bi = int(np.argmin(np.abs(BIN_CTRS - c)))
        hist[bi] += v
    f.Close()
    print(f"Loaded via PyROOT. Entries: {int(np.sum(hist))}")

# ── Import fit models ─────────────────────────────────────────────────────────
from gain_fit_models import fit_channel, linear_fit_gain, peak_mu

# ── Peak detection (minimal, inline) ─────────────────────────────────────────
GAIN_DEFAULT = 6000
MIN_ENTRIES  = 2000

def smooth(h, s=3.0):
    hw = max(1, int(3.5*s))
    k  = np.exp(-0.5*(np.arange(-hw,hw+1)/s)**2)
    k /= k.sum()
    return np.convolve(np.pad(h.astype(float), hw, mode='edge'), k, mode='valid')[:len(h)]

def find_peaks(h, g=GAIN_DEFAULT):
    sm  = smooth(h, max(1.0, g/BIN_WIDTH/10))
    sep = max(2, int(0.5*g/BIN_WIDTH))
    cands = [i for i in range(1,len(sm)-1) if sm[i]>sm[i-1] and sm[i]>sm[i+1]]
    sel = []
    for i in cands:
        if not sel or i - sel[-1] >= sep:
            sel.append(i)
        elif sm[i] > sm[sel[-1]]:
            sel[-1] = i
    idxs = sel
    if len(idxs) < 2:
        return []
    win = max(2, int(2.0*g/BIN_WIDTH))
    peaks = sorted(float(BIN_CTRS[i]) for i in idxs)
    cands2 = [p for p in peaks if g/3 <= p <= g*3] or [p for p in peaks if 300 <= p <= 25000]
    if not cands2:
        return []
    fp = cands2[int(np.argmax([h[int(np.argmin(np.abs(BIN_CTRS-p)))] for p in cands2]))]
    chain = [fp]
    for p in peaks:
        if p <= fp: continue
        if 0.5*g <= p - chain[-1] <= 1.5*g:
            chain.append(p)
        if len(chain) >= 8: break
    return chain if len(chain) >= 2 else []

total = int(np.sum(hist))
print(f"Total counts in histogram: {total}")
if total < MIN_ENTRIES:
    print(f"WARN: Only {total} entries — below MIN_ENTRIES={MIN_ENTRIES}. Fit may fail.")

peaks = find_peaks(hist, GAIN_DEFAULT)
print(f"Detected peaks: {[f'{p:.0f}' for p in peaks]}")

if len(peaks) < 2:
    print("ERROR: Fewer than 2 peaks detected — cannot fit.")
    sys.exit(1)

spacings = [peaks[i+1]-peaks[i] for i in range(len(peaks)-1)]
gain_est = float(np.clip(np.median(spacings), 3200, 8500))
n_peaks  = min(len(peaks), 8)
peaks_fit = peaks[:n_peaks]

margin  = gain_est * 1.2
mask    = (BIN_CTRS >= peaks_fit[0] - margin) & (BIN_CTRS <= peaks_fit[-1] + margin)
x_fit   = BIN_CTRS[mask]
y_fit   = hist[mask]

print(f"\nFit window: [{x_fit[0]:.0f}, {x_fit[-1]:.0f}]  ({len(x_fit)} bins, {int(np.sum(y_fit))} counts)")
print(f"Gain estimate from peak spacing: {gain_est:.0f} ADC/PE")
print(f"Number of peaks to fit: {n_peaks}")
print(f"\nRunning multigauss fit ...")

import time
t0 = time.time()
result = fit_channel(x_fit, y_fit, n_peaks, peaks_fit, gain_est, "multigauss")
elapsed = time.time() - t0

print(f"Fit completed in {elapsed:.1f} s")
print("")
print("=" * 50)
if result['success']:
    print(f"  SUCCESS")
    print(f"  Gain        : {result['gain']:.1f} ± {result['gain_err']:.1f} ADC/PE")
    print(f"  Intercept   : {result['intercept']:.1f} ± {result['intercept_err']:.1f}")
    print(f"  chi2/ndf    : {result['chi2_dof']:.3f}")
    print(f"  R²          : {result['r2_linear']:.4f}")
    print(f"  n_peaks     : {result['n_peaks']}")
    g = result['gain']
    if 3200 <= g <= 8500 and result['chi2_dof'] <= 15 and result['r2_linear'] >= 0.9:
        print(f"  Classification: GOOD")
    else:
        print(f"  Classification: BAD (outside quality cuts)")
else:
    print(f"  FAILED — fit did not converge")
print("=" * 50)
print("")

# Save minimal CSV
import csv
out_csv = os.path.join(OUTPUT_DIR, f"test1ch_RUN1295_ch{CHANNEL_ID}.csv")
with open(out_csv, 'w', newline='') as fout:
    w = csv.writer(fout)
    w.writerow(['channel_id','success','gain','gain_err','intercept','chi2_dof','r2_linear','n_peaks','elapsed_s'])
    w.writerow([CHANNEL_ID,
                result['success'],
                f"{result['gain']:.2f}",
                f"{result['gain_err']:.2f}",
                f"{result['intercept']:.2f}",
                f"{result['chi2_dof']:.4f}",
                f"{result['r2_linear']:.4f}",
                result['n_peaks'],
                f"{elapsed:.2f}"])

print(f"Result saved to: {out_csv}")
PYEOF

# ── Run the wrapper ───────────────────────────────────────────────────────────
echo "Running single-channel fit..."
echo ""

export GAIN_SCRIPT_DIR="$MODELS_DIR"
export TEST_INPUT_ROOT="$MERGED_ROOT"
export TEST_OUTPUT_DIR="$OUTPUT_DIR"
export TEST_CHANNEL="$CHANNEL"

START=$(date +%s)
python3 "$WRAPPER"
STATUS=$?
END=$(date +%s)

echo ""
echo "============================================================"
if [ $STATUS -eq 0 ]; then
    echo "  TEST PASSED  ($(( END - START ))s)"
    echo "  If this ran fine: re-submit the full job with -cpu 8 -mem 16000"
    echo "  and check the queue with: hep_q -u \$USER"
else
    echo "  TEST FAILED (exit $STATUS)"
    echo "  Check the log: $LOG_FILE"
fi
echo "============================================================"
echo ""

deactivate
exit $STATUS
