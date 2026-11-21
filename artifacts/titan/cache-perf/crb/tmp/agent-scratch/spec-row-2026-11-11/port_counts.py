#!/usr/bin/env python3
"""Recompute, from the raw perf rows of part 5 (2026-11-02), the counts that the open item
"Spec throughput of the pair port and the mesh cache" cites. No idle subtraction is applied.
Parts 1 and 2: every value is the long run (2 s) minus the short run (0.2 s) of one event set.
Part 3: the rates of the long runs themselves.
  1. per 64 B line: bus accesses, bus writes, L2 refills of CPU 2, and data flits at its port;
     also the bus writes of CPU 2 per line that CPU 2 wrote itself (its L1 write accesses / 2)
  2. per mesh cycle: bus writes of CPU 2 (mesh clock taken as 2.0e9 cycles per second)
  3. loop rate of the nine long runs of each case (variation from run to run)
Usage: port_counts.py [writepath.csv]"""
import re, sys
f = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T211150Z/writepath.csv"
row = re.compile(r"^(\d+),,(.+/),(\d+),(\d+\.\d+),,$")
bwrow = re.compile(r"^asm\w+,\d+,\d+,\d+,(\d+),[\d.]+,([\d.]+),")
case = None; cnt = {}; byt = {}; rate = {}
for n, line in enumerate(open(f), 1):
    line = line.rstrip("\n")
    m = re.match(r"-- (\S+) (short|long) set (\S+) events", line)
    if m: case = (m.group(1), m.group(3), m.group(2)); cnt[case] = {}; continue
    if line.startswith("-- idle"): case = None; continue
    if case is None: continue
    m = row.match(line)
    if m: cnt[case][m.group(2)] = (int(m.group(1)), int(m.group(3)), n); continue
    m = bwrow.match(line)
    if m: byt[case] = int(m.group(1)); rate[case] = float(m.group(2))

def delta(c, s, key):
    """(count, seconds, lines of 64 B, csv line numbers) of event `key`, long run minus short run."""
    lo, sh = cnt[(c, s, "long")], cnt[(c, s, "short")]
    k = [e for e in lo if key in e][0]
    return (lo[k][0] - sh[k][0], (lo[k][1] - sh[k][1]) / 1e9,
            (byt[(c, s, "long")] - byt[(c, s, "short")]) / 64, (sh[k][2], lo[k][2]))

MESH_HZ = 2.0e9
print("1. counts per 64 B line that the loop read or wrote (all threads of the case together)")
for c, s, key, name in [
    ("r8M-c2", "core3", "pmuv3_0/bus_access/", "bus accesses, all (BUS_ACCESS)"),
    ("r8M-c2", "core2", "event=0x61/", "bus writes (BUS_ACCESS_WR)"),
    ("r8M-c2", "xpport", "mxp_p1_dat_txflit_valid", "data flits, crosspoint to port"),
    ("r8M-c2", "core1", "l2d_cache_refill/", "L2 refills"),
    ("w8M-c2", "core2", "event=0x61/", "bus writes (BUS_ACCESS_WR)"),
    ("w8M-c2", "core3", "pmuv3_0/bus_access/", "bus accesses, all (BUS_ACCESS)"),
    ("w1G-c2", "core2", "event=0x61/", "bus writes (BUS_ACCESS_WR)"),
    ("w1G-c2", "core3", "pmuv3_0/bus_access/", "bus accesses, all (BUS_ACCESS)"),
    ("w8M-c2c3", "core2", "event=0x61/", "bus writes of CPU 2, per line of both"),
]:
    d, t, lines, where = delta(c, s, key)
    print(f"   {c:9s} {name:32s} {d / lines:7.4f} per line   ({d:,} in {t:.4f} s, csv lines {where[0]} and {where[1]})")
a = delta("r8M-c2", "core3", "pmuv3_0/bus_access/"); w = delta("r8M-c2", "core2", "event=0x61/")
print(f"   r8M-c2    bus accesses that are not writes  {a[0] / a[2] - w[0] / w[2]:7.4f} per line   (difference of two event sets, each long minus short)")
print("   bus writes of CPU 2 per line that CPU 2 wrote itself (own lines = L1 write accesses, event 0x41, / 2; same run)")
for c in ("w8M-c2", "w8M-c2c3", "w1G-c2"):
    bw_, l1 = delta(c, "core2", "event=0x61/"), delta(c, "core2", "event=0x41/")
    print(f"   {c:9s} {bw_[0] / (l1[0] / 2):7.4f} per own line   ({bw_[0]:,} bus writes, {l1[0]:,} L1 write accesses)")
print("2. bus writes of CPU 2 per mesh cycle (count per second / 2.0e9)")
for c in ("w1G-c2", "w8M-c2", "w8M-c2c3", "r8M-c2"):
    d, t, lines, where = delta(c, "core2", "event=0x61/")
    print(f"   {c:9s} {d / t:.4e} per second = {d / t / MESH_HZ:.3f} per mesh cycle = {d / t * 32 / 1e9:.1f} GB/s at 32 B each")
print("3. loop rate of the nine long runs of each case, GB/s")
for c in ("r8M-c2", "w8M-c2", "w1G-c2", "w8M-c2c3", "w8M-c2c4", "w8M-c2c4c6c8"):
    r = sorted(v for (cc, s, ln), v in rate.items() if cc == c and ln == "long")
    print(f"   {c:13s} {len(r)} runs, {r[0]:.2f} to {r[-1]:.2f}, spread {100 * (r[-1] - r[0]) / r[-1]:.1f} %")
