# Search every csv under results/ for runs with 2 threads and a write kernel at a DRAM-size buffer (>= 256 MiB),
# and print the case header that precedes each, to see whether any run put two writers on non-partner cores.
import os, re
root = "/home/jhan/workspace/titan/cache-perf/crb/results"
hits = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        if not f.endswith(".csv"): continue
        p = os.path.join(dp, f)
        try: L = open(p, errors="replace").read().split("\n")
        except Exception as e: print("skip", p, e); continue
        last_hdr = None
        for n, line in enumerate(L, 1):
            if line.startswith("--"): last_hdr = (n, line)
            m = re.match(r"^(write|asmwrite),(\d+),(\d+),best,,,([\d.]+)", line)
            if m and int(m.group(2)) == 2 and int(m.group(3)) >= 268435456:
                hits.append((p.replace(root + "/", ""), n, line, last_hdr))
            m = re.match(r"^(write|asmwrite),(\d+),(\d+),best,,,([\d.]+)", line)
            if m and int(m.group(2)) in (2,) and int(m.group(3)) == 8388608:
                hits.append((p.replace(root + "/", ""), n, line, last_hdr))
for h in hits: print(h)
print(len(hits), "rows")
