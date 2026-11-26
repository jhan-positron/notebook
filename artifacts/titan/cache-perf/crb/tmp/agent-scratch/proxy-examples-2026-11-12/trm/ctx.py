# Print lines matching a regex with N lines of context, for given pages (1-based PDF index).
import re, sys, os
d, pat, n = sys.argv[1], re.compile(sys.argv[2], re.I), int(sys.argv[3])
for pg in sys.argv[4:]:
    L = open(os.path.join(d, "p%04d.txt" % int(pg))).read().split("\n")
    keep = set()
    for i, l in enumerate(L):
        if pat.search(l): keep.update(range(max(0, i-n), min(len(L), i+n+1)))
    if keep:
        print("#### PAGE", pg)
        prev = None
        for i in sorted(keep):
            if prev is not None and i != prev+1: print("   ...")
            print(L[i]); prev = i
