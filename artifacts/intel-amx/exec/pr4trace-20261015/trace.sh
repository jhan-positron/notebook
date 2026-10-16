#!/usr/bin/env bash
# pr4trace-20261015: Perfetto trace of the "convert_k_blocks" span (TRACE_EVENT
# in model.hpp convert_pending_k_blocks, PR #4901) for runtron.pr4 at tp2 and
# tp4, CPU attention, prompt 1024, 8 users, 64 generated tokens, on OUR half of
# delphi-3bda. Answers the PR body's open item "The conversion ... its serial
# main-thread cost ... is not measured".
#
# Words used here: tron = the inference program under test; runtron = its
# command-line tool; Perfetto = the trace recorder built into tron (in-process
# backend, one file per run); pass = one forward computation; block = 16
# consecutive tokens of a KV page.
#
# Arm: new = runtron.pr4 (commit ea94e95a4e, TRON_K_VNNI=ON, TRON_AMX_DISPATCH=ON).
# Prompt 1024 = exactly 64 full blocks, so decode completes a block at generated
# tokens 16, 32, 48 and 64 (passes 24, 40, 56, 72 with 8 prefill passes first).
#
# Recipe: a copy of exec/vnnik-trace-20260914/trace.sh with the arm, the
# generated-token count (64) and the pass window (1-72) changed.
# TRON_TRACE_CATEGORIES="-*,+model,+scheduler" keeps the trace small.
#
# Outputs: exec/results/pr4trace-20261015/{new-tp<N>.perfetto-trace, new-tp<N>.log,
# runs.txt}; log exec/logs/pr4trace-20261015.log; marker exec/logs/pr4trace-20261015.done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=${RES:-$EXEC/results/pr4trace-20261015}
LOG=${LOG:-$EXEC/logs/pr4trace-20261015.log}
MARKER=${MARKER:-$EXEC/logs/pr4trace-20261015.done}
LOCAL=/var/tmp/jhan/traces/$(basename "$RES")
WT=/var/tmp/jhan/tron-pr4
RT_NEW=$WT/gen/runtron.pr4
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ARMS=${ARMS:-"new"}
TPS=${TPS:-"2 4"}
PROMPT=${PROMPT:-1024}
GEN=${GEN:-64}
PASSES=${PASSES:-1-72}
CATS=${CATS:-"-*,+model,+scheduler"}
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
mkdir -p "$RES" "$LOCAL" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
  esac
}
arm_bin() {
  local v="ARM_${1}_BIN"; if [ -n "${!v:-}" ]; then echo "${!v}"; return; fi
  case $1 in new) echo "$RT_NEW" ;; *) return 1 ;; esac
}
arm_env() { local v="ARM_${1}_ENV"; echo "${!v:-}"; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) bill_procs=$(ps -u 1062305141 -o pid= 2>/dev/null | wc -l)"; }
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-pr4trace*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
take_guard() {
  local n=0
  until campaign_guard_acquire; do
    n=$((n + 1)); [ $((n % 30)) -eq 1 ] && echo "$(ts) guard refused ($n); polling every 10 s"; [ $n -ge 1800 ] && { echo "$(ts) giving up after 1800 refusals (5 h)"; return 1; }
    sleep 10
  done
  return 0
}

exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== pr4trace started $(ts) pid $$ ARMS=[$ARMS] TPS=[$TPS] PROMPT=$PROMPT GEN=$GEN PASSES=$PASSES CATS=$CATS ==="
echo "$(ts) $(machine_line) binary=$(git -C "$WT" rev-parse --short HEAD) $(sha256sum "$RT_NEW" | cut -c1-16)"
[ -x "$RT_NEW" ] || { echo "$(ts) new binary missing"; echo no-new >"$MARKER"; exit 1; }
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
fails=0
for tp in $TPS; do
  case $tp in 2) model=$QWEN2 ;; 4) model=$QWEN4 ;; esac
  for arm in $ARMS; do
    bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; fails=$((fails+1)); continue; }
    envv=$(arm_env "$arm")
    name=${arm}-tp${tp}
    [ -s "$RES/$name.perfetto-trace" ] && grep -q "average tok/s" "$RES/$name.log" 2>/dev/null && { echo "$(ts) $name already done"; continue; }
    take_guard || { fails=$((fails+1)); break 2; }
    echo "### trace arm=$arm tp=$tp bin=$bin env=${envv:-none} prompt=$PROMPT gen=$GEN users=8 passes=$PASSES cats=$CATS $(ts) $(machine_line)" | tee -a "$RES/runs.txt"
    tracef=$LOCAL/$name.perfetto-trace
    rm -f "$tracef"
    ( cd "$(dirname "$(dirname "$bin")")" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && \
      env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=info TRON_TRACE_CATEGORIES="$CATS" ${envv:+env $envv} \
        timeout 900 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file /dev/hugepages/amx-pr4trace -o \
        --prompt-length "$PROMPT" -l "$GEN" -u 8 --trace-gen "$tracef" --trace-passes "$PASSES" ) >"$RES/$name.log" 2>&1
    rc=$?
    campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s|perfetto|trace" "$RES/$name.log" | grep -v "^\s*$" | head -30)
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res" || [ ! -s "$tracef" ]; then
      echo "RUN-FAILED $name rc=$rc trace_bytes=$(stat -c %s "$tracef" 2>/dev/null || echo 0)" | tee -a "$RES/runs.txt"; fails=$((fails+1))
    else
      cp "$tracef" "$RES/$name.perfetto-trace"
      echo "ok $name rc=$rc trace_bytes=$(stat -c %s "$tracef") $(grep -E 'Parsing the prompt took' "$RES/$name.log" | awk '{print $(NF-3)}' | sort -n | tail -1 | sed 's/^/ttft_max_s=/')" | tee -a "$RES/runs.txt"
    fi
    printf '%s\n' "$res" >>"$RES/runs.txt"
    sleep 5
  done
done
remove_our_slice_files
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")" >"$MARKER"
echo "=== pr4trace finished $(ts): $(cat "$MARKER") ==="
