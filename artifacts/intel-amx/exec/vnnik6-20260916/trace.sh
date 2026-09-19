#!/usr/bin/env bash
# vnnik6-20260916 traces: Perfetto traces of qwen-3-30b-a3b (kv_mul 8) runs for the arms of
# campaign.sh, prompt 1024, 8 users, tp2 and tp4, on OUR half of delphi-3bda. Fork of
# exec/vnnik-trace-20260914/trace.sh with the model and the arms taken from the environment.
#
# Words used here: Perfetto = the trace recorder built into tron (in-process backend, one file
# per run); pass = one scheduler forward() call (a prefill chunk or one decode step); Save K =
# the span of the main thread's K store per layer; Attention Ready/Pending = the attention
# workers' sections per layer.
#
# Recipe per run: the campaign's placement, 8 users, prompt PROMPT (1024), GEN (32) generated
# tokens, --trace-gen FILE --trace-passes PASSES (1-24: the prefill passes and the first
# decode steps; the window lifts the 5 s in-process cap), TRON_TRACE_CATEGORIES CATS
# ("-*,+model,+scheduler": the spans the analysis reads).
# Arms: ARMS (space separated) with ARM_<arm>_BIN = the binary (and optional ARM_<arm>_ENV).
# Outputs: $RES/{<arm>-tp<N>.perfetto-trace, <arm>-tp<N>.log, runs.txt}; log $LOG; marker
# $MARKER (ok | failed-N | no-binary).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=${RES:-$EXEC/results/vnnik6-trace-20260916}
LOG=${LOG:-$EXEC/logs/vnnik6-trace-20260916.log}
MARKER=${MARKER:-$EXEC/logs/vnnik6-trace-20260916.done}
LOCAL=/var/tmp/jhan/traces/$(basename "$RES")
OUR_RT_RE='^/var/tmp/jhan/tron-[a-z0-9]+/gen/runtron[.][a-z0-9]+ '
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ARMS=${ARMS:-"base headoff vnni"}
TPS=${TPS:-"2 4"}
PROMPT=${PROMPT:-1024}
GEN=${GEN:-32}
PASSES=${PASSES:-1-24}
CATS=${CATS:-"-*,+model,+scheduler"}
MODEL2=${MODEL2:-ingested-qwen-3-30b-a3b-instruct-2507-tp2}
MODEL4=${MODEL4:-ingested-qwen-3-30b-a3b-instruct-2507-tp4}
HPFILE=/dev/hugepages/amx-vnnik6
ARM_base_BIN=${ARM_base_BIN:-/var/tmp/jhan/tron-main0916/gen/runtron.main0916}
ARM_headoff_BIN=${ARM_headoff_BIN:-/var/tmp/jhan/tron-headoff0916/gen/runtron.headoff0916}
ARM_vnni_BIN=${ARM_vnni_BIN:-/var/tmp/jhan/tron-vnnik5/gen/runtron.vnnik5}
mkdir -p "$RES" "$LOCAL" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
  esac
}
arm_bin() { local v="ARM_${1}_BIN"; echo "${!v:-}"; }
arm_env() { local v="ARM_${1}_ENV"; echo "${!v:-}"; }
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
    # the nightly's leftover rinzler@N units: stop them once idle (lib-guard.sh recipe)
    rinzler_active && { rinzler_takeover_if_idle; echo "$GUARD_TAKEOVER_LAST" >"$RES/takeover.last"; }   # the parent campaign reads the stop time back
    sleep 60
  done
  return 0
}

exec >>"$LOG" 2>&1
rm -f "$MARKER" "$RES/takeover.last"
echo "=== vnnik6-trace started $(ts) pid $$ ARMS=[$ARMS] TPS=[$TPS] PROMPT=$PROMPT GEN=$GEN PASSES=$PASSES CATS=$CATS ==="
echo "$(ts) $(machine_line)"
for arm in $ARMS; do bin=$(arm_bin "$arm"); [ -x "$bin" ] || { echo "$(ts) binary of arm $arm missing: $bin"; echo no-binary >"$MARKER"; exit 1; }; done
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
fails=0
for tp in $TPS; do
  case $tp in 2) model=$MODEL2 ;; 4) model=$MODEL4 ;; *) echo "$(ts) unknown tp $tp"; fails=$((fails+1)); continue ;; esac
  for arm in $ARMS; do
    bin=$(arm_bin "$arm"); envv=$(arm_env "$arm")
    name=${arm}-tp${tp}
    [ -s "$RES/$name.perfetto-trace" ] && grep -q "average tok/s" "$RES/$name.log" 2>/dev/null && { echo "$(ts) $name already done"; continue; }
    take_guard || { fails=$((fails+1)); break 2; }
    echo "### trace arm=$arm tp=$tp bin=$bin env=${envv:-none} model=$model prompt=$PROMPT gen=$GEN users=8 passes=$PASSES cats=$CATS $(ts) $(machine_line)" | tee -a "$RES/runs.txt"
    tracef=$LOCAL/$name.perfetto-trace
    rm -f "$tracef"
    ( cd "$(dirname "$(dirname "$bin")")" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && \
      env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=info TRON_TRACE_CATEGORIES="$CATS" ${envv:+env $envv} \
        timeout -k 60 900 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o \
        --prompt-length "$PROMPT" -l "$GEN" -u 8 --trace-gen "$tracef" --trace-passes "$PASSES" ) >"$RES/$name.log" 2>&1
    rc=$?
    campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s|perfetto|trace" "$RES/$name.log" | grep -v "^\s*$" | head -30)
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res" || [ ! -s "$tracef" ]; then
      echo "RUN-FAILED $name rc=$rc trace_bytes=$(stat -c %s "$tracef" 2>/dev/null || echo 0)" | tee -a "$RES/runs.txt"; fails=$((fails+1))
    else
      cp "$tracef" "$RES/$name.perfetto-trace"
      echo "ok $name rc=$rc trace_bytes=$(stat -c %s "$tracef") $(sed -n 's/.*Parsing the prompt took \([0-9.]*\) s.*/\1/p' "$RES/$name.log" | sort -n | tail -1 | sed 's/^/ttft_max_s=/')" | tee -a "$RES/runs.txt"
    fi
    printf '%s\n' "$res" >>"$RES/runs.txt"
    sleep 5
  done
done
remove_our_slice_files
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")" >"$MARKER"
echo "=== vnnik6-trace finished $(ts): $(cat "$MARKER") ==="
