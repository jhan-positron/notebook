import json, collections
p='/home/positron-perf/positron/runs/churn-r1/isol.samples.jsonl'
rows=[json.loads(l) for l in open(p) if l.strip()]
print("rows", len(rows), "span_s %.0f" % (rows[-1]['t']-rows[0]['t']))
per=collections.defaultdict(collections.Counter)
for r in rows:
    for c,v in r['khz'].items(): per[c][v]+=1
for c in sorted(per, key=int):
    print(" cpu%s khz samples:" % c, dict(sorted(per[c].items(), key=lambda x:-x[1])))
foreign=[(round(r['t']-rows[0]['t']), r['foreign_running_on_watch']) for r in rows if r['foreign_running_on_watch']]
print("samples with foreign threads on 120-127:", len(foreign))
for t,f in foreign[:12]: print("  t+%ss" % t, json.dumps(f)[:300])
nth=collections.Counter(len(r['harness_threads']) for r in rows)
print("harness thread count per sample:", dict(nth))
names=collections.Counter(h['comm'] for r in rows for h in r['harness_threads'])
print("thread comm counts:", dict(names))
allowed=collections.Counter((h['comm'],h['allowed']) for r in rows for h in r['harness_threads'])
print("comm/allowed:", dict(allowed))
la=[r['loadavg'].split()[0] for r in rows]
print("loadavg1 first/max/last:", la[0], max(la, key=float), la[-1])
