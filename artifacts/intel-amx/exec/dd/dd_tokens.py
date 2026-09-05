#!/usr/bin/env python3
"""Compare two generated-token sequences and report the first divergence.

Inputs (both of the SAME kind):
  *.tok   : a runtron --output-token-file (whitespace-separated decimal ids;
            the first row is used - the recipe has exactly one prompt)
  *.log   : a runtron console log; generated text is extracted from the
            green ANSI chunks  \\x1b[38;2;000;128;000m ... \\x1b[0m
            (one chunk per generated token). Line-based diffs are wrong here
            (ASLR mapping lines, mid-line log continuation) - see QUEUE.md:68.

Usage: dd_tokens.py A B [--json out.json]
Prints: lengths, identical?, first differing 1-based position, number of
differing positions, and both continuations from the first difference.
"""
import json
import re
import sys

GREEN = re.compile(rb"\x1b\[38;2;000;128;000m(.*?)\x1b\[0m", re.S)


def load(path):
  if path.endswith(".tok"):
    with open(path) as f:
      rows = [ln for ln in f.read().splitlines() if ln.strip()]
    if not rows:
      return [], "ids"
    return [int(x) for x in rows[0].split()], "ids"
  raw = open(path, "rb").read()
  chunks = [c.decode("utf-8", errors="replace") for c in GREEN.findall(raw)]
  return chunks, "text"


def main(argv):
  if len(argv) < 3:
    print(__doc__)
    return 2
  a, ka = load(argv[1])
  b, kb = load(argv[2])
  if ka != kb:
    print(f"cannot compare {ka} with {kb}: give two .tok files or two .log files")
    return 2
  n = min(len(a), len(b))
  diff = [i for i in range(n) if a[i] != b[i]]
  res = {
    "a": argv[1], "b": argv[2], "kind": ka, "len_a": len(a), "len_b": len(b),
    "identical": len(a) == len(b) and not diff,
    "first_diff_pos_1based": (diff[0] + 1) if diff else None,
    "n_diff_positions": len(diff), "n_compared": n,
  }
  if diff:
    i = diff[0]
    res["a_at_first_diff"] = a[i]
    res["b_at_first_diff"] = b[i]
    res["a_continuation"] = a[i:i + 40]
    res["b_continuation"] = b[i:i + 40]
  print(json.dumps(res, ensure_ascii=True, indent=1))
  if "--json" in argv:
    with open(argv[argv.index("--json") + 1], "w") as f:
      json.dump(res, f, indent=1)
  return 0 if res["identical"] else 1


if __name__ == "__main__":
  sys.exit(main(sys.argv))
