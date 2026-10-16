#!/usr/bin/env python3
"""annot_compare.py <annotate-all.txt.gz> <objdump inst-1.s> [label]: the first (hottest) symbol section of a perf
annotate --stdio listing (apply_page_range), with: samples per instruction class, the hottest 24 instructions, and
the share of the function's samples inside each loop of the objdump listing (a loop = a backward jump; loops of
at most 150 instructions; nested loops are listed by their start)."""
import gzip, re, sys
from collections import defaultdict
path, dump = sys.argv[1], sys.argv[2]
label = sys.argv[3] if len(sys.argv) > 3 else path
L = re.compile(r'^\s*([\d.]+)\s*:\s*([0-9a-f]+):\s+(\S+)\s*(.*)$')
rows = []
with gzip.open(path, 'rt', errors='replace') as f:
    header = f.readline()
    for line in f:
        if line.startswith(' Percent |'): break
        m = L.match(line)
        if m: rows.append((float(m.group(1)), int(m.group(2), 16), m.group(3), m.group(4).strip()))
m = re.search(r'\((\d+) samples', header); total = int(m.group(1)) if m else 0
print(f"\n##### {label}: first section, {total} samples, {len(rows)} instructions, pct sum {sum(p for p, *_ in rows):.1f}")
def klass(mn, ops):
    if mn.startswith('vdpbf16ps'): return 'vdpbf16ps (bf16 dot)'
    if mn.startswith('vfmadd') or mn.startswith('vfnmadd'): return 'vfmadd (fp32 fma)'
    if mn.startswith(('vmovaps', 'vmovups', 'vmovdqa', 'vmovdqu', 'vbroadcastss', 'vpbroadcastd', 'vmovss', 'vmovd')):
        src = ops.split(',')[0] if ',' in ops else ops
        return 'vector load (memory source)' if '(' in src else 'vector mov/store'
    if mn.startswith('v'): return 'other vector (' + mn[:9] + ')' if mn[:4] in ('vext', 'vsha', 'vshu', 'vper') else 'other vector'
    if mn.startswith('j'): return 'branch'
    if mn in ('cmp', 'test', 'cmpb', 'cmpq', 'cmpl'): return 'cmp/test'
    if mn.startswith('mov') and '(' in ops and ops.index('(') < (ops.index(',') if ',' in ops else 99): return 'scalar load'
    if mn.startswith('mov'): return 'scalar mov/store'
    if mn in ('pause',): return 'pause'
    return 'other scalar'
by = defaultdict(float)
for p, a, mn, ops in rows: by[klass(mn, ops)] += p
print("| class | % of function |"); print("|---|---|")
for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:14]: print(f"| {k} | {v:.2f} |")
print("\nhottest 24 instructions:")
for p, a, mn, ops in sorted(rows, key=lambda r: -r[0])[:24]: print(f"  {p:6.2f}%  {a:x}: {mn} {ops[:60]}")
# loops of the objdump listing
ins = []
for line in open(dump, errors='replace'):
    m = re.match(r'^\s*([0-9a-f]+):\s+(\S+)\s*(.*)$', line)
    if m: ins.append((int(m.group(1), 16), m.group(2), m.group(3)))
addr = {a: i for i, (a, _, _) in enumerate(ins)}
loops = []
for i, (a, mn, ops) in enumerate(ins):
    if mn.startswith('j'):
        m = re.match(r'^([0-9a-f]+)', ops)
        if m:
            t = int(m.group(1), 16)
            if t < a and t in addr and i - addr[t] <= 150: loops.append((addr[t], i))
pct_at = {a: p for p, a, _, _ in rows}
print("\nloops (objdump idx range, instructions, % of the function's samples inside, hottest mnemonics):")
seen = set()
for j, i in sorted(loops, key=lambda l: -(sum(pct_at.get(ins[k][0], 0) for k in range(l[0], l[1] + 1)))):
    s = sum(pct_at.get(ins[k][0], 0) for k in range(j, i + 1))
    if s < 0.5 or (j, i) in seen: continue
    seen.add((j, i))
    mns = defaultdict(float)
    for k in range(j, i + 1): mns[ins[k][1]] += pct_at.get(ins[k][0], 0)
    top = ', '.join(f"{m} {v:.1f}" for m, v in sorted(mns.items(), key=lambda kv: -kv[1])[:4])
    print(f"  idx {j:4d}-{i:4d} n={i - j + 1:3d} {s:6.2f}%  [{top}]")
