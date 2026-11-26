#!/usr/bin/env bash
# pr5606-check-20261123 registry check. Runs ON delphi-3b35 in the option-OFF tree at S2. Read-only: no test
# runs, no FPGA card. Adapted from exec/pr5022-final-20261119/registry-check-3b35.sh.
# The registry is config/test-benchmarks.json (per machine class: run time and peak memory of every test).
# bin/slice is the test scheduler that reads it.
# It prints, for the registry file of the tree:
#   1. every row of t_amx_dispatch_dtype, with the name of its machine class,
#   2. the CTest registration of the test in this build, and the "metadata drift" warning that bin/slice run
#      would print for it (registry row against CTest registration),
#   3. `bin/slice bench --check-platform` and `bin/slice bench --check` (the two read-only checks that the CI
#      workflows run), with exit codes. Their whole output is saved next to the record.
# `bin/slice bench` without --check, and --update or --new, are NOT run: they measure on both halves of the
# machine.
# Usage (on 3b35): bash registry-check-3b35.sh       Record: exec/results/pr5606-check-20261123/registry-check.txt
set -u
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
WT=$(wt_of off)
OUT=$RES/registry-check.txt
{
  echo "# registry check on $(hostname), $(ts); build tree $WT; HEAD $(git -C "$WT" rev-parse HEAD); git tree hash $(git -C "$WT" rev-parse 'HEAD^{tree}')"
  [ "$(git -C "$WT" rev-parse HEAD)" = "$S2" ] || { echo "the tree is not at S2"; exit 1; }
  [ -z "$(dirty_of "$WT")" ] || { echo "the tree has changes"; exit 1; }
  echo "# option: $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt")"
  echo "# sha256 of config/test-benchmarks.json: $(sha256sum "$WT/config/test-benchmarks.json" | cut -c1-16); the file differs from S0: $(git -C "$WT" diff --quiet "$S0" "$S2" -- config/test-benchmarks.json && echo no || echo yes)"
  $PIN python3 - "$WT" <<'EOF'
import contextlib, importlib.machinery, importlib.util, io, json, sys
root = sys.argv[1]
NAME = 't_amx_dispatch_dtype'
reg = json.load(open(root + '/config/test-benchmarks.json'))
classes = [k for k, v in reg.items() if isinstance(v, dict) and 'tests' in v]
print("machine classes in the registry: " + ", ".join("%s (%d rows)" % (c, len(reg[c]["tests"])) for c in classes))
print(f"rows of {NAME}:")
n = 0
for c in classes:
    for row in reg[c]['tests']:
        if row['name'] == NAME or row['name'].startswith(NAME + '-'):
            n += 1
            print(f"  [{c}] " + json.dumps(row, separators=(',', ':')))
print(f"  count: {n}")
sys.path.insert(0, root + '/bin')
loader = importlib.machinery.SourceFileLoader('slice_mod', root + '/bin/slice')
mod = importlib.util.module_from_spec(importlib.util.spec_from_loader('slice_mod', loader))
sys.argv = ['slice']; loader.exec_module(mod)
platform = mod.get_server_type()
print(f"machine class of this host, as bin/slice sees it: {platform}")
bench = (mod.get_platform_bench() or {}).get('tests', [])
rows = [b for b in bench if mod.base_name_of(b['name']) == NAME]
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    manifest = {e['name']: e for e in mod.discover_tests_from_ctest()}
e = manifest.get(NAME, {})
print(f"CTest registration of {NAME} in this build: labels={e.get('labels')} skip_return_codes={e.get('skip_return_codes')} "
      f"min_slices={e.get('min_slices')} command={e.get('command')}")
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    mod.warn_benchmark_metadata_drift(rows, manifest)
print('drift warning for the test: ' + (buf.getvalue().strip().replace('\n', ' | ') or 'none'))
EOF
  for c in --check-platform --check; do
    f=$RES/registry-check$c.out
    ( cd "$WT" >/dev/null 2>&1 && $PIN python3 bin/slice bench $c ) >"$f" 2>&1; rc=$?
    echo "bin/slice bench $c: exit $rc; output ($(wc -l <"$f") lines, whole text in $f): $(tr '\n' ' ' <"$f" | cut -c1-500)"
  done
  echo "# finished $(ts)"
} >"$OUT" 2>&1
cat "$OUT"
