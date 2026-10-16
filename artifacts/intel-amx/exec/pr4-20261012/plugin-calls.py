#!/usr/bin/env python3
"""plugin-calls.py <plugins dir>: the generated-plugin check of PR3-handoff.md step 6.
For every *.hpp in the directory (read with its newlines removed), count:
  kv_ops    = `outer_state.template save_v<` calls (one per KV-writing operation, main side only)
  main_k    = `save_k<` calls whose argument list ends in `, 0, n_workers);` (main's call)
  helper_k  = `save_k<` calls whose argument list ends in `, worker_ix, n_workers);` (the helpers' call)
  other_k   = every other `save_k<` call
  helper_fn = occurrences of `save_k_helper` (the first shared-save version; must be absent)
PASS when every plugin has main_k == helper_k == kv_ops > 0 and other_k == helper_fn == 0. The last line is PASS or FAIL.
The generated K buffer is named by the generator (rope_1 for qwen3-4b), so the argument TAIL is matched, not a buffer name."""
import pathlib
import re
import sys

d = pathlib.Path(sys.argv[1])
files = sorted(d.glob('*.hpp'))
print(f"# generated plugins in {d}: {len(files)} files")
print(f"{'plugin':<52} {'kv_ops':>6} {'main_k':>7} {'helper_k':>8} {'other_k':>7} {'helper_fn':>9}  verdict")
ok = len(files) > 0
for f in files:
    s = f.read_text(errors='replace').replace('\n', '')
    kv_ops = s.count('outer_state.template save_v<')
    calls = re.findall(r'save_k<.*?\);', s)
    main_k = sum(1 for c in calls if re.search(r',\s*0,\s*n_workers\s*\);$', c))
    helper_k = sum(1 for c in calls if re.search(r',\s*worker_ix,\s*n_workers\s*\);$', c))
    other_k = len(calls) - main_k - helper_k
    helper_fn = s.count('save_k_helper')
    good = main_k == helper_k == kv_ops and kv_ops > 0 and other_k == 0 and helper_fn == 0
    ok = ok and good
    print(f"{f.name:<52} {kv_ops:>6} {main_k:>7} {helper_k:>8} {other_k:>7} {helper_fn:>9}  {'ok' if good else 'FAIL'}")
print(('PASS' if ok else 'FAIL') + f": {len(files)} plugins, rule main_k == helper_k == kv_ops > 0 and other_k == helper_fn == 0")
sys.exit(0 if ok else 1)
