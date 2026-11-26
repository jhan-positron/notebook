#!/usr/bin/env python3
"""schedule10.py - schedules and plan files of round 3 (steps YA YL YP YF YC).

Usage: schedule10.py [--seed N] [--test-divisor N] [--out DIR]

It writes, for session 1 and 2 and for each step:
  DIR/s<session>/<STEP>.tsv        one row per process (idx, tag, cpu, bytes, plan, args)
  DIR/s<session>/<STEP>/NNNN.plan  one plan file per process (plan format v1 of bwx8 and bwx10)
  DIR/s<session>/<STEP>.bin        one word, bwx8 or bwx10: the binary that run_bwx10.sh starts for the step
  DIR/MANIFEST.txt                 base seed, test divisor, the seed and the binary of each step and session
DIR is "sched10" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.
No step of round 3 runs with the host sampler, so no .watch file is written.
The step YA exists in session 1 only.
--test-divisor N divides every duration by N and marks the plans test=1 (local chain tests only).
N must divide 100 ms, the shortest window of round 3.
The same options give the same bytes. Exit status 1 if a balance check fails.
This file needs no other file of round 1 or 2: the parts taken from schedule8.py and schedule9.py are copied here.

Steps (CPUs 2 and 41; session 2 uses the reversed CPU order; one process at a time):
  YL   window length (bwx8): one trial of 30 s per process, count closed. Kernels asmread and read at 8M.
       Window plans: L100 = 300 windows of 100 ms, L300 = 100 of 300 ms, L1000 = 30 of 1000 ms (bins 0),
       L30000 = 1 window of 30000 ms with 10 ms bins (bins 1). 2 processes per kernel, plan and CPU.
       Order: replicate, then CPU, then the 8 conditions shuffled.
  YP   record pad (bwx10): asmread at 8M, one trial of 100 windows of 300 ms, count closed. Conditions:
       "--rec-pad P" with P = 0, 80, 400, 1040, 2080, 4000, and "--hot-copy" (label hot, pad left at 0).
       2 processes per condition and CPU. Order: replicate, then CPU, then the 7 conditions shuffled.
  YF   software prefetch family (bwx10): trials as step S2 of schedule8.py (4 trials per process:
       prefix K@S 1200 ms, target K@S 4 x 300 ms). 6 kernels, 4 sizes, 6 replicate sets per size and CPU.
       Order: replicate set, then size (shuffled), then CPU, then the 6 kernels. Per size and CPU the
       kernel orders of the 6 sets form a Williams square (defined at williams_square below).
  YC   prefetch family counters (bwx10): one trial, 20 windows of 300 ms, count read, the event set in the
       args column. 7 kernels at 3 sizes, 1 process per cell and CPU. Order: CPU, then the 21 cells shuffled.
  YA   acceptance of bwx10: CPU 2 only, 9 short processes with --trace, in a fixed order.
"""
import argparse
import hashlib
import os
import random
import shutil
import sys

STEPS = ["YA", "YL", "YP", "YF", "YC"]
BINARY = {"YA": "bwx10", "YL": "bwx8", "YP": "bwx10", "YF": "bwx10", "YC": "bwx10"}
CPUS = {1: [2, 41], 2: [41, 2]}                    # session 2 uses the reversed order
PMU_TYPE = 11                                      # armv8_pmuv3_0 on CRB (DECISIONS-bwx8.md)
YC_EVENTS = ("cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,"
             "l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009")
YL_KERNELS = ["asmread", "read"]
# name, windows, window length in ms, bins
YL_PLANS = [("L100", 300, 100, 0), ("L300", 100, 300, 0), ("L1000", 30, 1000, 0), ("L30000", 1, 30000, 1)]
# name, the options added to the command line
YP_CONDS = [("P%d" % p, " --rec-pad %d" % p) for p in (0, 80, 400, 1040, 2080, 4000)] + [("hot", " --hot-copy")]
YF_KERNELS = ["asmread", "read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]
YF_SIZES = ["32K", "1M", "8M", "16M"]
YC_KERNELS = YF_KERNELS + ["oldread"]
YC_SIZES = ["1M", "8M", "16M"]
# name, kernel, size, the options added after --trace
YA_PROCS = [("plain", "asmread", "8M", ""), ("pad80", "asmread", "8M", " --rec-pad 80"),
            ("hot", "asmread", "8M", " --hot-copy"), ("pf256", "read_pf256", "8M", ""),
            ("pf512", "read_pf512", "8M", ""), ("pf1024", "read_pf1024", "8M", ""),
            ("pf2048", "read_pf2048", "8M", ""), ("1pl", "read_1pl", "8M", ""),
            ("pf1024s", "read_pf1024", "32K", "")]
UNITS = 6                                          # replicate sets per size and CPU in YF
MIN_WIN_MS = 100                                   # the shortest window of round 3


def size_bytes(tok):
    mult = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    if tok and tok[-1] in mult:
        return int(tok[:-1]) * mult[tok[-1]]
    return int(tok)


def step_seed(base, step, session):
    h = hashlib.sha256(("%d/%s/%d" % (base, step, session)).encode()).hexdigest()
    return int(h[:8], 16)


def williams_ok(orders, n):
    """orders: n orders of the items 0..n-1. True if every item is once at every position and
    every ordered pair of different items is once a pair of neighbours."""
    pos = {(o[i], i) for o in orders for i in range(n)}
    pairs = [(o[i], o[i + 1]) for o in orders for i in range(n - 1)]
    return (len(orders) == n and all(sorted(o) == list(range(n)) for o in orders)
            and len(pos) == n * n and len(set(pairs)) == len(pairs) == n * (n - 1))


class Gen:
    """Builds the processes of one round 3 step and session."""

    def __init__(self, step, session, base, div):
        self.step, self.session, self.div = step, session, div
        self.seed = step_seed(base, step, session)
        self.rng = random.Random(self.seed)
        self.cpus = CPUS[session]
        self.procs = []

    def ms(self, v):
        return v // self.div

    def trial(self, cond, pfx, tgt, nwin, win_ms, count="closed", bins=0):
        # (cond, prev, pfx, pred, tgt, nwin, win_ms, count, bins); pfx: None or the ms of a prefix of the target.
        return (cond, "-", "%s:%d" % (tgt, self.ms(pfx)) if pfx else "-", "-", tgt, nwin, self.ms(win_ms), count, bins)

    def add(self, tag, cpu, size, keys, trials, extra=""):
        self.procs.append({"tag": tag, "cpu": cpu, "bytes": size_bytes(size), "keys": keys,
                           "trials": trials, "extra": extra})

    def williams_square(self, n):
        # A Williams square for an even n: n orders of n items in which every item takes every position
        # once, and every ordered pair of different items is once a pair of neighbours. Built from the
        # start order 0, 1, n-1, 2, n-2, ... shifted by 0 to n-1, with random item labels and row order.
        start, lo, hi = [0], 1, n - 1
        while lo <= hi:
            start.append(lo)
            if lo != hi:
                start.append(hi)
            lo, hi = lo + 1, hi - 1
        label = list(range(n))
        self.rng.shuffle(label)
        rows = [[label[(x + r) % n] for x in start] for r in range(n)]
        self.rng.shuffle(rows)
        return rows

    # ---- steps ----
    def YL(self):
        conds = [(k, p) for k in YL_KERNELS for p in YL_PLANS]
        for r in (1, 2):
            for cpu in self.cpus:
                block = list(conds)
                self.rng.shuffle(block)
                for k, (name, nwin, win_ms, bins) in block:
                    t = [self.trial("K=%s|S=8M|L=%d" % (k, win_ms), None, k + "@8M", nwin, win_ms, "closed", bins)]
                    self.add("%s-%s-cpu%d-p%d" % (name, k, cpu, r), cpu, "8M",
                             [("rep_set", r), ("kernel", k), ("size", size_bytes("8M")), ("lcond", name)], t)

    def YP(self):
        for r in (1, 2):
            for cpu in self.cpus:
                block = list(YP_CONDS)
                self.rng.shuffle(block)
                for name, extra in block:
                    t = [self.trial("K=asmread|S=8M|rec=%s" % name, None, "asmread@8M", 100, 300)]
                    self.add("%s-cpu%d-p%d" % (name, cpu, r), cpu, "8M",
                             [("rep_set", r), ("kernel", "asmread"), ("size", size_bytes("8M")), ("pcond", name)],
                             t, extra)

    def YF(self):
        order = {}
        for s in YF_SIZES:
            for cpu in self.cpus:
                order[s, cpu] = self.williams_square(len(YF_KERNELS))
        for r in range(UNITS):
            sizes = list(YF_SIZES)
            self.rng.shuffle(sizes)
            for s in sizes:
                for cpu in self.cpus:
                    for ki in order[s, cpu][r]:
                        k = YF_KERNELS[ki]
                        ks = "%s@%s" % (k, s)
                        t = [self.trial("K=%s|S=%s" % (k, s), 1200, ks, 4, 300)] * 4
                        self.add("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, s,
                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)

    def YC(self):
        extra = " --pmu-type %d --events %s" % (PMU_TYPE, YC_EVENTS)
        for cpu in self.cpus:
            cells = [(k, s) for k in YC_KERNELS for s in YC_SIZES]
            self.rng.shuffle(cells)
            for k, s in cells:
                t = [self.trial("K=%s|S=%s|count=read" % (k, s), None, "%s@%s" % (k, s), 20, 300, "read")]
                self.add("%s-%s-cpu%d" % (k, s, cpu), cpu, s,
                         [("rep_set", 1), ("kernel", k), ("size", size_bytes(s))], t, extra)

    def YA(self):
        for name, k, s, opts in YA_PROCS:
            ks = "%s@%s" % (k, s)
            t = [self.trial("K=%s|S=%s|acc=%s" % (k, s, name), 400, ks, 3, 300)]
            self.add("%s-cpu2" % name, 2, s,
                     [("kernel", k), ("size", size_bytes(s)), ("acond", name)], t, " --trace" + opts)


def generate(base, div):
    """Returns {(step, session): Gen}. YA only in session 1."""
    out = {}
    for session in (1, 2):
        for step in STEPS:
            if step == "YA" and session == 2:
                continue
            g = Gen(step, session, base, div)
            getattr(g, step)()
            out[step, session] = g
    return out


def plan_text(g, idx, p):
    pairs = [("step", g.step), ("session", g.session), ("cpu", p["cpu"]),
             ("bytes", p["bytes"]), ("proc", idx)] + p["keys"] + \
            [("seed", g.seed), ("test", 0 if g.div == 1 else 1)]
    lines = ["# bwx8-plan v1",
             "# " + " ".join("%s=%s" % kv for kv in pairs),
             "# trial cond rep prev pfx pred tgt nwin win_ms count bins"]
    seen = {}
    for n, t in enumerate(p["trials"]):
        seen[t[0]] = seen.get(t[0], 0) + 1      # rep: repeat number of this cond
        lines.append("%d %s %d %s %s %s %s %d %d %s %d" % ((n, t[0], seen[t[0]]) + t[1:]))
    return "\n".join(lines) + "\n"


def phase_ms(tok):
    return 0 if tok == "-" else int(tok.split(":")[1])


def proc_ms(p):
    """Nominal kernel work of one process, in ms."""
    return sum(phase_ms(t[1]) + phase_ms(t[2]) + phase_ms(t[3]) + t[5] * t[6] for t in p["trials"])


def write(gens, out, manifest):
    os.makedirs(out, exist_ok=True)
    for session in (1, 2):
        shutil.rmtree(os.path.join(out, "s%d" % session), ignore_errors=True)
    for (step, session), g in gens.items():
        sdir = os.path.join(out, "s%d" % session)
        os.makedirs(os.path.join(sdir, step))
        rows = ["idx\ttag\tcpu\tbytes\tplan\targs"]
        for idx, p in enumerate(g.procs):
            name = "%04d.plan" % idx
            with open(os.path.join(sdir, step, name), "w") as f:
                f.write(plan_text(g, idx, p))
            # The plan path is relative to the folder of run_bwx10.sh.
            args = "--trial --cpus %d --bytes %d --plan sched10/s%d/%s/%s%s" % (
                p["cpu"], p["bytes"], session, step, name, p["extra"])
            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))
        with open(os.path.join(sdir, step + ".tsv"), "w") as f:
            f.write("\n".join(rows) + "\n")
        with open(os.path.join(sdir, step + ".bin"), "w") as f:
            f.write(BINARY[step] + "\n")
    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:
        f.write(manifest)


def yf_orders_ok(g):
    """Per size and CPU: the kernel orders of the 6 replicate sets form a Williams square."""
    seen = {}
    for p in g.procs:
        k = dict(p["keys"])
        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(
            YF_KERNELS.index(k["kernel"]))
    return len(seen) == len(YF_SIZES) * 2 and all(
        len(sets) == UNITS and williams_ok(list(sets.values()), len(YF_KERNELS)) for sets in seen.values())


def blocks_ok(g, keys, conds):
    """The processes come in blocks of len(conds), and every block holds each condition once.
    A condition is the tuple of the header values named by `keys`."""
    got = [tuple(dict(p["keys"]).get(k) for k in keys) for p in g.procs]
    size = len(conds)
    return len(got) % size == 0 and all(
        sorted(got[i:i + size]) == sorted(conds) for i in range(0, len(got), size))


def report(gens):
    ok = True
    lines = ["step session binary processes trials nominal_kernel_work_s"]
    total = {1: [0, 0], 2: [0, 0]}
    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):
        n, tr = len(g.procs), sum(len(p["trials"]) for p in g.procs)
        ms = sum(map(proc_ms, g.procs))
        lines.append("%s %d %s %d %d %g" % (step, session, BINARY[step], n, tr, ms / 1000))
        total[session][0] += n
        total[session][1] += ms
    for session in (1, 2):
        lines.append("session %d total: %d processes, nominal kernel work %g s (%g min)"
                     % (session, total[session][0], total[session][1] / 1000, round(total[session][1] / 60000, 2)))
    lines.append("balance:")
    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):
        if step == "YF":
            a = yf_orders_ok(g)
            text = ("per size and CPU the kernel orders of the 6 sets put each kernel once at each position, "
                    "and each ordered pair of kernels is neighbours once")
        elif step == "YL":
            a = blocks_ok(g, ("kernel", "lcond"), [(k, p[0]) for k in YL_KERNELS for p in YL_PLANS])
            text = "each block of 8 processes holds every kernel and window plan once"
        elif step == "YP":
            a = blocks_ok(g, ("pcond",), [(c[0],) for c in YP_CONDS])
            text = "each block of 7 processes holds every condition once"
        else:
            continue
        ok = ok and a
        lines.append("%s session %d: %s: %s" % (step, session, text, "yes" if a else "NO"))
    return "\n".join(lines) + "\n", ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=20261115, help="base seed")
    ap.add_argument("--test-divisor", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched10"))
    a = ap.parse_args()
    if a.test_divisor < 1 or MIN_WIN_MS % a.test_divisor:
        sys.exit("--test-divisor must divide %d ms" % MIN_WIN_MS)
    gens = generate(a.seed, a.test_divisor)
    text, ok = report(gens)
    manifest = "base_seed=%d\ntest_divisor=%d\n" % (a.seed, a.test_divisor)
    manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed) for (step, session), g in gens.items())
    manifest += "".join("bin %s s%d %s\n" % (step, session, BINARY[step]) for (step, session) in gens)
    manifest += "watch none\n"
    write(gens, a.out, manifest)
    print("written: %s" % a.out)
    sys.stdout.write(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
