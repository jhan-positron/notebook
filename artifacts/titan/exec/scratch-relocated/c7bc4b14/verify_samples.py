import json, collections
p='/home/positron-perf/positron/runs/churn-r1/isol.samples.jsonl'
rows=[json.loads(l) for l in open(p) if l.strip()]
print("rows", len(rows), "keys", list(rows[0].keys()))
s=json.dumps(rows[len(rows)//2])
print("mid row (first 1800 chars):", s[:1800])
agg=collections.defaultdict(collections.Counter)
def walk(o, path=''):
    if isinstance(o, dict):
        if 'psr' in o:
            name = o.get('name') or o.get('comm') or o.get('command') or o.get('tid') or path
            agg[str(name)][str(o['psr'])] += 1
        for k, v in o.items(): walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        for v in o: walk(v, path)
for r in rows: walk(r)
print("== psr counts per thread name over all samples (name: {cpu: samples})")
for n, c in sorted(agg.items()): print(" ", n, dict(sorted(c.items(), key=lambda x: -x[1])[:10]))
print("== per-sample frequency fields (first 6 rows, any key containing 'freq' or 'khz')")
for r in rows[:6]:
    for k, v in r.items():
        if 'freq' in k.lower() or 'khz' in k.lower() or k in ('watch','cpus'):
            print("  t=%s %s=%s" % (r.get('t'), k, json.dumps(v)[:300]))
