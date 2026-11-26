#!/usr/bin/env python3
"""Review finding R3: truncation split against round-to-nearest split in the block form.

Reads the saved output of the design check verify-math/vm_checks.py (part E).
That check runs the specified block form (truncation split) and, for three
scenarios, a variant whose pieces are rounded to nearest. This script prints,
per scenario, the error of both against the float64 computation, the ratio
nearest / truncation, and the number of bf16 output words that differ between
the two rules. It computes nothing else.

Usage: python3 r3_rule_variants.py [path of vm_checks.out]
Without an argument it reads ../verify-math/vm_checks.out beside this script,
or the copy in the project folder.
"""
import re
import sys

import os

HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = (os.path.join(HERE, "..", "verify-math", "vm_checks.out"),
              "/home/jhan/workspace/intel-AMX/exec/gdn-20261120/design-checks/verify-math/vm_checks.out")
path = sys.argv[1] if len(sys.argv) > 1 else next(c for c in CANDIDATES if os.path.exists(c))
scen = None
rows = {}
for line in open(path):
    m = re.match(r"\s+SCENARIO (\w+) .*; (\d+) tokens", line)
    if m:
        scen = m.group(1)
        rows[scen] = {}
        continue
    if scen is None:
        continue
    m = re.match(r"\s+outputs: token loop \S+ \(.*?\)\s+block (\S+) ", line)
    if m:
        rows[scen]["trunc_o"] = float(m.group(1))
    m = re.match(r"\s+state  : token loop \S+ \(.*?\)\s+block (\S+) ", line)
    if m:
        rows[scen]["trunc_s"] = float(m.group(1))
    m = re.match(r"\s+bf16 recurrence words, block != token loop: (\d+) of (\d+)", line)
    if m:
        rows[scen]["trunc_words"], rows[scen]["words"] = int(m.group(1)), int(m.group(2))
    m = re.match(r"\s+variant \[round-to-nearest split\]: words != token (\d+) .*error vs oracle outputs (\S+) state (\S+);"
                 r".*against the specified form: (\d+) FP32 output values, (\d+) FP32 state values, (\d+) bf16 words differ", line)
    if m:
        rows[scen].update(near_words=int(m.group(1)), near_o=float(m.group(2)), near_s=float(m.group(3)),
                          o_bits=int(m.group(4)), s_bits=int(m.group(5)), rule_words=int(m.group(6)))

print("source: design-checks/verify-math/vm_checks.out, part E")
print("scenario | output words | words != token path: truncation, nearest | words that differ between the rules | "
      "output error vs float64: truncation, nearest, ratio | state error vs float64: truncation, nearest, ratio")
ratios, diffs = [], []
for name, r in rows.items():
    if "near_o" not in r:
        continue
    ro, rs = r["near_o"] / r["trunc_o"], r["near_s"] / r["trunc_s"]
    ratios += [ro, rs]
    diffs.append(r["rule_words"])
    print(f"{name:8s} | {r['words']} | {r['trunc_words']}, {r['near_words']} | {r['rule_words']} "
          f"({100.0 * r['rule_words'] / r['words']:.4f} %) | {r['trunc_o']:.3e}, {r['near_o']:.3e}, {ro:.3f} | "
          f"{r['trunc_s']:.3e}, {r['near_s']:.3e}, {rs:.3f}")
print(f"scenarios with the round-to-nearest variant: {len(diffs)}")
words = sorted({r["words"] for r in rows.values() if "near_o" in r})
print(f"bf16 output words that differ between the two rules: {min(diffs)} to {max(diffs)} of {words[0]}"
      + ("" if len(words) == 1 else f" to {words[-1]}"))
print(f"error of the nearest variant as a multiple of the truncation rule's error: {min(ratios):.2f} to {max(ratios):.2f}")
