#!/usr/bin/env python3
"""pr5606-check-20261123: apply one one-line fault of mutations.tsv to h/tron/models/self_attention.hpp.

The fault list is mutations.tsv (tab-separated: id, line number, old text, new text, effect).
A fault is applied only when the old text occurs exactly once on the named line, and the line lies inside a
region that `#ifdef TRON_AMX_DISPATCH` guards (the #else part of such a region does not count).

Usage:
  mutate.py ids <tsv>                 print the fault ids, one per line
  mutate.py effect <tsv> <id>         print the effect text of one fault
  mutate.py apply <tsv> <id> <tree>   apply one fault to <tree>/h/tron/models/self_attention.hpp
"""
import sys

HEADER = "h/tron/models/self_attention.hpp"
GUARD = "#ifdef TRON_AMX_DISPATCH"


def load(tsv):
    rows = {}
    for raw in open(tsv):
        if raw.startswith("#") or not raw.strip():
            continue
        ident, line, old, new, effect = raw.rstrip("\n").split("\t")
        rows[ident] = (int(line), old, new, effect)
    return rows


def guarded_lines(lines):
    """Returns {line number: line number of the #ifdef TRON_AMX_DISPATCH that guards it}."""
    inside = {}
    stack = []  # [is the AMX guard, line number, in the #else part]
    for no, text in enumerate(lines, 1):
        s = text.strip()
        if s.startswith(("#ifdef", "#ifndef", "#if ")) or s == "#if":
            stack.append([s == GUARD, no, False])
        elif s.startswith(("#else", "#elif")):
            if stack:
                stack[-1][2] = True
        elif s.startswith("#endif"):
            if stack:
                stack.pop()
        else:
            for is_guard, start, in_else in stack:
                if is_guard and not in_else:
                    inside[no] = start
    return inside


def main():
    cmd, tsv = sys.argv[1], sys.argv[2]
    rows = load(tsv)
    if cmd == "ids":
        print("\n".join(rows))
        return 0
    ident = sys.argv[3]
    if ident not in rows:
        print(f"unknown fault id {ident}")
        return 2
    line_no, old, new, effect = rows[ident]
    if cmd == "effect":
        print(effect)
        return 0
    path = f"{sys.argv[4]}/{HEADER}"
    lines = open(path).read().split("\n")
    text = lines[line_no - 1]
    if text.count(old) != 1:
        print(f"{ident}: the old text occurs {text.count(old)} time(s) on line {line_no}, wanted 1: {text.strip()!r}")
        return 3
    guard = guarded_lines(lines).get(line_no)
    if guard is None:
        print(f"{ident}: line {line_no} is not inside a region guarded by {GUARD}")
        return 4
    lines[line_no - 1] = text.replace(old, new)
    open(path, "w").write("\n".join(lines))
    print(f"{ident}: line {line_no} of {HEADER} changed; it is inside the {GUARD} region that starts at line {guard}")
    return 0


sys.exit(main())
