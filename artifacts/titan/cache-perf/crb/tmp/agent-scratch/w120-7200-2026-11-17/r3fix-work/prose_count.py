#!/usr/bin/env python3
"""prose_count.py - runs make_report.py with its output file moved to r3fix-work, and prints the word count of each prose unit."""
import io, re, sys, contextlib
S = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
src = open(S + "/make_report.py").read()
src = src.replace('OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"', f'OUT = "{S}/r3fix-work/trial.html"')
assert "r3fix-work/trial.html" in src
g = {"__name__": "__main__"}
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        exec(compile(src, "make_report.py", "exec"), g)
except SystemExit as e:
    print("exit", e.code)
tot = 0
for t in g["PROSE"]:
    txt = re.sub(r"\s+", " ", g["strip_tags"](t)).strip()
    n = len([w for w in re.findall(r"\S+", txt) if re.search(r"[A-Za-z0-9]", w)])
    tot += n
    print(f"{n:4d}  {txt[:230]}")
print("total", tot)
