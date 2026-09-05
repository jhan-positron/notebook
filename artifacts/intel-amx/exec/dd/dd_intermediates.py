#!/usr/bin/env python3
"""Shared parser for tron --intermediates-file logs (model.hpp log_intermediate).

Line format (model.hpp:1272-1284):
  <message right-aligned in 50 chars> (<len>): <v0> <v1> ... <v(len-1)>
  each value: " " + setw(11) + setprecision(8) default-float formatting.
Message forms (model.hpp:1291-1331):
  "<label> of token <T>"                     e.g. "Logits of token 2047"
  "<label> layer <L> of token <T>"           e.g. "WO layer 0 of token 63"
  "<label>"                                  (weight lines, no token)
bin/compare_intermediates keys on line[0:50]; we do the same and also parse
label / layer / token out of it.
"""
import re

import numpy as np

KEY_RE = re.compile(r"^(?P<label>.*?)(?: layer (?P<layer>\d+))? of token (?P<tok>\d+)$")

# Stage order inside one layer for sorting keys (ingested + shared labels;
# hand-written extras get order 50+ alphabetically).
STAGE_ORDER = {
  "Embedding": 0, "Input RMSNorm": 1,
  "WQ": 2, "WK": 3, "WV": 4, "WQ roped": 5, "WK roped": 6, "Attn out": 7,
  "Attn scores": 7, "WO": 8, "WO permuted output": 8, "Post-attn RMSNorm": 9,
  "WFF1": 10, "WFF3": 11, "Pre-WFF2": 12, "WFF2": 13,
  "Un-normalized final embedding": 20, "Final embedding": 21,
  "Logits": 30, "Top-k Logits": 31, "Top-k Token IDs for Logits": 32,
}


def split_line(line):
  """Return (key50, message, values_str) or None for a malformed line."""
  if len(line) < 52:
    return None
  key = line[0:50]
  rest = line[51:]
  # rest = "(<len>): v0 v1 ..."
  close = rest.find("): ")
  if not rest.startswith("(") or close < 0:
    return None
  return key, key.strip(), rest[close + 3:]


def parse_message(msg):
  m = KEY_RE.match(msg)
  if not m:
    return msg, None, None
  return m.group("label"), (int(m.group("layer")) if m.group("layer") is not None else None), int(m.group("tok"))


def values(values_str, dtype=np.float64):
  return np.fromstring(values_str, sep=" ", dtype=dtype)


def stage_rank(label):
  if label in STAGE_ORDER:
    return STAGE_ORDER[label]
  # "WFF1 expert 3" and similar
  base = label.split(" expert ")[0]
  return STAGE_ORDER.get(base, 50)


def index_offsets(path):
  """Map key50 -> byte offset of the line start (first occurrence wins,
  duplicates counted)."""
  idx = {}
  dups = 0
  with open(path, "rb") as f:
    off = 0
    for raw in f:
      key = raw[0:50].decode("ascii", errors="replace")
      if key in idx:
        dups += 1
      else:
        idx[key] = off
      off += len(raw)
  return idx, dups


def read_line_at(fh, off):
  fh.seek(off)
  return fh.readline().decode("ascii", errors="replace")
