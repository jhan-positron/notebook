#!/usr/bin/env bash
# Extra cells for round 1, run after exec/more-testing-r1.sh finishes and only
# while the 02:30Z deadline allows. First extra: an A/A control, the qwen-3-4b
# off arm repeated (same binary, same switches) so the run-to-run MMLU Pro
# noise of one arm is measured (needed to read the +1.51-point canon-vs-off
# difference seen at 19:22Z).
set -u
EXEC=~/workspace/intel-AMX/exec
H=$EXEC/more-testing-r1
RES=$EXEC/results/more-testing-r1
LOG=$EXEC/logs/more-testing-r1.log      # same log: the monitor follows it
MARKER=$EXEC/logs/more-testing-r1-extra.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== extra cells queued $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"
source "$H/rz.sh"
status() { python3 "$H/gen_status.py" 2>&1 | tail -1; }
# wait for the main campaign
while [ ! -e "$EXEC/logs/more-testing-r1.done" ]; do sleep 60; done
echo "=== extra cells start $(date -u +%FT%TZ) (main marker: $(cat "$EXEC/logs/more-testing-r1.done")) ==="
trap '[ -e "$MARKER" ] || { rz_stop; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; status; }' EXIT
if pgrep -x 'rinzler(\.[a-z0-9]+)?' >/dev/null; then echo "a rinzler is still running"; echo busy >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
DEADLINE=$(date -u -d "02:30" +%s); [ "$DEADLINE" -le "$(date -u +%s)" ] && DEADLINE=$(date -u -d "tomorrow 02:30" +%s)
stop_now() { local now; now=$(date -u +%s); [ $((now + $1 + 300)) -ge "$DEADLINE" ] && { echo "CLOCK-STOP (est $1 s)"; return 0; }; ci_took_dut && { echo CI-TOOK-DUT; return 0; }; rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
CELLS="
ingested-qwen-3-4b-instruct-2507-tp4 off 4 1 2700 rep2
"
echo "$CELLS" | grep -v '^\s*$' | while read -r a b c d e f; do
  if stop_now "$e"; then mkdir -p "$RES/cells/${a}__${b}__${f}"; echo skipped >"$RES/cells/${a}__${b}__${f}/STATUS"; status; continue; fi
  echo "### cell model=$a arm=$b tp=$c mmlu=$d tag=$f $(date -u +%FT%TZ)"
  bash "$H/run_cell.sh" "$a" "$b" "$c" "$d" "$f"; echo "cell rc=$?"
  status
  echo "### done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
done
campaign_guard_release
echo ok >"$MARKER"
status
echo "=== extra cells done $(date -u +%FT%TZ) ==="
