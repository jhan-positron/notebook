#!/usr/bin/env python3
"""Check every run_gdn_operation call site of the generated plugin.
For each call: are the 4 input channels waited on with start_reading_all()
in the 12 lines before the call, and which worker index is passed?"""
import re, sys
p = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp"
lines = open(p).read().split("\n")
calls = [i for i, l in enumerate(lines) if "tron::run_gdn_operation<" in l]
ok = 0
kinds = {}
for i in calls:
    m = re.search(r"recurrent_checkpoints\(\), (\w+), (\w+), (\w+), (\w+), (\w+), (\w+), n_workers\)", lines[i])
    ins = m.groups()[:4]; out = m.group(5); wix = m.group(6)
    before = "\n".join(lines[i-14:i])
    waited = all(f"q_batch->{name}_channel.start_reading_all();" in before for name in ins)
    out_started = f"q_batch->{out}_channel.start_writing(" in before
    kinds[wix] = kinds.get(wix, 0) + 1
    if waited and out_started: ok += 1
    else: print("MISSING at line", i+1, ins, waited, out_started)
print("call sites:", len(calls), "with all 4 inputs waited by start_reading_all and output start_writing:", ok)
print("by worker index argument:", kinds)
# which function holds the calls
for name in ("void run(", "void run_main_help(", "void run_attn("):
    idx = [i+1 for i, l in enumerate(lines) if name in l]
    print(name, "defined at lines", idx)
print("first/last call line:", calls[0]+1, calls[-1]+1)
