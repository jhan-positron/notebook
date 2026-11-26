#!/usr/bin/env python3
"""Own parse of writepath.csv (part 5). Read only.
For each case and event set: long run minus short run of each event, with csv line numbers.
Also the loop rate of every run (short and long), with per-thread min and max."""
import re, sys, collections
F = "/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T211150Z/writepath.csv"
row = re.compile(r"^(\d+),,(.+/),(\d+),(\d+\.\d+),,$")
bw = re.compile(r"^(asm\w+),(\d+),(\d+),(\d+),(\d+),([\d.]+),([\d.]+),([\d.]+),([\d.]+),([\d.]+)$")
hdr = re.compile(r"^-- (\S+) (short|long) set (\S+) events (\S+) args (.*)$")
cur = None
cnt = collections.OrderedDict()   # (case,set,len) -> {event: (count, ns, lineno, pct)}
runs = collections.OrderedDict()  # (case,set,len) -> (bytes, elapsed, agg, min, max, lineno)
args = {}
pcts = collections.Counter()
nrows = 0
for n, line in enumerate(open(F), 1):
    line = line.rstrip("\n")
    m = hdr.match(line)
    if m:
        cur = (m.group(1), m.group(3), m.group(2)); cnt[cur] = collections.OrderedDict(); args[m.group(1)] = m.group(5); continue
    if line.startswith("-- idle") or line.startswith("-- background"):
        mi = re.match(r"-- idle set (\S+) events", line)
        cur = ("idle", mi.group(1), "long") if mi else None
        if cur: cnt[cur] = collections.OrderedDict()
        continue
    m = row.match(line)
    if m:
        nrows += 1; pcts[m.group(4)] += 1
        if cur: cnt[cur][m.group(2)] = (int(m.group(1)), int(m.group(3)), n, m.group(4))
        continue
    m = bw.match(line)
    if m and cur:
        runs[cur] = (int(m.group(5)), float(m.group(6)), float(m.group(7)), float(m.group(8)), float(m.group(9)), n)
print("perf rows:", nrows, "percent-running values:", dict(pcts))
cases = ["w8M-c2", "w1G-c2", "w8M-c2c3", "w8M-c2c4", "w8M-c2c4c6c8", "r8M-c2"]
sets = ["occw", "occa", "xpdat", "xpstall", "xpport", "xpmix", "core1", "core2", "core3"]
print()
for c in cases:
    print("==", c, "| args:", args[c])
    longr = [(runs[(c, s, "long")][2], runs[(c, s, "long")][5], s) for s in sets]
    shortr = [(runs[(c, s, "short")][2], runs[(c, s, "short")][5], s) for s in sets]
    print("   long runs GB/s :", ", ".join(f"{r:.2f}(L{ln},{s})" for r, ln, s in longr))
    print("   short runs GB/s:", ", ".join(f"{r:.2f}(L{ln},{s})" for r, ln, s in shortr))
    lo = min(r for r, _, _ in longr); hi = max(r for r, _, _ in longr)
    nthreads = int(re.search(r"--threads (\d+)", args[c]).group(1))
    print(f"   long range {lo:.2f} to {hi:.2f}; per writer {lo/nthreads:.2f} to {hi/nthreads:.2f}")
    pm = [(runs[(c, s, 'long')][3], runs[(c, s, 'long')][4]) for s in sets]
    print("   per-thread min/max of long runs:", ", ".join(f"{a:.2f}/{b:.2f}" for a, b in pm))
    for s in sets:
        L, S = cnt[(c, s, "long")], cnt[(c, s, "short")]
        bl, bs = runs[(c, s, "long")], runs[(c, s, "short")]
        lines = (bl[0] - bs[0]) / 64
        for ev in L:
            d = L[ev][0] - S[ev][0]; t = (L[ev][1] - S[ev][1]) / 1e9
            short = ev.replace("arm_cmn_", "cmn").replace("armv8_pmuv3_0/", "core/").replace(",bynodeid=1,nodeid=0x98", "@98")
            print(f"   {s:8s} {short:42s} d={d:>14,d} t={t:.4f}s  /s={d/t:.4e}  /line={d/lines:.4f}  (L{S[ev][2]} {S[ev][0]}, L{L[ev][2]} {L[ev][0]})")
    print()
