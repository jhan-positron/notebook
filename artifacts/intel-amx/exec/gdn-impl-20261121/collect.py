#!/usr/bin/env python3
"""gdn-impl-20261121: collect every measured number of the campaign into one JSON file.

Words used here:
- runtron: tron's command-line tool. It prints, per user (request), the prompt time (= time to first token, TTFT)
  and the decode rate in tokens per second.
- attention statistics, GDN statistics: the [attn-stats] and [gdn-stats] lines that tron prints at exit when
  TRON_ATTN_STATS=1 and TRON_GDN_STATS=1 are set.
- forward: one scheduler step. Class decode_like = a decode step; class prompt_or_mixed = a prefill pass.
- cycles: TSC ticks; tsc_hz converts them to seconds.
- head token: one token of one (chain, key head) work item of a GDN layer. A layer of this model has 16 key heads,
  so one token of one layer is 16 head tokens.
- arm: one build with one set of switches (see campaign.sh).

Sessions: the repetition number of a run says which session it belongs to (campaign.sh FIRST_REP / REPS).
- reps 1-9   : session 1, the commits before the code review (stopped after repetition 1 and 7 runs of repetition 2)
- reps 11-19 : session 2, the final commits (the main data)
- reps 21-29 : control runs of the final commits (arms base, nost, orig)

Inputs : exec/results/gdn-impl-20261121/rt/<cell>__<arm>__rep<N>.log of the campaign arms, load/<run>.txt,
         rt-results.txt (its "### run=" lines give the commit of the binary of each run)
Output : exec/results/gdn-impl-20261121/collected<SUFFIX>.json (one record per run, one aggregate per cell and arm)
Usage  : [REPS_RANGE=11-19] [SUFFIX=] python3 collect.py [results folder]
"""
import glob
import json
import os
import re
import statistics as st
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121"
# The arms of the campaign (campaign.sh). Logs of other arms in the folder are trial runs made while the code was
# brought up; they are not collected.
ARMS = {"base", "p0", "b", "ab", "a0", "a", "orig", "nost"}
REP_LO, REP_HI = (int(x) for x in os.environ.get("REPS_RANGE", "11-19").split("-"))
SUFFIX = os.environ.get("SUFFIX", "")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
CLASSES = ("decode_like", "prompt_or_mixed")


def parse_log(path):
    rec = {"tps": [], "ttft": [], "prefill_tps": [], "gen_tokens": [], "context": [], "attn": {}, "gdn": {}}
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
        for tag, key in (("attn-stats", "attn"), ("gdn-stats", "gdn")):
            m = re.search(r"\[%s\] model \S+: (\{.*\})" % tag, line)
            if m:
                rec[key]["summary"] = json.loads(m.group(1))
            m = re.search(r"\[%s\] (decode_like|prompt_or_mixed)\S* (totals|forwards): (\{.*\})" % tag, line)
            if m:
                rec[key].setdefault(m.group(1), {})[m.group(2)] = json.loads(m.group(3))
        m = re.search(r"\[gdn-stats\] (decode_like|prompt_or_mixed)\S* wall_cycles per op: (.*)$", line)
        if m:
            rec["gdn"].setdefault(m.group(1), {})["wall_per_op"] = [int(x.split("=")[1]) for x in m.group(2).split()]
        m = re.search(r"\[gdn-stats\] (decode_like|prompt_or_mixed)\S* head_tokens per op \(token/(?:half|chain)/amx\): (.*)$", line)
        if m:
            rec["gdn"].setdefault(m.group(1), {})["head_tokens_per_op"] = [
                [int(v) for v in x.split("=")[1].split("/")] for x in m.group(2).split()]
        m = re.search(r"\[gdn-stats\] (decode_like|prompt_or_mixed)\S* per worker \(busy_cycles/head_tokens\): (.*)$", line)
        if m:
            rec["gdn"].setdefault(m.group(1), {})["per_worker"] = [
                [int(v) for v in x.split("=")[1].split("/")] for x in m.group(2).split()]
        m = re.search(r"Version: (\S+) hash: (\S+)", line)
        if m:
            rec["version"] = m.group(1)
    return rec


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


PREFILL_TOKENS_PER_PASS = 128   # tron's scheduler gives a prefill pass 128 prompt tokens per user


def passes(rec, cls, counted):
    """Number of passes to divide a per-class total by.

    A few runs count one more pass in the class prompt_or_mixed than the prompt needs: a pass with some decode jobs
    of users that finished their prompt earlier (2 of the 108 runs of session 2). Its work is small, so dividing by
    the counted number would make the per-pass values of such a run about 1.5 % too low. For that class the divisor
    is the number of prefill passes that the prompt needs, when the counted number is that or one more.
    """
    prompt = rec.get("prompt_tokens")
    if cls == "prompt_or_mixed" and prompt and prompt % PREFILL_TOKENS_PER_PASS == 0:
        nominal = prompt // PREFILL_TOKENS_PER_PASS
        if counted in (nominal, nominal + 1):
            return nominal
    return counted


def derive_attn(rec):
    """Per-class values from the attention statistics totals (the exit report)."""
    a = rec["attn"]
    hz = a.get("summary", {}).get("tsc_hz")
    out = {}
    for cls in CLASSES:
        c = a.get(cls, {})
        f, t = c.get("forwards"), c.get("totals")
        if not f or not t or not f.get("forwards") or not hz:
            continue
        n = passes(rec, cls, f["forwards"])
        wall = f["wall_cycles"]
        workers = f.get("n_attn_workers_max") or 1
        out[cls] = {
            "forwards": n, "forwards_counted": f["forwards"],
            "token_jobs_per_forward": f["token_jobs"] / n,
            "forward_wall_ms": wall / n / hz * 1e3,
            "attn_w0_wall_ms_per_forward": t["wall_cycles_w0"] / n / hz * 1e3,
            "attn_busy_ms_per_forward": t["busy_cycles"] / n / hz * 1e3 / workers,      # mean over the attention workers
            "attn_join_wait_ms_per_forward": t["join_wait_cycles"] / n / hz * 1e3 / workers,
            "attn_workers": workers,
            "avx_k_tokens_per_forward": (t["ready_avx_k_tokens"] + t["pending_avx_k_tokens"]) / n,
            "amx_k_tokens_per_forward": (t["ready_amx_k_tokens"] + t["pending_amx_k_tokens"]) / n,
            "amx_visits_per_forward": (t["ready_amx_visits"] + t["pending_amx_visits"]) / n,
            "avx_full_page_visits_per_forward": (t["ready_avx_full_page_visits"] + t["pending_avx_full_page_visits"]) / n,
        }
    return out


def derive_gdn(rec):
    """Per-class values from the GDN statistics (the exit report)."""
    g = rec["gdn"]
    hz = g.get("summary", {}).get("tsc_hz")
    out = {}
    for cls in CLASSES:
        c = g.get(cls, {})
        f, t = c.get("forwards"), c.get("totals")
        if not f or not t or not f.get("forwards") or not hz:
            continue
        n = passes(rec, cls, f["forwards"])
        us = lambda cycles, count: cycles / count / hz * 1e6 if count else None
        # The builds measured first printed the chain path as "half". Later builds print "chain".
        t = {k.replace("half_", "chain_"): v for k, v in t.items()}
        head_tokens = {p: t[f"{p}_head_tokens"] for p in ("token", "chain", "amx")}
        all_tokens = sum(head_tokens.values())
        d = {
            "forwards": n,
            "gdn_workers": f.get("n_gdn_workers_max"),
            "chains_per_forward": f.get("chains", 0) / n,
            "forward_wall_ms": f["wall_cycles"] / n / hz * 1e3,
            "gdn_wall_ms_per_forward": sum(c.get("wall_per_op", [])) / n / hz * 1e3 if c.get("wall_per_op") else None,
            "gdn_busy_ms_per_forward": t["busy_cycles"] / n / hz * 1e3,                  # summed over the GDN threads
            "head_tokens_per_forward": all_tokens / n,
            "share_token": head_tokens["token"] / all_tokens if all_tokens else None,
            "share_chain": head_tokens["chain"] / all_tokens if all_tokens else None,
            "share_amx": head_tokens["amx"] / all_tokens if all_tokens else None,
            "amx_blocks": t["amx_blocks"],
            "amx_fallback_blocks": t["amx_fallback_blocks"],
            "chain_full_block_tokens": t["chain_full_block_tokens"],
            # microseconds per head token (= per GDN step: one token of one key head), mean over the GDN threads
            "step_us": us(t["busy_cycles"], all_tokens),
            "step_start_us": us(t["start_cycles"], all_tokens),
            "step_pre_us": us(t["pre_cycles"], all_tokens),
            "step_recurrence_us": us(t["token_recurrence_cycles"] + t["chain_recurrence_cycles"] + t["amx_recurrence_cycles"], all_tokens),
            "step_post_us": us(t["post_cycles"], all_tokens),
            "step_write_us": us(t["write_cycles"], all_tokens),
            "recurrence_token_us": us(t["token_recurrence_cycles"], head_tokens["token"]),
            "recurrence_chain_us": us(t["chain_recurrence_cycles"], head_tokens["chain"]),
            "recurrence_amx_us": us(t["amx_recurrence_cycles"], head_tokens["amx"]),
        }
        pw = c.get("per_worker")
        if pw:
            steps = [b / h / hz * 1e6 for b, h in pw if h]
            d["step_us_per_worker"] = steps
            d["step_us_median_worker"] = st.median(steps) if steps else None
            d["step_us_slowest_worker"] = max(steps) if steps else None
        out[cls] = d
    return out


def run_tips():
    """run name -> short commit of the binary, from the header lines that run-one.sh writes."""
    tips = {}
    for line in open(RES + "/rt-results.txt", errors="replace"):
        m = re.match(r"### run=(\S+) .* tip=([0-9a-f]+) ", line)
        if m:
            tips[m.group(1)] = m.group(2)
    return tips


def main():
    runs = {}
    tips = run_tips()
    for path in sorted(glob.glob(RES + "/rt/*.log")):
        run = os.path.basename(path)[:-4]
        m = re.match(r"(.*?)__([a-z0-9-]+)__rep(\d+)$", run)
        if not m or m.group(2) not in ARMS or run.startswith(("trace-", "tok-")):
            continue
        if not REP_LO <= int(m.group(3)) <= REP_HI:
            continue
        rec = parse_log(path)
        rec["run"] = run
        rec["tip"] = tips.get(run)
        rec["cell"], rec["arm"], rec["rep"] = m.group(1), m.group(2), int(m.group(3))
        rec["users"] = len(rec["tps"])
        rec["derived"] = derive_attn(rec)
        rec["gdn_derived"] = derive_gdn(rec)
        rec["load"] = load_line(run)
        if rec["tps"]:
            rec["tps_mean"] = st.mean(rec["tps"]); rec["tps_sum"] = sum(rec["tps"])
            rec["ttft_max"] = max(rec["ttft"]); rec["ttft_mean"] = st.mean(rec["ttft"])
        runs[run] = rec
    cells = {}
    for run, r in runs.items():
        if not r["tps"]:
            continue
        cells.setdefault(r["cell"], {}).setdefault(r["arm"], []).append(r)
    agg = {}
    for cell, arms in cells.items():
        agg[cell] = {}
        for arm, rs in arms.items():
            rs.sort(key=lambda r: r["rep"])

            def col(fn):
                v = [fn(r) for r in rs]
                if any(x is None for x in v):
                    return None
                return {"values": v, "median": st.median(v), "min": min(v), "max": max(v), "n": len(v)}

            a = {
                "users": rs[0]["users"], "prompt_tokens": rs[0].get("prompt_tokens"),
                "decode_tps_per_user": col(lambda r: r["tps_mean"]),
                "ttft_max_s": col(lambda r: r["ttft_max"]),
                "ttft_mean_s": col(lambda r: r["ttft_mean"]),
                "runs": [r["run"] for r in rs],
                "tips": sorted({r["tip"] for r in rs if r["tip"]}),
                "load_our_app_cores_pct": col(lambda r: r["load"].get("our-app-cores")),
                "load_socket0_pct": col(lambda r: r["load"].get("socket0")),
            }
            for key, name in (("derived", "attn"), ("gdn_derived", "gdn")):
                for cls in CLASSES:
                    if all(cls in r[key] for r in rs):
                        a[f"{name}_{cls}"] = {
                            k: col(lambda r, k=k: r[key][cls][k]) for k in rs[0][key][cls]
                            if isinstance(rs[0][key][cls][k], (int, float)) or rs[0][key][cls][k] is None}
            agg[cell][arm] = a
    out = {"runs": runs, "cells": agg}
    json.dump(out, open(f"{RES}/collected{SUFFIX}.json", "w"), indent=1)
    by_arm = {}
    for r in runs.values():
        by_arm.setdefault(r["arm"], set()).add(r["tip"])
    print(f"reps {REP_LO}-{REP_HI} -> collected{SUFFIX}.json; runs {len(runs)}; commits per arm: "
          + ", ".join(f"{a}={'/'.join(sorted(str(t) for t in ts))}" for a, ts in sorted(by_arm.items())))
    med = lambda d, *ks: (lambda v: v["median"] if v else float("nan"))(_get(d, ks))
    print(f"{'cell':18} {'arm':6} {'n':>2} {'TTFT s':>8} {'tok/s':>7} {'pass ms':>8} {'GDN wall':>9} {'attn busy':>9} {'step us':>8} {'recur us':>8} {'amx %':>6} {'dec ms':>7}")
    order = sorted(agg, key=lambda c: (agg[c][next(iter(agg[c]))]["users"], agg[c][next(iter(agg[c]))]["prompt_tokens"] or 0))
    for cell in order:
        for arm, a in sorted(agg[cell].items()):
            print(f"{cell.replace('q35-tp4-', ''):18} {arm:6} {a['ttft_max_s']['n']:2d} {a['ttft_max_s']['median']:8.3f} {a['decode_tps_per_user']['median']:7.1f} "
                  f"{med(a, 'attn_prompt_or_mixed', 'forward_wall_ms'):8.2f} {med(a, 'gdn_prompt_or_mixed', 'gdn_wall_ms_per_forward'):9.2f} "
                  f"{med(a, 'attn_prompt_or_mixed', 'attn_busy_ms_per_forward'):9.2f} {med(a, 'gdn_prompt_or_mixed', 'step_us'):8.2f} "
                  f"{med(a, 'gdn_prompt_or_mixed', 'step_recurrence_us'):8.2f} {100 * med(a, 'gdn_prompt_or_mixed', 'share_amx'):6.1f} "
                  f"{med(a, 'attn_decode_like', 'forward_wall_ms'):7.3f}")


def _get(d, ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


if __name__ == "__main__":
    main()
