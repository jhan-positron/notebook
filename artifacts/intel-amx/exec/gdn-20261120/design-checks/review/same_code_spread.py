#!/usr/bin/env python3
"""How far two sets of runs differ when both run the same code (baseline of 2026-11-20).

What it computes: per cell, the median TTFT and the median decode speed of the two arms of the baseline
(AMX allowed, kill switch set). On Qwen3.5 4B both arms run the same code today. So the difference between
the two medians is the size of a difference that an A/B run can show without any change of the code.
A pass rule of the form "not slower than run 1" needs a tolerance of at least this size.

Input : exec/results/gdn-20261120/collected.json (written by collect.py), fields
        cells[cell][arm]["ttft_max_s"] and cells[cell][arm]["decode_tps_per_user"] (keys "values", "median").
Output: text on stdout. Saved beside this script as same_code_spread.out.
Usage : PYTHONDONTWRITEBYTECODE=1 python3 same_code_spread.py [path to collected.json] > same_code_spread.out
"""
import json
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/collected.json"
cells = json.load(open(SRC))["cells"]
order = sorted(cells, key=lambda c: (cells[c]["on"]["users"], cells[c]["on"]["prompt_tokens"]))

print("Source:", SRC)
print("Difference of the medians: arm 'on' (AMX allowed) against arm 'off' (kill switch set), percent of arm 'off'.")
print(f"{'cell':24} {'runs on/off':>11} {'TTFT (%)':>9} {'decode tok/s per user (%)':>26}")
d_ttft, d_dec = [], []
for c in order:
    on, off = cells[c]["on"], cells[c]["off"]
    diff = lambda k: 100.0 * (on[k]["median"] - off[k]["median"]) / off[k]["median"]
    d_ttft.append(diff("ttft_max_s"))
    d_dec.append(diff("decode_tps_per_user"))
    n = f"{len(on['ttft_max_s']['values'])}/{len(off['ttft_max_s']['values'])}"
    print(f"{on['users']} user{'s' if on['users'] > 1 else ' '}, prompt {on['prompt_tokens']:>5,}  {n:>11} {d_ttft[-1]:>+9.2f} {d_dec[-1]:>+26.2f}")
print(f"\nTTFT median, same code:   {min(d_ttft):+.2f} to {max(d_ttft):+.2f} %")
print(f"Decode median, same code: {min(d_dec):+.2f} to {max(d_dec):+.2f} %")
