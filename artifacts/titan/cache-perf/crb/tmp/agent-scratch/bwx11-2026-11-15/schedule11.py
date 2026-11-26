#!/usr/bin/env python3
"""schedule11.py - schedules and plan files of round 4 (steps ZA ZD ZC ZN ZM).

Usage: schedule11.py [--seed N] [--test-divisor N] [--out DIR]

It writes, for session 1 and 2 and for each step:
  DIR/s<session>/<STEP>.tsv        one row per process (idx, tag, cpu, bytes, plan, args)
  DIR/s<session>/<STEP>/NNNN.plan  one plan file per process (plan format v1 of bwx8, bwx10 and bwx11)
  DIR/s<session>/<STEP>.bin        one word: the binary that run_bwx11.sh starts for the step (bwx11 for every step)
  DIR/MANIFEST.txt                 base seed, test divisor, the seed and the binary of each step and session
DIR is "sched11" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.
No step of round 4 runs with the host sampler, so no .watch file is written.
The step ZA exists in session 1 only.
--test-divisor N divides every duration by N and marks the plans test=1 (local chain tests only).
N must divide 100 ms, the shortest window of round 4.
The same options give the same bytes. Exit status 1 if a balance check fails.
This file needs no file of an earlier round: the parts taken from schedule10.py are copied here.

"--evict-mb 512" (condition E512) is an option of bwx11: after first touch the worker writes another buffer
of 512 MiB twice and unmaps it, so that the lines of the test buffer leave all caches and come back from memory clean.
Condition E0 has no option. The evict step is real time that is not kernel work (est. 0.3 to 1 s per process).
It is not part of the nominal kernel work that this file and run_bwx11.sh print.

Steps (binary bwx11; CPUs 2 and 41; session 2 uses the reversed CPU order; one process at a time):
  ZD   clean lines: trials as step S2 of schedule8.py (4 trials per process: prefix K@S 1200 ms, target K@S
       4 x 300 ms). Kernels asmread, read, oldread; sizes 4M, 8M, 16M; conditions E0 and E512. The 6 cells
       (kernel, condition) run in 6 replicate sets per size and CPU.
       Order: replicate set, then size (shuffled), then CPU, then the 6 cells. Per size and CPU the cell
       orders of the 6 sets form a Williams square (defined at williams_square below).
  ZC   clean lines, counters: one trial, 20 windows of 300 ms, count read, the event set in the args column.
       Kernels asmread, oldread; sizes 8M, 16M; conditions E0 and E512; 2 processes per cell and CPU.
       Order: replicate, then CPU, then the 8 cells shuffled.
  ZN   slow load-only kernels: trials as S2. Kernels read_nop64, read_nop96, read_nop128; sizes 32K, 1M, 8M,
       16M; 6 replicate sets per size and CPU. Order: replicate set, then size (shuffled), then CPU, then the
       3 kernels. Per size and CPU the 6 sets use the 6 possible orders of 3 kernels once each: every kernel
       is twice at every position, and every ordered pair of kernels is twice a pair of neighbours.
  ZM   kick map: asmread at 8M, one trial of 300 windows of 100 ms, count closed, "--rec-pad P" with
       P = 0, 8, 16, 24, 32, 40, 48, 56, 64, 72. 2 processes per pad and CPU.
       Order: replicate, then CPU, then the 10 pads shuffled.
  ZA   acceptance of bwx11: CPU 2 only, 6 short processes with --trace, in a fixed order.
"""
import argparse
import hashlib
import itertools
import os
import random
import shutil
import sys

STEPS = ["ZA", "ZD", "ZC", "ZN", "ZM"]
BINARY = {"ZA": "bwx11", "ZD": "bwx11", "ZC": "bwx11", "ZN": "bwx11", "ZM": "bwx11"}
CPUS = {1: [2, 41], 2: [41, 2]}                    # session 2 uses the reversed order
PMU_TYPE = 11                                      # armv8_pmuv3_0 on CRB (DECISIONS-bwx8.md)
ZC_EVENTS = ("cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,"
             "bus_access=0x19,l2d_cache_lmiss_rd=0x4009")
EVICT_MB = 512
# name, megabytes of the evict buffer (0: no option), the options added to the command line
ECONDS = [("E0", 0, ""), ("E%d" % EVICT_MB, EVICT_MB, " --evict-mb %d" % EVICT_MB)]
ZD_KERNELS = ["asmread", "read", "oldread"]
ZD_SIZES = ["4M", "8M", "16M"]
ZD_CELLS = [(k, e) for k in ZD_KERNELS for e in ECONDS]
ZC_KERNELS = ["asmread", "oldread"]
ZC_SIZES = ["8M", "16M"]
ZN_KERNELS = ["read_nop64", "read_nop96", "read_nop128"]
ZN_SIZES = ["32K", "1M", "8M", "16M"]
ZM_PADS = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72]
# name, kernel, size, megabytes of the evict buffer, the options added after --trace
ZA_PROCS = [("plain", "asmread", "8M", 0, ""), ("evict", "asmread", "8M", EVICT_MB, " --evict-mb %d" % EVICT_MB),
            ("oldevict", "oldread", "8M", EVICT_MB, " --evict-mb %d" % EVICT_MB),
            ("nop64", "read_nop64", "8M", 0, ""), ("nop96", "read_nop96", "8M", 0, ""),
            ("nop128", "read_nop128", "8M", 0, "")]
UNITS = 6                                          # replicate sets per size and CPU in ZD and ZN
MIN_WIN_MS = 100                                   # the shortest window of round 4
EVICT_EST_S = (0.3, 1.0)                           # est. real time of the evict step of one process, in seconds


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


def all_orders_ok(orders, n):
    """orders: the orders of the items 0..n-1 of the replicate sets. True if they are all n! possible
    orders, each one once."""
    return sorted(tuple(o) for o in orders) == sorted(itertools.permutations(range(n)))


class Gen:
    """Builds the processes of one round 4 step and session."""

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

    def add(self, tag, cpu, size, keys, trials, extra="", evict=0):
        self.procs.append({"tag": tag, "cpu": cpu, "bytes": size_bytes(size), "keys": keys,
                           "trials": trials, "extra": extra, "evict": evict})

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

    def all_orders(self, n):
        # Every possible order of n items once, in a random row order. For n = 3 these are 6 orders: every
        # item is twice at every position, and every ordered pair of items is twice a pair of neighbours.
        rows = [list(o) for o in itertools.permutations(range(n))]
        self.rng.shuffle(rows)
        return rows

    # ---- steps ----
    def ZD(self):
        order = {}
        for s in ZD_SIZES:
            for cpu in self.cpus:
                order[s, cpu] = self.williams_square(len(ZD_CELLS))
        for r in range(UNITS):
            sizes = list(ZD_SIZES)
            self.rng.shuffle(sizes)
            for s in sizes:
                for cpu in self.cpus:
                    for ci in order[s, cpu][r]:
                        k, (ename, mb, extra) = ZD_CELLS[ci]
                        ks = "%s@%s" % (k, s)
                        t = [self.trial("K=%s|S=%s|evict=%d" % (k, s, mb), 1200, ks, 4, 300)] * 4
                        self.add("r%d-%s-cpu%d-%s-%s" % (r + 1, s, cpu, k, ename), cpu, s,
                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s)), ("econd", ename)],
                                 t, extra, mb)

    def ZC(self):
        events = " --pmu-type %d --events %s" % (PMU_TYPE, ZC_EVENTS)
        cells = [(k, s, e) for k in ZC_KERNELS for s in ZC_SIZES for e in ECONDS]
        for r in (1, 2):
            for cpu in self.cpus:
                block = list(cells)
                self.rng.shuffle(block)
                for k, s, (ename, mb, extra) in block:
                    t = [self.trial("K=%s|S=%s|evict=%d|count=read" % (k, s, mb), None, "%s@%s" % (k, s), 20, 300, "read")]
                    self.add("%s-%s-%s-cpu%d-p%d" % (k, s, ename, cpu, r), cpu, s,
                             [("rep_set", r), ("kernel", k), ("size", size_bytes(s)), ("econd", ename)],
                             t, extra + events, mb)

    def ZN(self):
        order = {}
        for s in ZN_SIZES:
            for cpu in self.cpus:
                order[s, cpu] = self.all_orders(len(ZN_KERNELS))
        for r in range(UNITS):
            sizes = list(ZN_SIZES)
            self.rng.shuffle(sizes)
            for s in sizes:
                for cpu in self.cpus:
                    for ki in order[s, cpu][r]:
                        k = ZN_KERNELS[ki]
                        ks = "%s@%s" % (k, s)
                        t = [self.trial("K=%s|S=%s" % (k, s), 1200, ks, 4, 300)] * 4
                        self.add("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, s,
                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)

    def ZM(self):
        for r in (1, 2):
            for cpu in self.cpus:
                block = list(ZM_PADS)
                self.rng.shuffle(block)
                for pad in block:
                    name = "P%d" % pad
                    t = [self.trial("K=asmread|S=8M|rec=%s" % name, None, "asmread@8M", 300, 100)]
                    self.add("%s-cpu%d-p%d" % (name, cpu, r), cpu, "8M",
                             [("rep_set", r), ("kernel", "asmread"), ("size", size_bytes("8M")), ("pcond", name)],
                             t, " --rec-pad %d" % pad)

    def ZA(self):
        for name, k, s, mb, opts in ZA_PROCS:
            ks = "%s@%s" % (k, s)
            t = [self.trial("K=%s|S=%s|acc=%s" % (k, s, name), 400, ks, 3, 300)]
            self.add("%s-cpu2" % name, 2, s,
                     [("kernel", k), ("size", size_bytes(s)), ("acond", name)], t, " --trace" + opts, mb)


def generate(base, div):
    """Returns {(step, session): Gen}. ZA only in session 1."""
    out = {}
    for session in (1, 2):
        for step in STEPS:
            if step == "ZA" and session == 2:
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
    """Nominal kernel work of one process, in ms. The evict step of a process is not kernel work."""
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
            # The plan path is relative to the folder of run_bwx11.sh.
            args = "--trial --cpus %d --bytes %d --plan sched11/s%d/%s/%s%s" % (
                p["cpu"], p["bytes"], session, step, name, p["extra"])
            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))
        with open(os.path.join(sdir, step + ".tsv"), "w") as f:
            f.write("\n".join(rows) + "\n")
        with open(os.path.join(sdir, step + ".bin"), "w") as f:
            f.write(BINARY[step] + "\n")
    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:
        f.write(manifest)


def set_orders(g, item):
    """{(size, cpu): {rep_set: [item index, in schedule order]}}; item(header keys) gives the index."""
    seen = {}
    for p in g.procs:
        k = dict(p["keys"])
        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(item(k))
    return seen


def zd_orders_ok(g):
    """Per size and CPU: the (kernel, condition) orders of the 6 replicate sets form a Williams square."""
    names = [(k, e[0]) for k, e in ZD_CELLS]
    seen = set_orders(g, lambda k: names.index((k["kernel"], k["econd"])))
    return len(seen) == len(ZD_SIZES) * 2 and all(
        len(sets) == UNITS and williams_ok(list(sets.values()), len(ZD_CELLS)) for sets in seen.values())


def zn_orders_ok(g):
    """Per size and CPU: the kernel orders of the 6 replicate sets are the 6 possible orders, each one once."""
    seen = set_orders(g, lambda k: ZN_KERNELS.index(k["kernel"]))
    return len(seen) == len(ZN_SIZES) * 2 and all(
        len(sets) == UNITS and all_orders_ok(list(sets.values()), len(ZN_KERNELS)) for sets in seen.values())


def blocks_ok(g, keys, conds):
    """The processes come in blocks of len(conds), and every block holds each condition once.
    A condition is the tuple of the header values named by `keys`."""
    got = [tuple(dict(p["keys"]).get(k) for k in keys) for p in g.procs]
    size = len(conds)
    return len(got) % size == 0 and all(
        sorted(got[i:i + size]) == sorted(conds) for i in range(0, len(got), size))


def report(gens):
    ok = True
    lines = ["step session binary processes trials nominal_kernel_work_s evict_processes"]
    total = {1: [0, 0, 0], 2: [0, 0, 0]}
    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):
        n, tr = len(g.procs), sum(len(p["trials"]) for p in g.procs)
        ms = sum(map(proc_ms, g.procs))
        ev = sum(1 for p in g.procs if p["evict"])
        lines.append("%s %d %s %d %d %g %d" % (step, session, BINARY[step], n, tr, ms / 1000, ev))
        total[session][0] += n
        total[session][1] += ms
        total[session][2] += ev
    for session in (1, 2):
        n, ms, ev = total[session]
        lines.append("session %d total: %d processes, nominal kernel work %g s (%g min)"
                     % (session, n, ms / 1000, round(ms / 60000, 2)))
        lines.append("session %d evict step: %d processes run with --evict-mb %d; the evict step is real time that is "
                     "not kernel work, est. %g to %g s per process, so est. %g to %g s more in the session; "
                     "it is not in the nominal kernel work and not in the longest process that gives MARGIN "
                     "(RESERVE of run_bwx11.sh, default 90 s, covers it)"
                     % (session, ev, EVICT_MB, EVICT_EST_S[0], EVICT_EST_S[1], ev * EVICT_EST_S[0], ev * EVICT_EST_S[1]))
    lines.append("balance:")
    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):
        if step == "ZD":
            a = zd_orders_ok(g)
            text = ("per size and CPU the orders of the 6 sets put each (kernel, condition) cell once at each "
                    "position, and each ordered pair of cells is neighbours once")
        elif step == "ZN":
            a = zn_orders_ok(g)
            text = ("per size and CPU the 6 sets use the 6 orders of the 3 kernels once each (each kernel twice at "
                    "each position, each ordered pair of kernels neighbours twice)")
        elif step == "ZC":
            a = blocks_ok(g, ("kernel", "size", "econd"),
                          [(k, size_bytes(s), e[0]) for k in ZC_KERNELS for s in ZC_SIZES for e in ECONDS])
            text = "each block of 8 processes holds every kernel, size and condition once"
        elif step == "ZM":
            a = blocks_ok(g, ("pcond",), [("P%d" % p,) for p in ZM_PADS])
            text = "each block of 10 processes holds every pad once"
        else:
            continue
        ok = ok and a
        lines.append("%s session %d: %s: %s" % (step, session, text, "yes" if a else "NO"))
    return "\n".join(lines) + "\n", ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=20261115, help="base seed")
    ap.add_argument("--test-divisor", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched11"))
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
