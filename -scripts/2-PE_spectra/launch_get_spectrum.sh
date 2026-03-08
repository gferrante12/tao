#!/bin/bash
set -e

# =====================================================
# launch_get_spectrum.sh - v3.0
# Supports both RTRAW and ESD file processing
# Works on CNAF and IHEP clusters
# =====================================================

if [ -z "$1" ]; then
echo "ERROR: RUN number not provided!"
echo ""
echo "Usage: $0 RUN [FILE_TYPE] [SOURCE] [OPTIONS]"
echo ""
echo "Arguments:"
echo "  RUN         - Run number (required)"
echo "  FILE_TYPE   - 'rtraw' or 'esd' (default: rtraw)"
echo "  SOURCE      - Calibration source for peak fit (optional)."
echo "                If omitted, histograms are saved but no fit is performed."
echo "                Known sources (arXiv:2204.03256, Table 1):"
echo "                  Ge68        Ge-68  e+ annihilation  1.022 MeV"
echo "                  Cs137       Cs-137 γ                0.662 MeV"
echo "                  Mn54        Mn-54  γ                0.835 MeV"
echo "                  Co60        Co-60  γ sum            2.506 MeV (1.173+1.333)"
echo "                  Co60_low    Co-60  γ low line       1.173 MeV"
echo "                  Co60_high   Co-60  γ high line      1.333 MeV"
echo "                  K40         K-40   γ                1.461 MeV"
echo "                  AmC_nH      n+H capture γ           2.223 MeV"
echo "                  AmC_O16     16O* de-excitation γ    6.130 MeV"
echo ""
echo "RTRAW-specific options:"
echo "  CALIB_RUN   - Calibration run number (required for RTRAW)"
echo "                • Omit or 'default' → run-range-aware default"
echo "                • Number (1210) → run-specific calibration"
echo "                • Path → custom calibration file"
echo "  pecut CUTVALUE - Enable PE/channel cut (threshold method)"
echo ""
echo "ESD-specific options (no calibration file needed):"
echo "  noradial    - Disable radial cut (default: 150mm, origin-based)"
echo "  pesum_basic - Use peSum() instead of PESum_g() (default: PESum_g)"
echo "  offaxis     - Off-axis radial cut around the Cs-137 CLS source position:"
echo "                  (-23.1093, -188.278, 37.3801) mm"
echo "                Intended for RUN 1112 and RUN 1344 (Cs-137 on CLS arm)."
echo ""
echo "Examples:"
echo "  # Ge-68 source (RTRAW, default calib):"
echo "  $0 1157 rtraw Ge68"
echo ""
echo "  # Cs-137 CLS source (RTRAW):"
echo "  $0 1344 rtraw Cs137"
echo ""
echo "  # No source — histograms only, no fit:"
echo "  $0 1345 rtraw"
echo ""
echo "  # Other RTRAW examples:"
echo "  $0 1210 rtraw Ge68 1210          # RTRAW, RUN1210 calib, Ge68 fit"
echo "  $0 1210 rtraw Ge68 default pecut 20  # with PE/channel cut"
echo ""
echo "  # ESD examples:"
echo "  $0 1210 esd Ge68                 # ESD, PESum_g, origin radial cut"
echo "  $0 1344 esd Cs137 offaxis        # ESD, Cs-137 off-axis radial cut"
echo "  $0 1345 esd                      # ESD, no source, no fit"
echo ""
exit 1
fi

RUN=$1
FILE_TYPE=${2:-rtraw}

# =====================================================
# SOURCE argument (3rd positional, optional)
# Maps to --source-name passed to get_spectrum.py and merge_spectrum.py
# =====================================================
VALID_SOURCES="Ge68 Cs137 Mn54 Co60 Co60_low Co60_high K40 AmC_nH AmC_O16"

# Peek at arg $3: if it matches a known source, consume it; otherwise leave it
# for FILE_TYPE-specific parsing (e.g. CALIB_RUN for rtraw).
SOURCE_NAME=""
_arg3="${3:-}"
for _s in $VALID_SOURCES; do
  if [ "${_arg3,,}" = "${_s,,}" ]; then
    SOURCE_NAME="$_s"
    break
  fi
done

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
        SCRIPTS_BASE="/storage/gpfs_data/juno/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/2-PE_spectra"
        PYTHON_ENV_ROOT="/storage/gpfs_data/juno/junofs/users/gferrante/python_env"
        RTRAW_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-rtraw"
        ESD_BASE="/storage/gpfs_data/juno/junofs/production/storm/dirac/juno/tao-kup"
        USE_EOS_CLI=false
        ;;
    "IHEP")
        BASE_DIR="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum"
        SCRIPTS_BASE="/junofs/users/gferrante/TAO/data_analysis/energy_spectrum/-scripts/2-PE_spectra"
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

# =====================================================
# Validate file type
# =====================================================
if [ "$FILE_TYPE" != "rtraw" ] && [ "$FILE_TYPE" != "esd" ]; then
  echo "ERROR: FILE_TYPE must be 'rtraw' or 'esd'"
  echo "Got: $FILE_TYPE"
  exit 1
fi

# =====================================================
# Parse arguments based on file type  
# =====================================================
CALIB_RUN_ARG=""
PECUT_ENABLED=false
PECUT_VALUE=-1
RADIAL_CUT_DISABLED=false
RADIAL_CUT_VALUE=150
USE_PESUM_BASIC=false
USE_OFFAXIS=false

# Cs-137 CLS source position (mm) — used when offaxis is requested
CLS_SRC_X=-23.1093
CLS_SRC_Y=-188.278
CLS_SRC_Z=37.3801

if [ "$FILE_TYPE" = "rtraw" ]; then
  # If SOURCE_NAME consumed $3, CALIB_RUN starts at $4; otherwise at $3.
  if [ -n "$SOURCE_NAME" ]; then
    CALIB_RUN_ARG=${4:-}
    _OPT_START=5
  else
    CALIB_RUN_ARG=${3:-}
    _OPT_START=4
  fi

  for ((i=_OPT_START; i<=$#; i++)); do
    arg="${!i}"
    if [ "$arg" = "pecut" ]; then
      PECUT_ENABLED=true
    elif [ "$PECUT_ENABLED" = true ] && [ "$PECUT_VALUE" = -1 ]; then
      PECUT_VALUE=$arg
      PECUT_ENABLED=true
    fi
  done

else  # ESD
  # If SOURCE_NAME consumed $3, ESD options start at $4; otherwise at $3.
  if [ -n "$SOURCE_NAME" ]; then
    _OPT_START=4
  else
    _OPT_START=3
  fi

  for ((i=_OPT_START; i<=$#; i++)); do
    arg="${!i}"
    if [ "$arg" = "noradial" ]; then
      RADIAL_CUT_DISABLED=true
    elif [ "$arg" = "pesum_basic" ]; then
      USE_PESUM_BASIC=true
    elif [ "$arg" = "offaxis" ]; then
      USE_OFFAXIS=true
    elif [ "$arg" = "pecut" ]; then
      echo "WARNING: 'pecut' not applicable to ESD (ignored)"
    fi
  done
fi

# Strip any option keyword that accidentally landed in CALIB_RUN_ARG
for _kw in pecut noradial pesum_basic offaxis $VALID_SOURCES; do
  if [ "${CALIB_RUN_ARG,,}" = "${_kw,,}" ]; then
    CALIB_RUN_ARG=""
    break
  fi
done

# =====================================================
# Setup calibration for RTRAW
# =====================================================

# Select the run-range-appropriate default gain calibration file.
# Runs below 1157 are not in the officially calibrated range but can use
# sipm_calib_1157-1193.txt as the closest available default — a warning is
# printed so the user can verify this is appropriate.
CALIB_BASE="${BASE_DIR}/1-gain_calibration_results"
if [ "$RUN" -ge 1295 ] 2>/dev/null; then
    DEFAULT_CALIB="${CALIB_BASE}/sipm_calib_1295-.txt"
elif [ "$RUN" -le 1193 ] 2>/dev/null; then
    DEFAULT_CALIB="${CALIB_BASE}/sipm_calib_1157-1193.txt"
    if [ "$RUN" -lt 1157 ] 2>/dev/null; then
        echo "WARNING: RUN $RUN is below the officially calibrated range (1157-1193)."
        echo "         Using sipm_calib_1157-1193.txt as the closest available default"
        echo "         gain calibration — verify this is appropriate for your run."
        echo ""
    fi
else
    # Gap 1194-1294: no dedicated file; use 1295+ as best guess
    DEFAULT_CALIB="${CALIB_BASE}/sipm_calib_1295-.txt"
    echo "WARNING: RUN $RUN is in the gap range 1194-1294 with no dedicated calibration."
    echo "         Using sipm_calib_1295-.txt as best guess — verify before use."
    echo ""
fi
CALIB_LABEL="default"

if [ "$FILE_TYPE" = "rtraw" ]; then
  if [ -z "$CALIB_RUN_ARG" ] || [ "$CALIB_RUN_ARG" = "default" ]; then
    GOOD_CALIB="$DEFAULT_CALIB"
    CALIB_LABEL="default"
    
  elif [[ "$CALIB_RUN_ARG" =~ ^[0-9]+$ ]]; then
    CALIB_DIR="${BASE_DIR}/1-gain_calibration_results/$CALIB_RUN_ARG"
    LATEST_CALIB=$(ls -dt "$CALIB_DIR"/*/ 2>/dev/null | head -1)
    LATEST_CALIB="${LATEST_CALIB%/}"
    
    if [ -n "$LATEST_CALIB" ]; then
      RUN_SPECIFIC_CALIB="${LATEST_CALIB}/root_tspectrum_good_RUN${CALIB_RUN_ARG}.txt"
      if [ -f "$RUN_SPECIFIC_CALIB" ]; then
        GOOD_CALIB="$RUN_SPECIFIC_CALIB"
        CALIB_LABEL="run${CALIB_RUN_ARG}"
      else
        echo "ERROR: Run-specific calibration file not found in $LATEST_CALIB!"
        exit 1
      fi
    else
      echo "ERROR: No calibration results found for RUN${CALIB_RUN_ARG}"
      exit 1
    fi
    
  else
    GOOD_CALIB="$CALIB_RUN_ARG"
    CALIB_LABEL="custom"
  fi
  
  if [ ! -f "$GOOD_CALIB" ]; then
    echo "ERROR: Calibration file not found: $GOOD_CALIB"
    exit 1
  fi
  
else
  GOOD_CALIB="$DEFAULT_CALIB"
  CALIB_LABEL="notused"
fi

# =====================================================
# EOS Helper Functions (for IHEP)
# =====================================================

eos_find_run() {
    local base=$1
    local run=$2
    
    if [ "$USE_EOS_CLI" = true ]; then
        local run_num=$run
        local run_prefix=$(printf "%08d" $((run_num / 100 * 100)))
        local group_prefix=$(printf "%08d" $((run_num / 1000 * 1000)))
        
        local tao_versions=$(eos ls "$base" 2>/dev/null | grep -E '^T[0-9]+\.[0-9]+\.[0-9]+$' | sort -V -r)
        
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
# Find input files (RTRAW or ESD)
# NOTE: Use a separate DATA_SEARCH_BASE variable so BASE_DIR (the results/
#       scripts working directory) is never overwritten.  Previously this
#       block re-assigned BASE_DIR, which corrupted SPECTRUM_DIR, LOGS_DIR,
#       GET_SPECTRUM_SCRIPT and every other path derived from BASE_DIR later
#       in the script.  Now BASE_DIR always points to the analysis work tree,
#       consistent with launch_extract_charge_calib.sh.
# =====================================================
if [ "$FILE_TYPE" = "esd" ]; then
    DATA_SEARCH_BASE="$ESD_BASE"
    FILE_EXT="esd"
else
    DATA_SEARCH_BASE="$RTRAW_BASE"
    FILE_EXT="rtraw"
fi

echo "Searching for RUN $RUN in $DATA_SEARCH_BASE..."

INPUT_BASE=$(eos_find_run "$DATA_SEARCH_BASE" "$RUN")

if [ -z "$INPUT_BASE" ]; then
    echo "ERROR: RUN $RUN not found in $DATA_SEARCH_BASE"
    exit 1
fi

echo "Found: $INPUT_BASE"

# Extract TAO version
TAO_VERSION=$(echo "$INPUT_BASE" | sed -n 's|.*/\(T[0-9]\+\.[0-9]\+\.[0-9]\+\)/.*|\1|p')

if [ -z "$TAO_VERSION" ]; then
    echo "ERROR: Could not parse TAO version from path"
    exit 1
fi

# Map TAO version to JUNO version
JUNO_VERSION=$(echo "$TAO_VERSION" | sed 's/^T/J/')
JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION}"

# Verify JUNO release exists
if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
    echo "WARNING: JUNO release not found at $JUNO_RELEASE"
    JUNO_VERSION_FALLBACK=$(echo "$TAO_VERSION" | sed 's/^T/J/' | sed 's/\.[0-9]$/\.1/')
    JUNO_RELEASE="/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/${JUNO_VERSION_FALLBACK}"
    if [ ! -f "${JUNO_RELEASE}/setup-tao.sh" ]; then
        echo "ERROR: Cannot find JUNO release for version $TAO_VERSION"
        exit 1
    fi
    echo "Using fallback: $JUNO_RELEASE"
fi

# Count input files
if [ "$USE_EOS_CLI" = true ]; then
    INPUT_FILES=($(eos ls "$INPUT_BASE" 2>/dev/null | grep "\.$FILE_EXT$" | sort | while read f; do echo "$INPUT_BASE/$f"; done))
else
    INPUT_FILES=($(ls "$INPUT_BASE"/*.$FILE_EXT 2>/dev/null | sort))
fi

if [ ${#INPUT_FILES[@]} -eq 0 ]; then
    echo "ERROR: No .$FILE_EXT files found in $INPUT_BASE"
    exit 1
fi
TOTAL_FILES=${#INPUT_FILES[@]}

# =====================================================
# Generate folder name
# =====================================================
if [ "$FILE_TYPE" = "rtraw" ]; then
  FOLDER_NAME="${RUN}_${FILE_TYPE}_${CALIB_LABEL}"
  if [ "$PECUT_ENABLED" = true ]; then
    FOLDER_NAME="${FOLDER_NAME}_pecut${PECUT_VALUE}"
  fi
else  # ESD
  FOLDER_NAME="${RUN}_${FILE_TYPE}"

  if [ "$RADIAL_CUT_DISABLED" = true ]; then
    FOLDER_NAME="${FOLDER_NAME}_noradialcut"
  elif [ "$USE_OFFAXIS" = true ]; then
    FOLDER_NAME="${FOLDER_NAME}_offsrc_rcut${RADIAL_CUT_VALUE}"
  else
    FOLDER_NAME="${FOLDER_NAME}_rcut${RADIAL_CUT_VALUE}"
  fi

  if [ "$USE_PESUM_BASIC" = true ]; then
    FOLDER_NAME="${FOLDER_NAME}_pesumbasic"
  else
    FOLDER_NAME="${FOLDER_NAME}_pesumg"
  fi
fi

# Append source name to folder so different calibration sources are segregated
if [ -n "$SOURCE_NAME" ]; then
  FOLDER_NAME="${FOLDER_NAME}_${SOURCE_NAME}"
else
  FOLDER_NAME="${FOLDER_NAME}_nosource"
fi

# =====================================================
# Display configuration
# =====================================================
echo ""
echo "=============================================================="
echo "  ENERGY SPECTRUM EXTRACTION - v3.0"
echo "=============================================================="
echo "  Cluster:      $CLUSTER"
echo "  RUN:          $RUN"
echo "  File type:    $FILE_TYPE"
echo "  TAO version:  $TAO_VERSION"
echo "  JUNO release: $JUNO_VERSION"
echo "  Input path:   $INPUT_BASE"
echo "  Total files:  $TOTAL_FILES"
if [ "$USE_EOS_CLI" = true ]; then
    echo "  EOS Mode:     CLI (XRootD URLs)"
fi
echo ""

if [ "$FILE_TYPE" = "rtraw" ]; then
  echo "  Calibration:  $(basename $GOOD_CALIB) [$CALIB_LABEL]"
  if [ "$PECUT_ENABLED" = true ]; then
    echo "  PE Cut:       ENABLED ($PECUT_VALUE PE/channel)"
  else
    echo "  PE Cut:       DISABLED (rounding method)"
  fi
else  # ESD
  echo "  Calibration:  Not needed (already applied)"
  
  if [ "$RADIAL_CUT_DISABLED" = true ]; then
    echo "  Radial Cut:   DISABLED"
  elif [ "$USE_OFFAXIS" = true ]; then
    echo "  Radial Cut:   ENABLED ($RADIAL_CUT_VALUE mm) [OFF-AXIS — CLS Cs-137 source]"
    echo "  Source pos:   X=$CLS_SRC_X  Y=$CLS_SRC_Y  Z=$CLS_SRC_Z mm"
  else
    echo "  Radial Cut:   ENABLED ($RADIAL_CUT_VALUE mm) [origin-based]"
  fi
  
  if [ "$USE_PESUM_BASIC" = true ]; then
    echo "  PE Type:      peSum() [basic]"
  else
    echo "  PE Type:      PESum_g() [geometry corrected]"
  fi
fi

# Print run-range-specific cvmfs file selection
if [ "$RUN" -ge 1295 ] 2>/dev/null; then
    echo "  Run range:    1295+"
    echo "  SiPM calib:   TAO_SiPM_calib_par_1770336000.root"
    echo "  Bad ch (st):  badch_T25.7.1_fixed.txt"
    echo "  Bad ch (dyn): badch_T25.7.1_dyn.txt"
elif [ "$RUN" -le 1193 ] 2>/dev/null; then
    if [ "$RUN" -lt 1157 ] 2>/dev/null; then
        echo "  Run range:    <1157 (using 1157-1193 config — WARNING: below official range)"
    else
        echo "  Run range:    1157-1193"
    fi
    echo "  SiPM calib:   TAO_SiPM_calib_par_1768003200.root"
    echo "  Bad ch (st):  ALLBad_channels_20260112_1053_st.txt"
    echo "  Bad ch (dyn): ALLBad_channels_20260112_1039_dy.txt"
    echo "  Rec params:   curve_params_StaticBaseline_T25.6.4_260114.csv"
    echo "  Non-unif map: Energy_nonUniformityMap_StaticBaseline_T25.6.4_260114.txt"
else
    echo "  Run range:    GAP 1194-1294 (no dedicated config — using 1295+ as best guess)"
    echo "  SiPM calib:   TAO_SiPM_calib_par_1770336000.root"
    echo "  Bad ch (st):  badch_T25.7.1_fixed.txt"
    echo "  Bad ch (dyn): badch_T25.7.1_dyn.txt"
fi

if [ -n "$SOURCE_NAME" ]; then
  echo "  Source:       $SOURCE_NAME"
else
  echo "  Source:       none (no peak fit will be performed)"
fi
echo "  Folder:       $FOLDER_NAME"
echo "=============================================================="
echo ""

# =====================================================
# Directory setup
# =====================================================
SCRIPTS_DIR="./get_spectrum/${FOLDER_NAME}"
OUTERR_DIR="${SCRIPTS_DIR}/out-err"
SPECTRUM_DIR="${BASE_DIR}/2-PE_spectra_results/RUN${RUN}/${FOLDER_NAME}_$(date +%Y-%m-%d_%H-%M-%S)"
LOGS_DIR="${BASE_DIR}/logs/RUN${RUN}/2-PE_spectra_results/${FOLDER_NAME}"

# Scripts
GET_SPECTRUM_SCRIPT="${SCRIPTS_BASE}/get_spectrum.py"
MERGE_SCRIPT="${SCRIPTS_BASE}/merge_spectrum.py"

# HTCondor/HEP Settings
MAX_RUNTIME=7200
MAX_RUNTIME_MERGE=3600

mkdir -p "$SCRIPTS_DIR" "$OUTERR_DIR" "$SPECTRUM_DIR" "$LOGS_DIR"

# =====================================================
# Generate individual job scripts
# =====================================================
echo "Generating individual job scripts..."
for i in ${!INPUT_FILES[@]}; do
    INPUT_FILE=${INPUT_FILES[$i]}
    JOB_ID=$(printf "%03d" $((i+1)))

    # Convert to XRootD URL if using EOS
    INPUT_FILE_URL=$(to_xrootd_url "$INPUT_FILE")

    MAIN="${SCRIPTS_DIR}/get_spectrum_${RUN}_${JOB_ID}.sh"

    # Generate main script
    cat > "$MAIN" <<EOFMAIN
#!/bin/bash
set -e

# Parameters
RUN=${RUN}
INPUT_FILE="${INPUT_FILE_URL}"
SPECTRUM_DIR=${SPECTRUM_DIR}
GET_SPECTRUM_SCRIPT=${GET_SPECTRUM_SCRIPT}
GOOD_CALIB=${GOOD_CALIB}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
JOB_ID=${JOB_ID}
LOGS_DIR=${LOGS_DIR}
TAO_VERSION=${TAO_VERSION}
FILE_TYPE=${FILE_TYPE}
SOURCE_NAME="${SOURCE_NAME}"
PECUT_VALUE=${PECUT_VALUE}
RADIAL_CUT_DISABLED=${RADIAL_CUT_DISABLED}
RADIAL_CUT_VALUE=${RADIAL_CUT_VALUE}
USE_PESUM_BASIC=${USE_PESUM_BASIC}
USE_OFFAXIS=${USE_OFFAXIS}
CLS_SRC_X=${CLS_SRC_X}
CLS_SRC_Y=${CLS_SRC_Y}
CLS_SRC_Z=${CLS_SRC_Z}

LOG_FILE="\${LOGS_DIR}/get_spectrum_\${RUN}_\${JOB_ID}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "Get Spectrum - Single File Processing"
echo "=========================================="
echo "RUN: \$RUN"
echo "TAO Version: \$TAO_VERSION"
echo "File Type: \$FILE_TYPE"
echo "Job ID: \$JOB_ID"
echo "Input: \$INPUT_FILE"
if [ "\$FILE_TYPE" = "rtraw" ]; then
    echo "Calibration: \$(basename \$GOOD_CALIB)"
    if [ \$PECUT_VALUE -gt 0 ] 2>/dev/null; then
        echo "PE Cut: \$PECUT_VALUE PE/ch"
    fi
else
    if [ "\$RADIAL_CUT_DISABLED" = true ]; then
        echo "Radial Cut: DISABLED"
    elif [ "\$USE_OFFAXIS" = true ]; then
        echo "Radial Cut: \${RADIAL_CUT_VALUE} mm [OFF-AXIS: (\$CLS_SRC_X, \$CLS_SRC_Y, \$CLS_SRC_Z) mm]"
    else
        echo "Radial Cut: \${RADIAL_CUT_VALUE} mm [origin-based]"
    fi
    if [ "\$USE_PESUM_BASIC" = true ]; then
        echo "PE Type: peSum()"
    else
        echo "PE Type: PESum_g()"
    fi
fi
echo ""

# Extract file number
FILE_NUM=\$(echo "\$(basename "\$INPUT_FILE")" | grep -oE '[0-9]{3,}' | tail -1)
if [ -z "\$FILE_NUM" ]; then
    FILE_NUM=${JOB_ID}
fi

OUTPUT_FILE="\${SPECTRUM_DIR}/spectrum_RUN\${RUN}-\${FILE_NUM}.root"

# Check if output exists
if [ -f "\$OUTPUT_FILE" ]; then
    echo "Output exists, skipping"
    exit 0
fi

# Setup JUNO-TAO Environment
echo "Setting up JUNO-TAO environment..."
source "\${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"

# Activate Python Environment
echo "Activating Python environment..."
source "\${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# Build command
CMD="python \"\$GET_SPECTRUM_SCRIPT\" \"\$INPUT_FILE\" \"\$GOOD_CALIB\" \"\$OUTPUT_FILE\""
CMD="\$CMD --run \$RUN"
if [ -n "\$SOURCE_NAME" ]; then
  CMD="\$CMD --source-name \$SOURCE_NAME"
fi

if [ "\$FILE_TYPE" = "rtraw" ]; then
    if [ \$PECUT_VALUE -gt 0 ] 2>/dev/null; then
        CMD="\$CMD --max-pe-per-channel \$PECUT_VALUE"
    fi
else  # ESD
    CMD="\$CMD --esd"
    
    if [ "\$RADIAL_CUT_DISABLED" = true ]; then
        CMD="\$CMD --no-radial-cut"
    else
        CMD="\$CMD --radial-cut \$RADIAL_CUT_VALUE"
        if [ "\$USE_OFFAXIS" = true ]; then
            CMD="\$CMD --source-pos \$CLS_SRC_X \$CLS_SRC_Y \$CLS_SRC_Z"
        fi
    fi
    
    if [ "\$USE_PESUM_BASIC" = true ]; then
        CMD="\$CMD --esd-pe-type pesum_basic"
    else
        CMD="\$CMD --esd-pe-type pesum_g"
    fi
fi

# Run get_spectrum.py
echo ""
echo "Running get_spectrum.py..."
eval \$CMD

if [ \$? -ne 0 ]; then
    echo "ERROR: Spectrum extraction failed!"
    deactivate
    exit 1
fi

if [ ! -f "\$OUTPUT_FILE" ]; then
    echo "ERROR: Output not created!"
    deactivate
    exit 1
fi

echo ""
echo "Extraction complete!"
echo "Output: \$(basename \$OUTPUT_FILE)"
deactivate
EOFMAIN

    chmod +x "$MAIN"

    # Generate submit files based on cluster
    if [ "$CLUSTER" = "CNAF" ]; then
        SUBMIT="${SCRIPTS_DIR}/get_spectrum_${RUN}_${JOB_ID}.sub"
        MAIN_ABS=$(realpath "$MAIN")
        OUTERR_ABS=$(realpath "$OUTERR_DIR")
        
        cat > "$SUBMIT" <<EOFSUBMIT
universe = vanilla
executable = $MAIN_ABS
output = $OUTERR_ABS/get_spectrum_${RUN}_${JOB_ID}.out
error = $OUTERR_ABS/get_spectrum_${RUN}_${JOB_ID}.err
log = $OUTERR_ABS/get_spectrum_${RUN}_${JOB_ID}.log
+MaxRuntime = $MAX_RUNTIME
request_cpus = 1
request_memory = 2GB
queue
EOFSUBMIT
    fi
done

echo "Generated $TOTAL_FILES job scripts"

# =====================================================
# Generate joblist.sh based on cluster
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/joblist.sh" <<'EOFJOBLIST'
#!/bin/bash
# Job submission for IHEP using hep_sub

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
OUTERR_DIR="${SCRIPT_DIR}/out-err"
MAX_CONCURRENT=100
CHECK_INTERVAL=30

echo "Starting job submission..."
echo "Max concurrent jobs: $MAX_CONCURRENT"
echo ""

JOB_SCRIPTS=($(ls ${SCRIPT_DIR}/get_spectrum_*.sh 2>/dev/null | sort))
TOTAL=${#JOB_SCRIPTS[@]}

if [ $TOTAL -eq 0 ]; then
    echo "ERROR: No job scripts found!"
    exit 1
fi

echo "Found $TOTAL job scripts"
echo "Submitting to IHEP HTCondor using hep_sub..."
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
echo "Submission Summary"
echo "=========================================="
echo "Total: $TOTAL"
echo "Submitted: $SUBMITTED"
echo "Failed: $FAILED"
echo ""
echo "Check queue: hep_q -u $USER"
EOFJOBLIST

else
    cat > "$SCRIPTS_DIR/joblist.sh" <<EOFJOBLIST
#!/bin/bash
# Job submission for CNAF using HTCondor
EOFJOBLIST

    for i in ${!INPUT_FILES[@]}; do
        JOB_ID=$(printf "%03d" $((i+1)))
        echo "condor_submit -maxjobs 51 -spool -name sn01-htc.cr.cnaf.infn.it -batch-name get_spectrum_${RUN}_${JOB_ID} get_spectrum_${RUN}_${JOB_ID}.sub" >> "$SCRIPTS_DIR/joblist.sh"
    done
fi

chmod +x "$SCRIPTS_DIR/joblist.sh"

# =====================================================
# Generate submit_all.sh
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo "=========================================="
echo "Submitting ${TOTAL_FILES} jobs for RUN ${RUN}"
echo "=========================================="
echo "Cluster: IHEP"
echo "Folder: ${FOLDER_NAME}"
echo ""

cd \$(dirname \$0)

if [ -f .submission.lock ]; then
    PID=\$(cat .submission.lock)
    if ps -p \$PID > /dev/null 2>&1; then
        echo "ERROR: Submission already running (PID: \$PID)"
        exit 1
    fi
fi

nohup bash joblist.sh > joblist.out 2>&1 &
SUBMIT_PID=\$!
echo \$SUBMIT_PID > .submission.lock

echo "Job submission started in background (PID: \$SUBMIT_PID)"
echo ""
echo "Monitor: tail -f \$(pwd)/joblist.out"
echo "Check queue: hep_q -u \$USER"
echo ""
EOFSUBMIT

else
    cat > "$SCRIPTS_DIR/submit_all.sh" <<EOFSUBMIT
#!/bin/bash

echo "=========================================="
echo "Submitting ${TOTAL_FILES} jobs for RUN ${RUN}"
echo "=========================================="
echo "Cluster: CNAF"
echo "Folder: ${FOLDER_NAME}"
echo ""

cd \$(dirname \$0)
nohup junosub joblist.sh > joblist.out 2>&1 &
SUBMIT_PID=\$!

echo "Job submission started in background (PID: \$SUBMIT_PID)"
echo ""
echo "Monitor: tail -f \$(pwd)/joblist.out"
echo "Check queue: condor_q -name sn01-htc.cr.cnaf.infn.it -batch get_spectrum_${RUN}"
echo ""
EOFSUBMIT
fi

chmod +x "$SCRIPTS_DIR/submit_all.sh"

# =====================================================
# Generate merge job (similar structure, cluster-aware)
# =====================================================
echo ""
echo "Generating merge job..."
MAIN_MERGE="${SCRIPTS_DIR}/merge_spectrum_${RUN}.sh"

cat > "$MAIN_MERGE" <<EOFMERGE
#!/bin/bash
set -e

RUN=${RUN}
SOURCE_NAME="${SOURCE_NAME}"
SPECTRUM_DIR=${SPECTRUM_DIR}
MERGE_SCRIPT=${MERGE_SCRIPT}
PYTHON_ENV_ROOT=${PYTHON_ENV_ROOT}
JUNO_RELEASE=${JUNO_RELEASE}
LOGS_DIR=${LOGS_DIR}

LOG_FILE="\${LOGS_DIR}/merge_spectrum_\${RUN}_\$(date +%Y%m%d_%H%M%S).log"
exec > "\$LOG_FILE" 2>&1

echo "=========================================="
echo "Merge Spectrum - RUN \$RUN"
echo "=========================================="

OUTPUT_FILE="\${SPECTRUM_DIR}/spectrum_RUN\${RUN}-MERGED.root"

if [ -f "\$OUTPUT_FILE" ]; then
    echo "Merged file exists, skipping"
    exit 0
fi

SPECTRUM_FILES=(\$(ls "\${SPECTRUM_DIR}"/spectrum_RUN\${RUN}-[0-9]*.root 2>/dev/null))
NUM_FILES=\${#SPECTRUM_FILES[@]}

if [ \$NUM_FILES -eq 0 ]; then
    echo "ERROR: No spectrum files found"
    exit 1
fi

echo "Found \$NUM_FILES files"

# Setup environment
source "\${JUNO_RELEASE}/setup-tao.sh"
ROOT_PYTHONPATH="\${PYTHONPATH}"
source "\${PYTHON_ENV_ROOT}/bin/activate"
export PYTHONPATH="\${ROOT_PYTHONPATH}:\${PYTHONPATH}"

# Run merge
MERGE_CMD="python \"\$MERGE_SCRIPT\" \"\$SPECTRUM_DIR/spectrum_RUN${RUN}-*.root\" \"\$OUTPUT_FILE\""
if [ -n "${SOURCE_NAME}" ]; then
  MERGE_CMD="\$MERGE_CMD --source-name ${SOURCE_NAME}"
fi
eval \$MERGE_CMD

if [ \$? -ne 0 ]; then
    echo "ERROR: Merge failed!"
    deactivate
    exit 1
fi

echo "Merge complete!"
echo "Output: \$OUTPUT_FILE"
deactivate
EOFMERGE

chmod +x "$MAIN_MERGE"

# Generate submit_merge.sh
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/submit_merge.sh" <<EOFSUBMITMERGE
#!/bin/bash
cd \$(dirname \$0)
hep_sub merge_spectrum_${RUN}.sh -g juno -o out-err/merge_${RUN}.out -e out-err/merge_${RUN}.err -mem 4000
echo "Merge job submitted"
echo "Check: hep_q -u \$USER"
EOFSUBMITMERGE

else
    SUBMIT_MERGE="${SCRIPTS_DIR}/merge_spectrum_${RUN}.sub"
    MAIN_MERGE_ABS=$(realpath "$MAIN_MERGE")
    OUTERR_ABS=$(realpath "$OUTERR_DIR")
    
    cat > "$SUBMIT_MERGE" <<EOFSUBMITMERGE
universe = vanilla
executable = $MAIN_MERGE_ABS
output = $OUTERR_ABS/merge_spectrum_${RUN}.out
error = $OUTERR_ABS/merge_spectrum_${RUN}.err
log = $OUTERR_ABS/merge_spectrum_${RUN}.log
+MaxRuntime = $MAX_RUNTIME_MERGE
request_cpus = 1
request_memory = 4GB
queue
EOFSUBMITMERGE

    cat > "$SCRIPTS_DIR/submit_merge.sh" <<EOFSUBMITMERGE
#!/bin/bash
cd \$(dirname \$0)
condor_submit -name sn01-htc.cr.cnaf.infn.it -batch-name merge_spectrum_${RUN} merge_spectrum_${RUN}.sub
echo "Merge job submitted"
EOFSUBMITMERGE
fi

chmod +x "$SCRIPTS_DIR/submit_merge.sh"

# =====================================================
# Generate check_status.sh
# =====================================================
if [ "$CLUSTER" = "IHEP" ]; then
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash
echo "=========================================="
echo "Job Status for RUN ${RUN} (IHEP)"
echo "=========================================="
TOTAL=$TOTAL_FILES
COMPLETED=\$(ls ${SPECTRUM_DIR}/spectrum_RUN${RUN}-[0-9]*.root 2>/dev/null | wc -l)
MERGED_EXISTS=\$(ls ${SPECTRUM_DIR}/spectrum_RUN${RUN}-MERGED.root 2>/dev/null | wc -l)

echo "Individual: \$COMPLETED/\$TOTAL (\$((COMPLETED * 100 / TOTAL))%)"
echo "Merged: \$([ \$MERGED_EXISTS -eq 1 ] && echo 'YES ✓' || echo 'NO')"
echo ""
echo "Queue:"
hep_q -u \$USER 2>/dev/null | head -20
echo ""
if [ \$COMPLETED -eq \$TOTAL ] && [ \$MERGED_EXISTS -eq 0 ]; then
    echo "Next: ./submit_merge.sh"
fi
EOFSTATUS

else
    cat > "$SCRIPTS_DIR/check_status.sh" <<EOFSTATUS
#!/bin/bash
echo "=========================================="
echo "Job Status for RUN ${RUN} (CNAF)"
echo "=========================================="
TOTAL=$TOTAL_FILES
COMPLETED=\$(ls ${SPECTRUM_DIR}/spectrum_RUN${RUN}-[0-9]*.root 2>/dev/null | wc -l)
MERGED_EXISTS=\$(ls ${SPECTRUM_DIR}/spectrum_RUN${RUN}-MERGED.root 2>/dev/null | wc -l)

echo "Individual: \$COMPLETED/\$TOTAL (\$((COMPLETED * 100 / TOTAL))%)"
echo "Merged: \$([ \$MERGED_EXISTS -eq 1 ] && echo 'YES ✓' || echo 'NO')"
echo ""
echo "Queue:"
condor_q -name sn01-htc.cr.cnaf.infn.it -batch get_spectrum_${RUN} 2>/dev/null || echo "No jobs"
echo ""
if [ \$COMPLETED -eq \$TOTAL ] && [ \$MERGED_EXISTS -eq 0 ]; then
    echo "Next: ./submit_merge.sh"
fi
EOFSTATUS
fi

chmod +x "$SCRIPTS_DIR/check_status.sh"

# =====================================================
# Final Summary
# =====================================================
echo ""
echo "=========================================="
echo "SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Generated:"
echo "  - $TOTAL_FILES job scripts"
if [ "$CLUSTER" = "CNAF" ]; then
    echo "  - $TOTAL_FILES HTCondor submit files"
fi
echo "  - 1 merge job"
echo "  - Submit & status scripts"
echo ""
echo "Output: $SPECTRUM_DIR"
echo "Config: $FOLDER_NAME"
echo ""
echo "To start:"
echo "  cd $SCRIPTS_DIR"
echo "  ./submit_all.sh"
echo ""
echo "To check:"
echo "  ./check_status.sh"
echo ""
echo "After completion:"
echo "  ./submit_merge.sh"
echo ""
echo "=========================================="
