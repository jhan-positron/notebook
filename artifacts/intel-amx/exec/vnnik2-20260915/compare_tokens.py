#!/usr/bin/env python3
"""Compare the greedy smoke outputs of the vnnik2-20260915 campaign: <dir>/<arm>.tokens
(runtron --output-token-file, one row of token ids per user). The K store is pure data
movement, so every VNNI arm (vnni = Monday's binary, vnni0/a/b/ab = the new binary with
the switches) must produce identical tokens; ab vs ab2 is the A/A control.
Usage: compare_tokens.py DIR
"""
import os
import re
import sys

d = sys.argv[1]
arms = ["vnni", "vnni0", "a", "b", "ab", "ab2"]
rows = {}
for a in arms:
    p = os.path.join(d, a + ".tokens")
    if not os.path.exists(p):
        continue
    lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
    if lines:
        rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("smoke token rows:", {a: len(r) for a, r in rows.items()})
pairs = [("ab", "ab2"), ("vnni", "vnni0"), ("vnni0", "a"), ("vnni0", "b"), ("vnni0", "ab"), ("vnni", "ab")]
for a, b in pairs:
    if a not in rows or b not in rows:
        print(f"{a} vs {b}: missing")
        continue
    ra, rb = rows[a], rows[b]
    n = min(len(ra), len(rb))
    first = next((i for i in range(n) if ra[i] != rb[i]), None)
    if first is None:
        print(f"{a} vs {b}: identical for {n} tokens (lengths {len(ra)} / {len(rb)})")
    else:
        print(f"{a} vs {b}: first difference at generated token {first} of {n} ({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens")
