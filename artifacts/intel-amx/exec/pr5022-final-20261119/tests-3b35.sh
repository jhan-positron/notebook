#!/usr/bin/env bash
# pr5022-final-20261119 tests. Runs ON delphi-3b35 after build-3b35.sh TAG=final. Pass or fail runs only, no benchmark.
# The three test binaries link the fake device (a software stand-in for the FPGA cards), so no card is opened and no
# huge page is taken (pos_heap_setup is called only by the real driver, src/pos/driver.cpp). Everything is pinned to
# our CPUs 96-143 at low priority, with SYSTEM_CONFIG="--instance 1,2" (our half), as jhan's rule for this machine says.
#
# Runs, each into its own log under exec/results/pr5022-final-20261119/tests/:
#   numerics            gen/t_amx_numerics                      AMX on: every case, with per-section durations
#   numerics-junit      the same run as a JUnit report
#   numerics-<section>  one run per kernel section, so each section reports its own assertion count
#   numerics-off        TRON_AMX_DISABLE=1: the QK and PV cases must be reported as skipped, exit code 0
#   numerics-off-kv     TRON_AMX_DISABLE=1 with the tag filter [kv_data]: every selected case skips, exit code 4
#   dispatch            gen/t_amx_dispatch_dtype                CPU fakes, with per-section durations
#   dispatch-off        the same under TRON_AMX_DISABLE=1 (the fakes ignore it; the counts must not change)
#   llama               gen/t_llama_unit                        AMX on
#   llama-off           gen/t_llama_unit under TRON_AMX_DISABLE=1
#   ctest-props         the CTest registration of t_amx_numerics (SKIP_RETURN_CODE and labels)
# Usage (on 3b35): bash tests-3b35.sh
# Log: exec/logs/pr5022-final-20261119-tests.log. Marker: exec/results/pr5022-final-20261119/tests.done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-final-20261119
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-tests.log
WT=/var/tmp/jhan/b35-pr5022-final
OUR_CPUS=96-143
mkdir -p "$RES/tests" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
rm -f "$RES/tests.done"
echo "=== tests started $(ts) pid $$ on $(hostname) ==="
[ "$(cat "$RES/build-final.done" 2>/dev/null)" = ok ] || { echo "build-final.done is not ok"; echo "failed: no build" >"$RES/tests.done"; exit 1; }
TREE=$(git -C "$WT" write-tree)
[ "$TREE" = "$(cat "$RES/tree.txt")" ] || { echo "tree hash changed: $TREE"; echo "failed: tree hash" >"$RES/tests.done"; exit 1; }
fails=0
: >"$RES/tests.txt"
{
  echo "# host $(hostname), $(date '+%F %T %Z'); build tree $WT; git tree hash $TREE"
  echo "# cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //'); AMX flags in /proc/cpuinfo: $(grep -m1 '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^amx' | tr '\n' ' ')"
  echo "# every run: nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG=\"--instance 1,2\" <env> timeout -k 60 3600 <binary> <args>"
  echo "# label | exit code (wanted) | assertions | summary line | command"
} >>"$RES/tests.txt"
assertions() {
  local n
  n=$(grep -oE 'All tests passed \([0-9]+ assertions' "$1" | grep -oE '[0-9]+' | head -1)
  [ -n "$n" ] || n=$(grep -oE '^assertions: *[0-9]+' "$1" | grep -oE '[0-9]+' | head -1)
  echo "${n:--}"
}
summary() { grep -E 'All tests passed|^test cases:|^assertions:' "$1" | tr '\n' ' ' | tr -s ' ' | cut -c1-260; }
# run <label> <wanted exit code> <extra env or ""> <binary> [args...]
run() {
  local label=$1 want=$2 extra=$3 bin=$4; shift 4
  local out=$RES/tests/$label.log rc
  echo "$(ts) run $label: $bin $* env=[$extra]"
  ( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" env SYSTEM_CONFIG="--instance 1,2" $extra timeout -k 60 3600 "gen/$bin" "$@" ) >"$out" 2>&1
  rc=$?
  echo "$label | $rc ($want) | $(assertions "$out") | $(summary "$out") | $extra gen/$bin $(printf '%q ' "$@")" >>"$RES/tests.txt"
  echo "$(ts) run $label: rc=$rc (wanted $want)"
  [ "$rc" -eq "$want" ] || fails=$((fails + 1))
}
QK='AMX QK does not digress from the AVX dotter'
PV='AMX PV stays inside the AVX weight-rounding envelope'
TR='AMX QK transpose writes the group_heads score rows'
run numerics 0 "" t_amx_numerics --skip-benchmarks --durations yes
run numerics-junit 0 "" t_amx_numerics --skip-benchmarks -r junit -o "$RES/tests/t_amx_numerics.junit.xml"
run numerics-qk4 0 "" t_amx_numerics "$QK" -c "4 heads: rows 0..3 match the dotter, rows 4..15 untouched"
run numerics-qk16 0 "" t_amx_numerics "$QK" -c "16 heads: all 16 rows match the dotter"
run numerics-pv4 0 "" t_amx_numerics "$PV" -c "4 heads: rows 0..3 in the envelope, rows 4..15 zero"
run numerics-pv16 0 "" t_amx_numerics "$PV" -c "16 heads"
run numerics-tr4 0 "" t_amx_numerics "$TR" -c "4 heads: rows 0..3 written, rows 4..15 untouched"
run numerics-tr16 0 "" t_amx_numerics "$TR" -c "16 heads: all 16 rows written"
run numerics-off 0 "TRON_AMX_DISABLE=1" t_amx_numerics --skip-benchmarks
run numerics-off-kv 4 "TRON_AMX_DISABLE=1" t_amx_numerics "[kv_data]"
run dispatch 0 "" t_amx_dispatch_dtype --skip-benchmarks --durations yes
run dispatch-off 0 "TRON_AMX_DISABLE=1" t_amx_dispatch_dtype --skip-benchmarks
run llama 0 "" t_llama_unit --skip-benchmarks
run llama-off 0 "TRON_AMX_DISABLE=1" t_llama_unit --skip-benchmarks
# the kill switch must really have skipped the two kernel cases
skips=$(grep -c 'AMX unavailable' "$RES/tests/numerics-off.log" || true)
echo "numerics-off: 'AMX unavailable' skip lines = $skips (wanted 2)" >>"$RES/tests.txt"
[ "${skips:-0}" -eq 2 ] || fails=$((fails + 1))
# CTest registration (I26): SKIP_RETURN_CODE 4 and the skip_return_code_4 label
( cd "$WT" && ctest --test-dir gen -R '^t_amx_numerics$' --show-only=json-v1 ) >"$RES/tests/ctest-props.json" 2>"$RES/tests/ctest-props.err"
python3 - "$RES/tests/ctest-props.json" >>"$RES/tests.txt" 2>&1 <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    for t in d.get('tests', []):
        props = {p['name']: p['value'] for p in t.get('properties', [])}
        print(f"ctest {t['name']}: SKIP_RETURN_CODE={props.get('SKIP_RETURN_CODE')} LABELS={props.get('LABELS')}")
    if not d.get('tests'): print('ctest: no test matched t_amx_numerics')
except Exception as e:
    print('ctest properties not readable:', e)
EOF
cat "$RES/tests.txt"
if [ "$fails" -eq 0 ]; then echo ok >"$RES/tests.done"; else echo "failed-$fails" >"$RES/tests.done"; fi
echo "=== tests finished $(ts): $(cat "$RES/tests.done") ==="
