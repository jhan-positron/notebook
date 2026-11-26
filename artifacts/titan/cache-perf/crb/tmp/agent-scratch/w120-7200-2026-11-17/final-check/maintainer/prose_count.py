#!/usr/bin/env python3
"""prose_count.py - run a copy of make_report.py with the output redirected to this folder and print the word count of each prose item.
Usage: python3 prose_count.py [path of the generator]   (default: S/make_report.py). The real report is not touched."""
import os, re, subprocess, sys
S = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
W = S + "/final-check/maintainer"
gen = sys.argv[1] if len(sys.argv) > 1 else S + "/make_report.py"
src = open(gen).read()
out = W + "/work/out.html"
os.makedirs(W + "/work", exist_ok=True)
code = src.replace('OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"', f'OUT = "{out}"')
assert code != src
# keep going after a failed check, so that the word counts are printed (the copy writes only into this folder)
n0 = code.count('    sys.exit(1)\nDATA = ')
assert n0 == 1
code = code.replace('    sys.exit(1)\nDATA = ', '    pass\nDATA = ')
code += '''
print("PROSE ITEMS")
for i, t in enumerate(PROSE):
    n = len([w for w in re.findall(r"\\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)])
    print(f"{i:3d} {n:4d}  " + re.sub(r"\\s+", " ", strip_tags(t)).strip())
print("TOTAL", words_n)
'''
open(W + "/work/gen_copy.py", "w").write(code)
r = subprocess.run([sys.executable, W + "/work/gen_copy.py"], capture_output=True, text=True)
o = r.stdout + r.stderr
i = o.find("PROSE ITEMS")
print("exit status", r.returncode)
print("\n".join(l for l in o[:i if i >= 0 else None].splitlines() if "FAIL" in l or "STOP" in l or "checks pass" in l or l.startswith("wrote")))
print(o[i:] if i >= 0 else "")
