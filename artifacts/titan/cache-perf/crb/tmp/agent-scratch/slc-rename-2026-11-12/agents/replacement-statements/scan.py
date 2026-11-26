#!/usr/bin/env python3
"""Scan every file under results/ for bandwidth rows with 1, 2 or 4 threads and a buffer of 8 MiB or 1 GiB.
Read only. Prints file, csv line, last '--' header, kernel, threads, bytes, rep, GB/s."""
import os, re, sys
ROOT = "/home/jhan/workspace/titan/cache-perf/crb/results"
want_bytes = {8388608: "8M", 1073741824: "1G"}
rowre = re.compile(r"^(read|write|copy|asmread|asmwrite|asmcopy),(\d+),(\d+),(\w+),(\d*),([\d.]*),([\d.]+)")
only_best = "--all" not in sys.argv
maxthreads = 4
for dp, dn, fn in sorted(os.walk(ROOT)):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        except Exception as e:
            continue
        hdr = ""
        for n, line in enumerate(lines, 1):
            if line.startswith("-- ") or line.startswith("== "):
                hdr = line[:150]
            m = rowre.match(line)
            if not m: continue
            k, t, b, rep, tb, el, g = m.groups()
            t = int(t); b = int(b)
            if b not in want_bytes or t > maxthreads: continue
            if only_best and rep != "best": continue
            print(f"{os.path.relpath(p, ROOT)}:{n}: [{hdr}] {k} threads={t} {want_bytes[b]} rep={rep} {g}")
