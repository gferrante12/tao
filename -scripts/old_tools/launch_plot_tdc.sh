#!/bin/bash

set -e
shopt -s nullglob

# =====================================================
# launch_plot_tdc.sh
# =====================================================

if [ -z "$1" ]; then
    echo "ERROR: RUN number not provided!"
    echo ""
    echo "Usage: $0 RUN [MODE]"
    echo ""
    echo "Modes:"
    echo "  process  - Process RTRAW files individually (default)"
    echo "  merge    - Merge TDC histograms from ROOT files"
    echo ""
    echo "Examples:"
    echo "  $0 1065             # Process RTRAW files"
    echo "  $0 1065 merge       # Merge TDC ROOT files"
    exit 1
fi

RUN=$1
MODE=${2:-process}

echo "=========================================="
echo "TDC ANALYSIS FOR RUN $RUN"
echo "=========================================="
echo "Mode: $MODE"
echo ""

# =====================================================
# Find RTRAW data (same logic as launch_get_spectrum_calib.sh)
# =====================================================
if [ "$MODE" = "process" ]; then
    RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
    FOUND_PATHS=$(find "$RTRAW_BASE" -mindepth 5 -maxdepth 7 -type d -name "$RUN" 2>/dev/null)

    if [ -z "$FOUND_PATHS" ]; then
        echo "ERROR: RUN $RUN not found in $RTRAW_BASE"
        echo ""
        echo "Searched structure:"
        echo "  $RTRAW_BASE/<TAO-version>/<detector>/<year>/<month>/<run>/"
        exit 1
    fi

    NUM_PATHS=$(echo "$FOUND_PATHS" | wc -l)
    if [ $NUM_PATHS -gt 1 ]; then
        echo "WARNING: Multiple paths found for RUN $RUN:"
        echo "$FOUND_PATHS"
        echo ""
        echo "Using first match:"
        INPUT_BASE=$(echo "$FOUND_PATHS" | head -n 1)
        echo "  $INPUT_BASE"
    else
        INPUT_BASE=$FOUND_PATHS
    fi

    # Extract TAO version and detector type from path
    TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')
    DETECTOR_TYPE=$(echo "$INPUT_BASE" | sed -n 's|.*/T[0-9]\+\.[0-9]\+\.[0-9]\+/\([^/]\+\)/.*|\1|p')

    if [ -z "$TAO_VERSION" ] || [ -z "$DETECTOR_TYPE" ]; then
        echo "ERROR: Could not parse TAO version or detector type from path:"
        echo "  $INPUT_BASE"
        exit 1
    fi

    # Map TAO version to JUNO version (T25.6.2 -> J25.6.2)
    JUNO_VERSION=$(echo "$TAO_VERSION" | sed 's/^T/J/')
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION}"

    echo ""
    echo "=========================================="
    echo "CONFIGURATION"
    echo "=========================================="
    echo "RUN: $RUN"
    echo "TAO Version: $TAO_VERSION"
    echo "Detector: $DETECTOR_TYPE"
    echo "JUNO Release: $JUNO_RELEASE"
    echo "Input path: $INPUT_BASE"
    echo ""

    # Verify input directory exists
    if [ ! -d "$INPUT_BASE" ]; then
        echo "ERROR: Input directory does not exist:"
        echo "  $INPUT_BASE"
        exit 1
    fi

    # Verify JUNO release exists
    if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
        echo "WARNING: JUNO release not found at $JUNO_RELEASE"
        echo "Trying fallback version..."
        JUNO_VERSION_FALLBACK=$(echo "$TAO_VERSION" | sed 's/^T/J/' | sed 's/\.[0-9]$/\.1/')
        JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION_FALLBACK}"
        if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
            echo "ERROR: Cannot find JUNO release for version $TAO_VERSION"
            echo "Tried:"
            echo "  $JUNO_VERSION"
            echo "  $JUNO_VERSION_FALLBACK"
            exit 1
        fi
        echo "Using fallback: $JUNO_RELEASE"
    fi
fi

# =====================================================
# Directory setup
# =====================================================
SCRIPTS_DIR="./extract_tdc/${RUN}"
OUTERR_DIR="${SCRIPTS_DIR}/.out-err"
TDC_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/tdc_analysis/RUN${RUN}/tdc_$(date +%Y-%m-%d_%H-%M-%S)"
PNG_DIR="${TDC_DIR}/plots"
LOGS_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/RUN${RUN}/tdc_analysis/"

# Scripts
PLOT_TDC_SCRIPT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/plot_tdc_from_rtraw.py"

# Python Environment
PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"

# HTCondor Settings
MAX_RUNTIME=3600  # 1 hour for individual jobs
MAX_RUNTIME_MERGE=7200  # 2 hours for merge job

# =====================================================
# Create directories
# =====================================================
mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$TDC_DIR" "$PNG_DIR" "$LOGS_DIR"

# =====================================================
# MODE: PROCESS
# =====================================================
if [ "$MODE" = "process" ]; then
    # Find RTRAW files
    RTRAW_FILES=($(ls "$INPUT_BASE"/*.rtraw 2>/dev/null | sort))
    if [ ${#RTRAW_FILES[@]} -eq 0 ]; then
        echo "ERROR: No .rtraw files found in $INPUT_BASE"
        exit 1
    fi

    TOTAL_FILES=${#RTRAW_FILES[@]}
    echo "Found $TOTAL_FILES RTRAW files"
    echo ""

    # =====================================================
    # Generate individual job scripts
    # =====================================================
    echo "Generating individual job scripts..."
    for i in ${!RTRAW_FILES[@]}; do
        RTRAW_FILE=${RTRAW_FILES[$i]}
        FILE_BASENAME=$(basename "$RTRAW_FILE")
        JOB_ID=$(printf "%03d" $((i+1)))

        MAIN="${SCRIPTS_DIR}/plot_tdc_${RUN}_${JOB_ID}.sh"
        SUBMIT="${SCRIPTS_DIR}/plot_tdc_${RUN}_${JOB_ID}.sub"
        MAIN_ABS=$(realpath "$MAIN")
        OUTERR_ABS=$(realpath "$OUTERR_DIR")

        # Generate main script
        cat > "$MAIN" <<EOFMAIN
#!/bin/bash
set -e

# Parameters
RUN=${RUN}
RTRAW_FILE=${RTRAW_FILE}
TDC_DIR=${TDC_DIR}
PNG_DIR=${PNG_DIR}
PLOT_TDC_SCRIPT=${PLOT_TDC_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
JOB_ID=${JOB_ID}
LOGS_DIR=${LOGS_DIR}

LOG_FILE="\${LOGS_DIR}/plot_tdc_\${RUN}_\${JOB_ID}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "TDC Analysis - Single RTRAW Processing"
echo "=========================================="
echo "RUN: \$RUN"
echo "Job ID: \$JOB_ID"
echo "Input: \$RTRAW_FILE"
echo ""

# Extract file number from filename
FILE_NUM=\$(echo "\$(basename "\$RTRAW_FILE")" | grep -oE '[0-9]{3,}' | tail -1)
if [ -z "\$FILE_NUM" ]; then
    FILE_NUM=${JOB_ID}
fi

OUTPUT_ROOT="\${TDC_DIR}/tdc_RUN\${RUN}_\${FILE_NUM}.root"

# Check if output already exists
if [ -f "\$OUTPUT_ROOT" ]; then
    echo "Output already exists: \$OUTPUT_ROOT"
    echo "Skipping..."
    exit 0
fi

# Verify input file exists
if [ ! -f "\$RTRAW_FILE" ]; then
    echo "ERROR: Input file not found: \$RTRAW_FILE"
    exit 1
fi

# Setup JUNO-TAO Environment
echo "Setting up JUNO-TAO environment..."
source "\${JUNO_RELEASE}/setup-tao.sh"
if [ \$? -ne 0 ]; then
    echo "ERROR: Failed to source JUNO-TAO environment!"
    exit 1
fi
ROOT_PYTHONPATH="\${PYTHONPATH}"

# Activate Python Virtual Environment
echo "Activating Python virtual environment..."
source "\${PYTHON_ENV_ROOT}/bin/activate"
if [ \$? -ne 0 ]; then
    echo "ERROR: Failed to activate Python virtual environment!"
    exit 1
fi
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# Run plot_tdc_from_rtraw.py
echo ""
echo "Running TDC extraction..."
echo ""
python "\$PLOT_TDC_SCRIPT" "\$RTRAW_FILE" "\$OUTPUT_ROOT" --png-dir "\$PNG_DIR"

if [ \$? -ne 0 ]; then
    echo "ERROR: TDC extraction failed!"
    deactivate
    exit 1
fi

# Verify output was created
if [ ! -f "\$OUTPUT_ROOT" ]; then
    echo "ERROR: Output file not created: \$OUTPUT_ROOT"
    deactivate
    exit 1
fi

echo ""
echo "=========================================="
echo "Extraction complete!"
echo "Output: \$OUTPUT_ROOT"
echo "=========================================="
deactivate
EOFMAIN

        chmod +x "$MAIN"

        # Generate HTCondor submit file
        cat > "$SUBMIT" <<EOFSUBMIT
universe = vanilla
executable = $MAIN_ABS
output = $OUTERR_ABS/plot_tdc_${RUN}_${JOB_ID}.out
error = $OUTERR_ABS/plot_tdc_${RUN}_${JOB_ID}.err
log = $OUTERR_ABS/plot_tdc_${RUN}_${JOB_ID}.log
+MaxRuntime = $MAX_RUNTIME
request_cpus = 1
request_memory = 2GB
queue
EOFSUBMIT
    done

    echo "Generated $TOTAL_FILES job scripts"

    # =====================================================
    # Generate joblist.sh and submit_all.sh
    # =====================================================
    cat > "$SCRIPTS_DIR/joblist.sh" <<EOFJOBLIST
#!/bin/bash
EOFJOBLIST

    for i in ${!RTRAW_FILES[@]}; do
        JOB_ID=$(printf "%03d" $((i+1)))
        SUBMIT="plot_tdc_${RUN}_${JOB_ID}.sub"
        echo "condor_submit -maxjobs 51 -spool -name sn01-htc.cr.cnaf.infn.it -batch-name plot_tdc_${RUN}_${JOB_ID} $SUBMIT" >> "$SCRIPTS_DIR/joblist.sh"
    done

    chmod +x "$SCRIPTS_DIR/joblist.sh"

    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash
echo "=========================================="
echo "Submitting TDC extraction jobs for RUN ${RUN}"
echo "=========================================="
echo ""
echo "Total jobs: $TOTAL_FILES"
echo ""
cd \$(dirname \$0)
./joblist.sh > joblist.out 2>&1 &
JUNOSUB_PID=\$!
echo ""
echo "Job submission started in background (PID: \$JUNOSUB_PID)"
echo ""
echo "Monitor progress:"
echo "  tail -f \$(pwd)/joblist.out"
echo ""
echo "Check HTCondor queue:"
echo "  condor_q -name sn01-htc.cr.cnaf.infn.it -batch plot_tdc_${RUN}"
echo ""
EOFSUBMIT

    chmod +x "$SCRIPTS_DIR/submit_all.sh"

    # =====================================================
    # Generate check_status.sh
    # =====================================================
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash
echo "=========================================="
echo "TDC Job Status for RUN ${RUN}"
echo "=========================================="
echo ""
TOTAL=$TOTAL_FILES
COMPLETED=\$(ls ${TDC_DIR}/tdc_RUN${RUN}_*.root 2>/dev/null | wc -l)
echo "Individual files:"
echo "  Total: \$TOTAL"
echo "  Completed: \$COMPLETED (\$((COMPLETED * 100 / TOTAL))%)"
echo "  Remaining: \$((TOTAL - COMPLETED))"
echo ""
echo "Output directory:"
echo "  ${TDC_DIR}"
echo ""
echo "HTCondor queue:"
condor_q -name sn01-htc.cr.cnaf.infn.it -batch plot_tdc_${RUN} 2>/dev/null || echo "  No jobs in queue"
echo ""
if [ \$COMPLETED -eq \$TOTAL ]; then
    echo "Next step: Merge results"
    echo "  $0 ${RUN} merge"
fi
echo ""
EOFSTATUS

    chmod +x "$SCRIPTS_DIR/check_status.sh"

    echo ""
    echo "=========================================="
    echo "PROCESS MODE SETUP COMPLETE"
    echo "=========================================="
    echo ""
    echo "Generated:"
    echo "  - $TOTAL_FILES individual job scripts"
    echo "  - $TOTAL_FILES HTCondor submit files"
    echo "  - Master submit script"
    echo "  - Status checker"
    echo ""
    echo "Output directory:"
    echo "  $TDC_DIR"
    echo ""
    echo "To start processing:"
    echo "  $SCRIPTS_DIR/submit_all.sh"
    echo ""
    echo "To check status:"
    echo "  $SCRIPTS_DIR/check_status.sh"
    echo ""
    echo "After completion, merge with:"
    echo "  $0 ${RUN} merge"
    echo "=========================================="

# =====================================================
# MODE: MERGE
# =====================================================
elif [ "$MODE" = "merge" ]; then
    # Find latest TDC directory for this run
    BASEDIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/tdc_analysis/RUN${RUN}"
    LATEST_TDC_DIR=$(ls -dt ${BASEDIR}/tdc_* 2>/dev/null | head -1)

    if [ -z "$LATEST_TDC_DIR" ]; then
        echo "ERROR: No TDC output directory found for RUN $RUN!"
        echo "  Expected pattern: ${BASEDIR}/tdc_*"
        echo ""
        echo "Run processing first:"
        echo "  $0 ${RUN} process"
        exit 1
    fi

    echo "Found TDC directory: $LATEST_TDC_DIR"

    # Check for individual files
    INDIVIDUAL_FILES=(${LATEST_TDC_DIR}/tdc_RUN${RUN}_*.root)
    if [ ! -f "${INDIVIDUAL_FILES[0]}" ]; then
        echo "ERROR: No individual TDC ROOT files found!"
        exit 1
    fi
    NUM_INDIVIDUAL=${#INDIVIDUAL_FILES[@]}
    if [ $NUM_INDIVIDUAL -eq 0 ]; then
        echo "ERROR: No individual TDC ROOT files found!"
        echo "  Expected: ${LATEST_TDC_DIR}/tdc_RUN${RUN}_*.root"
        echo ""
        echo "Run processing first:"
        echo "  $0 ${RUN} process"
        exit 1
    fi

    echo "Found $NUM_INDIVIDUAL individual TDC ROOT files to merge"
    echo ""

    MERGED_ROOT="${LATEST_TDC_DIR}/tdc_RUN${RUN}_MERGED.root"
    MERGED_PNG_DIR="${LATEST_TDC_DIR}/plots_merged"

    # Generate merge job script
    MAIN_MERGE="${SCRIPTS_DIR}/merge_tdc_${RUN}.sh"
    SUBMIT_MERGE="${SCRIPTS_DIR}/merge_tdc_${RUN}.sub"
    MAIN_MERGE_ABS=$(realpath "$MAIN_MERGE")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")

    cat > "$MAIN_MERGE" <<EOFMERGE
#!/bin/bash
set -e

# Parameters
RUN=${RUN}
LATEST_TDC_DIR=${LATEST_TDC_DIR}
MERGED_ROOT=${MERGED_ROOT}
MERGED_PNG_DIR=${MERGED_PNG_DIR}
PLOT_TDC_SCRIPT=${PLOT_TDC_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
LOGS_DIR=${LOGS_DIR}

LOG_FILE="\${LOGS_DIR}/merge_tdc_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "TDC Merge - RUN \$RUN"
echo "=========================================="
echo "Input directory: \$LATEST_TDC_DIR"
echo "Output ROOT: \$MERGED_ROOT"
echo "Output PNG dir: \$MERGED_PNG_DIR"
echo ""

# Check if output already exists
if [ -f "\$MERGED_ROOT" ]; then
    echo "Merged output already exists: \$MERGED_ROOT"
    echo "Skipping..."
    exit 0
fi

# Activate Python Virtual Environment (ROOT available system-wide)
echo "Activating Python virtual environment..."
source "\${PYTHON_ENV_ROOT}/bin/activate"
if [ \$? -ne 0 ]; then
    echo "ERROR: Failed to activate Python virtual environment!"
    exit 1
fi

# Run merge
echo ""
echo "Running TDC merge..."
echo ""
python "\$PLOT_TDC_SCRIPT" --merge "\${LATEST_TDC_DIR}/tdc_RUN\${RUN}_*.root" "\$MERGED_ROOT" --png-dir "\$MERGED_PNG_DIR"

if [ \$? -ne 0 ]; then
    echo "ERROR: Merge failed!"
    deactivate
    exit 1
fi

# Verify output was created
if [ ! -f "\$MERGED_ROOT" ]; then
    echo "ERROR: Merged output file not created: \$MERGED_ROOT"
    deactivate
    exit 1
fi

echo ""
echo "=========================================="
echo "Merge complete!"
echo "Output: \$MERGED_ROOT"
echo "Plots: \$MERGED_PNG_DIR"
echo "=========================================="
deactivate
EOFMERGE

    chmod +x "$MAIN_MERGE"

    # Generate HTCondor submit file
    cat > "$SUBMIT_MERGE" <<EOFSUBMIT
universe = vanilla
executable = $MAIN_MERGE_ABS
output = $OUTERR_ABS/merge_tdc_${RUN}.out
error = $OUTERR_ABS/merge_tdc_${RUN}.err
log = $OUTERR_ABS/merge_tdc_${RUN}.log
+MaxRuntime = $MAX_RUNTIME_MERGE
queue
EOFSUBMIT

    # Generate submit script
    cat > "$SCRIPTS_DIR/submit_merge.sh" <<EOFSUBMITMERGE
#!/bin/bash
echo "=========================================="
echo "Submitting TDC MERGE job for RUN ${RUN}"
echo "=========================================="
echo ""
echo "Input: ${LATEST_TDC_DIR}"
echo "Output: ${MERGED_ROOT}"
echo ""
cd \$(dirname \$0)
condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name merge_tdc_${RUN} merge_tdc_${RUN}.sub
if [ \$? -eq 0 ]; then
    echo ""
    echo "Merge job submitted successfully!"
    echo ""
    echo "Monitor progress:"
    echo "  condor_q -name sn01-htc.cr.cnaf.infn.it"
    echo ""
    echo "Check log:"
    echo "  tail -f ${LOGS_DIR}/merge_tdc_${RUN}_*.log"
else
    echo "ERROR: Failed to submit merge job"
    exit 1
fi
echo ""
EOFSUBMITMERGE

    chmod +x "$SCRIPTS_DIR/submit_merge.sh"

    echo ""
    echo "=========================================="
    echo "MERGE MODE SETUP COMPLETE"
    echo "=========================================="
    echo ""
    echo "Input: $NUM_INDIVIDUAL files"
    echo "Output: $MERGED_ROOT"
    echo "PNG plots: $MERGED_PNG_DIR"
    echo ""
    echo "To submit merge job:"
    echo "  $SCRIPTS_DIR/submit_merge.sh"
    echo ""
    echo "=========================================="

else
    echo "ERROR: Unknown mode '$MODE'"
    echo "Valid modes: process, merge"
    exit 1
fi
