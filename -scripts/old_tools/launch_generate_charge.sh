#!/bin/bash

set -e

# =====================================================
# generate_charge_extraction_calib.sh - v2.0
# Generate HTCondor jobs for charge extraction
# Now includes merge script generation
# =====================================================

if [ -z "$1" ]; then
echo "ERROR: RUN number not provided!"
echo ""
echo "Usage: $0 RUN"
echo ""
echo "Examples:"
echo "  $0 1210    # Generate extraction jobs for RUN 1210"
echo ""
exit 1
fi

RUN=$1

echo "=========================================="
echo "CHARGE EXTRACTION JOB GENERATION"
echo "=========================================="
echo "RUN: $RUN"
echo ""

# =====================================================
# Find RTRAW data
# =====================================================
RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"

FOUND_PATHS=$(find "$RTRAW_BASE" -mindepth 5 -maxdepth 7 -type d -name "$RUN" 2>/dev/null)

if [ -z "$FOUND_PATHS" ]; then
    echo "ERROR: RUN $RUN not found in $RTRAW_BASE"
    echo ""
    echo "Searched structure:"
    echo "  $RTRAW_BASE/<TAO-version>/<stream>/<group>/<subgroup>/<run>/"
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

# Extract TAO version from path
TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')
DETECTOR_TYPE=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')

if [ -z "$TAO_VERSION" ] || [ -z "$DETECTOR_TYPE" ]; then
    echo "ERROR: Could not parse TAO version or detector type from path:"
    echo "  $INPUT_BASE"
    exit 1
fi

# Map TAO version to JUNO version (T25.6.4 -> J25.6.4)
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

# =====================================================
# Find RTRAW files
# =====================================================
RTRAW_FILES=($(ls "$INPUT_BASE"/*.rtraw 2>/dev/null | sort))
if [ ${#RTRAW_FILES[@]} -eq 0 ]; then
    echo "ERROR: No .rtraw files found in $INPUT_BASE"
    exit 1
fi

TOTAL_FILES=${#RTRAW_FILES[@]}
echo "Found $TOTAL_FILES RTRAW files"
echo ""

# =====================================================
# Directory setup
# =====================================================
SCRIPTS_DIR="./charge_extraction/${RUN}"
OUTERR_DIR="${SCRIPTS_DIR}/.out-err"
SINGLE_CHARGE_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/charge_single/RUN${RUN}/$(date +%Y-%m-%d_%H-%M-%S)"
MERGED_CHARGE_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/charge_merged"
LOGS_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/RUN${RUN}/extract_calib"

# Scripts
EXTRACT_SCRIPT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/extract_charge_calib.py"
MERGE_SCRIPT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/merge_charge.py"

# Python Environment
PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"

# HTCondor Settings
MAX_RUNTIME=7200         # 2 hours for individual jobs
MAX_RUNTIME_MERGE=3600   # 1 hour for merge job

# =====================================================
# Create directories
# =====================================================
mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$SINGLE_CHARGE_DIR" "$MERGED_CHARGE_DIR" "$LOGS_DIR"

# =====================================================
# Generate individual extraction job scripts
# =====================================================
echo "Generating individual job scripts..."
for i in ${!RTRAW_FILES[@]}; do
    RTRAW_FILE=${RTRAW_FILES[$i]}
    FILE_BASENAME=$(basename "$RTRAW_FILE")
    JOB_ID=$(printf "%03d" $((i+1)))

    MAIN="${SCRIPTS_DIR}/extract_calib_${RUN}_${JOB_ID}.sh"
    SUBMIT="${SCRIPTS_DIR}/extract_calib_${RUN}_${JOB_ID}.sub"
    MAIN_ABS=$(realpath "$MAIN")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")

    # Generate main script
    cat > "$MAIN" <<EOFMAIN
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
RTRAW_FILE=${RTRAW_FILE}
SINGLE_CHARGE_DIR=${SINGLE_CHARGE_DIR}
EXTRACT_SCRIPT=${EXTRACT_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
JOB_ID=${JOB_ID}
LOGS_DIR=${LOGS_DIR}
TAO_VERSION=${TAO_VERSION}
DETECTOR_TYPE=${DETECTOR_TYPE}

LOG_FILE="\${LOGS_DIR}/extract_calib_\${RUN}_\${JOB_ID}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Calibration Run - Charge Extraction"
echo "=========================================="
echo "RUN: \$RUN"
echo "TAO Version: \$TAO_VERSION"
echo "Detector: \$DETECTOR_TYPE"
echo "Job ID: \$JOB_ID"
echo "Input: \$RTRAW_FILE"
echo ""

# Extract file number from filename (use last 3-digit sequence before extension)
FILE_NUM=\$(echo "\$(basename "\$RTRAW_FILE")" | sed -n 's/.*\\.\\([0-9]\\{3,\\}\\)\\.rtraw$/\\1/p')
if [ -z "\$FILE_NUM" ]; then
    # Fallback: extract run number after RUN. prefix
    FILE_NUM=\$(echo "\$(basename "\$RTRAW_FILE")" | sed -n 's/^RUN\\.\\([0-9]\\+\\)\\..*/\\1/p')
fi
if [ -z "\$FILE_NUM" ]; then
    echo "ERROR: Could not extract file number from: \$(basename "\$RTRAW_FILE")"
    exit 1
fi

OUTPUT_FILE="\${SINGLE_CHARGE_DIR}/CHARGE_single_RUN\${RUN}_\${FILE_NUM}.root"

# Check if output already exists
if [ -f "\$OUTPUT_FILE" ]; then
    echo "Output already exists: \$OUTPUT_FILE"
    echo "Skipping extraction..."
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

# Run extraction (NO SPATIAL CUT for calibration)
echo ""
echo "Running charge extraction with veto only..."
echo ""
echo "python \"\$EXTRACT_SCRIPT\" \"\$RTRAW_FILE\" \"\$SINGLE_CHARGE_DIR\" --mode calib"
python "\$EXTRACT_SCRIPT" "\$RTRAW_FILE" "\$SINGLE_CHARGE_DIR" --mode calib

if [ \$? -ne 0 ]; then
    echo "ERROR: Extraction failed!"
    deactivate
    exit 1
fi

# Verify output was created
if [ ! -f "\$OUTPUT_FILE" ]; then
    echo "ERROR: Output file not created: \$OUTPUT_FILE"
    deactivate
    exit 1
fi

echo ""
echo "=========================================="
echo "Extraction complete!"
echo "Output: \$OUTPUT_FILE"
echo "=========================================="
deactivate
EOFMAIN

    chmod +x "$MAIN"

    # Generate HTCondor submit file
    cat > "$SUBMIT" <<EOFSUBMIT
universe = vanilla
executable = $MAIN_ABS
output = $OUTERR_ABS/extract_calib_${RUN}_${JOB_ID}.out
error = $OUTERR_ABS/extract_calib_${RUN}_${JOB_ID}.err
log = $OUTERR_ABS/extract_calib_${RUN}_${JOB_ID}.log
+MaxRuntime = $MAX_RUNTIME
queue
EOFSUBMIT
done

echo "Generated $TOTAL_FILES job scripts"
echo ""

# =====================================================
# Generate joblist.sh and submit_all.sh
# =====================================================
echo "Generating job list..."
cat > "$SCRIPTS_DIR/joblist.sh" <<EOFJOBLIST
#!/bin/bash
# Job list for RUN $RUN - $TOTAL_FILES jobs
EOFJOBLIST

for i in ${!RTRAW_FILES[@]}; do
    JOB_ID=$(printf "%03d" $((i+1)))
    SUBMIT="extract_calib_${RUN}_${JOB_ID}.sub"
    echo "condor_submit -maxjobs 51 -spool -name sn01-htc.cr.cnaf.infn.it -batch-name extract_calib_${RUN}_${JOB_ID} $SUBMIT" >> "$SCRIPTS_DIR/joblist.sh"
done

chmod +x "$SCRIPTS_DIR/joblist.sh"

cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo ""
echo "=========================================="
echo "Submitting ${TOTAL_FILES} jobs for RUN ${RUN}..."
echo "=========================================="
echo ""

cd \$(dirname \$0)

nohup junosub joblist.sh > joblist.out 2>&1 &
JUNOSUB_PID=\$!

echo ""
echo "Job submission started in background (PID: \$JUNOSUB_PID)"
echo ""
echo "Monitor progress:"
echo "  tail -f \$(pwd)/joblist.out"
echo ""
echo "Check HTCondor queue:"
echo "  condor_q -name sn01-htc.cr.cnaf.infn.it -batch extract_calib_${RUN}"
echo ""
EOFSUBMIT

chmod +x "$SCRIPTS_DIR/submit_all.sh"

# =====================================================
# Generate merge job script
# =====================================================
echo "Generating merge job..."
MAIN_MERGE="${SCRIPTS_DIR}/merge_charge_${RUN}.sh"
SUBMIT_MERGE="${SCRIPTS_DIR}/merge_charge_${RUN}.sub"
MAIN_MERGE_ABS=$(realpath "$MAIN_MERGE")

cat > "$MAIN_MERGE" <<EOFMERGE
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
SINGLE_CHARGE_DIR=${SINGLE_CHARGE_DIR}
MERGED_CHARGE_DIR=${MERGED_CHARGE_DIR}
MERGE_SCRIPT=${MERGE_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
LOGS_DIR=${LOGS_DIR}

LOG_FILE="\${LOGS_DIR}/merge_charge_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Merge Charge Data - RUN \$RUN"
echo "=========================================="
echo "Input directory: \$SINGLE_CHARGE_DIR"
echo "Output directory: \$MERGED_CHARGE_DIR"
echo ""

OUTPUT_FILE="\${MERGED_CHARGE_DIR}/CHARGE_RUN\${RUN}_merged.root"

# Check if merged file already exists
if [ -f "\$OUTPUT_FILE" ]; then
    echo "Merged file already exists: \$OUTPUT_FILE"
    echo "Skipping..."
    exit 0
fi

# Count individual charge files
CHARGE_FILES=(\$(ls "\${SINGLE_CHARGE_DIR}"/CHARGE_single_RUN\${RUN}_*.root 2>/dev/null))
NUM_FILES=\${#CHARGE_FILES[@]}

if [ \$NUM_FILES -eq 0 ]; then
    echo "ERROR: No individual charge files found in \$SINGLE_CHARGE_DIR"
    exit 1
fi

echo "Found \$NUM_FILES individual charge files"
echo ""

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

# Run merge_charge.py
echo ""
echo "Running merge_charge.py..."
echo "Command: python \"\$MERGE_SCRIPT\" ${RUN} \"\$SINGLE_CHARGE_DIR\" \"\$MERGED_CHARGE_DIR\""
echo ""
python "\$MERGE_SCRIPT" "${RUN}" "\$SINGLE_CHARGE_DIR" "\$MERGED_CHARGE_DIR"

if [ \$? -ne 0 ]; then
    echo "ERROR: Merge failed!"
    deactivate
    exit 1
fi

# Verify merged file was created
if [ ! -f "\$OUTPUT_FILE" ]; then
    echo "ERROR: Merged file not created: \$OUTPUT_FILE"
    deactivate
    exit 1
fi

echo ""
echo "=========================================="
echo "Merge complete!"
echo "Output: \$OUTPUT_FILE"
echo "=========================================="
deactivate
EOFMERGE

chmod +x "$MAIN_MERGE"

# Generate HTCondor submit file for merge
cat > "$SUBMIT_MERGE" <<EOFSUBMITMERGE
universe = vanilla
executable = $MAIN_MERGE_ABS
output = $OUTERR_ABS/merge_charge_${RUN}.out
error = $OUTERR_ABS/merge_charge_${RUN}.err
log = $OUTERR_ABS/merge_charge_${RUN}.log
+MaxRuntime = $MAX_RUNTIME_MERGE
queue
EOFSUBMITMERGE

# Generate submit_merge.sh
cat > "$SCRIPTS_DIR/submit_merge.sh" <<EOFSUBMITMERGE
#!/bin/bash
echo ""
echo "=========================================="
echo "Submitting MERGE job for RUN ${RUN}"
echo "=========================================="
echo ""
echo "This merges all individual charge files"
echo ""
cd \$(dirname \$0)
condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name merge_charge_${RUN} merge_charge_${RUN}.sub
echo ""
echo "Monitor: condor_q -name sn01-htc.cr.cnaf.infn.it"
echo "Log: tail -f ${LOGS_DIR}/merge_charge_${RUN}_*.log"
echo ""
EOFSUBMITMERGE

chmod +x "$SCRIPTS_DIR/submit_merge.sh"

# =====================================================
# Generate check_status.sh
# =====================================================
cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash
echo ""
echo "=========================================="
echo "Calibration Extraction Status for RUN ${RUN}"
echo "=========================================="
echo ""
echo "TAO Version: ${TAO_VERSION}"
echo "Detector: ${DETECTOR_TYPE}"
echo "Input path: ${INPUT_BASE}"
echo ""

TOTAL=$TOTAL_FILES
COMPLETED=\$(ls ${SINGLE_CHARGE_DIR}/CHARGE_single_RUN${RUN}_*.root 2>/dev/null | wc -l)
MERGED_EXISTS=\$(ls ${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root 2>/dev/null | wc -l)

echo "Individual files:"
echo "  Total: \$TOTAL"
echo "  Completed: \$COMPLETED (\$((COMPLETED * 100 / TOTAL))%)"
echo "  Remaining: \$((TOTAL - COMPLETED))"
echo ""

if [ \$MERGED_EXISTS -eq 1 ]; then
    echo "Merged analysis: COMPLETED ✓"
elif [ \$COMPLETED -eq \$TOTAL ]; then
    echo "Merged analysis: Ready to run (use submit_merge.sh)"
else
    echo "Merged analysis: Waiting for individual jobs..."
fi
echo ""

echo "Output directories:"
echo "  Individual: ${SINGLE_CHARGE_DIR}"
echo "  Merged: ${MERGED_CHARGE_DIR}"
echo ""

echo "HTCondor queue:"
condor_q -name sn01-htc.cr.cnaf.infn.it -batch extract_calib_${RUN} 2>/dev/null || echo "  No jobs in queue"
echo ""

echo "Next steps:"
if [ \$COMPLETED -lt \$TOTAL ]; then
    echo "  1. Wait for individual jobs to complete"
    echo "  2. Monitor: tail -f ${SCRIPTS_DIR}/joblist.out"
elif [ \$MERGED_EXISTS -eq 0 ]; then
    echo "  1. All individual jobs complete!"
    echo "  2. Run: ${SCRIPTS_DIR}/submit_merge.sh"
    echo "  3. After merge: ./launch_gain_calibration.sh ${RUN}"
else
    echo "  1. All done! Merged file ready:"
    echo "     ${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root"
    echo "  2. Run gain calibration: ./launch_gain_calibration.sh ${RUN}"
fi
echo ""
EOFSTATUS

chmod +x "$SCRIPTS_DIR/check_status.sh"

# =====================================================
# Summary
# =====================================================
echo ""
echo "=========================================="
echo "Generation Complete!"
echo "=========================================="
echo ""
echo "RUN: $RUN"
echo "TAO Version: $TAO_VERSION"
echo "Detector: $DETECTOR_TYPE"
echo "JUNO Release: $JUNO_RELEASE"
echo "Type: CALIBRATION (no reconstruction)"
echo "Files: $TOTAL_FILES RTRAW files"
echo ""
echo "Full path:"
echo "  $INPUT_BASE"
echo ""
echo "Generated:"
echo "  - $TOTAL_FILES execution scripts"
echo "  - $TOTAL_FILES HTCondor submit files"
echo "  - 1 master submit script"
echo "  - 1 merge job script"
echo "  - 1 status checker"
echo ""
echo "Output directories:"
echo "  Individual: $SINGLE_CHARGE_DIR"
echo "  Merged: $MERGED_CHARGE_DIR"
echo ""
echo "To submit all jobs:"
echo "  $SCRIPTS_DIR/submit_all.sh"
echo ""
echo "To check status:"
echo "  $SCRIPTS_DIR/check_status.sh"
echo ""
echo "After completion:"
echo "  1. Merge: $SCRIPTS_DIR/submit_merge.sh"
echo "  2. Calibrate: ./launch_gain_calibration.sh $RUN"
echo ""
echo "=========================================="
