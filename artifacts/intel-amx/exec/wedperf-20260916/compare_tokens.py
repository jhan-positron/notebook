#!/usr/bin/env python3
"""Compare the greedy smoke outputs of the wedperf-20260916 campaign: <dir>/<cell>__<attn>__<arm>.tokens
(runtron --output-token-file, one row of token ids per user). For every (cell, attn) with both
arms present: first generated token where base and target differ, or "identical".
Expectation: models on the AMX path (128-dim heads, 4 query heads per KV head, bf16 KV) may
diverge (AMX and AVX never agree bit for bit, see memory runtron-determinism-recipe); models
whose K layout changes but run the software reader may diverge from add-order changes;
head-64 models (gpt-oss) take neither path and must be identical.
Usage: compare_tokens.py DIR
"""
import os
import re
import sys

d = sys.argv[1]
rows = {}
for f in sorted(os.listdir(d)):
    if not f.endswith(".tokens"):
        continue
    parts = f[:-len(".tokens")].split("__")
    if len(parts) != 3:
        continue
    lines = [l for l in open(os.path.join(d, f), errors="replace").read().splitlines() if l.strip()]
    if lines:
        rows[tuple(parts)] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("# smoke token comparison (base vs target, 1 user greedy, 128 tokens)")
# every attempted smoke leaves <cell>__<attn>__<arm>.log.attemptN before runtron starts (campaign.sh
# run_one), so a cell whose smokes failed in both arms still gets a "missing tokens" line
attempted = set()
for f in os.listdir(d):
    m = re.match(r"^(.+)__(.+)__(.+)\.log(\.attempt\d+)?$", f)
    if m:
        attempted.add((m.group(1), m.group(2)))
keys = sorted({(c, a) for c, a, _ in rows} | attempted)
for cell, attn in keys:
    ra, rb = rows.get((cell, attn, "base")), rows.get((cell, attn, "target"))
    if ra is None or rb is None:
        print(f"{cell} {attn}: missing tokens (base={ra is not None}, target={rb is not None})")
        continue
    n = min(len(ra), len(rb))
    first = next((i for i in range(n) if ra[i] != rb[i]), None)
    if first is None:
        print(f"{cell} {attn}: identical for {n} tokens (lengths {len(ra)} / {len(rb)})")
    else:
        print(f"{cell} {attn}: first difference at generated token {first} of {n} ({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens")
