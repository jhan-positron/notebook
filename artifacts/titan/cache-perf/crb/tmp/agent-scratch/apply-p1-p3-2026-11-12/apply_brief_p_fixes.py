#!/usr/bin/env python3
"""Fixes of the brief after the check of the second step of 2026-11-12 (check3).
  - line 166 (claims-X4, language-render-13): the date of the brief is a UTC date, and the line now says so
  - line 180 (claims-11): the shared port is an inference, as the report now says
  - line 181 (language-render-X2): "mesh cycles" was not defined in the brief
  - line 181 (numbers-writes-6, claims-10, language-render-4): the hypothesis gets its test
Usage: apply_brief_p_fixes.py <make-brief.py> [--write]"""
import sys
P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0


def sub(k, old, new, braces=False):
    global n
    assert L[k - 1].count(old) == 1, (k, L[k - 1].count(old), old[:70])
    assert "\n" not in new and (braces or ("{" not in new and "}" not in new))   # the line is part of an f-string
    L[k - 1] = L[k - 1].replace(old, new); n += 1


sub(166, "Brief generated {today}.</p>", "Brief generated {today} (UTC).</p>", braces=True)
sub(180, "Pair port: cores 2k and 2k+1 share one crosspoint port. Two partner cores",
    "Pair port: cores 2k and 2k+1 share one crosspoint port (inferred from two timing tests and the mesh map, not read from hardware). Two partner cores")
sub(181, "waited for the receiver in about 0.001 % of the mesh cycles.", "waited for the receiver in about 0.001 % of the cycles of the mesh clock (2.0 GHz).")
sub(181, "Hypothesis, not tested: the core keeps only a fixed number of writes unfinished at a time. At 1 GiB",
    "Hypothesis, not tested: the core keeps only a fixed number of writes unfinished at a time. The test is the write loop run on every core in turn. "
    "It was not run. At 1 GiB")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
