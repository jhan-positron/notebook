#!/usr/bin/env python3
"""Parse writepath.csv (part 5, 2026-11-02). Read only.
Prints for each case: the args, the loop rate of every run (short and long) with its csv line,
and for each event the long count, the short count, long minus short per second."""
import re, sys, collections
F = "/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T211150Z/writepath.csv"
hdr = re.compile(r"^-- (\S+) (short|long) set (\S+) events (.*?) args (.*)$")
row = re.compile(r"^(\d+|<not counted>|<not supported>),,(.+/),(\d+),(\d+\.\d+),,$")
bw = re.compile(r"^(asm\w+|read|write|copy),(\d+),(\d+),(\w+),(\d*),([\d.]*),([\d.]+),")
cases = collections.OrderedDict()
cur = None
for n, line in enumerate(open(F), 1):
    line = line.rstrip("\n")
    m = hdr.match(line)
    if m:
        c, ln, s, ev, args = m.groups()
        cur = cases.setdefault(c, {"args": set(), "runs": collections.OrderedDict()})
        cur["args"].add(args)
        cur_run = cur["runs"].setdefault((s, ln), {"hdr": n, "ev": collections.OrderedDict(), "bw": []})
        continue
    if line.startswith("-- "):
        cur = None; continue
    if cur is None: continue
    m = row.match(line)
    if m:
        cur_run["ev"][m.group(2)] = (m.group(1), int(m.group(3)), float(m.group(4)), n); continue
    m = bw.match(line)
    if m:
        cur_run["bw"].append((m.group(4), m.group(5), m.group(6), float(m.group(7)), n, line))
mode = sys.argv[1] if len(sys.argv) > 1 else "rates"
for c, d in cases.items():
    print(f"=== case {c}  args: {sorted(d['args'])}")
    if mode == "rates":
        for (s, ln), r in d["runs"].items():
            for rep, tb, el, agg, n, line in r["bw"]:
                print(f"   set {s:8s} {ln:5s} rep {rep:4s} bytes {tb:>13s} elapsed {el:>7s} GB/s {agg:7.2f}  (csv line {n})  [{line.split(',',7)[7]}]")
    else:
        sets = sorted({s for (s, ln) in d["runs"]})
        for s in sets:
            lo = d["runs"].get((s, "long")); sh = d["runs"].get((s, "short"))
            if not lo or not sh: continue
            for ev in lo["ev"]:
                lc, lt, lp, lnn = lo["ev"][ev]; sc, st, sp, snn = sh["ev"].get(ev, ("0", 0, 0, 0))
                try:
                    dlt = int(lc) - int(sc); dt = (lt - st) / 1e9
                    print(f"   {s:8s} {ev[:70]:70s} long {lc:>14s} ({lp:.0f}%) short {sc:>13s} d={dlt:>14,d} in {dt:.4f}s = {dlt/dt:.4e}/s  (csv {snn},{lnn})")
                except ValueError:
                    print(f"   {s:8s} {ev[:70]:70s} long {lc} short {sc}")
