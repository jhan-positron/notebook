#!/usr/bin/env python3
"""Check the rows of one audit output file against the house rules of
README.env-vars.md.

Usage: rowcheck.py <audit2/NN.json>
Prints one line per problem. Prints "OK" when no row breaks a rule.
"""
import json
import re
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
out = Path(sys.argv[1])
chunk_id = out.stem
spec = json.loads((work / "audit2" / f"{chunk_id}.in.json").read_text())
data = json.loads(out.read_text())

LIMIT = 1000
BRITISH = re.compile(
    r"\b(behaviour|colour|favour|honour|optimis\w*|recognis\w*|initialis\w*|organis\w*|"
    r"normalis\w*|serialis\w*|centre|grey|catalogue|licence|cancelled|labelled)\b",
    re.I,
)
problems = []
want = {r["name"]: r for r in spec["rows"]}
got = {r.get("name"): r for r in data.get("rows", [])}

for name in want:
    if name not in got:
        problems.append(f"{name}: row is missing from the output")
for name in got:
    if name not in want:
        problems.append(f"{name}: not a row of this chunk")

for name, r in got.items():
    if name not in want:
        continue
    cols = want[name]["columns"]
    cells = r.get("cells") or {}
    if r.get("verdict") not in ("correct", "imprecise", "wrong"):
        problems.append(f"{name}: verdict must be correct, imprecise or wrong")
    for c in cols:
        if c in ("Variable",):
            continue
        if c not in cells:
            problems.append(f"{name}: cell '{c}' is missing")
    for c in cells:
        if c not in cols:
            problems.append(f"{name}: unknown cell '{c}'")
    line = "| `" + name + "` | " + " | ".join(str(cells.get(c, "")) for c in cols if c != "Variable") + " |"
    if len(line) > LIMIT:
        problems.append(f"{name}: row has {len(line)} characters; the limit is {LIMIT}")
    for c, text in cells.items():
        text = str(text)
        where = f"{name} / {c}"
        if "|" in text or "\n" in text:
            problems.append(f"{where}: contains '|' or a line break")
        plain = re.sub(r"`[^`]*`", "``", text)  # text outside code spans
        if re.search(r"\band \d+ more\b", text):
            problems.append(f"{where}: a count of files ('and N more'); write 'and other files'")
        if re.search(r"\b(source )?comments? (says?|calls?|states?|explains?|notes?)\b", plain, re.I):
            problems.append(f"{where}: a sentence about a source comment; state the behaviour or delete it")
        if re.search(r"\bTRON\b", plain):
            problems.append(f"{where}: write 'Tron', not 'TRON', for the project name")
        m = BRITISH.search(plain)
        if m:
            problems.append(f"{where}: British spelling '{m.group(0)}'; the repository uses American spelling")
        if re.search(r"\bflags?\b", plain, re.I):
            problems.append(f"{where}: 'flag'; write 'command-line option' or 'option'")
        if re.search(r"[A-Za-z0-9_/.-]+\.(cpp|hpp|py|sh|yml|yaml|rs|c|h|nix|cmake|md):\d+", text):
            problems.append(f"{where}: a line number; rows hold no line numbers")
        if re.search(r"\b(typically|usually|normally|probably|often)\b", plain, re.I):
            problems.append(f"{where}: a vague word (typically, usually, normally, probably, often)")
        if ";" in plain:
            problems.append(f"{where}: a semicolon outside code; split the sentence")
    if "For" in cols and str(cells.get("For", "")) != want[name]["cells"]["For"]:
        problems.append(f"{name}: do not change the For cell; report a doubt in 'problems'")
    if "Values and default" in cols:
        v = str(cells.get("Values and default", ""))
        if want[name]["cells"].get("Values and default") and "Unset:" not in v:
            problems.append(f"{name} / Values and default: must say what happens when unset, after 'Unset:'")

if problems:
    print(f"{len(problems)} problem(s):")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("OK")
