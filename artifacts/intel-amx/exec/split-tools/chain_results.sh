#!/usr/bin/env bash
# Summarize the PR 3879 split chain results in exec/logs (split-<label>.{done,txt}, format
# patches, bench json). Usage: chain_results.sh [label ...]   (default: all eight steps)
set -u
L=~/workspace/intel-AMX/exec/logs
LABELS=${*:-"PR0-on PR0-off PR0b PR1-on PR1-off PR2-on R-mirror R-canon"}
for lab in $LABELS; do
  echo "=== $lab: $( [ -e $L/split-$lab.done ] && cat $L/split-$lab.done || echo '(no .done marker yet)' )"
  [ -e $L/split-$lab.txt ] && sed 's/^/    /' $L/split-$lab.txt
  [ -e $L/split-$lab.bench-done ] && echo "    bench marker: $(cat $L/split-$lab.bench-done); bench log: $(tail -1 $L/split-$lab-bench.log 2>/dev/null | cut -c1-100)"
  if [ -e $L/split-$lab-format.patch ]; then
    n=$(grep -c '^[-+][^-+]' $L/split-$lab-format.patch); echo "    format patch: $n changed lines, files: $(grep '^+++ b/' $L/split-$lab-format.patch | sed 's|^+++ b/||' | tr '\n' ' ')"
  fi
  if [ -e $L/split-$lab-test-benchmarks.json ]; then
    echo "    bench json entries for new tests:"; python3 - "$L/split-$lab-test-benchmarks.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
def walk(o,path=""):
    if isinstance(o,dict):
        for k,v in o.items():
            if k in ("t_page_share_counters","t_amx_numerics","t_amx_dispatch_dtype","t_amx_mirror","t_amx_arena_leak"):
                print(f"      {path}/{k}: {json.dumps(v)[:160]}")
            else: walk(v,f"{path}/{k}")
walk(d)
PY
  fi
  if [ -e $L/split-$lab.log ]; then
    echo "    log: $(wc -l < $L/split-$lab.log) lines; last: $(tail -1 $L/split-$lab.log | cut -c1-120)"
    grep -m5 -E "error:|FAILED|guard-never-free|dut-never-free|worktree-failed|no-checkout" $L/split-$lab.log | sed 's/^/    ! /'
  fi
done
