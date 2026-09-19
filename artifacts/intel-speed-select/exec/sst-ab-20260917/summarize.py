#!/usr/bin/env python3
"""Summarize the sst-ab-20260917 campaign: results/<name>/rt-results.txt + rt/*.log + power/*/summary.txt.

Words used here: TPS = runtron's per-request "average tok/s" (decode tokens per second per user), averaged over
the requests of one run; TTFT = "Parsing the prompt took S s" (max over the users); app_mhz = mean busy
frequency of the tron app cores during the run (turbostat, 5-s samples); pkg1_w = socket-1 package power.
Paired delta = for one repetition and one cell, arm B's run minus arm A's run (the two runs are back to back).
Writes summary.md to stdout and summary.json next to rt-results.txt.
"""
import sys, re, json, math, os, glob, datetime, statistics as st

RES = sys.argv[1]
HDR = re.compile(r"### runtron kind=(\S+) cell=(\S+) model=(\S+) tp=(\d) users=(\d+) attn=(\S+) prompt=(\d+) len=(\d+) arm=(\S+) rep=(\d+) attempt=(\d+) bin=(\S+) tip=(\S+) (\S+)")

def parse_log(path):
    d = {"tps": [], "ttft": [], "prefill_tps": [], "version": None, "hw_attn": None, "load_tput": None, "gen_tokens": None}
    if not os.path.exists(path): return None
    for line in open(path, errors="replace"):
        m = re.search(r"Version: (\S+) hash: ([0-9a-f]+)", line)
        if m: d["version"] = m[1]
        m = re.search(r"HW attention (enabled|disabled) for model", line)
        if m: d["hw_attn"] = m[1]
        m = re.search(r"Parsing the prompt took ([0-9.]+) s at ([0-9.]+) tokens/s", line)
        if m: d["ttft"].append(float(m[1])); d["prefill_tps"].append(float(m[2]))
        m = re.search(r"Generating (\d+) response tokens with \d+ context took [0-9.]+ s at ([0-9.]+) average tok/s", line)
        if m: d["gen_tokens"] = int(m[1]); d["tps"].append(float(m[2]))
        m = re.search(r"estimated response throughput ([0-9.]+) tok/s", line)
        if m: d["load_tput"] = float(m[1])
    if not d["tps"]: return None
    return d

def parse_power(path):
    out = {}
    if not os.path.exists(path): return out
    for tok in open(path).read().split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            try: out[k] = float(v) if v not in ("None", "") else None
            except ValueError: out[k] = v
    return out

runs = []
for path in sorted(glob.glob(os.path.join(RES, "rt", "*.log"))):
    base = os.path.basename(path)[:-4]
    if ".attempt" in base: continue
    m = re.match(r"(.+?)__(.+?)__rep(\d+)$", base)
    if not m: continue
    cell, arm, rep = m[1], m[2], int(m[3])
    d = parse_log(path)
    if d is None: continue
    p = parse_power(os.path.join(RES, "power", f"{cell}__{arm}__rep{rep}", "summary.txt"))
    runs.append({"cell": cell, "arm": arm, "rep": rep, "tps": st.mean(d["tps"]), "tps_users": d["tps"], "ttft": max(d["ttft"]) if d["ttft"] else None,
                 "prefill_tps": st.mean(d["prefill_tps"]) if d["prefill_tps"] else None, "load_tput": d["load_tput"], "gen_tokens": d["gen_tokens"],
                 "version": d["version"], "hw_attn": d["hw_attn"], "power": p, "mtime": os.path.getmtime(path)})

# header lines carry model names and the machine state
models = {}; starts = {}   # per (cell, arm, rep): start time of the LAST header = the attempt whose log was kept
if os.path.exists(os.path.join(RES, "rt-results.txt")):
    for line in open(os.path.join(RES, "rt-results.txt"), errors="replace"):
        m = HDR.match(line)
        if m and m[1] == "rt":
            models[m[2]] = m[3]
            starts[(m[2], m[9], int(m[10]))] = datetime.datetime.strptime(m[14], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
IDLE_FLAG_S = 300   # a pair whose second run started more than 5 min after the first run's log was written was not back to back
TCRIT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 11: 2.228, 12: 2.201}  # two-sided 95 %, key = n pairs (df = n-1)

def sd(xs): return st.stdev(xs) if len(xs) > 1 else 0.0
def fmt(x, nd=2): return "-" if x is None else f"{x:.{nd}f}"

cells = sorted({r["cell"] for r in runs}, key=lambda c: ["l8b", "q3-4b", "mixtral", "q25-32b"].index(c) if c in ["l8b", "q3-4b", "mixtral", "q25-32b"] else 99)
arms_order = ["boot", "tuned", "tunedplus"]
arms = [a for a in arms_order if any(r["arm"] == a for r in runs)] + sorted({r["arm"] for r in runs} - set(arms_order))

lines = [f"# {os.path.basename(RES.rstrip('/'))} summary", "",
         "Per cell and arm: mean over repetitions (sample sd, CV = sd/mean). TPS = decode tok/s per user; TTFT = prefill s (max over users). app MHz, dev MHz and pkg1 W are means over the turbostat 5-s samples whose app-core mean Busy% > 30; those samples cover prefill and decode together, so they show that the arm took effect and the pkg1 W delta is a whole-run delta, not the power cost of the TPS delta alone. fast cpus = app cpus (of 28) whose mean frequency is above the 2.7 GHz cap; the boot arm leaves 2 of them (126, 127, boot PCT cores) fast.", "",
         "| cell | model | arm | n | TPS/user | sd | CV % | TTFT s | prefill tok/s/user | app MHz | fast cpus | dev MHz | pkg1 W | HW attn | binary version |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
summary = {"cells": {}, "pairs": {}}
for c in cells:
    summary["cells"][c] = {}
    for a in arms:
        rs = [r for r in runs if r["cell"] == c and r["arm"] == a]
        if not rs: continue
        tps = [r["tps"] for r in rs]; ttft = [r["ttft"] for r in rs if r["ttft"] is not None]
        mhz = [r["power"].get("app_mhz") for r in rs if r["power"].get("app_mhz")]
        dmhz = [r["power"].get("dev_mhz") for r in rs if r["power"].get("dev_mhz")]
        pw = [r["power"].get("pkg1_w") for r in rs if r["power"].get("pkg1_w")]
        fast = [r["power"].get("app_cpus_fast") for r in rs if r["power"].get("app_cpus_fast") is not None]
        pf = [r["prefill_tps"] for r in rs if r["prefill_tps"]]
        row = {"n": len(rs), "tps_mean": st.mean(tps), "tps_sd": sd(tps), "tps_cv_pct": 100 * sd(tps) / st.mean(tps), "ttft_mean": st.mean(ttft) if ttft else None,
               "prefill_tps_mean": st.mean(pf) if pf else None, "app_mhz_mean": st.mean(mhz) if mhz else None, "dev_mhz_mean": st.mean(dmhz) if dmhz else None,
               "pkg1_w_mean": st.mean(pw) if pw else None, "fast_cpus_mean": st.mean(fast) if fast else None, "hw_attn": rs[0]["hw_attn"], "version": rs[0]["version"], "tps_runs": tps, "reps": [r["rep"] for r in rs]}
        summary["cells"][c][a] = row
        lines.append(f"| {c} | {models.get(c, '?')} | {a} | {len(rs)} | {fmt(row['tps_mean'])} | {fmt(row['tps_sd'])} | {fmt(row['tps_cv_pct'])} | {fmt(row['ttft_mean'], 3)} | {fmt(row['prefill_tps_mean'], 1)} | {fmt(row['app_mhz_mean'], 0)} | {fmt(row['fast_cpus_mean'], 1)} | {fmt(row['dev_mhz_mean'], 0)} | {fmt(row['pkg1_w_mean'], 1)} | {row['hw_attn'] or '-'} | {row['version'] or '-'} |")

lines += ["", "Paired deltas (same repetition, same cell, runs back to back): B minus A in % of A. t = mean / (sd / sqrt(n)) of the per-repetition % deltas; 95% CI = mean +/- t(0.975, n-1) x sd / sqrt(n); an interval that excludes 0 is p < 0.05 two-sided (n = 6 pairs: |t| > 2.571; n = 5: |t| > 2.776). idle = the longest wait between the two runs of a pair (second run's start minus first run's log time); FLAG marks pairs that were not back to back.", "",
          "| cell | comparison (B vs A) | n pairs | TPS delta % mean +/- 95% CI | sd | t | TTFT delta % mean (negative = faster) | pkg1 W delta mean | max idle between the pair's runs (s) |", "|---|---|---|---|---|---|---|---|---|"]
comps = [("tuned", "boot"), ("tunedplus", "boot"), ("tunedplus", "tuned")]
for c in cells:
    summary["pairs"][c] = {}
    by = {(r["arm"], r["rep"]): r for r in runs if r["cell"] == c}
    for b, a in comps:
        reps = sorted({rep for (arm, rep) in by if arm == a} & {rep for (arm, rep) in by if arm == b})
        if not reps: continue
        dt = [100 * (by[(b, rep)]["tps"] - by[(a, rep)]["tps"]) / by[(a, rep)]["tps"] for rep in reps]
        dtt = [100 * (by[(b, rep)]["ttft"] - by[(a, rep)]["ttft"]) / by[(a, rep)]["ttft"] for rep in reps if by[(a, rep)]["ttft"] and by[(b, rep)]["ttft"]]
        dw = [by[(b, rep)]["power"].get("pkg1_w", 0) - by[(a, rep)]["power"].get("pkg1_w", 0) for rep in reps if by[(a, rep)]["power"].get("pkg1_w") and by[(b, rep)]["power"].get("pkg1_w")]
        gaps = []
        for rep in reps:
            ra, rb = by[(a, rep)], by[(b, rep)]
            first, second = (ra, rb) if ra["mtime"] <= rb["mtime"] else (rb, ra)
            st2 = starts.get((c, second["arm"], rep))
            gaps.append(max(0.0, (st2 - first["mtime"])) if st2 else abs(rb["mtime"] - ra["mtime"]))
        max_gap = max(gaps)
        mean = st.mean(dt); s = sd(dt); t = mean / (s / math.sqrt(len(dt))) if s > 0 and len(dt) > 1 else float("nan")
        ci = TCRIT.get(len(dt), float("nan")) * s / math.sqrt(len(dt)) if len(dt) > 1 else float("nan")
        summary["pairs"][c][f"{b}_vs_{a}"] = {"n": len(dt), "tps_delta_pct": dt, "tps_delta_mean": mean, "tps_delta_sd": s, "t": t,
                                              "ttft_delta_mean": st.mean(dtt) if dtt else None, "pkg1_w_delta_mean": st.mean(dw) if dw else None, "reps": reps,
                                              "idle_s": gaps, "max_idle_s": max_gap, "tps_delta_ci95": ci}
        lines.append(f"| {c} | {b} vs {a} | {len(dt)} | {mean:+.2f} +/- {fmt(ci)} | {fmt(s)} | {fmt(t, 1)} | {fmt(st.mean(dtt) if dtt else None) if dtt else '-'} | {fmt(st.mean(dw), 1) if dw else '-'} | {max_gap:.0f}{' FLAG' if max_gap > IDLE_FLAG_S else ''} |")

summary["runs"] = runs
summary["models"] = models
json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1, default=str)
print("\n".join(lines))
