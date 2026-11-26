import json, re, collections
rows = [json.loads(l) for l in open('isaac_all_comments.jsonl')]
revs = json.load(open('isaac_reviews.json'))
bodies = [(r['pr'], r['submitted_at'], r['body']) for r in revs if (r['body'] or '').strip()]
mine = [r for r in rows if r['pr'] == 5022]
mine.sort(key=lambda r: (r['created_at'], r['id']))
I_RE = re.compile(r"\bI\b|\bI'd\b|\bI'm\b|\bmy\b")
COULD_RE = re.compile(r"Could (we|the|this|these|it)")
print("=== PR 5022 per-comment features")
for i, r in enumerate(mine, 1):
    b = r['body']
    last = b.rstrip().split("\n")[-1]
    fname = r['path'].split('/')[-1]
    print("[%2d] len=%4d ends_with_trailer=%s could=%s suggestion=%s first_person=%d %s:%s" % (
        i, len(b), last.startswith('Checked by:'), bool(COULD_RE.search(b)), '```suggestion' in b, len(I_RE.findall(b)), fname, r['line']))
print("all 26 end with trailer:", all(r['body'].rstrip().split("\n")[-1].startswith('Checked by:') for r in mine), "count", len(mine))
body5022 = [b for p, s, b in bodies if p == 5022][0]
ids = sorted(set(re.findall(r'\b[a-z][a-z-]*/[a-z][a-z-]*@[a-z0-9.-]+\b', body5022)))
print("\ndistinct agent ids in the PR 5022 summary:", len(ids), ids)
print("\n=== phrase recurrence in OTHER review summaries (not PR 5022); total other summaries =", sum(1 for pr, s, b in bodies if pr != 5022))
for p in ['shape I would pick', 'The shape here is right', 'Comments describe what is', 'count for nothing', 'is the floor', 'Ideal.', 'Not verified: none', 'Purpose: Justified', 'at least one confirmed finding is blocker or major', 'every review host', 'reviewers', 'I would pick']:
    n = sum(1 for pr, s, b in bodies if pr != 5022 and p in b)
    print("  %r: %d other summaries" % (p, n))
print("\n=== phrase recurrence in OTHER inline comments (not PR 5022)")
others = [r for r in rows if r['pr'] != 5022]
for p in ['trying to split this diff', 'split this diff into', 'landable steps', "a reason I'm missing", "Not about the code", "more fixture than it's worth", 'While reviewing I', 'hunk header', 'I never proved', 'opcode census', 'see my note', "I didn't check whether", "I can't find", 'land on their own', 'If this lands as more than one commit']:
    hits = [r for r in others if p in r['body']]
    prs = sorted({r['pr'] for r in hits})
    print("  %r: %d comments in %d other PRs %s" % (p, len(hits), len(prs), ('e.g. PR ' + ', '.join(str(x) for x in prs[:8])) if hits else ''))
