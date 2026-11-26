#!/usr/bin/env python3
"""Structure checks of GDN/gdn-amx-design.html (read-only). Prints one OK/BAD line per check. Exit code 0 = all OK."""
import html
import re
import sys

s = open(sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html", encoding="utf-8").read()
bad = 0


def check(ok, what):
    global bad
    bad += not ok
    print("OK " if ok else "BAD", what)


check(all(ord(c) < 128 for c in s), "pure ASCII")
n_src = len(re.findall(r'<li id="ref\d+">', s))   # top-level entries of the source list (an entry may hold a nested list)
check([int(x) for x in re.findall(r'<li id="ref(\d+)">', s)] == list(range(1, n_src + 1)), "source entries are numbered in order")
used = {int(x) for grp in re.findall(r"\[((?:Ref\d+(?:, )?)+)\]", s) for x in re.findall(r"Ref(\d+)", grp)}
check(n_src > 0 and used == set(range(1, n_src + 1)), f"{n_src} sources; cited in the body: {sorted(used)}")
check(not re.search(r'<span class="ref"><span class="ref">', s), "no reference mark is wrapped twice")
figs = [int(x) for x in re.findall(r'<figure id="fig(\d+)"', s)]
caps = [int(x) for x in re.findall(r"Figure (\d+)\.", s)]
check(figs == list(range(1, len(figs) + 1)) and caps == figs, f"figure ids {figs}; caption numbers {caps}")
ids = set(re.findall(r'\bid="([^"]+)"', s))
hrefs = re.findall(r'href="#([^"]+)"', s)
check(all(h in ids for h in hrefs), f"{len(hrefs)} internal links, all targets exist")
check("prefers-color-scheme" not in s and "color-scheme: light" in s, "light theme only (no prefers-color-scheme rule)")
check(all(" open" not in d for d in re.findall(r"<details[^>]*>", s)), "the word list is a folded details element")
txt = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style\b.*?</style>", " ", s, flags=re.S)))
for w in ("convoy", "refund", "in disguise", "swept", "ctx"):
    check(not re.search(r"\b" + re.escape(w) + r"\b", txt), f"no occurrence of {w!r}")
check(";" not in txt, "no semicolon in the text")
check(len(re.findall("<script", s)) == 0, "no script tag")
check("<function" not in s and "<lambda" not in s and " object at 0x" not in s, "no Python object text in the markup")
check(set(re.findall(r"<table([^>]*)>", s)) <= {"", ' class="prose"'}, "table tags carry no attribute or class prose only")
# every pattern id is defined once and used at least once (the ids themselves are compared by regen_check.py, which re-runs the generator)
defs = re.findall(r'<pattern id="([^"]+)"', s)
uses = set(re.findall(r'url\(#([^)]+)\)', s))
check(len(defs) == len(set(defs)) and set(defs) <= uses, f"{len(defs)} pattern ids, each defined once and used: {', '.join(defs)}")
sys.exit(1 if bad else 0)
