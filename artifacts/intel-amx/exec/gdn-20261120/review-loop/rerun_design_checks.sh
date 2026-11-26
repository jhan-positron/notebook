#!/bin/bash
# Re-run every pure-python design check from a scratch copy; stdout+stderr -> <script>.rerun.out; exit code -> <script>.rc
cd "$(dirname "$0")/dc" || exit 1
export PYTHONDONTWRITEBYTECODE=1
run_one() {
  d=$(dirname "$1"); b=$(basename "$1" .py)
  ( cd "$d" && start=$(date +%s) && timeout 1500 python3 "$b.py" > "$b.rerun.out" 2>&1; echo "$? $(( $(date +%s) - start ))s" > "$b.rc" )
}
export -f run_one
find . -name "*.py" ! -name "gdn_common.py" ! -name "vm_engine.py" ! -name "proto_copy.py" | sort | xargs -P "$(nproc)" -I{} bash -c 'run_one {}'
echo ALL-DONE
