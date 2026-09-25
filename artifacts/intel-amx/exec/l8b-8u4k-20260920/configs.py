#!/usr/bin/env python3
"""Config of the l8b-8u4k campaign (plan CI-test/status/llama-3.1-8b-8u-4k-plan.md, section 5; do not change).
Writes configs-full.json (one dict) next to this file. The dict has the keys scripts/perf.py uses; the name carries the
user count and the prompt length because perf.py keys its summary by name and user count only.
Copied from exec/l8b-levers-20260919/configs.py with the grid reduced to one cell."""
import json, os
MODEL = "llama-3.1-8b-instruct-good-tp2"
COMMON = dict(model=MODEL, user_sets=[], shared_prompt_length=0, generate_length=1536,
              start_capture=896, end_capture=1024, prompt_mode="sharegpt")
GRID = [  # (nominal_users, prompt_length, purpose)
    (32, 4096, "8 users per engine at prompt 4096, context lever at the recommended load"),
]
def cfg(users, plen):
    name = f"llama_3_1_8b_instruct_good_tp2_{users}u_p{plen}"
    return dict(name=name, sample_name=name, nominal_users=users, prompt_length=plen, **COMMON)
here = os.path.dirname(os.path.abspath(__file__))
def dump(fname, cfgs):
    with open(os.path.join(here, fname), "w") as f:
        json.dump(cfgs, f, indent=1)
    print(fname, [(c["nominal_users"], c["prompt_length"]) for c in cfgs])
full = [cfg(u, p) for u, p, _ in GRID]
dump("configs-full.json", full)
