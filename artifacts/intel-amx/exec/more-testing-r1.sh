#!/usr/bin/env bash
# more-testing round 1 campaign (jhan request 2026-09-04, input-2-ai/more-testing.md):
# the nightly System CI's tests (functional, perf, MMLU Pro, soak) from
# positron-ai/systems_test against rinzler built from PR3879 (jhan-amx-p0 @
# 60d66d9c04) in three arms (off / canon / mirror) on four models.
# Plan: PR3879/more-testing/test-plan.md. Stage 1 (machine handoff + builds)
# = exec/more-testing-r1-build.sh (marker exec/logs/more-testing-r1-build.done).
# Cells run model-major so each model's arm comparison completes early. Every
# cell is refused when its estimate would cross the 02:30Z deadline (the
# ci-runner-stop timer restores production inference at 02:45Z, CI prep 03:30Z).
set -u
EXEC=~/workspace/intel-AMX/exec
H=$EXEC/more-testing-r1
RES=$EXEC/results/more-testing-r1
LOG=$EXEC/logs/more-testing-r1.log
MARKER=$EXEC/logs/more-testing-r1.done
mkdir -p "$RES/cells" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== campaign start $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"
source "$H/rz.sh"
status() { python3 "$H/gen_status.py" 2>&1 | tail -1; }
trap '[ -e "$MARKER" ] || { rz_stop; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; status; }' EXIT

# Stage 0: builds must be done and the two arms must differ.
if [ "$(cat "$EXEC/logs/more-testing-r1-build.done" 2>/dev/null)" != ok ]; then echo "build marker not ok"; echo build-missing >"$MARKER"; exit 1; fi
cmp -s ~/workspace/tron-amx/gen/rinzler.canon ~/workspace/tron-amx/gen/rinzler.mirror && { echo "arms byte-identical"; echo build-identical >"$MARKER"; exit 1; }
sha256sum ~/workspace/tron-amx/gen/rinzler.canon ~/workspace/tron-amx/gen/rinzler.mirror

# Stage 1: cross-session guard (lease + flock + no runtron/rinzler + serving down).
if pgrep -x 'rinzler(\.[a-z0-9]+)?' >/dev/null; then echo "a rinzler is already running"; pgrep -a rinzler; echo busy >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi

# Deadline: 02:30Z (next occurrence). stop_now EST -> 0 when the cell must not start.
DEADLINE=$(date -u -d "02:30" +%s); [ "$DEADLINE" -le "$(date -u +%s)" ] && DEADLINE=$(date -u -d "tomorrow 02:30" +%s)
echo "deadline $(date -u -d @$DEADLINE +%FT%TZ)"
stop_now() {  # $1 = estimate in seconds for the next cell
  local now; now=$(date -u +%s)
  [ $((now + $1 + 300)) -ge "$DEADLINE" ] && { echo "CLOCK-STOP (est $1 s would cross the deadline)"; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }
  return 1
}

# Cells: MODEL ARM TP MMLU ESTIMATE_SECONDS ; SOAK line = soak ARM MINUTES USERS ESTIMATE
CELLS="
ingested-qwen-3-4b-instruct-2507-tp4 off    4 1 3000
ingested-qwen-3-4b-instruct-2507-tp4 canon  4 1 3000
ingested-qwen-3-4b-instruct-2507-tp4 mirror 4 1 3000
llama-3.1-8b-instruct-good-tp2       off    2 1 2100
llama-3.1-8b-instruct-good-tp2       canon  2 0 800
llama-3.1-8b-instruct-good-tp2       mirror 2 1 2100
soak mirror 60 25 4800
mixtral-8x7b-instruct-v0.1-tp2       off    2 1 1800
mixtral-8x7b-instruct-v0.1-tp2       canon  2 0 800
mixtral-8x7b-instruct-v0.1-tp2       mirror 2 1 1800
ingested-gpt-oss-120b-tp4            off    4 1 2400
ingested-gpt-oss-120b-tp4            canon  4 0 1000
ingested-gpt-oss-120b-tp4            mirror 4 1 2400
"
echo "$CELLS" | grep -v '^\s*$' | while read -r a b c d e; do
  if [ "$a" = soak ]; then
    if stop_now "$e"; then echo skipped >"$RES/soak.STATUS-skipped"; mkdir -p "$RES/soak"; echo skipped >"$RES/soak/STATUS"; status; continue; fi
    echo "### soak arm=$b minutes=$c users=$d $(date -u +%FT%TZ)"
    bash "$H/soak_cell.sh" "$b" "$c" "$d"; echo "soak rc=$?"
  else
    if stop_now "$e"; then mkdir -p "$RES/cells/${a}__${b}"; echo skipped >"$RES/cells/${a}__${b}/STATUS"; status; continue; fi
    echo "### cell model=$a arm=$b tp=$c mmlu=$d $(date -u +%FT%TZ)"
    bash "$H/run_cell.sh" "$a" "$b" "$c" "$d"; echo "cell rc=$?"
  fi
  status
  echo "### done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
done
campaign_guard_release
echo ok >"$MARKER"
status
echo "=== campaign done $(date -u +%FT%TZ) ==="
