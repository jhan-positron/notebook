#!/usr/bin/env python3
"""Score two t_amx_logit_ab dumps (dense fp32 logits per step).

File format (tron-amx t/t_amx_logit_ab.cpp:53-61): uint64 n; then n times
{ uint64 m; float32[m] }. Rows cover every prompt token and every forced step
(LogitsMode::ALL). With AMX_TOKENS = <prompt ids> + <64 forced ids>, the last
64 rows are the forced steps.

  dd_bin_score.py off.bin on.bin [--last 64] [--out steps.json]
"""
import argparse
import json
import struct
import sys

import numpy as np


def load(path):
  rows = []
  with open(path, "rb") as f:
    (n,) = struct.unpack("<Q", f.read(8))
    for _ in range(n):
      (m,) = struct.unpack("<Q", f.read(8))
      rows.append(np.frombuffer(f.read(4 * m), dtype=np.float32).astype(np.float64))
  return rows


def softmax(x):
  e = np.exp(x - x.max())
  return e / e.sum()


def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("off")
  ap.add_argument("on")
  ap.add_argument("--last", type=int, default=64, help="number of trailing rows that are forced steps")
  ap.add_argument("--out", default=None)
  a = ap.parse_args()
  A, B = load(a.off), load(a.on)
  if len(A) != len(B):
    print(f"row count differs: {len(A)} vs {len(B)}")
  n = min(len(A), len(B))
  rows = []
  for i in range(n):
    x, y = A[i], B[i]
    if x.shape != y.shape:
      rows.append({"row": i, "shape_mismatch": [int(x.size), int(y.size)]})
      continue
    o1 = int(np.argmax(x)); xx = x.copy(); xx[o1] = -np.inf; o2 = int(np.argmax(xx))
    n1 = int(np.argmax(y))
    d = y - x
    rows.append({
      "row": i, "step": i - (n - a.last) + 1 if i >= n - a.last else None,
      "off_top1": o1, "off_top2": o2, "on_top1": n1, "same_top1": o1 == n1,
      "margin_off": float(x[o1] - x[o2]), "delta_pair": float(d[o1] - d[o2]),
      "max_abs_delta": float(np.abs(d).max()), "identical": bool(not np.any(d)),
      "tvd": float(0.5 * np.abs(softmax(x) - softmax(y)).sum()),
    })
  ok = [r for r in rows if "margin_off" in r]
  summary = {
    "rows": n, "identical_rows": sum(r["identical"] for r in ok),
    "flip_rows": [r["row"] for r in ok if not r["same_top1"]],
    "flip_steps": [r["step"] for r in ok if not r["same_top1"] and r["step"]],
    "max_tvd": max((r["tvd"] for r in ok), default=None),
    "median_abs_delta_pair": float(np.median([abs(r["delta_pair"]) for r in ok])) if ok else None,
  }
  print(json.dumps(summary, indent=1))
  if a.out:
    with open(a.out, "w") as f:
      json.dump({"summary": summary, "rows": rows}, f, indent=1)
  return 0


if __name__ == "__main__":
  sys.exit(main())
