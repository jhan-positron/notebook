#!/usr/bin/env python3
"""Shared readers for the more-testing round-1 results tree
(exec/results/more-testing-r1/). Used by gen_status.py (markdown status) and
gen_results_html.py (charts page)."""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

HOME = os.path.expanduser("~")
RES = f"{HOME}/workspace/intel-AMX/exec/results/more-testing-r1"
CI = f"{RES}/ci-reference-20260904.json"

MODELS = [
    ("ingested-qwen-3-4b-instruct-2507-tp4", "qwen-3-4b (tp4)", "AMX-eligible"),
    ("llama-3.1-8b-instruct-good-tp2", "llama-3.1-8b-good (tp2)", "AMX-eligible"),
    ("mixtral-8x7b-instruct-v0.1-tp2", "mixtral-8x7b (tp2)", "AMX-eligible"),
    ("ingested-gpt-oss-120b-tp4", "gpt-oss-120b (tp4)", "not eligible (regression check)"),
]
ARMS = ["off", "canon", "mirror"]
SUBJECTS = ["biology", "business", "chemistry", "computer science", "economics", "engineering", "health",
            "history", "law", "math", "philosophy", "physics", "psychology", "other"]
SUBJECT_N = [71, 78, 113, 41, 84, 96, 81, 38, 110, 135, 49, 129, 79, 92]


def read(p, default=None):
    try:
        return open(p).read()
    except OSError:
        return default


def jload(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def parse_functional(cell):
    x = f"{cell}/functional.xml"
    if not os.path.exists(x):
        return None
    try:
        root = ET.parse(x).getroot()
    except ET.ParseError:
        return None
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = fails = errs = skips = 0
    failed, skipped = [], []
    for s in suites:
        tests += int(s.get("tests", 0)); fails += int(s.get("failures", 0))
        errs += int(s.get("errors", 0)); skips += int(s.get("skipped", 0))
        for tc in s.iter("testcase"):
            if tc.find("failure") is not None or tc.find("error") is not None:
                failed.append(tc.get("name"))
            if tc.find("skipped") is not None:
                skipped.append(tc.get("name"))
    return {"tests": tests, "passed": tests - fails - errs - skips, "failed": fails + errs, "skipped": skips,
            "failed_names": failed, "skipped_names": skipped}


def parse_mmlu(cell):
    d = f"{cell}/eval_results"
    if not os.path.isdir(d):
        return None
    per = {}
    corr = wrong = 0
    for s in SUBJECTS:
        j = jload(f"{d}/{s}_summary.json")
        if not j or s not in j:
            continue
        per[s] = j[s]
        corr += j[s]["corr"]; wrong += j[s]["wrong"]
    tot = corr + wrong
    log = read(f"{cell}/mmlu.log", "") or ""
    m = re.search(r"MMLU-Pro total for \S+: ([\d.]+)/([\d.]+) \(([\d.]+)%\)", log)
    return {"per_subject": per, "corr": corr, "wrong": wrong, "total": tot,
            "overall_pct": (100.0 * corr / tot) if tot else None,
            "complete": len(per) == len(SUBJECTS), "final_line": m.group(0) if m else None,
            "excluded": len(re.findall(r"returned an empty completion", log)),
            "random_guess": sum(int(x) for x in re.findall(r"(\d+) responses had no extractable answer", log))}


def parse_soak(d):
    log = read(f"{d}/soak.log", "")
    if not log:
        return None
    blocks = [m.start() for m in re.finditer(r"-- Duration: ", log)]
    if not blocks:
        return {"raw": True}
    seg = log[blocks[-1]:blocks[-1] + 6000]
    out = {"duration": re.search(r"-- Duration: (\S+)", seg).group(1), "models": {}}
    m = re.search(r"Errors: (\d+)", seg); out["errors"] = int(m.group(1)) if m else None
    m = re.search(r"Used Memory: ([\d.]+) GiB \(Growth: (-?[\d.]+) GiB\)", seg)
    if m: out["used_memory_gib"], out["growth_gib"] = float(m.group(1)), float(m.group(2))
    cur = None
    for l in seg.splitlines():
        m = re.search(r"^\s*Model: (\S+)", l)
        if m: cur = m.group(1); out["models"][cur] = {}; continue
        if cur:
            for key, rx in (("sent", r"Requests \(sent/succeeded/failed\): (\d+)/\d+/\d+"), ("succeeded", r"Requests \(sent/succeeded/failed\): \d+/(\d+)/\d+"),
                            ("failed", r"Requests \(sent/succeeded/failed\): \d+/\d+/(\d+)"), ("avg_ttft_s", r"Avg TTFT: ([\d.]+)s"),
                            ("total_gen_tok_s", r"Total token generation\s*: ([\d.]+)"), ("per_user_gen_tok_s", r"Per-user token generation: ([\d.]+)")):
                m = re.search(rx, l)
                if m: out["models"][cur][key] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    alerts = sorted(set(re.sub(r"\x1b\[[0-9;]*m", "", l).split("| ", 1)[-1].strip() for l in log.splitlines() if "ERROR" in l and "Errors:" not in l))
    out["alerts"] = alerts
    out["coherency_failures"] = len(re.findall(r"Failed coherency check", log))
    out["coherency_checks"] = len(re.findall(r"Starting coherency check", log))
    mm = re.search(r"Soak exiting: (.*)", log)
    out["exit_reason"] = re.sub(r"\x1b\[[0-9;]*m", "", mm.group(1)) if mm else None
    # time series: host memory growth (GiB) per monitor block, minutes since start
    series = []
    for m in re.finditer(r"-- Duration: (\d+):(\d+):(\d+)[^\n]*\n(?:.*\n){0,6}?\s*Used Memory: ([\d.]+) GiB \(Growth: (-?[\d.]+) GiB\)", log):
        t = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 60
        series.append((t, float(m.group(5))))
    out["growth_series"] = series
    # server-side mirror arena footprint over time, from rinzler.log timestamps
    rl = read(f"{d}/rinzler.log", "") or ""
    arena = []
    t0 = None
    for m in re.finditer(r"^\[(\d+):(\d+):(\d+)\.\d+\|.*KV cache footprint: ([\d.]+) GB DMA \+ ([\d.]+) GB K mirror", rl, re.M):
        t = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 60
        if t0 is None: t0 = t
        arena.append(((t - t0) % (24 * 60), float(m.group(4)), float(m.group(5))))
    out["arena_series"] = arena
    return out


def load_cell(d):
    return {"status": (read(f"{d}/STATUS", "") or "").strip() or "not run", "meta": jload(f"{d}/meta.json", {}),
            "functional": parse_functional(d), "perf": jload(f"{d}/perf.json"), "mmlu": parse_mmlu(d), "dir": d,
            "amx_lines": (read(f"{d}/rinzler-amx-lines.txt", "") or "").strip().splitlines()}


def load_all():
    """cells[(mid, arm)], extra[(mid, label)] (tagged repeats, with 'arm' key), soaks[tag] ('main' = planned)."""
    cells, extra = {}, {}
    for mid, _, _ in MODELS:
        for arm in ARMS:
            cells[(mid, arm)] = load_cell(f"{RES}/cells/{mid}__{arm}")
        for d in sorted(glob.glob(f"{RES}/cells/{mid}__*__*")):
            arm, tag = os.path.basename(d).split("__")[1:3]
            c = load_cell(d); c["arm"] = arm; c["tag"] = tag
            extra[(mid, f"{arm} (repeat {tag}, A/A control)")] = c
    soaks = {"main": (parse_soak(f"{RES}/soak"), jload(f"{RES}/soak/meta.json", {}), (read(f"{RES}/soak/STATUS", "") or "").strip() or "not run")}
    for d in sorted(glob.glob(f"{RES}/soak__*")):
        tag = os.path.basename(d).split("__", 1)[1]
        soaks[tag] = (parse_soak(d), jload(f"{d}/meta.json", {}), (read(f"{d}/STATUS", "") or "").strip() or "not run")
    return cells, extra, soaks, jload(CI, {})
