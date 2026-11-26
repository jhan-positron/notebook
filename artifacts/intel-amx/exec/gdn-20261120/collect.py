#!/usr/bin/env python3
"""gdn-20261120: collect every measured number of the campaign into one JSON file.

Words used here:
- runtron: tron's command-line tool. It prints, per user (request), the prompt time (= time to first token, TTFT)
  and the decode rate in tokens per second.
- attention statistics: the [attn-stats] lines that tron prints at exit when TRON_ATTN_STATS=1 (totals), and the
  per-layer files ("leaves") copied by poll-leaves.sh while the run was alive.
- forward: one scheduler step. Class decode_like = a decode step; class prompt_or_mixed = a prefill pass.
- cycles: TSC ticks; tsc_hz converts them to seconds.

Inputs : exec/results/gdn-20261120/rt/*.log, leaves/<run>/*, load/<run>.txt, trace/*.summary.json, bench/*.txt
Output : exec/results/gdn-20261120/collected.json (one record per run and one aggregate per cell and arm)
"""
import glob
import json
import os
import re
import statistics as st

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def parse_log(path):
    rec = {"tps": [], "ttft": [], "prefill_tps": [], "gen_tokens": [], "context": [], "attn": {}}
    for raw in open(path, errors="replace"):
        line = ANSI.sub("", raw)
        m = re.search(r"Generating (\d+) response tokens with (\d+) context took ([\d.]+) s at ([\d.]+) average tok/s", line)
        if m:
            rec["gen_tokens"].append(int(m.group(1))); rec["context"].append(int(m.group(2))); rec["tps"].append(float(m.group(4)))
        m = re.search(r"Parsing the prompt took ([\d.eE+-]+) s at ([\d.eE+-]+) tokens/s", line)
        if m:
            rec["prefill_tps"].append(float(m.group(2)))
        m = re.search(r"Request with (\d+) tokens in and (\d+) out .* saw ([\d.]+) s TTFT and ([\d.]+) s TTLT", line)
        if m:
            rec["ttft"].append(float(m.group(3))); rec["prompt_tokens"] = int(m.group(1))
        m = re.search(r"\[attn-stats\] model \S+: (\{.*\})", line)
        if m:
            rec["attn"]["summary"] = json.loads(m.group(1))
        m = re.search(r"\[attn-stats\] (decode_like|prompt_or_mixed)\S* (totals|forwards): (\{.*\})", line)
        if m:
            rec["attn"].setdefault(m.group(1), {})[m.group(2)] = json.loads(m.group(3))
        m = re.search(r"Version: (\S+) hash: (\S+)", line)
        if m:
            rec["version"] = m.group(1)
    return rec


def leaves(run):
    d = f"{RES}/leaves/{run}"
    out = {}
    if not os.path.isdir(d):
        return out
    for f in glob.glob(d + "/*"):
        name = os.path.basename(f)
        try:
            out[name] = json.loads(open(f).read())
        except Exception:
            pass
    return out


def load_line(run):
    p = f"{RES}/load/{run}.txt"
    out = {}
    if not os.path.exists(p):
        return out
    for line in open(p):
        f = line.split()
        if len(f) >= 3 and f[0] in ("socket0", "socket1", "our-app-cores", "our-dev-cores"):
            out[f[0]] = float(f[2].rstrip("%"))
        if line.startswith("=== load snapshot"):
            out["taken"] = line.split()[4]
    return out


def derive(rec):
    """Per-class derived values from the attention statistics totals (the exit report)."""
    a = rec["attn"]
    hz = a.get("summary", {}).get("tsc_hz")
    out = {}
    for cls in ("decode_like", "prompt_or_mixed"):
        c = a.get(cls, {})
        f, t = c.get("forwards"), c.get("totals")
        if not f or not t or not f.get("forwards") or not hz:
            continue
        n = f["forwards"]
        wall = f["wall_cycles"]
        out[cls] = {
            "forwards": n,
            "token_jobs_per_forward": f["token_jobs"] / n,
            "forward_wall_ms": wall / n / hz * 1e3,                       # T1 mean
            "forward_wall_total_s": wall / hz,
            "attn_w0_wall_ms_per_forward": t["wall_cycles_w0"] / n / hz * 1e3,  # T3 sum over layers, worker 0
            "attn_w0_wall_share": t["wall_cycles_w0"] / wall,
            "attn_busy_cpu_ms_per_forward": t["busy_cycles"] / n / hz * 1e3,     # T2 summed over workers
            "attn_join_wait_cpu_ms_per_forward": t["join_wait_cycles"] / n / hz * 1e3,
            "attn_workers": f.get("n_attn_workers_max"),
            "attn_worker_duty": t["busy_cycles"] / (f.get("n_attn_workers_max") or 1) / wall,
            "attn_jobs_per_forward": t["attn_jobs"] / n,
            "avx_k_tokens_per_forward": (t["ready_avx_k_tokens"] + t["pending_avx_k_tokens"]) / n,
            "amx_k_tokens": t["ready_amx_k_tokens"] + t["pending_amx_k_tokens"],
            "avx_full_page_visits_per_forward": (t["ready_avx_full_page_visits"] + t["pending_avx_full_page_visits"]) / n,
            "avx_visits_per_forward": (t["ready_avx_visits"] + t["pending_avx_visits"]) / n,
            "full_page_k_token_share": 64.0 * (t["ready_avx_full_page_visits"] + t["pending_avx_full_page_visits"])
            / max(1, t["ready_avx_k_tokens"] + t["pending_avx_k_tokens"]),
        }
    return out


def main():
    runs = {}
    for path in sorted(glob.glob(RES + "/rt/*.log")):
        run = os.path.basename(path)[:-4]
        rec = parse_log(path)
        m = re.match(r"(?:trace-)?(.*?)(?:__(on|off)__rep(\d+))?$", run)
        rec["run"] = run
        rec["cell"], rec["arm"], rec["rep"] = m.group(1), m.group(2), int(m.group(3)) if m.group(3) else None
        rec["traced"] = run.startswith("trace-")
        rec["users"] = len(rec["tps"])
        rec["derived"] = derive(rec)
        rec["load"] = load_line(run)
        lv = leaves(run)
        if lv:
            rec["leaves_taken"] = open(f"{RES}/leaves/{run}/.taken").read().strip() if os.path.exists(f"{RES}/leaves/{run}/.taken") else None
            rec["layer_leaves"] = {k: v for k, v in lv.items() if "_layer_" in k}
            rec["worker_leaves"] = {k: v for k, v in lv.items() if "_worker_" in k}
            rec["leaf_forwards"] = {k: v for k, v in lv.items() if k.endswith("_forwards")}
        if rec["tps"]:
            rec["tps_mean"] = st.mean(rec["tps"]); rec["tps_sum"] = sum(rec["tps"])
            rec["ttft_max"] = max(rec["ttft"]); rec["ttft_mean"] = st.mean(rec["ttft"])
        runs[run] = rec
    cells = {}
    for run, r in runs.items():
        if r["traced"] or r["arm"] is None or not r["tps"]:
            continue
        cells.setdefault(r["cell"], {}).setdefault(r["arm"], []).append(r)
    agg = {}
    for cell, arms in cells.items():
        agg[cell] = {}
        for arm, rs in arms.items():
            rs.sort(key=lambda r: r["rep"])
            def col(fn):
                v = [fn(r) for r in rs]
                return {"values": v, "median": st.median(v), "min": min(v), "max": max(v), "n": len(v)}
            a = {
                "users": rs[0]["users"], "prompt_tokens": rs[0].get("prompt_tokens"),
                "decode_tps_per_user": col(lambda r: r["tps_mean"]),
                "decode_tps_all_users": col(lambda r: r["tps_sum"]),
                "ttft_max_s": col(lambda r: r["ttft_max"]),
                "ttft_mean_s": col(lambda r: r["ttft_mean"]),
                "runs": [r["run"] for r in rs],
            }
            for cls in ("decode_like", "prompt_or_mixed"):
                if all(cls in r["derived"] for r in rs):
                    a[cls] = {k: col(lambda r, k=k: r["derived"][cls][k]) for k in rs[0]["derived"][cls] if isinstance(rs[0]["derived"][cls][k], (int, float))}
            agg[cell][arm] = a
    traces = {}
    for p in sorted(glob.glob(RES + "/trace/*.summary.json")):
        traces[os.path.basename(p).split(".")[0]] = json.load(open(p))
    bench = {}
    for p in sorted(glob.glob(RES + "/bench/*.json")):
        bench[os.path.basename(p)[:-5]] = json.load(open(p))
    out = {"runs": runs, "cells": agg, "traces": traces, "bench": bench}
    json.dump(out, open(RES + "/collected.json", "w"), indent=1)
    # short text table
    print(f"{'cell':22} {'arm':4} {'n':>2} {'TPS/user med':>13} {'(min-max)':>16} {'TTFT max med s':>15} {'fwd ms dec':>11} {'attn w0 share dec':>18} {'fwd ms prefill':>15} {'attn share pf':>14}")
    for cell in sorted(agg, key=lambda c: (agg[c][next(iter(agg[c]))]["users"], agg[c][next(iter(agg[c]))]["prompt_tokens"] or 0)):
        for arm, a in sorted(agg[cell].items()):
            d = a.get("decode_like", {}); p = a.get("prompt_or_mixed", {})
            t = a["decode_tps_per_user"]
            print(f"{cell:22} {arm:4} {t['n']:2d} {t['median']:13.2f} {t['min']:7.2f}-{t['max']:<8.2f} {a['ttft_max_s']['median']:15.3f} "
                  f"{d.get('forward_wall_ms', {}).get('median', float('nan')):11.3f} {100 * d.get('attn_w0_wall_share', {}).get('median', float('nan')):17.1f}% "
                  f"{p.get('forward_wall_ms', {}).get('median', float('nan')):15.2f} {100 * p.get('attn_w0_wall_share', {}).get('median', float('nan')):13.1f}%")


if __name__ == "__main__":
    main()
