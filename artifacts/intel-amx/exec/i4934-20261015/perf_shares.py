#!/usr/bin/env python3
"""perf_shares.py <results dir>: per-arm function shares (mean over reps) from the .bysym.txt files of perf-fix.sh,
with the symbol names reduced to '<class>::<function>' (template arguments and parameter lists dropped) so that the
same function compares across binaries. Prints one table per cell: share per arm and fixoff minus headoff, for every
function above 0.1 % in any arm, sorted by |delta|. The .bysym.txt files are sorted by symbol name, not by overhead."""
import glob, os, re, sys, statistics
from collections import defaultdict
SYM = re.compile(r'^\s*([\d.]+)%\s+\[([.k])\]\s+(.*?)\s*$')
def short(name):
    # drop the parameter list, then every template argument list, then the leading return type and namespaces
    depth = 0; out = []
    for ch in name:
        if ch == '<': depth += 1
        elif ch == '>': depth -= 1
        elif depth == 0: out.append(ch)
    s = ''.join(out)
    s = s.split('(')[0]
    s = s.strip()
    if ' ' in s: s = s.split(' ')[-1]
    parts = s.split('::')
    return '::'.join(parts[-2:]) if len(parts) >= 2 else s
runs = defaultdict(lambda: defaultdict(list))
for path in sorted(glob.glob(os.path.join(sys.argv[1], '*.bysym.txt'))):
    cell, arm, rep = os.path.basename(path)[:-len('.bysym.txt')].split('__')
    acc = defaultdict(float)
    for line in open(path, errors='replace'):
        m = SYM.match(line)
        if m:
            key = ('[k] ' if m.group(2) == 'k' else '') + short(m.group(3))
            acc[key] += float(m.group(1))
    runs[cell][arm].append(acc)
for cell in sorted(runs):
    arms = [a for a in ['headoff', 'fixoff', 'newoff', 'head', 'fix', 'new'] if a in runs[cell]]
    mean = {a: defaultdict(float) for a in arms}
    for a in arms:
        n = len(runs[cell][a])
        for acc in runs[cell][a]:
            for k, v in acc.items(): mean[a][k] += v / n
    keys = {k for a in arms for k, v in mean[a].items() if v >= 0.1}
    ref, hl = (('headoff', 'fixoff') if 'headoff' in arms else (arms[0], arms[1]))
    rows = sorted(keys, key=lambda k: -abs(mean[hl][k] - mean[ref][k]))
    print(f"\n## {cell}: share of samples on our CPUs (%), mean over {len(runs[cell][arms[0]])} reps; delta = {hl} - {ref}")
    print("| function | " + " | ".join(arms) + " | delta |")
    print("|---|" + "---|" * (len(arms) + 1))
    for k in rows[:28]:
        print(f"| {k[:60]} | " + " | ".join(f"{mean[a][k]:.2f}" for a in arms) + f" | {mean[hl][k] - mean[ref][k]:+.2f} |")
    print("| total listed | " + " | ".join(f"{sum(mean[a].values()):.1f}" for a in arms) + " | |")
