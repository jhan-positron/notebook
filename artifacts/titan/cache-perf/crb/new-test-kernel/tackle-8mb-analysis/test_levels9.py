#!/usr/bin/env python3
"""test_levels9.py - checks of levels9.py on synthetic data.

Usage: test_levels9.py
Prints one line per check. Exit status 0 only if every check passed.
Every synthetic trace has known switch times, counts or values, so a wrong rule in levels9.py fails a check.
The last block reads two session 1 result folders if they exist (it prints NOTE and no check if they do not).
"""
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, A)
import levels9 as L  # noqa: E402

FAILS = []
NCHECK = [0]
MIB8 = 8 << 20


def check(name, ok, detail=""):
    NCHECK[0] += 1
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail) + "]") if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


# ---------------------------------------------------------------- synthetic traces
def level_at(t, start_level, switches):
    """switches: sorted times; the level flips at each one. Returns 'low' or 'high'."""
    n = sum(1 for s in switches if s <= t)
    flip = {"low": "high", "high": "low"}
    return start_level if n % 2 == 0 else flip[start_level]


def synth_windows(n, switches, start_level="low", low=67.5, high=71.1, win=0.3, gap=1e-7, noise=0.0, seed=1,
                  t0=0.0007, drift=0.0):
    """n windows of `win` s. The rate of a window is the time mean of an abrupt two-level signal.
    drift: the low level starts `drift` GB/s higher after each down switch and decays to `low` in 1 s."""
    rng = random.Random(seed)
    out = []
    t = t0
    for _ in range(n):
        a, b = t, t + win
        cuts = [a] + [s for s in switches if a < s < b] + [b]
        tot = 0.0
        for c0, c1 in zip(cuts, cuts[1:]):
            lev = level_at(0.5 * (c0 + c1), start_level, switches)
            r = high if lev == "high" else low
            if lev == "low" and drift:
                last = max([s for s in switches if s <= c0] or [-9.0])
                r += drift * max(0.0, 1.0 - (c0 - last))
            tot += r * (c1 - c0)
        out.append((a, b, tot / (b - a) + rng.uniform(-noise, noise)))
        t = b + gap
    return out


def kinds(switches, start_level):
    """Expected (ups, downs) of a switch list."""
    u, d = [], []
    lev = start_level
    for s in switches:
        if lev == "low":
            u.append(s)
            lev = "high"
        else:
            d.append(s)
            lev = "low"
    return u, d


def matches(found, expected, tol):
    return len(found) == len(expected) and all(abs(a - b) <= tol for a, b in zip(sorted(found), sorted(expected)))


def test_segmentation():
    sw = [6.42, 8.31, 13.32, 15.47, 20.22, 20.86, 27.13, 28.64]
    wins = synth_windows(100, sw, "low", noise=0.03)
    seg = L.segment(wins)
    eu, ed = kinds(sw, "low")
    check("seg: two levels found", seg["high"] is not None and close(seg["low"], 67.5, 0.1)
          and close(seg["high"], 71.1, 0.1), (seg["low"], seg["high"]))
    check("seg: up times within 0.05 s", matches(L.ups(seg), eu, 0.05), (L.ups(seg), eu))
    check("seg: down times within 0.05 s", matches(L.downs(seg), ed, 0.05), (L.downs(seg), ed))
    worst = max(abs(a - b) for a, b in zip(sorted(L.ups(seg) + L.downs(seg)), sorted(sw)))
    check("seg: worst switch error below 0.02 s with 0.03 GB/s noise", worst < 0.02, worst)
    check("seg: every switch is marked 'mixed' or 'boundary'", all(s["how"] in ("mixed", "boundary")
                                                                  for s in seg["switches"]))
    # share of time high
    span = wins[-1][1] - wins[0][0]
    true_high = sum(b - a for a, b in zip(eu, ed)) / span
    check("seg: share high equals the planted share", close(seg["share_high"], true_high, 0.01),
          (seg["share_high"], true_high))
    # labels: a window that holds a switch far from its edges is mixed
    lab = seg["labels"]
    idx = int((6.42 - 0.0007) / 0.3000001)
    check("seg: the window that holds a switch is labelled mixed", lab[idx] == "mixed", lab[idx])
    check("seg: windows far from switches carry their level", lab[2] == "low" and lab[24] == "high",
          (lab[2], lab[24]))
    # starts high, other levels, drift of the low level after a down switch
    sw2 = [1.76, 6.43, 8.99, 13.33]
    wins2 = synth_windows(60, sw2, "high", low=69.0, high=71.6, noise=0.03, seed=5, drift=0.5)
    seg2 = L.segment(wins2)
    eu2, ed2 = kinds(sw2, "high")
    check("seg: start at high, up times within 0.05 s", matches(L.ups(seg2), eu2, 0.05), (L.ups(seg2), eu2))
    check("seg: start at high with a decaying low level, down times within 0.1 s",
          matches(L.downs(seg2), ed2, 0.1), (L.downs(seg2), ed2))
    # a switch exactly on a window boundary
    b = wins[10][1]
    wins3 = synth_windows(40, [b + 5e-8], "low")
    seg3 = L.segment(wins3)
    check("seg: switch on a window boundary is found there and marked 'boundary'",
          len(seg3["switches"]) == 1 and seg3["switches"][0]["how"] == "boundary"
          and close(seg3["switches"][0]["t"], b, 0.001), seg3["switches"])
    # a wrong estimator would fail: reversed fraction moves the time by more than 0.05 s
    w = wins[idx]
    wrong = w[0] + (w[1] - 6.42)          # the fraction at the new level in place of the old level
    check("seg: the check can fail (an estimate with the reversed fraction is more than 0.05 s away)",
          abs(wrong - 6.42) > 0.05, wrong)
    # not contiguous: a 1.2 s hole with a level change across it
    lowpart = synth_windows(10, [], "low")
    highpart = [(a + 4.2, b + 4.2, r) for a, b, r in synth_windows(10, [], "high")]
    seg4 = L.segment(lowpart + highpart)
    s4 = seg4["switches"]
    check("seg: a level change across a hole is marked 'gap' with the hole as bounds",
          len(s4) == 1 and s4[0]["how"] == "gap" and close(s4[0]["t_lo"], lowpart[-1][1], 1e-9)
          and close(s4[0]["t_hi"], highpart[0][0], 1e-9), s4)
    # excursion: a visit to low that is shorter than a window
    wins5 = synth_windows(40, [5.05, 5.20], "high")
    seg5 = L.segment(synth_windows(40, [1.0, 3.0], "high")[:20] + wins5[20:])
    seg5b = L.segment(wins5 + [(a + 12.01, b + 12.01, r) for a, b, r in synth_windows(10, [], "low")])
    check("seg: a 0.15 s visit to the other level is an excursion, not a switch pair",
          len([e for e in seg5b["excursions"] if e["level"] == "high"]) == 1
          and close([e for e in seg5b["excursions"] if e["level"] == "high"][0]["other_s"], 0.15, 0.01)
          and len(L.downs(seg5b)) == 1, (seg5b["excursions"], seg5b["switches"]))
    check("seg: joined trace keeps its two early switches", len(seg5["switches"]) >= 2, seg5["switches"])


def test_one_level():
    wins = synth_windows(200, [], "low", low=67.05, noise=0.05)
    seg = L.segment(wins)
    check("one level: high is None", seg["high"] is None and close(seg["low"], 67.05, 0.03), (seg["low"], seg["high"]))
    check("one level: no switches", seg["switches"] == [])
    check("one level: every label is 'one'", set(seg["labels"]) == {"one"}, set(seg["labels"]))
    # two plateaus closer than MIN_GAP are one level
    seg2 = L.segment(synth_windows(60, [9.0], "low", low=67.0, high=67.8))
    check("one level: plateaus 0.8 GB/s apart give no switch", seg2["high"] is None and seg2["switches"] == [])
    # the same shape 1.2 GB/s apart is two levels (so the rule above is the gap rule, not blindness)
    seg3 = L.segment(synth_windows(60, [9.0], "low", low=67.0, high=68.2))
    check("one level: plateaus 1.2 GB/s apart give one up switch", len(L.ups(seg3)) == 1
          and close(L.ups(seg3)[0], 9.0, 0.05), seg3["switches"])
    # one level with a single dip of two windows: no level from 2 windows
    wins4 = synth_windows(60, [], "high")
    wins4[30] = (wins4[30][0], wins4[30][1], 69.1)
    wins4[31] = (wins4[31][0], wins4[31][1], 69.8)
    seg4 = L.segment(wins4)
    check("one level: a dip of two windows makes no second level and no switch",
          seg4["high"] is None and seg4["switches"] == [] and len(seg4["excursions"]) == 1
          and seg4["labels"][30] == "mixed", (seg4["low"], seg4["high"], seg4["excursions"]))
    check("one level: fewer than 6 windows give one level", L.segment(synth_windows(5, [0.7], "low"))["high"] is None)
    check("empty input", L.segment([])["low"] is None and L.segment([])["switches"] == [])


def test_fits():
    t = [6.42 + 6.9 * k for k in (0, 1, 2, 3, 5, 6, 8)]
    f = L.fit_period(t)
    check("fit: period of a series with missing cycles", f is not None and close(f["period"], 6.9, 0.001)
          and close(f["phase"], 6.42, 0.01) and f["rms"] < 1e-6, f)
    check("fit: indices show the missing cycles", f is not None and [i - f["indices"][0] for i in f["indices"]]
          == [0, 1, 2, 3, 5, 6, 8], f)
    rng = random.Random(3)
    tj = [x + rng.uniform(-0.03, 0.03) for x in t]
    fj = L.fit_period(tj)
    check("fit: 0.03 s jitter keeps the period within 0.02 s", close(fj["period"], 6.9, 0.02) and fj["rms"] < 0.04, fj)
    tr = sorted(rng.uniform(0, 60) for _ in range(9))
    fr = L.fit_period(tr)
    check("fit: random times give a large rms (more than 0.3 s)", fr is None or fr["rms"] > 0.3, fr)
    check("fit: fewer than 3 times give no fit", L.fit_period([1.0, 7.9]) is None)
    per = [[6.4 + 6.9 * k + rng.uniform(-0.02, 0.02) for k in range(7) if rng.random() > 0.2] for _ in range(8)]
    fp = L.fit_pooled(per)
    check("fit: pooled period and phase", fp is not None and close(fp["period"], 6.9, 0.01)
          and close(fp["phase"], 6.4, 0.05) and fp["rms"] < 0.03, fp)
    check("fit: pooled fit refuses one recurring time", L.fit_pooled([[4.0], [4.02], [3.98], [4.01]]) is None)
    r, ph, sd = L.circ([1.0, 8.0, 15.0], 7.0)
    check("circ: one phase gives R = 1", close(r, 1.0, 1e-9) and close(ph, 1.0, 1e-6))
    r2 = L.circ([0.0, 1.75, 3.5, 5.25], 7.0)[0]
    check("circ: four even phases give R = 0", close(r2, 0.0, 1e-9), r2)
    cl = L.clusters([[6.40, 13.30], [6.43, 13.33, 20.2], [6.41]], width=0.15)
    check("clusters: recurring times are grouped", [(c["n"], c["nproc"]) for c in cl] == [(3, 3), (2, 2), (1, 1)]
          and close(cl[0]["mean"], 6.4133, 0.001), cl)
    h = L.histogram([3.90, 3.95, 4.01, 4.09, 4.10])
    check("histogram: 0.1 s bins", h == {39: 2, 40: 2, 41: 1}, h)


def test_wallclock():
    rng = random.Random(11)
    launches = [100 + 61 * i + rng.randint(0, 3) for i in range(12)]
    # (1) events tied to the process start
    per1 = [(l, [6.42 + 6.9 * k + rng.uniform(-0.02, 0.02) for k in range(7)]) for l in launches]
    w1 = L.wallclock_test(per1, 6.9, draws=40)
    check("wall clock: process-tied events have R near 1 since process start", w1["r_rel"] > 0.95, w1["r_rel"])
    check("wall clock: process-tied events do not exceed the random-offset null on the wall clock",
          w1["r_wall"] <= w1["null_max"], (w1["r_wall"], w1["null_max"]))
    # (2) events tied to the wall clock: a host event every 6.9 s of the day
    per2 = []
    for l in launches:
        first = (-l) % 6.9
        per2.append((l, [first + 6.9 * k + rng.uniform(-0.02, 0.02) for k in range(8)]))
    w2 = L.wallclock_test(per2, 6.9, draws=40)
    check("wall clock: wall-tied events have R near 1 on the wall clock", w2["r_wall"] > 0.95, w2["r_wall"])
    check("wall clock: wall-tied events exceed the random-offset null", w2["r_wall"] > w2["null_max"],
          (w2["r_wall"], w2["null_max"]))
    check("wall clock: wall-tied events have a lower R since process start", w2["r_rel"] < 0.8, w2["r_rel"])
    # (3) a launch cadence that is a multiple of the period: the period is reported as aliased
    per3 = [(100 + 69 * i, [6.42 + 6.9 * k for k in range(7)]) for i in range(12)]
    w3 = L.wallclock_test(per3, 6.9, draws=5)
    check("wall clock: launches every 10 periods are reported as aliased", w3["aliased"] > 0
          and w3["r_launch_at_rel"] > 0.5, (w3["aliased"], w3["r_launch_at_rel"]))
    check("wall clock: one process gives no test", L.wallclock_test([(5, [1.0, 2.0])], 6.9) is None)


# ---------------------------------------------------------------- synthetic csv files
def ns(t):
    return int(round(t * 1e9))


class Csv:
    def __init__(self):
        self.lines = []

    def proc(self, idx, tag, cpu, step="S4", session=1, utc="01:02:16", nbytes=MIB8, events=None, header=True,
             plan=None):
        if header:
            self.lines.append("-- step %s session %d idx %d tag %s waited_s 0 loadavg 0.10 0.20 0.30 1/1000 logins 0 "
                              "utc %s args --trial --cpus %d --bytes %d --plan sched/x.plan" % (
                                  step, session, idx, tag, utc, cpu, nbytes))
        self.lines.append("# bwx8 trial mode: GB = 1e9 bytes; times are whole ns since process start on CLOCK_MONOTONIC")
        self.lines.append("# W,trial,phase,widx,kernel,pass_bytes,bytes,t_start_ns,t_end_ns")
        for k, v in (("mode", "trial"), ("cpu", cpu), ("bytes", nbytes), ("pmu_type", 11 if events else "none"),
                     ("events", ";".join(events) if events else "none"), ("plan.step", step),
                     ("plan.session", session), ("plan.cpu", cpu), ("plan.proc", idx)):
            self.lines.append("M,%s,%s" % (k, v))
        for k, v in (plan or {}).items():
            self.lines.append("M,plan.%s,%s" % (k, v))

    def trial(self, trial, cond, kernel, size, wins, phase="target", counts=None, widx0=0, s_row=True,
              mux=None, count="closed"):
        """wins: list of (t_start_s, t_end_s, rate). counts: per window list of event counts (or None)."""
        if s_row:
            self.lines.append("S,%d,%s,1,-,-,-,%s@%s,%d,300,%s,0,none,none" % (
                trial, cond, kernel, L.size_name(size), len(wins), count))
            self.lines.append("P,%d,pre,8192,8192,1,0,2,0" % trial)
        rows = []
        for i, (a, b, r) in enumerate(wins):
            ta, tb = ns(a), ns(b)
            nb = int(round(r * (tb - ta)))
            self.lines.append("W,%d,%s,%d,%s,%d,%d,%d,%d" % (trial, phase, widx0 + i, kernel, size, nb, ta, tb))
            rows.append(nb)
            if counts is not None and counts[i] is not None:
                en = tb - ta
                run = en - 1000 if (mux and i in mux) else en
                self.lines.append("C,%d,%d,%d,%d,%d,%s" % (trial, widx0 + i, en, run, en - 50,
                                                           ",".join(str(c) for c in counts[i])))
        return rows

    def end(self, trial):
        self.lines.append("P,%d,post,8192,8192,1,0,2,0" % trial)
        self.lines.append("E,%d,2400262365,2399285756,0,2,48,56,NA,closed" % trial)

    def write(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines) + "\n")


def test_parser(tmp):
    c = Csv()
    c.proc(7, "read-cpu2-p1", 2, step="XW", session=2, utc="03:04:05", events=["cpu_cycles=0x11", "inst_retired=0x8"],
           plan={"kernel": "read", "size": MIB8})
    prev = [(0.001, 3.001, 67.0)]
    c.trial(0, "K=read|S=8M|prev=oldread@8M", "oldread", MIB8, prev, phase="prev")
    wins = synth_windows(20, [3.0 + 2.42], "low", t0=3.0011)
    c.trial(0, "x", "read", MIB8, wins, counts=[[1000 + i, 2000 + i] for i in range(20)], s_row=False)
    c.end(0)
    c.lines.append("X,0,count_read,some text")
    c.lines.append("-- killed tag read-cpu2-p1 status 130 utc 03:05:00")
    c.proc(8, "bare", 41, header=False)
    c.trial(0, "K=read|S=1M", "read", 1 << 20, synth_windows(10, [], "low", low=85.0))
    c.end(0)
    path = os.path.join(tmp, "parse.csv")
    c.write(path)
    ps = L.parse_csv(path)
    check("parser: two processes (one with a launch line, one bare)", len(ps) == 2, len(ps))
    p = ps[0]
    check("parser: launch line fields", (p.step, p.session, p.idx, p.tag, p.utc, p.launch_s) ==
          ("XW", "2", 7, "read-cpu2-p1", "03:04:05", 3 * 3600 + 4 * 60 + 5), (p.step, p.session, p.idx, p.utc))
    check("parser: args of the launch line", p.hdr.get("args", "").startswith("--trial --cpus 2"), p.hdr.get("args"))
    check("parser: M rows and cpu", p.M["plan.kernel"] == "read" and p.cpu == "2" and p.M["mode"] == "trial")
    check("parser: event names from M,events", p.events == ["cpu_cycles", "inst_retired"], p.events)
    check("parser: windows with phase, widx, kernel, bytes, times", len(p.W) == 21 and p.W[0].phase == "prev"
          and p.W[0].kernel == "oldread" and p.W[1].phase == "target" and p.W[1].widx == 0
          and p.W[1].t_start == ns(wins[0][0]) and p.W[1].t_end == ns(wins[0][1])
          and close(p.W[1].rate, 67.5, 1e-6), (len(p.W), p.W[1].rate))
    check("parser: C rows per target window", len(p.C) == 20 and p.C[(0, 3)]["counts"] == [1003, 2003]
          and p.C[(0, 3)]["enabled_ns"] == p.C[(0, 3)]["running_ns"], p.C.get((0, 3)))
    check("parser: E, P, S, X rows", 0 in p.E and len(p.P) == 2 and p.S[0][0] == "K=read|S=8M|prev=oldread@8M"
          and p.X and p.X[0][1] == "count_read", (p.E, p.P, p.X))
    check("parser: a killed line is kept", p.ended is not None and "killed" in p.ended)
    check("parser: main kernel and size are those of the target windows", (p.kernel, p.size) == ("read", MIB8)
          and (ps[1].kernel, ps[1].size) == ("read", 1 << 20), (p.kernel, p.size))
    ws, seg = L.segment_proc(p)
    check("parser: the previous-activity window of another kernel is not part of the level sequence",
          len(ws) == 20 and seg is not None and matches(L.ups(seg), [5.42], 0.05), (len(ws), seg and seg["switches"]))
    check("parser: a folder stands for its csv files", L.csv_paths([tmp]) == [path], L.csv_paths([tmp]))
    return path


def test_counters(tmp):
    ev = ["cpu_cycles=0x11", "inst_retired=0x8", "l2d_cache_refill=0x17"]
    c = Csv()
    sw = [3.15, 9.15]                       # up at 3.15, down at 9.15: windows 10 and 30 are mixed
    planted = {}
    for idx, (cpu, lowc, highc) in enumerate(((2, 300, 100), (2, 340, 120))):
        wins = synth_windows(40, sw, "low")
        counts, mux = [], set([2, 20])       # one multiplexed window at each level
        lab = []
        for i, (a, b, r) in enumerate(wins):
            nb = int(round(r * (ns(b) - ns(a))))
            lev = "low" if r < 68 else ("high" if r > 70.6 else "mixed")
            lab.append(lev)
            per64 = {"low": lowc, "high": highc, "mixed": 5000}[lev]
            l2 = per64 * nb // 64
            if i in mux:
                l2 = 10 ** 15            # must not reach any median
            counts.append([nb // 16 if lev != "high" else nb // 20, nb // 8, l2])
        c.proc(idx, "read-cpu%d-p%d" % (cpu, idx), cpu, step="XCA", events=ev)
        c.trial(0, "K=read|S=8M", "read", MIB8, wins, counts=counts, mux=mux, count="read")
        c.end(0)
        planted[idx] = (lowc, highc, lab)
    # one-level process of another kernel
    wins = synth_windows(20, [], "low", low=67.05)
    c.proc(2, "oldread-cpu2-p1", 2, step="XCA", events=ev)
    c.trial(0, "K=oldread|S=8M", "oldread", MIB8, wins,
            counts=[[int(round(r * (ns(b) - ns(a)))) // 16, 0, 77 * int(round(r * (ns(b) - ns(a)))) // 64]
                    for a, b, r in wins], count="read")
    c.end(0)
    path = os.path.join(tmp, "cnt.csv")
    c.write(path)
    procs = L.parse_csv(path)
    cells = L.counter_table(procs)
    key = ("XCA", "cpu_cycles,inst_retired,l2d_cache_refill", "read", MIB8, "2", "1")
    check("counters: cell keys", sorted(k[2] for k in cells) == ["oldread", "read"] and key in cells, sorted(cells))
    cell = cells[key]
    nmixed = sum(1 for l in planted[0][2] if l == "mixed")
    check("counters: the synthetic trace has mixed windows", nmixed == 2, nmixed)
    check("counters: multiplexed windows are counted and left out", cell["mux"] == 4 and cell["windows"] == 80,
          (cell["mux"], cell["windows"]))
    q0, q1 = cell["procs"]
    check("counters: per process, low level per 64 B is exact", close(q0["levels"]["low"]["per64"]["l2d_cache_refill"],
                                                                  300, 0.001)
          and close(q1["levels"]["low"]["per64"]["l2d_cache_refill"], 340, 0.001), q0["levels"]["low"]["per64"])
    check("counters: per process, high level per 64 B is exact",
          close(q0["levels"]["high"]["per64"]["l2d_cache_refill"], 100, 0.001)
          and close(q1["levels"]["high"]["per64"]["l2d_cache_refill"], 120, 0.001), q0["levels"]["high"]["per64"])
    nlow = sum(1 for l in planted[0][2] if l == "low") - 1
    nhigh = sum(1 for l in planted[0][2] if l == "high") - 1
    check("counters: window counts per level leave out mixed and multiplexed windows",
          q0["levels"]["low"]["n"] == nlow and q0["levels"]["high"]["n"] == nhigh and q0["mixed"] == 2,
          (q0["levels"]["low"]["n"], nlow, q0["levels"]["high"]["n"], nhigh, q0["mixed"]))
    check("counters: per pass = per 64 B x size / 64", close(q0["levels"]["low"]["per_pass"]["l2d_cache_refill"],
                                                             300 * MIB8 / 64.0, 1.0),
          q0["levels"]["low"]["per_pass"]["l2d_cache_refill"])
    check("counters: cycles per byte and instructions per byte",
          close(q0["levels"]["low"]["cyc_per_byte"], 1 / 16.0, 1e-6)
          and close(q0["levels"]["high"]["cyc_per_byte"], 1 / 20.0, 1e-6)
          and close(q0["levels"]["low"]["ins_per_byte"], 1 / 8.0, 1e-6), q0["levels"]["low"])
    d = [x for _, x in cell["diff"]["l2d_cache_refill"]]
    check("counters: low minus high per process", len(d) == 2 and close(d[0], 200, 0.001) and close(d[1], 220, 0.001), d)
    dc = [x for _, x in cell["diff_extra"]["cyc_per_byte"]]
    check("counters: low minus high of cycles per byte", close(dc[0], 1 / 16.0 - 1 / 20.0, 1e-6), dc)
    check("counters: pooled median over the windows of both processes",
          cell["pooled"]["low"]["per64"]["l2d_cache_refill"] in (300.0, 320.0, 340.0)
          and cell["pooled"]["low"]["n"] == 2 * nlow, cell["pooled"]["low"])
    old = cells[("XCA", "cpu_cycles,inst_retired,l2d_cache_refill", "oldread", MIB8, "2", "1")]
    check("counters: a one-level process has level 'one' and no difference",
          list(old["procs"][0]["levels"]) == ["one"] and close(old["pooled"]["one"]["per64"]["l2d_cache_refill"], 77, 0.001)
          and old["diff"]["l2d_cache_refill"] == [], old["pooled"])
    # NA counts
    c2 = Csv()
    c2.proc(0, "na", 2, step="XCB", events=["a=0x1", "b=0x2"])
    w2 = synth_windows(12, [], "low")
    c2.trial(0, "K=read|S=8M", "read", MIB8, w2, counts=[["NA", 640] for _ in w2], count="read")
    p2 = os.path.join(tmp, "na.csv")
    c2.write(p2)
    cl2 = L.counter_table(L.parse_csv(p2))
    st = list(cl2.values())[0]["pooled"]["one"]
    check("counters: an event that did not open (NA) has no value, the other event keeps its value",
          st["per64"]["a"] is None and st["per64"]["b"] is not None and st["cyc_per_byte"] is None, st)
    return path


def test_watch(tmp):
    """Sampler files in the format of hostwatch v1: a line only when something changed, ABS lines, key:=state."""
    folder = os.path.join(tmp, "bwx9-XW-s1-TEST")
    os.makedirs(folder)
    rng = random.Random(21)
    c = Csv()
    clk = 100
    hz = 20
    slot_ns = 10 ** 9 // hz
    boot_minus_mono = 5000 * 10 ** 9 + 123456789          # boot clock = mono clock + this
    for idx in range(4):
        up_t = [6.42 + 6.9 * k for k in range(4)]
        dn_t = [u + 1.5 + 0.2 * idx for u in up_t]
        sw = sorted(up_t + dn_t)
        wins = synth_windows(100, sw, "low", noise=0.02, seed=idx)
        c.proc(idx, "read-cpu2-p%d" % idx, 2, step="XW", utc="01:%02d:00" % idx)
        c.trial(0, "K=read|S=8M|prev=none", "read", MIB8, wins)
        c.end(0)
        # The process starts at mono time start_mono (on a tick of the boot clock).
        start_ticks = 400000 + 777 * idx
        start_mono = start_ticks * 10 ** 9 // clk - boot_minus_mono
        mono_hdr = start_mono + 150000000                # the sampler starts 0.15 s after the process
        lines = ["# hostwatch v1 pid=1 cpu=2 hz=%d max_s=120" % hz,
                 "# clocks mono_ns=%d boot_ns=%d real_ns=1" % (mono_hdr, mono_hdr + boot_minus_mono),
                 "# target starttime_ticks=%d clk_tck=%d comm=bwx8 unknown_header_key=7" % (start_ticks, clk)]
        t = mono_hdr + 30000000
        prev_t = None
        nslot = 0
        last_irq = None
        while t < start_mono + 31 * 10 ** 9:
            toks = []
            if prev_t is not None:
                a, b = (prev_t - start_mono) / 1e9, (t - start_mono) / 1e9
                hit_up = any(a < s <= b for s in up_t)
                hit_dn = any(a < s <= b for s in dn_t)
                if hit_up or hit_dn:
                    toks.append("planted_any=1")
                if hit_up:
                    toks.append("planted_up=3")
                    toks.append("th.%d.kworker/2:1.run_ns=5000" % (900 + idx))    # the tid differs per process
                if rng.random() < 0.05:
                    toks.append("decoy=1")
                if nslot % 100 == 50:
                    toks.append("state_key:=%d" % nslot)
                if nslot % 40 == 7:
                    toks.append("zero_key=0")
                if nslot % 10 == 0:                      # irq keys are read every 0.5 s
                    ai = (last_irq - start_mono) / 1e9 if last_irq else a
                    if any(ai < s <= b for s in dn_t):
                        toks.append("irq.planted_down=2")
                    last_irq = t
            if toks:
                lines.append("%d %s" % (t, " ".join(toks)))
            if nslot % 100 == 0:
                lines.append("%d ABS planted_any=555 abs_only=12345 decoy=99" % t)
            prev_t = t
            nslot += 1
            t += slot_ns + rng.randint(-1000000, 1000000)
        lines.append("# end reason=pid_gone samples=%d missed=0 max_sample_us=900" % nslot)
        with open(os.path.join(folder, "watch-%d.txt" % idx), "w") as f:
            f.write("\n".join(lines) + "\n")
    c.write(os.path.join(folder, "XW.csv"))
    wf = L.watch_files(folder)
    check("watch: files are matched to idx by number", sorted(wf) == [0, 1, 2, 3], sorted(wf))
    w0 = L.Watch(wf[1])
    s0, tick = w0.start_mono_ns()
    exp = (400000 + 777) * 10 ** 9 // clk - boot_minus_mono
    check("watch: process start on the monotonic clock from ticks and the mono/boot pair",
          close(s0, exp, 1.0) and close(tick, 1e7, 1e-6), (s0, exp, tick))
    check("watch: unknown header keys are kept and tolerated", w0.head.get("unknown_header_key") == "7")
    check("watch: slot length from hz, slot count from the end line", w0.slot_s() == (0.05, True)
          and w0.nslots() == int(w0.head["samples"]) and w0.nslots() > 500, (w0.slot_s(), w0.nslots()))
    sp = w0.span()
    check("watch: the sampled span is in s since process start", close(sp[0], 0.18, 1e-6) and 30.9 < sp[1] < 31.1, sp)
    ev = w0.events()
    check("watch: ABS lines give no change event", w0.abs_lines >= 6 and not any(k == "abs_only" for _, _, k, _ in ev),
          w0.abs_lines)
    check("watch: a delta of 0 is no change; key:=value is a change without a number",
          not any(k == "zero_key" for _, _, k, _ in ev)
          and [d for _, _, k, d in ev if k == "state_key"] and all(d is None for _, _, k, d in ev if k == "state_key"))
    check("watch: change interval is one slot; 0.5 s for irq keys",
          all(close(b - a, 0.05, 1e-9) for a, b, k, _ in ev if k == "planted_any")
          and all(close(b - a, 0.5, 1e-9) for a, b, k, _ in ev if k.startswith("irq.")))
    procs = L.load([folder])
    stats = [L.watch_proc(p, wf[p.idx])[1] for p in procs]
    pw = L.pool_watch(stats)
    nu, nd = pw["n"]["up"], pw["n"]["down"]
    check("watch: all planted switches are found and fully sampled", nu == 16 and nd == 16, (nu, nd))
    t = pw["tab"]

    def sh(k, kind):
        return t[k][kind] / float(pw["n"][kind])

    def base(k):
        return t[k]["grid"] / float(pw["grid_n"])

    check("watch: the planted key changes near every up switch and every down switch",
          sh("planted_any", "up") >= 0.95 and sh("planted_any", "down") >= 0.95,
          (sh("planted_any", "up"), sh("planted_any", "down")))
    check("watch: the base rate of the planted key is far below its switch share", base("planted_any") < 0.2,
          base("planted_any"))
    check("watch: a key planted at up switches only: share near 1 at up, near its base rate at down",
          sh("planted_up", "up") >= 0.95 and sh("planted_up", "down") <= base("planted_up") + 0.2,
          (sh("planted_up", "up"), sh("planted_up", "down"), base("planted_up")))
    check("watch: the decoy key is near its base rate at up and down switches",
          abs(sh("decoy", "up") - base("decoy")) <= 0.25 and abs(sh("decoy", "down") - base("decoy")) <= 0.25
          and 0.1 < base("decoy") < 0.6, (sh("decoy", "up"), sh("decoy", "down"), base("decoy")))
    check("watch: per-slot base rate of the decoy is near the planted 5 %",
          abs(t["decoy"]["slot"] / float(pw["slots"]) - 0.05) < 0.02, t["decoy"]["slot"] / float(pw["slots"]))
    check("watch: thread keys of different tids are pooled as th.*",
          "th.*.kworker/2:1.run_ns" in t and sh("th.*.kworker/2:1.run_ns", "up") >= 0.95
          and not any(k.startswith("th.9") for k in t), [k for k in t if k.startswith("th.")])
    check("watch: an irq key planted at down switches is found through its 0.5 s change interval",
          sh("irq.planted_down", "down") >= 0.95 and sh("irq.planted_down", "up") < 0.5,
          (sh("irq.planted_down", "down"), sh("irq.planted_down", "up")))
    check("watch: rate near up switches of the up-only key is above its overall rate",
          t["planted_up"]["sum_up"] / pw["dur"]["up"] > 5 * t["planted_up"]["sum_all"] / pw["dur"]["all"])
    # mis-alignment by 1 s must destroy the match (the alignment is used, not ignored)
    stats_bad = []
    for p in procs:
        w, st, ws, sw = L.watch_proc(p, wf[p.idx])
        stats_bad.append(L.watch_stats(w.events(), [(k, x + 1.0) for k, x in sw], w.span(), w.nslots(),
                                       clip=(ws[0].ts, ws[-1].te)))
    pb = L.pool_watch(stats_bad)
    check("watch: switch times shifted by 1 s lose the planted key", pb["tab"]["planted_any"]["up"] / 16.0 < 0.3,
          pb["tab"]["planted_any"]["up"])
    # a wrong header (boot_ns = mono_ns, so the boot offset is ignored) must also lose it
    wrong = os.path.join(tmp, "wrongclock")
    os.makedirs(wrong)
    shutil.copy(os.path.join(folder, "XW.csv"), wrong)
    for i, path in wf.items():
        txt = open(path).read().split("\n")
        m = [x for x in txt[1].split() if x.startswith("mono_ns=")][0]
        txt[1] = "# clocks %s boot_ns=%s real_ns=1" % (m, m.split("=")[1])
        with open(os.path.join(wrong, os.path.basename(path)), "w") as f:
            f.write("\n".join(txt))
    wf2 = L.watch_files(wrong)
    pw2 = L.pool_watch([L.watch_proc(p, wf2[p.idx])[1] for p in L.load([wrong])])
    check("watch: without the boot/mono offset no planted switch is sampled or matched",
          pw2["n"]["up"] == 0 or pw2["tab"].get("planted_any", {"up": 0})["up"] == 0, pw2["n"])
    # a switch outside the sampled span is not counted
    st_out = L.watch_stats(w0.events(), [("up", 500.0), ("up", 6.42)], w0.span(), w0.nslots())
    check("watch: a switch outside the sampled span is marked and not counted",
          [cv for _, _, _, cv in st_out["per_switch"]] == [False, True] and L.pool_watch([st_out])["n"]["up"] == 1)
    # the plain format of the task text: one line per sample, no hz in the header
    plain = os.path.join(tmp, "watch-77.txt")
    with open(plain, "w") as f:
        f.write("# mono_ns=1000000000 boot_ns=3000000000\n# starttime_ticks=250 clk_tck=100\n"
                "1100000000 a=0 b=0 txt=x\n1200000000 a=4 b=0 txt=x\n1300000000 a=0 b=0 txt=y\n1400000000 a=0 b=1 txt=y\n")
    wp = L.Watch(plain)
    evp = sorted(wp.events())
    check("watch: plain format: start = 2.5 s boot = 0.5 s mono; lines at 0.6 to 0.9 s", close(wp.start_mono_ns()[0], 5e8, 1)
          and close(wp.span()[0], 0.6, 1e-9) and close(wp.span()[1], 0.9, 1e-9), wp.span())
    check("watch: plain format: change interval = the distance to the line before; a text key changes when its "
          "text changes", [(round(a, 3), round(b, 3), k) for a, b, k, _ in evp]
          == [(0.6, 0.7, "a"), (0.7, 0.8, "txt"), (0.8, 0.9, "b")] and wp.slot_s()[1] is False, evp)
    # header without the needed keys
    bad = os.path.join(tmp, "watch-9.txt")
    with open(bad, "w") as f:
        f.write("# mono_ns=5\n100 a=1\n")
    check("watch: a header without the clock keys gives no alignment", L.Watch(bad).start_mono_ns() == (None, None)
          and L.Watch(bad).events() == [] and L.Watch(bad).span() is None)
    return folder


def test_live_sampler(tmp):
    """The real chain on this machine: the stand-in bwx8 and X/hostwatch.py beside it. Rates mean nothing here.
    It checks the shared file format and the clock alignment against times that the test measures itself."""
    X = os.path.normpath(os.path.join(A, "..", "..", "tmp", "agent-scratch", "bwx8-2026-11-14"))
    hw, src = os.path.join(X, "hostwatch.py"), os.path.join(X, "bwx8.c")
    if not (os.path.exists(hw) and os.path.exists(src) and shutil.which("gcc")):
        print("NOTE  hostwatch.py, bwx8.c or gcc not found: the live sampler checks did not run")
        return
    d = os.path.join(tmp, "live")
    os.makedirs(d)
    cflags = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "
              "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()
    binary = os.path.join(d, "bwx8")
    r = subprocess.run(["gcc"] + cflags + ["-o", binary, src], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        print("NOTE  the stand-in build of bwx8 failed: the live sampler checks did not run")
        return
    allowed = sorted(os.sched_getaffinity(0))
    if len(allowed) < 3:
        print("NOTE  fewer than 3 CPUs allowed: the live sampler checks did not run")
        return
    ctl, cpu, wcpu = allowed[0], allowed[len(allowed) // 2], allowed[-1]
    plan = os.path.join(d, "live.plan")
    with open(plan, "w") as f:
        f.write("# bwx8-plan v1\n# step=XW session=1 cpu=%d bytes=%d proc=0 seed=1 test=1\n"
                "# trial cond rep prev pfx pred tgt nwin win_ms count bins\n"
                "0 K=read|S=8M|prev=none 1 - - - read@8M 8 300 closed 0\n" % (cpu, MIB8))
    import time
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}
    csv = os.path.join(d, "XW.csv")
    with open(csv, "w") as out:
        out.write("-- step XW session 1 idx 0 tag live waited_s 0 loadavg 0 0 0 1/1 logins 0 utc 00:00:00 args x\n")
        out.flush()
        before = time.clock_gettime(time.CLOCK_MONOTONIC)
        child = subprocess.Popen([binary, "--trial", "--cpus", str(cpu), "--ctl-cpu", str(ctl), "--bytes", str(MIB8),
                                  "--plan", plan], stdout=out, stderr=subprocess.PIPE, env=env)
        after = time.clock_gettime(time.CLOCK_MONOTONIC)
        watch = subprocess.Popen(["taskset", "-c", str(wcpu), sys.executable, hw, "--pid", str(child.pid), "--cpu",
                                  str(cpu), "--out", os.path.join(d, "watch-0.txt"), "--max-s", "20"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        err = child.communicate(timeout=60)[1]
        watch.communicate(timeout=30)
    check("live: the stand-in bwx8 ran the plan", child.returncode == 0, err[-300:])
    check("live: hostwatch.py ended with status 0", watch.returncode == 0, watch.returncode)
    procs = L.load([d])
    wf = L.watch_files(d)
    check("live: one process and its watch file", len(procs) == 1 and 0 in wf and len(procs[0].W) == 8,
          (len(procs), sorted(wf)))
    if not (len(procs) == 1 and 0 in wf):
        return
    w = L.Watch(wf[0])
    s0, tick = w.start_mono_ns()
    check("live: the header of hostwatch.py holds mono_ns, boot_ns, starttime_ticks, clk_tck and hz",
          s0 is not None and w.slot_s()[1], sorted(w.head)[:12])
    if s0 is None:
        return
    check("live: process start from the header lies between the test's own clock reads around the launch, within "
          "one clock tick", before * 1e9 - tick <= s0 <= after * 1e9 + tick,
          (s0 / 1e9 - before, after - s0 / 1e9, tick / 1e9))
    sp = w.span()
    end = procs[0].W[-1].te
    check("live: the sampled span starts inside the first second of the process and ends within 1 s of its last "
          "window", sp is not None and 0.0 <= sp[0] <= 1.0 and abs(sp[1] - end) <= 1.0, (sp, end))
    ev = w.events()
    keys = set(k for _, _, k, _ in ev)
    check("live: the worker thread's run time is among the changed keys", any(k.endswith(".run_ns") and
                                                                              k.split(".")[0] in ("w", "m", "cpu")
                                                                              for k in keys), sorted(keys)[:20])
    wr = [k for k in keys if k in ("w.run_ns", "cpu.run_ns")]
    st = L.watch_proc(procs[0], wf[0])[1]
    check("live: a run-time key of the busy CPU changes in most +-0.15 s intervals (base rate above 0.8)",
          bool(wr) and st["grid_n"] > 10 and max(st["grid_changed"][k] for k in wr) / float(st["grid_n"]) > 0.8,
          (wr, st["grid_n"]))
    rc, outw, errw = run_cli(["watch", d])
    check("live: 'levels9.py watch' runs on the live folder", rc == 0 and errw == "" and "POOLED" in outw
          and "clock tick" in outw, errw[:300])


def test_cells(tmp):
    c = Csv()
    vals = {}
    idx = 0
    for kernel, size, base in (("read", MIB8, 70.0), ("oldread", MIB8, 67.0), ("read", 2 << 20, 80.0)):
        for cpu in (2, 41):
            for rep in range(3):
                c.proc(idx, "r%d-%s-cpu%d-%s" % (rep + 1, L.size_name(size), cpu, kernel), cpu, step="XF", nbytes=size,
                       plan={"kernel": kernel, "size": size, "rep_set": rep + 1})
                rates = []
                f4 = []
                t = 0.0005
                for tr in range(4):
                    pre = [(t + 0.3 * i, t + 0.3 * i + 0.2999, base + 0.01 * (idx + tr + i)) for i in range(4)]
                    t += 1.2
                    tg = [(t + 0.3 * i, t + 0.3 * i + 0.2999, base + 1.0 * tr + 0.1 * i + 0.001 * idx) for i in range(4)]
                    t += 1.2
                    c.trial(tr, "K=%s|S=%s" % (kernel, L.size_name(size)), kernel, size, pre, phase="prefix")
                    c.trial(tr, "x", kernel, size, tg, s_row=False)
                    c.end(tr)
                    rates += [r for _, _, r in pre] + [r for _, _, r in tg]
                    f4.append(tg[3][2])
                vals[idx] = (kernel, size, cpu, L.median(f4), L.median(rates), L.percentile(rates, 5),
                             L.percentile(rates, 95))
                idx += 1
    path = os.path.join(tmp, "XF.csv")
    c.write(path)
    cells = L.cell_table(L.parse_csv(path))
    check("cells: 6 cells of 3 processes", len(cells) == 6 and all(len(v) == 3 for v in cells.values()),
          {k: len(v) for k, v in cells.items()})
    ok = True
    worst = 0.0
    for key, lst in cells.items():
        for p, v in lst:
            k, s, cpu, f4, med, p5, p95 = vals[p.idx]
            if (key[1], key[2], key[3]) != (k, s, str(cpu)):
                ok = False
            worst = max(worst, abs(v["fourth"] - f4), abs(v["med_all"] - med), abs(v["p5"] - p5), abs(v["p95"] - p95))
    check("cells: every process sits in the cell of its kernel, size and cpu", ok)
    check("cells: fourth-window median, all-window median, 5th and 95th percentile are exact (1e-6 GB/s)",
          worst < 1e-6, worst)
    lst = cells[("XF", "read", MIB8, "2", "1")]
    check("cells: the fourth-window value is the median over the 4 trials (not the first trial)",
          close(lst[0][1]["fourth"], 70.0 + 0.3 + 1.5, 1e-6) and lst[0][1]["nfourth"] == 4, lst[0][1])
    check("percentile: linear interpolation", close(L.percentile([1, 2, 3, 4, 5], 5), 1.2, 1e-12)
          and close(L.percentile([1, 2, 3, 4, 5], 95), 4.8, 1e-12) and L.median([3, 1, 2, 10]) == 2.5)
    return path


def run_cli(args):
    r = subprocess.run([sys.executable, os.path.join(A, "levels9.py")] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    return r.returncode, r.stdout, r.stderr


def test_cli(tmp, cnt_path, watch_folder, cells_path):
    # a sustained file with a periodic process-tied pattern, for 'switches'
    c = Csv()
    for idx in range(6):
        up_t = [6.42 + 6.9 * k for k in range(8)]
        dn_t = [u + 1.5 + 0.41 * idx for u in up_t]
        wins = synth_windows(200, sorted(up_t + dn_t), "low", noise=0.02, seed=idx)
        c.proc(idx, "read-cpu2-p%d" % idx, 2, utc="01:%02d:%02d" % (idx, (17 * idx) % 60))
        c.trial(0, "K=read|S=8M", "read", MIB8, wins)
        c.end(0)
    c.proc(6, "oldread-cpu2-p1", 2, utc="01:10:00")
    c.trial(0, "K=oldread|S=8M", "oldread", MIB8, synth_windows(200, [], "low", low=67.05, noise=0.03))
    c.end(0)
    path = os.path.join(tmp, "S4.csv")
    c.write(path)
    rc, out, err = run_cli(["switches", path])
    check("cli switches: status 0 and no stderr", rc == 0 and err == "", err[:300])
    check("cli switches: the old read process has one level", "one level 67.0" in out)
    check("cli switches: the pooled fit finds the planted period 6.9 s",
          any("pooled fit of the up times" in l and "period 6.90" in l for l in out.splitlines()),
          [l for l in out.splitlines() if "pooled fit" in l])
    check("cli switches: the recurring up time 6.42 s is listed for 6 processes",
          any("mean   6.42" in l and "in  6 processes" in l for l in out.splitlines()),
          [l for l in out.splitlines() if "mean " in l][:3])
    check("cli switches: histogram, modulo table and wall-clock test are printed",
          "up times since process start (bin 0.1 s): n=48" in out and "wall clock: R, phase, sd s" in out
          and "wall-clock test near" in out and "(est.)" in out)
    rc, out2, err = run_cli(["switches", cells_path, "--sizes", "8M"])
    check("cli switches: multi-trial file runs, --sizes filters", rc == 0 and "S=2M" not in out2 and "S=8M" in out2,
          err[:300])
    # S2-style file with a switch: trial boundaries are printed
    c = Csv()
    c.proc(0, "r1-8M-cpu2-read", 2, step="S2")
    t = 0.0005
    sw = [2.81, 4.01]
    allw = synth_windows(32, sw, "high", t0=t)
    for tr in range(4):
        c.trial(tr, "K=read|S=8M", "read", MIB8, allw[8 * tr:8 * tr + 4], phase="prefix")
        c.trial(tr, "x", "read", MIB8, allw[8 * tr + 4:8 * tr + 8], s_row=False)
        c.end(tr)
    p2 = os.path.join(tmp, "S2.csv")
    c.write(p2)
    rc, out3, err = run_cli(["switches", p2])
    check("cli switches: S2-style process lists its switches and its trial starts",
          rc == 0 and "up   (est.): 4.0" in out3 and "down (est.): 2.8" in out3 and "trial starts: 0.00 2.40 4.80 7.20" in out3,
          out3[-600:] + err[:200])
    check("cli switches: switch times since the trial start are pooled",
          "up times since the start of the trial that holds them" in out3 and "   1.6 s    1" in out3)
    rc, outc, err = run_cli(["counters", cnt_path])
    check("cli counters: status 0, levels and difference printed",
          rc == 0 and err == "" and "level low" in outc and "level high" in outc and "level one" in outc
          and "low minus high" in outc and "4 multiplexed" in outc, err[:300])
    check("cli counters: the planted per-process differences 200 and 220 are printed",
          any("l2d_cache_refill" in l and "[200 220]" in l and "median 210" in l for l in outc.splitlines()),
          [l for l in outc.splitlines() if "l2d_cache_refill" in l][-1:])
    rc, outw, err = run_cli(["watch", watch_folder])
    check("cli watch: status 0, pooled table and tick printed",
          rc == 0 and err == "" and "POOLED: 16 up switches, 16 down switches" in outw and "clock tick: 10.0 ms" in outw,
          err[:300])
    first = [l.split()[0] for l in outw.splitlines() if l.startswith("  planted") or l.startswith("  decoy")
             or l.startswith("  state_key")]
    check("cli watch: the planted keys are sorted above the decoy and the state key",
          sorted(first[:2]) == ["planted_any", "planted_up"] and "decoy" in first, first)
    check("cli watch: every switch line names the planted key",
          all("planted_any" in l for l in outw.splitlines() if l.startswith("    up ") or l.startswith("    down")))
    rc, outf, err = run_cli(["cells", cells_path])
    check("cli cells: status 0 and 6 cells", rc == 0 and err == "" and outf.count("CELL step=XF") == 6, err[:300])
    check("cli cells: process values, median and range are printed",
          any(l.startswith("  fourth") and "median" in l and "range" in l for l in outf.splitlines()))
    rc, _, _ = run_cli([])
    check("cli: no command gives status 2", rc == 2, rc)


def test_real():
    R = os.path.normpath(os.path.join(A, "..", "..", "results"))
    s4 = os.path.join(R, "bwx8-S4-s1-20261115T010216Z", "S4.csv")
    if not os.path.exists(s4):
        print("NOTE  session 1 folder %s not found: the checks on real data did not run" % s4)
        return
    procs = L.parse_csv(s4)
    check("real S4: 18 processes of 200 windows", len(procs) == 18 and all(len(p.W) == 200 for p in procs), len(procs))
    old = [L.segment_proc(p)[1] for p in procs if p.kernel == "oldread"]
    check("real S4: old read has one level and no switch in 6 of 6 processes",
          len(old) == 6 and all(s["high"] is None and not s["switches"] for s in old))
    p4 = [p for p in procs if p.tag == "asmread-cpu41-p1"][0]
    seg = L.segment_proc(p4)[1]
    check("real S4: asmread-cpu41-p1 has its first up switch between 6.3 and 6.6 s (the trace shows 68.9, 70.6, 71.6 "
          "there)", seg["high"] is not None and L.ups(seg) and 6.3 < L.ups(seg)[0] < 6.6, L.ups(seg)[:2])


def test_review(tmp):
    """Checks added by the review of levels9.py."""
    # launch times across midnight (UTC): the wall-clock value must keep the real distance of the launches
    c = Csv()
    for i, utc in enumerate(("23:59:40", "00:00:40", "00:01:40")):
        c.proc(i, "read-cpu2-p%d" % (i + 1), 2, utc=utc)
        c.trial(0, "K=read|S=8M", "read", MIB8, synth_windows(40, [6.42], "low"))
        c.end(0)
    path = os.path.join(tmp, "midnight.csv")
    c.write(path)
    ps = L.parse_csv(path)
    ls = [q.launch_s for q in ps]
    check("review: launch seconds grow by 60 s across midnight", [b - a for a, b in zip(ls, ls[1:])] == [60, 60], ls)
    # a process with a previous activity: target start printed, first up per condition
    c = Csv()
    for i, (cond, t0, up) in enumerate((("K=read|S=8M|prev=none", 0.001, 6.42), ("K=read|S=8M|prev=none", 0.001, 6.45),
                                        ("K=read|S=8M|prev=oldread@8M", 3.002, 9.40),
                                        ("K=read|S=8M|prev=oldread@8M", 3.002, 9.46))):
        c.proc(i, "W-cpu2-p%d" % i, 2, step="XW", utc="02:00:%02d" % i)
        if t0 > 1:
            c.trial(0, cond, "oldread", MIB8, [(0.001, 3.001, 67.0)], phase="prev")
            c.trial(0, cond, "read", MIB8, synth_windows(60, [up], "low", t0=t0), s_row=False)
        else:
            c.trial(0, cond, "read", MIB8, synth_windows(60, [up], "low", t0=t0))
        c.end(0)
    c.lines.append("-- killed tag W-cpu2-p3 status 3 utc 02:01:00")
    path = os.path.join(tmp, "onset.csv")
    c.write(path)
    rc, out, err = run_cli(["switches", path])
    line = [x for x in out.split("\n") if "prev=oldread@8M" in x and "since first window" in x]
    check("review: the target start of a process with a previous activity is printed",
          rc == 0 and out.count("target starts at 3.00 s") == 2, err[-300:])
    check("review: first up per condition, since process start and since the first window of the kernel and size",
          len(line) == 1 and "[9.40 9.46] median 9.43" in line[0] and "[6.40 6.46] median 6.43" in line[0], line)
    check("review: a killed process carries a NOTE line", "NOTE: killed tag W-cpu2-p3 status 3" in out
          and out.count("NOTE:") == 1)
    # counters: 3 windows (step XEV) are too few for levels; their counts must still be shown, as 'unsplit'
    c = Csv()
    c.proc(0, "A", 2, step="XEV", events=["cpu_cycles=0x11"])
    wins = synth_windows(3, [], "low")
    rows = c.trial(0, "K=read|S=8M", "read", MIB8, wins, counts=[[5000], [5000], [5000]], count="read")
    c.end(0)
    c.lines.append("X,0,count_open,1 of 6 events did not open; first: x")
    path = os.path.join(tmp, "xev.csv")
    c.write(path)
    cells = L.counter_table(L.parse_csv(path))
    q = list(cells.values())[0]["procs"][0] if cells else None
    check("review: a counted process with 3 windows has level 'unsplit' with exact counts",
          q is not None and list(q["levels"]) == ["unsplit"] and q["levels"]["unsplit"]["n"] == 3 and q["mixed"] == 0
          and close(q["levels"]["unsplit"]["per64"]["cpu_cycles"], 5000 * 64.0 / rows[1], 1e-9),
          q and q["levels"])
    rc, out, err = run_cli(["counters", path])
    check("review: cli counters prints the unsplit level and the X row note",
          rc == 0 and "unsplit" in out and "NOTE: X row count_open x1" in out, out[-400:])


def main():
    tmp = tempfile.mkdtemp(prefix="levels9-test-")
    try:
        test_segmentation()
        test_one_level()
        test_fits()
        test_wallclock()
        test_parser(tmp)
        sub = os.path.join(tmp, "sub")
        os.makedirs(sub)
        cnt = test_counters(sub)
        wfolder = test_watch(tmp)
        cells = test_cells(sub)
        test_cli(tmp, cnt, wfolder, cells)
        test_review(tmp)
        test_live_sampler(tmp)
        test_real()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d checks, %d failed" % (NCHECK[0], len(FAILS)))
    for f in FAILS:
        print("FAILED: " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
