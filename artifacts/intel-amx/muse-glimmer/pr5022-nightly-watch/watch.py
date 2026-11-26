#!/usr/bin/env python3
"""Nightly performance watch for tron PR 5022 (AMX attention for Muse Glimmer).

Reads the nightly systems-test sessions from the Talos results service.
Computes the normal value of every model from the nights before the PR.
Compares the nights whose tron build contains the PR against that normal.
Writes report.html, status.json and one line in log.txt per run.

Usage:
    python3 -B watch.py             fetch, analyse, write the report
    python3 -B watch.py --offline   analyse the saved copy only (no network)
    python3 -B watch.py --backtest  print the false-alarm rate of the band rule
"""
import argparse
import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
import urllib.request

import report

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TALOS_API = "http://talos:5000"
TALOS_UI = "http://talos:5174"
REPO = "positron-ai/tron"
PR = 5022
MACHINES = {"delphi-3bda": "Intel", "andoria-b1a3": "AMD"}
RUNNER = "system-ci-runner"  # the scheduled nightly; hand-started reruns use other runners
# Until its last phase ends, Talos names a nightly session "Performance Benchmarks (date)"
# and gives it no `dut` field. The session keeps its uuid when it gets its final name.
RUNNING_NAME = "Performance Benchmarks"
RUNNING_MAX_AGE = 24 * 3600   # s; an older session without a `dut` field never finished
DUT_RE = re.compile(r"Connecting to ([a-z]+-[0-9a-f]{4})\.positron\.internal")
HISTORY_START = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp()
GLIMMER = "ingested_meta_models__muse_glimmer_30b_tp4_tps @ 8"
METRICS = ("tps", "ttft")  # decode rate per user, and time to first token (prefill)

# Band rule. A night is outside the normal when it differs from the baseline
# median by more than the largest of these three values.
BAND_SIGMAS = 4.0                              # times the night-to-night spread
BAND_FLOOR = {"tps": 0.0075, "ttft": 0.01}     # fraction of the median
BAND_FLOOR_ABS = {"tps": 0.0, "ttft": 3.0}     # Talos stores TTFT in whole ms
SEED_NIGHTS = 3      # the scan for a level shift starts from this many newest nights
SCAN_SIGMAS = 3.0    # two nights in a row beyond this many spreads are a level shift
MIN_BASELINE = 5     # fewer nights than this is reported as a short baseline

# What PR 5022 measured for the nightly configuration on delphi-3bda (PR body,
# section "Nightly configuration"): decode +4.6 %, TTFT -3.4 %.
PR_MEASURED = {("delphi-3bda", "tps"): 0.046, ("delphi-3bda", "ttft"): -0.034}

VALUE_RE = re.compile(
    r"([\d.]+) \(std dev ([\d.]+)\) TTFT (\d+)ms, prefill (\d+) tok/s "
    r"\((\d+) observed prompt tok, (\d+)% cached\) (.*)")
KEY_RE = re.compile(r"^(.*)_tps @ (\d+)$")
SHA_RE = re.compile(r"-([0-9a-f]{7,40})$")

NAMES = {
    "ingested_meta_models__muse_glimmer_30b_tp4": "Muse Glimmer 30B tp4",
    "ingested-gemma-4-31b-it_tp2": "gemma-4-31b tp2",
    "ingested_gpt_oss_120b_tp4": "gpt-oss-120b tp4",
    "ingested_qwen_3_4b_instruct_2507_tp2": "qwen-3-4b tp2",
    "ingested_qwen_3_4b_instruct_2507_tp4": "qwen-3-4b tp4",
    "llama_3_1_8b_instruct_good_tp2": "llama-3.1-8b tp2",
    "llama_3_2_3b_instruct_fast_tp2": "llama-3.2-3b tp2",
    "llama_3_3_70b_instruct_good_tp2": "llama-3.3-70b tp2",
    "llama_3_3_70b_instruct_good_tp4": "llama-3.3-70b tp4",
    "mixtral_8x7b_instruct_v0_1_tp2": "mixtral-8x7b tp2",
    "gemma_2_9b_it_fast_tp2": "gemma-2-9b tp2",
}


def series_name(key):
    m = KEY_RE.match(key)
    return "%s, %s users" % (NAMES.get(m.group(1), m.group(1)), m.group(2))


def utc(ts, fmt="%Y-%m-%d"):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime(fmt)


def load(name, default):
    try:
        with open(os.path.join(DATA, name)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    tmp = os.path.join(DATA, name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, os.path.join(DATA, name))


def gh(args):
    """Run the GitHub command-line tool. Returns its output, or None on failure."""
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


# ---------------------------------------------------------------- collection

def to_record(s):
    series, failed, unparsed = {}, {}, []
    for k, v in s.items():
        if not KEY_RE.match(k) or not isinstance(v, str):
            continue
        m = VALUE_RE.match(v)
        if not m:
            if v.startswith("FAILED"):
                failed[k] = v[:160]    # the perf test of this model failed that night
            else:
                unparsed.append(k)
            continue
        series[k] = {"tps": float(m.group(1)), "sd": float(m.group(2)),
                     "ttft": int(m.group(3)), "prefill": int(m.group(4)),
                     "obs": int(m.group(5)), "cached": int(m.group(6)),
                     "cfg": m.group(7)}
    mmlu = {}
    for k, v in s.items():
        if k.startswith("mmlu_pro_") and isinstance(v, str) and v.endswith("%"):
            try:
                mmlu[k[len("mmlu_pro_"):]] = float(v[:-1])
            except ValueError:
                pass
    sha = SHA_RE.search(str(s.get("tron_version") or ""))
    return {"uuid": s["uuid"], "dut": s["dut"], "started": s["started"],
            "ended": s.get("ended"), "tron_version": s.get("tron_version"),
            "sha": sha.group(1) if sha else None,
            "platformd": s.get("platformd_version"),
            "bitfile": s.get("bitfile_version"),
            "test_project": s.get("test_project"),
            "series": series, "failed": failed, "mmlu": mmlu, "unparsed": unparsed}


def collect(offline):
    """Merge the nightly sessions from Talos into the saved copy. Returns (nights, error)."""
    nights = load("nights.json", {})
    if offline:
        return nights, None
    try:
        with urllib.request.urlopen(TALOS_API + "/sessions", timeout=180) as r:
            entries = json.load(r)["entries"]
    except Exception as e:  # the saved copy still gives a report; the error is printed
        return nights, "Talos fetch failed: %s" % e
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    err = []
    for s in entries:
        if not (s.get("runner") == RUNNER and isinstance(s.get("started"), (int, float))
                and s["started"] >= HISTORY_START and s.get("uuid")):
            continue
        name = str(s.get("name", ""))
        if s.get("dut") in MACHINES and name.startswith("System CI"):
            nights[s["uuid"]] = to_record(s)
        elif (not s.get("dut") and name.startswith(RUNNING_NAME)
              and now - s["started"] < RUNNING_MAX_AGE):
            dut = running_dut(s["uuid"])
            if dut is None:
                err.append("running session %s: its log does not name one machine" % s["uuid"])
            elif dut in MACHINES:
                # `ended` of a running session is the end of its first phase, not of the session
                nights[s["uuid"]] = to_record(dict(s, dut=dut, ended=None))
    for n in nights.values():
        n["running"] = not n["ended"] and now - n["started"] < RUNNING_MAX_AGE
    save("nights.json", nights)
    return nights, "; ".join(err) or None


def running_dut(uuid):
    """Machine of a session without a `dut` field, read from its log. None when not found."""
    cache = load("duts.json", {})
    if uuid not in cache:
        try:
            with urllib.request.urlopen("%s/sessions/%s/logs" % (TALOS_API, uuid), timeout=180) as r:
                found = set(DUT_RE.findall(r.read().decode("utf-8", "replace")))
        except Exception:
            return None
        if len(found) != 1:
            return None
        cache[uuid] = found.pop()
        save("duts.json", cache)
    return cache[uuid]


def pr_state(offline):
    """State of the PR. A merged state never changes, so it is read from the saved copy."""
    saved = load("pr.json", {})
    if saved.get("state") == "MERGED" or offline:
        return saved or {"state": "UNKNOWN"}
    out = gh(["pr", "view", str(PR), "-R", REPO, "--json", "state,mergedAt,mergeCommit"])
    if out is None:
        # A stale "not merged" would count nights with the PR as nights before it.
        return dict(saved or {"state": "UNKNOWN"}, stale=True)
    j = json.loads(out)
    st = {"state": j["state"], "mergedAt": j.get("mergedAt"),
          "oid": (j.get("mergeCommit") or {}).get("oid")}
    if st["state"] == "MERGED" and st["mergedAt"]:
        st["merged_ts"] = dt.datetime.strptime(
            st["mergedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    save("pr.json", st)
    return st


def mark_pr(nights, pr, offline):
    """Set night["has_pr"]: True, False, or None when it cannot be decided."""
    cache = load("contains.json", {})
    for n in nights.values():
        if pr.get("state") != "MERGED":
            n["has_pr"] = False
        elif n["started"] < pr["merged_ts"]:
            n["has_pr"] = False      # the session started before the merge
        elif not n["sha"]:
            n["has_pr"] = None
        else:
            if n["sha"] not in cache and not offline:
                # behind_by == 0 means the merge commit is an ancestor of the nightly build
                out = gh(["api", "repos/%s/compare/%s...%s" % (REPO, pr["oid"], n["sha"]),
                          "--jq", ".behind_by"])
                if out is not None and out.strip().isdigit():
                    cache[n["sha"]] = int(out.strip()) == 0
            n["has_pr"] = cache.get(n["sha"])
    save("contains.json", cache)


def commits_between(old, new, offline):
    """First lines of the commits in new that are not in old (main is linear)."""
    cache = load("commits.json", {})
    key = "%s...%s" % (old, new)
    if key not in cache and not offline:
        out = gh(["api", "repos/%s/compare/%s" % (REPO, key),
                  "--jq", "[.commits[].commit.message | split(\"\\n\")[0]]"])
        if out is not None:
            cache[key] = json.loads(out)
            save("commits.json", cache)
    return cache.get(key)


# ------------------------------------------------------------------ analysis

def rsigma(vals):
    """Robust spread: 1.4826 x the median distance from the median (equals the
    standard deviation for bell-shaped data, and ignores a single odd night)."""
    m = statistics.median(vals)
    return 1.4826 * statistics.median([abs(v - m) for v in vals])


def step_sigma(vals):
    """Night-to-night spread from the steps between neighbouring nights.
    A level shift changes one step only, so it does not inflate this value."""
    if len(vals) < 3:
        return 0.0
    return 1.4826 * statistics.median([abs(b - a) for a, b in zip(vals, vals[1:])]) / 2 ** 0.5


def half_band(vals, metric, sigmas=BAND_SIGMAS, noise=0.0):
    c = statistics.median(vals)
    return max(sigmas * max(rsigma(vals), noise), BAND_FLOOR[metric] * c, BAND_FLOOR_ABS[metric])


def stable_start(vals, metric):
    """Index of the oldest value of the newest run without a level shift.

    Walk back from the newest nights. One night outside the band stays in the
    run. Two nights in a row outside the band are a level shift and end it."""
    noise = step_sigma(vals)   # keeps a few close newest nights from ending the run too early
    start = max(0, len(vals) - SEED_NIGHTS)
    i = start - 1
    while i >= 0:
        tail = vals[start:]
        c, h = statistics.median(tail), half_band(tail, metric, SCAN_SIGMAS, noise)
        if abs(vals[i] - c) <= h:
            start, i = i, i - 1
        elif i >= 1 and abs(vals[i - 1] - c) <= h:
            start, i = i - 1, i - 2
        else:
            break
    return start


def baseline(pre, key, metric):
    """Baseline of one series from the nights before the PR (oldest first)."""
    have = [n for n in pre if key in n["series"]]
    if not have:
        return None
    ref = have[-1]
    env = lambda n: (n["platformd"], n["bitfile"], n["series"][key]["cfg"])
    same = []
    for n in reversed(have):   # newest run of nights with the same platform software and test settings
        if env(n) != env(ref):
            break
        same.append(n)
    same.reverse()
    vals = [n["series"][key][metric] for n in same]
    used = same[stable_start(vals, metric):]
    vals = [n["series"][key][metric] for n in used]
    c = statistics.median(vals)
    return {"n": len(vals), "median": c, "lo": min(vals), "hi": max(vals),
            "sigma": rsigma(vals), "half": half_band(vals, metric),
            "first": used[0]["started"], "last": used[-1]["started"],
            "uuids": [n["uuid"] for n in used], "short": len(vals) < MIN_BASELINE,
            "cfg": ref["series"][key]["cfg"], "platformd": ref["platformd"],
            "bitfile": ref["bitfile"]}


def judge(value, base, metric):
    """normal, faster or slower. A higher decode rate is faster. A lower TTFT is faster."""
    d = value - base["median"]
    if abs(d) <= base["half"]:
        return "normal"
    return "faster" if (d > 0) == (metric == "tps") else "slower"


def analyse(nights):
    out = {}
    for dut in MACHINES:
        mine = sorted((n for n in nights.values() if n["dut"] == dut), key=lambda n: n["started"])
        pre = [n for n in mine if n["has_pr"] is False]
        post = [n for n in mine if n["has_pr"] is True]
        keys = sorted({k for n in pre[-3:] + post for k in n["series"]},
                      key=lambda k: (k != GLIMMER, series_name(k)))
        rows = []
        for key in keys:
            for metric in METRICS:
                base = baseline(pre, key, metric)
                if base is None:
                    continue
                after = []
                for n in post:
                    s = n["series"].get(key)
                    if s is None:
                        if key in n["failed"]:
                            after.append({"uuid": n["uuid"], "started": n["started"],
                                          "state": "test failed", "why": n["failed"][key]})
                        continue
                    row = {"uuid": n["uuid"], "started": n["started"], "value": s[metric]}
                    if s["cfg"] != base["cfg"]:
                        row["state"] = "test settings changed"
                    else:
                        row["state"] = judge(s[metric], base, metric)
                        row["delta"] = s[metric] / base["median"] - 1
                    row["env_changed"] = (n["platformd"], n["bitfile"]) != (base["platformd"], base["bitfile"])
                    after.append(row)
                comparable = [a for a in after if "delta" in a]
                verdict = {"state": "waiting", "n": len(comparable)}
                if comparable:
                    med = statistics.median(a["value"] for a in comparable)
                    verdict.update(state=judge(med, base, metric), median=med,
                                   delta=med / base["median"] - 1,
                                   latest=comparable[-1]["value"],
                                   latest_delta=comparable[-1]["delta"],
                                   latest_state=comparable[-1]["state"])
                expected = "faster" if (key == GLIMMER and dut == "delphi-3bda") else "normal"
                n_failed = sum(1 for a in after if a["state"] == "test failed")
                if n_failed:
                    check = "TEST FAILED"
                elif verdict["state"] == "waiting":
                    check = "waiting"
                elif verdict["state"] == expected:
                    check = "as expected"
                elif verdict["state"] == "faster":
                    check = "faster, not expected"
                elif verdict["state"] == "slower":
                    check = "SLOWER"
                else:
                    check = "NO GAIN"   # Glimmer on Intel stayed inside the normal band
                last_pre = [n for n in pre if key in n["series"]][-1]
                rows.append({"key": key, "name": series_name(key), "metric": metric,
                             "glimmer": key == GLIMMER, "base": base, "after": after,
                             "verdict": verdict, "expected": expected, "check": check,
                             "pre_latest": last_pre["series"][key][metric],
                             "pr_measured": PR_MEASURED.get((dut, metric)) if key == GLIMMER else None})
        out[dut] = {"rows": rows, "n_pre": len(pre), "n_post": len(post),
                    "unknown": [n["uuid"] for n in mine if n["has_pr"] is None]}
    return out


def false_alarms(res, nights):
    """Leave one baseline night out, build the band from the others, test the left-out night."""
    total = flagged = 0
    detail = []
    for dut, a in res.items():
        for r in a["rows"]:
            vals = [nights[u]["series"][r["key"]][r["metric"]] for u in r["base"]["uuids"]]
            if len(vals) < MIN_BASELINE + 1:
                continue
            bad = []
            for i, v in enumerate(vals):
                rest = vals[:i] + vals[i + 1:]
                if abs(v - statistics.median(rest)) > half_band(rest, r["metric"]):
                    bad.append(v)
            total += len(vals)
            flagged += len(bad)
            detail.append((dut, r, len(vals), bad))
    return {"total": total, "flagged": flagged}, detail


def backtest(nights):
    for n in nights.values():
        n["has_pr"] = False
    count, detail = false_alarms(analyse(nights), nights)
    print("Rule: %.1f spreads, floors %s" % (BAND_SIGMAS, BAND_FLOOR))
    for dut, r, n, bad in detail:
        print("%-13s %-30s %-4s n=%2d median %9.2f band +-%5.2f%% flagged %d %s" % (
            dut, r["name"], r["metric"], n, r["base"]["median"],
            100 * r["base"]["half"] / r["base"]["median"], len(bad), bad or ""))
    print("flagged %d of %d baseline nights (%.1f %%)" % (
        count["flagged"], count["total"], 100.0 * count["flagged"] / max(count["total"], 1)))


# ------------------------------------------------------------------- output

def events(nights):
    """What changed since the last run: new nights, new results, finished nights."""
    seen = load("state.json", None)
    now = {u: {"keys": sorted(n["series"]), "ended": bool(n["ended"])} for u, n in nights.items()}
    save("state.json", now)
    if seen is None:
        return None
    ev = []
    for u, n in sorted(nights.items(), key=lambda kv: kv[1]["started"]):
        tag = "%s night %s (tron %s, %s)" % (
            n["dut"], utc(n["started"]), n["tron_version"],
            {True: "WITH PR %d" % PR, False: "before PR %d" % PR, None: "PR state unknown"}[n["has_pr"]])
        old = seen.get(u)
        if old is None:
            ev.append("NEW NIGHT: %s, %d perf results so far" % (tag, len(n["series"])))
            continue
        added = sorted(set(n["series"]) - set(old["keys"]))
        if added:
            ev.append("NEW RESULTS: %s: +%d%s" % (tag, len(added), ", Glimmer included" if GLIMMER in added else ""))
        if n["ended"] and not old["ended"]:
            ev.append("NIGHT FINISHED: %s, %d perf results" % (tag, len(n["series"])))
    return ev


def fmt_value(metric, v):
    return "%.2f TPS" % v if metric == "tps" else "%d ms" % round(v)


def summary_lines(res, pr, nights, err):
    lines = []
    if err:
        lines.append("ERROR: " + err)
    if pr.get("stale"):
        lines.append("ERROR: GitHub did not answer. The PR state below is the last saved one and may be out of date.")
    if pr.get("state") == "MERGED":
        lines.append("PR %d: MERGED %s as %s" % (PR, pr["mergedAt"], pr["oid"][:10]))
    else:
        lines.append("PR %d: %s (not merged; every night counts as before the PR)" % (PR, pr.get("state")))
    for dut, a in res.items():
        lines.append("%s (%s): %d nights before the PR, %d with it%s" % (
            dut, MACHINES[dut], a["n_pre"], a["n_post"],
            ", %d undecided" % len(a["unknown"]) if a["unknown"] else ""))
        for r in a["rows"]:
            if not r["glimmer"]:
                continue
            b, v = r["base"], r["verdict"]
            line = "  Glimmer %-6s normal %s (band +-%.2f %%, %d nights %s..%s)" % (
                "decode" if r["metric"] == "tps" else "TTFT", fmt_value(r["metric"], b["median"]),
                100 * b["half"] / b["median"], b["n"], utc(b["first"], "%m-%d"), utc(b["last"], "%m-%d"))
            if v["state"] != "waiting":
                line += " | with PR: %s (%+.2f %%, %d night%s) -> %s" % (
                    fmt_value(r["metric"], v["median"]), 100 * v["delta"], v["n"],
                    "" if v["n"] == 1 else "s", r["check"])
            else:
                line += " | waiting"
            lines.append(line)
        for r in a["rows"]:
            if r["check"] == "TEST FAILED" and r["metric"] == "tps":
                lines.append("  TEST FAILED with the PR: %s: %s" % (
                    r["name"], "; ".join(x["why"] for x in r["after"] if x["state"] == "test failed")))
        others = [r for r in a["rows"] if not r["glimmer"] and r["verdict"]["state"] != "waiting"]
        bad = [r for r in others if r["check"] == "SLOWER"]
        good = [r for r in others if r["verdict"]["state"] == "faster"]
        if others:
            lines.append("  other models: %d series compared, %d slower, %d faster" % (len(others), len(bad), len(good)))
            for r in bad + good:
                lines.append("    %s %s %s: %s vs normal %s (%+.2f %%, band +-%.2f %%)" % (
                    r["check"] if r in bad else "faster", r["name"],
                    "decode" if r["metric"] == "tps" else "TTFT",
                    fmt_value(r["metric"], r["verdict"]["median"]), fmt_value(r["metric"], r["base"]["median"]),
                    100 * r["verdict"]["delta"], 100 * r["base"]["half"] / r["base"]["median"]))
        short = sorted({r["name"] for r in a["rows"] if r["base"]["short"]})
        if short:
            lines.append("  short baseline (fewer than %d nights): %s" % (MIN_BASELINE, "; ".join(short)))
    unparsed = sorted({k for n in nights.values() for k in n["unparsed"]})
    if unparsed:
        lines.append("UNPARSED result strings (not analysed): " + ", ".join(unparsed))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--backtest", action="store_true")
    args = ap.parse_args()

    nights, err = collect(args.offline)
    if args.backtest:
        backtest(nights)
        return
    pr = pr_state(args.offline)
    mark_pr(nights, pr, args.offline)
    res = analyse(nights)

    # the commits that arrived together with the PR in its first nightly, per machine
    arrived = {}
    for dut in MACHINES:
        mine = sorted((n for n in nights.values() if n["dut"] == dut), key=lambda n: n["started"])
        pre = [n for n in mine if n["has_pr"] is False and n["sha"]]
        post = [n for n in mine if n["has_pr"] is True and n["sha"]]
        if pre and post:
            arrived[dut] = {"old": pre[-1]["sha"], "new": post[0]["sha"],
                            "commits": commits_between(pre[-1]["sha"], post[0]["sha"], args.offline)}

    now = dt.datetime.now(dt.timezone.utc)
    ev = events(nights)
    lines = summary_lines(res, pr, nights, err)
    status = {"generated": now.strftime("%Y-%m-%d %H:%M UTC"), "pr": pr, "error": err,
              "machines": res, "arrived": arrived, "summary": lines,
              "false_alarms": false_alarms(res, nights)[0],
              "nights": sorted(nights.values(), key=lambda n: n["started"])}
    # The Glimmer table is saved once per date. The page shows every saved table, newest first.
    snap = report.glimmer_snapshot(status)
    log = load("table-log.json", {})
    old = log.get(snap["date"])
    if old is None or (old["head"], old["rows"]) != (snap["head"], snap["rows"]):
        log[snap["date"]] = dict(snap, saved=status["generated"])
        save("table-log.json", log)
        ev = (ev or []) + ["TABLE %s: section \"%s\"" % ("ADDED" if old is None else "UPDATED", snap["title"])]
    status["table_log"] = [log[k] for k in sorted(log, reverse=True)]
    with open(os.path.join(HERE, "status.json"), "w") as f:
        json.dump(status, f, indent=1)
    with open(os.path.join(HERE, "report.html"), "w") as f:
        f.write(report.render(status))
    table = report.snapshot_markdown(snap)

    sys.stdout.reconfigure(encoding="utf-8")   # the table holds the signs for plus-minus and minus
    print("RUN %s" % status["generated"])
    print("\n".join(lines))
    print("GLIMMER TABLE, page section \"%s\" (Markdown, put it in the report to jhan as it is):" % snap["title"])
    print(table)
    if ev is None:
        print("EVENTS: first run, %d nights stored" % len(nights))
    elif ev:
        print("EVENTS:")
        print("\n".join("  " + e for e in ev))
    else:
        print("EVENTS: none since the last run")
    alerts = [l.strip() for l in lines if "SLOWER" in l or "NO GAIN" in l or "TEST FAILED" in l or l.startswith("ERROR")]
    with open(os.path.join(HERE, "log.txt"), "a") as f:
        f.write("%s | PR %s | events %s | alerts %d\n" % (
            status["generated"], pr.get("state"), "first run" if ev is None else len(ev), len(alerts)))
    print("CHANGED=%d ALERTS=%d" % (1 if ev else 0, len(alerts)))


if __name__ == "__main__":
    sys.exit(main())
