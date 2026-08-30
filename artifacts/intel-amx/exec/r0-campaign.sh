#!/usr/bin/env bash
# R0 guarded measurement slot: router P0 per router/02-option-c-plan.md sec 3.
#   P0b - standalone router-kernel microbench (validate, single-core sweep,
#         one multi-core split point, license-clock via turbostat), then
#   P0a - runtron trace captures on ingested-gpt-oss-20b-tp2 in PRODUCTION
#         hardware-attention mode (USE_HW_ATTN deliberately NOT set - unlike
#         the attention campaigns), plus a gpt-oss-120b runnability check.
# Serving policy (p2-ci-models precedent): rinzler active WITH traffic ->
# serving-busy and exit; idle 10 min -> stop it. NEVER restarted here
# (project policy: hand-back is not ours).
# Marker values: ok / guard-stop / serving-busy / build-missing / check-output
# / aborted (unexpected termination; written by the EXIT trap).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-campaign.log
MARKER=$EXEC/logs/r0-campaign.done
TRON=~/workspace/tron-router-p0
RT=$TRON/gen/runtron
BENCH=/tmp/bench_router_kernel
BSRC=~/workspace/intel-AMX/router/bench_router_kernel.cpp
MB=$OUT/p0b-microbench.txt
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-campaign start $(date -u +%FT%TZ) ==="
SWEEP_FAIL=0
CAP_FAIL=0

# Every intended path writes $MARKER before exiting; if we die without one
# (SIGTERM, set -u abort), still clean our hugepage file, release the guard
# (no-op when not held), and leave an 'aborted' marker.
trap '[ -e "$MARKER" ] || { rm -f /dev/hugepages/amx-r0* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

# Release the guard, remove our hugepage file, write the marker, exit.
stop_partial() { # $1 = marker value, $2 = message
  echo "$2"
  rm -f /dev/hugepages/amx-r0* 2>/dev/null
  campaign_guard_release
  echo "$1" >"$MARKER"
  exit 1
}

# --- 2. binary presence + header ---------------------------------------------
if [ ! -x "$RT" ]; then
  echo "runtron missing at $RT - run r0-build.sh first"
  echo build-missing >"$MARKER"; exit 1
fi
# The binary must come from a SUCCESSFUL r0-build.sh run: a re-run that failed
# leaves the old binary in place with marker build-failed, and capturing it
# would record the wrong HEAD against markerless traces.
BUILD_DONE=$(cat "$EXEC/logs/r0-build.done" 2>/dev/null || true)
if [ "$BUILD_DONE" != ok ]; then
  echo "r0-build.done is '${BUILD_DONE:-missing}' (need ok) - run r0-build.sh first"
  echo build-missing >"$MARKER"; exit 1
fi
# Bench source must exist BEFORE any destructive action (rinzler stop is
# irreversible by policy) - do not spend the slot if the compile cannot start.
if [ ! -r "$BSRC" ]; then
  echo "bench source missing at $BSRC"
  echo build-missing >"$MARKER"; exit 1
fi
echo "host=$(hostname) kernel=$(uname -r) date=$(date -u +%FT%TZ)"
echo "worktree=$TRON HEAD=$(git -C "$TRON" rev-parse HEAD)"
sha256sum "$RT"
# bench binary sha256 is recorded at step 5, right after it is compiled

# --- 3. serving handling (p2-ci-models precedent) -----------------------------
source "$EXEC/lib-guard.sh"
# CI lease check BEFORE the destructive part: rinzler stop + hugepage removal
# are allowed only when the lease says CI is NOT holding the DUT (lib-guard.sh
# authority order). journal-idle rinzler during a CI phase is still CI's.
if ci_lease_busy; then
  echo "System CI holds the DUT (lease busy) - not touching serving, not launching"
  echo guard-stop >"$MARKER"; exit 1
fi
if rinzler_active; then
  traffic=$(journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
    | grep -icE 'session|request|prompt|generate|token') || true
  if [ "${traffic:-0}" -gt 0 ]; then
    echo "rinzler serving has traffic ($traffic journal lines in 10 min) - not stopping a live stack"
    echo serving-busy >"$MARKER"; exit 1
  fi
  echo "rinzlers active but zero traffic for 10 min - stopping (no restart afterwards: hand-back is not ours)"
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3
  sleep 5
  for f in /dev/hugepages/slice-*-of-8; do
    [ -e "$f" ] || continue
    if fuser -s "$f" 2>/dev/null; then
      echo "keeping $f (fuser: still open)"
    else
      rm -f "$f"; echo "removed $f (fuser: no open handles)"
    fi
  done
fi

# --- 4. cross-session campaign guard (lease + flock + no-runtron) --------------
if ! campaign_guard_acquire; then echo guard-stop >"$MARKER"; exit 1; fi

# --- 5. compile the bench on 3bda (p0-fused-sweep approach: plain g++) ---------
cd "$TRON" || stop_partial build-missing "cannot cd into $TRON"
g++ -O3 -std=c++17 -mavx512f -mavx512bw -mavx512vl -mavx512dq -mavx512bf16 \
    -mavx2 -mfma -mamx-tile -mamx-bf16 -pthread \
    -o "$BENCH" "$BSRC" \
  || stop_partial check-output "bench compile failed"
sha256sum "$BENCH"

# --- 6. bench validation pass ---------------------------------------------------
echo "--- P0b validation $(date -u +%FT%TZ) ---"
VAL_FAIL=0
for arm in avx_fp32 avx_bf16 amx_bf16; do
  for nm in "32 4" "128 8"; do
    set -- $nm; n=$1; m=$2
    echo "+ taskset -c 96 $BENCH --validate --arm $arm --n $n --m $m --regime l2"
    taskset -c 96 "$BENCH" --validate --arm "$arm" --n "$n" --m "$m" --regime l2 \
      || { echo "VALIDATE-FAILED arm=$arm n=$n m=$m"; VAL_FAIL=1; }
  done
done
[ "$VAL_FAIL" -eq 0 ] || stop_partial check-output "bench validation failed"

# --- 7. P0b single-core sweep (cpu 96) -----------------------------------------
echo "--- P0b sweep $(date -u +%FT%TZ) ---"
{
  echo "# P0b router-kernel microbench, cpu 96, $(date -u +%FT%TZ), bench sha256:"
  sha256sum "$BENCH"
  for arm in avx_fp32 avx_bf16 amx_bf16; do
    for pair in "32 24" "128 36"; do          # (n, layers): 20b, 120b geometry
      set -- $pair; n=$1; layers=$2
      for m in 1 2 4 8 16; do
        for regime in l2 cyclic disrupted; do
          if [ "$regime" = l2 ]; then L=1; else L=$layers; fi
          taskset -c 96 "$BENCH" --arm "$arm" --n "$n" --m "$m" \
            --regime "$regime" --layers "$L" --disruptor-cpus 98 --seconds 2 \
            || { echo "RUN-FAILED arm=$arm n=$n m=$m regime=$regime"; SWEEP_FAIL=1; }
        done
      done
    done
  done
} >>"$MB"

# --- 8. multi-core split point (4 workers over N) -------------------------------
echo "--- P0b multi-core split point $(date -u +%FT%TZ) ---"
{
  echo "# P0b multi-core split point (--workers 4 --worker-cpus 96,98,100,102), $(date -u +%FT%TZ)"
  for arm in avx_fp32 avx_bf16 amx_bf16; do
    for cfg in "128 1 36" "128 8 36" "32 8 24"; do   # (n, m, layers), cyclic
      set -- $cfg; n=$1; m=$2; L=$3
      "$BENCH" --arm "$arm" --n "$n" --m "$m" --regime cyclic --layers "$L" \
        --workers 4 --worker-cpus 96,98,100,102 --seconds 2 \
        || { echo "RUN-FAILED multicore arm=$arm n=$n m=$m"; SWEEP_FAIL=1; }
    done
  done
} >>"$MB"

# --- 9. license-clock: turbostat over a long steady run per arm -----------------
for arm in avx_fp32 avx_bf16 amx_bf16; do
  echo "--- license-clock arm=$arm $(date -u +%FT%TZ) ---"
  echo "+ taskset -c 96 $BENCH --arm $arm --n 128 --m 8 --regime cyclic --layers 36 --seconds 20"
  taskset -c 96 "$BENCH" --arm "$arm" --n 128 --m 8 --regime cyclic --layers 36 \
    --seconds 20 >"$OUT/p0b-freq-$arm-run.txt" 2>&1 &
  bpid=$!
  sleep 2
  if ! sudo -n turbostat --quiet --cpu 96 --show CPU,Avg_MHz,Bzy_MHz,PkgWatt \
        --interval 3 --num_iterations 5 >"$OUT/p0b-freq-$arm.txt" 2>&1; then
    echo "turbostat --cpu failed, falling back to --Summary"
    if ! sudo -n turbostat --quiet --Summary --show Avg_MHz,Bzy_MHz,PkgWatt \
          --interval 3 --num_iterations 5 >"$OUT/p0b-freq-$arm.txt" 2>&1; then
      echo "turbostat unavailable" >"$OUT/p0b-freq-$arm.txt"
    fi
  fi
  wait "$bpid" 2>/dev/null \
    || { echo "RUN-FAILED license-clock steady run arm=$arm"; SWEEP_FAIL=1; }
done

# --- 10. CI re-check before the runtron phase -----------------------------------
if ci_took_dut; then
  stop_partial guard-stop "CI took the DUT after P0b - stopping (P0b results kept)"
fi

# --- 11. P0a runtron captures (production hardware-attention mode) ---------------
# NOTE: do NOT set USE_HW_ATTN - the plan requires production attention mode.
RTARGS="stream-generate-text -m ingested-gpt-oss-20b-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-r0 --nr_hugepages 128 -o"

# 11a. smoke
echo "--- P0a smoke $(date -u +%FT%TZ) ---"
echo "+ timeout 300 ./gen/runtron $RTARGS --prompt-length 2048 -l 16 -u 1"
if ! timeout 300 ./gen/runtron $RTARGS --prompt-length 2048 -l 16 -u 1 \
      >"$OUT/gptoss20b-smoke.txt" 2>&1; then
  tail -20 "$OUT/gptoss20b-smoke.txt"
  stop_partial check-output "P0a smoke run failed"
fi
grep -E "Parsing the prompt took|average tok/s" "$OUT/gptoss20b-smoke.txt" \
  || echo "smoke NO-TIMING"

# 11b. four decode captures (generation-phase trace)
for cfg in "1 2048" "1 8192" "8 2048" "8 8192"; do
  set -- $cfg; U=$1; CTX=$2
  if ci_took_dut; then
    stop_partial guard-stop "CI took the DUT before u=$U ctx=$CTX capture"
  fi
  TRACE=$OUT/gptoss20b-u$U-ctx$CTX-hwattn.perfetto-trace
  echo "### P0a decode capture u=$U ctx=$CTX len=256 $(date -u +%FT%TZ)"
  # 1800 not 900: the 8u/8K cell has no 900 s precedent (p2-8u8k used 1800)
  # and --trace-gen adds overhead.
  echo "+ timeout 1800 ./gen/runtron $RTARGS --trace-gen $TRACE --prompt-length $CTX -l 256 -u $U"
  timeout 1800 ./gen/runtron $RTARGS --trace-gen "$TRACE" \
      --prompt-length "$CTX" -l 256 -u "$U" 2>&1 \
    | tee "$OUT/gptoss20b-u$U-ctx$CTX.txt" \
    | grep -E "Parsing the prompt took|average tok/s"
  PS=("${PIPESTATUS[@]}")   # grep alone must not decide success: the parsing
  if [ "${PS[0]}" -ne 0 ] || [ "${PS[1]}" -ne 0 ]; then  # line prints mid-run
    echo "RUN-FAILED u=$U ctx=$CTX (runtron=${PS[0]} tee=${PS[1]}; 124 = timeout)"
    CAP_FAIL=1
  elif [ "${PS[2]}" -ne 0 ]; then
    echo "NO-TIMING u=$U ctx=$CTX (run exited 0 but no timing lines)"
  fi
done

# 11c. one prefill capture (whole-run trace, NOT --trace-gen)
if ci_took_dut; then
  stop_partial guard-stop "CI took the DUT before the prefill capture"
fi
echo "### P0a prefill capture ctx=8192 $(date -u +%FT%TZ)"
echo "+ timeout 900 ./gen/runtron $RTARGS --trace $OUT/gptoss20b-prefill8k.perfetto-trace --prompt-length 8192 -l 8 -u 1"
timeout 900 ./gen/runtron $RTARGS --trace "$OUT/gptoss20b-prefill8k.perfetto-trace" \
    --prompt-length 8192 -l 8 -u 1 2>&1 \
  | tee "$OUT/gptoss20b-prefill8k.txt" \
  | grep -E "Parsing the prompt took|average tok/s"
PS=("${PIPESTATUS[@]}")
if [ "${PS[0]}" -ne 0 ] || [ "${PS[1]}" -ne 0 ]; then
  echo "RUN-FAILED prefill8k (runtron=${PS[0]} tee=${PS[1]}; 124 = timeout)"
  CAP_FAIL=1
elif [ "${PS[2]}" -ne 0 ]; then
  echo "NO-TIMING prefill8k (run exited 0 but no timing lines)"
fi

# 11d. gpt-oss-120b runnability check (plugin name recorded by r0-build.sh)
if ci_took_dut; then
  stop_partial guard-stop "CI took the DUT before the 120b attempt"
fi
M120=$(grep 'gpt-oss-120b-plugin=' "$EXEC/logs/r0-build.log" 2>/dev/null \
  | tail -1 | cut -d= -f2)
F120=$OUT/gptoss120b-runnability.txt
echo "### P0a 120b runnability check: plugin='${M120:-unrecorded}' $(date -u +%FT%TZ)"
if [ -n "${M120:-}" ] && [ "$M120" != none ]; then
  RTARGS120="stream-generate-text -m $M120 \
    --instance 0,4 --devices 10:00.0,13:00.0 \
    --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
    --numa 0 --hugepage_file /dev/hugepages/amx-r0 --nr_hugepages 128 -o"
  echo "+ timeout 600 ./gen/runtron $RTARGS120 --prompt-length 2048 -l 16 -u 1"
  echo "# gpt-oss-120b runnability attempt: model=$M120, $(date -u +%FT%TZ)" >"$F120"
  if timeout 600 ./gen/runtron $RTARGS120 --prompt-length 2048 -l 16 -u 1 \
        >"$OUT/gptoss120b-attempt-full.txt" 2>&1; then
    echo "RUNNABLE: yes" >>"$F120"
    grep -E "Parsing the prompt took|average tok/s" \
      "$OUT/gptoss120b-attempt-full.txt" >>"$F120" \
      || echo "NO-TIMING (exit 0 but no timing lines)" >>"$F120"
  else
    rc=$?
    # A resource-shaped failure with the 20b config (128 hugepages) is not an
    # honest "not runnable" verdict - retry once with more pages before ruling.
    if grep -qiE 'hugepage|huge page|mmap|alloc|out of memory|ENOMEM|bad_alloc' \
         "$OUT/gptoss120b-attempt-full.txt"; then
      echo "first attempt failed (exit=$rc) with resource-shaped errors - retrying with --nr_hugepages 300" >>"$F120"
      RTARGS120B=${RTARGS120/--hugepage_file \/dev\/hugepages\/amx-r0 --nr_hugepages 128/--hugepage_file /dev/hugepages/amx-r0b --nr_hugepages 300}
      echo "+ timeout 600 ./gen/runtron $RTARGS120B --prompt-length 2048 -l 16 -u 1"
      if timeout 600 ./gen/runtron $RTARGS120B --prompt-length 2048 -l 16 -u 1 \
            >"$OUT/gptoss120b-attempt2-full.txt" 2>&1; then
        echo "RUNNABLE: yes (needed 300 hugepages)" >>"$F120"
        grep -E "Parsing the prompt took|average tok/s" \
          "$OUT/gptoss120b-attempt2-full.txt" >>"$F120" \
          || echo "NO-TIMING (exit 0 but no timing lines)" >>"$F120"
      else
        rc2=$?
        echo "RUNNABLE: no (exit=$rc attempt1/128pg, exit=$rc2 attempt2/300pg; 124 = timeout). Attempt2 tail:" >>"$F120"
        tail -40 "$OUT/gptoss120b-attempt2-full.txt" >>"$F120"
      fi
    else
      echo "RUNNABLE: no (exit=$rc; 124 = timeout; failure not resource-shaped). Output tail:" >>"$F120"
      tail -40 "$OUT/gptoss120b-attempt-full.txt" >>"$F120"
    fi
  fi
  grep RUNNABLE "$F120"
else
  echo "no ingested-gpt-oss-120b* plugin name recorded by r0-build.sh (strings scan) - 120b cannot be attempted with this binary" >"$F120"
  cat "$F120"
fi

# --- 12. cleanup + final marker ---------------------------------------------------
rm -f /dev/hugepages/amx-r0* 2>/dev/null
campaign_guard_release
if [ "$SWEEP_FAIL" -ne 0 ] || [ "$CAP_FAIL" -ne 0 ]; then
  echo check-output >"$MARKER"
else
  echo ok >"$MARKER"
fi
echo "=== r0-campaign done $(date -u +%FT%TZ) ==="
