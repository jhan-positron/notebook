#!/usr/bin/env python3
"""Compare the greedy smoke outputs of the vnnik-20260914 campaign.

Reads <dir>/<arm>.tokens (runtron --output-token-file: one row of generated token ids per
user; every integer on a row is a token id) for the arms base, vnni, off, vnnioff and the
A/A repeats base2, vnni2, and
prints, for each pair, how many leading tokens agree and where the first difference is.
The expectation stated in the design (section 5): base and vnni agree for a long run and
differ only at a near-tie, because the dense pages give bit-identical scores and only the
partial page's add order differs; off and vnnioff differ from both earlier for the same
reason (AVX add order versus AMX).
Usage: compare_tokens.py DIR
"""
import os
import re
import sys

d = sys.argv[1]
arms = ["base", "vnni", "off", "vnnioff", "base2", "vnni2"]
rows = {}
for a in arms:
    p = os.path.join(d, a + ".tokens")
    if not os.path.exists(p):
        continue
    lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
    if not lines:
        continue
    rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("smoke token rows:", {a: len(r) for a, r in rows.items()})
# The two same-arm pairs are the A/A controls: they must read identical before the
# base-vs-vnni row means anything (a repeated run of the same binary with the same
# recipe must reproduce its tokens).
pairs = [("base", "base2"), ("vnni", "vnni2"), ("base", "vnni"), ("off", "vnnioff"), ("base", "off"), ("vnni", "vnnioff")]
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
        print(f"{a} vs {b}: first difference at generated token {first} of {n} "
              f"({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens")
