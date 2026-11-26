import re, sys
P = sys.argv[1]; pat = sys.argv[2]; w = int(sys.argv[3]) if len(sys.argv) > 3 else 120
for n, line in enumerate(open(P, encoding="utf-8"), 1):
    for m in re.finditer(pat, line):
        s = max(0, m.start() - w); e = min(len(line), m.end() + w)
        print(n, repr(line[s:e]))
