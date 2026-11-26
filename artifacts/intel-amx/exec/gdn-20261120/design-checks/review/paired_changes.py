#!/usr/bin/env python3
"""Predicted TTFT of every run setting of the plan, and the predicted change of every pair of runs.

What it computes (all values are estimates, from the prediction model of section 4 of gdn-amx-design.html):
  1. TTFT per cell for six run settings: today (base build), Part 0, Part A, Part B on today's GDN kernel,
     Part 0 with Part B, Parts A and B. Levels: working value ("mid"), low case ("lo"), high case ("hi").
     A level uses every factor at that level together, as section 4 defines its range. No level is mixed here.
  2. The change of four pairs of runs, in seconds, as a percent of run 1 of the pair, and as a percent of today's TTFT:
       Part A against Part 0, Part B off in both runs      (Part 0 -> Part A)
       Part A against Part 0, Part B on in both runs       (Part 0 with Part B -> Parts A and B)
       Part B on against off, GDN prefill on Part 0        (Part 0 -> Part 0 with Part B)
       Part B on against off, GDN prefill on Part A        (Part A -> Parts A and B)
  3. A check that the seconds saved by one part do not depend on the setting of the other part (the model is a sum).
  4. A check of the pass rules of the plan table as the page worded them in review round 1 (digest 8a9fbfa5): is the percent of the
     A/B run (denominator: run 1 of the pair) inside the range that section 4 gives for that part (denominator:
     today's TTFT)?
  5. The quantities of the proposed pass rules, each as a percent of the base-run TTFT, with the low and high case.
  6. The mixed cases of the pair Part 0 -> Part A (low factor of one part with the high factor of the other).
     They are labeled as mixed. Section 4 does not define them.
  7. Decode speed with Part B against the kill-switch run.

Input : exec/results/gdn-20261120/predictions.json (written by predict.py). The stored predictions are also
        recomputed here from the stored inputs and factors with the formulas of predict.py, as a cross-check.
Output: text on stdout. Saved beside this script as paired_changes.out.
Usage : PYTHONDONTWRITEBYTECODE=1 python3 paired_changes.py [path to predictions.json] > paired_changes.out
"""
import json
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json"

# run setting -> scenario name in predictions.json (None = measured baseline)
STATE = [
    ("T", "today (base build)", None),
    ("0", "Part 0", "reorder"),
    ("A", "Part A", "amx_gdn"),
    ("B", "Part B, today's GDN", "amx_attn"),
    ("0B", "Part 0 with Part B", "reorder_attn"),
    ("AB", "Parts A and B", "amx_both"),
]
# pair name, run 1, run 2
PAIRS = [
    ("Part A against Part 0, Part B off", "0", "A"),
    ("Part A against Part 0, Part B on", "0B", "AB"),
    ("Part B on against off, GDN on Part 0", "0", "0B"),
    ("Part B on against off, GDN on Part A", "A", "AB"),
]
# scenario -> (GDN factor key, attention kernel on, clock cost on); copied from SCEN of predict.py
SCEN = {
    "reorder": ("s_gdn_reorder", False, False),
    "amx_gdn": ("s_gdn_amx", False, True),
    "amx_attn": (None, True, False),
    "reorder_attn": ("s_gdn_reorder", True, False),
    "amx_both": ("s_gdn_amx", True, True),
}
LEVELS = ("lo", "mid", "hi")
LEVEL_NAME = {"lo": "low case", "mid": "working values", "hi": "high case"}

pred = json.load(open(SRC))
asm = pred["assumptions"]
cells = pred["cells"]
order = sorted(cells, key=lambda c: (cells[c]["users"], cells[c]["prompt"]))


def label(c):
    return f"{cells[c]['users']} user{'s' if cells[c]['users'] > 1 else ' '}, prompt {cells[c]['prompt']:>5,}"


def ttft(c, state, level):
    """TTFT in seconds of one run setting at one level, read from predictions.json."""
    scen = dict((k, s) for k, _, s in STATE)[state]
    if scen is None:
        return cells[c]["prefill"]["ttft_s"]
    return cells[c]["pred"][level][scen]["ttft_s"]


def recompute(c, scen, level):
    """TTFT from the stored inputs and factors, with the formula of predict.py."""
    p = cells[c]["prefill"]
    gkey, attn_on, tax_on = SCEN[scen]
    d = 0.0
    if gkey:
        d += p["gdn_ms"] * (1 - 1 / asm[gkey][level])
    if attn_on:
        d += p["attn_full_ms"] * (1 - 1 / asm["s_attn_prefill"][level])   # prefill: the factor divides the full-page time only
        d -= p["attn_other_ms"] * asm["tax_attn_other"][level]             # the other attention work runs at the AMX clock
    if tax_on:
        d -= p["rest_ms"] * asm["tax_rest_amx_gdn"][level]
    return p["ttft_s"] - p["passes"] * d / 1e3


def pc(x, base):
    return 100.0 * x / base


print("Source:", SRC)
print("Factors (low / working / high):")
for k in ("s_gdn_reorder", "s_gdn_amx", "s_attn_prefill", "s_attn_decode", "tax_rest_amx_gdn", "tax_attn_other"):
    print(f"  {k:18} {asm[k]['lo']} / {asm[k]['mid']} / {asm[k]['hi']}")

# ---------------------------------------------------------------- cross-check of the stored predictions
worst = max(abs(recompute(c, s, l) - cells[c]["pred"][l][s]["ttft_s"]) for c in order for s in SCEN for l in LEVELS)
print(f"\nCross-check: stored TTFT against the formula of predict.py, largest difference = {worst:.1e} s")
assert worst < 1e-9

# ---------------------------------------------------------------- 1. TTFT per run setting
for level in ("mid", "lo", "hi"):
    print(f"\n1. TTFT per run setting (s, est.), {LEVEL_NAME[level]}. In brackets: change against today (%).")
    print(f"{'cell':24}" + "".join(f"{name:>24}" for _, name, _ in STATE))
    for c in order:
        t0 = ttft(c, "T", level)
        row = f"{label(c):24}"
        for k, _, _ in STATE:
            v = ttft(c, k, level)
            row += f"{v:>15.3f} ({pc(v - t0, t0):+5.1f})" if k != "T" else f"{v:>24.3f}"
        print(row)

# ---------------------------------------------------------------- 2. pairs
for level in ("mid", "lo", "hi"):
    print(f"\n2. Change from run 1 to run 2 of each pair (est.), {LEVEL_NAME[level]} in both runs.")
    print("   Columns per pair: seconds, percent of run 1, percent of today's TTFT.")
    for name, r1, r2 in PAIRS:
        print(f"   {name}  ({dict((k, n) for k, n, _ in STATE)[r1]} -> {dict((k, n) for k, n, _ in STATE)[r2]})")
        of1, of0 = [], []
        for c in order:
            a, b, t0 = ttft(c, r1, level), ttft(c, r2, level), ttft(c, "T", level)
            of1.append(pc(b - a, a))
            of0.append(pc(b - a, t0))
            print(f"     {label(c):24} run 1 {a:7.3f} s  run 2 {b:7.3f} s  change {b - a:+7.3f} s  {of1[-1]:+5.1f} % of run 1  {of0[-1]:+5.1f} % of today")
        print(f"     over the 6 cells: {max(of1):+.1f} to {min(of1):+.1f} % of run 1, {max(of0):+.1f} to {min(of0):+.1f} % of today")

# ---------------------------------------------------------------- 3. the model is a sum
d_b = max(abs((ttft(c, "T", l) - ttft(c, "B", l)) - (ttft(c, x, l) - ttft(c, x + "B", l))) for c in order for l in LEVELS for x in ("0", "A"))
d_a = max(abs((ttft(c, "0", l) - ttft(c, "A", l)) - (ttft(c, "0B", l) - ttft(c, "AB", l))) for c in order for l in LEVELS)
print("\n3. The model is a sum: the seconds that one part saves do not depend on the other part.")
print(f"   Seconds saved by Part B on today's GDN, on Part 0 and on Part A: largest difference = {d_b:.1e} s")
print(f"   Seconds saved by Part A over Part 0 with Part B off and with Part B on: largest difference = {d_a:.1e} s")
assert d_b < 1e-9 and d_a < 1e-9

# ---------------------------------------------------------------- 4. the pass rules as worded on the page
print("\n4. Pass rules as worded on the page: percent of the A/B run (of run 1) against the range of section 4 (of today).")
print("   Working values in both runs. 'range' is the low to high case of that part for the cell, as section 4 prints it.")
CHECKS = [
    ("Task 6, Part A, GDN switch, Part B off", "0", "A", "A"),
    ("Task 6, Part A, GDN switch, Part B on", "0B", "AB", "A"),
    ("Task 5, Part B, kill switch on a build with Part 0", "0", "0B", "B"),
]
for name, r1, r2, part in CHECKS:
    print(f"   {name}")
    n_out = 0
    for c in order:
        a, b, t0 = ttft(c, r1, "mid"), ttft(c, r2, "mid"), ttft(c, "T", "mid")
        ab = pc(b - a, a)
        lo, mid, hi = (pc(ttft(c, part, l) - t0, t0) for l in LEVELS)
        inside = hi <= ab <= lo
        n_out += not inside
        print(f"     {label(c):24} A/B run {ab:+5.1f} % of run 1.  Section 4: {mid:+5.1f} % of today, range {lo:+5.1f} to {hi:+5.1f} %.  {'inside' if inside else 'OUTSIDE'}")
    print(f"     cells outside the range at the working values: {n_out} of {len(order)}")

# ---------------------------------------------------------------- 5. the proposed rules
print("\n5. Quantities of the proposed pass rules, each as a percent of the base-run TTFT (est.).")
print("   Format: working value (low case to high case). A case uses every factor at that level.")
RULES = [
    ("Task 2. Part 0, total: base run -> Part 0 run", lambda c, l: ttft(c, "0", l) - ttft(c, "T", l)),
    ("Task 5. Part B: Part 0 run -> Part 0 with Part B (seconds of the A/B run)", lambda c, l: ttft(c, "0B", l) - ttft(c, "0", l)),
    ("Task 6. Part A, total: (base run -> Part 0 run) plus (A/B run with the GDN switch)",
     lambda c, l: (ttft(c, "0", l) - ttft(c, "T", l)) + (ttft(c, "AB", l) - ttft(c, "0B", l))),
    ("Task 6. Parts A and B, total: base run -> run with no switch set", lambda c, l: ttft(c, "AB", l) - ttft(c, "T", l)),
]
COLUMN = ["0", "B", "A", "AB"]
for (name, fn), col in zip(RULES, COLUMN):
    print(f"   {name}")
    for c in order:
        t0 = ttft(c, "T", "mid")
        lo, mid, hi = (pc(fn(c, l), t0) for l in LEVELS)
        ref = [pc(ttft(c, col, l) - t0, t0) for l in LEVELS]
        same = max(abs(x - y) for x, y in zip((lo, mid, hi), ref)) < 1e-9
        print(f"     {label(c):24} {fn(c, 'mid'):+7.3f} s = {mid:+5.1f} % ({lo:+5.1f} to {hi:+5.1f} %)   equal to the column of section 4: {'yes' if same else 'NO'}")
        assert same

# ---------------------------------------------------------------- 6. mixed cases of Part 0 -> Part A
print("\n6. Mixed cases of the pair Part 0 -> Part A (Part B equal in both runs). Section 4 does not define them.")
print("   The factors of Part 0 and of Part A are separate estimates. A positive value means that Part A is slower.")
for c in order:
    out = []
    for l0, la in (("hi", "lo"), ("mid", "lo"), ("mid", "mid"), ("lo", "hi")):
        a, b = ttft(c, "0", l0), ttft(c, "A", la)
        out.append(f"Part 0 {l0:>3} / Part A {la:>3}: {b - a:+7.3f} s {pc(b - a, a):+6.1f} %")
    print(f"     {label(c):24} " + "   ".join(out))

# ---------------------------------------------------------------- 7. decode
print("\n7. Decode speed with Part B (tok/s per user, est.). Run 1: kill switch set. Run 2: Part B on.")
print("   Parts 0 and A do not change decode. So run 1 equals today's value in the model.")
for c in order:
    d0 = cells[c]["decode"]["tps"]
    lo, mid, hi = (cells[c]["pred"][l]["amx_attn"]["tps"] for l in LEVELS)
    print(f"     {label(c):24} run 1 {d0:6.1f}   run 2 {mid:6.1f} ({pc(mid - d0, d0):+.1f} %)   low case {lo:6.1f} ({pc(lo - d0, d0):+.1f} %)   high case {hi:6.1f} ({pc(hi - d0, d0):+.1f} %)")

# ---------------------------------------------------------------- rows for the page
print("\nRows for the page table 'Predicted TTFT fall of the two A/B runs' (working values, est.).")
print("Columns: users | prompt | task 5, A/B run of Part B: fall (s) | % of the base run | % of run 1 |")
print("         task 6, A/B run of Part A: fall (s) | % of the base run | % of run 1 with Part B on | % of run 1 with Part B off")
for c in order:
    r = cells[c]
    t0 = ttft(c, "T", "mid")
    b1, b2 = ttft(c, "0", "mid"), ttft(c, "0B", "mid")
    a1, a2 = ttft(c, "0B", "mid"), ttft(c, "AB", "mid")
    o1, o2 = ttft(c, "0", "mid"), ttft(c, "A", "mid")
    assert abs((a1 - a2) - (o1 - o2)) < 1e-9
    row = [f"{r['users']}", f"{r['prompt']:,}", f"{b1 - b2:.3f}", f"{pc(b1 - b2, t0):.1f}", f"{pc(b1 - b2, b1):.1f}",
           f"{a1 - a2:.3f}", f"{pc(a1 - a2, t0):.1f}", f"{pc(a1 - a2, a1):.1f}", f"{pc(o1 - o2, o1):.1f}"]
    print(" | ".join(row))

print("\nRanges over the 6 cells for the prose (working values, est.).")
f5 = [pc(ttft(c, "0", "mid") - ttft(c, "0B", "mid"), ttft(c, "0", "mid")) for c in order]
f6on = [pc(ttft(c, "0B", "mid") - ttft(c, "AB", "mid"), ttft(c, "0B", "mid")) for c in order]
f6off = [pc(ttft(c, "0", "mid") - ttft(c, "A", "mid"), ttft(c, "0", "mid")) for c in order]
f6base = [pc(ttft(c, "0", "mid") - ttft(c, "A", "mid"), ttft(c, "T", "mid")) for c in order]
print(f"  A/B run of Part B on a build with Part 0: TTFT falls by {min(f5):.1f} to {max(f5):.1f} % of run 1")
print(f"  A/B run of Part A, Part B on : TTFT falls by {min(f6on):.1f} to {max(f6on):.1f} % of run 1")
print(f"  A/B run of Part A, Part B off: TTFT falls by {min(f6off):.1f} to {max(f6off):.1f} % of run 1")
print(f"  A/B run of Part A, either setting of Part B: {min(f6base):.1f} to {max(f6base):.1f} % of the base run")
