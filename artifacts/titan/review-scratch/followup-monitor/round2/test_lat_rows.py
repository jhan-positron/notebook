#!/usr/bin/env python3
"""test_lat_rows.py - the latency CSV reader (gen_run3.lat_rows) against the row shapes the
programs print: run 2 (cycles + 3 counters), run 3 (+ perf_cov), run 4 (cycles + 6 counters +
perf_cov) with a refused optional event ("-" in its column), an invalid row ("-" everywhere), a
tiny nonzero count in exponent form, and a row with the wrong field count (rejected).
Run: python3 test_lat_rows.py (exit 0 when every case behaves)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_run3 import lat_rows

H4 = "mem,size_bytes,mode,rep,loads,ns_per_load,cycles_per_load,l1d_refill_per_load,l2d_refill_per_load,l3d_refill_rd_per_load,l1d_refill_hwprf_per_load,l2d_refill_hwprf_per_load,l2d_refill_l1dhwprf_per_load,perf_cov"
H3 = "mem,size_bytes,mode,rep,loads,ns_per_load,cycles_per_load,l1d_refill_per_load,l2d_refill_per_load,l3d_refill_rd_per_load,perf_cov"
H2 = "mem,size_bytes,mode,rep,loads,ns_per_load,cycles_per_load,l1d_refill_per_load,l2d_refill_per_load,l3d_refill_rd_per_load"
META = "# latency: ns_per_load = elapsed_ns / loads; cpu=2 mem=dram cntfrq_hz=1000000000 loads=65536 reps=3 fresh=0 flush=0 sparse=0 seq=0 cme=0 events=prefetch"
SIZE = "# size=4096 lines=64 backing=hugetlb segments=1 sparse=0"

def rows(header, body):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write("\n".join([META, header, SIZE] + body) + "\n")
    try: return lat_rows(f.name)
    finally: os.unlink(f.name)

fails = 0
def check(name, cond):
    global fails
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails += 1

r = rows(H4, ["dram,4096,repeat,0,65536,2.003,4.01,0.0003,0.0002,0.0002,0.0000,-,-,1.0000", "dram,4096,best,-,-,2.003"])
check("run 4 row, two refused optional events: timing and first counters kept", r[0]["ns"] == 2.003 and r[0]["c1"] == 0.0003 and r[0]["c4"] == 0.0 and r[0]["cov"] == 1.0)
check("refused columns read as None, not 0", r[0]["c5"] is None and r[0]["c6"] is None)
check("best row kept with timing only", r[1]["mode"] == "best" and "c1" not in r[1])

r = rows(H4, ["dram,4096,repeat,0,65536,2.003,-,-,-,-,-,-,-,-", "# perf: counters of the row above are invalid: multiplexed"])
check("invalid row: timing kept, every counter None", r[0]["ns"] == 2.003 and r[0]["cyc"] is None and r[0]["cov"] is None and all(r[0][f"c{i}"] is None for i in range(1, 7)))

r = rows(H4, ["dram,4096,repeat,0,65536,2.003,4.01,0.0003,0.0002,0.0002,4.600e-05,0.0000,0.0000,1.0000"])
check("tiny nonzero count in exponent form parses", abs(r[0]["c4"] - 4.6e-05) < 1e-12 and r[0]["c5"] == 0.0)

r = rows(H3, ["dram,4096,repeat,0,65536,2.003,4.01,0.0003,0.0002,0.0002,1.0000"])
check("run 3 row: three counters and perf_cov", r[0]["c3"] == 0.0002 and r[0]["cov"] == 1.0 and "c4" not in r[0])
r = rows(H2, ["dram,4096,repeat,0,65536,2.003,4.01,0.0003,0.0002,0.0002"])
check("run 2 row: three counters, no perf_cov", r[0]["c3"] == 0.0002 and r[0]["cov"] is None)

try:
    rows(H4, ["dram,4096,repeat,0,65536,2.003,4.01,0.0003,0.0002,0.0002,1.0000"])
    check("truncated row rejected", False)
except AssertionError as e:
    check("truncated row rejected: " + str(e).split(":")[-1].strip()[:40], True)

print("FAIL" if fails else "PASS", fails, "failure(s)")
sys.exit(1 if fails else 0)
