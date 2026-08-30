#!/usr/bin/env bash
# R0 addendum: repetitions 2 and 3 of the realistic-regime P0b cells
# (G0-preregistration.md: "t_bench = mean of 3 repetitions"; rep 1 came from
# r0-campaign.sh step 7). Guarded like every campaign; runs on delphi-3bda
# after r0-campaign.sh, while the machine is still quiet.
# Marker values: ok / guard-stop / check-output / aborted.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/router
LOG=$EXEC/logs/r0-bench-reps.log
MARKER=$EXEC/logs/r0-bench-reps.done
BENCH=/tmp/bench_router_kernel
MB=$OUT/p0b-microbench.txt
mkdir -p "$OUT" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== r0-bench-reps start $(date -u +%FT%TZ) ==="
trap '[ -e "$MARKER" ] || { campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

source "$EXEC/lib-guard.sh"
if [ ! -x "$BENCH" ]; then
  # Recompile if the campaign's binary is gone (e.g. /tmp cleaned).
  g++ -O3 -std=c++17 -mavx512f -mavx512bw -mavx512vl -mavx512dq -mavx512bf16 \
      -mavx2 -mfma -mamx-tile -mamx-bf16 -pthread \
      -o "$BENCH" ~/workspace/intel-AMX/router/bench_router_kernel.cpp \
    || { echo "bench compile failed"; echo check-output >"$MARKER"; exit 1; }
fi
sha256sum "$BENCH"
if ! campaign_guard_acquire; then echo guard-stop >"$MARKER"; exit 1; fi

FAIL=0
# The campaign's amx n=32 workers=4 split point was correctly refused
# (8 cols/worker < the 16-col AMX tile granularity); measure workers=2 instead.
{
  echo "# amx n=32 multi-core split point retake (workers=2), $(date -u +%FT%TZ)"
  "$BENCH" --arm amx_bf16 --n 32 --m 8 --regime cyclic --layers 24 \
    --workers 2 --worker-cpus 96,98 --seconds 2 \
    || { echo "RUN-FAILED multicore-retake amx n=32 m=8 w=2"; FAIL=1; }
} >>"$MB"
for rep in 2 3; do
  if ci_took_dut; then
    echo "CI took the DUT at rep $rep - stopping"
    campaign_guard_release; echo guard-stop >"$MARKER"; exit 1
  fi
  {
    echo "# P0b realistic-regime repetition $rep, cpu 96, $(date -u +%FT%TZ)"
    for arm in avx_fp32 avx_bf16 amx_bf16; do
      for pair in "32 24" "128 36"; do
        set -- $pair; n=$1; layers=$2
        for m in 1 2 4 8 16; do
          for regime in cyclic disrupted; do
            taskset -c 96 "$BENCH" --arm "$arm" --n "$n" --m "$m" \
              --regime "$regime" --layers "$layers" --disruptor-cpus 98 \
              --seconds 2 \
              || { echo "RUN-FAILED rep=$rep arm=$arm n=$n m=$m regime=$regime"; FAIL=1; }
          done
        done
      done
    done
  } >>"$MB"
done

campaign_guard_release
if [ "$FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== r0-bench-reps done $(date -u +%FT%TZ) ==="
