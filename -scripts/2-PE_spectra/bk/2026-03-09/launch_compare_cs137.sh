#!/bin/bash

# launch_compare_cs137.sh - Cs-137 CLS pipeline comparison
#   RUN 1112 (full + CLS position 60) vs RUN 1344 (full + CLS position 60)
#   8 pipeline combinations × 3 metrics (resolution / mean / sigma)
# Works on both CNAF and IHEP clusters
#
# Usage:
#   ./launch_compare_cs137.sh

set -e

# ========================================
# Hardcoded pos-60 file basenames
# ========================================
# RUN1112 CLS pos-60: RTRAW file basenames
POS60_1112_FILES=(174 175 176)
# RUN1344 CLS pos-60: RTRAW file basenames
POS60_1344_FILES=(109 110 111)

POS60_1112_ARGS="--pos60-1112 ${POS60_1112_FILES[*]}"
POS60_1344_ARGS="--pos60-1344 ${POS60_1344_FILES[*]}"

echo "============================================"
echo "Cs-137 CLS PIPELINE COMPARISON"
echo "  RUN 1112  (full CLS + pos-60)"
echo "  RUN 1344  (full CLS + pos-60)"
echo "============================================"
echo "  RUN1112 pos-60 files: ${POS60_1112_FILES[*]}  (hardcoded)"
echo "  RUN1344 pos-60 files: ${POS60_1344_FILES[*]}  (hardcoded)"
echo ""

# ========================================
# Cluster Detection and Path Configuration
# ========================================

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
        echo "Please check:"
        echo "  CNAF: /storage/gpfs_data/juno"
        echo "  IHEP: command 'eos' available and /junofs/users/gferrante exists"
        exit 1
        ;;
esac

echo "Cluster: $CLUSTER"
echo ""

# ========================================
# CONFIGURATION
# ========================================

OUTPUT_DIR="${OUTPUT_ROOT}/compare_cs137/$(date +%Y%m%d_%H%M%S)"
SCRIPT="${SCRIPTS_BASE}/compare_run_groups.py"
LOG_DIR="${LOG_ROOT}/compare_cs137"
LOG_FILE="${LOG_DIR}/compare_cs137_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

# Redirect output
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Log file: $LOG_FILE"
echo "Output directory: $OUTPUT_DIR"
echo ""

# ========================================
# ENVIRONMENT SETUP
# ========================================

# Auto-detect JUNO version (try multiple fallbacks)
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

echo "JUNO Release: $JUNO_RELEASE"
echo ""

echo "Setting up JUNO-TAO environment..."
source "${JUNO_RELEASE}/setup-tao.sh"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to source JUNO-TAO environment!"
    exit 1
fi

ROOT_PYTHONPATH="${PYTHONPATH}"

echo "Activating Python virtual environment..."
source "${PYTHON_ENV_ROOT}/bin/activate"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate Python virtual environment!"
    exit 1
fi

export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"
export MPLCONFIGDIR="$MATPLOTLIB_DIR"
mkdir -p "$MPLCONFIGDIR"

# Verify script exists
if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: Comparison script not found: $SCRIPT"
    exit 1
fi

echo ""

# ========================================
# RUN COMPARISON
# ========================================

echo "Running Cs-137 comparison..."
echo ""

python "$SCRIPT" \
    --base-dir "$BASE_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --cs137 \
    $POS60_1112_ARGS \
    $POS60_1344_ARGS

EXIT_CODE=$?

deactivate

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "SUCCESS"
    echo "============================================"
    echo "Comparison plots saved to: $OUTPUT_DIR"
    echo ""
    echo "Generated plots:"
    find "$OUTPUT_DIR" -name "*.png" -type f | while read f; do
        echo "  $(basename $f)"
    done
    echo ""
else
    echo ""
    echo "============================================"
    echo "ERROR: Comparison failed"
    echo "============================================"
    exit $EXIT_CODE
fi

echo "Log saved: $LOG_FILE"
echo ""
