#!/usr/bin/env python3
"""pr5022-optb-20261124: write the report page of the A/B test from summary.json (made by collect.py).

The page text is the template below. Every number of the charts and tables comes from summary.json, which this
script puts into the page as one JSON object. The prose numbers are checked against that object before writing.
Usage: python3 gen_report.py [output html]
"""
import json
import sys
from pathlib import Path

RES = Path("/home/jhan/workspace/intel-AMX/exec/results/pr5022-optb-20261124")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-optb-ab.html")
TEMPLATE = Path(__file__).with_name("report-template.html")

s = json.loads((RES / "summary.json").read_text())
cells = s["cells"]
runs = [r for c in cells.values() for arm in c["runs"].values() for r in arm.values()]


def pct_range(key):
    v = [float(r[key].rstrip("%")) for r in runs]
    return [min(v), max(v)]


load1 = [float(r["loadavg"].split()[0]) for r in runs]
data = {
    "cells": cells,
    "load": {
        "socket0": pct_range("socket0_busy"),
        "socket1": pct_range("socket1_busy"),
        "ours": pct_range("our_app_cores_busy"),
        "loadavg1": [min(load1), max(load1)],
        "cards_open": sorted({r["our_cards_open"] for r in runs}),
        "hugepages_free_node1": sorted({r["hugepages_free_node1"] for r in runs}),
        "n_runs": len(runs),
    },
}
# The prose of the template states these values. Stop when the data says something else.
g, l = cells["glm-tp4"]["metrics"], cells["l8b-tp4-cpu"]["metrics"]
checks = [
    (f"{g['tps_user']['delta']:+.3f}", "+0.095"), (f"{g['tps_user']['delta_pct']:+.2f}", "+0.16"),
    (f"{l['tps_user']['delta']:+.3f}", "-0.011"), (f"{l['tps_user']['delta_pct']:+.2f}", "-0.01"),
    (f"{g['prefill_s']['delta_pct']:+.2f}", "+0.08"), (f"{l['prefill_s']['delta_pct']:+.2f}", "-0.05"),
    (str(data["load"]["socket0"]), "[42.4, 42.5]"), (str(data["load"]["socket1"]), "[0.0, 0.3]"),
    (str(data["load"]["ours"]), "[0.0, 0.1]"), (str(data["load"]["cards_open"]), "['[]']"),
    (str(len(runs)), "16"),
]
for got, want in checks:
    assert got == want, f"the page text says {want}, the data says {got}"
for m in (g, l):
    for metric in m.values():
        assert metric["verdict"] == "within the band", metric
ids = s["identity.txt"]
assert ids.count("identical") == 4 and "DIFFERENT" not in ids and "identity cells that differ: 0" in ids
assert s["tests.txt"].count("exit code 0: All tests passed") == 6
assert s["chain.done"].strip() == "ok"
page = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", json.dumps(data, sort_keys=True))
OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT} ({len(page)} bytes); load average (1 min) range over the 16 runs: {data['load']['loadavg1']}")
