#!/usr/bin/env python3
"""Read-only: find the first-run findings that match rows F22 to F34 of the record."""
import json, re

S = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc"
d = dict(json.load(open(S + "/check1_results.json")))
items = []
for area in ("report-rename", "brief-language", "answer-facts", "replacement-statements"):
    for f in d["find:" + area]["findings"]:
        items.append((area, f["id"], f["severity"], json.dumps(f)))
    for x in d["verify:" + area]["extra_findings"]:
        items.append((area + " extra", x["id"], x["severity"], json.dumps(x)))
    for v in d["verify:" + area]["verdicts"]:
        items.append((area + " verdict", v["id"], v["verdict"], json.dumps(v)))
keys = {
    "F22": [r"32 to 60 threads"],
    "F23": [r"2\.6 ns"],
    "F24": [r"about 1 memory request", r"About 1 memory request"],
    "F25": [r"Footprints"],
    "F26": [r"\(part 5\)"],
    "F27": [r"DRAM: 148 ns"],
    "F28": [r"repetition 0", r"1342"],
    "F29": [r"29 avg \(85\)"],
    "F30": [r"the same port carries"],
    "F31": [r"1\.8 . 10\^?9", r"1\.8 × 10"],
    "F32": [r"latency times in-flight", r"times the round trip"],
    "F33": [r"no more than one"],
    "F34": [r"text-align", r"flush", r"align"],
}
for k, pats in keys.items():
    hit = sorted(set("%s %s (%s)" % (a, i, s) for a, i, s, t in items if any(re.search(p, t) for p in pats)))
    print(k, "->", hit if hit else "NO first-run finding matches")
