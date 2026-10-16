#!/usr/bin/env python3
"""bench_tables.py: tables from tail_bench CSV files.

usage: bench_tables.py <csv> [<csv> ...]  -> markdown on stdout

Per scenario and kv_mul: a table of median ns per visit by n live rows (1..15)
for every arm, the dotter minus reader difference, and the per-step conversion
for the qwen-3-4b tp2 8-user decode step (see STEP below). With several CSV
files (repeat runs) the median over the runs of each cell's median is used and
the spread between runs is reported.
"""
import csv
import statistics
import sys
from collections import defaultdict

# The decode step the conversion refers to (exec/results/i4934-r2/attn-fixoff-p1024.txt
# and the E2-cpu campaign): qwen-3-4b, tp2, 8 users, prompt 1024, kill switch.
STEP = dict(
    forward_us=14194.6,       # mean decode forward, fixoff, prompt 1024
    layers=36,
    kv_heads_per_engine=4,    # 8 KV heads / tp2
    users=8,
    workers=20,               # attention threads per engine in the trace
    gap_pct=1.1,              # fixoff vs headoff at tp2 prompt 1024 (round 2)
)
STEP['visits_per_worker'] = STEP['layers'] * STEP['kv_heads_per_engine'] * STEP['users'] / STEP['workers']
STEP['gap_us'] = STEP['forward_us'] * STEP['gap_pct'] / 100


def load(paths):
    cells = defaultdict(list)   # (scenario, arm, kv_mul, n) -> [median_ns per run]
    checks = {}
    header = []
    for p in paths:
        for row in csv.reader(open(p)):
            if not row or row[0].startswith('#'):
                if row and row[0].startswith('#'):
                    header.append(row[0])
                continue
            if row[0] == 'check':
                checks[(row[1], row[2], p)] = row[4]
                continue
            scenario, arm, kv_mul, n, iters, med, p10, p90, mean = row
            cells[(scenario, arm, int(kv_mul), int(n))].append(float(med))
    return cells, checks, header


def main():
    paths = sys.argv[1:]
    cells, checks, header = load(paths)
    print('# tail_bench results\n')
    for h in header:
        print(h)
    print()
    print('Correctness (max relative error of every arm against a double-precision reference, all n):\n')
    print('| arm | kv_mul | run | max rel err |')
    print('|---|---|---|---|')
    for (arm, kv, p), v in sorted(checks.items()):
        print(f'| {arm} | {kv} | {p.rsplit("/", 1)[-1]} | {v} |')
    print()
    scenarios = []
    arms = []
    for (sc, arm, kv, n) in cells:
        if sc not in scenarios:
            scenarios.append(sc)
        if arm not in arms:
            arms.append(arm)
    for sc in scenarios:
        for kv in (4, 8):
            print(f'## scenario {sc}, kv_mul {kv}: median ns per visit (median over {len(paths)} runs)\n')
            print('| n | ' + ' | '.join(arms) + ' | dotter - reader | run spread (max over arms) |')
            print('|---|' + '---|' * (len(arms) + 2))
            for n in range(1, 16):
                vals = {}
                spread = 0.0
                for arm in arms:
                    v = cells.get((sc, arm, kv, n), [])
                    if not v:
                        continue
                    vals[arm] = statistics.median(v)
                    if len(v) > 1:
                        spread = max(spread, (max(v) - min(v)) / max(1e-9, statistics.median(v)) * 100)
                if not vals:
                    continue
                diff = vals.get('dotter', float('nan')) - vals.get('reader', float('nan'))
                print(f'| {n} | ' + ' | '.join(f'{vals.get(a, float("nan")):.0f}' for a in arms)
                      + f' | {diff:+.0f} | {spread:.0f} % |')
            print()
            if kv == 4:
                # Conversion: a visit scores on average about 8 rows (1 to 15 over a block's life).
                ds = [cells.get((sc, 'dotter', kv, n), [float('nan')]) for n in range(1, 16)]
                rs = [cells.get((sc, 'reader', kv, n), [float('nan')]) for n in range(1, 16)]
                d_mean = statistics.mean(statistics.median(x) for x in ds)
                r_mean = statistics.mean(statistics.median(x) for x in rs)
                extra_ns = d_mean - r_mean
                per_step_us = extra_ns * STEP['visits_per_worker'] / 1000
                print(f'Per-step conversion (kv_mul 4): mean over n of dotter {d_mean:.0f} ns, '
                      f'reader {r_mean:.0f} ns, difference {extra_ns:+.0f} ns per visit. '
                      f'x {STEP["visits_per_worker"]:.1f} tail visits per worker per step = '
                      f'{per_step_us:+.1f} us per step, against the measured gap of '
                      f'{STEP["gap_us"]:.0f} us ({STEP["gap_pct"]} % of {STEP["forward_us"]:.0f} us).\n')
                best = min((a for a in arms if a != 'reader'),
                           key=lambda a: statistics.mean(statistics.median(cells.get((sc, a, kv, n), [float('inf')])) for n in range(1, 16)))
                b_mean = statistics.mean(statistics.median(cells.get((sc, best, kv, n), [float('nan')])) for n in range(1, 16))
                print(f'Fastest row-major arm in this scenario: {best} ({b_mean:.0f} ns mean over n, '
                      f'{b_mean - r_mean:+.0f} ns vs reader, {b_mean - d_mean:+.0f} ns vs dotter).\n')


if __name__ == '__main__':
    main()
