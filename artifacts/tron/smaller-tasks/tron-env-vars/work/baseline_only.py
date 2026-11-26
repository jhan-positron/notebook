#!/usr/bin/env python3
"""Print the names that the regular-expression scan found in one area's files
but that the area's sweep inventory does not list.

Usage: baseline_only.py <area>
Reads:  areas/<area>.files.txt, baseline.json, inventory/sweep/<area>.json
"""
import json
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
area = sys.argv[1]

files = set((work / "areas" / f"{area}.files.txt").read_text().split())
baseline = json.loads((work / "baseline.json").read_text())["names"]
sweep = json.loads((work / "inventory" / "sweep" / f"{area}.json").read_text())
have = {v["name"] for v in sweep.get("variables", [])}

rows = []
for name, roles in sorted(baseline.items()):
    sites = {
        role: [s for s in roles[role] if s.rsplit(":", 1)[0] in files]
        for role in ("read", "set")
    }
    if not sites["read"] and not sites["set"]:
        continue
    if name in have:
        continue
    rows.append((name, sites))

print(f"{len(rows)} scan names in area '{area}' are absent from the sweep inventory")
for name, sites in rows:
    read = ", ".join(sites["read"][:4]) or "-"
    setter = ", ".join(sites["set"][:4]) or "-"
    print(f"{name}\tread: {read}\tset: {setter}")
