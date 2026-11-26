# recheck_short.py - recompute the numbers of the Short version and its detail bullets from facts.json (read-only).
import json, statistics as st
S = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
iv = json.load(open(S + '/facts.json'))['intervals']
ds = sorted(set((r['dataset'], r['part'], r['role'], r['speed_MTps']) for r in iv))
for d in ds: print(d, sum(1 for r in iv if (r['dataset'], r['part'], r['role'], r['speed_MTps']) == d))
def sel(**kw):
    return [r for r in iv if all(r.get(k) == v for k, v in kw.items())]
# sentence 1: part C, kernel read against oldread of the same process and round
C = [r for r in iv if r['part'] == 'C' and r['speed_MTps'] == 7200 and r['role'] == 'rerun']
print('part C intervals', len(C), sorted(set(r['kernel'] for r in C)))
drops = {}
for r in C:
    if r['kernel'] != 'read': continue
    o = [x for x in C if x['kernel'] == 'oldread' and x['proc_key'] == r['proc_key'] and x['round'] == r['round']]
    assert len(o) == 1
    d = (1 - r['GBps'] / o[0]['GBps']) * 100
    drops.setdefault(r['kernel_before'], []).append(d)
for k, v in drops.items(): print('read after', k, 'n', len(v), 'min %.2f max %.2f' % (min(v), max(v)))
allv = [x for v in drops.values() for x in v]
print('all pairs', len(allv), 'min %.2f max %.2f' % (min(allv), max(allv)))
