#!/usr/bin/env python3
"""Near-tie flip statistics from the per-step logit comparisons (issue #4444).

Input: steps-*.json files written by exec/dd/dd_logits_step.py. Each row of
"steps" holds, for one generated step k:
  margin_off          OFF-arm top-1 logit minus top-2 logit (logit units)
  ulp_top1_off        bf16 ulp (one notch) of the OFF-arm top-1 logit
  margin_off_ulps     margin_off / ulp_top1_off
  delta_pair          (on - off) of top-1 minus (on - off) of top-2 of the OFF pair,
                      i.e. how much the arm change moves the margin
  margin_on_same_pair margin_off + delta_pair
  off_top1/off_top2/on_top1/on_top2, same_top1
  mean_abs_delta, frac_changed, tvd (vocabulary-wide statistics)
"OFF arm" means the log passed as --off to dd_logits_step.py (the first-named arm
of the pair, e.g. "new" in new-vs-base); "ON arm" is the --on log.

Tie-break rule (dd_logits_step.py top2(): np.argmax = first maximal index, as
std::max_element): on an exact tie the LOWER id wins. So the ON arm keeps the OFF
top-1 iff  m + d > 0, or m + d == 0 and off_top1 < off_top2.

Usage: tie_stats.py [--out-dir DIR]   (writes tie_stats.json and tie_stats.md)
"""
import argparse
import json
import os
import sys

import numpy as np

R = "/home/jhan/workspace/intel-AMX/exec/results"
PAIRS = [
  # name, file, off arm, on arm, note
  ("new-vs-base", f"{R}/p83-20261013/steps-new-vs-base.json", "new (PR4 ea94e95a, CPU attention)", "base (main 72308ec9, CPU)", "prompt 1024"),
  ("new-vs-head", f"{R}/p83-20261013/steps-new-vs-head.json", "new", "head (PR3 dfafd13d, CPU)", "prompt 1024"),
  ("new-vs-newforced", f"{R}/p83-20261013/steps-new-vs-newforced.json", "new", "new replayed (A/A control)", "prompt 1024, control"),
  ("fnew-vs-fhead", f"{R}/p83-20261013/steps-fnew-vs-fhead.json", "fnew (PR4, FPGA attention)", "fhead (PR3, FPGA)", "prompt 1024"),
  ("fnew-vs-fbase", f"{R}/p83-20261013/steps-fnew-vs-fbase.json", "fnew", "fbase (main, FPGA)", "prompt 1024"),
  ("new-vs-newoff", f"{R}/p83-20261013/steps-new-vs-newoff.json", "new", "newoff (PR4, TRON_AMX_DISABLE=1)", "prompt 1024"),
  ("r3x-vs-r4x-20260830", f"{R}/dd/steps-r4x.json", "r3x (runtron.canon, AMX off)", "r4x (runtron.canon, AMX on)", "prompt 2048, 2026-08-30"),
]
CONTROL = "new-vs-newforced"
T = f"{R}/td-20261016"
ARMS2 = {"base": "base (main 72308ec9, AMX on)", "baseoff": "baseoff (main, TRON_AMX_DISABLE=1)",
         "new": "new (PR4 ea94e95a, AMX on)", "newoff": "newoff (PR4, TRON_AMX_DISABLE=1)",
         "poc": "poc (runtron.poc, AMX on)", "pocoff": "pocoff (runtron.poc, TRON_AMX_DISABLE=1)",
         "trunc": "trunc (runtron.trunc, AMX on)", "clean": "clean (runtron.clean, AMX on)"}
PAIRS2 = [(f"{a}-vs-{b}", f"{T}/steps-{a}-vs-{b}.json", ARMS2[a], ARMS2[b], "prompt 1024, 2026-10-16")
          for a, b in [("base", "poc"), ("baseoff", "pocoff"), ("clean", "baseoff"), ("base", "new"), ("new", "newoff"),
                       ("newoff", "trunc"), ("new", "trunc"), ("baseoff", "base"), ("baseoff", "newoff"), ("clean", "new")]]
CONTROLS2 = ["baseoff-vs-pocoff", "clean-vs-baseoff"]
KEY_STEPS = [20, 84, 248]
POOL_P83 = ["new-vs-base", "new-vs-head", "fnew-vs-fhead", "fnew-vs-fbase", "new-vs-newoff"]
POOL_ALL = POOL_P83 + ["r3x-vs-r4x-20260830"]


def pct(a, q):
  return float(np.percentile(np.asarray(a, dtype=float), q))  # numpy default: linear interpolation


def dist(a):
  a = np.asarray(a, dtype=float)
  return {"n": int(a.size), "median": pct(a, 50), "p10": pct(a, 10), "p05": pct(a, 5), "p95": pct(a, 95),
          "min": float(a.min()), "max": float(a.max())}


def load(path):
  d = json.load(open(path))
  rows = [r for r in d["steps"] if "margin_off" in r]
  return d["summary"], rows


def model_flip(m, d, o1, o2):
  """ON arm's top-1 differs from OFF top-1, restricted to the OFF top pair, with the lowest-id tie-break."""
  s = m + d
  if s < 0:
    return True
  if s == 0:
    return o2 < o1
  return False


def predict(margins, o1s, o2s, dpool):
  """P(flip at k) with d drawn from dpool independently of m_k."""
  dpool = np.asarray(dpool, dtype=float)
  ps = []
  for m, o1, o2 in zip(margins, o1s, o2s):
    p = float(np.mean(dpool < -m))
    if o2 < o1:
      p += float(np.mean(dpool == -m))
    ps.append(p)
  ps = np.asarray(ps)
  # exact Poisson-binomial distribution of the flip count (independent steps)
  pmf = np.array([1.0])
  for p in ps:
    pmf = np.convolve(pmf, [1 - p, p])
  return ps, pmf


def tail(pmf, k):
  return float(pmf[k:].sum()) if k < pmf.size else 0.0


def analyse(name, path, off_arm, on_arm, note):
  summary, rows = load(path)
  n = len(rows)
  m = np.array([r["margin_off"] for r in rows])
  mu = np.array([r["margin_off_ulps"] for r in rows])
  ulp = np.array([r["ulp_top1_off"] for r in rows])
  d = np.array([r["delta_pair"] for r in rows])
  du = d / ulp
  o1 = np.array([r["off_top1"] for r in rows])
  o2 = np.array([r["off_top2"] for r in rows])
  n1 = np.array([r["on_top1"] for r in rows])
  same = np.array([r["same_top1"] for r in rows])
  steps = np.array([r["step"] for r in rows])
  obs_flips = [int(s) for s in steps[~same]]

  # consistency of the fields
  assert np.allclose(m / ulp, mu), "margin_off_ulps != margin_off/ulp_top1_off"
  assert np.allclose(np.array([r["margin_on_same_pair"] for r in rows]), m + d), "margin_on_same_pair != margin_off + delta_pair"
  on_in_pair = bool(np.all(np.isin(n1, np.stack([o1, o2], 1)) | True))  # placeholder, computed exactly below
  on_in_pair = all(int(n1[i]) in (int(o1[i]), int(o2[i])) for i in range(n))
  assert sorted(obs_flips) == sorted(summary["flip_steps"]), "flip_steps mismatch with summary"

  # Q3 reconstruction by the deterministic model
  model = np.array([model_flip(m[i], d[i], o1[i], o2[i]) for i in range(n)])
  model_flips = [int(s) for s in steps[model]]
  reproduced = model_flips == obs_flips and bool(np.all(model == ~same))

  out = {
    "file": path, "off_arm": off_arm, "on_arm": on_arm, "note": note, "n_steps": n,
    "fields": {"margin": "margin_off", "margin_ulps": "margin_off_ulps", "ulp": "ulp_top1_off",
               "delta_pair": "delta_pair", "mean_abs_delta": "mean_abs_delta", "frac_changed": "frac_changed",
               "tvd": "tvd", "flip": "same_top1 == false"},
    "observed_flips": obs_flips,
    "on_top1_always_in_off_top_pair": on_in_pair,
    # Q1
    "margin_logit": dist(m), "margin_ulps": dist(mu),
    "margin_counts": {"eq_0": int((mu == 0).sum()), "le_1ulp": int((mu <= 1).sum()),
                      "le_2ulp": int((mu <= 2).sum()), "le_4ulp": int((mu <= 4).sum())},
    "ulp_top1_values": {str(k): int(v) for k, v in zip(*np.unique(ulp, return_counts=True))},
    # Q2
    "abs_delta_pair_logit": dist(np.abs(d)), "abs_delta_pair_ulps": dist(np.abs(du)),
    "delta_pair_signed_counts": {"neg": int((d < 0).sum()), "zero": int((d == 0).sum()), "pos": int((d > 0).sum())},
    "mean_abs_delta": dist([r["mean_abs_delta"] for r in rows]),
    "frac_changed": dist([r["frac_changed"] for r in rows]),
    "tvd": dist([r["tvd"] for r in rows]),
    "summary_crosscheck": {"nonflip_median_abs_delta_pair": summary["nonflip_median_abs_delta_pair"],
                           "nonflip_p95_abs_delta_pair": summary["nonflip_p95_abs_delta_pair"],
                           "nonflip_median_frac_changed": summary["nonflip_median_frac_changed"],
                           "median_margin_off": summary["median_margin_off"], "max_tvd": summary["max_tvd"],
                           "n_identical_steps": summary["n_identical_steps"]},
    # Q3 deterministic
    "model_flips": model_flips, "model_reproduces_observed": reproduced,
    # Q7
    "steps_top1_differs": int((~same).sum()), "steps_top1_same": int(same.sum()),
    "steps_logits_identical": int(sum(r["frac_changed"] == 0 for r in rows)),
    "steps_frac_changed_ge_0p5": int(sum(r["frac_changed"] >= 0.5 for r in rows)),
    # Q8
    "scale": {"median_abs_delta_pair_over_median_margin_logit": float(np.median(np.abs(d)) / np.median(m)) if np.median(m) else None,
              "median_abs_delta_pair_over_median_margin_ulps": float(np.median(np.abs(du)) / np.median(mu)) if np.median(mu) else None},
  }
  # Q4 rank of the flip-step margins (rank 1 = smallest margin; ties share the lowest rank)
  ranks = []
  for s in obs_flips:
    i = int(np.where(steps == s)[0][0])
    ranks.append({"step": s, "margin_logit": float(m[i]), "margin_ulps": float(mu[i]), "ulp": float(ulp[i]),
                  "delta_pair": float(d[i]), "delta_pair_ulps": float(du[i]),
                  "off_top1": int(o1[i]), "off_top2": int(o2[i]), "on_top1": int(n1[i]),
                  "rank_logit_1_is_smallest": int((m < m[i]).sum() + 1), "n_steps_with_smaller_or_equal_margin_logit": int((m <= m[i]).sum()),
                  "rank_ulps_1_is_smallest": int((mu < mu[i]).sum() + 1), "n_steps_with_smaller_or_equal_margin_ulps": int((mu <= mu[i]).sum())})
  out["flip_steps_detail"] = ranks
  # near-tie steps (margin <= 2 ulps): what the pair movement did there
  out["near_tie_steps"] = [{"step": int(steps[i]), "margin_ulps": float(mu[i]), "delta_pair_ulps": float(du[i]),
                            "off_top1": int(o1[i]), "off_top2": int(o2[i]), "flip": bool(not same[i])}
                           for i in range(n) if mu[i] <= 2]
  # Q5 at-risk steps
  p95_abs_d = pct(np.abs(d), 95)
  p95_abs_du = pct(np.abs(du), 95)
  out["at_risk"] = {"p95_abs_delta_pair_logit": p95_abs_d, "steps_margin_le_p95_logit": int((m <= p95_abs_d).sum()),
                    "p95_abs_delta_pair_ulps": p95_abs_du, "steps_margin_le_p95_ulps": int((mu <= p95_abs_du).sum()),
                    "max_abs_delta_pair_logit": float(np.abs(d).max()), "steps_margin_le_max_logit": int((m <= np.abs(d).max()).sum())}
  return out, {"m": m, "mu": mu, "d": d, "du": du, "o1": o1, "o2": o2, "obs": len(obs_flips)}


def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
  a = ap.parse_args()

  res, raw = {}, {}
  for name, path, off_arm, on_arm, note in PAIRS:
    res[name], raw[name] = analyse(name, path, off_arm, on_arm, note)

  pred, pool_stats = predict_set(res, raw, {"pooled_p83": POOL_P83, "pooled_all": POOL_ALL})
  tot = totals(pred, raw, POOL_ALL, "pooled_all")

  # second set: 2026-10-16 campaign
  res2, raw2 = {}, {}
  for name, path, off_arm, on_arm, note in PAIRS2:
    res2[name], raw2[name] = analyse(name, path, off_arm, on_arm, note)
  nonident2 = [n for n in res2 if n not in CONTROLS2]
  pred2, pool_stats2 = predict_set(res2, raw2, {"pooled_td": nonident2})
  tot2 = totals(pred2, raw2, nonident2, "pooled_td")
  seven = [n for n in nonident2 if n != "new-vs-newoff"]
  tot2["without_repeat_new_vs_newoff"] = totals(pred2, raw2, seven, "pooled_td", pool_members=nonident2)
  key = {}
  for st in KEY_STEPS:
    key[str(st)] = {}
    for pre, n, src, rr in [("td/", n, raw2[n], res2[n]) for n in res2] + [("p83/", n, raw[n], res[n]) for n in POOL_P83]:
      i = st - 1
      key[str(st)][pre + n] = {
        "margin_ulps": float(src["mu"][i]), "margin_logit": float(src["m"][i]), "delta_pair_ulps": float(src["du"][i]),
        "off_top1": int(src["o1"][i]), "off_top2": int(src["o2"][i]), "flip": st in rr["observed_flips"]}
  td = {"pairs": res2, "prediction": pred2, "pools": pool_stats2, "totals": tot2, "key_steps": key,
        "controls": CONTROLS2, "nonidentical_pairs": nonident2}
  finish(res, pred, pool_stats, tot, td, a.out_dir)
  return 0


def predict_set(res, raw, pools):
  pool_d = {k: np.concatenate([raw[p]["d"] for p in v]) for k, v in pools.items()}
  pool_du = {k: np.concatenate([raw[p]["du"] for p in v]) for k, v in pools.items()}
  pred = {}
  for name in res:
    r = raw[name]
    entry = {"observed": r["obs"], "n_steps": int(r["m"].size)}
    sources = {"own": (r["d"], r["du"])}
    for k in pools:
      sources[k] = (pool_d[k], pool_du[k])
    for src, (dd, ddu) in sources.items():
      for unit, mm, pool in (("logit", r["m"], dd), ("ulps", r["mu"], ddu)):
        ps, pmf = predict(mm, r["o1"], r["o2"], pool)
        entry[f"{src}_{unit}"] = {"pool_size": int(pool.size), "expected_flips": float(ps.sum()),
                                  "p_at_least_one": 1.0 - float(pmf[0]),
                                  "p_ge_observed": tail(pmf, r["obs"]) if r["obs"] > 0 else 1.0,
                                  "p_le_observed": float(pmf[: r["obs"] + 1].sum()),
                                  "steps_with_nonzero_p": int((ps > 0).sum()),
                                  "top5_steps_by_p": [{"step": int(i + 1), "p": float(ps[i]), "margin": float(mm[i])}
                                                      for i in np.argsort(-ps, kind="stable")[:5]]}
    pred[name] = entry
  pool_stats = {k: {"members": v, "n": int(pool_d[k].size),
                    "abs_delta_pair_logit": dist(np.abs(pool_d[k])), "abs_delta_pair_ulps": dist(np.abs(pool_du[k])),
                    "signed_counts": {"neg": int((pool_d[k] < 0).sum()), "zero": int((pool_d[k] == 0).sum()), "pos": int((pool_d[k] > 0).sum())}}
                for k, v in pools.items()}
  return pred, pool_stats


def totals(pred, raw, members, pool, pool_members=None):
  """Sum of expected flips over a list of pairs, plus the exact distribution of the summed count (pool, ulps)."""
  pool_members = pool_members or members
  out = {"pairs": members,
         "observed_flips_total": int(sum(raw[p]["obs"] for p in members)),
         "steps_total": int(sum(raw[p]["m"].size for p in members))}
  for src in ("own", pool):
    for unit in ("logit", "ulps"):
      out[f"expected_flips_total_{src}_{unit}"] = float(sum(pred[p][f"{src}_{unit}"]["expected_flips"] for p in members))
  # exact tail for the summed count: recompute the Poisson-binomial over all steps of all members (pool, ulps)
  pmf = np.array([1.0])
  for p in members:
    r = raw[p]
    pool_du = np.concatenate([raw[q]["du"] for q in pool_members])
    ps, _ = predict(r["mu"], r["o1"], r["o2"], pool_du)
    for x in ps:
      pmf = np.convolve(pmf, [1 - x, x])
  k = out["observed_flips_total"]
  out[f"p_total_ge_observed_{pool}_ulps"] = tail(pmf, k)
  out[f"p_total_le_observed_{pool}_ulps"] = float(pmf[: k + 1].sum())
  return out


def finish(res, pred, pool_stats, tot, td, out_dir):
  out = {"pairs": res, "prediction": pred, "pools": pool_stats, "totals": tot, "td20261016": td,
         "conventions": {"percentile": "numpy.percentile linear interpolation",
                         "ulp": "bf16 ulp of the OFF top-1 logit = 2^(floor(log2|x|)-7) (dd_logits_step.bf16_ulp)",
                         "flip_model": "flip iff margin_off + delta_pair < 0, or == 0 and off_top2 < off_top1 (lowest id wins ties)",
                         "prediction": "P(flip_k) = P(d < -m_k) + [off_top2 < off_top1] P(d == -m_k), d drawn from the empirical delta_pair set; flip count = Poisson-binomial over steps"}}
  os.makedirs(out_dir, exist_ok=True)
  jp = os.path.join(out_dir, "tie_stats.json")
  json.dump(out, open(jp, "w"), indent=1)
  md = render(out) + render_td(out["td20261016"], out)
  mp = os.path.join(out_dir, "tie_stats.md")
  open(mp, "w").write(md)
  print(md)
  print(f"\n[written] {jp}\n[written] {mp}")


def f(x, nd=4):
  if x is None:
    return "-"
  if isinstance(x, float):
    s = f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"
  return str(x)


def render(o):
  P, pred, pools, tot = o["pairs"], o["prediction"], o["pools"], o["totals"]
  names = list(P.keys())
  L = []
  L.append("# Near-tie flip statistics (issue #4444), 2026-10-16\n")
  L.append("Section 1 (Q1 to Q8) covers the 2026-10-13 p83 pairs and the 2026-08-30 record. Section 2 (at the end) covers the ten pairs of the 2026-10-16 campaign.\n")
  nc = [n for n in names if n != CONTROL]
  med_du = [P[n]["abs_delta_pair_ulps"]["median"] for n in nc]
  med_mu = [P[n]["margin_ulps"]["median"] for n in nc]
  ranks_u = [r["rank_ulps_1_is_smallest"] for n in nc for r in P[n]["flip_steps_detail"]]
  exp_u = [pred[n]["own_ulps"]["expected_flips"] for n in nc]
  obs = [pred[n]["observed"] for n in nc]
  L.append(f"Short version. The arm change moves the top-1-minus-top-2 logit gap by a median of {f(min(med_du),1)} to {f(max(med_du),1)} bf16 notches per step, while the gap itself is a median of {f(min(med_mu),0)} to {f(max(med_mu),0)} notches, so a flip needs a step whose gap is already within a few notches of zero. Every observed flip sits at such a step: the six flip steps rank {', '.join(str(x) for x in ranks_u)} of 256 by gap in notches (1 = smallest). The flip model (gap plus a pair movement drawn independently from the measured movements) reproduces every observed flip by construction and, in its predictive form, expects {f(min(exp_u),2)} to {f(max(exp_u),2)} flips per 256 steps per pair against {min(obs)} to {max(obs)} observed, so the observed flip counts are what near-ties plus notch-level numerics produce.\n")
  L.append("Words used here.\n")
  L.append("- forced run: a run whose generated token ids are replaced by a fixed list (teacher forcing), so both arms see the same input at every step and their logits can be compared step by step.")
  L.append("- OFF arm / ON arm: the two logs of one pair, as passed to dd_logits_step.py as --off and --on. OFF is the first-named arm (new, fnew, r3x); its top pair defines the margin.")
  L.append("- margin (field margin_off): OFF-arm top-1 logit minus top-2 logit, in logit units; margin_off_ulps is the same in bf16 notches of the top-1 logit.")
  L.append("- ulp (one notch, field ulp_top1_off): the spacing of bf16 numbers at the top-1 logit, 0.0625 for logits in [8,16), 0.125 in [16,32), 0.25 in [32,64); all three occur (field ulp_top1_off, counts in tie_stats.json ulp_top1_values). Pair quantities in ulps use the top-1 notch, so they are half-integers when the top-2 logit lies in the next-lower binade.")
  L.append("- delta_pair (field delta_pair): (ON minus OFF) of the top-1 logit minus (ON minus OFF) of the top-2 logit, i.e. how far the arm change moves the margin; negative = toward a flip.")
  L.append("- flip (field same_top1 == false): the ON arm's top-1 id differs from the OFF arm's top-1 id at that step. Ties go to the lower id (np.argmax, std::max_element).")
  L.append("- TVD (field tvd): total variation distance between the two arms' softmax distributions at the step, 0 = identical, 1 = disjoint.")
  L.append("- frac_changed: fraction of vocabulary logits that differ between the arms at the step; mean_abs_delta: mean |ON - OFF| over the vocabulary.")
  L.append("- pooled_p83: delta_pair values of the five non-control prompt-1024 pairs together (new-vs-newforced excluded, all zero); pooled_all adds the 2026-08-30 prompt-2048 pair.\n")
  L.append("Pairs (file, arms):\n")
  for n in names:
    p = P[n]
    L.append(f"- {n}: {p['off_arm']} vs {p['on_arm']}, {p['note']}, {p['n_steps']} steps, observed flips {p['observed_flips']} [{p['file']}]")
  L.append("")
  L.append("## Q1. OFF-arm margin per step (margin_off, margin_off_ulps)\n")
  L.append("| pair | median (logit) | p10 | p05 | min | median (ulps) | p10 | p05 | min | =0 | <=1 ulp | <=2 | <=4 |")
  L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
  for n in names:
    p = P[n]; a = p["margin_logit"]; b = p["margin_ulps"]; c = p["margin_counts"]
    L.append(f"| {n} | {f(a['median'])} | {f(a['p10'])} | {f(a['p05'])} | {f(a['min'])} | {f(b['median'],1)} | {f(b['p10'],1)} | {f(b['p05'],1)} | {f(b['min'],1)} | {c['eq_0']} | {c['le_1ulp']} | {c['le_2ulp']} | {c['le_4ulp']} |")
  L.append("\nThe five prompt-1024 pairs share the OFF arm (new or fnew), so their margin rows repeat by construction. Counts are steps out of n_steps.\n")
  L.append("## Q2. Pair movement (delta_pair) and vocabulary-wide change per step\n")
  L.append("| pair | median abs delta_pair (logit) | p95 | max | median (ulps) | p95 | max | neg/zero/pos | mean_abs_delta median / p95 / max | frac_changed median / p95 / max | tvd median / p95 / max |")
  L.append("|---|---|---|---|---|---|---|---|---|---|---|")
  for n in names:
    p = P[n]; a = p["abs_delta_pair_logit"]; b = p["abs_delta_pair_ulps"]; s = p["delta_pair_signed_counts"]
    md_ = p["mean_abs_delta"]; fc = p["frac_changed"]; tv = p["tvd"]
    L.append(f"| {n} | {f(a['median'])} | {f(a['p95'])} | {f(a['max'])} | {f(b['median'],2)} | {f(b['p95'],2)} | {f(b['max'],2)} | {s['neg']}/{s['zero']}/{s['pos']} | {f(md_['median'])} / {f(md_['p95'])} / {f(md_['max'])} | {f(fc['median'],3)} / {f(fc['p95'],3)} / {f(fc['max'],3)} | {f(tv['median'])} / {f(tv['p95'])} / {f(tv['max'])} |")
  L.append("\nStatistics are over all steps of the pair (flip steps included). The summary block of each json excludes the flip steps from the delta_pair and frac_changed statistics; the cross-check below shows both.\n")
  L.append("| pair | p95 abs delta_pair: all steps / summary nonflip_p95_abs_delta_pair | median frac_changed: all / summary nonflip_median_frac_changed | max tvd: all / summary max_tvd | identical steps: all / summary n_identical_steps |")
  L.append("|---|---|---|---|---|")
  for n in names:
    p = P[n]; s = p["summary_crosscheck"]
    L.append(f"| {n} | {f(p['abs_delta_pair_logit']['p95'])} / {f(s['nonflip_p95_abs_delta_pair'])} | {f(p['frac_changed']['median'],4)} / {f(s['nonflip_median_frac_changed'],4)} | {f(p['tvd']['max'],5)} / {f(s['max_tvd'],5)} | {p['steps_logits_identical']} / {s['n_identical_steps']} |")
  L.append("")
  L.append("Pooled delta_pair sets:\n")
  L.append("| pool | n | median abs (logit) | p95 | max | median abs (ulps) | p95 | max | neg/zero/pos |")
  L.append("|---|---|---|---|---|---|---|---|---|")
  for k, v in pools.items():
    a = v["abs_delta_pair_logit"]; b = v["abs_delta_pair_ulps"]; s = v["signed_counts"]
    L.append(f"| {k} | {v['n']} | {f(a['median'])} | {f(a['p95'])} | {f(a['max'])} | {f(b['median'],2)} | {f(b['p95'],2)} | {f(b['max'],2)} | {s['neg']}/{s['zero']}/{s['pos']} |")
  L.append("")
  L.append("## Q3. Flip model\n")
  L.append("Deterministic form: flip at step k iff m_k + d_k < 0, or m_k + d_k == 0 and the OFF top-2 id is lower than the OFF top-1 id (lowest id wins an exact tie). Check of the rule at the known flips: step 84 of new-vs-base has m + d = 0 with off_top1 1499 > off_top2 258, so the lower id 258 wins in the ON arm (on_top1 = 258); step 248 of new-vs-newoff has m + d = -0.125 < 0. The model is evaluated on every step and compared with same_top1; it also checks that the ON top-1 is always one of the OFF top pair (no third token overtakes).\n")
  L.append("| pair | observed flips | model flips | model == observed | ON top-1 always in OFF top pair |")
  L.append("|---|---|---|---|---|")
  for n in names:
    p = P[n]
    L.append(f"| {n} | {p['observed_flips']} | {p['model_flips']} | {p['model_reproduces_observed']} | {p['on_top1_always_in_off_top_pair']} |")
  L.append("\nPredictive form: d is drawn independently of m_k from an empirical delta_pair set (the pair's own 256 values, pooled_p83, or pooled_all), in logit units or in ulps (d/ulp vs m/ulp). Expected flips = sum over steps of P(flip_k); P(at least one) and P(count >= observed) come from the exact Poisson-binomial distribution of the flip count over the steps (independence across steps assumed).\n")
  L.append("| pair | observed | own (logit): expected / P(>=1) / P(>=obs) | own (ulps) | pooled_p83 (logit) | pooled_p83 (ulps) | pooled_all (logit) | pooled_all (ulps) |")
  L.append("|---|---|---|---|---|---|---|---|")
  for n in names:
    e = pred[n]
    def cell(k):
      c = e[k]; return f"{f(c['expected_flips'],2)} / {f(c['p_at_least_one'],2)} / {f(c['p_ge_observed'],2)}"
    L.append(f"| {n} | {e['observed']} | {cell('own_logit')} | {cell('own_ulps')} | {cell('pooled_p83_logit')} | {cell('pooled_p83_ulps')} | {cell('pooled_all_logit')} | {cell('pooled_all_ulps')} |")
  L.append(f"\nTotals over the six non-control pairs ({tot['steps_total']} steps): observed {tot['observed_flips_total']} flips; expected {f(tot['expected_flips_total_own_logit'],2)} (own, logit), {f(tot['expected_flips_total_own_ulps'],2)} (own, ulps), {f(tot['expected_flips_total_pooled_all_logit'],2)} (pooled_all, logit), {f(tot['expected_flips_total_pooled_all_ulps'],2)} (pooled_all, ulps). For the control pair the own set is all zeros, so its expected count is 0 by construction; its pooled rows show what the model predicts for the same margins under a real arm change. The ulp form is the physically right one: the pair movement is quantized at the notch of the step's own logit (0.0625 to 0.25), and the logit-unit form applies the large movements of 0.25-notch steps to the small-margin steps, which have the 0.0625 notch, so it over-predicts by about 2x (14.8 vs 6.9 expected for 6 observed).\n")
  L.append("Steps that carry the predicted flip probability (pooled_all, ulps), top 3 per pair:\n")
  for n in names:
    t = pred[n]["pooled_all_ulps"]["top5_steps_by_p"][:3]
    L.append(f"- {n}: " + ", ".join(f"step {x['step']} (margin {f(x['margin'],1)} ulps, p {f(x['p'],3)})" for x in t) + f"; steps with p > 0: {pred[n]['pooled_all_ulps']['steps_with_nonzero_p']}")
  L.append("")
  L.append("## Q4. Are the flip-step margins special?\n")
  L.append("| pair | step | margin (logit) | margin (ulps) | delta_pair (logit / ulps) | rank by margin, 1 = smallest (logit) | steps with margin <= this | rank (ulps) | steps with margin <= this (ulps) |")
  L.append("|---|---|---|---|---|---|---|---|---|")
  for n in names:
    for r in P[n]["flip_steps_detail"]:
      L.append(f"| {n} | {r['step']} | {f(r['margin_logit'])} | {f(r['margin_ulps'],1)} | {f(r['delta_pair'])} / {f(r['delta_pair_ulps'],1)} | {r['rank_logit_1_is_smallest']} | {r['n_steps_with_smaller_or_equal_margin_logit']} | {r['rank_ulps_1_is_smallest']} | {r['n_steps_with_smaller_or_equal_margin_ulps']} |")
  worst = max(r["rank_ulps_1_is_smallest"] for n in names for r in P[n]["flip_steps_detail"])
  L.append(f"\nEvery flip happened at a step whose OFF margin is among the {worst} smallest of its 256 margins in notches. The three exact ties (0 ulps) all flipped when the pair moved by -1 ulp. Step 145 of 2026-08-30 is the one flip that needed a movement beyond the p95: margin 3 ulps, movement -6 ulps (the p95 of that pair is 4 ulps). The other flips needed movements of 1 to 2 ulps, inside the median-to-p95 range of the pair movement.\n")
  L.append("Near-tie steps (OFF margin <= 2 ulps) and what the pair movement did there (delta_pair in ulps; flip marked with *):\n")
  for n in names:
    if n == CONTROL:
      continue
    L.append(f"- {n}: " + ", ".join(f"step {r['step']} m={f(r['margin_ulps'],1)} d={f(r['delta_pair_ulps'],1)}{'*' if r['flip'] else ''}" for r in P[n]["near_tie_steps"]))
  saved = [(n, r["step"], r["off_top1"], r["off_top2"]) for n in names if n != CONTROL for r in P[n]["near_tie_steps"]
           if r["margin_ulps"] + r["delta_pair_ulps"] == 0 and not r["flip"]]
  L.append("\nA near-tie step survives when the movement is 0 or positive, or when the post-movement exact tie keeps the lower id. Steps that reached an exact tie in the ON arm and survived because the OFF top-1 had the lower id: " + ", ".join(f"{n} step {st} (ids {a} vs {b})" for n, st, a, b in saved) + ". Step 248 of the FPGA arm fnew is an exact tie (ids 13 vs 624, 13 wins) and stayed one in fnew-vs-fhead (movement 0) and widened in fnew-vs-fbase (movement +1 ulp), so it did not flip there.\n")
  L.append("## Q5. Steps at risk per run\n")
  L.append("At risk = OFF margin <= the p95 of |delta_pair| of the same pair (a movement that the arm change produces in 1 of 20 steps would close the gap).\n")
  L.append("| pair | p95 abs delta_pair (logit) | at-risk steps (logit) | p95 (ulps) | at-risk steps (ulps) | max abs delta_pair (logit) | steps with margin <= max |")
  L.append("|---|---|---|---|---|---|---|")
  for n in names:
    r = P[n]["at_risk"]
    L.append(f"| {n} | {f(r['p95_abs_delta_pair_logit'])} | {r['steps_margin_le_p95_logit']} | {f(r['p95_abs_delta_pair_ulps'],2)} | {r['steps_margin_le_p95_ulps']} | {f(r['max_abs_delta_pair_logit'])} | {r['steps_margin_le_max_logit']} |")
  L.append("")
  L.append("## Q6. The 2026-08-30 record (prompt 2048, AMX on vs off, runtron.canon)\n")
  p = P["r3x-vs-r4x-20260830"]
  L.append(f"File {p['file']} (OFF = r3x forced with r1a.tok, ON = r4x, 256 steps). Flips {p['observed_flips']}; margins at the flips: " + ", ".join(f"step {r['step']} = {f(r['margin_ulps'],0)} ulps ({f(r['margin_logit'])} logit), pair moved {f(r['delta_pair_ulps'],0)} ulps" for r in p["flip_steps_detail"]) + f". Margin median {f(p['margin_logit']['median'])} logit ({f(p['margin_ulps']['median'],1)} ulps); exact ties {p['margin_counts']['eq_0']}, <= 1 ulp {p['margin_counts']['le_1ulp']}, <= 4 ulps {p['margin_counts']['le_4ulp']}. Pair movement median {f(p['abs_delta_pair_ulps']['median'],1)} ulp, p95 {f(p['abs_delta_pair_ulps']['p95'],1)} ulps (handoff: 1 and 4). Model reproduces the flips: {p['model_reproduces_observed']}; expected flips own/ulps {f(pred['r3x-vs-r4x-20260830']['own_ulps']['expected_flips'],2)}, pooled_all/ulps {f(pred['r3x-vs-r4x-20260830']['pooled_all_ulps']['expected_flips'],2)}, observed 3. Same pattern as the prompt-1024 pairs: flips sit at the 0-, 0- and 3-ulp margins (ranks 1, 1, 3 of 256), and the arm change moves every other step's logits too (frac_changed median {f(p['frac_changed']['median'],3)}).\n")
  L.append("## Q7. Cross-checks\n")
  L.append("| pair | steps where top-1 differs | steps where top-1 same | steps with all logits identical (frac_changed = 0) | steps with frac_changed >= 0.5 | frac_changed median / min |")
  L.append("|---|---|---|---|---|---|")
  for n in names:
    p = P[n]
    L.append(f"| {n} | {p['steps_top1_differs']} | {p['steps_top1_same']} | {p['steps_logits_identical']} | {p['steps_frac_changed_ge_0p5']} | {f(p['frac_changed']['median'],3)} / {f(p['frac_changed']['min'],3)} |")
  L.append("\nThe top token differs only at the listed flip steps; at every other step the two arms pick the same id (steps_top1_same = 256 minus flips). The logits are not bit-identical: the median step has about 80 % of the vocabulary changed by at least one notch in the prompt-1024 pairs. new-vs-head and fnew-vs-fhead each have exactly one step with all logits identical (field n_identical_steps = 1), so 'never identical' holds at 255 of 256 steps for those two pairs and at 256 of 256 for the others. The control pair new-vs-newforced is identical at all 256 steps.\n")
  L.append("## Q8. Scale\n")
  L.append("| pair | median abs delta_pair / median margin (logit) | same ratio in ulps |")
  L.append("|---|---|---|")
  for n in names:
    s = P[n]["scale"]
    L.append(f"| {n} | {f(s['median_abs_delta_pair_over_median_margin_logit'])} | {f(s['median_abs_delta_pair_over_median_margin_ulps'])} |")
  p = P["new-vs-base"]
  L.append(f"\nFor new-vs-base: median |delta_pair| {f(p['abs_delta_pair_logit']['median'])} logit vs median margin {f(p['margin_logit']['median'])} logit, ratio {f(p['scale']['median_abs_delta_pair_over_median_margin_logit'])}; in notches {f(p['abs_delta_pair_ulps']['median'],1)} vs {f(p['margin_ulps']['median'],1)} ulps. The typical pair movement is about 1/60 of the typical gap, so only the few steps whose gap is itself a few notches can flip.\n")
  L.append("## Reproduce\n")
  L.append("```\npython3 /home/jhan/workspace/intel-AMX/exec/td-20261016/tiestats/tie_stats.py\n```\nOutputs tie_stats.json (every number above plus per-step prediction details) and tie_stats.md next to the script. Inputs are read only.")
  return "\n".join(L) + "\n"


def render_td(td, o):
  P, pred, pools, tot, key = td["pairs"], td["prediction"], td["pools"], td["totals"], td["key_steps"]
  names = list(P.keys()); nc = td["nonidentical_pairs"]
  L = ["", "# Section 2. The 2026-10-16 campaign (10 new pairs, same cell: qwen3-4b tp2, prompt 1024, 256 forced steps)", ""]
  exp = [pred[n]["own_ulps"]["expected_flips"] for n in nc]
  L.append(f"Short version. Ten new pairwise comparisons from /home/jhan/workspace/intel-AMX/exec/results/td-20261016/steps-<off>-vs-<on>.json, all arms fed the same 256 token ids. Two pairs are bit-identical controls ({', '.join(td['controls'])}); the other eight show {tot['observed_flips_total']} flips in {tot['steps_total']} steps, all at steps 20, 84 or 248, where the OFF margin is 0 to 2 notches. The flip model reproduces every flip; its predictive form expects {f(tot['expected_flips_total_own_ulps'],2)} flips over the eight pairs (own movements, ulps) or {f(tot['expected_flips_total_pooled_td_ulps'],2)} (pooled), against {tot['observed_flips_total']} observed; P(count <= {tot['observed_flips_total']}) = {f(tot['p_total_le_observed_pooled_td_ulps'],2)} under the pooled model, so the observed count is on the low side of the model and inside it.")
  L.append("")
  L.append("Arms: " + "; ".join(ARMS2[k] for k in ARMS2) + ". The OFF arm of a pair is the first-named one. new-vs-newoff is a re-run of the section 1 pair with tonight's logs.")
  L.append("")
  L.append("## S2.1 Pairs, margins (margin_off / margin_off_ulps of the OFF arm) and flips\n")
  L.append("| pair | observed flips | model == observed | median margin (logit) | p05 | min | median (ulps) | p05 | min | =0 | <=1 ulp | <=2 | <=4 |")
  L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
  for n in names:
    p = P[n]; a = p["margin_logit"]; b = p["margin_ulps"]; c = p["margin_counts"]
    L.append(f"| {n} | {p['observed_flips']} | {p['model_reproduces_observed']} | {f(a['median'])} | {f(a['p05'])} | {f(a['min'])} | {f(b['median'],1)} | {f(b['p05'],1)} | {f(b['min'],1)} | {c['eq_0']} | {c['le_1ulp']} | {c['le_2ulp']} | {c['le_4ulp']} |")
  L.append("\nThe ON top-1 is one of the OFF top pair at every step of every pair (field on_top1_always_in_off_top_pair = true in tie_stats.json).\n")
  L.append("## S2.2 Pair movement (delta_pair) and vocabulary-wide change\n")
  L.append("| pair | median abs delta_pair (logit) | p95 | max | median (ulps) | p95 | max | neg/zero/pos | identical steps | frac_changed median | tvd median / max |")
  L.append("|---|---|---|---|---|---|---|---|---|---|---|")
  for n in names:
    p = P[n]; a = p["abs_delta_pair_logit"]; b = p["abs_delta_pair_ulps"]; s = p["delta_pair_signed_counts"]
    L.append(f"| {n} | {f(a['median'])} | {f(a['p95'])} | {f(a['max'])} | {f(b['median'],2)} | {f(b['p95'],2)} | {f(b['max'],2)} | {s['neg']}/{s['zero']}/{s['pos']} | {p['steps_logits_identical']} | {f(p['frac_changed']['median'],3)} | {f(p['tvd']['median'])} / {f(p['tvd']['max'])} |")
  v = pools["pooled_td"]; a = v["abs_delta_pair_logit"]; b = v["abs_delta_pair_ulps"]
  L.append(f"\nPooled movement set pooled_td (the eight non-identical pairs, n = {v['n']}): median |delta_pair| {f(a['median'])} logit / {f(b['median'],2)} ulps, p95 {f(a['p95'])} / {f(b['p95'],2)}, max {f(a['max'])} / {f(b['max'],2)}; signed neg/zero/pos {v['signed_counts']['neg']}/{v['signed_counts']['zero']}/{v['signed_counts']['pos']}. base-vs-poc has 64 identical steps (the first 64, frac_changed = 0), so its own movement set is 25 % zeros.\n")
  L.append("## S2.3 Flip model: expected vs observed\n")
  L.append("| pair | observed | own (ulps): expected / P(>=1) / P(>=obs) | own (logit) | pooled_td (ulps) | pooled_td (logit) | at-risk steps (margin <= p95 abs delta_pair, ulps) |")
  L.append("|---|---|---|---|---|---|---|")
  for n in names:
    e = pred[n]
    def cell(k):
      c = e[k]; return f"{f(c['expected_flips'],2)} / {f(c['p_at_least_one'],2)} / {f(c['p_ge_observed'],2)}"
    L.append(f"| {n} | {e['observed']} | {cell('own_ulps')} | {cell('own_logit')} | {cell('pooled_td_ulps')} | {cell('pooled_td_logit')} | {P[n]['at_risk']['steps_margin_le_p95_ulps']} |")
  w = tot["without_repeat_new_vs_newoff"]
  L.append(f"\nSum over the eight non-identical pairs ({tot['steps_total']} steps): observed {tot['observed_flips_total']}; expected {f(tot['expected_flips_total_own_ulps'],2)} (own, ulps), {f(tot['expected_flips_total_pooled_td_ulps'],2)} (pooled_td, ulps), {f(tot['expected_flips_total_own_logit'],2)} (own, logit), {f(tot['expected_flips_total_pooled_td_logit'],2)} (pooled_td, logit). Exact distribution of the summed count under pooled_td/ulps: P(>= {tot['observed_flips_total']}) = {f(tot['p_total_ge_observed_pooled_td_ulps'],3)}, P(<= {tot['observed_flips_total']}) = {f(tot['p_total_le_observed_pooled_td_ulps'],3)}. Without the repeated new-vs-newoff (seven pairs, {w['steps_total']} steps): observed {w['observed_flips_total']}, expected {f(w['expected_flips_total_own_ulps'],2)} (own, ulps) / {f(w['expected_flips_total_pooled_td_ulps'],2)} (pooled_td, ulps), P(>= {w['observed_flips_total']}) = {f(w['p_total_ge_observed_pooled_td_ulps'],3)}. The observed count is below the expectation and inside the model's range (P(<= observed) about 0.2); the ulp form of the model is the right one (section 1, Q3), and the logit form over-predicts by about 2x for the same reason as before.\n")
  L.append("## S2.4 Steps 20, 84 and 248 across every pair of the cell\n")
  L.append("Margin of the OFF arm in ulps (m) and movement in ulps (d) at the three steps where flips occur; flip marked with *. The p83 pairs of section 1 (same cell, 2026-10-13 logs) are listed below the new ones for comparison.\n")
  L.append("| pair | step 20: m / d / OFF ids | step 84: m / d / OFF ids | step 248: m / d / OFF ids |")
  L.append("|---|---|---|---|")
  order = [("td/" + n) for n in names] + [k for k in key["20"] if k.startswith("p83/")]
  for k in order:
    cells = []
    for st in KEY_STEPS:
      r = key[str(st)][k]
      cells.append(f"{f(r['margin_ulps'],1)} / {f(r['delta_pair_ulps'],1)}{'*' if r['flip'] else ''} / {r['off_top1']} vs {r['off_top2']}")
    L.append(f"| {k} | " + " | ".join(cells) + " |")
  L.append("")
  ids = {st: sorted({tuple(sorted((r["off_top1"], r["off_top2"]))) for r in key[str(st)].values()}) for st in KEY_STEPS}
  flip_moves = sorted({r["delta_pair_ulps"] for st in KEY_STEPS for r in key[str(st)].values() if r["flip"]})
  flip_margins = sorted({r["margin_ulps"] for st in KEY_STEPS for r in key[str(st)].values() if r["flip"]})
  L.append("Reading the table. Each of the three steps is a near-tie between the same two ids in every arm of the cell: " + "; ".join(f"step {st}: ids {ids[st][0][0]} and {ids[st][0][1]}" for st in KEY_STEPS) + f" (one id pair per step, {sum(len(v) for v in ids.values())} pairs in all). The OFF margins at the flips are {', '.join(f(x,0) for x in flip_margins)} notches and the movements at the flips are {', '.join(f(x,0) for x in flip_moves)} notches, the median-to-p95 range of the pair movement; no flip required a movement outside that range. Which arm is called OFF decides the sign: an arm that holds the pair at margin 0 with the lower id first survives a 0 movement and flips on -1 notch (step 20 in baseoff, clean; step 248 in baseoff), and an arm that holds it at 1 or 2 notches flips only when the movement is at least that large (step 84 in new, baseoff; step 248 in new, newoff).\n")
  return "\n".join(L) + "\n"


if __name__ == "__main__":
  sys.exit(main())
