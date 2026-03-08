#!/bin/bash
# reorganize_energy_resolution.sh
# Auto-generated: renames full old-style folders to new source-tagged names
# and removes stale duplicate empty folders.
#
# Usage: cd <parent_of_energy_resolution> && bash reorganize_energy_resolution.sh
# A dry-run mode is available: pass --dry-run as argument.
#
set -euo pipefail

BASE="${1:-energy_resolution}"
DRY_RUN=false
for arg in "$@"; do [ "$arg" = "--dry-run" ] && DRY_RUN=true; done

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $*"
    else
        echo "  >> $*"
        "$@"
    fi
}

echo "=================================================="
echo "  Energy-resolution folder reorganisation"
echo "  Base: $BASE"
[ "$DRY_RUN" = true ] && echo "  *** DRY-RUN MODE — no changes written ***"
echo "=================================================="
echo ""
echo "Total operations: 88 renames, 46 deletes"
echo ""

# ==================================================
# RUN1112
# ==================================================
echo "  [RUN1112] 1112_esd_noradialcut_pesumbasic_2026-02-20_22-26-26"
echo "       → 1112_esd_noradialcut_pesumbasic_Cs137_2026-02-23_03-17-24"
run_cmd rmdir "$BASE/RUN1112/1112_esd_noradialcut_pesumbasic_Cs137_2026-02-23_03-17-24"
run_cmd mv   "$BASE/RUN1112/1112_esd_noradialcut_pesumbasic_2026-02-20_22-26-26" "$BASE/RUN1112/1112_esd_noradialcut_pesumbasic_Cs137_2026-02-23_03-17-24"

echo "  [RUN1112] 1112_esd_noradialcut_pesumg_2026-02-20_22-23-31"
echo "       → 1112_esd_noradialcut_pesumg_Cs137_2026-02-23_03-17-15"
run_cmd rmdir "$BASE/RUN1112/1112_esd_noradialcut_pesumg_Cs137_2026-02-23_03-17-15"
run_cmd mv   "$BASE/RUN1112/1112_esd_noradialcut_pesumg_2026-02-20_22-23-31" "$BASE/RUN1112/1112_esd_noradialcut_pesumg_Cs137_2026-02-23_03-17-15"

echo "  [RUN1112] 1112_esd_offsrc_rcut150_pesumg_2026-02-20_22-23-56"
echo "       → 1112_esd_offsrc_rcut150_pesumg_Cs137_2026-02-23_03-17-11"
run_cmd rmdir "$BASE/RUN1112/1112_esd_offsrc_rcut150_pesumg_Cs137_2026-02-23_03-17-11"
run_cmd mv   "$BASE/RUN1112/1112_esd_offsrc_rcut150_pesumg_2026-02-20_22-23-56" "$BASE/RUN1112/1112_esd_offsrc_rcut150_pesumg_Cs137_2026-02-23_03-17-11"

echo "  [RUN1112] 1112_rtraw_default_2026-02-20_22-16-23"
echo "       → 1112_rtraw_default_Cs137_2026-02-23_03-17-02"
run_cmd rmdir "$BASE/RUN1112/1112_rtraw_default_Cs137_2026-02-23_03-17-02"
run_cmd mv   "$BASE/RUN1112/1112_rtraw_default_2026-02-20_22-16-23" "$BASE/RUN1112/1112_rtraw_default_Cs137_2026-02-23_03-17-02"

echo "  [RUN1112] 1112_rtraw_run1112_2026-02-20_22-16-33"
echo "       → 1112_rtraw_run1112_Cs137_2026-02-23_03-17-07"
run_cmd rmdir "$BASE/RUN1112/1112_rtraw_run1112_Cs137_2026-02-23_03-17-07"
run_cmd mv   "$BASE/RUN1112/1112_rtraw_run1112_2026-02-20_22-16-33" "$BASE/RUN1112/1112_rtraw_run1112_Cs137_2026-02-23_03-17-07"

# ==================================================
# RUN1157
# ==================================================
echo "  [RUN1157] 1157_esd_noradialcut_pesumbasic_2026-02-20_22-27-56"
echo "       → 1157_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-13-39"
run_cmd rmdir "$BASE/RUN1157/1157_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-08-14"
run_cmd rmdir "$BASE/RUN1157/1157_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-13-39"
run_cmd mv   "$BASE/RUN1157/1157_esd_noradialcut_pesumbasic_2026-02-20_22-27-56" "$BASE/RUN1157/1157_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-13-39"

echo "  [RUN1157] 1157_esd_noradialcut_pesumg_2026-02-20_22-27-43"
echo "       → 1157_esd_noradialcut_pesumg_Ge68_2026-02-23_03-13-38"
run_cmd rmdir "$BASE/RUN1157/1157_esd_noradialcut_pesumg_nosource_2026-02-23_03-08-12"
run_cmd rmdir "$BASE/RUN1157/1157_esd_noradialcut_pesumg_Ge68_2026-02-23_03-13-38"
run_cmd mv   "$BASE/RUN1157/1157_esd_noradialcut_pesumg_2026-02-20_22-27-43" "$BASE/RUN1157/1157_esd_noradialcut_pesumg_Ge68_2026-02-23_03-13-38"

echo "  [RUN1157] 1157_esd_rcut150_pesumbasic_2026-02-20_22-28-04"
echo "       → 1157_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-13-39"
run_cmd rmdir "$BASE/RUN1157/1157_esd_rcut150_pesumbasic_nosource_2026-02-23_03-08-13"
run_cmd rmdir "$BASE/RUN1157/1157_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-13-39"
run_cmd mv   "$BASE/RUN1157/1157_esd_rcut150_pesumbasic_2026-02-20_22-28-04" "$BASE/RUN1157/1157_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-13-39"

echo "  [RUN1157] 1157_esd_rcut150_pesumg_2026-02-20_22-27-37"
echo "       → 1157_esd_rcut150_pesumg_Ge68_2026-02-23_03-13-37"
run_cmd rmdir "$BASE/RUN1157/1157_esd_rcut150_pesumg_Ge68_2026-02-23_03-08-08"
run_cmd rmdir "$BASE/RUN1157/1157_esd_rcut150_pesumg_Ge68_2026-02-23_03-13-37"
run_cmd mv   "$BASE/RUN1157/1157_esd_rcut150_pesumg_2026-02-20_22-27-37" "$BASE/RUN1157/1157_esd_rcut150_pesumg_Ge68_2026-02-23_03-13-37"

echo "  [RUN1157] 1157_rtraw_default_2026-02-20_22-27-25"
echo "       → 1157_rtraw_default_Ge68_2026-02-23_03-13-23"
run_cmd rmdir "$BASE/RUN1157/1157_rtraw_default_Ge68_2026-02-23_03-07-48"
run_cmd rmdir "$BASE/RUN1157/1157_rtraw_default_Ge68_2026-02-23_03-13-23"
run_cmd mv   "$BASE/RUN1157/1157_rtraw_default_2026-02-20_22-27-25" "$BASE/RUN1157/1157_rtraw_default_Ge68_2026-02-23_03-13-23"

echo "  [RUN1157] 1157_rtraw_run1157_2026-02-20_22-27-30"
echo "       → 1157_rtraw_run1157_Ge68_2026-02-23_03-15-07"
run_cmd rmdir "$BASE/RUN1157/1157_rtraw_run1157_nosource_2026-02-23_03-08-07"
run_cmd rmdir "$BASE/RUN1157/1157_rtraw_run1157_nosource_2026-02-23_03-13-36"
run_cmd rmdir "$BASE/RUN1157/1157_rtraw_run1157_Ge68_2026-02-23_03-15-07"
run_cmd mv   "$BASE/RUN1157/1157_rtraw_run1157_2026-02-20_22-27-30" "$BASE/RUN1157/1157_rtraw_run1157_Ge68_2026-02-23_03-15-07"

# ==================================================
# RUN1236
# ==================================================
echo "  [RUN1236] 1236_esd_noradialcut_pesumbasic_2026-02-21_01-15-07"
echo "       → 1236_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-15-22"
run_cmd rmdir "$BASE/RUN1236/1236_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-08-23"
run_cmd rmdir "$BASE/RUN1236/1236_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-15-22"
run_cmd mv   "$BASE/RUN1236/1236_esd_noradialcut_pesumbasic_2026-02-21_01-15-07" "$BASE/RUN1236/1236_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-15-22"

echo "  [RUN1236] 1236_esd_noradialcut_pesumg_2026-02-21_01-14-51"
echo "       → 1236_esd_noradialcut_pesumg_Ge68_2026-02-23_03-15-20"
run_cmd rmdir "$BASE/RUN1236/1236_esd_noradialcut_pesumg_nosource_2026-02-23_03-08-20"
run_cmd rmdir "$BASE/RUN1236/1236_esd_noradialcut_pesumg_Ge68_2026-02-23_03-15-20"
run_cmd mv   "$BASE/RUN1236/1236_esd_noradialcut_pesumg_2026-02-21_01-14-51" "$BASE/RUN1236/1236_esd_noradialcut_pesumg_Ge68_2026-02-23_03-15-20"

echo "  [RUN1236] 1236_esd_rcut150_pesumbasic_2026-02-21_01-15-15"
echo "       → 1236_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-15-21"
run_cmd rmdir "$BASE/RUN1236/1236_esd_rcut150_pesumbasic_nosource_2026-02-23_03-08-22"
run_cmd rmdir "$BASE/RUN1236/1236_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-15-21"
run_cmd mv   "$BASE/RUN1236/1236_esd_rcut150_pesumbasic_2026-02-21_01-15-15" "$BASE/RUN1236/1236_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-15-21"

echo "  [RUN1236] 1236_esd_rcut150_pesumg_2026-02-21_01-14-44"
echo "       → 1236_esd_rcut150_pesumg_Ge68_2026-02-23_03-15-19"
run_cmd rmdir "$BASE/RUN1236/1236_esd_rcut150_pesumg_Ge68_2026-02-23_03-08-19"
run_cmd rmdir "$BASE/RUN1236/1236_esd_rcut150_pesumg_Ge68_2026-02-23_03-15-19"
run_cmd mv   "$BASE/RUN1236/1236_esd_rcut150_pesumg_2026-02-21_01-14-44" "$BASE/RUN1236/1236_esd_rcut150_pesumg_Ge68_2026-02-23_03-15-19"

echo "  [RUN1236] 1236_rtraw_default_2026-02-21_01-13-57"
echo "       → 1236_rtraw_default_Ge68_2026-02-23_03-08-16"
run_cmd rmdir "$BASE/RUN1236/1236_rtraw_default_Ge68_2026-02-23_03-08-16"
run_cmd mv   "$BASE/RUN1236/1236_rtraw_default_2026-02-21_01-13-57" "$BASE/RUN1236/1236_rtraw_default_Ge68_2026-02-23_03-08-16"

echo "  [RUN1236] 1236_rtraw_run1236_2026-02-21_01-14-07"
echo "       → 1236_rtraw_run1236_Ge68_2026-02-23_03-15-18"
run_cmd rmdir "$BASE/RUN1236/1236_rtraw_run1236_nosource_2026-02-23_03-08-17"
run_cmd rmdir "$BASE/RUN1236/1236_rtraw_run1236_Ge68_2026-02-23_03-15-18"
run_cmd mv   "$BASE/RUN1236/1236_rtraw_run1236_2026-02-21_01-14-07" "$BASE/RUN1236/1236_rtraw_run1236_Ge68_2026-02-23_03-15-18"

# ==================================================
# RUN1253
# ==================================================
echo "  [RUN1253] 1253_esd_noradialcut_pesumbasic_2026-02-21_01-25-32"
echo "       → 1253_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-00"
run_cmd rmdir "$BASE/RUN1253/1253_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-08-30"
run_cmd rmdir "$BASE/RUN1253/1253_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-00"
run_cmd mv   "$BASE/RUN1253/1253_esd_noradialcut_pesumbasic_2026-02-21_01-25-32" "$BASE/RUN1253/1253_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-00"

echo "  [RUN1253] 1253_esd_noradialcut_pesumg_2026-02-21_01-25-30"
echo "       → 1253_esd_noradialcut_pesumg_Ge68_2026-02-23_03-15-58"
run_cmd rmdir "$BASE/RUN1253/1253_esd_noradialcut_pesumg_nosource_2026-02-23_03-08-27"
run_cmd rmdir "$BASE/RUN1253/1253_esd_noradialcut_pesumg_Ge68_2026-02-23_03-15-58"
run_cmd mv   "$BASE/RUN1253/1253_esd_noradialcut_pesumg_2026-02-21_01-25-30" "$BASE/RUN1253/1253_esd_noradialcut_pesumg_Ge68_2026-02-23_03-15-58"

echo "  [RUN1253] 1253_esd_rcut150_pesumbasic_2026-02-21_01-25-31"
echo "       → 1253_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-15-59"
run_cmd rmdir "$BASE/RUN1253/1253_esd_rcut150_pesumbasic_nosource_2026-02-23_03-08-29"
run_cmd rmdir "$BASE/RUN1253/1253_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-15-59"
run_cmd mv   "$BASE/RUN1253/1253_esd_rcut150_pesumbasic_2026-02-21_01-25-31" "$BASE/RUN1253/1253_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-15-59"

echo "  [RUN1253] 1253_esd_rcut150_pesumg_2026-02-21_01-25-23"
echo "       → 1253_esd_rcut150_pesumg_Ge68_2026-02-23_03-15-57"
run_cmd rmdir "$BASE/RUN1253/1253_esd_rcut150_pesumg_Ge68_2026-02-23_03-08-26"
run_cmd rmdir "$BASE/RUN1253/1253_esd_rcut150_pesumg_Ge68_2026-02-23_03-15-57"
run_cmd mv   "$BASE/RUN1253/1253_esd_rcut150_pesumg_2026-02-21_01-25-23" "$BASE/RUN1253/1253_esd_rcut150_pesumg_Ge68_2026-02-23_03-15-57"

echo "  [RUN1253] 1253_rtraw_default_2026-02-21_01-18-12"
echo "       → 1253_rtraw_default_Ge68_2026-02-23_03-15-55"
run_cmd rmdir "$BASE/RUN1253/1253_rtraw_default_Ge68_2026-02-23_03-08-24"
run_cmd rmdir "$BASE/RUN1253/1253_rtraw_default_Ge68_2026-02-23_03-15-55"
run_cmd mv   "$BASE/RUN1253/1253_rtraw_default_2026-02-21_01-18-12" "$BASE/RUN1253/1253_rtraw_default_Ge68_2026-02-23_03-15-55"

echo "  [RUN1253] 1253_rtraw_run1253_2026-02-21_01-25-15"
echo "       → 1253_rtraw_run1253_Ge68_2026-02-23_03-15-56"
run_cmd rmdir "$BASE/RUN1253/1253_rtraw_run1253_nosource_2026-02-23_03-08-25"
run_cmd rmdir "$BASE/RUN1253/1253_rtraw_run1253_Ge68_2026-02-23_03-15-56"
run_cmd mv   "$BASE/RUN1253/1253_rtraw_run1253_2026-02-21_01-25-15" "$BASE/RUN1253/1253_rtraw_run1253_Ge68_2026-02-23_03-15-56"

# ==================================================
# RUN1257
# ==================================================
echo "  [RUN1257] 1257_esd_noradialcut_pesumbasic_2026-02-21_01-31-02"
echo "       → 1257_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-05"
run_cmd rmdir "$BASE/RUN1257/1257_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-08-37"
run_cmd rmdir "$BASE/RUN1257/1257_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-05"
run_cmd mv   "$BASE/RUN1257/1257_esd_noradialcut_pesumbasic_2026-02-21_01-31-02" "$BASE/RUN1257/1257_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-05"

echo "  [RUN1257] 1257_esd_noradialcut_pesumg_2026-02-21_01-30-59"
echo "       → 1257_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-03"
run_cmd rmdir "$BASE/RUN1257/1257_esd_noradialcut_pesumg_nosource_2026-02-23_03-08-34"
run_cmd rmdir "$BASE/RUN1257/1257_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-03"
run_cmd mv   "$BASE/RUN1257/1257_esd_noradialcut_pesumg_2026-02-21_01-30-59" "$BASE/RUN1257/1257_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-03"

echo "  [RUN1257] 1257_esd_rcut150_pesumbasic_2026-02-21_01-31-00"
echo "       → 1257_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-04"
run_cmd rmdir "$BASE/RUN1257/1257_esd_rcut150_pesumbasic_nosource_2026-02-23_03-08-35"
run_cmd rmdir "$BASE/RUN1257/1257_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-04"
run_cmd mv   "$BASE/RUN1257/1257_esd_rcut150_pesumbasic_2026-02-21_01-31-00" "$BASE/RUN1257/1257_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-04"

echo "  [RUN1257] 1257_esd_rcut150_pesumg_2026-02-21_01-30-57"
echo "       → 1257_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-02"
run_cmd rmdir "$BASE/RUN1257/1257_esd_rcut150_pesumg_Ge68_2026-02-23_03-08-32"
run_cmd rmdir "$BASE/RUN1257/1257_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-02"
run_cmd mv   "$BASE/RUN1257/1257_esd_rcut150_pesumg_2026-02-21_01-30-57" "$BASE/RUN1257/1257_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-02"

echo "  [RUN1257] 1257_rtraw_default_2026-02-21_01-18-24"
echo "       → 1257_rtraw_default_Ge68_2026-02-23_03-16-01"
run_cmd rmdir "$BASE/RUN1257/1257_rtraw_default_Ge68_2026-02-23_03-08-31"
run_cmd rmdir "$BASE/RUN1257/1257_rtraw_default_Ge68_2026-02-23_03-16-01"
run_cmd mv   "$BASE/RUN1257/1257_rtraw_default_2026-02-21_01-18-24" "$BASE/RUN1257/1257_rtraw_default_Ge68_2026-02-23_03-16-01"

echo "  [RUN1257] 1257_rtraw_run1257_2026-02-21_01-30-56"
echo "       → 1257_rtraw_run1257_Ge68_2026-02-23_03-16-01"
run_cmd rmdir "$BASE/RUN1257/1257_rtraw_run1257_nosource_2026-02-23_03-08-31"
run_cmd rmdir "$BASE/RUN1257/1257_rtraw_run1257_Ge68_2026-02-23_03-16-01"
run_cmd mv   "$BASE/RUN1257/1257_rtraw_run1257_2026-02-21_01-30-56" "$BASE/RUN1257/1257_rtraw_run1257_Ge68_2026-02-23_03-16-01"

# ==================================================
# RUN1259
# ==================================================
echo "  [RUN1259] 1259_esd_noradialcut_pesumbasic_2026-02-21_01-31-25"
echo "       → 1259_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-15"
run_cmd rmdir "$BASE/RUN1259/1259_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-08-44"
run_cmd rmdir "$BASE/RUN1259/1259_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-15"
run_cmd mv   "$BASE/RUN1259/1259_esd_noradialcut_pesumbasic_2026-02-21_01-31-25" "$BASE/RUN1259/1259_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-15"

echo "  [RUN1259] 1259_esd_noradialcut_pesumg_2026-02-21_01-31-22"
echo "       → 1259_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-08"
run_cmd rmdir "$BASE/RUN1259/1259_esd_noradialcut_pesumg_nosource_2026-02-23_03-08-41"
run_cmd rmdir "$BASE/RUN1259/1259_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-08"
run_cmd mv   "$BASE/RUN1259/1259_esd_noradialcut_pesumg_2026-02-21_01-31-22" "$BASE/RUN1259/1259_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-08"

echo "  [RUN1259] 1259_esd_rcut150_pesumbasic_2026-02-21_01-31-24"
echo "       → 1259_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-14"
run_cmd rmdir "$BASE/RUN1259/1259_esd_rcut150_pesumbasic_nosource_2026-02-23_03-08-42"
run_cmd rmdir "$BASE/RUN1259/1259_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-14"
run_cmd mv   "$BASE/RUN1259/1259_esd_rcut150_pesumbasic_2026-02-21_01-31-24" "$BASE/RUN1259/1259_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-14"

echo "  [RUN1259] 1259_esd_rcut150_pesumg_2026-02-21_01-31-21"
echo "       → 1259_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-07"
run_cmd rmdir "$BASE/RUN1259/1259_esd_rcut150_pesumg_Ge68_2026-02-23_03-08-40"
run_cmd rmdir "$BASE/RUN1259/1259_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-07"
run_cmd mv   "$BASE/RUN1259/1259_esd_rcut150_pesumg_2026-02-21_01-31-21" "$BASE/RUN1259/1259_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-07"

echo "  [RUN1259] 1259_rtraw_default_2026-02-21_01-18-27"
echo "       → 1259_rtraw_default_Ge68_2026-02-23_03-16-06"
run_cmd rmdir "$BASE/RUN1259/1259_rtraw_default_Ge68_2026-02-23_03-08-38"
run_cmd rmdir "$BASE/RUN1259/1259_rtraw_default_Ge68_2026-02-23_03-16-06"
run_cmd mv   "$BASE/RUN1259/1259_rtraw_default_2026-02-21_01-18-27" "$BASE/RUN1259/1259_rtraw_default_Ge68_2026-02-23_03-16-06"

echo "  [RUN1259] 1259_rtraw_run1259_2026-02-21_01-31-20"
echo "       → 1259_rtraw_run1259_Ge68_2026-02-23_03-16-06"
run_cmd rmdir "$BASE/RUN1259/1259_rtraw_run1259_nosource_2026-02-23_03-08-39"
run_cmd rmdir "$BASE/RUN1259/1259_rtraw_run1259_Ge68_2026-02-23_03-16-06"
run_cmd mv   "$BASE/RUN1259/1259_rtraw_run1259_2026-02-21_01-31-20" "$BASE/RUN1259/1259_rtraw_run1259_Ge68_2026-02-23_03-16-06"

# ==================================================
# RUN1260
# ==================================================
echo "  [RUN1260] 1260_esd_noradialcut_pesumbasic_2026-02-21_01-31-49"
echo "       → 1260_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-20"
run_cmd rmdir "$BASE/RUN1260/1260_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-08-57"
run_cmd rmdir "$BASE/RUN1260/1260_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-20"
run_cmd mv   "$BASE/RUN1260/1260_esd_noradialcut_pesumbasic_2026-02-21_01-31-49" "$BASE/RUN1260/1260_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-20"

echo "  [RUN1260] 1260_esd_noradialcut_pesumg_2026-02-21_01-31-46"
echo "       → 1260_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-18"
run_cmd rmdir "$BASE/RUN1260/1260_esd_noradialcut_pesumg_nosource_2026-02-23_03-08-53"
run_cmd rmdir "$BASE/RUN1260/1260_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-18"
run_cmd mv   "$BASE/RUN1260/1260_esd_noradialcut_pesumg_2026-02-21_01-31-46" "$BASE/RUN1260/1260_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-18"

echo "  [RUN1260] 1260_esd_rcut150_pesumbasic_2026-02-21_01-31-47"
echo "       → 1260_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-19"
run_cmd rmdir "$BASE/RUN1260/1260_esd_rcut150_pesumbasic_nosource_2026-02-23_03-08-54"
run_cmd rmdir "$BASE/RUN1260/1260_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-19"
run_cmd mv   "$BASE/RUN1260/1260_esd_rcut150_pesumbasic_2026-02-21_01-31-47" "$BASE/RUN1260/1260_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-19"

echo "  [RUN1260] 1260_esd_rcut150_pesumg_2026-02-21_01-31-44"
echo "       → 1260_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-17"
run_cmd rmdir "$BASE/RUN1260/1260_esd_rcut150_pesumg_Ge68_2026-02-23_03-08-51"
run_cmd rmdir "$BASE/RUN1260/1260_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-17"
run_cmd mv   "$BASE/RUN1260/1260_esd_rcut150_pesumg_2026-02-21_01-31-44" "$BASE/RUN1260/1260_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-17"

echo "  [RUN1260] 1260_rtraw_default_2026-02-21_01-18-32"
echo "       → 1260_rtraw_default_Ge68_2026-02-23_03-16-16"
run_cmd rmdir "$BASE/RUN1260/1260_rtraw_default_Ge68_2026-02-23_03-08-45"
run_cmd rmdir "$BASE/RUN1260/1260_rtraw_default_Ge68_2026-02-23_03-16-16"
run_cmd mv   "$BASE/RUN1260/1260_rtraw_default_2026-02-21_01-18-32" "$BASE/RUN1260/1260_rtraw_default_Ge68_2026-02-23_03-16-16"

echo "  [RUN1260] 1260_rtraw_run1260_2026-02-21_01-31-43"
echo "       → 1260_rtraw_run1260_Ge68_2026-02-23_03-16-16"
run_cmd rmdir "$BASE/RUN1260/1260_rtraw_run1260_nosource_2026-02-23_03-08-50"
run_cmd rmdir "$BASE/RUN1260/1260_rtraw_run1260_Ge68_2026-02-23_03-16-16"
run_cmd mv   "$BASE/RUN1260/1260_rtraw_run1260_2026-02-21_01-31-43" "$BASE/RUN1260/1260_rtraw_run1260_Ge68_2026-02-23_03-16-16"

# ==================================================
# RUN1261
# ==================================================
echo "  [RUN1261] 1261_esd_noradialcut_pesumbasic_2026-02-21_01-32-10"
echo "       → 1261_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-26"
run_cmd rmdir "$BASE/RUN1261/1261_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-09-04"
run_cmd rmdir "$BASE/RUN1261/1261_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-26"
run_cmd mv   "$BASE/RUN1261/1261_esd_noradialcut_pesumbasic_2026-02-21_01-32-10" "$BASE/RUN1261/1261_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-26"

echo "  [RUN1261] 1261_esd_noradialcut_pesumg_2026-02-21_01-32-07"
echo "       → 1261_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-23"
run_cmd rmdir "$BASE/RUN1261/1261_esd_noradialcut_pesumg_nosource_2026-02-23_03-09-01"
run_cmd rmdir "$BASE/RUN1261/1261_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-23"
run_cmd mv   "$BASE/RUN1261/1261_esd_noradialcut_pesumg_2026-02-21_01-32-07" "$BASE/RUN1261/1261_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-23"

echo "  [RUN1261] 1261_esd_rcut150_pesumbasic_2026-02-21_01-32-08"
echo "       → 1261_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-24"
run_cmd rmdir "$BASE/RUN1261/1261_esd_rcut150_pesumbasic_nosource_2026-02-23_03-09-03"
run_cmd rmdir "$BASE/RUN1261/1261_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-24"
run_cmd mv   "$BASE/RUN1261/1261_esd_rcut150_pesumbasic_2026-02-21_01-32-08" "$BASE/RUN1261/1261_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-24"

echo "  [RUN1261] 1261_esd_rcut150_pesumg_2026-02-21_01-32-06"
echo "       → 1261_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-22"
run_cmd rmdir "$BASE/RUN1261/1261_esd_rcut150_pesumg_Ge68_2026-02-23_03-09-00"
run_cmd rmdir "$BASE/RUN1261/1261_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-22"
run_cmd mv   "$BASE/RUN1261/1261_esd_rcut150_pesumg_2026-02-21_01-32-06" "$BASE/RUN1261/1261_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-22"

echo "  [RUN1261] 1261_rtraw_default_2026-02-21_01-18-36"
echo "       → 1261_rtraw_default_Ge68_2026-02-23_03-16-21"
run_cmd rmdir "$BASE/RUN1261/1261_rtraw_default_Ge68_2026-02-23_03-08-58"
run_cmd rmdir "$BASE/RUN1261/1261_rtraw_default_Ge68_2026-02-23_03-16-21"
run_cmd mv   "$BASE/RUN1261/1261_rtraw_default_2026-02-21_01-18-36" "$BASE/RUN1261/1261_rtraw_default_Ge68_2026-02-23_03-16-21"

echo "  [RUN1261] 1261_rtraw_run1261_2026-02-21_01-32-05"
echo "       → 1261_rtraw_run1261_Ge68_2026-02-23_03-16-22"
run_cmd rmdir "$BASE/RUN1261/1261_rtraw_run1261_nosource_2026-02-23_03-08-59"
run_cmd rmdir "$BASE/RUN1261/1261_rtraw_run1261_Ge68_2026-02-23_03-16-22"
run_cmd mv   "$BASE/RUN1261/1261_rtraw_run1261_2026-02-21_01-32-05" "$BASE/RUN1261/1261_rtraw_run1261_Ge68_2026-02-23_03-16-22"

# ==================================================
# RUN1262
# ==================================================
echo "  [RUN1262] 1262_esd_noradialcut_pesumbasic_2026-02-21_01-32-35"
echo "       → 1262_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-33"
run_cmd rmdir "$BASE/RUN1262/1262_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-33"
run_cmd mv   "$BASE/RUN1262/1262_esd_noradialcut_pesumbasic_2026-02-21_01-32-35" "$BASE/RUN1262/1262_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-33"

echo "  [RUN1262] 1262_esd_noradialcut_pesumg_2026-02-21_01-32-32"
echo "       → 1262_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-30"
run_cmd rmdir "$BASE/RUN1262/1262_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-30"
run_cmd mv   "$BASE/RUN1262/1262_esd_noradialcut_pesumg_2026-02-21_01-32-32" "$BASE/RUN1262/1262_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-30"

echo "  [RUN1262] 1262_esd_rcut150_pesumbasic_2026-02-21_01-32-34"
echo "       → 1262_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-31"
run_cmd rmdir "$BASE/RUN1262/1262_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-31"
run_cmd mv   "$BASE/RUN1262/1262_esd_rcut150_pesumbasic_2026-02-21_01-32-34" "$BASE/RUN1262/1262_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-31"

echo "  [RUN1262] 1262_esd_rcut150_pesumg_2026-02-21_01-32-26"
echo "       → 1262_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-28"
run_cmd rmdir "$BASE/RUN1262/1262_esd_rcut150_pesumg_Ge68_2026-02-23_03-09-07"
run_cmd rmdir "$BASE/RUN1262/1262_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-28"
run_cmd mv   "$BASE/RUN1262/1262_esd_rcut150_pesumg_2026-02-21_01-32-26" "$BASE/RUN1262/1262_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-28"

echo "  [RUN1262] 1262_rtraw_default_2026-02-21_01-18-39"
echo "       → 1262_rtraw_default_Ge68_2026-02-23_03-16-26"
run_cmd rmdir "$BASE/RUN1262/1262_rtraw_default_Ge68_2026-02-23_03-09-05"
run_cmd rmdir "$BASE/RUN1262/1262_rtraw_default_Ge68_2026-02-23_03-16-26"
run_cmd mv   "$BASE/RUN1262/1262_rtraw_default_2026-02-21_01-18-39" "$BASE/RUN1262/1262_rtraw_default_Ge68_2026-02-23_03-16-26"

echo "  [RUN1262] 1262_rtraw_run1262_2026-02-21_01-32-25"
echo "       → 1262_rtraw_run1262_Ge68_2026-02-23_03-16-27"
run_cmd rmdir "$BASE/RUN1262/1262_rtraw_run1262_nosource_2026-02-23_03-09-06"
run_cmd rmdir "$BASE/RUN1262/1262_rtraw_run1262_Ge68_2026-02-23_03-16-27"
run_cmd mv   "$BASE/RUN1262/1262_rtraw_run1262_2026-02-21_01-32-25" "$BASE/RUN1262/1262_rtraw_run1262_Ge68_2026-02-23_03-16-27"

# ==================================================
# RUN1263
# ==================================================
echo "  [RUN1263] 1263_esd_noradialcut_pesumbasic_2026-02-21_01-32-59"
echo "       → 1263_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-39"
run_cmd rmdir "$BASE/RUN1263/1263_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-39"
run_cmd mv   "$BASE/RUN1263/1263_esd_noradialcut_pesumbasic_2026-02-21_01-32-59" "$BASE/RUN1263/1263_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-39"

echo "  [RUN1263] 1263_esd_noradialcut_pesumg_2026-02-21_01-32-55"
echo "       → 1263_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-37"
run_cmd rmdir "$BASE/RUN1263/1263_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-37"
run_cmd mv   "$BASE/RUN1263/1263_esd_noradialcut_pesumg_2026-02-21_01-32-55" "$BASE/RUN1263/1263_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-37"

echo "  [RUN1263] 1263_esd_rcut150_pesumbasic_2026-02-21_01-32-57"
echo "       → 1263_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-38"
run_cmd rmdir "$BASE/RUN1263/1263_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-38"
run_cmd mv   "$BASE/RUN1263/1263_esd_rcut150_pesumbasic_2026-02-21_01-32-57" "$BASE/RUN1263/1263_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-38"

echo "  [RUN1263] 1263_esd_rcut150_pesumg_2026-02-21_01-32-53"
echo "       → 1263_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-36"
run_cmd rmdir "$BASE/RUN1263/1263_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-36"
run_cmd mv   "$BASE/RUN1263/1263_esd_rcut150_pesumg_2026-02-21_01-32-53" "$BASE/RUN1263/1263_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-36"

echo "  [RUN1263] 1263_rtraw_default_2026-02-21_01-18-43"
echo "       → 1263_rtraw_default_Ge68_2026-02-23_03-16-34"
run_cmd rmdir "$BASE/RUN1263/1263_rtraw_default_Ge68_2026-02-23_03-16-34"
run_cmd mv   "$BASE/RUN1263/1263_rtraw_default_2026-02-21_01-18-43" "$BASE/RUN1263/1263_rtraw_default_Ge68_2026-02-23_03-16-34"

echo "  [RUN1263] 1263_rtraw_run1263_2026-02-21_01-32-52"
echo "       → 1263_rtraw_run1263_Ge68_2026-02-23_03-16-34"
run_cmd rmdir "$BASE/RUN1263/1263_rtraw_run1263_Ge68_2026-02-23_03-16-34"
run_cmd mv   "$BASE/RUN1263/1263_rtraw_run1263_2026-02-21_01-32-52" "$BASE/RUN1263/1263_rtraw_run1263_Ge68_2026-02-23_03-16-34"

# ==================================================
# RUN1295
# ==================================================
echo "  [RUN1295] 1295_esd_noradialcut_pesumbasic_2026-02-21_01-33-38"
echo "       → 1295_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-47"
run_cmd rmdir "$BASE/RUN1295/1295_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-47"
run_cmd mv   "$BASE/RUN1295/1295_esd_noradialcut_pesumbasic_2026-02-21_01-33-38" "$BASE/RUN1295/1295_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-47"

echo "  [RUN1295] 1295_esd_noradialcut_pesumg_2026-02-21_01-33-34"
echo "       → 1295_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-45"
run_cmd rmdir "$BASE/RUN1295/1295_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-45"
run_cmd mv   "$BASE/RUN1295/1295_esd_noradialcut_pesumg_2026-02-21_01-33-34" "$BASE/RUN1295/1295_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-45"

echo "  [RUN1295] 1295_esd_rcut150_pesumbasic_2026-02-21_01-33-36"
echo "       → 1295_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-46"
run_cmd rmdir "$BASE/RUN1295/1295_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-46"
run_cmd mv   "$BASE/RUN1295/1295_esd_rcut150_pesumbasic_2026-02-21_01-33-36" "$BASE/RUN1295/1295_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-46"

echo "  [RUN1295] 1295_esd_rcut150_pesumg_2026-02-21_01-33-33"
echo "       → 1295_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-43"
run_cmd rmdir "$BASE/RUN1295/1295_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-43"
run_cmd mv   "$BASE/RUN1295/1295_esd_rcut150_pesumg_2026-02-21_01-33-33" "$BASE/RUN1295/1295_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-43"

echo "  [RUN1295] 1295_rtraw_default_2026-02-21_01-18-50"
echo "       → 1295_rtraw_default_Ge68_2026-02-23_03-16-40"
run_cmd rmdir "$BASE/RUN1295/1295_rtraw_default_Ge68_2026-02-23_03-09-11"
run_cmd rmdir "$BASE/RUN1295/1295_rtraw_default_Ge68_2026-02-23_03-16-40"
run_cmd mv   "$BASE/RUN1295/1295_rtraw_default_2026-02-21_01-18-50" "$BASE/RUN1295/1295_rtraw_default_Ge68_2026-02-23_03-16-40"

echo "  [RUN1295] 1295_rtraw_run1295_2026-02-21_01-33-31"
echo "       → 1295_rtraw_run1295_Ge68_2026-02-23_03-16-42"
run_cmd rmdir "$BASE/RUN1295/1295_rtraw_run1295_Ge68_2026-02-23_03-16-42"
run_cmd mv   "$BASE/RUN1295/1295_rtraw_run1295_2026-02-21_01-33-31" "$BASE/RUN1295/1295_rtraw_run1295_Ge68_2026-02-23_03-16-42"

# ==================================================
# RUN1296
# ==================================================
echo "  [RUN1296] 1296_esd_noradialcut_pesumbasic_2026-02-21_01-33-58"
echo "       → 1296_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-53"
run_cmd rmdir "$BASE/RUN1296/1296_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-53"
run_cmd mv   "$BASE/RUN1296/1296_esd_noradialcut_pesumbasic_2026-02-21_01-33-58" "$BASE/RUN1296/1296_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-53"

echo "  [RUN1296] 1296_esd_noradialcut_pesumg_2026-02-21_01-33-56"
echo "       → 1296_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-51"
run_cmd rmdir "$BASE/RUN1296/1296_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-51"
run_cmd mv   "$BASE/RUN1296/1296_esd_noradialcut_pesumg_2026-02-21_01-33-56" "$BASE/RUN1296/1296_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-51"

echo "  [RUN1296] 1296_esd_rcut150_pesumbasic_2026-02-21_01-33-57"
echo "       → 1296_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-52"
run_cmd rmdir "$BASE/RUN1296/1296_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-52"
run_cmd mv   "$BASE/RUN1296/1296_esd_rcut150_pesumbasic_2026-02-21_01-33-57" "$BASE/RUN1296/1296_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-52"

echo "  [RUN1296] 1296_esd_rcut150_pesumg_2026-02-21_01-33-55"
echo "       → 1296_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-50"
run_cmd rmdir "$BASE/RUN1296/1296_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-50"
run_cmd mv   "$BASE/RUN1296/1296_esd_rcut150_pesumg_2026-02-21_01-33-55" "$BASE/RUN1296/1296_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-50"

echo "  [RUN1296] 1296_rtraw_default_2026-02-21_01-18-55"
echo "       → 1296_rtraw_default_Ge68_2026-02-23_03-16-49"
run_cmd rmdir "$BASE/RUN1296/1296_rtraw_default_Ge68_2026-02-23_03-16-49"
run_cmd mv   "$BASE/RUN1296/1296_rtraw_default_2026-02-21_01-18-55" "$BASE/RUN1296/1296_rtraw_default_Ge68_2026-02-23_03-16-49"

echo "  [RUN1296] 1296_rtraw_run1296_2026-02-21_01-33-53"
echo "       → 1296_rtraw_run1296_Ge68_2026-02-23_03-16-49"
run_cmd rmdir "$BASE/RUN1296/1296_rtraw_run1296_Ge68_2026-02-23_03-16-49"
run_cmd mv   "$BASE/RUN1296/1296_rtraw_run1296_2026-02-21_01-33-53" "$BASE/RUN1296/1296_rtraw_run1296_Ge68_2026-02-23_03-16-49"

# ==================================================
# RUN1319
# ==================================================
echo "  [RUN1319] 1319_esd_noradialcut_pesumbasic_2026-02-21_01-34-18"
echo "       → 1319_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-56"
run_cmd rmdir "$BASE/RUN1319/1319_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-56"
run_cmd mv   "$BASE/RUN1319/1319_esd_noradialcut_pesumbasic_2026-02-21_01-34-18" "$BASE/RUN1319/1319_esd_noradialcut_pesumbasic_Ge68_2026-02-23_03-16-56"

echo "  [RUN1319] 1319_esd_noradialcut_pesumg_2026-02-21_01-34-17"
echo "       → 1319_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-56"
run_cmd rmdir "$BASE/RUN1319/1319_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-56"
run_cmd mv   "$BASE/RUN1319/1319_esd_noradialcut_pesumg_2026-02-21_01-34-17" "$BASE/RUN1319/1319_esd_noradialcut_pesumg_Ge68_2026-02-23_03-16-56"

echo "  [RUN1319] 1319_esd_rcut150_pesumbasic_2026-02-21_01-34-18"
echo "       → 1319_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-56"
run_cmd rmdir "$BASE/RUN1319/1319_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-56"
run_cmd mv   "$BASE/RUN1319/1319_esd_rcut150_pesumbasic_2026-02-21_01-34-18" "$BASE/RUN1319/1319_esd_rcut150_pesumbasic_Ge68_2026-02-23_03-16-56"

echo "  [RUN1319] 1319_esd_rcut150_pesumg_2026-02-21_01-34-17"
echo "       → 1319_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-55"
run_cmd rmdir "$BASE/RUN1319/1319_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-55"
run_cmd mv   "$BASE/RUN1319/1319_esd_rcut150_pesumg_2026-02-21_01-34-17" "$BASE/RUN1319/1319_esd_rcut150_pesumg_Ge68_2026-02-23_03-16-55"

echo "  [RUN1319] 1319_rtraw_default_2026-02-21_01-19-03"
echo "       → 1319_rtraw_default_Ge68_2026-02-23_03-16-54"
run_cmd rmdir "$BASE/RUN1319/1319_rtraw_default_Ge68_2026-02-23_03-16-54"
run_cmd mv   "$BASE/RUN1319/1319_rtraw_default_2026-02-21_01-19-03" "$BASE/RUN1319/1319_rtraw_default_Ge68_2026-02-23_03-16-54"

echo "  [RUN1319] 1319_rtraw_run1319_2026-02-21_01-34-16"
echo "       → 1319_rtraw_run1319_Ge68_2026-02-23_03-16-55"
run_cmd rmdir "$BASE/RUN1319/1319_rtraw_run1319_Ge68_2026-02-23_03-16-55"
run_cmd mv   "$BASE/RUN1319/1319_rtraw_run1319_2026-02-21_01-34-16" "$BASE/RUN1319/1319_rtraw_run1319_Ge68_2026-02-23_03-16-55"

# ==================================================
# RUN1344
# ==================================================
echo "  [RUN1344] 1344_esd_noradialcut_pesumbasic_2026-02-21_01-37-15"
echo "       → 1344_esd_noradialcut_pesumbasic_Cs137_2026-02-23_03-17-47"
run_cmd rmdir "$BASE/RUN1344/1344_esd_noradialcut_pesumbasic_Cs137_2026-02-23_03-17-47"
run_cmd mv   "$BASE/RUN1344/1344_esd_noradialcut_pesumbasic_2026-02-21_01-37-15" "$BASE/RUN1344/1344_esd_noradialcut_pesumbasic_Cs137_2026-02-23_03-17-47"

echo "  [RUN1344] 1344_esd_noradialcut_pesumg_2026-02-21_01-37-03"
echo "       → 1344_esd_noradialcut_pesumg_Cs137_2026-02-23_03-17-38"
run_cmd rmdir "$BASE/RUN1344/1344_esd_noradialcut_pesumg_Cs137_2026-02-23_03-17-38"
run_cmd mv   "$BASE/RUN1344/1344_esd_noradialcut_pesumg_2026-02-21_01-37-03" "$BASE/RUN1344/1344_esd_noradialcut_pesumg_Cs137_2026-02-23_03-17-38"

echo "  [RUN1344] 1344_esd_offsrc_rcut150_pesumg_2026-02-21_01-36-56"
echo "       → 1344_esd_offsrc_rcut150_pesumg_Cs137_2026-02-23_03-17-33"
run_cmd rmdir "$BASE/RUN1344/1344_esd_offsrc_rcut150_pesumg_Cs137_2026-02-23_03-17-33"
run_cmd mv   "$BASE/RUN1344/1344_esd_offsrc_rcut150_pesumg_2026-02-21_01-36-56" "$BASE/RUN1344/1344_esd_offsrc_rcut150_pesumg_Cs137_2026-02-23_03-17-33"

echo "  [RUN1344] 1344_rtraw_default_2026-02-21_01-19-08"
echo "       → 1344_rtraw_default_Cs137_2026-02-23_03-17-27"
run_cmd rmdir "$BASE/RUN1344/1344_rtraw_default_Cs137_2026-02-23_03-17-27"
run_cmd mv   "$BASE/RUN1344/1344_rtraw_default_2026-02-21_01-19-08" "$BASE/RUN1344/1344_rtraw_default_Cs137_2026-02-23_03-17-27"

echo "  [RUN1344] 1344_rtraw_run1344_2026-02-21_01-36-53"
echo "       → 1344_rtraw_run1344_Cs137_2026-02-23_03-17-30"
run_cmd rmdir "$BASE/RUN1344/1344_rtraw_run1344_Cs137_2026-02-23_03-17-30"
run_cmd mv   "$BASE/RUN1344/1344_rtraw_run1344_2026-02-21_01-36-53" "$BASE/RUN1344/1344_rtraw_run1344_Cs137_2026-02-23_03-17-30"

# ==================================================
# RUN1345
# ==================================================
echo "  [RUN1345] 1345_esd_noradialcut_pesumbasic_2026-02-21_01-38-27"
echo "       → 1345_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-18-02"
run_cmd rmdir "$BASE/RUN1345/1345_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-18-02"
run_cmd mv   "$BASE/RUN1345/1345_esd_noradialcut_pesumbasic_2026-02-21_01-38-27" "$BASE/RUN1345/1345_esd_noradialcut_pesumbasic_nosource_2026-02-23_03-18-02"

echo "  [RUN1345] 1345_esd_noradialcut_pesumg_2026-02-21_01-38-25"
echo "       → 1345_esd_noradialcut_pesumg_nosource_2026-02-23_03-18-01"
run_cmd rmdir "$BASE/RUN1345/1345_esd_noradialcut_pesumg_nosource_2026-02-23_03-18-01"
run_cmd mv   "$BASE/RUN1345/1345_esd_noradialcut_pesumg_2026-02-21_01-38-25" "$BASE/RUN1345/1345_esd_noradialcut_pesumg_nosource_2026-02-23_03-18-01"

echo "  [RUN1345] 1345_esd_rcut150_pesumbasic_2026-02-21_01-38-26"
echo "       → 1345_esd_rcut150_pesumbasic_nosource_2026-02-23_03-18-02"
run_cmd rmdir "$BASE/RUN1345/1345_esd_rcut150_pesumbasic_nosource_2026-02-23_03-18-02"
run_cmd mv   "$BASE/RUN1345/1345_esd_rcut150_pesumbasic_2026-02-21_01-38-26" "$BASE/RUN1345/1345_esd_rcut150_pesumbasic_nosource_2026-02-23_03-18-02"

echo "  [RUN1345] 1345_esd_rcut150_pesumg_2026-02-21_01-38-24"
echo "       → 1345_esd_rcut150_pesumg_nosource_2026-02-23_03-18-01"
run_cmd rmdir "$BASE/RUN1345/1345_esd_rcut150_pesumg_nosource_2026-02-23_03-18-01"
run_cmd mv   "$BASE/RUN1345/1345_esd_rcut150_pesumg_2026-02-21_01-38-24" "$BASE/RUN1345/1345_esd_rcut150_pesumg_nosource_2026-02-23_03-18-01"

echo "  [RUN1345] 1345_rtraw_default_2026-02-21_01-38-55"
echo "       → 1345_rtraw_default_nosource_2026-02-23_03-18-00"
run_cmd rmdir "$BASE/RUN1345/1345_rtraw_default_nosource_2026-02-23_03-18-00"
run_cmd mv   "$BASE/RUN1345/1345_rtraw_default_2026-02-21_01-38-55" "$BASE/RUN1345/1345_rtraw_default_nosource_2026-02-23_03-18-00"

echo "  [RUN1345] 1345_rtraw_run1345_2026-02-22_01-25-16"
echo "       → 1345_rtraw_run1345_nosource_2026-02-23_03-18-00"
run_cmd rmdir "$BASE/RUN1345/1345_rtraw_run1345_nosource_2026-02-23_03-18-00"
run_cmd mv   "$BASE/RUN1345/1345_rtraw_run1345_2026-02-22_01-25-16" "$BASE/RUN1345/1345_rtraw_run1345_nosource_2026-02-23_03-18-00"

echo ""
echo "WARNING: the following full folders had no matching empty counterpart"
echo "         and were left untouched:"
echo "  RUN1112/1112_esd_offsrc_rcut150_pesumbasic_2026-02-20_22-24-25"
echo "  RUN1344/1344_esd_offsrc_rcut150_pesumbasic_2026-02-21_01-37-09"
echo ""
echo "WARNING: the following empty folders had no matching full folder"
echo "         and were left untouched:"
echo "  RUN1112/1112_esd_rcut150_pesumbasic_Cs137_2026-02-23_03-17-20"
echo "  RUN1344/1344_esd_rcut150_pesumbasic_Cs137_2026-02-23_03-17-42"

echo ""
echo "Done."
