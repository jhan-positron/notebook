#!/usr/bin/env bash
# pr4737-ci-sim-20261002 (runs ON delphi-3bda, detached): the "Test host" job of the default CI, done by hand with the
# VNNI K option on, at the PR #4737 head COMMIT in /var/tmp/jhan/tron-i4500b. Three suites through
# exec/i4525-20260922/host-suite.sh (make build-test-host + make test-host = bin/slice run --filter=host
# --exclude-tag=slow, inside nix develop, our half of the machine): (1) "head": the suite as is; (2) "break": the same
# with a deliberate break of the row-major tail dispatch (self_attention.hpp: the tail-row scores set to 0), to show the
# suite catches it; (3) "restored": the break reverted, the suite again. Each step waits for the CI lease and for other
# people's activity to end (bill excluded). Markers: RES/host-suite-{head,break,restored}.done, RES/chain.done.
# Usage: COMMIT=<sha> bash run.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/pr4737-ci-sim-20261002
LOG=$EXEC/logs/pr4737-ci-sim-20261002.log
WT=/var/tmp/jhan/tron-i4500b
COMMIT=${COMMIT:?}
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
rm -f "$RES/chain.done"
echo "=== pr4737 CI simulation started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT ==="
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy or another person active"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
suite() { RES="$RES" WT="$WT" SUFFIX="$1" bash "$EXEC/i4525-20260922/host-suite.sh"; echo "$(ts) suite $1: $(cat "$RES/host-suite-$1.done" 2>/dev/null)"; }
wait_slot "checkout"
git -C "$WT" checkout -q --detach "$COMMIT" || { echo "$(ts) checkout failed"; echo "stopped: checkout" >"$RES/chain.done"; exit 1; }
echo "$(ts) $WT at $(git -C "$WT" rev-parse HEAD) ($(git -C "$WT" log -1 --format=%s))"
suite head
wait_slot "break"
python3 - "$WT/h/tron/models/self_attention.hpp" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old = """                  k{k_vnni::row_ptr(plane, i)};
              for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
                s_pages[offset][i] = dot_q[offset](k);
"""
new = """                  k{k_vnni::row_ptr(plane, i)};
              (void)k;  // DELIBERATE BREAK (pr4737-ci-sim): tail-row scores zeroed
              for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
                s_pages[offset][i] = 0;
"""
assert s.count(old) == 1, "break anchor not unique"
p.write_text(s.replace(old, new)); print("break applied")
PY
git -C "$WT" diff --stat
suite break
git -C "$WT" checkout -- h/tron/models/self_attention.hpp
echo "$(ts) break reverted: $(git -C "$WT" status --short | wc -l) dirty files"
wait_slot "restored"
suite restored
echo done >"$RES/chain.done"
echo "=== pr4737 CI simulation finished $(ts) ==="
