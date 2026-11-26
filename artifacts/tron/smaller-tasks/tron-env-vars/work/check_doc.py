#!/usr/bin/env python3
"""Deterministic checks of the rendered document against the checkout.

Usage: check_doc.py <checkout> <README.environment.md>

1. Every name that the regular-expression scan found (baseline.json) has a row,
   or a verifier rejected it with a reason.
2. Every name in the document occurs in a tracked file of the checkout.
3. Every repository path that the document names exists in the checkout.
4. Every evidence quote of every row is in the cited file near the cited line.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
root = Path(sys.argv[1])
doc_path = Path(sys.argv[2])
doc = doc_path.read_text()

tracked = set(
    subprocess.run(["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True).stdout.splitlines()
)
dirs = set()
for f in tracked:
    parts = f.split("/")
    for i in range(1, len(parts)):
        dirs.add("/".join(parts[:i]))

doc_names = re.findall(r"^\| `([A-Za-z_][A-Za-z0-9_]*)` \|", doc, flags=re.M)
# Sections 4.6 and 6.4 list several names in one row, keyed by a file path.
in_list = False
for line in doc.splitlines():
    if line.startswith(("| Test file |", "| Workflow or script |")):
        in_list = True
    elif not line.startswith("|"):
        in_list = False
    elif in_list and line.startswith("| `"):
        doc_names += re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", line.split(" | ", 1)[1])
dups = sorted({n for n in doc_names if doc_names.count(n) > 1})
names = set(doc_names)
print(f"rows in document: {len(doc_names)}; distinct names: {len(names)}; duplicate rows: {dups}")

# 1. baseline coverage
baseline = json.loads((work / "baseline.json").read_text())["names"]
rejected = {}
for f in (work / "inventory" / "verified").glob("*.json"):
    for r in json.loads(f.read_text()).get("rejected", []):
        for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", r.get("name", "")):
            rejected.setdefault(n, r.get("reason", ""))
absent = sorted(n for n in baseline if n not in names)
unexplained = [n for n in absent if n not in rejected]
print(f"1. scan names: {len(baseline)}; with a row: {len(baseline) - len(absent)}; "
      f"rejected by a verifier with a reason: {len(absent) - len(unexplained)}; unexplained: {len(unexplained)}")
for n in unexplained:
    v = baseline[n]
    print("   UNEXPLAINED", n, (v["read"] + v["set"])[:3])

# 2. names occur in the checkout
missing = []
for n in sorted(names):
    r = subprocess.run(["git", "-C", str(root), "grep", "-l", "-w", "-F", "-e", n, "--", "."], capture_output=True, text=True)
    files = [f for f in r.stdout.splitlines() if f not in ("README.environment.md", "README.env-vars.md")]
    if not files:
        missing.append(n)
print(f"2. names that occur in no tracked file: {len(missing)} {missing}")

# 3. repository paths named in the document exist
paths = set()
for m in re.finditer(r"`([^`\s]+)`", doc):
    p = m.group(1).rstrip(".,:;)")
    if "/" not in p or p.startswith(("/", "$", "<", "-", "~", "http", "refs/")):
        continue
    if re.search(r"[<>*{}$=|\\]", p):
        continue
    paths.add(p)
for m in re.finditer(r"\]\(([^)#]+)\)", doc):
    paths.add(m.group(1))
bad_paths = sorted(p for p in paths if p.rstrip("/") not in tracked and p.rstrip("/") not in dirs)
print(f"3. path-like names checked: {len(paths)}; not in the checkout: {len(bad_paths)}")
for p in bad_paths:
    print("   NOT A TRACKED PATH", p)

# 4. evidence quotes
index = json.loads((work / "chunks" / "index.json").read_text())
total = ok = 0
bad_ev = []
cache = {}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


for c in index:
    for r in json.loads((work / "chunks" / f"{c['id']}.final.json").read_text())["rows"]:
        for e in r.get("evidence", []) or []:
            total += 1
            site = e.get("site", "")
            m = re.match(r"(.+?):(\d+)", site)
            if not m or m.group(1) not in tracked:
                bad_ev.append((r["name"], site, "no such file"))
                continue
            f, line = m.group(1), int(m.group(2))
            if f not in cache:
                cache[f] = (root / f).read_text("utf-8", "replace").splitlines()
            lines = cache[f]
            window = norm(" ".join(lines[max(0, line - 6): line + 5]))
            q = norm(e.get("quote", ""))
            if q and (q in window or q[:60] in window):
                ok += 1
            else:
                bad_ev.append((r["name"], site, q[:70]))
print(f"4. evidence quotes: {total}; found within 5 lines of the cited line: {ok}; not found: {len(bad_ev)}")
for b in bad_ev[:40]:
    print("   EVIDENCE", b)
