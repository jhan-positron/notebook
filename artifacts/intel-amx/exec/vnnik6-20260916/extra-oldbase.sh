#!/usr/bin/env bash
# vnnik6 extra cell: did the base move between the PR's old base and main? The 2026-09-15 one-run
# cell measured 36.28 TPS per user with runtron.p0perf13 (commit 544ca05c7a); today's main binary
# runtron.main0916 (c7844ca2ce) measures about 34.3. This script runs both, interleaved, tp2
# prompt 1024, 8 users, OLD_REPS (6) repetitions, on our half, AFTER the main campaign has written
# its .done marker. It reuses campaign.sh's functions (VNNIK6_FUNCTIONS_ONLY=1) with its own NAME,
# so the results land in exec/results/vnnik6-oldbase-20260916/.
# Arms: old = runtron.p0perf13 (544ca05c7a, PR #3879 code, row-major K); base = runtron.main0916.
# Usage (on delphi-3bda): setsid nohup bash extra-oldbase.sh &
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=vnnik6-oldbase-20260916
VNNIK6_FUNCTIONS_ONLY=1 source "$EXEC/vnnik6-20260916/campaign.sh"
RT_OLD=/var/tmp/jhan/tron-p0perf13/gen/runtron.p0perf13
arm_bin() { case $1 in base) echo "$RT_BASE" ;; old) echo "$RT_OLD" ;; *) return 1 ;; esac; }
arm_tip() { case $1 in base) echo "${TIP_BASE:-?}" ;; old) echo 544ca05c7a ;; *) echo "?" ;; esac; }
OUR_RT_RE='^/var/tmp/jhan/tron-(main0916|p0perf13)/gen/runtron[.](main0916|p0perf13) '
ARMS="old base"
OLD_REPS=${OLD_REPS:-6}
exec >>"$LOG" 2>&1
echo "=== $NAME started $(ts) pid $$: waits for $EXEC/logs/vnnik6-20260916.done ==="
while [ ! -s "$EXEC/logs/vnnik6-20260916.done" ]; do sleep 60; done
echo "$(ts) main campaign done: $(cat "$EXEC/logs/vnnik6-20260916.done")"
# the 6-h takeover rule (lib-guard.sh): inherit the main campaign's last stop time from its log
tl=$(grep "GUARD takeover: all checks passed" "$EXEC/logs/vnnik6-20260916.log" | tail -1 | cut -d' ' -f1)
if [ -n "$tl" ]; then GUARD_TAKEOVER_LAST=$(date -d "$tl" +%s 2>/dev/null || echo 0); echo "$(ts) inherited takeover time $tl ($GUARD_TAKEOVER_LAST)"; fi
export GUARD_TAKEOVER_LAST
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another instance holds $INST_LOCK; exit"; exit 1; }
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
[ -x "$RT_OLD" ] && [ -x "$RT_BASE" ] || { echo "$(ts) binary missing"; finish no-binary; exit 1; }
TIP_BASE=$(git -C /var/tmp/jhan/tron-main0916 rev-parse --short HEAD 2>/dev/null || echo "?")
{
  echo "# $NAME: old base (runtron.p0perf13, 544ca05c7a) vs main base (runtron.main0916, $TIP_BASE); qwen-3-30b-a3b tp2 prompt 1024, 8 users, 256 tokens; host $(hostname); started $(ts)"
  echo "# USE_HW_ATTN=0; env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE"
  echo "# placement tp2: $(placement 2)"
  sha256sum "$RT_OLD" "$RT_BASE"
  for b in "$RT_OLD" "$RT_BASE"; do ( cd "$(dirname "$b")" && echo "version $(basename "$b"): $("./$(basename "$b")" --version 2>&1 | head -1)" ); done
} >>"$RES/rt-results.txt"
rt_fail=0
for rep in $(seq 1 "$OLD_REPS"); do for arm in $ARMS; do run_rt 2 1024 "$arm" "$rep" || rt_fail=$((rt_fail + 1)); done; done
VNNIK6_ARMS="old base" VNNIK6_PAIRS="base:old" python3 "$EXEC/vnnik6-20260916/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md"
remove_our_slice_files
campaign_guard_release 2>/dev/null
echo "$([ $rt_fail -eq 0 ] && echo ok || echo "ok-with-$rt_fail-failed-runs")" >"$MARKER"
status "finished: $(cat "$MARKER")"
echo "=== $NAME finished $(ts): $(cat "$MARKER") ==="
