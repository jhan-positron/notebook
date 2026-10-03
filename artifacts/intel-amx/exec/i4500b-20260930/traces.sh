#!/usr/bin/env bash
# i4500b-20260930 traces (runs ON delphi-3bda, our half): Perfetto traces of runtron decode passes, three binaries that
# share the merge base c7844ca2ce (none has PR #4191): base = main c7844ca2ce (runtron.main0916, row-major K, AMX on),
# fix = f34b0fe2ec (runtron.fix of build step A0: the row-major tail block, converted at the forward end), fixS1 =
# 452b2052c9 (runtron.fixS1 of build step A: blocks completed under hardware attention stay row-major). Cells: qwen-3-4b
# tp2 with 2 users and tp4 with 4 users, prompt 1024, 40 generated tokens, FPGA attention, decode passes 10 and later
# (the block-completing steps 16 and 32 are inside), categories model + scheduler + hwattention (the fix's
# "convert_k_blocks" span is in "model"). Recipe of exec/issue4500-20260918/campaign.sh block m3 (rt_run).
# Outputs: exec/results/i4500b-20260930/traces/<arm>__tp<N>__<U>u.perfetto-trace, traces/rt-results.txt, rt/<name>.log;
# marker traces/traces.done. Analysis on claude-box: exec/issue4500-20260918/trace_analyze.py TRACE_DIR.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500b-20260930
RES=$EXEC/results/i4500b-20260930
TR=$RES/traces
LOCAL=/var/tmp/jhan/traces/i4500b-20260930
HPFILE=/dev/hugepages/amx-i4500b-trace
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
BIN_base=${BIN_base:-/var/tmp/jhan/tron-main0916/gen/runtron.main0916}
BIN_fix=${BIN_fix:-/var/tmp/jhan/tron-i4500/gen/runtron.fix}
BIN_fixS1=${BIN_fixS1:-/var/tmp/jhan/tron-i4500b/gen/runtron.fixS1}
TRACE_ARMS=${TRACE_ARMS:-"base fix fixS1"}
CATS='-*,+model,+scheduler,+hwattention'
GEN=${GEN:-40}; PASSES=${PASSES:-"10-"}
OUR_RT_RE='runtron[.a-z0-9A-Z]* .*--hugepage_file /dev/hugepages/amx-i4500b-trace'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
source "$EXEC/lib-guard.sh"
source "$C/lib.sh"
mkdir -p "$TR" "$RES/rt" "$LOCAL"
exec >>"$RES/traces.log" 2>&1
rm -f "$TR/traces.done"; gaveup=0
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
  esac
}
model_of() { case $1 in 2) echo "$QWEN2" ;; 4) echo "$QWEN4" ;; esac; }
arm_bin() { local v="BIN_$1"; echo "${!v:-}"; }
kill_ours() { pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; return 0; }
trap 'stop_watcher; kill_ours; remove_our_hugepage_files "$HPFILE"; campaign_guard_release 2>/dev/null' EXIT
echo "=== i4500b traces started $(ts) pid $$ arms=[$TRACE_ARMS] gen=$GEN passes=$PASSES cats=$CATS ==="
for arm in $TRACE_ARMS; do b=$(arm_bin "$arm"); [ -x "$b" ] && echo "$(ts) $arm = $b sha256 $(sha256sum "$b" | cut -c1-16)" || echo "$(ts) WARNING $arm binary missing: $b"; done
for tp_users in "2 2" "4 4"; do
  set -- $tp_users; tp=$1; users=$2; model=$(model_of "$tp")
  for arm in $TRACE_ARMS; do
    bin=$(arm_bin "$arm"); [ -x "$bin" ] || { echo "TRACE-FAILED arm=$arm: $bin missing" >>"$TR/rt-results.txt"; gaveup=1; continue; }
    name="${arm}__tp${tp}__${users}u"; tracef=$LOCAL/$name.perfetto-trace; rlog=$RES/rt/$name.log; stops=0
    while :; do
      [ -s "$TR/$name.perfetto-trace" ] && { echo "$(ts) trace $name already done"; break; }
      NEED_HUGEPAGES=$([ "$tp" = 4 ] && echo 256 || echo 128) wait_clear || { echo "$(ts) blocked while waiting; traces give up"; gaveup=1; break 3; }
      take_guard || { echo "$(ts) guard refused; traces give up"; gaveup=1; break 3; }
      status "trace $name"
      echo "### arm=$arm bin=$bin tp=$tp users=$users gen=$GEN passes=$PASSES prompt=1024 $(ts) $(machine_line)" >>"$TR/rt-results.txt"
      rm -f "$tracef" "$RES/traces.STOPPED"; watch_run "$RES/traces.STOPPED" "$OUR_RT_RE" "$HPFILE" & WPID=$!
      (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN -u TRON_HWATTN_EARLY_LAUNCH_MIN_B TRON_LOG_LEVEL=info TRON_TRACE_CATEGORIES="$CATS" \
          timeout -k 60 1200 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o \
          --prompt-length 1024 -l "$GEN" -u "$users" --dont-stop --trace-gen "$tracef" --trace-passes "$PASSES") >"$rlog" 2>&1
      rc=$?
      stop_watcher; campaign_guard_release; remove_our_hugepage_files "$HPFILE"
      res=$(grep -E "Version:|HW attention (enabled|disabled)|average tok/s|Tracing session|perfetto" "$rlog" 2>/dev/null | cut -c1-240 | tr '\n' ' ')
      echo "trace $name rc=$rc $res" >>"$TR/rt-results.txt"
      if [ -e "$RES/traces.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ] || [ $rc -eq 124 ]; then
        echo "TRACE-STOPPED $name rc=$rc $(cat "$RES/traces.STOPPED" 2>/dev/null)" >>"$TR/rt-results.txt"
        stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "TRACE-GIVEN-UP $name" >>"$TR/rt-results.txt"; gaveup=1; break; }
        sleep 120; continue
      fi
      if [ $rc -eq 0 ] && [ -s "$tracef" ]; then cp "$tracef" "$TR/$name.perfetto-trace"; echo "trace_bytes=$(stat -c %s "$tracef") -> $TR/$name.perfetto-trace" >>"$TR/rt-results.txt"
      else echo "TRACE-FAILED $name rc=$rc (see $rlog)" >>"$TR/rt-results.txt"; gaveup=1; fi
      break
    done
  done
done
missing=0; for tp_users in "2 2" "4 4"; do set -- $tp_users; for arm in $TRACE_ARMS; do [ -s "$TR/${arm}__tp$1__$2u.perfetto-trace" ] || missing=$((missing + 1)); done; done
if [ $missing -eq 0 ] && [ $gaveup -eq 0 ]; then echo done >"$TR/traces.done"; else echo "incomplete ($missing traces missing, gaveup=$gaveup)" >"$TR/traces.done"; fi
status "traces finished: $(cat "$TR/traces.done")"
echo "=== i4500b traces finished $(ts) ==="
