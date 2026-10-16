#!/usr/bin/env python3
"""Config files of the pr4424ci campaign (2026-10-09). Writes, next to this file:
  sw8k.json       the ONE extra cell: ingested-qwen-3-4b-instruct-2507-tp2, 8 users (= 2 per engine on the nightly's
                  4 tp2 engines), prompt_length 8192, generate_length 1536, TPS window 896..1024, ShareGPT prompts.
                  campaign.sh runs it with software attention (USE_HW_ATTN=0 in /opt/positron/user/config.env).
  nightly14.json  the harness's own perf config list (scripts/perf.py configs of ~/workspace/ai-runs/systems_test, 14
                  entries on origin/main 14f0ce4), dumped as a FALLBACK record. The full passes do NOT read this file:
                  campaign.sh passes CI_MIMIC_CONFIGS_JSON="" and the driver then uses scripts.perf.configs directly,
                  so the campaign follows whatever the harness checkout carries.
Every dict has the keys scripts/perf.py uses. Run with the harness venv and the talos stub FIRST on PYTHONPATH:
  cd ~/workspace/ai-runs/systems_test && PYTHONPATH=<this dir>/talos_stub:$PWD .venv/bin/python <this dir>/configs.py
(importing scripts.perf imports talos; the real talos package registers a session in the CI database at import time)."""
import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "talos_stub"))   # never the real talos
MODEL = "ingested-qwen-3-4b-instruct-2507-tp2"
SW8K = dict(name="ingested_qwen_3_4b_instruct_2507_tp2_8u_p8192", sample_name="ingested_qwen_3_4b_instruct_2507_tp2_8u_p8192",
            model=MODEL, nominal_users=8, user_sets=[], shared_prompt_length=0, prompt_length=8192, generate_length=1536,
            start_capture=896, end_capture=1024, prompt_mode="sharegpt")


def dump(fname, cfgs):
    with open(os.path.join(here, fname), "w") as f:
        json.dump(cfgs, f, indent=1)
    print(fname, [(c["name"], c["nominal_users"], c["prompt_length"]) for c in cfgs])


dump("sw8k.json", [SW8K])
try:
    from scripts import perf as perf_mod   # the harness checkout must be on PYTHONPATH
except ImportError as exc:
    print(f"nightly14.json not written: scripts.perf not importable ({exc}); run from the harness venv with PYTHONPATH set")
    sys.exit(1)
# harness names repeat (llama_3_1_8b_instruct_good_tp2 at 8u/1024 and 32u/4096; llama_3_3_70b_instruct_good_tp2 at 8u and 4u):
# the cell identity is (model, nominal_users, prompt_length); the driver and summarize.py key on that, never on the name
keys = [(c["model"], c["nominal_users"], c["prompt_length"]) for c in perf_mod.configs]
assert len(set(keys)) == len(keys), f"harness cells (model, users, prompt_length) are not unique: {keys}"
dups = sorted({c["name"] for c in perf_mod.configs if [x["name"] for x in perf_mod.configs].count(c["name"]) > 1})
print("harness names that repeat (cells differ by users/prompt_length):", dups)
dump("nightly14.json", perf_mod.configs)
print(f"harness list: {len(perf_mod.configs)} configs")
