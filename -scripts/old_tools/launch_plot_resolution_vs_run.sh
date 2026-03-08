#!/bin/bash

# launch_plot_resolution_vs_run.sh - Create multi-run resolution trend plots
# MODIFIED VERSION: Dynamically finds latest diagnostic plot files for each RUN

set -e

# ========================================
# CONFIGURATION
# ========================================

echo "==========================================="
echo "Multi-Run Energy Resolution Trend Analysis"
echo "==========================================="
echo ""

# ========================================
# AUTO-DETECT JUNO_RELEASE
# ========================================

# Find a recent RUN directory to determine JUNO version
RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
PLOT_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plots/energy_resolution"

SAMPLE_RUN=$(find "$PLOT_BASE" -maxdepth 1 -type d -name "[0-9]*" 2>/dev/null | head -1 | xargs basename)

if [ -n "$SAMPLE_RUN" ]; then
    FOUND_PATHS=$(find "$RTRAW_BASE" -mindepth 5 -maxdepth 7 -type d -name "$SAMPLE_RUN" 2>/dev/null)
    if [ -n "$FOUND_PATHS" ]; then
        INPUT_BASE=$(echo "$FOUND_PATHS" | head -n 1)
        TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')

        if [ -n "$TAO_VERSION" ]; then
            JUNO_VERSION=$(echo "$TAO_VERSION" | sed 's/^T/J/')
            JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION}"

            if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
                JUNO_VERSION_FALLBACK=$(echo "$TAO_VERSION" | sed 's/^T/J/' | sed 's/\.[0-9]$/\.1/')
                JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION_FALLBACK}"
            fi
        else
            JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3"
        fi
    else
        JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3"
    fi
else
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.3"
fi

echo "JUNO Release: ${JUNO_RELEASE}"
echo ""

# ========================================
# PATHS - MODIFIED OUTPUT DIRECTORY
# ========================================

INPUT_DIR="$PLOT_BASE"
OUTPUT_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plots/resolution_vs_OV/$(date +%Y-%m-%d_%H-%M-%S)"
PLOT_SCRIPT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plot_resolution_vs_run.py"
PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
LOG_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/resolution_vs_OV"
LOG_FILE="${LOG_DIR}/resolution_vs_OV_$(date +%Y-%m-%d_%H-%M-%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Redirect output to log file
exec > "$LOG_FILE" 2>&1

echo "Started at: $(date)"
echo ""

# ========================================
# VERIFY INPUT DIRECTORY
# ========================================

if [ ! -d "$INPUT_DIR" ]; then
    echo "ERROR: Input directory not found: $INPUT_DIR"
    echo ""
    echo "This script expects diagnostic plot ROOT files from plot_energy_resolution.py"
    echo "Run launch_plot_energy_resolution.sh first for each RUN you want to analyze"
    exit 1
fi

echo "✓ Input directory found: $INPUT_DIR"

# ========================================
# DYNAMIC LOOKUP - Find latest diagnostic file for each RUN
# ========================================

echo ""
echo "Scanning for diagnostic ROOT files with dynamic lookup..."
echo ""

# Find all RUN directories
RUN_DIRS=$(find "$INPUT_DIR" -maxdepth 1 -type d -name "[0-9]*" 2>/dev/null | sort)

if [ -z "$RUN_DIRS" ]; then
    echo "ERROR: No RUN directories found in $INPUT_DIR"
    exit 1
fi

# For each RUN, find the latest diagnostic file
DIAGNOSTIC_FILES=""
NUM_RUNS=0

for RUN_DIR in $RUN_DIRS; do
    RUN_NUM=$(basename "$RUN_DIR")

    # Find most recent directory for this RUN
    LATEST_DIR=$(ls -dt "${RUN_DIR}"/*/ 2>/dev/null | head -1)

    if [ -z "$LATEST_DIR" ]; then
        echo "  WARNING: No timestamped directories found for RUN${RUN_NUM}"
        continue
    fi

    # Look for diagnostic_plots file in latest directory
    DIAG_FILE=$(find "$LATEST_DIR" -maxdepth 1 -name "diagnostic_plots_RUN${RUN_NUM}.root" -type f 2>/dev/null | head -1)

    if [ -n "$DIAG_FILE" ]; then
        echo "  ✓ RUN${RUN_NUM}: Found $(basename $(dirname $DIAG_FILE))/$(basename $DIAG_FILE)"
        DIAGNOSTIC_FILES="$DIAGNOSTIC_FILES $DIAG_FILE"
        NUM_RUNS=$((NUM_RUNS + 1))
    else
        echo "  ✗ RUN${RUN_NUM}: No diagnostic_plots file found in $LATEST_DIR"
    fi
done

echo ""

if [ $NUM_RUNS -eq 0 ]; then
    echo "ERROR: No diagnostic plots ROOT files found!"
    echo ""
    echo "Expected pattern: ${INPUT_DIR}/[RUN]/[TIMESTAMP]/diagnostic_plots_RUN*.root"
    echo ""
    echo "Current directory structure:"
    echo ""
    ls -d "$INPUT_DIR"/*/ 2>/dev/null | while read rundir; do
        echo "  $(basename $rundir):"
        ls -d "$rundir"*/ 2>/dev/null | while read timestamp; do
            echo "    $(basename $timestamp):"
            ls -1 "$timestamp"/*.root 2>/dev/null | xargs -n 1 basename | sed 's/^/      /'
        done
    done
    echo ""
    echo "SOLUTION:"
    echo "  1. Run launch_plot_energy_resolution.sh for each RUN"
    echo "     Example: ./launch_plot_energy_resolution.sh 1053"
    echo "  2. This creates diagnostic_plots_RUN*.root files"
    echo "  3. Then run this script to compare multiple runs"
    exit 1
fi

echo "✓ Found $NUM_RUNS diagnostic plots ROOT files"
echo ""

# List found RUNs
echo "Detected RUNs:"
for DIAG_FILE in $DIAGNOSTIC_FILES; do
    RUN_NUM=$(echo "$DIAG_FILE" | sed -n 's/.*diagnostic_plots_RUN\([0-9]\+\).root/\1/p')
    TIMESTAMP=$(basename $(dirname "$DIAG_FILE"))
    echo "  RUN${RUN_NUM} (${TIMESTAMP})"
done
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

echo "==========================================="
echo "Creating multi-run resolution trend plots..."
echo "==========================================="
echo ""

python "$PLOT_SCRIPT" --input-dir "$INPUT_DIR" --output-dir "$OUTPUT_DIR"

PLOT_STATUS=$?

echo ""

if [ $PLOT_STATUS -eq 0 ]; then
    echo "==========================================="
    echo "✓ SUCCESS: Multi-run resolution plots created!"
    echo "==========================================="
    echo ""
    echo "Output directory: $OUTPUT_DIR"
    echo ""
    echo "Generated plots:"
    ls -1 "$OUTPUT_DIR"/*.png 2>/dev/null | xargs -n 1 basename || echo "  (No PNG files found)"
    echo ""
    echo "Text summary:"
    if [ -f "$OUTPUT_DIR/resolution_summary.txt" ]; then
        echo "  ✓ resolution_summary.txt"
        echo ""
        echo "Summary statistics:"
        grep -v "^#" "$OUTPUT_DIR/resolution_summary.txt" | awk 'NF>0' | wc -l | xargs echo "    Total entries:"
    else
        echo "  (No text summary found)"
    fi
else
    echo "✗ ERROR: Plotting failed (exit code $PLOT_STATUS)"
    exit 1
fi

deactivate

echo ""
echo "Finished at: $(date)"
echo "Log saved: $LOG_FILE"
echo ""

echo "==========================================="
echo "To view results:"
echo "  cd $OUTPUT_DIR"
echo "  ls -lh *.png"
echo "  cat resolution_summary.txt"
echo "==========================================="
