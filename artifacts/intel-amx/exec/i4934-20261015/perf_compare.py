#!/usr/bin/env python3
"""perf_compare.py <results dir> [--min-delta 0.3]: compare the perf runs of perf-fix.sh between arms.

Reads <cell>__<arm>__rep<N>.stat.txt (perf stat text: a count, an event name) and .bysym.txt (perf report by
symbol: "  12.34%  [.] name"). Per cell: the counters per arm (mean over repetitions) with the ratio to headoff,
then the symbols whose share differs between fixoff and headoff by at least --min-delta percentage points.
"""
import glob
import os
import re
import statistics
import sys
from collections import defaultdict

ARMS = ['headoff', 'fixoff', 'newoff']
STAT_RE = re.compile(r'^\s*([\d,]+)\s+(\S+)')
SYM_RE = re.compile(r'^\s*([\d.]+)%\s+\[([.k])\]\s+(.*)$')


def read_stat(path):
    out = {}
    for line in open(path, errors='replace'):
        m = STAT_RE.match(line)
        if m and not line.strip().endswith('seconds time elapsed'):
            out[m.group(2)] = int(m.group(1).replace(',', ''))
    return out


def read_syms(path):
    out = {}
    for line in open(path, errors='replace'):
        m = SYM_RE.match(line)
        if m:
            key = ('[k] ' if m.group(2) == 'k' else '') + m.group(3).strip()
            out[key] = out.get(key, 0.0) + float(m.group(1))
    return out


def main():
    res = sys.argv[1]
    min_delta = 0.3
    if '--min-delta' in sys.argv:
        min_delta = float(sys.argv[sys.argv.index('--min-delta') + 1])
    runs = defaultdict(lambda: defaultdict(list))  # cell -> arm -> [(stat, syms)]
    for path in sorted(glob.glob(os.path.join(res, '*.bysym.txt'))):
        base = os.path.basename(path)[:-len('.bysym.txt')]
        cell, arm, rep = base.split('__')
        stat_path = os.path.join(res, base + '.stat.txt')
        stat = read_stat(stat_path) if os.path.exists(stat_path) else {}
        runs[cell][arm].append((stat, read_syms(path), rep))
    for cell in sorted(runs):
        print(f"\n## {cell}")
        arms = [a for a in ARMS if a in runs[cell]] + sorted(a for a in runs[cell] if a not in ARMS)
        events = []
        for a in arms:
            for st, _, _ in runs[cell][a]:
                for e in st:
                    if e not in events:
                        events.append(e)
        print("| arm | reps | " + " | ".join(events) + " | IPC | LLC-load-misses per 1e9 insn |")
        print("|---|---|" + "---|" * (len(events) + 2))
        ref = {}
        for a in arms:
            means = {}
            for e in events:
                vals = [st[e] for st, _, _ in runs[cell][a] if e in st]
                means[e] = statistics.mean(vals) if vals else float('nan')
            ipc = means.get('instructions', float('nan')) / means.get('cycles', float('nan')) if means.get('cycles') else float('nan')
            mpi = means.get('LLC-load-misses', float('nan')) / means.get('instructions', float('nan')) * 1e9 if means.get('instructions') else float('nan')
            if a == 'headoff':
                ref = dict(means, IPC=ipc, MPI=mpi)
            cells = []
            for e in events:
                v = means[e]
                r = f" ({v / ref[e]:.4f}x)" if ref and ref.get(e) else ''
                cells.append(f"{v:,.0f}{r}")
            cells.append(f"{ipc:.3f}" + (f" ({ipc / ref['IPC']:.4f}x)" if ref and ref.get('IPC') else ''))
            cells.append(f"{mpi:,.0f}" + (f" ({mpi / ref['MPI']:.4f}x)" if ref and ref.get('MPI') else ''))
            print(f"| {a} | {len(runs[cell][a])} | " + " | ".join(cells) + " |")
        # symbol shares
        share = {}
        for a in arms:
            acc = defaultdict(list)
            for _, syms, _ in runs[cell][a]:
                for s, v in syms.items():
                    acc[s].append(v)
            n = len(runs[cell][a])
            share[a] = {s: sum(v) / n for s, v in acc.items()}  # a missing rep counts 0
        if 'headoff' in share and 'fixoff' in share:
            keys = set(share['headoff']) | set(share['fixoff'])
            rows = []
            for s in keys:
                h = share['headoff'].get(s, 0.0)
                f = share['fixoff'].get(s, 0.0)
                nw = share.get('newoff', {}).get(s, 0.0)
                if abs(f - h) >= min_delta or max(h, f) >= 3.0:
                    rows.append((f - h, s, h, f, nw))
            rows.sort(key=lambda r: -abs(r[0]))
            print(f"\nsymbol shares (% of samples on our CPUs; mean over reps); fixoff - headoff >= {min_delta} pt or share >= 3 %:")
            print("| fixoff - headoff | headoff | fixoff | newoff | symbol |")
            print("|---|---|---|---|---|")
            for d, s, h, f, nw in rows[:40]:
                print(f"| {d:+.2f} | {h:.2f} | {f:.2f} | {nw:.2f} | {s[:110]} |")
            tot = {a: sum(share[a].values()) for a in share}
            print("listed share totals: " + ", ".join(f"{a} {t:.1f} %" for a, t in tot.items()))


if __name__ == '__main__':
    main()
