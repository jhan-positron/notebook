#!/usr/bin/env python3
"""schedule9.py - schedules and plan files of round 2 (steps XW XCA XCB XCC XEV XN XF).

Usage: schedule9.py [--seed N] [--test-divisor N] [--out DIR]

It writes, for session 1 and 2 and for each step:
  DIR/s<session>/<STEP>.tsv        one row per process (idx, tag, cpu, bytes, plan, args)
  DIR/s<session>/<STEP>/NNNN.plan  one plan file per process (plan format v1 of bwx8)
  DIR/s<session>/<STEP>.watch      empty; only for the steps that run with the host sampler
  DIR/MANIFEST.txt                 base seed, test divisor, and the seed of each step and session
DIR is "sched9" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.
The step XEV exists in session 1 only.
--test-divisor N divides every duration by N and marks the plans test=1 (local chain tests only).
The same options give the same bytes. Exit status 1 if a balance check fails.

Steps (CPUs 2 and 41; session 2 uses the reversed CPU order; one process at a time):
  XW   watch and onset: one trial, 100 windows of 300 ms, count closed, 7 conditions W0 to W6,
       2 processes per condition and CPU. Order: replicate, then CPU, then the 7 conditions shuffled.
  XCA XCB XCC   sustained with counters (count read), one event set per step, given in the args
       column. Per CPU: 2 processes each of read, asmread, oldread at 8M with 100 windows, and one
       process each of read at 1M, 32K and 16M with 20 windows.
  XEV  event acceptance: CPU 2 only, one process per event set, 3 windows, count read.
  XN   core-limit family: trials as step S2 of schedule8.py; kernels asmread, read_nop16,
       read_nop32, read_sparse; sizes 32K, 1M, 8M; 6 replicate sets per size and CPU.
  XF   finer sizes: trials as step S2; 3 processes per kernel, size and CPU.
"""
import argparse
import itertools
import os
import shutil
import sys

sys.dont_write_bytecode = True           # the import below must not write a file into this folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schedule8                         # noqa: E402  (Gen, plan_text, proc_ms, size_bytes)

STEPS = ["XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF"]
WATCH_STEPS = ["XW", "XCA", "XCB", "XCC"]          # steps that run with hostwatch.py
PMU_TYPE = 11                                      # armv8_pmuv3_0 on CRB (DECISIONS-bwx8.md)
EVENTS = {
    "A": "cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,"
         "l3d_cache_refill=0x2a,stall_backend_mem=0x4005",
    "B": "l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009,l3d_cache_lmiss_rd=0x400b,"
         "ll_cache_miss_rd=0x37,l2d_cache=0x16,bus_access=0x19",
    "C": "exc_taken=0x09,l1d_tlb_refill=0x05,dtlb_walk=0x34,l2d_cache_wb=0x18,"
         "l3d_cache_allocate=0x29,mem_access=0x13",
}
# XW: name, target kernel, target size, previous activity (3000 ms) or None.
XW_CONDS = [("W0", "read", "8M", None), ("W1", "read", "8M", "oldread@8M"),
            ("W2", "read", "8M", "read@1M"), ("W3", "asmread", "8M", None),
            ("W4", "oldread", "8M", None), ("W5", "read", "4M", None), ("W6", "read", "16M", None)]
XC_LONG = [("read", "8M"), ("asmread", "8M"), ("oldread", "8M")]     # 2 processes each, 100 windows
XC_SHORT = [("read", "1M"), ("read", "32K"), ("read", "16M")]        # 1 process each, 20 windows
XN_KERNELS = ["asmread", "read_nop16", "read_nop32", "read_sparse"]
XN_SIZES = ["32K", "1M", "8M"]
XN_PERMS = list(itertools.permutations(range(4)))
XF_CELLS = [("read", s) for s in ("1572864", "2M", "2621440", "3M", "5M", "6M", "12M", "24M", "32M", "64M")] + \
           [("oldread", s) for s in ("2M", "3M", "6M", "12M", "32M")]
UNITS = 6
size_bytes = schedule8.size_bytes


def positions_balanced(orders, n):
    """Every item 0..n-1 takes every position floor or ceil of len(orders)/n times."""
    lo = len(orders) // n
    hi = lo + (1 if len(orders) % n else 0)
    return all(lo <= sum(1 for o in orders if o[pos] == item) <= hi
               for item in range(n) for pos in range(n))


class Gen9(schedule8.Gen):
    """Builds the processes of one round 2 step and session."""

    def add9(self, tag, cpu, size, keys, trials, extra=""):
        self.add(tag, cpu, size_bytes(size), keys, trials)
        self.procs[-1]["extra"] = extra

    def XW(self):
        for r in (1, 2):
            for cpu in self.cpus:
                conds = list(XW_CONDS)
                self.rng.shuffle(conds)
                for name, k, s, prev in conds:
                    cond = "K=%s|S=%s|prev=%s" % (k, s, prev or "none")
                    t = [self.trial(cond, self.at(prev, 3000) if prev else "-", "-", "-",
                                    "%s@%s" % (k, s), 100, "closed")]
                    self.add9("%s-cpu%d-p%d" % (name, cpu, r), cpu, s,
                              [("rep_set", r), ("kernel", k), ("size", size_bytes(s)),
                               ("wcond", name), ("prev", prev or "none")], t)

    def counted(self, evset):
        extra = " --pmu-type %d --events %s" % (PMU_TYPE, EVENTS[evset])
        short = {}
        for cpu in self.cpus:
            # The three short processes of a CPU are drawn into its two replicate blocks: 2 and 1, or 1 and 2.
            s = list(XC_SHORT)
            self.rng.shuffle(s)
            cut = self.rng.choice([1, 2])
            short[cpu] = [s[:cut], s[cut:]]
        for r in (1, 2):
            for cpu in self.cpus:
                items = [(k, s, 100) for k, s in XC_LONG] + [(k, s, 20) for k, s in short[cpu][r - 1]]
                self.rng.shuffle(items)
                for k, s, nwin in items:
                    cond = "K=%s|S=%s|count=read" % (k, s)
                    t = [self.trial(cond, "-", "-", "-", "%s@%s" % (k, s), nwin, "read")]
                    self.add9("%s-%s-cpu%d-p%d" % (k, s, cpu, r), cpu, s,
                              [("rep_set", r), ("kernel", k), ("size", size_bytes(s)), ("evset", evset)],
                              t, extra)

    def XCA(self):
        self.counted("A")

    def XCB(self):
        self.counted("B")

    def XCC(self):
        self.counted("C")

    def XEV(self):
        for evset in "ABC":
            t = [self.trial("K=read|S=8M|count=read", "-", "-", "-", "read@8M", 3, "read")]
            self.add9("ev%s-cpu2" % evset, 2, "8M",
                      [("kernel", "read"), ("size", size_bytes("8M")), ("evset", evset)], t,
                      " --pmu-type %d --events %s" % (PMU_TYPE, EVENTS[evset]))

    def xn_orders(self):
        # A saved random selection of 6 of the 24 kernel orders, in which each kernel takes
        # each position once or twice (6 sets over 4 positions cannot be more equal).
        while True:
            pick = self.rng.sample(XN_PERMS, UNITS)
            if positions_balanced(pick, 4):
                return pick

    def XN(self):
        # As S2 of schedule8.py: replicate set, then size (shuffled), then CPU, then the kernels.
        order = {}
        for s in XN_SIZES:
            for cpu in self.cpus:
                order[s, cpu] = self.xn_orders()
        for r in range(UNITS):
            sizes = list(XN_SIZES)
            self.rng.shuffle(sizes)
            for s in sizes:
                for cpu in self.cpus:
                    for ki in order[s, cpu][r]:
                        k = XN_KERNELS[ki]
                        t = [self.same_kernel_trial("K=%s|S=%s" % (k, s), "%s@%s" % (k, s))] * 4
                        self.add9("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, s,
                                  [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)

    def XF(self):
        for r in (1, 2, 3):
            for cpu in self.cpus:
                cells = list(XF_CELLS)
                self.rng.shuffle(cells)
                for k, s in cells:
                    t = [self.same_kernel_trial("K=%s|S=%s" % (k, s), "%s@%s" % (k, s))] * 4
                    self.add9("r%d-%s-cpu%d-%s" % (r, s, cpu, k), cpu, s,
                              [("rep_set", r), ("kernel", k), ("size", size_bytes(s))], t)


def generate(base, div):
    """Returns {(step, session): Gen9}. XEV only in session 1."""
    out = {}
    for session in (1, 2):
        for step in STEPS:
            if step == "XEV" and session == 2:
                continue
            g = Gen9(step, session, base, div)
            getattr(g, step)()
            out[step, session] = g
    return out


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
                f.write(schedule8.plan_text(g, idx, p))
            # The plan path is relative to the folder of run_bwx9.sh.
            args = "--trial --cpus %d --bytes %d --plan sched9/s%d/%s/%s%s" % (
                p["cpu"], p["bytes"], session, step, name, p["extra"])
            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))
        with open(os.path.join(sdir, step + ".tsv"), "w") as f:
            f.write("\n".join(rows) + "\n")
        if step in WATCH_STEPS:
            open(os.path.join(sdir, step + ".watch"), "w").close()
    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:
        f.write(manifest)


def xn_orders_ok(g):
    """Per size and CPU: 6 sets of 4 kernels, 6 different orders, positions balanced."""
    seen = {}
    for p in g.procs:
        k = dict(p["keys"])
        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(
            XN_KERNELS.index(k["kernel"]))
    return len(seen) == len(XN_SIZES) * 2 and all(
        len(sets) == UNITS and len({tuple(o) for o in sets.values()}) == UNITS
        and all(sorted(o) == [0, 1, 2, 3] for o in sets.values())
        and positions_balanced(list(sets.values()), 4) for sets in seen.values())


def report(gens):
    ok = True
    lines = ["step session processes trials nominal_kernel_work_s"]
    total = [0, 0]
    for (step, session), g in sorted(gens.items(), key=lambda x: (x[0][1], STEPS.index(x[0][0]))):
        n, tr = len(g.procs), sum(len(p["trials"]) for p in g.procs)
        ms = sum(map(schedule8.proc_ms, g.procs))
        lines.append("%s %d %d %d %g" % (step, session, n, tr, ms / 1000))
        if session == 1:
            total[0] += n
            total[1] += ms
    lines.append("session 1 total: %d processes, nominal kernel work %g s (%g min)"
                 % (total[0], total[1] / 1000, round(total[1] / 60000, 2)))
    lines.append("balance:")
    for (step, session), g in sorted(gens.items()):
        if step == "XN":
            a = xn_orders_ok(g)
            ok = ok and a
            lines.append("XN session %d: per size and CPU 6 different kernel orders, each kernel "
                         "once or twice at each position: %s" % (session, "yes" if a else "NO"))
    return "\n".join(lines) + "\n", ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=20261115, help="base seed")
    ap.add_argument("--test-divisor", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched9"))
    a = ap.parse_args()
    if a.test_divisor < 1 or 300 % a.test_divisor:
        sys.exit("--test-divisor must divide 300 ms")
    gens = generate(a.seed, a.test_divisor)
    text, ok = report(gens)
    manifest = "base_seed=%d\ntest_divisor=%d\n" % (a.seed, a.test_divisor)
    manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed)
                        for (step, session), g in gens.items())
    write(gens, a.out, manifest)
    print("written: %s" % a.out)
    sys.stdout.write(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
