#!/usr/bin/env python3
"""Page pass 8 (main session, 2026-11-20): two new record files and the Note lint result. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p).read(); orig = s
edits = [
 ("The trial merge ran in the session, and its output is not kept in a record file.</li>",
  "The trial merge is recorded in <code>trial-merge.txt</code> in the results folder. It was repeated on 2026-11-20 at 06:17 PST, with 0 conflict markers.</li>"),
 ("<li id=\"R50\"><code>registry-check-before.txt</code>, <code>registry-check-after.txt</code> and <code>wall-times.txt</code> in the results folder.</li>",
  "<li id=\"R50\"><code>registry-check-before.txt</code>, <code>registry-check-after.txt</code> and <code>wall-times.txt</code> in the results folder. The answer of <code>bin/slice route</code> is in <code>slice-route.txt</code>, and the output of <code>make lint-notes</code> is in <code>lint-notes.txt</code>.</li>"),
]
todo = 0
for old, new in edits:
    if old in s:
        assert s.count(old) == 1, ('not unique', old[:60]); s = s.replace(old, new); todo += 1
    else:
        assert new in s, ('neither old nor new text found', old[:60])
# one more bullet in the Part C status list, after the bullet "Done on delphi-3b35 on 2026-11-20: ..."
anchor = "The registry got a hand edit, and the update tool was not run.</li>"
bullet = ("\n<li>Lint at the final tree, 2026-11-20: <code>make lint-notes</code> (the check that every \"Note [...]\" reference in a comment has its definition) exits 0 on delphi-3b35. "
          "No changed file includes <code>&lt;cassert&gt;</code>. <code>git diff --check</code> against main is clean. The changelog line has 79 characters, and the limit is 80 "
          "<a class=\"ref\" href=\"#R50\">[R50]</a>.</li>")
assert s.count(anchor) == 1, s.count(anchor)
if 'Lint at the final tree, 2026-11-20' not in s:
    s = s.replace(anchor, anchor + bullet); todo += 1
if s != orig:
    open(p, 'w').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
