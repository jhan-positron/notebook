#!/usr/bin/env python3
"""pr5606-check-20261123: compare the symbol sizes of the option-OFF tree with the option-ON tree, both at S2.

Input: the two files defs.tsv that symbols.py writes (one row per definition of a symbol that the test object
defines as weak or unique: mangled name, object, nm type, size). The object "TEST" is the test's own object.
Why: in the ON tree every object is compiled with -DTRON_AMX_DISPATCH (the two test-support objects excepted).
In the OFF tree only the test object is. When a symbol has the same size in the same object of both trees, the
define did not change that copy.
Usage: symbols-compare.py <defs.tsv of the OFF tree> <defs.tsv of the ON tree>
"""
import sys


def load(path):
    rows = {}
    for raw in open(path):
        if raw.startswith("#"):
            continue
        name, obj, typ, size = raw.rstrip("\n").split("\t")
        rows[(name, obj)] = (typ, size)
    return rows


off, on = load(sys.argv[1]), load(sys.argv[2])
t_off = {k[0]: v for k, v in off.items() if k[1] == "TEST"}
t_on = {k[0]: v for k, v in on.items() if k[1] == "TEST"}
both = set(t_off) & set(t_on)
print(f"test object, weak or unique symbols: OFF tree {len(t_off)}, ON tree {len(t_on)}, in both {len(both)}, "
      f"only OFF {len(set(t_off) - set(t_on))}, only ON {len(set(t_on) - set(t_off))}")
d = [n for n in both if t_off[n][1] != t_on[n][1]]
print(f"  of the {len(both)} in both, with a different size in the two trees: {len(d)}")
for n in d[:10]:
    print(f"    {t_off[n][1]} B / {t_on[n][1]} B  {n[:160]}")
o_off = {k: v for k, v in off.items() if k[1] != "TEST"}
o_on = {k: v for k, v in on.items() if k[1] != "TEST"}
both = set(o_off) & set(o_on)
print(f"definitions in other objects (symbol, object): OFF tree {len(o_off)}, ON tree {len(o_on)}, in both {len(both)}, "
      f"only OFF {len(set(o_off) - set(o_on))}, only ON {len(set(o_on) - set(o_off))}")
d = [k for k in both if o_off[k][1] != o_on[k][1]]
print(f"  of the {len(both)} in both, with a different size in the two trees: {len(d)}")
for k in d[:10]:
    print(f"    {o_off[k][1]} B / {o_on[k][1]} B  {k[1]}  {k[0][:140]}")
for label, a, b in (("only in the OFF tree", o_off, o_on), ("only in the ON tree", o_on, o_off)):
    objs = sorted({k[1] for k in set(a) - set(b)})
    if objs:
        print(f"  objects with definitions {label}: {', '.join(objs[:8])}")
