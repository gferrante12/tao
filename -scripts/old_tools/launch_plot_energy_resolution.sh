#!/bin/bash

# launch_plot_energy_resolution.sh - Create energy resolution diagnostic plots
# ADAPTED VERSION: Automatically finds spectrum files from get_spectrum output

set -e

# ========================================
# CONFIGURATION
# ========================================

if [ -z "$1" ]; then
    echo "ERROR: RUN number not provided!"
    echo ""
    echo "Usage: $0 RUN [CUTLABEL]"
    echo ""
    echo "Examples:"
    echo "  $0 1053              # Auto-detect most recent no_cut directory"
    echo "  $0 1053 no_cut       # Specific cut mode"
    echo "  $0 1053 pe_cut20     # Specific PE cut"
    exit 1
fi

RUN=$1
CUTLABEL=${2:-"no_cut"}  # Default to no_cut if not specified

echo "=========================================="
echo "Energy Resolution Plots for RUN ${RUN}"
echo "=========================================="
echo ""

# ========================================
# AUTO-DETECT LATEST SPECTRUM DIRECTORY
# ========================================

BASE_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/energy_resolution/RUN${RUN}"

# Find most recent directory matching the cut label
SPECTRUM_DIR=$(find "$BASE_DIR" -maxdepth 1 -type d -name "${RUN}_${CUTLABEL}_*" 2>/dev/null | sort -r | head -1)

if [ -z "$SPECTRUM_DIR" ]; then
    echo "ERROR: No spectrum directory found for RUN ${RUN} with cut label '${CUTLABEL}'"
    echo ""
    echo "Searched in: $BASE_DIR"
    echo "Pattern: ${RUN}_${CUTLABEL}_*"
    echo ""
    echo "Available directories:"
    ls -1d "$BASE_DIR"/*/ 2>/dev/null | xargs -n 1 basename || echo "  (none found)"
    echo ""
    echo "Tip: Specify cut label explicitly if different from default"
    echo "     e.g., $0 $RUN pe_cut20"
    exit 1
fi

echo "Found spectrum directory:"
echo "  $SPECTRUM_DIR"
echo ""

# ========================================
# FIND INPUT FILES
# ========================================

# Look for MERGED file first (better statistics)
INPUT_FILE="${SPECTRUM_DIR}/spectrum_RUN${RUN}-MERGED.root"

if [ ! -f "$INPUT_FILE" ]; then
    # Fall back to first individual file
    INPUT_FILE=$(find "$SPECTRUM_DIR" -name "spectrum_RUN${RUN}-*.root" -type f 2>/dev/null | sort | head -1)
fi

if [ -z "$INPUT_FILE" ] || [ ! -f "$INPUT_FILE" ]; then
    echo "ERROR: No spectrum files found in $SPECTRUM_DIR"
    echo ""
    echo "Expected files:"
    echo "  spectrum_RUN${RUN}-MERGED.root (preferred)"
    echo "  OR spectrum_RUN${RUN}-001.root, -002.root, etc."
    echo ""
    echo "Available files:"
    ls -1 "$SPECTRUM_DIR"/*.root 2>/dev/null || echo "  (no ROOT files found)"
    exit 1
fi

echo "Using spectrum file: $(basename $INPUT_FILE)"
FILE_SIZE=$(du -h "$INPUT_FILE" | cut -f1)
echo "  File size: $FILE_SIZE"
echo ""

# ========================================
# AUTO-DETECT JUNO_RELEASE FROM RTRAW PATH
# ========================================

RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
FOUND_PATHS=$(find "$RTRAW_BASE" -mindepth 5 -maxdepth 7 -type d -name "$RUN" 2>/dev/null)

if [ -z "$FOUND_PATHS" ]; then
    echo "WARNING: RUN ${RUN} not found in RTRAW, using fallback..."
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3"
else
    INPUT_BASE=$(echo "$FOUND_PATHS" | head -n 1)
    TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')

    if [ -z "$TAO_VERSION" ]; then
        JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3"
    else
        JUNO_VERSION=$(echo "$TAO_VERSION" | sed 's/^T/J/')
        JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION}"

        if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
            JUNO_VERSION_FALLBACK=$(echo "$TAO_VERSION" | sed 's/^T/J/' | sed 's/\.[0-9]$/\.1/')
            JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION_FALLBACK}"
        fi
    fi
fi

echo "JUNO Release: ${JUNO_RELEASE}"
echo ""

# ========================================
# OUTPUT SETUP
# ========================================

OUTPUT_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plots/energy_resolution/${RUN}/$(date +%Y-%m-%d_%H-%M-%S)"
PLOT_SCRIPT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plot_energy_resolution.py"
RUN_NAME="RUN${RUN}"
PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
LOG_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/${RUN}_plot_resolution"
LOG_FILE="${LOG_DIR}/${RUN}_plot_resolution_$(date +%Y-%m-%d_%H-%M-%S).log"

mkdir -p "$LOG_DIR"
exec > "$LOG_FILE" 2>&1

echo "Started at: $(date)"
echo ""
echo "Configuration:"
echo "  RUN: ${RUN}"
echo "  Cut label: ${CUTLABEL}"
echo "  Input: $INPUT_FILE"
echo "  Output: $OUTPUT_DIR"
echo ""

# ========================================
# ENVIRONMENT SETUP
# ========================================

echo "Setting up JUNO-TAO environment..."
source ${JUNO_RELEASE}/setup-tao.sh
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
export MPLCONFIGDIR="/storage/gpfs_data/juno/junofs/users/gferrante/.matplotlib"
mkdir -p "$MPLCONFIGDIR"

# Verify script exists
if [ ! -f "$PLOT_SCRIPT" ]; then
    echo "ERROR: Plot script not found: $PLOT_SCRIPT"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "✓ Output directory ready: $OUTPUT_DIR"
echo ""

# ========================================
# RUN PLOTTING
# ========================================

echo "=========================================="
echo "Creating energy resolution plots..."
echo "=========================================="
echo ""

python "$PLOT_SCRIPT" "$INPUT_FILE" "$RUN_NAME" --output-dir "$OUTPUT_DIR"
PLOT_STATUS=$?

echo ""

if [ $PLOT_STATUS -eq 0 ]; then
    echo "=========================================="
    echo "✓ SUCCESS: Energy resolution plots created!"
    echo "=========================================="
    echo ""
    echo "Output directory: $OUTPUT_DIR"
    echo ""
    echo "Generated plots:"
    ls -1 "$OUTPUT_DIR"/*.png 2>/dev/null || echo "  (No PNG files found)"
    echo ""
    echo "ROOT file:"
    ls -1 "$OUTPUT_DIR"/*.root 2>/dev/null || echo "  (No ROOT file found)"
else
    echo "✗ ERROR: Plotting failed (exit code $PLOT_STATUS)"
    exit 1
fi

deactivate

echo ""
echo "Finished at: $(date)"
echo "Log saved: $LOG_FILE"
echo ""
echo "=========================================="
echo "Next step:"
echo "  Run multi-run analysis:"
echo "  ./launch_plot_resolution_vs_run.sh"
echo "=========================================="
