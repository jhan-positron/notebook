#!/usr/bin/env python3
"""Merge the per-area verified inventories and the critic outputs into one
record per variable name, and assign each name to one section of the document.

Usage: merge.py            (reads inventory/, writes merged.json)
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

work = Path(__file__).resolve().parent
inv = work / "inventory"

RUNTIME_AREAS = {"cpp-pos-system", "cpp-tron", "cpp-rinzler-runtron"}

records = {}


def rec(name):
    return records.setdefault(
        name,
        {
            "name": name,
            "entries": [],
            "rederive": None,
            "conflicts": [],
            "set_only_reader": "",
            "stale_docs": [],
            "doc_mentions": [],
        },
    )


for f in sorted((inv / "verified").glob("*.json")):
    d = json.loads(f.read_text())
    for v in d["variables"]:
        e = dict(v)
        e["area"] = f.stem
        rec(v["name"])["entries"].append(e)

for f in sorted((inv / "critic").glob("rederive-*.json")):
    for v in json.loads(f.read_text())["variables"]:
        rec(v["name"])["rederive"] = v

flows = json.loads((inv / "critic" / "flows.json").read_text())
for c in flows["conflicts"]:
    if c["name"] in records:
        records[c["name"]]["conflicts"].append(c["finding"])
for s in flows["set_only_readers"]:
    if s["name"] in records:
        records[s["name"]]["set_only_reader"] = s["read_by"]
for m in flows["missing"]:
    e = dict(m)
    e["area"] = "critic-flows"
    rec(m["name"])["entries"].append(e)

tok = json.loads((inv / "critic" / "token-sweep.json").read_text())
for m in tok["missing"]:
    e = dict(m)
    e["area"] = "critic-token-sweep"
    rec(m["name"])["entries"].append(e)

docs = json.loads((inv / "sweep" / "docs.json").read_text())
for v in docs["variables"]:
    if v["name"] in records:
        records[v["name"]]["doc_mentions"] = v["mentions"]

# ---------------------------------------------------------------- sections


def owner_of(r):
    owners = Counter(e.get("owner", "tron").split(":")[0] for e in r["entries"])
    if owners.get("tron"):
        return "tron"
    return owners.most_common(1)[0][0]


def reader_sites(r):
    return [
        x.get("site", "")
        for e in r["entries"]
        if e.get("role") == "read"
        for x in e.get("readers", [])
    ]


DISPATCH_FILES = (
    "bin/dice",
    "bin/slice",
    "bin/rinzler",
    "bin/runtron",
    "bin/dice_lsf",
    "bin/dice-lsf",
    "bin/dice_",
    "bin/slice_",
)


def section_of(r):
    areas = {e["area"] for e in r["entries"]}
    read_areas = {e["area"] for e in r["entries"] if e.get("role") == "read"}
    auds = Counter(e.get("audience") for e in r["entries"])
    owner = owner_of(r)
    sites = reader_sites(r)
    if read_areas & RUNTIME_AREAS or r["rederive"]:
        return "runtime"
    if owner != "tron":
        return "external"
    if not read_areas:
        return "set-only"
    if any(s.split(":")[0].startswith(DISPATCH_FILES) and "-tests/" not in s for s in sites):
        return "dispatch"
    for a in ("operator", "developer-debug"):
        if auds.get(a):
            return "tools"
    order = ["tooling", "test", "build", "packaging", "ci"]
    present = [a for a in order if auds.get(a)]
    best = max(present, key=lambda a: (auds[a], -order.index(a))) if present else "ci"
    return {"tooling": "tools", "test": "tests", "build": "build", "packaging": "packaging", "ci": "ci"}[best]


for r in records.values():
    r["owner"] = owner_of(r)
    r["read_somewhere"] = any(e.get("role") == "read" for e in r["entries"])
    r["areas"] = sorted({e["area"] for e in r["entries"]})
    r["section"] = section_of(r)

overrides_path = work / "section_overrides.json"
if overrides_path.exists():
    for name, sec in json.loads(overrides_path.read_text()).items():
        if name in records:
            records[name]["section"] = sec
        else:
            print("override for unknown name:", name)

(work / "merged.json").write_text(json.dumps(records, indent=1, sort_keys=True))

by = defaultdict(list)
for n, r in sorted(records.items()):
    by[r["section"]].append(n)
print("total names:", len(records))
for s, names in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f"\n## {s} ({len(names)})")
    print(" ".join(names))
