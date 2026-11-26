# svgtexts.py - list the text labels of the three Figure 1 variants and compare the numeric labels.
import re, html, sys
P = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
t = open(P).read()
out = {}
for c in ('f1w', 'f1m', 'f1n'):
    m = re.search(r'<svg class="%s".*?</svg>' % c, t, re.S)
    s = m.group(0)
    texts = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'<text[^>]*>(.*?)</text>', s, re.S)]
    out[c] = texts
    print(c, len(texts))
nums = {c: sorted(x for x in out[c] if re.match(r'^[0-9.]+( % to [0-9.]+)?( %)?$', x) and '.' in x) for c in out}
print('numeric label lists equal:', nums['f1w'] == nums['f1m'] == nums['f1n'], len(nums['f1w']))
if '-v' in sys.argv:
    for x in out['f1w']: print(repr(x))
