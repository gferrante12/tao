#!/bin/bash

# launch_compare_run_groups.sh - Master script to run all run group comparisons
# Works on both CNAF and IHEP clusters

set -e

echo "================================================================"
echo "COMPREHENSIVE RUN GROUP COMPARISONS"
echo "================================================================"
echo ""
echo "This script will perform all comparison analyses:"
echo "  1. Cs-137: RUN 1112 vs 1344 (RTRAW + ESD)"
echo "  2. Ge-68 OV Scan: RUNs 1253, 1257, 1259, 1260, 1261, 1262, 1263"
echo "  3. Ge-68 Specific: RUNs 1157, 1236, 1295, 1296, 1319"
echo ""
echo "Usage:"
echo "  ./launch_compare_run_groups.sh"
echo ""

# ========================================
# Hardcoded pos-60 file basenames
# ========================================
# RUN1112 CLS pos-60: RTRAW file basenames
POS60_1112_FILES=(174 175 176)
# RUN1344 CLS pos-60: RTRAW file basenames
POS60_1344_FILES=(109 110 111)

POS60_1112_ARGS="--pos60-1112 ${POS60_1112_FILES[*]}"
POS60_1344_ARGS="--pos60-1344 ${POS60_1344_FILES[*]}"

echo "  RUN1112 pos-60 files : ${POS60_1112_FILES[*]}  (hardcoded)"
echo "  RUN1344 pos-60 files : ${POS60_1344_FILES[*]}  (hardcoded)"
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

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${OUTPUT_ROOT}/comprehensive_comparison_${TIMESTAMP}"
SCRIPT="${SCRIPTS_BASE}/compare_run_groups.py"
LOG_DIR="${LOG_ROOT}/comprehensive_comparison"
LOG_FILE="${LOG_DIR}/comprehensive_comparison_${TIMESTAMP}.log"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

# Redirect output
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Timestamp: $TIMESTAMP"
echo "Log file: $LOG_FILE"
echo "Output root directory: $OUTPUT_DIR"
echo ""

# ========================================
# ENVIRONMENT SETUP
# ========================================

# Auto-detect JUNO version (try multiple fallbacks)
if [ -f "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/setup-tao.sh" ]; then
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1"
elif [ -f "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4/setup-tao.sh" ]; then
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4"
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
# RUN ALL COMPARISONS
# ========================================

START_TIME=$(date +%s)

echo "================================================================"
echo "RUNNING ALL COMPARISONS"
echo "================================================================"
echo ""

python "$SCRIPT" \
    --base-dir "$BASE_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --all \
    $POS60_1112_ARGS \
    $POS60_1344_ARGS

EXIT_CODE=$?

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

deactivate

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "================================================================"
    echo "ALL COMPARISONS COMPLETED SUCCESSFULLY"
    echo "================================================================"
    echo ""
    echo "Elapsed time: ${ELAPSED} seconds"
    echo "Output directory: $OUTPUT_DIR"
    echo ""
    echo "Directory structure:"
    if command -v tree &> /dev/null; then
        tree -L 2 "$OUTPUT_DIR" 2>/dev/null
    else
        echo "Output contents:"
        find "$OUTPUT_DIR" -type f -name "*.png" | sort
    fi
    echo ""
    
    # Count total plots
    TOTAL_PLOTS=$(find "$OUTPUT_DIR" -name "*.png" -type f | wc -l)
    echo "Total plots generated: $TOTAL_PLOTS"
    echo ""
    
    # Summary by comparison type
    echo "Summary by comparison type:"
    echo ""
    
    CS137_COUNT=$(find "$OUTPUT_DIR/cs137_"* -name "*.png" -type f 2>/dev/null | wc -l)
    if [ $CS137_COUNT -gt 0 ]; then
        echo "  Cs-137 comparisons: $CS137_COUNT plots"
        find "$OUTPUT_DIR/cs137_"* -name "*.png" -type f 2>/dev/null | while read f; do
            echo "    - $(basename $f)"
        done
        echo ""
    fi
    
    OV_COUNT=$(find "$OUTPUT_DIR/ge68_ov_scan" -name "*.png" -type f 2>/dev/null | wc -l)
    if [ $OV_COUNT -gt 0 ]; then
        echo "  Ge-68 OV scan: $OV_COUNT plots"
        find "$OUTPUT_DIR/ge68_ov_scan" -name "*.png" -type f 2>/dev/null | while read f; do
            echo "    - $(basename $f)"
        done
        echo ""
    fi
    
    SPECIFIC_COUNT=$(find "$OUTPUT_DIR/ge68_specific" -name "*.png" -type f 2>/dev/null | wc -l)
    if [ $SPECIFIC_COUNT -gt 0 ]; then
        echo "  Ge-68 specific runs: $SPECIFIC_COUNT plots"
        find "$OUTPUT_DIR/ge68_specific" -name "*.png" -type f 2>/dev/null | while read f; do
            echo "    - $(basename $f)"
        done
        echo ""
    fi
    
else
    echo ""
    echo "================================================================"
    echo "ERROR: Comparison failed"
    echo "================================================================"
    echo "Elapsed time: ${ELAPSED} seconds"
    exit $EXIT_CODE
fi

echo "Log saved: $LOG_FILE"
echo ""
echo "================================================================"
echo "To view results:"
echo "  cd $OUTPUT_DIR"
echo "  ls -R *.png"
echo "================================================================"
echo ""
