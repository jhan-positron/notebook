#!/usr/bin/env bash
# glimmer-20261016 tests0 (runs ON delphi-3bda, detached): the three AMX unit tests of /var/tmp/jhan/tron-g16, pinned to our
# half (fake-label tests: pos_fake maps no hugepage file). Also t_amx_numerics under the kill switch. Log + per-test outputs in
# exec/results/glimmer-20261016/tests0/. Marker tests0.done (ok|failed).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/glimmer-20261016/tests0
WT=/var/tmp/jhan/tron-g16
OUR_CPUS=72-143,216-287
mkdir -p "$RES"
exec >>"$RES/tests0.log" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== tests0 started $(ts) head=$(git -C $WT rev-parse --short HEAD) ==="
cd "$WT" || { echo failed >"$RES/../tests0.done"; exit 1; }
ok=1
run() { # $1 name $2 binary $3 extra env (string) $4... args
  local name=$1 bin=$2 envs=$3; shift 3
  local t0 rc; t0=$(date +%s)
  env -u TRON_AMX_DISABLE SYSTEM_CONFIG="--instance 1,2" $envs nice -n10 taskset -c $OUR_CPUS timeout -k 60 3600 "$bin" "$@" >"$RES/$name.log" 2>&1; rc=$?
  local summary; summary=$(grep -E "^(All tests passed|test cases:|assertions:)" "$RES/$name.log" | tr '\n' ' ')
  local warns; warns=$(grep -c "AMX unavailable" "$RES/$name.log")
  echo "$(ts) $name | rc=$rc | $(( $(date +%s) - t0 ))s | $summary| amx-unavailable-warnings=$warns"
  [ $rc = 0 ] || ok=0
}
run t_amx_numerics        gen/t_amx_numerics        ""                   --skip-benchmarks
run t_amx_numerics_killsw gen/t_amx_numerics        "TRON_AMX_DISABLE=1" --skip-benchmarks
run t_amx_dispatch_dtype  gen/t_amx_dispatch_dtype  ""                   --skip-benchmarks
run t_llama_unit          gen/t_llama_unit          ""                   --skip-benchmarks
# section-level evidence for the 16-head cases
grep -E "16 heads|4 heads" "$RES/t_amx_numerics.log" | head -20
[ $ok = 1 ] && echo ok >"$RES/../tests0.done" || echo failed >"$RES/../tests0.done"
echo "=== tests0 finished $(ts) ok=$ok ==="
