#!/usr/bin/env python3
"""d3b.py - round 1 minus round 0 for every position of the 4 processes with records, with a mark where a record
lies in or near one of the two intervals. Shows how far the two rounds differ where no record is on file."""
import datetime as dt, os, re, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, ivs, one, f2
recs = []
for i, l in enumerate(open(R + "/dimm-check-20261117/h-5.txt", errors="replace"), 1):
    m = re.match(r"(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: Hardware error from APEI", l)
    if m:
        recs.append((dt.datetime.strptime(m[1], "%Y-%m-%dT%H:%M:%S"), i))
for row, pre, tag in (("L-1", "w120-R8", "a6456"), ("L-2", "w120-R1", "p1nop"), ("L-2", "w120-R1", "p2add"), ("R0", "w120-R0", "p1")):
    d = one(pre)
    day = re.search(r"(\d{8})T", os.path.basename(d))[1]
    for l in open(d + "/launches.txt"):
        p = l.split()
        if p[0] == "launch" and p[1] == tag: A = dt.datetime.strptime(day + p[3], "%Y%m%d%H:%M:%S")
        if p[0] == "rc" and p[2] == tag: B = dt.datetime.strptime(day + p[4], "%Y%m%d%H:%M:%S")
    iv = ivs(d + "/%s.csv" % tag)
    offs = [(t - A).total_seconds() for t, i in recs if A <= t <= B]
    def mark(x):
        if any(x["ts"] <= o - 1 and o + 1 <= x["te"] for o in offs): return "inside"
        if any(o - 1 < x["te"] and x["ts"] < o + 1 for o in offs): return "possible"
        return ""
    print("==", row, tag)
    clean = []
    for pos in sorted({x["pos"] for x in iv}):
        a = next(x for x in iv if x["pos"] == pos and x["r"] == 0); b = next(x for x in iv if x["pos"] == pos and x["r"] == 1)
        ma, mb = mark(a), mark(b)
        dlt = b["tot"] - a["tot"]
        if not ma and not mb: clean.append(dlt)
        print("   pos %2d %-15s r0 %s %-8s r1 %s %-8s r1-r0 %+.2f (%.2f %%)" % (pos, a["k"], f2(a["tot"]), ma, f2(b["tot"]), mb, dlt, dlt / a["tot"] * 100))
    print("   positions with no record in or near either round: %d, r1-r0 from %+.2f to %+.2f GB/s" % (len(clean), min(clean), max(clean)))
