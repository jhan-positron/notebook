#!/usr/bin/env python3
"""check_accept8.py - Stage 1 items 1 and 4 on the output of a --trace run of bwx8 on CRB.
Usage: check_accept8.py <csv> <plan> [<csv> <plan> ...]
Applies the trace, window and bin rules of test_runner8.py to every trial, and prints the rates and gaps.
Exit status 0 only if no rule reports a problem."""
import re, sys
import test_runner8 as T

bad = 0
for csv, plan in zip(sys.argv[1::2], sys.argv[2::2]):
    out = open(csv).read()
    rows, lines = T.rows_of(out), T.plan_lines(plan)
    m = {f[1]: f[2] for f in rows.get("M", [])}
    print("== %s cpu %s ctl %s madvise_ok %s kernels %s" % (csv.split("/")[-1], m.get("cpu"), m.get("ctl_cpu"), m.get("madvise_ok"), m.get("kernels")))
    faults = dict(re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M))
    for i, f in enumerate(lines):
        ev, numbered = T.events_of(rows, i)
        w, e = T.of_trial(rows, "W", i), T.of_trial(rows, "E", i)[0]
        p = T.trace_problems(f, ev, w, e) + T.window_problems(f, w)
        if int(f[10]):
            p += T.bin_problems(f, w, T.of_trial(rows, "B", i), {t for n, t in ev if n == "clock"})
        if not numbered: p.append("TR rows not numbered")
        if faults.get(str(i)) != "0": p.append("minflt %s" % faults.get(str(i)))
        pre, post = [x for x in T.of_trial(rows, "P", i)]
        if pre[3:5] != ["8192", "8192"] or post[3:5] != ["8192", "8192"]: p.append("huge-page coverage %s %s" % (pre[3:5], post[3:5]))
        x = T.of_trial(rows, "X", i)
        tg = [r for r in w if r[2] == "target"]
        rates = ["%.2f" % (int(r[6]) / (int(r[8]) - int(r[7]))) for r in tg]
        print("trial %d %-28s count %-6s target GB/s %s | wall %s cpu %s nvcsw %s nivcsw %s gap_ns %s max_gap %s sink %s state %s%s%s"
              % (i, f[1], f[9], " ".join(rates), e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9], " X=%s" % x if x else "", " PROBLEM %s" % p if p else ""))
        bad += len(p)
print("# problems: %d" % bad)
sys.exit(1 if bad else 0)
