#!/bin/bash
# round3: PR 5015 head 7e7f52d761 + round3.patch, built and tested on our half of delphi-3bda (socket 1 cpus, fake device).
set -u
WT=/var/tmp/jhan/tron-g16h
OUR=72-143,216-287
LOG=/var/tmp/jhan/round3.log
DONE=/var/tmp/jhan/round3.done
HEAD=7e7f52d76134d824c6724d2f3c2973cbfa9db748
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
fail() { echo "failed: $*" >"$DONE"; echo "=== round3 FAILED $(ts): $*"; exit 1; }
rm -f "$DONE"
echo "=== round3 start $(ts) pid $$ load $(cut -d' ' -f1-3 /proc/loadavg)"
for p in $(pgrep -x rinzler); do echo "rinzler $p: $(taskset -cp $p 2>/dev/null | cut -c1-80)"; done
cd "$WT" || fail "cd $WT"
git checkout -q --detach "$HEAD" || fail "checkout $HEAD"
git apply --check /var/tmp/jhan/round3.patch || fail "patch does not apply"
git apply /var/tmp/jhan/round3.patch || fail "patch apply"
echo "$(ts) worktree at $(git rev-parse HEAD) + patch: $(git status --short | tr '\n' ' ')"
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
t0=$(date +%s)
nice -n10 taskset -c "$OUR" cmake --build gen --target t_amx_numerics t_amx_dispatch_dtype t_llama_unit -j20 2>&1 | tail -8
rc=${PIPESTATUS[0]}
echo "$(ts) build rc=$rc took $(( $(date +%s) - t0 )) s"
[ "$rc" -eq 0 ] || fail "build rc=$rc"
echo "warnings in the build log for the AMX test units:"; grep -c 'warning:' /dev/null || true
run() {  # label binary extra-env...
  local label=$1 bin=$2; shift 2
  local out=/var/tmp/jhan/round3-$label.log
  ( nice -n10 taskset -c "$OUR" env SYSTEM_CONFIG="--instance 1,2" "$@" timeout -k 60 3600 "./gen/$bin" --skip-benchmarks ) >"$out" 2>&1
  local r=$?
  echo "$(ts) $label rc=$r | $(grep -E '^(test cases|assertions|All tests passed)' "$out" | tr '\n' ' ') | skips: $(grep -c 'AMX unavailable' "$out")"
}
run t_amx_numerics t_amx_numerics
run t_amx_dispatch_dtype t_amx_dispatch_dtype
run t_llama_unit t_llama_unit
run t_amx_numerics-killswitch t_amx_numerics TRON_AMX_DISABLE=1
run t_amx_dispatch_dtype-killswitch t_amx_dispatch_dtype TRON_AMX_DISABLE=1
echo ok >"$DONE"
echo "=== round3 done $(ts)"
