#!/bin/bash
# launch_gain_calibration.sh - Run gain calibration on merged CHARGE histograms
# Works on both CNAF and IHEP clusters
set -e

# ========================================
# CONFIGURATION - HARDCODED RUN NUMBER
# ========================================

RUN=1112  # ← CHANGE THIS FOR DIFFERENT RUNS

echo "=========================================="
echo "RUN number: ${RUN}"
echo "=========================================="
echo ""

# ========================================
# CLUSTER DETECTION
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

if [ "$CLUSTER" = "UNKNOWN" ]; then
    echo "ERROR: Unknown cluster"
    echo "Cannot detect CNAF or IHEP environment"
    exit 1
fi

echo "Detected cluster: $CLUSTER"
echo ""

# ========================================
# CLUSTER-SPECIFIC PATHS
# ========================================

case $CLUSTER in
    "CNAF")
        SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        MATPLOTLIB_CACHE="/storage/gpfs_data/juno/junofs/users/gferrante/.matplotlib"
        ;;
    "IHEP")
        SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        MATPLOTLIB_CACHE="/junofs/users/gferrante/.matplotlib"
        ;;
esac

# Paths - NOW USING MERGED CHARGE FILES
MERGED_CHARGE_DIR="${SCRIPTS_BASE}/charge_merged"
OUTPUT_DIR="${SCRIPTS_BASE}/calibration_results/${RUN}/$(date +%Y-%m-%d_%H-%M-%S)"
GAIN_SCRIPT="${SCRIPTS_BASE}/gain_calibration.py"

# Input file - USING CHARGE_RUNXXX_merged.root
INPUT_FILE="${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root"

# Run name
RUN_NAME="RUN${RUN}"

# Log file
LOGDIR="${SCRIPTS_BASE}/logs/RUN${RUN}/gain_calib"
LOGFILE="${LOGDIR}/${RUN}_$(date +%Y-%m-%d_%H-%M-%S).log"

mkdir -p ${LOGDIR} ${OUTPUT_DIR}

# ========================================
# AUTO-DETECT JUNO RELEASE
# ========================================

echo "Detecting JUNO release for RUN ${RUN}..."

# Try to find the TAO version from the merged file's path/metadata
# Or use a reasonable default
if [ "$CLUSTER" = "CNAF" ]; then
    RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
else
    RTRAW_BASE="/eos/juno/tao-rtraw"
fi

# Try to find RUN directory to get TAO version
if [ "$CLUSTER" = "IHEP" ]; then
    # Use eos command
    TAO_VERSIONS=$(eos ls "$RTRAW_BASE" 2>/dev/null | grep -E '^T[0-9]+\.[0-9]+\.[0-9]+$' | sort -V -r | head -5)
    
    for TAO_VER in $TAO_VERSIONS; do
        for STREAM in "mix_stream" "TVT" "WT_TVT"; do
            RUN_PREFIX=$(printf "%08d" $((RUN / 100 * 100)))
            GROUP_PREFIX=$(printf "%08d" $((RUN / 1000 * 1000)))
            TEST_PATH="$RTRAW_BASE/$TAO_VER/$STREAM/$GROUP_PREFIX/$RUN_PREFIX/$RUN"
            
            if eos ls "$TEST_PATH" >/dev/null 2>&1; then
                TAO_VERSION=$TAO_VER
                break 2
            fi
        done
    done
else
    # Use find command
    FOUND_PATH=$(find "$RTRAW_BASE" -mindepth 5 -maxdepth 7 -type d -name "$RUN" 2>/dev/null | head -1)
    if [ -n "$FOUND_PATH" ]; then
        TAO_VERSION=$(echo "$FOUND_PATH" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')
    fi
fi

# Fallback to default if not found
if [ -z "$TAO_VERSION" ]; then
    echo "WARNING: Could not auto-detect TAO version for RUN ${RUN}"
    echo "Using default: T25.7.1"
    TAO_VERSION="T25.7.1"
else
    echo "Detected TAO version: $TAO_VERSION"
fi

# Map TAO version to JUNO version
JUNO_VERSION=$(echo "$TAO_VERSION" | sed 's/^T/J/')
JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION}"

# Verify JUNO release exists
if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
    echo "WARNING: JUNO release not found at $JUNO_RELEASE"
    echo "Trying fallback..."
    JUNO_VERSION_FALLBACK=$(echo "$TAO_VERSION" | sed 's/^T/J/' | sed 's/\.[0-9]$/\.1/')
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION_FALLBACK}"
    
    if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
        echo "ERROR: Cannot find JUNO release"
        echo "Tried: $JUNO_VERSION and $JUNO_VERSION_FALLBACK"
        exit 1
    fi
    echo "Using fallback: $JUNO_RELEASE"
fi

echo "JUNO release: $JUNO_RELEASE"
echo ""

# ========================================
# REDIRECT OUTPUT TO LOG
# ========================================
exec > "$LOGFILE" 2>&1

echo "=========================================="
echo "Gain Calibration for RUN ${RUN}"
echo "=========================================="
echo "Cluster: $CLUSTER"
echo "JUNO Release: $JUNO_VERSION"
echo "Started at: $(date)"
echo ""

# ========================================
# VERIFY INPUT FILE EXISTS
# ========================================
echo "Checking for merged CHARGE file..."

if [ ! -f "$INPUT_FILE" ]; then
    echo "ERROR: Merged CHARGE file not found: $INPUT_FILE"
    echo ""
    echo "You need to run merge first:"
    echo "  cd ${SCRIPTS_BASE}/charge_extraction/${RUN}"
    echo "  ./submit_merge.sh"
    echo ""
    echo "Expected file: CHARGE_RUN${RUN}_merged.root"
    exit 1
fi

FILE_SIZE=$(du -h "$INPUT_FILE" | cut -f1)
echo "✓ Input file found: $INPUT_FILE"
echo "  File size: $FILE_SIZE"
echo ""

# ========================================
# SETUP JUNO-TAO ENVIRONMENT
# ========================================
echo "Setting up JUNO-TAO environment..."
source ${JUNO_RELEASE}/setup-tao.sh

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to source JUNO-TAO environment!"
    exit 1
fi

echo "✓ JUNO-TAO environment loaded"

ROOT_PYTHONPATH="${PYTHONPATH}"

# ========================================
# ACTIVATE PYTHON VIRTUAL ENVIRONMENT
# ========================================
echo "Activating Python virtual environment..."
source "${PYTHON_ENV_ROOT}/bin/activate"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate Python virtual environment!"
    exit 1
fi

echo "✓ Python virtual environment activated"

export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"

# Set matplotlib cache directory to avoid permission errors
export MPLCONFIGDIR="$MATPLOTLIB_CACHE"
mkdir -p "$MPLCONFIGDIR"

echo ""
echo "Python: $(which python)"
echo "Version: $(python --version)"
echo ""

# Check packages
echo "Checking Python packages..."
python -c "import numpy, scipy, matplotlib" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Some packages missing (numpy, scipy, matplotlib)"
fi
echo ""

# ========================================
# VERIFY GAIN SCRIPT EXISTS
# ========================================
if [ ! -f "$GAIN_SCRIPT" ]; then
    echo "ERROR: Gain calibration script not found: $GAIN_SCRIPT"
    exit 1
fi

echo "✓ Gain calibration script found"
echo ""

# ========================================
# CREATE OUTPUT DIRECTORY
# ========================================
mkdir -p "$OUTPUT_DIR"
echo "✓ Output directory ready: $OUTPUT_DIR"
echo ""

# ========================================
# RUN GAIN CALIBRATION
# ========================================
echo "=========================================="
echo "Starting gain calibration..."
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Cluster: $CLUSTER"
echo "  Input: $INPUT_FILE"
echo "  Output: $OUTPUT_DIR"
echo "  Run name: $RUN_NAME"
echo "  JUNO version: $JUNO_VERSION"
echo "  Note: Processing ADC histograms from merged CHARGE file"
echo ""
echo "Processing all channels (including OOR if present)..."
echo "This may take 5-15 minutes..."
echo ""

START_TIME=$(date +%s)

python "$GAIN_SCRIPT" "$INPUT_FILE" "$OUTPUT_DIR" "$RUN_NAME"

CALIB_STATUS=$?

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "=========================================="

if [ $CALIB_STATUS -eq 0 ]; then
    echo "✓ SUCCESS: Gain calibration completed!"
    echo ""
    echo "Processing time: ${MINUTES}m ${SECONDS}s"
    echo ""
    echo "Output files:"
    
    # Check for different output formats (scipy_workflow or root_tspectrum)
    GOOD_TXT_SCIPY="${OUTPUT_DIR}/scipy_workflow_good_${RUN_NAME}.txt"
    GOOD_TXT_ROOT="${OUTPUT_DIR}/root_tspectrum_good_${RUN_NAME}.txt"
    BAD_TXT="${OUTPUT_DIR}/scipy_workflow_bad_${RUN_NAME}.txt"
    NOFIT_TXT="${OUTPUT_DIR}/scipy_workflow_nofit_${RUN_NAME}.txt"
    PLOT_DIR="${OUTPUT_DIR}/plots_${RUN_NAME}"
    
    # Check which format was produced
    if [ -f "$GOOD_TXT_SCIPY" ]; then
        GOOD_TXT="$GOOD_TXT_SCIPY"
    elif [ -f "$GOOD_TXT_ROOT" ]; then
        GOOD_TXT="$GOOD_TXT_ROOT"
    fi
    
    if [ -f "$GOOD_TXT" ]; then
        echo "  ✓ Good fits: $(basename $GOOD_TXT)"
        LINE_COUNT=$(wc -l < "$GOOD_TXT")
        echo "    Path: $GOOD_TXT"
        echo "    Channels: ${LINE_COUNT} lines"
    fi
    
    if [ -f "$BAD_TXT" ]; then
        echo "  ✓ Bad fits: $(basename $BAD_TXT)"
        LINE_COUNT=$(wc -l < "$BAD_TXT")
        echo "    Channels: ${LINE_COUNT} lines"
    fi
    
    if [ -f "$NOFIT_TXT" ]; then
        echo "  ✓ No fits: $(basename $NOFIT_TXT)"
        LINE_COUNT=$(wc -l < "$NOFIT_TXT")
        echo "    Channels: ${LINE_COUNT} lines"
    fi
    
    if [ -d "$PLOT_DIR" ]; then
        PLOT_COUNT=$(find "$PLOT_DIR" -name "*.png" 2>/dev/null | wc -l)
        echo "  ✓ Sample plots: $PLOT_DIR"
        echo "    Files: ${PLOT_COUNT} PNG"
    fi
    
    echo ""
    echo "View results:"
    if [ -f "$GOOD_TXT" ]; then
        echo "  head -20 $GOOD_TXT"
    fi
    if [ -d "$PLOT_DIR" ]; then
        echo "  ls $PLOT_DIR/*.png | head"
    fi
    echo ""
    echo "Use this calibration file for energy spectrum:"
    echo "  $GOOD_TXT"
else
    echo "✗ ERROR: Gain calibration failed (exit code $CALIB_STATUS)"
    exit 1
fi

echo "=========================================="
echo "Finished at: $(date)"
echo "=========================================="

deactivate

echo ""
echo "Log saved: $LOGFILE"
echo ""
echo "Next steps:"
echo "  1. Check calibration results:"
echo "     cat $GOOD_TXT | head -20"
echo ""
echo "  2. Run energy spectrum extraction:"
echo "     ./launch_get_spectrum_calib.sh ${RUN} rtraw ${RUN}"
echo "     (This will use calibration from RUN${RUN})"
echo ""
