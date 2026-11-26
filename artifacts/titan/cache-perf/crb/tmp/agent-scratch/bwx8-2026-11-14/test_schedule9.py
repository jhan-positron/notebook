#!/usr/bin/env python3
"""test_schedule9.py - checks of schedule9.py, hostwatch.py, run_bwx9.sh and visit9.sh (round 2).

Usage: test_schedule9.py [--no-run] [--no-bwx8]
Prints one line per check. Exit status 0 only if every check passed.
--no-run leaves out the checks that start run_bwx9.sh with a dummy bwx8 (they take minutes
on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).
--no-bwx8 leaves out the build of the local stand-in bwx8 and the run of every plan through it.
Rules are also applied to a defective input, and such a check passes only if that is rejected.
This machine has no CPU 41: for the run through bwx8 the test rewrites CPU 41 to a local CPU
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
import statistics
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
X = os.path.dirname(os.path.abspath(__file__))
SCHED = os.path.join(X, "schedule9.py")
RUN = os.path.join(X, "run_bwx9.sh")
VISIT = os.path.join(X, "visit9.sh")
WATCH = os.path.join(X, "hostwatch.py")
READ_KERNELS = ["oldread", "read", "asmread", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse"]
# The flags of build8.sh.
CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "
          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()
# The task: processes per step and session, trials per process, nominal kernel work in seconds.
TABLE = {"XW": (28, 1, 864.0), "XCA": (18, 1, 396.0), "XCB": (18, 1, 396.0), "XCC": (18, 1, 396.0),
         "XEV": (3, 1, 2.7), "XN": (144, 4, 1382.4), "XF": (90, 4, 864.0)}
WATCH_STEPS = ["XCA", "XCB", "XCC", "XW"]
EVENTS = {
    "A": "cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17,l3d_cache_refill=0x2a,stall_backend_mem=0x4005",
    "B": "l1d_cache_lmiss_rd=0x39,l2d_cache_lmiss_rd=0x4009,l3d_cache_lmiss_rd=0x400b,ll_cache_miss_rd=0x37,l2d_cache=0x16,bus_access=0x19",
    "C": "exc_taken=0x09,l1d_tlb_refill=0x05,dtlb_walk=0x34,l2d_cache_wb=0x18,l3d_cache_allocate=0x29,mem_access=0x13",
}
# name: (kernel, size, previous activity)
XW = {"W0": ("read", "8M", None), "W1": ("read", "8M", "oldread@8M"), "W2": ("read", "8M", "read@1M"),
      "W3": ("asmread", "8M", None), "W4": ("oldread", "8M", None), "W5": ("read", "4M", None),
      "W6": ("read", "16M", None)}
XN_KERNELS = ["asmread", "read_nop16", "read_nop32", "read_sparse"]
XN_SIZES = ["32K", "1M", "8M"]
XF_CELLS = [("read", s) for s in ("1572864", "2M", "2621440", "3M", "5M", "6M", "12M", "24M", "32M", "64M")] + \
           [("oldread", s) for s in ("2M", "3M", "6M", "12M", "32M")]
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
        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and int(win_ms) >= 1):
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
                want = "--trial --cpus %d --bytes %d --plan sched9/s%d/%s/%s" % (p["cpu"], p["bytes"], session, step, f[4])
                if not (f[5] == want or f[5].startswith(want + " --pmu-type ")):
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


def s2_style(p, k, s):
    """4 trials: the kernel at the size, with itself as 1.2 s prefix, 4 windows, uncounted."""
    t = p["trials"]
    return len(t) == 4 and all(
        x == {"cond": "K=%s|S=%s" % (k, s), "rep": i + 1, "prev": "-", "pfx": "%s@%s:%d" % (k, s, 4 * x["win_ms"]),
              "pred": "-", "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": x["win_ms"], "count": "closed", "bins": 0,
              "ms": 8 * x["win_ms"]} for i, x in enumerate(t)) and \
        p["bytes"] == nbytes(s) and p["head"].get("size") == str(nbytes(s)) and p["head"].get("kernel") == k


# ---------- rules of the steps; each returns a list of defects ----------
def xw_rules(procs, cpus, win=300, prev_ms=3000):
    bad = []
    if len(procs) != 28:
        return ["process count %d" % len(procs)]
    for b in range(4):
        block = procs[7 * b:7 * b + 7]
        r, cpu = b // 2 + 1, cpus[b % 2]
        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):
            bad.append("block %d: CPU or rep_set" % b)
        if sorted(p["head"].get("wcond") for p in block) != sorted(XW):
            bad.append("block %d: does not hold every condition once" % b)
    for p in procs:
        name = p["head"].get("wcond")
        if name not in XW:
            bad.append("process %d: wcond" % p["idx"])
            continue
        k, s, prev = XW[name]
        want = {"cond": "K=%s|S=%s|prev=%s" % (k, s, prev or "none"), "rep": 1,
                "prev": "%s:%d" % (prev, prev_ms) if prev else "-", "pfx": "-", "pred": "-", "tgt": "%s@%s" % (k, s),
                "nwin": 100, "win_ms": win, "count": "closed", "bins": 0, "ms": 100 * win + (prev_ms if prev else 0)}
        if p["trials"] != [want]:
            bad.append("process %d (%s): trial" % (p["idx"], name))
        if p["bytes"] != nbytes(s) or p["head"].get("kernel") != k or p["head"].get("size") != str(nbytes(s)) \
                or p["head"].get("prev") != (prev or "none") or p["extra"] or not p["tag"].startswith(name + "-"):
            bad.append("process %d (%s): bytes, header, args or tag" % (p["idx"], name))
    if len({tuple(p["head"].get("wcond") for p in procs[7 * b:7 * b + 7]) for b in range(4)}) < 2:
        bad.append("the condition order is the same in every block")
    return bad


def xc_rules(procs, cpus, evset, win=300):
    bad = []
    if len(procs) != 18:
        return ["process count %d" % len(procs)]
    if [k for k, _ in itertools.groupby(p["cpu"] for p in procs)] != [cpus[0], cpus[1], cpus[0], cpus[1]]:
        bad.append("CPU blocks are not first, second, first, second")
    want = collections.Counter()
    for cpu in cpus:
        for k in ("read", "asmread", "oldread"):
            want[cpu, k, "8M", 100] = 2
        for s in ("1M", "32K", "16M"):
            want[cpu, "read", s, 20] = 1
    got = collections.Counter()
    for p in procs:
        t = p["trials"][0]
        k, s = t["tgt"].split("@")
        got[p["cpu"], k, s, t["nwin"]] += 1
        if p["trials"] != [{"cond": "K=%s|S=%s|count=read" % (k, s), "rep": 1, "prev": "-", "pfx": "-", "pred": "-",
                            "tgt": t["tgt"], "nwin": t["nwin"], "win_ms": win, "count": "read", "bins": 0,
                            "ms": t["nwin"] * win}]:
            bad.append("process %d: trial" % p["idx"])
        if p["bytes"] != nbytes(s) or p["head"].get("evset") != evset or p["head"].get("kernel") != k:
            bad.append("process %d: bytes or header" % p["idx"])
        if p["extra"] != " --pmu-type 11 --events " + EVENTS[evset]:
            bad.append("process %d: event set in args" % p["idx"])
    if got != want:
        bad.append("kernels, sizes and window counts per CPU")
    for b, cpu in enumerate([cpus[0], cpus[1], cpus[0], cpus[1]]):
        block = [p for p in procs if p["cpu"] == cpu and p["head"].get("rep_set") == str(b // 2 + 1)]
        if sorted(p["trials"][0]["tgt"] for p in block if p["trials"][0]["nwin"] == 100) != ["asmread@8M", "oldread@8M", "read@8M"]:
            bad.append("block %d: the three 8M kernels are not there once each" % b)
    return bad


def xn_rules(procs, cpus):
    bad = []
    if len(procs) != 144:
        return ["process count %d" % len(procs)]
    sets = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in procs:
        h = p["head"]
        k, s = h.get("kernel"), p["tag"].split("-")[1]
        if k not in XN_KERNELS or s not in XN_SIZES or not s2_style(p, k, s):
            bad.append("process %d: not 4 trials of one kernel of the family with itself as prefix" % p["idx"])
        if p["order"] != HEAD_S2 or p["extra"]:
            bad.append("process %d: header keys or args" % p["idx"])
        sets[s, p["cpu"]][int(h.get("rep_set", 0))].append(k)
    assign = set()
    if len(sets) != 6:
        bad.append("sizes and CPUs")
    for (s, cpu), orders in sets.items():
        o = [tuple(orders[r]) for r in sorted(orders)]
        if sorted(orders) != [1, 2, 3, 4, 5, 6] or any(sorted(x) != sorted(XN_KERNELS) for x in o):
            bad.append("size %s cpu %d: not 6 sets of the 4 kernels" % (s, cpu))
            continue
        if len(set(o)) != 6:
            bad.append("size %s cpu %d: a kernel order occurs twice" % (s, cpu))
        pos = collections.Counter((k, i) for x in o for i, k in enumerate(x))
        if len(pos) != 16 or not set(pos.values()) <= {1, 2}:
            bad.append("size %s cpu %d: a kernel is not once or twice at each position" % (s, cpu))
        assign.add(tuple(o))
    if len(assign) < 2:
        bad.append("every size and CPU uses the same kernel orders")
    size_orders = set()
    for r in range(6):
        block = procs[24 * r:24 * r + 24]
        if any(p["head"].get("rep_set") != str(r + 1) for p in block):
            bad.append("block %d: rep_set" % (r + 1))
        sizes = []
        for g in range(3):
            eight = block[8 * g:8 * g + 8]
            if len({p["bytes"] for p in eight}) != 1 or [p["cpu"] for p in eight] != [cpus[0]] * 4 + [cpus[1]] * 4:
                bad.append("block %d group %d: size or CPU order" % (r + 1, g))
            sizes.append(eight[0]["bytes"])
        if len(set(sizes)) != 3:
            bad.append("block %d: a size is missing" % (r + 1))
        size_orders.add(tuple(sizes))
    if len(size_orders) < 2:
        bad.append("the size order is the same in every block")
    return bad


def xf_rules(procs, cpus):
    bad = []
    if len(procs) != 90:
        return ["process count %d" % len(procs)]
    orders = set()
    for b in range(6):
        block = procs[15 * b:15 * b + 15]
        r, cpu = b // 2 + 1, cpus[b % 2]
        if any(p["cpu"] != cpu or p["head"].get("rep_set") != str(r) for p in block):
            bad.append("block %d: CPU or rep_set" % b)
        cells = [(p["head"].get("kernel"), p["tag"].split("-")[1]) for p in block]
        if sorted(cells) != sorted(XF_CELLS):
            bad.append("block %d: does not hold every kernel and size once" % b)
        orders.add(tuple(cells))
    for p in procs:
        if not s2_style(p, p["head"].get("kernel"), p["tag"].split("-")[1]) or p["order"] != HEAD_S2 or p["extra"]:
            bad.append("process %d: trials, header keys or args" % p["idx"])
    if len(orders) != 6:
        bad.append("two blocks have the same order")
    return bad


def schedule_checks(tmp):
    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))
    r = gen(a)
    check("schedule9.py runs with status 0", r.returncode == 0, r.stderr)
    tree, errors = load(a)
    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])
    check("the 7 steps exist in session 1; session 2 has the same steps without XEV",
          sorted(tree) == sorted([(s, 1) for s in TABLE] + [(s, 2) for s in TABLE if s != "XEV"]), sorted(tree))

    # The validator itself rejects defective plans.
    good = open(os.path.join(a, "s1", "XW", "0000.plan")).read()
    w1 = [p for p in tree["XW", 1] if p["head"]["wcond"] == "W1"][0]
    good1 = open(os.path.join(a, "s1", "XW", w1["plan"])).read()
    line = good.split("\n")[3]
    bad = {"rep not 1": good.replace(line, line.replace(" 1 - ", " 2 - ", 1)),
           "size above bytes": good1.replace("oldread@8M:3000", "oldread@16M:3000"),
           "unknown kernel": good1.replace("oldread@8M:3000", "copy@8M:3000"),
           "previous activity without a duration": good1.replace("oldread@8M:3000", "oldread@8M"),
           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),
           "trial number": good.replace("\n0 ", "\n1 ", 1),
           "wrong first line": good.replace("plan v1", "plan v2"),
           "count word": good.replace(line, line.replace("closed", "shut")),
           "comma in cond": good.replace(line, line.replace("|", ",", 1)),
           "blank in cond": good.replace(line, line.replace("|", " ", 1)),
           "header lacks seed": good.replace(" seed=", " sead=")}
    check("validator accepts generated plans", not rejected(good) and not rejected(good1))
    for name, text in bad.items():
        check("validator rejects: " + name, text not in (good, good1) and rejected(text))

    # Counts and nominal work, from the files and from the printed report.
    for step, (n, tr, sec) in TABLE.items():
        for s in (1, 2):
            if (step, s) not in tree:
                continue
            procs = tree[step, s]
            ms = sum(proc_ms(p) for p in procs)
            check("%s session %d: %d processes of %d trial(s), %.1f s of nominal kernel work" % (step, s, n, tr, sec),
                  len(procs) == n and all(len(p["trials"]) == tr for p in procs) and ms == round(sec * 1000),
                  (len(procs), ms))
            check("%s session %d: the report prints the process count and the nominal work" % (step, s),
                  ("\n%s %d %d %d %g\n" % (step, s, n, n * tr, sec)) in r.stdout, r.stdout[:400])
    short = copy.deepcopy(tree["XN", 1])
    short[0]["trials"].pop()
    check("nominal work: a schedule with one trial missing does not give the XN value",
          sum(proc_ms(p) for p in short) != 1382400)
    check("one process at a time is at most 33 s of kernel work (the longest: XW with a previous activity)",
          max(proc_ms(p) for procs in tree.values() for p in procs) == 33000)

    # Header pairs.
    check("plan headers: seed is one value per step and session, test=0",
          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)
              for procs in tree.values()))
    check("plan headers: the seeds of the steps and sessions differ",
          len({procs[0]["head"]["seed"] for procs in tree.values()}) == 13)
    check("plan headers: kernel and size name the target of every trial",
          all(all(t["tgt"].split("@")[0] == p["head"]["kernel"] and nbytes(t["tgt"].split("@")[1]) == int(p["head"]["size"])
                  and int(p["head"]["size"]) == p["bytes"] for t in p["trials"])
              for procs in tree.values() for p in procs))
    check("cond labels are key=value pairs that agree with the trial (kernel, size, counter mode, previous activity)",
          all(dict(x.split("=") for x in t["cond"].split("|")).get("count", "closed") == t["count"]
              and "K=%s|S=%s" % tuple(t["tgt"].split("@")) == "|".join(t["cond"].split("|")[:2])
              and dict(x.split("=") for x in t["cond"].split("|")).get("prev", "none") ==
              (t["prev"].split(":")[0] if t["prev"] != "-" else "none")
              for procs in tree.values() for p in procs for t in p["trials"]))

    # CPU order of the sessions.
    for (step, s), procs in sorted(tree.items()):
        if step == "XEV":
            continue
        check("%s session %d: CPU order %d then %d" % ((step, s) + cpus_of(s)), cpu_blocks(procs, *cpus_of(s)))
    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["XW", 1], 41, 2))
    check("session 2 is not session 1 with the CPUs exchanged (own random order)",
          [p["head"]["wcond"] for p in tree["XW", 1]] != [p["head"]["wcond"] for p in tree["XW", 2]]
          and [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree["XF", 1]] !=
          [p["tag"].replace("cpu2", "c").replace("cpu41", "c") for p in tree["XF", 2]])

    # XW.
    for s in (1, 2):
        d = xw_rules(tree["XW", s], cpus_of(s))
        check("XW session %d: 7 conditions once per replicate block and CPU, trials as specified" % s, not d, d[:3])
    check("XW rules reject the session 1 schedule under the session 2 CPU order", bool(xw_rules(tree["XW", 1], (41, 2))))
    m = copy.deepcopy(tree["XW", 1])
    m[0]["trials"][0]["nwin"] = 99
    check("XW rules reject a trial of 99 windows", bool(xw_rules(m, (2, 41))))
    m = copy.deepcopy(tree["XW", 1])
    m[0], m[7] = m[7], m[0]
    check("XW rules reject two processes exchanged between blocks", bool(xw_rules(m, (2, 41))))
    m = copy.deepcopy(tree["XW", 1])
    for p in m:
        if p["head"]["wcond"] == "W1":
            p["trials"][0]["prev"] = "-"
    check("XW rules reject W1 without its previous activity", bool(xw_rules(m, (2, 41))))
    fixed = sorted(tree["XW", 1], key=lambda p: (int(p["head"]["rep_set"]), p["cpu"], p["head"]["wcond"]))
    check("XW rules reject a fixed condition order in every block",
          xw_rules(fixed, (2, 41)) == ["the condition order is the same in every block"], xw_rules(fixed, (2, 41))[:3])

    # XCA, XCB, XCC, XEV.
    for step, evset in (("XCA", "A"), ("XCB", "B"), ("XCC", "C")):
        for s in (1, 2):
            d = xc_rules(tree[step, s], cpus_of(s), evset)
            check("%s session %d: per CPU 2 x 3 kernels at 8M (100 windows) and read at 1M, 32K, 16M (20 windows), "
                  "count read, event set %s in args" % (step, s, evset), not d, d[:3])
    check("XC rules reject the event set of another step", bool(xc_rules(tree["XCA", 1], (2, 41), "B")))
    m = copy.deepcopy(tree["XCA", 1])
    m[0]["trials"][0]["count"] = "closed"
    check("XC rules reject a trial with count closed", bool(xc_rules(m, (2, 41), "A")))
    check("the event sets: 6 events each, names below 32 characters, 18 different names and codes",
          all(len(v.split(",")) == 6 and all(re.match(r"^[a-z0-9_]{1,31}=0x[0-9a-f]+$", e) for e in v.split(","))
              for v in EVENTS.values())
          and len({e.split("=")[0] for v in EVENTS.values() for e in v.split(",")}) == 18
          and len({int(e.split("=")[1], 16) for v in EVENTS.values() for e in v.split(",")}) == 18)
    ev = tree["XEV", 1]
    check("XEV: CPU 2 only, one process per event set, one trial read@8M, 3 windows of 300 ms, count read",
          [p["cpu"] for p in ev] == [2, 2, 2] and [p["head"]["evset"] for p in ev] == ["A", "B", "C"]
          and all(p["extra"] == " --pmu-type 11 --events " + EVENTS[p["head"]["evset"]] and p["bytes"] == 8 << 20
                  and p["trials"] == [{"cond": "K=read|S=8M|count=read", "rep": 1, "prev": "-", "pfx": "-", "pred": "-",
                                       "tgt": "read@8M", "nwin": 3, "win_ms": 300, "count": "read", "bins": 0, "ms": 900}]
                  for p in ev))
    check("XEV: session 2 has no schedule, no plan folder and no marker",
          not [f for f in os.listdir(os.path.join(a, "s2")) if f.startswith("XEV")])

    # XN.
    for s in (1, 2):
        d = xn_rules(tree["XN", s], cpus_of(s))
        check("XN session %d: S2-style trials, header keys as S2, 6 different kernel orders per size and CPU, "
              "each kernel once or twice at each position, block order as S2" % s, not d, d[:3])
    m = copy.deepcopy(tree["XN", 1])
    for i in range(0, 144, 4):                       # every set in the order of XN_KERNELS
        for p, k in zip(m[i:i + 4], XN_KERNELS):
            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]
            p["head"]["kernel"] = k
            for t in p["trials"]:
                t.update(cond="K=%s|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))
    d = xn_rules(m, (2, 41))
    check("XN rules reject a schedule in which every set has one fixed kernel order",
          any("occurs twice" in x for x in d) and any("once or twice" in x for x in d), d[:3])
    m = copy.deepcopy(tree["XN", 1])
    m[3], m[4] = m[4], m[3]
    check("XN rules reject CPUs that alternate inside a size", bool(xn_rules(m, (2, 41))))
    m = copy.deepcopy(tree["XN", 1])
    m[5]["trials"][0]["pfx"] = "asmread@1M:1200" if m[5]["head"]["kernel"] != "asmread" else "read_nop16@1M:1200"
    check("XN rules reject a prefix of another kernel or size", bool(xn_rules(m, (2, 41))))
    check("XN rules reject the session 1 schedule under the session 2 CPU order", bool(xn_rules(tree["XN", 1], (41, 2))))

    # XF.
    for s in (1, 2):
        d = xf_rules(tree["XF", s], cpus_of(s))
        check("XF session %d: 15 kernel and size cells once per replicate block and CPU, S2-style trials, "
              "the order differs between blocks" % s, not d, d[:3])
    m = copy.deepcopy(tree["XF", 1])
    m[0], m[15] = m[15], m[0]
    check("XF rules reject two processes exchanged between blocks", bool(xf_rules(m, (2, 41))))
    check("XF: the sizes in bytes are the listed ones (1.5, 2, 2.5, 3, 5, 6, 12, 24, 32, 64 MiB for read)",
          sorted({p["bytes"] for p in tree["XF", 1] if p["head"]["kernel"] == "read"}) ==
          [int(x * 1048576) for x in (1.5, 2, 2.5, 3, 5, 6, 12, 24, 32, 64)]
          and sorted({p["bytes"] for p in tree["XF", 1] if p["head"]["kernel"] == "oldread"}) ==
          [x << 20 for x in (2, 3, 6, 12, 32)])

    # Marker files of the host sampler.
    for s in (1, 2):
        sdir = os.path.join(a, "s%d" % s)
        marks = sorted(f[:-6] for f in os.listdir(sdir) if f.endswith(".watch"))
        check("session %d: empty .watch markers for XW, XCA, XCB, XCC and for no other step" % s,
              marks == WATCH_STEPS and all(os.path.getsize(os.path.join(sdir, m + ".watch")) == 0 for m in marks), marks)

    # Determinism.
    gen(b)
    r3 = gen(c, "--seed", "7")
    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)
    nfiles = 1 + sum(TABLE[s][0] + 1 for s in TABLE) + sum(TABLE[s][0] + 1 for s in TABLE if s != "XEV") + 8
    check("two runs with one base seed give the same bytes (%d files)" % nfiles, ta == tb and len(ta) == nfiles, len(ta))
    check("another base seed gives the same file names and other bytes",
          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc
          and all(ta["s1/%s.tsv" % s] != tc["s1/%s.tsv" % s] for s in ("XW", "XCA", "XN", "XF")))
    check("the base seed and the seed of every step and session are saved in MANIFEST.txt",
          b"base_seed=20261115\ntest_divisor=1\n" in ta["MANIFEST.txt"] and b"base_seed=7\n" in tc["MANIFEST.txt"]
          and all(("seed %s s%d %s\n" % (st, s, procs[0]["head"]["seed"])).encode() in ta["MANIFEST.txt"]
                  for (st, s), procs in tree.items()))
    tree7, errors7 = load(c)
    check("another base seed keeps the rules (grammar, XW, XN, XF, XCB)",
          not errors7 and not xw_rules(tree7["XW", 2], (41, 2)) and not xn_rules(tree7["XN", 1], (2, 41))
          and not xf_rules(tree7["XF", 2], (41, 2)) and not xc_rules(tree7["XCB", 1], (2, 41), "B"))
    saved = os.path.join(X, "sched9")
    check("the saved sched9/ beside the scripts is the output of the default base seed",
          os.path.isdir(saved) and tree_bytes(saved) == ta)

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
          and not xw_rules(ttree["XW", 1], (2, 41), 3, 30), terr[:3])
    check("--test-divisor 7 is refused (it does not divide 300 ms)",
          gen(os.path.join(tmp, "u"), "--test-divisor", "7").returncode != 0)
    return t


# ---------- every plan through the local stand-in bwx8 ----------
def bwx8_checks(tmp, sched):
    allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)
    d = os.path.join(tmp, "bwx8")
    os.makedirs(d)
    binary = os.path.join(d, "bwx8")
    r = subprocess.run(["gcc"] + CFLAGS + ["-o", binary, os.path.join(X, "bwx8.c")], capture_output=True, text=True)
    if not check("stand-in build of bwx8.c in a temporary folder (flags of build8.sh)", r.returncode == 0, r.stdout + r.stderr):
        return
    if not check("this machine allows CPU 0, CPU 2 and one more CPU below 120", 0 in allowed and 2 in allowed and len(allowed) > 2):
        return
    alt = 41 if 41 in allowed else [c for c in allowed if c not in (0, 2)][0]
    shutil.copytree(sched, os.path.join(d, "sched9"))
    jobs = []
    for session in (1, 2):
        sdir = os.path.join(d, "sched9", "s%d" % session)
        for name in sorted(f for f in os.listdir(sdir) if f.endswith(".tsv")):
            step = name[:-4]
            for row in open(os.path.join(sdir, name)).read().split("\n")[1:-1]:
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
                             sum((1 if t[3] != "-" else 0) + (4 if t[4] != "-" else 0) for t in trials)))
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}

    def one(job):
        step, session, idx, args, ntr, nwin, nother = job
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
            and m.get("mode") == "trial"
        if ok and "--events" in args:
            ok = m.get("pmu_type") == "11" and m.get("events", "").count(";") == 5 and rows["C"] + rows["X"] >= 1
        return None if ok else (step, session, idx, r.returncode, r.stderr[-200:], dict(rows))

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, jobs))
    per = collections.defaultdict(list)
    for job, res in zip(jobs, results):
        per[job[0], job[1]].append(res)
    for (step, session), res in sorted(per.items(), key=lambda x: (x[0][1], x[0][0])):
        bad = [x for x in res if x]
        check("%s session %d: bwx8 accepts each of the %d plans with its args: status 0, one S and one E row per trial, "
              "every planned window as a W row" % (step, session, len(res)),
              len(res) == TABLE[step][0] and not bad, bad[:2])
    check("all %d plans of both sessions ran through bwx8 (%.0f s)" % (len(jobs), time.time() - t0),
          len(jobs) == sum(v[0] for v in TABLE.values()) * 2 - 3 and all(x is None for x in results))
    # The acceptance means something only if bwx8 refuses a defective plan and missing counter settings.
    plan = os.path.join(d, "sched9", "s1", "XN", "0000.plan")
    text = open(plan).read()
    args = ["--trial", "--cpus", "2", "--bytes", re.search(r" bytes=(\d+) ", text).group(1), "--plan"]
    for name, bad in (("an unknown kernel", text.replace("@", "x@")),
                      ("a size above --bytes", re.sub(r"@(32K|1M|8M)", "@64M", text)),
                      ("a prefix that is not a multiple of 4 ms", re.sub(r":12 ", ":13 ", text))):
        p = os.path.join(d, "bad.plan")
        with open(p, "w") as f:
            f.write(bad)
        r = subprocess.run([binary] + args + [p], env=env, capture_output=True, text=True)
        check("bwx8 refuses a plan with %s (status 2)" % name, bad != text and r.returncode == 2, (r.returncode, r.stderr))
    ev = os.path.join(d, "sched9", "s1", "XEV", "0000.plan")
    r = subprocess.run([binary, "--trial", "--cpus", "2", "--bytes", "8388608", "--plan", ev], env=env, capture_output=True, text=True)
    check("bwx8 refuses the XEV plan when the event options are left out of the args (status 2)",
          r.returncode == 2 and "--events" in r.stderr, (r.returncode, r.stderr))


# ---------- hostwatch.py ----------
CHILD = """
import os, sys, threading, time
os.sched_setaffinity(0, {%d})
def spin():
    end = time.time() + %g
    while time.time() < end:
        pass
t = threading.Thread(target=spin)
t.start()
t.join()
"""


def read_watch(path):
    """(header and footer lines, sample lines as (t, is absolute, dict))."""
    head, samples = [], []
    for l in open(path).read().split("\n"):
        if l.startswith("#"):
            head.append(l)
        elif l:
            f = l.split(" ")
            absolute = f[1] == "ABS"
            d = collections.OrderedDict()
            for item in f[2 if absolute else 1:]:
                k, _, v = item.partition("=")
                d[k] = v
            samples.append((int(f[0]), absolute, d))
    return head, samples


def delta_sum(samples, key):
    return sum(int(d[key]) for _, absolute, d in samples if not absolute and key in d)


def hostwatch_checks(tmp):
    allowed = sorted(os.sched_getaffinity(0))
    if not check("hostwatch: this machine allows 3 or more CPUs", len(allowed) >= 3):
        return
    c_work, c_watch = allowed[-1], allowed[-2]
    d = os.path.join(tmp, "hw")
    os.makedirs(d)
    out = os.path.join(d, "busy.txt")
    # A second process on the same CPU: a thread of another process that the sampler must find and follow.
    other = subprocess.Popen([sys.executable, "-c", CHILD % (c_work, 60)])
    time.sleep(0.5)
    child = subprocess.Popen([sys.executable, "-c", CHILD % (c_work, 3.0)])
    time.sleep(0.3)                                  # the worker thread exists and is on its CPU
    start_ticks = open("/proc/%d/stat" % child.pid).read().rsplit(")", 1)[1].split()[19]
    t0 = time.time()
    r = subprocess.run(["taskset", "-c", str(c_watch), sys.executable, WATCH, "--pid", str(child.pid), "--cpu", str(c_work),
                        "--out", out], capture_output=True, text=True, timeout=60)
    took = time.time() - t0
    child.wait()
    head, samples = read_watch(out)
    text = "\n".join(head)
    check("hostwatch on a busy child: status 0, no message, ends by itself when the child is gone",
          r.returncode == 0 and r.stdout == "" and r.stderr == "" and took < 6 and
          re.search(r"^# end reason=pid_gone samples=\d+ missed=\d+ max_sample_us=\d+ errors=0$", text, re.M) is not None,
          (r.returncode, r.stderr, took, head[-1:]))
    m = re.search(r"^# clocks mono_ns=(\d+) boot_ns=(\d+) real_ns=(\d+)$", text, re.M)
    check("hostwatch header: version line with pid and cpu; CLOCK_MONOTONIC, CLOCK_BOOTTIME and CLOCK_REALTIME in ns",
          head[0] == "# hostwatch v1 pid=%d cpu=%d hz=20 max_s=120" % (child.pid, c_work) and m is not None
          and abs(int(m.group(3)) / 1e9 - t0) < 5 and int(m.group(2)) >= int(m.group(1)) > 0, head[:3])
    check("hostwatch header: the start time of the process (field 22 of its stat file) with the clock tick rate",
          ("# target starttime_ticks=%s clk_tck=%d comm=" % (start_ticks, os.sysconf("SC_CLK_TCK"))) in text, head[:4])
    check("hostwatch header: the thread of the other process on the watched CPU is listed with its comm, then the scan line",
          re.search(r"^# th tid=\d+ pid=%d comm=\S+$" % other.pid, text, re.M) is not None
          and re.search(r"^# scan threads=\d+ on_cpu=\d+ took_ms=[\d.]+$", text, re.M) is not None, head[:8])
    first = samples[0] if samples else (0, False, {})
    keys = ["m.run_ns", "m.nvcsw", "m.nivcsw", "m.minflt", "m.majflt", "m.utime", "m.stime", "m.cpu", "m.slices",
            "w.run_ns", "w.wait_ns", "w.slices", "w.nvcsw", "w.nivcsw", "w.minflt", "w.majflt", "w.utime", "w.stime"]
    check("hostwatch: the first sample line holds the absolute values of the main thread (m.) and the worker thread (w.)",
          first[1] and all(k in first[2] for k in keys) and first[2].get("w.cpu") == str(c_work),
          [k for k in keys if k not in first[2]])
    check("hostwatch: the absolute line holds the cpuN line of /proc/schedstat, column N of /proc/softirqs, "
          "/proc/vmstat and /proc/interrupts",
          first[1] and all(k in first[2] for k in ("cpu.pcount", "cpu.run_ns", "sirq.TIMER", "sirq.SCHED", "sirq.RCU"))
          and sum(k.startswith("vm.") for k in first[2]) > 20 and any(k.startswith("irq.") for k in first[2]),
          [k for k in first[2] if not k.startswith(("vm.", "th."))][:40])
    # Why: the kernel gives /proc/vmstat in pieces of about one memory page. A reader that stops after a
    # short first piece loses the last keys (found in review: 175 of 178 keys on this machine).
    vm_keys = {l.split()[0] for l in open("/proc/vmstat").read().split("\n") if len(l.split()) == 2 and l.split()[1].isdigit()}
    got_keys = {k[3:] for k in first[2] if k.startswith("vm.")}
    check("hostwatch: the absolute line holds every key of /proc/vmstat (the file is read to its end, not only its first piece)",
          len(vm_keys) > 20 and got_keys == vm_keys, (len(vm_keys), len(got_keys), sorted(vm_keys ^ got_keys)[:8]))
    for path, single in (("/proc/vmstat", False), ("/proc/softirqs", False), ("/proc/schedstat", False),
                         ("/proc/interrupts", False), ("/proc/self/status", True)):
        try:
            want_lines = open(path, "rb").read().count(b"\n")
        except OSError:
            want_lines = None
        r = subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, %r); import hostwatch as h; "
                            "d = h.Src(%r, %r).read(); print(-1 if d is None else d.count(b'\\n'))" % (X, path, single)],
                           capture_output=True, text=True)
        check("hostwatch reader: %s is read whole (%s lines)" % (path, want_lines),
              r.returncode == 0 and (want_lines is None or abs(int(r.stdout) - want_lines) <= 2) and (want_lines is None or want_lines < 3 or int(r.stdout) >= 3),
              (r.returncode, r.stdout, r.stderr[-200:]))
    # Why: an error inside a sample must not end the sampling, and must not be recorded as "the process is gone".
    sl = subprocess.Popen(["sleep", "30"])
    for name, patch, want_rc, want in (
            ("sample", "h.Watch.vm = lambda self, cur: int('x')", 0, r"^# end reason=max_s samples=\d+ missed=\d+ max_sample_us=\d+ errors=[1-9]\d*$"),
            ("first scan", "h.Watch.scanner = lambda self, first: int('x')", 1, r"^# end reason=error samples=0 missed=0 max_sample_us=0 errors=0$")):
        oute = os.path.join(d, "err-%s.txt" % name.replace(" ", ""))
        r = subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, %r); import hostwatch as h; %s; "
                            "sys.argv = ['hostwatch.py', '--pid', '%d', '--cpu', '%d', '--out', %r, '--max-s', '0.5']; sys.exit(h.main())"
                            % (X, patch, sl.pid, c_work, oute)], capture_output=True, text=True, timeout=60)
        texte = open(oute).read() if os.path.exists(oute) else ""
        check("hostwatch with an error in the %s: status %d, the footer names it (not pid_gone)%s" % (
              name, want_rc, ", every sample line is 'hw.error:=ValueError', the sampling goes on to --max-s" if want_rc == 0 else ", the message is on stderr"),
              r.returncode == want_rc and re.search(want, texte, re.M) is not None
              and ((want_rc == 0 and texte.count(" hw.error:=ValueError\n") >= 5 and r.stderr == "") or (want_rc == 1 and "ValueError" in r.stderr)),
              (r.returncode, r.stderr[-200:], texte[-300:]))
    sl.kill()
    sl.wait()
    deltas = [s for s in samples if not s[1]]
    gaps = [b[0] - a[0] for a, b in zip(deltas, deltas[1:])]
    check("hostwatch: delta lines at 20 Hz (median gap 45 to 55 ms), times rising, 30 or more lines in 2.7 s",
          len(deltas) >= 30 and all(g > 0 for g in gaps) and 45e6 <= statistics.median(gaps) <= 55e6,
          (len(deltas), sorted(gaps)[:3], gaps and statistics.median(gaps)))
    span = (samples[-1][0] - samples[0][0]) / 1e9 if samples else 0
    run = delta_sum(samples, "w.run_ns") / 1e9
    check("hostwatch: the worker thread shares its CPU with the other process: w.run_ns is 25 to 75 % of the time, "
          "w.nivcsw and w.slices rise",
          span > 2 and 0.25 * span <= run <= 0.75 * span and delta_sum(samples, "w.nivcsw") > 5
          and delta_sum(samples, "w.slices") > 5, (span, run, delta_sum(samples, "w.nivcsw")))
    thkeys = {k for _, absolute, dd in samples if not absolute for k in dd if k.startswith("th.%d." % (other.pid + 0))}
    th_any = {k for _, absolute, dd in samples if not absolute for k in dd if k.startswith("th.") and k.endswith(".run_ns")}
    th_run = max([delta_sum(samples, k) for k in th_any] or [0]) / 1e9
    check("hostwatch: a thread of the other process on the CPU is followed (th.<tid>.<comm>.run_ns is 25 to 75 % of the time)",
          0.25 * span <= th_run <= 0.75 * span, (span, th_run, sorted(thkeys)[:5]))
    check("hostwatch: the CPU counters move (cpu.pcount, cpu.run_ns, sirq.TIMER) and vmstat keys are reported as vm.<key>",
          delta_sum(samples, "cpu.pcount") > 5 and delta_sum(samples, "cpu.run_ns") > 5e8
          and delta_sum(samples, "sirq.TIMER") > 5
          and any(k.startswith("vm.") for _, absolute, dd in samples if not absolute for k in dd))
    check("hostwatch: every item of a delta line is key=number or key:=state",
          all(re.match(r"^-?\d+$", v) or v.startswith("=") for _, absolute, dd in samples if not absolute for v in dd.values())
          and all(dd for _, _, dd in samples))

    # --max-s, SIGTERM, a process that does not exist, a CPU that does not exist.
    out2 = os.path.join(d, "max.txt")
    t0 = time.time()
    r = subprocess.run([sys.executable, WATCH, "--pid", str(other.pid), "--cpu", str(c_work), "--out", out2, "--max-s", "1",
                        "--hz", "50"], capture_output=True, text=True, timeout=60)
    head2, samples2 = read_watch(out2)
    check("hostwatch --max-s 1 --hz 50 on a process that keeps running: status 0 after about 1 s, reason=max_s, 35 or more samples",
          r.returncode == 0 and 0.9 < time.time() - t0 < 4 and "reason=max_s" in head2[-1]
          and int(re.search(r"samples=(\d+)", head2[-1]).group(1)) >= 35 and "hz=50 max_s=1" in head2[0],
          (r.returncode, time.time() - t0, head2[-1:]))
    check("hostwatch: an absolute line is the first line only (the next one is due after 5 s)",
          [s[1] for s in samples2].count(True) == 1 and samples2[0][1])
    out3 = os.path.join(d, "term.txt")
    p = subprocess.Popen([sys.executable, WATCH, "--pid", str(other.pid), "--cpu", str(c_work), "--out", out3])
    end = time.time() + 20
    while time.time() < end and not (os.path.exists(out3) and "# scan" in open(out3).read()):
        time.sleep(0.05)
    time.sleep(5.3)
    p.send_signal(signal.SIGTERM)
    rc = p.wait(timeout=20)
    head3, samples3 = read_watch(out3)
    check("hostwatch: SIGTERM ends it with status 0 and the footer reason=signal",
          rc == 0 and head3 and "reason=signal" in head3[-1], (rc, head3[-1:]))
    check("hostwatch: after 5 s a second absolute line follows",
          [s[1] for s in samples3].count(True) == 2, [s[1] for s in samples3].count(True))
    other.kill()
    other.wait()
    out4 = os.path.join(d, "gone.txt")
    r = subprocess.run([sys.executable, WATCH, "--pid", str(other.pid), "--cpu", str(c_work), "--out", out4],
                       capture_output=True, text=True, timeout=60)
    head4, _ = read_watch(out4)
    check("hostwatch on a process that is gone: status 0, start time 'na', reason=pid_gone, no error text",
          r.returncode == 0 and r.stderr == "" and "starttime_ticks=na " in "\n".join(head4)
          and "reason=pid_gone" in head4[-1], (r.returncode, r.stderr, head4))
    sleeper = subprocess.Popen(["sleep", "30"])
    out5 = os.path.join(d, "nocpu.txt")
    r = subprocess.run([sys.executable, WATCH, "--pid", str(sleeper.pid), "--cpu", "9999", "--out", out5, "--max-s", "0.5"],
                       capture_output=True, text=True, timeout=60)
    sleeper.kill()
    sleeper.wait()
    head5, samples5 = read_watch(out5)
    check("hostwatch with a CPU that the host does not have: no crash, the missing values are 'na'",
          r.returncode == 0 and r.stderr == "" and samples5 and samples5[0][2].get("cpu.pcount") == "na"
          and samples5[0][2].get("sirq.TIMER") == "na" and "m.run_ns" in samples5[0][2], (r.returncode, r.stderr))
    r = subprocess.run([sys.executable, WATCH, "--pid", "1", "--out", os.path.join(d, "x.txt")], capture_output=True, text=True)
    check("hostwatch without --cpu: status 2, no output file", r.returncode == 2 and not os.path.exists(os.path.join(d, "x.txt")))
    src = open(WATCH).read()
    check("hostwatch source: opens only files under /proc and the output file, and starts no process",
          not re.search(r"\b(subprocess|os\.system|os\.popen|os\.kill|sched_setaffinity|os\.fork|os\.exec)", src)
          and re.findall(r"os\.open\(([^,]+),", src) == ["self.path", "path"]
          and re.findall(r"\bopen\(([^,)]+)", src.replace("os.open(", "")) == ["a.out"]
          and all(x.startswith("/proc") for x in re.findall(r"\"(/[a-z][^\"]*)\"", src)), re.findall(r"\"(/[a-z][^\"]*)\"", src))


# ---------- run_bwx9.sh with a dummy bwx8 ----------
DUMMY = """#!/usr/bin/env bash
# Stand-in for bwx8: records its process ids, checks the plan file, sleeps, ends with DUMMY_EXIT.
echo "$$ $*" >> "$DUMMY_LOG"
grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"
echo "PMU=${BWX_PMU_TYPE:-} EV=${BWX_EVENTS:-}" >> "$DUMMY_LOG.env"
while (( $# )); do if [[ $1 == --plan && ! -r $2 ]]; then echo "no plan $2" >&2; exit 7; fi; shift; done
echo "M,dummy,1"
sleep "${DUMMY_SLEEP:-0}" & echo "$! sleep" >> "$DUMMY_LOG"
wait $!
# DUMMY_TOUCH=1: the marker file appears when this process ends.
[[ -z ${DUMMY_TOUCH:-} ]] || : > "$BWX8_MARKER"
exit "${DUMMY_EXIT:-0}"
"""

PS_STUB = """#!/usr/bin/env bash
# Stand-in for ps: its second call creates the file named by PS_TOUCH. Then it runs the real ps.
# run_bwx9.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.
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
# Every program that run_bwx9.sh and the dummy start, except python3.
TOOLS = ["env", "bash", "taskset", "date", "sleep", "cut", "who", "wc", "ps", "head", "setsid", "dirname", "awk",
         "sha256sum", "sort", "tr", "mkdir", "cp", "hostname", "cat", "grep"]


def cpu_list(text):
    cpus = set()
    for part in text.split(":")[1].strip().split(","):
        a, _, b = part.partition("-")
        cpus.update(range(int(a), int(b or a) + 1))
    return cpus


def utc(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


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


class Box:
    """A copy of run_bwx9.sh and hostwatch.py with a test schedule and the dummy binary in a temporary folder."""

    def __init__(self, tmp, sched):
        self.dir = os.path.join(tmp, "box")
        os.makedirs(self.dir)
        shutil.copy(RUN, self.dir)
        shutil.copy(WATCH, self.dir)
        shutil.copytree(sched, os.path.join(self.dir, "sched9"))
        self.bin = os.path.join(self.dir, "bwx8")
        with open(self.bin, "w") as f:
            f.write(DUMMY)
        os.chmod(self.bin, 0o755)
        with open(os.path.join(self.dir, "build.txt"), "w") as f:
            f.write("dummy build record\n")
        os.makedirs(os.path.join(self.dir, "bin"))
        stub = os.path.join(self.dir, "bin", "ps")
        with open(stub, "w") as f:
            f.write(PS_STUB % shutil.which("ps"))
        os.chmod(stub, 0o755)
        os.makedirs(os.path.join(self.dir, "nopy"))
        for t in TOOLS:
            os.symlink(shutil.which(t), os.path.join(self.dir, "nopy", t))
        allowed = sorted(os.sched_getaffinity(0))
        self.watch_cpu = str(allowed[-1])
        self.n = 0

    def rows(self, step, session=1):
        text = open(os.path.join(self.dir, "sched9", "s%d" % session, step + ".tsv")).read()
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
             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED", "BWX8_SHA256",
                          "BWX_PMU_TYPE", "BWX_EVENTS", "WATCH_CPU")}
        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin,
                 BWX8_RESULTS=self.results, DUMMY_LOG=self.log, WATCH_CPU=self.watch_cpu)
        e.update(env)
        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out
        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx9.sh")] + args, env=e, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)

    def run(self, args, pre=(), **env):
        p = self.start(args, pre, **env)
        out, err = p.communicate(timeout=600)
        return p.returncode, out, err

    def folder(self):
        d = os.listdir(self.results) if os.path.isdir(self.results) else []
        return os.path.join(self.results, d[0]) if len(d) == 1 else None

    def file(self, name):
        f = self.folder()
        path = os.path.join(f, name) if f else ""
        return open(path).read() if os.path.exists(path) else ""

    def csv(self, step):
        return self.file(step + ".csv")

    def launched(self):
        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []

    def wait_launch(self, watch=None):
        """Waits for the dummy and its sleep. watch: also for the scan line of this sampler file."""
        end = time.time() + 90
        while time.time() < end and (len(self.launched()) < 2 or (watch and "# scan" not in self.file(watch))):
            time.sleep(0.2)
        return len(self.launched()) >= 2 and (not watch or "# scan" in self.file(watch))

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
    """visit9.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""
    d = os.path.join(tmp, "visit")
    os.makedirs(os.path.join(d, "bin"))
    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())
    copy_path = os.path.join(d, "visit9.sh")
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
        r = subprocess.run([shutil.which("bash"), copy_path, name, "XEV", "XW"], env=e, capture_output=True, text=True)
        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr

    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",
                         BWX8_SHA256="0a1b", ENVV="WATCH_CPU=100")
    check("visit9.sh: one login; the marker check is the first remote action, then run_bwx9.sh in ~/cache-perf/bwx8-20261114",
          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1
          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")
          and cmd.endswith("exit 3; fi; cd ~/cache-perf/bwx8-20261114 && STOP_AT=2026-11-15T15:00Z SESSION=2 "
                           "SESSION1_END=2026-11-15T03:00Z BWX8_SHA256=0a1b WATCH_CPU=100 ./run_bwx9.sh XEV XW\n")
          and open(os.path.join(d, "ok.log")).read().startswith("ssh status 0 utc "), (rc, cmd, err))
    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b"}
    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),
                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b|x")):
        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))
        check("visit9.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),
              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")), (rc, cmd, err))
    rc, cmd, err = visit("nostop", SESSION="1")
    check("visit9.sh: STOP_AT not set: no login", rc != 0 and cmd is None, (rc, cmd, err))
    a, b = open(os.path.join(X, "visit8.sh")).read().split("\n"), open(VISIT).read().split("\n")
    check("visit9.sh differs from visit8.sh only in comment lines and in the name of the script that it starts",
          [l for l in a if not l.startswith("#")] == [l.replace("./run_bwx9.sh", "./run_bwx8.sh") for l in b if not l.startswith("#")])


def run_checks(tmp, sched):
    for f in ("run_bwx9.sh", "visit9.sh"):
        r = subprocess.run(["bash", "-n", os.path.join(X, f)], capture_output=True, text=True)
        check("bash -n " + f, r.returncode == 0, r.stderr)
    # The stop controls are the text of run_bwx8.sh: every line of these functions is in both files.
    old, new = open(os.path.join(X, "run_bwx8.sh")).read(), open(RUN).read()
    kept = [l for l in old.split("\n") if re.match(r"^(why_stop|check_marker|check_deadline|trap|settle)\b|^  (if \[\[ -e \$(MARKER|STOPFILE)|if \(\( STOP_EPOCH)", l)]
    check("run_bwx9.sh keeps the lines of why_stop, check_marker, check_deadline, settle and the trap of run_bwx8.sh unchanged",
          len(kept) == 8 and all(new.count(l) == 1 for l in kept), [l[:60] for l in kept if new.count(l) != 1])
    check("run_bwx9.sh: stop_child is the line of run_bwx8.sh with the stop of the sampler added at its end",
          re.search(r"(?m)^stop_child\(\) .*$", old).group(0)[:-2] + " stop_watch; }" == re.search(r"(?m)^stop_child\(\) .*$", new).group(0))
    box = Box(tmp, sched)

    # ---- steps and the dry run ----
    for name in ("S2", "C4", "Xw", "X", "X-1", "XW;id"):
        rc, out, err = box.run(["--dry-run", name], SESSION="1")
        check("step name '%s' is refused with status 2" % name, rc == 2 and "unknown step" in err and not out, (rc, err))
    rc, out, err = box.run(["--dry-run", "XZ9"], SESSION="1")
    check("a name of the right form without a schedule: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))
    rc, out, err = box.run(["--dry-run", "XN", "XN"], SESSION="1")
    check("a step named twice: status 2", rc == 2 and "twice" in err and "step XN" not in out, (rc, err))
    rc, out, err = box.run(["--dry-run", "XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF"], SESSION="1")
    want = {"XEV": "3 processes, nominal kernel work 0.027 s", "XW": "28 processes, nominal kernel work 8.640 s",
            "XCA": "18 processes, nominal kernel work 3.960 s", "XCB": "18 processes, nominal kernel work 3.960 s",
            "XCC": "18 processes, nominal kernel work 3.960 s", "XN": "144 processes, nominal kernel work 13.824 s",
            "XF": "90 processes, nominal kernel work 8.640 s"}
    check("--dry-run of all 7 steps, session 1, without counter settings in the environment: status 0, the counts of each step",
          rc == 0 and all(("step %s session 1: %s" % kv) in out for kv in want.items())
          and out.count("\nbwx8 --trial ") == 319 and "warning" in err, (rc, out[:300], err[-300:]))
    check("--dry-run: the command lines are the args column, with the event options of the counter steps",
          all(("bwx8 %s  # idx %s, tag %s, nominal " % (r[5], r[0], r[1])) in out
              for st in want for r in box.rows(st)) and out.count(" --pmu-type 11 --events ") == 57)
    check("--dry-run: the host sampler is announced for XW, XCA, XCB, XCC and for no other step",
          sorted(re.findall(r"^step (\S+) host sampler: hostwatch.py on CPU %s " % box.watch_cpu, out, re.M)) == WATCH_STEPS, out[:500])
    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))
    rc, out, err = box.run(["--dry-run", "XW", "XN", "XF"], SESSION="2")
    check("--dry-run session 2: the first command line of each step uses CPU 41",
          rc == 0 and len(re.findall(r"# ---- step \S+ session 2 ----\n.*\n.*\n(?:step \S+ host sampler.*\n)?bwx8 --trial --cpus 41 ", out)) == 3, (rc, out[:500]))
    rc, out, err = box.run(["--dry-run", "XEV"], SESSION="2")
    check("XEV in session 2: status 2, 'missing schedule'", rc == 2 and "missing schedule" in err, (rc, err))
    rc, out, err = box.run(["--dry-run", "XN"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None, BWX8_BIN=None, BWX8_RESULTS=None)
    check("no warning without the test settings", rc == 0 and "warning" not in err, err)

    # ---- a normal run without sampler: XEV ----
    rows = box.rows("XEV")
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none")
    f = box.folder()
    csv = box.csv("XEV")
    heads = re.findall(r"^-- step XEV session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)
    check("XEV normal end: status 0, the counts are printed before the result folder is made",
          rc == 0 and 0 <= out.find("step XEV session 1: 3 processes") < out.find("result folder: "), (rc, err, out))
    check("XEV normal end: folder name bwx9-XEV-s1-<UTC> and its six files, no sampler file",
          f is not None and re.match(r"^bwx9-XEV-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None
          and sorted(os.listdir(f)) == ["XEV.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],
          f and os.listdir(f))
    check("XEV normal end: one header line per process in schedule order, each followed by its output; schedule.tsv is a copy",
          heads == [(r[0], r[1], r[5]) for r in rows] and csv.count("M,dummy,1\n") == 3 and "-- killed" not in csv
          and "-- failed" not in csv and box.file("schedule.tsv") == open(os.path.join(box.dir, "sched9", "s1", "XEV.tsv")).read(), heads)
    launched = [l for l in box.launched() if not l.endswith(" sleep")]
    check("XEV normal end: the binary gets the args column, with --pmu-type 11 and the event set, and no counter setting in its environment",
          [l.split(" ", 1)[1] for l in launched] == [r[5] for r in rows] and all(" --events " + EVENTS[e] in l for l, e in zip(launched, "ABC"))
          and open(box.log + ".env").read() == "PMU= EV=\n" * 3 and box.none_alive(), launched)
    env = box.file("env.txt")
    check("XEV normal end: env.txt holds session, from, load, digests of bwx8, run_bwx9.sh, schedule and build record, paths, end line",
          "session=1 from=0 " in env and "loadavg=" in env and "## end utc=" in env and "/run_bwx9.sh\n" in env
          and "/sched9/s1/XEV.tsv\n" in env and "host sampler" not in env
          and (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin, box.results)) in env
          and box.file("launches.txt").count("== XEV.csv idx ") == 3, env)

    # ---- the rule for the counter settings ----
    tsv = os.path.join(box.dir, "sched9", "s1", "XEV.tsv")
    saved = open(tsv).read()
    with open(tsv, "w") as fh:
        fh.write(re.sub(r" --pmu-type 11 --events \S+", "", saved))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none")
    check("a counted step without the options in args and without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",
          rc == 2 and "needs BWX_PMU_TYPE" in err and not box.launched() and open(tsv).read() != saved, (rc, err))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11")
    check("the same with BWX_PMU_TYPE only: status 2, nothing starts", rc == 2 and "needs BWX_EVENTS" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="11", BWX_EVENTS="a=0x11")
    check("the same with both settings: runs, and the binary finds them in its environment",
          rc == 0 and len(box.launched()) == 2 and open(box.log + ".env").read() == "PMU=11 EV=a=0x11\n", (rc, err))
    rc, out, err = box.run(["--dry-run", "XEV"], SESSION="1", BWX_PMU_TYPE="eleven", BWX_EVENTS="a=0x11")
    check("BWX_PMU_TYPE that is not a whole number: status 2", rc == 2 and "whole number" in err, (rc, err))
    with open(tsv, "w") as fh:
        fh.write(saved)
    rc, out, err = box.run(["--from", "143", "XN"], SESSION="1", STOP_AT="none")
    check("an uncounted step (XN, count closed, no options in args) needs no counter setting: runs",
          rc == 0 and len(box.launched()) == 2 and "--plan sched9/s1/XN/0143.plan" in box.launched()[0]
          and re.findall(r"^-- step XN session 1 idx (\d+) ", box.csv("XN"), re.M) == ["143"]
          and " from=143 " in box.file("env.txt") and "to run from idx 143: 1 processes" in out, (rc, err))

    # ---- the host sampler ----
    row = box.rows("XW")[27]
    rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="2")
    f = box.folder()
    w = box.file("watch-27.txt")
    pid = box.launched()[0].split()[0] if box.launched() else "?"
    check("XW with the sampler: status 0, watch-27.txt and watch-stderr.txt beside the six files, nothing in watch-stderr.txt",
          rc == 0 and f is not None and sorted(os.listdir(f)) == ["XW.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv",
                                                                   "stderr.txt", "watch-27.txt", "watch-selftest.txt", "watch-stderr.txt"]
          and box.file("watch-stderr.txt") == "" and box.file("stderr.txt") == "", (rc, err, f and os.listdir(f), box.file("watch-stderr.txt")))
    check("XW with the sampler: it watched the benchmark process and the CPU of the schedule row, for at most nominal time + 30 s",
          w.startswith("# hostwatch v1 pid=%s cpu=%s hz=20 max_s=31\n" % (pid, row[2])), w[:200])
    m = re.search(r"\n# end reason=(\w+) samples=(\d+) ", w)
    check("XW with the sampler: it sampled while the benchmark ran (20 or more samples in 2 s) and ended with the benchmark",
          m is not None and m.group(1) in ("pid_gone", "signal") and int(m.group(2)) >= 20 and w.endswith("\n")
          and box.none_alive(), (m and m.groups(), w[-200:]))
    check("XW with the sampler: the samples hold the threads of the benchmark process (m. keys)",
          " ABS " in w and " m.run_ns=" in w and " m.nivcsw=" in w)
    env = box.file("env.txt")
    check("XW with the sampler: env.txt records the CPU of the sampler and the digest of hostwatch.py",
          re.search(r"^## host sampler: WATCH_CPU=%s Python \S+ sha256 %s$" % (
              box.watch_cpu, subprocess.run(["sha256sum", WATCH], capture_output=True, text=True).stdout.split()[0]), env, re.M) is not None, env)
    cpus = open(box.log + ".cpus").read()
    check("XW with the sampler: the sampler ran pinned to WATCH_CPU only, and the benchmark kept the CPUs 0-119",
          cpu_list(cpus) == {c for c in os.sched_getaffinity(0) if c < 120}
          and re.search(r"^# sampler pid=\d+ allowed_cpus=%s$" % box.watch_cpu, w, re.M) is not None, (cpus, w[:400]))

    rc, out, err = box.run(["--from", "26", "XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="1")
    check("XW, two processes: one sampler file per process, named by idx, each with header and footer",
          rc == 0 and all(box.file("watch-%d.txt" % i).startswith("# hostwatch v1 pid=") and "\n# end reason=" in box.file("watch-%d.txt" % i)
                          for i in (26, 27)) and box.file("watch-26.txt").split("\n")[0] != box.file("watch-27.txt").split("\n")[0]
          and box.none_alive(), (rc, err))

    p = box.start(["XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch("watch-0.txt")
    alive_before = len(samplers(box.case))
    open(box.stopfile, "w").close()
    out, err = p.communicate(timeout=60)
    tag = box.rows("XW")[0][1]
    check("XW, stop file during a process: status 5, '-- killed', the benchmark and its sampler are gone, the sampler file has its footer",
          up and alive_before == 1 and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv("XW")
          and box.none_alive() and "\n# end reason=" in box.file("watch-0.txt"), (up, alive_before, p.returncode, err))
    p = box.start(["XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch("watch-0.txt")
    open(box.marker, "w").close()
    out, err = p.communicate(timeout=60)
    check("XW, marker file during a process: status 3, '-- killed', one process started, benchmark and sampler gone",
          up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in box.csv("XW") and box.csv("XW").count("-- step ") == 1
          and box.none_alive(), (up, p.returncode, err))
    p = box.start(["XW"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch("watch-0.txt")
    os.kill(p.pid, signal.SIGTERM)
    out, err = p.communicate(timeout=60)
    csv = box.csv("XW")
    check("XW, interrupted during a process: status 130, '-- killed' marks the cut process, benchmark and sampler gone",
          up and p.returncode == 130 and box.none_alive()
          and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None
          and csv.count("-- step ") == 1, (up, p.returncode, err, csv))
    p = box.start(["XW"], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")
    up = box.wait_launch("watch-0.txt")
    out, err = p.communicate(timeout=120)
    check("XW, STOP_AT reached during a process: status 4, '-- killed', benchmark and sampler gone",
          up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv("XW") and box.none_alive(), (up, p.returncode, err))
    rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", DUMMY_EXIT="3", DUMMY_SLEEP="1")
    check("XW, failing binary: status 1, '-- failed', the sampler is gone and its file has the footer",
          rc == 1 and ("-- failed tag %s exit 3" % row[1]) in box.csv("XW") and box.none_alive()
          and "\n# end reason=" in box.file("watch-27.txt"), (rc, err))
    check("XW with the sampler: the start check of the sampler ran on the script before the first process and ended cleanly",
          re.search(r"^# end reason=max_s samples=\d+ missed=\d+ max_sample_us=\d+ errors=0$", box.file("watch-selftest.txt"), re.M) is not None
          and "max_s=0.3\n" in box.file("watch-selftest.txt") and "warning: the sampler file" not in err, box.file("watch-selftest.txt")[-200:])
    # Why: taskset can leave the CPUs 0-119 of the script, and the machine rule forbids CPUs 126 and 127.
    for value in ("120", "126", "127", "100000", "-1", "1,126", "100-127", "a[$(id)]", ""):
        rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", WATCH_CPU=value)
        if value == "":
            # An empty WATCH_CPU means the default 100: on a machine without CPU 100 the start check must stop the step.
            usable = 100 in os.sched_getaffinity(0)
            check("WATCH_CPU empty (default 100)%s" % (": runs" if usable else ", and this machine has no CPU 100: the start check stops "
                                                         "the step with status 2 before the first process, watch-stderr.txt holds the message"),
                  (rc == 0) if usable else (rc == 2 and "start check of the host sampler failed" in err and not box.launched()
                                            and box.file("watch-stderr.txt") != "" and box.csv("XW") == ""), (rc, err))
        else:
            check("WATCH_CPU='%s': status 2, nothing starts, no result folder" % value,
                  rc == 2 and "WATCH_CPU must be a CPU from 0 to 119" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    rc, out, err = box.run(["--from", "27", "XW"], SESSION="1", STOP_AT="none", WATCH_CPU=row[2])
    check("WATCH_CPU equal to a CPU of the schedule: status 2, nothing starts",
          rc == 2 and "is a CPU of the schedule" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none", WATCH_CPU="126")
    check("a step without sampler does not read WATCH_CPU: runs", rc == 0 and len(box.launched()) == 2, (rc, err))

    nopy = os.path.join(box.dir, "nopy")
    rc, out, err = box.run(["--from", "143", "XN"], pre=[os.path.join(nopy, "env")], SESSION="1", STOP_AT="none", PATH=nopy)
    ok_without = rc == 0 and len(box.launched()) == 2
    rc, out, err = box.run(["XEV", "XW"], pre=[os.path.join(nopy, "env")], SESSION="1", STOP_AT="none", PATH=nopy)
    check("python3 missing: a step with the sampler stops with status 2 before the first process of the call "
          "(a step without sampler runs under the same PATH)",
          ok_without and rc == 2 and "python3 is missing" in err and not box.launched() and not os.path.exists(box.results), (ok_without, rc, err))
    rc, out, err = box.run(["--dry-run", "XW"], pre=[os.path.join(nopy, "env")], SESSION="1", PATH=nopy)
    check("python3 missing: the dry run still prints the step", rc == 0 and out.count("\nbwx8 --trial ") == 28, (rc, err))
    os.rename(os.path.join(box.dir, "hostwatch.py"), os.path.join(box.dir, "hostwatch.moved"))
    rc, out, err = box.run(["XW"], SESSION="1", STOP_AT="none")
    check("hostwatch.py missing: a step with the sampler stops with status 2, nothing starts",
          rc == 2 and "hostwatch.py" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none")
    check("hostwatch.py missing: a step without sampler runs", rc == 0 and len(box.launched()) == 2, (rc, err))
    os.rename(os.path.join(box.dir, "hostwatch.moved"), os.path.join(box.dir, "hostwatch.py"))

    # ---- stop controls without sampler (as test_schedule8.py tests run_bwx8.sh) ----
    tag = rows[0][1]
    p = box.start(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch()
    open(box.marker, "w").close()
    out, err = p.communicate(timeout=60)
    csv = box.csv("XEV")
    check("marker file appears during a process: status 3, '-- killed', no process left",
          up and p.returncode == 3 and ("-- killed tag %s status 3" % tag) in csv
          and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)
    check("marker file present at the start: status 3, nothing starts, no result folder",
          rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")
    csv = box.csv("XEV")
    check("marker file appears between two processes: status 3, the first process ended, the second does not start",
          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,1\n") == 1 and "-- killed" not in csv
          and len(box.launched()) == 2, (rc, err, csv))
    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", PS_TOUCH=late,
                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])
    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",
          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("XEV")
          and box.file("launches.txt").count("== XEV.csv idx ") == 1, (rc, err))
    p = box.start(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch()
    open(box.stopfile, "w").close()
    out, err = p.communicate(timeout=60)
    check("stop file appears during a process: status 5, '-- killed', no process left",
          up and p.returncode == 5 and ("-- killed tag %s status 5" % tag) in box.csv("XEV") and box.none_alive(),
          (up, p.returncode, err))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_STOPFILE=box.stopfile)
    check("stop file present at the start: status 5, nothing starts", rc == 5 and not box.launched(), (rc, err))
    p = box.start(["XEV"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch()
    os.kill(p.pid, signal.SIGTERM)
    out, err = p.communicate(timeout=60)
    csv = box.csv("XEV")
    check("interrupted during a process: status 130, '-- killed' marks the cut process, no process left",
          up and p.returncode == 130 and box.none_alive()
          and re.search(r"^-- killed tag %s status 130 utc \S+$" % re.escape(tag), csv, re.M) is not None
          and csv.count("-- step ") == 1, (up, p.returncode, err, csv))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT=utc(30))
    check("STOP_AT nearer than MARGIN: status 4, nothing starts",
          rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))
    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the
    # test divisor 100 the longest XEV process is 0.009 s (1 s); with divisor 1 the longest XW process is 33 s.
    real = os.path.join(box.dir, "sched9-real")
    os.rename(os.path.join(box.dir, "sched9"), os.path.join(box.dir, "sched9-test"))
    shutil.copytree(os.path.join(X, "sched9"), os.path.join(box.dir, "sched9"))
    rc, out, err = box.run(["XW"], SESSION="1", STOP_AT=utc(100))
    check("MARGIN follows the longest process of the step: the real XW schedule refuses at 123 s, not at 91 s",
          rc == 4 and not box.launched() and "less than 123 s away" in err and "longest process 33 s, MARGIN 123 s" in out,
          (rc, err, out))
    rc, out, err = box.run(["--dry-run", "XEV", "XW", "XCA", "XCB", "XCC", "XN", "XF"], SESSION="1")
    check("--dry-run of the real schedules, session 1: 319 processes and the nominal work of the task (864, 396 x 3, 2.7, 1382.4, 864 s)",
          rc == 0 and out.count("\nbwx8 --trial ") == 319
          and all(s in out for s in ("step XW session 1: 28 processes, nominal kernel work 864.000 s",
                                     "step XCA session 1: 18 processes, nominal kernel work 396.000 s",
                                     "step XCB session 1: 18 processes, nominal kernel work 396.000 s",
                                     "step XCC session 1: 18 processes, nominal kernel work 396.000 s",
                                     "step XEV session 1: 3 processes, nominal kernel work 2.700 s",
                                     "step XN session 1: 144 processes, nominal kernel work 1382.400 s",
                                     "step XF session 1: 90 processes, nominal kernel work 864.000 s")), (rc, err, out[:300]))
    rc, out, err = box.run(["--dry-run", "XW", "XCA", "XCB", "XCC", "XN", "XF"], SESSION="2")
    check("--dry-run of the real schedules, session 2: 316 processes", rc == 0 and out.count("\nbwx8 --trial ") == 316, (rc, err))
    shutil.rmtree(os.path.join(box.dir, "sched9"))
    os.rename(os.path.join(box.dir, "sched9-test"), os.path.join(box.dir, "sched9"))
    p = box.start(["XEV"], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")
    up = box.wait_launch()
    out, err = p.communicate(timeout=120)
    check("STOP_AT reached during a process: status 4, '-- killed', no process left",
          up and p.returncode == 4 and ("-- killed tag %s status 4" % tag) in box.csv("XEV") and box.none_alive(),
          (up, p.returncode, err))
    rc, out, err = box.run(["XEV"], SESSION="1")
    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")
    csv = box.csv("XEV")
    check("failing binary: status 1, '-- failed', the next process does not start",
          rc == 1 and ("-- failed tag %s exit 3" % tag) in csv and csv.count("-- step ") == 1, (rc, err, csv))

    # ---- session 2 ----
    rc, out, err = box.run(["XN"], SESSION="2", STOP_AT="none")
    check("session 2 without SESSION1_END: status 2, nothing starts",
          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["XN"], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))
    check("session 2 earlier than 3 h after SESSION1_END: refused with status 2, nothing starts",
          rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "@0", "-4 hours",
                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)), "2026-02-30T00:00Z"):
        rc, out, err = box.run(["--from", "143", "XN"], SESSION="2", STOP_AT="none", SESSION1_END=value)
        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,
              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    s1end = utc(-3 * 3600 - 60)
    row2 = box.rows("XN", 2)[143]
    rc, out, err = box.run(["--from", "143", "XN"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)
    env = box.file("env.txt")
    check("session 2 later than 3 h after SESSION1_END: runs the session 2 schedule, folder bwx9-XN-s2-, SESSION1_END in env.txt",
          rc == 0 and "bwx9-XN-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env
          and ("-- step XN session 2 idx 143 tag %s " % row2[1]) in box.csv("XN")
          and "--plan sched9/s2/XN/0143.plan" in box.launched()[0], (rc, err))
    row2 = box.rows("XW", 2)[27]
    rc, out, err = box.run(["--from", "27", "XW"], SESSION="2", STOP_AT="none", SESSION1_END=s1end, DUMMY_SLEEP="1")
    check("session 2 with the sampler: the sampler watches the CPU of the session 2 row",
          rc == 0 and ("cpu=%s hz=20" % row2[2]) in box.file("watch-27.txt").split("\n")[0] and box.none_alive(), (rc, err))

    # ---- other refusals ----
    rc, out, err = box.run(["XEV"], STOP_AT="none")
    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_SHA256="0" * 64)
    check("bwx8 differs from BWX8_SHA256: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))
    digest = subprocess.run(["sha256sum", box.bin], capture_output=True, text=True).stdout.split()[0]
    rc, out, err = box.run(["--from", "2", "XEV"], SESSION="1", STOP_AT="none", BWX8_SHA256=digest)
    check("bwx8 equals BWX8_SHA256: runs", rc == 0 and len(box.launched()) == 2, (rc, err))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none", BWX8_BIN=os.path.join(box.dir, "absent"))
    check("missing binary: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "3", "XEV"], SESSION="1", STOP_AT="none")
    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "1", "XEV", "XN"], SESSION="1", STOP_AT="none")
    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))
    allowed = sorted(os.sched_getaffinity(0))
    rc, out, err = box.run(["--from", "2", "XEV"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")
    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""
    check("the benchmark is confined to CPUs 0-119, whatever CPU the script was started on",
          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1 and cpu_list(seen) == {c for c in allowed if c < 120},
          (rc, err, seen))
    tsv = os.path.join(box.dir, "sched9", "s1", "XEV.tsv")
    saved = open(tsv).read()
    made = os.path.join(box.dir, "made-by-schedule")
    for what, old_, new_ in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("cpu", "\t2\t", "\ta[$(touch${IFS}%s)]\t")):
        with open(tsv, "w") as fh:
            fh.write(saved.replace(old_, new_ % made, 1))
        rc, out, err = box.run(["--dry-run", "XEV"], SESSION="1")
        check("schedule with a command in %s: status 2, the command does not run" % what,
              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved, (rc, err))
    with open(tsv, "w") as fh:
        fh.write(saved)
    os.rename(os.path.join(box.dir, "sched9", "s1", "XEV", "0001.plan"), os.path.join(box.dir, "moved.plan"))
    rc, out, err = box.run(["XEV"], SESSION="1", STOP_AT="none")
    check("missing plan file: status 2 before the first launch", rc == 2 and "missing plan file" in err and not box.launched(), (rc, err))


def main():
    with open("/proc/loadavg") as f:
        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))
    tmp = tempfile.mkdtemp(prefix="test_schedule9.")
    try:
        sched = schedule_checks(tmp)
        if "--no-bwx8" in sys.argv[1:]:
            print("SKIP  the run of every plan through the local stand-in bwx8 (--no-bwx8)")
        else:
            bwx8_checks(tmp, sched)
        hostwatch_checks(tmp)
        visit_checks(tmp)
        if "--no-run" in sys.argv[1:]:
            print("SKIP  the checks of run_bwx9.sh with a dummy bwx8 (--no-run)")
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
