#!/usr/bin/env python3
"""Page pass 12 (main session, 2026-11-20, CI results in): the combined reply and reply I7 state the result of the
two attempts of the legacy test-host job. Run before fill_placeholders.py. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p).read(); orig = s
edits = [
 # combined reply, bullet "Linked AMX-on build"
 ("and its test-host job ran on ⟦RUNNER⟧. The kernel cases execute only on a Granite Rapids runner.</li>",
  "and its test-host job ran on ⟦RUNNER⟧. The kernel cases execute only on a Granite Rapids runner. Both attempts pass all 106 host tests. The job log has one line per test executable, so it does not list single cases.</li>"),
 # I7, second bullet of "What covers this PR"
 ("run ⟦CMAKERUN⟧, test-host on ⟦RUNNER⟧.</li>",
  "run ⟦CMAKERUN⟧, test-host on ⟦RUNNER⟧. Both attempts pass all 106 host tests.</li>"),
]
todo = 0
for old, new in edits:
    if new in s: continue
    assert s.count(old) == 1, ('not found exactly once', old[:70], s.count(old)); s = s.replace(old, new); todo += 1
if s != orig:
    open(p, 'w').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
