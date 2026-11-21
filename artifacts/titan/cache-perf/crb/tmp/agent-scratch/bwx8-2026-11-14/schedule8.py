#!/usr/bin/env python3
"""schedule8.py - schedules and plan files of the design tackle-8mb.md.

Usage: schedule8.py [--seed N] [--select KERNEL@SIZE,...] [--test-divisor N]
                    [--out DIR] [--report]

It writes, for session 1 and 2 and for each step:
  DIR/s<session>/<step>.tsv      one row per process (idx, tag, cpu, bytes, plan, args)
  DIR/s<session>/<step>/NNNN.plan  one plan file per process (not for B6W)
  DIR/MANIFEST.txt               base seed, options, and the seed of each step and session
DIR is "sched" beside this file by default. The folders DIR/s1 and DIR/s2 are replaced.
The steps BIN and CS are written only for the kernels and sizes named by --select.
--report prints the counts and the balance checks and writes nothing.
--test-divisor N divides every duration by N and marks the plans test=1.
The same options give the same bytes. Exit status 1 if a balance check fails.
"""
import argparse
import hashlib
import itertools
import os
import random
import shutil
import sys

KERNELS = ["oldread", "read", "asmread"]
CPUS = {1: [2, 41], 2: [41, 2]}          # session 2 uses the reversed order
M8 = 8 << 20
S2_SIZES = ["32K", "1M", "4M", "8M", "16M"]
MODES = ["closed", "open", "read"]       # counter modes
UNITS = 6                                # processes per CPU and session
PERMS = list(itertools.permutations(range(3)))
STEPS = ["B6W", "S2", "S4", "P3G", "P3", "S3G", "S3", "BIN", "CS", "CM", "C4"]
# B6SEQ of run_bwx.sh, unchanged.
B6SEQ = ("asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,"
         "oldread,oldread2,asmread,oldread2,oldread,asmread")
# Start order of design line 242.
S3_START = [0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6]
S3_PREDS = ["oldread@8M", "read@8M", "asmread@8M", "oldread@1M"]


def size_bytes(tok):
    mult = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    if tok and tok[-1] in mult:
        return int(tok[:-1]) * mult[tok[-1]]
    return int(tok)


def step_seed(base, step, session):
    h = hashlib.sha256(("%d/%s/%d" % (base, step, session)).encode()).hexdigest()
    return int(h[:8], 16)


class Gen:
    """Builds the processes of one step and session."""

    def __init__(self, step, session, base, div):
        self.step, self.session, self.div = step, session, div
        self.seed = step_seed(base, step, session)
        self.rng = random.Random(self.seed)
        self.cpus = CPUS[session]
        self.procs = []

    def ms(self, v):
        return v // self.div

    def at(self, kernel_size, ms):
        return "%s:%d" % (kernel_size, self.ms(ms))

    def trial(self, cond, prev, pfx, pred, tgt, nwin=4, count="closed", bins=0):
        return (cond, prev, pfx, pred, tgt, nwin, self.ms(300), count, bins)

    def same_kernel_trial(self, cond, ks, count="closed", bins=0):
        # The target kernel is its own 1.2 s prefix (design line 207).
        return self.trial(cond, "-", self.at(ks, 1200), "-", ks, 4, count, bins)

    def add(self, tag, cpu, nbytes, keys, trials):
        self.procs.append({"tag": tag, "cpu": cpu, "bytes": nbytes,
                           "keys": keys, "trials": trials, "args": None})

    def perm_rows(self):
        # 24 cycles: each of the six orders of three items four times, shuffled.
        rows = PERMS * 4
        self.rng.shuffle(rows)
        return rows

    def williams_rows(self):
        # Design line 242: 12 shifted rows, random relabel, two copies, shuffled.
        label = list(range(12))
        self.rng.shuffle(label)
        rows = [[label[(x + r) % 12] for x in S3_START] for r in range(12)] * 2
        self.rng.shuffle(rows)
        return rows

    def by_process(self, make_rows, emit):
        # One saved row set per CPU. Process i takes rows 4i to 4i+3 as its cycles.
        rows = {cpu: make_rows() for cpu in self.cpus}
        for i in range(UNITS):
            for cpu in self.cpus:
                emit(i, cpu, rows[cpu][4 * i:4 * i + 4])

    # ---- steps ----
    def B6W(self):
        for i in (1, 2):
            for cpu in self.cpus:
                args = ("--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 "
                        "--min-ms %d --stop pass" % (cpu, B6SEQ, self.ms(300)))
                self.procs.append({"tag": "cpu%d-p%d" % (cpu, i), "cpu": cpu,
                                   "bytes": M8, "keys": [], "trials": [], "args": args})

    def S2(self):
        # order[size][cpu][r]: the kernel order of replicate set r+1.
        order = {}
        for s in S2_SIZES:
            for cpu in self.cpus:
                p = list(PERMS)
                self.rng.shuffle(p)
                order[s, cpu] = p
        for r in range(UNITS):
            sizes = list(S2_SIZES)
            self.rng.shuffle(sizes)
            for s in sizes:
                for cpu in self.cpus:
                    for ki in order[s, cpu][r]:
                        k = KERNELS[ki]
                        cond = "K=%s|S=%s" % (k, s)
                        t = [self.same_kernel_trial(cond, "%s@%s" % (k, s))] * 4
                        self.add("r%d-%s-cpu%d-%s" % (r + 1, s, cpu, k), cpu, size_bytes(s),
                                 [("rep_set", r + 1), ("kernel", k), ("size", size_bytes(s))], t)

    def sustained(self, count):
        for i in range(3):
            for cpu in self.cpus:
                ks = list(KERNELS)
                self.rng.shuffle(ks)
                for k in ks:
                    cond = "K=%s|S=8M" % k
                    if count != "closed":
                        cond += "|count=%s" % count
                    t = [self.trial(cond, "-", "-", "-", k + "@8M", 200, count)]
                    self.add("%s-cpu%d-p%d" % (k, cpu, i + 1), cpu, M8,
                             [("kernel", k), ("size", M8)], t)

    def S4(self):
        self.sustained("closed")

    def C4(self):
        self.sustained("read")

    def P3(self):
        def emit(i, cpu, cycles):
            t = []
            for row in cycles:
                for ki in row:
                    k = KERNELS[ki]
                    t.append(self.same_kernel_trial("K=%s|S=8M" % k, k + "@8M"))
            self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)
        self.by_process(self.perm_rows, emit)

    def P3G(self):
        conds = [(j, k) for j in KERNELS for k in KERNELS]
        for i in range(UNITS):
            for cpu in self.cpus:
                t = []
                for _ in range(4):
                    cyc = list(conds)
                    self.rng.shuffle(cyc)
                    for j, k in cyc:
                        t.append(self.trial("J=%s|K=%s" % (j, k), self.at(j + "@8M", 2400),
                                            self.at(k + "@8M", 1200), "-", k + "@8M"))
                self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)

    def S3G(self):
        def emit(i, cpu, cycles):
            t = []
            for row in cycles:
                for ji in row:
                    j = KERNELS[ji]
                    t.append(self.trial("J=%s|K=oldread" % j, self.at(j + "@8M", 1200),
                                        self.at("oldread@8M", 1200),
                                        self.at("oldread@8M", 300), "oldread@8M"))
            self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)
        self.by_process(self.perm_rows, emit)

    def twelve(self, cells):
        # cells: 12 tuples (cond, predecessor, target kernel, counter mode).
        def emit(i, cpu, cycles):
            t = []
            for row in cycles:
                for c in row:
                    cond, pred, tgt, count = cells[c]
                    t.append(self.trial(cond, "-", self.at("oldread@8M", 1200),
                                        self.at(pred, 300), tgt + "@8M", 4, count))
            self.add("cpu%d-p%d" % (cpu, i + 1), cpu, M8, [], t)
        self.by_process(self.williams_rows, emit)

    def S3(self):
        self.twelve([("P=%s|T=%s" % (p, t), p, t, "closed")
                     for p in S3_PREDS for t in KERNELS])

    def CM(self):
        two = ["oldread", "read"]
        self.twelve([("P=%s@8M|T=%s|count=%s" % (p, t, m), p + "@8M", t, m)
                     for m in MODES for p in two for t in two])

    def selected(self, select, make_trials):
        # One kernel and size per process. make_trials(i, cpu, kernel, size token).
        for i in range(UNITS):
            sel = list(select)
            self.rng.shuffle(sel)
            for k, s in sel:
                for cpu in self.cpus:
                    self.add("%s-%s-cpu%d-p%d" % (k, s, cpu, i + 1), cpu, size_bytes(s),
                             [("kernel", k), ("size", size_bytes(s))],
                             make_trials(i, cpu, k, s))

    def BIN(self, select):
        # Modes A (window records only) and B (10 ms bins). ABBA BAAB, or its mirror.
        def trials(i, cpu, k, s):
            order = [0, 1, 1, 0, 1, 0, 0, 1]
            if i % 2:
                order = [1 - b for b in order]
            return [self.same_kernel_trial("K=%s|S=%s|bins=%d" % (k, s, b),
                                           "%s@%s" % (k, s), "closed", b) for b in order]
        self.selected(select, trials)

    def CS(self, select):
        rows = {(k, s, cpu): self.perm_rows() for k, s in select for cpu in self.cpus}

        def trials(i, cpu, k, s):
            t = []
            for row in rows[k, s, cpu][4 * i:4 * i + 4]:
                for mi in row:
                    t.append(self.same_kernel_trial("K=%s|S=%s|count=%s" % (k, s, MODES[mi]),
                                                    "%s@%s" % (k, s), MODES[mi]))
            return t
        self.selected(select, trials)


def generate(base, div, select):
    """Returns {(step, session): Gen}. BIN and CS only if select is not empty."""
    out = {}
    for session in (1, 2):
        for step in STEPS:
            g = Gen(step, session, base, div)
            if step in ("BIN", "CS"):
                if not select:
                    continue
                getattr(g, step)(select)
            else:
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
    if p["args"]:
        a = p["args"].split()
        get = lambda o: a[a.index(o) + 1]
        return len(get("--seq").split(",")) * int(get("--rounds")) * int(get("--min-ms"))
    return sum(phase_ms(t[1]) + phase_ms(t[2]) + phase_ms(t[3]) + t[5] * t[6]
               for t in p["trials"])


def write(gens, out, manifest):
    os.makedirs(out, exist_ok=True)
    for session in (1, 2):
        shutil.rmtree(os.path.join(out, "s%d" % session), ignore_errors=True)
    for (step, session), g in gens.items():
        sdir = os.path.join(out, "s%d" % session)
        rows = ["idx\ttag\tcpu\tbytes\tplan\targs"]
        if g.procs[0]["args"] is None:
            os.makedirs(os.path.join(sdir, step))
        else:
            os.makedirs(sdir, exist_ok=True)
        for idx, p in enumerate(g.procs):
            if p["args"] is None:
                name = "%04d.plan" % idx
                with open(os.path.join(sdir, step, name), "w") as f:
                    f.write(plan_text(g, idx, p))
                # The plan path is relative to the folder of run_bwx8.sh.
                args = "--trial --cpus %d --bytes %d --plan sched/s%d/%s/%s" % (
                    p["cpu"], p["bytes"], session, step, name)
            else:
                name, args = "-", p["args"]
            rows.append("%d\t%s\t%d\t%d\t%s\t%s" % (idx, p["tag"], p["cpu"], p["bytes"], name, args))
        with open(os.path.join(sdir, step + ".tsv"), "w") as f:
            f.write("\n".join(rows) + "\n")
    with open(os.path.join(out, "MANIFEST.txt"), "w") as f:
        f.write(manifest)


def cycles_by_cpu(g, n):
    """{cpu: rows}, a row being the cond labels of n successive trials of a process."""
    rows = {}
    for p in g.procs:
        c = [t[0] for t in p["trials"]]
        rows.setdefault(p["cpu"], []).extend(c[i:i + n] for i in range(0, len(c), n))
    return rows


def williams_ok(rows):
    """Design line 242: every ordered pair of distinct conditions twice as neighbours
    inside rows, and every condition twice at every position."""
    pairs, pos = {}, {}
    for row in rows:
        for i, c in enumerate(row):
            pos[c, i] = pos.get((c, i), 0) + 1
            if i:
                pairs[row[i - 1], c] = pairs.get((row[i - 1], c), 0) + 1
    return (len(rows) == 24 and len(pairs) == 132 and set(pairs.values()) == {2},
            len(pos) == 144 and set(pos.values()) == {2})


def s2_orders_ok(g):
    """Each of the six kernel orders once per size and CPU."""
    seen = {}
    for p in g.procs:
        k = dict(p["keys"])
        seen.setdefault((k["size"], p["cpu"]), {}).setdefault(k["rep_set"], []).append(k["kernel"])
    return len(seen) == len(S2_SIZES) * 2 and all(
        len(sets) == 6 and len({tuple(o) for o in sets.values()}) == 6
        and all(len(o) == 3 for o in sets.values()) for sets in seen.values())


def report(gens):
    ok = True
    lines = ["step session processes trials nominal_kernel_work_s"]
    total = {}
    for (step, session), g in sorted(gens.items(), key=lambda x: (STEPS.index(x[0][0]), x[0][1])):
        n, tr, ms = len(g.procs), sum(len(p["trials"]) for p in g.procs), sum(map(proc_ms, g.procs))
        lines.append("%s %d %d %d %g" % (step, session, n, tr, ms / 1000))
        t = total.setdefault(step, [0, 0, 0])
        t[0] += n; t[1] += tr; t[2] += ms
    lines.append("both sessions together:")
    for step in STEPS:
        if step in total:
            n, tr, ms = total[step]
            lines.append("%s total: %d processes, %d trials, nominal kernel work %g s (%g min)"
                         % (step, n, tr, ms / 1000, round(ms / 60000, 2)))
    lines.append("balance:")
    for (step, session), g in sorted(gens.items(), key=lambda x: (STEPS.index(x[0][0]), x[0][1])):
        if step in ("S3", "CM"):
            for cpu, rows in cycles_by_cpu(g, 12).items():
                a, b = williams_ok(rows)
                ok = ok and a and b
                lines.append("%s session %d cpu %d: each ordered pair of distinct conditions "
                             "is neighbours twice inside rows: %s; every condition is twice "
                             "at every position: %s" % (step, session, cpu,
                                                        "yes" if a else "NO", "yes" if b else "NO"))
        if step == "S2":
            a = s2_orders_ok(g)
            ok = ok and a
            lines.append("S2 session %d: each kernel order once per size and CPU: %s"
                         % (session, "yes" if a else "NO"))
    return "\n".join(lines) + "\n", ok


def parse_select(text):
    sel = []
    for item in filter(None, text.split(",")):
        k, _, s = item.partition("@")
        try:
            b = size_bytes(s)
        except ValueError:
            b = 0
        if k not in KERNELS or b <= 0 or b % 256:
            sys.exit("bad --select entry '%s': use KERNEL@SIZE, kernels %s" % (item, KERNELS))
        if (k, s) in sel:
            sys.exit("--select names '%s' twice" % item)
        sel.append((k, s))
    return sel


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=20261114, help="base seed")
    ap.add_argument("--select", default="", help="KERNEL@SIZE,... for the steps BIN and CS")
    ap.add_argument("--test-divisor", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sched"))
    ap.add_argument("--report", action="store_true", help="print the report, write nothing")
    a = ap.parse_args()
    if a.test_divisor < 1 or 300 % a.test_divisor:
        sys.exit("--test-divisor must divide 300 ms")
    select = parse_select(a.select)
    gens = generate(a.seed, a.test_divisor, select)
    text, ok = report(gens)
    if not a.report:
        manifest = "base_seed=%d\ntest_divisor=%d\nselect=%s\n" % (a.seed, a.test_divisor, a.select)
        manifest += "".join("seed %s s%d %d\n" % (step, session, g.seed)
                            for (step, session), g in gens.items())
        write(gens, a.out, manifest)
        print("written: %s" % a.out)
    sys.stdout.write(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
