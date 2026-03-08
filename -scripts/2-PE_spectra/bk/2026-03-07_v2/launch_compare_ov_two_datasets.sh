#!/bin/bash

# launch_compare_ov_two_datasets.sh
# Compare RTRAW custom-gain OV scans for two Ge-68 datasets:
#   Dataset A: RUNs 1253, 1257, 1259, 1260, 1261, 1262, 1263
#   Dataset B: RUNs 1053, 1054, 1055, 1056, 1057, 1058
#
# Produces three PNG plots (resolution / mean / sigma) each showing four
# data series: continuous PE and discrete PE for each dataset.
#
# Works on both CNAF and IHEP clusters.

set -e

echo "============================================"
echo "Ge-68 OV SCAN: TWO-DATASET COMPARISON"
echo "============================================"
echo ""

# ──────────────────────────────────────────────
# Cluster detection
# ──────────────────────────────────────────────

detect_cluster() {
    if [ -d "/storage/gpfs_data/juno" ]; then
        echo "CNAF"
    elif command -v eos &> /dev/null && [ -d "/junofs/users/gferrante" ]; then
        echo "IHEP"
    else
        echo "UNKNOWN"
    fi
}

CLUSTER=$(detect_cluster)

case $CLUSTER in
    "CNAF")
        SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/2-PE_spectra"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        BASE_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/energy_resolution"
        OUTPUT_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plots"
        LOG_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs"
        MATPLOTLIB_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/.matplotlib"
        ;;
    "IHEP")
        SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/2-PE_spectra"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/energy_resolution"
        OUTPUT_ROOT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plots"
        LOG_ROOT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs"
        MATPLOTLIB_DIR="/junofs/users/gferrante/.matplotlib"
        ;;
    *)
        echo "ERROR: Unknown cluster"
        echo "  CNAF: expects /storage/gpfs_data/juno"
        echo "  IHEP: expects 'eos' command + /junofs/users/gferrante"
        exit 1
        ;;
esac

echo "Cluster   : $CLUSTER"
echo "Base dir  : $BASE_DIR"
echo ""

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${OUTPUT_ROOT}/ov_two_datasets_${TIMESTAMP}"
SCRIPT="${SCRIPTS_BASE}/compare_ov_scan_two_datasets.py"
LOG_DIR="${LOG_ROOT}/ov_two_datasets"
LOG_FILE="${LOG_DIR}/ov_two_datasets_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "Output dir: $OUTPUT_DIR"
echo "Log file  : $LOG_FILE"
echo ""

# ──────────────────────────────────────────────
# JUNO environment
# ──────────────────────────────────────────────

if [ -f "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/setup-tao.sh" ]; then
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1"
elif [ -f "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4/setup-tao.sh" ]; then
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4"
elif [ -f "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3/setup-tao.sh" ]; then
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3"
else
    echo "ERROR: Cannot find JUNO release on CVMFS"
    exit 1
fi

echo "JUNO release: $JUNO_RELEASE"
source "${JUNO_RELEASE}/setup-tao.sh" || { echo "ERROR: setup-tao.sh failed"; exit 1; }
ROOT_PYTHONPATH="${PYTHONPATH}"

source "${PYTHON_ENV_ROOT}/bin/activate" || { echo "ERROR: venv activation failed"; exit 1; }
export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"
export MPLCONFIGDIR="$MATPLOTLIB_DIR"
mkdir -p "$MPLCONFIGDIR"

if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: Script not found: $SCRIPT"
    exit 1
fi

echo ""

# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

echo "Running comparison..."
echo ""

python "$SCRIPT" \
    --base-dir  "$BASE_DIR" \
    --output-dir "$OUTPUT_DIR"

EXIT_CODE=$?
deactivate

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "SUCCESS"
    echo "============================================"
    echo "Plots saved to: $OUTPUT_DIR"
    echo ""
    find "$OUTPUT_DIR" -name "*.png" | sort | while read f; do
        echo "  $(basename $f)"
    done
    echo ""
else
    echo ""
    echo "============================================"
    echo "ERROR: script exited with code $EXIT_CODE"
    echo "============================================"
    exit $EXIT_CODE
fi

echo "Log: $LOG_FILE"
echo ""
