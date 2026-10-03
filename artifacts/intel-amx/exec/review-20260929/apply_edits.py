#!/usr/bin/env python3
"""Apply the plain-English edits (original -> fix, verbatim) to every string value of the page's data files.

Usage: apply_edits.py edits.json
Writes the data files in place and prints matched / unmatched counts; unmatched edits go to pe/unmatched.json.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = ['report-base.json', 'synth.json', 'testdata-result.json', 'meta.json', 'glossary.json', 'buildtest.json', 'test-table.json']
edits = json.load(open(sys.argv[1]))
if isinstance(edits, dict):
    edits = edits['edits']

docs = {name: json.load(open(HERE / name)) for name in DATA}


def walk(obj, fn):
    if isinstance(obj, dict):
        return {k: walk(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk(v, fn) for v in obj]
    if isinstance(obj, str):
        return fn(obj)
    return obj


matched = []
unmatched = []
for e in edits:
    orig, fix = e['original'], e['fix']
    if not orig or orig == fix:
        continue
    hits = 0

    def fn(s):
        global hits
        if orig in s:
            hits += s.count(orig)
            return s.replace(orig, fix)
        return s

    for name in DATA:
        docs[name] = walk(docs[name], fn)
    (matched if hits else unmatched).append(dict(e, hits=hits))

for name in DATA:
    json.dump(docs[name], open(HERE / name, 'w'), indent=1)
json.dump(unmatched, open(HERE / 'pe2' / 'unmatched.json', 'w'), indent=1)
print(f'edits {len(edits)}: matched {len(matched)}, unmatched {len(unmatched)}')
multi = [m for m in matched if m['hits'] > 1]
print(f'edits that hit more than one place: {len(multi)}')
