#!/usr/bin/env python3
"""d3.py - defect vfix-r3-3: hardware error records of the saved journal against EVERY interval of the processes
of rows L-1 to L-4, R0, R0b (not only oldread at position 0 and asmread at position 1).
A record with the journal time J and a launch line with the time L lies between J-L-1 and J-L+1 s after the process start.
inside = this whole span lies in the interval. possible = the span and the interval share a part."""
import datetime as dt, os, re, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, ivs, one, f2
recs = []
for i, l in enumerate(open(R + "/dimm-check-20261117/h-5.txt", errors="replace"), 1):
    m = re.match(r"(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: Hardware error from APEI", l)
    if m:
        recs.append((dt.datetime.strptime(m[1], "%Y-%m-%dT%H:%M:%S"), i))
print("records in the journal:", len(recs))
rows = [("L-1", "w120-R8", ["a6456"]), ("L-2", "w120-R1", ["p1nop", "p2add"]), ("L-3", "w120-R5", ["thp"]),
        ("L-4", "w120-R6", ["st1", "st2", "st3"]), ("R0", "w120-R0", ["p1", "p2"]), ("R0b", "w120-R0b", ["cA", "cB", "cC"])]
tot = 0
for row, pre, tags in rows:
    d = one(pre)
    day = re.search(r"(\d{8})T", os.path.basename(d))[1]
    la = {}
    for l in open(d + "/launches.txt"):
        p = l.split()
        if p[0] == "launch": la.setdefault(p[1], {})["a"] = p[3]
        if p[0] == "rc": la.setdefault(p[2], {})["b"] = p[4]
    for tag in tags:
        A = dt.datetime.strptime(day + la[tag]["a"], "%Y%m%d%H:%M:%S"); B = dt.datetime.strptime(day + la[tag]["b"], "%Y%m%d%H:%M:%S")
        iv = ivs(d + "/%s.csv" % tag)
        hits = [(t, i) for t, i in recs if A <= t <= B]
        tot += len(hits)
        print("==", row, tag, "window", A, "to", B, "| records", len(hits), "| intervals", len(iv))
        by = {}
        for t, i in hits:
            off = (t - A).total_seconds()
            found = False
            for x in iv:
                if x["ts"] <= off - 1 and off + 1 <= x["te"]:
                    by.setdefault((x["r"], x["pos"]), []).append((i, off, "inside")); found = True
                elif off - 1 < x["te"] and x["ts"] < off + 1:
                    by.setdefault((x["r"], x["pos"]), []).append((i, off, "possible")); found = True
            if not found:
                print("   journal line", i, "at", off, "s: in no interval")
        for (r, pos), h in sorted(by.items()):
            x = next(y for y in iv if (y["r"], y["pos"]) == (r, pos))
            sib = [y for y in iv if y["pos"] == pos and y["r"] != r]
            print("   round %d pos %2d %-14s I line %5d  %s GB/s  t %.2f to %.2f s | records %s | other round: %s"
                  % (r, pos, x["k"], x["line"], f2(x["tot"]), x["ts"], x["te"], h,
                     ["%s GB/s, I line %d, %s" % (f2(y["tot"]), y["line"], "has records" if (y["r"], y["pos"]) in by else "no records") for y in sib]))
print("records in all windows:", tot)
