#!/usr/bin/env python3
"""Page pass 7 (main session, 2026-11-20): remove the promise to attach the A/B record files, settle the I16 row.
Idempotent: each edit is skipped when its new text is already present. Writes only when every edit is placed."""
import sys
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p).read(); orig = s
edits = [
 # 1. status box: go list
 ("Then I edit the PR description, attach the A/B record files as one comment, post the 26 inline replies and the combined reply, and add the comment on #5021.</li>\n</ol>",
  "Then I edit the PR description, post the 26 inline replies and the combined reply, and add the comment on #5021.</li>\n</ol>\n"
  "<p>One reply changed in substance since you read it, besides I25. Card <a href=\"#T8\">T8</a> and the combined reply no longer say that the five A/B record files are attached to the PR. "
  "The files total 540 KB, one PR comment holds 65 KB, and the command line cannot attach files. The replies now say that the files stay outside the repository. "
  "If you want them on the PR, drag them into a comment in the browser. Card T8 lists the paths.</p>"),
 # 2. T8 reply
 ("<p>What I added:</p>\n<ul><li>The A/B record files, attached to this PR as a comment: <code>glimmer-20261016/rt-results.txt</code> and <code>attn-stats-compare.md</code>, <code>glimext-20261018/rt-results.txt</code> and <code>identity.txt</code>, <code>glimci-20261017/summary.md</code>.</li></ul>\n<p>What I cannot add to this PR:",
  "<p>The A/B record files stay outside the repository. The Verification section names the file behind each table.</p>\n<p>What I cannot add to this PR:"),
 # 3. combined reply
 ("<strong>Granite Rapids timing.</strong> No per-kernel number exists. The A/B record files are attached in a separate comment. A per-kernel timing",
  "<strong>Granite Rapids timing.</strong> No per-kernel number exists. The A/B record files stay outside the repository. A per-kernel timing"),
 # 4. Part C, CI and issues
 ("<li>One PR comment with the A/B record files, posted together with the replies. The combined reply says that they are attached (T8).</li></ul>",
  "</ul>"),
 # 5. provenance paragraph
 ("Two things in the replies need an action that the go list must carry: the A/B record files as a PR comment, and the comment on #5021.",
  "One thing in the replies needs an action that the go list carries: the comment on #5021. The promise to attach the A/B record files was removed from T8 and from the combined reply on 2026-11-20, because the command line cannot attach files."),
 # 6. I16 row
 ("<div>The draft of the PR description cites the default CI run in its OFF row. It does not cite the two job ids that Isaac named, and it does not mention the guard move. The reply states both. Say if the description should carry them as well.</div>",
  "<div>Settled on 2026-11-20. The PR description cites the default CI run at the final head in its OFF row. The two job ids of the reviewed commit and the guard move stay in this reply. The description reports the head and does not narrate changes.</div>"),
]
todo = 0
for old, new in edits:
    if old in s:
        assert s.count(old) == 1, ('not unique', old[:70])
        s = s.replace(old, new); todo += 1
    else:
        assert new in s, ('neither old nor new text found', old[:70])
# 7. T8: a "Before posting" row with the reason and the paths, placed after the T8 reply block
marker = '<div class="row"><div class="k">Before posting</div><div>T8, 2026-11-20:'
if marker not in s:
    i = s.index('id="T8"'); j = s.index('<div class="card" id="T9"', i)
    card = s[i:j]
    tail = '</p></div></div>\n'
    assert card.endswith(tail), repr(card[-60:])
    row = ('</p></div>\n' + marker + ' the earlier draft said that five record files are attached to the PR as a comment. That sentence is removed. '
           'The files total 540 KB (two of them are raw logs of 139 KB and 309 KB), one PR comment holds 65 KB, and the command line cannot attach files. '
           'To put them on the PR by hand, drag these files into a comment in the browser: under <code>/home/jhan/workspace/intel-AMX/exec/results/</code>, '
           '<code>glimmer-20261016/rt-results.txt</code>, <code>glimmer-20261016/attn-stats-compare.md</code>, <code>glimext-20261018/rt-results.txt</code>, '
           '<code>glimext-20261018/identity.txt</code> and <code>glimci-20261017/summary.md</code>.</div></div></div>\n')
    card2 = card[:-len(tail)] + row
    assert card2.count('<div') - card2.count('</div') == card.count('<div') - card.count('</div'), 'div balance of the T8 card'
    s = s[:i] + card2 + s[j:]; todo += 1
assert s.count('<div') == s.count('</div'), 'page div balance'
if s != orig:
    open(p, 'w').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}; "A/B record files" mentions left: {s.count("A/B record files")}')
