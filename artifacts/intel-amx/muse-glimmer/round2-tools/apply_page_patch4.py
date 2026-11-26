#!/usr/bin/env python3
"""Patch 4 of ../round2-respond-2-issac.html: the review request to Isaac of 2026-11-24 19:46 UTC.

Each replacement asserts that its old text occurs once. Kept as a record. Do not run it again.
Usage: apply_page_patch4.py PAGE.html
"""
import sys

page = sys.argv[1]
s = open(page, encoding='utf-8').read()
R28 = '<a class="ref" href="#R28">[R28]</a>'
REPL = [
 ('short version',
  'His review stays at "changes requested" until he reviews again.</p></div>',
  'His review is requested again, and it stays at "changes requested" until he reviews.</p></div>'),
 ('bullet on what the go did not cover',
  '<li>The go did not cover a new review request, a registry refresh or the merge. None of them was done.</li>',
  f'''<li>After the eleven steps you asked me to request Isaac's review. GitHub recorded the new request at 19:46:07 UTC (11:46 PST) {R28}.</li>
<li>Isaac was on the list since 2026-11-20, so the plain request call changed nothing. I removed the old request and added it again, and the timeline of the PR shows both events.</li>
<li>The go did not cover a registry refresh or the merge. Neither was done.</li>'''),
 ('ask box',
  "<li>The next event is Isaac's new review. A reply to a new finding needs a new go.</li>",
  "<li>The next event is Isaac's new review, which is requested since 19:46 UTC. A reply to a new finding needs a new go.</li>"),
 ('reference R28',
  'They checked 26, 15 and 19 claims.</li>\n</ul></li>',
  'They checked 26, 15 and 19 claims.</li>\n<li>The review request events of Isaac are in <code>RES/after-go/review-request-events-isaac.tsv</code>. The newest request is of 2026-11-24 19:46:07 UTC.</li>\n</ul></li>'),
]
for name, old, new in REPL:
    assert s.count(old) == 1, f'{name}: old text found {s.count(old)} times'
    s = s.replace(old, new)
open(page, 'w', encoding='utf-8').write(s)
print(f'{len(REPL)} replacements applied to {page}')
