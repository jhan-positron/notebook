#!/usr/bin/env bash
# pr5606-check-20261123: AMX instruction count and wall times of the dispatch test. Runs ON delphi-3b35.
# Uses our CPUs only (96-143, low priority), SYSTEM_CONFIG="--instance 1,2", the fake device, no FPGA card.
#
# Part 1 (amx-insn-<opt>-<state>.txt): counts the AMX instructions in gen/t_amx_dispatch_dtype with
#   objdump -d --no-show-raw-insn. The six names: tdpbf16ps (bf16 dot product on tiles), tileloadd, tilestored,
#   tilezero, ldtilecfg and tilerelease (tile load, store, clear, configure, release).
# Part 2 (wall-times-<opt>.txt, only with WALL=1): 5 runs of each kept binary gen/t_amx_dispatch_dtype.<state>
#   with /usr/bin/time, in the form of exec/results/pr5022-final-20261119/wall-times.txt. No build may run during
#   this part.
# Usage (on 3b35): OPT=off|on STATE=S2 [WALL=1 WALL_STATES="S0 S2"] bash extras-3b35.sh
set -u
OPT=${OPT:?OPT=off|on is required}
STATE=${STATE:?STATE=S0|S1|S2 is required}
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
WT=$(wt_of "$OPT") || exit 1
SHA=$(sha_of "$STATE") || exit 1
mkdir -p "$RES/tests"
BIN=$WT/gen/t_amx_dispatch_dtype
OUT=$RES/amx-insn-$OPT-$STATE.txt
{
  echo "# AMX instructions in $BIN on $(hostname), $(ts); state $STATE = commit $SHA"
  [ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || echo "WARNING: the tree is at $(git -C "$WT" rev-parse HEAD), not at $SHA"
  echo "# option: $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt"); sha256 of the binary: $(sha256sum "$BIN" | cut -c1-64)"
  echo "# command: objdump -d --no-show-raw-insn gen/t_amx_dispatch_dtype | grep -c -w <name>"
  DIS=$RES/tests/$OPT-$STATE-dispatch.objdump.tmp
  $PIN objdump -d --no-show-raw-insn "$BIN" >"$DIS" 2>/dev/null
  echo "disassembly lines: $(wc -l <"$DIS")"
  total=0
  for m in tdpbf16ps tileloadd tilestored tilezero ldtilecfg tilerelease; do
    n=$(grep -c -w "$m" "$DIS" || true); total=$((total + n)); echo "$m: $n"
  done
  echo "total AMX instructions: $total"
  echo "any mnemonic that starts with 'tile', 'tdp' or 'ldtilecfg'/'sttilecfg': $(awk -F'\t' 'NF>=3{split($3,a," "); print a[1]}' "$DIS" | grep -c -E '^(tile|tdp|ldtilecfg|sttilecfg)' || true)"
  rm -f "$DIS"
} >"$OUT" 2>&1
cat "$OUT"
if [ "${WALL:-0}" = 1 ]; then
  WOUT=$RES/wall-times-$OPT.txt
  TMP=$RES/tests/$OPT-wall.time.tmp
  {
    echo "# wall time and peak resident memory of the dispatch test binaries, option $(echo "$OPT" | tr a-z A-Z) build"
    echo "# host $(hostname), $(ts); load average $(cut -d' ' -f1-3 /proc/loadavg); busy on our CPUs $OUR_CPUS over 2 s: $(busy_pct)"
    echo "# each run: cd $WT; nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG=\"--instance 1,2\" /usr/bin/time -f \"%e s %M KiB\" gen/t_amx_dispatch_dtype.<state>"
    for st in ${WALL_STATES:-S0 S2}; do
      b=gen/t_amx_dispatch_dtype.$st
      [ -x "$WT/$b" ] || { echo "t_amx_dispatch_dtype $st: no kept binary $WT/$b"; continue; }
      echo "# $st binary sha256 $(sha256sum "$WT/$b" | cut -c1-16), $(stat -c %s "$WT/$b") bytes"
      for i in 1 2 3 4 5; do
        ( cd "$WT" >/dev/null 2>&1 && $PIN env SYSTEM_CONFIG="--instance 1,2" /usr/bin/time -f "%e s %M KiB" -o "$TMP" "$b" >/dev/null 2>&1 )
        rc=$?
        echo "t_amx_dispatch_dtype $st run $i: $(tail -1 "$TMP") (exit $rc)"
      done
    done
    rm -f "$TMP"
  } >"$WOUT" 2>&1
  cat "$WOUT"
fi
