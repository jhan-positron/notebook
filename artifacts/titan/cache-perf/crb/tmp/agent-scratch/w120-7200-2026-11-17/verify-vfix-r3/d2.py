#!/usr/bin/env python3
"""d2.py - defect vfix-r3-2: oldread per mesh (CPUs 0-63 = mesh 0, CPUs 64-119 = mesh 1), 7200 MT/s against
the bwx12 and bwx11 rows at 8000 MT/s, with and without part C, and without part C and control I."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, ivs, one, f2
def old(prefix, f, pos=None):
    d = one(prefix)
    if f is None:
        f = [n for n in os.listdir(d) if n.endswith(".csv")][0]
    return [dict(x, src="%s/%s line %d round %d" % (os.path.basename(d), f, x["line"], x["r"]))
            for x in ivs(d + "/" + f) if x["k"] == "oldread" and (pos is None or x["pos"] == pos)]
G = dict(
    L=[x for t in ("T72L1", "T72L2", "T72L3") for x in old("w120-" + t, "a6456.csv", 0)],
    C=[x for t in ("T72C1", "T72C2", "T72C3", "T72C4") for x in old("w120-" + t, None)],
    I=[x for t in ("T72I1", "T72I2") for x in old("w120-" + t, "a6456.csv", 0)],
    F=old("w120-w120-F72d12", "a6456.csv", 0))
B = [x for pre, f in (("w120-R8", "a6456.csv"), ("w120-R1", "p1nop.csv"), ("w120-R1", "p2add.csv"), ("w120-R5", "thp.csv"),
                      ("w120-R6", "st1.csv"), ("w120-R6", "st2.csv"), ("w120-R6", "st3.csv"), ("w120-R0", "p1.csv"),
                      ("w120-R0", "p2.csv"), ("w120-R0b", "cA.csv"), ("w120-R0b", "cB.csv"), ("w120-R0b", "cC.csv"))
     for x in old(pre, f, 0)]
def show(name, L_):
    lo0, hi0 = min(L_, key=lambda x: x["m0"]), max(L_, key=lambda x: x["m0"])
    lo1, hi1 = min(L_, key=lambda x: x["m1"]), max(L_, key=lambda x: x["m1"])
    print("%-34s n %2d  mesh 0 %s to %s  mesh 1 %s to %s" % (name, len(L_), f2(lo0["m0"]), f2(hi0["m0"]), f2(lo1["m1"]), f2(hi1["m1"])))
    return lo0, hi0, lo1, hi1
for k in "LCIF":
    show("7200 " + k, G[k])
b = show("8000 bwx12 and bwx11, position 0", B)
for name, keys in (("7200 all (L, C, I, F)", "LCIF"), ("7200 without C (L, I, F)", "LIF"), ("7200 without C and I (L, F)", "LF")):
    L_ = [x for k in keys for x in G[k]]
    lo0, hi0, lo1, hi1 = show(name, L_)
    print("   mesh 0 lower in every interval:", hi0["m0"] < b[0]["m0"], "| mesh 1 higher in every interval:", lo1["m1"] > b[3]["m1"])
    print("   mesh 0 highest from:", hi0["src"], "| mesh 1 lowest from:", lo1["src"], "| mesh 1 highest from:", hi1["src"])
