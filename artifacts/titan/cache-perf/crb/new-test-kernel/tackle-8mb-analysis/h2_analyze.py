#!/usr/bin/env python3
"""h2_analyze.py - the test of hypothesis H2: the original program at 8 MiB.

H2: the original gain of 0.94 % was measured while the new read loop was at
its low level. run_h2.sh ran the two original binaries (bw_old = old read,
bw_new = new read) many times at 8 MiB. This script reads its H2.csv files
and prints, for each session and CPU:

  1. every process: its three repetition rates, their median and maximum;
  2. the gain new/old of each pair of neighbouring processes;
  3. the class of every new-read repetition: "low" (rate <= --low-max),
     "high" (rate >= --high-min) or "between".

It prints the numbers of the original run of 2026-11-13 (one-thread.csv,
8 MiB, read kernel) in the same form first.

All rates are in GB/s (1 GB = 1e9 bytes), column aggregate_GBps of the csv.
gain = 100 x (new / old - 1), in percent.

Usage: h2_analyze.py [--results DIR] [--original FILE] [--low-max 69.5]
                     [--high-min 70.5] [H2.csv ...]
  Without file arguments it reads DIR/h2-s*-*/H2.csv (DIR defaults to the
  results folder of this project).
Exit status: 0; 2 if a file cannot be read or holds a line it cannot place.
"""
import argparse
import glob
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "..", "results"))
ORIGINAL = os.path.join(RESULTS, "kernels-20261113T181222Z", "one-thread.csv")
BYTES_8M = "8M"
HEAD = re.compile(r"-- binary (\S+) kernel (\S+) threads (\d+) cpus (\S+) bytes (\S+) round (\d+) load (\S+) utc (\S+)(.*)$")
EXTRA = re.compile(r" (session|idx|pair|pos|tag|waited_s) (\S+)")
BINARIES = ("bw_old", "bw_new")
NAME = {"bw_old": "old", "bw_new": "new"}


def gain(new, old):
    """gain of new over old, in percent"""
    return 100.0 * (new / old - 1.0)


def classify(rate, low_max, high_min):
    """class of one repetition rate (GB/s) against the two levels"""
    if rate <= low_max:
        return "low"
    if rate >= high_min:
        return "high"
    return "between"


def parse(path):
    """[process] of one csv file written by run_kernels.sh or run_h2.sh.

    A process is a dict: binary, kernel, cpu, bytes, round, load, utc, rates
    (list of float, the repetitions in order), status ("ok", "killed",
    "failed"), n (its place in the file, from 0), and for run_h2.sh also
    session, idx, pair, pos, tag."""
    procs, cur = [], None
    with open(path) as f:
        for line in f:
            line = line.strip()
            m = HEAD.match(line)
            if m:
                cur = dict(binary=m.group(1), kernel=m.group(2), cpu=m.group(4), bytes=m.group(5),
                           round=int(m.group(6)), load=m.group(7), utc=m.group(8), rates=[],
                           status="ok", n=len(procs), file=path)
                for k, v in EXTRA.findall(m.group(9)):
                    cur[k] = v if k == "tag" else int(v)
                procs.append(cur)
                continue
            if line.startswith("-- killed") or line.startswith("-- failed"):
                if cur is None:
                    raise ValueError("%s: '%s' before any process" % (path, line))
                cur["status"] = line.split()[1]
                continue
            p = line.split(",")
            if len(p) > 6 and p[3].isdigit():
                if cur is None or p[0] != cur["kernel"]:
                    raise ValueError("%s: row '%s' does not belong to the header before it" % (path, line))
                if int(p[3]) != len(cur["rates"]):
                    raise ValueError("%s: repetition %s out of order in '%s'" % (path, p[3], line))
                cur["rates"].append(float(p[6]))
    return procs


def complete(p):
    return p["status"] == "ok" and len(p["rates"]) == 3


def pairs_of(procs):
    """[(old process, new process)] of the neighbouring pairs of one CPU and session.

    With a "pair" field (run_h2.sh) the two processes of one pair number
    belong together. Without it (the original run) the processes of one round
    belong together: the original ran bw_old and bw_new directly one after
    the other. Only complete processes are paired."""
    by = {}
    for p in procs:
        if complete(p):
            by.setdefault(p.get("pair", p["round"]), {}).setdefault(p["binary"], []).append(p)
    out = []
    for key in sorted(by):
        d = by[key]
        if len(d.get("bw_old", [])) == 1 and len(d.get("bw_new", [])) == 1:
            out.append((key, d["bw_old"][0], d["bw_new"][0]))
    return out


def fmt_rates(rates):
    return " ".join("%6.2f" % r for r in rates) if rates else "(no repetition)"


def report_group(title, procs, low_max, high_min, out):
    """the three parts for the processes of one CPU in one session (or one original CPU)"""
    w = out.append
    w("")
    w("== %s ==" % title)
    w("processes (rates in GB/s, the three repetitions in order):")
    for b in BINARIES:
        mine = [p for p in procs if p["binary"] == b]
        for p in mine:
            tag = "idx %2d pair %2d pos %d" % (p["idx"], p["pair"], p["pos"]) if "idx" in p else "round %d" % p["round"]
            if complete(p):
                w("  %s %s: %s | median %6.2f | max %6.2f" % (NAME[b], tag, fmt_rates(p["rates"]),
                                                          statistics.median(p["rates"]), max(p["rates"])))
            else:
                w("  %s %s: %s | NOT COMPLETE (status %s, %d of 3 repetitions): left out below"
                  % (NAME[b], tag, fmt_rates(p["rates"]), p["status"], len(p["rates"])))
        good = [p for p in mine if complete(p)]
        if good:
            meds = [statistics.median(p["rates"]) for p in good]
            allr = [r for p in good for r in p["rates"]]
            w("  %s summary: %d processes, %d repetitions | median of process medians %6.2f | lowest %6.2f | highest (best) %6.2f"
              % (NAME[b], len(good), len(allr), statistics.median(meds), min(allr), max(allr)))
        else:
            w("  %s summary: no complete process" % NAME[b])
    w("gain new/old of each pair of neighbouring processes (percent):")
    pr = pairs_of(procs)
    gm, gx = [], []
    for key, o, n in pr:
        a = gain(statistics.median(n["rates"]), statistics.median(o["rates"]))
        b = gain(max(n["rates"]), max(o["rates"]))
        gm.append(a)
        gx.append(b)
        first = "old first" if o["n"] < n["n"] else "new first"
        w("  pair %2d (%s): old median %6.2f max %6.2f | new median %6.2f max %6.2f | gain of medians %6.2f %% | gain of maxima %6.2f %%"
          % (key, first, statistics.median(o["rates"]), max(o["rates"]), statistics.median(n["rates"]), max(n["rates"]), a, b))
    if pr:
        w("  pair summary: %d pairs | gain of medians: median %6.2f %%, lowest %6.2f %%, highest %6.2f %% | gain of maxima: median %6.2f %%, lowest %6.2f %%, highest %6.2f %%"
          % (len(pr), statistics.median(gm), min(gm), max(gm), statistics.median(gx), min(gx), max(gx)))
    else:
        w("  no complete pair")
    good = {b: [r for p in procs if p["binary"] == b and complete(p) for r in p["rates"]] for b in BINARIES}
    if good["bw_old"] and good["bw_new"]:
        w("  gain of the best repetitions (the estimator of the original table): old best %6.2f | new best %6.2f | gain %6.2f %%"
          % (max(good["bw_old"]), max(good["bw_new"]), gain(max(good["bw_new"]), max(good["bw_old"]))))
    w("class of every repetition (low: rate <= %.2f GB/s, high: rate >= %.2f GB/s, between: the rest):" % (low_max, high_min))
    for b in ("bw_new", "bw_old"):
        mine = [p for p in procs if p["binary"] == b and complete(p)]
        count = {"low": 0, "between": 0, "high": 0}
        for rep in range(3):
            c = {"low": 0, "between": 0, "high": 0}
            for p in mine:
                c[classify(p["rates"][rep], low_max, high_min)] += 1
            for k in c:
                count[k] += c[k]
            if b == "bw_new":
                w("  new repetition %d: low %d, between %d, high %d" % (rep, c["low"], c["between"], c["high"]))
        w("  %s all repetitions (%d): low %d, between %d, high %d"
          % (NAME[b], sum(count.values()), count["low"], count["between"], count["high"]))
        if b == "bw_new":
            for p in mine:
                cl = [classify(r, low_max, high_min) for r in p["rates"]]
                if len(set(cl)) > 1:
                    tag = "idx %d" % p["idx"] if "idx" in p else "round %d" % p["round"]
                    w("  new %s changes class inside the process: %s (%s)" % (tag, " ".join(cl), fmt_rates(p["rates"]).strip()))
    return {"pairs": pr, "gain_medians": gm, "gain_maxima": gx}


def cpu_key(c):
    return (0, int(c)) if c.isdigit() else (1, c)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Analyse the H2.csv files of run_h2.sh (original program at 8 MiB).")
    ap.add_argument("files", nargs="*", help="H2.csv files (default: <results>/h2-s*-*/H2.csv)")
    ap.add_argument("--results", default=RESULTS, help="results folder (default %(default)s)")
    ap.add_argument("--original", default=ORIGINAL, help="one-thread.csv of the original run (default %(default)s)")
    ap.add_argument("--low-max", type=float, default=69.5, help="a rate at or below this is 'low' (GB/s, default %(default)s)")
    ap.add_argument("--high-min", type=float, default=70.5, help="a rate at or above this is 'high' (GB/s, default %(default)s)")
    a = ap.parse_args(argv)
    if a.low_max >= a.high_min:
        print("--low-max must be below --high-min", file=sys.stderr)
        return 2
    files = a.files or sorted(glob.glob(os.path.join(a.results, "h2-s*-*", "H2.csv")))
    out = []
    w = out.append
    w("H2 analysis: the original program (bw_old = old read, bw_new = new read), read kernel, 8 MiB, 1 thread.")
    w("Rates are in GB/s (1 GB = 1e9 bytes). gain = 100 x (new / old - 1), in percent.")
    w("Levels: low = rate <= %.2f GB/s, high = rate >= %.2f GB/s, between = the rest." % (a.low_max, a.high_min))
    try:
        w("")
        w("#### original run of 2026-11-13: %s" % a.original)
        orig = [p for p in parse(a.original) if p["kernel"] == "read" and p["bytes"] == BYTES_8M]
        for cpu in sorted({p["cpu"] for p in orig}, key=cpu_key):
            report_group("original, CPU %s (one pair per round)" % cpu, [p for p in orig if p["cpu"] == cpu], a.low_max, a.high_min, out)
        good = {b: [r for p in orig if p["binary"] == b and complete(p) for r in p["rates"]] for b in BINARIES}
        if good["bw_old"] and good["bw_new"]:
            w("")
            w("original, all CPUs: old best %6.2f | new best %6.2f | gain of the best repetitions %6.2f %% | class of the new best: %s"
              % (max(good["bw_old"]), max(good["bw_new"]), gain(max(good["bw_new"]), max(good["bw_old"])),
                 classify(max(good["bw_new"]), a.low_max, a.high_min)))
        w("")
        w("#### H2 runs: %d file(s)" % len(files))
        if not files:
            w("no H2.csv found under %s (pattern h2-s*-*/H2.csv): nothing to analyse" % a.results)
        procs = []
        for fn in files:
            got = parse(fn)
            bad = [p for p in got if "session" not in p or "pair" not in p or "idx" not in p]
            if bad:
                raise ValueError("%s: %d header line(s) without session, idx or pair (not a file of run_h2.sh)" % (fn, len(bad)))
            w("%s: %d processes, %d complete" % (fn, len(got), sum(complete(p) for p in got)))
            procs += got
        seen = {}
        for p in procs:
            k = (p["session"], p["idx"])
            if k in seen and complete(p) and complete(seen[k]):
                raise ValueError("session %d idx %d is complete in two files: %s and %s" % (k[0], k[1], seen[k]["file"], p["file"]))
            if k not in seen or complete(p):
                seen[k] = p
        procs = sorted(seen.values(), key=lambda p: (p["session"], p["idx"]))
        for i, p in enumerate(procs):
            p["n"] = i
        summary = []
        for s in sorted({p["session"] for p in procs}):
            for cpu in dict.fromkeys(p["cpu"] for p in procs if p["session"] == s):
                grp = [p for p in procs if p["session"] == s and p["cpu"] == cpu]
                r = report_group("session %d, CPU %s" % (s, cpu), grp, a.low_max, a.high_min, out)
                new = [x for p in grp if p["binary"] == "bw_new" and complete(p) for x in p["rates"]]
                c = [classify(x, a.low_max, a.high_min) for x in new]
                summary.append("  session %d CPU %3s: %2d pairs | gain of medians: median %s | new repetitions: low %d, between %d, high %d"
                               % (s, cpu, len(r["pairs"]),
                                  "%6.2f %%" % statistics.median(r["gain_medians"]) if r["pairs"] else "(none)",
                                  c.count("low"), c.count("between"), c.count("high")))
        if summary:
            w("")
            w("#### summary of the H2 runs")
            out += summary
    except (OSError, ValueError) as e:
        print("\n".join(out))
        print("error: %s" % e, file=sys.stderr)
        return 2
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
