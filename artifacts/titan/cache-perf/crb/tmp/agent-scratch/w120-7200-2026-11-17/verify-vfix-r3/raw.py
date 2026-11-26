#!/usr/bin/env python3
"""raw.py - own check of the four vfix-r3 defects against the raw files. Reads only, writes nothing.
It does not import the generator of the facts sheet."""
import datetime as dt, glob, os, re, sys
sys.dont_write_bytecode = True
R = "/home/jhan/workspace/titan/cache-perf/crb/results"

def ivs(path, start=None, end=None):
    """Intervals of a bwx csv (or of the line range start..end of it): I row line, round, pos, kernel,
    total / mesh 0 / mesh 1 rate as the sum over the T rows of bytes / elapsed_s / 1e9, first start and last end."""
    out, cur, d = [], None, {}
    for i, l in enumerate(open(path), 1):
        if start and i < start or end and i > end:
            continue
        p = l.rstrip("\n").split(",")
        if p[0] in ("T", "I"):
            k = (int(p[1]), int(p[2]), p[3])
            x = d.get(k)
            if x is None:
                x = d[k] = dict(r=k[0], pos=k[1], k=k[2], line=None, tot=0.0, m0=0.0, m1=0.0, ts=1e9, te=0.0, n=0, t0=None, t1=None)
                out.append(x)
        if p[0] == "T":
            x["t0"] = x["t0"] or i
            rate = int(p[6]) / float(p[7]) / 1e9
            x["tot"] += rate
            x["m0" if int(p[5]) < 64 else "m1"] += rate
            x["ts"] = min(x["ts"], float(p[9])); x["te"] = max(x["te"], float(p[10])); x["n"] += 1; x["t1"] = i
        elif p[0] == "I":
            x["line"] = i; x["agg"] = float(p[8])
    return out

def one(prefix):
    h = sorted(glob.glob(R + "/" + prefix + "-2026*"))
    assert len(h) == 1, h
    return h[0]

f2 = lambda v: "%.2f" % v
