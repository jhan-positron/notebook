#!/usr/bin/env python3
"""Config grid of the l8b-levers campaign (Saturday plan section 5; do not change except by dropping failed cells).
Writes configs-full.json, configs-no8192.json (8192 cells dropped), configs-no7168.json (8192 and 7168 cells
dropped), check-32u-p8192.json and check-32u-p7168.json (the hand-check cells of section 6) next to this file.
Every dict has the keys scripts/perf.py uses; names differ per prompt length because perf.py keys its summary
by name and user count only."""
import json, os
MODEL = "llama-3.1-8b-instruct-good-tp2"
COMMON = dict(model=MODEL, user_sets=[], shared_prompt_length=0, generate_length=1536,
              start_capture=896, end_capture=1024, prompt_mode="sharegpt")
GRID = [  # (nominal_users, prompt_length, purpose)
    (8, 1024, "today's nightly config (reference); 2 users per engine"),
    (8, 2048, "context lever"),
    (8, 3000, "8K triple, two minibatches"),
    (8, 4096, "context lever; long-prompt shape at today's load (T2)"),
    (8, 7168, "16K pair partner of 32 x 1024"),
    (8, 8192, "context lever (T2)"),
    (4, 7168, "8K triple, one minibatch; 1 user per engine"),
    (16, 1024, "users lever; 8K triple; 4 users per engine"),
    (32, 1024, "users lever; the recommended shape (T1); 8 users per engine"),
    (32, 2048, "context lever at 8 users per engine"),
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
dump("configs-no8192.json", [c for c in full if c["prompt_length"] != 8192])
dump("configs-no7168.json", [c for c in full if c["prompt_length"] not in (7168, 8192)])
dump("check-32u-p8192.json", [cfg(32, 8192)])
dump("check-32u-p7168.json", [cfg(32, 7168)])
