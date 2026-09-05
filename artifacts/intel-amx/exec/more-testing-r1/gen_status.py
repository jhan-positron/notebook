#!/usr/bin/env python3
"""Regenerate PR3879/more-testing/round-1/status.md from the raw results of
the more-testing round-1 campaign (exec/results/more-testing-r1/) and the
nightly-CI reference JSON. Safe to run at any time; missing cells are shown
as not run yet.
"""
import datetime
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmlu_diff import compare  # noqa: E402

HOME = os.path.expanduser("~")
RES = f"{HOME}/workspace/intel-AMX/exec/results/more-testing-r1"
OUT = f"{HOME}/workspace/intel-AMX/PR3879/more-testing/round-1/status.md"
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
    failed = []
    for s in suites:
        tests += int(s.get("tests", 0)); fails += int(s.get("failures", 0))
        errs += int(s.get("errors", 0)); skips += int(s.get("skipped", 0))
        for tc in s.iter("testcase"):
            if tc.find("failure") is not None or tc.find("error") is not None:
                failed.append(tc.get("name"))
    return {"tests": tests, "passed": tests - fails - errs - skips, "failed": fails + errs, "skipped": skips, "failed_names": failed}


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
    m = re.search(r"MMLU-Pro total for \S+: ([\d.]+)/([\d.]+) \(([\d.]+)%\)", read(f"{cell}/mmlu.log", "") or "")
    return {"per_subject": per, "corr": corr, "wrong": wrong, "total": tot,
            "overall_pct": (100.0 * corr / tot) if tot else None,
            "complete": len(per) == len(SUBJECTS), "final_line": m.group(0) if m else None,
            "failed_requests": len(re.findall(r"returned an empty completion|Request failed", read(f"{cell}/mmlu.log", "") or ""))}


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
    out["exit_reason"] = (re.search(r"Soak exiting: (.*)", log) or [None, None])[1] if re.search(r"Soak exiting: (.*)", log) else None
    return out


def fmt(x, nd=2, unit=""):
    if x is None: return "n/a"
    return f"{x:.{nd}f}{unit}"


def delta_pct(a, b):
    if a is None or b is None or b == 0: return "n/a"
    return f"{100.0 * (a - b) / b:+.1f}%"


ci = jload(CI, {})
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
cells = {}
extra = {}   # (mid, label) -> cell dict for tagged repeat cells, e.g. off__rep2
for mid, _, _ in MODELS:
    for d in sorted(glob.glob(f"{RES}/cells/{mid}__*__*")):
        arm, tag = os.path.basename(d).split("__")[1:3]
        extra[(mid, f"{arm} (repeat {tag}, A/A control)")] = {"status": (read(f"{d}/STATUS", "") or "").strip() or "not run",
            "meta": jload(f"{d}/meta.json", {}), "functional": parse_functional(d), "perf": jload(f"{d}/perf.json"),
            "mmlu": parse_mmlu(d), "dir": d, "amx_lines": [], "arm": arm}
    for arm in ARMS:
        c = f"{RES}/cells/{mid}__{arm}"
        st = (read(f"{c}/STATUS", "") or "").strip() or "not run"
        cells[(mid, arm)] = {"status": st, "meta": jload(f"{c}/meta.json", {}), "functional": parse_functional(c),
                             "perf": jload(f"{c}/perf.json"), "mmlu": parse_mmlu(c), "dir": c,
                             "amx_lines": (read(f"{c}/rinzler-amx-lines.txt", "") or "").strip().splitlines()}
soak = parse_soak(f"{RES}/soak")
soak_meta = jload(f"{RES}/soak/meta.json", {})
soak_status = (read(f"{RES}/soak/STATUS", "") or "").strip() or "not run"
extra_soaks = []
for d in sorted(glob.glob(f"{RES}/soak__*")):
    extra_soaks.append((os.path.basename(d).split("__", 1)[1], parse_soak(d), jload(f"{d}/meta.json", {}), (read(f"{d}/STATUS", "") or "").strip() or "not run"))

L = []
w = L.append
w("# Status report: AMX change (PR3879) under the nightly System CI tests, round 1")
w("")
w(f"Generated {now} by `exec/more-testing-r1/gen_status.py`. Test plan: `../test-plan.md`. "
  "Raw data: `exec/results/more-testing-r1/`. Words used here are defined in the test plan; the short list: "
  "**off** = AMX kill switch on (baseline), **canon** = AMX on, normal K layout, **mirror** = AMX on with the K mirror arena; "
  "**MMLU Pro** = multiple-choice accuracy test (percent correct on the fixed 1196-question 10% set); "
  "**TPS** = per-user generated tokens per second; **TTFT** = time to first token; **CI ref** = nightly CI run 33833914529 of 2026-09-04 (main branch, tron 2026.09.04-fe8dbdee).")
w("")
done = [k for k, v in cells.items() if v["status"] == "done"]
running = [k for k, v in cells.items() if v["status"] == "running"]
failed = [k for k, v in cells.items() if v["status"] not in ("done", "running", "not run", "skipped")]
skipped = [k for k, v in cells.items() if v["status"] == "skipped"]
w("## Short version")
w("")
w(f"{len(done)} of {len(cells)} model-arm cells are done" + (f", {len(running)} running" if running else "") +
  (f", {len(skipped)} skipped for time" if skipped else "") + (f", {len(failed)} failed to run" if failed else "") +
  f"; soak: {soak_status}.")
# headline per model
for mid, label, elig in MODELS:
    off = cells[(mid, "off")]
    parts = []
    for arm in ("canon", "mirror"):
        c = cells[(mid, arm)]
        if c["status"] != "done": continue
        f = c["functional"]; p = c["perf"]; m = c["mmlu"]
        seg = []
        if f: seg.append(f"functional {f['passed']} passed/{f['failed']} failed")
        if p and off["perf"]: seg.append(f"TPS {delta_pct(p['tps_mean'], off['perf']['tps_mean'])} vs off")
        if m and m["complete"] and off["mmlu"] and off["mmlu"]["complete"]:
            seg.append(f"MMLU {m['overall_pct']:.2f}% vs off {off['mmlu']['overall_pct']:.2f}% ({m['overall_pct'] - off['mmlu']['overall_pct']:+.2f} points)")
        if seg: parts.append(f"{arm}: " + ", ".join(seg))
    if parts:
        w(f"- **{label}**: " + "; ".join(parts) + ".")
w("")
w("## Build and machine facts")
w("")
anymeta = next((v["meta"] for v in cells.values() if v["meta"]), {})
w(f"- tron tree `~/workspace/tron-amx` at `{anymeta.get('tron_head', '60d66d9c04')}` (PR3879 head); rinzler binaries built 2026-09-04 17:33-17:46 UTC "
  "(`exec/logs/more-testing-r1-build.log`): canon sha256 `0b5fe23f...`, mirror sha256 `fc32cabe...`, version 2026.09.04-60d66d9c-jhan-amx-p0.")
w("- delphi-3bda, production rinzler serving stopped 17:33 UTC per the standing policy (idle: zero client connections, zero request lines). "
  "One rinzler process per cell on port 13100 with production's per-instance card, core, and hugepage arguments; `USE_HW_ATTN=0` in every arm.")
w("- Client: systems_test `470aca1` in `/var/tmp/jhan/st-venv` on delphi-3bda itself (CI's client runs on another host through the platformd proxy over 2-4 engines).")
w("")
w("## Results per model")
w("")
for mid, label, elig in MODELS:
    w(f"### {label}: `{mid}` ({elig})")
    w("")
    ciperf = (ci.get("perf", {}).get(mid) or [{}])[-1]
    cimmlu = ci.get("mmlu", {}).get(mid, {})
    w("| Arm | Status | Functional (pass/skip/fail) | TPS mean (sd) [tok/s per user] | TPS vs off | TTFT [ms] | MMLU Pro overall [%] | MMLU vs off [points] | Wall time |")
    w("|---|---|---|---|---|---|---|---|---|")
    ci_over = (cimmlu.get("scores_pct") or {}).get("overall")
    w(f"| CI ref (main, 2-4 engines) | done 2026-09-04 | see note | {fmt(ciperf.get('tps'))} | n/a | {ciperf.get('ttft_ms', 'n/a')} | {fmt(ci_over)} | n/a | perf {ciperf.get('minutes', 'n/a')} min, MMLU {cimmlu.get('minutes', 'n/a')} min |")
    off = cells[(mid, "off")]
    for arm in ARMS:
        c = cells[(mid, arm)]
        f, p, m = c["functional"], c["perf"], c["mmlu"]
        fcol = f"{f['passed']}/{f['skipped']}/{f['failed']}" if f else "n/a"
        if f and f["failed_names"]: fcol += " (" + ", ".join(f["failed_names"][:4]) + (", ..." if len(f["failed_names"]) > 4 else "") + ")"
        tps = f"{p['tps_mean']:.2f} ({p['tps_std_dev']:.2f})" if p else "n/a"
        dtps = delta_pct(p["tps_mean"], off["perf"]["tps_mean"]) if (p and off["perf"] and arm != "off") else ("baseline" if arm == "off" and p else "n/a")
        ttft = str(p["ttft_mean_ms"]) if p else "n/a"
        if m and m["total"]:
            mm = f"{m['overall_pct']:.2f}" + ("" if m["complete"] else f" (partial: {len(m['per_subject'])}/14 subjects)")
        elif c["meta"].get("run_mmlu") is False and c["status"] == "done":
            mm = "not planned"
        else:
            mm = "n/a"
        if m and m["complete"] and arm != "off" and off["mmlu"] and off["mmlu"]["complete"]:
            dm = f"{m['overall_pct'] - off['mmlu']['overall_pct']:+.2f}"
        else:
            dm = "baseline" if (arm == "off" and m and m["complete"]) else "n/a"
        ph = c["meta"].get("phases", {})
        wall = ", ".join(f"{k} {v['seconds'] // 60} min" for k, v in ph.items()) if ph else "n/a"
        w(f"| {arm} | {c['status']} | {fcol} | {tps} | {dtps} | {ttft} | {mm} | {dm} | {wall} |")
    for (emid, elabel), c in extra.items():
        if emid != mid: continue
        f, p, m = c["functional"], c["perf"], c["mmlu"]
        fcol = f"{f['passed']}/{f['skipped']}/{f['failed']}" if f else "n/a"
        tps = f"{p['tps_mean']:.2f} ({p['tps_std_dev']:.2f})" if p else "n/a"
        dtps = delta_pct(p["tps_mean"], off["perf"]["tps_mean"]) if (p and off["perf"]) else "n/a"
        ttft = str(p["ttft_mean_ms"]) if p else "n/a"
        mm = f"{m['overall_pct']:.2f}" if (m and m["total"]) else "n/a"
        dm = f"{m['overall_pct'] - off['mmlu']['overall_pct']:+.2f}" if (m and m["complete"] and off["mmlu"] and off["mmlu"]["complete"]) else "n/a"
        ph = c["meta"].get("phases", {})
        wall = ", ".join(f"{k} {v['seconds'] // 60} min" for k, v in ph.items()) if ph else "n/a"
        w(f"| {elabel} | {c['status']} | {fcol} | {tps} | {dtps} | {ttft} | {mm} | {dm} | {wall} |")
    w("")
    # per-question answer changes relative to the off arm (same 1196 questions)
    if off["mmlu"] and off["mmlu"]["complete"]:
        rows = []
        for arm in ("canon", "mirror"):
            m = cells[(mid, arm)]["mmlu"]
            if m and m["complete"]:
                rows.append((arm, compare(f"{off['dir']}/eval_results", f"{cells[(mid, arm)]['dir']}/eval_results")))
        for (emid, elabel), c in extra.items():
            if emid == mid and c["mmlu"] and c["mmlu"]["complete"]:
                rows.append((elabel, compare(f"{off['dir']}/eval_results", f"{c['dir']}/eval_results")))
        if rows:
            w("MMLU Pro answer changes relative to the off arm (identical question set; a changed answer means the greedy chain-of-thought diverged and ended on another letter):")
            w("")
            w("| Compared with off | Responses byte-identical | Final answer changed | right -> wrong | wrong -> right | wrong -> other wrong | Net [questions] |")
            w("|---|---|---|---|---|---|---|")
            for name, r in rows:
                n = r["n_common"] or 1
                w(f"| {name} | {r['response_identical']} ({100*r['response_identical']/n:.1f}%) | {r['pred_changed']} ({100*r['pred_changed']/n:.1f}%) | {r['right_to_wrong']} | {r['wrong_to_right']} | {r['wrong_to_wrong_changed']} | {r['wrong_to_right'] - r['right_to_wrong']:+d} |")
            w("")
    w(f"Note: CI's functional phase ran {mid} inside a multi-model group; CI reports group totals only "
      "(150 passed/2 skipped for the six-model tp4 group, 48 passed/4 skipped for the gpt-oss-120b + qwen-3-4b tp4 group). "
      "In our cells the two proxy-authentication tests (`test_auth_reject_no_token`, `test_auth_reject_bad_token`) skip themselves because rinzler answers directly (Server header `drogon/`); CI exercises them through the platformd proxy once per night. Every other skip is listed by name in the cell's `functional.xml`.")
    # per-subject MMLU
    rows = []
    if cimmlu.get("scores_pct"):
        rows.append(("CI ref", [cimmlu["scores_pct"].get(s) for s in SUBJECTS], ci_over))
    for arm in ARMS:
        m = cells[(mid, arm)]["mmlu"]
        if m and m["per_subject"]:
            rows.append((arm, [100.0 * m["per_subject"][s]["acc"] if s in m["per_subject"] else None for s in SUBJECTS], m["overall_pct"]))
    if rows:
        w("")
        w("MMLU Pro per subject, percent correct (question counts per subject: " +
          ", ".join(f"{s} {n}" for s, n in zip(SUBJECTS, [71, 78, 113, 41, 84, 96, 81, 38, 110, 135, 49, 129, 79, 92])) + "):")
        w("")
        w("| Arm | overall | " + " | ".join(SUBJECTS) + " |")
        w("|---|---|" + "---|" * len(SUBJECTS))
        for name, vals, over in rows:
            w(f"| {name} | {fmt(over)} | " + " | ".join(fmt(v, 1) for v in vals) + " |")
    # AMX evidence lines
    ev = []
    for arm in ARMS:
        ls = cells[(mid, arm)]["amx_lines"]
        if ls:
            keep = [l for l in ls if re.search(r"HW attention|K mirror", l)]
            if keep: ev.append(f"- {arm}: " + " / ".join(re.sub(r"^\[[^\]]*\]\s*\[[a-z ]*\]\s*", "", l)[:160] for l in keep[:3]))
    if ev:
        w("")
        w("Server log evidence (attention engine and mirror arena):")
        w("")
        L.extend(ev)
    w("")
w("## Soak")
w("")
w(f"Planned: 60 minutes, 25 users, mirror arm, models llama-3.1-8b-instruct-good-tp2 + ingested-qwen-3-4b-instruct-2507-tp2 on one tp2 engine. Status: {soak_status}.")
w("")
def soak_block(sk, meta, label):
    if not sk or sk.get("raw"):
        w(f"- {label}: no summary block in the log yet."); w(""); return
    exit_reason = re.sub(r"\x1b\[[0-9;]*m", "", sk.get("exit_reason") or "n/a")
    w(f"- {label}: arm {meta.get('arm', '?')}, {meta.get('users', '?')} users, duration {sk['duration']}, exit: {exit_reason}. "
      f"Harness error count {sk.get('errors')} (request failures are in the table; the count also includes monitor alerts, listed below). "
      f"Host used memory at the end {fmt(sk.get('used_memory_gib'))} GiB, growth since start {fmt(sk.get('growth_gib'), 3)} GiB (this is whole-host memory: server plus the test client running on the same host). "
      f"Coherency probes {sk['coherency_checks']}, failures {sk['coherency_failures']}.")
    for a in sk.get("alerts", []):
        w(f"  - monitor alert: {a}")
    w("")
    w("| Model | Requests sent/succeeded/failed | Avg TTFT [s] | Total generation [tok/s] | Per-user generation [tok/s] |")
    w("|---|---|---|---|---|")
    for mname, v in sk["models"].items():
        w(f"| {mname} | {v.get('sent', 'n/a')}/{v.get('succeeded', 'n/a')}/{v.get('failed', 'n/a')} | {fmt(v.get('avg_ttft_s'))} | {fmt(v.get('total_gen_tok_s'))} | {fmt(v.get('per_user_gen_tok_s'))} |")
    w("")

if soak:
    soak_block(soak, soak_meta, "Planned soak")
for tag, sk, meta, st_ in extra_soaks:
    w(f"Extra soak `{tag}` (status {st_}):")
    w("")
    soak_block(sk, meta, f"Extra soak {tag}")
cis = ci.get("soak", {})
if cis.get("models"):
    w(f"CI reference soak (3 h, 100 users, 4 tp2 engines, models {', '.join(cis.get('model_list', []))}): errors {cis.get('errors')}, memory growth {fmt(cis.get('growth_gib'), 3)} GiB; "
      + "; ".join(f"{k}: {v.get('sent')}/{v.get('succeeded')}/{v.get('failed')} requests, TTFT {v.get('avg_ttft_s')} s, {v.get('per_user_gen_tok_s')} tok/s per user" for k, v in cis["models"].items()) + ".")
    w("")
notes = read(f"{RES}/notes.md")
if notes:
    w("## Notes from the analyst (hand-written, `exec/results/more-testing-r1/notes.md`)")
    w("")
    L.extend(notes.rstrip().splitlines())
    w("")
w("## Cells not run or failed")
w("")
notes = []
for (mid, arm), c in cells.items():
    if c["status"] in ("skipped",):
        notes.append(f"- {mid} / {arm}: skipped (would not finish before the 02:30 UTC deadline).")
    elif c["status"] not in ("done", "running", "not run"):
        notes.append(f"- {mid} / {arm}: {c['status']} (see `{os.path.relpath(c['dir'], HOME + '/workspace/intel-AMX')}/`).")
    elif c["status"] == "not run":
        notes.append(f"- {mid} / {arm}: not run yet.")
L.extend(notes or ["- none"])
w("")
w("## Timeline (UTC)")
w("")
tl = []
for (mid, arm), c in cells.items():
    if c["meta"].get("started"):
        tl.append((c["meta"]["started"], f"{c['meta']['started'][11:16]} - {c['meta'].get('ended', '...')[11:16]}  {mid} / {arm}  ({c['status']})"))
if soak_meta.get("started"):
    tl.append((soak_meta["started"], f"{soak_meta['started'][11:16]} - {soak_meta.get('ended', '...')[11:16]}  soak ({soak_status})"))
for _, t in sorted(tl):
    w(f"- {t}")
if not tl:
    w("- nothing started yet")
w("")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {OUT} ({len(L)} lines); cells done={len(done)} running={len(running)} skipped={len(skipped)} failed={len(failed)}; soak={soak_status}")
