#!/usr/bin/env python3
"""Per-step logit comparison of two teacher-forced runtron runs.

  dd_logits_step.py --off off.txt --on on.txt --forced forced.tok [--prompt-len N] --out steps.json

off.txt / on.txt : --intermediates-file logs of the two arms, same prompt, ON arm
                   force-fed with the OFF arm's generated ids (forced.tok).
Step k (1-based) is predicted by the forward pass whose last input token sits at
position P-2+k where P is the prompt length, so its logits are the line
"Logits of token <P-2+k>" (N = token-tree index = absolute position for one prompt
in a fresh process). With --prompt-len omitted, P is derived from the log:
P-1 = smallest N among the 'Logits of token N' lines (runtron logs logits only
for the last prompt token and each decode step).

Per step: top-1 of each arm (argmax, ties -> lowest id, as std::max_element), the
OFF arm's margin (top-1 minus top-2) in logit units and in bf16 ulps of the
top-1 logit, the ON-arm change of that pair, the forced id and its rank in both
arms, graded vocabulary-wide statistics (mean |delta|, max |delta|, fraction of
changed entries, TVD), and the sparse 'Top-k Token IDs for Logits'[0] cross-check.
Logits on tp executors are bf16 and print exactly at 8 digits, so |delta| values
are multiples of the bf16 ulp; the graded statistics are the ones to compare
across builds (rounding mode vs add order), not the single-pair delta.
"""
import argparse
import json
import math
import sys

import numpy as np

from dd_intermediates import parse_message, split_line, values


def bf16_ulp(x):
  x = abs(float(x))
  if x == 0 or x != x:
    return float("nan")
  return 2.0 ** (math.floor(math.log2(x)) - 7)


def collect(path):
  """{N: {'logits': arr, 'topk_ids': arr|None, 'topk_logits': arr|None}} for every Logits line."""
  out = {}
  with open(path, "r", errors="replace") as f:
    for line in f:
      s = split_line(line)
      if s is None:
        continue
      _, msg, vs = s
      label, layer, tok = parse_message(msg)
      if tok is None or layer is not None:
        continue
      if label not in ("Logits", "Top-k Logits", "Top-k Token IDs for Logits"):
        continue
      d = out.setdefault(tok, {})
      if label == "Logits":
        d["logits"] = values(vs)
      elif label == "Top-k Logits":
        d["topk_logits"] = values(vs)
      else:
        d["topk_ids"] = values(vs).astype(np.int64)
  return out


def softmax(x):
  x = x.astype(np.float64)
  e = np.exp(x - x.max())
  return e / e.sum()


def top2(x):
  i1 = int(np.argmax(x))  # first maximal index = lowest id on ties
  y = x.copy()
  y[i1] = -np.inf
  i2 = int(np.argmax(y))
  return i1, i2


def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--off", required=True)
  ap.add_argument("--on", required=True)
  ap.add_argument("--forced", required=True, help="OFF arm's --output-token-file row (ids replayed into ON)")
  ap.add_argument("--prompt-len", type=int, default=None, help="prompt length P; default: derived from the OFF log")
  ap.add_argument("--out", required=True)
  ap.add_argument("--mark", type=int, default=30, help="step to highlight (default 30)")
  a = ap.parse_args()

  forced = [int(x) for x in open(a.forced).read().split()]
  off = collect(a.off)
  on = collect(a.on)
  logit_ns = sorted(n for n, d in off.items() if "logits" in d)
  if not logit_ns:
    print("no 'Logits of token N' lines in the OFF log", file=sys.stderr)
    return 2
  P = a.prompt_len if a.prompt_len else logit_ns[0] + 1
  steps = list(range(1, len(forced) + 1))

  rows = []
  for k in steps:
    N = P - 2 + k
    if N not in off or N not in on or "logits" not in off[N] or "logits" not in on[N]:
      rows.append({"step": k, "N": N, "missing": True})
      continue
    lo, ln = off[N]["logits"], on[N]["logits"]
    if lo.shape != ln.shape:
      rows.append({"step": k, "N": N, "shape_mismatch": [int(lo.size), int(ln.size)]})
      continue
    o1, o2 = top2(lo)
    n1, n2 = top2(ln)
    d = ln - lo
    f = forced[k - 1]
    ulp = bf16_ulp(lo[o1])
    row = {
      "step": k, "N": N, "forced_id": f,
      "off_top1": o1, "off_top2": o2, "on_top1": n1, "on_top2": n2,
      "same_top1": o1 == n1,
      "margin_off": float(lo[o1] - lo[o2]),
      "ulp_top1_off": ulp,
      "margin_off_ulps": float((lo[o1] - lo[o2]) / ulp) if ulp == ulp else None,
      "margin_on_same_pair": float(ln[o1] - ln[o2]),
      "delta_top1": float(d[o1]), "delta_top2": float(d[o2]),
      "delta_pair": float(d[o1] - d[o2]),
      "forced_rank_off": int((lo > lo[f]).sum()) + 1, "forced_rank_on": int((ln > ln[f]).sum()) + 1,
      "max_abs_delta": float(np.abs(d).max()), "mean_abs_delta": float(np.abs(d).mean()),
      "frac_changed": float((d != 0).mean()),
      "argmax_abs_delta": int(np.abs(d).argmax()),
      "tvd": float(0.5 * np.abs(softmax(lo) - softmax(ln)).sum()),
      "off_top1_logit": float(lo[o1]), "on_top1_logit": float(ln[n1]),
    }
    for arm, src in (("off", off[N]), ("on", on[N])):
      if "topk_ids" in src and src["topk_ids"].size:
        row[f"{arm}_sparse_top1"] = int(src["topk_ids"][0])
    rows.append(row)

  ok = [r for r in rows if "margin_off" in r]
  flips = [r["step"] for r in ok if not r["same_top1"]]
  nonflip = [r for r in ok if r["same_top1"]]

  def med(key, rs):
    return float(np.median([r[key] for r in rs])) if rs else None

  def p95(key, rs):
    return float(np.percentile([abs(r[key]) for r in rs], 95)) if rs else None

  summary = {
    "prompt_len": P, "prompt_len_source": "argument" if a.prompt_len else "derived from first Logits line",
    "n_steps": len(steps), "n_with_logits": len(ok), "flip_steps": flips, "first_flip": flips[0] if flips else None,
    "nonflip_median_abs_delta_pair": med("delta_pair", [dict(r, delta_pair=abs(r["delta_pair"])) for r in nonflip]),
    "nonflip_p95_abs_delta_pair": p95("delta_pair", nonflip),
    "nonflip_median_mean_abs_delta": med("mean_abs_delta", nonflip),
    "nonflip_p95_mean_abs_delta": p95("mean_abs_delta", nonflip),
    "nonflip_median_frac_changed": med("frac_changed", nonflip),
    "median_margin_off": med("margin_off", ok),
    "max_tvd": float(max(r["tvd"] for r in ok)) if ok else None,
    "max_max_abs_delta": float(max(r["max_abs_delta"] for r in ok)) if ok else None,
    "n_identical_steps": sum(1 for r in ok if r["max_abs_delta"] == 0),
  }
  mark = next((r for r in ok if r["step"] == a.mark), None)
  if mark:
    summary["marked_step"] = mark
  res = {"summary": summary, "steps": rows, "args": vars(a)}
  with open(a.out, "w") as f:
    json.dump(res, f, indent=1)
  print(json.dumps({k: v for k, v in summary.items() if k != "marked_step"}, indent=1))
  print(f"{'step':>4} {'same':>5} {'margin_off':>11} {'m/ulp':>6} {'delta_pair':>11} {'mean|d|':>9} {'frac':>6} {'tvd':>8}  off_top1 on_top1 forced")
  for r in ok:
    mu = r["margin_off_ulps"]
    print(f"{r['step']:>4} {str(r['same_top1']):>5} {r['margin_off']:>11.5f} {(mu if mu is not None else float('nan')):>6.1f} {r['delta_pair']:>11.5f} "
          f"{r['mean_abs_delta']:>9.6f} {r['frac_changed']:>6.3f} {r['tvd']:>8.5f}  {r['off_top1']:>7} {r['on_top1']:>7} {r['forced_id']:>6}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
