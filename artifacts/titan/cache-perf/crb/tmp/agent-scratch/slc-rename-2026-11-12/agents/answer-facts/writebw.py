# Per-line counts (long run minus short run) for the cases of writebw.csv. Read only.
import re, sys
f = sys.argv[1]
want = sys.argv[2:]
idle = {}; cur = None; data = {}   # data[(case, len, evset)] = {"bytes":..,"rate":..,"rows":{ev:(count, ns, pct, line)}}
for n, line in enumerate(open(f), 1):
    line = line.rstrip("\n")
    if line.startswith("-- background"):
        cur = "idle"; continue
    m = re.match(r"-- (\S+) (short|long) events (\S+) args (.*)$", line)
    if m:
        cur = (m.group(1), m.group(2), m.group(3)); data[cur] = {"rows": {}, "args": m.group(4), "hdr": n}; continue
    m = re.match(r"^(asm\w+),(\d+),(\d+),(\d+),(\d+),([\d.]+),([\d.]+),", line)
    if m and cur and cur != "idle":
        data[cur]["bytes"] = int(m.group(5)); data[cur]["rate"] = float(m.group(7)); data[cur]["elapsed"] = float(m.group(6)); continue
    p = line.split(",")
    if len(p) >= 5 and p[0].isdigit() and p[1] == "":
        ev = p[2]; ns = int(p[3]); pct = float(p[4])
        if cur == "idle": idle[ev] = (int(p[0]), ns, pct, n)
        elif cur: data[cur]["rows"][ev] = (int(p[0]), ns, pct, n)
bad = [(k, ev, r) for k, d in data.items() for ev, r in d["rows"].items() if r[2] < 100.0]
bad += [("idle", ev, r) for ev, r in idle.items() if r[2] < 100.0]
print("rows below 100 in the whole file:", len(bad))
cases = sorted({k[0] for k in data})
for c in cases:
    if want and c not in want: continue
    sets = sorted({k[2] for k in data if k[0] == c})
    print("==", c, "| args:", data[(c, "long", sets[0])]["args"])
    for s in sets:
        lo, sh = data[(c, "long", s)], data[(c, "short", s)]
        lines = (lo["bytes"] - sh["bytes"]) / 64
        dt_loop = lo["elapsed"] - sh["elapsed"]
        print(f"   set {s}: long rate {lo['rate']:.2f} short rate {sh['rate']:.2f} GB/s; long-short rate {(lo['bytes']-sh['bytes'])/dt_loop/1e9:.2f} GB/s; lines {lines:,.0f}")
        for ev in lo["rows"]:
            d = lo["rows"][ev][0] - sh["rows"][ev][0]
            dt = (lo["rows"][ev][1] - sh["rows"][ev][1]) / 1e9
            idl = idle.get(ev, (0, 1, 0, 0)); idle_rate = idl[0] / (idl[1] / 1e9)
            print(f"      {ev:48s} {d/lines:8.4f} per line; minus idle {(d - idle_rate*dt)/lines:8.4f}; pct {lo['rows'][ev][2]:.2f}/{sh['rows'][ev][2]:.2f}; csv lines {sh['rows'][ev][3]} and {lo['rows'][ev][3]}")
