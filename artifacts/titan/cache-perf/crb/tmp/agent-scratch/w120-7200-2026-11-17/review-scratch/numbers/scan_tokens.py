import re, html, pickle, statistics, itertools, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
s = open('report-snapshot.html').read()
s2 = re.sub(r'<style.*?</style>', '', s, flags=re.S)
# keep titles and text; drop attributes
txt = re.sub(r'<[^>]+>', ' ', s2)
txt = html.unescape(txt)
d = pickle.load(open('raw.pkl', 'rb'))
A, B, D = d['A'], d['B'], d['D']
med = statistics.median
f2 = lambda x: '%.2f' % x
allowed = {}
def add(x, why): allowed.setdefault(f2(x), set()).add(why)
groups = {}
for name, ivs in D.items():
    for i in ivs:
        add(i['total'], 'interval %s' % name)
        groups.setdefault((name, i['kernel']), []).append(i['total'])
for (name, k), v in groups.items(): add(med(v), 'median %s %s' % (name, k))
for k, (vals, h, iv, l) in A.items():
    for v in vals: add(v, 'interval A %s' % (k,))
    add(med(vals), 'median A')
    add(h['load'], 'load')
for k, vals in B.items():
    for v in vals: add(v, 'interval B %s' % (k,))
    add(med(vals), 'median B')
toks = re.findall(r'(?<![\d.])\d+\.\d\d(?![\d])', txt)
from collections import Counter
c = Counter(toks)
unk = sorted(t for t in c if t not in allowed)
print('distinct 2-decimal tokens', len(c), 'not interval/median/load of part A:', len(unk))
for t in unk:
    ctxs = [txt[max(0, m.start()-70):m.end()+30].replace('\n', ' ') for m in re.finditer(r'(?<![\d.])' + re.escape(t) + r'(?![\d])', txt)]
    print(t, c[t], '|', re.sub(r'\s+', ' ', ctxs[0]))
