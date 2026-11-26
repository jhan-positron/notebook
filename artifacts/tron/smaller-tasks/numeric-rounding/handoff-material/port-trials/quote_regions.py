#!/usr/bin/env python3
"""quote_regions.py <file> <max-lines> : Markdown quotes of both sides of each conflict region."""
import sys
path, maxl = sys.argv[1], int(sys.argv[2])
lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
i = 0; n = 0
while i < len(lines):
    if lines[i].startswith('<<<<<<< '):
        n += 1
        j = i
        while not lines[j].startswith('======='): j += 1
        k = j
        while not lines[k].startswith('>>>>>>> '): k += 1
        ours, theirs = lines[i+1:j], lines[j+1:k]
        print(f"**Region {n}** (merged file lines {i+1}-{k+1}; our side {len(ours)} lines, PR #5571 side {len(theirs)} lines)\n")
        for label, side in (("Our side (HEAD = 775bba7661)", ours), ("PR #5571 side (59429b0955)", theirs)):
            print(f"{label}:\n")
            print("```cpp")
            if not side: print("(empty)")
            for l in side[:maxl]: print(l)
            if len(side) > maxl: print(f"... ({len(side)-maxl} more lines not quoted)")
            print("```\n")
        i = k
    i += 1
