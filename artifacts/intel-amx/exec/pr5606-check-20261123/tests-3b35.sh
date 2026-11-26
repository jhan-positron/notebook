#!/usr/bin/env bash
# pr5606-check-20261123 tests. Runs ON delphi-3b35 after build-3b35.sh for the same OPT and STATE.
# Pass or fail runs only, no benchmark. The test binaries link the fake device (a software stand-in for the FPGA
# cards), so no card is opened and no huge page is taken. Everything is pinned to our CPUs 96-143 at low priority,
# with SYSTEM_CONFIG="--instance 1,2" (our half). Adapted from exec/pr5022-final-20261119/tests-3b35.sh.
#
# Runs, each into its own log under exec/results/pr5606-check-20261123/tests/<opt>-<state>-<label>.log:
#   dispatch      gen/t_amx_dispatch_dtype   with per-section durations
#   dispatch-off  the same under the kill switch TRON_AMX_DISABLE=1
#   numerics      gen/t_amx_numerics         with per-section durations
#   numerics-off  the same under the kill switch
#   llama         gen/t_llama_unit
#   llama-off     the same under the kill switch
# Usage (on 3b35): OPT=off|on STATE=S0|S1|S2 [TESTS="dispatch numerics llama"] bash tests-3b35.sh
# Record: exec/results/pr5606-check-20261123/tests-<opt>-<state>.txt. Marker: tests-<opt>-<state>.done.
# Log: exec/logs/pr5606-check-20261123-tests-<opt>-<state>.log.
set -u
OPT=${OPT:?OPT=off|on is required}
STATE=${STATE:?STATE=S0|S1|S2 is required}
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
TESTS=${TESTS:-'dispatch numerics llama'}
TAG=$OPT-$STATE
LOG=$LOGDIR/$NAME-tests-$TAG.log
OUT=$RES/tests-$TAG.txt
WT=$(wt_of "$OPT") || { echo "OPT must be off or on"; exit 1; }
SHA=$(sha_of "$STATE") || { echo "STATE must be S0, S1 or S2"; exit 1; }
mkdir -p "$RES/tests" "$LOGDIR"
exec >>"$LOG" 2>&1
only_3b35
rm -f "$RES/tests-$TAG.done"
echo "=== tests $TAG started $(ts) pid $$ on $(hostname) ==="
stop() { echo "$1"; echo "failed: $1" >"$RES/tests-$TAG.done"; exit 1; }
[ "$(cat "$RES/build-$TAG.done" 2>/dev/null)" = ok ] || stop "build-$TAG.done is not ok"
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || stop "$WT is not at $SHA"
[ -z "$(dirty_of "$WT")" ] || stop "$WT has changes outside gen"
fails=0
{
  echo "# host $(hostname), $(date -u '+%F %T UTC'); build tree $WT; state $STATE = commit $SHA; git tree hash $(git -C "$WT" rev-parse 'HEAD^{tree}')"
  echo "# option: $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt")"
  echo "# cpu: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //'); AMX flags in /proc/cpuinfo: $(grep -m1 '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^amx' | tr '\n' ' ')"
  echo "# load average: $(cut -d' ' -f1-3 /proc/loadavg); busy on our CPUs $OUR_CPUS over 2 s: $(busy_pct)"
  echo "# every run: nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG=\"--instance 1,2\" <env> timeout -k 60 3600 <binary> <args>"
  echo "# label | exit code (wanted) | assertions | summary line | sha256 of the binary (first 12) | command"
} >"$OUT"
assertions() {
  local n
  n=$(grep -oE 'All tests passed \([0-9]+ assertions?' "$1" | grep -oE '[0-9]+' | head -1)
  [ -n "$n" ] || n=$(grep -oE '^assertions: *[0-9]+' "$1" | grep -oE '[0-9]+' | head -1)
  echo "${n:--}"
}
summary() { grep -E 'All tests passed|^test cases:|^assertions:' "$1" | tr '\n' ' ' | tr -s ' ' | cut -c1-260; }
# run <label> <wanted exit code> <extra env or ""> <binary> [args...]
run() {
  local label=$1 want=$2 extra=$3 bin=$4; shift 4
  local out=$RES/tests/$TAG-$label.log rc
  echo "$(ts) run $label: $bin $* env=[$extra]"
  # shellcheck disable=SC2086
  ( cd "$WT" >/dev/null 2>&1 && $PIN env SYSTEM_CONFIG="--instance 1,2" $extra timeout -k 60 3600 "gen/$bin" "$@" ) >"$out" 2>&1
  rc=$?
  echo "$label | $rc ($want) | $(assertions "$out") | $(summary "$out") | $(sha256sum "$WT/gen/$bin" | cut -c1-12) | $extra gen/$bin $(printf '%q ' "$@")" >>"$OUT"
  echo "$(ts) run $label: rc=$rc (wanted $want)"
  [ "$rc" -eq "$want" ] || fails=$((fails + 1))
}
for t in $TESTS; do
  case $t in
    dispatch)
      run dispatch 0 "" t_amx_dispatch_dtype --skip-benchmarks --durations yes
      run dispatch-off 0 "TRON_AMX_DISABLE=1" t_amx_dispatch_dtype --skip-benchmarks
      echo "dispatch: test cases listed by --list-tests: $( ( cd "$WT" >/dev/null 2>&1 && $PIN gen/t_amx_dispatch_dtype --list-tests 2>/dev/null ) | grep -E '^[0-9]+ test case' | tr -s ' ' )" >>"$OUT"
      ;;
    numerics)
      run numerics 0 "" t_amx_numerics --skip-benchmarks --durations yes
      run numerics-off 0 "TRON_AMX_DISABLE=1" t_amx_numerics --skip-benchmarks
      echo "numerics-off: 'AMX unavailable' skip lines = $(grep -c 'AMX unavailable' "$RES/tests/$TAG-numerics-off.log" || true)" >>"$OUT"
      ;;
    llama)
      run llama 0 "" t_llama_unit --skip-benchmarks
      run llama-off 0 "TRON_AMX_DISABLE=1" t_llama_unit --skip-benchmarks
      ;;
    *) echo "unknown test $t"; fails=$((fails + 1)) ;;
  esac
done
cat "$OUT"
if [ "$fails" -eq 0 ]; then echo ok >"$RES/tests-$TAG.done"; else echo "failed-$fails" >"$RES/tests-$TAG.done"; fi
echo "=== tests $TAG finished $(ts): $(cat "$RES/tests-$TAG.done") ==="
