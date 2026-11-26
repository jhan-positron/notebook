#!/usr/bin/env python3
"""gdn-impl-20261121: compare the measured effect of the GDN/AMX changes with the prediction of 2026-11-21.

Words used here:
- prediction: exec/results/gdn-20261120/predictions.json, written by predict.py before any change was built
  (GDN/gdn-amx-design.html section 4). Per cell it holds a low, a working ("mid") and a high value of the time to
  first token (TTFT) and of the decode speed, for these scenarios:
    reorder       Part 0 (GDN chain kernel, no AMX)
    amx_gdn       Part A (AMX block kernel for GDN)
    amx_attn      Part B alone (AMX attention kernel on today's GDN loop; not runnable, used through seconds)
    reorder_attn  Part 0 + Part B
    amx_both      Part A + Part B
- arm: one build with one set of switches (campaign.sh): base, p0, b, ab, a0, a.
- cell: one combination of user count and prompt length.
- fall: base TTFT minus the TTFT of an arm. Every predicted range is a percent of the base TTFT, so a fall is
  divided by the TTFT of the base run of THIS session (the plan's rule, design section 6).
- pass rules: the rules of tasks 2, 5 and 6 of the plan (design section 6).

Inputs : exec/results/gdn-impl-20261121/collected<SUFFIX>.json (collect.py), exec/results/gdn-20261120/predictions.json
Output : exec/results/gdn-impl-20261121/comparison<SUFFIX>.json and a text table on stdout.
Usage  : [SUFFIX=-session1] python3 compare.py [results folder]
"""
import json
import os
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121"
PRED = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/predictions.json"
CELLS = ["q35-tp4-1u-p1024", "q35-tp4-1u-p4096", "q35-tp4-1u-p8192", "q35-tp4-8u-p1024", "q35-tp4-8u-p4096", "q35-tp4-8u-p8192"]
# measured arm -> predicted scenario, for the direct comparisons against the base run
DIRECT = [("p0", "reorder", "Part 0"), ("a", "amx_gdn", "Part A"), ("b", "reorder_attn", "Part 0 + Part B"), ("ab", "amx_both", "Parts A and B")]
SUFFIX = os.environ.get("SUFFIX", "")   # same meaning as in collect.py: which session's file to read and write
DECODE_RULE_PCT = 1.1   # task 5: decode with Part B at most 1.1 % below decode with the kill switch


def med(a, *keys):
    d = a
    for k in keys:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return None
        d = d[k]
    return d["median"] if isinstance(d, dict) and "median" in d else d


def spread(a, *keys):
    d = a
    for k in keys:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            return None
        d = d[k]
    return [d["min"], d["max"]] if isinstance(d, dict) and "min" in d else None


def verdict(x, lo, hi):
    """Where a measured fall lies against the predicted range [lo, hi] (percent of base)."""
    if x is None:
        return "no data"
    if x < lo:
        return "below the range"
    if x > hi:
        return "above the range"
    return "inside the range"


def main():
    col = json.load(open(f"{RES}/collected{SUFFIX}.json"))["cells"]
    pred = json.load(open(PRED))
    out = {"assumptions": pred["assumptions"], "cells": {}, "rules": {}}
    for cell in CELLS:
        if cell not in col or "base" not in col[cell]:
            continue
        arms = col[cell]
        pc = pred["cells"][cell]
        base = arms["base"]
        t_base = med(base, "ttft_max_s")
        tps_base = med(base, "decode_tps_per_user")
        t_pred_base = pc["prefill"]["ttft_s"]
        rec = {
            "users": base["users"], "prompt": base["prompt_tokens"],
            "base": {"ttft_s": t_base, "ttft_range_s": spread(base, "ttft_max_s"), "tps": tps_base, "tps_range": spread(base, "decode_tps_per_user"),
                     "ttft_2026_11_20_s": t_pred_base, "tps_2026_11_20": pc["decode"]["tps"], "n": base["ttft_max_s"]["n"]},
            "arms": {}, "direct": {}, "terms": {},
        }
        for arm, a in arms.items():
            t = med(a, "ttft_max_s")
            tps = med(a, "decode_tps_per_user")
            rec["arms"][arm] = {
                "n": a["ttft_max_s"]["n"], "tips": a.get("tips", []), "ttft_s": t,
                # every repetition against the median of the base run: the fall of the time to first token
                "ttft_fall_pct_per_rep": [100 * (t_base - v) / t_base for v in a["ttft_max_s"]["values"]],
                "tps_change_pct_per_rep": [100 * (v - tps_base) / tps_base for v in a["decode_tps_per_user"]["values"]],
                "ttft_spread_pct": 100 * (a["ttft_max_s"]["max"] - a["ttft_max_s"]["min"]) / t,
                "tps_spread_pct": 100 * (a["decode_tps_per_user"]["max"] - a["decode_tps_per_user"]["min"]) / tps, "ttft_range_s": spread(a, "ttft_max_s"),
                "ttft_fall_pct_of_base": 100 * (t_base - t) / t_base,
                "tps": tps, "tps_range": spread(a, "decode_tps_per_user"), "tps_change_pct": 100 * (tps - tps_base) / tps_base,
                "load_our_app_cores_pct": med(a, "load_our_app_cores_pct"), "load_socket0_pct": med(a, "load_socket0_pct"),
            }
            pf, dc, g, gd = a.get("attn_prompt_or_mixed", {}), a.get("attn_decode_like", {}), a.get("gdn_prompt_or_mixed", {}), a.get("gdn_decode_like", {})
            rec["terms"][arm] = {
                "prefill_pass_ms": med(pf, "forward_wall_ms"), "prefill_passes": med(pf, "forwards"),
                "prefill_gdn_wall_ms": med(g, "gdn_wall_ms_per_forward"), "prefill_gdn_busy_ms": med(g, "gdn_busy_ms_per_forward"),
                "prefill_attn_busy_ms": med(pf, "attn_busy_ms_per_forward"), "prefill_attn_join_wait_ms": med(pf, "attn_join_wait_ms_per_forward"),
                "prefill_attn_w0_wall_ms": med(pf, "attn_w0_wall_ms_per_forward"),
                "prefill_amx_k_tokens": med(pf, "amx_k_tokens_per_forward"), "prefill_avx_k_tokens": med(pf, "avx_k_tokens_per_forward"),
                "gdn_step_us": med(g, "step_us"), "gdn_step_median_worker_us": med(g, "step_us_median_worker"),
                "gdn_step_slowest_worker_us": med(g, "step_us_slowest_worker"),
                "gdn_step_pre_us": med(g, "step_pre_us"), "gdn_step_recurrence_us": med(g, "step_recurrence_us"),
                "gdn_step_post_us": med(g, "step_post_us"), "gdn_step_start_us": med(g, "step_start_us"), "gdn_step_write_us": med(g, "step_write_us"),
                "gdn_share_token": med(g, "share_token"), "gdn_share_chain": med(g, "share_chain"), "gdn_share_amx": med(g, "share_amx"),
                "gdn_amx_fallback_blocks": med(g, "amx_fallback_blocks"),
                "decode_step_ms": med(dc, "forward_wall_ms"), "decode_gdn_wall_ms": med(gd, "gdn_wall_ms_per_forward"),
                "decode_attn_busy_ms": med(dc, "attn_busy_ms_per_forward"), "decode_gdn_step_us": med(gd, "step_us"),
                "decode_attn_join_wait_ms": med(dc, "attn_join_wait_ms_per_forward"), "attn_workers": med(pf, "attn_workers"),
                "decode_amx_k_tokens": med(dc, "amx_k_tokens_per_forward"),
            }
        # direct comparisons: arm against the base run, against the predicted scenario
        for arm, scenario, name in DIRECT:
            if arm not in arms:
                continue
            p = {lvl: 100 * (t_pred_base - pc["pred"][lvl][scenario]["ttft_s"]) / t_pred_base for lvl in ("lo", "mid", "hi")}
            m = rec["arms"][arm]["ttft_fall_pct_of_base"]
            ptps = {lvl: 100 * (pc["pred"][lvl][scenario]["tps"] - pc["decode"]["tps"]) / pc["decode"]["tps"] for lvl in ("lo", "mid", "hi")}
            rec["direct"][arm] = {
                "name": name, "scenario": scenario, "measured_fall_pct": m, "measured_ttft_s": rec["arms"][arm]["ttft_s"],
                "predicted_fall_pct": p, "predicted_ttft_s_scaled": {lvl: t_base * (1 - p[lvl] / 100) for lvl in p},
                "verdict": verdict(m, p["lo"], p["hi"]),
                "measured_tps_change_pct": rec["arms"][arm]["tps_change_pct"], "predicted_tps_change_pct": ptps,
                "predicted_pass_ms": {lvl: pc["pred"][lvl][scenario]["t1_prefill_ms"] for lvl in ("lo", "mid", "hi")},
                "measured_pass_ms": rec["terms"][arm]["prefill_pass_ms"],
            }
        # the plan's paired comparisons (design section 6)
        rules = {}
        if "p0" in arms:
            p = {lvl: 100 * (t_pred_base - pc["pred"][lvl]["reorder"]["ttft_s"]) / t_pred_base for lvl in ("lo", "hi")}
            m = rec["arms"]["p0"]["ttft_fall_pct_of_base"]
            rules["task2_part0"] = {"measured_pct_of_base": m, "range": [p["lo"], p["hi"]], "verdict": verdict(m, p["lo"], p["hi"])}
        if "p0" in arms and "b" in arms:
            fall_s = rec["arms"]["p0"]["ttft_s"] - rec["arms"]["b"]["ttft_s"]
            p = {lvl: 100 * (t_pred_base - pc["pred"][lvl]["amx_attn"]["ttft_s"]) / t_pred_base for lvl in ("lo", "mid", "hi")}
            m = 100 * fall_s / t_base
            dec = 100 * (rec["arms"]["b"]["tps"] - rec["arms"]["p0"]["tps"]) / rec["arms"]["p0"]["tps"]
            rules["task5_partB"] = {"ab_fall_s": fall_s, "measured_pct_of_base": m, "range": [p["lo"], p["hi"]], "working": p["mid"],
                                    "verdict": verdict(m, p["lo"], p["hi"]),
                                    "decode_change_vs_kill_switch_pct": dec, "decode_rule_pass": dec >= -DECODE_RULE_PCT,
                                    "amx_k_tokens_per_prefill_pass": rec["terms"]["b"]["prefill_amx_k_tokens"]}
        if "a0" in arms and "a" in arms and "p0" in arms:
            ab_fall = rec["arms"]["a0"]["ttft_s"] - rec["arms"]["a"]["ttft_s"]
            base_to_p0 = t_base - rec["arms"]["p0"]["ttft_s"]
            p = {lvl: 100 * (t_pred_base - pc["pred"][lvl]["amx_gdn"]["ttft_s"]) / t_pred_base for lvl in ("lo", "mid", "hi")}
            m = 100 * (base_to_p0 + ab_fall) / t_base
            rules["task6_partA"] = {"ab_fall_s": ab_fall, "ab_fall_pct_of_run1": 100 * ab_fall / rec["arms"]["a0"]["ttft_s"],
                                    "ttft_lower_with_part_a": ab_fall > 0, "measured_pct_of_base": m, "range": [p["lo"], p["hi"]],
                                    "working": p["mid"], "verdict": verdict(m, p["lo"], p["hi"])}
        rec["rules"] = rules
        # measured factors against the assumed ones
        tb = rec["terms"]["base"]
        fac = {}
        for arm in rec["terms"]:
            ta = rec["terms"][arm]
            f = {}
            if tb.get("prefill_gdn_wall_ms") and ta.get("prefill_gdn_wall_ms"):
                f["gdn_wall"] = tb["prefill_gdn_wall_ms"] / ta["prefill_gdn_wall_ms"]
            if tb.get("gdn_step_us") and ta.get("gdn_step_us"):
                f["gdn_step_mean"] = tb["gdn_step_us"] / ta["gdn_step_us"]
            if tb.get("gdn_step_median_worker_us") and ta.get("gdn_step_median_worker_us"):
                f["gdn_step_median_worker"] = tb["gdn_step_median_worker_us"] / ta["gdn_step_median_worker_us"]
            if tb.get("prefill_attn_busy_ms") and ta.get("prefill_attn_busy_ms"):
                f["attn_busy_prefill"] = tb["prefill_attn_busy_ms"] / ta["prefill_attn_busy_ms"]
            if tb.get("decode_attn_busy_ms") and ta.get("decode_attn_busy_ms"):
                f["attn_busy_decode"] = tb["decode_attn_busy_ms"] / ta["decode_attn_busy_ms"]
            if tb.get("prefill_pass_ms") and ta.get("prefill_pass_ms") and tb.get("prefill_gdn_wall_ms") and ta.get("prefill_gdn_wall_ms"):
                f["pass_fall_ms"] = tb["prefill_pass_ms"] - ta["prefill_pass_ms"]
                f["gdn_wall_fall_ms"] = tb["prefill_gdn_wall_ms"] - ta["prefill_gdn_wall_ms"]
                f["rest_ms"] = ta["prefill_pass_ms"] - ta["prefill_gdn_wall_ms"]
                f["rest_base_ms"] = tb["prefill_pass_ms"] - tb["prefill_gdn_wall_ms"]
            fac[arm] = f
        rec["factors"] = fac
        out["cells"][cell] = rec
    # all-cell rule summary
    def all_cells(rule, key):
        vals = [out["cells"][c]["rules"].get(rule, {}).get(key) for c in out["cells"]]
        return vals
    out["rules"] = {
        "task2_part0_verdicts": all_cells("task2_part0", "verdict"),
        "task5_partB_verdicts": all_cells("task5_partB", "verdict"),
        "task5_decode_rule": all_cells("task5_partB", "decode_rule_pass"),
        "task6_partA_verdicts": all_cells("task6_partA", "verdict"),
        "task6_ttft_lower": all_cells("task6_partA", "ttft_lower_with_part_a"),
    }
    json.dump(out, open(f"{RES}/comparison{SUFFIX}.json", "w"), indent=1)

    f1 = lambda v, d=1: "   n/a" if v is None else f"{v:6.{d}f}"
    print("TTFT fall in percent of the base run of this session; predicted low / working / high in brackets")
    print(f"{'cell':10} {'base s':>8} | " + " | ".join(f"{n:^38}" for _, _, n in DIRECT))
    for cell, rec in out["cells"].items():
        row = f"{cell.replace('q35-tp4-', ''):10} {rec['base']['ttft_s']:8.3f} | "
        parts = []
        for arm, _, _ in DIRECT:
            d = rec["direct"].get(arm)
            parts.append("{:^38}".format("-" if not d else f"{d['measured_fall_pct']:5.1f} [{d['predicted_fall_pct']['lo']:4.1f} /{d['predicted_fall_pct']['mid']:5.1f} /{d['predicted_fall_pct']['hi']:5.1f}] {d['verdict'].split()[0]}"))
        print(row + " | ".join(parts))
    print("\ndecode tok/s per user, change against the base run in percent")
    arms_seen = sorted({a for r in out["cells"].values() for a in r["arms"]})
    print(f"{'cell':10} " + " ".join(f"{a:>14}" for a in arms_seen))
    for cell, rec in out["cells"].items():
        print(f"{cell.replace('q35-tp4-', ''):10} " + " ".join(
            f"{rec['arms'][a]['tps']:7.1f} {rec['arms'][a]['tps_change_pct']:+5.1f}%" if a in rec["arms"] else f"{'-':>14}" for a in arms_seen))
    print("\nprefill pass: wall / GDN wall / attention busy (ms), GDN step (us), AMX share of GDN tokens")
    for cell, rec in out["cells"].items():
        for a in arms_seen:
            if a not in rec["terms"]:
                continue
            t = rec["terms"][a]
            print(f"{cell.replace('q35-tp4-', ''):10} {a:5} pass {f1(t['prefill_pass_ms'], 2)} gdn {f1(t['prefill_gdn_wall_ms'], 2)} attn {f1(t['prefill_attn_busy_ms'], 2)} "
                  f"step {f1(t['gdn_step_us'], 2)} (pre {f1(t['gdn_step_pre_us'], 2)} rec {f1(t['gdn_step_recurrence_us'], 2)} post {f1(t['gdn_step_post_us'], 2)}) "
                  f"amx {f1(None if t['gdn_share_amx'] is None else 100 * t['gdn_share_amx'], 0)}% dec step {f1(t['decode_step_ms'], 3)} ms")
    print("\nrules:", json.dumps(out["rules"]))


if __name__ == "__main__":
    main()
