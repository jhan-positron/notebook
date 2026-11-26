#!/usr/bin/env python3
"""pr5606-check-20261123: list the failed sections of a Catch2 console log.

Catch2 (the test framework) prints a header before each failure: a line of dashes, the test case name, the
section name (indented), a line of dashes, and the source line. Then it prints "<file>:<line>: FAILED:" with
the failed expression and its expansion. This script prints one line per section that has a failure:
  the section name (first 70 characters), the count of failures, and the first failure (line, expression, values).
Usage: catch-failures.py <log> [<count of sections in the test>]
"""
import re
import sys

log = open(sys.argv[1], errors="replace").read().split("\n")
total = sys.argv[2] if len(sys.argv) > 2 else "?"
DASH = re.compile(r"^-{60,}$")
FAILED = re.compile(r"^(.*?):(\d+): FAILED:\s*$")

sections = {}  # name -> list of failure texts, in order of first appearance
current = "(no section)"
i = 0
while i < len(log):
    if DASH.match(log[i]):
        # header block: lines up to the next dash line
        j = i + 1
        block = []
        while j < len(log) and not DASH.match(log[j]):
            block.append(log[j])
            j += 1
        if j < len(log) and block:
            # the first line that is not indented is the test case name; the indented rest is the section path
            sect = " ".join(x.strip() for x in block[1:] if x.startswith(" "))
            current = sect or "(test case level)"
            i = j + 1
            continue
    m = FAILED.match(log[i])
    if m:
        expr = log[i + 1].strip() if i + 1 < len(log) else ""
        expansion = ""
        for k in range(i + 2, min(i + 8, len(log))):
            if log[k].startswith("with expansion:"):
                expansion = log[k + 1].strip() if k + 1 < len(log) else ""
                break
            if log[k].startswith("due to"):
                expr = (expr + " " + log[k].strip()).strip()
        if log[i + 1].startswith("due to") if i + 1 < len(log) else False:
            expr = log[i + 1].strip()
        sections.setdefault(current, []).append(f"line {m.group(2)}: {expr}" + (f" with values {expansion}" if expansion else ""))
    i += 1

fatal = [x.strip() for x in log if "fatal error condition" in x or "SIGSEGV" in x or "SIGABRT" in x]
print(f"sections with a failure: {len(sections)} of {total}")
for name, fails in sections.items():
    print(f"  [{name[:70]}] failures: {len(fails)}; first: {fails[0]}")
if fatal:
    print(f"  fatal: {fatal[0]}")
