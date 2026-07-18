#!/usr/bin/env python3
"""compare_csv.py OLD.csv NEW.csv — keyed compare of checkerboard results-v2
CSVs. Key = (Model,TP,SUP,SUG,SSP,Spec,Instances,Users); skips rows with
Failed Instances > 0; prints per-model geomean NEW/OLD ratios for Parse and
Generate plus the matched-config count, then the gpt-oss rows in detail."""
import csv, sys, math
def load(p):
    d = {}
    with open(p) as f:
        for r in csv.DictReader(f):
            try:
                if int(float(r["Failed Instances"])) > 0: continue
                k = (r["Model"], r["TP"], r["Single User Prompt (tok)"],
                     r["Single User Generate (tok)"], r["Shared System Prompt (tok)"],
                     r["Speculation"], r["Instances"], r["Users"])
                d[k] = (float(r["Parse (tok/s)"]), float(r["Generate (tok/s)"]))
            except (KeyError, ValueError): continue
    return d
old, new = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(old) & set(new))
print(f"matched configs: {len(common)}  (old rows {len(old)}, new rows {len(new)})")
per = {}
for k in common:
    m = f"{k[0]}-tp{k[1]}"
    per.setdefault(m, []).append((old[k], new[k], k))
print(f"{'model':44s} {'n':>3s} {'parse nw/old':>10s} {'gen new/old':>11s}")
for m in sorted(per):
    rows = per[m]
    gp = math.exp(sum(math.log(n[0]/o[0]) for o, n, _ in rows)/len(rows))
    gg = math.exp(sum(math.log(n[1]/o[1]) for o, n, _ in rows)/len(rows))
    print(f"{m:44s} {len(rows):3d} {gp:10.3f} {gg:11.3f}")
print("\ngpt-oss detail (SUP/SUG/SSP/inst/users: old-parse new-parse | old-gen new-gen):")
for m in sorted(per):
    if "gpt-oss" not in m: continue
    for o, n, k in per[m]:
        print(f"  p{k[2]:>5s} g{k[3]:>5s} s{k[4]:>4s} {k[6]}x{k[7]:>2s}u: "
              f"{o[0]:7.1f} {n[0]:7.1f} ({n[0]/o[0]-1:+6.1%}) | "
              f"{o[1]:6.1f} {n[1]:6.1f} ({n[1]/o[1]-1:+6.1%})")
