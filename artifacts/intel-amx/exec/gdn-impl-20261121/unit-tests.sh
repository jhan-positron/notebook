#!/usr/bin/env bash
# gdn-impl-20261121: run the unit-test programs of the three campaign builds on delphi-3b35 and write one table.
# Runs ON delphi-3b35, on our CPUs (96-143). It opens no FPGA card.
#
# Words: tron = the inference program; GDN = GatedDeltaNet, the recurrent layer type of Qwen3.5 4B; AMX = Intel
# tile-matrix instructions; build tag = ctr (counters only), pa (+ GDN chain and block kernels), pab (+ attention
# kernels); kill switch = TRON_AMX_DISABLE=1 (no AMX kernel runs); GDN switch = TRON_AMX_GDN_DISABLE=1 (only the
# GDN block kernel is off).
# Why the extra rows: the GDN tests take the chain kernel where the AMX block kernel is not available. Running the
# pab test programs once more under each switch runs those branches on this AMX machine.
# Output: exec/results/gdn-impl-20261121/unit-tests.txt (the table) and unit/<tag>__<test>__<env>.txt (full output).
# "skip lines" counts the lines in which a test says that an AMX case did not run.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/gdn-impl-20261121
OUT=${OUT:-$RES/unit-tests.txt}
TAGS=${TAGS:-"ctr pa pab"}
TESTS=${TESTS:-"t_gated_delta_net t_amx_numerics t_amx_dispatch_dtype t_llama_unit t_tronstats_convention"}
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
mkdir -p "$RES/unit"
run_one() {  # tag test env-label env-assignment
  local tag=$1 test=$2 label=$3 env=$4 wt=/var/tmp/jhan/b35-gdn-$1 f=$RES/unit/$1__$2__$3.txt
  [ -x "$wt/gen/$test" ] || { echo "$tag | $(git -C "$wt" rev-parse --short=10 HEAD) | $test | 0 | 0 | missing binary | 0 | $label"; return; }
  ( cd "$wt" && env SYSTEM_CONFIG="--instance 1,2" $env taskset -c 96-143 "./gen/$test" --skip-benchmarks ) >"$f" 2>&1
  local rc=$? line a c result
  line=$(grep -aE "^(All tests passed|test cases:|assertions:)" "$f" | tr '\n' ' ')
  if grep -aq "^All tests passed" "$f"; then
    a=$(sed -nE 's/^All tests passed \(([0-9]+) assertions? in ([0-9]+) test cases?\).*/\1/p' "$f")
    c=$(sed -nE 's/^All tests passed \(([0-9]+) assertions? in ([0-9]+) test cases?\).*/\2/p' "$f")
    result=passed
  else
    a=$(sed -nE 's/^assertions: *([0-9]+) .*/\1/p' "$f"); c=$(sed -nE 's/^test cases: *([0-9]+) .*/\1/p' "$f")
    result="FAILED rc=$rc [$line]"
  fi
  echo "$tag | $(git -C "$wt" rev-parse --short=10 HEAD) | $test | ${a:-0} | ${c:-0} | $result | $(grep -aciE "AMX.*(skipped|unavailable)" "$f") | $label"
}
{
  echo "# Unit tests of the three campaign builds on delphi-3b35, run $(date -u +%FT%TZ), CPUs 96-143,"
  echo "# command per binary: SYSTEM_CONFIG=\"--instance 1,2\" [switch] taskset -c 96-143 ./gen/<test> --skip-benchmarks"
  echo "# \"skip lines\" = output lines that say an AMX case did not run (0 = every AMX case executed)."
  echo "# format: build | commit | test | assertions | test cases | result | skip lines | switch"
  for tag in $TAGS; do
    for t in $TESTS; do run_one "$tag" "$t" none ""; done
  done
  for t in t_gated_delta_net t_amx_numerics; do
    run_one pab "$t" kill-switch "TRON_AMX_DISABLE=1"
    run_one pab "$t" gdn-switch "TRON_AMX_GDN_DISABLE=1"
  done
} | tee "$OUT"
