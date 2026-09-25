#!/usr/bin/env python3
"""Config grid of the q4b-swattn campaign (qwen3-4b Saturday plan section 5; do not change except by dropping failed cells).
Writes configs-full.json (9 cells), configs-no8192.json (prompt-8192 cell dropped), configs-no7168.json (8192 and 7168
dropped), check-8u-p8192.json and check-8u-p7168.json (the check cells of plan section 6) next to this file.
Every dict has the keys scripts/perf.py uses; names differ per prompt length because perf.py keys its summary by name
and user count only. Every cell: model ingested-qwen-3-4b-instruct-2507-tp2, nominal_users 8 (= 2 users per engine on
the nightly's 4 tp2 engines), generate_length 1536 (the nightly's generation length; never varied), TPS window 896 to
1024, ShareGPT prompts. Only prompt_length varies. 5k/6k/7k/8k are written as multiples of the 64-token KV page."""
import json, os
MODEL = "ingested-qwen-3-4b-instruct-2507-tp2"
COMMON = dict(model=MODEL, user_sets=[], shared_prompt_length=0, generate_length=1536,
              start_capture=896, end_capture=1024, prompt_mode="sharegpt")
GRID = [  # (nominal_users, prompt_length, purpose)
    (8, 1024, "the nightly's own config (prompt 1024); reference cell, band of plan section 7"),
    (8, 1536, "jhan's 1.5k prompt cell"),
    (8, 2048, "context lever"),
    (8, 3000, "context lever (same length as the llama grid, for the cross-model chart)"),
    (8, 4096, "context lever"),
    (8, 5120, "context lever"),
    (8, 6144, "context lever"),
    (8, 7168, "context lever"),
    (8, 8192, "context lever, longest cell"),
]
def cfg(users, plen):
    name = f"ingested_qwen_3_4b_instruct_2507_tp2_{users}u_p{plen}"
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
dump("check-8u-p8192.json", [cfg(8, 8192)])
dump("check-8u-p7168.json", [cfg(8, 7168)])
