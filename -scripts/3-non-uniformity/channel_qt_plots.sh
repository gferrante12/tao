#!/bin/bash
# channel_qt_plots.sh  —  RUN 1295 TDC vs ADC plots
# File discovery mirrors launch_extract_charge_calib.sh:
#   CNAF → POSIX filesystem
#   IHEP → EOS CLI (eos ls) for discovery + XRootD URL for ROOT I/O
# ─────────────────────────────────────────────────────────────────────────────
set -e

RUN=1295
JOB_ID=001

JUNO_RELEASE=/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1

# ── Cluster detection (mirrors detect_cluster() in launch_extract_charge_calib.sh)
if [ -d "/storage/gpfs_data/juno" ]; then
    CLUSTER="CNAF"
    SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/3-non-uniformity"
    PYTHON_ENV_ROOT=/storage/gpfs_data/juno/junofs/users/gferrante/python_env
    LOGS_DIR=/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/RUN${RUN}/qt_plots
elif command -v eos &> /dev/null && [ -d "/junofs/users/gferrante" ]; then
    CLUSTER="IHEP"
    SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/3-non-uniformity"
    PYTHON_ENV_ROOT=/junofs/users/gferrante/python_env
    LOGS_DIR=/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/RUN${RUN}/qt_plots
else
    CLUSTER="LOCAL"
    PYTHON_ENV_ROOT="${HOME}/python_env"
    LOGS_DIR="./qt_plots_logs"
fi

QT_SCRIPT="${SCRIPTS_BASE}/channel_qt_plots.py"

# ── Performance / cache fixes ─────────────────────────────────────────────────
#
# 1. Matplotlib: AFS home is not writable for the cache → redirect to /tmp.
#    This avoids the slow AFS probe + warning on every import.
export MPLCONFIGDIR="/tmp/matplotlib_${USER}_$$"
mkdir -p "${MPLCONFIGDIR}"
#
# 2. XRootD: the installed seckrb5 plugin (v5.8.4) is incompatible with the
#    SecClnt version (v5.7.3).  Each TFile::Open() tries Kerberos, fails, and
#    only then falls back to unix/gsi — adding several seconds per file open.
#    Tell XRootD to skip krb5 entirely and go straight to unix+gsi.
export XrdSecPROTOCOL="unix,gsi"
#    Suppress the repeated incompatibility warnings from the plugin loader:
export XrdSecDISABLEKRB5=1

# ── Logging ──────────────────────────────────────────────────────────────────
mkdir -p "${LOGS_DIR}"
LOG_FILE="${LOGS_DIR}/qt_plots_${RUN}_${JOB_ID}_$(date +%Y%m%d_%H%M%S).log"
exec > "${LOG_FILE}" 2>&1

echo "Cluster    : ${CLUSTER}"
echo "RUN        : ${RUN}"
echo "Job ID     : ${JOB_ID}"
echo "Log file   : ${LOG_FILE}"
echo "MPLCONFIGDIR : ${MPLCONFIGDIR}"
echo "XrdSecPROTOCOL : ${XrdSecPROTOCOL}"
echo ""

# ── JUNO-TAO environment ─────────────────────────────────────────────────────
echo "Setting up JUNO-TAO environment..."
source "${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="${PYTHONPATH}"

echo "Activating Python environment..."
source "${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"

# ── Analysis ──────────────────────────────────────────────────────────────────
# channel_qt_plots.py auto-discovers the first RTRAW file for RUN 1295:
#   IHEP → eos ls /eos/juno/tao-rtraw  →  XRootD URL (root://junoeos01.ihep.ac.cn/...)
#   CNAF → glob /storage/gpfs_data/juno/.../1295/*.rtraw
#
# --n-channels 2    → 2 sample channels (one scatter PNG each) + summary PNG
# --max-events 5000 → fast sample; raise to 50000+ for production-quality plots
#
# Optional overrides (uncomment as needed):
#   --rtraw-file    root://junoeos01.ihep.ac.cn//eos/juno/tao-rtraw/.../file.rtraw
#   --output-dir    /path/to/custom_output
#   --n-channels    40
#   --max-events    50000

echo ""
echo "Running TDC vs ADC channel plots for RUN ${RUN}..."
python "$QT_SCRIPT" \
    --n-channels 2      \
    --max-events 5000   \
    --tdc-lo 0          \
    --tdc-hi 600

deactivate

# Clean up per-job matplotlib cache
rm -rf "${MPLCONFIGDIR}"

echo ""
echo "Done."
