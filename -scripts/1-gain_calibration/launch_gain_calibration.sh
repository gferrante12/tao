#!/bin/bash
set -e

# =====================================================
# launch_gain_calibration.sh - v1.1
# Standalone launcher for gain calibration pipeline.
# Generates job scripts for:
#   - gain_calibration_stable.py     (multi-Gaussian, 3 classification methods)
#   - gain_calibration_experimental.py (EMG + AP models, N channels)
#   - gain_vs_time.py                (gain evolution over time)
#
# Each tool can be enabled/disabled via flags below.
# Works on CNAF (HTCondor) and IHEP (hep_sub).
#
# Usage:
#   ./launch_gain_calibration.sh RUN
#   ./launch_gain_calibration.sh 1295
# =====================================================

# =====================================================
# ██  USER FLAGS — edit these to control what runs  ██
# =====================================================
RUN_STABLE=true                 # gain_calibration_stable.py
RUN_EXPERIMENTAL=true           # gain_calibration_experimental.py
RUN_GAIN_VS_TIME=true           # gain_vs_time.py

PLOTS_MODE="sample"             # none / sample / all
N_EXPERIMENTAL_CH=3             # channels for experimental
USE_RAW_HISTS=false             # --use-raw flag (false → H_adcClean_*)
MAX_RUNTIME=7200                # 2h per job
# =====================================================

if [ -z "$1" ]; then
    echo "ERROR: RUN number not provided!"
    echo ""
    echo "Usage: $0 RUN"
    echo ""
    echo "Flags (edit inside script):"
    echo "  RUN_STABLE=$RUN_STABLE"
    echo "  RUN_EXPERIMENTAL=$RUN_EXPERIMENTAL"
    echo "  RUN_GAIN_VS_TIME=$RUN_GAIN_VS_TIME"
    echo "  PLOTS_MODE=$PLOTS_MODE"
    echo "  N_EXPERIMENTAL_CH=$N_EXPERIMENTAL_CH"
    echo ""
    exit 1
fi

RUN=$1
JUNO_RELEASE=/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1

# =====================================================
# Cluster Detection
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
        SCRIPTS_PY="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        CHARGE_BASE="${BASE_DIR}/0-extract_QT_results"
        RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
        USE_EOS_CLI=false
        ;;
    "IHEP")
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        SCRIPTS_PY="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        CHARGE_BASE="${BASE_DIR}/0-extract_QT_results"
        RTRAW_BASE="/eos/juno/tao-rtraw"
        EOS_SERVER="root://junoeos01.ihep.ac.cn"
        USE_EOS_CLI=true
        ;;
    *)
        echo "ERROR: Unknown cluster"
        exit 1
        ;;
esac

echo "============================================"
echo "GAIN CALIBRATION LAUNCHER"
echo "============================================"
echo "Cluster        : $CLUSTER"
echo "RUN            : $RUN"
echo "Stable         : $RUN_STABLE"
echo "Experimental   : $RUN_EXPERIMENTAL"
echo "Gain vs Time   : $RUN_GAIN_VS_TIME"
echo "Plots mode     : $PLOTS_MODE"
echo ""

# =====================================================
# Locate merged CHARGE ROOT file
# =====================================================
MERGED_CHARGE_DIR="${CHARGE_BASE}/charge_merged"
MERGED_ROOT=""

# Try to find the merged file
for pattern in "charge_merged_RUN${RUN}*.root" "merged_charge_RUN${RUN}*.root" "charge_RUN${RUN}_merged*.root"; do
    FOUND=$(find "$MERGED_CHARGE_DIR" -name "$pattern" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        MERGED_ROOT="$FOUND"
        break
    fi
done

if [ -z "$MERGED_ROOT" ]; then
    # Fallback: any ROOT file in merged dir
    MERGED_ROOT=$(find "$MERGED_CHARGE_DIR" -name "*.root" 2>/dev/null | head -1)
fi

if [ -z "$MERGED_ROOT" ] || [ ! -f "$MERGED_ROOT" ]; then
    echo "ERROR: Cannot find merged CHARGE ROOT file in:"
    echo "  $MERGED_CHARGE_DIR"
    echo ""
    echo "Run launch_extract_charge_calib.sh first, then submit_merge.sh"
    exit 1
fi

echo "Input file: $MERGED_ROOT"
echo "  Size: $(du -h "$MERGED_ROOT" | cut -f1)"
echo ""

# =====================================================
# Directory setup
# =====================================================
SCRIPTS_DIR="${SCRIPTS_PY}/launchers/RUN${RUN}"
OUTERR_DIR="${SCRIPTS_PY}/launchers/out-err"
OUTPUT_BASE="${BASE_DIR}/1-gain_calibration_results/RUN${RUN}"
LOGS_DIR="${BASE_DIR}/logs/RUN${RUN}/1-gain_calibration_results"

# Guard: warn if launcher folder already exists
if [ -d "$SCRIPTS_DIR" ]; then
    echo "WARNING: Launcher folder already exists:"
    echo "  $SCRIPTS_DIR"
    echo "Existing scripts will be overwritten. Continue? [y/N]"
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$LOGS_DIR"

RUN_NAME="RUN${RUN}"
RAW_FLAG=""
[ "$USE_RAW_HISTS" = true ] && RAW_FLAG="--use-raw"

# =====================================================
# Helper: generate cluster-specific submit wrapper
# =====================================================
generate_submit() {
    local JOB_NAME=$1
    local JOB_SCRIPT=$2
    local MEM=${3:-4000}

    if [ "$CLUSTER" = "IHEP" ]; then
        cat > "${SCRIPTS_DIR}/submit_${JOB_NAME}.sh" <<EOFSUB
#!/bin/bash
echo "Submitting ${JOB_NAME} for RUN ${RUN}..."
cd \$(dirname \$0)
hep_sub "${JOB_SCRIPT}" \\
    -g juno \\
    -o "${OUTERR_DIR}/${JOB_NAME}.out" \\
    -e "${OUTERR_DIR}/${JOB_NAME}.err" \\
    -mem ${MEM}
echo "Submitted. Check: hep_q -u \$USER"
EOFSUB
    else
        local JOB_ABS=$(realpath "$JOB_SCRIPT")
        local OUTERR_ABS=$(realpath "$OUTERR_DIR")
        cat > "${SCRIPTS_DIR}/${JOB_NAME}.sub" <<EOFSUB
universe = vanilla
executable = ${JOB_ABS}
output = ${OUTERR_ABS}/${JOB_NAME}.out
error  = ${OUTERR_ABS}/${JOB_NAME}.err
log    = ${OUTERR_ABS}/${JOB_NAME}.log
+MaxRuntime = ${MAX_RUNTIME}
request_cpus = 1
request_memory = ${MEM}MB
queue
EOFSUB
        cat > "${SCRIPTS_DIR}/submit_${JOB_NAME}.sh" <<EOFSUB
#!/bin/bash
echo "Submitting ${JOB_NAME} for RUN ${RUN}..."
cd \$(dirname \$0)
condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name ${JOB_NAME} ${JOB_NAME}.sub
echo "Submitted. Monitor: condor_q -name sn01-htc.cr.cnaf.infn.it"
EOFSUB
    fi
    chmod +x "${SCRIPTS_DIR}/submit_${JOB_NAME}.sh"
}


# =====================================================
# JOB 1: gain_calibration_stable.py
# =====================================================
if [ "$RUN_STABLE" = true ]; then
    echo "Generating gain_calibration_stable job..."
    STABLE_OUT="${OUTPUT_BASE}/stable_$(date +%Y%m%d_%H%M%S)"
    STABLE_JOB="${SCRIPTS_DIR}/gain_stable_${RUN}.sh"

    cat > "$STABLE_JOB" <<EOFSTABLE
#!/bin/bash
set -e
LOG_FILE="${LOGS_DIR}/gain_stable_${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "Gain Calibration STABLE — RUN ${RUN}"
echo "=========================================="

source "${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"
source "${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

mkdir -p "${STABLE_OUT}"

START_TIME=\$(date +%s)

python3 "${SCRIPTS_PY}/gain_calibration_stable.py" \\
    "${MERGED_ROOT}" \\
    "${STABLE_OUT}" \\
    "${RUN_NAME}" \\
    ${RAW_FLAG} \\
    --plots ${PLOTS_MODE}

END_TIME=\$(date +%s)
echo ""
echo "Done in \$(( (END_TIME - START_TIME) / 60 ))m \$(( (END_TIME - START_TIME) % 60 ))s"
echo "Output: ${STABLE_OUT}"
deactivate
EOFSTABLE
    chmod +x "$STABLE_JOB"
    generate_submit "gain_stable_${RUN}" "$STABLE_JOB" 4000
    echo "  → $STABLE_JOB"
fi


# =====================================================
# JOB 2: gain_calibration_experimental.py
# =====================================================
if [ "$RUN_EXPERIMENTAL" = true ]; then
    echo "Generating gain_calibration_experimental job..."
    EXPER_OUT="${OUTPUT_BASE}/experimental_$(date +%Y%m%d_%H%M%S)"
    EXPER_JOB="${SCRIPTS_DIR}/gain_experimental_${RUN}.sh"

    cat > "$EXPER_JOB" <<EOFEXPER
#!/bin/bash
set -e
LOG_FILE="${LOGS_DIR}/gain_experimental_${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "Gain Calibration EXPERIMENTAL — RUN ${RUN}"
echo "  Models: multigauss, EMG, multigauss_ap"
echo "  Channels: ${N_EXPERIMENTAL_CH}"
echo "=========================================="

source "${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"
source "${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

mkdir -p "${EXPER_OUT}"

START_TIME=\$(date +%s)

python3 "${SCRIPTS_PY}/gain_calibration_experimental.py" \\
    "${MERGED_ROOT}" \\
    "${EXPER_OUT}" \\
    "${RUN_NAME}" \\
    ${RAW_FLAG} \\
    --n-channels ${N_EXPERIMENTAL_CH}

END_TIME=\$(date +%s)
echo ""
echo "Done in \$(( (END_TIME - START_TIME) / 60 ))m \$(( (END_TIME - START_TIME) % 60 ))s"
echo "Output: ${EXPER_OUT}"
deactivate
EOFEXPER
    chmod +x "$EXPER_JOB"
    generate_submit "gain_experimental_${RUN}" "$EXPER_JOB" 8000
    echo "  → $EXPER_JOB"
fi


# =====================================================
# JOB 3: gain_vs_time.py
# =====================================================
if [ "$RUN_GAIN_VS_TIME" = true ]; then
    echo "Generating gain_vs_time job..."
    GVT_OUT="${OUTPUT_BASE}/gain_vs_time_$(date +%Y%m%d_%H%M%S)"
    GVT_JOB="${SCRIPTS_DIR}/gain_vs_time_${RUN}.sh"
    SINGLE_CHARGE_DIR=$(ls -dt $CHARGE_BASE/charge_single/RUN${RUN}/*/  2>/dev/null | head -1)

    cat > "$GVT_JOB" <<EOFGVT
#!/bin/bash
set -e
LOG_FILE="${LOGS_DIR}/gain_vs_time_${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "Gain vs Time — RUN ${RUN}"
echo "=========================================="

source "${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"
source "${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

mkdir -p "${GVT_OUT}"

# Build timestamps from RTRAW filenames
TIMESTAMPS_FILE="${GVT_OUT}/timestamps.txt"
echo "# file_number  unix_timestamp" > "\$TIMESTAMPS_FILE"
NFILES=0

if [ "${USE_EOS_CLI}" = "true" ]; then
    RTRAW_LIST=\$(eos ls "${RTRAW_BASE}" 2>/dev/null | grep '\.rtraw\$' | sort)
else
    RTRAW_LIST=\$(ls "${RTRAW_BASE}"/*.rtraw 2>/dev/null | xargs -n1 basename | sort)
fi

while IFS= read -r fname; do
    [ -z "\$fname" ] && continue
    FILE_NUM=\$(echo "\$fname" | grep -oE '\.[0-9]{3}_T[0-9]' | grep -oE '[0-9]{3}' | head -1)
    [ -z "\$FILE_NUM" ] && continue
    TS14=\$(echo "\$fname" | grep -oE '\.[0-9]{14}\.' | tr -d '.')
    [ -z "\$TS14" ] && continue
    YY=\${TS14:0:4}; MM=\${TS14:4:2}; DD=\${TS14:6:2}
    HH=\${TS14:8:2}; MI=\${TS14:10:2}; SS=\${TS14:12:2}
    UNIX_TS=\$(date -d "\${YY}-\${MM}-\${DD} \${HH}:\${MI}:\${SS} UTC" +%s 2>/dev/null || echo "0")
    echo "\$(echo \$FILE_NUM | sed 's/^0*//')  \$UNIX_TS" >> "\$TIMESTAMPS_FILE"
    NFILES=\$((NFILES+1))
done <<< "\$RTRAW_LIST"

echo "Built timestamps: \$NFILES entries"

TS_FLAG=""
[ \$NFILES -gt 0 ] && TS_FLAG="--timestamps \$TIMESTAMPS_FILE"

python3 "${SCRIPTS_PY}/gain_vs_time.py" \\
    "${SINGLE_CHARGE_DIR}" \\
    "${GVT_OUT}" \\
    "${RUN_NAME}" \\
    \$TS_FLAG

echo ""
echo "Done! Output: ${GVT_OUT}"
deactivate
EOFGVT
    chmod +x "$GVT_JOB"
    generate_submit "gain_vs_time_${RUN}" "$GVT_JOB" 8000
    echo "  → $GVT_JOB"
fi


# =====================================================
# submit_all.sh — run everything
# =====================================================
cat > "${SCRIPTS_DIR}/submit_all.sh" <<'EOFALL'
#!/bin/bash
echo "Submitting all enabled gain calibration jobs..."
SCRIPT_DIR=$(cd $(dirname $0) && pwd)
for sub in ${SCRIPT_DIR}/submit_gain_*.sh ${SCRIPT_DIR}/submit_gain_vs_time_*.sh; do
    [ -f "$sub" ] && echo "  Running: $(basename $sub)" && bash "$sub"
done
echo "All jobs submitted."
EOFALL
chmod +x "${SCRIPTS_DIR}/submit_all.sh"


# =====================================================
# Summary
# =====================================================
echo ""
echo "============================================"
echo "SETUP COMPLETE"
echo "============================================"
echo ""
echo "Cluster       : $CLUSTER"
echo "RUN           : $RUN"
echo "Input         : $MERGED_ROOT"
echo "Output base   : $OUTPUT_BASE"
echo "Scripts       : $SCRIPTS_DIR"
echo ""
echo "Generated jobs:"
[ "$RUN_STABLE" = true ]       && echo "  ✓ gain_stable_${RUN}.sh          → submit_gain_stable_${RUN}.sh"
[ "$RUN_EXPERIMENTAL" = true ] && echo "  ✓ gain_experimental_${RUN}.sh    → submit_gain_experimental_${RUN}.sh"
[ "$RUN_GAIN_VS_TIME" = true ] && echo "  ✓ gain_vs_time_${RUN}.sh         → submit_gain_vs_time_${RUN}.sh"
echo ""
echo "To submit all:"
echo "  cd $SCRIPTS_DIR && ./submit_all.sh"
echo ""
echo "============================================"
