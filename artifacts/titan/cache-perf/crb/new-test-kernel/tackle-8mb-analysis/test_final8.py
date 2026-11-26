#!/usr/bin/env python3
"""test_final8.py - checks of final8.py.

Usage: test_final8.py [--tmp DIR]
Prints one line per check. Exit status 0 only if every check passed.

Part 1 builds small synthetic result folders (csv files in the format of run_bwx8.sh) in a temporary
folder (under --tmp, else under $TMPDIR) and runs final8.build on them. Each rule evaluator gets a case that
supports its hypothesis and a case that contradicts it, so a wrong threshold or a wrong sign fails a check.
Part 2 (smoke test) runs final8.py on the real result folders, if they exist, and compares a few known
session 1 numbers.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, A)
import final8 as F  # noqa: E402

FAILS = []
NCHECK = [0]
K32, M1, M4, M8, M16 = 32 << 10, 1 << 20, 4 << 20, 8 << 20, 16 << 20
LOW, HIGH = 67.5, 71.0


def check(name, ok, detail=""):
    NCHECK[0] += 1
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail) + "]") if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


# ---------------------------------------------------------------- synthetic folders
class Folder:
    """One result folder: <prefix>-<STEP>-s<session>-<UTC>/<STEP>.csv and launches.txt."""

    def __init__(self, root, prefix, step, ses):
        self.step, self.ses = step, ses
        self.dir = os.path.join(root, "%s-%s-s%d-20261115T0%d0000Z" % (prefix, step, ses, ses))
        os.makedirs(self.dir)
        self.lines, self.launch, self.n = [], [], 0

    def proc(self, cpu, kernel, size, trials, win_ms=300, tag=None, events=None, counts=None, M=None, bins=None):
        """trials: list of lists of window rates (GB/s). With 8 rates per trial the first 4 are prefix windows
        (S2 style); otherwise all are target windows. counts: function(trial, window index, rate) -> list of
        counts per 64 B, one per event (target windows only). bins: rate of the 10 ms B rows of each target
        window, a number or a function of the bin number."""
        idx = self.n
        self.n += 1
        tag = tag or "%s-%d-cpu%d-p%d" % (kernel, size, cpu, idx)
        self.lines.append("-- step %s session %d idx %d tag %s waited_s 0 loadavg 0.50 0.40 0.30 1/100 logins 0 "
                          "utc 01:%02d:%02d args --trial --cpus %d" % (self.step, self.ses, idx, tag, idx // 60,
                                                                        idx % 60, cpu))
        self.launch.append("== %s.csv idx %d %s utc 01:%02d:%02d loadavg 0.50 0.40 0.30 1/100 logins 0" % (
            self.step, idx, tag, idx // 60, idx % 60))
        w = self.lines.append
        w("# bwx8 trial mode: synthetic")
        m = {"mode": "trial", "cpu": cpu, "bytes": size, "events": ";".join("%s=0x1" % e for e in events) if events
             else "none", "plan.step": self.step, "plan.session": self.ses, "plan.cpu": cpu, "plan.proc": idx,
             "plan.kernel": kernel, "plan.size": size}
        m.update(M or {})
        for k, v in m.items():
            w("M,%s,%s" % (k, v))
        t = 1000
        dur = win_ms * 1000000
        for ti, rates in enumerate(trials):
            s2 = len(rates) == 8
            ntgt = 4 if s2 else len(rates)
            w("S,%d,K=%s|S=%d,%d,-,-,-,%s@%d,%d,%d,%s,%d,none,none" % (
                ti, kernel, size, ti + 1, kernel, size, ntgt, win_ms, "read" if events else "closed", 1 if bins else 0))
            for k, r in enumerate(rates):
                phase, widx = ("prefix", k) if s2 and k < 4 else ("target", k - 4 if s2 else k)
                nbytes = int(round(r * dur))
                w("W,%d,%s,%d,%s,%d,%d,%d,%d" % (ti, phase, widx, kernel, size, nbytes, t, t + dur))
                if events and phase == "target":
                    cs = counts(ti, widx, r)
                    w("C,%d,%d,%d,%d,%d,%s" % (ti, widx, dur, dur, dur, ",".join(
                        str(int(round(c * nbytes / 64.0))) for c in cs)))
                if bins and phase == "target":
                    done = 0.0
                    for b in range(win_ms // 10):
                        done += (bins(b) if callable(bins) else bins) * 10000000
                        w("B,%d,%d,%d,%d,%d" % (ti, widx, b, t + (b + 1) * 10000000, int(round(done))))
                t += dur + 100
            w("E,%d,%d,%d,0,0,50,100,NA,%s" % (ti, t, t, "read" if events else "closed"))
        return idx

    def save(self):
        with open(os.path.join(self.dir, self.step + ".csv"), "w") as f:
            f.write("\n".join(self.lines) + "\n")
        with open(os.path.join(self.dir, "launches.txt"), "w") as f:
            f.write("\n".join(self.launch) + "\n")


def flat(rate, n=8, trials=4):
    return [[rate] * n for _ in range(trials)]


def two_level(n=8, trials=4):
    """S2-style trials that visit both levels: 3 of 4 trials low, one high (median low, p95 high)."""
    return [[LOW] * n, [HIGH] * n, [LOW] * n, [LOW] * n][:trials]


def toggles(n, events, start="low", low=LOW, high=HIGH):
    """n window rates; the level flips at each window index in `events` (sorted)."""
    lev = start
    out = []
    ev = set(events)
    for i in range(n):
        if i in ev:
            lev = "high" if lev == "low" else "low"
        out.append(high if lev == "high" else low)
    return out


def build(root):
    J, text = F.build(root, summary=os.path.join(root, "no-summary.json"))
    json.loads(json.dumps(J))            # must be serialisable
    return J, text


# ---------------------------------------------------------------- item 6: counters by level
def test_counters(tmp):
    def make(root, sessions, ev_low, ev_high, two_level_procs=4, counted_shift=0.0, sign_flip=False):
        for ses in sessions:
            s4 = Folder(root, "bwx8", "S4", ses)
            xc = Folder(root, "bwx9", "XCB", ses)
            for cpu in (2, 41):
                for k in ("read", "asmread"):
                    for rep in range(2):
                        s4.proc(cpu, k, M8, [toggles(100, [21, 42, 67])])
                n = 0
                for k in ("read", "asmread"):
                    for rep in range(2):
                        n += 1
                        tog = [21, 42, 67] if n <= two_level_procs else []
                        flip = sign_flip and n % 2 == 0

                        def counts(ti, widx, r, flip=flip):
                            low = r < 69.0 + counted_shift
                            a, b = (ev_low, ev_high) if not flip else (ev_high, ev_low)
                            # 'same' has a within-level spread of 0.01 and no level difference
                            return [a if low else b, 0.50 + 0.01 * (widx % 3)]
                        xc.proc(cpu, k, M8, [toggles(100, tog, low=LOW + counted_shift, high=HIGH + counted_shift)],
                                events=["l1d_cache_lmiss_rd", "same"], counts=counts)
                xc.proc(cpu, "oldread", M8, [[67.0] * 100], events=["l1d_cache_lmiss_rd", "same"],
                        counts=lambda ti, widx, r: [0.007, 0.5])
            s4.save()
            xc.save()

    root = os.path.join(tmp, "c1")
    make(root, (1, 2), 0.37, 0.30)
    J, _ = build(root)
    r3 = J["counters"]["rule3"]
    cell = r3["l1d_cache_lmiss_rd"]["per_cell"]["cpu2/s1"]
    check("counters: an event 0.07 higher at the low level 'differs'", cell["verdict"] == "differs", cell)
    check("counters: low minus high is +0.07 in 4 processes", len(cell["diffs"]) == 4 and
          all(close(d, 0.07, 1e-3) for d in cell["diffs"]), cell["diffs"])
    check("counters: both sessions and both CPUs give 'confirmed'",
          r3["l1d_cache_lmiss_rd"]["overall"].startswith("confirmed"), r3["l1d_cache_lmiss_rd"]["overall"])
    check("counters: an event without a level difference 'does not differ'",
          all(v["verdict"] == "does not differ" for v in r3["same"]["per_cell"].values())
          and r3["same"]["overall"] == "does not differ", r3["same"])
    rows = [r for r in J["counters"]["rows"] if r["event"] == "l1d_cache_lmiss_rd" and r["kernel"] == "asmread"
            and r["cpu"] == 2 and r["session"] == 1]
    check("counters: table row has low 0.37 and high 0.30 per 64 B", len(rows) == 1 and close(rows[0]["low"], 0.37, 1e-3)
          and close(rows[0]["high"], 0.30, 1e-3), rows)
    old = [r for r in J["counters"]["rows"] if r["kernel"] == "oldread" and r["event"] == "l1d_cache_lmiss_rd"]
    check("counters: old read has one level with 0.007 per 64 B", old and all(close(r["single"], 0.007, 1e-4) and
                                                                               r["low"] is None for r in old), old[:1])
    acc = [a for a in J["counters"]["acceptance"] if a["step"] == "XCB"]
    check("acceptance rule 1: counted levels equal to the S4 levels pass", len(acc) == 4 and all(a["pass"] for a in acc),
          acc)

    root = os.path.join(tmp, "c2")
    make(root, (1,), 0.37, 0.30)
    J, _ = build(root)
    o = J["counters"]["rule3"]["l1d_cache_lmiss_rd"]["overall"]
    check("counters: one session alone is not 'confirmed'", "session 2 missing" in o and "confirmed:" not in o, o)

    root = os.path.join(tmp, "c3")
    make(root, (1, 2), 0.37, 0.30, sign_flip=True)
    J, _ = build(root)
    r = J["counters"]["rule3"]["l1d_cache_lmiss_rd"]
    check("counters: processes with opposite signs 'do not differ'",
          all(v["verdict"] == "does not differ" for v in r["per_cell"].values()) and
          not r["overall"].startswith("confirmed"), r["overall"])

    root = os.path.join(tmp, "c4")
    make(root, (1, 2), 0.37, 0.30, two_level_procs=2)
    J, _ = build(root)
    r = J["counters"]["rule3"]["l1d_cache_lmiss_rd"]["per_cell"]["cpu41/s2"]
    check("counters: 2 processes with both levels are 'Insufficient data'", r["verdict"].startswith("Insufficient data"),
          r["verdict"])

    root = os.path.join(tmp, "c5")
    make(root, (1,), 0.37, 0.30, counted_shift=1.0)
    J, _ = build(root)
    acc = [a for a in J["counters"]["acceptance"] if a["step"] == "XCB"]
    check("acceptance rule 1: counted levels 1.0 GB/s off fail", acc and all(a["pass"] is False and
                                                                          a["verdict"] == "counted mode differs"
                                                                          for a in acc), acc)
    # the evaluator alone: spread rule
    r = F.rule3_event([([1.0, 1.2], [0.5, 0.7])] * 3)
    check("rule3_event: difference 0.5 with spread 0.1 differs", r["differs"] is True and r["sign"] == 1, r)
    r = F.rule3_event([([0.8, 1.4], [0.5, 0.7])] * 3)
    check("rule3_event: difference 0.5 with spread 0.3 does not differ (needs more than twice the spread)",
          r["differs"] is False, r)


# ---------------------------------------------------------------- item 7: XN and ZN
def test_families(tmp):
    def make_xn(root, sessions, nop16_high, slow8):
        for ses in sessions:
            xn = Folder(root, "bwx9", "XN", ses)
            for cpu in (2, 41):
                for rep in range(1, 7):
                    M = {"plan.rep_set": rep}
                    xn.proc(cpu, "asmread", K32, flat(132.0), M=M)
                    xn.proc(cpu, "asmread", M1, flat(85.24), M=M)
                    xn.proc(cpu, "asmread", M8, two_level(), M=M)
                    xn.proc(cpu, "read_nop16", K32, flat(131.0), M=M)
                    xn.proc(cpu, "read_nop16", M8, [[LOW] * 8, [nop16_high] * 8, [LOW] * 8, [LOW] * 8], M=M)
                    xn.proc(cpu, "slowk", K32, flat(60.0), M=M)
                    xn.proc(cpu, "slowk", M8, flat(slow8), M=M)
            xn.save()

    root = os.path.join(tmp, "f1")
    make_xn(root, (1, 2), HIGH, 60.0)
    J, _ = build(root)
    xn = J["families"]["XN"]
    c = xn["rule6"]["cpu2/s1"]
    check("rule 6: asmread levels come from its 8 MiB cell (p95 71.0, p5 67.5)", close(c["asm_high"], HIGH, 0.01)
          and close(c["asm_low"], LOW, 0.01), c)
    check("rule 6 (a) holds for a fast kernel that reaches the asmread high level",
          all(v["kernels"]["read_nop16"]["a"] is True for v in xn["rule6"].values()), xn["rule6"])
    check("rule 6 (b) holds for a slow kernel that keeps its rate",
          all(v["kernels"]["slowk"]["b"] is True and v["kernels"]["slowk"]["a"] is None
              for v in xn["rule6"].values()), xn["rule6"])
    check("rule 6 (c) holds: spread at 8 MiB 7.5 against 72 at 32 KiB", all(v["c"] is True for v in xn["rule6"].values()))
    check("rule 6 overall: not contradicted", all(v == "H1 not contradicted for this kernel"
                                                  for v in xn["overall"].values()), xn["overall"])
    row = [r for r in xn["rows"] if r["kernel"] == "asmread" and r["size"] == "1M" and r["cpu"] == 41 and
           r["session"] == 2]
    check("XN rows: asmread 1 MiB cell median 85.24 from 6 processes", len(row) == 1 and close(row[0]["median"], 85.24,
                                                                                               0.005) and row[0]["n"] == 6)
    row = [r for r in xn["rows"] if r["kernel"] == "slowk" and r["size"] == "32K" and r["cpu"] == 2 and r["session"] == 1]
    check("XN rows: gain of asmread over a 60 GB/s kernel at 32 KiB is 120 %", close(row[0]["asmread_gain_pct"], 120.0, 0.1),
          row)

    root = os.path.join(tmp, "f2")
    make_xn(root, (1, 2), HIGH - 3.0, 57.0)
    J, _ = build(root)
    xn = J["families"]["XN"]
    check("rule 6 (a) fails for a fast kernel 3 GB/s under the asmread high level",
          all(v["kernels"]["read_nop16"]["a"] is False for v in xn["rule6"].values()))
    check("rule 6 (b) fails for a slow kernel that loses 3 GB/s",
          all(v["kernels"]["slowk"]["b"] is False for v in xn["rule6"].values()))
    check("rule 6 overall: contradicted on both CPUs in both sessions",
          xn["overall"]["read_nop16"].startswith("H1 contradicted") and "(a)" in xn["overall"]["read_nop16"] and
          xn["overall"]["slowk"].startswith("H1 contradicted") and "(b)" in xn["overall"]["slowk"], xn["overall"])
    check("rule 6 overall: asmread itself stays not contradicted",
          xn["overall"]["asmread"] == "H1 not contradicted for this kernel")

    root = os.path.join(tmp, "f3")
    make_xn(root, (1,), HIGH - 3.0, 57.0)
    J, _ = build(root)
    o = J["families"]["XN"]["overall"]["read_nop16"]
    check("rule 6 overall: one session gives no 'contradicted'", "session 2 missing" in o and
          not o.startswith("H1 contradicted"), o)

    def make_zn(root, sessions, slow8, fast_p95):
        for ses in sessions:
            zn = Folder(root, "bwx11", "ZN", ses)
            yf = Folder(root, "bwx10", "YF", ses)
            for cpu in (2, 41):
                for rep in range(1, 7):
                    M = {"plan.rep_set": rep}
                    yf.proc(cpu, "asmread", M8, two_level(), M=M)
                    yf.proc(cpu, "asmread", K32, flat(132.0), M=M)
                    zn.proc(cpu, "read_nop128", K32, flat(60.0), M=M)
                    zn.proc(cpu, "read_nop128", M8, flat(slow8), M=M)
                    zn.proc(cpu, "read_nop64", K32, flat(90.0), M=M)
                    zn.proc(cpu, "read_nop64", M8, [[LOW] * 8, [fast_p95] * 8, [LOW] * 8, [LOW] * 8], M=M)
                    zn.proc(cpu, "read_nop96", K32, flat(70.0), M=M)
                    zn.proc(cpu, "read_nop96", M8, flat(69.0), M=M)
            zn.save()
            yf.save()

    root = os.path.join(tmp, "f4")
    make_zn(root, (1, 2), 59.5, HIGH)
    J, _ = build(root)
    zn = J["families"]["ZN"]
    c = zn["rule2"]["cpu41/s2"]
    check("ZN: S8 comes from asmread at 8 MiB of YF (67.5 to 71.0)", close(c["S8_low"], LOW, 0.01) and
          close(c["S8_high"], HIGH, 0.01), c)
    check("ZN: slow kernel within 1.0 GB/s of C_k holds", c["kernels"]["read_nop128"]["prediction_holds"] is True
          and c["kernels"]["read_nop128"]["contradicts"] is False, c["kernels"]["read_nop128"])
    check("ZN: fast kernel with p95 inside S8 holds", c["kernels"]["read_nop64"]["prediction_holds"] is True)
    check("ZN: kernel between 66 and 76 at most min(C_k, top of S8) + 1.0 holds",
          c["kernels"]["read_nop96"]["prediction_holds"] is True and "between" in c["kernels"]["read_nop96"]["class"])
    check("ZN overall: slow kernel does not contradict H1", zn["overall"]["read_nop128"].startswith("H1 not contradicted"),
          zn["overall"])
    check("ZN rows: gain of asmread (YF, 132) over read_nop128 (60) at 32 KiB is 120 %",
          any(r["kernel"] == "read_nop128" and r["size"] == "32K" and close(r["asmread_gain_pct"], 120.0, 0.1)
              for r in zn["rows"]))

    root = os.path.join(tmp, "f5")
    make_zn(root, (1, 2), 57.0, HIGH + 2.0)
    J, _ = build(root)
    zn = J["families"]["ZN"]
    c = zn["rule2"]["cpu2/s1"]
    check("ZN: slow kernel that loses 3 GB/s fails and contradicts", c["kernels"]["read_nop128"]["prediction_holds"]
          is False and c["kernels"]["read_nop128"]["contradicts"] is True)
    check("ZN: fast kernel with p95 2 GB/s above S8 fails", c["kernels"]["read_nop64"]["prediction_holds"] is False)
    check("ZN overall: contradicted on both CPUs in both sessions",
          zn["overall"]["read_nop128"].startswith("H1 contradicted"), zn["overall"])
    check("ZN overall: the contradiction rule does not apply to a fast kernel",
          zn["overall"]["read_nop64"].startswith("not a slow kernel"), zn["overall"])


# ---------------------------------------------------------------- items 9 and 10: YL and YP
def test_yl(tmp):
    def make(root, by_len, one_window_rate=LOW, late_switch=0):
        yl = Folder(root, "bwx10", "YL", 1)
        for cpu in (2, 41):
            n1 = 0
            for k in ("read", "asmread"):
                for rep in range(2):
                    for wms, (n, start, tog) in by_len.items():
                        yl.proc(cpu, k, M8, [toggles(n, tog, start=start)], win_ms=wms, M={"plan.lcond": "L%d" % wms})
                    n1 += 1
                    # late_switch processes per CPU go from the low to the high level 10 s into the one window
                    bins = (lambda b: LOW if b < 1000 else HIGH) if n1 <= late_switch else one_window_rate
                    yl.proc(cpu, k, M8, [[one_window_rate]], win_ms=30000, bins=bins, M={"plan.lcond": "L30000"})
        yl.save()

    root = os.path.join(tmp, "y1")
    make(root, {100: (300, "high", [16, 21, 42, 44]), 300: (100, "high", [16, 21, 42, 44]),
                1000: (30, "high", [16, 21])})
    J, _ = build(root)
    v = J["YL"]["verdict"]["cpu2/s1"]
    check("YL: switches that keep windows 16 and 21 at 100 and 1000 ms support H7", v["verdict"] == "H7 supported", v)
    check("YL: medians are first fall 16 and first up 21", v["medians"]["100"]["fall"] == 16 and
          v["medians"]["1000"]["up"] == 21, v["medians"])
    check("YL: 4 of 4 one-window runs show no switch after 0.3 s", v["one_window_quiet"] == 4 and
          v["one_window_processes"] == 4, v)
    p = [r for r in J["YL"]["processes"] if r["window_ms"] == 100 and r["cpu"] == 41][0]
    check("YL: the process row lists every switch with its window", p["switches"] == [["fall", 16], ["up", 21],
                                                                                    ["fall", 42], ["up", 44]], p)
    p = [r for r in J["YL"]["processes"] if r.get("one_window")][0]
    check("YL: a one-window run gives 300 rates per 0.1 s", len(p["rates_per_0_1s"]) == 300 and
          close(p["rates_per_0_1s"][7], LOW, 0.01), len(p["rates_per_0_1s"]))
    check("YL overall: one session is not 'confirmed'", "session 2 missing" in J["YL"]["overall"], J["YL"]["overall"])

    root = os.path.join(tmp, "y2")
    make(root, {100: (300, "low", [63, 127, 132]), 300: (100, "high", [16, 21, 42, 44]), 1000: (30, "low", [6, 12, 13])})
    J, _ = build(root)
    v = J["YL"]["verdict"]["cpu41/s1"]
    check("YL: switches that keep their time (6.3 s and 12.76 s) reject H7", v["verdict"].startswith("H7 rejected"), v)

    root = os.path.join(tmp, "y4")
    make(root, {100: (300, "high", [16, 21, 42, 44]), 1000: (30, "high", [16, 21])}, late_switch=2)
    J, _ = build(root)
    v = J["YL"]["verdict"]["cpu2/s1"]
    p = [r for r in J["YL"]["processes"] if r.get("one_window") and r["switches_after_0_3s"]]
    check("YL: a one-window run that changes level after 10 s has 1 switch after 0.3 s", len(p) == 4 and
          all(r["switches_after_0_3s"] == 1 and close(r["switch_times_s"][0], 10.0, 0.11) for r in p), p[:1])
    check("YL: only 2 of 4 quiet one-window runs: H7 is not 'supported'", v["one_window_quiet"] == 2 and
          v["verdict"] == "undecided", v)
    root = os.path.join(tmp, "y5")
    make(root, {100: (300, "high", [16, 21, 42, 44]), 1000: (30, "high", [16, 21])}, late_switch=1)
    J, _ = build(root)
    check("YL: 3 of 4 quiet one-window runs are enough for 'supported'",
          J["YL"]["verdict"]["cpu41/s1"]["one_window_quiet"] == 3 and
          J["YL"]["verdict"]["cpu41/s1"]["verdict"] == "H7 supported", J["YL"]["verdict"]["cpu41/s1"])

    root = os.path.join(tmp, "y3")
    make(root, {100: (300, "high", [16, 21, 42, 44]), 1000: (30, "low", [6, 12, 13])})
    J, _ = build(root)
    v = J["YL"]["verdict"]["cpu2/s1"]
    check("YL: index at 100 ms and time at 1000 ms is 'undecided'", v["verdict"] == "undecided", v)


def test_yp(tmp):
    base_ups = [21, 44, 67, 90]

    def series(shift):
        ev = []
        for u in base_ups:
            ev += [u - shift, u - shift + 5]
        return toggles(100, sorted(e for e in ev if 0 < e < 100))

    def make(root, sessions, shift_of, hot_switches=0):
        for ses in sessions:
            yp = Folder(root, "bwx10", "YP", ses)
            for cpu in (2, 41):
                for rep in range(2):
                    for pad in (0, 80, 400, 1040, 2080, 4000):
                        yp.proc(cpu, "asmread", M8, [series(shift_of(pad))],
                                M={"rec_pad": pad, "hot_copy": 0, "win_addr": "%x" % (0xffff7c000c38 + pad),
                                   "win_size": 80, "plan.pcond": "P%d" % pad})
                    yp.proc(cpu, "asmread", M8, [toggles(100, [21, 26, 44, 49][:hot_switches])],
                            M={"rec_pad": 0, "hot_copy": 1, "win_addr": "ffff7c000c38", "win_size": 80})
            yp.save()

    root = os.path.join(tmp, "p1")
    make(root, (1, 2), lambda pad: (pad // 80) % 23)
    J, _ = build(root)
    yp = J["YP"]
    r = [x for x in yp["shift"] if x["pad"] == 400 and x["cpu"] == 2 and x["session"] == 1][0]
    check("YP: pad 400 moves the up series by 5 windows", r["median_shift"] == 5 and r["match"] is True, r)
    r = [x for x in yp["shift"] if x["pad"] == 1040 and x["cpu"] == 41 and x["session"] == 2][0]
    check("YP: pad 1040 (13 windows) matches modulo the spacing of 23", r["match"] is True and
          close(r["predicted_modulo_spacing"], -10.0, 1e-9), r)
    check("YP: falls move with the ups (pad 400: 5 windows)",
          [x for x in yp["shift"] if x["pad"] == 400][0]["fall"]["median_shift"] == 5)
    check("YP: verdict 'H7 supported' per session and 'confirmed' overall",
          yp["verdict"]["s1"].startswith("H7 supported") and yp["overall"].startswith("confirmed"), yp["overall"])
    check("YP: hot-copy without a switch meets the prediction", yp["hot_copy"]["s1"]["prediction_holds"] is True and
          yp["hot_copy"]["s1"]["switches_per_process"] == [0, 0, 0, 0], yp["hot_copy"])
    p = [x for x in yp["processes"] if x["pad"] == 80 and not x["hot_copy"]][0]
    check("YP: process row has M,win_addr, the up windows and the old statistic", p["win_addr"] == "ffff7c000c88" and
          p["ups"] == [20, 43, 66, 89] and p["first_fall_after_30"] == 48, p)

    root = os.path.join(tmp, "p2")
    make(root, (1, 2), lambda pad: 0, hot_switches=4)
    J, _ = build(root)
    yp = J["YP"]
    r = [x for x in yp["shift"] if x["pad"] == 400 and x["cpu"] == 2 and x["session"] == 1][0]
    check("YP: events that keep their window give shift 0 and no match", r["median_shift"] == 0 and r["match"] is False, r)
    check("YP: verdict 'H7 rejected' when no pad moves the events", yp["verdict"]["s1"].startswith("H7 rejected") and
          yp["overall"].startswith("H7 rejected"), yp["verdict"])
    check("YP: hot-copy with 4 switches per process fails the prediction",
          yp["hot_copy"]["s2"]["prediction_holds"] is False, yp["hot_copy"])

    root = os.path.join(tmp, "p3")
    make(root, (1,), lambda pad: {0: 0, 80: 1, 400: 5}.get(pad, 9))
    J, _ = build(root)
    check("YP: 2 of 5 pads matching is 'undecided'", J["YP"]["verdict"]["s1"].startswith("undecided"),
          J["YP"]["verdict"])
    check("YP overall: one session is not 'confirmed'", "session 2 missing" in J["YP"]["overall"])
    check("nearest_shift and circ_diff", F.nearest_shift([16, 39], [21, 44]) == [5, 5] and
          F.circ_diff(13, -10, 23) == 0 and F.circ_diff(2, 13, 23) == -11)


# ---------------------------------------------------------------- item 11: YC and YF
def test_prefetch(tmp):
    ev = list(F.YC_EVENTS)

    def make(root, sessions, pf_rate, pf_miss, asm_miss=0.36):
        for ses in sessions:
            yf = Folder(root, "bwx10", "YF", ses)
            yc = Folder(root, "bwx10", "YC", ses)
            for cpu in (2, 41):
                for rep in range(1, 7):
                    M = {"plan.rep_set": rep}
                    yf.proc(cpu, "asmread", M1, flat(85.2), M=M)
                    yf.proc(cpu, "asmread", M8, two_level(), M=M)
                    yf.proc(cpu, "read_pf1024", M1, flat(77.4), M=M)
                    yf.proc(cpu, "read_pf1024", M8, flat(pf_rate + 0.01 * rep), M=M)
                yc.proc(cpu, "asmread", M8, [[LOW] * 20], events=ev,
                        counts=lambda ti, w, r: [2.6, 2.75, asm_miss, 0.82, asm_miss, 0.0005])
                yc.proc(cpu, "read_pf1024", M8, [[pf_rate] * 20], events=ev,
                        counts=lambda ti, w, r: [2.7, 3.75, pf_miss, 0.82, pf_miss, 0.0006])
            yf.save()
            yc.save()

    root = os.path.join(tmp, "h1")
    make(root, (1, 2), 74.0, 0.15)
    J, _ = build(root)
    pf = J["prefetch"]
    r = pf["rule3"]["cpu2/s1"]
    check("H1b: a kernel with 42 % of the misses and +3 GB/s supports H1b", r["verdict"] == "H1b supported" and
          r["halving"] == ["read_pf1024"], r)
    sh = [x for x in pf["share"] if x["size"] == "8M" and x["cpu"] == 2 and x["session"] == 1][0]
    check("H1b: share of the asmread L1 long misses is 0.15 / 0.36", close(sh["share"], 0.15 / 0.36, 1e-3), sh)
    c = [x for x in pf["contrast"] if x["size"] == "8M" and x["cpu"] == 41 and x["session"] == 2][0]
    check("H1b: contrast pf minus asmread has six values near +6.5 (process medians), repeatable",
          len(c["values"]) == 6 and close(c["median"], 74.035 - LOW, 0.01) and c["repeatable"] and c["sign"] == 1, c)
    check("H1b: share of the 1 MiB to 8 MiB loss recovered = 6.535 / 17.7", close(c["share_of_loss_recovered"],
                                                                               (74.035 - LOW) / (85.2 - LOW), 1e-3), c)
    check("H1b overall: confirmed with both sessions", pf["overall"].startswith("confirmed"), pf["overall"])
    yc = [x for x in pf["YC"] if x["kernel"] == "read_pf1024" and x["cpu"] == 2 and x["session"] == 1][0]
    check("YC row: counts per 64 B and the YF cell values", close(yc["per64"]["cpu_cycles"], 2.7, 1e-3) and
          close(yc["per64"]["l1d_cache_lmiss_rd"], 0.15, 1e-3) and close(yc["yf_median"], 74.035, 0.01), yc)

    root = os.path.join(tmp, "h2")
    make(root, (1, 2), 66.0, 0.15)
    J, _ = build(root)
    pf = J["prefetch"]
    check("H1b: a kernel that halves the misses and is 5 GB/s slower rejects H1b",
          all(v["verdict"].startswith("H1b rejected") for v in pf["rule3"].values()) and
          pf["overall"].startswith("H1b rejected"), pf["overall"])

    root = os.path.join(tmp, "h3")
    make(root, (1, 2), 74.0, 0.19)
    J, _ = build(root)
    pf = J["prefetch"]
    check("H1b: a kernel with 53 % of the misses is 'Insufficient data'",
          all(v["verdict"].startswith("Insufficient data") for v in pf["rule3"].values()), pf["rule3"])

    root = os.path.join(tmp, "h4")
    make(root, (1,), 72.5, 0.15)
    J, _ = build(root)
    pf = J["prefetch"]
    check("H1b: a rise of 1.5 GB/s is 'undecided'", pf["rule3"]["cpu2/s1"]["verdict"].startswith("undecided"),
          pf["rule3"]["cpu2/s1"])
    check("H1b overall: one session is not 'confirmed'", "session 2 missing" in pf["overall"], pf["overall"])


# ---------------------------------------------------------------- item 12: ZC and ZD
def test_evict(tmp):
    ev = list(F.ZC_EVENTS)

    def make(root, sessions, wb_evict, high_evict, old_evict=67.0, with_zc=True):
        for ses in sessions:
            zd = Folder(root, "bwx11", "ZD", ses)
            zc = Folder(root, "bwx11", "ZC", ses)
            for cpu in (2, 41):
                for rep in range(1, 7):
                    for e in (0, 512):
                        M = {"plan.rep_set": rep, "evict_mb": e, "plan.econd": "E%d" % e}
                        hi = high_evict if e else HIGH
                        for k in ("asmread", "read"):
                            zd.proc(cpu, k, M8, [[LOW] * 8, [hi] * 8, [LOW] * 8, [LOW] * 8], M=M)
                        zd.proc(cpu, "oldread", M8, flat(old_evict if e else 67.0), M=M)
                for e in (0, 512):
                    for rep in range(2):
                        wb = wb_evict if e else 0.82
                        zc.proc(cpu, "asmread", M8, [[LOW] * 20], events=ev, M={"evict_mb": e},
                                counts=lambda ti, w, r, wb=wb: [2.6, 0.34, 0.82, wb, 3.3, 0.0005])
            zd.save()
            if with_zc:
                zc.save()
            else:
                shutil.rmtree(zc.dir)

    root = os.path.join(tmp, "e1")
    make(root, (1, 2), 0.05, HIGH + 4.0)
    J, _ = build(root)
    e = J["evict"]
    check("H1d: check passes (0.05 write-backs) and +4 GB/s supports H1d", e["rule1"]["s1"]["check"] is True and
          e["rule1"]["s1"]["verdict"] == "H1d supported" and e["overall"].startswith("confirmed"), e["rule1"])
    check("H1d: the rise of the 8 MiB p95 is 4.0 GB/s for both kernels on both CPUs",
          len(e["rule1"]["s2"]["p95_rise_8M"]) == 4 and all(close(v, 4.0, 0.01)
                                                            for v in e["rule1"]["s2"]["p95_rise_8M"].values()))
    zc = [r for r in e["ZC"] if r["evict_mb"] == 512 and r["cpu"] == 2 and r["session"] == 1][0]
    check("ZC row: write-backs per 64 B with evict", close(zc["per64"]["l2d_cache_wb"], 0.05, 1e-3) and
          zc["processes"] == 2, zc)
    zd = [r for r in e["ZD"] if r["kernel"] == "read" and r["cpu"] == 41 and r["session"] == 2][0]
    check("ZD row: p95 without and with evict", close(zd["plain"]["p95"], HIGH, 0.01) and
          close(zd["evict"]["p95"], HIGH + 4.0, 0.01) and close(zd["p95_diff"], 4.0, 0.01), zd)

    root = os.path.join(tmp, "e2")
    make(root, (1, 2), 0.05, HIGH + 0.5)
    J, _ = build(root)
    check("H1d: check passes and +0.5 GB/s rejects H1d", J["evict"]["rule1"]["s1"]["verdict"] == "H1d rejected" and
          J["evict"]["overall"].startswith("H1d rejected"), J["evict"]["overall"])

    root = os.path.join(tmp, "e3")
    make(root, (1,), 0.05, HIGH + 2.0)
    J, _ = build(root)
    check("H1d: a rise of 2.0 GB/s is 'partly'", J["evict"]["rule1"]["s1"]["verdict"] == "partly")

    root = os.path.join(tmp, "e4")
    make(root, (1, 2), 0.82, HIGH + 4.0)
    J, _ = build(root)
    r = J["evict"]["rule1"]["s1"]
    check("H1d: write-backs stay at 0.82: 'Insufficient data' although the rate rises", r["check"] is False and
          r["verdict"].startswith("Insufficient data") and J["evict"]["overall"].startswith("Insufficient data"), r)
    check("H1d: the descriptive rise is still reported when the check fails",
          all(close(v, 4.0, 0.01) for v in r["p95_rise_8M"].values()) and len(r["p95_rise_8M"]) == 4, r)

    root = os.path.join(tmp, "e5")
    make(root, (1,), 0.05, HIGH + 4.0, old_evict=67.6)
    J, _ = build(root)
    check("H1d: old read control moved by 0.6 GB/s: not decided",
          J["evict"]["rule1"]["s1"]["verdict"].startswith("not decided"), J["evict"]["rule1"]["s1"])

    root = os.path.join(tmp, "e6")
    make(root, (1,), 0.05, HIGH + 4.0, with_zc=False)
    J, _ = build(root)
    check("H1d: without ZC the check cannot be made: 'Insufficient data'",
          J["evict"]["rule1"]["s1"]["verdict"].startswith("Insufficient data") and
          J["evict"]["rule1"]["s1"]["check"] is None, J["evict"]["rule1"]["s1"])


# ---------------------------------------------------------------- item 13: ZS
def test_zs(tmp):
    ev = list(F.ZC_EVENTS)
    sizes = [M1, 3 << 19, 2 << 20, 5 << 19, 3 << 20, M4, 5 << 20, 6 << 20, M8, 12 << 20, M16, 24 << 20, 32 << 20]

    def make(root, sessions, cost, bad=(), old_cyc=2.671):
        for ses in sessions:
            zs = Folder(root, "bwx11", "ZS", ses)
            for cpu in (2, 41):
                for i, size in enumerate(sizes):
                    r = min(0.95, 0.08 * i)
                    cyc = 2.10 + cost * r + (0.5 if size in bad else 0.0)
                    zs.proc(cpu, "asmread", size, [[70.0] * 20], events=ev,
                            counts=lambda ti, w, rr, cyc=cyc, r=r: [cyc, 0.3, r, r, 3.3, 0.0005])
                    zs.proc(cpu, "oldread", size, [[67.0] * 20], events=ev,
                            counts=lambda ti, w, rr, r=r: [old_cyc, 0.007, r, r, 3.3, 0.0])
            zs.save()

    root = os.path.join(tmp, "z1")
    make(root, (1, 2), 0.60)
    J, _ = build(root)
    z = J["ZS"]
    c = z["rule"]["cpu2/s1"]
    check("ZS: 0.60 cycles per L2 refill lies inside the band at all 11 counted sizes", c["outside"] == 0 and
          c["evaluated"] == 11 and c["exceeds"] is False, c)
    check("ZS: least-squares line gives slope 0.60 and intercept 2.10", close(c["slope"], 0.60, 1e-3) and
          close(c["intercept"], 2.10, 1e-3), (c["slope"], c["intercept"]))
    check("ZS: old read within 0.02 of 2.671 at every size with r below 0.83", c["oldread_fails"] == 0 and
          c["oldread_checked"] == 11, (c["oldread_fails"], c["oldread_checked"]))
    check("ZS overall: not contradicted", z["overall"].startswith("H1c in its simple form is not contradicted"),
          z["overall"])
    row = [r for r in z["rows"] if r["kernel"] == "asmread" and r["size"] == "8M" and r["cpu"] == 41 and
           r["session"] == 2][0]
    check("ZS row: band at r = 0.64 is 2.37 to 2.5916", close(row["band_low"], 2.10 + 0.5 * 0.64 - 0.05, 1e-3) and
          close(row["band_high"], 2.10 + 0.69 * 0.64 + 0.05, 1e-3) and row["inside"] is True, row)

    root = os.path.join(tmp, "z2")
    make(root, (1, 2), 0.60, bad=(2 << 20, 3 << 20, M4), old_cyc=2.70)
    J, _ = build(root)
    z = J["ZS"]
    check("ZS: 3 sizes outside on both CPUs in both sessions contradict H1c",
          all(v["outside"] == 3 and v["exceeds"] for v in z["rule"].values()) and
          z["overall"].startswith("H1c in its simple form is contradicted"), z["overall"])
    check("ZS: old read at 2.70 cycles fails the old read check", z["rule"]["cpu2/s1"]["oldread_fails"] == 11)

    root = os.path.join(tmp, "z3")
    make(root, (1, 2), 0.60, bad=(2 << 20, M1, M8))
    J, _ = build(root)
    z = J["ZS"]
    check("ZS: sizes 1 and 8 MiB outside are not counted (1 of 11 outside)",
          all(v["outside"] == 1 and not v["exceeds"] for v in z["rule"].values()) and
          z["overall"].startswith("H1c in its simple form is not contradicted"), z["overall"])

    root = os.path.join(tmp, "z4")
    make(root, (1,), 0.90)
    J, _ = build(root)
    z = J["ZS"]
    check("ZS: 0.90 cycles per refill leaves the band at large r; one session gives no overall verdict",
          z["rule"]["cpu2/s1"]["exceeds"] is True and "session 2 missing" in z["overall"], z["overall"])
    check("zs_band(0.82)", close(F.zs_band(0.82)[0], 2.46, 1e-9) and close(F.zs_band(0.82)[1], 2.7158, 1e-9))


# ---------------------------------------------------------------- item 14: ZM
def test_zm(tmp):
    root = os.path.join(tmp, "m1")
    zm = Folder(root, "bwx11", "ZM", 1)
    base = 0xffff7c000c38
    for cpu in (2, 41):
        for pad in (0, 8, 16):
            # the kick sits at offset 1680 of the pad 0 layout: window (1680 - pad) / 80 only if that is whole
            ups = [21] if pad == 0 else []
            zm.proc(cpu, "asmread", M8, [toggles(60, ups + ([40] if ups else []))], win_ms=100,
                    M={"rec_pad": pad, "win_addr": "%x" % (base + pad), "win_size": 80})
    zm.save()
    J, text = build(root)
    c = J["ZM"]["by_cell"]["cpu2/s1"]
    ups = [e for e in c["events"] if e["event"] == "up"]
    check("ZM: one up at window 21 of the pad 0 process, address win_addr + 80 x 21",
          len(ups) == 1 and ups[0]["index"] == 21 and ups[0]["offset"] == 1680 and
          ups[0]["address"] == "%x" % (base + 1680) and ups[0]["mod64"] == (base + 1680) % 64 and
          ups[0]["mod4096"] == (base + 1680) % 4096, ups)
    falls = [e for e in c["events"] if e["event"] == "fall"]
    check("ZM: one fall at window 40 (offset 3200)", len(falls) == 1 and falls[0]["offset"] == 3200, falls)
    tab = {r[0]: r for r in c["offset_table"]}
    check("ZM: offset table: 1 process with an up at offset 1680, no process without",
          tab[1680][1] == 1 and tab[1680][2] == 0, tab[1680])
    check("ZM: offset 1688 (pad 8, window 21) shows no event (one-level process)", tab[1688][1] == 0 and tab[1688][3] == 0,
          tab[1688])
    check("ZM: offset 2400 of the pad 0 process: level before is high, no fall", tab[2400][4] == 1 and tab[2400][3] == 0,
          tab[2400])
    p = [x for x in J["ZM"]["processes"] if x["pad"] == 0 and x["cpu"] == 2][0]
    b = [x for x in p["boundaries"] if x[0] == 21][0]
    check("ZM: boundary record: index, address, level before, level after, event",
          b[1] == "%x" % (base + 1680) and b[2] == "low" and b[3] == "high" and b[4] == "up" and
          len(p["boundaries"]) == 59, b)
    check("ZM: text lists the event addresses modulo 64, 2048 and 4096", "mod 64" in text and "mod 2048" in text and
          "mod 4096" in text)


def test_switch_window(tmp):
    root = os.path.join(tmp, "sw")
    f = Folder(root, "bwx8", "S4", 1)
    rates = [HIGH] * 16 + [0.5 * (LOW + HIGH)] + [LOW] * 4 + [HIGH] * 20
    f.proc(2, "asmread", M8, [rates])
    # one window of another kernel before the target moves the record index by 1
    f.proc(2, "read", M8, [rates], tag="with-prev")
    f.lines.insert(next(i for i, l in enumerate(f.lines) if l.startswith("W,0,target,0,read")),
                   "W,0,prev,0,oldread,%d,%d,1,900" % (M8, M8))
    f.save()
    procs = F.Data(root).procs("S4", 1)
    d = F.index_switches(procs[0])
    check("switch window: a fall inside window 16 (rate half way) has switch window 16; an up at the boundary "
          "before window 21 has switch window 21", [(x["kind"], x["index"]) for x in d["switches"]] ==
          [("fall", 16), ("up", 21)], d["switches"])
    d = F.index_switches(procs[1])
    check("switch window: it is the record index over all windows of the process (one earlier window adds 1)",
          [(x["kind"], x["index"]) for x in d["switches"]] == [("fall", 17), ("up", 22)], d["switches"])


# ---------------------------------------------------------------- pure rule functions and missing data
def test_rules():
    v = F.onset_verdict([9.1, 9.1, 9.2], [6.1, 6.1, 6.2])
    check("rule 5: first up 6.1 s into the target is 'tied to the start of the target', process start rejected",
          v["verdict"].startswith("tied to the start of the target") and "rejected" in v["verdict"], v)
    v = F.onset_verdict([6.4, 6.5], [3.4, 3.5])
    check("rule 5: first up 6.4 s after process start is 'tied to the process start', target start rejected",
          v["verdict"].startswith("tied to the process start") and "rejected" in v["verdict"], v)
    v = F.onset_verdict([12.0], [9.0])
    check("rule 5: neither fits gives 'other time base'", v["verdict"] == "other time base", v)
    s = F.sampler_verdict({2: {"share_up": 0.9, "share_down": 0.1, "base": 0.1},
                           41: {"share_up": 0.85, "share_down": 0.1, "base": 0.2}}, "k")
    check("rule 4: share 0.9 and 0.85 with base 0.1 and 0.2 accompanies the up switch only", s == {"up": True,
                                                                                                "down": False}, s)
    s = F.sampler_verdict({2: {"share_up": 1.0, "share_down": 1.0, "base": 1.0},
                           41: {"share_up": 1.0, "share_down": 1.0, "base": 1.0}}, "k")
    check("rule 4: a key that always changes (base 1.0) does not accompany", s == {"up": False, "down": False}, s)
    s = F.sampler_verdict({2: {"share_up": 0.9, "share_down": 0.0, "base": 0.1},
                           41: {"share_up": 0.5, "share_down": 0.0, "base": 0.1}}, "k")
    check("rule 4: one CPU alone is not enough", s["up"] is False, s)
    s = F.sampler_verdict({2: {"share_up": 0.9, "share_down": 0.9, "base": 0.1}}, "k")
    check("rule 4: data of a single CPU cannot meet 'on both CPUs'", s == {"up": False, "down": False}, s)

    def h2(share_low, gain_low):
        return {"share_low": share_low, "median_gain_low_pct": gain_low}
    check("H2 rule: 100 % low and gain 0.2 % in both sessions is 'supported'",
          F.h2_verdict({1: h2(1.0, 0.2), 2: h2(0.8, 1.5)}) == "supported")
    check("H2 rule: under 25 % low in both sessions is 'rejected'",
          F.h2_verdict({1: h2(0.0, None), 2: h2(0.2, 0.3)}) == "rejected")
    check("H2 rule: low gain 3 % (more than 1.5 points from 0.94 %) is 'undecided'",
          F.h2_verdict({1: h2(1.0, 3.0), 2: h2(1.0, 0.5)}) == "undecided")
    check("H2 rule: 60 % low in one session (under 75 %) is 'undecided'",
          F.h2_verdict({1: h2(1.0, 0.2), 2: h2(0.6, 0.2)}) == "undecided")
    check("H2 rule: 30 % low in one session (not under 25 %) is not 'rejected'",
          F.h2_verdict({1: h2(0.0, None), 2: h2(0.3, 0.3)}) == "undecided")
    check("H2 rule: one session gives no verdict", "session 2 missing" in F.h2_verdict({1: h2(1.0, 0.2)}))
    r = F.rule1_zd({2: 0.1, 41: 0.1}, {("asmread", 2): 3.5, ("read", 2): 3.5, ("asmread", 41): 0.5, ("read", 41): 3.2},
                   {2: 0.0, 41: 0.1})
    check("rule 1 of round 4: one rise below 1.0 among rises above 3.0 is 'partly'", r["verdict"] == "partly", r)
    r = F.rule1_zd({2: 0.1}, {("asmread", 2): 3.5, ("read", 2): 3.5}, {2: 0.0})
    check("rule 1 of round 4: rises on a single CPU cannot meet 'on both CPUs'",
          r["check"] is True and r["verdict"].startswith("Insufficient data"), r)
    r = F.rule1_zd({2: 0.1, 41: 0.1}, {("asmread", 2): 3.5, ("read", 2): 3.5, ("asmread", 41): 3.5}, {2: 0.0, 41: 0.0})
    check("rule 1 of round 4: a missing 'read' cell on one CPU gives 'Insufficient data', not 'supported'",
          r["verdict"].startswith("Insufficient data"), r)
    r = F.rule1_zd({2: 0.1, 41: 0.1}, {(k, c): 3.5 for k in ("asmread", "read") for c in (2, 41)}, {2: 0.0, 41: 0.0})
    check("rule 1 of round 4: all four rises at least 3.0 with a passed check is 'H1d supported'",
          r["verdict"] == "H1d supported", r)
    def pads(n_match):
        return [{"match": i < n_match, "median_shift": 5.0} for i in range(5)]
    check("rule 2 of round 3: 4 of 5 pads on both CPUs is 'H7 supported'",
          F.yp_verdict({2: pads(5), 41: pads(4)}).startswith("H7 supported"))
    check("rule 2 of round 3: 3 of 5 pads on one CPU is not 'H7 supported'",
          F.yp_verdict({2: pads(5), 41: pads(3)}).startswith("undecided"))
    check("rule 2 of round 3: one CPU alone is not 'H7 supported'", F.yp_verdict({2: pads(5)}).startswith("undecided"))

    def cell(median, p95, p5):
        return {"median": median, "p95": p95, "p5": p5}
    cells = {("asmread", F.K32): cell(132.0, 132.0, 132.0), ("asmread", F.M8): cell(67.5, 71.0, 67.4),
             ("k_near", F.K32): cell(130.0, 130.0, 130.0), ("k_near", F.M8): cell(67.5, 70.2, 67.4),
             ("k_far", F.K32): cell(130.0, 130.0, 130.0), ("k_far", F.M8): cell(67.5, 69.5, 67.4)}
    r = F.rule6_cell(cells, ["asmread", "k_near", "k_far"])["kernels"]
    check("rule 6 part (a): p95 0.8 GB/s below asmread holds, 1.5 GB/s below fails (limit 1.0)",
          r["k_near"]["a"] is True and r["k_far"]["a"] is False and r["asmread"]["a"] is True, r)
    r = F.rule_zn_kernel(70.0, 69.0, 73.0, 67.5, 71.0)
    check("rule 2 of round 4: between kernel with p95 above min(C_k, top of S8) + 1.0 fails",
          r["prediction_holds"] is False, r)


def test_missing(tmp):
    root = os.path.join(tmp, "empty")
    os.makedirs(root)
    J, text = build(root)
    check("empty results folder: build works and reports every step as missing",
          "ZS s2" in text and J["ZS"]["overall"].startswith("no data") and J["YP"]["overall"] == "no data")
    check("empty results folder: every claim names its missing data",
          len(J["claims"]) >= 9 and all(c["missing"] for c in J["claims"]), [c["id"] for c in J["claims"]])
    check("empty results folder: inventory marks S2 session 1 as missing",
          any(r["step"] == "S2" and r["session"] == 1 and r["folder"] is None for r in J["inventory"]["rows"]))
    # inventory counts on a synthetic folder with a killed process and an X row
    root = os.path.join(tmp, "inv")
    f = Folder(root, "bwx8", "S4", 1)
    f.proc(2, "read", M8, [toggles(100, [21, 42])])
    f.proc(2, "read", M8, [[LOW] * 5])
    f.lines.append("-- killed idx 1 utc 01:00:09")
    f.lines.insert(5, "X,-1,madvise,synthetic")
    f.save()
    J, _ = build(root)
    r = [x for x in J["inventory"]["rows"] if x["step"] == "S4" and x["session"] == 1][0]
    check("inventory: 2 processes, 1 killed, 1 X row, load 0.50", r["processes"] == 2 and r["killed"] == 1 and
          r["x_rows"] == 1 and r["load_min"] == 0.5 and r["load_median"] == 0.5 and r["first_launch_utc"] == "01:00:00"
          and r["last_launch_utc"] == "01:00:01", r)
    lv = [x for x in J["levels"]["rows"] if x["step"] == "S4"]
    check("levels: the killed process is left out; the other has low 67.5, high 71.0, share high 0.21",
          len(lv) == 1 and lv[0]["processes"] == 1 and close(lv[0]["low"], LOW, 0.01) and close(lv[0]["high"], HIGH, 0.01)
          and close(lv[0]["share_high"], 0.21, 1e-9), lv)
    sw = J["switch_timing"]["S4"]["s1"]
    check("switch timing: one process alone gives no recurring switch", sw["up_recurring"] == [] and
          len(sw["up_clusters"]) == 1 and sw["up_clusters"][0]["index_median"] == 21, sw["up_clusters"])


def test_cut_file(tmp):
    """A csv file copied while its step ran ends with a process whose last trial has no E row."""
    root = os.path.join(tmp, "cut")
    f = Folder(root, "bwx9", "XN", 1)
    for _ in range(6):
        f.proc(2, "asmread", M8, flat(70.0))
    f.proc(2, "asmread", M8, flat(40.0, trials=2))
    while not f.lines[-1].startswith("E,"):
        f.lines.pop()
    f.lines.pop()                          # the last trial keeps its W rows and loses its E row
    f.save()
    J, text = build(root)
    r = [x for x in J["inventory"]["rows"] if x["step"] == "XN" and x["session"] == 1][0]
    check("cut file: the inventory counts 7 processes and 1 incomplete", r["processes"] == 7 and
          r["incomplete"] == 1 and r["killed"] == 0, r)
    c = [x for x in J["families"]["XN"]["rows"] if x["kernel"] == "asmread" and x["size"] == "8M"][0]
    check("cut file: the incomplete process (40 GB/s) is left out of the cell: 6 processes, median 70.0",
          c["n"] == 6 and close(c["median"], 70.0, 1e-6) and close(c["p5"], 70.0, 1e-6), c)


def test_round1_fallback(tmp):
    """Without the summary file of analyze8.py the round 1 cells are recomputed and say so."""
    root = os.path.join(tmp, "r1")
    f = Folder(root, "bwx8", "S2", 1)
    for rep in range(1, 7):
        M = {"plan.rep_set": rep}
        f.proc(2, "oldread", M8, flat(67.0), M=M)
        f.proc(2, "read", M8, flat(71.0 + 0.01 * rep), M=M)
        f.proc(2, "asmread", M8, flat(70.0), M=M)
    f.save()
    J, text = build(root)
    row = [r for r in J["round1"]["cells"] if r["size"] == "8M" and r["cpu"] == 2][0]
    nm = row["new_minus_old"]
    check("round 1 without summary: cell medians and six set values are recomputed",
          row["source"] == "recomputed with levels9" and close(row["oldread"], 67.0, 1e-6) and
          close(row["asmread"], 70.0, 1e-6) and len(nm["sets"]) == 6 and close(nm["median"], 4.035, 1e-6) and
          close(nm["gain_pct"], 100.0 * 4.035 / 67.0, 1e-6), row)
    check("round 1 without summary: no P1 or P2 verdict is invented", J["round1"]["P1"] is None and
          "not recomputed here" in text and "not evaluated here" in [c for c in J["claims"]
                                                                   if c["id"].startswith("H1 / P1")][0]["overall"])
    cur = [r for r in J["size_curve"]["rows"] if r["kernel"] == "read" and r["size"] == "8M"]
    check("size curve: S2 cell of 6 processes with median 71.035", len(cur) == 1 and cur[0]["n"] == 6 and
          close(cur[0]["median"], 71.035, 1e-6) and cur[0]["step"] == "S2", cur)


# ---------------------------------------------------------------- item 16: supplementary evaluations
def test_supplementary(tmp):
    """The four evaluations that were defined after the data was seen. They must count what they say, and they
    must leave the recorded verdicts of blocks 10 and 11 as they are."""
    U, FALLS = [21, 44, 67, 90, 114], [30, 53, 76, 99, 120]
    check("supplementary: the prediction is every reference window minus pad / 80, cut to the windows 0 to 99",
          F.sup_predicted([21, 44, 67, 90, 114, 137, 179], 4000) == [17, 40, 64, 87] and
          F.sup_predicted([21, 44, 67, 90, 114, 137, 179], 1040) == [8, 31, 54, 77] and
          F.sup_predicted([21, 44], 0) == [21, 44] and F.sup_predicted([16, 42], 2080) == [16])
    check("supplementary: an event matches within 1 window and not at 2 windows",
          F.sup_count_match([20, 45, 69, 88], [21, 44, 67, 90]) == 2 and F.sup_count_match([], [21]) == 0)
    d = {"index": list(range(10)), "labels": ["high"] * 4 + ["mixed"] + ["low"] * 5}
    check("supplementary: the level before window w is that of the last level window up to w - 2",
          F.sup_level_before(d, 5) == "high" and F.sup_level_before(d, 6) == "high" and
          F.sup_level_before(d, 7) == "low" and F.sup_level_before(d, 1) is None and
          F.sup_level_before(d, 5, fixed="low") == "low")
    check("supplementary: a predicted up window counts only if the process is low before it",
          F.sup_eligible(d, [8], [3, 8], "low") == (1, 1) and F.sup_eligible(d, [], [3, 8], "low") == (1, 0) and
          F.sup_eligible(d, [8], [3, 8], "high") == (1, 0))

    def run60(extra=()):
        return [toggles(200, sorted(U + FALLS + list(extra)))]

    def make(root, sessions, shift_of):
        for ses in sessions:
            s4 = Folder(root, "bwx8", "S4", ses)
            for cpu in (2, 41):
                s4.proc(cpu, "read", M8, run60((150, 153) if cpu == 2 and ses == 1 else ()))
                s4.proc(cpu, "asmread", M8, run60())
                s4.proc(cpu, "asmread", M8, run60())
                s4.proc(cpu, "oldread", M8, [[67.0] * 200])
            s4.save()
            yp = Folder(root, "bwx10", "YP", ses)
            for cpu in (2, 41):
                for pad in (0, 400, 1040):
                    k = shift_of(pad)
                    ev = sorted(e - k for e in U + FALLS if 0 < e - k < 100)
                    M = {"rec_pad": pad, "hot_copy": 0, "win_size": 80}
                    yp.proc(cpu, "asmread", M8, [toggles(100, ev)], M=M)
                    if pad == 400:
                        yp.proc(cpu, "asmread", M8, [[LOW] * 100], M=M)                   # stays low: no up
                        yp.proc(cpu, "asmread", M8, [toggles(100, ev[1:], start="high")], M=M)   # high at window 16
                yp.proc(cpu, "asmread", M8, [toggles(100, [5, 9])], M={"rec_pad": 0, "hot_copy": 1, "win_size": 80})
            yp.save()

    root = os.path.join(tmp, "s1")
    make(root, (1, 2), lambda pad: pad // 80)
    J, text = build(root)
    sup = J["supplementary"]["yp_round1"]
    ref = sup["reference"]
    check("supplementary YP: the reference ups are the S4 windows that at least 5 load-only processes share; the up "
          "at window 150 of one process and old read stay out", ref["up"]["series"] == U and
          ref["fall"]["series"] == FALLS and ref["up"]["processes_pooled"] == 12 and
          ref["up"]["same_series_from"] == 2 and ref["up"]["same_series_to"] == 12, ref["up"])
    rows = [r for r in sup["rows"] if r["kind"] == "up" and r["pad"] == 400 and r["cpu"] == 2 and r["session"] == 1]
    check("supplementary YP: pad 400 predicts the up windows 16, 39, 62, 85, and a run moved by 5 windows matches 4 of 4",
          len(rows) == 3 and rows[0]["predicted_windows"] == [16, 39, 62, 85] and rows[0]["events"] == [16, 39, 62, 85]
          and rows[0]["n_events_match"] == 4 and (rows[0]["n_eligible"], rows[0]["n_eligible_hit"]) == (4, 4), rows[:1])
    check("supplementary YP: a run that stays low has 4 predicted windows at the low level and 0 ups there",
          rows[1]["levels"] == "one level, low" and rows[1]["n_events"] == 0 and
          (rows[1]["n_eligible"], rows[1]["n_eligible_hit"]) == (4, 0), rows[1])
    check("supplementary YP: a run that is high at the first predicted window has 3 windows that count, not 4",
          rows[2]["events"] == [39, 62, 85] and rows[2]["n_events_match"] == 3 and
          (rows[2]["n_eligible"], rows[2]["n_eligible_hit"]) == (3, 3), rows[2])
    c = [x for x in sup["cells"] if x["kind"] == "up" and x["pad"] == 400 and x["cpu"] == 2 and x["session"] == 1][0]
    check("supplementary YP: the cell of pad 400 sums its 3 processes: 7 of 7 ups match, 7 of 11 predicted windows hit",
          (c["n_events_match"], c["n_events"], c["n_eligible_hit"], c["n_eligible"]) == (7, 7, 7, 11) and
          close(c["share_events_match_pct"], 100.0, 1e-9) and close(c["share_eligible_hit_pct"], 700.0 / 11, 1e-9), c)
    f = [r for r in sup["rows"] if r["kind"] == "fall" and r["pad"] == 400 and r["cpu"] == 41 and r["session"] == 2]
    check("supplementary YP: the falls use their own reference (30 - 5 = 25 ...) and need the high level before",
          f[0]["predicted_windows"] == [25, 48, 71, 94] and f[0]["n_events_match"] == 4 and
          (f[0]["n_eligible"], f[0]["n_eligible_hit"]) == (4, 4) and f[1]["n_eligible"] == 0, f[:2])
    s = [x for x in sup["summary"] if x["kind"] == "up" and x["group"] == "padded" and x["session"] == 1][0]
    check("supplementary YP: session summary of the padded runs: 22 of 22 ups match, 22 of 30 predicted windows hit",
          (s["n_events_match"], s["n_events"], s["n_eligible_hit"], s["n_eligible"]) == (22, 22, 22, 30), s)
    check("supplementary YP: the hot-copy runs are not part of the evaluation",
          len([r for r in sup["rows"] if r["kind"] == "up"]) == 20, len(sup["rows"]))
    check("supplementary YP: with two sessions the overall line says 'both sessions' and counts 44 of 44 ups",
          "both sessions: 44 of 44 ups" in sup["summary_text"]["up"]["overall"], sup["summary_text"]["up"])
    check("supplementary YP: the recorded verdict of rule 2 is printed beside it and is not changed",
          sup["recorded_verdict"] == J["YP"]["overall"] and sup["label"] == F.SUP_LABEL and
          ("16.1 YP against the round 1 series (%s)" % F.SUP_LABEL) in text and
          ("(block 10, unchanged): %s." % J["YP"]["overall"]) in text)

    root = os.path.join(tmp, "s2")
    make(root, (1,), lambda pad: 0)
    J, _ = build(root)
    sup = J["supplementary"]["yp_round1"]
    r = [x for x in sup["rows"] if x["kind"] == "up" and x["pad"] == 1040 and x["cpu"] == 2][0]
    check("supplementary YP: runs that keep their windows do not match the prediction for pad 1040 (0 of 4 ups; the "
          "run is low before 1 predicted window, and no up is there)", r["predicted_windows"] == [8, 31, 54, 77] and
          r["events"] == [21, 44, 67, 90] and r["n_events_match"] == 0 and r["n_eligible"] == 1 and
          r["n_eligible_hit"] == 0, r)
    s = [x for x in sup["summary"] if x["kind"] == "fall" and x["group"] == "padded" and x["session"] == 1][0]
    check("supplementary YP: the same holds for the falls (share 0 %)", s["n_events"] > 0 and s["n_events_match"] == 0
          and s["share_events_match_pct"] == 0.0, s)
    check("supplementary YP: one session gives 'session 2 missing' in the overall line",
          "session 2 missing" in sup["summary_text"]["up"]["overall"] and "s2" not in sup["summary_text"]["up"],
          sup["summary_text"]["up"])

    # items 2, 3 and 4: rates and counts
    ev = list(F.YC_EVENTS)

    def make_rates(root, sessions, sparse32=133.4, pf1=77.4, nop8=54.9, with_yf=True, pf32=None):
        for ses in sessions:
            s2 = Folder(root, "bwx8", "S2", ses)
            xn = Folder(root, "bwx9", "XN", ses)
            zn = Folder(root, "bwx11", "ZN", ses)
            yf = Folder(root, "bwx10", "YF", ses) if with_yf else None
            yc = Folder(root, "bwx10", "YC", ses)
            zd = Folder(root, "bwx11", "ZD", ses)
            for cpu in (2, 41):
                for rep in range(1, 7):
                    M = {"plan.rep_set": rep}
                    for size, rate in ((K32, 66.7), (M1, 67.1), (M8, 67.0)):
                        s2.proc(cpu, "oldread", size, flat(rate), M=M)
                    s2.proc(cpu, "read", M8, two_level(), M=M)
                    s2.proc(cpu, "asmread", M8, two_level(), M=M)
                    for size, rate in ((K32, sparse32), (M1, 85.4)):
                        xn.proc(cpu, "read_sparse", size, flat(rate), M=M)
                    xn.proc(cpu, "read_sparse", M8, two_level(), M=M)
                    xn.proc(cpu, "asmread", M8, two_level(), M=M)
                    zn.proc(cpu, "read_nop96", K32, flat(55.0), M=M)
                    zn.proc(cpu, "read_nop96", M8, flat(nop8), M=M)
                    if yf:
                        yf.proc(cpu, "asmread", M1, flat(85.2), M=M)
                        yf.proc(cpu, "asmread", M8, two_level(), M=M)
                        yf.proc(cpu, "read_pf1024", M1, flat(pf1), M=M)
                        yf.proc(cpu, "read_pf1024", M8, flat(66.0), M=M)
                        if pf32 is not None:
                            yf.proc(cpu, "asmread", K32, flat(132.4), M=M)
                            yf.proc(cpu, "read_pf1024", K32, flat(pf32), M=M)
                    zd.proc(cpu, "asmread", M8, [[69.0] * 8, [72.0] * 8, [69.0] * 8, [69.0] * 8], M=M)
                    zd.proc(cpu, "asmread", M8, flat(80.0), M=dict(M, evict_mb=512))
                for size, am, pm in ((M1, 0.30, 0.006), (M8, 0.36, 0.27)):
                    yc.proc(cpu, "asmread", size, [[LOW] * 20], events=ev,
                            counts=lambda ti, w, r, am=am: [2.6, 2.75, am, 0.82, am, 0.0005])
                    yc.proc(cpu, "read_pf1024", size, [[66.0] * 20], events=ev,
                            counts=lambda ti, w, r, pm=pm: [2.7, 3.75, pm, 0.82, pm, 0.0006])
            for f in (s2, xn, zn, yc, zd) + ((yf,) if yf else ()):
                f.save()

    root = os.path.join(tmp, "s3")
    make_rates(root, (1, 2))
    J, text = build(root)
    S = J["supplementary"]
    r = [x for x in S["old_without_adds"]["rows"] if x["size"] == "32K" and x["cpu"] == 41 and x["session"] == 2][0]
    check("supplementary old read: read_sparse 133.4 over old read 66.7 at 32 KiB is the ratio 2.000",
          close(r["oldread"], 66.7, 1e-6) and close(r["read_sparse"], 133.4, 1e-6) and close(r["ratio"], 2.0, 1e-6) and
          close(r["difference"], 66.7, 1e-6), r)
    r = [x for x in S["old_without_adds"]["rows"] if x["size"] == "8M" and x["cpu"] == 2 and x["session"] == 1][0]
    check("supplementary old read: at 8 MiB the ratio uses the cell medians (67.5 over 67.0)",
          close(r["ratio"], LOW / 67.0, 1e-6) and len(S["old_without_adds"]["rows"]) == 12, r)
    s = [x for x in S["old_without_adds"]["summary"] if x["size"] == "32K"][0]
    check("supplementary old read: the 32 KiB summary spans 4 cells", s["cells"] == 4 and
          close(s["ratio_min"], 2.0, 1e-6) and close(s["ratio_max"], 2.0, 1e-6), s)
    P = S["prefetch_1M"]
    r = [x for x in P["rows"] if x["size"] == "1M" and x["cpu"] == 2 and x["session"] == 1][0]
    check("supplementary prefetch: at 1 MiB the kernel keeps 0.006 / 0.30 of the misses (98 % removed) and is 7.8 GB/s "
          "lower", close(r["share_kept"], 0.02, 1e-3) and close(r["removed_pct"], 98.0, 0.1) and
          close(r["difference"], 77.4 - 85.2, 1e-6), r)
    r = [x for x in P["rows"] if x["size"] == "8M" and x["cpu"] == 41 and x["session"] == 2][0]
    check("supplementary prefetch: at 8 MiB the kernel keeps 0.27 / 0.36 of the misses and is 1.5 GB/s lower",
          close(r["share_kept"], 0.75, 1e-3) and close(r["difference"], 66.0 - LOW, 1e-6), r)
    s = [x for x in P["summary"] if x["size"] == "1M"][0]
    check("supplementary prefetch: the 1 MiB line says 'lower in all 4 cells' with both sessions",
          s["cells"] == 4 and s["cells_lower"] == 4 and s["not_lower"] == [] and
          "at 1 MiB (both sessions) the prefetch removes 98.0 to 98.0 %" in P["summary_text"]["1M"] and
          "7.80 to 7.80 GB/s lower than asmread in all 4 cells" in P["summary_text"]["1M"], P["summary_text"])
    check("supplementary prefetch: the recorded verdict of rule 3 is printed beside it and is not changed",
          P["recorded_verdict"] == J["prefetch"]["overall"] and
          ("(block 11, unchanged): %s." % J["prefetch"]["overall"]) in text)
    G = S["gain_from_two_rates"]
    r = [x for x in G["rows"] if x["kernel"] == "read_nop96" and x["cpu"] == 2 and x["session"] == 1][0]
    check("supplementary gain: C_k 55.0 and the asmread levels 67.5 and 71.0 (step YF) predict 22.73 to 29.09 %",
          r["asmread_step"] == "YF" and close(r["C"], 55.0, 1e-6) and close(r["asmread_low"], LOW, 0.01) and
          close(r["asmread_high"], HIGH, 0.01) and close(r["predicted_low_pct"], 100 * (LOW / 55.0 - 1), 0.02) and
          close(r["predicted_high_pct"], 100 * (HIGH / 55.0 - 1), 0.02), r)
    check("supplementary gain: the measured gain 67.5 / 54.9 - 1 = 22.95 % lies inside the range",
          close(r["measured_pct"], 100 * (LOW / 54.9 - 1), 1e-6) and r["inside"] is True, r)
    r = [x for x in G["rows"] if x["kernel"] == "oldread" and x["cpu"] == 41 and x["session"] == 2][0]
    check("supplementary gain: old read (C_k 66.7, 67.0 at 8 MiB) gives 0.75 %, below the range from 1.20 %: outside",
          close(r["measured_pct"], 100 * (LOW / 67.0 - 1), 1e-6) and close(r["predicted_low_pct"], 100 * (LOW / 66.7 - 1),
                                                                         0.02) and r["inside"] is False, r)
    check("supplementary gain: the summary counts 4 of 8 cells inside and names the cells outside",
          G["cells"] == 8 and G["cells_inside"] == 4 and len(G["outside"]) == 4 and G["missing"] ==
          ["read_nop128 session 1", "read_nop128 session 2"] and "in 4 of 8 cells" in G["summary_text"], G["summary_text"])

    root = os.path.join(tmp, "s4")
    make_rates(root, (1,), sparse32=66.7, pf1=86.0, nop8=45.0, with_yf=False)
    J, _ = build(root)
    S = J["supplementary"]
    r = [x for x in S["old_without_adds"]["rows"] if x["size"] == "32K" and x["cpu"] == 2][0]
    check("supplementary old read: a read_sparse that is as slow as old read gives the ratio 1.000",
          close(r["ratio"], 1.0, 1e-6), r)
    check("supplementary prefetch: without step YF there is no rate, and the line says 'Insufficient data'",
          S["prefetch_1M"]["summary"] == [] and "Insufficient data" in S["prefetch_1M"]["summary_text"]["1M"] and
          all(x["difference"] is None for x in S["prefetch_1M"]["rows"]), S["prefetch_1M"]["summary_text"])
    r = [x for x in S["gain_from_two_rates"]["rows"] if x["kernel"] == "read_nop96" and x["cpu"] == 2][0]
    check("supplementary gain: without YF the asmread levels come from ZD without evict (69.0 and 72.0)",
          r["asmread_step"] == "ZD" and close(r["asmread_low"], 69.0, 0.01) and close(r["asmread_high"], 72.0, 0.01), r)
    check("supplementary gain: a slow kernel that loses rate at 8 MiB (45.0) has a measured gain outside the range",
          close(r["measured_pct"], 100 * (69.0 / 45.0 - 1), 1e-6) and r["inside"] is False, r)

    root = os.path.join(tmp, "s5")
    make_rates(root, (1, 2), pf1=86.0)
    J, _ = build(root)
    P = J["supplementary"]["prefetch_1M"]
    s = [x for x in P["summary"] if x["size"] == "1M"][0]
    check("supplementary prefetch: a prefetch kernel that is faster at 1 MiB is named as a cell that disagrees",
          s["cells_lower"] == 0 and len(s["not_lower"]) == 4 and "cells that disagree" in P["summary_text"]["1M"] and
          "lower than asmread in 0 of 4 cells" in P["summary_text"]["1M"], P["summary_text"]["1M"])

    check("supplementary prefetch: without 32 KiB cells in step YF there is no 32 KiB line",
          "at_32K" not in P and "32K" not in P["summary_text"], P["summary_text"])
    root = os.path.join(tmp, "s5b")
    make_rates(root, (1, 2), pf32=102.4)
    J, text = build(root)
    P = J["supplementary"]["prefetch_1M"]
    check("supplementary prefetch: at 32 KiB a prefetch kernel at 102.4 against asmread at 132.4 is 30.00 GB/s lower "
          "in 4 of 4 cells", P["at_32K"]["cells"] == 4 and P["at_32K"]["cells_lower"] == 4 and
          close(P["at_32K"]["difference_min"], -30.0, 1e-6) and close(P["at_32K"]["lower_by_max"], 30.0, 1e-6) and
          "is -30.00 to -30.00 GB/s, and it is below 0 in 4 of 4 cells" in P["summary_text"]["32K"] and
          P["summary_text"]["32K"] in text, P.get("summary_text"))
    root = os.path.join(tmp, "s5c")
    make_rates(root, (1,), pf32=140.0)
    P = build(root)[0]["supplementary"]["prefetch_1M"]
    check("supplementary prefetch: a prefetch kernel that is faster at 32 KiB counts as 0 of 2 cells lower, one session",
          P["at_32K"]["cells"] == 2 and P["at_32K"]["cells_lower"] == 0 and P["at_32K"]["lower_by_min"] is None and
          close(P["at_32K"]["difference_max"], 7.6, 1e-6) and "below 0 in 0 of 2 cells" in P["summary_text"]["32K"] and
          "session 2 missing" in P["summary_text"]["32K"], P.get("summary_text"))

    root = os.path.join(tmp, "s6")
    os.makedirs(root)
    J, text = build(root)
    S = J["supplementary"]
    check("supplementary: an empty results folder gives empty tables and 'no data' lines, not a crash",
          S["yp_round1"]["rows"] == [] and S["yp_round1"]["reference"]["up"]["series"] == [] and
          S["yp_round1"]["summary_text"]["up"]["overall"].startswith("no data") and
          S["old_without_adds"]["rows"] == [] and S["prefetch_1M"]["rows"] == [] and
          S["gain_from_two_rates"]["summary_text"] == "no data" and "16. SUPPLEMENTARY EVALUATIONS" in text)


# ---------------------------------------------------------------- smoke test on the real folders
def test_real(tmp):
    if not os.path.isdir(F.RESULTS) or not F.Data(F.RESULTS).folders:
        print("NOTE  no real result folder under %s: smoke test not run" % F.RESULTS)
        return
    out = os.path.join(tmp, "real")
    os.makedirs(out)
    r = subprocess.run([sys.executable, os.path.join(A, "final8.py"), "--out-dir", out], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    check("real: final8.py ends with status 0", r.returncode == 0, r.stderr[-400:])
    if r.returncode != 0:
        return
    with open(os.path.join(out, "final8.json")) as f:
        J = json.load(f)
    with open(os.path.join(out, "final8.txt")) as f:
        text = f.read()
    check("real: final8.json loads and has the 15 blocks", all(k in J for k in (
        "inventory", "round1", "size_curve", "levels", "switch_timing", "counters", "families", "H2", "YL", "YP",
        "prefetch", "evict", "ZS", "ZM", "claims", "readings")))
    check("real: final8.json has the supplementary block with its label and its four parts", all(
        k in J.get("supplementary", {}) for k in ("yp_round1", "old_without_adds", "prefetch_1M", "gain_from_two_rates"))
        and J["supplementary"]["label"] == F.SUP_LABEL and ("\n16. SUPPLEMENTARY EVALUATIONS (%s)" % F.SUP_LABEL) in text)
    check("real: final8.txt has one block per item", all(("\n%d. " % i) in text for i in range(2, 16)) and
          text.count("reading:") >= 10)
    have = J["folders"]
    if "XN/s1" in have:
        rows = [x for x in J["families"]["XN"]["rows"] if x["kernel"] == "asmread" and x["size"] == "1M" and
                x["session"] == 1]
        check("real: XN session 1, asmread 1 MiB cell median is 85.24 GB/s on CPU 2 and CPU 41",
              sorted(x["cpu"] for x in rows) == [2, 41] and all(close(x["median"], 85.24, 0.005) for x in rows), rows)
    else:
        print("NOTE  XN session 1 missing: check not run")
    if "XCB/s1" in have:
        rows = [x for x in J["counters"]["rows"] if x["step"] == "XCB" and x["event"] == "l1d_cache_lmiss_rd" and
                x["kernel"] == "asmread" and x["size"] == "8M" and x["cpu"] == 2 and x["session"] == 1]
        check("real: XCB session 1, l1d_cache_lmiss_rd of asmread 8 MiB at the low level on CPU 2 is about 0.37",
              len(rows) == 1 and close(rows[0]["low"], 0.37, 0.01), rows)
    else:
        print("NOTE  XCB session 1 missing: check not run")
    if "YP/s1" in have:
        rows = [x for x in J["YP"]["shift"] if x["pad"] == 400 and x["session"] == 1]
        check("real: YP session 1, pad 400 shifts the up series by 5 windows on both CPUs",
              sorted(x["cpu"] for x in rows) == [2, 41] and all(x["median_shift"] == 5 and x["match"] for x in rows),
              rows)
    else:
        print("NOTE  YP session 1 missing: check not run")
    if "S2/s1" in have:
        inv = [x for x in J["inventory"]["rows"] if x["step"] == "S2" and x["session"] == 1]
        check("real: inventory, S2 session 1 has 180 processes", inv and inv[0]["processes"] == 180, inv)
        rows = [x for x in J["round1"]["cells"] if x["size"] == "8M" and x["cpu"] == 2 and x["session"] == 1]
        check("real: round 1, new minus old at 8 MiB on CPU 2 in session 1 is +3.91 GB/s (gain 5.83 %)",
              len(rows) == 1 and close(rows[0]["new_minus_old"]["median"], 3.91, 0.005) and
              close(rows[0]["new_minus_old"]["gain_pct"], 5.83, 0.005) and len(rows[0]["new_minus_old"]["sets"]) == 6,
              rows)
    if "ZC/s1" in have:
        check("real: ZC session 1, the evict check fails (write-backs about 0.82), verdict 'Insufficient data'",
              J["evict"]["rule1"]["s1"]["check"] is False and
              J["evict"]["rule1"]["s1"]["verdict"].startswith("Insufficient data"), J["evict"]["rule1"]["s1"])
    S = J.get("supplementary", {})
    if "S4/s1" in have and "S4/s2" in have:
        ref = S["yp_round1"]["reference"]
        check("real: supplementary, the round 1 reference ups are 21, 44, 67, 90, 114, 137, 179 and the falls are "
              "16, 42, 69, 95, 122, 148, 168, 194", ref["up"]["series"] == [21, 44, 67, 90, 114, 137, 179] and
              ref["fall"]["series"] == [16, 42, 69, 95, 122, 148, 168, 194], ref)
        if "YP/s1" in have:
            rows = [x for x in S["yp_round1"]["rows"] if x["kind"] == "up" and x["pad"] == 4000 and x["session"] == 1
                    and x["cpu"] == 2]
            check("real: supplementary, YP session 1, pad 4000 on CPU 2: both processes have their 4 ups at the "
                  "predicted windows 17, 40, 64, 87", len(rows) == 2 and all(
                      x["predicted_windows"] == [17, 40, 64, 87] and x["n_events_match"] == 4 and x["n_events"] == 4
                      for x in rows), rows)
    else:
        print("NOTE  S4 session 1 or 2 missing: supplementary reference check not run")
    if "S2/s1" in have and "XN/s1" in have:
        rows = [x for x in S["old_without_adds"]["rows"] if x["size"] == "32K" and x["session"] == 1]
        check("real: supplementary, read_sparse is 1.99 to 2.00 times old read at 32 KiB in session 1 on both CPUs",
              sorted(x["cpu"] for x in rows) == [2, 41] and all(1.99 <= x["ratio"] <= 2.00 for x in rows), rows)
    if "YC/s1" in have and "YF/s1" in have:
        rows = [x for x in S["prefetch_1M"]["rows"] if x["size"] == "1M" and x["session"] == 1]
        check("real: supplementary, session 1 at 1 MiB: 8 prefetch cells remove 94 to 99.5 % of the misses and are "
              "7.7 to 7.9 GB/s lower", len(rows) == 8 and all(94.0 <= x["removed_pct"] <= 99.5 and
                                                               -7.9 <= x["difference"] <= -7.7 for x in rows), rows)
    if "ZN/s1" in have and "YF/s1" in have:
        rows = [x for x in S["gain_from_two_rates"]["rows"] if x["kernel"] == "read_nop128" and x["session"] == 1
                and x["cpu"] == 2]
        check("real: supplementary, read_nop128 on CPU 2 in session 1: measured gain 57.94 % inside 56.77 to 65.55 %",
              len(rows) == 1 and close(rows[0]["measured_pct"], 57.94, 0.005) and
              close(rows[0]["predicted_low_pct"], 56.77, 0.005) and close(rows[0]["predicted_high_pct"], 65.55, 0.005)
              and rows[0]["inside"] is True, rows)
    if "H2/s1" in have:
        rows = [x for x in J["H2"]["rows"] if x["cpu"] == "2" and x["session"] == 1]
        check("real: H2 session 1, CPU 2 has 36 of 36 new-read repetitions low", rows and rows[0]["low"] == 36 and
              rows[0]["new_repetitions"] == 36, rows)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    base = argv[argv.index("--tmp") + 1] if "--tmp" in argv else None
    tmp = tempfile.mkdtemp(prefix="test_final8_", dir=base)
    try:
        test_rules()
        test_counters(tmp)
        test_families(tmp)
        test_yl(tmp)
        test_yp(tmp)
        test_prefetch(tmp)
        test_evict(tmp)
        test_zs(tmp)
        test_zm(tmp)
        test_switch_window(tmp)
        test_missing(tmp)
        test_cut_file(tmp)
        test_round1_fallback(tmp)
        test_supplementary(tmp)
        test_real(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d checks, %d failed" % (NCHECK[0], len(FAILS)))
    for f in FAILS:
        print("FAILED: " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
