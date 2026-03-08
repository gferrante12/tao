#!/bin/bash
# =============================================================================
# launch_nu_pipeline.sh
#
# Launch the full TAO non-uniformity analysis pipeline.
#
# Runs all 6 analysis scripts in order via tao_nu_pipeline.py:
#
#   Step 1  (optional)  channel_qt_plots.py   — TDC-ADC per-SiPM diagnostics
#   Step 2              acu_scan_compare.py   — ACU Ge-68 z-scan (15 PNG)
#   Step 3              cls_scan_compare.py   — CLS Cs-137 scan  (30 PNG)
#   Step 4              fit_peaks_ge68.py     — Ge-68 physics-model fits
#   Step 5              fit_peaks_cs137.py    — Cs-137 physics-model fits
#   Step 6              ly_extractor.py       — LY extraction → g(r,θ)
#   Step 7              nu_map.py             — r-z maps, shells, deviation
#
# Each step caches its primary output; re-running the script skips
# completed steps automatically.  Use --force to override.
#
# Works on both CNAF and IHEP clusters.
#
# Usage:
#   ./launch_nu_pipeline.sh [OPTIONS]
#
# Options (all optional — cluster defaults are applied automatically):
#   --spectra-dir    PATH   Directory containing RUN*/ sub-folders
#   --output-root PATH   Root directory for all outputs
#   --sim-npz     PATH   Simulation g_r_theta.npz for data/sim ratio plots
#   --force              Re-run all steps even if outputs exist
#   --verbose            Print verbose fit output
#   --skip-scan          Skip ACU/CLS pipeline comparison (steps 2-3)
#   --skip-fits          Skip Ge-68/Cs-137 peak fits (steps 4-5)
#   --only-maps          Run only LY extraction + map steps (6-7)
#   --qt-plots    PATH   Also run channel_qt_plots.py on this ROOT file
#   --help               Show this message
# =============================================================================

set -e

# ============================================================================
# Help
# ============================================================================
usage() {
    sed -n '/^# Usage/,/^# =====/p' "$0" | grep '^#' | sed 's/^# \?//'
    exit 0
}
for arg in "$@"; do [ "$arg" = "--help" ] && usage; done

# ============================================================================
# Cluster detection
# ============================================================================
detect_cluster() {
    if [ -d "/storage/gpfs_data/juno" ]; then
        echo "CNAF"
    elif command -v eos &>/dev/null && [ -d "/junofs/users/gferrante" ]; then
        echo "IHEP"
    else
        echo "LOCAL"
    fi
}

CLUSTER=$(detect_cluster)

case "$CLUSTER" in
    "CNAF")
        BASE_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/3-non-uniformity"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        SPECTRA_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/2-PE_spectra"
        OUTPUT_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/nu_pipeline_output"
        LOG_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs"
        COORDS_CSV="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/ACU_CLS/InitialP_meanQEdepP_gamma.csv"
        MATPLOTLIB_DIR="/storage/gpfs_data/juno/junofs/users/gferrante/.matplotlib"
        JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1"
        ;;
    "IHEP")
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/"
        SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/3-non-uniformity"
        PYTHON_ENV_ROOT="/junofs/users/gferrante/python_env"
        SPECTRA_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/2-PE_spectra"
        OUTPUT_ROOT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/nu_pipeline_output"
        LOG_ROOT="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/logs"
        COORDS_CSV="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/ACU_CLS/InitialP_meanQEdepP_gamma.csv"
        MATPLOTLIB_DIR="/junofs/users/gferrante/.matplotlib"
        JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1"
        ;;
esac

PIPELINE_SCRIPT="${SCRIPTS_BASE}/tao_nu_pipeline.py"

# ============================================================================
# Parse command-line overrides
# ============================================================================
FORCE_FLAG=""
VERBOSE_FLAG=""
SKIP_SCAN_FLAG=""
SKIP_FITS_FLAG=""
ONLY_MAPS_FLAG=""
SIM_NPZ=""
QT_ROOT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --spectra-dir)    SPECTRA_BASE="$2";    shift 2 ;;
        --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
        --sim-npz)     SIM_NPZ="$2";     shift 2 ;;
        --force)       FORCE_FLAG="--force";      shift ;;
        --verbose)     VERBOSE_FLAG="--verbose";  shift ;;
        --skip-scan)   SKIP_SCAN_FLAG="--skip-scan"; shift ;;
        --skip-fits)   SKIP_FITS_FLAG="--skip-fits"; shift ;;
        --only-maps)   ONLY_MAPS_FLAG="--only-maps"; shift ;;
        --qt-plots)    QT_ROOT_FILE="$2"; shift 2 ;;
        *) echo "WARNING: unknown option '$1' — ignored"; shift ;;
    esac
done

# ============================================================================
# Timestamp & log setup
# ============================================================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${LOG_ROOT}/nu_pipeline"
LOG_FILE="${LOG_DIR}/nu_pipeline_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR" "$OUTPUT_ROOT"
[ -n "$MATPLOTLIB_DIR" ] && { export MPLCONFIGDIR="$MATPLOTLIB_DIR"; mkdir -p "$MATPLOTLIB_DIR"; }

# Tee stdout+stderr to both console and log
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "  TAO NON-UNIFORMITY PIPELINE"
echo "============================================================"
echo "  Cluster      : $CLUSTER"
echo "  spectra-dir     : $SPECTRA_BASE"
echo "  output-root  : $OUTPUT_ROOT"
echo "  scripts-base : $SCRIPTS_BASE"
echo "  coords-csv   : $COORDS_CSV"
echo "  Log          : $LOG_FILE"
[ -n "$SIM_NPZ"       ] && echo "  sim-npz      : $SIM_NPZ"
[ -n "$FORCE_FLAG"    ] && echo "  MODE         : FORCE (all steps re-run)"
[ -n "$SKIP_SCAN_FLAG"] && echo "  SKIP         : ACU/CLS scan comparisons (steps 2-3)"
[ -n "$SKIP_FITS_FLAG"] && echo "  SKIP         : Ge-68/Cs-137 fits (steps 4-5)"
[ -n "$ONLY_MAPS_FLAG"] && echo "  MODE         : only-maps (steps 6-7)"
echo ""

# ============================================================================
# Environment setup
# ============================================================================
if [ -n "$JUNO_RELEASE" ]; then
    if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
        echo "ERROR: JUNO release not found at ${JUNO_RELEASE}"
        exit 1
    fi
    echo "Setting up JUNO-TAO environment (J25.7.1) ..."
    source "${JUNO_RELEASE}/setup-tao.sh"
    ROOT_PYTHONPATH="${PYTHONPATH}"
fi

if [ -n "$PYTHON_ENV_ROOT" ]; then
    echo "Activating Python virtual environment ..."
    source "${PYTHON_ENV_ROOT}/bin/activate"
    [ -n "$JUNO_RELEASE" ] && export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"
fi

# Verify tao_nu_pipeline.py is available
if [ ! -f "$PIPELINE_SCRIPT" ]; then
    # Try next to this script
    PIPELINE_SCRIPT="$(cd "$(dirname "$0")" && pwd)/tao_nu_pipeline.py"
fi
if [ ! -f "$PIPELINE_SCRIPT" ]; then
    echo "ERROR: tao_nu_pipeline.py not found."
    echo "  Searched: ${SCRIPTS_BASE}/tao_nu_pipeline.py"
    echo "  and: $(dirname "$0")/tao_nu_pipeline.py"
    [ -n "$PYTHON_ENV_ROOT" ] && deactivate
    exit 1
fi
echo "Pipeline script : $PIPELINE_SCRIPT"
echo ""

# ============================================================================
# (Optional) Step 1: channel_qt_plots.py
# ============================================================================
if [ -n "$QT_ROOT_FILE" ]; then
    QT_SCRIPT="${SCRIPTS_BASE}/channel_qt_plots.py"
    if [ ! -f "$QT_SCRIPT" ]; then
        QT_SCRIPT="$(dirname "$PIPELINE_SCRIPT")/channel_qt_plots.py"
    fi
    QT_OUTPUT_DIR="${OUTPUT_ROOT}/qt_plots_${TIMESTAMP}"

    echo "============================================================"
    echo "  STEP 1: TDC-ADC diagnostic plots"
    echo "============================================================"
    echo "  Input: $QT_ROOT_FILE"
    echo "  Output: $QT_OUTPUT_DIR"
    echo ""

    if [ -f "$QT_SCRIPT" ]; then
        # Detect file type: pass --rtraw for RTRAW files, --charge-file for CHARGE files
        QT_TYPE_FLAG=""
        case "$QT_ROOT_FILE" in
            *.rtraw) QT_TYPE_FLAG="--rtraw" ;;
            CHARGE_*) QT_TYPE_FLAG="--charge-file" ;;
        esac

        python "$QT_SCRIPT" \
            "$QT_ROOT_FILE"  \
            --output-dir "$QT_OUTPUT_DIR" \
            $QT_TYPE_FLAG \
            --n-channels 40
        QT_EXIT=$?
        if [ $QT_EXIT -eq 0 ]; then
            echo "  ✓  QT plots done → $QT_OUTPUT_DIR"
        else
            echo "  ✗  QT plots failed (exit $QT_EXIT) — continuing"
        fi
    else
        echo "  WARNING: channel_qt_plots.py not found — skipping step 1"
    fi
    echo ""
fi

# ============================================================================
# Steps 2-7: tao_nu_pipeline.py
# ============================================================================
echo "============================================================"
echo "  STEPS 2-7: Main pipeline"
echo "============================================================"
echo ""

START=$(date +%s)

# Build argument list
PIPELINE_ARGS=(
    --spectra-dir   "$SPECTRA_BASE"
    --coords-csv    "$COORDS_CSV"
    --output-root   "$OUTPUT_ROOT"
    --scripts-base  "$SCRIPTS_BASE"
)
[ -n "$SIM_NPZ"        ] && PIPELINE_ARGS+=(--sim-npz      "$SIM_NPZ")
[ -n "$FORCE_FLAG"     ] && PIPELINE_ARGS+=(--force)
[ -n "$VERBOSE_FLAG"   ] && PIPELINE_ARGS+=(--verbose)
[ -n "$SKIP_SCAN_FLAG" ] && PIPELINE_ARGS+=(--skip-scan)
[ -n "$SKIP_FITS_FLAG" ] && PIPELINE_ARGS+=(--skip-fits)
[ -n "$ONLY_MAPS_FLAG" ] && PIPELINE_ARGS+=(--only-maps)

python "$PIPELINE_SCRIPT" "${PIPELINE_ARGS[@]}"

PIPELINE_EXIT=$?
END=$(date +%s)
ELAPSED=$(( END - START ))

if [ -n "$PYTHON_ENV_ROOT" ]; then
    deactivate
fi

echo ""
if [ $PIPELINE_EXIT -eq 0 ]; then
    echo "============================================================"
    echo "  SUCCESS  (${ELAPSED}s)"
    echo "============================================================"
    echo ""
    echo "  Output root : $OUTPUT_ROOT"
    echo ""
    echo "  Output summary:"
    for sub in acu_scan cls_scan extra_plots ge68_fits cs137_fits ly_output nu_maps qt_plots_*; do
        SUBDIR="${OUTPUT_ROOT}/${sub}"
        # glob expansion: only print if actually exists
        [ -d "$SUBDIR" ] || continue
        N_PNG=$(find "$SUBDIR" -name "*.png" 2>/dev/null | wc -l)
        N_JSON=$(find "$SUBDIR" -name "*.json" 2>/dev/null | wc -l)
        N_NPZ=$(find "$SUBDIR" -name "*.npz"  2>/dev/null | wc -l)
        printf "    %-30s  %3d PNG  %2d JSON  %d NPZ\n" \
               "$(basename "$SUBDIR")" "$N_PNG" "$N_JSON" "$N_NPZ"
    done
    echo ""
    echo "  Total PNG files: $(find "$OUTPUT_ROOT" -name '*.png' 2>/dev/null | wc -l)"
    echo "  Log : $LOG_FILE"
else
    echo "============================================================"
    echo "  ERROR: pipeline failed (exit code ${PIPELINE_EXIT})"
    echo "  See log: $LOG_FILE"
    echo "============================================================"
    exit $PIPELINE_EXIT
fi
