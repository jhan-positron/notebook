#!/usr/bin/env python3
"""Compare the approved texts P1, P2 and P3 (record section 10.6, state before this step) with the
report lines that now hold them. For each sentence of an approved text it says whether the same
sentence stands in the report line (after removing tags and normalising spaces and 10^n).
Usage: sentences_p.py <record.before.md> <report.html>"""
import re, sys, html
rec = open(sys.argv[1], encoding="utf-8").read().split("\n")
rep = open(sys.argv[2], encoding="utf-8").read().split("\n")


def norm(s):
    s = re.sub(r"<sup>(\d+)</sup>", r"^\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def sentences(s):
    s = norm(s)
    out = re.split(r'(?<=[.?!])\s+(?=[A-Z"0-9])', s)
    return [x.strip() for x in out if x.strip()]


P = {}
for i, line in enumerate(rec):
    m = re.match(r"\*\*(P[123])\. ", line)
    if m:
        k = i + 1
        while not rec[k].startswith("> "): k += 1
        P[m.group(1)] = rec[k][2:]
target = {"P1": [380, 214, 437], "P2": [214, 380], "P3": [289]}
tot = kept = 0
for name in ("P1", "P2", "P3"):
    hay = " ".join(norm(rep[n - 1]) for n in target[name])
    print(f"== {name}: {len(sentences(P[name]))} sentences, compared with report lines {target[name]}")
    for s in sentences(P[name]):
        tot += 1
        if s in hay: kept += 1
        else: print("   not word for word:", s)
print(f"total {tot} sentences, {kept} word for word, {tot - kept} others")
