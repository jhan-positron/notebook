# refs.py - reference check: every [RefN] used in the body has an entry, every entry is used, numbering is in order of first use, every named file exists, internal anchors resolve.
import re, html, os
P = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t = open(P).read()
i = t.index('<h2 id="refs">')
body, refs = t[:i], t[i:]
used = [int(x) for x in re.findall(r'\[Ref(\d+)\]', body)]
order = []
for u in used:
    if u not in order: order.append(u)
defs = [int(x) for x in re.findall(r'\[Ref(\d+)\]', refs)]
print('used distinct', len(order), 'max', max(order), 'defined (occurrences in ref section)', len(defs), 'distinct', len(set(defs)))
print('used but not defined:', sorted(set(order) - set(defs)))
print('defined but not used in body:', sorted(set(defs) - set(order)))
print('first-use order is ascending:', order == sorted(order), [o for a, o in zip(sorted(order), order) if a != o][:10])
hrefs = re.findall(r'href="([^"]+)"', t)
ids = set(re.findall(r'id="([^"]+)"', t))
print('hrefs', len(hrefs), 'distinct', len(set(hrefs)))
bad = [h for h in set(hrefs) if h.startswith('#') and h[1:] not in ids]
print('internal anchors without target:', bad)
print('non-internal hrefs:', [h for h in set(hrefs) if not h.startswith('#')][:20])
# reference entries: paths
R = '/home/jhan/workspace/titan/cache-perf/crb/results'; S = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
txt = html.unescape(re.sub(r'<[^>]+>', '', refs))
entries = re.findall(r'\[Ref(\d+)\]\s*(\S+)', txt)
miss = 0
for n, p in entries:
    p = p.rstrip(':,')
    if p.startswith('R/'): q = R + p[1:]
    elif p.startswith('S/'): q = S + p[1:]
    elif p.startswith('/'): q = p
    else:
        print('Ref', n, 'no path token:', p); continue
    if not os.path.exists(q):
        miss += 1; print('MISSING Ref', n, q)
print('entries', len(entries), 'missing files', miss)
