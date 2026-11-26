# Lists every run of writepath.csv: case, short/long, event set, loop bytes, elapsed, rate, and the perf rows with column 5.
import re, sys
f = sys.argv[1]
case = None
runs = []   # (case, len, set, line_no, bytes, elapsed, rate)
rows = []   # (case, len, set, line_no, count, event, ns, pct)
below100 = []
for n, line in enumerate(open(f), 1):
    line = line.rstrip("\n")
    m = re.match(r"-- (\S+) (short|long) set (\S+) events", line)
    if m:
        case = (m.group(1), m.group(2), m.group(3)); continue
    m = re.match(r"-- idle set (\S+) events", line)
    if m:
        case = ("idle", "idle", m.group(1)); continue
    if line.startswith("--"):
        case = None; continue
    m = re.match(r"^(asm\w+),(\d+),(\d+),(\d+),(\d+),([\d.]+),([\d.]+),", line)
    if m and case:
        runs.append((case, n, int(m.group(5)), float(m.group(6)), float(m.group(7)), int(m.group(2)), int(m.group(3))))
        continue
    p = line.split(",")
    if len(p) >= 5 and p[0].isdigit() and p[1] == "":
        # event names can contain commas
        # find fields from the right: ..., ns, pct, '', ''
        pct = p[-3]; ns = p[-4]; ev = ",".join(p[2:-4])
        rows.append((case, n, int(p[0]), ev, int(ns), float(pct)))
        if float(pct) < 100.0:
            below100.append((case, n, ev, pct))
print("perf rows:", len(rows), " rows below 100:", len(below100))
for b in below100[:20]: print("  BELOW 100:", b)
want = sys.argv[2:] or None
for r in runs:
    if want and r[0][0] not in want: continue
    print(f"{r[0][0]:14s} {r[0][1]:5s} {r[0][2]:8s} line {r[1]:5d} bytes {r[2]:>15,d} elapsed {r[3]:.4f} rate {r[4]:6.2f} threads {r[5]} bytes_per_thread {r[6]}")
