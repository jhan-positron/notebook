#!/usr/bin/env python3
"""Recompute, from the raw perf rows of the 2026-11-02 root run (part 5), the numbers this
update cites. No idle subtraction is applied to the two free-running cycle counters.
  1. mesh clock: dtc_cycles count / counter run time, every raw row
  2. core clock of CPU 2: cycles, long run minus short run
  3. data flits per mesh cycle for every directly counted port or link, long minus short
Usage: mesh_clock.py [writepath.csv]"""
import re, sys
f = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T211150Z/writepath.csv"
row = re.compile(r"^(\d+),,(.+/),(\d+),(\d+\.\d+),,$")
case = None; data = {}; rates = []
for line in open(f):
    line = line.rstrip("\n")
    m = re.match(r"-- (\S+) (short|long) set (\S+) events", line)
    if m: case = (m.group(1), m.group(3), m.group(2)); data.setdefault(case, {}); continue
    m = re.match(r"-- idle set (\S+) events", line)
    if m: case = ("idle", m.group(1), "idle"); data.setdefault(case, {}); continue
    m = row.match(line)
    if case and m:
        cnt, ev, ns, pct = int(m.group(1)), m.group(2), int(m.group(3)), float(m.group(4))
        data[case][ev] = (cnt, ns, pct)
        if ev.endswith("/dtc_cycles/"): rates.append((cnt / ns, ev.split("/")[0], case, pct))
print("1. mesh cycle counter (dtc_cycles), count / run time of each raw row")
for mesh in ("arm_cmn_0", "arm_cmn_1"):
    r = [x[0] for x in rates if x[1] == mesh]
    print(f"   {mesh}: {len(r)} rows, {min(r):.6f} to {max(r):.6f} GHz")
print(f"   all {len(rates)} rows: {min(x[0] for x in rates):.6f} to {max(x[0] for x in rates):.6f} GHz; "
      f"rows with the counter running less than 100 %: {sum(1 for x in rates if x[3] < 100)}; "
      f"idle rows: {sum(1 for x in rates if x[2][0] == 'idle')}")
print("2. core cycle counter of CPU 2 (armv8_pmuv3_0/cycles/), long run minus short run")
for (c, s, ln), ev in sorted(data.items()):
    if s == "core3" and ln == "long":
        sh = data[(c, s, "short")]; k = [k for k in ev if k.endswith("/cycles/")][0]
        dc, dt = ev[k][0] - sh[k][0], ev[k][1] - sh[k][1]
        print(f"   {c:14s} {dc:>13,} cycles / {dt / 1e9:.9f} s = {dc / dt:.5f} GHz")
print("3. data flits per mesh cycle, long run minus short run, highest first")
out = []
for (c, s, ln), ev in data.items():
    if ln != "long" or (c, s, "short") not in data: continue
    sh = data[(c, s, "short")]
    cyc = [k for k in ev if k.endswith("/dtc_cycles/") and k.startswith("arm_cmn_0")]
    if not cyc: continue
    dc = ev[cyc[0]][0] - sh[cyc[0]][0]
    for k in ev:
        if "dat_txflit_valid" in k:
            out.append(((ev[k][0] - sh[k][0]) / dc, c, s, k.split("/")[1].split(",")[0], ev[k][0] - sh[k][0], dc))
out.sort(reverse=True)
for v, c, s, name, df, dc in out[:6]:
    print(f"   {v:.4f} flits per cycle  {c:14s} {name:24s} ({df:,} flits / {dc:,} cycles)")
print(f"   {len(out)} direct data-flit counts; above 1.0 flit per cycle: {sum(1 for x in out if x[0] > 1.0)}")
