#!/usr/bin/env python3
"""Scan every file under results/ for bandwidth rows. Read only.
Prints, for chosen (threads, bytes) combinations, every 'best' row and every repetition row with file, line and
the last '-- ' header line before it (which holds the CPUs)."""
import os, re, sys, collections
R = "/home/jhan/workspace/titan/cache-perf/crb/results"
rowre = re.compile(r"^(read|write|copy|asmread|asmwrite|asmcopy),(\d+),(\d+),(\w+),(\d*),([\d.]*),([\d.]+),([\d.]*),([\d.]*),([\d.]*)")
want_threads = set(int(x) for x in sys.argv[1].split(",")) if len(sys.argv) > 1 else {1, 2, 4}
want_bytes = set(int(x) for x in sys.argv[2].split(",")) if len(sys.argv) > 2 else {8388608, 1073741824}
kernels = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
nfiles = 0; nrows = 0
combos = collections.Counter()
for dp, dn, fn in sorted(os.walk(R)):
    for f in sorted(fn):
        p = os.path.join(dp, f); nfiles += 1
        try:
            lines = open(p, errors="replace").read().split("\n")
        except Exception as e:
            print("cannot read", p, e); continue
        hdr = ""
        for n, line in enumerate(lines, 1):
            if line.startswith("-- "): hdr = line[:150]; continue
            m = rowre.match(line)
            if not m: continue
            nrows += 1
            k, t, b, rep = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            combos[(k, t, b)] += 1
            if t in want_threads and b in want_bytes and (kernels is None or k in kernels):
                print(f"{os.path.relpath(p, R)}:{n}: {k},{t},{b},{rep} agg={m.group(7)} min={m.group(8)} max={m.group(9)} | {hdr}")
print("files scanned:", nfiles, "bandwidth rows:", nrows, file=sys.stderr)
if os.environ.get("COMBOS"):
    for (k, t, b), c in sorted(combos.items(), key=lambda x: (x[0][2], x[0][1], x[0][0])):
        print(f"   combo kernel={k} threads={t} bytes={b} rows={c}", file=sys.stderr)
