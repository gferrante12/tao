#!/usr/bin/env bash
# ============================================================
# One-time submit script — Gain calibration RUN 1295
# Hardcoded input: /junofs/users/gferrante/TAO/data_analysis/energy_spectrum/charge_merged/CHARGE_RUN1295_merged.root
# ============================================================
set -euo pipefail

RUN=1295
INPUT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/charge_merged/CHARGE_RUN1295_merged.root"
OUT_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/gain_calibration/RUN1295"
LOG_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs/RUN1295/1-gain_calibration"

# Scripts are expected in the same directory as this submit script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#SCRIPT_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/1-gain_calibration"
GAIN_CALIB="${SCRIPT_DIR}/gain_calibration.py"
FUNC_LIB="${SCRIPT_DIR}/gain_fit_functions.py"

# ── Sanity checks ────────────────────────────────────────────
if [[ ! -f "${INPUT}" ]]; then
    echo "ERROR: Input file not found: ${INPUT}"
    exit 1
fi
if [[ ! -f "${GAIN_CALIB}" ]]; then
    echo "ERROR: gain_calibration.py not found at ${GAIN_CALIB}"
    exit 1
fi
if [[ ! -f "${FUNC_LIB}" ]]; then
    echo "ERROR: gain_fit_functions.py not found at ${FUNC_LIB}"
    exit 1
fi

mkdir -p "${OUT_DIR}" "${LOG_DIR}"

# ── Job parameters ───────────────────────────────────────────
# Histogram prefix: H_adcClean_ (clean tier from extract_charge_calib)
HIST_PREFIX="H_adcClean_"
MODELS="MULTI_GAUSS,GAUSS_CT,EMG,GEN_POISSON"
N_PEAKS=6        # fit up to 6 PE peaks (max 8 supported)
SAMPLE=50        # plots per category per model
N_PEAKS_MODEL=6

# ── Submit via qsub (HTCondor-style on IHEP) ─────────────────
# Adjust scheduler options for your cluster (CNAF/IHEP differ).
# This script uses IHEP HTCondor-like qsub syntax.

JOB_NAME="gain_calib_RUN${RUN}"
LOG_OUT="${LOG_DIR}/${JOB_NAME}.out"
LOG_ERR="${LOG_DIR}/${JOB_NAME}.err"

echo "Submitting gain calibration for RUN ${RUN}"
echo "  Input   : ${INPUT}"
echo "  Output  : ${OUT_DIR}"
echo "  Models  : ${MODELS}"
echo "  Peaks   : ${N_PEAKS}"
echo "  Sample  : ${SAMPLE} per category"
echo "  Log out : ${LOG_OUT}"
echo "  Log err : ${LOG_ERR}"
echo ""

# ── Build python command ──────────────────────────────────────
PY_CMD="python3 ${GAIN_CALIB} \
    --input       ${INPUT} \
    --hist_prefix ${HIST_PREFIX} \
    --model       ${MODELS} \
    --n_peaks     ${N_PEAKS} \
    --sample      ${SAMPLE} \
    --output_dir  ${OUT_DIR}"

# ── Detect scheduler and submit ───────────────────────────────
if command -v condor_submit &>/dev/null; then
    # HTCondor (IHEP)
    SUBMIT_FILE="${LOG_DIR}/condor_${JOB_NAME}.sub"
    cat > "${SUBMIT_FILE}" <<CONDOREOF
Universe   = vanilla
Executable = /usr/bin/bash
Arguments  = -c "${PY_CMD}"
Output     = ${LOG_OUT}
Error      = ${LOG_ERR}
Log        = ${LOG_DIR}/${JOB_NAME}.condor.log
request_memory = 8192
request_cpus   = 1
+JobFlavour    = "workday"
Queue 1
CONDOREOF
    condor_submit "${SUBMIT_FILE}"
    echo "Submitted via HTCondor. Job file: ${SUBMIT_FILE}"

elif command -v bsub &>/dev/null; then
    # LSF (CNAF)
    bsub -J "${JOB_NAME}" \
         -q medium \
         -o "${LOG_OUT}" \
         -e "${LOG_ERR}" \
         -M 8192 \
         bash -c "${PY_CMD}"
    echo "Submitted via LSF."

elif command -v sbatch &>/dev/null; then
    # SLURM fallback
    sbatch --job-name="${JOB_NAME}" \
           --output="${LOG_OUT}" \
           --error="${LOG_ERR}" \
           --mem=8G \
           --time=04:00:00 \
           --wrap="${PY_CMD}"
    echo "Submitted via SLURM."

else
    echo "No batch scheduler found — running interactively."
    eval "${PY_CMD}" 2>&1 | tee "${LOG_OUT}"
fi
