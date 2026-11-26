#!/usr/bin/env python3
"""d1.py - defect vfix-r3-1: oldread of part C against the 8000 MT/s processes that started after 120-thread work."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, ivs, one, f2
import re
def old0(path, **kw):
    return [x for x in ivs(path, **kw) if x["k"] == "oldread"]
print("== part C, oldread (all positions)")
C = []
for tag in ("T72C1", "T72C2", "T72C3", "T72C4"):
    d = one("w120-" + tag)
    f = [n for n in os.listdir(d) if n.endswith(".csv")][0]
    for x in old0(d + "/" + f):
        C.append(x["tot"]); print("  ", tag, f, "round", x["r"], "pos", x["pos"], "I line", x["line"], f2(x["tot"]))
print("  part C range", f2(min(C)), "to", f2(max(C)), "n", len(C))
print("== part L, oldread")
Lr = []
for tag in ("T72L1", "T72L2", "T72L3"):
    d = one("w120-" + tag)
    for x in old0(d + "/a6456.csv"):
        if x["pos"] == 0:
            Lr.append(x["tot"])
print("  part L range", f2(min(Lr)), "to", f2(max(Lr)), "n", len(Lr))
print("== pool L-1..L-4, bwx12, oldread at position 0")
pool = [("L-1", "w120-R8", "a6456"), ("L-2", "w120-R1", "p1nop"), ("L-2", "w120-R1", "p2add"), ("L-3", "w120-R5", "thp"),
        ("L-4", "w120-R6", "st1"), ("L-4", "w120-R6", "st2"), ("L-4", "w120-R6", "st3")]
def launches(d):
    out = {}; prev_rc = None; rows = []
    for l in open(d + "/launches.txt"):
        p = l.split()
        if p[0] == "launch":
            out[p[1]] = dict(utc=p[3], load=float(p[5]), prev_rc=prev_rc, threads=l.split("--threads ")[1].split()[0])
        elif p[0] == "rc":
            prev_rc = (p[2], p[4], out[p[2]]["threads"])
    return out
busy, idle = [], []
for row, pre, tag in pool:
    d = one(pre); la = launches(d)[tag]
    v = [x["tot"] for x in old0(d + "/%s.csv" % tag) if x["pos"] == 0]
    print("  ", row, tag, "launch", la["utc"], "load", la["load"], "previous rc:", la["prev_rc"], [f2(x) for x in v])
    (busy if la["load"] >= 1.0 else idle).extend(v)
print("  started after 120-thread work:", f2(min(busy)), "to", f2(max(busy)), "n", len(busy))
print("  started at a load below 1.0:", f2(min(idle)), "to", f2(max(idle)), "n", len(idle))
print("  L and C together: n", len(Lr) + len(C), "highest", f2(max(Lr + C)), "| lowest of the 5 bwx12 processes", f2(min(busy)),
      "| below without overlap:", max(Lr + C) < min(busy))
print("== bwx11 rows R0, R0b: oldread at position 0, processes that follow a 120-thread process")
b11 = []
for row, pre, tags in (("R0", "w120-R0", ("p1", "p2")), ("R0b", "w120-R0b", ("cA", "cB", "cC"))):
    d = one(pre); L_ = launches(d)
    for tag in tags:
        la = L_[tag]
        v = [(x["line"], x["tot"]) for x in old0(d + "/%s.csv" % tag) if x["pos"] == 0]
        print("  ", row, tag, "launch", la["utc"], "load", la["load"], "previous rc:", la["prev_rc"], [(a, f2(b)) for a, b in v])
        if la["prev_rc"] and la["prev_rc"][2] == "120":
            b11.extend(b for a, b in v)
print("  bwx11 after 120-thread work:", f2(min(b11)), "to", f2(max(b11)), "n", len(b11), "| overlap with part C:", min(b11) <= max(C))
print("== runner bwx, tags common-6000-*, oldread at position 0")
bx = []; nproc = 0
for folder, csv in (("B7-20261113T232859Z", "B7.csv"), ("B7-20261114T024352Z", "B7.csv"), ("C3-20261114T022708Z", "C3.csv"), ("C3-20261114T054116Z", "C3.csv")):
    path = R + "/" + folder + "/" + csv
    steps = [(i, l) for i, l in enumerate(open(path), 1) if l.startswith("-- step")]
    nl = sum(1 for _ in open(path))
    for j, (i, l) in enumerate(steps):
        tag = l.split(" tag ")[1].split()[0]
        if not tag.startswith("common-6000-"):
            continue
        end = steps[j + 1][0] - 1 if j + 1 < len(steps) else nl
        prev = steps[j - 1][1] if j else None
        assert prev and "--threads 120 " in prev and " binary bwx " in prev, (folder, tag)
        v = [x["tot"] for x in ivs(path, start=i, end=end) if x["k"] == "oldread" and x["pos"] == 0]
        nproc += 1; bx.extend(v)
print("  runner bwx:", f2(min(bx)), "to", f2(max(bx)), "n", len(bx), "processes", nproc, "| overlap with part C:", min(bx) <= max(C))
