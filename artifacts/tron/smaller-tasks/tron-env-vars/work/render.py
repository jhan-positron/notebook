#!/usr/bin/env python3
"""Render README.environment.md from the checked row files and the prose
template.

Usage: render.py <out.md>
Reads: chunks/index.json, chunks/<id>.final.json (or <id>.rows.json),
       row_overrides.json (optional), template.md
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

work = Path(__file__).resolve().parent
out_path = Path(sys.argv[1])

index = json.loads((work / "chunks" / "index.json").read_text())
overrides = {}
if (work / "row_overrides.json").exists():
    overrides = json.loads((work / "row_overrides.json").read_text())

rows = {}
unchecked = []
for c in index:
    f = work / "chunks" / f"{c['id']}.final.json"
    if not f.exists():
        f = work / "chunks" / f"{c['id']}.rows.json"
        unchecked.append(c["id"])
    data = json.loads(f.read_text())
    for r in data["rows"]:
        r = dict(r)
        r["section"] = c["section"]
        r["chunk"] = c["id"]
        if r["name"] in rows:
            raise SystemExit(f"duplicate row: {r['name']}")
        rows[r["name"]] = r

for name, patch in overrides.items():
    if name not in rows:
        raise SystemExit(f"override for unknown row: {name}")
    rows[name].update(patch)

# Cells from the final audit pass replace the fields that the tables render.
STD = {"Read by": "read_by", "Set by": "who_sets"}
audited = 0
for f in sorted((work / "audit2").glob("[0-9][0-9].json")):
    for a in json.loads(f.read_text()).get("rows", []):
        r = rows.get(a.get("name"))
        cells = a.get("cells") or {}
        if r is None or not cells:
            continue
        audited += 1
        if r["section"] == "external":
            r["defined_by"] = cells.get("Defined by", r.get("defined_by"))
            r["tron_use"] = cells.get("Tron", r.get("tron_use"))
            r["read_by"] = cells.get("Where", r.get("read_by"))
            r["effect"] = cells.get("What Tron does with it", r.get("effect"))
            continue
        for col, field in STD.items():
            if col in cells:
                r[field] = cells[col]
        if "Values and default" in cells:
            r["values"], r["default"] = cells["Values and default"], ""
        if "Effect" in cells:
            r["effect"], r["notes"] = cells["Effect"], ""

# Last corrections, from the audit of the head file.
final_path = work / "final_patches.json"
if final_path.exists():
    for name, patch in json.loads(final_path.read_text()).items():
        rows[name].update(patch)

expected = {n for c in index for n in c["names"]}
missing = sorted(expected - set(rows))
extra = sorted(set(rows) - expected)
if missing or extra:
    raise SystemExit(f"row set mismatch: missing={missing} extra={extra}")

dropped = sorted(n for n, r in rows.items() if r.get("drop"))
live = {n: r for n, r in rows.items() if not r.get("drop")}


def clean(text):
    """Make a field safe for a Markdown table cell."""
    if text is None:
        return ""
    text = str(text).replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s{2,}", " ", text)
    text = text.replace("|", "\\|")
    # The repository writes the project name as "Tron". Variable names such as
    # TRON_LOG_DIR are untouched, because "_" is a word character.
    text = re.sub(r"\bTRON\b", "Tron", text)
    # One spelling of the instance number in paths, as in "How to set a variable".
    text = text.replace("instance-<N>.env", "instance-N.env").replace("/var/run/rinzler/<N>", "/var/run/rinzler/N")
    return text


def join(*parts):
    return " ".join(p for p in (clean(x) for x in parts) if p)


def code(name):
    return f"`{name}`"


def table(header, body_rows):
    if not body_rows:
        return "_No variables._\n"
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for cells in body_rows:
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def by_name(items):
    return sorted(items, key=lambda r: (r["name"].lower(), r["name"]))


def std_table(items, with_for=False, with_setter=True):
    header = ["Variable"]
    if with_for:
        header.append("For")
    header.append("Read by")
    if with_setter:
        header.append("Set by")
    header += ["Values and default", "Effect"]
    body = []
    for r in by_name(items):
        cells = [code(r["name"])]
        if with_for:
            cells.append({"operators": "Operators", "developers": "Developers"}.get(r.get("for", ""), clean(r.get("for", ""))))
        cells.append(clean(r.get("read_by")))
        if with_setter:
            cells.append(clean(r.get("who_sets")))
        cells.append(join(r.get("values"), r.get("default")))
        cells.append(join(r.get("effect"), r.get("notes")))
        body.append(cells)
    return table(header, body)


tables = {}
counts = defaultdict(int)

# --- section 1: running programs, one table per topic
runtime = [r for r in live.values() if r["section"] == "runtime"]
TOPICS = ["system", "weights", "memory", "attention", "generation", "server", "tokenizer", "logging", "stats", "tracing"]
for t in TOPICS:
    tables[f"runtime.{t}"] = std_table([r for r in runtime if r.get("topic") == t], with_for=True, with_setter=False)
bad = sorted(r["name"] for r in runtime if r.get("topic") not in TOPICS)
if bad:
    raise SystemExit(f"runtime rows without a known topic: {bad}")
bad = sorted(r["name"] for r in runtime if r.get("for") not in ("operators", "developers"))
if bad:
    raise SystemExit(f"runtime rows without a known 'for': {bad}")


def grouped(section, groups, fallback):
    items = [r for r in live.values() if r["section"] == section]
    for r in items:
        if r.get("group") not in groups:
            r["group"] = fallback
    for g in groups:
        tables[f"{section}.{g}"] = std_table([r for r in items if r["group"] == g])
    return items


grouped("dispatch", ["dice", "dice-grant", "dice-lsf", "dice-test-hooks", "slice", "wrappers"], "dice")
grouped("tools", ["load-test", "benchmark", "perfetto", "ingest", "coverage", "lint", "hardware-tools", "other"], "other")
grouped("build", ["make", "remote-build", "cmake", "nix", "ingest-build", "packaging"], "make")

# --- tests
tests = [r for r in live.values() if r["section"] == "tests"]
hand = [r for r in tests if r.get("hand_set")]
fixture = [r for r in tests if not r.get("hand_set")]
TEST_GROUPS = ["models", "hardware", "proxy", "tool-tests", "other"]
for r in hand:
    if r.get("group") not in TEST_GROUPS:
        r["group"] = "other"
for g in TEST_GROUPS:
    tables[f"tests.{g}"] = std_table([r for r in hand if r["group"] == g], with_setter=False)


def first_path(text):
    m = re.search(r"`([^`\s]+/[^`\s]+)`", text or "")
    return m.group(1) if m else ""


def name_lists(items, key_of, header):
    groups = defaultdict(list)
    for r in items:
        groups[key_of(r)].append(r["name"])
    body = []
    for key in sorted(groups):
        names = sorted(groups[key], key=lambda n: (n.lower(), n))
        body.append([code(key), ", ".join(code(n) for n in names)])
    return table(header, body)


tables["tests.fixture"] = name_lists(
    fixture,
    lambda r: first_path(r.get("set_in")) or first_path(r.get("read_by")),
    ["Test file", "Variables that it sets for its helper programs"],
)

# --- ci
ci = [r for r in live.values() if r["section"] == "ci"]
SOURCES = ["repository variable", "repository secret", "workflow env", "step env", "runner", "script"]
for r in ci:
    if r.get("source") not in SOURCES:
        raise SystemExit(f"ci row with unknown source: {r['name']} {r.get('source')!r}")
for s in SOURCES:
    items = [r for r in ci if r["source"] == s]
    if s == "step env":
        tables["ci.step-env"] = name_lists(
            items,
            lambda r: first_path(r.get("who_sets")) or first_path(r.get("read_by")),
            ["Workflow or script", "Variables that it sets for its steps"],
        )
    else:
        tables["ci." + s.replace(" ", "-")] = std_table(items)

# --- external
external = [r for r in live.values() if r["section"] == "external"]
EXT_GROUPS = ["os", "github-actions", "build-tools", "python", "ml-libraries", "network", "sanitizers", "lsf", "tracing", "other"]
for r in external:
    if r.get("group") not in EXT_GROUPS:
        r["group"] = "other"
for g in EXT_GROUPS:
    tables[f"external.{g}"] = table(
        ["Variable", "Defined by", "Tron", "Where", "What Tron does with it"],
        [
            [
                code(r["name"]),
                clean(r.get("defined_by")),
                clean(r.get("tron_use")).capitalize(),
                clean(r.get("read_by")),
                clean(r.get("effect")),
            ]
            for r in by_name([x for x in external if x["group"] == g])
        ],
    )

template = (work / "template.md").read_text()


def fill(m):
    key = m.group(1)
    if key not in tables:
        raise SystemExit(f"template asks for unknown table: {key}")
    used.add(key)
    return tables[key].rstrip("\n")


terms_file = work / "extra_terms.md"
terms = terms_file.read_text().rstrip("\n") if terms_file.exists() else ""
template = template.replace("{{terms}}\n", terms + "\n" if terms else "")

used = set()
doc = re.sub(r"\{\{table:([a-z0-9.\-]+)\}\}", fill, template)
unused = sorted(k for k in tables if k not in used and "_No variables._" not in tables[k])
if unused:
    raise SystemExit(f"tables with rows that the template does not place: {unused}")
left = re.findall(r"\{\{(?:table:|terms)[^}]*\}\}", doc)
if left:
    raise SystemExit(f"unfilled placeholders: {left}")

out_path.write_text(doc)

for r in live.values():
    counts[r["section"]] += 1
print(f"wrote {out_path}: {len(doc.splitlines())} lines, {len(doc.encode())} bytes")
print(f"rows: {len(live)} live, {len(dropped)} dropped {dropped}; cells taken from the final audit: {audited}")
print("by section:", dict(counts))
print("empty tables:", sorted(k for k, v in tables.items() if "_No variables._" in v))
if unchecked:
    print("WARNING: chunks rendered from unchecked rows:", unchecked)
