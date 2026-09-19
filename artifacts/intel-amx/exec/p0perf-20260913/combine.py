#!/usr/bin/env python3
"""Pool the per-engine harness results of one CI-config cell into perf.json.

A cell of the p0perf-20260913 campaign runs one harness client per engine (tp2: two engines
with 2 users each; tp4: one engine with 4 users). Each client writes perf-e<k>.json in the
format of exec/more-testing-r1/st_perf.py. The nightly pools its 8 users into one mean, so this
script pools every user sample of the cell the same way:
  tps_mean      = mean over all per-user, per-round decode samples (896-1024 capture window)
  tps_std_dev   = population standard deviation of the same samples (numpy.std convention)
  min_tps       = the slowest sample
  ttft_mean_ms  = mean of every user's time to first token, rounded to whole ms
  n_users       = users of the cell (sum over engines); per_engine keeps each client's numbers.
Usage: combine.py CELL_DIR N_ENGINES   (fails when fewer than N_ENGINES files are present)
"""
import glob
import json
import os
import statistics
import sys

cell, n_expected = sys.argv[1], int(sys.argv[2])
files = sorted(glob.glob(os.path.join(cell, "perf-e*.json")))
if len(files) != n_expected:
    sys.exit(f"combine: {len(files)} of {n_expected} per-engine files present in {cell}")
parts = [json.load(open(f)) for f in files]
tps = [float(x) for p in parts for x in p["tps_results"]]
ttfts = [float(x) for p in parts for x in p["ttfts_ms"]]
if not tps or not ttfts:
    sys.exit("combine: no samples")
weights = [len(p["tps_results"]) for p in parts]
total = sum(weights)
out = {
    "model": parts[0]["model"],
    "n_users": sum(int(p["n_users"]) for p in parts),
    "n_engines": len(parts),
    "users_per_engine": [int(p["n_users"]) for p in parts],
    "n_rounds": parts[0]["n_rounds"],
    "params": parts[0]["params"],
    "tps_mean": statistics.mean(tps),
    "tps_std_dev": statistics.pstdev(tps) if len(tps) > 1 else 0.0,
    "min_tps": min(tps),
    "tps_results": tps,
    "ttft_mean_ms": round(statistics.mean(ttfts)),
    "ttfts_ms": ttfts,
    "prefill_mean_tok_s": (parts[0]["params"]["prompt_length"] / (statistics.mean(ttfts) / 1000.0)),
    "prompt_tokens_mean": sum(p.get("prompt_tokens_mean", 0) * w for p, w in zip(parts, weights)) / total,
    "cache_hit_pct": sum(p.get("cache_hit_pct", 0) * w for p, w in zip(parts, weights)) / total,
    "goal": parts[0].get("goal"),
    "test_passed": all(bool(p.get("test_passed")) for p in parts),
    "minutes": max(float(p["minutes"]) for p in parts),
    "per_engine": [{"file": os.path.basename(f), "n_users": p["n_users"], "tps_mean": p["tps_mean"], "tps_std_dev": p["tps_std_dev"],
                    "min_tps": p["min_tps"], "ttft_mean_ms": p["ttft_mean_ms"], "minutes": p["minutes"], "n_samples": len(p["tps_results"])}
                   for f, p in zip(files, parts)],
}
json.dump(out, open(os.path.join(cell, "perf.json"), "w"), indent=1)
print(f"combine: {len(parts)} engine(s), {out['n_users']} users, {len(tps)} samples: TPS mean {out['tps_mean']:.2f} (sd {out['tps_std_dev']:.2f}, min {out['min_tps']:.2f}) TTFT {out['ttft_mean_ms']} ms")
