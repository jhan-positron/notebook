#!/usr/bin/env python3
"""final8.py - every number of the tackle-8mb investigation that a final report needs.

Reads all result folders of rounds 1 to 4 under the results folder and writes
  final8.json   machine-readable: every number, with the folder names it came from
  final8.txt    the same as readable text, one block per item
It can be run again at any time. A step or a session without a folder is reported as missing.
Blocks 1 to 15 hold the numbers and the verdicts by the recorded rules. Block 16 holds supplementary
evaluations that were defined after the data was seen. They never replace a recorded verdict.

  final8.py [--results DIR] [--out-dir DIR] [--summary s12-summary.json]

Standard library only. Helpers (not changed): levels9.py, h2_analyze.py.

Words used here
  step       one batch of processes of a run script; its result folder is <prefix>-<STEP>-s<session>-<UTC>.
  session    one visit set on the test machine: 1 or 2.
  cell       the processes of one step, kernel, size, CPU and session.
  rate       bytes / time of a window, in GB/s (1 GB = 1e9 bytes).
  level      a rate at which a process stays (levels9.py finds a low and a high level, or one level).
  record index  position of a window among all windows of its process, in time order, from 0. The runner
             stores window i in the record win[i].
  switch window  record index of the first window that ends after the estimated switch time. A switch at a
             window boundary gets the index of the window after the boundary.
  reading:   a detail that the decisions file leaves open. The simplest reading is used and marked.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import levels9 as L          # noqa: E402
import h2_analyze as H2      # noqa: E402

RESULTS = os.path.normpath(os.path.join(HERE, "..", "..", "results"))
K32, M1, M4, M8, M16 = 32 << 10, 1 << 20, 4 << 20, 8 << 20, 16 << 20
STEPS = ["B6W", "S2", "S4", "XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF", "H2", "YA", "YL", "YP", "YC", "YF",
         "ZA", "ZC", "ZD", "ZN", "ZM", "ZS"]
SESSION1_ONLY = ("XEV", "YA", "ZA")
FOLDER_RE = re.compile(r"^bwx\d+-([A-Za-z0-9]+)-s(\d+)-\d{8}T\d{6}Z$")
H2_RE = re.compile(r"^h2-s(\d+)-\d{8}T\d{6}Z$")
LOAD_ONLY = ("read", "asmread")
med = L.median

READINGS = []


def reading(text):
    """Registers one 'reading:' choice and returns the line for the text output."""
    if text not in READINGS:
        READINGS.append(text)
    return "reading: " + text


# ------------------------------------------------------------------ small helpers
def fx(x, nd=2):
    return "NA" if x is None else "%.*f" % (nd, x)


def fl(v, nd=2):
    return "[" + " ".join(fx(x, nd) for x in v) + "]"


def size_label(n):
    if n % (1 << 20) == 0:
        return "%dM" % (n >> 20)
    if n % (1 << 19) == 0:
        return "%.1fM" % (n / float(1 << 20))
    if n % 1024 == 0:
        return "%dK" % (n >> 10)
    return str(n)


def ck(cpu, ses):
    return "cpu%d/s%d" % (cpu, ses)


def tbl(head, rows, indent="  "):
    """Text table: columns padded to the widest entry."""
    rows = [[str(c) for c in r] for r in rows]
    w = [len(h) for h in head]
    for r in rows:
        for i, c in enumerate(r):
            w[i] = max(w[i], len(c))
    out = [indent + "  ".join(h.ljust(w[i]) for i, h in enumerate(head)).rstrip()]
    for r in rows:
        out.append(indent + "  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip())
    return out


def win_ms(p):
    """Requested window length of the first trial, in ms (None if the S row is missing)."""
    for t in sorted(p.S):
        try:
            return int(p.S[t][7])
        except (ValueError, IndexError):
            return None
    return None


def same_sign(vals):
    return bool(vals) and (all(v > 0 for v in vals) or all(v < 0 for v in vals))


def missing_sessions(sessions):
    return [s for s in (1, 2) if s not in sessions]


# ------------------------------------------------------------------ data access
class Data:
    """Result folders found by name. procs(step, session) parses on first use."""

    def __init__(self, results):
        self.results = results
        self.folders = {}
        for d in sorted(glob.glob(os.path.join(results, "*"))):
            if not os.path.isdir(d):
                continue
            b = os.path.basename(d)
            m = FOLDER_RE.match(b)
            key = None
            if m and m.group(1) in STEPS and m.group(1) != "H2":
                key = (m.group(1), int(m.group(2)))
            else:
                m = H2_RE.match(b)
                if m:
                    key = ("H2", int(m.group(1)))
            if key:
                self.folders.setdefault(key, []).append(d)
        self._procs = {}

    def sessions(self, *steps):
        return sorted(set(s for (st, s) in self.folders if st in steps))

    def names(self, step, ses):
        return [os.path.basename(d) for d in self.folders.get((step, ses), [])]

    def procs(self, step, ses):
        """Processes of one step and session, over all its folders. A process index that occurs twice (a
        continued step) keeps the later copy unless that copy did not end. Processes with a killed or failed
        line, and processes with a trial that has W rows and no E row (a csv file that was copied while its
        step ran ends with such a process), stay out of every statistic; the inventory counts them."""
        key = (step, ses)
        if key not in self._procs:
            by, extra = {}, []
            for d in self.folders.get(key, []):
                for p in L.load([d]):
                    if p.ended or not p.W or set(w.trial for w in p.W) - set(p.E):
                        continue
                    try:
                        p.cpu_i = int(p.cpu)
                    except ValueError:
                        p.cpu_i = -1
                    p.ses = ses
                    if p.idx < 0:
                        extra.append(p)
                    else:
                        by[p.idx] = p
            self._procs[key] = [by[i] for i in sorted(by)] + extra
        return self._procs[key]


def group(procs, keyf):
    out = {}
    for p in procs:
        out.setdefault(keyf(p), []).append(p)
    return out


def cell_stats(plist):
    """Cell values of S2-style processes as 'levels9.py cells' defines them: per process the median, 5th and
    95th percentile of all windows of the kernel and size; the cell value is the median over the processes."""
    vals = [(p, L.proc_cell_values(p)) for p in plist]
    vals = [(p, v) for p, v in vals if v]
    return {"n": len(vals),
            "median": med([v["med_all"] for _, v in vals]),
            "p95": med([v["p95"] for _, v in vals]),
            "p5": med([v["p5"] for _, v in vals]),
            "fourth": med([v["fourth"] for _, v in vals if v["fourth"] is not None]),
            "proc_median": [v["med_all"] for _, v in vals],
            "proc_p95": [v["p95"] for _, v in vals],
            "proc_p5": [v["p5"] for _, v in vals]}


def cells_of(procs):
    """{(kernel, size, cpu): cell_stats} of the processes of one step and session."""
    return {k: cell_stats(v) for k, v in group(procs, lambda p: (p.kernel, p.size, p.cpu_i)).items()}


def rec_windows(p):
    """All windows of the process in time order; the position is the record index."""
    return sorted(p.W, key=lambda w: w.t_start)


def index_switches(p):
    """Level description of the main sequence of a process, with record indices.

    Returns None for fewer than levels9.MIN_SEQ windows, else a dict: low, high (None for one level),
    labels (one per window of the main sequence), index (record index per window of the main sequence),
    switches: list of dict(kind 'up' or 'fall', index, t)."""
    ws, seg = L.segment_proc(p)
    if seg is None:
        return None
    pos = {id(w): i for i, w in enumerate(rec_windows(p))}
    idx = [pos[id(w)] for w in ws]
    sw = []
    for s in seg["switches"]:
        j = next((k for k, w in enumerate(ws) if w.te > s["t"]), len(ws) - 1)
        sw.append({"kind": "up" if s["kind"] == "up" else "fall", "index": idx[j], "t": s["t"]})
    return {"low": seg["low"], "high": seg["high"], "labels": seg["labels"], "index": idx, "switches": sw,
            "n": len(ws)}


def counter_proc(p):
    """Medians over the counted target windows that are not multiplexed: rate and count per 64 B per event."""
    wins = L.counter_windows(p)
    good = [w for w in wins if not w["mux"]]
    ev = p.events
    out = {"n": len(good), "mux": len(wins) - len(good), "rate": med([w["rate"] for w in good]), "per64": {}}
    for i, e in enumerate(ev):
        out["per64"][e] = med([L.per64(w["counts"][i], w["bytes"]) for w in good
                               if i < len(w["counts"]) and w["counts"][i] is not None])
    return out


def evict_of(p):
    try:
        return int(p.M.get("evict_mb", "0") or 0)
    except ValueError:
        return 0


def pad_of(p):
    try:
        return int(p.M.get("rec_pad", "0") or 0)
    except ValueError:
        return 0


# ------------------------------------------------------------------ item 1: inventory
def scan_folder(folder):
    n = killed = failed = xrows = incomplete = 0
    utcs, loads = [], []
    wt, et = set(), set()        # trials of the current process with a W row, with an E row
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        with open(path) as f:
            for line in f:
                if line.startswith("-- step ") or line.startswith("-- binary "):
                    n += 1
                    incomplete += 1 if wt - et else 0
                    wt, et = set(), set()
                    m = re.search(r" utc (\S+)", line)
                    if m:
                        utcs.append(m.group(1))
                elif line.startswith("-- killed"):
                    killed += 1
                elif line.startswith("-- failed"):
                    failed += 1
                elif line.startswith("X,"):
                    xrows += 1
                elif line.startswith("W,") or line.startswith("E,"):
                    (wt if line[0] == "W" else et).add(line.split(",", 2)[1])
        incomplete += 1 if wt - et else 0
        wt, et = set(), set()
    lp = os.path.join(folder, "launches.txt")
    if os.path.exists(lp):
        with open(lp) as f:
            for line in f:
                m = re.match(r"^== .*\bloadavg (\S+)", line)
                if m:
                    try:
                        loads.append(float(m.group(1)))
                    except ValueError:
                        pass
    return {"folder": os.path.basename(folder), "processes": n, "first_launch_utc": utcs[0] if utcs else None,
            "last_launch_utc": utcs[-1] if utcs else None, "launches_with_load": len(loads),
            "load_min": min(loads) if loads else None, "load_median": med(loads),
            "load_max": max(loads) if loads else None, "killed": killed, "failed": failed, "x_rows": xrows,
            "incomplete": incomplete}


def item1(data):
    rows, T = [], ["1. INVENTORY", "",
                   "Load = first value of 'loadavg' in launches.txt (1 minute load average before each process).",
                   "Launch times are the UTC time of day of the launch lines of the csv file.",
                   "incomplete = processes with a trial that has W rows and no E row (the file was cut). They and the",
                   "processes with a killed or failed line are left out of every statistic below."]
    out = []
    for step in STEPS:
        for ses in (1, 2):
            fs = data.folders.get((step, ses), [])
            if not fs:
                if ses == 2 and step in SESSION1_ONLY:
                    continue
                rows.append({"step": step, "session": ses, "folder": None})
                out.append([step, ses, "MISSING", "", "", "", "", "", "", "", ""])
                continue
            for d in fs:
                r = scan_folder(d)
                r.update(step=step, session=ses)
                rows.append(r)
                out.append([step, ses, r["folder"], r["processes"], r["first_launch_utc"], r["last_launch_utc"],
                            "%s / %s / %s" % (fx(r["load_min"]), fx(r["load_median"]), fx(r["load_max"])),
                            r["killed"], r["failed"], r["incomplete"], r["x_rows"]])
    T += tbl(["step", "ses", "folder", "procs", "first", "last", "load min / median / max", "killed", "failed",
              "incomplete", "X rows"], out)
    return {"rows": rows}, T


# ------------------------------------------------------------------ item 2: round 1
def item2(data, summary_path):
    T = ["2. ROUND 1 (step S2): rates of the fourth target window, new minus old, P1, P2, decomposition", ""]
    J = {"source": None, "cells": [], "P1": None, "P2": None, "candidate": None, "folders": {}}
    S = None
    if summary_path and os.path.exists(summary_path):
        with open(summary_path) as f:
            S = json.load(f)
    covered = set(S.get("folders", [])) if S else set()
    stage2 = (S or {}).get("stage2") or {}
    for ses in (1, 2):
        names = data.names("S2", ses)
        J["folders"]["s%d" % ses] = names
        if not names:
            T.append("session %d: S2 folder missing." % ses)
            continue
        use_summary = bool(stage2) and all(n in covered for n in names)
        procs = data.procs("S2", ses)
        byc = group(procs, lambda p: (p.cpu_i, p.size, p.kernel))
        for cpu in sorted(set(p.cpu_i for p in procs)):
            sc = (stage2.get("cells") or {}).get(ck(cpu, ses)) if use_summary else None
            for size in (K32, M1, M4, M8, M16):
                row = {"size": size_label(size), "cpu": cpu, "session": ses,
                       "source": os.path.basename(summary_path) if sc else "recomputed with levels9"}
                z = (sc or {}).get("sizes", {}).get(size_label(size))
                if z:
                    for k in ("oldread", "read", "asmread"):
                        row[k] = z["rates"][k]["fourth"]["filtered"]["median"]
                    for name in ("new_minus_old", "asm_minus_old"):
                        c = z[name]["fourth"]["filtered"]
                        row[name] = {"median": c["median"], "sets": [u["value"] for u in c["units"]],
                                     "limit": c["limit"], "repeatable": c["repeatable"],
                                     "gain_pct": (c.get("gain_pct") or {}).get("median")}
                else:
                    row["source"] = "recomputed with levels9"
                    f4 = {}
                    for k in ("oldread", "read", "asmread"):
                        pl = byc.get((cpu, size, k), [])
                        f4[k] = {p.M.get("plan.rep_set", str(i)): (L.proc_cell_values(p) or {}).get("fourth")
                                 for i, p in enumerate(pl)}
                        row[k] = med([v for v in f4[k].values() if v is not None])
                    for name, k in (("new_minus_old", "read"), ("asm_minus_old", "asmread")):
                        sets = [f4[k][r] - f4["oldread"][r] for r in sorted(f4[k])
                                if f4[k][r] is not None and f4["oldread"].get(r) is not None]
                        gains = [100.0 * (f4[k][r] / f4["oldread"][r] - 1.0) for r in sorted(f4[k])
                                 if f4[k][r] is not None and f4["oldread"].get(r)]
                        row[name] = {"median": med(sets), "sets": sets, "limit": None, "repeatable": None,
                                     "gain_pct": med(gains)}
                J["cells"].append(row)
            if sc:
                dec = sc["decomposition"]["filtered"]
                sh = dec.get("shares") or {}
                J.setdefault("per_cell", {})[ck(cpu, ses)] = {
                    "P1": {"outcome": sc["P1"]["filtered"]["outcome"], "median": sc["P1"]["filtered"]["median"],
                           "limit": sc["P1"]["filtered"]["limit"],
                           "largest_abs_plus_limit": sc["P1"]["filtered"]["largest_abs_plus_limit"],
                           "margin": sc["P1"]["filtered"]["margin"]},
                    "P2": {k: {"median": sc["P2"][k]["filtered"]["median"], "limit": sc["P2"][k]["filtered"]["limit"],
                               "repeatable": sc["P2"][k]["filtered"]["repeatable"],
                               "sign": sc["P2"][k]["filtered"]["sign"]} for k in sc["P2"]},
                    "decomposition": {"resolved": dec.get("resolved"),
                                      "dG_median": dec["dG"]["median"],
                                      "new_term_median": dec["new_term"]["median"],
                                      "old_term_median": dec["old_term"]["median"],
                                      "new_share_pct": (sh.get("new_share_pct") or {}).get("median"),
                                      "old_share_pct": (sh.get("old_share_pct") or {}).get("median")}}
    if stage2:
        J["source"] = os.path.basename(summary_path)
        J["P1"], J["P2"], J["candidate"] = stage2.get("P1"), stage2.get("P2"), stage2.get("candidate")
        J["confirm"] = stage2.get("confirm")
    rows = []
    for r in J["cells"]:
        nm = r["new_minus_old"]
        rows.append([r["size"], r["cpu"], r["session"], fx(r["oldread"]), fx(r["read"]), fx(r["asmread"]),
                     fx(nm["median"]), fl(nm["sets"]), fx(nm["gain_pct"]),
                     "NA" if nm["repeatable"] is None else ("yes" if nm["repeatable"] else "no"),
                     r["source"]])
    T.append("Cell medians in GB/s (6 processes). 'new - old' = read minus oldread per matched set (6 values).")
    T += tbl(["size", "cpu", "ses", "oldread", "read", "asmread", "new - old", "six set values", "gain %",
              "repeatable", "source"], rows)
    T.append("")
    for key in sorted(J.get("per_cell", {})):
        c = J["per_cell"][key]
        T.append("  %s: P1 %s (old 8M - old 1M median %s GB/s, largest |d| + limit %s, margin %s). "
                 "P2 read %s GB/s (%s), asmread %s GB/s (%s). Decomposition: new loop %s %%, old loop %s %% "
                 "of the lost advantage (resolved: %s)." % (
                     key, c["P1"]["outcome"], fx(c["P1"]["median"], 3), fx(c["P1"]["largest_abs_plus_limit"], 3),
                     fx(c["P1"]["margin"], 2), fx(c["P2"]["read"]["median"]),
                     "repeatable" if c["P2"]["read"]["repeatable"] else "not repeatable",
                     fx(c["P2"]["asmread"]["median"]),
                     "repeatable" if c["P2"]["asmread"]["repeatable"] else "not repeatable",
                     fx(c["decomposition"]["new_share_pct"], 1), fx(c["decomposition"]["old_share_pct"], 1),
                     c["decomposition"]["resolved"]))
    if J["P1"]:
        T.append("  P1 overall: %s. Per CPU: %s." % (J["P1"].get("overall"), ", ".join(
            "%s %s" % (c, v.get("outcome")) for c, v in sorted(J["P1"].get("per_cpu", {}).items()))))
        for k in sorted(J["P2"] or {}):
            T.append("  P2 %s: %s. Confirmed on both CPUs: %s." % (k, ", ".join(
                "%s %s" % (c, v.get("outcome")) for c, v in sorted(J["P2"][k].get("per_cpu", {}).items())),
                "yes" if J["P2"][k].get("confirmed_both") else "no"))
        for name in ("new_minus_old@8M", "new_minus_old@16M", "new_minus_old@1M"):
            c = (J.get("confirm") or {}).get(name)
            if c:
                T.append("  %s: confirmed on both CPUs: %s, sign %s." % (
                    name, "yes" if c.get("confirmed_both") else "no", c.get("sign")))
    else:
        T.append("  P1, P2 and the decomposition are not recomputed here: run analyze8.py summary on the S2 folders.")
    return J, T


# ------------------------------------------------------------------ item 3: size curve
def item3(data):
    T = ["3. SIZE CURVE (steps S2, XF, ZS)", "",
         "median = median over the processes of the process median of all windows. p5, p95 = median over the",
         "processes of the 5th and 95th percentile window rate. GB/s."]
    rows, out = [], []
    for step in ("S2", "XF", "ZS"):
        for ses in (1, 2):
            if not data.names(step, ses):
                T.append("  %s session %d missing." % (step, ses))
                continue
            for (kernel, size, cpu), c in cells_of(data.procs(step, ses)).items():
                rows.append({"step": step, "kernel": kernel, "size_bytes": size, "size": size_label(size), "cpu": cpu,
                             "session": ses, "n": c["n"], "median": c["median"], "p5": c["p5"], "p95": c["p95"],
                             "folders": data.names(step, ses)})
    rows.sort(key=lambda r: (r["kernel"] != "oldread", r["kernel"], r["size_bytes"], r["cpu"], r["session"],
                             r["step"]))
    for r in rows:
        out.append([r["kernel"], r["size"], r["cpu"], r["session"], r["step"], r["n"], fx(r["median"]), fx(r["p5"]),
                    fx(r["p95"])])
    T += tbl(["kernel", "size", "cpu", "ses", "step", "procs", "median", "p5", "p95"], out)
    return {"rows": rows}, T


# ------------------------------------------------------------------ item 4: levels in sustained runs
def level_cell(plist):
    two, one = [], []
    nhigh = nlow = 0
    for p in plist:
        d = index_switches(p)
        if d is None:
            continue
        if d["high"] is None:
            one.append(d["low"])
        else:
            two.append((d["low"], d["high"]))
            nhigh += d["labels"].count("high")
            nlow += d["labels"].count("low")
    return {"processes": len(two) + len(one), "two_levels": len(two), "one_level": len(one),
            "low": med([a for a, _ in two]), "high": med([b for _, b in two]),
            "share_high": (nhigh / float(nhigh + nlow)) if nhigh + nlow else None,
            "one_level_rates": one}


def item4(data):
    T = ["4. LEVELS IN SUSTAINED RUNS (steps S4, XW, XCA, XCB, XCC)", "",
         "low, high = median over the processes with two levels of the level medians (GB/s).",
         "share high = windows at the high level / windows at the low or the high level, over those processes.",
         "one-level rates = the level median of each process with one level."]
    rows, out = [], []
    for step in ("S4", "XW", "XCA", "XCB", "XCC"):
        for ses in (1, 2):
            if not data.names(step, ses):
                T.append("  %s session %d missing." % (step, ses))
                continue
            procs = [p for p in data.procs(step, ses) if step in ("S4", "XW") or p.size == M8]
            for (cond, kernel, size, cpu), pl in sorted(group(
                    procs, lambda p: (p.cond, p.kernel, p.size, p.cpu_i)).items()):
                c = level_cell(pl)
                c.update(step=step, cond=cond, kernel=kernel, size=size_label(size), cpu=cpu, session=ses,
                         folders=data.names(step, ses))
                rows.append(c)
                out.append([step, cond, cpu, ses, c["processes"], c["two_levels"], c["one_level"], fx(c["low"]),
                            fx(c["high"]), fx(c["share_high"], 3), fl(c["one_level_rates"])])
    T += tbl(["step", "condition", "cpu", "ses", "procs", "two levels", "one level", "low", "high", "share high",
              "one-level rates"], out)
    return {"rows": rows}, T


# ------------------------------------------------------------------ item 5: switch timing
def cluster_events(events, width=0.15):
    """events: list of (t, index, proc id). Sorted times are cut where two neighbours are more than `width`
    apart. Returns clusters in time order."""
    out, cur = [], []
    for e in sorted(events):
        if cur and e[0] - cur[-1][0] > width:
            out.append(cur)
            cur = []
        cur.append(e)
    if cur:
        out.append(cur)
    res = []
    for c in out:
        ts = [e[0] for e in c]
        res.append({"n": len(c), "processes": len(set(e[2] for e in c)), "t_median_s": med(ts),
                    "t_min_s": ts[0], "t_max_s": ts[-1], "spread_s": ts[-1] - ts[0],
                    "index_median": med([e[1] for e in c])})
    return res


ONSET_S4_S = 6.4       # s: the S4 first-up time that rule 5 of round 2 names
SAMPLER_KEYS = ("w.nivcsw", "sirq.TIMER", "sirq.SCHED", "sirq.RCU")


def onset_verdict(t_proc, t_tgt):
    """Rule 5 of round 2 for one condition: lists of first-up times since process start and since target start."""
    if not t_proc:
        return {"verdict": "no up switch in this condition", "median_since_process_start": None,
                "median_since_target_start": None, "n": 0}
    mp, mt = med(t_proc), med(t_tgt)
    dp, dt = abs(mp - ONSET_S4_S), abs(mt - ONSET_S4_S)
    if dp <= 0.6 and dt <= 0.6:
        v = "both predictions fit (the condition does not separate them)"
    elif dp <= 0.6:
        v = "tied to the process start" + ("; target-start prediction rejected" if dt > 1.5 else "")
    elif dt <= 0.6:
        v = "tied to the start of the target" + ("; process-start prediction rejected" if dp > 1.5 else "")
    else:
        v = "other time base"
    return {"verdict": v, "median_since_process_start": mp, "median_since_target_start": mt, "n": len(t_proc)}


def sampler_verdict(per_cpu, key):
    """Rule 4 of round 2 for one key. per_cpu: {cpu: dict(share_up, share_down, base)}."""
    res = {}
    for kind in ("up", "down"):
        ok = len(per_cpu) >= 2          # the rule says "on both CPUs"
        for c in per_cpu.values():
            s, b = c.get("share_" + kind), c.get("base")
            if s is None or b is None or not (s >= 0.8 and s >= 3.0 * b):
                ok = False
        res[kind] = ok
    return res


def item5(data):
    T = ["5. SWITCH TIMING", ""]
    J = {"S4": {}, "XW_onset": {}, "XW_sampler": {}}
    T.append(reading("a fall or an up is 'recurring' when at least 3 processes of the session show it inside "
                     "one cluster (pooled switch times cut at gaps above 0.15 s); CPUs and the two load-only "
                     "kernels are pooled."))
    for ses in (1, 2):
        if not data.names("S4", ses):
            T.append("S4 session %d missing." % ses)
            continue
        ev = {"fall": [], "up": []}
        wlen = []
        for p in data.procs("S4", ses):
            d = index_switches(p)
            if d is None:
                continue
            if win_ms(p):
                wlen.append(win_ms(p) / 1000.0)
            for s in d["switches"]:
                ev[s["kind"]].append((s["t"], s["index"], "%d:%s" % (p.cpu_i, p.tag)))
        w = med(wlen) or 0.3
        js = {"folders": data.names("S4", ses), "window_s": w}
        T.append("")
        T.append("S4 session %d (%s), window length %.1f s. Times are est., in s since process start." % (
            ses, ", ".join(js["folders"]), w))
        for kind in ("fall", "up"):
            cl = cluster_events(ev[kind])
            for c in cl:
                c["t_median_windows"] = c["t_median_s"] / w
                c["spread_windows"] = c["spread_s"] / w
            rec = [c for c in cl if c["processes"] >= 3]
            js[kind + "_clusters"] = cl
            js[kind + "_recurring"] = rec
            T.append("  recurring %ss (%d of %d clusters):" % (kind, len(rec), len(cl)))
            T += tbl(["time s", "time in windows", "switch window", "processes", "spread s", "spread in windows"],
                     [[fx(c["t_median_s"], 3), fx(c["t_median_windows"], 2), fx(c["index_median"], 1),
                       c["processes"], fx(c["spread_s"], 3), fx(c["spread_windows"], 3)] for c in rec], "    ")
        fi = [c["index_median"] for c in js["fall_recurring"]]
        js["fall_intervals_windows"] = [fi[i + 1] - fi[i] for i in range(len(fi) - 1)]
        ft = [c["t_median_s"] for c in js["fall_recurring"]]
        js["fall_intervals_s"] = [ft[i + 1] - ft[i] for i in range(len(ft) - 1)]
        T.append("  intervals between successive recurring falls: %s windows (from the switch windows), %s s" % (
            fl(js["fall_intervals_windows"], 1), fl(js["fall_intervals_s"], 2)))
        J["S4"]["s%d" % ses] = js
    # XW onset (rule 5) and sampler (rule 4)
    T.append("")
    T.append("XW onset (rule 5 of round 2). First up switch per process, est., in s.")
    T.append(reading("the S4 first-up time of rule 5 is the fixed value %.1f s that the rule names; the median "
                     "is taken over the processes of both CPUs of a session that show an up switch."
                     % ONSET_S4_S))
    for ses in (1, 2):
        if not data.names("XW", ses):
            T.append("  XW session %d missing." % ses)
            continue
        procs = data.procs("XW", ses)
        jo = {"folders": data.names("XW", ses), "rows": [], "conditions": {}}
        out = []
        for cond, pl in sorted(group(procs, lambda p: p.cond).items()):
            allp, allt = [], []
            for cpu, pc in sorted(group(pl, lambda p: p.cpu_i).items()):
                tp, tt = [], []
                for p in pc:
                    d = index_switches(p)
                    up = next((s["t"] for s in (d["switches"] if d else []) if s["kind"] == "up"), None)
                    ts = p.trial_starts()
                    t0 = ts[0][2] if ts and ts[0][2] is not None else 0.0
                    tp.append(up)
                    tt.append(None if up is None else up - t0)
                row = {"cond": cond, "cpu": cpu, "since_process_start": tp, "since_target_start": tt,
                       "median_since_process_start": med([x for x in tp if x is not None]),
                       "median_since_target_start": med([x for x in tt if x is not None])}
                jo["rows"].append(row)
                out.append([cond, cpu, fl(tp), fx(row["median_since_process_start"]), fl(tt),
                            fx(row["median_since_target_start"])])
                allp += [x for x in tp if x is not None]
                allt += [x for x in tt if x is not None]
            v = onset_verdict(allp, allt)
            v["has_previous_activity"] = "prev=none" not in cond
            jo["conditions"][cond] = v
        T.append("  session %d (%s):" % (ses, ", ".join(jo["folders"])))
        T += tbl(["condition", "cpu", "since process start", "median", "since target start", "median"], out, "    ")
        for cond, v in sorted(jo["conditions"].items()):
            if v["has_previous_activity"]:
                T.append("    rule 5, %s: median %s s since process start, %s s since target start (%d processes): %s."
                         % (cond, fx(v["median_since_process_start"]), fx(v["median_since_target_start"]), v["n"],
                            v["verdict"]))
        J["XW_onset"]["s%d" % ses] = jo
    T.append("")
    T.append("XW sampler (rule 4 of round 2). share = share of the fully sampled switches with a change of the key")
    T.append("within 0.15 s. base = share of all spans of the same width with a change (levels9.py watch).")
    for ses in (1, 2):
        if not data.names("XW", ses):
            continue
        js = {"folders": data.names("XW", ses), "cpus": {}, "keys": {}, "errors": []}
        per_key = {}
        for cpu, pc in sorted(group(data.procs("XW", ses), lambda p: p.cpu_i).items()):
            stats = []
            for p in pc:
                path = L.watch_files(p.folder).get(p.idx)
                if path is None:
                    continue
                try:
                    st = L.watch_proc(p, path)[1]
                except (OSError, ValueError, KeyError, IndexError) as e:
                    js["errors"].append("%s: %s" % (os.path.basename(path), e))
                    continue
                if st is not None:
                    stats.append(st)
            if not stats:
                continue
            pw = L.pool_watch(stats)
            js["cpus"][str(cpu)] = {"up_switches": pw["n"]["up"], "down_switches": pw["n"]["down"],
                                    "processes": len(stats)}
            for k in pw["keys"]:
                if k in SAMPLER_KEYS or k.startswith("th."):
                    r = pw["tab"][k]
                    per_key.setdefault(k, {})[cpu] = {
                        "share_up": r["up"] / float(pw["n"]["up"]) if pw["n"]["up"] else None,
                        "share_down": r["down"] / float(pw["n"]["down"]) if pw["n"]["down"] else None,
                        "base": r["grid"] / float(pw["grid_n"]) if pw["grid_n"] else None}
        cpus = sorted(int(c) for c in js["cpus"])
        out = []
        for k in sorted(per_key, key=lambda k: (k not in SAMPLER_KEYS, k)):
            full = {c: per_key[k].get(c, {"share_up": 0.0 if js["cpus"][str(c)]["up_switches"] else None,
                                           "share_down": 0.0 if js["cpus"][str(c)]["down_switches"] else None,
                                           "base": 0.0}) for c in cpus}
            v = sampler_verdict(full, k)
            js["keys"][k] = {"per_cpu": {str(c): full[c] for c in cpus}, "accompanies_up": v["up"],
                             "accompanies_down": v["down"]}
            out.append([k] + [x for c in cpus for x in (fx(full[c]["share_up"], 3), fx(full[c]["share_down"], 3),
                                                        fx(full[c]["base"], 3))]
                       + ["yes" if v["up"] else "no", "yes" if v["down"] else "no"])
        js["any_key_accompanies"] = any(v["accompanies_up"] or v["accompanies_down"] for v in js["keys"].values())
        T.append("  session %d (%s): %s" % (ses, ", ".join(js["folders"]), "; ".join(
            "CPU %s: %d up and %d down switches in %d processes" % (c, v["up_switches"], v["down_switches"],
                                                                     v["processes"])
            for c, v in sorted(js["cpus"].items(), key=lambda x: int(x[0])))))
        T += tbl(["key"] + [h for c in cpus for h in ("up cpu%d" % c, "down cpu%d" % c, "base cpu%d" % c)]
                 + ["accompanies up", "accompanies down"], out, "    ")
        T.append("    rule 4 (share at least 0.8 and at least 3 times the base, on both CPUs): %s." % (
            "at least one key accompanies the switches" if js["any_key_accompanies"]
            else "no listed key accompanies the switches"))
        for e in js["errors"]:
            T.append("    sampler file not used: %s" % e)
        J["XW_sampler"]["s%d" % ses] = js
    return J, T


# ------------------------------------------------------------------ item 6: counters by level
def rule3_event(pairs, need=3):
    """Rule 3 of round 2 for one event on one CPU in one session.

    pairs: per process that shows both levels: (per-window values at the low level, at the high level), counts
    per 64 B. Returns dict(verdict, diffs, median_diff, spread, sign)."""
    pairs = [(a, b) for a, b in pairs if a and b]
    if len(pairs) < need:
        return {"verdict": "Insufficient data: %d processes with both levels (rule needs %d)" % (len(pairs), need),
                "diffs": [med(a) - med(b) for a, b in pairs], "median_diff": None, "spread": None, "sign": None,
                "differs": None}
    diffs = [med(a) - med(b) for a, b in pairs]
    spread = max(0.5 * (max(v) - min(v)) for a, b in pairs for v in (a, b))
    m = med(diffs)
    differs = same_sign(diffs) and abs(m) > 2.0 * spread
    return {"verdict": "differs" if differs else "does not differ", "diffs": diffs, "median_diff": m,
            "spread": spread, "sign": (1 if m > 0 else -1) if differs else None, "differs": differs}


def rule3_overall(per_cell):
    """per_cell: {'cpuC/sS': result of rule3_event}. Confirmed needs both sessions and both CPUs, one sign."""
    ses = sorted(set(int(k.split("/s")[1]) for k in per_cell))
    miss = missing_sessions(ses)
    if miss:
        return "session %s missing: not confirmed yet" % ", ".join(str(s) for s in miss)
    if len(per_cell) >= 4 and all(v["differs"] for v in per_cell.values()) and \
            len(set(v["sign"] for v in per_cell.values())) == 1:
        return "confirmed: differs between the levels"
    if all(v["differs"] is False for v in per_cell.values()):
        return "does not differ"
    return "not confirmed"


def level_ref(data, step, cpu, sessions):
    """Median low and high level of the load-only 8 MiB processes of a step on one CPU, over the given sessions."""
    lo, hi, ups = [], [], []
    for ses in sessions:
        for p in data.procs(step, ses):
            if p.cpu_i != cpu or p.kernel not in LOAD_ONLY or p.size != M8 or "prev=" in p.cond and \
                    "prev=none" not in p.cond:
                continue
            d = index_switches(p)
            if d and d["high"] is not None:
                lo.append(d["low"])
                hi.append(d["high"])
                ups += [s["index"] for s in d["switches"] if s["kind"] == "up"]
    return med(lo), med(hi), ups, len(lo)


def item6(data):
    T = ["6. COUNTERS BY LEVEL (steps XCA, XCB, XCC; rule 3 of round 2) and the acceptance check of rule 1", "",
         "Counts per 64 B read, medians over the windows of a level. 'one' = processes with one level.",
         "low - high = per process with both levels: median at low minus median at high."]
    J = {"rows": [], "rule3": {}, "acceptance": []}
    T.append(reading("rule 3 pools the 2 'read' and the 2 'asmread' processes at 8 MiB of one CPU as 'the 4 "
                     "load-only processes'; the within-level spread is the largest half range over both levels "
                     "of those processes."))
    for step in ("XCA", "XCB", "XCC"):
        for ses in (1, 2):
            if not data.names(step, ses):
                T.append("  %s session %d missing." % (step, ses))
                continue
            procs = data.procs(step, ses)
            cells = L.counter_table(procs)
            out = []
            for key in sorted(cells, key=lambda k: (k[3], k[2], int(k[4]) if str(k[4]).isdigit() else 0)):
                _, _, kernel, size, cpu, _ = key
                cell = cells[key]
                for e in cell["events"]:
                    lv = {lev: cell["pooled"][lev]["per64"][e] for lev in cell["pooled"]}
                    single = lv.get("one", lv.get("unsplit"))
                    diffs = [d for _, d in cell["diff"][e] if d is not None]
                    J["rows"].append({"step": step, "event": e, "kernel": kernel, "size": size_label(size),
                                      "cpu": int(cpu), "session": ses, "low": lv.get("low"), "high": lv.get("high"),
                                      "single": single, "low_minus_high": diffs, "processes": len(cell["procs"]),
                                      "multiplexed_windows": cell["mux"], "folders": data.names(step, ses)})
                    out.append([e, kernel, size_label(size), cpu, ses, "%.6g" % lv["low"] if lv.get("low") is not None
                                else "-", "%.6g" % lv["high"] if lv.get("high") is not None else "-",
                                "%.6g" % single if single is not None else "-",
                                "[" + " ".join("%.4g" % d for d in diffs) + "]"])
            T.append("")
            T.append("%s session %d (%s):" % (step, ses, ", ".join(data.names(step, ses))))
            T += tbl(["event", "kernel", "size", "cpu", "ses", "low", "high", "single level", "low - high"], out)
            # rule 3 per event and CPU
            for cpu in sorted(set(p.cpu_i for p in procs)):
                qs = [q for key, cell in cells.items() for q in cell["procs"]
                      if key[2] in LOAD_ONLY and key[3] == M8 and int(key[4]) == cpu]
                events = sorted(set(e for q in qs for e in q["proc"].events))
                for e in events:
                    pairs = []
                    for q in qs:
                        ev = q["proc"].events
                        if e not in ev or "low" not in q["levels"] or "high" not in q["levels"]:
                            continue
                        i = ev.index(e)
                        vals = {"low": [], "high": []}
                        for w in q["wins"]:
                            if w["level"] in vals and i < len(w["counts"]) and w["counts"][i] is not None:
                                vals[w["level"]].append(L.per64(w["counts"][i], w["bytes"]))
                        pairs.append((vals["low"], vals["high"]))
                    r = rule3_event(pairs)
                    r["step"] = step
                    r["load_only_processes"] = len(qs)
                    J["rule3"].setdefault(e, {"per_cell": {}})["per_cell"][ck(cpu, ses)] = r
    out = []
    for e in sorted(J["rule3"]):
        pc = J["rule3"][e]["per_cell"]
        J["rule3"][e]["overall"] = rule3_overall(pc)
        for key in sorted(pc):
            r = pc[key]
            out.append([e, key, r["verdict"], "[" + " ".join("%.4g" % d for d in r["diffs"]) + "]",
                        "%.4g" % r["median_diff"] if r["median_diff"] is not None else "NA",
                        "%.4g" % r["spread"] if r["spread"] is not None else "NA", J["rule3"][e]["overall"]])
    T.append("")
    T.append("Rule 3 verdict per event (8 MiB, load-only processes with both levels):")
    T += tbl(["event", "cell", "verdict", "low - high per process", "median", "largest within-level spread",
              "overall"], out)
    # acceptance, rule 1
    T.append("")
    T.append("Acceptance check of rule 1 of round 2: counted levels within 0.5 GB/s of the S4 levels of the CPU.")
    T.append(reading("the S4 levels of a CPU are the medians over the load-only S4 processes with two levels, "
                     "over all S4 sessions that exist; step XW (sampler, not counted) is checked the same way."))
    T.append("The switch-time part of rule 1 is shown as a count only: counted up switches whose switch window is")
    T.append("within 1 window of an S4 up switch window of the same CPU. It has no verdict here.")
    s4s = data.sessions("S4")
    out = []
    for step in ("XW", "XCA", "XCB", "XCC"):
        for ses in data.sessions(step):
            for cpu in sorted(set(p.cpu_i for p in data.procs(step, ses))):
                lo, hi, ups, n = level_ref(data, step, cpu, [ses])
                slo, shi, sups, sn = level_ref(data, "S4", cpu, s4s)
                if n == 0 or sn == 0:
                    verdict = "Insufficient data: %s" % ("no S4 process with two levels" if sn == 0
                                                         else "no process with two levels")
                    ok = None
                else:
                    ok = abs(lo - slo) <= 0.5 and abs(hi - shi) <= 0.5
                    verdict = "pass" if ok else "counted mode differs" if step != "XW" else "sampled mode differs"
                near = sum(1 for u in ups if any(abs(u - s) <= 1 for s in sups))
                J["acceptance"].append({"step": step, "cpu": cpu, "session": ses, "low": lo, "high": hi,
                                        "s4_low": slo, "s4_high": shi, "pass": ok, "verdict": verdict,
                                        "processes_two_levels": n, "ups": len(ups), "ups_near_s4": near,
                                        "folders": data.names(step, ses) + [n_ for s in s4s
                                                                            for n_ in data.names("S4", s)]})
                out.append([step, cpu, ses, n, fx(lo), fx(slo), fx(hi), fx(shi), verdict, "%d of %d" % (near, len(ups))])
    T += tbl(["step", "cpu", "ses", "procs with two levels", "low", "S4 low", "high", "S4 high",
              "verdict (levels only)", "ups near an S4 up"], out)
    return J, T


# ------------------------------------------------------------------ item 7: kernel families XN and ZN
def rule6_cell(cells, kernels):
    """Rule 6 of round 2 on one CPU in one session. cells: {(kernel, size): cell_stats}."""
    asm = cells.get(("asmread", M8))
    res = {"kernels": {}, "c": None, "asm_high": None, "asm_low": None}
    if not asm or asm["p95"] is None:
        res["error"] = "asmread at 8 MiB missing"
        return res
    hi, lo = asm["p95"], asm["p5"]
    res["asm_high"], res["asm_low"] = hi, lo
    for k in kernels:
        c32, c8 = cells.get((k, K32)), cells.get((k, M8))
        if not c32 or not c8 or c32["median"] is None or c8["median"] is None:
            res["kernels"][k] = {"C": None, "a": None, "b": None, "note": "cell missing"}
            continue
        C = c32["median"]
        a = (abs(c8["p95"] - hi) <= 1.0) if C >= hi + 5.0 else None
        b = (abs(c8["median"] - C) <= 1.0) if C < lo else None
        res["kernels"][k] = {"C": C, "median_8M": c8["median"], "p95_8M": c8["p95"], "a": a, "b": b,
                             "p95_minus_asm_p95": c8["p95"] - hi, "median_8M_minus_C": c8["median"] - C}
    m8 = [cells[(k, M8)]["median"] for k in kernels if cells.get((k, M8)) and cells[(k, M8)]["median"] is not None]
    m32 = [cells[(k, K32)]["median"] for k in kernels if cells.get((k, K32)) and
           cells[(k, K32)]["median"] is not None]
    if len(m8) == len(kernels) and len(m32) == len(kernels) and max(m32) > min(m32):
        res["spread_8M"], res["spread_32K"] = max(m8) - min(m8), max(m32) - min(m32)
        res["c"] = res["spread_8M"] <= 0.25 * res["spread_32K"]
    return res


def word(x):
    return "not tested" if x is None else ("holds" if x else "fails")


def rule6_overall(per_cell, kernel):
    """Contradicted for a kernel if (a) or (b) fails on both CPUs in both sessions."""
    ses = sorted(set(int(k.split("/s")[1]) for k in per_cell))
    out = {}
    for part in ("a", "b"):
        vals = [per_cell[k]["kernels"].get(kernel, {}).get(part) for k in sorted(per_cell)]
        out[part] = vals
    miss = missing_sessions(ses)
    fails = [p for p in ("a", "b") if len(out[p]) >= 4 and all(v is False for v in out[p])]
    if miss:
        f1 = [p for p in ("a", "b") if out[p] and all(v is False for v in out[p])]
        return "session %s missing: no overall verdict%s" % (
            ", ".join(str(s) for s in miss),
            " (part (%s) fails on every CPU of the session that exists)" % ", ".join(f1) if f1 else "")
    if fails:
        return "H1 contradicted for this kernel: part (%s) fails on both CPUs in both sessions" % ", ".join(fails)
    return "H1 not contradicted for this kernel"


def rule_zn_kernel(C, median8, p95_8, s8lo, s8hi):
    """Rule 2 of round 4 for one kernel on one CPU in one session."""
    if C is None or median8 is None:
        return {"class": None, "prediction_holds": None, "contradicts": None}
    if C <= 66.0:
        return {"class": "slow (C_k at most 66)", "prediction_holds": abs(median8 - C) <= 1.0,
                "loss_32K_to_8M": C - median8, "contradicts": (C - median8) > 1.0}
    if s8lo is None or s8hi is None:
        return {"class": "fast or between", "prediction_holds": None, "contradicts": None,
                "note": "S8 missing (asmread at 8 MiB from YF or ZD of the same session)"}
    if C >= 76.0:
        return {"class": "fast (C_k at least 76)", "prediction_holds": s8lo - 1.0 <= p95_8 <= s8hi + 1.0,
                "contradicts": None}
    return {"class": "between 66 and 76", "prediction_holds": p95_8 <= min(C, s8hi) + 1.0, "contradicts": None}


def item7(data):
    T = ["7. KERNEL FAMILIES (step XN with rule 6 of round 2; step ZN with rule 2 of round 4)", "",
         "median, p95, p5 = cell values (median over the 6 processes) in GB/s. C_k = cell median at 32 KiB."]
    J = {"XN": {"rows": [], "rule6": {}, "overall": {}}, "ZN": {"rows": [], "rule2": {}, "overall": {}}}
    T.append(reading("in rule 6 the 'asmread 8 MiB high level' is the asmread cell p95 at 8 MiB and the 'low level' "
                     "is its cell p5, both from XN of the same CPU and session."))
    T.append(reading("in rule 2 of round 4, S8 is the range from the cell p5 to the cell p95 of asmread at 8 MiB of "
                     "the same CPU and session, from YF if it exists, else from ZD without evict; the limit for "
                     "a kernel between 66 and 76 GB/s is applied to its 8 MiB p95."))
    for step in ("XN", "ZN"):
        allk = set()
        for ses in (1, 2):
            if not data.names(step, ses):
                T.append("  %s session %d missing." % (step, ses))
                continue
            cells = cells_of(data.procs(step, ses))
            kernels = sorted(set(k for k, _, _ in cells), key=lambda k: (k != "asmread", len(k), k))
            allk |= set(kernels)
            asm_src = {}
            if step == "ZN":
                src = "YF" if data.names("YF", ses) else "ZD" if data.names("ZD", ses) else None
                if src:
                    pr = [p for p in data.procs(src, ses) if p.kernel == "asmread" and evict_of(p) == 0]
                    asm_src = cells_of(pr)
                J["ZN"].setdefault("asmread_source", {})["s%d" % ses] = (
                    {"step": src, "folders": data.names(src, ses)} if src else None)
            else:
                asm_src = {k: v for k, v in cells.items() if k[0] == "asmread"}
            out = []
            for (kernel, size, cpu) in sorted(cells, key=lambda k: (k[1], kernels.index(k[0]), k[2])):
                c = cells[(kernel, size, cpu)]
                a = asm_src.get(("asmread", size, cpu))
                gain = 100.0 * (a["median"] / c["median"] - 1.0) if a and a["median"] and c["median"] else None
                J[step]["rows"].append({"kernel": kernel, "size": size_label(size), "cpu": cpu, "session": ses,
                                        "n": c["n"], "median": c["median"], "p95": c["p95"], "p5": c["p5"],
                                        "asmread_gain_pct": gain, "folders": data.names(step, ses)})
                out.append([kernel, size_label(size), cpu, ses, c["n"], fx(c["median"]), fx(c["p95"]), fx(c["p5"]),
                            fx(gain)])
            T.append("")
            T.append("%s session %d (%s):" % (step, ses, ", ".join(data.names(step, ses))))
            T += tbl(["kernel", "size", "cpu", "ses", "procs", "median", "p95", "p5", "gain of asmread %"], out)
            for cpu in sorted(set(c for _, _, c in cells)):
                cc = {(k, s): v for (k, s, c), v in cells.items() if c == cpu}
                if step == "XN":
                    r = rule6_cell(cc, kernels)
                    J["XN"]["rule6"][ck(cpu, ses)] = r
                    if r.get("error"):
                        T.append("  rule 6, CPU %d: %s." % (cpu, r["error"]))
                        continue
                    T.append("  rule 6, CPU %d session %d: asmread 8 MiB high %s, low %s GB/s. Part (c): spread at "
                             "8 MiB %s, at 32 KiB %s GB/s: %s." % (cpu, ses, fx(r["asm_high"]), fx(r["asm_low"]),
                                                                  fx(r.get("spread_8M")), fx(r.get("spread_32K")),
                                                                  word(r["c"])))
                    T += tbl(["kernel", "C_k", "8M median", "8M p95", "p95 - asmread p95", "(a)", "(b)"],
                             [[k, fx(v.get("C")), fx(v.get("median_8M")), fx(v.get("p95_8M")),
                               fx(v.get("p95_minus_asm_p95")), word(v["a"]), word(v["b"])]
                              for k, v in r["kernels"].items()], "    ")
                else:
                    a8 = asm_src.get(("asmread", M8, cpu))
                    s8lo, s8hi = (a8["p5"], a8["p95"]) if a8 else (None, None)
                    res = {"S8_low": s8lo, "S8_high": s8hi, "kernels": {}}
                    rows = []
                    for k in kernels:
                        c32, c8 = cc.get((k, K32)), cc.get((k, M8))
                        v = rule_zn_kernel(c32["median"] if c32 else None, c8["median"] if c8 else None,
                                           c8["p95"] if c8 else None, s8lo, s8hi)
                        v.update(C=c32["median"] if c32 else None, median_8M=c8["median"] if c8 else None,
                                 p95_8M=c8["p95"] if c8 else None)
                        res["kernels"][k] = v
                        rows.append([k, fx(v["C"]), fx(v["median_8M"]), fx(v["p95_8M"]), v["class"] or "cell missing",
                                     word(v["prediction_holds"]), fx(v.get("loss_32K_to_8M")),
                                     "-" if v["contradicts"] is None else ("yes" if v["contradicts"] else "no")])
                    J["ZN"]["rule2"][ck(cpu, ses)] = res
                    T.append("  rule 2 of round 4, CPU %d session %d: S8 = %s to %s GB/s." % (
                        cpu, ses, fx(s8lo), fx(s8hi)))
                    T += tbl(["kernel", "C_k", "8M median", "8M p95", "class", "prediction", "loss 32K to 8M",
                              "loses more than 1.0"], rows, "    ")
        if step == "XN" and J["XN"]["rule6"]:
            pc = {k: v for k, v in J["XN"]["rule6"].items() if not v.get("error")}
            for k in sorted(allk):
                J["XN"]["overall"][k] = rule6_overall(pc, k)
                T.append("  rule 6 overall, %s: %s." % (k, J["XN"]["overall"][k]))
            J["XN"]["part_c"] = {k: v["c"] for k, v in pc.items()}
            J["XN"]["tested_b"] = any(v["kernels"][k].get("b") is not None for v in pc.values() for k in v["kernels"])
            T.append("  rule 6 part (c): %s. Part (b) tested by a kernel of this family: %s." % (
                ", ".join("%s %s" % (k, word(v)) for k, v in sorted(J["XN"]["part_c"].items())),
                "yes" if J["XN"]["tested_b"] else "no (no kernel has C_k below the asmread low level)"))
        if step == "ZN" and J["ZN"]["rule2"]:
            pc = J["ZN"]["rule2"]
            ses_have = sorted(set(int(k.split("/s")[1]) for k in pc))
            miss = missing_sessions(ses_have)
            for k in sorted(allk):
                vals = [pc[c]["kernels"].get(k, {}).get("contradicts") for c in sorted(pc)]
                slow = [v for v in vals if v is not None]
                if not slow:
                    o = "not a slow kernel (C_k above 66 GB/s): the contradiction rule does not apply"
                elif miss:
                    o = "session %s missing: no overall verdict (slow kernel; loses more than 1.0 GB/s in %d of %d " \
                        "cells)" % (", ".join(str(s) for s in miss), sum(1 for v in slow if v), len(slow))
                elif len(slow) >= 4 and all(slow):
                    o = "H1 contradicted: this slow kernel loses more than 1.0 GB/s on both CPUs in both sessions"
                else:
                    o = "H1 not contradicted by this kernel (loses more than 1.0 GB/s in %d of %d cells)" % (
                        sum(1 for v in slow if v), len(slow))
                J["ZN"]["overall"][k] = o
                T.append("  rule 2 of round 4 overall, %s: %s." % (k, o))
    return J, T


# ------------------------------------------------------------------ item 8: H2
H2_LOW_MAX, H2_HIGH_MIN, H2_ORIGINAL_GAIN = 69.5, 70.5, 0.94


def h2_cpu_session(procs):
    """Counts and gains of the H2 processes of one CPU in one session (h2_analyze logic)."""
    new = [r for p in procs if p["binary"] == "bw_new" and H2.complete(p) for r in p["rates"]]
    cl = [H2.classify(r, H2_LOW_MAX, H2_HIGH_MIN) for r in new]
    gains, low_gains = [], []
    for _, o, n in H2.pairs_of(procs):
        g = H2.gain(med(n["rates"]), med(o["rates"]))
        gains.append(g)
        if med(n["rates"]) <= H2_LOW_MAX:
            low_gains.append(g)
    n = len(new)
    return {"new_repetitions": n, "low": cl.count("low"), "between": cl.count("between"), "high": cl.count("high"),
            "share_low": cl.count("low") / float(n) if n else None, "pairs": len(gains),
            "median_gain_pct": med(gains), "low_pairs": len(low_gains), "median_gain_low_pct": med(low_gains)}


def h2_verdict(per_ses):
    """H2 rule for one CPU. per_ses: {session: result of h2_cpu_session}."""
    def sup(r):
        return (r["share_low"] is not None and r["share_low"] >= 0.75 and r["median_gain_low_pct"] is not None
                and abs(r["median_gain_low_pct"] - H2_ORIGINAL_GAIN) <= 1.5)

    def rej(r):
        return r["share_low"] is not None and r["share_low"] < 0.25

    miss = missing_sessions(sorted(per_ses))
    if miss:
        one = [("meets the 'supported' condition" if sup(r) else "meets the 'rejected' condition" if rej(r)
                else "meets neither condition") for r in per_ses.values()]
        return "session %s missing: no verdict yet (the session that exists %s)" % (
            ", ".join(str(s) for s in miss), "; ".join(one))
    if all(sup(r) for r in per_ses.values()):
        return "supported"
    if all(rej(r) for r in per_ses.values()):
        return "rejected"
    return "undecided"


def item8(data):
    T = ["8. H2: the original program at 8 MiB (bw_old = old read, bw_new = new read)", "",
         "A new-read repetition is low at or below %.1f GB/s and high at or above %.1f GB/s." % (H2_LOW_MAX,
                                                                                               H2_HIGH_MIN),
         "gain = 100 x (new / old - 1) of the process medians of a pair of neighbouring processes."]
    T.append(reading("'the low processes' of the H2 rule are the pairs whose new-read process has a median "
                     "repetition rate at or below 69.5 GB/s; the 'within 1.5 percentage points of 0.94 %' condition "
                     "must hold in both sessions."))
    J = {"rows": [], "verdict": {}, "folders": {}}
    per = {}
    for ses in (1, 2):
        fs = data.folders.get(("H2", ses), [])
        J["folders"]["s%d" % ses] = [os.path.basename(d) for d in fs]
        if not fs:
            T.append("  H2 session %d missing." % ses)
            continue
        seen = {}
        for d in fs:
            for path in sorted(glob.glob(os.path.join(d, "H2.csv"))):
                for p in H2.parse(path):
                    k = p.get("idx", len(seen))
                    if k not in seen or H2.complete(p):
                        seen[k] = p
        procs = [seen[k] for k in sorted(seen)]
        for i, p in enumerate(procs):
            p["n"] = i
        for cpu in sorted(set(p["cpu"] for p in procs), key=H2.cpu_key):
            r = h2_cpu_session([p for p in procs if p["cpu"] == cpu])
            r.update(cpu=cpu, session=ses, folders=J["folders"]["s%d" % ses])
            J["rows"].append(r)
            per.setdefault(cpu, {})[ses] = r
    T += tbl(["cpu", "ses", "new repetitions", "low", "between", "high", "pairs", "median gain %", "low pairs",
              "median gain of low pairs %"],
             [[r["cpu"], r["session"], r["new_repetitions"], r["low"], r["between"], r["high"], r["pairs"],
               fx(r["median_gain_pct"]), r["low_pairs"], fx(r["median_gain_low_pct"])] for r in J["rows"]])
    for cpu in sorted(per, key=H2.cpu_key):
        J["verdict"]["cpu" + cpu] = h2_verdict(per[cpu])
        T.append("  H2 rule, CPU %s: %s." % (cpu, J["verdict"]["cpu" + cpu]))
    return J, T


# ------------------------------------------------------------------ item 9: YL
YL_INDEX = {"fall": (16, 42), "up": (21, 44)}        # record indices that rule 1 of round 3 predicts
YL_TIME_S = {"fall": (4.93, 12.76), "up": (6.3, 13.2)}   # S4 times: the time-based prediction


S4_UP_INDEX = (21, 44, 67, 90, 114, 137, 179)       # S4 up switch windows of session 1 (decisions file)


def yl_up_share(up_indices, wms):
    """Descriptive: how many up switches lie within 1 window of an S4 up window (index reading), and of the
    window that holds the time of an S4 up window (time reading: S4 index x 0.3 s)."""
    ix = sum(1 for u in up_indices if any(abs(u - c) <= 1 for c in S4_UP_INDEX))
    tm = sum(1 for u in up_indices if any(abs(u - int(c * 300.0 / wms)) <= 1 for c in S4_UP_INDEX))
    return {"ups": len(up_indices), "near_s4_index": ix, "near_s4_time": tm}


def read_b_rows(folder):
    """{process idx: [(trial, widx, bin, t_end_ns, bytes since window start)]} of the csv files of a folder.
    levels9.parse_csv does not keep the B rows."""
    out, cur = {}, None
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        with open(path) as f:
            for line in f:
                if line.startswith("-- step"):
                    fs = line.split()
                    try:
                        cur = int(fs[fs.index("idx") + 1])
                    except (ValueError, IndexError):
                        cur = None
                elif line.startswith("B,") and cur is not None:
                    p = line.rstrip("\n").split(",")
                    try:
                        out.setdefault(cur, []).append((int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5])))
                    except (ValueError, IndexError):
                        pass
    return out


def bin_rates(p, brows, per=10):
    """Rates per `per` bins (0.1 s for 10 ms bins) of the first target window: list of (t0_s, t1_s, GB/s)."""
    tw = [w for w in p.W if w.phase == "target"]
    if not tw or not brows:
        return [], None
    w0 = min(tw, key=lambda w: w.t_start)
    rows = sorted((b for b in brows if b[0] == w0.trial and b[1] == w0.widx), key=lambda b: b[2])
    out = []
    pt, pb = w0.t_start, 0
    for i in range(per - 1, len(rows), per):
        t, b = rows[i][3], rows[i][4]
        if t > pt:
            out.append((pt / 1e9, t / 1e9, (b - pb) / float(t - pt)))
        pt, pb = t, b
    return out, w0.t_start / 1e9


def yl_match(value, kind, wms):
    """Which prediction a median switch window matches (within 1 window): 'index', 'time', 'both' or 'neither'."""
    if value is None:
        return None
    ix = any(abs(value - c) <= 1.0 for c in YL_INDEX[kind])
    tm = any(abs(value - int(t * 1000.0 / wms)) <= 1.0 for t in YL_TIME_S[kind])
    return "both" if ix and tm else "index" if ix else "time" if tm else "neither"


def yl_verdict(med_by_len, one_window_counts):
    """Rule 1 of round 3 on one CPU in one session.

    med_by_len: {window ms: {'fall': median or None, 'up': median or None}} for the lengths other than 300 ms
    that exist. one_window_counts: per one-window process the count of switches after 0.3 s."""
    quiet = sum(1 for c in one_window_counts if c == 0)
    one_ok = (quiet >= 3) if one_window_counts else None      # "at least 3 of 4 processes"
    kinds = []
    for wms in sorted(med_by_len):
        for kind in ("fall", "up"):
            m = yl_match(med_by_len[wms].get(kind), kind, wms)
            if m is not None:
                kinds.append(m)
    info = {"matches": kinds, "one_window_quiet": quiet, "one_window_processes": len(one_window_counts),
            "one_window_ok": one_ok}
    if not kinds:
        info["verdict"] = "Insufficient data: no process with 100 ms or 1000 ms windows shows a switch"
    elif all(k == "index" for k in kinds) and one_ok:
        info["verdict"] = "H7 supported"
    elif all(k == "time" for k in kinds):
        info["verdict"] = "H7 rejected (the medians match the time prediction)"
    else:
        info["verdict"] = "undecided"
    return info


def item9(data):
    T = ["9. YL: window length (rule 1 of round 3, hypothesis H7)", "",
         "first fall, first up, switches = switch windows (record indices). u = up, f = fall."]
    T.append(reading("rule 1 is decided on the 100 ms and 1000 ms runs, because at 300 ms the index prediction and "
                     "the time prediction give the same windows; a median matches the index prediction if it is "
                     "within 1 window of 16 or 42 (first fall) or of 21 or 44 (first up), and the time prediction "
                     "if it is within 1 window of the window that holds 4.93 or 12.76 s (fall) or 6.3 or 13.2 s "
                     "(up); kernels 'read' and 'asmread' are pooled; a median that does not exist (no process "
                     "shows that switch) is left out."))
    T.append(reading("one-window runs: the 10 ms bins are joined in groups of 10 (0.1 s), levels9 segments these "
                     "rates, and a switch counts if its est. time is more than 0.3 s after the window start."))
    J = {"processes": [], "verdict": {}, "folders": {}}
    for ses in (1, 2):
        names = data.names("YL", ses)
        J["folders"]["s%d" % ses] = names
        if not names:
            T.append("  YL session %d missing." % ses)
            continue
        brows = {}
        for d in data.folders[("YL", ses)]:
            brows.update(read_b_rows(d))
        out = []
        per_cpu = {}
        for p in sorted(data.procs("YL", ses), key=lambda p: (win_ms(p) or 0, p.kernel, p.cpu_i, p.idx)):
            wms = win_ms(p)
            row = {"kernel": p.kernel, "window_ms": wms, "cpu": p.cpu_i, "session": ses, "idx": p.idx, "tag": p.tag}
            pc = per_cpu.setdefault(p.cpu_i, {"len": {}, "one": []})
            if len([w for w in p.W if w.phase == "target"]) == 1:
                rates, t0 = bin_rates(p, brows.get(p.idx, []))
                seg = L.segment(rates) if len(rates) >= L.MIN_SEQ else None
                late = [s for s in (seg["switches"] if seg else []) if s["t"] > t0 + 0.3]
                row.update(one_window=True, rates_per_0_1s=[round(r[2], 3) for r in rates],
                           low=seg["low"] if seg else None, high=seg["high"] if seg else None,
                           switches_after_0_3s=len(late) if seg else None,
                           switch_times_s=[round(s["t"] - t0, 2) for s in late])
                if seg:
                    pc["one"].append(len(late))
                out.append([p.kernel, wms, p.cpu_i, ses, p.idx, len(rates), fx(row["low"]), fx(row["high"]), "-", "-",
                            "%s switches after 0.3 s%s" % (row["switches_after_0_3s"], (
                                " at " + fl(row["switch_times_s"]) + " s") if late else "")])
            else:
                d = index_switches(p)
                sw = d["switches"] if d else []
                ff = next((s["index"] for s in sw if s["kind"] == "fall"), None)
                fu = next((s["index"] for s in sw if s["kind"] == "up"), None)
                row.update(one_window=False, windows=d["n"] if d else len(p.W), low=d["low"] if d else None,
                           high=d["high"] if d else None, first_fall=ff, first_up=fu,
                           switches=[[s["kind"], s["index"]] for s in sw])
                z = pc["len"].setdefault(wms, {"fall": [], "up": [], "all_up": []})
                z["all_up"] += [s["index"] for s in sw if s["kind"] == "up"]
                if ff is not None:
                    z["fall"].append(ff)
                if fu is not None:
                    z["up"].append(fu)
                out.append([p.kernel, wms, p.cpu_i, ses, p.idx, row["windows"], fx(row["low"]), fx(row["high"]),
                            "-" if ff is None else ff, "-" if fu is None else fu,
                            " ".join("%s%d" % (s["kind"][0], s["index"]) for s in sw) or "no switch"])
            J["processes"].append(row)
        T.append("")
        T.append("YL session %d (%s):" % (ses, ", ".join(names)))
        T += tbl(["kernel", "window ms", "cpu", "ses", "idx", "windows or 0.1 s rates", "low", "high", "first fall",
                  "first up", "switches"], out)
        for cpu in sorted(per_cpu):
            pc = per_cpu[cpu]
            meds = {w: {"fall": med(z["fall"]), "up": med(z["up"]), "n_fall": len(z["fall"]), "n_up": len(z["up"])}
                    for w, z in pc["len"].items()}
            v = yl_verdict({w: m for w, m in meds.items() if w != 300}, pc["one"])
            v["medians"] = {str(w): m for w, m in meds.items()}
            v["up_share"] = {str(w): yl_up_share(z["all_up"], w) for w, z in pc["len"].items() if w}
            J["verdict"][ck(cpu, ses)] = v
            T.append("  rule 1, CPU %d session %d: %s. Medians: %s. One-window runs without a switch after 0.3 s: "
                     "%d of %d." % (cpu, ses, v["verdict"], "; ".join(
                         "%d ms: first fall %s (%d processes), first up %s (%d processes)" % (
                             w, fx(m["fall"], 1), m["n_fall"], fx(m["up"], 1), m["n_up"])
                         for w, m in sorted(meds.items())), v["one_window_quiet"], v["one_window_processes"]))
            T.append("    descriptive, not part of rule 1: up switches within 1 window of an S4 up window %s, and of "
                     "the window that holds the same time: %s." % (list(S4_UP_INDEX), "; ".join(
                         "%s ms: %d and %d of %d" % (w, u["near_s4_index"], u["near_s4_time"], u["ups"])
                         for w, u in sorted(v["up_share"].items(), key=lambda x: int(x[0])))))
    J["overall"] = both_sessions_verdict(J["verdict"], "H7 supported", "H7 rejected")
    T.append("  rule 1 overall: %s." % J["overall"])
    return J, T


def both_sessions_verdict(per_cell, good_prefix, bad_prefix):
    """'confirmed' needs the good verdict on both CPUs in both sessions."""
    if not per_cell:
        return "no data"
    ses = sorted(set(int(k.split("/s")[1]) for k in per_cell))
    vals = [v["verdict"] for v in per_cell.values()]
    miss = missing_sessions(ses)
    state = "all cells that exist say '%s'" % good_prefix if all(x.startswith(good_prefix) for x in vals) else \
        "all cells that exist say '%s'" % bad_prefix if all(x.startswith(bad_prefix) for x in vals) else \
        "verdicts of the cells that exist: " + "; ".join("%s %s" % (k, per_cell[k]["verdict"])
                                                          for k in sorted(per_cell))
    if miss:
        return "session %s missing: not confirmed yet (%s)" % (", ".join(str(s) for s in miss), state)
    if len(per_cell) >= 4 and all(x.startswith(good_prefix) for x in vals):
        return "confirmed: %s on both CPUs in both sessions" % good_prefix
    if len(per_cell) >= 4 and all(x.startswith(bad_prefix) for x in vals):
        return "%s on both CPUs in both sessions" % bad_prefix
    return "not confirmed (%s)" % state


# ------------------------------------------------------------------ item 10: YP
def nearest_shift(series, ref):
    """Per event of `series`: (nearest event of ref) minus (the event). Positive = the padded run is earlier."""
    return [min(ref, key=lambda r: (abs(r - u), r)) - u for u in series] if ref else []


def circ_diff(a, b, period):
    """a - b reduced to (-period/2, period/2]."""
    if not period:
        return a - b
    d = (a - b) % period
    return d - period if d > period / 2.0 else d


def yp_pad_result(pad, ups, ref_ups, win_size=80):
    """Shift of the up series of one pad against the pad 0 series of the same CPU and session."""
    sh = nearest_shift(ups, ref_ups)
    gaps = sorted(ref_ups[i + 1] - ref_ups[i] for i in range(len(ref_ups) - 1) if ref_ups[i + 1] - ref_ups[i] > 2)
    period = med(gaps)
    pred = pad / float(win_size)
    res = {"pad": pad, "n": len(sh), "shifts": sh, "median_shift": med(sh), "predicted": pred,
           "pad0_spacing": period, "predicted_modulo_spacing": None, "match": None,
           "n_match": sum(1 for x in sh if abs(circ_diff(x, pred, period)) <= 1.0)}
    if sh and period:
        res["predicted_modulo_spacing"] = circ_diff(pred, 0.0, period)
    if sh:
        res["match"] = abs(circ_diff(res["median_shift"], pred, period)) <= 1.0
    return res


def recurring(series_list, tol=1):
    """Events of the first series that every other series also has within `tol` windows."""
    if not series_list:
        return []
    return [v for v in series_list[0] if all(any(abs(v - x) <= tol for x in s) for s in series_list[1:])]


def yp_fall_result(pad, falls_by_proc, ref_falls, win_size=80):
    """Shift of the falls: per padded process and per recurring pad 0 fall r, r minus the nearest fall of
    the process. Descriptive; the comparison is modulo the spacing of the recurring pad 0 falls."""
    sh = [r - min(f, key=lambda x: (abs(x - r), x)) for f in falls_by_proc if f for r in ref_falls]
    gaps = [ref_falls[i + 1] - ref_falls[i] for i in range(len(ref_falls) - 1)]
    period = med(gaps)
    pred = pad / float(win_size)
    return {"n": len(sh), "shifts": sh, "median_shift": med(sh), "pad0_fall_spacing": period,
            "predicted_modulo_spacing": circ_diff(pred, 0.0, period) if period else pred,
            "match": (abs(circ_diff(med(sh), pred, period)) <= 1.0) if sh else None}


def yp_verdict(per_cpu):
    """Rule 2 of round 3 for one session. per_cpu: {cpu: [yp_pad_result of each pad other than 0]}."""
    if not per_cpu:
        return "no data"
    cnt = {c: (sum(1 for r in rs if r["match"]), len(rs)) for c, rs in per_cpu.items()}
    txt = ", ".join("CPU %s: %d of %d pads match" % (c, a, b) for c, (a, b) in sorted(cnt.items()))
    if len(per_cpu) >= 2 and all(a >= 4 for a, _ in cnt.values()):
        return "H7 supported (%s)" % txt
    evaluated = [r for rs in per_cpu.values() for r in rs if r["median_shift"] is not None]
    if evaluated and all(abs(r["median_shift"]) <= 0.5 for r in evaluated) and \
            all(b >= 5 for _, b in cnt.values()):
        return "H7 rejected: the events keep their window for every pad (%s)" % txt
    return "undecided (%s)" % txt


def item10(data):
    T = ["10. YP: record pad (rule 2 of round 3, hypothesis H7)", "",
         "The statistic that rule 2 fixed ('the first fall after window 30') is replaced by the series of all up",
         "and fall switch windows, because that fall is absent in some processes. It is still printed where it",
         "exists.",
         "shift = (nearest pad 0 switch window of the same CPU and session) minus (switch window of the padded",
         "run). A positive shift means the padded run switches earlier. Prediction: pad / 80 windows."]
    T.append(reading("each up of a padded run is matched to the nearest pad 0 up, so a shift is known only modulo "
                     "the spacing of the pad 0 ups (about 23 windows); the prediction pad / 80 is therefore also "
                     "reduced modulo that spacing before the 'within 1 window' comparison."))
    T.append(reading("the falls 'at windows 70 and 95 of pad 0' are the recurring pad 0 falls: the falls of the first "
                     "pad 0 process that every other pad 0 process of the CPU and session also has within 1 window "
                     "(the switch window of a fall is the window in which the rate falls, 69 and 95 in session "
                     "1); for each of them the nearest fall of each padded process gives one shift value, and "
                     "the comparison is modulo the spacing of these falls; the falls are descriptive."))
    T.append(reading("rule 2 is decided on the up series: 'supported' if at least 4 of the 5 pads match on both "
                     "CPUs, 'rejected' if the median shift is 0 (at most 0.5) for every pad; the --hot-copy "
                     "prediction (median switch count at most 1 over the hot-copy processes of a session) is "
                     "reported beside the verdict."))
    J = {"processes": [], "shift": [], "verdict": {}, "hot_copy": {}, "folders": {}}
    for ses in (1, 2):
        names = data.names("YP", ses)
        J["folders"]["s%d" % ses] = names
        if not names:
            T.append("  YP session %d missing." % ses)
            continue
        out, hot = [], []
        series = {}
        for p in sorted(data.procs("YP", ses), key=lambda p: (p.M.get("hot_copy") == "1", pad_of(p), p.cpu_i, p.idx)):
            d = index_switches(p)
            sw = d["switches"] if d else []
            ups = [s["index"] for s in sw if s["kind"] == "up"]
            falls = [s["index"] for s in sw if s["kind"] == "fall"]
            is_hot = p.M.get("hot_copy") == "1"
            f30 = next((f for f in falls if f > 30), None)
            row = {"pad": pad_of(p), "hot_copy": is_hot, "cpu": p.cpu_i, "session": ses, "idx": p.idx, "tag": p.tag,
                   "win_addr": p.M.get("win_addr"), "ups": ups, "falls": falls, "first_fall_after_30": f30,
                   "switches": len(sw)}
            J["processes"].append(row)
            out.append(["hot-copy" if is_hot else row["pad"], p.cpu_i, ses, p.idx, row["win_addr"] or "NA",
                        " ".join(str(u) for u in ups) or "-", " ".join(str(f) for f in falls) or "-",
                        "-" if f30 is None else f30])
            if is_hot:
                hot.append(len(sw))
            else:
                z = series.setdefault((p.cpu_i, row["pad"]), {"up": [], "fall": [], "f30": [], "fall_by_proc": []})
                z["up"] += ups
                z["fall"] += falls
                if falls:
                    z["fall_by_proc"].append(falls)
                if f30 is not None:
                    z["f30"].append(f30)
        T.append("")
        T.append("YP session %d (%s):" % (ses, ", ".join(names)))
        T += tbl(["pad", "cpu", "ses", "idx", "M,win_addr", "up switch windows", "fall switch windows",
                  "first fall after window 30"], out)
        per_cpu, out = {}, []
        for cpu in sorted(set(c for c, _ in series)):
            ref = series.get((cpu, 0))
            for pad in sorted(p for c, p in series if c == cpu and p != 0):
                z = series[(cpu, pad)]
                if not ref:
                    r = {"pad": pad, "n": 0, "shifts": [], "median_shift": None, "predicted": pad / 80.0,
                         "match": None, "note": "no pad 0 process on this CPU"}
                    f = {"median_shift": None, "n": 0, "match": None, "predicted_modulo_spacing": None}
                    f30 = None
                else:
                    r = yp_pad_result(pad, sorted(z["up"]), sorted(ref["up"]))
                    f = yp_fall_result(pad, z["fall_by_proc"], recurring(ref["fall_by_proc"]))
                    f30 = (med(ref["f30"]) - med(z["f30"])) if ref["f30"] and z["f30"] else None
                r.update(cpu=cpu, session=ses, fall=f, first_fall_after_30_shift=f30,
                         pad0_ups=sorted(ref["up"]) if ref else [],
                         pad0_recurring_falls=recurring(ref["fall_by_proc"]) if ref else [])
                J["shift"].append(r)
                per_cpu.setdefault(cpu, []).append(r)
                out.append([pad, cpu, ses, fx(r["predicted"], 1), fx(r.get("predicted_modulo_spacing"), 1),
                            fx(r["median_shift"], 1), "%d of %d" % (r.get("n_match", 0), r["n"]),
                            word(r["match"]) if r["match"] is not None else "NA",
                            fx(f["predicted_modulo_spacing"], 1), fx(f["median_shift"], 1), f["n"],
                            word(f["match"]) if f["match"] is not None else "NA", fx(f30, 1)])
        T.append("  shift of the series against pad 0 (windows):")
        T += tbl(["pad", "cpu", "ses", "predicted pad/80", "modulo up spacing", "median up shift",
                  "ups that match", "up series", "modulo fall spacing", "median fall shift", "fall values",
                  "fall series", "shift of 'first fall after 30'"], out, "    ")
        for cpu in sorted(set(c for c, _ in series)):
            ref = series.get((cpu, 0))
            if ref:
                T.append("    pad 0, CPU %d: up switch windows %s (the pad 0 processes pooled); recurring fall switch "
                         "windows %s." % (cpu, sorted(ref["up"]), recurring(ref["fall_by_proc"])))
        v = yp_verdict(per_cpu)
        J["verdict"]["s%d" % ses] = v
        J["hot_copy"]["s%d" % ses] = {"switches_per_process": hot, "median": med(hot),
                                      "prediction_holds": (med(hot) <= 1) if hot else None}
        T.append("  rule 2, session %d: %s." % (ses, v))
        T.append("  --hot-copy, session %d: switches per process %s, median %s: the prediction 'at most 1' %s." % (
            ses, hot, fx(med(hot), 1), word((med(hot) <= 1) if hot else None)))
    vs = J["verdict"]
    miss = missing_sessions(sorted(int(k[1:]) for k in vs))
    if not vs:
        J["overall"] = "no data"
    elif miss:
        J["overall"] = "session %s missing: not confirmed yet (%s)" % (
            ", ".join(str(s) for s in miss), "; ".join("%s: %s" % (k, v) for k, v in sorted(vs.items())))
    elif all(v.startswith("H7 supported") for v in vs.values()):
        J["overall"] = "confirmed: H7 supported in both sessions on both CPUs"
    elif all(v.startswith("H7 rejected") for v in vs.values()):
        J["overall"] = "H7 rejected in both sessions"
    else:
        J["overall"] = "not confirmed (%s)" % "; ".join("%s: %s" % (k, v) for k, v in sorted(vs.items()))
    T.append("  rule 2 overall: %s." % J["overall"])
    return J, T


# ------------------------------------------------------------------ item 11: YC and YF
YC_EVENTS = ("cpu_cycles", "inst_retired", "l1d_cache_refill", "l2d_cache_refill", "l1d_cache_lmiss_rd",
             "l2d_cache_lmiss_rd")
PF_KERNELS = ("read_pf256", "read_pf512", "read_pf1024", "read_pf2048")


def trial_rep(p, trial):
    try:
        return int(p.S[trial][1])
    except (KeyError, ValueError, IndexError):
        return None


def aa_value(p):
    """A/A value of a process: median(rep 1, rep 3) - median(rep 2, rep 4), where the value of a repeat is
    the median rate of all windows of the kernel and size in that trial."""
    grp = p.main_group()
    by = {}
    for w in p.group_windows(grp):
        by.setdefault(trial_rep(p, w.trial), []).append(w.rate)
    a = [med(by[r]) for r in (1, 3) if r in by]
    b = [med(by[r]) for r in (2, 4) if r in by]
    return (med(a) - med(b)) if len(a) == 2 and len(b) == 2 else None


def contrast(pa, pb, units=6):
    """Shared repeatability rule for 'A minus B' with the processes of a cell as units, paired by rep_set.
    Unit value: process median over all windows. Limit: sum of the two A/A spreads."""
    va = {p.M.get("plan.rep_set"): (L.proc_cell_values(p) or {}).get("med_all") for p in pa}
    vb = {p.M.get("plan.rep_set"): (L.proc_cell_values(p) or {}).get("med_all") for p in pb}
    sets = [r for r in sorted(va, key=str) if r in vb and va[r] is not None and vb[r] is not None]
    vals = [va[r] - vb[r] for r in sets]
    aa = [[aa_value(p) for p in pl] for pl in (pa, pb)]
    spreads = [max([abs(x) for x in a if x is not None] or [0.0]) for a in aa]
    complete = (len(vals) == units and len(pa) == units and len(pb) == units
                and all(x is not None for a in aa for x in a))
    m = med(vals)
    limit = sum(spreads)
    rep = bool(complete and m is not None and abs(m) > limit and same_sign(vals))
    return {"values": vals, "sets": sets, "median": m, "spreads": spreads, "limit": limit, "complete": complete,
            "repeatable": rep, "sign": (1 if m > 0 else -1) if rep else None,
            "state": "repeatable" if rep else ("incomplete" if not complete else "not distinguished from variation")}


def rule3_yf(share, pf_rate, asm_high):
    """Rule 3 of round 3 at 8 MiB on one CPU in one session.
    share: {kernel: L1 long misses per line / those of asmread}. pf_rate: {kernel: rate}. asm_high: rate."""
    halving = sorted(k for k, s in share.items() if s is not None and s <= 0.5 and pf_rate.get(k) is not None)
    if asm_high is None or not share:
        return {"verdict": "Insufficient data: a cell is missing", "halving": halving}
    if not halving:
        return {"verdict": "Insufficient data: no prefetch kernel has at most half of the asmread L1 long misses",
                "halving": halving}
    rise = {k: pf_rate[k] - asm_high for k in halving}
    if any(r < 1.0 for r in rise.values()):
        v = "H1b rejected: %s" % ", ".join("%s halves the misses and is %+.2f GB/s against asmread" % (k, rise[k])
                                           for k in halving if rise[k] < 1.0)
    elif all(r >= 2.0 for r in rise.values()):
        v = "H1b supported"
    else:
        v = "undecided (rise between 1.0 and 2.0 GB/s)"
    return {"verdict": v, "halving": halving, "rise": rise}


def item11(data):
    T = ["11. YC and YF: the prefetch family (rule 3 of round 3, hypothesis H1b)", ""]
    T.append(reading("in rule 3 the rate of a prefetch kernel is its YF cell p95 at 8 MiB and the 'asmread high "
                     "level' is the asmread YF cell p95 at 8 MiB of the same CPU and session; the miss share uses "
                     "the YC medians over all counted windows of a process."))
    T.append(reading("repeatability rule for 'prefetch kernel minus asmread': the unit value is the process median "
                     "over all windows, pairs are the processes with the same rep_set, and the A/A value of a "
                     "process is median(repeat 1, repeat 3) minus median(repeat 2, repeat 4) of the per-trial "
                     "median rates."))
    J = {"YC": [], "YF": [], "contrast": [], "share": [], "rule3": {}, "folders": {}}
    for ses in (1, 2):
        J["folders"]["s%d" % ses] = {"YC": data.names("YC", ses), "YF": data.names("YF", ses)}
        yc = data.procs("YC", ses) if data.names("YC", ses) else []
        yf = data.procs("YF", ses) if data.names("YF", ses) else []
        if not data.names("YC", ses):
            T.append("  YC session %d missing." % ses)
        if not data.names("YF", ses):
            T.append("  YF session %d missing." % ses)
        cells = cells_of(yf)
        ycv = {}
        out = []
        for (kernel, size, cpu), pl in sorted(group(yc, lambda p: (p.kernel, p.size, p.cpu_i)).items(),
                                               key=lambda x: (x[0][1], x[0][0], x[0][2])):
            cs = [counter_proc(p) for p in pl]
            per64 = {e: med([c["per64"].get(e) for c in cs if c["per64"].get(e) is not None]) for e in YC_EVENTS}
            rate = med([c["rate"] for c in cs if c["rate"] is not None])
            ycv[(kernel, size, cpu)] = per64
            c = cells.get((kernel, size, cpu), {})
            J["YC"].append({"kernel": kernel, "size": size_label(size), "cpu": cpu, "session": ses, "per64": per64,
                            "yc_rate": rate, "yc_processes": len(pl), "yf_median": c.get("median"),
                            "yf_p95": c.get("p95")})
            out.append([kernel, size_label(size), cpu, ses] + ["%.4g" % per64[e] if per64[e] is not None else "NA"
                                                               for e in YC_EVENTS]
                       + [fx(rate), fx(c.get("median")), fx(c.get("p95"))])
        if out:
            T.append("")
            T.append("YC session %d (%s): counts per 64 B, the YC rate, and the YF cell median and p95 (GB/s):" % (
                ses, ", ".join(data.names("YC", ses))))
            T += tbl(["kernel", "size", "cpu", "ses", "cycles", "instructions", "L1 refill", "L2 refill",
                      "L1 long miss", "L2 long miss", "YC rate", "YF median", "YF p95"], out)
        out = []
        for (kernel, size, cpu) in sorted(cells, key=lambda k: (k[1], k[0], k[2])):
            c = cells[(kernel, size, cpu)]
            J["YF"].append({"kernel": kernel, "size": size_label(size), "cpu": cpu, "session": ses, "n": c["n"],
                            "median": c["median"], "p95": c["p95"], "p5": c["p5"]})
            out.append([kernel, size_label(size), cpu, ses, c["n"], fx(c["median"]), fx(c["p95"]), fx(c["p5"])])
        if out:
            T.append("")
            T.append("YF session %d (%s): cell values in GB/s:" % (ses, ", ".join(data.names("YF", ses))))
            T += tbl(["kernel", "size", "cpu", "ses", "procs", "median", "p95", "p5"], out)
        byc = group(yf, lambda p: (p.kernel, p.size, p.cpu_i))
        cpus = sorted(set(p.cpu_i for p in yf + yc))
        out, out2 = [], []
        for cpu in cpus:
            for size in (M1, M8):
                for k in PF_KERNELS:
                    pa, pb = byc.get((k, size, cpu), []), byc.get(("asmread", size, cpu), [])
                    if not pa or not pb:
                        continue
                    r = contrast(pa, pb)
                    r.update(kernel=k, size=size_label(size), cpu=cpu, session=ses)
                    a1, a8 = cells.get(("asmread", M1, cpu)), cells.get(("asmread", M8, cpu))
                    k8 = cells.get((k, M8, cpu))
                    if size == M8 and a1 and a8 and k8 and a1["median"] != a8["median"]:
                        r["share_of_loss_recovered"] = (k8["median"] - a8["median"]) / (a1["median"] - a8["median"])
                    J["contrast"].append(r)
                    out.append([k, size_label(size), cpu, ses, fx(r["median"]), fl(r["values"]), fx(r["limit"]),
                                r["state"], fx(r.get("share_of_loss_recovered"), 3)])
            share, rate = {}, {}
            for size in (M1, M8, M16):
                a = (ycv.get(("asmread", size, cpu)) or {}).get("l1d_cache_lmiss_rd")
                for k in PF_KERNELS:
                    v = (ycv.get((k, size, cpu)) or {}).get("l1d_cache_lmiss_rd")
                    s = (v / a) if v is not None and a else None
                    if (k, size, cpu) in ycv:
                        J["share"].append({"kernel": k, "size": size_label(size), "cpu": cpu, "session": ses,
                                           "l1_long_miss": v, "asmread_l1_long_miss": a, "share": s})
                        out2.append([k, size_label(size), cpu, ses, "%.4g" % v if v is not None else "NA",
                                     "%.4g" % a if a is not None else "NA", fx(s, 3)])
                    if size == M8:
                        if (k, size, cpu) in ycv:
                            share[k] = s
                        c = cells.get((k, M8, cpu))
                        rate[k] = c["p95"] if c else None
            if yc and yf:
                a8 = cells.get(("asmread", M8, cpu))
                r = rule3_yf(share, rate, a8["p95"] if a8 else None)
                r["asmread_high"] = a8["p95"] if a8 else None
                r["share_8M"], r["pf_p95_8M"] = share, rate
                J["rule3"][ck(cpu, ses)] = r
        if out:
            T.append("")
            T.append("  prefetch kernel minus asmread (YF session %d), six process values, GB/s:" % ses)
            T += tbl(["kernel", "size", "cpu", "ses", "median", "six values (by rep_set)", "limit", "state",
                      "share of the 1M to 8M loss recovered"], out, "    ")
        if out2:
            T.append("  share of the asmread L1 long misses (YC session %d):" % ses)
            T += tbl(["kernel", "size", "cpu", "ses", "L1 long miss per 64 B", "asmread", "share"], out2, "    ")
        for cpu in cpus:
            r = J["rule3"].get(ck(cpu, ses))
            if r:
                T.append("  rule 3, CPU %d session %d: %s. asmread high level %s GB/s; kernels with at most half of "
                         "the misses: %s." % (cpu, ses, r["verdict"], fx(r["asmread_high"]),
                                              ", ".join(r["halving"]) or "none"))
            else:
                T.append("  rule 3, CPU %d session %d: Insufficient data: %s missing." % (
                    cpu, ses, "YC" if not yc else "YF"))
    pc = J["rule3"]
    if not pc:
        J["overall"] = "no data: YC and YF are both needed"
    else:
        ses_have = sorted(set(int(k.split("/s")[1]) for k in pc))
        miss = missing_sessions(ses_have)
        desc = "; ".join("%s: %s" % (k, pc[k]["verdict"]) for k in sorted(pc))
        if miss:
            J["overall"] = "session %s missing: not confirmed yet (%s)" % (", ".join(str(s) for s in miss), desc)
        elif len(pc) >= 4 and all(v["verdict"].startswith("H1b rejected") for v in pc.values()):
            rep = [c for c in J["contrast"] if c["size"] == "8M" and c["kernel"] in
                   (pc.get(ck(c["cpu"], c["session"])) or {}).get("halving", [])]
            neg = all(c["repeatable"] and c["sign"] < 0 for c in rep) if rep else False
            J["overall"] = "H1b rejected on both CPUs in both sessions (the contrast pf minus asmread at 8 MiB " \
                           "of the kernels that halve the misses is %s)" % (
                               "repeatable and negative in every cell" if neg else
                               "not repeatable and negative in every cell")
        elif len(pc) >= 4 and all(v["verdict"].startswith("H1b supported") for v in pc.values()):
            rep = [c for c in J["contrast"] if c["size"] == "8M" and c["kernel"] in
                   (pc.get(ck(c["cpu"], c["session"])) or {}).get("halving", [])]
            ok = bool(rep) and all(c["repeatable"] and c["sign"] > 0 for c in rep)
            J["overall"] = "confirmed: H1b supported" if ok else \
                "H1b supported in every cell, but the contrast at 8 MiB is not repeatable: not confirmed"
        else:
            J["overall"] = "not confirmed (%s)" % desc
    T.append("  rule 3 overall: %s." % J["overall"])
    return J, T


# ------------------------------------------------------------------ item 12: ZC and ZD
ZC_EVENTS = ("cpu_cycles", "l1d_cache_lmiss_rd", "l2d_cache_refill", "l2d_cache_wb", "bus_access",
             "l2d_cache_lmiss_rd")


def rule1_zd(wb_evict, rises, old_change):
    """Rule 1 of round 4 for one session.
    wb_evict: {cpu: l2d_cache_wb per 64 B of asmread at 8 MiB with evict} from ZC, or {} if ZC is missing.
    rises: {(kernel, cpu): 8 MiB cell p95 with evict minus without} for 'asmread' and 'read' from ZD.
    old_change: {cpu: old read 8 MiB cell median with evict minus without}."""
    if not wb_evict or any(v is None for v in wb_evict.values()):
        return {"check": None, "verdict": "Insufficient data: ZC counts with evict are missing, so the check of the "
                                          "intervention cannot be made"}
    check = all(v < 0.2 for v in wb_evict.values())
    if not check:
        return {"check": False, "verdict": "Insufficient data: with evict the L2 write-backs per 64 B stay at %s "
                                           "(the check needs below 0.2), so the intervention did not change the "
                                           "mechanism and H1d stays open" % fl(sorted(wb_evict.values()), 3)}
    cpus = set(c for _, c in rises)
    if len(cpus) < 2 or any(rises.get((k, c)) is None for k in LOAD_ONLY for c in cpus):
        return {"check": True, "verdict": "Insufficient data: the check passed, but ZD cells are missing (the rule "
                                          "needs 'asmread' and 'read' at 8 MiB without and with evict on both CPUs)"}
    if any(v is None or abs(v) > 0.3 for v in old_change.values()) or not old_change:
        return {"check": True, "verdict": "not decided: the old read control moved by more than 0.3 GB/s or is missing"}
    vals = list(rises.values())
    if all(v >= 3.0 for v in vals):
        v = "H1d supported"
    elif all(v < 1.0 for v in vals):
        v = "H1d rejected"
    else:
        v = "partly"
    return {"check": True, "verdict": v}


def item12(data):
    T = ["12. ZC and ZD: clean lines by --evict-mb (rule 1 of round 4, hypothesis H1d)", ""]
    T.append(reading("the check uses, per CPU, the median over the ZC evict processes of asmread at 8 MiB of "
                     "l2d_cache_wb per 64 B, and it passes only if every CPU is below 0.2; 'supported' needs a "
                     "rise of at least 3.0 GB/s for both kernels on both CPUs, 'rejected' needs every rise below "
                     "1.0 GB/s, anything else is 'partly'; the old read control uses the 8 MiB cell medians."))
    J = {"ZC": [], "ZD": [], "rule1": {}, "folders": {}}
    for ses in (1, 2):
        J["folders"]["s%d" % ses] = {"ZC": data.names("ZC", ses), "ZD": data.names("ZD", ses)}
        zc = data.procs("ZC", ses) if data.names("ZC", ses) else []
        zd = data.procs("ZD", ses) if data.names("ZD", ses) else []
        if not data.names("ZC", ses):
            T.append("  ZC session %d missing." % ses)
        if not data.names("ZD", ses):
            T.append("  ZD session %d missing." % ses)
        if not zc and not zd:
            continue
        out = []
        wb = {}
        for (kernel, size, cpu, ev), pl in sorted(group(zc, lambda p: (p.kernel, p.size, p.cpu_i,
                                                                       evict_of(p))).items()):
            cs = [counter_proc(p) for p in pl]
            per64 = {e: med([c["per64"].get(e) for c in cs if c["per64"].get(e) is not None]) for e in ZC_EVENTS}
            rates = [c["rate"] for c in cs if c["rate"] is not None]
            wbs = [c["per64"].get("l2d_cache_wb") for c in cs if c["per64"].get("l2d_cache_wb") is not None]
            J["ZC"].append({"kernel": kernel, "size": size_label(size), "cpu": cpu, "session": ses, "evict_mb": ev,
                            "processes": len(pl), "per64": per64, "rate_median": med(rates), "rates": rates,
                            "l2d_cache_wb_per_process": wbs})
            out.append([kernel, size_label(size), cpu, ses, ev, len(pl)]
                       + ["%.4g" % per64[e] if per64[e] is not None else "NA" for e in ZC_EVENTS]
                       + [fl(wbs, 3), fl(rates)])
            if kernel == "asmread" and size == M8 and ev > 0:
                wb[cpu] = per64["l2d_cache_wb"]
        if out:
            T.append("")
            T.append("ZC session %d (%s): counts per 64 B (median over the processes):" % (
                ses, ", ".join(data.names("ZC", ses))))
            T += tbl(["kernel", "size", "cpu", "ses", "evict MiB", "procs", "cycles", "L1 long miss", "L2 refill",
                      "L2 write-back", "bus access", "L2 long miss", "write-backs per process", "rates GB/s"], out)
        cells = {k: cell_stats(v) for k, v in group(zd, lambda p: (p.kernel, p.size, p.cpu_i,
                                                                    evict_of(p) > 0)).items()}
        out = []
        rises, oldc = {}, {}
        for (kernel, size, cpu) in sorted(set(k[:3] for k in cells), key=lambda k: (k[1], k[0], k[2])):
            a, b = cells.get((kernel, size, cpu, False)), cells.get((kernel, size, cpu, True))
            row = {"kernel": kernel, "size": size_label(size), "cpu": cpu, "session": ses,
                   "plain": {"n": a["n"], "median": a["median"], "p95": a["p95"]} if a else None,
                   "evict": {"n": b["n"], "median": b["median"], "p95": b["p95"]} if b else None}
            if a and b and a["median"] is not None and b["median"] is not None:
                row["median_diff"], row["p95_diff"] = b["median"] - a["median"], b["p95"] - a["p95"]
            J["ZD"].append(row)
            out.append([kernel, size_label(size), cpu, ses, fx(a["median"] if a else None),
                        fx(b["median"] if b else None), fx(row.get("median_diff")), fx(a["p95"] if a else None),
                        fx(b["p95"] if b else None), fx(row.get("p95_diff"))])
            if size == M8 and kernel in LOAD_ONLY:
                rises[(kernel, cpu)] = row.get("p95_diff")
            if size == M8 and kernel == "oldread":
                oldc[cpu] = row.get("median_diff")
        if out:
            T.append("")
            T.append("ZD session %d (%s): cell values in GB/s, without and with --evict-mb 512:" % (
                ses, ", ".join(data.names("ZD", ses))))
            T += tbl(["kernel", "size", "cpu", "ses", "median plain", "median evict", "difference", "p95 plain",
                      "p95 evict", "difference"], out)
        r = rule1_zd(wb, rises, oldc)
        r.update(wb_evict={str(c): v for c, v in wb.items()},
                 p95_rise_8M={"%s/cpu%d" % k: v for k, v in rises.items()},
                 oldread_median_change_8M={str(c): v for c, v in oldc.items()})
        if r["verdict"] == "H1d supported":
            sh = {}
            for (kernel, cpu) in rises:
                a, b = cells.get((kernel, M8, cpu, False)), cells.get((kernel, M8, cpu, True))
                if a and b and a["median"] != 85.2:
                    sh["%s/cpu%d" % (kernel, cpu)] = (b["median"] - a["median"]) / (85.2 - a["median"])
            r["share_of_loss_recovered"] = sh
        J["rule1"]["s%d" % ses] = r
        T.append("  rule 1, session %d: %s." % (ses, r["verdict"]))
        T.append("    check: L2 write-backs per 64 B of asmread at 8 MiB with evict: %s (needs below 0.2)." % (
            ", ".join("CPU %s %s" % (c, fx(v, 3)) for c, v in sorted(wb.items())) or "no ZC value"))
        T.append("    descriptive: rise of the 8 MiB p95 with evict: %s. Old read control (8 MiB median change): %s." % (
            ", ".join("%s CPU %d %s GB/s" % (k[0], k[1], fx(v)) for k, v in sorted(rises.items())) or "no ZD value",
            ", ".join("CPU %s %s GB/s" % (c, fx(v)) for c, v in sorted(oldc.items())) or "no ZD value"))
    rs = J["rule1"]
    miss = missing_sessions(sorted(int(k[1:]) for k in rs))
    desc = "; ".join("%s: %s" % (k, v["verdict"]) for k, v in sorted(rs.items()))
    if not rs:
        J["overall"] = "no data"
    elif any(v["verdict"].startswith("Insufficient data") for v in rs.values()):
        J["overall"] = "Insufficient data: H1d stays open (%s)%s" % (
            desc, "; session %s missing" % ", ".join(str(s) for s in miss) if miss else "")
    elif miss:
        J["overall"] = "session %s missing: not confirmed yet (%s)" % (", ".join(str(s) for s in miss), desc)
    elif all(v["verdict"] == "H1d supported" for v in rs.values()):
        J["overall"] = "confirmed: H1d supported in both sessions"
    elif all(v["verdict"] == "H1d rejected" for v in rs.values()):
        J["overall"] = "H1d rejected in both sessions"
    else:
        J["overall"] = "not confirmed (%s)" % desc
    T.append("  rule 1 overall: %s." % J["overall"])
    return J, T


# ------------------------------------------------------------------ item 13: ZS
ZS_BASE, ZS_LO, ZS_HI, ZS_TOL = 2.10, 0.50, 0.69, 0.05
ZS_OLD_CYC, ZS_OLD_TOL, ZS_OLD_R = 2.671, 0.02, 0.83
ZS_EXCLUDED = (M1, M8)


def zs_band(r):
    return (ZS_BASE + ZS_LO * r - ZS_TOL, ZS_BASE + ZS_HI * r + ZS_TOL)


def lsq(xs, ys):
    """Least-squares line y = a + b x. Returns (slope, intercept) or (None, None)."""
    n = len(xs)
    if n < 2:
        return None, None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None, None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return b, my - b * mx


def rule_zs_cell(asm, old):
    """Rule of step ZS on one CPU in one session.
    asm, old: {size in bytes: dict(cyc, r)} with cycles per 64 B and L2 refills per 64 B."""
    res = {"sizes": {}, "outside": 0, "evaluated": 0}
    for size in sorted(asm):
        v = asm[size]
        if v["cyc"] is None or v["r"] is None:
            continue
        lo, hi = zs_band(v["r"])
        inside = lo <= v["cyc"] <= hi
        counted = size not in ZS_EXCLUDED
        res["sizes"][size_label(size)] = {"cyc": v["cyc"], "r": v["r"], "band_low": lo, "band_high": hi,
                                          "inside": inside, "counted": counted}
        if counted:
            res["evaluated"] += 1
            res["outside"] += 0 if inside else 1
    res["exceeds"] = res["outside"] > 2
    pts = [(v["r"], v["cyc"]) for v in asm.values() if v["cyc"] is not None and v["r"] is not None]
    res["slope"], res["intercept"] = lsq([p[0] for p in pts], [p[1] for p in pts])
    oc = {}
    for size in sorted(old):
        v = old[size]
        if v["cyc"] is None or v["r"] is None:
            continue
        applies = v["r"] < ZS_OLD_R
        oc[size_label(size)] = {"cyc": v["cyc"], "r": v["r"], "applies": applies,
                                "holds": (abs(v["cyc"] - ZS_OLD_CYC) <= ZS_OLD_TOL) if applies else None}
    res["oldread"] = oc
    res["oldread_fails"] = sum(1 for v in oc.values() if v["holds"] is False)
    res["oldread_checked"] = sum(1 for v in oc.values() if v["applies"])
    return res


def rule_zs_overall(per_cell):
    if not per_cell:
        return "no data: step ZS has no result folder"
    ses = sorted(set(int(k.split("/s")[1]) for k in per_cell))
    miss = missing_sessions(ses)
    desc = ", ".join("%s: %d of %d sizes outside" % (k, v["outside"], v["evaluated"]) for k, v in sorted(per_cell.items()))
    if miss:
        return "session %s missing: no overall verdict yet (%s)" % (", ".join(str(s) for s in miss), desc)
    if len(per_cell) >= 4 and all(v["exceeds"] for v in per_cell.values()):
        return "H1c in its simple form is contradicted: more than 2 sizes outside the band on both CPUs in both " \
               "sessions (%s)" % desc
    return "H1c in its simple form is not contradicted (%s)" % desc


def item13(data):
    T = ["13. ZS: size as the dose (rule of step ZS, hypothesis H1c)", "",
         "r = l2d_cache_refill per 64 B. Band for asmread: cycles per 64 B from %.2f + %.2f r - %.2f to "
         "%.2f + %.2f r + %.2f." % (ZS_BASE, ZS_LO, ZS_TOL, ZS_BASE, ZS_HI, ZS_TOL),
         "All values are medians over the counted windows of the process (20 windows of 0.3 s)."]
    T.append(reading("a size is 'outside' if its cycles per 64 B lie outside the closed band; sizes 1 and 8 MiB "
                     "are printed and not counted; with more than one process in a cell the cell value is the "
                     "median over the processes."))
    J = {"rows": [], "rule": {}, "folders": {}}
    for ses in (1, 2):
        names = data.names("ZS", ses)
        J["folders"]["s%d" % ses] = names
        if not names:
            T.append("  ZS session %d missing." % ses)
            continue
        vals = {}
        out = []
        for (kernel, size, cpu), pl in sorted(group(data.procs("ZS", ses),
                                                    lambda p: (p.kernel, p.size, p.cpu_i)).items(),
                                               key=lambda x: (x[0][0], x[0][2], x[0][1])):
            cs = [counter_proc(p) for p in pl]

            def m(e):
                return med([c["per64"].get(e) for c in cs if c["per64"].get(e) is not None])
            v = {"rate": med([c["rate"] for c in cs if c["rate"] is not None]), "cyc": m("cpu_cycles"),
                 "r": m("l2d_cache_refill"), "l1_long_miss": m("l1d_cache_lmiss_rd"), "l2_wb": m("l2d_cache_wb"),
                 "bus_access": m("bus_access")}
            vals[(kernel, size, cpu)] = v
            row = dict(v, kernel=kernel, size=size_label(size), size_bytes=size, cpu=cpu, session=ses)
            if kernel == "asmread" and v["r"] is not None and v["cyc"] is not None:
                row["band_low"], row["band_high"] = zs_band(v["r"])
                row["inside"] = row["band_low"] <= v["cyc"] <= row["band_high"]
            J["rows"].append(row)
            out.append([kernel, size_label(size), cpu, ses, fx(v["rate"]), fx(v["cyc"], 3), fx(v["r"], 3),
                        fx(v["l1_long_miss"], 3), fx(v["l2_wb"], 3), fx(v["bus_access"], 3),
                        "%s to %s" % (fx(row["band_low"], 3), fx(row["band_high"], 3)) if "inside" in row else "-",
                        ("inside" if row["inside"] else "outside") if "inside" in row else "-"])
        T.append("")
        T.append("ZS session %d (%s):" % (ses, ", ".join(names)))
        T += tbl(["kernel", "size", "cpu", "ses", "rate GB/s", "cycles/64B", "r", "L1 long miss", "L2 write-back",
                  "bus access", "band", "asmread"], out)
        for cpu in sorted(set(c for _, _, c in vals)):
            r = rule_zs_cell({s: v for (k, s, c), v in vals.items() if k == "asmread" and c == cpu},
                             {s: v for (k, s, c), v in vals.items() if k == "oldread" and c == cpu})
            J["rule"][ck(cpu, ses)] = r
            T.append("  CPU %d session %d: asmread outside the band at %d of %d counted sizes (%s): %s. "
                     "Least-squares line (descriptive): cycles per 64 B = %s + %s r. Old read: within %.2f of %.3f "
                     "at %d of %d sizes with r below %.2f." % (
                         cpu, ses, r["outside"], r["evaluated"],
                         ", ".join(s for s, v in r["sizes"].items() if v["counted"] and not v["inside"]) or "none",
                         "more than 2" if r["exceeds"] else "at most 2", fx(r["intercept"], 3), fx(r["slope"], 3),
                         ZS_OLD_TOL, ZS_OLD_CYC, r["oldread_checked"] - r["oldread_fails"], r["oldread_checked"],
                         ZS_OLD_R))
    J["overall"] = rule_zs_overall(J["rule"])
    T.append("  rule overall: %s." % J["overall"])
    return J, T


# ------------------------------------------------------------------ item 14: ZM
def zm_boundaries(p):
    """Every window boundary of a ZM process: [record index i, address of win[i], level before, level after,
    event, level before carried from the last window on a level]. Boundary i lies before window i."""
    d = index_switches(p)
    if d is None:
        return None
    try:
        base = int(p.M.get("win_addr", ""), 16)
    except ValueError:
        base = None
    try:
        wsz = int(p.M.get("win_size", "80"))
    except ValueError:
        wsz = 80
    ev = {s["index"]: s["kind"] for s in d["switches"]}
    out = []
    carried = None
    for j in range(1, d["n"]):
        if d["labels"][j - 1] in ("low", "high", "one"):
            carried = d["labels"][j - 1]
        i = d["index"][j]
        out.append([i, None if base is None else base + wsz * i, d["labels"][j - 1], d["labels"][j],
                    ev.get(i, "none"), carried])
    return {"win_addr": base, "win_size": wsz, "pad": pad_of(p), "boundaries": out, "low": d["low"],
            "high": d["high"]}


def item14(data):
    T = ["14. ZM: kick map (rule 3 of round 4, descriptive, no decision rule)", "",
         "Boundary i lies before window i. Record address = M,win_addr + 80 x i. Offset = pad + 80 x i (the",
         "position in the pad 0 layout). Level before = level of the last window on a level before the boundary."]
    J = {"processes": [], "by_cell": {}, "folders": {}}
    for ses in (1, 2):
        names = data.names("ZM", ses)
        J["folders"]["s%d" % ses] = names
        if not names:
            T.append("  ZM session %d missing." % ses)
            continue
        for cpu, pl in sorted(group(data.procs("ZM", ses), lambda p: p.cpu_i).items()):
            events, table = [], {}
            nproc = two = 0
            for p in sorted(pl, key=lambda p: (pad_of(p), p.idx)):
                z = zm_boundaries(p)
                if z is None:
                    continue
                nproc += 1
                two += 1 if z["high"] is not None else 0
                J["processes"].append({
                    "cpu": cpu, "session": ses, "idx": p.idx, "tag": p.tag, "pad": z["pad"],
                    "win_addr": p.M.get("win_addr"), "low": z["low"], "high": z["high"],
                    "columns": ["record index", "record address", "level before", "level after", "event",
                                "last level before"],
                    "boundaries": [[b[0], None if b[1] is None else "%x" % b[1], b[2], b[3], b[4], b[5]]
                                   for b in z["boundaries"]]})
                for i, addr, before, after, event, carried in z["boundaries"]:
                    off = z["pad"] + z["win_size"] * i
                    t = table.setdefault(off, {"low_up": 0, "low_none": 0, "high_fall": 0, "high_none": 0,
                                               "other": 0})
                    if carried == "low" and event in ("up", "none"):
                        t["low_" + event] += 1
                    elif carried == "high" and event in ("fall", "none"):
                        t["high_" + event] += 1
                    else:
                        t["other"] += 1
                    if event != "none":
                        events.append({"event": event, "pad": z["pad"], "index": i, "offset": off,
                                       "address": None if addr is None else "%x" % addr,
                                       "mod64": None if addr is None else addr % 64,
                                       "mod4096": None if addr is None else addr % 4096,
                                       "mod2048": None if addr is None else addr % 2048, "idx": p.idx})
            J["by_cell"][ck(cpu, ses)] = {
                "processes": nproc, "two_levels": two, "events": events,
                "offset_table_columns": ["offset", "low before: up", "low before: none", "high before: fall",
                                         "high before: none", "other"],
                "offset_table": [[off, t["low_up"], t["low_none"], t["high_fall"], t["high_none"], t["other"]]
                                 for off, t in sorted(table.items())]}
            T.append("")
            T.append("ZM CPU %d session %d (%s): %d processes, %d with two levels, %d events." % (
                cpu, ses, ", ".join(names), nproc, two, len(events)))
            for kind in ("up", "fall"):
                es = [e for e in events if e["event"] == kind and e["address"] is not None]
                for name in ("mod64", "mod2048", "mod4096", "offset"):
                    cnt = {}
                    for e in es:
                        cnt[e[name]] = cnt.get(e[name], 0) + 1
                    T.append("  %-4s %-7s (value x count): %s" % (kind, {"mod64": "mod 64", "mod2048": "mod 2048",
                                                                        "mod4096": "mod 4096",
                                                                        "offset": "offset"}[name],
                                                                 " ".join("%dx%d" % (v, c) for v, c in
                                                                          sorted(cnt.items())) or "-"))
            rows = [[off, t["low_up"], t["low_none"], t["high_fall"], t["high_none"]]
                    for off, t in sorted(table.items()) if t["low_up"] or t["high_fall"]]
            T.append("  offsets with at least one event (%d of %d offsets); counts are processes:" % (
                len(rows), len(table)))
            T += tbl(["offset", "low before: up", "low before: none", "high before: fall", "high before: none"],
                     rows, "    ")
    return J, T


# ------------------------------------------------------------------ item 15: claims
def item15(J, data):
    T = ["15. CLAIMS: verdict of every hypothesis by its recorded rule", ""]
    claims = []

    def names(steps):
        return {"s%d" % s: [n for st in steps for n in data.names(st, s)] for s in (1, 2)}

    def miss(steps):
        return ["%s session %d" % (st, s) for st in steps for s in (1, 2)
                if not data.names(st, s) and not (s == 2 and st in SESSION1_ONLY)]

    def add(cid, statement, rule, per_session, overall, metrics, steps):
        claims.append({"id": cid, "statement": statement, "rule": rule, "per_session": per_session,
                       "overall": overall, "metrics": metrics, "folders": names(steps), "missing": miss(steps)})

    # H1 / P1 / P2
    r1 = J["round1"]
    pc = r1.get("per_cell", {})
    ps = {}
    for ses in (1, 2):
        cs = {k: v for k, v in pc.items() if k.endswith("/s%d" % ses)}
        ps["s%d" % ses] = "; ".join("%s: P1 %s, P2 read %s GB/s (%s), new loop carries %s %% of the lost advantage" % (
            k, v["P1"]["outcome"], fx(v["P2"]["read"]["median"]),
            "repeatable" if v["P2"]["read"]["repeatable"] else "not repeatable",
            fx(v["decomposition"]["new_share_pct"], 1)) for k, v in sorted(cs.items())) or "no verdict available"
    if r1.get("P1"):
        ov = "P1 %s; P2 read confirmed on both CPUs: %s; P2 asmread confirmed on both CPUs: %s; candidate %s" % (
            r1["P1"].get("overall"), (r1["P2"].get("read") or {}).get("confirmed_both"),
            (r1["P2"].get("asmread") or {}).get("confirmed_both"), r1.get("candidate"))
    else:
        ov = "not evaluated here: the round 1 summary file is missing"
    m8 = {"%s/cpu%d/s%d" % (r["size"], r["cpu"], r["session"]): {"new_minus_old": r["new_minus_old"]["median"],
                                                                "gain_pct": r["new_minus_old"]["gain_pct"]}
          for r in r1["cells"] if r["size"] in ("1M", "8M", "16M")}
    add("H1 / P1 / P2", "The old loop keeps its rate from 1 to 8 MiB (P1) and the new loop loses rate (P2), so the "
        "small gain at 8 MiB comes from the new loop.", "design: P1, P2, decomposition; shared repeatability rule",
        ps, ov, m8, ["S2"])
    # H1 two limits, XN
    xn = J["families"]["XN"]
    ps = {}
    for ses in (1, 2):
        cs = {k: v for k, v in xn["rule6"].items() if k.endswith("/s%d" % ses) and not v.get("error")}
        ps["s%d" % ses] = "; ".join("%s: (c) %s; %s" % (k, word(v["c"]), ", ".join(
            "%s (a) %s (b) %s" % (kn, word(kv["a"]), word(kv["b"])) for kn, kv in v["kernels"].items()))
            for k, v in sorted(cs.items())) or "XN missing"
    add("H1 two limits (rule 6 of round 2, XN)", "At 8 MiB the rate of a load-only kernel is min(C_k, S).",
        "rule 6 of round 2", ps, "; ".join("%s: %s" % (k, v) for k, v in sorted(xn["overall"].items())) or "no data",
        {"rule6": xn["rule6"]}, ["XN"])
    zn = J["families"]["ZN"]
    ps = {}
    for ses in (1, 2):
        cs = {k: v for k, v in zn["rule2"].items() if k.endswith("/s%d" % ses)}
        ps["s%d" % ses] = "; ".join("%s: %s" % (k, ", ".join(
            "%s C_k %s, 8M median %s, prediction %s" % (kn, fx(kv["C"]), fx(kv["median_8M"]),
                                                        word(kv["prediction_holds"]))
            for kn, kv in v["kernels"].items())) for k, v in sorted(cs.items())) or "ZN missing"
    add("H1 two limits (rule 2 of round 4, ZN)", "A slow load-only kernel keeps its 32 KiB rate at 8 MiB.",
        "rule 2 of round 4", ps, "; ".join("%s: %s" % (k, v) for k, v in sorted(zn["overall"].items())) or
        "no data: ZN has no result folder", {"rule2": zn["rule2"]}, ["ZN", "YF", "ZD"])
    # H1b
    pf = J["prefetch"]
    ps = {"s%d" % ses: "; ".join("%s: %s" % (k, v["verdict"]) for k, v in sorted(pf["rule3"].items())
                                 if k.endswith("/s%d" % ses)) or "YC or YF missing" for ses in (1, 2)}
    add("H1b", "At 8 MiB the load-only loop is limited by the first-level cache misses that the hardware prefetcher "
        "leaves.", "rule 3 of round 3", ps, pf["overall"],
        {"rule3": pf["rule3"], "contrast_8M": [c for c in pf["contrast"] if c["size"] == "8M"]}, ["YC", "YF"])
    # H1c
    zs = J["ZS"]
    ps = {"s%d" % ses: "; ".join("%s: %d of %d counted sizes outside the band, line %s + %s r" % (
        k, v["outside"], v["evaluated"], fx(v["intercept"], 3), fx(v["slope"], 3))
        for k, v in sorted(zs["rule"].items()) if k.endswith("/s%d" % ses)) or "ZS missing" for ses in (1, 2)}
    add("H1c (via ZS)", "Each line that must come from the SLC costs a fixed number of extra cycles (0.50 to 0.69 "
        "per L2 refill).", "rule of step ZS", ps, zs["overall"], {"rule": zs["rule"]}, ["ZS"])
    # H1d
    ev = J["evict"]
    ps = {"s%d" % ses: (ev["rule1"].get("s%d" % ses) or {}).get("verdict", "ZC and ZD missing") for ses in (1, 2)}
    add("H1d", "Clean buffer lines would raise the 8 MiB rate, because the L2 write-back would carry no data.",
        "rule 1 of round 4", ps, ev["overall"], {"rule1": ev["rule1"]}, ["ZC", "ZD"])
    # H2
    h2 = J["H2"]
    ps = {"s%d" % ses: "; ".join("CPU %s: %d low, %d between, %d high, median gain %s %%" % (
        r["cpu"], r["low"], r["between"], r["high"], fx(r["median_gain_pct"]))
        for r in h2["rows"] if r["session"] == ses) or "H2 missing" for ses in (1, 2)}
    add("H2", "The original 0.94 % gain was measured while the new loop was at the low level.", "H2 rule of round 2",
        ps, "; ".join("%s: %s" % (k, v) for k, v in sorted(h2["verdict"].items())) or "no data",
        {"rows": h2["rows"]}, ["H2"])
    # H3a
    sw = J["switch_timing"]
    ps, anyk = {}, []
    for ses in (1, 2):
        s = sw["XW_sampler"].get("s%d" % ses)
        o = sw["XW_onset"].get("s%d" % ses)
        if not s:
            ps["s%d" % ses] = "XW missing"
            continue
        anyk.append(s["any_key_accompanies"])
        keys = [k for k, v in s["keys"].items() if v["accompanies_up"] or v["accompanies_down"]]
        ps["s%d" % ses] = "rule 4: %s; rule 5: %s" % (
            "keys that accompany the switches: " + ", ".join(keys) if keys
            else "no listed key accompanies the switches",
            "; ".join("%s: %s" % (c, v["verdict"]) for c, v in sorted((o or {}).get("conditions", {}).items())
                      if v["has_previous_activity"]))
    T.append(reading("H3a (a kernel timer on the worker's CPU triggers the switch) is 'not supported' in a session "
                     "if no listed sampler key accompanies the switches by rule 4; rule 4 names a coinciding "
                     "activity and cannot confirm a cause."))
    if not anyk:
        ov = "no data"
    elif len(anyk) < 2:
        ov = "session 2 missing: %s in session 1, not confirmed yet" % (
            "a key accompanies the switches" if anyk[0] else "H3a not supported")
    else:
        ov = "H3a not supported in both sessions" if not any(anyk) else \
            "a sampler key accompanies the switches in %d of 2 sessions" % sum(1 for a in anyk if a)
    add("H3a", "A kernel timer on the worker's CPU triggers the level switch.", "rules 4 and 5 of round 2", ps, ov,
        {"sampler": {k: {kk: vv for kk, vv in v["keys"].items() if kk in SAMPLER_KEYS}
                     for k, v in sw["XW_sampler"].items()}}, ["XW"])
    # H4 (what differs between the levels)
    cn = J["counters"]
    dif = sorted(e for e, v in cn["rule3"].items() if any(c["differs"] for c in v["per_cell"].values()))
    ps = {"s%d" % ses: ("events that differ on at least one CPU: " + (", ".join(sorted(
        e for e, v in cn["rule3"].items() if any(c["differs"] for k, c in v["per_cell"].items()
                                                 if k.endswith("/s%d" % ses)))) or "none"))
          if any(data.names(st, ses) for st in ("XCA", "XCB", "XCC")) else "XCA, XCB, XCC missing" for ses in (1, 2)}
    add("H4 (counters by level)", "Some event counts differ between the low and the high level.", "rule 3 of round 2",
        ps, "; ".join("%s: %s" % (e, cn["rule3"][e]["overall"]) for e in dif) or "no event differs",
        {"acceptance": cn["acceptance"]}, ["XCA", "XCB", "XCC", "S4"])
    # H7
    yl, yp = J["YL"], J["YP"]
    ps = {"s%d" % ses: "YL: %s. YP: %s; hot-copy prediction %s" % (
        "; ".join("%s %s" % (k, v["verdict"]) for k, v in sorted(yl["verdict"].items())
                  if k.endswith("/s%d" % ses)) or "missing",
        yp["verdict"].get("s%d" % ses, "missing"),
        word((yp["hot_copy"].get("s%d" % ses) or {}).get("prediction_holds"))) for ses in (1, 2)}
    add("H7", "The low or high level depends on the address of the runner's window record, not on time.",
        "rules 1 and 2 of round 3 (rule 2 with the replaced statistic, see item 10)", ps,
        "YL: %s. YP: %s" % (yl["overall"], yp["overall"]),
        {"YL": yl["verdict"], "YP_shift": [{k: r.get(k) for k in ("pad", "cpu", "session", "predicted", "median_shift",
                                                                   "match")} for r in yp["shift"]]}, ["YL", "YP"])
    for c in claims:
        T.append("%s: %s" % (c["id"], c["statement"]))
        T.append("  rule: %s" % c["rule"])
        for s in ("s1", "s2"):
            T.append("  session %s: %s" % (s[1], c["per_session"].get(s)))
            T.append("    folders: %s" % (", ".join(c["folders"][s]) or "none"))
        T.append("  overall: %s" % c["overall"])
        if c["missing"]:
            T.append("  missing data: %s" % ", ".join(c["missing"]))
        T.append("")
    return claims, T


# ------------------------------------------------------------------ item 16: supplementary evaluations
SUP_LABEL = "supplementary, defined after the data was seen"
SUP_MIN_PROCS = 5       # an S4 switch window enters the reference series with at least this many processes
SUP_NEED = {"up": "low", "fall": "high"}      # the level a process must have before it can show the event
SUP_SLOW = (("oldread", "S2"), ("read_nop96", "ZN"), ("read_nop128", "ZN"))


def pct(a, b):
    return (100.0 * a / b) if b else None


def sup_reference(data, kind, min_procs=SUP_MIN_PROCS):
    """Reference series of round 1: the switch windows at which at least `min_procs` of the load-only 60 s
    processes of step S4 (all sessions that exist, pooled) show a switch of this kind ('up' or 'fall')."""
    seen, nproc, ses_have = {}, 0, []
    for ses in (1, 2):
        if not data.names("S4", ses):
            continue
        ses_have.append(ses)
        for p in data.procs("S4", ses):
            d = index_switches(p) if p.kernel in LOAD_ONLY else None
            if d is None:
                continue
            nproc += 1
            for s in d["switches"]:
                if s["kind"] == kind:
                    seen.setdefault(s["index"], set()).add((ses, p.cpu_i, p.idx))
    cnt = {w: len(v) for w, v in seen.items()}
    series = sorted(w for w, n in cnt.items() if n >= min_procs)
    same = [m for m in range(1, nproc + 1) if sorted(w for w, n in cnt.items() if n >= m) == series]
    return {"series": series, "sessions": ses_have, "processes_pooled": nproc, "min_processes": min_procs,
            "same_series_from": min(same) if same and series else None,
            "same_series_to": max(same) if same and series else None,
            "windows": [{"window": w, "processes": cnt[w],
                         "by_session": {"s%d" % s: sum(1 for x in seen[w] if x[0] == s) for s in ses_have}}
                        for w in sorted(cnt) if cnt[w] >= 2],
            "folders": [n for s in ses_have for n in data.names("S4", s)]}


def sup_predicted(series, pad, win_size=80, nwin=100):
    """The reference windows moved earlier by pad / win_size windows, cut to the windows 0 to nwin - 1."""
    out = []
    for u in series:
        w = u - pad / float(win_size)
        if 0 <= w <= nwin - 1:
            out.append(int(w) if w == int(w) else w)
    return out


def sup_count_match(events, predicted, tol=1):
    """How many of `events` lie within `tol` windows of a predicted window."""
    return sum(1 for e in events if any(abs(e - w) <= tol for w in predicted))


def sup_level_before(d, w, fixed=None):
    """Level of the process just before the windows w - 1 to w + 1: the label ('low' or 'high') of the last
    window with a record index of at most w - 2 that sits on a level. None if there is no such window.
    `fixed` is the level of a process that shows one level only."""
    if fixed:
        return fixed
    best, lev = -1, None
    for i, lab in zip(d["index"], d["labels"]):
        if best < i <= w - 2 and lab in ("low", "high"):
            best, lev = i, lab
    return lev


def sup_eligible(d, events, predicted, need, fixed=None, tol=1):
    """(predicted windows before which the process has the level `need`, how many of them have an event
    within `tol` windows)."""
    n = hit = 0
    for w in predicted:
        if sup_level_before(d, w, fixed) != need:
            continue
        n += 1
        hit += 1 if any(abs(e - w) <= tol for e in events) else 0
    return n, hit


def sup_sum(rows):
    ne, nm = sum(r["n_events"] for r in rows), sum(r["n_events_match"] for r in rows)
    nl, nh = sum(r["n_eligible"] for r in rows), sum(r["n_eligible_hit"] for r in rows)
    return {"processes": len(rows), "n_events": ne, "n_events_match": nm, "share_events_match_pct": pct(nm, ne),
            "n_predicted": sum(r["n_predicted"] for r in rows), "n_eligible": nl, "n_eligible_hit": nh,
            "share_eligible_hit_pct": pct(nh, nl)}


def sup_yp(data, recorded):
    """YP against the round 1 series (item 1 of the supplementary evaluations)."""
    names = {"up": ("up", "ups", "low"), "fall": ("fall", "falls", "high")}
    J = {"label": SUP_LABEL, "recorded_verdict": recorded, "reference": {}, "predicted": [], "rows": [], "cells": [],
         "summary": [], "summary_text": {"up": {}, "fall": {}},
         "folders": {"s%d" % s: data.names("YP", s) for s in (1, 2)}}
    T = ["16.1 YP against the round 1 series (%s)" % SUP_LABEL, "",
         "Recorded verdict of rule 2 of round 3 (block 10, unchanged): %s." % recorded,
         "This evaluation does not replace it. It compares the padded runs with the 60 s runs of round 1 (step S4)",
         "in place of the pad 0 processes of step YP.",
         reading("supplementary: the reference series U (ups) and the reference series of the falls are the switch "
                 "windows at which at least %d of the load-only S4 processes of round 1 show the switch (the "
                 "sessions that exist are pooled, the window must be the same)." % SUP_MIN_PROCS),
         reading("supplementary: the prediction for pad P is every reference window minus P / 80, cut to the windows "
                 "of the run (0 to 99); an event 'matches' within 1 window; a process is 'at the low level before "
                 "window w' when the last window up to w - 2 that sits on a level is low; a process with one level "
                 "gets the nearer of the two level medians of the two-level YP processes of its CPU and session.")]
    for kind in ("up", "fall"):
        r = sup_reference(data, kind)
        J["reference"][kind] = r
        T.append("  reference %s windows of round 1: %s (%d load-only processes of S4, sessions %s; the same series "
                 "results for every limit from %s to %s processes)." % (
                     names[kind][0], r["series"] or "none: S4 missing", r["processes_pooled"],
                     ", ".join(str(s) for s in r["sessions"]) or "none", r["same_series_from"], r["same_series_to"]))
    seen_pred = set()
    for ses in (1, 2):
        if not data.names("YP", ses):
            T.append("  YP session %d missing." % ses)
            continue
        ds = [(p, index_switches(p)) for p in data.procs("YP", ses) if p.M.get("hot_copy") != "1"]
        ds = [(p, d) for p, d in ds if d is not None]
        ref = {}
        for cpu, pl in group([x for x in ds if x[1]["high"] is not None], lambda x: x[0].cpu_i).items():
            ref[cpu] = (med([d["low"] for _, d in pl]), med([d["high"] for _, d in pl]))
        for p, d in sorted(ds, key=lambda x: (pad_of(x[0]), x[0].cpu_i, x[0].idx)):
            pad, fixed, lev = pad_of(p), None, "two levels"
            if d["high"] is None:
                lo_hi = ref.get(p.cpu_i)
                fixed = "unknown" if not lo_hi else \
                    ("low" if abs(d["low"] - lo_hi[0]) <= abs(d["low"] - lo_hi[1]) else "high")
                lev = "one level, %s" % fixed
            try:
                wsz = int(p.M.get("win_size", 80) or 80)
            except ValueError:
                wsz = 80
            for kind in ("up", "fall"):
                ev = [s["index"] for s in d["switches"] if s["kind"] == kind]
                pred = sup_predicted(J["reference"][kind]["series"], pad, wsz, len(rec_windows(p)))
                ne, nh = sup_eligible(d, ev, pred, SUP_NEED[kind], fixed)
                J["rows"].append({"kind": kind, "pad": pad, "cpu": p.cpu_i, "session": ses, "idx": p.idx,
                                  "levels": lev, "events": ev, "predicted_windows": pred, "n_events": len(ev),
                                  "n_events_match": sup_count_match(ev, pred), "n_predicted": len(pred),
                                  "n_eligible": ne, "n_eligible_hit": nh})
                if (kind, pad) not in seen_pred:
                    seen_pred.add((kind, pad))
                    J["predicted"].append({"kind": kind, "pad": pad, "windows": pred})
    for kind in ("up", "fall"):
        one, many, need = names[kind]
        rows = [r for r in J["rows"] if r["kind"] == kind]
        T.append("")
        T.append("  %s of each YP process against the prediction from round 1:" % many)
        T += tbl(["pad", "cpu", "ses", "idx", "levels", "%s windows" % one, "predicted windows",
                  "%s that match" % many, "predicted with the process %s before" % need, "of these with %s %s" % (
                      "an" if kind == "up" else "a", one)],
                 [[r["pad"], r["cpu"], r["session"], r["idx"], r["levels"],
                   " ".join(str(e) for e in r["events"]) or "-", " ".join(str(w) for w in r["predicted_windows"]) or "-",
                   "%d of %d" % (r["n_events_match"], r["n_events"]), r["n_eligible"], r["n_eligible_hit"]]
                  for r in rows], "    ")
        out = []
        for (pad, cpu, ses), rs in sorted(group(rows, lambda r: (r["pad"], r["cpu"], r["session"])).items()):
            c = sup_sum(rs)
            c.update(kind=kind, pad=pad, cpu=cpu, session=ses)
            J["cells"].append(c)
            out.append([pad, cpu, ses, c["processes"], "%d of %d" % (c["n_events_match"], c["n_events"]),
                        fx(c["share_events_match_pct"], 1), "%d of %d" % (c["n_eligible_hit"], c["n_eligible"]),
                        fx(c["share_eligible_hit_pct"], 1)])
        if out:
            T.append("  per pad, CPU and session:")
            T += tbl(["pad", "cpu", "ses", "procs", "%s that match" % many, "share %",
                      "predicted windows (process %s before) with %s %s" % (need, "an" if kind == "up" else "a", one),
                      "share %"], out, "    ")
        ses_have = sorted(set(r["session"] for r in rows))

        def line(rs):
            c = sup_sum(rs)
            return c, "%d of %d %s lie within 1 window of a predicted window (%s %%). %d of %d predicted windows " \
                      "with the process at the %s level before show %s %s within 1 window (%s %%)" % (
                          c["n_events_match"], c["n_events"], many, fx(c["share_events_match_pct"], 1),
                          c["n_eligible_hit"], c["n_eligible"], need, "an" if kind == "up" else "a", one,
                          fx(c["share_eligible_hit_pct"], 1))
        for grp, sel in (("padded", lambda r: r["pad"] != 0), ("pad 0", lambda r: r["pad"] == 0)):
            for ses in ses_have:
                c, txt = line([r for r in rows if sel(r) and r["session"] == ses])
                c.update(kind=kind, group=grp, session=ses)
                J["summary"].append(c)
                txt = "%s, %s runs, session %d: %s" % (many, grp if grp == "pad 0" else "padded", ses, txt)
                if grp == "padded":
                    J["summary_text"][kind]["s%d" % ses] = txt
                T.append("  summary, %s." % txt)
        if rows:
            c, txt = line([r for r in rows if r["pad"] != 0])
            c.update(kind=kind, group="padded", session="all that exist")
            J["summary"].append(c)
            miss = missing_sessions(ses_have)
            J["summary_text"][kind]["overall"] = ("%s, padded runs, %s: %s" % (
                many, "session %s missing, one session only (not confirmed)" % ", ".join(str(s) for s in miss)
                if miss else "both sessions", txt))
        else:
            J["summary_text"][kind]["overall"] = "no data: YP has no result folder"
        T.append("  summary, %s." % J["summary_text"][kind]["overall"])
    return J, T


def sup_old_without_adds(cells):
    """Old read (step S2) against read_sparse (step XN): the same loads and the same count of instructions
    per 128 B, with no-operation instructions in place of the vector adds."""
    J = {"label": SUP_LABEL, "rows": [], "summary": []}
    T = ["16.2 Old read without its vector adds: read_sparse of step XN against old read of step S2 (%s)" % SUP_LABEL,
         "", "Cell medians in GB/s. ratio = read_sparse / old read. This is a comparison of two kernels of two",
         "steps. The two loops differ in the adds, and also in the place of the loop in the code."]
    for ses in (1, 2):
        s2, xn = cells("S2", ses), cells("XN", ses)
        if s2 is None or xn is None:
            T.append("  session %d: %s missing." % (ses, " and ".join(n for n, c in (("S2", s2), ("XN", xn)) if c is None)))
            continue
        for size in (K32, M1, M8):
            for cpu in sorted(set(c for (k, s, c) in s2 if k == "oldread" and s == size) |
                              set(c for (k, s, c) in xn if k == "read_sparse" and s == size)):
                a, b = s2.get(("oldread", size, cpu)), xn.get(("read_sparse", size, cpu))
                a, b = (a or {}).get("median"), (b or {}).get("median")
                J["rows"].append({"size": size_label(size), "cpu": cpu, "session": ses, "oldread": a, "read_sparse": b,
                                  "ratio": (b / a) if a and b else None, "difference": (b - a) if a and b else None})
    T += tbl(["size", "cpu", "ses", "old read (S2)", "read_sparse (XN)", "ratio", "difference"],
             [[r["size"], r["cpu"], r["session"], fx(r["oldread"]), fx(r["read_sparse"]), fx(r["ratio"], 3),
               fx(r["difference"])] for r in sorted(J["rows"], key=lambda r: ((K32, M1, M8).index(
                   {"32K": K32, "1M": M1, "8M": M8}[r["size"]]), r["cpu"], r["session"]))])
    for size in ("32K", "1M", "8M"):
        rs = [r for r in J["rows"] if r["size"] == size and r["ratio"] is not None]
        if not rs:
            continue
        s = {"size": size, "cells": len(rs), "oldread_min": min(r["oldread"] for r in rs),
             "oldread_max": max(r["oldread"] for r in rs), "read_sparse_min": min(r["read_sparse"] for r in rs),
             "read_sparse_max": max(r["read_sparse"] for r in rs), "ratio_min": min(r["ratio"] for r in rs),
             "ratio_max": max(r["ratio"] for r in rs), "sessions": sorted(set(r["session"] for r in rs))}
        J["summary"].append(s)
        T.append("  %s, %d cells of CPU and session: old read %s to %s GB/s, read_sparse %s to %s GB/s, ratio %s to %s." % (
            size, s["cells"], fx(s["oldread_min"]), fx(s["oldread_max"]), fx(s["read_sparse_min"]),
            fx(s["read_sparse_max"]), fx(s["ratio_min"], 3), fx(s["ratio_max"], 3)))
    return J, T


def sup_prefetch(P, recorded):
    """The prefetch family at 1 MiB and 8 MiB, from the rows of block 11 (steps YC and YF)."""
    J = {"label": SUP_LABEL, "recorded_verdict": recorded, "rows": [], "summary": [], "summary_text": {}}
    T = ["16.3 The prefetch family at 1 MiB and at 8 MiB (%s)" % SUP_LABEL, "",
         "Recorded verdict of rule 3 of round 3 (block 11, unchanged): %s." % recorded,
         "kept = L1 long misses per line of the prefetch kernel / those of asmread (step YC, one process per cell).",
         "difference = cell median of the prefetch kernel minus cell median of asmread (step YF, 6 processes), GB/s."]
    share = {(r["kernel"], r["size"], r["cpu"], r["session"]): r["share"] for r in P.get("share", [])}
    rate = {(r["kernel"], r["size"], r["cpu"], r["session"]): r["median"] for r in P.get("YF", [])}
    keys = sorted(set(k for k in list(share) + list(rate) if k[0] in PF_KERNELS and k[1] in ("1M", "8M")),
                  key=lambda k: (k[1] != "1M", PF_KERNELS.index(k[0]), k[2], k[3]))
    for k in keys:
        s, r, a = share.get(k), rate.get(k), rate.get(("asmread",) + k[1:])
        J["rows"].append({"kernel": k[0], "size": k[1], "cpu": k[2], "session": k[3], "share_kept": s,
                          "removed_pct": None if s is None else 100.0 * (1.0 - s), "rate": r, "asmread_rate": a,
                          "difference": (r - a) if r is not None and a is not None else None})
    T += tbl(["kernel", "size", "cpu", "ses", "kept", "removed %", "rate", "asmread", "difference"],
             [[r["kernel"], r["size"], r["cpu"], r["session"], fx(r["share_kept"], 3), fx(r["removed_pct"], 1),
               fx(r["rate"]), fx(r["asmread_rate"]), fx(r["difference"])] for r in J["rows"]])
    ses_have = sorted(set(r["session"] for r in J["rows"]))
    miss = missing_sessions(ses_have)
    scope = "no data" if not ses_have else ("session %s missing, one session only (not confirmed)" % ", ".join(
        str(s) for s in miss) if miss else "both sessions")
    for size, name in (("1M", "1 MiB"), ("8M", "8 MiB")):
        rs = [r for r in J["rows"] if r["size"] == size and r["removed_pct"] is not None and r["difference"] is not None]
        if not rs:
            J["summary_text"][size] = "at %s: Insufficient data (YC and YF are both needed)" % name
            T.append("  %s." % J["summary_text"][size])
            continue
        low = [r for r in rs if r["difference"] < 0]
        dis = ["%s CPU %d session %d (%+.2f GB/s)" % (r["kernel"], r["cpu"], r["session"], r["difference"])
               for r in rs if r["difference"] >= 0]
        s = {"size": size, "cells": len(rs), "cells_lower": len(low),
             "removed_pct_min": min(r["removed_pct"] for r in rs), "removed_pct_max": max(r["removed_pct"] for r in rs),
             "lower_by_min": min(-r["difference"] for r in low) if low else None,
             "lower_by_max": max(-r["difference"] for r in low) if low else None, "not_lower": dis,
             "sessions": ses_have}
        J["summary"].append(s)
        s["kept_pct_min"], s["kept_pct_max"] = 100.0 - s["removed_pct_max"], 100.0 - s["removed_pct_min"]
        if s["removed_pct_min"] >= 0:
            txt = "at %s (%s) the prefetch removes %s to %s %% of the asmread first-level long misses, and the rate "                   "is " % (name, scope, fx(s["removed_pct_min"], 1), fx(s["removed_pct_max"], 1))
        else:
            txt = "at %s (%s) the prefetch kernels keep %s to %s %% of the asmread first-level long misses (above "                   "100 %%: more misses than asmread), and the rate is " % (
                      name, scope, fx(s["kept_pct_min"], 1), fx(s["kept_pct_max"], 1))
        if low:
            txt += "%s to %s GB/s lower than asmread in %s%d cells of kernel, CPU and session" % (
                fx(s["lower_by_min"]), fx(s["lower_by_max"]), "all " if len(low) == len(rs) else "%d of " % len(low),
                len(rs))
        else:
            txt += "lower than asmread in 0 of %d cells" % len(rs)
        if dis:
            txt += "; cells that disagree: " + ", ".join(dis)
        J["summary_text"][size] = txt
        T.append("  %s." % txt)
    # 32 KiB: the data is in the first-level cache, so a difference to asmread there is not a cost of misses
    d32 = [rate[k] - rate[("asmread",) + k[1:]] for k in sorted(rate)
           if k[0] in PF_KERNELS and k[1] == "32K" and rate.get(k) is not None
           and rate.get(("asmread",) + k[1:]) is not None]
    if d32:
        low = [-d for d in d32 if d < 0]
        J["at_32K"] = {"cells": len(d32), "cells_lower": len(low), "lower_by_min": min(low) if low else None,
                       "lower_by_max": max(low) if low else None, "difference_min": min(d32),
                       "difference_max": max(d32)}
        J["summary_text"]["32K"] = (
            "at 32 KiB (%s), where the data is in the first-level cache, the cell median of a prefetch kernel minus that of "
            "asmread is %s to %s GB/s, and it is below 0 in %d of %d cells of kernel, CPU and session" % (
                scope, fx(min(d32)), fx(max(d32)), len(low), len(d32)))
        T.append("  %s." % J["summary_text"]["32K"])
    return J, T


def sup_gain(data, cells):
    """Gain of asmread over a slow kernel at 8 MiB, predicted from two rates: the 32 KiB rate of the slow
    kernel and the two levels of asmread at 8 MiB."""
    J = {"label": SUP_LABEL, "rows": [], "asmread_source": {}}
    T = ["16.4 Gain at 8 MiB predicted from two rates (%s)" % SUP_LABEL, "",
         "C_k = cell median of the slow kernel k at 32 KiB. low, high = cell 5th and 95th percentile of asmread at",
         "8 MiB (the two levels), from YF of the same session if it exists, else from ZD without evict.",
         "predicted gain range = low / C_k - 1 to high / C_k - 1. measured gain = asmread 8 MiB cell median /",
         "8 MiB cell median of k - 1. All gains in percent. 'inside' compares the unrounded values."]
    for ses in (1, 2):
        src = "YF" if data.names("YF", ses) else "ZD" if data.names("ZD", ses) else None
        if src is None:
            T.append("  session %d: asmread at 8 MiB missing (YF and ZD)." % ses)
            continue
        J["asmread_source"]["s%d" % ses] = {"step": src, "folders": data.names(src, ses)}
        asm = cells_of([p for p in data.procs(src, ses) if p.kernel == "asmread" and evict_of(p) == 0])
        for kernel, step in SUP_SLOW:
            kc = cells(step, ses)
            if kc is None:
                T.append("  session %d: %s missing (kernel %s)." % (ses, step, kernel))
                continue
            for cpu in sorted(set(c for (k, _, c) in kc if k == kernel)):
                c32, c8, a = kc.get((kernel, K32, cpu)), kc.get((kernel, M8, cpu)), asm.get(("asmread", M8, cpu))
                C, k8 = (c32 or {}).get("median"), (c8 or {}).get("median")
                r = {"kernel": kernel, "step": step, "asmread_step": src, "cpu": cpu, "session": ses, "C": C,
                     "median_8M": k8, "asmread_low": (a or {}).get("p5"), "asmread_high": (a or {}).get("p95"),
                     "asmread_median": (a or {}).get("median"), "predicted_low_pct": None, "predicted_high_pct": None,
                     "measured_pct": None, "inside": None}
                if C and k8 and a and a["median"] is not None:
                    r["predicted_low_pct"] = 100.0 * (a["p5"] / C - 1.0)
                    r["predicted_high_pct"] = 100.0 * (a["p95"] / C - 1.0)
                    r["measured_pct"] = 100.0 * (a["median"] / k8 - 1.0)
                    r["inside"] = r["predicted_low_pct"] <= r["measured_pct"] <= r["predicted_high_pct"]
                J["rows"].append(r)
    T += tbl(["kernel", "cpu", "ses", "step", "C_k", "asmread from", "low", "high", "predicted gain %", "asmread median",
              "8M median of k", "measured gain %", "inside"],
             [[r["kernel"], r["cpu"], r["session"], r["step"], fx(r["C"]), r["asmread_step"], fx(r["asmread_low"]),
               fx(r["asmread_high"]), "%s to %s" % (fx(r["predicted_low_pct"]), fx(r["predicted_high_pct"])),
               fx(r["asmread_median"]), fx(r["median_8M"]), fx(r["measured_pct"]),
               "NA" if r["inside"] is None else ("yes" if r["inside"] else "no")]
              for r in sorted(J["rows"], key=lambda r: ([k for k, _ in SUP_SLOW].index(r["kernel"]), r["cpu"],
                                                        r["session"]))])
    ev = [r for r in J["rows"] if r["inside"] is not None]
    out = ["%s CPU %d session %d" % (r["kernel"], r["cpu"], r["session"]) for r in ev if not r["inside"]]
    have = set((r["kernel"], r["session"]) for r in ev)
    miss = ["%s session %d" % (k, s) for k, _ in SUP_SLOW for s in (1, 2) if (k, s) not in have]
    J["cells"], J["cells_inside"], J["outside"], J["missing"] = len(ev), len(ev) - len(out), out, miss
    J["summary_text"] = "no data" if not ev else (
        "the measured gain lies inside the predicted range in %d of %d cells of kernel, CPU and session%s%s" % (
            len(ev) - len(out), len(ev), ("; outside: " + ", ".join(out)) if out else "",
            ("; missing: " + ", ".join(miss)) if miss else ""))
    T.append("  %s." % J["summary_text"])
    return J, T


def item16(J, data):
    T = ["16. SUPPLEMENTARY EVALUATIONS (%s)" % SUP_LABEL, "",
         "Every evaluation of this block was defined after the data was seen. None of them replaces a verdict of",
         "block 15. The recorded verdict is printed beside each evaluation that belongs to a recorded rule.", ""]
    memo = {}

    def cells(step, ses):
        """cells_of the step and session, or None if the folder is missing."""
        if (step, ses) not in memo:
            memo[(step, ses)] = cells_of(data.procs(step, ses)) if data.names(step, ses) else None
        return memo[(step, ses)]

    out = {"label": SUP_LABEL}
    for key, (j, t) in (("yp_round1", sup_yp(data, J["YP"]["overall"])),
                        ("old_without_adds", sup_old_without_adds(cells)),
                        ("prefetch_1M", sup_prefetch(J["prefetch"], J["prefetch"]["overall"])),
                        ("gain_from_two_rates", sup_gain(data, cells))):
        out[key] = j
        T += t + [""]
    return out, T[:-1]


# ------------------------------------------------------------------ build and main
def build(results=RESULTS, summary=None):
    """Returns (json object, text)."""
    del READINGS[:]
    data = Data(results)
    summary = summary if summary is not None else os.path.join(HERE, "s12-summary.json")
    J = {"tool": "final8.py", "results_folder": results,
         "folders": {"%s/s%d" % k: [os.path.basename(d) for d in v] for k, v in sorted(data.folders.items())}}
    parts = []
    for key, fn in (("inventory", item1), ("round1", lambda d: item2(d, summary)), ("size_curve", item3),
                    ("levels", item4), ("switch_timing", item5), ("counters", item6), ("families", item7),
                    ("H2", item8), ("YL", item9), ("YP", item10), ("prefetch", item11), ("evict", item12),
                    ("ZS", item13), ("ZM", item14)):
        J[key], T = fn(data)
        parts.append(T)
    J["claims"], T = item15(J, data)
    parts.append(T)
    J["supplementary"], T = item16(J, data)
    parts.append(T)
    J["readings"] = list(READINGS)
    head = ["final8.py: numbers of the tackle-8mb investigation. Rates in GB/s (1 GB = 1e9 bytes).",
            "Results folder: %s" % results,
            "Missing step folders: %s" % (", ".join(
                "%s s%d" % (st, s) for st in STEPS for s in (1, 2)
                if (st, s) not in data.folders and not (s == 2 and st in SESSION1_ONLY)) or "none"),
            "A line that starts with 'reading:' marks a detail that the decisions file leaves open.", ""]
    text = "\n".join(head)
    for T in parts:
        text += "\n".join(T) + "\n\n" + "=" * 100 + "\n"
    text += "READINGS (all 'reading:' choices of this output)\n" + "\n".join("  - " + r for r in READINGS) + "\n"
    return J, text


def main(argv=None):
    ap = argparse.ArgumentParser(description="Final numbers of the tackle-8mb investigation.")
    ap.add_argument("--results", default=RESULTS, help="results folder (default %(default)s)")
    ap.add_argument("--out-dir", default=HERE, help="folder for final8.json and final8.txt (default %(default)s)")
    ap.add_argument("--summary", default=None, help="round 1 summary of analyze8.py (default s12-summary.json "
                                                    "beside this script)")
    a = ap.parse_args(argv)
    J, text = build(a.results, a.summary)
    with open(os.path.join(a.out_dir, "final8.json"), "w") as f:
        json.dump(J, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(a.out_dir, "final8.txt"), "w") as f:
        f.write(text)
    print("wrote %s and %s" % (os.path.join(a.out_dir, "final8.json"), os.path.join(a.out_dir, "final8.txt")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
