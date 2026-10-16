# usage: python3 -I edit.py <file> <spec.py>
# spec defines EDITS = [(old, new), ...] (each old occurs exactly once) and/or
# RANGES = [(start_marker, end_marker, new), ...]: text from start_marker (inclusive)
# up to end_marker (exclusive) is replaced by new; both markers occur exactly once.
import sys, runpy
path, spec = sys.argv[1], sys.argv[2]
g = runpy.run_path(spec)
s = open(path, encoding="utf-8").read()
for start, end, new in g.get("RANGES", []):
    for m in (start, end):
        n = s.count(m)
        if n != 1:
            sys.exit(f"{path}: marker expected once, found {n}:\n{m[:200]}")
    i, j = s.index(start), s.index(end)
    if j < i:
        sys.exit(f"{path}: end marker before start marker:\n{start[:100]}")
    s = s[:i] + new + s[j:]
for old, new in g.get("EDITS", []):
    n = s.count(old)
    if n != 1:
        sys.exit(f"{path}: expected 1 occurrence, found {n}:\n{old[:200]}")
    s = s.replace(old, new)
open(path, "w", encoding="utf-8").write(s)
print(f"{path}: {len(g.get('RANGES', []))} ranges, {len(g.get('EDITS', []))} edits applied")
