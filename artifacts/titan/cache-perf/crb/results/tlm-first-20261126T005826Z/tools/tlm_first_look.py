#!/usr/bin/env python3
"""First look at the outputs of the CRB telemetry session of 2026-11-26.

usage: python3 -I tlm_first_look.py SESSION_FOLDER
Reads only. Prints: the metrics of the atx summary (5 s collection on an idle
machine), and the interrupt lines that changed between the two snapshots.
"""
import re
import sys
from pathlib import Path

sess = Path(sys.argv[1])


def read_summary(path):
    """Return rows (metric, unit, target, min, max, avg, twa, count)."""
    rows, metric, state = [], None, None
    for raw in path.read_text().splitlines():
        line = raw.rstrip("\r")
        m = re.match(r"^Metric: (\S+) - (.*) \(([^)]*)\)$", line)
        if m:
            metric, state = (m.group(1), m.group(3)), None
            continue
        if line.startswith("Summary Statistics"):
            state = "header"
            continue
        if state == "header":
            if line.startswith("Target,"):
                if line != "Target,Min,Max,Average,Time Weighted Average,Count":
                    raise SystemExit(f"unexpected header: {line!r}")
                state = "rows"
            continue
        if state == "rows":
            if not line.strip():
                state = None
                continue
            f = line.split(",")
            rows.append((metric[0], metric[1], f[0], float(f[1]), float(f[2]),
                         float(f[3]), float(f[4]), int(f[5])))
    return rows


rows = read_summary(sess / "atx-trial-1" / "atx_summary.csv")
names = sorted({r[0] for r in rows})
print(f"atx summary: {len(rows)} rows, {len(names)} metric names, "
      f"targets: {sorted({r[2] for r in rows})}")
units = {}
for r in rows:
    units.setdefault(r[1], 0)
    units[r[1]] += 1
print("rows per unit:", dict(sorted(units.items())))
counts = sorted({r[7] for r in rows})
print("sample counts per row:", counts)


def family(name):
    return re.sub(r"\d+", "N", name)


fam = {}
for r in rows:
    fam.setdefault((family(r[0]), r[1]), []).append(r)
print("\nfamily (digits replaced by N), unit, rows, lowest min, highest max, "
      "sum of averages, mean of averages")
for (f, u), rs in sorted(fam.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    avgs = [x[5] for x in rs]
    print(f"  {f:22s} {u:8s} {len(rs):4d}  {min(x[3] for x in rs):9.2f} "
          f"{max(x[4] for x in rs):9.2f}  {sum(avgs):10.2f} {sum(avgs)/len(avgs):9.2f}")

print("\npower rows (Watts), average over the 5 s:")
tot = 0.0
for r in sorted(rows):
    if r[1] == "Watts":
        print(f"  {r[0]:22s} {r[2]:22s} min {r[3]:8.2f} max {r[4]:8.2f} avg {r[5]:8.2f}")
        tot += r[5]
print(f"  sum of the power averages: {tot:.2f} W")


def irq_totals(path):
    out = {}
    lines = path.read_text().splitlines()
    ncpu = len(lines[0].split())
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.split()
        nums = []
        for p in parts[:ncpu]:
            if p.isdigit():
                nums.append(int(p))
            else:
                break
        out[key.strip()] = (sum(nums), " ".join(parts[len(nums):]))
    return out


t0 = irq_totals(sess / "irq-t0.txt")
t1 = irq_totals(sess / "irq-t1.txt")
diff = []
for k, (v1, desc) in t1.items():
    v0 = t0.get(k, (0, ""))[0]
    if v1 != v0:
        diff.append((v1 - v0, k, desc))
diff.sort(reverse=True)
print(f"\ninterrupt lines that changed between the two snapshots: {len(diff)}")
for d, k, desc in diff[:12]:
    print(f"  {d:8d}  {k:>6s}  {desc[:70]}")
named = [(k, v, d) for k, (v, d) in t1.items()
         if re.search(r"scmi|pcc|mbox|mailbox|mhu", d, re.I)]
print("interrupt lines with scmi, pcc, mbox, mailbox or mhu in the name:")
for k, v, d in named:
    print(f"  {k:>6s} total at end {v:10d}  change {v - t0.get(k, (0, ''))[0]:6d}  {d[:70]}")
if not named:
    print("  none")
