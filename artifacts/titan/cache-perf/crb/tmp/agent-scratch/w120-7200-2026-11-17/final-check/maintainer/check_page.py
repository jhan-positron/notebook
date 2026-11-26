#!/usr/bin/env python3
"""check_page.py - checks of the built page that do not use the generator: reference links, balanced tags, leftover phrases."""
import re, sys
from html.parser import HTMLParser
P = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"
t = open(P, encoding="utf-8").read()
hrefs = set(re.findall(r'href="#(ref\d+)"', t)); ids = set(re.findall(r'<li id="(ref\d+)"', t))
print("reference links:", len(hrefs), "targets:", len(ids), "links without target:", sorted(hrefs - ids), "targets never linked:", sorted(ids - hrefs))
nums = sorted(int(x[3:]) for x in ids); print("reference numbers run from", nums[0], "to", nums[-1], "without a gap:", nums == list(range(1, len(nums) + 1)))
first = []
for m in re.finditer(r'href="#ref(\d+)"', t):
    if int(m.group(1)) not in first: first.append(int(m.group(1)))
print("numbered in the order of first use:", first == sorted(first))
VOID = {"meta", "br", "link", "img", "input", "hr", "circle", "line", "rect", "path", "polygon", "polyline", "ellipse", "use"}
class B(HTMLParser):
    def __init__(s): super().__init__(); s.st = []; s.bad = []
    def handle_starttag(s, tag, a):
        if tag not in VOID: s.st.append(tag)
    def handle_startendtag(s, tag, a): pass
    def handle_endtag(s, tag):
        if tag in VOID: return
        if not s.st or s.st[-1] != tag: s.bad.append((tag, s.st[-3:], s.getpos()))
        else: s.st.pop()
b = B(); b.feed(t)
print("unbalanced tags:", b.bad[:5], "left open:", b.st)
vis = re.sub(r"<style>.*?</style>", " ", t, flags=re.S)
for ph in ("test line", "three ways", "two rules", "Each memory speed has", "each memory speed has", "another load-only loop", "is the cause."):
    print(f"  phrase {ph!r}: {vis.count(ph)} times")
print("page bytes:", len(t.encode()))
