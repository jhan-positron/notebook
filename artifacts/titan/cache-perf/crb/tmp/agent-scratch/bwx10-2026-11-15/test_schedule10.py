#!/usr/bin/env python3
"""test_schedule10.py - checks of schedule10.py, run_bwx10.sh and visit10.sh (round 3).

Usage: test_schedule10.py [--no-run] [--no-bwx8] [--no-long] [--no-bwx10]
Prints one line per check. Exit status 0 only if every check passed.
--no-run leaves out the checks that start run_bwx10.sh with dummy binaries (they take minutes
on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).
--no-bwx8 leaves out the build of the local stand-in bwx8 (from folder X of round 1) and the run of
every plan of the bwx8 step YL through it.
--no-long leaves out the 8 runs of 30 s that put the real window plans of YL (test divisor 1) through bwx8.
--no-bwx10 leaves out the run of the plans of YA, YP, YF and YC through a local stand-in bwx10. These
checks also print SKIP when bwx10.c is not beside this file or does not build here: the runner
is the work of another part.
Rules are also applied to a defective input, and such a check passes only if that is rejected.
This machine has no CPU 41: for the runs through a stand-in the test rewrites CPU 41 to a local CPU
in a copy of the schedule. Nothing else of the copy differs.
"""
import collections
import concurrent.futures
import copy
import itertools
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
Y = os.path.dirname(os.path.abspath(__file__))
X = os.path.join(os.path.dirname(Y), "bwx8-2026-11-14")      # round 1 and 2: bwx8.c, run_bwx9.sh, visit9.sh, hostwatch.py
SCHED = os.path.join(Y, "schedule10.py")
RUN = os.path.join(Y, "run_bwx10.sh")
VISIT = os.path.join(Y, "visit10.sh")
WATCH = os.path.join(Y, "hostwatch.py")
NEW_KERNELS = ["read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]
READ_KERNELS = ["oldread", "read", "asmread", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse"] + NEW_KERNELS
# The flags of build8.sh.
CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "
          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()
# The task: processes per step and session, trials per process, nominal kernel work in seconds, binary.
TABLE = collections.OrderedDict([("YA", (9, 1, 11.7, "bwx10")), ("YL", (32, 1, 960.0, "bwx8")), ("YP", (28, 1, 840.0, "bwx10")),
                                 ("YF", (288, 4, 2764.8, "bwx10")), ("YC", (42, 1, 252.0, "bwx10"))])
EVENTS = "cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009"
# name: (windows, window length in ms, bins)
YL = collections.OrderedDict([("L100", (300, 100, 0)), ("L300", (100, 300, 0)), ("L1000", (30, 1000, 0)), ("L30000", (1, 30000, 1))])
YL_KERNELS = ["asmread", "read"]
# name: the options after the plan
YP = collections.OrderedDict([("P0", " --rec-pad 0"), ("P80", " --rec-pad 80"), ("P400", " --rec-pad 400"),
                              ("P1040", " --rec-pad 1040"), ("P2080", " --rec-pad 2080"), ("P4000", " --rec-pad 4000"),
                              ("hot", " --hot-copy")])
YF_KERNELS = ["asmread"] + NEW_KERNELS
YF_SIZES = ["32K", "1M", "8M", "16M"]
YC_KERNELS = YF_KERNELS + ["oldread"]
YC_SIZES = ["1M", "8M", "16M"]
# tag, kernel, size, the options after the plan
YA = [("plain-cpu2", "asmread", "8M", " --trace"), ("pad80-cpu2", "asmread", "8M", " --trace --rec-pad 80"),
      ("hot-cpu2", "asmread", "8M", " --trace --hot-copy"), ("pf256-cpu2", "read_pf256", "8M", " --trace"),
      ("pf512-cpu2", "read_pf512", "8M", " --trace"), ("pf1024-cpu2", "read_pf1024", "8M", " --trace"),
      ("pf2048-cpu2", "read_pf2048", "8M", " --trace"), ("1pl-cpu2", "read_1pl", "8M", " --trace"),
      ("pf1024s-cpu2", "read_pf1024", "32K", " --trace")]
HEAD_S2 = ["step", "session", "cpu", "bytes", "proc", "rep_set", "kernel", "size", "seed", "test"]

FAILS = []
COUNT = [0]


def check(name, ok, detail=""):
    COUNT[0] += 1
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail)[:600] + "]") if detail and not ok else ""))
    sys.stdout.flush()
    if not ok:
        FAILS.append(name)
    return ok


# ---------- an independent validator of plan format v1 (DECISIONS-bwx8.md, "Plan file") ----------
PHASE = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?):(\d+)$")
TGT = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?)$")
COND = re.compile(r"^[^=|, ]+=[^=|, ]+(\|[^=|, ]+=[^=|, ]+)*$")


def nbytes(tok):
    m = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
    return int(tok[:-1]) * m[tok[-1]] if tok[-1] in m else int(tok)


def parse_plan(text):
    """Returns (header dict, header key order, trials) or raises ValueError that names the defect."""
    if not text.endswith("\n"):
        raise ValueError("no final newline")
    lines = text[:-1].split("\n")
    if len(lines) < 4:
        raise ValueError("fewer than 4 lines")
    if lines[0] != "# bwx8-plan v1":
        raise ValueError("line 1")
    if not lines[1].startswith("# "):
        raise ValueError("line 2")
    head = collections.OrderedDict()
    for pair in lines[1][2:].split(" "):
        k, eq, v = pair.partition("=")
        if not k or not eq or not v or k in head or "," in pair:
            raise ValueError("line 2 pair '%s'" % pair)
        head[k] = v
    for k in ("step", "session", "cpu", "bytes", "proc", "seed", "test"):
        if k not in head:
            raise ValueError("line 2 lacks " + k)
    if lines[2] != "# trial cond rep prev pfx pred tgt nwin win_ms count bins":
        raise ValueError("line 3")
    total = int(head["bytes"])
    seen = collections.Counter()
    trials = []

    def size_ok(tok):
        b = nbytes(tok)
        return b > 0 and b % 256 == 0 and b <= total

    for n, line in enumerate(lines[3:]):
        f = line.split(" ")
        if len(f) != 11 or "" in f:
            raise ValueError("trial line %d: fields" % n)
        trial, cond, rep, prev, pfx, pred, tgt, nwin, win_ms, count, bins = f
        if trial != str(n):
            raise ValueError("trial line %d: number" % n)
        if not COND.match(cond):
            raise ValueError("trial line %d: cond" % n)
        seen[cond] += 1
        if rep != str(seen[cond]) or not 1 <= seen[cond] <= 4:
            raise ValueError("trial line %d: rep" % n)
        ms = {}
        for name, tok in (("prev", prev), ("pfx", pfx), ("pred", pred)):
            ms[name] = 0
            if tok == "-":
                continue
            m = PHASE.match(tok)
            if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)) or int(m.group(3)) < 1:
                raise ValueError("trial line %d: %s" % (n, name))
            ms[name] = int(m.group(3))
        if ms["pfx"] % 4:
            raise ValueError("trial line %d: pfx not a multiple of 4" % n)
        m = TGT.match(tgt)
        if not m or m.group(1) not in READ_KERNELS or not size_ok(m.group(2)):
            raise ValueError("trial line %d: tgt" % n)
        # The limits of the plan parser of bwx8.c: nwin 1 to 4096 (MAX_NWIN), win_ms 1 to 3600000 (MAX_MS).
        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and 1 <= int(win_ms) <= 3600000):
            raise ValueError("trial line %d: windows" % n)
        if count not in ("closed", "open", "read") or bins not in ("0", "1"):
            raise ValueError("trial line %d: count or bins" % n)
        trials.append({"cond": cond, "rep": int(rep), "prev": prev, "pfx": pfx, "pred": pred, "tgt": tgt,
                       "nwin": int(nwin), "win_ms": int(win_ms), "count": count, "bins": int(bins),
                       "ms": ms["prev"] + ms["pfx"] + ms["pred"] + int(nwin) * int(win_ms)})
    return head, list(head), trials


def rejected(text):
    try:
        parse_plan(text)
    except ValueError:
        return True
    return False


# ---------- reading a generated tree ----------
def gen(out, *opts):
    return subprocess.run([sys.executable, SCHED, "--out", out] + list(opts), capture_output=True, text=True)


def load(out):
    """{(step, session): [process]}; a process holds its schedule row, header and trials."""
    tree, errors = {}, []
    for session in (1, 2):
        sdir = os.path.join(out, "s%d" % session)
        for name in sorted(os.listdir(sdir)):
            if not name.endswith(".tsv"):
                continue
            step = name[:-4]
            rows = open(os.path.join(sdir, name)).read().split("\n")
            if rows[0] != "idx\ttag\tcpu\tbytes\tplan\targs" or rows[-1] != "":
                errors.append("%s s%d: header or end of the schedule" % (step, session))
            procs = []
            for n, row in enumerate(rows[1:-1]):
                f = row.split("\t")
                if len(f) != 6 or f[0] != str(n) or f[4] != "%04d.plan" % n:
                    errors.append("%s s%d row %d: columns, idx or plan name" % (step, session, n))
                    continue
                p = {"idx": n, "tag": f[1], "cpu": int(f[2]), "bytes": int(f[3]), "plan": f[4], "args": f[5]}
                want = "--trial --cpus %d --bytes %d --plan sched10/s%d/%s/%s" % (p["cpu"], p["bytes"], session, step, f[4])
                if not (f[5] == want or f[5].startswith(want + " --")):
                    errors.append("%s s%d row %d: args" % (step, session, n))
                p["extra"] = f[5][len(want):]
                try:
                    p["head"], p["order"], p["trials"] = parse_plan(open(os.path.join(sdir, step, f[4])).read())
                except (ValueError, OSError) as e:
                    errors.append("%s s%d row %d: %s" % (step, session, n, e))
                    continue
                h = p["head"]
                if (h["step"], h["session"], h["cpu"], h["bytes"], h["proc"]) != (step, str(session), f[2], f[3], f[0]):
                    errors.append("%s s%d row %d: header pairs differ from the row" % (step, session, n))
                procs.append(p)
            tags = [p["tag"] for p in procs]
            if len(set(tags)) != len(tags) or any(re.search(r"\s", t) for t in tags):
                errors.append("%s s%d: a tag occurs twice or holds a blank" % (step, session))
            if len(os.listdir(os.path.join(sdir, step))) != len(procs):
                errors.append("%s s%d: plan files and rows differ in number" % (step, session))
            tree[step, session] = procs
    return tree, errors


def proc_ms(p):
    return sum(t["ms"] for t in p["trials"])


def tree_bytes(out):
    d = {}
    for root, _, files in os.walk(out):
        for f in files:
            path = os.path.join(root, f)
            d[os.path.relpath(path, out)] = open(path, "rb").read()
    return d


def cpu_blocks(procs, first, second):
    """The CPUs alternate first, second, first, ... when equal neighbours are merged."""
    seq = [k for k, _ in itertools.groupby(p["cpu"] for p in procs)]
    return len(seq) % 2 == 0 and all(c == (first, second)[i % 2] for i, c in enumerate(seq))


def cpus_of(session):
    return (2, 41) if session == 1 else (41, 2)


def one_trial(cond, tgt, nwin, win, count="closed", bins=0, pfx=0):
    return [{"cond": cond, "rep": 1, "prev": "-", "pfx": "%s:%d" % (tgt, pfx) if pfx else "-", "pred": "-", "tgt": tgt,
             "nwin": nwin, "win_ms": win, "count": count, "bins": bins, "ms": pfx + nwin * win}]


def s2_style(p, k, s):
    """4 trials: the kernel at the size, with itself as 1.2 s prefix, 4 windows, uncounted."""
    t = p["trials"]
    return len(t) == 4 and all(
        x == {"cond": "K=%s|S=%s" % (k, s), "rep": i + 1, "prev": "-", "pfx": "%s@%s:%d" % (k, s, 4 * x["win_ms"]),
              "pred": "-", "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": x["win_ms"], "count": "closed", "bins": 0,
              "ms": 8 * x["win_ms"]} for i, x in enumerate(t)) and \
        p["bytes"] == nbytes(s) and p["head"].get("size") == str(nbytes(s)) and p["head"].get("kernel") == k


# ---------- rules of the steps; each returns a list of defects. div: the test divisor of the tree ----------
def yl_rules(procs, cpus, div=1):
    bad = []
    if len(procs) != 32:
        return ["process count %d" % len(procs)]
    conds = sorted((k, n) for k in YL_KERNELS for n in YL)
    for b in range(4):
        block = procs[8 * b:8 * b + 8]
        r, cpu = b // 2 + 1, cpus[b % 2]
        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):
            bad.append("block %d: CPU or rep_set" % b)
        if sorted((p["head"].get("kernel"), p["head"].get("lcond")) for p in block) != conds:
            bad.append("block %d: does not hold every kernel and window plan once" % b)
    for p in procs:
        k, name = p["head"].get("kernel"), p["head"].get("lcond")
        if k not in YL_KERNELS or name not in YL:
            bad.append("process %d: kernel or lcond" % p["idx"])
            continue
        nwin, win, bins = YL[name]
        if p["trials"] != one_trial("K=%s|S=8M|L=%d" % (k, win), k + "@8M", nwin, win // div, "closed", bins):
            bad.append("process %d (%s): trial" % (p["idx"], name))
        if p["bytes"] != 8 << 20 or p["head"].get("size") != str(8 << 20) or p["extra"] \
                or not p["tag"].startswith("%s-%s-" % (name, k)):
            bad.append("process %d (%s): bytes, header, args or tag" % (p["idx"], name))
    if len({tuple((p["head"].get("kernel"), p["head"].get("lcond")) for p in procs[8 * b:8 * b + 8]) for b in range(4)}) < 2:
        bad.append("the condition order is the same in every block")
    return bad


def yp_rules(procs, cpus, div=1):
    bad = []
    if len(procs) != 28:
        return ["process count %d" % len(procs)]
    for b in range(4):
        block = procs[7 * b:7 * b + 7]
        r, cpu = b // 2 + 1, cpus[b % 2]
        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):
            bad.append("block %d: CPU or rep_set" % b)
        if sorted(p["head"].get("pcond") for p in block) != sorted(YP):
            bad.append("block %d: does not hold every condition once" % b)
    for p in procs:
        name = p["head"].get("pcond")
        if name not in YP:
            bad.append("process %d: pcond" % p["idx"])
            continue
        if p["trials"] != one_trial("K=asmread|S=8M|rec=%s" % name, "asmread@8M", 100, 300 // div):
            bad.append("process %d (%s): trial" % (p["idx"], name))
        if p["extra"] != YP[name]:
            bad.append("process %d (%s): the options in args" % (p["idx"], name))
        if p["bytes"] != 8 << 20 or p["head"].get("kernel") != "asmread" or p["head"].get("size") != str(8 << 20) \
                or not p["tag"].startswith(name + "-"):
            bad.append("process %d (%s): bytes, header or tag" % (p["idx"], name))
    if len({tuple(p["head"].get("pcond") for p in procs[7 * b:7 * b + 7]) for b in range(4)}) < 2:
        bad.append("the condition order is the same in every block")
    return bad


def yf_rules(procs, cpus):
    bad = []
    if len(procs) != 288:
        return ["process count %d" % len(procs)]
    sets = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in procs:
        h = p["head"]
        k, s = h.get("kernel"), p["tag"].split("-")[1]
        if k not in YF_KERNELS or s not in YF_SIZES or not s2_style(p, k, s):
            bad.append("process %d: not 4 trials of one kernel of the family with itself as prefix" % p["idx"])
        if p["order"] != HEAD_S2 or p["extra"]:
            bad.append("process %d: header keys or args" % p["idx"])
        sets[s, p["cpu"]][int(h.get("rep_set", 0))].append(k)
    assign = set()
    if len(sets) != 8:
        bad.append("sizes and CPUs")
    for (s, cpu), orders in sets.items():
        o = [tuple(orders[r]) for r in sorted(orders)]
        if sorted(orders) != [1, 2, 3, 4, 5, 6] or any(sorted(x) != sorted(YF_KERNELS) for x in o):
            bad.append("size %s cpu %d: not 6 sets of the 6 kernels" % (s, cpu))
            continue
        pos = collections.Counter((k, i) for x in o for i, k in enumerate(x))
        if len(pos) != 36 or set(pos.values()) != {1}:
            bad.append("size %s cpu %d: a kernel is not once at each position" % (s, cpu))
        pairs = collections.Counter((x[i], x[i + 1]) for x in o for i in range(5))
        if len(pairs) != 30 or set(pairs.values()) != {1}:
            bad.append("size %s cpu %d: an ordered pair of kernels is not once a pair of neighbours" % (s, cpu))
        assign.add(tuple(o))
    if len(assign) < 2:
        bad.append("every size and CPU uses the same kernel orders")
    size_orders = set()
    for r in range(6):
        block = procs[48 * r:48 * r + 48]
        if any(p["head"].get("rep_set") != str(r + 1) for p in block):
            bad.append("block %d: rep_set" % (r + 1))
        sizes = []
        for g in range(4):
            twelve = block[12 * g:12 * g + 12]
            if len({p["bytes"] for p in twelve}) != 1 or [p["cpu"] for p in twelve] != [cpus[0]] * 6 + [cpus[1]] * 6:
                bad.append("block %d group %d: size or CPU order" % (r + 1, g))
            sizes.append(twelve[0]["bytes"])
        if len(set(sizes)) != 4:
            bad.append("block %d: a size is missing" % (r + 1))
        size_orders.add(tuple(sizes))
    if len(size_orders) < 2:
        bad.append("the size order is the same in every block")
    return bad


def yc_rules(procs, cpus, div=1):
    bad = []
    if len(procs) != 42:
        return ["process count %d" % len(procs)]
    if [p["cpu"] for p in procs] != [cpus[0]] * 21 + [cpus[1]] * 21:
        bad.append("CPU blocks are not 21 processes of the first CPU, then 21 of the second")
    cells = sorted((k, s) for k in YC_KERNELS for s in YC_SIZES)
    orders = []
    for b in range(2):
        block = procs[21 * b:21 * b + 21]
        got = [tuple(p["trials"][0]["tgt"].split("@")) for p in block]
        if sorted(got) != cells:
            bad.append("block %d: does not hold every kernel and size once" % b)
        orders.append(got)
    for p in procs:
        k, s = p["trials"][0]["tgt"].split("@")
        if p["trials"] != one_trial("K=%s|S=%s|count=read" % (k, s), "%s@%s" % (k, s), 20, 300 // div, "read"):
            bad.append("process %d: trial" % p["idx"])
        if p["bytes"] != nbytes(s) or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)):
            bad.append("process %d: bytes or header" % p["idx"])
        if p["extra"] != " --pmu-type 11 --events " + EVENTS:
            bad.append("process %d: event set in args" % p["idx"])
    if orders[0] == orders[1]:
        bad.append("the cell order is the same for both CPUs")
    return bad


def ya_rules(procs, div=1):
    bad = []
    if len(procs) != 9:
        return ["process count %d" % len(procs)]
    for p, (tag, k, s, extra) in zip(procs, YA):
        ks = "%s@%s" % (k, s)
        name = tag[:-5]
        if p["tag"] != tag or p["cpu"] != 2 or p["bytes"] != nbytes(s) or p["extra"] != extra \
                or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)) or p["head"].get("acond") != name:
            bad.append("process %d: tag, CPU, bytes, args or header" % p["idx"])
        if p["trials"] != one_trial("K=%s|S=%s|acc=%s" % (k, s, name), ks, 3, 300 // div, "closed", 0, 400 // div):
            bad.append("process %d: trial" % p["idx"])
    return bad


def schedule_checks(tmp):
    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))
    r = gen(a)
    check("schedule10.py runs with status 0", r.returncode == 0, r.stderr)
    tree, errors = load(a)
    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])
    check("the 5 steps exist in session 1; session 2 has the same steps without YA",
          sorted(tree) == sorted([(s, 1) for s in TABLE] + [(s, 2) for s in TABLE if s != "YA"]), sorted(tree))

    # The validator itself rejects defective plans.
    good = open(os.path.join(a, "s1", "YL", "0000.plan")).read()
    good1 = open(os.path.join(a, "s1", "YA", "0000.plan")).read()
    line = good.split("\n")[3]
    bad = {"rep not 1": good.replace(line, line.replace(" 1 - ", " 2 - ", 1)),
           "size above bytes": good1.replace("asmread@8M:400", "asmread@16M:400"),
           "unknown kernel": good1.replace("asmread@8M:400", "copy@8M:400"),
           "prefix without a duration": good1.replace("asmread@8M:400", "asmread@8M"),
           "prefix that is not a multiple of 4 ms": good1.replace("asmread@8M:400", "asmread@8M:401"),
           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),
           "trial number": good.replace("\n0 ", "\n1 ", 1),
           "wrong first line": good.replace("plan v1", "plan v2"),
           "count word": good.replace(line, line.replace("closed", "shut")),
           "bins 2": good.replace(line, line[:-1] + "2"),
           "4097 windows": good.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line)),
           "a window of 3600001 ms": good.replace(line, re.sub(r" (\d+) \d+ closed", r" \1 3600001 closed", line)),
           "comma in cond": good.replace(line, line.replace("|", ",", 1)),
           "blank in cond": good.replace(line, line.replace("|", " ", 1)),
           "header lacks seed": good.replace(" seed=", " sead=")}
    check("validator accepts generated plans", not rejected(good) and not rejected(good1))
    for name, text in bad.items():
        check("validator rejects: " + name, text not in (good, good1) and rejected(text))

    # Counts and nominal work, from the files and from the printed report.
    for step, (n, tr, sec, word) in TABLE.items():
        for s in (1, 2):
            if (step, s) not in tree:
                continue
            procs = tree[step, s]
            ms = sum(proc_ms(p) for p in procs)
            check("%s session %d: %d processes of %d trial(s), %.1f s of nominal kernel work" % (step, s, n, tr, sec),
                  len(procs) == n and all(len(p["trials"]) == tr for p in procs) and ms == round(sec * 1000),
                  (len(procs), ms))
            check("%s session %d: the report prints the binary, the process count and the nominal work" % (step, s),
                  ("\n%s %d %s %d %d %g\n" % (step, s, word, n, n * tr, sec)) in r.stdout, r.stdout[:400])
    check("the report prints the totals of each session: 399 processes and 4828.5 s, 390 processes and 4816.8 s",
          "\nsession 1 total: 399 processes, nominal kernel work 4828.5 s (80.47 min)\n" in r.stdout
          and "\nsession 2 total: 390 processes, nominal kernel work 4816.8 s (80.28 min)\n" in r.stdout, r.stdout[:900])
    check("the report states the balance of YL, YP and YF for both sessions, each with 'yes'",
          len(re.findall(r"^Y[LPF] session [12]: .*: yes$", r.stdout, re.M)) == 6 and ": NO" not in r.stdout, r.stdout[-900:])
    short = copy.deepcopy(tree["YF", 1])
    short[0]["trials"].pop()
    check("nominal work: a schedule with one trial missing does not give the YF value",
          sum(proc_ms(p) for p in short) != 2764800)
    check("one process at a time is at most 30 s of kernel work (YL and YP)",
          max(proc_ms(p) for procs in tree.values() for p in procs) == 30000
          and all(proc_ms(p) == 30000 for st in ("YL", "YP") for p in tree[st, 1]))

    # Header pairs.
    check("plan headers: seed is one value per step and session, test=0",
          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)
              for procs in tree.values()))
    check("plan headers: the seeds of the steps and sessions differ",
          len({procs[0]["head"]["seed"] for procs in tree.values()}) == 9)
    check("plan headers: kernel and size name the target of every trial",
          all(all(t["tgt"].split("@")[0] == p["head"]["kernel"] and nbytes(t["tgt"].split("@")[1]) == int(p["head"]["size"])
                  and int(p["head"]["size"]) == p["bytes"] for t in p["trials"])
              for procs in tree.values() for p in procs))
    check("cond labels are key=value pairs that agree with the trial (kernel, size, counter mode)",
          all(dict(x.split("=") for x in t["cond"].split("|")).get("count", "closed") == t["count"]
              and "K=%s|S=%s" % tuple(t["tgt"].split("@")) == "|".join(t["cond"].split("|")[:2])
              for procs in tree.values() for p in procs for t in p["trials"]))
    check("no trial of round 3 has a previous activity or a predecessor, and only YL L30000 has bins",
          all(t["prev"] == "-" and t["pred"] == "-" and (t["bins"] == 1) == (p["head"].get("lcond") == "L30000")
              for procs in tree.values() for p in procs for t in p["trials"]))

    # CPU order of the sessions.
    for (step, s), procs in sorted(tree.items()):
        if step == "YA":
            continue
        check("%s session %d: CPU order %d then %d" % ((step, s) + cpus_of(s)), cpu_blocks(procs, *cpus_of(s)))
    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["YL", 1], 41, 2))
    check("session 2 is not session 1 with the CPUs exchanged (own random order)",
          all([p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree[st, 1]] !=
              [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree[st, 2]] for st in ("YL", "YP", "YF", "YC")))

    # YL.
    for s in (1, 2):
        d = yl_rules(tree["YL", s], cpus_of(s))
        check("YL session %d: asmread and read at 8M with the 4 window plans once per replicate block and CPU, each trial "
              "30 s (300 x 100, 100 x 300, 30 x 1000 ms without bins, 1 x 30000 ms with bins), no option in args" % s, not d, d[:3])
    check("YL rules reject the session 1 schedule under the session 2 CPU order", bool(yl_rules(tree["YL", 1], (41, 2))))
    m = copy.deepcopy(tree["YL", 1])
    m[0]["trials"][0]["nwin"] += 1
    check("YL rules reject a trial with one more window", bool(yl_rules(m, (2, 41))))
    m = copy.deepcopy(tree["YL", 1])
    for p in m:
        if p["head"]["lcond"] == "L30000":
            p["trials"][0]["bins"] = 0
    check("YL rules reject L30000 without bins", bool(yl_rules(m, (2, 41))))
    m = copy.deepcopy(tree["YL", 1])
    m[0], m[8] = m[8], m[0]
    check("YL rules reject two processes exchanged between blocks", bool(yl_rules(m, (2, 41))))
    fixed = sorted(tree["YL", 1], key=lambda p: (int(p["head"]["rep_set"]), p["cpu"], p["head"]["kernel"], p["head"]["lcond"]))
    check("YL rules reject a fixed condition order in every block",
          yl_rules(fixed, (2, 41)) == ["the condition order is the same in every block"], yl_rules(fixed, (2, 41))[:3])

    # YP.
    for s in (1, 2):
        d = yp_rules(tree["YP", s], cpus_of(s))
        check("YP session %d: asmread at 8M, 100 windows of 300 ms; --rec-pad 0, 80, 400, 1040, 2080, 4000 and --hot-copy "
              "once per replicate block and CPU" % s, not d, d[:3])
    check("YP rules reject the session 1 schedule under the session 2 CPU order", bool(yp_rules(tree["YP", 1], (41, 2))))
    m = copy.deepcopy(tree["YP", 1])
    [p for p in m if p["head"]["pcond"] == "P80"][0]["extra"] = " --rec-pad 800"
    check("YP rules reject a pad that differs from its label", bool(yp_rules(m, (2, 41))))
    m = copy.deepcopy(tree["YP", 1])
    [p for p in m if p["head"]["pcond"] == "hot"][0]["extra"] = ""
    check("YP rules reject the hot condition without --hot-copy", bool(yp_rules(m, (2, 41))))
    m = copy.deepcopy(tree["YP", 1])
    m[0], m[7] = m[7], m[0]
    check("YP rules reject two processes exchanged between blocks", bool(yp_rules(m, (2, 41))))

    # YF.
    for s in (1, 2):
        d = yf_rules(tree["YF", s], cpus_of(s))
        check("YF session %d: S2-style trials, header keys as S2, 6 kernels at 32K, 1M, 8M, 16M; per size and CPU each kernel "
              "once at each position and each ordered pair of kernels once as neighbours; block order as S2" % s, not d, d[:3])
    m = copy.deepcopy(tree["YF", 1])
    for i in range(0, 288, 6):                       # every set in the order of YF_KERNELS
        for p, k in zip(m[i:i + 6], YF_KERNELS):
            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]
            p["head"]["kernel"] = k
            for t in p["trials"]:
                t.update(cond="K=%s|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))
    d = yf_rules(m, (2, 41))
    check("YF rules reject a schedule in which every set has one fixed kernel order",
          any("once at each position" in x for x in d) and any("neighbours" in x for x in d), d[:3])
    m = copy.deepcopy(tree["YF", 1])
    m[5], m[6] = m[6], m[5]
    check("YF rules reject CPUs that alternate inside a size", bool(yf_rules(m, (2, 41))))
    m = copy.deepcopy(tree["YF", 1])
    m[5]["trials"][0]["pfx"] = "asmread@1M:1200" if m[5]["head"]["kernel"] != "asmread" else "read_1pl@1M:1200"
    check("YF rules reject a prefix of another kernel or size", bool(yf_rules(m, (2, 41))))
    check("YF rules reject the session 1 schedule under the session 2 CPU order", bool(yf_rules(tree["YF", 1], (41, 2))))
    check("YF: 6 processes per kernel, size and CPU",
          set(collections.Counter((p["head"]["kernel"], p["bytes"], p["cpu"]) for p in tree["YF", 1]).values()) == {6}
          and len({(p["head"]["kernel"], p["bytes"], p["cpu"]) for p in tree["YF", 1]}) == 48)

    # YC, YA.
    for s in (1, 2):
        d = yc_rules(tree["YC", s], cpus_of(s))
        check("YC session %d: 7 kernels at 1M, 8M, 16M once per CPU, 20 windows of 300 ms, count read, "
              "--pmu-type 11 and the 6 events in args" % s, not d, d[:3])
    m = copy.deepcopy(tree["YC", 1])
    m[0]["trials"][0]["count"] = "closed"
    check("YC rules reject a trial with count closed", bool(yc_rules(m, (2, 41))))
    m = copy.deepcopy(tree["YC", 1])
    m[3]["extra"] = m[3]["extra"].replace("0x4009", "0x4008")
    check("YC rules reject another event code", bool(yc_rules(m, (2, 41))))
    check("YC rules reject the session 1 schedule under the session 2 CPU order", bool(yc_rules(tree["YC", 1], (41, 2))))
    check("the event set: 6 events, names below 32 characters, 6 different names and codes",
          len(EVENTS.split(",")) == 6 and all(re.match(r"^[a-z0-9_]{1,31}=0x[0-9a-f]+$", e) for e in EVENTS.split(","))
          and len({e.split("=")[0] for e in EVENTS.split(",")}) == 6 and len({int(e.split("=")[1], 16) for e in EVENTS.split(",")}) == 6)
    d = ya_rules(tree["YA", 1])
    check("YA: CPU 2 only, 9 processes with --trace in the fixed order (plain, --rec-pad 80, --hot-copy, the 5 new kernels at 8M, "
          "read_pf1024 at 32K), each one trial: prefix 400 ms, 3 windows of 300 ms, count closed, bins 0", not d, d[:3])
    m = copy.deepcopy(tree["YA", 1])
    m[4]["extra"] = ""
    check("YA rules reject a process without --trace", bool(ya_rules(m)))
    check("YA: session 2 has no schedule, no plan folder and no binary file",
          not [f for f in os.listdir(os.path.join(a, "s2")) if f.startswith("YA")])

    # Binary files and sampler markers.
    for s in (1, 2):
        sdir = os.path.join(a, "s%d" % s)
        bins = {f[:-4]: open(os.path.join(sdir, f)).read() for f in os.listdir(sdir) if f.endswith(".bin")}
        check("session %d: one .bin file per step; YL names bwx8, every other step names bwx10; one word and a newline" % s,
              bins == {st: TABLE[st][3] + "\n" for st in TABLE if (st, s) in tree}, bins)
        check("session %d: no .watch file (no step of round 3 runs with the host sampler)" % s,
              not [f for f in os.listdir(sdir) if f.endswith(".watch")])

    # Determinism.
    gen(b)
    r3 = gen(c, "--seed", "7")
    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)
    nfiles = 1 + sum(TABLE[s][0] + 2 for s in TABLE) + sum(TABLE[s][0] + 2 for s in TABLE if s != "YA")
    check("two runs with one base seed give the same bytes (%d files)" % nfiles, ta == tb and len(ta) == nfiles, len(ta))
    check("another base seed gives the same file names and other bytes",
          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc
          and all(ta["s1/%s.tsv" % s] != tc["s1/%s.tsv" % s] for s in ("YL", "YP", "YF", "YC")))
    check("the base seed and the seed of every step and session are saved in MANIFEST.txt",
          b"base_seed=20261115\ntest_divisor=1\n" in ta["MANIFEST.txt"] and b"base_seed=7\n" in tc["MANIFEST.txt"]
          and all(("seed %s s%d %s\n" % (st, s, procs[0]["head"]["seed"])).encode() in ta["MANIFEST.txt"]
                  for (st, s), procs in tree.items()))
    check("MANIFEST.txt names the binary of every step and session, and states that no step has a sampler marker",
          all(("bin %s s%d %s\n" % (st, s, TABLE[st][3])).encode() in ta["MANIFEST.txt"] for (st, s) in tree)
          and ta["MANIFEST.txt"].count(b"\nbin ") == 9 and ta["MANIFEST.txt"].endswith(b"\nwatch none\n"), ta["MANIFEST.txt"][-200:])
    tree7, errors7 = load(c)
    check("another base seed keeps the rules (grammar, YL, YP, YF, YC, YA)",
          not errors7 and not yl_rules(tree7["YL", 2], (41, 2)) and not yf_rules(tree7["YF", 1], (2, 41))
          and not yp_rules(tree7["YP", 2], (41, 2)) and not yc_rules(tree7["YC", 1], (2, 41)) and not ya_rules(tree7["YA", 1]))
    saved = os.path.join(Y, "sched10")
    check("the saved sched10/ beside the scripts is the output of the default base seed",
          os.path.isdir(saved) and tree_bytes(saved) == ta)
    src = open(SCHED).read()
    check("schedule10.py imports the standard library only (no file of round 1 or 2)",
          sorted(set(re.findall(r"^(?:import|from) (\w+)", src, re.M))) == ["argparse", "hashlib", "os", "random", "shutil", "sys"]
          and "sys.path" not in src, sorted(set(re.findall(r"^(?:import|from) (\w+)", src, re.M))))
    check("hostwatch.py in this folder is the file of round 2, byte for byte",
          open(WATCH, "rb").read() == open(os.path.join(X, "hostwatch.py"), "rb").read())

    # --test-divisor.
    t = os.path.join(tmp, "t")
    r6 = gen(t, "--test-divisor", "100")
    ttree, terr = load(t)
    check("--test-divisor 100: valid plans, test=1, every duration divided by 100, window counts unchanged",
          r6.returncode == 0 and not terr and sorted(ttree) == sorted(tree)
          and all(p["head"]["test"] == "1" for pp in ttree.values() for p in pp)
          and all(sum(proc_ms(p) for p in ttree[k]) * 100 == sum(proc_ms(p) for p in tree[k]) for k in tree)
          and all([t_["nwin"] for p in ttree[k] for t_ in p["trials"]] == [t_["nwin"] for p in tree[k] for t_ in p["trials"]]
                  for k in tree)
          and not yl_rules(ttree["YL", 1], (2, 41), 100) and not yp_rules(ttree["YP", 1], (2, 41), 100)
          and not yc_rules(ttree["YC", 2], (41, 2), 100) and not ya_rules(ttree["YA", 1], 100)
          and not yf_rules(ttree["YF", 1], (2, 41)), terr[:3])
    for div in ("7", "3", "300", "0"):
        check("--test-divisor %s is refused (it does not divide 100 ms, the shortest window)" % div,
              gen(os.path.join(tmp, "u"), "--test-divisor", div).returncode != 0 and not os.path.exists(os.path.join(tmp, "u")))
    return a, t


# ---------- plans through a local stand-in binary ----------
def stand_in_jobs(d, steps, alt, sessions=(1, 2), only=None):
    """Jobs for the plans of `steps` in the tree d/sched10. CPU 41 is rewritten to `alt` in that tree."""
    jobs = []
    for session in sessions:
        sdir = os.path.join(d, "sched10", "s%d" % session)
        for step in steps:
            if not os.path.exists(os.path.join(sdir, step + ".tsv")):
                continue
            for n, row in enumerate(open(os.path.join(sdir, step + ".tsv")).read().split("\n")[1:-1]):
                if only is not None and n not in only:
                    continue
                f = row.split("\t")
                args = f[5]
                plan = os.path.join(sdir, step, f[4])
                text = open(plan).read()
                if f[2] == "41" and alt != 41:
                    args = args.replace("--cpus 41 ", "--cpus %d " % alt)
                    with open(plan, "w") as out:
                        out.write(text.replace(" cpu=41 ", " cpu=%d " % alt))
                trials = [l.split(" ") for l in text.split("\n")[3:-1]]
                jobs.append((step, session, f[0], args.split(), len(trials), sum(int(t[7]) for t in trials),
                             sum((1 if t[3] != "-" else 0) + (4 if t[4] != "-" else 0) for t in trials),
                             sum(int(t[7]) * (int(t[8]) // 10 + 2) for t in trials if t[10] == "1")))
    return jobs


def run_job(binary, d, env, job):
    """None if the binary accepted the plan and printed every planned row, or a tuple that describes the defect."""
    step, session, idx, args, ntr, nwin, nother, nbins = job
    try:
        r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return (step, session, idx, "timeout")
    rows = collections.Counter()
    for l in r.stdout.split("\n"):
        f = l.split(",")
        rows[f[0] if f[0] != "W" else "W." + ("target" if f[2] == "target" else "other")] += 1
    m = dict(l.split(",", 2)[1:] for l in r.stdout.split("\n") if l.startswith("M,") and l.count(",") >= 2)
    ok = r.returncode == 0 and rows["S"] == ntr and rows["E"] == ntr and rows["W.target"] == nwin \
        and rows["W.other"] == nother and m.get("plan.step") == step and m.get("plan.proc") == idx \
        and m.get("mode") == "trial" and m.get("rec_bins") == str(nbins) and (rows["B"] >= 1) == (nbins > 0)
    if ok and "--events" in args:
        ok = m.get("pmu_type") == "11" and m.get("events", "").count(";") == 5 and rows["C"] + rows["X"] >= 1
    if ok and "--trace" in args:
        ok = m.get("trace") == "1" and rows["TR"] >= 1
    return None if ok else (step, session, idx, r.returncode, r.stderr[-200:], dict(rows))


def local_cpus():
    allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)
    if not check("this machine allows CPU 0, CPU 2 and one more CPU below 120", 0 in allowed and 2 in allowed and len(allowed) > 2):
        return None
    return 41 if 41 in allowed else [c for c in allowed if c not in (0, 2)][0]


def bwx8_checks(tmp, real, sched):
    d = os.path.join(tmp, "bwx8")
    os.makedirs(d)
    binary = os.path.join(d, "bwx8")
    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, os.path.join(X, "bwx8.c")], capture_output=True, text=True)
    if not check("stand-in build of bwx8.c of round 1 in a temporary folder (flags of build8.sh)", r.returncode == 0, r.stdout + r.stderr):
        return
    alt = local_cpus()
    if alt is None:
        return
    shutil.copytree(sched, os.path.join(d, "sched10"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}
    jobs = stand_in_jobs(d, ["YL"], alt)
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda j: run_job(binary, d, env, j), jobs))
    for session in (1, 2):
        res = [x for j, x in zip(jobs, results) if j[1] == session]
        bad = [x for x in res if x]
        check("YL session %d (test divisor 100): bwx8 accepts each of the %d plans with its args: status 0, one S and one E row "
              "per trial, every planned window as a W row, B rows only for the plan with bins" % (session, len(res)),
              len(res) == 32 and not bad, bad[:2])
    check("all %d plans of the bwx8 step ran through bwx8 (%.0f s)" % (len(jobs), time.time() - t0),
          len(jobs) == 64 and all(x is None for x in results))
    # The real window plans, test divisor 1: the first replicate block of session 1 holds every kernel and
    # window plan once, all on CPU 2. Each process is 30 s of kernel work; the 8 run at the same time.
    if "--no-long" in sys.argv[1:]:
        print("SKIP  the 8 runs of 30 s of the real YL window plans through bwx8 (--no-long)")
    else:
        dr = os.path.join(tmp, "bwx8real")
        os.makedirs(dr)
        shutil.copytree(real, os.path.join(dr, "sched10"))
        jobs = stand_in_jobs(dr, ["YL"], alt, sessions=(1,), only=set(range(8)))
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda j: run_job(binary, dr, env, j), jobs))
        bad = [x for x in results if x]
        forms = sorted((j[5], j[7]) for j in jobs)
        check("YL real plans (test divisor 1, first block of session 1, %.0f s): bwx8 accepts 300 x 100 ms, 100 x 300 ms, "
              "30 x 1000 ms and 1 x 30000 ms with bins (3002 bin records) for both kernels and prints every window" % (time.time() - t0),
              forms == [(1, 3002)] * 2 + [(30, 0)] * 2 + [(100, 0)] * 2 + [(300, 0)] * 2 and not bad, (forms, bad[:2]))
    # The acceptance means something only if bwx8 refuses a defective plan.
    plan = os.path.join(d, "sched10", "s1", "YL", "0000.plan")
    text = open(plan).read()
    line = text.split("\n")[3]
    args = ["--trial", "--cpus", "2", "--bytes", "8388608", "--plan"]
    for name, bad in (("an unknown kernel", text.replace("@", "x@")),
                      ("a size above --bytes", text.replace("@8M", "@64M")),
                      ("4097 windows", text.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line))),
                      ("a window of 3600001 ms", text.replace(line, re.sub(r" (\d+) \d+ closed", r" \1 3600001 closed", line))),
                      ("bins 2", text.replace(line, line[:-1] + "2"))):
        p = os.path.join(d, "bad.plan")
        with open(p, "w") as f:
            f.write(bad)
        r = subprocess.run([binary] + args + [p], env=env, capture_output=True, text=True)
        check("bwx8 refuses a plan with %s (status 2)" % name, bad != text and r.returncode == 2, (r.returncode, r.stderr))
    row = open(os.path.join(d, "sched10", "s1", "YP.tsv")).read().split("\n")[1].split("\t")
    r = subprocess.run([binary] + row[5].split(), cwd=d, env=env, capture_output=True, text=True)
    check("the old bwx8 refuses the args of a YP process (--rec-pad or --hot-copy): a wrong .bin word cannot run such a step",
          r.returncode != 0 and ("--rec-pad" in row[5] or "--hot-copy" in row[5]), (r.returncode, r.stderr[-200:]))


def bwx10_checks(tmp, sched):
    src = os.path.join(Y, "bwx10.c")
    if "--no-bwx10" in sys.argv[1:]:
        print("SKIP  the run of the plans of YA, YP, YF and YC through a local stand-in bwx10 (--no-bwx10)")
        return
    if not os.path.exists(src):
        print("SKIP  the run of the plans of YA, YP, YF and YC through a local stand-in bwx10 (bwx10.c is not in this folder)")
        return
    d = os.path.join(tmp, "bwx10")
    os.makedirs(d)
    binary = os.path.join(d, "bwx10")
    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, src], capture_output=True, text=True)
    if r.returncode != 0:
        print("SKIP  the run of the plans of YA, YP, YF and YC through a local stand-in bwx10 (bwx10.c does not build here: %s)"
              % (r.stdout + r.stderr).strip().split("\n")[0][:200])
        return
    alt = local_cpus()
    if alt is None:
        return
    shutil.copytree(sched, os.path.join(d, "sched10"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}
    r = subprocess.run([binary, "--list"], env=env, capture_output=True, text=True)
    check("the stand-in bwx10 lists the kernels of round 3 (asmread, read, oldread and the 5 new ones)",
          r.returncode == 0 and set(NEW_KERNELS + ["asmread", "read", "oldread"]) <= set(r.stdout.split()), r.stdout[:300])
    jobs = stand_in_jobs(d, ["YA", "YP", "YF", "YC"], alt)
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda j: run_job(binary, d, env, j), jobs))
    per = collections.defaultdict(list)
    for job, res in zip(jobs, results):
        per[job[0], job[1]].append(res)
    for (step, session), res in sorted(per.items(), key=lambda x: (x[0][1], x[0][0])):
        bad = [x for x in res if x]
        check("%s session %d (test divisor 100): the stand-in bwx10 accepts each of the %d plans with its args: status 0, one S and "
              "one E row per trial, every planned window as a W row" % (step, session, len(res)),
              len(res) == TABLE[step][0] and not bad, bad[:2])
    check("all %d plans of the bwx10 steps ran through the stand-in bwx10 (%.0f s)" % (len(jobs), time.time() - t0),
          len(jobs) == 9 + 2 * (28 + 288 + 42) and all(x is None for x in results))


# ---------- run_bwx10.sh with dummy binaries ----------
DUMMY = """#!/usr/bin/env bash
# Stand-in for @WORD@: records its process ids and its own path, checks the plan file, sleeps, ends with DUMMY_EXIT.
echo "$$ $*" >> "$DUMMY_LOG"
echo "$0" >> "$DUMMY_LOG.bin"
grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"
echo "PMU=${BWX_PMU_TYPE:-} EV=${BWX_EVENTS:-}" >> "$DUMMY_LOG.env"
while (( $# )); do if [[ $1 == --plan && ! -r $2 ]]; then echo "no plan $2" >&2; exit 7; fi; shift; done
echo "M,dummy,@WORD@"
sleep "${DUMMY_SLEEP:-0}" & echo "$! sleep" >> "$DUMMY_LOG"
wait $!
# DUMMY_TOUCH=1: the marker file appears when this process ends.
[[ -z ${DUMMY_TOUCH:-} ]] || : > "$BWX8_MARKER"
exit "${DUMMY_EXIT:-0}"
"""

PS_STUB = """#!/usr/bin/env bash
# Stand-in for ps: its second call creates the file named by PS_TOUCH. Then it runs the real ps.
# run_bwx10.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.
if [[ -n ${PS_TOUCH:-} ]]; then
  echo call >> "$PS_TOUCH.calls"
  if (( $(wc -l < "$PS_TOUCH.calls") == 2 )); then : > "$PS_TOUCH"; fi
fi
exec %s "$@"
"""

SSH_STUB = """#!/bin/bash
# Stand-in for ssh: records the remote command (its last argument). It opens no connection.
printf '%s\\n' "${@: -1}" >> "$SSH_LOG"
"""


def cpu_list(text):
    cpus = set()
    for part in text.split(":")[1].strip().split(","):
        a, _, b = part.partition("-")
        cpus.update(range(int(a), int(b or a) + 1))
    return cpus


def utc(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def sha256(path):
    return subprocess.run(["sha256sum", path], capture_output=True, text=True).stdout.split()[0]


def samplers(path_part):
    """Process ids of running hostwatch.py processes whose command line names this path."""
    found = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                cmd = open("/proc/%s/cmdline" % pid, "rb").read().decode("utf-8", "replace")
            except OSError:
                continue
            if "hostwatch.py" in cmd and path_part in cmd:
                found.append(int(pid))
    return found


def dummy(folder, word):
    """Writes the dummy binary `word` and its build record into `folder`. Returns the path of the binary."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, word)
    with open(path, "w") as f:
        f.write(DUMMY.replace("@WORD@", word))
    os.chmod(path, 0o755)
    with open(os.path.join(folder, "build.txt"), "w") as f:
        f.write("dummy build record of %s\n" % word)
    return path


class Box:
    """A copy of run_bwx10.sh and hostwatch.py with a test schedule in a temporary folder. The dummy bwx10 is beside
    the script, as on CRB. The dummy bwx8 is in its own folder with its own build record."""

    def __init__(self, tmp, sched):
        self.dir = os.path.join(tmp, "box")
        os.makedirs(self.dir)
        shutil.copy(RUN, self.dir)
        shutil.copy(WATCH, self.dir)
        shutil.copytree(sched, os.path.join(self.dir, "sched10"))
        self.bin10 = dummy(self.dir, "bwx10")
        self.bin8 = dummy(os.path.join(tmp, "old8"), "bwx8")
        # A home folder with the accepted bwx8 at the path that run_bwx10.sh uses on CRB.
        self.home = os.path.join(tmp, "home")
        self.home8 = dummy(os.path.join(self.home, "cache-perf", "bwx8-20261114"), "bwx8")
        os.makedirs(os.path.join(self.dir, "bin"))
        stub = os.path.join(self.dir, "bin", "ps")
        with open(stub, "w") as f:
            f.write(PS_STUB % shutil.which("ps"))
        os.chmod(stub, 0o755)
        self.watch_cpu = str(sorted(os.sched_getaffinity(0))[-1])
        self.n = 0

    def sched(self, *parts):
        return os.path.join(self.dir, "sched10", *parts)

    def rows(self, step, session=1):
        text = open(self.sched("s%d" % session, step + ".tsv")).read()
        return [r.split("\t") for r in text.split("\n")[1:-1]]

    def start(self, args, pre=(), **env):
        """Starts the script in fresh result, marker and log paths. Returns the process."""
        self.n += 1
        self.case = os.path.join(self.dir, "case%d" % self.n)
        os.makedirs(self.case)
        self.results = os.path.join(self.case, "results")
        self.marker = os.path.join(self.case, "RUNNING")
        self.stopfile = os.path.join(self.case, "STOP")
        self.log = os.path.join(self.case, "dummy.log")
        e = {k: v for k, v in os.environ.items()
             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256", "BWX10_SHA256",
                          "BWX_PMU_TYPE", "BWX_EVENTS", "WATCH_CPU")}
        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin8, BWX10_BIN=self.bin10,
                 BWX8_RESULTS=self.results, DUMMY_LOG=self.log, WATCH_CPU=self.watch_cpu)
        e.update(env)
        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out
        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx10.sh")] + args, env=e, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)

    def run(self, args, pre=(), **env):
        p = self.start(args, pre, **env)
        out, err = p.communicate(timeout=900)
        return p.returncode, out, err

    def folders(self):
        return sorted(os.path.join(self.results, d) for d in os.listdir(self.results)) if os.path.isdir(self.results) else []

    def folder(self):
        d = self.folders()
        return d[0] if len(d) == 1 else None

    def file(self, name):
        f = self.folder()
        path = os.path.join(f, name) if f else ""
        return open(path).read() if os.path.exists(path) else ""

    def csv(self, step):
        return self.file(step + ".csv")

    def launched(self):
        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []

    def binaries(self):
        """The path of the dummy of each launch, in order."""
        return open(self.log + ".bin").read().split("\n")[:-1] if os.path.exists(self.log + ".bin") else []

    def wait_launch(self):
        end = time.time() + 90
        while time.time() < end and len(self.launched()) < 2:
            time.sleep(0.2)
        return len(self.launched()) >= 2

    def none_alive(self):
        time.sleep(0.5)
        for l in self.launched():
            try:
                os.kill(int(l.split()[0]), 0)
                return False
            except OSError:
                pass
        return not samplers(self.case)


def visit_checks(tmp):
    """visit10.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""
    d = os.path.join(tmp, "visit")
    os.makedirs(os.path.join(d, "bin"))
    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())
    copy_path = os.path.join(d, "visit10.sh")
    with open(copy_path, "w") as f:
        f.write(text)
    with open(os.path.join(d, "bin", "ssh"), "w") as f:
        f.write(SSH_STUB)
    os.chmod(os.path.join(d, "bin", "ssh"), 0o755)
    os.symlink(shutil.which("date"), os.path.join(d, "bin", "date"))
    log = os.path.join(d, "ssh.log")

    def visit(name, **env):
        if os.path.exists(log):
            os.remove(log)
        e = {"PATH": os.path.join(d, "bin"), "SSH_LOG": log, "HOME": d}
        e.update(env)
        r = subprocess.run([shutil.which("bash"), copy_path, name, "YA", "YL"], env=e, capture_output=True, text=True)
        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr

    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",
                         BWX8_SHA256="0a1b", BWX10_SHA256="2c3d", ENVV="RESERVE=90")
    check("visit10.sh: one login; the marker check is the first remote action, then run_bwx10.sh in ~/cache-perf/bwx10-20261115 "
          "with both digests",
          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1
          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")
          and cmd.endswith("exit 3; fi; cd ~/cache-perf/bwx10-20261115 && STOP_AT=2026-11-15T15:00Z SESSION=2 "
                           "SESSION1_END=2026-11-15T03:00Z BWX8_SHA256=0a1b BWX10_SHA256=2c3d RESERVE=90 ./run_bwx10.sh YA YL\n")
          and open(os.path.join(d, "ok.log")).read().startswith("ssh status 0 utc "), (rc, cmd, err))
    rc, cmd, err = visit("plain", STOP_AT="none", SESSION="1")
    check("visit10.sh without digests and SESSION1_END: the three settings are passed empty",
          rc == 0 and cmd is not None and cmd.endswith("STOP_AT=none SESSION=1 SESSION1_END= BWX8_SHA256= BWX10_SHA256=  ./run_bwx10.sh YA YL\n"),
          (rc, cmd, err))
    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b", "BWX10_SHA256": "2c3d"}
    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),
                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b|x"), ("BWX10_SHA256", "2c3d x"),
                       ("BWX10_SHA256", "2c3d;id")):
        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))
        check("visit10.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),
              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")), (rc, cmd, err))
    rc, cmd, err = visit("nostop", SESSION="1")
    check("visit10.sh: STOP_AT not set: no login", rc != 0 and cmd is None, (rc, cmd, err))
    a, b = open(os.path.join(X, "visit9.sh")).read().split("\n"), open(VISIT).read().split("\n")
    back = [l.replace("./run_bwx10.sh", "./run_bwx9.sh").replace("bwx10-20261115", "bwx8-20261114")
            .replace(" BWX10_SHA256=${BWX10_SHA256:-}", "").replace(" BWX10_SHA256;", ";") for l in b if not l.startswith("#")]
    check("visit10.sh differs from visit9.sh only in comment lines, the folder on CRB, the script that it starts and BWX10_SHA256",
          [l for l in a if not l.startswith("#")] == back, [x for x in back if x not in a][:2])
    check("visit10.sh names one host only, the CRB login of the handoff, and starts ssh once",
          re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", open(VISIT).read()) == ["192.168.2.45"]
          and len(re.findall(r"(?m)^ssh ", open(VISIT).read())) == 1 and "scp" not in open(VISIT).read())


def run_checks(tmp, sched):
    for f in ("run_bwx10.sh", "visit10.sh"):
        r = subprocess.run(["bash", "-n", os.path.join(Y, f)], capture_output=True, text=True)
        check("bash -n " + f, r.returncode == 0, r.stderr)
    # The stop controls and the launch function are the text of run_bwx9.sh.
    part = re.compile(r"(?s)\n# ---- stop controls[^\n]*\n(.*?\n)# ---- end of the copied part ----\n")
    old, new = part.search(open(os.path.join(X, "run_bwx9.sh")).read()), part.search(open(RUN).read())
    check("run_bwx10.sh keeps the stop controls and the launch function of run_bwx9.sh unchanged (54 lines: why_stop, "
          "check_marker, check_deadline, the trap, settle, one, stop_child, stop_watch)",
          old is not None and new is not None and old.group(1) == new.group(1) and old.group(1).count("\n") == 54
          and all(w in new.group(1) for w in ("why_stop()", "check_marker()", "check_deadline()", "trap '", "settle()", "one()")),
          old and old.group(1).count("\n"))
    box = Box(tmp, sched)
    absent = os.path.join(box.dir, "absent")

    # ---- steps and the dry run ----
    for name in ("S2", "XW", "Yl", "Y", "Y-1", "YL;id"):
        rc, out, err = box.run(["--dry-run", name], SESSION="1")
        check("step name '%s' is refused with status 2" % name, rc == 2 and "unknown step" in err and not out, (rc, err))
    rc, out, err = box.run(["--dry-run", "YZ9"], SESSION="1")
    check("a name of the right form without a schedule: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))
    rc, out, err = box.run(["--dry-run", "YF", "YF"], SESSION="1")
    check("a step named twice: status 2", rc == 2 and "twice" in err and "step YF" not in out, (rc, err))
    rc, out, err = box.run(["--dry-run", "YA", "YL", "YP", "YF", "YC"], SESSION="1", BWX8_BIN=absent, BWX10_BIN=absent)
    want = {"YA": "9 processes, nominal kernel work 0.117 s", "YL": "32 processes, nominal kernel work 9.600 s",
            "YP": "28 processes, nominal kernel work 8.400 s", "YF": "288 processes, nominal kernel work 27.648 s",
            "YC": "42 processes, nominal kernel work 2.520 s"}
    check("--dry-run of all 5 steps, session 1, without the binaries and without counter settings: status 0, the counts of each step "
          "(9, 32, 28, 288, 42)",
          rc == 0 and all(("step %s session 1: %s" % kv) in out for kv in want.items())
          and out.count("\nbwx8 --trial ") == 32 and out.count("\nbwx10 --trial ") == 367 and "warning" in err, (rc, out[:300], err[-300:]))
    check("--dry-run: the command lines are the binary word of the step and the args column",
          all(("%s %s  # idx %s, tag %s, nominal " % (TABLE[st][3], r[5], r[0], r[1])) in out
              for st in want for r in box.rows(st)) and out.count(" --pmu-type 11 --events ") == 42
          and out.count(" --rec-pad ") == 25 and out.count(" --hot-copy") == 5 and out.count(" --trace") == 9)
    check("--dry-run: the binary of each step is printed (YL bwx8, the others bwx10)",
          sorted(re.findall(r"^step (\S+) binary: (\S+)$", out, re.M)) == sorted((st, TABLE[st][3]) for st in TABLE), out[:500])
    check("--dry-run: no host sampler is announced", "host sampler" not in out)
    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))
    rc, out, err = box.run(["--dry-run", "YL", "YP", "YF", "YC"], SESSION="2")
    check("--dry-run session 2: the first command line of each step uses CPU 41",
          rc == 0 and len(re.findall(r"# ---- step \S+ session 2 ----\n.*\n.*\n.*\nbwx(?:8|10) --trial --cpus 41 ", out)) == 4, (rc, out[:500]))
    rc, out, err = box.run(["--dry-run", "YA"], SESSION="2")
    check("YA in session 2: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))
    rc, out, err = box.run(["--dry-run", "YF"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX10_BIN=None,
                           BWX8_RESULTS=None)
    check("no warning without the test settings", rc == 0 and "warning" not in err, err)
    rc, out, err = box.run(["--dry-run", "YF"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX8_RESULTS=None)
    check("BWX10_BIN alone gives its warning", rc == 0 and err.count("warning") == 1 and "BWX10_BIN" in err, err)

    # ---- a normal run of a bwx10 step: YA ----
    rows = box.rows("YA")
    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none")
    f = box.folder()
    csv = box.csv("YA")
    heads = re.findall(r"^-- step YA session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)
    check("YA normal end: status 0, the counts are printed before the result folder is made",
          rc == 0 and 0 <= out.find("step YA session 1: 9 processes") < out.find("result folder: "), (rc, err, out))
    check("YA normal end: folder name bwx10-YA-s1-<UTC> and its six files, no sampler file",
          f is not None and re.match(r"^bwx10-YA-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None
          and sorted(os.listdir(f)) == ["YA.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],
          f and os.listdir(f))
    check("YA normal end: one header line per process in schedule order, each followed by its output; schedule.tsv is a copy",
          heads == [(r[0], r[1], r[5]) for r in rows] and csv.count("M,dummy,bwx10\n") == 9 and "-- killed" not in csv
          and "-- failed" not in csv and box.file("schedule.tsv") == open(box.sched("s1", "YA.tsv")).read(), heads)
    launched = [l for l in box.launched() if not l.endswith(" sleep")]
    check("YA normal end: the binary gets the args column (--trace, --rec-pad 80, --hot-copy), no counter setting in its environment",
          [l.split(" ", 1)[1] for l in launched] == [r[5] for r in rows] and launched[1].endswith(" --trace --rec-pad 80")
          and launched[2].endswith(" --trace --hot-copy") and open(box.log + ".env").read() == "PMU= EV=\n" * 9 and box.none_alive(), launched)
    check("YA normal end: every process is the binary named bwx10, and build.txt is the build record beside it",
          box.binaries() == [box.bin10] * 9 and box.file("build.txt") == "dummy build record of bwx10\n", box.binaries()[:2])
    env = box.file("env.txt")
    check("YA normal end: env.txt holds session, from, load, the word and the digests of the binary, of run_bwx10.sh, of the schedule "
          "and of the build record, paths, end line",
          "session=1 from=0 " in env and "loadavg=" in env and "## end utc=" in env and "/run_bwx10.sh\n" in env
          and "/sched10/s1/YA.tsv\n" in env and "host sampler" not in env and " binary=bwx10 " in env
          and ("%s  %s\n" % (sha256(box.bin10), box.bin10)) in env
          and ("%s  %s\n" % (sha256(os.path.join(box.dir, "build.txt")), os.path.join(box.dir, "build.txt"))) in env
          and (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin10, box.results)) in env
          and box.file("launches.txt").count("== YA.csv idx ") == 9, env)

    # ---- the binary of a step ----
    rc, out, err = box.run(["--from", "30", "YL"], SESSION="1", STOP_AT="none")
    env = box.file("env.txt")
    check("YL (word bwx8): the two processes are the old binary, build.txt is the record from its folder, env.txt names it",
          rc == 0 and box.binaries() == [box.bin8] * 2 and box.file("build.txt") == "dummy build record of bwx8\n"
          and " binary=bwx8 " in env and (" BIN=%s RESULTS=" % box.bin8) in env and ("%s  %s\n" % (sha256(box.bin8), box.bin8)) in env
          and ("  %s\n" % os.path.join(os.path.dirname(box.bin8), "build.txt")) in env
          and os.path.basename(box.folder() or "").startswith("bwx10-YL-s1-") and box.csv("YL").count("M,dummy,bwx8\n") == 2
          and "to run from idx 30: 2 processes" in out, (rc, err, box.binaries()))
    # Both words in one call: the schedules of YL and YA are cut to their first two rows for this case.
    saved = {st: open(box.sched("s1", st + ".tsv")).read() for st in ("YL", "YA")}
    for st, text in saved.items():
        with open(box.sched("s1", st + ".tsv"), "w") as fh:
            fh.write("\n".join(text.split("\n")[:3]) + "\n")
    rc, out, err = box.run(["YL", "YA"], SESSION="1", STOP_AT="none")
    fl = box.folders()
    check("one call with a bwx8 step and a bwx10 step: each step starts its own binary and copies its own build record",
          rc == 0 and box.binaries() == [box.bin8] * 2 + [box.bin10] * 2 and len(fl) == 2
          and open(os.path.join(fl[0], "build.txt")).read() == "dummy build record of bwx10\n" and "bwx10-YA-s1-" in fl[0]
          and open(os.path.join(fl[1], "build.txt")).read() == "dummy build record of bwx8\n" and "bwx10-YL-s1-" in fl[1],
          (rc, err, box.binaries(), fl))
    for st, text in saved.items():
        with open(box.sched("s1", st + ".tsv"), "w") as fh:
            fh.write(text)
    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none", BWX8_BIN=None, BWX10_BIN=None, HOME=box.home)
    check("without the test settings the word bwx8 is $HOME/cache-perf/bwx8-20261114/bwx8, with the build record of that folder",
          rc == 0 and box.binaries() == [box.home8] and box.file("build.txt") == "dummy build record of bwx8\n"
          and (" BIN=%s RESULTS=" % box.home8) in box.file("env.txt"), (rc, err, box.binaries()))
    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", BWX8_BIN=None, BWX10_BIN=None, HOME=box.home)
    check("without the test settings the word bwx10 is bwx10 beside run_bwx10.sh",
          rc == 0 and box.binaries() == [box.bin10] and (" BIN=%s RESULTS=" % box.bin10) in box.file("env.txt"), (rc, err, box.binaries()))
    binfile = box.sched("s1", "YL.bin")
    made = os.path.join(box.dir, "made-by-bin")
    for what, content in (("another word", "bwx9\n"), ("two words", "bwx8 bwx10\n"), ("two lines", "bwx8\nbwx10\n"), ("nothing", ""),
                          ("a path", "/bin/true\n"), ("a command", "$(touch %s)\n" % made)):
        with open(binfile, "w") as fh:
            fh.write(content)
        rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none")
        rc2, out2, err2 = box.run(["--dry-run", "YL"], SESSION="1")
        check("YL.bin with %s: status 2 in a run and in a dry run, nothing starts, no result folder" % what,
              rc == 2 and rc2 == 2 and "must hold the one word bwx8 or bwx10" in err and "must hold" in err2
              and not box.launched() and not os.path.exists(box.results) and not os.path.exists(made) and "bwx" not in out2, (rc, err, rc2))
    os.remove(binfile)
    rc, out, err = box.run(["YA", "YL"], SESSION="1", STOP_AT="none")
    check("YL.bin missing, YL second in the call: status 2 before the first process of the call",
          rc == 2 and "YL.bin (the binary of step YL)" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    with open(binfile, "w") as fh:
        fh.write("bwx10\n")
    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none")
    check("the word decides, not the step name: YL.bin with bwx10 starts the binary bwx10",
          rc == 0 and box.binaries() == [box.bin10] and " binary=bwx10 " in box.file("env.txt"), (rc, err))
    with open(binfile, "w") as fh:
        fh.write("bwx8\n")

    # ---- the digests ----
    d8, d10, zero = sha256(box.bin8), sha256(box.bin10), "0" * 64
    check("the two dummy binaries differ, so each digest names one of them", d8 != d10)
    cases = [("BWX8_SHA256 wrong, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=zero), 2),
             ("BWX8_SHA256 wrong, a bwx10 step only (bwx8 is not used, so it is not checked)", ["--from", "8", "YA"], dict(BWX8_SHA256=zero), 0),
             ("BWX10_SHA256 wrong, a bwx10 step", ["--from", "8", "YA"], dict(BWX10_SHA256=zero), 2),
             ("BWX10_SHA256 wrong, a bwx8 step only (bwx10 is not used, so it is not checked)", ["--from", "31", "YL"], dict(BWX10_SHA256=zero), 0),
             ("BWX8_SHA256 right, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=d8), 0),
             ("BWX10_SHA256 right, a bwx10 step", ["--from", "8", "YA"], dict(BWX10_SHA256=d10), 0),
             ("both right, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=d8, BWX10_SHA256=d10), 0),
             ("BWX8_SHA256 holds the digest of bwx10, a bwx8 step", ["--from", "31", "YL"], dict(BWX8_SHA256=d10, BWX10_SHA256=d10), 2),
             ("BWX10_SHA256 holds the digest of bwx8, a bwx10 step", ["--from", "8", "YA"], dict(BWX8_SHA256=d8, BWX10_SHA256=d8), 2),
             ("BWX10_SHA256 right and BWX8_SHA256 wrong, a call with YA then YL", ["YA", "YL"], dict(BWX8_SHA256=zero, BWX10_SHA256=d10), 2),
             ("BWX8_SHA256 right and BWX10_SHA256 wrong, a call with YL then YP", ["YL", "YP"], dict(BWX8_SHA256=d8, BWX10_SHA256=zero), 2)]
    for name, args, env_, want_rc in cases:
        rc, out, err = box.run(args, SESSION="1", STOP_AT="none", **env_)
        if want_rc:
            check("%s: status 2 before the first process of the call, no result folder" % name,
                  rc == 2 and "is not the binary with the digest given for it" in err and not box.launched()
                  and not os.path.exists(box.results), (rc, err))
        else:
            e = box.file("env.txt")
            check("%s: runs, and env.txt records both settings" % name,
                  rc == 0 and len(box.launched()) == 2 and (" BWX8_SHA256=%s BWX10_SHA256=%s binary=" % (
                      env_.get("BWX8_SHA256", ""), env_.get("BWX10_SHA256", ""))) in e, (rc, err))
    rc, out, err = box.run(["--dry-run", "YL", "YA"], SESSION="1", BWX8_SHA256=zero, BWX10_SHA256=zero)
    check("a dry run checks no digest", rc == 0, (rc, err))
    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none", BWX8_BIN=absent)
    check("the binary of the step is missing (bwx8): status 2", rc == 2 and "missing" in err and "bwx8" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", BWX8_BIN=absent)
    check("a missing bwx8 does not stop a call that uses bwx10 only", rc == 0 and len(box.launched()) == 2, (rc, err))
    rc, out, err = box.run(["YL", "YA"], SESSION="1", STOP_AT="none", BWX10_BIN=absent)
    check("the binary of the second step is missing (bwx10): status 2 before the first process of the call",
          rc == 2 and "missing" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    os.rename(os.path.join(os.path.dirname(box.bin8), "build.txt"), os.path.join(os.path.dirname(box.bin8), "build.moved"))
    rc, out, err = box.run(["--from", "31", "YL"], SESSION="1", STOP_AT="none")
    rc2, out2, err2 = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none")
    check("build.txt missing beside bwx8: a bwx8 step stops with status 2, a bwx10 step runs",
          rc == 2 and "build.txt" in err and rc2 == 0 and len(box.launched()) == 2, (rc, err, rc2, err2))
    os.rename(os.path.join(os.path.dirname(box.bin8), "build.moved"), os.path.join(os.path.dirname(box.bin8), "build.txt"))

    # ---- the rule for the counter settings ----
    tsv = box.sched("s1", "YC.tsv")
    saved_yc = open(tsv).read()
    with open(tsv, "w") as fh:
        fh.write(re.sub(r" --pmu-type 11 --events \S+", "", saved_yc))
    rc, out, err = box.run(["YC"], SESSION="1", STOP_AT="none")
    check("a counted step without the options in args and without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",
          rc == 2 and "needs BWX_PMU_TYPE" in err and not box.launched() and open(tsv).read() != saved_yc, (rc, err))
    rc, out, err = box.run(["YC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11")
    check("the same with BWX_PMU_TYPE only: status 2, nothing starts", rc == 2 and "needs BWX_EVENTS" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "41", "YC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11", BWX_EVENTS="a=0x11")
    check("the same with both settings: runs, and the binary finds them in its environment",
          rc == 0 and len(box.launched()) == 2 and open(box.log + ".env").read() == "PMU=11 EV=a=0x11\n", (rc, err))
    rc, out, err = box.run(["--dry-run", "YC"], SESSION="1", BWX_PMU_TYPE="eleven", BWX_EVENTS="a=0x11")
    check("BWX_PMU_TYPE that is not a whole number: status 2", rc == 2 and "whole number" in err, (rc, err))
    with open(tsv, "w") as fh:
        fh.write(saved_yc)
    rc, out, err = box.run(["--from", "41", "YC"], SESSION="1", STOP_AT="none")
    check("YC as scheduled (options in args) needs no counter setting: runs with --pmu-type 11 and the 6 events on the command line",
          rc == 0 and len(box.launched()) == 2 and box.launched()[0].endswith(" --pmu-type 11 --events " + EVENTS)
          and open(box.log + ".env").read() == "PMU= EV=\n", (rc, err))
    rc, out, err = box.run(["--from", "287", "YF"], SESSION="1", STOP_AT="none")
    check("an uncounted step (YF, count closed, no options in args) needs no counter setting: runs",
          rc == 0 and len(box.launched()) == 2 and "--plan sched10/s1/YF/0287.plan" in box.launched()[0]
          and re.findall(r"^-- step YF session 1 idx (\d+) ", box.csv("YF"), re.M) == ["287"]
          and " from=287 " in box.file("env.txt") and "to run from idx 287: 1 processes" in out, (rc, err))

    # ---- the host sampler is still started by a .watch file (no schedule of round 3 has one) ----
    open(box.sched("s1", "YA.watch"), "w").close()
    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="2")
    w = box.file("watch-8.txt")
    pid = box.launched()[0].split()[0] if box.launched() else "?"
    check("a step with a .watch file runs with hostwatch.py: watch-8.txt names the benchmark process and the CPU of its row, "
          "has samples and its end line; the sampler is gone",
          rc == 0 and w.startswith("# hostwatch v1 pid=%s cpu=2 hz=20 max_s=31\n" % pid) and "\n# end reason=" in w
          and " m.run_ns=" in w and box.none_alive() and "host sampler: hostwatch.py on CPU %s " % box.watch_cpu in out
          and re.search(r"^## host sampler: WATCH_CPU=%s Python \S+ sha256 %s$" % (box.watch_cpu, sha256(WATCH)),
                        box.file("env.txt"), re.M) is not None, (rc, err, w[:200]))
    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")
    check("a step with a .watch file and WATCH_CPU=126: status 2, nothing starts",
          rc == 2 and "WATCH_CPU must be a CPU from 0 to 119" in err and not box.launched(), (rc, err))
    os.remove(box.sched("s1", "YA.watch"))
    rc, out, err = box.run(["--from", "8", "YA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")
    check("a step without a .watch file does not read WATCH_CPU and writes no sampler file",
          rc == 0 and len(box.launched()) == 2 and not [f for f in os.listdir(box.folder()) if f.startswith("watch")], (rc, err))

    # ---- stop controls, for a step of each binary ----
    for step, word in (("YL", "bwx8"), ("YA", "bwx10")):
        rows = box.rows(step)
        tag = rows[0][1]
        note = "%s (%s)" % (step, word)
        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
        up = box.wait_launch()
        open(box.marker, "w").close()
        out, err = p.communicate(timeout=60)
        csv = box.csv(step)
        check("%s: marker file appears during a process: status 3, '-- killed', no process left" % note,
              up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in csv
              and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))
        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)
        check("%s: marker file present at the start: status 3, nothing starts, no result folder" % note,
              rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))
        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
        up = box.wait_launch()
        open(box.stopfile, "w").close()
        out, err = p.communicate(timeout=60)
        check("%s: stop file appears during a process: status 5, '-- killed', no process left" % note,
              up and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv(step) and box.none_alive(),
              (up, p.returncode, err))
        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", BWX8_STOPFILE=box.stopfile)
        check("%s: stop file present at the start: status 5, nothing starts" % note, rc == 5 and not box.launched(), (rc, err))
        p = box.start([step], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
        up = box.wait_launch()
        os.kill(p.pid, signal.SIGTERM)
        out, err = p.communicate(timeout=60)
        csv = box.csv(step)
        check("%s: interrupted during a process: status 130, '-- killed' marks the cut process, no process left" % note,
              up and p.returncode == 130 and box.none_alive()
              and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None
              and csv.count("-- step ") == 1, (up, p.returncode, err, csv))
        rc, out, err = box.run([step], SESSION="1", STOP_AT=utc(30))
        check("%s: STOP_AT nearer than MARGIN: status 4, nothing starts" % note,
              rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))
        p = box.start([step], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")
        up = box.wait_launch()
        out, err = p.communicate(timeout=120)
        check("%s: STOP_AT reached during a process: status 4, '-- killed', no process left" % note,
              up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv(step) and box.none_alive(),
              (up, p.returncode, err))
        rc, out, err = box.run([step], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")
        csv = box.csv(step)
        check("%s: failing benchmark: status 1, '-- failed', the next process does not start" % note,
              rc == 1 and ("-- failed tag %s exit 3" % tag) in csv and csv.count("-- step ") == 1
              and box.binaries() == [box.bin8 if word == "bwx8" else box.bin10], (rc, err, csv))
    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")
    csv = box.csv("YA")
    check("marker file appears between two processes: status 3, the first process ended, the second does not start",
          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,bwx10\n") == 1 and "-- killed" not in csv
          and len(box.launched()) == 2, (rc, err, csv))
    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case
    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none", PS_TOUCH=late,
                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])
    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",
          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("YA")
          and box.file("launches.txt").count("== YA.csv idx ") == 1, (rc, err))
    rc, out, err = box.run(["YA"], SESSION="1")
    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))
    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the test
    # divisor 100 the longest process is 0.3 s (1 s); with divisor 1 the processes of YL and YP are 30 s.
    os.rename(box.sched(), os.path.join(box.dir, "sched10-test"))
    shutil.copytree(os.path.join(Y, "sched10"), box.sched())
    rc, out, err = box.run(["YL"], SESSION="1", STOP_AT=utc(100))
    check("MARGIN follows the longest process of the step: the real YL schedule refuses at 120 s, not at 91 s",
          rc == 4 and not box.launched() and "less than 120 s away" in err and "longest process 30 s, MARGIN 120 s" in out,
          (rc, err, out))
    rc, out, err = box.run(["--dry-run", "YA", "YL", "YP", "YF", "YC"], SESSION="1")
    check("--dry-run of the real schedules, session 1: 399 processes (32 of bwx8) and the nominal work of the task "
          "(11.7, 960, 840, 2764.8, 252 s)",
          rc == 0 and out.count("\nbwx8 --trial ") == 32 and out.count("\nbwx10 --trial ") == 367
          and all(s in out for s in ("step YA session 1: 9 processes, nominal kernel work 11.700 s",
                                     "step YL session 1: 32 processes, nominal kernel work 960.000 s",
                                     "step YP session 1: 28 processes, nominal kernel work 840.000 s",
                                     "step YF session 1: 288 processes, nominal kernel work 2764.800 s",
                                     "step YC session 1: 42 processes, nominal kernel work 252.000 s")), (rc, err, out[:300]))
    rc, out, err = box.run(["--dry-run", "YL", "YP", "YF", "YC"], SESSION="2")
    check("--dry-run of the real schedules, session 2: 390 processes (32 of bwx8)",
          rc == 0 and out.count("\nbwx8 --trial ") == 32 and out.count("\nbwx10 --trial ") == 358, (rc, err))
    shutil.rmtree(box.sched())
    os.rename(os.path.join(box.dir, "sched10-test"), box.sched())

    # ---- session 2 ----
    rc, out, err = box.run(["YF"], SESSION="2", STOP_AT="none")
    check("session 2 without SESSION1_END: status 2, nothing starts",
          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))
    for step in ("YL", "YF"):
        rc, out, err = box.run([step], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))
        check("session 2 of %s earlier than 3 h after SESSION1_END: refused with status 2, nothing starts" % step,
              rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "@0", "-4 hours",
                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)), "2026-02-30T00:00Z"):
        rc, out, err = box.run(["--from", "287", "YF"], SESSION="2", STOP_AT="none", SESSION1_END=value)
        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,
              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    s1end = utc(-3 * 3600 - 60)
    row2 = box.rows("YF", 2)[287]
    rc, out, err = box.run(["--from", "287", "YF"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)
    env = box.file("env.txt")
    check("session 2 later than 3 h after SESSION1_END: runs the session 2 schedule, folder bwx10-YF-s2-, SESSION1_END in env.txt",
          rc == 0 and "bwx10-YF-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env
          and ("-- step YF session 2 idx 287 tag %s " % row2[1]) in box.csv("YF")
          and "--plan sched10/s2/YF/0287.plan" in box.launched()[0], (rc, err))
    row2 = box.rows("YL", 2)[31]
    rc, out, err = box.run(["--from", "31", "YL"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)
    check("session 2 of the bwx8 step: runs the session 2 row with the old binary",
          rc == 0 and box.binaries() == [box.bin8] and ("-- step YL session 2 idx 31 tag %s " % row2[1]) in box.csv("YL")
          and box.launched()[0].split(" ", 1)[1] == row2[5], (rc, err))

    # ---- other refusals ----
    rc, out, err = box.run(["YA"], STOP_AT="none")
    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "9", "YA"], SESSION="1", STOP_AT="none")
    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "1", "YA", "YF"], SESSION="1", STOP_AT="none")
    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))
    allowed = sorted(os.sched_getaffinity(0))
    rc, out, err = box.run(["--from", "8", "YA"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")
    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""
    check("the benchmark is confined to CPUs 0-119, whatever CPU the script was started on",
          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1 and cpu_list(seen) == {c for c in allowed if c < 120},
          (rc, err, seen))
    tsv = box.sched("s1", "YA.tsv")
    saved_ya = open(tsv).read()
    made = os.path.join(box.dir, "made-by-schedule")
    for what, old_, new_ in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("cpu", "\t2\t", "\ta[$(touch${IFS}%s)]\t")):
        with open(tsv, "w") as fh:
            fh.write(saved_ya.replace(old_, new_ % made, 1))
        rc, out, err = box.run(["--dry-run", "YA"], SESSION="1")
        check("schedule with a command in %s: status 2, the command does not run" % what,
              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved_ya, (rc, err))
    with open(tsv, "w") as fh:
        fh.write(saved_ya)
    os.rename(box.sched("s1", "YA", "0001.plan"), os.path.join(box.dir, "moved.plan"))
    rc, out, err = box.run(["YA"], SESSION="1", STOP_AT="none")
    check("missing plan file: status 2 before the first launch", rc == 2 and "missing plan file" in err and not box.launched(), (rc, err))


def main():
    with open("/proc/loadavg") as f:
        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))
    tmp = tempfile.mkdtemp(prefix="test_schedule10.")
    try:
        real, sched = schedule_checks(tmp)
        if "--no-bwx8" in sys.argv[1:]:
            print("SKIP  the run of every plan of YL through the local stand-in bwx8 (--no-bwx8)")
        else:
            bwx8_checks(tmp, real, sched)
        bwx10_checks(tmp, sched)
        visit_checks(tmp)
        if "--no-run" in sys.argv[1:]:
            print("SKIP  the checks of run_bwx10.sh with dummy binaries (--no-run)")
        else:
            run_checks(tmp, sched)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open("/proc/loadavg") as f:
        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))
    print("# checks: %d, passed: %d, failed: %d%s" % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS),
                                                      "".join("\n#   " + n for n in FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
