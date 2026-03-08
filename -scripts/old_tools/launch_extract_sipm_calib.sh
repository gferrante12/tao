#!/bin/bash

set -e

# =====================================================
# launch_extract_sipm_calib.sh
# Extract SiPM calibration parameters from ROOT file
# =====================================================

echo "=========================================="
echo "EXTRACT SIPM CALIBRATION PARAMETERS"
echo "=========================================="
echo ""

# =====================================================
# Configuration
# =====================================================

# Input ROOT file (CVMFS path)
INPUT_ROOT="/cvmfs/juno.ihep.ac.cn/tao-dbdata/main/tao-dbdata/offline-data/Calibration/Calib.CD.SiPM.Param/TAO_SiPM_calib_par_1768003200.root"

# Output text file
OUTPUT_TXT="sipm_calib_parameters.txt"

# Python script location (adjust if needed)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACT_SCRIPT="${SCRIPT_DIR}/extract_sipm_calib.py"

# JUNO Release (adjust if needed)
JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.6.4"

# Python Environment (adjust if needed, or comment out if not using venv)
PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"

# =====================================================
# Check files exist
# =====================================================

if [ ! -f "$INPUT_ROOT" ]; then
    echo "ERROR: Input ROOT file not found:"
    echo "  $INPUT_ROOT"
    exit 1
fi

if [ ! -f "$EXTRACT_SCRIPT" ]; then
    echo "ERROR: Python script not found:"
    echo "  $EXTRACT_SCRIPT"
    echo ""
    echo "Make sure extract_sipm_calib.py is in the same directory as this script"
    exit 1
fi

if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
    echo "WARNING: JUNO release not found at $JUNO_RELEASE"
    echo "Trying without JUNO environment setup..."
    JUNO_RELEASE=""
fi

echo "Configuration:"
echo "  Input:  $INPUT_ROOT"
echo "  Output: $OUTPUT_TXT"
echo "  Script: $EXTRACT_SCRIPT"
if [ -n "$JUNO_RELEASE" ]; then
    echo "  JUNO:   $JUNO_RELEASE"
fi
echo ""

# =====================================================
# Setup environment
# =====================================================

# Setup JUNO-TAO environment (for ROOT)
if [ -n "$JUNO_RELEASE" ]; then
    echo "Setting up JUNO-TAO environment..."
    source "${JUNO_RELEASE}/setup-tao.sh"
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to source JUNO-TAO environment!"
        exit 1
    fi
    ROOT_PYTHONPATH="${PYTHONPATH}"
fi

# Activate Python virtual environment (optional)
if [ -d "$PYTHON_ENV_ROOT" ]; then
    echo "Activating Python virtual environment..."
    source "${PYTHON_ENV_ROOT}/bin/activate"
    if [ $? -ne 0 ]; then
        echo "WARNING: Failed to activate Python virtual environment"
        echo "Continuing without virtual environment..."
    else
        if [ -n "$ROOT_PYTHONPATH" ]; then
            export PYTHONPATH="${ROOT_PYTHONPATH}:${PYTHONPATH}"
        fi
    fi
fi

echo ""

# =====================================================
# Run extraction
# =====================================================

echo "Running extraction..."
echo ""

python "$EXTRACT_SCRIPT" "$INPUT_ROOT" "$OUTPUT_TXT"

EXIT_CODE=$?

# =====================================================
# Cleanup
# =====================================================

if command -v deactivate &> /dev/null; then
    deactivate 2>/dev/null || true
fi

# =====================================================
# Final status
# =====================================================

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "=========================================="
    echo "✓ EXTRACTION COMPLETE"
    echo "=========================================="
    echo ""
    echo "Output file: $OUTPUT_TXT"
    echo ""
    echo "To view the file:"
    echo "  head -n 20 $OUTPUT_TXT"
    echo "  less $OUTPUT_TXT"
    echo ""
else
    echo "=========================================="
    echo "✗ EXTRACTION FAILED"
    echo "=========================================="
    exit $EXIT_CODE
fi
