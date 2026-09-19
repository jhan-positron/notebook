#!/usr/bin/env bash
# vnnik-trace-20260914: Perfetto traces of the "Save K" span (TRACE_EVENT in
# model.hpp save_k_impl) for the base and the vnni binary at tp2 and tp4, prompt
# 1024, 8 users, on OUR half of delphi-3bda. Answers Monday report section 7.1:
# how long the K store takes on the main thread and how long the attention
# workers wait for it.
#
# Words used here: tron = the inference program under test; runtron = its
# command-line tool; AMX = the Intel matrix instruction set; VNNI layout = the
# pair-interleaved K layout the vnni binary stores K in; Perfetto = the trace
# recorder built into tron (in-process backend, one file per run).
#
# Arms (CPU attention, USE_HW_ATTN=0, AMX on in both):
#   base = runtron.p0perf13 (commit 544ca05c7a, row-major K)
#   vnni = runtron.vnnik    (branch tip 5e45ae55ae, VNNI K)
# Optional extra arms via ARMS/ARM_<name>_BIN/ARM_<name>_ENV (for later steps).
#
# Recipe per run: the campaign's placement (exec/vnnik-20260914/campaign.sh), 8
# users, prompt 1024, 32 generated (the trace needs prefill + a few decode
# steps, not 256), --trace-gen FILE --trace-passes 1-16 (8 prefill passes of
# 1024 tokens + 8 decode steps; the window lifts the 5 s in-process cap),
# TRON_TRACE_CATEGORIES="-*,+model,+scheduler" (the spans this measurement reads;
# fewer events = less trace overhead). The untraced TTFT of the same cells is in
# exec/results/vnnik-20260914 for the overhead check.
#
# Outputs: exec/results/vnnik-trace-20260914/{<arm>-tp<N>.perfetto-trace,
# <arm>-tp<N>.log, runs.txt}; log exec/logs/vnnik-trace-20260914.log; marker
# exec/logs/vnnik-trace-20260914.done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=${RES:-$EXEC/results/vnnik-trace-20260914}
LOG=${LOG:-$EXEC/logs/vnnik-trace-20260914.log}
MARKER=${MARKER:-$EXEC/logs/vnnik-trace-20260914.done}
LOCAL=/var/tmp/jhan/traces/$(basename "$RES")
WT=/var/tmp/jhan/tron-vnnik
BASE_WT=/var/tmp/jhan/tron-p0perf13
RT_BASE=$BASE_WT/gen/runtron.p0perf13
RT_VNNI=$WT/gen/runtron.vnnik
OUR_RT_RE='^/var/tmp/jhan/tron-[a-z0-9]+/gen/runtron[.][a-z0-9]+ '
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ARMS=${ARMS:-"base vnni"}
TPS=${TPS:-"2 4"}
PROMPT=${PROMPT:-1024}
GEN=${GEN:-32}
PASSES=${PASSES:-1-16}
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
  case $1 in base) echo "$RT_BASE" ;; vnni) echo "$RT_VNNI" ;; *) return 1 ;; esac
}
arm_env() {  # extra env assignments, space separated
  local v="ARM_${1}_ENV"; echo "${!v:-}"
}
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) bill_procs=$(ps -u 1062305141 -o pid= 2>/dev/null | wc -l)"; }
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-vnnik*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
take_guard() {
  local n=0
  until campaign_guard_acquire; do
    n=$((n + 1)); echo "$(ts) guard refused ($n); waiting 60 s"; [ $n -ge 60 ] && { echo "$(ts) giving up after 60 refusals"; return 1; }
    sleep 60
  done
  return 0
}

exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== vnnik-trace started $(ts) pid $$ ARMS=[$ARMS] TPS=[$TPS] PROMPT=$PROMPT GEN=$GEN PASSES=$PASSES CATS=$CATS ==="
echo "$(ts) $(machine_line)"
[ -x "$RT_BASE" ] || { echo "$(ts) base binary missing"; echo no-base >"$MARKER"; exit 1; }
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
        timeout 900 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file /dev/hugepages/amx-vnnik -o \
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
echo "=== vnnik-trace finished $(ts): $(cat "$MARKER") ==="
