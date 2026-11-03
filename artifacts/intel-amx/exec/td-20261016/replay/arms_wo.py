#!/usr/bin/env python3
"""arms_wo.py: the logged 'WO layer L of token T' records of the td-20261016 arms compared pairwise
(first logged value downstream of attention), and the replay's PREDICTED WO difference of a pair
(replay output difference pushed through the dequantized o_proj) next to the logged one.
Run on delphi-3bda from /var/tmp/jhan/td/replay with the <arm>-L01.txt extracts present.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay as R  # noqa: E402
import wo_check as W  # noqa: E402

f32, f64 = np.float32, np.float64
PAIRS = [("base", "poc"), ("clean", "baseoff"), ("baseoff", "pocoff"), ("clean", "newoff"), ("newoff", "trunc"),
         ("new", "trunc"), ("base", "new"), ("newoff", "new"), ("clean", "new"), ("clean", "base"), ("baseoff", "base")]
MODEL_OF = {"base": "base", "poc": "base", "new": "new", "newoff": "newoff", "trunc": "trunc", "baseoff": "clean",
            "pocoff": "clean", "clean": "clean"}


def cls(T):
    if T < 128: return "prompt_0-127"
    if T < 1024: return "prompt_128-1023"
    return "decode"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", type=int, default=0)
    ap.add_argument("--arms", default="base,new,poc,newoff,trunc,baseoff,pocoff,clean")
    ap.add_argument("--predict-tokens", default="1,100,127,128,129,150,191,1024,1090,1278")
    ap.add_argument("--out", default="arms_wo.json")
    ap.add_argument("--results", default=None, help="replay results json: per-token predicted differences, set overlap with the logged WO")
    args = ap.parse_args()
    arms = {}
    for a in args.arms.split(","):
        p = f"{a}-L01.txt"
        if os.path.exists(p) and os.path.exists(f"{a}-L01.done"):
            arms[a] = R.load_extract(p, args.layer)[0]
            print(f"# loaded {a}: tokens {arms[a]['O'].shape[0]}")
    res = {"layer": args.layer, "arms": sorted(arms), "qkv_identity_vs_base": {}, "pairs": {}, "predicted": {}}
    if "base" in arms:
        for a in arms:
            if a == "base": continue
            res["qkv_identity_vs_base"][a] = {nm: int(np.count_nonzero(arms[a][nm] != arms["base"][nm])) for nm in ("Q", "K", "V")}
        print("# Q/K/V identity vs base (values differing):", res["qkv_identity_vs_base"])
    for a, b in PAIRS:
        if a not in arms or b not in arms: continue
        Oa, Ob = arms[a]["O"], arms[b]["O"]
        n = min(Oa.shape[0], Ob.shape[0])
        rows = []
        for T in range(n):
            d = Oa[T].astype(f64) - Ob[T].astype(f64)
            nrm = np.sqrt((Ob[T].astype(f64) ** 2).sum())
            rows.append((T, int(np.count_nonzero(Oa[T] != Ob[T])), float(np.sqrt((d ** 2).sum()) / nrm)))
        summ = {}
        for c in ("prompt_0-127", "prompt_128-1023", "decode", "all"):
            sub = [r for r in rows if c == "all" or cls(r[0]) == c]
            dif = [r for r in sub if r[1] > 0]
            summ[c] = {"tokens": len(sub), "tokens_with_any_WO_difference": len(dif),
                       "first_differing_token": dif[0][0] if dif else None,
                       "median_frac_elements_differing_when_differing": float(np.median([r[1] / 2560 for r in dif])) if dif else 0.0,
                       "median_rel_l2_when_differing": float(np.median([r[2] for r in dif])) if dif else 0.0,
                       "max_rel_l2": float(max(r[2] for r in sub)) if sub else 0.0}
        res["pairs"][f"{a}_vs_{b}"] = summ
        print(f"{a} vs {b}: " + "; ".join(f"{c}: {v['tokens_with_any_WO_difference']}/{v['tokens']} tokens differ, first {v['first_differing_token']}, "
                                          f"median rel L2 {v['median_rel_l2_when_differing']:.1e}, max {v['max_rel_l2']:.1e}" for c, v in summ.items()))
    # predicted vs logged WO difference for pairs with both arms present
    Wo, _ = W.dequant_o_proj(args.layer)
    toks = [int(x) for x in args.predict_tokens.split(",")]
    for a, b in [("clean", "newoff"), ("newoff", "new"), ("base", "new"), ("clean", "base"), ("new", "trunc")]:
        if a not in arms or b not in arms: continue
        rows = {}
        for T in toks:
            if T >= min(arms[a]["O"].shape[0], arms[b]["O"].shape[0]): continue
            oa, _ = W.attention_outputs(arms["base"] if "base" in arms else arms[a], MODEL_OF[a], T, R.WITHIN_PAIR_ORDER, R.AMX_MODEL)
            ob, _ = W.attention_outputs(arms["base"] if "base" in arms else arms[b], MODEL_OF[b], T, R.WITHIN_PAIR_ORDER, R.AMX_MODEL)
            pred = (oa - ob) @ Wo
            logged = arms[a]["O"][T].astype(f64) - arms[b]["O"][T].astype(f64)
            nrm = np.sqrt((arms[b]["O"][T].astype(f64) ** 2).sum())
            rows[T] = {"predicted_rel_l2": float(np.sqrt((pred ** 2).sum()) / nrm), "logged_rel_l2": float(np.sqrt((logged ** 2).sum()) / nrm),
                       "attn_out_bf16_elements_differing_predicted": int(np.count_nonzero(oa != ob)),
                       "logged_WO_elements_differing": int(np.count_nonzero(arms[a]["O"][T] != arms[b]["O"][T]))}
            print(f"  predicted {a} vs {b} token {T}: attn bf16 differing {rows[T]['attn_out_bf16_elements_differing_predicted']}/4096, "
                  f"WO rel L2 predicted {rows[T]['predicted_rel_l2']:.1e} logged {rows[T]['logged_rel_l2']:.1e} (logged WO elements differing {rows[T]['logged_WO_elements_differing']}/2560)")
        res["predicted"][f"{a}_vs_{b}"] = rows
    if args.results:
        rr = json.load(open(args.results))
        sample = [int(t) for t in rr["per_token"]]
        res["set_overlap"] = {}
        for a, b, key in [("clean", "newoff", "clean_vs_newoff"), ("newoff", "new", "newoff_vs_new"), ("base", "new", "base_vs_new"),
                          ("clean", "base", "clean_vs_base"), ("new", "trunc", "new_vs_trunc"), ("newoff", "trunc", "newoff_vs_trunc"), ("clean", "new", "clean_vs_new")]:
            if a not in arms or b not in arms: continue
            Oa, Ob = arms[a]["O"], arms[b]["O"]
            logged = {T for T in sample if T < min(Oa.shape[0], Ob.shape[0]) and np.any(Oa[T] != Ob[T])}
            pred = {T for T in sample if rr["per_token"][str(T)]["M2"][key]["n_bf16_differ"] > 0}
            pred_big = {T for T in sample if rr["per_token"][str(T)]["M2"][key]["n_bf16_differ"] > 1}
            both = logged & pred
            res["set_overlap"][key] = {"sampled_tokens": len(sample), "logged_differing": sorted(logged), "predicted_differing": sorted(pred),
                                       "n_logged": len(logged), "n_predicted": len(pred), "n_both": len(both),
                                       "n_logged_not_predicted": len(logged - pred), "n_predicted_not_logged": len(pred - logged),
                                       "n_predicted_more_than_one_element": len(pred_big), "n_both_more_than_one_element": len(logged & pred_big),
                                       "first_logged": min(logged) if logged else None, "first_predicted": min(pred) if pred else None}
            o = res["set_overlap"][key]
            print(f"set overlap {key}: logged {o['n_logged']} predicted {o['n_predicted']} both {o['n_both']} logged-not-predicted {o['n_logged_not_predicted']} "
                  f"predicted-not-logged {o['n_predicted_not_logged']} (predicted >1 element: {o['n_predicted_more_than_one_element']}, of which logged {o['n_both_more_than_one_element']}) "
                  f"first logged {o['first_logged']} first predicted {o['first_predicted']}")
    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
