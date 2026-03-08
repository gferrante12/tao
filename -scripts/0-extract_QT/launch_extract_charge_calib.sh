#!/bin/bash
set -e

# =====================================================
# generate_charge_extraction_calib.sh - v3.0
# Generate HTCondor jobs for charge extraction
# Now with proper EOS CLI support for IHEP
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

# =====================================================
# Cluster Detection and Path Configuration
# =====================================================

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
        BASE_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        SCRIPTS_BASE_QT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/0-extract_QT"
        SCRIPTS_BASE_GAIN="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
        ESD_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-kup"
        USE_EOS_CLI=false
        ;;
    "IHEP")
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/"
        SCRIPTS_BASE_QT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/0-extract_QT"
        SCRIPTS_BASE_GAIN="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        RTRAW_BASE="/eos/juno/tao-rtraw"
        ESD_BASE="/eos/juno/tao-kup"
        EOS_SERVER="root://junoeos01.ihep.ac.cn"
        USE_EOS_CLI=true
        ;;
    *)
        echo "ERROR: Unknown cluster"
        echo "Please check:"
        echo "  CNAF: /storage/gpfs_data/juno"
        echo "  IHEP: command 'eos' available and /junofs/users/gferrante exists"
        exit 1
        ;;
esac

echo "=========================================="
echo "CHARGE EXTRACTION JOB GENERATION"
echo "=========================================="
echo "Cluster: $CLUSTER"
echo "RUN: $RUN"
if [ "$USE_EOS_CLI" = true ]; then
    echo "EOS Mode: CLI (using 'eos' command)"
    echo "EOS Server: $EOS_SERVER"
fi
echo ""

# =====================================================
# EOS Helper Functions
# =====================================================

eos_find_run() {
    local base=$1
    local run=$2
    
    if [ "$USE_EOS_CLI" = true ]; then
        echo "Searching for RUN $run in EOS..." >&2
        
        # Calculate directory structure from run number
        # Example: RUN 1112 → 00001000/00001100/1112
        local run_num=$run
        local run_prefix=$(printf "%08d" $((run_num / 100 * 100)))      # 00001100
        local group_prefix=$(printf "%08d" $((run_num / 1000 * 1000)))  # 00001000
        
        # Get list of TAO versions
        local tao_versions=$(eos ls "$base" 2>/dev/null | grep -E '^T[0-9]+\.[0-9]+\.[0-9]+$' | sort -V -r)
        
        # Try each version with each stream type
        for version in $tao_versions; do
            for stream in "mix_stream" "TVT" "WT_TVT"; do
                local test_path="$base/$version/$stream/$group_prefix/$run_prefix/$run"
                
                if eos ls "$test_path" >/dev/null 2>&1; then
                    echo "$test_path"
                    return 0
                fi
            done
        done
        
        return 1
    else
        find "$base" -mindepth 5 -maxdepth 7 -type d -name "$run" 2>/dev/null | head -1
    fi
}

eos_list_files() {
    local dir=$1
    local pattern=$2
    
    if [ "$USE_EOS_CLI" = true ]; then
        # Use EOS CLI to list files
        eos ls "$dir" 2>/dev/null | grep "$pattern" | while read f; do
            echo "$dir/$f"
        done
    else
        # Standard filesystem ls
        ls "$dir"/$pattern 2>/dev/null
    fi
}

eos_count_files() {
    local dir=$1
    local pattern=$2
    
    if [ "$USE_EOS_CLI" = true ]; then
        eos ls "$dir" 2>/dev/null | grep -c "$pattern" || echo "0"
    else
        ls "$dir"/$pattern 2>/dev/null | wc -l
    fi
}

to_xrootd_url() {
    local path=$1
    
    if [ "$USE_EOS_CLI" = true ]; then
        # Convert EOS path to XRootD URL
        echo "${EOS_SERVER}/${path}"
    else
        # Return path as-is for local filesystem
        echo "$path"
    fi
}

# =====================================================
# Find RTRAW data
# =====================================================

echo "Searching for RUN $RUN in $RTRAW_BASE..."

INPUT_BASE=$(eos_find_run "$RTRAW_BASE" "$RUN")

if [ -z "$INPUT_BASE" ]; then
    echo "ERROR: RUN $RUN not found in $RTRAW_BASE"
    echo ""
    echo "Searched structure:"
    echo "  $RTRAW_BASE/<TAO-version>/<stream>/<group>/<subgroup>/<run>/"
    echo ""
    if [ "$USE_EOS_CLI" = true ]; then
        echo "Available TAO versions in EOS:"
        eos ls "$RTRAW_BASE" 2>/dev/null | head -10
    fi
    exit 1
fi

echo "Found: $INPUT_BASE"

# Extract TAO version from path
TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')

if [ -z "$TAO_VERSION" ]; then
    echo "ERROR: Could not parse TAO version from path:"
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
echo "JUNO Release: $JUNO_RELEASE"
echo "Input path: $INPUT_BASE"
echo ""

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
echo "Listing RTRAW files..."

if [ "$USE_EOS_CLI" = true ]; then
    # Use EOS CLI to get file list
    RTRAW_FILES=($(eos ls "$INPUT_BASE" 2>/dev/null | grep '\.rtraw$' | sort | while read f; do echo "$INPUT_BASE/$f"; done))
else
    # Standard filesystem
    RTRAW_FILES=($(ls "$INPUT_BASE"/*.rtraw 2>/dev/null | sort))
fi

if [ ${#RTRAW_FILES[@]} -eq 0 ]; then
    echo "ERROR: No .rtraw files found in $INPUT_BASE"
    if [ "$USE_EOS_CLI" = true ]; then
        echo ""
        echo "EOS directory contents:"
        eos ls "$INPUT_BASE" 2>/dev/null | head -10
    fi
    exit 1
fi

TOTAL_FILES=${#RTRAW_FILES[@]}
echo "Found $TOTAL_FILES RTRAW files"
echo ""

# =====================================================
# Directory setup
# =====================================================
SCRIPTS_DIR="./-scripts/0-extract_QT/RUN_charge_extraction_scripts/RUN${RUN}"
OUTERR_DIR="${SCRIPTS_DIR}/out-err"
SINGLE_CHARGE_DIR="${BASE_DIR}/0-extract_QT_results/charge_single/RUN${RUN}/$(date +%Y-%m-%d_%H-%M-%S)"
MERGED_CHARGE_DIR="${BASE_DIR}/0-extract_QT_results/charge_merged"
LOGS_DIR="${BASE_DIR}/logs/RUN${RUN}/0-extract_QT"
LOGS_GAIN_DIR="${BASE_DIR}/logs/RUN${RUN}/1-gain_calibration"

# Scripts
EXTRACT_SCRIPT="${SCRIPTS_BASE_QT}/extract_charge_calib.py"
MERGE_SCRIPT="${SCRIPTS_BASE_QT}/merge_charge.py"

# HTCondor Settings
MAX_RUNTIME=7200         # 2 hours for individual jobs
MAX_RUNTIME_MERGE=3600   # 1 hour for merge job

# Create directories
mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$SINGLE_CHARGE_DIR" "$MERGED_CHARGE_DIR" "$LOGS_DIR" "$LOGS_GAIN_DIR"

echo "Output directories created:"
echo "  Scripts: $SCRIPTS_DIR"
echo "  Output: $SINGLE_CHARGE_DIR"
echo "  Logs: $LOGS_DIR"
echo ""

# =====================================================
# Generate individual extraction job scripts
# =====================================================
echo "Generating job scripts..."

for i in ${!RTRAW_FILES[@]}; do
    RTRAW_FILE=${RTRAW_FILES[$i]}
    FILE_BASENAME=$(basename "$RTRAW_FILE")
    JOB_ID=$(printf "%03d" $((i+1)))

    # Convert to XRootD URL if using EOS
    RTRAW_FILE_URL=$(to_xrootd_url "$RTRAW_FILE")

    MAIN="${SCRIPTS_DIR}/extract_calib_${RUN}_${JOB_ID}.sh"
    
    # Generate main execution script
    cat > "$MAIN" <<EOFMAIN
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
RTRAW_FILE="${RTRAW_FILE_URL}"
SINGLE_CHARGE_DIR=${SINGLE_CHARGE_DIR}
EXTRACT_SCRIPT=${EXTRACT_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
JOB_ID=${JOB_ID}
LOGS_DIR=${LOGS_DIR}

LOG_FILE="\${LOGS_DIR}/extract_calib_\${RUN}_\${JOB_ID}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Charge Extraction - RUN \$RUN - Job \$JOB_ID"
echo "=========================================="
echo "Input: \$RTRAW_FILE"
echo ""

# Extract file number
FILE_NUM=\$(echo "${FILE_BASENAME}" | grep -oE '[0-9]{3,}' | tail -1)
if [ -z "\$FILE_NUM" ]; then
    FILE_NUM=${JOB_ID}
fi

OUTPUT_FILE="\${SINGLE_CHARGE_DIR}/CHARGE_single_RUN\${RUN}_\${FILE_NUM}.root"

# Check if output exists
if [ -f "\$OUTPUT_FILE" ]; then
    echo "Output exists, skipping"
    exit 0
fi

# Setup environment
echo "Setting up JUNO-TAO environment..."
source "\${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"

echo "Activating Python environment..."
source "\${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# Run extraction
echo ""
echo "Running charge extraction..."
python "\$EXTRACT_SCRIPT" "\$RTRAW_FILE" "\$SINGLE_CHARGE_DIR" --mode calib2

if [ \$? -ne 0 ]; then
    echo "ERROR: Extraction failed!"
    deactivate
    exit 1
fi

if [ ! -f "\$OUTPUT_FILE" ]; then
    echo "ERROR: Output not created"
    deactivate
    exit 1
fi

echo ""
echo "Extraction complete!"
echo "Output: \$OUTPUT_FILE"
deactivate
EOFMAIN

    chmod +x "$MAIN"

    # =====================================================
    # Generate submission files based on cluster
    # =====================================================
    if [ "$CLUSTER" = "CNAF" ]; then
        # CNAF: Generate HTCondor .sub file
        SUBMIT="${SCRIPTS_DIR}/extract_calib_${RUN}_${JOB_ID}.sub"
        MAIN_ABS=$(realpath "$MAIN")
        OUTERR_ABS=$(realpath "$OUTERR_DIR")
        
        cat > "$SUBMIT" <<EOFSUBMIT
universe = vanilla
executable = $MAIN_ABS
output = $OUTERR_ABS/extract_calib_${RUN}_${JOB_ID}.out
error = $OUTERR_ABS/extract_calib_${RUN}_${JOB_ID}.err
log = $OUTERR_ABS/extract_calib_${RUN}_${JOB_ID}.log
+MaxRuntime = 7200
queue
EOFSUBMIT
    fi
    # Note: IHEP doesn't need separate submission files - hep_sub takes script directly
done

echo "Generated $TOTAL_FILES job scripts"
if [ "$CLUSTER" = "CNAF" ]; then
    echo "Generated $TOTAL_FILES HTCondor submit files"
fi
echo ""

# =====================================================
# Generate joblist.sh based on cluster
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    # IHEP: Use hep_sub with queue monitoring
    cat > "$SCRIPTS_DIR/joblist.sh" <<'EOFJOBLIST'
#!/bin/bash
# Job submission for IHEP using hep_sub with queue control

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
OUTERR_DIR="${SCRIPT_DIR}/out-err"
MAX_CONCURRENT=100  # Maximum number of concurrent jobs
CHECK_INTERVAL=30   # Check queue every 30 seconds

echo "Starting job submission..."
echo "Script directory: $SCRIPT_DIR"
echo "Max concurrent jobs: $MAX_CONCURRENT"
echo ""

# Get list of job scripts
JOB_SCRIPTS=($(ls ${SCRIPT_DIR}/extract_calib_*.sh 2>/dev/null | sort))
TOTAL=${#JOB_SCRIPTS[@]}

if [ $TOTAL -eq 0 ]; then
    echo "ERROR: No job scripts found!"
    exit 1
fi

echo "Found $TOTAL job scripts"
echo "Submitting to IHEP HTCondor using hep_sub..."
echo ""

# Function to count running + idle jobs
count_my_jobs() {
    hep_q -u $USER 2>/dev/null | grep -E "^ *[0-9]+" | wc -l
}

SUBMITTED=0
FAILED=0
SKIPPED=0

for SCRIPT in "${JOB_SCRIPTS[@]}"; do
    JOB_NAME=$(basename "$SCRIPT" .sh)
    
    # Check if we've reached the limit
    CURRENT_JOBS=$(count_my_jobs)
    while [ $CURRENT_JOBS -ge $MAX_CONCURRENT ]; do
        echo "[$SUBMITTED/$TOTAL] Queue full ($CURRENT_JOBS jobs). Waiting ${CHECK_INTERVAL}s..."
        sleep $CHECK_INTERVAL
        CURRENT_JOBS=$(count_my_jobs)
    done
    
    # Submit job
    hep_sub "$SCRIPT" \
        -g juno \
        -o "${OUTERR_DIR}/${JOB_NAME}.out" \
        -e "${OUTERR_DIR}/${JOB_NAME}.err" \
        -mem 2000 >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        SUBMITTED=$((SUBMITTED + 1))
        echo "[$SUBMITTED/$TOTAL] Submitted: $JOB_NAME (queue: $CURRENT_JOBS)"
    else
        FAILED=$((FAILED + 1))
        echo "[$SUBMITTED/$TOTAL] FAILED: $JOB_NAME"
    fi
    
    # Small delay between submissions
    sleep 0.2
done

echo ""
echo "=========================================="
echo "Submission Summary"
echo "=========================================="
echo "Total scripts: $TOTAL"
echo "Submitted: $SUBMITTED"
echo "Failed: $FAILED"
echo ""
echo "Check queue: hep_q -u $USER"
echo "Final queue status:"
hep_q -u $USER 2>/dev/null | head -20
EOFJOBLIST

else
    # CNAF: Use condor_submit via junosub (unchanged)
    cat > "$SCRIPTS_DIR/joblist.sh" <<EOFJOBLIST
#!/bin/bash
# Job submission for CNAF using HTCondor

EOFJOBLIST

    for i in ${!RTRAW_FILES[@]}; do
        JOB_ID=$(printf "%03d" $((i+1)))
        echo "condor_submit -maxjobs 51 -spool -name sn01-htc.cr.cnaf.infn.it -batch-name extract_calib_${RUN}_${JOB_ID} extract_calib_${RUN}_${JOB_ID}.sub" >> "$SCRIPTS_DIR/joblist.sh"
    done
fi

chmod +x "$SCRIPTS_DIR/joblist.sh"

# =====================================================
# Generate submit_all.sh based on cluster
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo ""
echo "=========================================="
echo "Submitting ${TOTAL_FILES} jobs for RUN ${RUN}"
echo "=========================================="
echo "Cluster: IHEP"
echo "Method: hep_sub (max 100 concurrent)"
echo ""

cd \$(dirname \$0)

# Check if already running
if [ -f .submission.lock ]; then
    PID=\$(cat .submission.lock)
    if ps -p \$PID > /dev/null 2>&1; then
        echo "ERROR: Submission already running (PID: \$PID)"
        echo "To force restart: rm .submission.lock"
        exit 1
    fi
fi

# Run submission in background
nohup bash joblist.sh > joblist.out 2>&1 &
SUBMIT_PID=\$!
echo \$SUBMIT_PID > .submission.lock

echo ""
echo "Job submission started in background (PID: \$SUBMIT_PID)"
echo ""
echo "Monitor progress:"
echo "  tail -f \$(pwd)/joblist.out"
echo ""
echo "Check queue:"
echo "  hep_q -u \$USER"
echo ""
echo "Check status:"
echo "  ./check_status.sh"
echo ""
EOFSUBMIT

else
    # CNAF version (unchanged)
    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo ""
echo "=========================================="
echo "Submitting ${TOTAL_FILES} jobs for RUN ${RUN}"
echo "=========================================="
echo "Cluster: CNAF"
echo "Method: HTCondor"
echo ""

cd \$(dirname \$0)

nohup junosub joblist.sh > joblist.out 2>&1 &
SUBMIT_PID=\$!

echo ""
echo "Job submission started in background (PID: \$SUBMIT_PID)"
echo ""
echo "Monitor: tail -f \$(pwd)/joblist.out"
echo "Check queue: condor_q -name sn01-htc.cr.cnaf.infn.it -batch extract_calib_${RUN}"
echo "Check status: ./check_status.sh"
echo ""
EOFSUBMIT
fi

chmod +x "$SCRIPTS_DIR/submit_all.sh"


# =====================================================
# Generate check_status.sh based on cluster
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash

echo ""
echo "=========================================="
echo "Status for RUN ${RUN} (IHEP)"
echo "=========================================="
echo ""

TOTAL=$TOTAL_FILES
COMPLETED=\$(ls ${SINGLE_CHARGE_DIR}/CHARGE_single_RUN${RUN}_*.root 2>/dev/null | wc -l)

echo "Individual files:"
echo "  Total: \$TOTAL"
echo "  Completed: \$COMPLETED (\$((COMPLETED * 100 / TOTAL))%)"
echo "  Remaining: \$((TOTAL - COMPLETED))"
echo ""

echo "Queue status:"
echo "----------------------------------------"
hep_q -u \$USER 2>/dev/null | head -30
echo "----------------------------------------"
echo ""

if [ \$COMPLETED -lt \$TOTAL ]; then
    echo "Status: Jobs still running"
    echo "Next: Wait for completion"
elif [ ! -f "${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root" ]; then
    echo "Status: All jobs complete!"
    echo "Next: Run merge (./submit_merge.sh)"
else
    echo "Status: All done! ✓"
    echo "Merged file: ${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root"
fi
echo ""
EOFSTATUS

else
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash

echo ""
echo "=========================================="
echo "Status for RUN ${RUN} (CNAF)"
echo "=========================================="
echo ""

TOTAL=$TOTAL_FILES
COMPLETED=\$(ls ${SINGLE_CHARGE_DIR}/CHARGE_single_RUN${RUN}_*.root 2>/dev/null | wc -l)

echo "Individual files:"
echo "  Total: \$TOTAL"
echo "  Completed: \$COMPLETED (\$((COMPLETED * 100 / TOTAL))%)"
echo "  Remaining: \$((TOTAL - COMPLETED))"
echo ""

echo "Queue status:"
echo "----------------------------------------"
condor_q -name sn01-htc.cr.cnaf.infn.it -batch extract_calib_${RUN} 2>/dev/null || echo "  No jobs in queue"
echo "----------------------------------------"
echo ""

if [ \$COMPLETED -lt \$TOTAL ]; then
    echo "Status: Jobs still running"
    echo "Next: Wait for completion"
    echo "Monitor: tail -f ${SCRIPTS_DIR}/joblist.out"
elif [ ! -f "${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root" ]; then
    echo "Status: All jobs complete!"
    echo "Next: Run merge (./submit_merge.sh)"
else
    echo "Status: All done! ✓"
    echo "Merged file: ${MERGED_CHARGE_DIR}/CHARGE_RUN${RUN}_merged.root"
fi
echo ""
EOFSTATUS
fi

chmod +x "$SCRIPTS_DIR/check_status.sh"

# =====================================================
# Generate merge job script
# =====================================================
echo ""
echo "Generating merge job..."
MAIN_MERGE="${SCRIPTS_DIR}/merge_charge_${RUN}.sh"

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

# Generate submit_merge.sh (cluster-specific)
if [ "$CLUSTER" = "IHEP" ]; then
    # IHEP: Use hep_sub
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

OUTERR_DIR="\$(pwd)/out-err"
MERGE_SCRIPT="\$(pwd)/merge_charge_${RUN}.sh"

hep_sub "\$MERGE_SCRIPT" \\
    -g juno \\
    -o "\${OUTERR_DIR}/merge_charge_${RUN}.out" \\
    -e "\${OUTERR_DIR}/merge_charge_${RUN}.err" \\
    -mem 4000

echo ""
echo "Merge job submitted"
echo "Check queue: hep_q -u \$USER"
echo "Log: tail -f ${LOGS_DIR}/merge_charge_${RUN}_*.log"
echo ""
EOFSUBMITMERGE

else
    # CNAF: Use condor_submit
    SUBMIT_MERGE="${SCRIPTS_DIR}/merge_charge_${RUN}.sub"
    MAIN_MERGE_ABS=$(realpath "$MAIN_MERGE")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")
    
    cat > "$SUBMIT_MERGE" <<EOFSUBMITMERGE
universe = vanilla
executable = $MAIN_MERGE_ABS
output = $OUTERR_ABS/merge_charge_${RUN}.out
error = $OUTERR_ABS/merge_charge_${RUN}.err
log = $OUTERR_ABS/merge_charge_${RUN}.log
+MaxRuntime = $MAX_RUNTIME_MERGE
queue
EOFSUBMITMERGE

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
fi

chmod +x "$SCRIPTS_DIR/submit_merge.sh"

# =====================================================
# Generate gain calibration job script
# =====================================================
echo ""
echo "Generating gain calibration job..."

GAIN_SCRIPT="${SCRIPTS_BASE_GAIN}/gain_calibration.py"
MODELS_SCRIPT="${SCRIPTS_BASE_GAIN}/gain_fit_models.py"
CALIB_RESULTS_BASE="${BASE_DIR}/1-gain_calibration_results"
GAIN_JOB="${SCRIPTS_DIR}/gain_calibration_${RUN}.sh"

cat > "$GAIN_JOB" <<EOFGAIN
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
MERGED_CHARGE_DIR=${MERGED_CHARGE_DIR}
CALIB_RESULTS_BASE=${CALIB_RESULTS_BASE}
GAIN_SCRIPT=${GAIN_SCRIPT}
MODELS_SCRIPT=${MODELS_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
LOGS_GAIN_DIR=${LOGS_GAIN_DIR}

# Output dir is timestamped at runtime so it is unique even on re-runs
OUTPUT_DIR="\${CALIB_RESULTS_BASE}/${RUN}/\$(date +%Y-%m-%d_%H-%M-%S)"
LOG_FILE="\${LOGS_GAIN_DIR}/gain_calibration_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"

mkdir -p "\$OUTPUT_DIR"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Gain Calibration v3 - RUN \$RUN"
echo "=========================================="
echo "Output: \$OUTPUT_DIR"
echo ""

INPUT_FILE="\${MERGED_CHARGE_DIR}/CHARGE_RUN\${RUN}_merged.root"
RUN_NAME="RUN\${RUN}"

if [ ! -f "\$INPUT_FILE" ]; then
    echo "ERROR: Merged CHARGE file not found: \$INPUT_FILE"
    echo "Run submit_merge.sh first and wait for it to complete."
    exit 1
fi

FILE_SIZE=\$(du -h "\$INPUT_FILE" | cut -f1)
echo "Input: \$INPUT_FILE (\$FILE_SIZE)"
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

# Verify model library is co-located with the fit script
MODELS_DIR=\$(dirname "\$GAIN_SCRIPT")
if [ ! -f "\${MODELS_DIR}/gain_fit_models.py" ]; then
    echo "WARNING: gain_fit_models.py not found next to gain_calibration.py"
    echo "         Expected: \${MODELS_DIR}/gain_fit_models.py"
    echo "         Copying from \$MODELS_SCRIPT ..."
    cp "\$MODELS_SCRIPT" "\${MODELS_DIR}/gain_fit_models.py"
fi

# Run gain_calibration.py
# Models:
#   multigauss    — plain multi-Gaussian baseline
#   multigauss_ct — binomial optical-CT model (physics-motivated)
#   multigauss_ap — SYSU afterpulse model (Ziang Li 2026)
#   emg           — EMG CT tail (provides p_ct for get_spectrum --pct-file)
#   emg_ap        — EMG + afterpulse (most complete)
echo ""
echo "Running gain_calibration.py..."
echo "Command: python \"\$GAIN_SCRIPT\" \"\$INPUT_FILE\" \"\$OUTPUT_DIR\" \"\$RUN_NAME\""
echo "         --models multigauss,multigauss_ct,multigauss_ap,emg"
echo "         --plots sample --workers 8"
echo ""
START_TIME=\$(date +%s)
python "\$GAIN_SCRIPT" "\$INPUT_FILE" "\$OUTPUT_DIR" "\$RUN_NAME" \\
    --models multigauss,multigauss_ct,multigauss_ap,emg \\
    --plots sample \\
    --workers 8
CALIB_STATUS=\$?
END_TIME=\$(date +%s)
ELAPSED=\$((END_TIME - START_TIME))

echo ""
if [ \$CALIB_STATUS -ne 0 ]; then
    echo "ERROR: Gain calibration failed (exit code \$CALIB_STATUS)"
    deactivate
    exit 1
fi

echo "=========================================="
echo "Gain calibration complete!"
echo "Processing time: \$((ELAPSED/60))m \$((ELAPSED%60))s"
echo ""
echo "Output files:"
for f in "\${OUTPUT_DIR}"/*.csv; do
    [ -f "\$f" ] && echo "  \$(basename \$f): \$(wc -l < \$f) lines"
done
[ -f "\${OUTPUT_DIR}/summary_\${RUN_NAME}.txt" ] && \
    echo "  summary_\${RUN_NAME}.txt"
PLOT_COUNT=\$(find "\${OUTPUT_DIR}/plots" -name "*.png" 2>/dev/null | wc -l)
[ \$PLOT_COUNT -gt 0 ] && echo "  Plots: \$PLOT_COUNT PNG"
echo ""
echo "Calibration results: \$OUTPUT_DIR"
echo "=========================================="
deactivate
EOFGAIN

chmod +x "$GAIN_JOB"

# Generate submit_gain_calibration.sh (cluster-specific)
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_gain_calibration.sh" <<EOFSUBGAIN
#!/bin/bash
echo ""
echo "=========================================="
echo "Submitting GAIN CALIBRATION job for RUN ${RUN}"
echo "=========================================="
echo ""
echo "This runs gain_calibration.py on the merged CHARGE file."
echo "Make sure submit_merge.sh has completed before running this."
echo ""
cd \$(dirname \$0)

OUTERR_DIR="\$(pwd)/out-err"
GAIN_JOB="\$(pwd)/gain_calibration_${RUN}.sh"

hep_sub "\$GAIN_JOB" \\
    -g juno \\
    -o "\${OUTERR_DIR}/gain_calibration_${RUN}.out" \\
    -e "\${OUTERR_DIR}/gain_calibration_${RUN}.err" \\
    #-cpu 4 \\
    #-mem 8000

echo ""
echo "Gain calibration job submitted"
echo "Check queue: hep_q -u \$USER"
echo "Log: tail -f ${LOGS_GAIN_DIR}/gain_calibration_${RUN}_*.log"
echo ""
EOFSUBGAIN

else
    # CNAF: condor_submit
    GAIN_JOB_ABS=$(realpath "$GAIN_JOB")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")

    cat > "$SCRIPTS_DIR/gain_calibration_${RUN}.sub" <<EOFSUBGAINSUB
universe = vanilla
executable = $GAIN_JOB_ABS
output = $OUTERR_ABS/gain_calibration_${RUN}.out
error = $OUTERR_ABS/gain_calibration_${RUN}.err
log = $OUTERR_ABS/gain_calibration_${RUN}.log
+MaxRuntime = 14400
queue
EOFSUBGAINSUB

    cat > "$SCRIPTS_DIR/submit_gain_calibration.sh" <<EOFSUBGAIN
#!/bin/bash
echo ""
echo "=========================================="
echo "Submitting GAIN CALIBRATION job for RUN ${RUN}"
echo "=========================================="
echo ""
echo "This runs gain_calibration.py on the merged CHARGE file."
echo "Make sure submit_merge.sh has completed before running this."
echo ""
cd \$(dirname \$0)
condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name gain_calibration_${RUN} gain_calibration_${RUN}.sub
echo ""
echo "Monitor: condor_q -name sn01-htc.cr.cnaf.infn.it"
echo "Log: tail -f ${LOGS_GAIN_DIR}/gain_calibration_${RUN}_*.log"
echo ""
EOFSUBGAIN
fi

chmod +x "$SCRIPTS_DIR/submit_gain_calibration.sh"

# =====================================================
# Generate gain_vs_time job script
# =====================================================
echo ""
echo "Generating gain_vs_time job..."

GVT_SCRIPT="${SCRIPTS_BASE_GAIN}/gain_vs_time.py"
GVT_JOB="${SCRIPTS_DIR}/gain_vs_time_${RUN}.sh"
GVT_OUTPUT_DIR="${BASE_DIR}/1-gain_calibration_results/RUN${RUN}/gain_vs_time/$(date +%Y%m%d_%H%M%S)"

cat > "$GVT_JOB" <<EOFGVT
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
SINGLE_CHARGE_DIR=${SINGLE_CHARGE_DIR}
RTRAW_INPUT_DIR=${INPUT_BASE}
GVT_OUTPUT_DIR=${GVT_OUTPUT_DIR}
GVT_SCRIPT=${GVT_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
LOGS_GAIN_DIR=${LOGS_GAIN_DIR}
USE_EOS_CLI=${USE_EOS_CLI}

LOG_FILE="\${LOGS_GAIN_DIR}/gain_vs_time_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Gain vs Time - RUN \$RUN"
echo "=========================================="
echo "Charge dir  : \$SINGLE_CHARGE_DIR"
echo "Output dir  : \$GVT_OUTPUT_DIR"
echo ""

mkdir -p "\$GVT_OUTPUT_DIR"

# ------------------------------------------------------------------
# Build timestamps.txt  (file_number  unix_timestamp_seconds)
# Parse the 14-digit YYYYMMDDHHMMSS embedded in each RTRAW filename:
#   RUN.NNNN.TAODAQ...mix_stream.20260228193800.001_T25...rtraw
# ------------------------------------------------------------------
TIMESTAMPS_FILE="\${GVT_OUTPUT_DIR}/timestamps.txt"
echo "# file_number  unix_timestamp_seconds" > "\$TIMESTAMPS_FILE"

if [ "\$USE_EOS_CLI" = "true" ]; then
    RTRAW_LIST=\$(eos ls "\$RTRAW_INPUT_DIR" 2>/dev/null | grep '\.rtraw\$' | sort)
else
    RTRAW_LIST=\$(ls "\$RTRAW_INPUT_DIR"/*.rtraw 2>/dev/null | xargs -n1 basename | sort)
fi

NFILES=0
while IFS= read -r fname; do
    [ -z "\$fname" ] && continue
    # 3-digit file number: the NNN in .NNN_T25...
    FILE_NUM=\$(echo "\$fname" | grep -oE '\.[0-9]{3}_T[0-9]' | grep -oE '[0-9]{3}' | head -1)
    [ -z "\$FILE_NUM" ] && continue
    # 14-digit UTC timestamp YYYYMMDDHHMMSS between two dots
    TS14=\$(echo "\$fname" | grep -oE '\.[0-9]{14}\.' | tr -d '.')
    [ -z "\$TS14" ] && continue
    YY=\${TS14:0:4}; MM=\${TS14:4:2}; DD=\${TS14:6:2}
    HH=\${TS14:8:2}; MI=\${TS14:10:2}; SS=\${TS14:12:2}
    UNIX_TS=\$(date -d "\${YY}-\${MM}-\${DD} \${HH}:\${MI}:\${SS} UTC" +%s 2>/dev/null \
              || python3 -c "import calendar,datetime; \
                             dt=datetime.datetime(\${YY},\${MM},\${DD},\${HH},\${MI},\${SS}); \
                             print(int(calendar.timegm(dt.timetuple())))")
    # Strip leading zeros so file_number matches what extract_charge_calib.py writes
    echo "\$(echo \$FILE_NUM | sed 's/^0*//')  \$UNIX_TS" >> "\$TIMESTAMPS_FILE"
    NFILES=\$((NFILES+1))
done <<< "\$RTRAW_LIST"

echo "Built timestamps.txt: \$NFILES entries"
echo ""

if [ \$NFILES -eq 0 ]; then
    echo "WARNING: No timestamps extracted – running without --timestamps (fallback: idx×60 s)."
    TS_FLAG=""
else
    TS_FLAG="--timestamps \$TIMESTAMPS_FILE"
fi

# ------------------------------------------------------------------
# Setup environment
# ------------------------------------------------------------------
echo "Setting up JUNO-TAO environment..."
source "\${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"

echo "Activating Python virtual environment..."
source "\${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# ------------------------------------------------------------------
# Run gain_vs_time.py
# ------------------------------------------------------------------
echo ""
echo "Running gain_vs_time.py..."
python "\$GVT_SCRIPT" \\
    "\$SINGLE_CHARGE_DIR" \\
    "\$GVT_OUTPUT_DIR" \\
    "RUN\${RUN}" \\
    \$TS_FLAG

GVT_STATUS=\$?

if [ \$GVT_STATUS -ne 0 ]; then
    echo "ERROR: gain_vs_time.py failed (exit code \$GVT_STATUS)"
    deactivate
    exit 1
fi

echo ""
echo "=========================================="
echo "Gain vs Time complete!"
NPLOTS=\$(find "\$GVT_OUTPUT_DIR" -name "*.png" 2>/dev/null | wc -l)
echo "  Plots : \$NPLOTS PNG files in \$GVT_OUTPUT_DIR"
[ -f "\${GVT_OUTPUT_DIR}/gain_vs_time_summary.csv" ] && \
    echo "  CSV   : \${GVT_OUTPUT_DIR}/gain_vs_time_summary.csv"
echo "=========================================="
deactivate
EOFGVT

chmod +x "$GVT_JOB"

# ── submit_gain_vs_time.sh  (cluster-specific) ────────────────────────────────
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_gain_vs_time.sh" <<EOFSUBGVT
#!/bin/bash
echo ""
echo "=========================================="
echo "Submitting GAIN VS TIME job for RUN ${RUN}"
echo "=========================================="
echo ""
echo "Runs gain_vs_time.py on individual CHARGE files (no merge needed)."
echo "Can be submitted once all extract_calib jobs are complete."
echo ""
cd \$(dirname \$0)

OUTERR_DIR="\$(pwd)/out-err"
GVT_JOB="\$(pwd)/gain_vs_time_${RUN}.sh"

hep_sub "\$GVT_JOB" \\
    -g juno \\
    -o "\${OUTERR_DIR}/gain_vs_time_${RUN}.out" \\
    -e "\${OUTERR_DIR}/gain_vs_time_${RUN}.err" \\
    -mem 8000

echo ""
echo "Gain vs time job submitted"
echo "Check queue : hep_q -u \$USER"
echo "Log         : tail -f ${LOGS_GAIN_DIR}/gain_vs_time_${RUN}_*.log"
echo ""
EOFSUBGVT

else
    # CNAF: condor_submit
    GVT_JOB_ABS=$(realpath "$GVT_JOB")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")

    cat > "$SCRIPTS_DIR/gain_vs_time_${RUN}.sub" <<EOFSUBGVTSUB
universe = vanilla
executable = $GVT_JOB_ABS
output = $OUTERR_ABS/gain_vs_time_${RUN}.out
error  = $OUTERR_ABS/gain_vs_time_${RUN}.err
log    = $OUTERR_ABS/gain_vs_time_${RUN}.log
+MaxRuntime = 14400
queue
EOFSUBGVTSUB

    cat > "$SCRIPTS_DIR/submit_gain_vs_time.sh" <<EOFSUBGVT
#!/bin/bash
echo ""
echo "=========================================="
echo "Submitting GAIN VS TIME job for RUN ${RUN}"
echo "=========================================="
echo ""
echo "Runs gain_vs_time.py on individual CHARGE files (no merge needed)."
echo "Can be submitted once all extract_calib jobs are complete."
echo ""
cd \$(dirname \$0)
condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name gain_vs_time_${RUN} gain_vs_time_${RUN}.sub
echo ""
echo "Monitor : condor_q -name sn01-htc.cr.cnaf.infn.it"
echo "Log     : tail -f ${LOGS_GAIN_DIR}/gain_vs_time_${RUN}_*.log"
echo ""
EOFSUBGVT
fi

chmod +x "$SCRIPTS_DIR/submit_gain_vs_time.sh"

# =====================================================
# Summary
# =====================================================
echo ""
echo "=========================================="
echo "Generation Complete!"
echo "=========================================="
echo ""
echo "Cluster: $CLUSTER"
echo "RUN: $RUN"
echo "TAO Version: $TAO_VERSION"
echo "JUNO Release: $JUNO_RELEASE"
echo "Type: CALIBRATION (no reconstruction)"
echo "Files: $TOTAL_FILES RTRAW files"
echo ""
if [ "$USE_EOS_CLI" = true ]; then
    echo "EOS Mode: CLI access"
    echo "Files accessed via: $EOS_SERVER"
fi
echo ""
echo "Input path:"
echo "  $INPUT_BASE"
echo ""
echo "Generated:"
echo "  - $TOTAL_FILES execution scripts"
if [ "$CLUSTER" = "CNAF" ]; then
    echo "  - $TOTAL_FILES HTCondor submit files"
fi
echo "  - 1 joblist script (submit_all.sh)"
echo "  - 1 status checker (check_status.sh)"
echo "  - 1 merge job (merge_charge_${RUN}.sh + submit_merge.sh)"
echo "  - 1 gain calibration job (gain_calibration_${RUN}.sh + submit_gain_calibration.sh)"
echo "  - 1 gain vs time job     (gain_vs_time_${RUN}.sh + submit_gain_vs_time.sh)"
echo ""
echo "Output directories:"
echo "  Individual: $SINGLE_CHARGE_DIR"
echo "  Merged: $MERGED_CHARGE_DIR"
echo ""
echo "To submit all jobs:"
echo "   ./$SCRIPTS_DIR/submit_all.sh"
echo ""
echo "To check status:"
echo "   ./$SCRIPTS_DIR/check_status.sh"
echo ""
echo "After completion:"
echo "  1. Merge:            ./$SCRIPTS_DIR/submit_merge.sh"
echo "  2. Gain calibration: ./$SCRIPTS_DIR/submit_gain_calibration.sh"
echo "     (run step 2 only after the merge job finishes)"
echo "  3. Gain vs time:     ./$SCRIPTS_DIR/submit_gain_vs_time.sh"
echo "     (runs on individual CHARGE files; can start once all extract jobs are done)"
echo ""
echo "=========================================="
