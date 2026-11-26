#!/usr/bin/env python3
"""Mechanical checks of the report against its backup: tag balance, script and style blocks,
ids and links, hunk count, line count, and the figure geometry script."""
import re, subprocess, sys
from html.parser import HTMLParser
R = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
B = "/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-spec-row.html"
G = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/check_geometry.py"
r, b = open(R, encoding="utf-8").read(), open(B, encoding="utf-8").read()
VOID = {"meta", "link", "br", "hr", "img", "input", "col", "wbr", "source", "area", "base", "embed", "track"}
SVGSELF = set()

class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.stack = []; s.bad = []; s.maxul = 0
    def handle_starttag(s, t, a):
        if t in VOID: return
        s.stack.append((t, s.getpos()[0]))
        s.maxul = max(s.maxul, sum(1 for x, _ in s.stack if x == "ul"))
    def handle_startendtag(s, t, a): pass
    def handle_endtag(s, t):
        if t in VOID: return
        if not s.stack or s.stack[-1][0] != t:
            s.bad.append((t, s.getpos()[0], s.stack[-1] if s.stack else None))
            # try to recover: pop until match
            for i in range(len(s.stack) - 1, -1, -1):
                if s.stack[i][0] == t: del s.stack[i:]; break
        else: s.stack.pop()

def balance(txt):
    p = P(); p.feed(txt); p.close(); return p

pr, pb = balance(r), balance(b)
print(f"tag mismatches: report {len(pr.bad)} (open at end {len(pr.stack)}), backup {len(pb.bad)} (open at end {len(pb.stack)}); deepest ul nesting: report {pr.maxul}, backup {pb.maxul}")
for x in pr.bad[:10]: print("   ", x)
blk = lambda t, tag: re.findall(rf"<{tag}\b[^>]*>.*?</{tag}>", t, flags=re.S)
print("script blocks identical:", blk(r, "script") == blk(b, "script"), len(blk(r, "script")), "| style identical:", blk(r, "style") == blk(b, "style"), len(blk(r, "style")))
ids = lambda t: sorted(re.findall(r'\bid="([^"]+)"', t)); hrefs = lambda t: sorted(re.findall(r'\bhref="([^"]+)"', t))
print("ids identical:", ids(r) == ids(b), len(ids(r)), "| hrefs identical:", hrefs(r) == hrefs(b), len(hrefs(r)))
d = subprocess.run(["diff", "-U0", B, R], capture_output=True, text=True).stdout
hunks = [l for l in d.split("\n") if l.startswith("@@")]
print("hunks with diff -U0:", len(hunks)); print("   " + " ".join(h.split(" ")[2] for h in hunks))
d3 = subprocess.run(["diff", "-u", B, R], capture_output=True, text=True).stdout
print("hunks with default context:", sum(1 for l in d3.split("\n") if l.startswith("@@")))
print("lines:", r.count("\n"), "| backup:", b.count("\n"))
g = subprocess.run([sys.executable, G, R, "6"], capture_output=True, text=True)
print("geometry:", [l for l in g.stdout.split("\n") if "RESULT" in l], g.stderr[-200:])
# round-1 baseline of the reviewer
try:
    d1 = subprocess.run(["diff", "-U0", "/tmp/crb-review-round1.html", R], capture_output=True, text=True).stdout
    h1 = [l.split(" ")[2] for l in d1.split("\n") if l.startswith("@@")]
    print("hunks against the round-1 state:", len(h1), " ".join(h1))
except Exception as e: print("round-1 baseline:", e)
