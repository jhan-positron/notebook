from pathlib import Path
from statistics import mean, median
from collections import defaultdict

ROOT = Path('/home/jhan/workspace/titan/cache-perf/asimov')
CPUS = {2:(2,3), 4:(3,2), 6:(4,3), 8:(5,2)}
REGIONS = {0:(1,3), 1:(2,4), 2:(3,3), 3:(4,4), 4:(5,3)}

def corr(x, y):
    mx, my = mean(x), mean(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y)) / (sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))**0.5

runs = {}
for run in ('002', '004'):
    cells = {}
    for cpu, cp in CPUS.items():
        for region, rp in REGIONS.items():
            path = ROOT / f'results/membench-jibin-{run}/results/19700101T000000Z/latency-ocm-region{region}-cpu{cpu}.csv'
            rows = [line.split(',') for line in path.read_text().splitlines() if line.startswith('ocm,')]
            best = float(next(row[5] for row in rows if row[2] == 'best'))
            timed = [row for row in rows if row[2] != 'best']
            bp = next(row for row in timed if float(row[5]) == best)
            cells[cpu,region] = dict(best=best, dist=sum(abs(a-b) for a,b in zip(cp,rp)), l2=[float(r[8]) for r in timed], l3=[float(r[9]) for r in timed], best_l2=float(bp[8]), best_l3=float(bp[9]))
    runs[run] = cells
    print(f'RUN {run}: 20 CPU/region cells, all timed passes; L2 column8, L3 column9 (zero-based).')
    for event in ('l2', 'l3'):
        for label, vals in [('all passes',[v for c in cells.values() for v in c[event]]), ('per-cell mean',[mean(c[event]) for c in cells.values()]), ('per-cell median',[median(c[event]) for c in cells.values()]), ('best-pass',[c['best_'+event] for c in cells.values()])]:
            print(f'  {event} {label}: {min(vals):.9f} to {max(vals):.9f}')
        cpu_means = {cpu:mean(v for (c,r),d in cells.items() if c==cpu for v in d[event]) for cpu in CPUS}
        region_means = {region:mean(v for (c,r),d in cells.items() if r==region for v in d[event]) for region in REGIONS}
        print(' ',event,'per-CPU means',cpu_means)
        print(' ',event,'per-region means',region_means)

keys = list(runs['002'])
x = [runs['002'][k]['best'] for k in keys]
y = [runs['004'][k]['best'] for k in keys]
dist = [runs['002'][k]['dist'] for k in keys]
print('Paired best latency over all20 CPU/region cells, raw Pearson r:',corr(x,y))
xmeans = {d:mean(v for v,k in zip(x,dist) if k==d) for d in set(dist)}
ymeans = {d:mean(v for v,k in zip(y,dist) if k==d) for d in set(dist)}
print('Pearson r after subtracting each run own distance-group mean:',corr([v-xmeans[d] for v,d in zip(x,dist)],[v-ymeans[d] for v,d in zip(y,dist)]))
