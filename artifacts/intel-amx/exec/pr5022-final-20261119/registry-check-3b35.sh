#!/usr/bin/env bash
# pr5022-final-20261119 registry check. Runs ON delphi-3b35 in the build tree. Read-only: no test runs, no card.
# The registry is config/test-benchmarks.json (per machine class: run time and memory of every test, and the exit
# code a test may return when all its cases skip). bin/slice is the test scheduler that reads it.
# Prints, for the registry file that is in the build tree right now:
#   1. bin/slice bench --check-platform and bin/slice bench --check (the two checks the CI workflows run), and
#   2. the "metadata drift" warning bin/slice run would print for the two AMX tests: registry row against the
#      CTest registration (labels, minimum slices, skip return codes).
# Usage (on 3b35): bash registry-check-3b35.sh <label>      Output: exec/results/<name>/registry-check-<label>.txt
set -u
LABEL=${1:?label, for example before or after}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-final-20261119
OUT=$EXEC/results/$NAME/registry-check-$LABEL.txt
WT=/var/tmp/jhan/b35-pr5022-final
PIN="nice -n10 taskset -c 96-143"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
export PATH=/tools/uv/0.9.5:$PATH
{
  echo "# registry check '$LABEL' on $(hostname), $(date -u +%FT%TZ); build tree $WT; git tree hash $(git -C "$WT" write-tree)"
  echo "# sha256 of config/test-benchmarks.json: $(sha256sum "$WT/config/test-benchmarks.json" | cut -c1-16)"
  echo "# rows of the two AMX tests for this machine class:"
  $PIN python3 - "$WT" <<'EOF'
import contextlib, importlib.machinery, importlib.util, io, json, sys
root = sys.argv[1]
sys.path.insert(0, root + '/bin')
loader = importlib.machinery.SourceFileLoader('slice_mod', root + '/bin/slice')
mod = importlib.util.module_from_spec(importlib.util.spec_from_loader('slice_mod', loader))
sys.argv = ['slice']; loader.exec_module(mod)
platform = mod.get_server_type()
bench = (mod.get_platform_bench() or {}).get('tests', [])
rows = [b for b in bench if mod.base_name_of(b['name']) in ('t_amx_numerics', 't_amx_dispatch_dtype')]
for r in rows:
    print(f'#   [{platform}] ' + json.dumps(r, separators=(',', ':')))
manifest = {e['name']: e for e in mod.discover_tests_from_ctest()}
for n in ('t_amx_numerics', 't_amx_dispatch_dtype'):
    e = manifest.get(n, {})
    print(f"#   CTest registration {n}: labels={e.get('labels')} skip_return_codes={e.get('skip_return_codes')} min_slices={e.get('min_slices')}")
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    mod.warn_benchmark_metadata_drift(rows, manifest)
print('drift warning for the two AMX tests: ' + (buf.getvalue().strip().replace('\n', ' | ') or 'none'))
EOF
  for c in --check-platform --check; do
    out=$( cd "$WT" 2>/dev/null >/dev/null && $PIN python3 bin/slice bench $c 2>&1 ); rc=$?
    echo "bin/slice bench $c: exit $rc: $(echo "$out" | tr '\n' ' ' | cut -c1-400)"
  done
} >"$OUT" 2>&1
cat "$OUT"
