#!/usr/bin/env python3
"""Run the systems_test perf benchmark for one model exactly as system_ci's
perf phase does (scripts/perf.py test_performance), minus platformd
provisioning and talos reporting.

Env needed: OPENAI_HOST, OPENAI_TOKEN. PYTHONPATH must list the talos stub
directory first and the systems_test checkout second.
"""
import argparse
import json
import logging
import os
import sys
import time

import numpy as np

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
                    datefmt="%d/%b/%Y %H:%M:%S UTC")
logging.Formatter.converter = time.gmtime

from scripts.perf import configs, format_perf_params  # noqa: E402
from testlib.tps import Config, benchmark_tps  # noqa: E402
from testlib.hf_models import hf_map  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--users", type=int, default=None, help="override nominal_users")
ap.add_argument("--out", required=True)
a = ap.parse_args()

cfg = next(c for c in configs if c["model"] == a.model)
users = a.users or cfg["nominal_users"]
# perf.py passes the Hugging Face hub id; testlib/prompt.py then downloads the
# tokenizer from the hub. Some of these repos are gated (mistralai/...), and the
# CI runner has HF_TOKEN for that. The DUT holds the same files under
# /opt/positron/weights/huggingface/<hub id>, so use that directory when it has
# tokenizer files (identical tokenizer, no network or token needed).
hub_id = hf_map["-".join(a.model.split("-")[:-1])]["hf"]
local_dir = os.path.join(os.environ.get("WEIGHTS_ROOT", "/opt/positron/weights/"), "huggingface", hub_id)
tokenizer_model = local_dir if any(os.path.exists(os.path.join(local_dir, f)) for f in ("tokenizer.json", "tokenizer.model", "tokenizer_config.json")) else hub_id
print("tokenizer source:", tokenizer_model)
tps_config = Config(
    n_users=users,
    n_rounds=10,
    model=a.model,
    tokenizer_model=tokenizer_model,
    shared_prompt_length=cfg["shared_prompt_length"],
    prompt_length=cfg["prompt_length"],
    generate_length=cfg["generate_length"],
    start_capture=cfg["start_capture"],
    end_capture=cfg["end_capture"],
    continuous_usage=1,
)
print("perf params:", format_perf_params({**cfg, "nominal_users": users}))
t0 = time.time()
result = benchmark_tps(tps_config, raise_for_goal=False)
minutes = (time.time() - t0) / 60
ttfts, tps_results = result.ttfts, result.tpss
ttft_mean = round(float(np.mean(ttfts))) if ttfts else 0
prompt_tokens = list(getattr(result, "prompt_tokens", []) or [])
cached_tokens = list(getattr(result, "cached_tokens", []) or [])
total_prompt_tokens = sum(prompt_tokens)
out = {
    "model": a.model,
    "n_users": users,
    "n_rounds": 10,
    "params": {k: cfg[k] for k in ("shared_prompt_length", "prompt_length", "generate_length", "start_capture", "end_capture", "prompt_mode")},
    "tps_mean": float(np.mean(tps_results)) if tps_results else 0.0,
    "tps_std_dev": float(np.std(tps_results)) if tps_results else 0.0,
    "min_tps": float(min(tps_results)) if tps_results else 0.0,
    "tps_results": [float(x) for x in tps_results],
    "ttft_mean_ms": ttft_mean,
    "ttfts_ms": [float(x) for x in ttfts],
    "prefill_mean_tok_s": (cfg["prompt_length"] / (ttft_mean / 1000)) if ttft_mean else 0,
    "prompt_tokens_mean": (float(np.mean(prompt_tokens)) if prompt_tokens else cfg["prompt_length"]),
    "cache_hit_pct": (100.0 * sum(cached_tokens) / total_prompt_tokens) if total_prompt_tokens else 0.0,
    "goal": tps_config.goals.get(a.model),
    "test_passed": bool(result.test_passed),
    "minutes": minutes,
}
json.dump(out, open(a.out, "w"), indent=1)
print(f"Perf test for {a.model} completed in {minutes:.2f}mins; TPS mean {out['tps_mean']:.2f} (sd {out['tps_std_dev']:.2f}, min {out['min_tps']:.2f}) TTFT {ttft_mean} ms")
