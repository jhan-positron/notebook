#!/usr/bin/env python3
"""Range of the 1-thread asm read rate at 8 MiB over CPUs 0-119 (per-core sweep of 2026-11-02)."""
import sys, statistics
base = '/home/jhan/workspace/titan/cache-perf/crb/results/followup3-20261102T031936Z/'
for sweep in (1, 2):
    best = {}; reps = {}
    cpu = None
    for ln, line in enumerate(open(base + f'percore-asmread-{sweep}.csv'), 1):
        line = line.strip()
        if line.startswith('-- cpu'):
            cpu = int(line.split()[2]); reps[cpu] = []
        elif line.startswith('asmread,'):
            f = line.split(',')
            if f[3] == 'best':
                best[cpu] = float(f[6])
            else:
                reps[cpu].append(float(f[6]))
    vals = sorted(best.values())
    print(f'sweep {sweep}: n={len(best)} best min={vals[0]} max={vals[-1]} median={statistics.median(vals)}')
    allreps = [v for c in reps for v in reps[c]]
    print(f'   all reps: n={len(allreps)} min={min(allreps)} max={max(allreps)}')
    lo = sorted(best.items(), key=lambda kv: kv[1])[:6]
    hi = sorted(best.items(), key=lambda kv: kv[1])[-6:]
    print('   lowest:', lo)
    print('   highest:', hi)
    print('   cpu0..5:', [(c, best[c], reps[c]) for c in range(6)])
    print('   cpu64, 119:', best.get(64), best.get(119))
    m0 = [best[c] for c in range(0, 64)]; m1 = [best[c] for c in range(64, 120)]
    print(f'   mesh0 (cpus 0-63): min={min(m0)} max={max(m0)} median={statistics.median(m0)}')
    print(f'   mesh1 (cpus 64-119): min={min(m1)} max={max(m1)} median={statistics.median(m1)}')
