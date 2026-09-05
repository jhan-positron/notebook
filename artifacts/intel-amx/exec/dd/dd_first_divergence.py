#!/usr/bin/env python3
"""Locate the first (token, layer, stage) where two intermediates logs differ.

  dd_first_divergence.py --off off.txt --on on.txt --out layers.json [--threshold 0]
                         [--heatmap-labels WO,WFF2] [--csv per_key.csv]

Streams both files (they can be tens of GB): builds a byte-offset index of the
OFF file keyed on the 50-char key (as bin/compare_intermediates does), then walks
the ON file once, seeking into OFF for each key. Per key: relative L2 error
||on-off|| / ||off||, max |on-off|, fraction of changed elements, and the largest
element change measured in bf16 ulps of the OFF value (1 ulp = one bf16 step of
that element). Keys are sorted by (token, layer, stage order) and the first key
whose relative error exceeds the threshold is reported, together with per-label
heatmaps (token x layer), per-label summaries, per-token first layer over the
threshold, and the keys present in only one file (both directions).

Threshold: default 0 = any difference (the A/A control must give none).
"""
import argparse
import csv
import json
import sys

import numpy as np

from dd_intermediates import index_offsets, parse_message, read_line_at, split_line, stage_rank, values


def max_ulps(off, d):
  """largest |d| / bf16_ulp(|off|) over elements; elements with off == 0 use the ulp of the smallest nonzero |off|."""
  a = np.abs(off)
  nz = a[a > 0]
  if nz.size == 0:
    return float("inf") if np.any(d) else 0.0
  a = np.where(a > 0, a, nz.min())
  ulp = np.exp2(np.floor(np.log2(a)) - 7)
  return float(np.max(np.abs(d) / ulp))


def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--off", required=True, help="reference log (AMX off)")
  ap.add_argument("--on", required=True, help="test log (AMX on, force-fed)")
  ap.add_argument("--out", required=True)
  ap.add_argument("--threshold", type=float, default=0.0)
  ap.add_argument("--heatmap-labels", default="Attn out,WO,WFF2,Logits")
  ap.add_argument("--csv", default=None, help="write per-key rows")
  a = ap.parse_args()

  off_idx, off_dups = index_offsets(a.off)
  print(f"OFF index: {len(off_idx)} keys, {off_dups} duplicate keys", file=sys.stderr)
  seen_on = set()
  rows = []
  missing_in_off = []
  labels_hm = [s.strip() for s in a.heatmap_labels.split(",") if s.strip()]
  hm = {lab: {} for lab in labels_hm}
  n = 0
  with open(a.off, "rb") as foff, open(a.on, "r", errors="replace") as fon:
    for line in fon:
      s = split_line(line)
      if s is None:
        continue
      key, msg, vs_on = s
      if key in seen_on:
        continue
      seen_on.add(key)
      label, layer, tok = parse_message(msg)
      if key not in off_idx:
        missing_in_off.append(msg)
        continue
      s2 = split_line(read_line_at(foff, off_idx[key]))
      if s2 is None:
        continue
      von = values(vs_on)
      voff = values(s2[2])
      if von.shape != voff.shape:
        rows.append({"key": msg, "label": label, "layer": layer, "token": tok, "len": int(von.size),
                     "rel_l2": float("nan"), "max_abs": float("nan"), "frac_changed": float("nan"), "max_ulps": float("nan"),
                     "shape_mismatch": [int(voff.size), int(von.size)]})
        continue
      d = von - voff
      nrm = float(np.linalg.norm(voff))
      rel = float(np.linalg.norm(d) / nrm) if nrm > 0 else (0.0 if not np.any(d) else float("inf"))
      rows.append({"key": msg, "label": label, "layer": layer, "token": tok, "len": int(von.size), "rel_l2": rel,
                   "max_abs": float(np.abs(d).max()) if d.size else 0.0,
                   "frac_changed": float((d != 0).mean()) if d.size else 0.0,
                   "max_ulps": max_ulps(voff, d) if d.size else 0.0})
      if label in hm and tok is not None:
        hm[label][(tok, layer if layer is not None else -1)] = rel
      n += 1
      if n % 50000 == 0:
        print(f"  {n} keys compared", file=sys.stderr)
  missing_in_on = [k.strip() for k in off_idx if k not in seen_on]

  def sort_key(r):
    return (r["token"] if r["token"] is not None else -1, r["layer"] if r["layer"] is not None else -1, stage_rank(r["label"]))

  rows.sort(key=sort_key)
  over = [r for r in rows if not (r["rel_l2"] <= a.threshold)]  # nan/inf count as over
  first = over[0] if over else None
  by_label = {}
  for r in rows:
    b = by_label.setdefault(r["label"], {"n": 0, "n_over": 0, "max_rel": 0.0, "max_frac_changed": 0.0, "max_ulps": 0.0,
                                         "first_token_over": None, "first_layer_over": None, "layers_over_ge63": set(), "layers_seen": set()})
    b["n"] += 1
    if r["layer"] is not None:
      b["layers_seen"].add(r["layer"])
    if not (r["rel_l2"] <= a.threshold):
      b["n_over"] += 1
      if b["first_token_over"] is None:
        b["first_token_over"], b["first_layer_over"] = r["token"], r["layer"]
      if r["layer"] is not None and r["token"] is not None and r["token"] >= 63:
        b["layers_over_ge63"].add(r["layer"])
    for k in ("rel_l2", "frac_changed", "max_ulps"):
      v = r[k]
      if v == v and v != float("inf"):
        kk = {"rel_l2": "max_rel", "frac_changed": "max_frac_changed", "max_ulps": "max_ulps"}[k]
        b[kk] = max(b[kk], v)
  for b in by_label.values():
    b["n_layers_seen"] = len(b.pop("layers_seen"))
    b["n_layers_with_delta_tokens_ge63"] = len(b.pop("layers_over_ge63"))
  first_layer_by_token = {}
  for r in over:
    if r["token"] is None:
      continue
    if r["token"] not in first_layer_by_token:
      first_layer_by_token[r["token"]] = {"layer": r["layer"], "label": r["label"], "rel": r["rel_l2"], "max_ulps": r["max_ulps"]}
  # the first full page: layer-0 attention-output / WO keys at token 63.. for the H5 rule
  page0 = [r for r in rows if r["token"] is not None and r["token"] >= 63 and r["layer"] == 0 and r["label"] in ("Attn out", "WO")]
  res = {
    "summary": {
      "n_keys_compared": len(rows), "n_over_threshold": len(over), "threshold": a.threshold,
      "first_over": first,
      "min_token_over": min((r["token"] for r in over if r["token"] is not None), default=None),
      "n_missing_in_off": len(missing_in_off), "n_missing_in_on": len(missing_in_on),
      "off_duplicate_keys": off_dups,
      "layer0_page1_attn_out_max_ulps": max((r["max_ulps"] for r in page0 if r["label"] == "Attn out"), default=None),
      "layer0_page1_attn_out_max_frac_changed": max((r["frac_changed"] for r in page0 if r["label"] == "Attn out"), default=None),
      "layer0_page1_wo_max_frac_changed": max((r["frac_changed"] for r in page0 if r["label"] == "WO"), default=None),
    },
    "by_label": by_label,
    "first_layer_by_token": {str(k): v for k, v in sorted(first_layer_by_token.items())},
    "missing_in_off": missing_in_off[:200], "missing_in_on": missing_in_on[:200],
    "heatmap": {lab: [[t, l, v] for (t, l), v in sorted(cells.items())] for lab, cells in hm.items()},
    "args": vars(a),
  }
  with open(a.out, "w") as f:
    json.dump(res, f, indent=1)
  if a.csv:
    with open(a.csv, "w", newline="") as f:
      w = csv.writer(f)
      w.writerow(["key", "label", "layer", "token", "len", "rel_l2", "max_abs", "frac_changed", "max_ulps"])
      for r in rows:
        w.writerow([r["key"], r["label"], r["layer"], r["token"], r["len"], r["rel_l2"], r["max_abs"], r["frac_changed"], r["max_ulps"]])
  print(json.dumps(res["summary"], indent=1))
  for lab, b in sorted(by_label.items(), key=lambda kv: stage_rank(kv[0])):
    print(f"{lab:>30}: n={b['n']:>7} over={b['n_over']:>7} max_rel={b['max_rel']:.3e} max_frac={b['max_frac_changed']:.3f} max_ulps={b['max_ulps']:.1f} "
          f"first_over=(tok {b['first_token_over']}, layer {b['first_layer_over']}) layers_with_delta(T>=63)={b['n_layers_with_delta_tokens_ge63']}/{b['n_layers_seen']}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
