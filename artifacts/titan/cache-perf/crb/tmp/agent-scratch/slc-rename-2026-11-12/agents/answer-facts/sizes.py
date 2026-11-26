import re, sys
P = "/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html"
for n, line in enumerate(open(P, encoding="utf-8"), 1):
    if n > 425: break
    for m in re.finditer(r"(8 MiB|1 GiB)", line):
        s = max(0, m.start() - 70); e = min(len(line), m.end() + 50)
        print(n, repr(line[s:e]))
