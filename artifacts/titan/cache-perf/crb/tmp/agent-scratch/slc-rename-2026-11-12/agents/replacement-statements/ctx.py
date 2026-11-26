#!/usr/bin/env python3
"""Print every occurrence of a regex in a file with line number and N chars of context."""
import re, sys
path, pat = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
flags = re.I
for ln, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
    for m in re.finditer(pat, line, flags):
        s = max(0, m.start() - n); e = min(len(line), m.end() + n)
        print(f"{ln}: ...{line[s:e].strip()}...")
        print()
