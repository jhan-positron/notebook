#!/usr/bin/env python3
"""d3c.py - are there records of the saved journal inside the processes of the runner bwx rows (B7a, B7b, C3a, C3b, tags
common-6000-*)? Counts the records between the launch time of each such step and the end of its last T row. Reads only."""
import datetime as dt, os, re, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, ivs
recs = []
first = last = None
for i, l in enumerate(open(R + "/dimm-check-20261117/h-5.txt", errors="replace"), 1):
    m0 = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)", l)
    if m0:
        first = first or m0[1]; last = m0[1]
    m = re.match(r"(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: Hardware error from APEI", l)
    if m:
        recs.append((dt.datetime.strptime(m[1], "%Y-%m-%dT%H:%M:%S"), i))
print("journal: first line time", first, "last line time", last, "records", len(recs))
tot_p = tot_r = hit_iv = 0
for folder, csv in (("B7-20261113T232859Z", "B7.csv"), ("B7-20261114T024352Z", "B7.csv"), ("C3-20261114T022708Z", "C3.csv"), ("C3-20261114T054116Z", "C3.csv")):
    path = R + "/" + folder + "/" + csv
    day = dt.datetime.strptime(re.search(r"(\d{8})T(\d{6})", folder)[0], "%Y%m%dT%H%M%S")
    steps = [(i, l) for i, l in enumerate(open(path), 1) if l.startswith("-- step")]
    nl = sum(1 for _ in open(path))
    n_p = n_r = 0
    for j, (i, l) in enumerate(steps):
        tag = l.split(" tag ")[1].split()[0]
        if not tag.startswith("common-6000-"):
            continue
        hms = re.search(r" utc (\d\d:\d\d:\d\d) ", l)[1]
        A = dt.datetime.combine(day.date(), dt.datetime.strptime(hms, "%H:%M:%S").time())
        if A < day - dt.timedelta(seconds=1): A += dt.timedelta(days=1)
        end = steps[j + 1][0] - 1 if j + 1 < len(steps) else nl
        iv = ivs(path, start=i, end=end)
        B = A + dt.timedelta(seconds=max(x["te"] for x in iv) + 1)
        offs = [(t - A).total_seconds() for t, _ in recs if A <= t <= B]
        n_p += 1; n_r += len(offs)
        for x in iv:
            if any(x["ts"] <= o - 1 and o + 1 <= x["te"] for o in offs): hit_iv += 1
    print(folder, "processes", n_p, "records between launch and last T row end (+1 s)", n_r)
    tot_p += n_p; tot_r += n_r
print("total: processes", tot_p, "records", tot_r, "| intervals (all kernels) with a record wholly inside:", hit_iv)
