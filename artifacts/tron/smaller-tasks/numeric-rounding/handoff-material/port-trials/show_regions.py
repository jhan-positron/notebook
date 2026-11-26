#!/usr/bin/env python3
"""show_regions.py <file> <max-lines-per-side>: print both sides of each conflict region."""
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
        print(f"--- region {n} at line {i+1}: ours {j-i-1} lines, theirs {k-j-1} lines")
        print("  [ours/HEAD]")
        for l in lines[i+1:j][:maxl]: print("    " + l)
        if j-i-1 > maxl: print(f"    ... ({j-i-1-maxl} more)")
        print("  [theirs/cherry-picked]")
        for l in lines[j+1:k][:maxl]: print("    " + l)
        if k-j-1 > maxl: print(f"    ... ({k-j-1-maxl} more)")
        i = k
    i += 1
