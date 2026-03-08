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
        SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
        ESD_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-kup"
        USE_EOS_CLI=false
        ;;
    "IHEP")
        SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
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
SCRIPTS_DIR="./charge_extraction/${RUN}"
OUTERR_DIR="${SCRIPTS_DIR}/out-err"
SINGLE_CHARGE_DIR="${SCRIPTS_BASE}/charge_single/RUN${RUN}/$(date +%Y-%m-%d_%H-%M-%S)"
MERGED_CHARGE_DIR="${SCRIPTS_BASE}/charge_merged"
LOGS_DIR="${SCRIPTS_BASE}/logs/RUN${RUN}/extract_calib"

# Scripts
EXTRACT_SCRIPT="${SCRIPTS_BASE}/extract_charge_calib.py"
MERGE_SCRIPT="${SCRIPTS_BASE}/merge_charge.py"

# HTCondor Settings
MAX_RUNTIME=7200         # 2 hours for individual jobs
MAX_RUNTIME_MERGE=3600   # 1 hour for merge job

# Create directories
mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$SINGLE_CHARGE_DIR" "$MERGED_CHARGE_DIR" "$LOGS_DIR"

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
python "\$EXTRACT_SCRIPT" "\$RTRAW_FILE" "\$SINGLE_CHARGE_DIR" --mode calib

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
request_cpus = 1
request_memory = 2GB
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
request_cpus = 1
request_memory = 4GB
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

GAIN_SCRIPT="${SCRIPTS_BASE}/gain_calibration.py"
CALIB_RESULTS_BASE="${SCRIPTS_BASE}/calibration_results"
GAIN_JOB="${SCRIPTS_DIR}/gain_calibration_${RUN}.sh"

cat > "$GAIN_JOB" <<EOFGAIN
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
MERGED_CHARGE_DIR=${MERGED_CHARGE_DIR}
CALIB_RESULTS_BASE=${CALIB_RESULTS_BASE}
GAIN_SCRIPT=${GAIN_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
LOGS_DIR=${LOGS_DIR}

# Output dir is timestamped at runtime so it is unique even on re-runs
OUTPUT_DIR="\${CALIB_RESULTS_BASE}/${RUN}/\$(date +%Y-%m-%d_%H-%M-%S)"
LOG_FILE="\${LOGS_DIR}/gain_calibration_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"

mkdir -p "\$OUTPUT_DIR"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Gain Calibration - RUN \$RUN"
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

# Run gain_calibration.py
echo ""
echo "Running gain_calibration.py..."
echo "Command: python \"\$GAIN_SCRIPT\" \"\$INPUT_FILE\" \"\$OUTPUT_DIR\" \"\$RUN_NAME\""
echo ""
START_TIME=\$(date +%s)
python "\$GAIN_SCRIPT" "\$INPUT_FILE" "\$OUTPUT_DIR" "\$RUN_NAME"
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
for f in \${OUTPUT_DIR}/*.txt; do
    [ -f "\$f" ] && echo "  \$(basename \$f): \$(wc -l < \$f) lines"
done
PLOT_COUNT=\$(find "\${OUTPUT_DIR}/plots_\${RUN_NAME}" -name "*.png" 2>/dev/null | wc -l)
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
    -mem 4000

echo ""
echo "Gain calibration job submitted"
echo "Check queue: hep_q -u \$USER"
echo "Log: tail -f ${LOGS_DIR}/gain_calibration_${RUN}_*.log"
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
+MaxRuntime = $MAX_RUNTIME_MERGE
request_cpus = 1
request_memory = 4GB
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
echo "Log: tail -f ${LOGS_DIR}/gain_calibration_${RUN}_*.log"
echo ""
EOFSUBGAIN
fi

chmod +x "$SCRIPTS_DIR/submit_gain_calibration.sh"


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
echo ""
echo "=========================================="
