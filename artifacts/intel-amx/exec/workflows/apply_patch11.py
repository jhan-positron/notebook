#!/usr/bin/env python3
"""Page pass 11 (main session, 2026-11-20): reply I4 writes "pack<16>" outside a code span. Plain words instead,
so that GitHub markdown cannot read "<16>" as markup. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p).read(); orig = s
edits = [
 ("(pack&lt;16&gt; ns per call, and the share of zero-AMX-page calls for Muse Glimmer)",
  "(ns per call of the 16-head pack, and the share of zero-AMX-page calls for Muse Glimmer)"),
]
todo = 0
for old, new in edits:
    if old in s:
        assert s.count(old) == 1, ('not unique', old[:60], s.count(old)); s = s.replace(old, new); todo += 1
    else:
        assert s.count(new) == 1, ('neither old nor new text found', old[:60])
if s != orig:
    open(p, 'w').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
