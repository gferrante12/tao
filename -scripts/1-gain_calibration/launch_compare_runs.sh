#!/bin/bash
set -e

# =====================================================
# launch_compare_runs.sh
# Compare gain calibration between RUN 1295 and RUN 1410
#
# Runs compare_runs_gain.py on IHEP or CNAF.
# Can be submitted via hep_sub (IHEP) or condor (CNAF),
# or run interactively.
#
# Usage:
#   ./launch_compare_runs.sh              # interactive
#   ./launch_compare_runs.sh --submit     # submit to batch
# =====================================================

RUN_1=1295
RUN_2=1410

JUNO_RELEASE=/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1

# =====================================================
# Cluster detection
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
        ;;
    "IHEP")
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        SCRIPTS_PY="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        ;;
    *)
        echo "ERROR: Unknown cluster"
        exit 1
        ;;
esac

OUTPUT_DIR="${BASE_DIR}/1-gain_calibration_results/comparison_RUN${RUN_1}_vs_RUN${RUN_2}"
LOGS_DIR="${BASE_DIR}/logs/comparison"
OUTERR_DIR="${SCRIPTS_PY}/launchers/out-err"

mkdir -p "$OUTPUT_DIR" "$LOGS_DIR" "$OUTERR_DIR"

echo "============================================"
echo "GAIN COMPARISON LAUNCHER"
echo "============================================"
echo "Cluster   : $CLUSTER"
echo "RUN 1     : $RUN_1"
echo "RUN 2     : $RUN_2"
echo "Output    : $OUTPUT_DIR"
echo ""

# =====================================================
# Build the job script
# =====================================================
JOB_SCRIPT="${SCRIPTS_PY}/launchers/compare_runs_${RUN_1}_vs_${RUN_2}.sh"

cat > "$JOB_SCRIPT" <<EOFJOB
#!/bin/bash
set -e
LOG_FILE="${LOGS_DIR}/compare_RUN${RUN_1}_vs_RUN${RUN_2}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "Gain Comparison: RUN ${RUN_1} vs RUN ${RUN_2}"
echo "=========================================="

# Setup environment
source "${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"
source "${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# Matplotlib cache fix for AFS
export MPLCONFIGDIR="/tmp/matplotlib_\${USER}_\$\$"
mkdir -p "\$MPLCONFIGDIR"

START_TIME=\$(date +%s)

python3 "${SCRIPTS_PY}/compare_runs_gain.py" \\
    "${OUTPUT_DIR}"

END_TIME=\$(date +%s)
echo ""
echo "Done in \$(( (END_TIME - START_TIME) / 60 ))m \$(( (END_TIME - START_TIME) % 60 ))s"
echo "Output: ${OUTPUT_DIR}"

# Cleanup
rm -rf "\$MPLCONFIGDIR"
deactivate
EOFJOB
chmod +x "$JOB_SCRIPT"

echo "Job script: $JOB_SCRIPT"

# =====================================================
# Run interactively or submit
# =====================================================
if [ "${1}" = "--submit" ]; then
    JOB_NAME="compare_${RUN_1}_vs_${RUN_2}"

    if [ "$CLUSTER" = "IHEP" ]; then
        echo "Submitting to IHEP batch..."
        hep_sub "$JOB_SCRIPT" \
            -g juno \
            -o "${OUTERR_DIR}/${JOB_NAME}.out" \
            -e "${OUTERR_DIR}/${JOB_NAME}.err" \
            -mem 4000
        echo "Submitted. Check: hep_q -u $USER"
    else
        # CNAF HTCondor
        SUB_FILE="${SCRIPTS_PY}/launchers/${JOB_NAME}.sub"
        JOB_ABS=$(realpath "$JOB_SCRIPT")
        OUTERR_ABS=$(realpath "$OUTERR_DIR")
        cat > "$SUB_FILE" <<EOFSUB
universe = vanilla
executable = ${JOB_ABS}
output = ${OUTERR_ABS}/${JOB_NAME}.out
error  = ${OUTERR_ABS}/${JOB_NAME}.err
log    = ${OUTERR_ABS}/${JOB_NAME}.log
+MaxRuntime = 3600
request_cpus = 1
request_memory = 4000MB
queue
EOFSUB
        echo "Submitting to CNAF HTCondor..."
        condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name "$JOB_NAME" "$SUB_FILE"
        echo "Submitted. Monitor: condor_q -name sn01-htc.cr.cnaf.infn.it"
    fi
else
    echo "Running interactively..."
    echo ""
    bash "$JOB_SCRIPT"
fi
