#!/usr/bin/env python3
"""edit.py <file> <old-file> <new-file>: replace the exact text of old-file by new-file in <file>, exactly one match.
   edit.py --lines <file> <first> <last> <new-file> <anchor-first> <anchor-last>: replace lines first..last (1-based,
   inclusive) by new-file after checking that line `first` contains anchor-first and line `last` contains anchor-last."""
import sys, pathlib
if sys.argv[1] == '--lines':
    p = pathlib.Path(sys.argv[2]); first, last = int(sys.argv[3]), int(sys.argv[4])
    new = pathlib.Path(sys.argv[5]).read_text(); a1, a2 = sys.argv[6], sys.argv[7]
    lines = p.read_text().splitlines(keepends=True)
    if a1 not in lines[first - 1]: print(f"FAIL {p}: line {first} is {lines[first-1]!r}, expected anchor {a1!r}"); sys.exit(1)
    if a2 not in lines[last - 1]: print(f"FAIL {p}: line {last} is {lines[last-1]!r}, expected anchor {a2!r}"); sys.exit(1)
    p.write_text(''.join(lines[:first - 1]) + new + ''.join(lines[last:]))
    print(f"ok {p}: lines {first}-{last} ({last - first + 1}) replaced by {new.count(chr(10))} lines")
else:
    p = pathlib.Path(sys.argv[1]); old = pathlib.Path(sys.argv[2]).read_text(); new = pathlib.Path(sys.argv[3]).read_text()
    s = p.read_text(); n = s.count(old)
    if n != 1: print(f"FAIL {p}: {n} matches for {sys.argv[2]}"); sys.exit(1)
    p.write_text(s.replace(old, new)); print(f"ok {p}: {sys.argv[2]}")
