#!/usr/bin/env python3
"""Compare the greedy smoke outputs of the vnnik6-20260916 campaign: <dir>/<arm>.tokens
(runtron --output-token-file, one row of token ids per user). Arms: base and base2 (the main
binary twice = A/A control), headoff (PR head with the layout off: expected identical to base,
since a row-major slot runs the same dotter), vnni and vnni2 (PR head with the layout on,
twice). base vs vnni diverged at generated token 5 in the 2026-09-15 run.
Usage: compare_tokens.py DIR
"""
import os
import re
import sys

d = sys.argv[1]
arms = ["base", "base2", "headoff", "headoff2", "vnni", "vnni2"]
rows = {}
for a in arms:
    p = os.path.join(d, a + ".tokens")
    if not os.path.exists(p):
        continue
    lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
    if lines:
        rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("smoke token rows:", {a: len(r) for a, r in rows.items()})
pairs = [("base", "base2", "A/A of the main binary"), ("vnni", "vnni2", "A/A of the VNNI binary"),
         ("headoff", "headoff2", "A/A of the headoff binary (run only when the base build failed)"),
         ("base", "headoff", "main vs PR head with the layout off: expected identical"),
         ("base", "vnni", "main vs VNNI layout: diverged at token 5 on 2026-09-15"),
         ("headoff", "vnni", "PR head, layout off vs on")]
for a, b, why in pairs:
    if a not in rows or b not in rows:
        print(f"{a} vs {b}: missing ({why})")
        continue
    ra, rb = rows[a], rows[b]
    n = min(len(ra), len(rb))
    first = next((i for i in range(n) if ra[i] != rb[i]), None)
    if first is None:
        print(f"{a} vs {b}: identical for {n} tokens (lengths {len(ra)} / {len(rb)}) [{why}]")
    else:
        print(f"{a} vs {b}: first difference at generated token {first} of {n} ({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens [{why}]")
