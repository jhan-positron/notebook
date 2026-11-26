#!/usr/bin/env python3
"""gdn-impl-20261121: every number of the result page, read from the result files. No number is typed by hand.

Inputs (all under /home/jhan/workspace/intel-AMX/exec/results/):
  gdn-impl-20261121/comparison.json   compare.py: campaign medians against the prediction
  gdn-impl-20261121/collected.json    collect.py: every run
  gdn-impl-20261121/bench/*.txt       stand-alone measurements (tasks 1, 3 and 4 of the plan)
  gdn-impl-20261121/unit-tests.txt    unit-test results of the three builds
  gdn-impl-20261121/tokens/summary.txt  token-check.sh: generated tokens of each arm against the base arm
  gdn-20261120/predictions.json       the prediction of 2026-11-21
load() returns one dict. gen_report.py turns it into the page.
"""
import glob
import json
import os
import re
import statistics
import statistics as st
import sys

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121"
BENCH = RES + "/bench"
PRED = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json"
CELLS = ["q35-tp4-1u-p1024", "q35-tp4-1u-p4096", "q35-tp4-1u-p8192", "q35-tp4-8u-p1024", "q35-tp4-8u-p4096", "q35-tp4-8u-p8192"]


def _lines(path):
    return open(path, errors="replace").read().splitlines() if os.path.exists(path) else []


def _row_value(lines, label, col=0):
    """The first number after a row label of a benchmark table."""
    for l in lines:
        if label in l:
            nums = re.findall(r"[-+]?\d+\.\d+|[-+]?\d+", l.split(label, 1)[1])
            return float(nums[col])
    return None


def task1():
    """Loop order of the design (two passes, [chunk][row] halves) against today's token loop."""
    runs = []
    for f in sorted(glob.glob(BENCH + "/task1-single-cpu140-run*.txt")):
        L = _lines(f)
        runs.append({
            "token_ns": _row_value(L, "(2) token loop today, one key-head group (128 KiB working copy)"),
            "design_order_ns": _row_value(L, "(2) slice replay G1, blocked  layout, window 128 tokens"),
            "design_order_w32_ns": _row_value(L, "(2) slice replay G1, blocked  layout, window  32 tokens"),
            "l1_slice_ns": _row_value(L, "(2) one 32 KiB slice held in L1 for the chain (x2 = one value head)"),
        })
    copies = []
    for f in sorted(glob.glob(BENCH + "/task1-16copies-cpu*.txt")):
        L = _lines(f)
        copies.append({
            "token_ns": _row_value(L, "(2) token loop today, one key-head group (128 KiB working copy)"),
            "design_order_ns": _row_value(L, "(2) slice replay G1, blocked  layout, window 128 tokens"),
        })
    # every ratio is formed inside one run file
    ratios = [r["token_ns"] / r["design_order_ns"] for r in runs]
    ratios32 = [r["token_ns"] / r["design_order_w32_ns"] for r in runs if r["design_order_w32_ns"]]
    ratios16 = [r["token_ns"] / r["design_order_ns"] for r in copies]
    return {"runs": runs, "ratio": [min(ratios), max(ratios)], "copies16_ratio": [min(ratios16), max(ratios16)],
            "ratio_w32": [min(ratios32), max(ratios32)] if ratios32 else None,
            "token_us": [min(r["token_ns"] for r in runs) / 1e3, max(r["token_ns"] for r in runs) / 1e3],
            "design_order_us": [min(r["design_order_ns"] for r in runs) / 1e3, max(r["design_order_ns"] for r in runs) / 1e3],
            "n_copies": len(copies)}


def slice_variants():
    out = {}
    labels = {
        "token": "token loop today, standard layout, 8 chunks per row (64 KiB)",
        "two_pass_blocked": "two passes, blocked layout [chunk][row], 4 chunks per slice (32 KiB)",
        "two_pass_rows": "two passes, row layout [row][4 chunks], 4 chunks per slice (32 KiB)",
        "fused_rows": "fused passes, row layout, 4 chunks per slice (32 KiB)",
        "fused_std8": "fused passes, standard layout, 8 chunks per row (64 KiB)",
        "read_only": "read loop only, 4-chunk blocked slice in L1 (x2 slices = per value head)",
        "fma": "12 independent FMAs per iteration, no memory operand: ns per FMA",
    }
    files = sorted(glob.glob(BENCH + "/slice-variants-cpu140-run*.txt"))
    for k, lab in labels.items():
        v = [_row_value(_lines(f), lab) for f in files]
        out[k] = [min(v), max(v)]
        # ops per cycle column (3rd number) for the FMA and read-only rows
        if k in ("fma", "read_only", "fused_rows"):
            o = [_row_value(_lines(f), lab, 2) for f in files]
            out[k + "_ops_per_cycle"] = [min(o), max(o)]
    per_run = [_row_value(_lines(f), labels["token"]) / _row_value(_lines(f), labels["fused_rows"]) for f in files]
    out["fused_ratio"] = [min(per_run), max(per_run)]          # formed inside each run file
    out["two_pass_blocked_runs"] = [_row_value(_lines(f), labels["two_pass_blocked"]) for f in files]
    return out


def task3():
    tables = []
    for f in sorted(glob.glob(BENCH + "/task3-table-cpu140-run*.txt")):
        L = _lines(f)
        tables.append({"token_ns": _row_value(L, "token kernel (today)"), "chain_ns": _row_value(L, "chain kernel (Part 0)"),
                       "block_ns": _row_value(L, "block kernel (Part A)")})
    clock = {}
    for l in _lines(BENCH + "/task3-clock-cpu140.txt"):
        m = re.match(r"(\w+)-(\d+|16copies) \| freq_khz_median (\d+).*ns_per_token_per_value_head ([\d.]+)", l)
        if m:
            clock.setdefault(m.group(1) if m.group(2) != "16copies" else m.group(1) + "_16copies", []).append(
                (int(m.group(3)) / 1e6, float(m.group(4))))
    numerics = []
    L = _lines(BENCH + "/task3-table-cpu140-run1.txt")
    for l in L:
        m = re.match(r"(.+?)\s+\| (IDENTICAL|DIFFER)\s+\| ([\d.]+)\s*% (\d+)\s+(\d+)\s+\| ([\d.e+-]+)\s+(\d+)\s+\| ([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.]+)", l)
        if m:
            numerics.append({"case": m.group(1).strip(), "chain_bits": m.group(2), "differ_pct": float(m.group(3)), "max_incr": int(m.group(4)),
                             "max_incr_large": int(m.group(5)), "state_rel_l2": float(m.group(6)), "token_err": float(m.group(8)),
                             "block_err": float(m.group(9)), "state_err_ratio": float(m.group(10))})
    burst = []
    for l in _lines(BENCH + "/task3-burst-cpu140.txt"):
        m = re.match(r"burst (\w+) .* gap_us (\d+) bursts (\d+) kernel_us_per_burst ([\d.]+) ns_per_token_per_value_head ([\d.]+) "
                     r"scalar_clock_ghz first_quarter ([\d.]+) rest ([\d.]+) all ([\d.]+)", l)
        if m:
            burst.append({"kernel": m.group(1), "gap_us": int(m.group(2)), "kernel_us": float(m.group(4)), "ns": float(m.group(5)),
                          "clock_first_quarter": float(m.group(6)), "clock_rest": float(m.group(7))})
    decay = []
    for l in _lines(BENCH + "/task3-decay-cpu140.txt"):
        m = re.match(r"(\S+) (\w+) host .* decay ([\d.e-]+)-([\d.e-]+) .* ns_per_token_per_value_head ([\d.]+)", l)
        if m:
            decay.append({"build": m.group(1), "kernel": m.group(2), "decay_lo": float(m.group(3)), "decay_hi": float(m.group(4)), "ns": float(m.group(5))})
    zu = {}
    for l in _lines(BENCH + "/task3-zeroupper-cpu140.txt"):
        m = re.match(r"(amx_gdn_bench\w*)-\d+ \| freq_khz_median (\d+) .* ns_per_token_per_value_head ([\d.]+)", l)
        if m:
            zu.setdefault("without" if m.group(1).endswith("nozu") else "with", []).append((int(m.group(2)) / 1e6, float(m.group(3))))
    stall = []
    for l in _lines(BENCH + "/stall-test.txt"):
        m = re.match(r"aggressors=(\w+) \| stall_probe cpu (\d+) .* gaps_over_20us (\d+) over_100us (\d+) over_1ms (\d+) longest_us ([\d.]+) lost_ms ([\d.]+)", l)
        if m:
            stall.append({"aggressors": m.group(1), "cpu": int(m.group(2)), "over_20us": int(m.group(3)), "over_100us": int(m.group(4)),
                          "over_1ms": int(m.group(5)), "longest_us": float(m.group(6)), "lost_ms": float(m.group(7))})
    rng = lambda key: [min(t[key] for t in tables) / 1e3, max(t[key] for t in tables) / 1e3] if tables else None
    med = lambda key: statistics.median(t[key] for t in tables) / 1e3 if tables else None
    ratio = lambda key: [min(t["token_ns"] / t[key] for t in tables), max(t["token_ns"] / t[key] for t in tables)] if tables else None
    return {"tables": tables, "token_us": rng("token_ns"), "chain_us": rng("chain_ns"), "block_us": rng("block_ns"),
            "token_med_us": med("token_ns"), "chain_med_us": med("chain_ns"), "block_med_us": med("block_ns"),
            "chain_ratio": ratio("chain_ns"), "block_ratio": ratio("block_ns"),   # formed inside each run file
            "clock": clock, "numerics": numerics, "burst": burst, "decay": decay, "zeroupper": zu, "stall": stall}


def task4():
    rows = []
    for l in _lines(BENCH + "/task4-summary-cpu142.txt"):
        m = re.match(r"(cache|memory)\s+(\w+)\s+\|\s*([\d.]+) -\s*([\d.]+) \|\s*([\d.]+) -\s*([\d.]+) \|\s*([\d.]+) -\s*([\d.]+) \|\s*([\d.]+) -\s*([\d.]+) \|\s*([\d.]+) -\s*([\d.]+)", l)
        if m:
            g = [float(x) for x in m.groups()[2:]]
            rows.append({"regime": m.group(1), "use": m.group(2), "avx_us": g[0:2], "amx_us": g[2:4], "ratio": g[4:6], "avx_clock": g[6:8], "amx_clock": g[8:10]})
    parts = {}
    L = _lines(BENCH + "/task4-summary-cpu142.txt")
    for key, lab in (("qk_avx", "QK,  AVX-512"), ("qk_amx", "QK,  AMX kernel"), ("pv_avx", "PV,  AVX-512"), ("pv_amx", "PV,  AMX kernel"),
                     ("pack", "pack of one query group")):
        for l in L:
            if lab in l:
                parts[key] = float(re.findall(r"\d+\.\d+", l.split(")")[-1])[0])
                break
    # The summary file rounds its ratios twice. Form them again from the times of each table run.
    per_run, t_avx, t_amx = {}, {}, {}
    for f in sorted(glob.glob(BENCH + "/task4-table-cpu142-run*.txt")):
        for l in _lines(f):
            m = re.match(r"(cache|memory)\s+(\w+)\s+\|\s*([\d.]+) \(.*?\)\s+\|\s*([\d.]+) \(", l)
            if m:
                k = (m.group(1), m.group(2))
                per_run.setdefault(k, []).append(float(m.group(3)) / float(m.group(4)))
                t_avx.setdefault(k, []).append(float(m.group(3)))
                t_amx.setdefault(k, []).append(float(m.group(4)))
    for r in rows:
        k = (r["regime"], r["use"])
        if per_run.get(k):
            r["ratio"] = [min(per_run[k]), max(per_run[k])]
            r["avx_us"] = [min(t_avx[k]), max(t_avx[k])]
            r["amx_us"] = [min(t_amx[k]), max(t_amx[k])]
    loops = {}
    for l in _lines(BENCH + "/task4-clock-cpu142.txt"):
        m = re.search(r"(avx|amx)\.(cache|memory)\.(\w+) host .* us_per_page_unit ([\d.]+) freq_khz_median (\d+)", l)
        if m:
            loops.setdefault((m.group(2), m.group(3)), {}).setdefault(m.group(1), []).append(float(m.group(4)))
    # the ratio is formed inside each repetition of the 4 s loops (the n-th AVX-512 loop with the n-th AMX loop)
    loop_ratio = {}
    for k, v in loops.items():
        if "avx" in v and "amx" in v and len(v["avx"]) == len(v["amx"]):
            r_ = [x / y for x, y in zip(v["avx"], v["amx"])]
            loop_ratio[k] = [min(r_), max(r_)]
    load = {}
    for l in _lines(BENCH + "/task4-load.txt"):
        f = l.split()
        if len(f) >= 3 and f[0] in ("socket0", "our-app-cores"):
            load[f[0]] = float(f[2].rstrip("%"))
    cache = [r for r in rows if r["regime"] == "cache"]
    return {"rows": rows, "parts": parts, "loops": loops, "loop_ratio": loop_ratio, "load": load,
            "selfcheck": next((l.strip() for l in _lines(BENCH + "/task4-summary-cpu142.txt") if "running sums v*" in l), None),
            "cache_ratio": [min(r["ratio"][0] for r in cache), max(r["ratio"][1] for r in cache)] if cache else None,
            "memory_decode_ratio": next((r["ratio"] for r in rows if r["regime"] == "memory" and r["use"] == "decode"), None)}


def unit_tests(name="unit-tests.txt"):
    rows = []
    for l in _lines(f"{RES}/{name}"):
        if l.startswith("#") or "|" not in l:
            continue
        f = [x.strip() for x in l.split("|")]
        rows.append({"build": f[0], "commit": f[1], "test": f[2], "assertions": int(f[3]), "cases": int(f[4]), "result": f[5], "skips": int(f[6]),
                     "switch": f[7] if len(f) > 7 else "none"})
    return rows


def review():
    """Counts of the code review before the final commits (understand/review-result.json)."""
    r = json.load(open("/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/understand/review-result.json"))
    v = [x["verdict"]["verdict"] for x in r]
    sev = [x["severity"] for x in r]
    return {"n": len(r), "confirmed": v.count("confirmed"), "partly": v.count("partly"), "refuted": len(r) - v.count("confirmed") - v.count("partly"),
            "bug": sev.count("bug"), "false_claim": sev.count("false-claim"), "test_gap": sev.count("test-gap")}


def tokens():
    """Generated tokens of the token-check runs, read from tokens/p<prompt>__<arm>.txt.

    rows  : every arm against the base arm of the same prompt
    pairs : arm pairs of the same prompt (a second run of an arm, the stand-alone Part B build, Part A with and
            without Part B)
    """
    import glob
    files = {}
    for f in glob.glob(RES + "/tokens/p*__*.txt"):
        m = re.match(r"p(\d+)__(\w+)\.txt$", os.path.basename(f))
        if m:
            files[(int(m.group(1)), m.group(2))] = open(f).read().split()

    def cmp_(x, y):
        n = min(len(x), len(y))
        first = next((i for i in range(n) if x[i] != y[i]), None)
        if first is None and len(x) != len(y):
            first = n
        return {"tokens": len(y), "equal": sum(1 for i in range(n) if x[i] == y[i]), "of": n, "first_difference": first}

    order = ["orig", "base", "base2", "p0", "a0", "a", "a2", "b", "b2", "bonly", "ab", "ab2"]
    rows, pairs = [], []
    for prompt in sorted({k[0] for k in files}):
        base = files.get((prompt, "base"))
        if base is None:
            continue
        for arm in order:
            if (prompt, arm) in files and arm != "base":
                rows.append({"prompt": prompt, "arm": arm, **cmp_(base, files[(prompt, arm)])})
        for x, y, kind in (("base", "base2", "repeat"), ("a", "a2", "repeat"), ("b", "b2", "repeat"), ("ab", "ab2", "repeat"),
                           ("b", "bonly", "partb"), ("a", "ab", "a_ab")):
            if (prompt, x) in files and (prompt, y) in files:
                pairs.append({"prompt": prompt, "x": x, "y": y, "kind": kind, **cmp_(files[(prompt, x)], files[(prompt, y)])})
    return {"rows": rows, "pairs": pairs}


def logit_margins():
    """The two best scores per arm and generated token (logit_summary.py output, tokens/logits-summary-*.txt)."""
    import glob
    out = {}
    for f in sorted(glob.glob(RES + "/tokens/logits-summary-p*-l*.txt")):
        for l in _lines(f):
            m = re.match(r"prompt (\d+) len (\d+) arm (\w+) generated (\d+): best (\d+) (\S+), second (\d+) (\S+), margin (\S+) = (\S+) bf16 steps", l)
            if m:
                out[(int(m.group(1)), m.group(3), int(m.group(4)))] = {
                    "len": int(m.group(2)), "id1": int(m.group(5)), "v1": float(m.group(6)), "id2": int(m.group(7)), "v2": float(m.group(8)),
                    "margin": float(m.group(9)), "steps": float(m.group(10))}
    return out


def bench_loads():
    out = []
    for name, f in (("Task 1 (loop order)", "task1-load.txt"), ("Task 3 (GDN kernels)", "task3-load.txt"), ("Task 3 in bursts", "task3-burst-load.txt"),
                    ("Stall test", "stall-test-load.txt"), ("Task 4 (attention kernel)", "task4-load.txt")):
        d = {"name": name}
        for l in _lines(f"{BENCH}/{f}"):
            x = l.split()
            if len(x) >= 3 and x[0] in ("socket0", "our-app-cores"):
                d[x[0]] = float(x[2].rstrip("%"))
            if l.startswith("=== load snapshot"):
                d["taken"] = l.split()[4]
        if "our-app-cores" in d:
            out.append(d)
    return out


def session_times(first_rep, last_rep):
    """Start of the first run and end of the last run of a block of repetitions, from the campaign log."""
    t0 = t1 = None
    for l in _lines("/home/jhan/workspace/intel-AMX/exec/logs/gdn-impl-20261121-campaign.log"):
        m = re.match(r"(\S+Z) (start|end) \S+__rep(\d+)", l)
        if m and first_rep <= int(m.group(3)) <= last_rep:
            if m.group(2) == "start" and t0 is None:
                t0 = m.group(1)
            if m.group(2) == "end":
                t1 = m.group(1)
    return t0, t1


def side_runs():
    """Runs outside the campaign that the page cites: around the subnormal fix (q-a before, f-a after), and the
    token-check runs (counters of the AMX paths)."""
    sys.path.insert(0, "/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121")
    import collect
    out = {}
    for run in ("q35-tp4-1u-p1024__q-a__rep1", "q35-tp4-1u-p1024__q-a__rep2", "q35-tp4-1u-p1024__f-a__rep1", "q35-tp4-1u-p1024__f-a__rep2",
                "tok-q35-tp4-1u-p1024__ab__rep1", "tok-q35-tp4-1u-p1024__b__rep1", "tok-q35-tp4-1u-p1024__a__rep1"):
        path = f"{RES}/rt/{run}.log"
        if not os.path.exists(path):
            continue
        rec = collect.parse_log(path)
        g = collect.derive_gdn(rec).get("prompt_or_mixed", {})
        walls = rec["gdn"].get("prompt_or_mixed", {}).get("wall_per_op") or []
        med = statistics.median(walls) if walls else None
        at = rec["attn"].get("prompt_or_mixed", {}).get("totals", {})
        gt = rec["gdn"].get("prompt_or_mixed", {}).get("totals", {})
        ld = collect.load_line(run)
        out[run] = {"ttft": max(rec["ttft"]) if rec["ttft"] else None, "gdn_wall_ms": g.get("gdn_wall_ms_per_forward"),
                    "load_ours": ld.get("our-app-cores"), "load_socket0": ld.get("socket0"),
                    "ops": len(walls), "ops_over_1_5": sum(w > 1.5 * med for w in walls) if walls else None,
                    "max_over_median": max(walls) / med if walls else None,
                    "amx_k_tokens": at.get("ready_amx_k_tokens", 0) + at.get("pending_amx_k_tokens", 0),
                    "amx_head_tokens": gt.get("amx_head_tokens")}
    return out


def score_compare():
    """Best scores of two runs, step by step, from the kept top-k lines (tokens/logits-p1024-l<len>__<arm>.txt).

    A step is one generated token. The log keeps the 320 best scores of a step. Differences are counted in bf16
    steps at the size of the base score, over the token ids that both runs keep.
    Returns per pair: per-step rows (g, common ids, ids that differ, largest difference, difference of the best id,
    same best id, margin of the base run between its two best ids).
    """
    import math

    def read(path):
        rows = {}
        for line in _lines(path):
            m = re.search(r"Top-k (Logits|Token IDs for Logits) of token (\d+) \((\d+)\):(.*)", line)
            if m:
                rows.setdefault(int(m.group(2)), {})["v" if m.group(1) == "Logits" else "id"] = m.group(4).split()
                rows[int(m.group(2))]["k"] = int(m.group(3))
        return rows

    step = lambda x: 2.0 ** (math.floor(math.log2(abs(x))) - 7)
    prompt = 1024
    out = {}
    for name, fx, fy in (("repeat", "logits-p1024-l4__base.txt", "logits-p1024-l190__base.txt"), ("b", "logits-p1024-l4__base.txt", "logits-p1024-l4__b.txt"),
                         ("a", "logits-p1024-l190__base.txt", "logits-p1024-l190__a.txt")):
        x, y = read(f"{RES}/tokens/{fx}"), read(f"{RES}/tokens/{fy}")
        rows = []
        for tok in sorted(set(x) & set(y)):
            if "v" not in x[tok] or "v" not in y[tok]:
                continue
            dx = dict(zip(x[tok]["id"], map(float, x[tok]["v"])))
            dy = dict(zip(y[tok]["id"], map(float, y[tok]["v"])))
            common = set(dx) & set(dy)
            d = [abs(dx[i] - dy[i]) / step(dx[i]) for i in common]
            i1, i2 = x[tok]["id"][0], x[tok]["id"][1]
            rows.append({"g": tok - (prompt - 1), "k": x[tok]["k"], "common": len(common), "differ": sum(v > 0 for v in d), "largest": max(d) if d else 0.0,
                         "best_diff": abs(dx[i1] - dy[i1]) / step(dx[i1]) if i1 in dy else None, "same_best": i1 == y[tok]["id"][0],
                         "margin": (dx[i1] - dx[i2]) / step(dx[i1])})
        if rows:
            out[name] = rows
    return out


def _json(name):
    try:
        return json.load(open(f"{RES}/{name}"))
    except FileNotFoundError:
        return None


def load():
    cmp_ = json.load(open(RES + "/comparison.json"))
    col = json.load(open(RES + "/collected.json"))
    pred = json.load(open(PRED))
    builds = {}
    for tag in ("ctr", "pa", "pab"):
        L = _lines(f"{RES}/build-{tag}.txt")
        tip = next((l.split()[1] for l in L if l.startswith("tip ")), None)
        builds[tag] = tip
    return {"cmp": cmp_, "col": col, "pred": pred, "task1": task1(), "variants": slice_variants(), "task3": task3(), "task4": task4(),
            "unit": unit_tests() + [u for u in unit_tests("unit-tests-noamx.txt") if u["build"] == "noamx"],
            "tokens": tokens(), "builds": builds, "cells": [c for c in CELLS if c in cmp_["cells"]],
            # session 1 = the commits before the code review; controls = arms base, nost, orig of the final commits
            "cmp1": _json("comparison-session1.json"), "cmpc": _json("comparison-controls.json"),
            "unit1": unit_tests("unit-tests-session1.txt"), "unit_measured": unit_tests("unit-tests-measured.txt"),
            "logit": logit_margins(), "scores": score_compare(), "bench_loads": bench_loads(), "session2_times": session_times(11, 19),
            "side": side_runs(), "colc": _json("collected-controls.json"), "col1": _json("collected-session1.json")}


if __name__ == "__main__":
    d = load()
    for k in ("task1", "variants", "task4", "builds"):
        print(k, json.dumps(d[k], indent=0)[:1200])
    t3 = d["task3"]
    print("task3", t3["token_us"], t3["chain_us"], t3["block_us"], {k: v[:2] for k, v in t3["clock"].items()})
    print("numerics", len(t3["numerics"]), "burst", len(t3["burst"]), "decay", len(t3["decay"]), "stall", len(t3["stall"]), "unit", len(d["unit"]), "tokens", len(d["tokens"]["rows"]), len(d["tokens"]["pairs"]))
