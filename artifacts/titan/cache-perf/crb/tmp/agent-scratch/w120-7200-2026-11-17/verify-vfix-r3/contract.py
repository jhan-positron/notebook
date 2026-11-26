#!/usr/bin/env python3
"""contract.py - compares the new facts.json with the copy saved before this correction (bak-before-vfix-r3).
CONTRACT: no field of the "intervals" records or of meta.launches renamed or removed, no GBps value, n or line number changed.
Prints every path of the json tree that was changed, removed or added. Reads only."""
import json, os, sys
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
old = json.load(open(S + "/bak-before-vfix-r3/facts.json")); new = json.load(open(S + "/facts.json"))
print("intervals: identical list:", old["intervals"] == new["intervals"], "| n", len(old["intervals"]), len(new["intervals"]))
print("meta.launches identical:", old["meta"]["launches"] == new["meta"]["launches"])
print("meta.counts identical:", old["meta"]["counts"] == new["meta"]["counts"], "| meta.checks identical:", old["meta"]["checks"] == new["meta"]["checks"])
chg, rem, add = [], [], []
def walk(a, b, path):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b: rem.append(path + "." + k)
            else: walk(a[k], b[k], path + "." + k)
        for k in b:
            if k not in a: add.append(path + "." + k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, "%s[%d]" % (path, i))
    elif a != b:
        chg.append(path)
walk(old, new, "")
print("removed paths:", rem)
print("changed paths:", chg)
print("added paths:")
for p in add: print("   ", p)
