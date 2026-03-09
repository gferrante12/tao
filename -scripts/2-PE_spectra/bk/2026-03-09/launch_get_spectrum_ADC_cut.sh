#!/bin/bash
set -e

# =====================================================
# launch_get_spectrum_ADC_cut.sh - v1.0
# Launches get_spectrum_ADC_cut.py on a full RTRAW run.
#
# Produces three independent ADC-based PE spectra per file:
#   Mode A — standard:  ADC_HIT_MIN <= adc <= ADC_HIT_MAX  + MAX_TOTAL_ADC cut
#   Mode B — inv+cut:   adc >= ADC_HIT_MAX                  + MAX_TOTAL_ADC cut
#   Mode C — inv-cut:   adc >= ADC_HIT_MAX                  + no event ADC cut
#
# Full CALIB2 multi-detector veto (CD+WT+TVT) is applied in all modes.
# Gain calibration is auto-selected from the official path based on run
# number (sipm_calib_1157-1193.txt or sipm_calib_1295-.txt); an explicit
# override file can be supplied as the second argument.
#
# Works on both CNAF (HTCondor via condor_submit) and
# IHEP (hep_sub) clusters.
# =====================================================

if [ -z "$1" ]; then
    echo "ERROR: RUN number not provided!"
    echo ""
    echo "Usage: $0 RUN [CALIB_FILE]"
    echo ""
    echo "Arguments:"
    echo "  RUN        - Run number (required)"
    echo "  CALIB_FILE - Path to a gain calibration TXT file (optional)."
    echo "               If omitted the official run-range file is used:"
    echo "                 RUN <= 1193  → sipm_calib_1157-1193.txt"
    echo "                 RUN >= 1295  → sipm_calib_1295-.txt"
    echo "                 RUN 1194-1294 → sipm_calib_1295-.txt  (with warning)"
    echo ""
    echo "Examples:"
    echo "  # Auto-select official calibration:"
    echo "  $0 1295"
    echo ""
    echo "  # Override with a custom calibration file:"
    echo "  $0 1295 /path/to/my_sipm_calib.txt"
    echo ""
    exit 1
fi

RUN=$1
CALIB_FILE_OVERRIDE="${2:-}"

# =====================================================
# Cluster Detection and Path Configuration
# (mirrors launch_get_spectrum.sh and
#  launch_extract_charge_calib.sh exactly)
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
        SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/2-PE_spectra"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
        USE_EOS_CLI=false
        ;;
    "IHEP")
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/2-PE_spectra"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        RTRAW_BASE="/eos/juno/tao-rtraw"
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

# =====================================================
# EOS Helper Functions  (identical to other launchers)
# =====================================================

eos_find_run() {
    local base=$1
    local run=$2

    if [ "$USE_EOS_CLI" = true ]; then
        echo "Searching for RUN $run in EOS..." >&2

        local run_prefix=$(printf "%08d" $((run / 100 * 100)))
        local group_prefix=$(printf "%08d" $((run / 1000 * 1000)))

        local tao_versions
        tao_versions=$(eos ls "$base" 2>/dev/null | grep -E '^T[0-9]+\.[0-9]+\.[0-9]+$' | sort -V -r)

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

to_xrootd_url() {
    local path=$1
    if [ "$USE_EOS_CLI" = true ]; then
        echo "${EOS_SERVER}/${path}"
    else
        echo "$path"
    fi
}

# =====================================================
# Validate optional calibration override file
# =====================================================
if [ -n "$CALIB_FILE_OVERRIDE" ] && [ ! -f "$CALIB_FILE_OVERRIDE" ]; then
    echo "ERROR: Calibration override file not found: $CALIB_FILE_OVERRIDE"
    exit 1
fi

# =====================================================
# Print run-range calibration selection info
# (purely informational — the Python script does the
#  actual selection via get_official_calib_file())
# =====================================================
CALIB_LABEL="default"
if [ -n "$CALIB_FILE_OVERRIDE" ]; then
    CALIB_LABEL="custom:$(basename "$CALIB_FILE_OVERRIDE")"
    echo "Calibration override: $CALIB_FILE_OVERRIDE"
elif [ "$RUN" -ge 1295 ] 2>/dev/null; then
    echo "Calibration (auto): sipm_calib_1295-.txt  [RUN $RUN >= 1295]"
elif [ "$RUN" -le 1193 ] 2>/dev/null; then
    echo "Calibration (auto): sipm_calib_1157-1193.txt  [RUN $RUN <= 1193]"
    if [ "$RUN" -lt 1157 ] 2>/dev/null; then
        echo "WARNING: RUN $RUN is below the officially calibrated range (1157-1193)."
        echo "         Using sipm_calib_1157-1193.txt as the closest available default."
        echo ""
    fi
else
    echo "WARNING: RUN $RUN is in the gap range 1194-1294 with no dedicated calibration."
    echo "         Using sipm_calib_1295-.txt as best guess."
    echo ""
    CALIB_LABEL="gap_default"
fi

# =====================================================
# Folder name (used for scripts dir + output dir)
# =====================================================
FOLDER_NAME="${RUN}_rtraw_ADC_cut_${CALIB_LABEL}"

# =====================================================
# Find RTRAW data
# =====================================================
echo ""
echo "Searching for RUN $RUN in $RTRAW_BASE..."

INPUT_BASE=$(eos_find_run "$RTRAW_BASE" "$RUN")

if [ -z "$INPUT_BASE" ]; then
    echo "ERROR: RUN $RUN not found in $RTRAW_BASE"
    echo ""
    echo "Searched structure:"
    echo "  $RTRAW_BASE/<TAO-version>/<stream>/<group>/<subgroup>/<run>/"
    if [ "$USE_EOS_CLI" = true ]; then
        echo ""
        echo "Available TAO versions in EOS:"
        eos ls "$RTRAW_BASE" 2>/dev/null | head -10
    fi
    exit 1
fi

echo "Found: $INPUT_BASE"

# =====================================================
# Extract TAO / JUNO version from path
# =====================================================
TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')

if [ -z "$TAO_VERSION" ]; then
    echo "ERROR: Could not parse TAO version from path:"
    echo "  $INPUT_BASE"
    exit 1
fi

JUNO_VERSION=$(echo "$TAO_VERSION" | sed 's/^T/J/')
JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION}"

# Verify JUNO release; try minor-version fallback
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
# Count RTRAW files
# =====================================================
echo "Listing RTRAW files..."

if [ "$USE_EOS_CLI" = true ]; then
    RTRAW_FILES=($(eos ls "$INPUT_BASE" 2>/dev/null | grep '\.rtraw$' | sort | while read f; do echo "$INPUT_BASE/$f"; done))
else
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

# =====================================================
# Directory setup
# =====================================================
SCRIPTS_DIR="./get_spectrum_ADC_cut/${FOLDER_NAME}"
OUTERR_DIR="${SCRIPTS_DIR}/out-err"
SPECTRUM_DIR="${BASE_DIR}/2-ADC_cut_PE_spectra_results/RUN${RUN}/${FOLDER_NAME}_$(date +%Y-%m-%d_%H-%M-%S)"
LOGS_DIR="${BASE_DIR}/logs/RUN${RUN}/2-ADC_cut_PE_spectra_results/${FOLDER_NAME}"

# Python script to launch (must live in SCRIPTS_BASE)
ADC_cut_SCRIPT="${SCRIPTS_BASE}/get_spectrum_ADC_cut.py"

# HTCondor / HEP settings
MAX_RUNTIME=7200        # 2 hours per per-file job
MAX_RUNTIME_MERGE=1800  # 30 min for hadd merge

mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$SPECTRUM_DIR" "$LOGS_DIR"

# =====================================================
# Print configuration banner
# =====================================================
echo ""
echo "=============================================================="
echo "  ADC_cut SPECTRUM EXTRACTION - v1.0"
echo "=============================================================="
echo "  Cluster:      $CLUSTER"
echo "  RUN:          $RUN"
echo "  TAO version:  $TAO_VERSION"
echo "  JUNO release: $JUNO_VERSION"
echo "  Input path:   $INPUT_BASE"
echo "  Total files:  $TOTAL_FILES"
if [ "$USE_EOS_CLI" = true ]; then
    echo "  EOS Mode:     CLI (XRootD URLs)"
fi
echo ""
if [ -n "$CALIB_FILE_OVERRIDE" ]; then
    echo "  Calibration:  $CALIB_FILE_OVERRIDE  [OVERRIDE]"
else
    echo "  Calibration:  auto (run-range aware, see above)"
fi
echo ""
echo "  Spectra produced per file:"
echo "    Mode A  ADC_HIT_MIN <= adc <= ADC_HIT_MAX  + MAX_TOTAL_ADC event cut"
echo "    Mode B  adc >= ADC_HIT_MAX (inverted)       + MAX_TOTAL_ADC event cut"
echo "    Mode C  adc >= ADC_HIT_MAX (inverted)       + no MAX_TOTAL_ADC cut"
echo ""
echo "  Veto:         CALIB2 (CD+WT+TVT muon, 1000µs+5µs windows, TDC [240,440]ns)"
echo "  Folder:       $FOLDER_NAME"
echo "=============================================================="
echo ""

# =====================================================
# Generate individual per-file job scripts
# =====================================================
echo "Generating $TOTAL_FILES job scripts..."

for i in "${!RTRAW_FILES[@]}"; do
    RTRAW_FILE=${RTRAW_FILES[$i]}
    FILE_BASENAME=$(basename "$RTRAW_FILE")
    JOB_ID=$(printf "%03d" $((i+1)))

    # Convert path to XRootD URL when on IHEP
    RTRAW_FILE_URL=$(to_xrootd_url "$RTRAW_FILE")

    MAIN="${SCRIPTS_DIR}/ADC_cut_${RUN}_${JOB_ID}.sh"

    cat > "$MAIN" <<EOFMAIN
#!/bin/bash
set -e

# ====== CONFIGURATION ======
RUN=${RUN}
RTRAW_FILE="${RTRAW_FILE_URL}"
SPECTRUM_DIR=${SPECTRUM_DIR}
ADC_cut_SCRIPT=${ADC_cut_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
JOB_ID=${JOB_ID}
LOGS_DIR=${LOGS_DIR}
TAO_VERSION=${TAO_VERSION}
CALIB_FILE_OVERRIDE="${CALIB_FILE_OVERRIDE}"

LOG_FILE="\${LOGS_DIR}/ADC_cut_\${RUN}_\${JOB_ID}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "ADC_cut Spectrum - RUN \$RUN - Job \$JOB_ID"
echo "=========================================="
echo "TAO Version : \$TAO_VERSION"
echo "Input       : \$RTRAW_FILE"
if [ -n "\$CALIB_FILE_OVERRIDE" ]; then
    echo "Calibration : \$CALIB_FILE_OVERRIDE  [OVERRIDE]"
else
    echo "Calibration : auto (run-range aware)"
fi
echo ""

# ── Output file (derive from file number embedded in filename) ──────────────
FILE_NUM=\$(echo "${FILE_BASENAME}" | grep -oE '[0-9]{3,}' | tail -1)
if [ -z "\$FILE_NUM" ]; then
    FILE_NUM=${JOB_ID}
fi

OUTPUT_FILE="\${SPECTRUM_DIR}/ADC_cut_spectrum_RUN\${RUN}_\${FILE_NUM}.root"

# Skip if output already exists
if [ -f "\$OUTPUT_FILE" ]; then
    echo "Output already exists, skipping: \$(basename \$OUTPUT_FILE)"
    exit 0
fi

# ── Environment setup ────────────────────────────────────────────────────────
echo "Setting up JUNO-TAO environment..."
source "\${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"

echo "Activating Python virtual environment..."
source "\${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# ── Build Python command ─────────────────────────────────────────────────────
CMD="python \"\$ADC_cut_SCRIPT\" \"\$RTRAW_FILE\" \"\$SPECTRUM_DIR\" --run \$RUN"
if [ -n "\$CALIB_FILE_OVERRIDE" ]; then
    CMD="\$CMD --calib-file \"\$CALIB_FILE_OVERRIDE\""
fi

# ── Run ──────────────────────────────────────────────────────────────────────
echo ""
echo "Running get_spectrum_ADC_cut.py..."
eval \$CMD

EXIT_CODE=\$?
if [ \$EXIT_CODE -ne 0 ]; then
    echo "ERROR: get_spectrum_ADC_cut.py failed (exit code \$EXIT_CODE)"
    deactivate
    exit 1
fi

if [ ! -f "\$OUTPUT_FILE" ]; then
    echo "ERROR: Expected output not found: \$OUTPUT_FILE"
    deactivate
    exit 1
fi

echo ""
echo "Done: \$(basename \$OUTPUT_FILE)"
deactivate
EOFMAIN

    chmod +x "$MAIN"

    # ── Generate cluster-specific submission artefacts ────────────────────────
    if [ "$CLUSTER" = "CNAF" ]; then
        SUBMIT="${SCRIPTS_DIR}/ADC_cut_${RUN}_${JOB_ID}.sub"
        MAIN_ABS=$(realpath "$MAIN")
        OUTERR_ABS=$(realpath "$OUTERR_DIR")

        cat > "$SUBMIT" <<EOFSUBMIT
universe = vanilla
executable = $MAIN_ABS
output = $OUTERR_ABS/ADC_cut_${RUN}_${JOB_ID}.out
error  = $OUTERR_ABS/ADC_cut_${RUN}_${JOB_ID}.err
log    = $OUTERR_ABS/ADC_cut_${RUN}_${JOB_ID}.log
+MaxRuntime = $MAX_RUNTIME
request_cpus = 1
request_memory = 2GB
queue
EOFSUBMIT
    fi
done

echo "Generated $TOTAL_FILES job scripts"
if [ "$CLUSTER" = "CNAF" ]; then
    echo "Generated $TOTAL_FILES HTCondor submit files"
fi
echo ""

# =====================================================
# joblist.sh — cluster-aware job submission list
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/joblist.sh" <<'EOFJOBLIST'
#!/bin/bash
# Throttled job submission for IHEP using hep_sub

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
OUTERR_DIR="${SCRIPT_DIR}/out-err"
MAX_CONCURRENT=100
CHECK_INTERVAL=30

echo "Starting ADC_cut spectrum job submission..."
echo "Max concurrent jobs: $MAX_CONCURRENT"
echo ""

JOB_SCRIPTS=($(ls "${SCRIPT_DIR}"/ADC_cut_*.sh 2>/dev/null | sort))
TOTAL=${#JOB_SCRIPTS[@]}

if [ $TOTAL -eq 0 ]; then
    echo "ERROR: No job scripts found!"
    exit 1
fi

echo "Found $TOTAL job scripts"
echo ""

count_my_jobs() {
    hep_q -u $USER 2>/dev/null | grep -E "^ *[0-9]+" | wc -l
}

SUBMITTED=0
FAILED=0

for SCRIPT in "${JOB_SCRIPTS[@]}"; do
    JOB_NAME=$(basename "$SCRIPT" .sh)

    CURRENT_JOBS=$(count_my_jobs)
    while [ $CURRENT_JOBS -ge $MAX_CONCURRENT ]; do
        echo "[$SUBMITTED/$TOTAL] Queue full ($CURRENT_JOBS jobs). Waiting ${CHECK_INTERVAL}s..."
        sleep $CHECK_INTERVAL
        CURRENT_JOBS=$(count_my_jobs)
    done

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

    sleep 0.2
done

echo ""
echo "=========================================="
echo "Submission complete"
echo "=========================================="
echo "Total: $TOTAL"
echo "Submitted: $SUBMITTED"
echo "Failed: $FAILED"
echo ""
echo "Check queue: hep_q -u $USER"
EOFJOBLIST

else
    # CNAF: plain list of condor_submit calls
    cat > "$SCRIPTS_DIR/joblist.sh" <<EOFJOBLIST
#!/bin/bash
# HTCondor submission for CNAF
EOFJOBLIST

    for i in "${!RTRAW_FILES[@]}"; do
        JOB_ID=$(printf "%03d" $((i+1)))
        echo "condor_submit -maxjobs 51 -spool -name sn01-htc.cr.cnaf.infn.it \
-batch-name ADC_cut_${RUN}_${JOB_ID} ADC_cut_${RUN}_${JOB_ID}.sub" \
            >> "$SCRIPTS_DIR/joblist.sh"
    done
fi

chmod +x "$SCRIPTS_DIR/joblist.sh"

# =====================================================
# submit_all.sh
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo ""
echo "=========================================="
echo "Submitting ${TOTAL_FILES} ADC_cut jobs for RUN ${RUN}"
echo "=========================================="
echo "Cluster: IHEP"
echo "Folder : ${FOLDER_NAME}"
echo ""

cd \$(dirname \$0)

if [ -f .submission.lock ]; then
    PID=\$(cat .submission.lock)
    if ps -p \$PID > /dev/null 2>&1; then
        echo "ERROR: Submission already running (PID: \$PID)"
        echo "To force restart: rm .submission.lock"
        exit 1
    fi
fi

nohup bash joblist.sh > joblist.out 2>&1 &
SUBMIT_PID=\$!
echo \$SUBMIT_PID > .submission.lock

echo "Job submission started in background (PID: \$SUBMIT_PID)"
echo ""
echo "Monitor:     tail -f \$(pwd)/joblist.out"
echo "Queue:       hep_q -u \$USER"
echo "Status:      ./check_status.sh"
echo ""
EOFSUBMIT

else
    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo ""
echo "=========================================="
echo "Submitting ${TOTAL_FILES} ADC_cut jobs for RUN ${RUN}"
echo "=========================================="
echo "Cluster: CNAF"
echo "Folder : ${FOLDER_NAME}"
echo ""

cd \$(dirname \$0)

nohup junosub joblist.sh > joblist.out 2>&1 &
SUBMIT_PID=\$!

echo "Job submission started in background (PID: \$SUBMIT_PID)"
echo ""
echo "Monitor: tail -f \$(pwd)/joblist.out"
echo "Queue:   condor_q -name sn01-htc.cr.cnaf.infn.it -batch ADC_cut_${RUN}"
echo "Status:  ./check_status.sh"
echo ""
EOFSUBMIT
fi

chmod +x "$SCRIPTS_DIR/submit_all.sh"

# =====================================================
# check_status.sh
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash
echo ""
echo "=========================================="
echo "Status for RUN ${RUN} ADC_cut spectra (IHEP)"
echo "=========================================="
echo ""

TOTAL=$TOTAL_FILES
COMPLETED=\$(ls "${SPECTRUM_DIR}"/ADC_cut_spectrum_RUN${RUN}_*.root 2>/dev/null \
             | grep -v MERGED | wc -l)
MERGED_EXISTS=\$(ls "${SPECTRUM_DIR}"/ADC_cut_spectrum_RUN${RUN}_MERGED.root \
                 2>/dev/null | wc -l)

echo "Individual files:"
echo "  Total    : \$TOTAL"
echo "  Completed: \$COMPLETED (\$((COMPLETED * 100 / TOTAL))%)"
echo "  Remaining: \$((TOTAL - COMPLETED))"
echo ""
echo "Merged    : \$([ \$MERGED_EXISTS -eq 1 ] && echo 'YES ✓' || echo 'NO')"
echo ""
echo "Queue:"
hep_q -u \$USER 2>/dev/null | head -20
echo ""
if [ \$COMPLETED -eq \$TOTAL ] && [ \$MERGED_EXISTS -eq 0 ]; then
    echo "→ All jobs done. Run: ./submit_merge.sh"
elif [ \$MERGED_EXISTS -eq 1 ]; then
    echo "→ Complete. ✓"
fi
EOFSTATUS

else
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash
echo ""
echo "=========================================="
echo "Status for RUN ${RUN} ADC_cut spectra (CNAF)"
echo "=========================================="
echo ""

TOTAL=$TOTAL_FILES
COMPLETED=\$(ls "${SPECTRUM_DIR}"/ADC_cut_spectrum_RUN${RUN}_*.root 2>/dev/null \
             | grep -v MERGED | wc -l)
MERGED_EXISTS=\$(ls "${SPECTRUM_DIR}"/ADC_cut_spectrum_RUN${RUN}_MERGED.root \
                 2>/dev/null | wc -l)

echo "Individual files:"
echo "  Total    : \$TOTAL"
echo "  Completed: \$COMPLETED (\$((COMPLETED * 100 / TOTAL))%)"
echo "  Remaining: \$((TOTAL - COMPLETED))"
echo ""
echo "Merged    : \$([ \$MERGED_EXISTS -eq 1 ] && echo 'YES ✓' || echo 'NO')"
echo ""
echo "Queue:"
condor_q -name sn01-htc.cr.cnaf.infn.it -batch ADC_cut_${RUN} 2>/dev/null \
    || echo "No jobs in queue"
echo ""
if [ \$COMPLETED -eq \$TOTAL ] && [ \$MERGED_EXISTS -eq 0 ]; then
    echo "→ All jobs done. Run: ./submit_merge.sh"
elif [ \$MERGED_EXISTS -eq 1 ]; then
    echo "→ Complete. ✓"
fi
EOFSTATUS
fi

chmod +x "$SCRIPTS_DIR/check_status.sh"

# =====================================================
# merge job — uses hadd to add the three mode histograms
# across all per-file ROOT outputs.
# (h_PEcontin_a, h_PEdiscrete_a, h_nHit_a, same for b/c
#  are TH1F objects; hadd adds them correctly.)
# =====================================================
echo ""
echo "Generating merge job..."
MAIN_MERGE="${SCRIPTS_DIR}/merge_ADC_cut_${RUN}.sh"

cat > "$MAIN_MERGE" <<EOFMERGE
#!/bin/bash
set -e

RUN=${RUN}
SPECTRUM_DIR=${SPECTRUM_DIR}
JUNO_RELEASE=${JUNO_RELEASE}
LOGS_DIR=${LOGS_DIR}

LOG_FILE="\${LOGS_DIR}/merge_ADC_cut_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo ""
echo "=========================================="
echo "Merge ADC_cut Spectra - RUN \$RUN"
echo "=========================================="

OUTPUT_FILE="\${SPECTRUM_DIR}/ADC_cut_spectrum_RUN\${RUN}_MERGED.root"

if [ -f "\$OUTPUT_FILE" ]; then
    echo "Merged file already exists, skipping."
    exit 0
fi

# Collect all per-file outputs (exclude any pre-existing merged file)
INPUT_FILES=(\$(ls "\${SPECTRUM_DIR}"/ADC_cut_spectrum_RUN\${RUN}_*.root 2>/dev/null \
              | grep -v "_MERGED.root" | sort))
N=\${#INPUT_FILES[@]}

if [ \$N -eq 0 ]; then
    echo "ERROR: No individual ADC_cut_spectrum files found in \$SPECTRUM_DIR"
    exit 1
fi

echo "Found \$N input files"
echo "Output : \$OUTPUT_FILE"
echo ""

# Source JUNO environment for ROOT (hadd)
source "\${JUNO_RELEASE}/setup-tao.sh"

echo "Running hadd..."
hadd -f "\$OUTPUT_FILE" "\${INPUT_FILES[@]}"

if [ \$? -ne 0 ]; then
    echo "ERROR: hadd failed!"
    exit 1
fi

echo ""
echo "Merge complete!"
echo "Output: \$OUTPUT_FILE"
echo ""

# Quick summary of merged histogram entries
echo "Histogram entries in merged file:"
python3 - <<'PYEOF'
import ROOT, os, sys
ROOT.gROOT.SetBatch(True)
f = ROOT.TFile.Open(os.environ.get('OUTPUT_FILE', ''))
if not f or f.IsZombie():
    print("  (cannot open merged file for summary)")
    sys.exit(0)
for mode in ('a', 'b', 'c'):
    for hname in (f"h_PEcontin_{mode}", f"h_PEdiscrete_{mode}", f"h_nHit_{mode}"):
        h = f.Get(hname)
        entries = int(h.GetEntries()) if h else -1
        print(f"  {hname:<22}: {entries:>10d} entries")
f.Close()
PYEOF
EOFMERGE

# Export OUTPUT_FILE for the inline python3 summary above
# (achieved via eval within the job; no action needed here)

chmod +x "$MAIN_MERGE"

# ── Cluster-specific merge submission ─────────────────────────────────────────
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_merge.sh" <<EOFSUBMERGE
#!/bin/bash
cd \$(dirname \$0)
echo "Submitting merge job for RUN ${RUN}..."
hep_sub merge_ADC_cut_${RUN}.sh \
    -g juno \
    -o out-err/merge_ADC_cut_${RUN}.out \
    -e out-err/merge_ADC_cut_${RUN}.err \
    -mem 4000
echo "Merge job submitted."
echo "Check: hep_q -u \$USER"
echo "Log  : tail -f ${LOGS_DIR}/merge_ADC_cut_${RUN}_*.log"
EOFSUBMERGE

else
    MAIN_MERGE_ABS=$(realpath "$MAIN_MERGE")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")

    cat > "$SCRIPTS_DIR/merge_ADC_cut_${RUN}.sub" <<EOFMERGESUB
universe = vanilla
executable = $MAIN_MERGE_ABS
output = $OUTERR_ABS/merge_ADC_cut_${RUN}.out
error  = $OUTERR_ABS/merge_ADC_cut_${RUN}.err
log    = $OUTERR_ABS/merge_ADC_cut_${RUN}.log
+MaxRuntime = $MAX_RUNTIME_MERGE
request_cpus = 1
request_memory = 4GB
queue
EOFMERGESUB

    cat > "$SCRIPTS_DIR/submit_merge.sh" <<EOFSUBMERGE
#!/bin/bash
cd \$(dirname \$0)
echo "Submitting merge job for RUN ${RUN}..."
condor_submit -name sn01-htc.cr.cnaf.infn.it \
    -batch-name merge_ADC_cut_${RUN} \
    merge_ADC_cut_${RUN}.sub
echo "Merge job submitted."
echo "Monitor: condor_q -name sn01-htc.cr.cnaf.infn.it"
echo "Log    : tail -f ${LOGS_DIR}/merge_ADC_cut_${RUN}_*.log"
EOFSUBMERGE
fi

chmod +x "$SCRIPTS_DIR/submit_merge.sh"

# =====================================================
# Final summary
# =====================================================
echo ""
echo "=========================================="
echo "SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Cluster    : $CLUSTER"
echo "RUN        : $RUN"
echo "TAO version: $TAO_VERSION"
echo "Input path : $INPUT_BASE"
echo "Files      : $TOTAL_FILES RTRAW files"
echo ""
if [ -n "$CALIB_FILE_OVERRIDE" ]; then
    echo "Calibration: $CALIB_FILE_OVERRIDE  [OVERRIDE]"
else
    echo "Calibration: auto (run-range aware)"
fi
echo ""
echo "Generated:"
echo "  - $TOTAL_FILES per-file job scripts"
if [ "$CLUSTER" = "CNAF" ]; then
    echo "  - $TOTAL_FILES HTCondor submit files"
fi
echo "  - joblist.sh / submit_all.sh / check_status.sh"
echo "  - merge_ADC_cut_${RUN}.sh + submit_merge.sh"
echo ""
echo "Output directory:"
echo "  $SPECTRUM_DIR"
echo ""
echo "Scripts directory:"
echo "  $SCRIPTS_DIR"
echo ""
echo "To submit all jobs:"
echo "  cd $SCRIPTS_DIR"
echo "  ./submit_all.sh"
echo ""
echo "To check progress:"
echo "  ./check_status.sh"
echo ""
echo "After all jobs complete, merge with:"
echo "  ./submit_merge.sh"
echo ""
echo "=========================================="
