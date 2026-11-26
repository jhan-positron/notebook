#!/usr/bin/env python3
"""test_make_report.py - fail-loud tests of make_report.py.

Each case runs a copy of the generator on a damaged copy of facts.json.
The generator must stop, or it must print a FAIL line and exit with status 1, and it must not write a page.
The copies and their output go to a temporary folder under test-tmp of this folder. The real report and facts.json are not touched.
Run: python3 test_make_report.py   (exit status 0 = all cases behave as required)"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
S = os.path.dirname(os.path.abspath(__file__))
os.makedirs(S + "/test-tmp", exist_ok=True)          # the copies stay inside the scratch folder of this rerun
T = tempfile.mkdtemp(prefix="test_make_report_", dir=S + "/test-tmp")
src = open(S + "/make_report.py").read()
facts = json.load(open(S + "/facts.json"))

def run(name, mutate, patch=lambda s: s):
    d = copy.deepcopy(facts)
    mutate(d)
    json.dump(d, open(f"{T}/facts-{name}.json", "w"))
    code = src.replace('S + "/facts.json"', repr(f"{T}/facts-{name}.json"))
    code = code.replace('OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"', f'OUT = "{T}/out-{name}.html"')
    assert code != src and f"{T}/out-{name}.html" in code
    code = patch(code)
    open(f"{T}/gen-{name}.py", "w").write(code)
    r = subprocess.run([sys.executable, f"{T}/gen-{name}.py"], capture_output=True, text=True)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if "FAIL" in l or "STOP" in l or "NOT WRITTEN" in l or l.startswith("wrote")]
    print(f"--- {name}: exit status {r.returncode}; output file written: {os.path.exists(f'{T}/out-{name}.html')}")
    for l in lines[:4]:
        print("    " + l[:230])
    return r.returncode

def drop_one(d):
    i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "rerun-L" and r["kernel"] == "oldread")
    del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1
def change_a(d):
    r = next(r for r in d["intervals"] if r["dataset"] == "rerun-A" and r["binary"] == "bw_new" and r["kernel"] == "read" and r["session"] == 1 and r["round"] == 1)
    r["GBps"] = round(r["GBps"] + 5.0, 2)
def change_bwx(d):
    r = next(r for r in d["intervals"] if r["dataset"] == "rerun-C" and r["kernel"] == "read")
    r["GBps"] = round(r["GBps"] + 0.5, 3)
def change_bwx_old(d):
    r = next(r for r in d["intervals"] if r["dataset"] == "B7a" and r["kernel"] == "read" and r["pos"] == 6)
    r["GBps"] = round(r["GBps"] + 0.5, 3)
def drop_bwx_old(d):
    i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "B5a-rev" and r["kernel"] == "asmread")
    del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1
def change_10mod(d):
    r = next(r for r in d["intervals"] if r["dataset"] == "X1d10" and r["kernel"] == "asmread" and r["pos"] == 1)
    r["GBps"] = round(r["GBps"] + 0.5, 3)
def drop_x2d12(d):
    i = next(i for i, r in enumerate(d["intervals"]) if r["dataset"] == "X2d12" and r["kernel"] == "oldread" and r["pos"] == 0)
    del d["intervals"][i]; d["meta"]["counts"]["intervals"] -= 1
def bwx_load(d):
    r = next(r for r in d["intervals"] if r["dataset"] == "C3b" and r["kernel"] == "read")
    for x in d["intervals"]:
        if x["proc_key"] == r["proc_key"]:
            x["load1_at_launch"] = round(x["load1_at_launch"] + 1.0, 2)
def other_boot(d):
    r = next(r for r in d["intervals"] if r["dataset"] == "control-I" and r["kernel"] == "asmread")
    r["boot"] = "00000000-0000-0000-0000-000000000000"
res = {}
res["control (no damage)"] = run("ok", lambda d: None)
res["one part L record removed"] = run("count", drop_one)
res["one part A value changed by 5 GB/s"] = run("valueA", change_a)
res["one bwx12 value changed by 0.5 GB/s"] = run("valueX", change_bwx)
res["one record from another boot"] = run("boot", other_boot)
res["one value of runner bwx changed by 0.5 GB/s"] = run("valueB", change_bwx_old)
res["one record of runner bwx removed"] = run("countB", drop_bwx_old)
res["one asmread value of a 10-module boot changed by 0.5 GB/s"] = run("value10", change_10mod)
res["one record of row X2d12 removed"] = run("countX2", drop_x2d12)
res["load at launch of one process of runner bwx changed by 1.0"] = run("loadB", bwx_load)
res["a reference path that does not exist"] = run("ref", lambda d: None, lambda s: s.replace('whole-chip-read-drop-easy-read.html"', 'no-such-file.html"'))
print()
ok = res["control (no damage)"] == 0 and all(v != 0 for k, v in res.items() if k != "control (no damage)")
for k, v in res.items():
    print(f"{'PASS' if (v == 0) == (k.startswith('control')) else 'FAIL'}  {k}: exit status {v}")
shutil.rmtree(T, ignore_errors=True)
sys.exit(0 if ok else 1)
