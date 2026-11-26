#!/usr/bin/env python3
"""test_schedule11.py - checks of schedule11.py, run_bwx11.sh and visit11.sh (round 4).

Usage: test_schedule11.py [--no-run] [--no-bwx10] [--no-long] [--no-bwx11]
Prints one line per check. Exit status 0 only if every check passed.
--no-run leaves out the checks that start run_bwx11.sh with dummy binaries (they take minutes
on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).
--no-bwx10 leaves out the build of the local stand-in bwx10 (from folder Y of round 3) and the checks that
this older binary refuses the args and the plans of round 4.
--no-bwx11 leaves out the run of every plan of ZA, ZD, ZC, ZN and ZM through a local stand-in bwx11. These
checks also print SKIP when bwx11.c is not beside this file or does not build here: the runner
is the work of another part.
--no-long leaves out the 10 runs of 30 s that put the real plans of ZM (test divisor 1) through bwx11.
Rules are also applied to a defective input, and such a check passes only if that is rejected.
This machine has no CPU 41: for the runs through a stand-in the test rewrites CPU 41 to a local CPU
in a copy of the schedule. Nothing else of the copy differs.
"""
import collections
import concurrent.futures
import copy
import difflib
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
Z = os.path.dirname(os.path.abspath(__file__))
Y = os.path.join(os.path.dirname(Z), "bwx10-2026-11-15")     # round 3: bwx10.c, run_bwx10.sh, visit10.sh, hostwatch.py
X = os.path.join(os.path.dirname(Z), "bwx8-2026-11-14")      # round 1 and 2: run_bwx9.sh
SCHED = os.path.join(Z, "schedule11.py")
RUN = os.path.join(Z, "run_bwx11.sh")
VISIT = os.path.join(Z, "visit11.sh")
WATCH = os.path.join(Z, "hostwatch.py")
NEW_KERNELS = ["read_nop64", "read_nop96", "read_nop128"]
READ_KERNELS = ["oldread", "read", "asmread", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse",
                "read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"] + NEW_KERNELS
# The flags of build8.sh.
CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "
          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()
# The task: processes per step and session, trials per process, nominal kernel work in seconds, binary,
# processes with --evict-mb in session 1.
TABLE = collections.OrderedDict([("ZA", (6, 1, 7.8, "bwx11", 2)), ("ZD", (216, 4, 2073.6, "bwx11", 108)),
                                 ("ZC", (32, 1, 192.0, "bwx11", 16)), ("ZN", (144, 4, 1382.4, "bwx11", 0)),
                                 ("ZM", (40, 1, 1200.0, "bwx11", 0))])
EVENTS = "cpu_cycles=0x11,l1d_cache_lmiss_rd=0x39,l2d_cache_refill=0x17,l2d_cache_wb=0x18,bus_access=0x19,l2d_cache_lmiss_rd=0x4009"
# condition name: (megabytes of the evict buffer, the option in args)
ECOND = collections.OrderedDict([("E0", (0, "")), ("E512", (512, " --evict-mb 512"))])
ZD_KERNELS = ["asmread", "read", "oldread"]
ZD_SIZES = ["4M", "8M", "16M"]
ZD_CELLS = [(k, e) for k in ZD_KERNELS for e in ECOND]
ZC_KERNELS = ["asmread", "oldread"]
ZC_SIZES = ["8M", "16M"]
ZN_KERNELS = NEW_KERNELS
ZN_SIZES = ["32K", "1M", "8M", "16M"]
ZM_PADS = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72]
# tag, kernel, size, the options after the plan
ZA = [("plain-cpu2", "asmread", "8M", " --trace"), ("evict-cpu2", "asmread", "8M", " --trace --evict-mb 512"),
      ("oldevict-cpu2", "oldread", "8M", " --trace --evict-mb 512"), ("nop64-cpu2", "read_nop64", "8M", " --trace"),
      ("nop96-cpu2", "read_nop96", "8M", " --trace"), ("nop128-cpu2", "read_nop128", "8M", " --trace")]
HEAD_S2 = ["step", "session", "cpu", "bytes", "proc", "rep_set", "kernel", "size", "seed", "test"]
HEAD_ZD = HEAD_S2[:8] + ["econd"] + HEAD_S2[8:]
ALL_STEPS = ["ZA", "ZD", "ZC", "ZN", "ZM"]

FAILS = []
COUNT = [0]


SKIPS = [0]


def skip(text):
    """One part of the test that did not run. The last line of the output gives the number of such parts."""
    SKIPS[0] += 1
    print("SKIP  " + text)
    sys.stdout.flush()


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
                want = "--trial --cpus %d --bytes %d --plan sched11/s%d/%s/%s" % (p["cpu"], p["bytes"], session, step, f[4])
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


def s2_style(p, k, s, tail=""):
    """4 trials: the kernel at the size, with itself as 1.2 s prefix, 4 windows, uncounted. tail: the end of the cond label."""
    t = p["trials"]
    return len(t) == 4 and all(
        x == {"cond": "K=%s|S=%s%s" % (k, s, tail), "rep": i + 1, "prev": "-", "pfx": "%s@%s:%d" % (k, s, 4 * x["win_ms"]),
              "pred": "-", "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": x["win_ms"], "count": "closed", "bins": 0,
              "ms": 8 * x["win_ms"]} for i, x in enumerate(t)) and \
        p["bytes"] == nbytes(s) and p["head"].get("size") == str(nbytes(s)) and p["head"].get("kernel") == k


# ---------- rules of the steps; each returns a list of defects. div: the test divisor of the tree ----------
def set_rules(procs, cpus, items, sizes, item_of, times, what):
    """Shared by ZD and ZN. The processes come in 6 replicate sets. A set holds the sizes in one order; a size holds
    the first CPU, then the second; a CPU holds every item once. Per size and CPU: every item is `times` times at
    every position, and every ordered pair of items is `times` times a pair of neighbours."""
    bad = []
    n = len(items)
    sets = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in procs:
        sets[p["tag"].split("-")[1], p["cpu"]][int(p["head"].get("rep_set", 0))].append(item_of(p))
    assign = set()
    if len(sets) != 2 * len(sizes):
        bad.append("sizes and CPUs")
    for (s, cpu), orders in sets.items():
        o = [tuple(orders[r]) for r in sorted(orders)]
        if sorted(orders) != [1, 2, 3, 4, 5, 6] or any(sorted(x) != sorted(items) for x in o):
            bad.append("size %s cpu %d: not 6 sets of the %d %s" % (s, cpu, n, what))
            continue
        pos = collections.Counter((k, i) for x in o for i, k in enumerate(x))
        if len(pos) != n * n or set(pos.values()) != {times}:
            bad.append("size %s cpu %d: an item is not %d time(s) at each position" % (s, cpu, times))
        pairs = collections.Counter((x[i], x[i + 1]) for x in o for i in range(n - 1))
        if len(pairs) != n * (n - 1) or set(pairs.values()) != {times}:
            bad.append("size %s cpu %d: an ordered pair is not %d time(s) a pair of neighbours" % (s, cpu, times))
        assign.add(tuple(o))
    if len(assign) < 2:
        bad.append("every size and CPU uses the same orders")
    per_set = 2 * n * len(sizes)
    size_orders = set()
    for r in range(6):
        block = procs[per_set * r:per_set * (r + 1)]
        if any(p["head"].get("rep_set") != str(r + 1) for p in block):
            bad.append("block %d: rep_set" % (r + 1))
        got = []
        for g in range(len(sizes)):
            group = block[2 * n * g:2 * n * (g + 1)]
            if len({p["bytes"] for p in group}) != 1 or [p["cpu"] for p in group] != [cpus[0]] * n + [cpus[1]] * n:
                bad.append("block %d group %d: size or CPU order" % (r + 1, g))
            got.append(group[0]["bytes"] if group else None)
        if sorted(got, key=str) != sorted((nbytes(s) for s in sizes), key=str):
            bad.append("block %d: a size is missing" % (r + 1))
        size_orders.add(tuple(got))
    if len(size_orders) < 2:
        bad.append("the size order is the same in every block")
    return bad


def zd_rules(procs, cpus):
    bad = []
    if len(procs) != 216:
        return ["process count %d" % len(procs)]
    for p in procs:
        h = p["head"]
        k, s, e = h.get("kernel"), p["tag"].split("-")[1], h.get("econd")
        if k not in ZD_KERNELS or s not in ZD_SIZES or e not in ECOND:
            bad.append("process %d: kernel, size or condition" % p["idx"])
            continue
        if not s2_style(p, k, s, "|evict=%d" % ECOND[e][0]):
            bad.append("process %d: not 4 trials of one kernel with itself as prefix and the evict label of its condition" % p["idx"])
        if p["order"] != HEAD_ZD or p["extra"] != ECOND[e][1] or p["tag"] != "r%s-%s-cpu%d-%s-%s" % (h.get("rep_set"), s, p["cpu"], k, e):
            bad.append("process %d: header keys, the option of the condition in args, or tag" % p["idx"])
    if bad:
        return bad
    return set_rules(procs, cpus, ZD_CELLS, ZD_SIZES, lambda p: (p["head"]["kernel"], p["head"]["econd"]), 1, "cells")


def zn_rules(procs, cpus):
    bad = []
    if len(procs) != 144:
        return ["process count %d" % len(procs)]
    for p in procs:
        h = p["head"]
        k, s = h.get("kernel"), p["tag"].split("-")[1]
        if k not in ZN_KERNELS or s not in ZN_SIZES or not s2_style(p, k, s):
            bad.append("process %d: not 4 trials of one slow load-only kernel with itself as prefix" % p["idx"])
        if p["order"] != HEAD_S2 or p["extra"]:
            bad.append("process %d: header keys or args" % p["idx"])
    if bad:
        return bad
    return set_rules(procs, cpus, ZN_KERNELS, ZN_SIZES, lambda p: p["head"]["kernel"], 2, "kernels")


def zc_rules(procs, cpus, div=1):
    bad = []
    if len(procs) != 32:
        return ["process count %d" % len(procs)]
    cells = sorted((k, s, e) for k in ZC_KERNELS for s in ZC_SIZES for e in ECOND)
    orders = set()
    for b in range(4):
        block = procs[8 * b:8 * b + 8]
        r, cpu = b // 2 + 1, cpus[b % 2]
        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):
            bad.append("block %d: CPU or rep_set" % b)
        got = [tuple(p["trials"][0]["tgt"].split("@")) + (p["head"].get("econd"),) for p in block]
        if sorted(got, key=str) != cells:
            bad.append("block %d: does not hold every kernel, size and condition once" % b)
        orders.add(tuple(got))
    for p in procs:
        k, s = p["trials"][0]["tgt"].split("@")
        e = p["head"].get("econd")
        if e not in ECOND:
            bad.append("process %d: econd" % p["idx"])
            continue
        if p["trials"] != one_trial("K=%s|S=%s|evict=%d|count=read" % (k, s, ECOND[e][0]), "%s@%s" % (k, s), 20, 300 // div, "read"):
            bad.append("process %d: trial" % p["idx"])
        if p["bytes"] != nbytes(s) or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)):
            bad.append("process %d: bytes or header" % p["idx"])
        if p["extra"] != ECOND[e][1] + " --pmu-type 11 --events " + EVENTS:
            bad.append("process %d: the option of the condition or the event set in args" % p["idx"])
    if len(orders) < 2:
        bad.append("the cell order is the same in every block")
    return bad


def zm_rules(procs, cpus, div=1):
    bad = []
    if len(procs) != 40:
        return ["process count %d" % len(procs)]
    names = ["P%d" % p for p in ZM_PADS]
    for b in range(4):
        block = procs[10 * b:10 * b + 10]
        r, cpu = b // 2 + 1, cpus[b % 2]
        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):
            bad.append("block %d: CPU or rep_set" % b)
        if sorted(p["head"].get("pcond", "") for p in block) != sorted(names):
            bad.append("block %d: does not hold every pad once" % b)
    for p in procs:
        name = p["head"].get("pcond")
        if name not in names:
            bad.append("process %d: pcond" % p["idx"])
            continue
        if p["trials"] != one_trial("K=asmread|S=8M|rec=%s" % name, "asmread@8M", 300, 100 // div):
            bad.append("process %d (%s): trial" % (p["idx"], name))
        if p["extra"] != " --rec-pad " + name[1:]:
            bad.append("process %d (%s): the option in args" % (p["idx"], name))
        if p["bytes"] != 8 << 20 or p["head"].get("kernel") != "asmread" or p["head"].get("size") != str(8 << 20) \
                or not p["tag"].startswith(name + "-"):
            bad.append("process %d (%s): bytes, header or tag" % (p["idx"], name))
    if len({tuple(p["head"].get("pcond") for p in procs[10 * b:10 * b + 10]) for b in range(4)}) < 2:
        bad.append("the pad order is the same in every block")
    return bad


def za_rules(procs, div=1):
    bad = []
    if len(procs) != 6:
        return ["process count %d" % len(procs)]
    for p, (tag, k, s, extra) in zip(procs, ZA):
        ks = "%s@%s" % (k, s)
        name = tag[:-5]
        if p["tag"] != tag or p["cpu"] != 2 or p["bytes"] != nbytes(s) or p["extra"] != extra \
                or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)) or p["head"].get("acond") != name:
            bad.append("process %d: tag, CPU, bytes, args or header" % p["idx"])
        if p["trials"] != one_trial("K=%s|S=%s|acc=%s" % (k, s, name), ks, 3, 300 // div, "closed", 0, 400 // div):
            bad.append("process %d: trial" % p["idx"])
    return bad


def untagged(procs):
    return [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in procs]


def schedule_checks(tmp):
    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))
    r = gen(a)
    check("schedule11.py runs with status 0", r.returncode == 0, r.stderr)
    tree, errors = load(a)
    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])
    check("the 5 steps exist in session 1; session 2 has the same steps without ZA",
          sorted(tree) == sorted([(s, 1) for s in TABLE] + [(s, 2) for s in TABLE if s != "ZA"]), sorted(tree))

    # The validator itself rejects defective plans.
    good = open(os.path.join(a, "s1", "ZM", "0000.plan")).read()
    good1 = open(os.path.join(a, "s1", "ZA", "0000.plan")).read()
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
    for step, (n, tr, sec, word, ev) in TABLE.items():
        for s in (1, 2):
            if (step, s) not in tree:
                continue
            procs = tree[step, s]
            ms = sum(proc_ms(p) for p in procs)
            nev = sum(1 for p in procs if "--evict-mb" in p["extra"])
            check("%s session %d: %d processes of %d trial(s), %.1f s of nominal kernel work, %d processes with --evict-mb 512"
                  % (step, s, n, tr, sec, ev),
                  len(procs) == n and all(len(p["trials"]) == tr for p in procs) and ms == round(sec * 1000) and nev == ev
                  and all(" --evict-mb 512" in p["extra"] for p in procs if "--evict-mb" in p["extra"]), (len(procs), ms, nev))
            check("%s session %d: the report prints the binary, the process count, the nominal work and the evict count" % (step, s),
                  ("\n%s %d %s %d %d %g %d\n" % (step, s, word, n, n * tr, sec, ev)) in r.stdout, r.stdout[:400])
    check("the report prints the totals of each session: 438 processes and 4855.8 s, 432 processes and 4848 s",
          "\nsession 1 total: 438 processes, nominal kernel work 4855.8 s (80.93 min)\n" in r.stdout
          and "\nsession 2 total: 432 processes, nominal kernel work 4848 s (80.8 min)\n" in r.stdout, r.stdout[:900])
    check("the report states the evict step of each session: 126 and 124 processes, real time that is not kernel work, "
          "est. 0.3 to 1 s per process, not in the nominal work",
          all(re.search(r"^session %d evict step: %d processes run with --evict-mb 512; the evict step is real time that is not "
                        r"kernel work, est\. 0\.3 to 1 s per process, so est\. %s to %d s more in the session; it is not in the "
                        r"nominal kernel work" % (s, n, lo, n), r.stdout, re.M)
              for s, n, lo in ((1, 126, r"37\.8"), (2, 124, r"37\.2"))), r.stdout[:1500])
    check("the report states the balance of ZD, ZC, ZN and ZM for both sessions, each with 'yes'",
          len(re.findall(r"^Z[DCNM] session [12]: .*: yes$", r.stdout, re.M)) == 8 and ": NO" not in r.stdout, r.stdout[-900:])
    short = copy.deepcopy(tree["ZD", 1])
    short[0]["trials"].pop()
    check("nominal work: a schedule with one trial missing does not give the ZD value",
          sum(proc_ms(p) for p in short) != 2073600)
    check("one process at a time is at most 30 s of kernel work (ZM)",
          max(proc_ms(p) for procs in tree.values() for p in procs) == 30000
          and all(proc_ms(p) == 30000 for p in tree["ZM", 1]))

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

    def evict_agrees(p, step):
        m = re.search(r" --evict-mb (\d+)", p["extra"])
        mb = m.group(1) if m else "0"
        labels = {dict(x.split("=") for x in t["cond"].split("|")).get("evict") for t in p["trials"]}
        if step in ("ZD", "ZC"):
            return labels == {mb} and p["head"].get("econd") == "E" + mb
        return labels == {None} and "econd" not in p["head"] and (mb == "0" or step == "ZA")

    check("the evict option in args agrees with the cond label and the header (ZD, ZC); no other step has the label, "
          "and only ZA has the option without it",
          all(evict_agrees(p, st) for (st, _), procs in tree.items() for p in procs))
    m = copy.deepcopy(tree["ZD", 1][0])
    m["extra"] = "" if m["extra"] else " --evict-mb 512"
    check("that rule rejects a process whose option differs from its label", not evict_agrees(m, "ZD"))
    check("no trial of round 4 has a previous activity, a predecessor or bins",
          all(t["prev"] == "-" and t["pred"] == "-" and t["bins"] == 0
              for procs in tree.values() for p in procs for t in p["trials"]))
    check("every kernel of the schedules is one of asmread, read, oldread, read_nop64, read_nop96, read_nop128",
          {p["head"]["kernel"] for procs in tree.values() for p in procs} == set(["asmread", "read", "oldread"] + NEW_KERNELS))

    # CPU order of the sessions.
    for (step, s), procs in sorted(tree.items()):
        if step == "ZA":
            continue
        check("%s session %d: CPU order %d then %d" % ((step, s) + cpus_of(s)), cpu_blocks(procs, *cpus_of(s)))
    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["ZM", 1], 41, 2))
    check("session 2 is not session 1 with the CPUs exchanged (own random order)",
          all(untagged(tree[st, 1]) != untagged(tree[st, 2]) for st in ("ZD", "ZC", "ZN", "ZM")))

    # ZD.
    for s in (1, 2):
        d = zd_rules(tree["ZD", s], cpus_of(s))
        check("ZD session %d: S2-style trials; asmread, read, oldread at 4M, 8M, 16M with E0 (no option) and E512 "
              "(--evict-mb 512); per size and CPU each (kernel, condition) cell once at each position and each ordered pair of "
              "cells once as neighbours; order: replicate set, size, CPU" % s, not d, d[:3])
    check("ZD: 6 processes per kernel, size, condition and CPU (108 cells)",
          collections.Counter((p["head"]["kernel"], p["bytes"], p["head"]["econd"], p["cpu"]) for p in tree["ZD", 1])
          == {(k, nbytes(s), e, c): 6 for k in ZD_KERNELS for s in ZD_SIZES for e in ECOND for c in (2, 41)})
    m = copy.deepcopy(tree["ZD", 1])
    for i in range(0, 216, 6):                       # every set in the order of ZD_CELLS
        for p, (k, e) in zip(m[i:i + 6], ZD_CELLS):
            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]
            p["head"].update(kernel=k, econd=e)
            p["extra"] = ECOND[e][1]
            p["tag"] = "r%s-%s-cpu%d-%s-%s" % (p["head"]["rep_set"], s, p["cpu"], k, e)
            for t in p["trials"]:
                t.update(cond="K=%s|S=%s|evict=%d" % (k, s, ECOND[e][0]), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))
    d = zd_rules(m, (2, 41))
    check("ZD rules reject a schedule in which every set has one fixed cell order",
          any("at each position" in x for x in d) and any("neighbours" in x for x in d), d[:3])
    m = copy.deepcopy(tree["ZD", 1])
    m[5], m[6] = m[6], m[5]
    check("ZD rules reject CPUs that alternate inside a size", bool(zd_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZD", 1])
    m[5]["trials"][0]["pfx"] = "asmread@1M:1200" if m[5]["head"]["kernel"] != "asmread" else "read@1M:1200"
    check("ZD rules reject a prefix of another kernel or size", bool(zd_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZD", 1])
    p = [x for x in m if x["head"]["econd"] == "E512"][0]
    p["extra"] = ""
    check("ZD rules reject an E512 process without --evict-mb 512", bool(zd_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZD", 1])
    p = [x for x in m if x["head"]["econd"] == "E0"][0]
    p["extra"] = " --evict-mb 512"
    check("ZD rules reject an E0 process with --evict-mb 512", bool(zd_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZD", 1])
    p = [x for x in m if x["head"]["econd"] == "E512"][0]
    p["extra"] = " --evict-mb 256"
    check("ZD rules reject another size of the evict buffer", bool(zd_rules(m, (2, 41))))
    check("ZD rules reject the session 1 schedule under the session 2 CPU order", bool(zd_rules(tree["ZD", 1], (41, 2))))

    # ZN.
    for s in (1, 2):
        d = zn_rules(tree["ZN", s], cpus_of(s))
        check("ZN session %d: S2-style trials, header keys as S2, no option; read_nop64, read_nop96, read_nop128 at 32K, 1M, 8M, "
              "16M; per size and CPU each kernel twice at each position and each ordered pair of kernels twice as neighbours; "
              "order: replicate set, size, CPU" % s, not d, d[:3])
    check("ZN: 6 processes per kernel, size and CPU (24 cells)",
          collections.Counter((p["head"]["kernel"], p["bytes"], p["cpu"]) for p in tree["ZN", 1])
          == {(k, nbytes(s), c): 6 for k in ZN_KERNELS for s in ZN_SIZES for c in (2, 41)})
    m = copy.deepcopy(tree["ZN", 1])
    for i in range(0, 144, 3):
        for p, k in zip(m[i:i + 3], ZN_KERNELS):
            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]
            p["head"]["kernel"] = k
            for t in p["trials"]:
                t.update(cond="K=%s|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))
    d = zn_rules(m, (2, 41))
    check("ZN rules reject a schedule in which every set has one fixed kernel order",
          any("at each position" in x for x in d) and any("neighbours" in x for x in d), d[:3])
    m = copy.deepcopy(tree["ZN", 1])
    m[2], m[3] = m[3], m[2]
    check("ZN rules reject CPUs that alternate inside a size", bool(zn_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZN", 1])
    m[7]["extra"] = " --evict-mb 512"
    check("ZN rules reject a process with an option", bool(zn_rules(m, (2, 41))))
    check("ZN rules reject the session 1 schedule under the session 2 CPU order", bool(zn_rules(tree["ZN", 1], (41, 2))))

    # ZC.
    for s in (1, 2):
        d = zc_rules(tree["ZC", s], cpus_of(s))
        check("ZC session %d: asmread and oldread at 8M and 16M with E0 and E512 once per replicate block and CPU, "
              "20 windows of 300 ms, count read, --pmu-type 11 and the 6 events in args" % s, not d, d[:3])
    check("ZC: 2 processes per kernel, size, condition and CPU (16 cells)",
          collections.Counter((p["head"]["kernel"], p["bytes"], p["head"]["econd"], p["cpu"]) for p in tree["ZC", 1])
          == {(k, nbytes(s), e, c): 2 for k in ZC_KERNELS for s in ZC_SIZES for e in ECOND for c in (2, 41)})
    m = copy.deepcopy(tree["ZC", 1])
    m[0]["trials"][0]["count"] = "closed"
    check("ZC rules reject a trial with count closed", bool(zc_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZC", 1])
    m[3]["extra"] = m[3]["extra"].replace("0x4009", "0x4008")
    check("ZC rules reject another event code", bool(zc_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZC", 1])
    p = [x for x in m if x["head"]["econd"] == "E512"][0]
    p["extra"] = p["extra"].replace(" --evict-mb 512", "")
    check("ZC rules reject an E512 process without --evict-mb 512", bool(zc_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZC", 1])
    m[0], m[8] = m[8], m[0]
    check("ZC rules reject two processes exchanged between blocks", bool(zc_rules(m, (2, 41))))
    check("ZC rules reject the session 1 schedule under the session 2 CPU order", bool(zc_rules(tree["ZC", 1], (41, 2))))
    check("the event set: 6 events with l2d_cache_wb=0x18 and bus_access=0x19, names below 32 characters, 6 different names and codes",
          len(EVENTS.split(",")) == 6 and all(re.match(r"^[a-z0-9_]{1,31}=0x[0-9a-f]+$", e) for e in EVENTS.split(","))
          and len({e.split("=")[0] for e in EVENTS.split(",")}) == 6 and len({int(e.split("=")[1], 16) for e in EVENTS.split(",")}) == 6
          and "l2d_cache_wb=0x18" in EVENTS.split(",") and "bus_access=0x19" in EVENTS.split(","))

    # ZM.
    for s in (1, 2):
        d = zm_rules(tree["ZM", s], cpus_of(s))
        check("ZM session %d: asmread at 8M, 300 windows of 100 ms, count closed; --rec-pad 0, 8, 16, 24, 32, 40, 48, 56, 64, 72 "
              "once per replicate block and CPU" % s, not d, d[:3])
    check("ZM: 2 processes per pad and CPU (20 cells)",
          collections.Counter((p["head"]["pcond"], p["cpu"]) for p in tree["ZM", 1])
          == {("P%d" % x, c): 2 for x in ZM_PADS for c in (2, 41)})
    m = copy.deepcopy(tree["ZM", 1])
    [p for p in m if p["head"]["pcond"] == "P8"][0]["extra"] = " --rec-pad 80"
    check("ZM rules reject a pad that differs from its label", bool(zm_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZM", 1])
    m[0]["trials"][0]["nwin"] += 1
    check("ZM rules reject a trial with one more window", bool(zm_rules(m, (2, 41))))
    m = copy.deepcopy(tree["ZM", 1])
    m[0], m[10] = m[10], m[0]
    check("ZM rules reject two processes exchanged between blocks", bool(zm_rules(m, (2, 41))))
    fixed = sorted(tree["ZM", 1], key=lambda p: (int(p["head"]["rep_set"]), p["cpu"], int(p["head"]["pcond"][1:])))
    check("ZM rules reject a fixed pad order in every block",
          zm_rules(fixed, (2, 41)) == ["the pad order is the same in every block"], zm_rules(fixed, (2, 41))[:3])
    check("ZM rules reject the session 1 schedule under the session 2 CPU order", bool(zm_rules(tree["ZM", 1], (41, 2))))

    # ZA.
    d = za_rules(tree["ZA", 1])
    check("ZA: CPU 2 only, 6 processes with --trace in the fixed order (asmread plain, asmread and oldread with --evict-mb 512, "
          "read_nop64, read_nop96, read_nop128, all at 8M), each one trial: prefix 400 ms, 3 windows of 300 ms, count closed, bins 0",
          not d, d[:3])
    m = copy.deepcopy(tree["ZA", 1])
    m[4]["extra"] = ""
    check("ZA rules reject a process without --trace", bool(za_rules(m)))
    m = copy.deepcopy(tree["ZA", 1])
    m[1]["extra"] = " --trace"
    check("ZA rules reject the evict process without --evict-mb 512", bool(za_rules(m)))
    check("ZA: session 2 has no schedule, no plan folder and no binary file",
          not [f for f in os.listdir(os.path.join(a, "s2")) if f.startswith("ZA")])

    # Binary files and sampler markers.
    for s in (1, 2):
        sdir = os.path.join(a, "s%d" % s)
        bins = {f[:-4]: open(os.path.join(sdir, f)).read() for f in os.listdir(sdir) if f.endswith(".bin")}
        check("session %d: one .bin file per step; every step names bwx11; one word and a newline" % s,
              bins == {st: "bwx11\n" for st in TABLE if (st, s) in tree}, bins)
        check("session %d: no .watch file (no step of round 4 runs with the host sampler)" % s,
              not [f for f in os.listdir(sdir) if f.endswith(".watch")])

    # Determinism.
    gen(b)
    r3 = gen(c, "--seed", "7")
    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)
    nfiles = 1 + sum(TABLE[s][0] + 2 for s in TABLE) + sum(TABLE[s][0] + 2 for s in TABLE if s != "ZA")
    check("two runs with one base seed give the same bytes (%d files)" % nfiles, ta == tb and len(ta) == nfiles == 889, len(ta))
    check("another base seed gives the same file names and other bytes",
          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc
          and all(ta["s%d/%s.tsv" % (n, s)] != tc["s%d/%s.tsv" % (n, s)] for s in ("ZD", "ZC", "ZN", "ZM") for n in (1, 2)))
    check("the base seed and the seed of every step and session are saved in MANIFEST.txt",
          b"base_seed=20261115\ntest_divisor=1\n" in ta["MANIFEST.txt"] and b"base_seed=7\n" in tc["MANIFEST.txt"]
          and all(("seed %s s%d %s\n" % (st, s, procs[0]["head"]["seed"])).encode() in ta["MANIFEST.txt"]
                  for (st, s), procs in tree.items()))
    check("MANIFEST.txt names the binary of every step and session, and states that no step has a sampler marker",
          all(("bin %s s%d bwx11\n" % (st, s)).encode() in ta["MANIFEST.txt"] for (st, s) in tree)
          and ta["MANIFEST.txt"].count(b"\nbin ") == 9 and ta["MANIFEST.txt"].endswith(b"\nwatch none\n"), ta["MANIFEST.txt"][-200:])
    tree7, errors7 = load(c)
    check("another base seed keeps the rules (grammar, ZD, ZC, ZN, ZM, ZA)",
          not errors7 and not zd_rules(tree7["ZD", 2], (41, 2)) and not zn_rules(tree7["ZN", 1], (2, 41))
          and not zm_rules(tree7["ZM", 2], (41, 2)) and not zc_rules(tree7["ZC", 1], (2, 41)) and not za_rules(tree7["ZA", 1]))
    saved = os.path.join(Z, "sched11")
    check("the saved sched11/ beside the scripts is the output of the default base seed",
          os.path.isdir(saved) and tree_bytes(saved) == ta)
    src = open(SCHED).read()
    check("schedule11.py imports the standard library only (no file of an earlier round)",
          sorted(set(re.findall(r"^(?:import|from) (\w+)", src, re.M))) == ["argparse", "hashlib", "itertools", "os", "random", "shutil", "sys"]
          and "sys.path" not in src, sorted(set(re.findall(r"^(?:import|from) (\w+)", src, re.M))))
    check("hostwatch.py in this folder is the file of round 3, byte for byte",
          open(WATCH, "rb").read() == open(os.path.join(Y, "hostwatch.py"), "rb").read())

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
          and not zd_rules(ttree["ZD", 1], (2, 41)) and not zn_rules(ttree["ZN", 2], (41, 2))
          and not zc_rules(ttree["ZC", 2], (41, 2), 100) and not za_rules(ttree["ZA", 1], 100)
          and not zm_rules(ttree["ZM", 1], (2, 41), 100), terr[:3])
    check("--test-divisor 100 keeps the order and the args of the processes (only durations and the test mark differ)",
          all([(p["tag"], p["args"]) for p in ttree[k]] == [(p["tag"], p["args"]) for p in tree[k]] for k in tree))
    for div in ("7", "3", "300", "0"):
        check("--test-divisor %s is refused (it does not divide 100 ms, the shortest window)" % div,
              gen(os.path.join(tmp, "u"), "--test-divisor", div).returncode != 0 and not os.path.exists(os.path.join(tmp, "u")))
    return a, t


# ---------- plans through a local stand-in binary ----------
def stand_in_jobs(d, steps, alt, sessions=(1, 2), only=None):
    """Jobs for the plans of `steps` in the tree d/sched11. CPU 41 is rewritten to `alt` in that tree."""
    jobs = []
    for session in sessions:
        sdir = os.path.join(d, "sched11", "s%d" % session)
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
        r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True, timeout=600)
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
    if ok and "--rec-pad" in args:
        ok = m.get("rec_pad") == args[args.index("--rec-pad") + 1]
    if ok:
        # The runner records the evict setting of the process in the row M,evict_mb (0 without the option).
        ok = m.get("evict_mb") == (args[args.index("--evict-mb") + 1] if "--evict-mb" in args else "0")
    return None if ok else (step, session, idx, r.returncode, r.stderr[-200:], dict(rows))


def local_cpus():
    allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)
    if not check("this machine allows CPU 0, CPU 2 and one more CPU below 120", 0 in allowed and 2 in allowed and len(allowed) > 2):
        return None
    return 41 if 41 in allowed else [c for c in allowed if c not in (0, 2)][0]


def build_stand_in(src, d, word):
    """Builds `src` as d/<word> with the flags of build8.sh. Returns (path, None) or (None, first line of the compiler output)."""
    os.makedirs(d)
    binary = os.path.join(d, word)
    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, src], capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stdout + r.stderr).strip().split("\n")[0][:200]
    return binary, None


def bwx10_checks(tmp, sched):
    """The older runner refuses what is new in round 4, so a wrong .bin word cannot run such a process."""
    binary, why = build_stand_in(os.path.join(Y, "bwx10.c"), os.path.join(tmp, "bwx10"), "bwx10")
    if not check("stand-in build of bwx10.c of round 3 in a temporary folder (flags of build8.sh)", binary is not None, why):
        return
    d = os.path.dirname(binary)
    shutil.copytree(sched, os.path.join(d, "sched11"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}

    def first(step, pred):
        for row in open(os.path.join(d, "sched11", "s1", step + ".tsv")).read().split("\n")[1:-1]:
            f = row.split("\t")
            if f[2] == "2" and pred(f):
                return f[5].split()

    args = first("ZD", lambda f: "--evict-mb" in f[5] and "asmread" in f[1])
    r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True)
    check("the old bwx10 refuses the args of a ZD process with --evict-mb 512 (status not 0)",
          r.returncode != 0 and "--evict-mb" in args, (r.returncode, r.stderr[-200:]))
    args = first("ZD", lambda f: "--evict-mb" not in f[5] and "asmread" in f[1])
    r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True)
    check("the old bwx10 runs the same kind of process without the option (status 0), so the refusal comes from the option",
          r.returncode == 0 and "--evict-mb" not in args, (r.returncode, r.stderr[-200:]))
    args = first("ZN", lambda f: "read_nop64" in f[1])
    r = subprocess.run([binary] + args, cwd=d, env=env, capture_output=True, text=True)
    check("the old bwx10 refuses a ZN plan (kernel read_nop64 is unknown to it)", r.returncode != 0, (r.returncode, r.stderr[-200:]))


def bwx11_checks(tmp, real, sched):
    what = "the run of the plans of ZA, ZD, ZC, ZN and ZM through a local stand-in bwx11"
    src = os.path.join(Z, "bwx11.c")
    if "--no-bwx11" in sys.argv[1:]:
        skip("%s (--no-bwx11)" % what)
        return
    if not os.path.exists(src):
        skip("%s (bwx11.c is not in this folder)" % what)
        return
    binary, why = build_stand_in(src, os.path.join(tmp, "bwx11"), "bwx11")
    if binary is None:
        skip("%s (bwx11.c does not build here: %s)" % (what, why))
        return
    d = os.path.dirname(binary)
    alt = local_cpus()
    if alt is None:
        return
    shutil.copytree(sched, os.path.join(d, "sched11"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}
    r = subprocess.run([binary, "--list"], env=env, capture_output=True, text=True)
    check("the stand-in bwx11 lists the kernels of round 4 (asmread, read, oldread, read_nop64, read_nop96, read_nop128)",
          r.returncode == 0 and set(NEW_KERNELS + ["asmread", "read", "oldread"]) <= set(r.stdout.split()), r.stdout[:300])
    jobs = stand_in_jobs(d, ALL_STEPS, alt)
    t0 = time.time()
    # 4 at a time: a process with --evict-mb 512 writes 512 MiB of memory.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: run_job(binary, d, env, j), jobs))
    per = collections.defaultdict(list)
    for job, res in zip(jobs, results):
        per[job[0], job[1]].append(res)
    for (step, session), res in sorted(per.items(), key=lambda x: (x[0][1], ALL_STEPS.index(x[0][0]))):
        bad = [x for x in res if x]
        check("%s session %d (test divisor 100): the stand-in bwx11 accepts each of the %d plans with its args: status 0, one S and "
              "one E row per trial, every planned window as a W row, the pad and the evict setting in the M rows"
              % (step, session, len(res)), len(res) == TABLE[step][0] and not bad, bad[:2])
    check("all %d plans of round 4 ran through the stand-in bwx11 (%.0f s)" % (len(jobs), time.time() - t0),
          len(jobs) == 438 + 432 and all(x is None for x in results))
    # The acceptance means something only if bwx11 refuses a defective plan.
    plan = os.path.join(d, "sched11", "s1", "ZM", "0000.plan")
    text = open(plan).read()
    line = text.split("\n")[3]
    args = ["--trial", "--cpus", "2", "--bytes", "8388608", "--plan"]
    for name, bad in (("an unknown kernel", text.replace("@", "x@")),
                      ("a size above --bytes", text.replace("@8M", "@64M")),
                      ("4097 windows", text.replace(line, re.sub(r" \d+ (\d+ closed)", r" 4097 \1", line))),
                      ("bins 2", text.replace(line, line[:-1] + "2"))):
        p = os.path.join(d, "bad.plan")
        with open(p, "w") as f:
            f.write(bad)
        r = subprocess.run([binary] + args + [p], env=env, capture_output=True, text=True)
        check("bwx11 refuses a plan with %s (status 2)" % name, bad != text and r.returncode == 2, (r.returncode, r.stderr))
    r = subprocess.run([binary] + args + [plan, "--evict-mb", "x"], cwd=d, env=env, capture_output=True, text=True)
    check("bwx11 refuses --evict-mb with a value that is not a number", r.returncode != 0, (r.returncode, r.stderr[-200:]))
    # The real plans of ZM, test divisor 1: the first replicate block of session 1 holds every pad once, all on
    # CPU 2. Each process is 30 s of kernel work; the 10 run at the same time.
    if "--no-long" in sys.argv[1:]:
        skip("the 10 runs of 30 s of the real ZM plans through bwx11 (--no-long)")
        return
    dr = os.path.join(tmp, "bwx11real")
    os.makedirs(dr)
    shutil.copytree(real, os.path.join(dr, "sched11"))
    jobs = stand_in_jobs(dr, ["ZM"], alt, sessions=(1,), only=set(range(10)))
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda j: run_job(binary, dr, env, j), jobs))
    bad = [x for x in results if x]
    pads = sorted(int(j[3][j[3].index("--rec-pad") + 1]) for j in jobs)
    check("ZM real plans (test divisor 1, first block of session 1, %.0f s): bwx11 accepts 300 windows of 100 ms with each of "
          "the 10 pads and prints every window" % (time.time() - t0),
          pads == ZM_PADS and [j[5] for j in jobs] == [300] * 10 and not bad, (pads, bad[:2]))


# ---------- run_bwx11.sh with dummy binaries ----------
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
# run_bwx11.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.
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
    """A copy of run_bwx11.sh and hostwatch.py with a test schedule in a temporary folder. The dummy bwx11 is beside
    the script, as on CRB. The dummy bwx8 and the dummy bwx10 are each in an own folder with an own build record."""

    def __init__(self, tmp, sched):
        self.dir = os.path.join(tmp, "box")
        os.makedirs(self.dir)
        shutil.copy(RUN, self.dir)
        shutil.copy(WATCH, self.dir)
        shutil.copytree(sched, os.path.join(self.dir, "sched11"))
        self.bin11 = dummy(self.dir, "bwx11")
        self.bin8 = dummy(os.path.join(tmp, "old8"), "bwx8")
        self.bin10 = dummy(os.path.join(tmp, "old10"), "bwx10")
        self.bin = {"bwx8": self.bin8, "bwx10": self.bin10, "bwx11": self.bin11}
        # A home folder with the accepted bwx8 and bwx10 at the paths that run_bwx11.sh uses on CRB.
        self.home = os.path.join(tmp, "home")
        self.home8 = dummy(os.path.join(self.home, "cache-perf", "bwx8-20261114"), "bwx8")
        self.home10 = dummy(os.path.join(self.home, "cache-perf", "bwx10-20261115"), "bwx10")
        os.makedirs(os.path.join(self.dir, "bin"))
        stub = os.path.join(self.dir, "bin", "ps")
        with open(stub, "w") as f:
            f.write(PS_STUB % shutil.which("ps"))
        os.chmod(stub, 0o755)
        self.watch_cpu = str(sorted(os.sched_getaffinity(0))[-1])
        self.n = 0

    def sched(self, *parts):
        return os.path.join(self.dir, "sched11", *parts)

    def set_bin(self, step, content):
        """Writes the .bin file of a step, in both sessions (the schedules of schedule11.py name bwx11)."""
        for s in ("s1", "s2"):
            if os.path.exists(self.sched(s, step + ".tsv")):
                with open(self.sched(s, step + ".bin"), "w") as f:
                    f.write(content)

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
             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256", "BWX10_SHA256", "BWX11_SHA256",
                          "BWX_PMU_TYPE", "BWX_EVENTS", "WATCH_CPU")}
        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin8, BWX10_BIN=self.bin10,
                 BWX11_BIN=self.bin11, BWX8_RESULTS=self.results, DUMMY_LOG=self.log, WATCH_CPU=self.watch_cpu)
        e.update(env)
        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out
        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx11.sh")] + args, env=e, text=True,
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
    """visit11.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""
    d = os.path.join(tmp, "visit")
    os.makedirs(os.path.join(d, "bin"))
    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())
    copy_path = os.path.join(d, "visit11.sh")
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
        r = subprocess.run([shutil.which("bash"), copy_path, name, "ZA", "ZD"], env=e, capture_output=True, text=True)
        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr

    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",
                         BWX8_SHA256="0a1b", BWX10_SHA256="2c3d", BWX11_SHA256="4e5f", ENVV="RESERVE=90")
    check("visit11.sh: one login; the marker check is the first remote action, then run_bwx11.sh in ~/cache-perf/bwx11-20261115 "
          "with the three digests",
          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1
          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")
          and cmd.endswith("exit 3; fi; cd ~/cache-perf/bwx11-20261115 && STOP_AT=2026-11-15T15:00Z SESSION=2 "
                           "SESSION1_END=2026-11-15T03:00Z BWX8_SHA256=0a1b BWX10_SHA256=2c3d BWX11_SHA256=4e5f RESERVE=90 "
                           "./run_bwx11.sh ZA ZD\n")
          and open(os.path.join(d, "ok.log")).read().startswith("ssh status 0 utc "), (rc, cmd, err))
    rc, cmd, err = visit("plain", STOP_AT="none", SESSION="1")
    check("visit11.sh without digests and SESSION1_END: the four settings are passed empty",
          rc == 0 and cmd is not None
          and cmd.endswith("STOP_AT=none SESSION=1 SESSION1_END= BWX8_SHA256= BWX10_SHA256= BWX11_SHA256=  ./run_bwx11.sh ZA ZD\n"),
          (rc, cmd, err))
    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b",
          "BWX10_SHA256": "2c3d", "BWX11_SHA256": "4e5f"}
    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),
                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b|x"), ("BWX10_SHA256", "2c3d x"),
                       ("BWX10_SHA256", "2c3d;id"), ("BWX11_SHA256", "4e5f x"), ("BWX11_SHA256", "4e5f;id"), ("BWX11_SHA256", "$(id)")):
        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))
        check("visit11.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),
              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")), (rc, cmd, err))
    rc, cmd, err = visit("nostop", SESSION="1")
    check("visit11.sh: STOP_AT not set: no login", rc != 0 and cmd is None, (rc, cmd, err))
    a, b = open(os.path.join(Y, "visit10.sh")).read().split("\n"), open(VISIT).read().split("\n")
    back = [l.replace("./run_bwx11.sh", "./run_bwx10.sh").replace("bwx11-20261115", "bwx10-20261115")
            .replace(" BWX11_SHA256=${BWX11_SHA256:-}", "").replace(" BWX11_SHA256;", ";") for l in b if not l.startswith("#")]
    check("visit11.sh differs from visit10.sh only in comment lines, the folder on CRB, the script that it starts and BWX11_SHA256",
          [l for l in a if not l.startswith("#")] == back and len(back) > 8, [x for x in back if x not in a][:2])
    check("visit11.sh names one host only, the CRB login of the handoff, and starts ssh once",
          re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", open(VISIT).read()) == ["192.168.2.45"]
          and len(re.findall(r"(?m)^ssh ", open(VISIT).read())) == 1 and "scp" not in open(VISIT).read())


def script_diff():
    """The code lines (no comment lines) that run_bwx11.sh adds to and removes from run_bwx10.sh, after the names of
    round 4 are written back to those of round 3."""
    old = [l for l in open(os.path.join(Y, "run_bwx10.sh")).read().split("\n") if not l.lstrip().startswith("#")]
    new = [l.replace("sched11", "sched10").replace("run_bwx11.sh", "run_bwx10.sh").replace("^Z[A-Z0-9]+$", "^Y[A-Z0-9]+$")
           .replace("$RESULTS/bwx11-$STEP_NAME", "$RESULTS/bwx10-$STEP_NAME")
           for l in open(RUN).read().split("\n") if not l.lstrip().startswith("#")]
    d = list(difflib.ndiff(old, new))
    return [l[2:] for l in d if l.startswith("+ ")], [l[2:] for l in d if l.startswith("- ")]


def run_checks(tmp, sched):
    for f in ("run_bwx11.sh", "visit11.sh"):
        r = subprocess.run(["bash", "-n", os.path.join(Z, f)], capture_output=True, text=True)
        check("bash -n " + f, r.returncode == 0, r.stderr)
    # The stop controls and the launch function are the text of run_bwx9.sh and run_bwx10.sh.
    part = re.compile(r"(?s)\n# ---- stop controls[^\n]*\n(.*?\n)# ---- end of the copied part ----\n")
    old, mid, new = (part.search(open(f).read()) for f in (os.path.join(X, "run_bwx9.sh"), os.path.join(Y, "run_bwx10.sh"), RUN))
    check("run_bwx11.sh keeps the stop controls and the launch function of run_bwx9.sh and run_bwx10.sh unchanged (54 lines: "
          "why_stop, check_marker, check_deadline, the trap, settle, one, stop_child, stop_watch)",
          old is not None and mid is not None and new is not None and old.group(1) == new.group(1) == mid.group(1)
          and old.group(1).count("\n") == 54
          and all(w in new.group(1) for w in ("why_stop()", "check_marker()", "check_deadline()", "trap '", "settle()", "one()")),
          old and old.group(1).count("\n"))
    added, removed = script_diff()
    key = ("for v in BWX8_MARKER", "BIN10=${BWX10_BIN:-$HOME/cache-perf/bwx10-20261115/bwx10}", "BIN11=${BWX11_BIN:-$SRC/bwx11}",
           "bwx11) BIN=$BIN11 ;;", "must hold the one word bwx8, bwx10 or bwx11", "case $BIN_WORD in bwx8) WANT=${BWX8_SHA256:-} ;; "
           "bwx10) WANT=${BWX10_SHA256:-} ;; *) WANT=${BWX11_SHA256:-} ;; esac", "BWX11_SHA256=${BWX11_SHA256:-} binary=$BIN_WORD")
    check("the code of run_bwx11.sh differs from run_bwx10.sh only in: the names (sched11, step pattern, result folder), the "
          "path of bwx10, the word bwx11, its test setting and its digest (7 lines added, 5 removed)",
          len(added) == 7 and len(removed) == 5 and all(sum(k in l for l in added) == 1 for k in key), (added, removed))
    check("RESERVE keeps its default of 90 s", open(RUN).read().count("RESERVE=${RESERVE:-90} ") == 1)
    box = Box(tmp, sched)
    absent = os.path.join(box.dir, "absent")
    last = {st: TABLE[st][0] - 1 for st in TABLE}            # the last idx of each step

    # ---- steps and the dry run ----
    for name in ("S2", "YF", "Zd", "Z", "Z-1", "ZD;id"):
        rc, out, err = box.run(["--dry-run", name], SESSION="1")
        check("step name '%s' is refused with status 2" % name, rc == 2 and "unknown step" in err and not out, (rc, err))
    rc, out, err = box.run(["--dry-run", "ZZ9"], SESSION="1")
    check("a name of the right form without a schedule: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))
    rc, out, err = box.run(["--dry-run", "ZD", "ZD"], SESSION="1")
    check("a step named twice: status 2", rc == 2 and "twice" in err and "step ZD" not in out, (rc, err))
    rc, out, err = box.run(["--dry-run"] + ALL_STEPS, SESSION="1", BWX8_BIN=absent, BWX10_BIN=absent, BWX11_BIN=absent)
    want = {"ZA": "6 processes, nominal kernel work 0.078 s", "ZD": "216 processes, nominal kernel work 20.736 s",
            "ZC": "32 processes, nominal kernel work 1.920 s", "ZN": "144 processes, nominal kernel work 13.824 s",
            "ZM": "40 processes, nominal kernel work 12.000 s"}
    check("--dry-run of all 5 steps, session 1, without the binaries and without counter settings: status 0, the counts of each step "
          "(6, 216, 32, 144, 40)",
          rc == 0 and all(("step %s session 1: %s" % kv) in out for kv in want.items())
          and out.count("\nbwx11 --trial ") == 438 and "\nbwx8 " not in out and "\nbwx10 " not in out and "warning" in err,
          (rc, out[:300], err[-300:]))
    check("--dry-run: the command lines are the binary word of the step and the args column",
          all(("bwx11 %s  # idx %s, tag %s, nominal " % (r[5], r[0], r[1])) in out
              for st in want for r in box.rows(st)) and out.count(" --pmu-type 11 --events ") == 32
          and out.count(" --rec-pad ") == 40 and out.count(" --evict-mb 512") == 126 and out.count(" --trace") == 6)
    check("--dry-run: the binary of each step is printed (bwx11 for every step)",
          sorted(re.findall(r"^step (\S+) binary: (\S+)$", out, re.M)) == sorted((st, "bwx11") for st in TABLE), out[:500])
    check("--dry-run: no host sampler is announced", "host sampler" not in out)
    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))
    rc, out, err = box.run(["--dry-run", "ZD", "ZC", "ZN", "ZM"], SESSION="2")
    check("--dry-run session 2: the first command line of each step uses CPU 41, and the steps hold 432 processes",
          rc == 0 and len(re.findall(r"# ---- step \S+ session 2 ----\n.*\n.*\n.*\nbwx11 --trial --cpus 41 ", out)) == 4
          and out.count("\nbwx11 --trial ") == 432, (rc, out[:500]))
    rc, out, err = box.run(["--dry-run", "ZA"], SESSION="2")
    check("ZA in session 2: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))
    rc, out, err = box.run(["--dry-run", "ZD"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX10_BIN=None,
                           BWX11_BIN=None, BWX8_RESULTS=None)
    check("no warning without the test settings", rc == 0 and "warning" not in err, err)
    rc, out, err = box.run(["--dry-run", "ZD"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX10_BIN=None,
                           BWX8_RESULTS=None)
    check("BWX11_BIN alone gives its warning", rc == 0 and err.count("warning") == 1 and "BWX11_BIN" in err, err)

    # ---- a normal run of a bwx11 step: ZA ----
    rows = box.rows("ZA")
    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none")
    f = box.folder()
    csv = box.csv("ZA")
    heads = re.findall(r"^-- step ZA session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)
    check("ZA normal end: status 0, the counts are printed before the result folder is made",
          rc == 0 and 0 <= out.find("step ZA session 1: 6 processes") < out.find("result folder: "), (rc, err, out))
    check("ZA normal end: folder name bwx11-ZA-s1-<UTC> and its six files, no sampler file",
          f is not None and re.match(r"^bwx11-ZA-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None
          and sorted(os.listdir(f)) == ["ZA.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],
          f and os.listdir(f))
    check("ZA normal end: one header line per process in schedule order, each followed by its output; schedule.tsv is a copy",
          heads == [(r[0], r[1], r[5]) for r in rows] and csv.count("M,dummy,bwx11\n") == 6 and "-- killed" not in csv
          and "-- failed" not in csv and box.file("schedule.tsv") == open(box.sched("s1", "ZA.tsv")).read(), heads)
    launched = [l for l in box.launched() if not l.endswith(" sleep")]
    check("ZA normal end: the binary gets the args column (--trace, --evict-mb 512), no counter setting in its environment",
          [l.split(" ", 1)[1] for l in launched] == [r[5] for r in rows] and launched[0].endswith(".plan --trace")
          and launched[1].endswith(" --trace --evict-mb 512") and launched[2].endswith(" --trace --evict-mb 512")
          and open(box.log + ".env").read() == "PMU= EV=\n" * 6 and box.none_alive(), launched)
    check("ZA normal end: every process is the binary named bwx11, and build.txt is the build record beside it",
          box.binaries() == [box.bin11] * 6 and box.file("build.txt") == "dummy build record of bwx11\n", box.binaries()[:2])
    env = box.file("env.txt")
    check("ZA normal end: env.txt holds session, from, load, the word and the digests of the binary, of run_bwx11.sh, of the schedule "
          "and of the build record, the three digest settings, paths, end line",
          "session=1 from=0 " in env and "loadavg=" in env and "## end utc=" in env and "/run_bwx11.sh\n" in env
          and "/sched11/s1/ZA.tsv\n" in env and "host sampler" not in env and " BWX8_SHA256= BWX10_SHA256= BWX11_SHA256= binary=bwx11 " in env
          and ("%s  %s\n" % (sha256(box.bin11), box.bin11)) in env
          and ("%s  %s\n" % (sha256(os.path.join(box.dir, "build.txt")), os.path.join(box.dir, "build.txt"))) in env
          and (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin11, box.results)) in env
          and box.file("launches.txt").count("== ZA.csv idx ") == 6, env)

    # ---- the binary of a step. The schedules name bwx11 for every step. From here to the end of the stop controls the
    # ---- .bin file of ZM holds bwx8 and that of ZC holds bwx10, so every word is tested with a step. ----
    box.set_bin("ZM", "bwx8\n")
    box.set_bin("ZC", "bwx10\n")
    word_of = {"ZM": "bwx8", "ZC": "bwx10", "ZA": "bwx11"}
    for step in ("ZM", "ZC"):
        word = word_of[step]
        rc, out, err = box.run(["--from", str(last[step] - 1), step], SESSION="1", STOP_AT="none")
        env = box.file("env.txt")
        check("%s with the word %s: the two processes are that binary, build.txt is the record from its folder, env.txt names it"
              % (step, word),
              rc == 0 and box.binaries() == [box.bin[word]] * 2 and box.file("build.txt") == "dummy build record of %s\n" % word
              and (" binary=%s " % word) in env and (" BIN=%s RESULTS=" % box.bin[word]) in env
              and ("%s  %s\n" % (sha256(box.bin[word]), box.bin[word])) in env
              and ("  %s\n" % os.path.join(os.path.dirname(box.bin[word]), "build.txt")) in env
              and os.path.basename(box.folder() or "").startswith("bwx11-%s-s1-" % step)
              and box.csv(step).count("M,dummy,%s\n" % word) == 2
              and ("to run from idx %d: 2 processes" % (last[step] - 1)) in out and ("step %s binary: %s\n" % (step, word)) in out,
              (rc, err, box.binaries()))
    # The three words in one call: the schedules of ZM, ZC and ZA are cut to their first two rows for this case.
    saved = {st: open(box.sched("s1", st + ".tsv")).read() for st in ("ZM", "ZC", "ZA")}
    for st, text in saved.items():
        with open(box.sched("s1", st + ".tsv"), "w") as fh:
            fh.write("\n".join(text.split("\n")[:3]) + "\n")
    rc, out, err = box.run(["ZM", "ZC", "ZA"], SESSION="1", STOP_AT="none")
    fl = box.folders()
    check("one call with a bwx8 step, a bwx10 step and a bwx11 step: each step starts its own binary and copies its own build record",
          rc == 0 and box.binaries() == [box.bin8] * 2 + [box.bin10] * 2 + [box.bin11] * 2 and len(fl) == 3
          and all(("bwx11-%s-s1-" % st) in fl[i] and open(os.path.join(fl[i], "build.txt")).read() == "dummy build record of %s\n" % w
                  for i, (st, w) in enumerate((("ZA", "bwx11"), ("ZC", "bwx10"), ("ZM", "bwx8")))),
          (rc, err, box.binaries(), fl))
    for st, text in saved.items():
        with open(box.sched("s1", st + ".tsv"), "w") as fh:
            fh.write(text)
    for step, path, where in (("ZM", box.home8, "$HOME/cache-perf/bwx8-20261114/bwx8"),
                              ("ZC", box.home10, "$HOME/cache-perf/bwx10-20261115/bwx10"),
                              ("ZA", box.bin11, "bwx11 beside run_bwx11.sh")):
        word = word_of[step]
        rc, out, err = box.run(["--from", str(last[step]), step], SESSION="1", STOP_AT="none", BWX8_BIN=None, BWX10_BIN=None,
                               BWX11_BIN=None, HOME=box.home)
        check("without the test settings the word %s is %s, with the build record of that folder" % (word, where),
              rc == 0 and box.binaries() == [path] and box.file("build.txt") == "dummy build record of %s\n" % word
              and (" BIN=%s RESULTS=" % path) in box.file("env.txt"), (rc, err, box.binaries()))
    made = os.path.join(box.dir, "made-by-bin")
    for what, content in (("another word", "bwx9\n"), ("two words", "bwx8 bwx11\n"), ("two lines", "bwx8\nbwx11\n"), ("nothing", ""),
                          ("a path", "/bin/true\n"), ("a command", "$(touch %s)\n" % made)):
        box.set_bin("ZM", content)
        rc, out, err = box.run(["--from", "39", "ZM"], SESSION="1", STOP_AT="none")
        rc2, out2, err2 = box.run(["--dry-run", "ZM"], SESSION="1")
        check("ZM.bin with %s: status 2 in a run and in a dry run, nothing starts, no result folder" % what,
              rc == 2 and rc2 == 2 and "must hold the one word bwx8, bwx10 or bwx11" in err and "must hold" in err2
              and not box.launched() and not os.path.exists(box.results) and not os.path.exists(made) and "bwx" not in out2, (rc, err, rc2))
    os.remove(box.sched("s1", "ZM.bin"))
    rc, out, err = box.run(["ZA", "ZM"], SESSION="1", STOP_AT="none")
    check("ZM.bin missing, ZM second in the call: status 2 before the first process of the call",
          rc == 2 and "ZM.bin (the binary of step ZM)" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    for word in ("bwx11", "bwx10", "bwx8"):
        box.set_bin("ZM", word + "\n")
        rc, out, err = box.run(["--from", "39", "ZM"], SESSION="1", STOP_AT="none")
        check("the word decides, not the step name: ZM.bin with %s starts the binary %s" % (word, word),
              rc == 0 and box.binaries() == [box.bin[word]] and (" binary=%s " % word) in box.file("env.txt"), (rc, err))

    # ---- the digests (ZM uses bwx8, ZC uses bwx10, ZA uses bwx11) ----
    dig = {w: sha256(box.bin[w]) for w in box.bin}
    zero = "0" * 64
    check("the three dummy binaries differ, so each digest names one of them", len(set(dig.values())) == 3)
    one_proc = {"ZM": ["--from", "39", "ZM"], "ZC": ["--from", "31", "ZC"], "ZA": ["--from", "5", "ZA"]}
    cases = []
    for step, word in sorted(word_of.items()):
        var = word.upper() + "_SHA256"
        others = sorted(w for w in dig if w != word)
        cases.append(("%s wrong, a %s step (%s)" % (var, word, step), one_proc[step], {var: zero}, 2))
        cases.append(("%s right, a %s step (%s)" % (var, word, step), one_proc[step], {var: dig[word]}, 0))
        cases.append(("%s holds the digest of %s, a %s step (%s)" % (var, others[0], word, step), one_proc[step],
                      {w.upper() + "_SHA256": dig[others[0]] for w in dig}, 2))
        cases.append(("the digests of %s and %s wrong, a %s step only (%s; a binary that is not used is not checked)"
                      % (others[0], others[1], word, step), one_proc[step], {w.upper() + "_SHA256": zero for w in others}, 0))
        cases.append(("all three right, a %s step (%s)" % (word, step), one_proc[step], {w.upper() + "_SHA256": dig[w] for w in dig}, 0))
    right = {w.upper() + "_SHA256": dig[w] for w in dig}
    cases += [("BWX11_SHA256 right and BWX8_SHA256 wrong, a call with ZA then ZM", ["ZA", "ZM"], dict(right, BWX8_SHA256=zero), 2),
              ("BWX8_SHA256 right and BWX10_SHA256 wrong, a call with ZM then ZC", ["ZM", "ZC"], dict(right, BWX10_SHA256=zero), 2),
              ("BWX8_SHA256 and BWX10_SHA256 right and BWX11_SHA256 wrong, a call with ZM, ZC, then ZA", ["ZM", "ZC", "ZA"],
               dict(right, BWX11_SHA256=zero), 2)]
    for name, args, env_, want_rc in cases:
        rc, out, err = box.run(args, SESSION="1", STOP_AT="none", **env_)
        if want_rc:
            check("%s: status 2 before the first process of the call, no result folder" % name,
                  rc == 2 and "is not the binary with the digest given for it" in err and not box.launched()
                  and not os.path.exists(box.results), (rc, err))
        else:
            e = box.file("env.txt")
            check("%s: runs, and env.txt records the three settings" % name,
                  rc == 0 and len(box.launched()) == 2 and (" BWX8_SHA256=%s BWX10_SHA256=%s BWX11_SHA256=%s binary=" % (
                      env_.get("BWX8_SHA256", ""), env_.get("BWX10_SHA256", ""), env_.get("BWX11_SHA256", ""))) in e, (rc, err))
    rc, out, err = box.run(["--dry-run", "ZM", "ZC", "ZA"], SESSION="1", BWX8_SHA256=zero, BWX10_SHA256=zero, BWX11_SHA256=zero)
    check("a dry run checks no digest", rc == 0, (rc, err))
    for step, word in sorted(word_of.items()):
        var = word.upper() + "_BIN"
        rc, out, err = box.run(one_proc[step], SESSION="1", STOP_AT="none", **{var: absent})
        check("the binary of the step is missing (%s, step %s): status 2" % (word, step),
              rc == 2 and "missing" in err and word in err and not box.launched(), (rc, err))
    rc, out, err = box.run(one_proc["ZA"], SESSION="1", STOP_AT="none", BWX8_BIN=absent, BWX10_BIN=absent)
    check("a missing bwx8 and a missing bwx10 do not stop a call that uses bwx11 only", rc == 0 and len(box.launched()) == 2, (rc, err))
    rc, out, err = box.run(["ZM", "ZA"], SESSION="1", STOP_AT="none", BWX11_BIN=absent)
    check("the binary of the second step is missing (bwx11): status 2 before the first process of the call",
          rc == 2 and "missing" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    os.rename(os.path.join(os.path.dirname(box.bin10), "build.txt"), os.path.join(os.path.dirname(box.bin10), "build.moved"))
    rc, out, err = box.run(one_proc["ZC"], SESSION="1", STOP_AT="none")
    rc2, out2, err2 = box.run(one_proc["ZA"], SESSION="1", STOP_AT="none")
    check("build.txt missing beside bwx10: a bwx10 step stops with status 2, a bwx11 step runs",
          rc == 2 and "build.txt" in err and rc2 == 0 and len(box.launched()) == 2, (rc, err, rc2, err2))
    os.rename(os.path.join(os.path.dirname(box.bin10), "build.moved"), os.path.join(os.path.dirname(box.bin10), "build.txt"))

    # ---- the rule for the counter settings ----
    tsv = box.sched("s1", "ZC.tsv")
    saved_zc = open(tsv).read()
    with open(tsv, "w") as fh:
        fh.write(re.sub(r" --pmu-type 11 --events \S+", "", saved_zc))
    rc, out, err = box.run(["ZC"], SESSION="1", STOP_AT="none")
    check("a counted step without the options in args and without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",
          rc == 2 and "needs BWX_PMU_TYPE" in err and not box.launched() and open(tsv).read() != saved_zc, (rc, err))
    rc, out, err = box.run(["ZC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11")
    check("the same with BWX_PMU_TYPE only: status 2, nothing starts", rc == 2 and "needs BWX_EVENTS" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "31", "ZC"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11", BWX_EVENTS="a=0x11")
    check("the same with both settings: runs, and the binary finds them in its environment",
          rc == 0 and len(box.launched()) == 2 and open(box.log + ".env").read() == "PMU=11 EV=a=0x11\n", (rc, err))
    rc, out, err = box.run(["--dry-run", "ZC"], SESSION="1", BWX_PMU_TYPE="eleven", BWX_EVENTS="a=0x11")
    check("BWX_PMU_TYPE that is not a whole number: status 2", rc == 2 and "whole number" in err, (rc, err))
    with open(tsv, "w") as fh:
        fh.write(saved_zc)
    rc, out, err = box.run(["--from", "31", "ZC"], SESSION="1", STOP_AT="none")
    check("ZC as scheduled (options in args) needs no counter setting: runs with --pmu-type 11 and the 6 events on the command line",
          rc == 0 and len(box.launched()) == 2 and box.launched()[0].endswith(" --pmu-type 11 --events " + EVENTS)
          and open(box.log + ".env").read() == "PMU= EV=\n", (rc, err))
    rc, out, err = box.run(["--from", "215", "ZD"], SESSION="1", STOP_AT="none")
    check("an uncounted step (ZD, count closed) needs no counter setting: runs",
          rc == 0 and len(box.launched()) == 2 and "--plan sched11/s1/ZD/0215.plan" in box.launched()[0]
          and re.findall(r"^-- step ZD session 1 idx (\d+) ", box.csv("ZD"), re.M) == ["215"]
          and " from=215 " in box.file("env.txt") and "to run from idx 215: 1 processes" in out, (rc, err))

    # ---- the host sampler is still started by a .watch file (no schedule of round 4 has one) ----
    open(box.sched("s1", "ZA.watch"), "w").close()
    rc, out, err = box.run(["--from", "5", "ZA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="2")
    w = box.file("watch-5.txt")
    pid = box.launched()[0].split()[0] if box.launched() else "?"
    check("a step with a .watch file runs with hostwatch.py: watch-5.txt names the benchmark process and the CPU of its row, "
          "has samples and its end line; the sampler is gone",
          rc == 0 and w.startswith("# hostwatch v1 pid=%s cpu=2 hz=20 max_s=31\n" % pid) and "\n# end reason=" in w
          and " m.run_ns=" in w and box.none_alive() and "host sampler: hostwatch.py on CPU %s " % box.watch_cpu in out
          and re.search(r"^## host sampler: WATCH_CPU=%s Python \S+ sha256 %s$" % (box.watch_cpu, sha256(WATCH)),
                        box.file("env.txt"), re.M) is not None, (rc, err, w[:200]))
    rc, out, err = box.run(["--from", "5", "ZA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")
    check("a step with a .watch file and WATCH_CPU=126: status 2, nothing starts",
          rc == 2 and "WATCH_CPU must be a CPU from 0 to 119" in err and not box.launched(), (rc, err))
    os.remove(box.sched("s1", "ZA.watch"))
    rc, out, err = box.run(["--from", "5", "ZA"], SESSION="1", STOP_AT="none", WATCH_CPU="126")
    check("a step without a .watch file does not read WATCH_CPU and writes no sampler file",
          rc == 0 and len(box.launched()) == 2 and not [f for f in os.listdir(box.folder()) if f.startswith("watch")], (rc, err))

    # ---- stop controls, for a step of each binary ----
    for step, word in (("ZM", "bwx8"), ("ZC", "bwx10"), ("ZA", "bwx11")):
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
              and box.binaries() == [box.bin[word]], (rc, err, csv))
    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")
    csv = box.csv("ZA")
    check("marker file appears between two processes: status 3, the first process ended, the second does not start",
          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,bwx11\n") == 1 and "-- killed" not in csv
          and len(box.launched()) == 2, (rc, err, csv))
    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case
    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none", PS_TOUCH=late,
                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])
    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",
          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("ZA")
          and box.file("launches.txt").count("== ZA.csv idx ") == 1, (rc, err))
    rc, out, err = box.run(["ZA"], SESSION="1")
    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))
    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the test
    # divisor 100 the longest process is 0.3 s (1 s); with divisor 1 the processes of ZM are 30 s and those of ZD 9.6 s.
    os.rename(box.sched(), os.path.join(box.dir, "sched11-test"))
    shutil.copytree(os.path.join(Z, "sched11"), box.sched())
    rc, out, err = box.run(["ZM"], SESSION="1", STOP_AT=utc(100))
    check("MARGIN follows the longest process of the step: the real ZM schedule refuses at 120 s, not at 91 s",
          rc == 4 and not box.launched() and "less than 120 s away" in err and "longest process 30 s, MARGIN 120 s" in out,
          (rc, err, out))
    rc, out, err = box.run(["ZD"], SESSION="1", STOP_AT=utc(95))
    check("the real ZD schedule: longest process 10 s (9.6 s of kernel work; the evict step is not in it), MARGIN 100 s",
          rc == 4 and not box.launched() and "less than 100 s away" in err and "longest process 10 s, MARGIN 100 s" in out,
          (rc, err, out))
    rc, out, err = box.run(["--dry-run"] + ALL_STEPS, SESSION="1")
    check("--dry-run of the real schedules, session 1: 438 processes of bwx11 and the nominal work of the task "
          "(7.8, 2073.6, 192, 1382.4, 1200 s)",
          rc == 0 and out.count("\nbwx11 --trial ") == 438 and "\nbwx8 " not in out and "\nbwx10 " not in out
          and all(s in out for s in ("step ZA session 1: 6 processes, nominal kernel work 7.800 s",
                                     "step ZD session 1: 216 processes, nominal kernel work 2073.600 s",
                                     "step ZC session 1: 32 processes, nominal kernel work 192.000 s",
                                     "step ZN session 1: 144 processes, nominal kernel work 1382.400 s",
                                     "step ZM session 1: 40 processes, nominal kernel work 1200.000 s")), (rc, err, out[:300]))
    rc, out, err = box.run(["--dry-run", "ZD", "ZC", "ZN", "ZM"], SESSION="2")
    check("--dry-run of the real schedules, session 2: 432 processes of bwx11",
          rc == 0 and out.count("\nbwx11 --trial ") == 432, (rc, err))
    shutil.rmtree(box.sched())
    os.rename(os.path.join(box.dir, "sched11-test"), box.sched())

    # ---- session 2 (ZM still names bwx8, ZC bwx10) ----
    rc, out, err = box.run(["ZD"], SESSION="2", STOP_AT="none")
    check("session 2 without SESSION1_END: status 2, nothing starts",
          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))
    for step in ("ZM", "ZD"):
        rc, out, err = box.run([step], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))
        check("session 2 of %s earlier than 3 h after SESSION1_END: refused with status 2, nothing starts" % step,
              rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "@0", "-4 hours",
                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)), "2026-02-30T00:00Z"):
        rc, out, err = box.run(["--from", "215", "ZD"], SESSION="2", STOP_AT="none", SESSION1_END=value)
        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,
              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    s1end = utc(-3 * 3600 - 60)
    row2 = box.rows("ZD", 2)[215]
    rc, out, err = box.run(["--from", "215", "ZD"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)
    env = box.file("env.txt")
    check("session 2 later than 3 h after SESSION1_END: runs the session 2 schedule, folder bwx11-ZD-s2-, SESSION1_END in env.txt",
          rc == 0 and "bwx11-ZD-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env
          and ("-- step ZD session 2 idx 215 tag %s " % row2[1]) in box.csv("ZD")
          and "--plan sched11/s2/ZD/0215.plan" in box.launched()[0] and box.binaries() == [box.bin11], (rc, err))
    for step, word in (("ZM", "bwx8"), ("ZC", "bwx10")):
        row2 = box.rows(step, 2)[last[step]]
        rc, out, err = box.run(["--from", str(last[step]), step], SESSION="2", STOP_AT="none", SESSION1_END=s1end)
        check("session 2 of a step with the word %s (%s): runs the session 2 row with that binary" % (word, step),
              rc == 0 and box.binaries() == [box.bin[word]] and ("-- step %s session 2 idx %d tag %s " % (step, last[step], row2[1])) in box.csv(step)
              and box.launched()[0].split(" ", 1)[1] == row2[5], (rc, err))

    # ---- other refusals ----
    rc, out, err = box.run(["ZA"], STOP_AT="none")
    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "6", "ZA"], SESSION="1", STOP_AT="none")
    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "1", "ZA", "ZD"], SESSION="1", STOP_AT="none")
    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))
    allowed = sorted(os.sched_getaffinity(0))
    rc, out, err = box.run(["--from", "5", "ZA"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")
    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""
    check("the benchmark is confined to CPUs 0-119, whatever CPU the script was started on",
          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1 and cpu_list(seen) == {c for c in allowed if c < 120},
          (rc, err, seen))
    tsv = box.sched("s1", "ZA.tsv")
    saved_za = open(tsv).read()
    made = os.path.join(box.dir, "made-by-schedule")
    for what, old_, new_ in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("cpu", "\t2\t", "\ta[$(touch${IFS}%s)]\t")):
        with open(tsv, "w") as fh:
            fh.write(saved_za.replace(old_, new_ % made, 1))
        rc, out, err = box.run(["--dry-run", "ZA"], SESSION="1")
        check("schedule with a command in %s: status 2, the command does not run" % what,
              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved_za, (rc, err))
    with open(tsv, "w") as fh:
        fh.write(saved_za)
    os.rename(box.sched("s1", "ZA", "0001.plan"), os.path.join(box.dir, "moved.plan"))
    rc, out, err = box.run(["ZA"], SESSION="1", STOP_AT="none")
    check("missing plan file: status 2 before the first launch", rc == 2 and "missing plan file" in err and not box.launched(), (rc, err))


def main():
    with open("/proc/loadavg") as f:
        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))
    tmp = tempfile.mkdtemp(prefix="test_schedule11.")
    try:
        real, sched = schedule_checks(tmp)
        if "--no-bwx10" in sys.argv[1:]:
            skip("the checks that the local stand-in bwx10 refuses the args and plans of round 4 (--no-bwx10)")
        else:
            bwx10_checks(tmp, sched)
        bwx11_checks(tmp, real, sched)
        visit_checks(tmp)
        if "--no-run" in sys.argv[1:]:
            skip("the checks of run_bwx11.sh with dummy binaries (--no-run)")
        else:
            run_checks(tmp, sched)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open("/proc/loadavg") as f:
        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))
    print("# checks: %d, passed: %d, failed: %d, parts not run (SKIP lines): %d%s"
          % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS), SKIPS[0], "".join("\n#   " + n for n in FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
