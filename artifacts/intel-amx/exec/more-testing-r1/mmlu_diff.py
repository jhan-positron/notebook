#!/usr/bin/env python3
"""Per-question comparison of two MMLU Pro runs (eval_results/ directories of
two cells). Both runs answer the identical question set, so the interesting
numbers are: how many predicted letters changed, and of those how many went
right->wrong and wrong->right. Also reports questions where the model's full
response text is byte-identical (no numerics-induced divergence at all).

Usage: mmlu_diff.py <eval_results_A> <eval_results_B> [--json out]
"""
import glob
import json
import os
import sys


def load(d):
    q = {}
    for f in glob.glob(os.path.join(d, "*_result.json")):
        for r in json.load(open(f)):
            q[str(r["question_id"])] = r
    return q


def compare(a_dir, b_dir):
    A, B = load(a_dir), load(b_dir)
    common = sorted(set(A) & set(B), key=int)
    out = {"n_common": len(common), "n_only_a": len(set(A) - set(B)), "n_only_b": len(set(B) - set(A)),
           "pred_changed": 0, "right_to_wrong": 0, "wrong_to_right": 0, "wrong_to_wrong_changed": 0,
           "response_identical": 0, "response_identical_pred_same": 0, "per_subject": {}}
    for qid in common:
        a, b = A[qid], B[qid]
        subj = a.get("category", "?")
        ps = out["per_subject"].setdefault(subj, {"n": 0, "pred_changed": 0, "right_to_wrong": 0, "wrong_to_right": 0, "response_identical": 0})
        ps["n"] += 1
        same_resp = (a.get("response") or "") == (b.get("response") or "")
        if same_resp:
            out["response_identical"] += 1; ps["response_identical"] += 1
        if a["pred"] != b["pred"]:
            out["pred_changed"] += 1; ps["pred_changed"] += 1
            ra, rb = a["pred"] == a["answer"], b["pred"] == b["answer"]
            if ra and not rb: out["right_to_wrong"] += 1; ps["right_to_wrong"] += 1
            elif rb and not ra: out["wrong_to_right"] += 1; ps["wrong_to_right"] += 1
            else: out["wrong_to_wrong_changed"] += 1
        elif same_resp:
            out["response_identical_pred_same"] += 1
    out["score_a"] = sum(1 for q in common if A[q]["pred"] == A[q]["answer"])
    out["score_b"] = sum(1 for q in common if B[q]["pred"] == B[q]["answer"])
    return out


if __name__ == "__main__":
    a, b = sys.argv[1], sys.argv[2]
    res = compare(a, b)
    if "--json" in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    n = res["n_common"]
    print(f"questions compared: {n} (only in A: {res['n_only_a']}, only in B: {res['n_only_b']})")
    print(f"score A {res['score_a']}/{n} = {100*res['score_a']/n:.2f}%   score B {res['score_b']}/{n} = {100*res['score_b']/n:.2f}%   delta {100*(res['score_b']-res['score_a'])/n:+.2f} points")
    print(f"response text identical: {res['response_identical']} ({100*res['response_identical']/n:.1f}%)")
    print(f"predicted letter changed: {res['pred_changed']} ({100*res['pred_changed']/n:.1f}%): right->wrong {res['right_to_wrong']}, wrong->right {res['wrong_to_right']}, wrong->other wrong {res['wrong_to_wrong_changed']}")
    print("per subject (n, changed, r->w, w->r, identical responses):")
    for s, v in sorted(res["per_subject"].items()):
        print(f"  {s:18s} {v['n']:4d} {v['pred_changed']:4d} {v['right_to_wrong']:4d} {v['wrong_to_right']:4d} {v['response_identical']:4d}")
