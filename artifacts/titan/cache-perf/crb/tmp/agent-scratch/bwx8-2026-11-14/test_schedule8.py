#!/usr/bin/env python3
"""test_schedule8.py - checks of schedule8.py, run_bwx8.sh and visit8.sh.

Usage: test_schedule8.py [--no-run]
Prints one line per check. Exit status 0 only if every check passed.
--no-run leaves out the checks that start run_bwx8.sh with a dummy bwx8 (they take minutes
on a loaded machine, because the script waits up to 20 s for a quiet system before a launch).
Every rule is also applied to a defective input, and the check passes only if that is rejected.
"""
import collections
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

X = os.path.dirname(os.path.abspath(__file__))
SCHED = os.path.join(X, "schedule8.py")
RUN = os.path.join(X, "run_bwx8.sh")
VISIT = os.path.join(X, "visit8.sh")
OLD_RUN = os.path.join(X, "..", "bwx-2026-11-13", "run_bwx.sh")
KERNELS = ["oldread", "read", "asmread"]
SELECT = "read@1M,asmread@8M"
M8 = 8 << 20
# Contract, "Nominal kernel work that schedule8.py must print": processes and seconds, both sessions.
NOMINAL = {"S2": (360, 3456.0), "S4": (36, 2160.0), "P3": (24, 691.2), "S3": (24, 3110.4),
           "P3G": (24, 4147.2), "S3G": (24, 1123.2), "B6W": (8, 124.8)}
# Contract table: processes per session and trials per process.
TABLE = {"B6W": (4, 0), "S2": (180, 4), "S4": (18, 1), "P3G": (12, 36), "P3": (12, 12),
         "S3G": (12, 12), "S3": (12, 48), "BIN": (24, 8), "CS": (24, 12), "CM": (12, 48), "C4": (18, 1)}

FAILS = []


def check(name, ok, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail) + "]") if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


# ---------- an independent validator of the plan grammar of the contract ----------
PHASE = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?):(\d+)$")
TGT = re.compile(r"^([a-z0-9_]+)@(\d+[KMG]?)$")
COND = re.compile(r"^[^=|, ]+=[^=|, ]+(\|[^=|, ]+=[^=|, ]+)*$")


def nbytes(tok):
    m = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
    return int(tok[:-1]) * m[tok[-1]] if tok[-1] in m else int(tok)


def parse_plan(text):
    """Returns (header dict, trials) or raises ValueError that names the defect."""
    if not text.endswith("\n"):
        raise ValueError("no final newline")
    lines = text[:-1].split("\n")
    if len(lines) < 4:
        raise ValueError("fewer than 4 lines")
    if lines[0] != "# bwx8-plan v1":
        raise ValueError("line 1")
    if not lines[1].startswith("# "):
        raise ValueError("line 2")
    head = {}
    for pair in lines[1][2:].split(" "):
        k, eq, v = pair.partition("=")
        if not k or not eq or not v or k in head:
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
            if not m or m.group(1) not in KERNELS or not size_ok(m.group(2)) or int(m.group(3)) < 1:
                raise ValueError("trial line %d: %s" % (n, name))
            ms[name] = int(m.group(3))
        if ms["pfx"] % 4:
            raise ValueError("trial line %d: pfx not a multiple of 4" % n)
        m = TGT.match(tgt)
        if not m or m.group(1) not in KERNELS or not size_ok(m.group(2)):
            raise ValueError("trial line %d: tgt" % n)
        if not (nwin.isdigit() and 1 <= int(nwin) <= 4096 and win_ms.isdigit() and int(win_ms) >= 1):
            raise ValueError("trial line %d: windows" % n)
        if count not in ("closed", "open", "read") or bins not in ("0", "1"):
            raise ValueError("trial line %d: count or bins" % n)
        trials.append({"cond": cond, "rep": int(rep), "prev": prev, "pfx": pfx, "pred": pred, "tgt": tgt,
                       "nwin": int(nwin), "win_ms": int(win_ms), "count": count, "bins": int(bins),
                       "ms": ms["prev"] + ms["pfx"] + ms["pred"] + int(nwin) * int(win_ms)})
    return head, trials


def rejected(text):
    try:
        parse_plan(text)
    except ValueError:
        return True
    return False


# ---------- reading a generated tree ----------
def gen(out, *opts):
    return subprocess.run([sys.executable, SCHED, "--out", out] + list(opts),
                          capture_output=True, text=True)


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
                if len(f) != 6 or f[0] != str(n):
                    errors.append("%s s%d row %d: columns or idx" % (step, session, n))
                    continue
                p = {"idx": n, "tag": f[1], "cpu": int(f[2]), "bytes": int(f[3]), "plan": f[4],
                     "args": f[5], "head": {}, "trials": []}
                if f[4] != "-":
                    rel = "sched/s%d/%s/%s" % (session, step, f[4])
                    want = "--trial --cpus %d --bytes %d --plan %s" % (p["cpu"], p["bytes"], rel)
                    if f[5] != want:
                        errors.append("%s s%d row %d: args" % (step, session, n))
                    try:
                        p["head"], p["trials"] = parse_plan(open(os.path.join(sdir, step, f[4])).read())
                    except (ValueError, OSError) as e:
                        errors.append("%s s%d row %d: %s" % (step, session, n, e))
                        continue
                    h = p["head"]
                    if (h["step"], h["session"], h["cpu"], h["bytes"], h["proc"]) != \
                            (step, str(session), f[2], f[3], f[0]):
                        errors.append("%s s%d row %d: header pairs differ from the row" % (step, session, n))
                procs.append(p)
            tags = [p["tag"] for p in procs]
            if len(set(tags)) != len(tags):
                errors.append("%s s%d: a tag occurs twice" % (step, session))
            tree[step, session] = procs
    return tree, errors


def proc_ms(p):
    if p["plan"] == "-":
        a = p["args"].split()
        return len(a[a.index("--seq") + 1].split(",")) * int(a[a.index("--rounds") + 1]) * \
            int(a[a.index("--min-ms") + 1])
    return sum(t["ms"] for t in p["trials"])


def tree_bytes(out):
    d = {}
    for root, _, files in os.walk(out):
        for f in files:
            path = os.path.join(root, f)
            d[os.path.relpath(path, out)] = open(path, "rb").read()
    return d


# ---------- rules, each returns True if the processes obey it ----------
def rows_of(procs, n):
    """{cpu: [row]}: rows of n cond labels, in schedule order."""
    rows = collections.defaultdict(list)
    for p in procs:
        c = [t["cond"] for t in p["trials"]]
        rows[p["cpu"]].extend(tuple(c[i:i + n]) for i in range(0, len(c), n))
    return rows


def perms_four_times(rows):
    """24 rows: each of the six orders of three labels four times."""
    labels = sorted(set(itertools.chain(*rows)))
    want = collections.Counter({p: 4 for p in itertools.permutations(labels)})
    return len(labels) == 3 and collections.Counter(rows) == want


def williams(rows):
    """Design line 242: each ordered pair of distinct conditions twice as neighbours inside rows,
    every condition twice at every position."""
    pairs, pos = collections.Counter(), collections.Counter()
    for r in rows:
        for i, c in enumerate(r):
            pos[c, i] += 1
            if i:
                pairs[r[i - 1], c] += 1
    return len(rows) == 24 and len(pairs) == 132 and set(pairs.values()) == {2} and \
        len(pos) == 144 and set(pos.values()) == {2}


START = [0, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6]


def from_start_order(rows):
    """The 24 rows are the 12 shifts of the start order under one relabelling, each twice."""
    if len(rows) != 24 or len(set(rows[0])) != 12:
        return False
    label = {START[i]: rows[0][i] for i in range(12)}
    shifts = {tuple(label[(x + d) % 12] for x in START): d for d in range(12)}
    return all(r in shifts for r in rows) and \
        collections.Counter(shifts[r] for r in rows) == collections.Counter({d: 2 for d in range(12)})


def shift_seq(rows):
    """The shift number of each row, counted from the first row (which gets 0)."""
    label = {START[i]: rows[0][i] for i in range(12)}
    shifts = {tuple(label[(x + d) % 12] for x in START): d for d in range(12)}
    return [shifts.get(r) for r in rows]


def rows_shuffled(rows):
    """Design line 242, 'shuffle the 24 rows, and assign them to the 6 processes x 4 cycles': the rows
    are not the 12 shifts in order, twice, and no two processes (4 rows each) hold the same rows in
    the same order. Without the shuffle, processes 1 to 3 and 4 to 6 of a CPU would run the same cycles."""
    groups = [tuple(rows[i:i + 4]) for i in range(0, len(rows), 4)]
    return shift_seq(rows) != list(range(12)) * 2 and len(set(groups)) == len(groups)


def order_varies(seqs):
    """Design lines 209 and 226, 'saved random assignment': the row sequences of the CPUs and sessions
    are not one fixed list. All sequences differ, and none repeats its first 6 rows."""
    seqs = [tuple(q) for q in seqs]
    return len(set(seqs)) == len(seqs) and all(q[:6] * (len(q) // 6) != q for q in seqs)


def cpu_blocks(procs, first, second):
    """The CPUs alternate first, second, first, ... when equal neighbours are merged."""
    seq = [k for k, _ in itertools.groupby(p["cpu"] for p in procs)]
    return len(seq) % 2 == 0 and all(c == (first, second)[i % 2] for i, c in enumerate(seq))


def s2_rules(procs, cpus):
    """Stage 2 order rules (design lines 207 to 209). Returns a list of defects."""
    bad = []
    assign = set()
    sets = collections.defaultdict(list)
    for p in procs:
        h, t = p["head"], p["trials"]
        k, s = h.get("kernel"), p["tag"].split("-")[1]
        if len(t) != 4 or any(x != {"cond": "K=%s|S=%s" % (k, s), "rep": i + 1, "prev": "-",
                                    "pfx": "%s@%s:%d" % (k, s, t[0]["win_ms"] * 4), "pred": "-",
                                    "tgt": "%s@%s" % (k, s), "nwin": 4, "win_ms": t[0]["win_ms"],
                                    "count": "closed", "bins": 0, "ms": t[0]["win_ms"] * 8}
                              for i, x in enumerate(t)):
            bad.append("process %d: not 4 trials of one kernel with itself as prefix" % p["idx"])
        if nbytes(s) != p["bytes"] or h.get("size") != str(p["bytes"]):
            bad.append("process %d: size" % p["idx"])
        sets[s, p["cpu"]].append((int(h.get("rep_set", 0)), k, p["idx"]))
    if sorted({s for s, _ in sets}, key=nbytes) != ["32K", "1M", "4M", "8M", "16M"]:
        bad.append("sizes")
    for (s, cpu), members in sets.items():
        orders = collections.defaultdict(list)
        for r, k, _ in members:
            orders[r].append(k)
        if sorted(orders) != [1, 2, 3, 4, 5, 6] or \
                {tuple(o) for o in orders.values()} != set(itertools.permutations(KERNELS)):
            bad.append("size %s cpu %d: the six sets do not use the six kernel orders once each" % (s, cpu))
        assign.add(tuple(tuple(orders[r]) for r in sorted(orders)))
    # Design line 209, 'with a saved random assignment': which set gets which order is drawn per size and CPU.
    if len(assign) < 2:
        bad.append("every size and CPU gives the same kernel order to the same set")
    # Process order: replicate block, then size, then CPU in session order, then the three kernels.
    size_orders = set()
    for r in range(6):
        block = procs[30 * r:30 * r + 30]
        if any(p["head"].get("rep_set") != str(r + 1) for p in block) or len(block) != 30:
            bad.append("block %d: rep_set" % (r + 1))
            continue
        sizes = []
        for g in range(5):
            six = block[6 * g:6 * g + 6]
            if len({p["bytes"] for p in six}) != 1 or [p["cpu"] for p in six] != [cpus[0]] * 3 + [cpus[1]] * 3:
                bad.append("block %d group %d: size or CPU order" % (r + 1, g))
            sizes.append(six[0]["bytes"])
        if len(set(sizes)) != 5:
            bad.append("block %d: a size is missing" % (r + 1))
        size_orders.add(tuple(sizes))
    if len(size_orders) < 2:
        bad.append("the size order is the same in every block")
    return bad


def s2_fixed_assignment(procs):
    """A copy of a Stage 2 schedule in which set r of every size and CPU uses the same kernel order."""
    m = copy.deepcopy(procs)
    fixed = list(itertools.permutations(KERNELS))
    for i in range(0, len(m), 3):
        for p, k in zip(m[i:i + 3], fixed[int(m[i]["head"]["rep_set"]) - 1]):
            s, ms = p["tag"].split("-")[1], p["trials"][0]["win_ms"]
            p["tag"] = "-".join(p["tag"].split("-")[:3] + [k])
            p["head"]["kernel"] = k
            for t in p["trials"]:
                t.update(cond="K=%s|S=%s" % (k, s), pfx="%s@%s:%d" % (k, s, 4 * ms), tgt="%s@%s" % (k, s))
    return m


def same_kernel(t, k, s):
    return t["prev"] == "-" and t["pred"] == "-" and t["tgt"] == "%s@%s" % (k, s) and \
        t["pfx"] == "%s@%s:%d" % (k, s, 4 * t["win_ms"]) and t["nwin"] == 4


def cond_dict(cond):
    return dict(x.split("=") for x in cond.split("|"))


def per_cpu_count(procs, n):
    return collections.Counter(p["cpu"] for p in procs) == collections.Counter({2: n, 41: n})


def mutate_swap(procs):
    """A copy with the first two trials of the first process exchanged."""
    m = copy.deepcopy(procs)
    t = m[0]["trials"]
    t[0], t[1] = t[1], t[0]
    return m


def schedule_checks(tmp):
    a, b, c = (os.path.join(tmp, n) for n in ("a", "b", "c"))
    r = gen(a, "--select", SELECT)
    check("schedule8.py runs with status 0", r.returncode == 0, r.stderr)
    tree, errors = load(a)
    check("every schedule row and plan file obeys the format and the plan grammar", not errors, errors[:3])
    check("all 11 steps exist in both sessions", len(tree) == 22, sorted(tree))

    # The validator itself rejects defective plans.
    good = open(os.path.join(a, "s1", "S3", "0000.plan")).read()
    line = good.split("\n")[3]
    bad = {"rep out of order": good.replace(" 1 - ", " 2 - ", 1),
           "prefix not a multiple of 4": good.replace("oldread@8M:1200", "oldread@8M:1202", 1),
           "size above bytes": good.replace(line, line.replace("oldread@8M:1200", "oldread@16M:1200")),
           "unknown kernel": good.replace(line, line.replace("oldread@8M:1200", "copy@8M:1200")),
           "two spaces": good.replace(line, line.replace(" ", "  ", 1)),
           "trial number": good.replace("\n1 ", "\n7 ", 1),
           "wrong first line": good.replace("plan v1", "plan v2"),
           "count word": good.replace(line, line.replace("closed", "shut")),
           "size not a multiple of 256": good.replace(line, line[:line.rindex("@8M")] + "@1000" + line[line.rindex("@8M") + 3:]),
           "comma in cond": good.replace(line, line.replace("|", ",", 1)),
           "header lacks seed": good.replace(" seed=", " sead=")}
    check("validator accepts a generated plan", not rejected(good))
    for name, text in bad.items():
        check("validator rejects: " + name, text != good and rejected(text))

    # Counts and nominal work, from the files.
    for step, (n, sec) in NOMINAL.items():
        procs = tree[step, 1] + tree[step, 2]
        ms = sum(proc_ms(p) for p in procs)
        check("%s: %d processes and %.1f s of nominal kernel work in both sessions" % (step, n, sec),
              len(procs) == n and ms == round(sec * 1000), (len(procs), ms))
    short = copy.deepcopy(tree["S2", 1] + tree["S2", 2])
    short[0]["trials"].pop()
    check("nominal work: a schedule with one trial missing does not give the S2 value",
          sum(proc_ms(p) for p in short) != 3456000)
    for step, (n, tr) in TABLE.items():
        for s in (1, 2):
            procs = tree[step, s]
            check("%s session %d: %d processes of %d trials" % (step, s, n, tr),
                  len(procs) == n and all(len(p["trials"]) == tr for p in procs))
    for step, (n, sec) in NOMINAL.items():
        want = "%s total: %d processes, " % (step, n)
        hit = [l for l in r.stdout.split("\n") if l.startswith(want)]
        check("report prints the %s total" % step,
              len(hit) == 1 and ("nominal kernel work %g s " % sec) in hit[0], hit)

    # Header pairs that the analysis groups by.
    check("plan headers: seed is one value per step and session, test=0",
          all(len({p["head"]["seed"] for p in procs}) == 1 and all(p["head"]["test"] == "0" for p in procs)
              for (step, _), procs in tree.items() if step != "B6W"))
    check("plan headers: the seeds of the steps and sessions differ",
          len({procs[0]["head"]["seed"] for (step, _), procs in tree.items() if step != "B6W"}) == 20)
    check("plan headers: kernel and size where a process has one kernel",
          all(all(p["head"].get("kernel") in KERNELS and p["head"].get("size") == str(p["bytes"])
                  and {t["tgt"].split("@")[0] for t in p["trials"]} == {p["head"]["kernel"]} for p in procs)
              for (step, _), procs in tree.items() if step in ("S2", "S4", "C4", "BIN", "CS")))
    check("cond labels are key=value pairs that agree with the trial",
          all(cond_dict(t["cond"]).get("count", "closed") == t["count"]
              and int(cond_dict(t["cond"]).get("bins", 0)) == t["bins"]
              and cond_dict(t["cond"]).get("K", cond_dict(t["cond"]).get("T")) == t["tgt"].split("@")[0]
              for procs in tree.values() for p in procs for t in p["trials"]))

    # Session order of the CPUs.
    for (step, s), procs in sorted(tree.items()):
        first, second = (2, 41) if s == 1 else (41, 2)
        check("%s session %d: CPU order %d then %d" % (step, s, first, second), cpu_blocks(procs, first, second))
    check("CPU order rule rejects session 1 read as session 2", not cpu_blocks(tree["S3", 1], 41, 2))

    # Stage 2.
    for s in (1, 2):
        defects = s2_rules(tree["S2", s], (2, 41) if s == 1 else (41, 2))
        check("S2 session %d: order rules" % s, not defects, defects[:3])
    m = copy.deepcopy(tree["S2", 1])
    m[0]["head"]["kernel"], m[1]["head"]["kernel"] = m[1]["head"]["kernel"], m[0]["head"]["kernel"]
    m[0]["trials"], m[1]["trials"] = m[1]["trials"], m[0]["trials"]
    m[0]["tag"], m[1]["tag"] = m[1]["tag"], m[0]["tag"]
    check("S2 rules reject a set whose kernel order repeats another set", bool(s2_rules(m, (2, 41))))
    m = copy.deepcopy(tree["S2", 1])
    m[2], m[3] = m[3], m[2]
    check("S2 rules reject CPUs that alternate inside a size", bool(s2_rules(m, (2, 41))))
    check("S2 rules reject the session 1 schedule under the session 2 CPU order",
          bool(s2_rules(tree["S2", 1], (41, 2))))
    m = copy.deepcopy(tree["S2", 1])
    m[5]["trials"][0]["pfx"] = "oldread@1M:1200" if m[5]["head"]["kernel"] != "oldread" else "read@1M:1200"
    check("S2 rules reject a prefix of another kernel", bool(s2_rules(m, (2, 41))))
    check("S2 rules reject a schedule whose sets have the same kernel order in every size and CPU",
          s2_rules(s2_fixed_assignment(tree["S2", 1]), (2, 41)) ==
          ["every size and CPU gives the same kernel order to the same set"],
          s2_rules(s2_fixed_assignment(tree["S2", 1]), (2, 41))[:3])

    # Stage 3 and the mixed-sequence counters: 12 conditions, design line 242.
    preds = ["oldread@8M", "read@8M", "asmread@8M", "oldread@1M"]
    s3_conds = {"P=%s|T=%s" % (p, t) for p in preds for t in KERNELS}
    cm_conds = {"P=%s@8M|T=%s|count=%s" % (p, t, m) for p in ("oldread", "read")
                for t in ("oldread", "read") for m in ("closed", "open", "read")}
    for step, conds in (("S3", s3_conds), ("CM", cm_conds)):
        for s in (1, 2):
            procs = tree[step, s]
            rows = rows_of(procs, 12)
            check("%s session %d: 6 processes per CPU, each cycle holds the 12 conditions once" % (step, s),
                  per_cpu_count(procs, 6) and all(set(r) == conds for rr in rows.values() for r in rr))
            check("%s session %d: trial is prefix oldread@8M, predecessor P, target T@8M" % (step, s),
                  all(t["prev"] == "-" and t["pfx"] == "oldread@8M:%d" % (4 * t["win_ms"])
                      and t["pred"] == "%s:%d" % (cond_dict(t["cond"])["P"], t["win_ms"])
                      and t["tgt"] == cond_dict(t["cond"])["T"] + "@8M" and t["nwin"] == 4
                      for p in procs for t in p["trials"]))
            for cpu in (2, 41):
                check("%s session %d cpu %d: pair and position balance of line 242" % (step, s, cpu),
                      williams(rows[cpu]))
                check("%s session %d cpu %d: rows are the shifted start order, relabelled, twice" % (step, s, cpu),
                      from_start_order(rows[cpu]))
                check("%s session %d cpu %d: the 24 rows are shuffled over the processes" % (step, s, cpu),
                      rows_shuffled(rows[cpu]), shift_seq(rows[cpu]))
        check("%s: the order of the shifted rows differs between CPUs and sessions" % step,
              len({tuple(shift_seq(rows_of(tree[step, s], 12)[cpu])) for s in (1, 2) for cpu in (2, 41)}) == 4)
        check("%s: the relabelling differs between CPUs and sessions" % step,
              len({tuple(sorted(rows_of(tree[step, s], 12)[cpu])) for s in (1, 2) for cpu in (2, 41)}) == 4)
    bad_rows = rows_of(mutate_swap([p for p in tree["S3", 1] if p["cpu"] == 2]), 12)[2]
    check("balance rule rejects a schedule with two trials exchanged", not williams(bad_rows))
    check("start-order rule rejects a schedule with two trials exchanged", not from_start_order(bad_rows))
    rnd = [tuple(sorted(r)) for r in rows_of(tree["S3", 1], 12)[2]]
    check("start-order rule rejects rows that are not shifts", not from_start_order(rnd))
    good_rows = rows_of(tree["S3", 1], 12)[2]
    by_shift = dict(zip(shift_seq(good_rows), good_rows))
    plain = [by_shift[d] for d in range(12)] * 2
    check("shuffle rule rejects the 12 shifted rows in order, twice (it still obeys the balance rule)",
          williams(plain) and from_start_order(plain) and not rows_shuffled(plain))

    # P3, S3G, CS: all six orders four times per CPU and session (CS: per kernel and size too).
    for s in (1, 2):
        for step in ("P3", "S3G"):
            rows = rows_of(tree[step, s], 3)
            check("%s session %d: 6 processes per CPU; six orders four times each per CPU" % (step, s),
                  per_cpu_count(tree[step, s], 6) and all(perms_four_times(rows[c]) for c in (2, 41)))
        check("P3 session %d: every trial is a kernel at 8M with itself as prefix" % s,
              all(same_kernel(t, cond_dict(t["cond"])["K"], "8M") and cond_dict(t["cond"])["S"] == "8M"
                  for p in tree["P3", s] for t in p["trials"]))
        check("S3G session %d: previous J 1.2 s, prefix, predecessor and target old read" % s,
              all(t["prev"] == "%s@8M:%d" % (cond_dict(t["cond"])["J"], 4 * t["win_ms"])
                  and t["pfx"] == "oldread@8M:%d" % (4 * t["win_ms"])
                  and t["pred"] == "oldread@8M:%d" % t["win_ms"] and t["tgt"] == "oldread@8M"
                  for p in tree["S3G", s] for t in p["trials"]))
        groups = collections.defaultdict(list)
        for p in tree["CS", s]:
            groups[p["head"]["kernel"], p["head"]["size"], p["cpu"]].append(p)
        check("CS session %d: 6 processes per kernel, size and CPU; six mode orders four times each" % s,
              len(groups) == 4 and all(len(g) == 6 and perms_four_times(rows_of(g, 3)[g[0]["cpu"]])
                                       for g in groups.values()))
        check("CS session %d: modes closed, open, read on one kernel and size per process" % s,
              all({t["count"] for t in p["trials"]} == {"closed", "open", "read"}
                  and all(same_kernel(t, p["head"]["kernel"], cond_dict(t["cond"])["S"])
                          and nbytes(cond_dict(t["cond"])["S"]) == p["bytes"] for t in p["trials"])
                  for p in tree["CS", s]))
        # P3G: 9 conditions in each of 4 cycles.
        nine = {"J=%s|K=%s" % (j, k) for j in KERNELS for k in KERNELS}
        rows = rows_of(tree["P3G", s], 9)
        check("P3G session %d: 6 processes per CPU, each cycle holds the 9 conditions once" % s,
              per_cpu_count(tree["P3G", s], 6) and all(set(r) == nine for rr in rows.values() for r in rr))
        check("P3G session %d: the cycles are not all in one order" % s,
              all(len(set(rows[c])) > 12 for c in (2, 41)))
        check("P3G session %d: previous J 2.4 s, then K as prefix and target" % s,
              all(t["prev"] == "%s@8M:%d" % (cond_dict(t["cond"])["J"], 8 * t["win_ms"])
                  and t["pfx"] == "%s@8M:%d" % (cond_dict(t["cond"])["K"], 4 * t["win_ms"])
                  and t["pred"] == "-" and t["tgt"] == cond_dict(t["cond"])["K"] + "@8M"
                  for p in tree["P3G", s] for t in p["trials"]))
        # S4 and C4.
        for step, count in (("S4", "closed"), ("C4", "read")):
            procs = tree[step, s]
            per = collections.Counter((p["head"]["kernel"], p["cpu"]) for p in procs)
            triples = [procs[i:i + 3] for i in range(0, 18, 3)]
            check("%s session %d: 3 processes per kernel and CPU, the three kernels in each replicate" % (step, s),
                  set(per.values()) == {3} and len(per) == 6 and
                  all(len({p["cpu"] for p in t}) == 1 and {p["head"]["kernel"] for p in t} == set(KERNELS)
                      for t in triples))
            check("%s session %d: one trial, no prefix, 200 windows at 8M, count %s" % (step, s, count),
                  all((t["prev"], t["pfx"], t["pred"], t["nwin"], t["count"], t["tgt"]) ==
                      ("-", "-", "-", 200, count, p["head"]["kernel"] + "@8M")
                      for p in procs for t in p["trials"]))
            check("%s session %d: the kernel order differs between replicates" % (step, s),
                  len({tuple(p["head"]["kernel"] for p in t) for t in triples}) > 1)
        # BIN.
        groups = collections.defaultdict(list)
        for p in tree["BIN", s]:
            groups[p["head"]["kernel"], p["head"]["size"], p["cpu"]].append(
                tuple(t["bins"] for t in p["trials"]))
        ab, ba = (0, 1, 1, 0, 1, 0, 0, 1), (1, 0, 0, 1, 0, 1, 1, 0)
        check("BIN session %d: orders ABBA BAAB and BAAB ABBA alternate between processes" % s,
              len(groups) == 4 and all(g == [ab, ba] * 3 for g in groups.values()), dict(groups))
        check("BIN session %d: trials as S2" % s,
              all(same_kernel(t, p["head"]["kernel"], cond_dict(t["cond"])["S"])
                  for p in tree["BIN", s] for t in p["trials"]))
    for step in ("P3", "S3G"):
        check("%s: the order of the 24 rows differs between CPUs and sessions and is not one fixed list" % step,
              order_varies([rows_of(tree[step, s], 3)[c] for s in (1, 2) for c in (2, 41)]))
    cs = collections.defaultdict(list)
    for s in (1, 2):
        for p in tree["CS", s]:
            cs[s, p["head"]["kernel"], p["head"]["size"], p["cpu"]].extend(
                tuple(t["count"] for t in p["trials"][i:i + 3]) for i in range(0, 12, 3))
    check("CS: the order of the 24 rows differs between kernels, sizes, CPUs and sessions and is not one fixed list",
          len(cs) == 8 and order_varies(cs.values()))
    p3 = rows_of(tree["P3", 1], 3)
    plain = sorted(set(p3[2])) * 4
    check("row-order rule rejects the six orders as a fixed list, four times (it still obeys the order count)",
          perms_four_times(plain) and not order_varies([plain, p3[41]])
          and not order_varies([p3[2], p3[2]]))
    bad_rows = rows_of(mutate_swap(tree["P3", 1]), 3)[tree["P3", 1][0]["cpu"]]
    check("order-count rule rejects a schedule with two trials exchanged", not perms_four_times(bad_rows))

    # B6W: the unchanged sequence of run_bwx.sh.
    seq = re.search(r"^B6SEQ=(\S+)$", open(OLD_RUN).read(), re.M).group(1)
    check("B6W: 2 processes per CPU, arguments with the B6 sequence of run_bwx.sh",
          all([p["args"] for p in tree["B6W", s]] ==
              ["--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 --min-ms 300 --stop pass" % (c, seq)
               for c in ((2, 41) if s == 1 else (41, 2)) * 2] for s in (1, 2)))

    # Determinism.
    gen(b, "--select", SELECT)
    r3 = gen(c, "--select", SELECT, "--seed", "7")
    ta, tb, tc = tree_bytes(a), tree_bytes(b), tree_bytes(c)
    check("two runs with one base seed give the same bytes", ta == tb and len(ta) == 671, len(ta))
    check("another base seed gives the same file names and other bytes",
          r3.returncode == 0 and sorted(ta) == sorted(tc) and ta != tc
          and ta["s1/S2.tsv"] != tc["s1/S2.tsv"] and ta["s1/S3/0000.plan"] != tc["s1/S3/0000.plan"])
    check("the base seed is saved in MANIFEST.txt", b"base_seed=20261114\n" in ta["MANIFEST.txt"]
          and b"base_seed=7\n" in tc["MANIFEST.txt"])
    tree7, errors7 = load(c)
    check("another base seed keeps the rules (grammar, S2 order, S3 balance)",
          not errors7 and not s2_rules(tree7["S2", 2], (41, 2))
          and all(williams(rows_of(tree7["S3", 2], 12)[cpu]) for cpu in (2, 41)))

    # Without --select the optional steps are not written.
    d = os.path.join(tmp, "d")
    r4 = gen(d)
    td = tree_bytes(d)
    check("without --select: no BIN and no CS, the other steps unchanged",
          r4.returncode == 0 and not any("/BIN" in k or "/CS" in k for k in td)
          and all(td[k] == ta[k] for k in td if k != "MANIFEST.txt"))
    check("a bad --select entry is refused", gen(d, "--select", "copy@8M").returncode != 0
          and gen(d, "--select", "read@1000").returncode != 0)
    saved = os.path.join(X, "sched")
    check("the saved sched/ beside the scripts is the output of the default base seed",
          os.path.isdir(saved) and tree_bytes(saved) == td)
    e = os.path.join(tmp, "e")
    r5 = subprocess.run([sys.executable, SCHED, "--out", e, "--report"], capture_output=True, text=True)
    check("--report prints the counts and writes nothing",
          r5.returncode == 0 and not os.path.exists(e) and "S2 total: 360 processes" in r5.stdout
          and "pair of distinct conditions" in r5.stdout and "each kernel order once" in r5.stdout)

    # --test-divisor.
    t = os.path.join(tmp, "t")
    r6 = gen(t, "--select", SELECT, "--test-divisor", "100")
    ttree, terr = load(t)
    check("--test-divisor 100: valid plans, test=1, every duration divided by 100",
          r6.returncode == 0 and not terr
          and all(p["head"]["test"] == "1" for (st, _), pp in ttree.items() if st != "B6W" for p in pp)
          and all(sum(proc_ms(p) for p in ttree[k]) * 100 == sum(proc_ms(p) for p in tree[k]) for k in tree))
    check("--test-divisor 7 is refused (it does not divide 300 ms)",
          gen(os.path.join(tmp, "u"), "--test-divisor", "7").returncode != 0)
    return t


# ---------- run_bwx8.sh with a dummy bwx8 ----------
DUMMY = """#!/usr/bin/env bash
# Stand-in for bwx8: records its process ids, checks the plan file, sleeps, ends with DUMMY_EXIT.
echo "$$ $*" >> "$DUMMY_LOG"
grep Cpus_allowed_list /proc/$$/status >> "$DUMMY_LOG.cpus"
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
# run_bwx8.sh calls ps once for env.txt and then once per launch, after the wait and before the last marker check.
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
    """'Cpus_allowed_list: 0-3,8' as a set of CPU numbers."""
    cpus = set()
    for part in text.split(":")[1].strip().split(","):
        a, _, b = part.partition("-")
        cpus.update(range(int(a), int(b or a) + 1))
    return cpus


def utc(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


class Box:
    """A copy of run_bwx8.sh with a test schedule and the dummy binary in a temporary folder."""

    def __init__(self, tmp, sched):
        self.dir = os.path.join(tmp, "box")
        os.makedirs(self.dir)
        shutil.copy(RUN, self.dir)
        shutil.copytree(sched, os.path.join(self.dir, "sched"))
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
        self.n = 0

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
                          "BWX_PMU_TYPE", "BWX_EVENTS")}
        e.update(HOME=self.case, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_BIN=self.bin,
                 BWX8_RESULTS=self.results, DUMMY_LOG=self.log)
        e.update(env)
        e = {k: v for k, v in e.items() if v is not None}      # None: leave this setting out
        return subprocess.Popen(list(pre) + [os.path.join(self.dir, "run_bwx8.sh")] + args, env=e, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)

    def run(self, args, pre=(), **env):
        p = self.start(args, pre, **env)
        out, err = p.communicate(timeout=400)
        return p.returncode, out, err

    def folder(self):
        d = os.listdir(self.results) if os.path.isdir(self.results) else []
        return os.path.join(self.results, d[0]) if len(d) == 1 else None

    def csv(self, step):
        f = self.folder()
        path = os.path.join(f, step + ".csv") if f else ""
        return open(path).read() if os.path.exists(path) else ""

    def launched(self):
        return [l for l in open(self.log).read().split("\n") if l] if os.path.exists(self.log) else []

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
        return True


def visit_checks(tmp):
    """visit8.sh with a stand-in ssh. PATH holds only the stand-in and date, so no real ssh can start."""
    d = os.path.join(tmp, "visit")
    os.makedirs(os.path.join(d, "bin"))
    text, n = re.subn(r"(?m)^N=.*$", "N=" + d, open(VISIT).read())
    copy_path = os.path.join(d, "visit8.sh")
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
        r = subprocess.run([shutil.which("bash"), copy_path, name, "S2"], env=e, capture_output=True, text=True)
        return r.returncode, open(log).read() if os.path.exists(log) else None, r.stderr

    rc, cmd, err = visit("ok", STOP_AT="2026-11-15T15:00Z", SESSION="2", SESSION1_END="2026-11-15T03:00Z",
                         BWX8_SHA256="0a1b")
    check("visit8.sh: one login; the marker check is the first remote action, then run_bwx8.sh with the settings",
          n == 1 and rc == 0 and cmd is not None and cmd.count("\n") == 1
          and cmd.startswith("if [ -e /tmp/positron-perf.RUNNING ]; then ")
          and cmd.endswith("&& STOP_AT=2026-11-15T15:00Z SESSION=2 SESSION1_END=2026-11-15T03:00Z "
                           "BWX8_SHA256=0a1b  ./run_bwx8.sh S2\n"), (rc, cmd, err))
    # A value with a blank or a shell character would split or change the remote command line:
    # the login would do nothing, or run something else. Handoff rule: keep the number of logins small.
    ok = {"STOP_AT": "2026-11-15T15:00Z", "SESSION": "2", "SESSION1_END": "2026-11-15T03:00Z", "BWX8_SHA256": "0a1b"}
    for var, value in (("SESSION1_END", "2026-11-15 03:00"), ("STOP_AT", "2026-11-15 15:00"),
                       ("STOP_AT", "none;id"), ("SESSION", "1$(id)"), ("BWX8_SHA256", "0a1b|x")):
        rc, cmd, err = visit("bad", **dict(ok, **{var: value}))
        check("visit8.sh: %s='%s' is refused with status 2 before the login, no log file" % (var, value),
              rc == 2 and cmd is None and var in err and not os.path.exists(os.path.join(d, "bad.log")),
              (rc, cmd, err))


def run_checks(tmp, sched):
    for f in ("run_bwx8.sh", "visit8.sh"):
        r = subprocess.run(["bash", "-n", os.path.join(X, f)], capture_output=True, text=True)
        check("bash -n " + f, r.returncode == 0, r.stderr)
    box = Box(tmp, sched)

    rc, out, err = box.run(["--dry-run", "P3", "P3"], SESSION="1")
    check("a step named twice: status 2, nothing is printed for it (the script never repeats a process)",
          rc == 2 and "twice" in err and "step P3" not in out, (rc, out[:200], err))
    rc, out, err = box.run(["--dry-run", "P3"], SESSION="1")
    rc2, out2, err2 = box.run(["--dry-run", "P3"], SESSION="1", BWX8_MARKER=None, BWX8_STOPFILE=None,
                              BWX8_BIN=None, BWX8_RESULTS=None)
    check("a warning names each test setting that moves the marker, the stop file, the binary or the results",
          rc == 0 and all(("warning: %s is set" % v) in err for v in
                          ("BWX8_MARKER", "BWX8_STOPFILE", "BWX8_BIN", "BWX8_RESULTS"))
          and rc2 == 0 and "warning" not in err2 and out2 == out, (rc, err, rc2, err2))

    # Schedule fields that reach shell arithmetic must be plain numbers: arithmetic runs a command
    # that is written inside an array subscript, in a dry run too.
    tsv = os.path.join(box.dir, "sched", "s1", "B6W.tsv")
    saved_tsv = open(tsv).read()
    for what, old, new in (("idx", "\n0\t", "\na[$(touch${IFS}%s)]\t"), ("--rounds", "--rounds 4", "--rounds a[$(touch${IFS}%s)]"),
                           ("--min-ms", "--min-ms 3", "--min-ms a[$(touch${IFS}%s)]3")):
        made = os.path.join(box.dir, "made-by-schedule")
        with open(tsv, "w") as f:
            f.write(saved_tsv.replace(old, new % made, 1))
        rc, out, err = box.run(["--dry-run", "B6W"], SESSION="1")
        check("schedule with a command in %s: status 2, the command does not run" % what,
              rc == 2 and not os.path.exists(made) and open(tsv).read() != saved_tsv, (rc, err))
        if os.path.exists(made):
            os.remove(made)
    with open(tsv, "w") as f:
        f.write(saved_tsv)

    rc, out, err = box.run(["--dry-run", "S2", "S3"], SESSION="1")
    check("--dry-run: status 0, prints the counts of each step",
          rc == 0 and "step S2 session 1: 180 processes, nominal kernel work 17.280 s" in out
          and "step S3 session 1: 12 processes, nominal kernel work 15.552 s" in out
          and "selected conditions (15):" in out and "selected conditions (12):" in out
          and out.count("\nbwx8 --trial ") == 192, (rc, out[:300], err))
    check("--dry-run: starts nothing and makes no result folder", not box.launched() and not os.path.exists(box.results))

    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none")
    f = box.folder()
    csv = box.csv("B6W")
    heads = re.findall(r"^-- step B6W session 1 idx (\d+) tag (\S+) waited_s \d+ loadavg .* logins \d+ utc \S+ args (.*)$", csv, re.M)
    check("normal end: status 0", rc == 0, (rc, err))
    check("normal end: the counts are printed before the result folder is made",
          "step B6W session 1: 4 processes, nominal kernel work 0.624 s" in out
          and 0 <= out.find("step B6W session 1: 4 processes") < out.find("result folder: "), out)
    check("normal end: folder name and its six files",
          f is not None and re.match(r"^bwx8-B6W-s1-\d{8}T\d{6}Z$", os.path.basename(f)) is not None
          and sorted(os.listdir(f)) == ["B6W.csv", "build.txt", "env.txt", "launches.txt", "schedule.tsv", "stderr.txt"],
          f and os.listdir(f))
    if f:
        rows = open(os.path.join(box.dir, "sched", "s1", "B6W.tsv")).read()
        check("normal end: schedule.tsv and build.txt are copies",
              open(os.path.join(f, "schedule.tsv")).read() == rows
              and open(os.path.join(f, "build.txt")).read() == "dummy build record\n")
        want = [tuple(r.split("\t")[i] for i in (0, 1, 5)) for r in rows.split("\n")[1:-1]]
        check("normal end: one header line per process, in schedule order, each followed by its output",
              heads == want and csv.count("M,dummy,1\n") == 4 and "-- killed" not in csv and "-- failed" not in csv, heads)
        env = open(os.path.join(f, "env.txt")).read()
        check("normal end: env.txt holds session, from, load, digests and the end line",
              "session=1 from=0 " in env and "loadavg=" in env and "## sha256:" in env and "## end utc=" in env
              and open(os.path.join(f, "launches.txt")).read().count("== B6W.csv idx ") == 4, env)
        check("normal end: env.txt records the marker, stop file, binary and result paths in use",
              (" MARKER=%s STOPFILE=%s BIN=%s RESULTS=%s\n" % (box.marker, box.stopfile, box.bin, box.results)) in env, env)
    check("normal end: each process ran once", len(box.launched()) == 8 and box.none_alive())

    rc, out, err = box.run(["--from", "11", "P3"], SESSION="1", STOP_AT="none")
    csv = box.csv("P3")
    env = open(os.path.join(box.folder(), "env.txt")).read() if box.folder() else ""
    check("--from 11: only idx 11 runs, with its plan file, and env.txt records from=11",
          rc == 0 and re.findall(r"^-- step P3 session 1 idx (\d+) ", csv, re.M) == ["11"]
          and " from=11 " in env and "to run from idx 11: 1 processes" in out
          and len(box.launched()) == 2 and "--plan sched/s1/P3/0011.plan" in box.launched()[0], (rc, err, csv))
    # Design line 364, "use only the permitted CPUs": the script moves itself to CPUs 0-119, whatever
    # it was started on. Started on one CPU, the benchmark must see every CPU of this machine below 120.
    allowed = sorted(os.sched_getaffinity(0))
    rc, out, err = box.run(["--from", "3", "B6W"], pre=["taskset", "-c", str(allowed[0])], SESSION="1", STOP_AT="none")
    seen = open(box.log + ".cpus").read() if os.path.exists(box.log + ".cpus") else ""
    check("the benchmark is confined to CPUs 0-119 (needs a machine with 2 or more CPUs to tell)",
          rc == 0 and len(allowed) > 1 and seen.count("\n") == 1
          and cpu_list(seen) == {c for c in allowed if c < 120}, (rc, err, seen, allowed))
    rc, out, err = box.run(["--from", "12", "P3"], SESSION="1", STOP_AT="none")
    check("--from past the last idx: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "1", "P3", "S3"], SESSION="1", STOP_AT="none")
    check("--from with two steps: status 2", rc == 2 and not box.launched(), (rc, err))

    p = box.start(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch()
    open(box.marker, "w").close()
    out, err = p.communicate(timeout=60)
    csv = box.csv("B6W")
    check("marker file appears during a process: status 3, '-- killed', no process left",
          up and p.returncode == 3 and "-- killed tag cpu2-p1 status 3" in csv
          and csv.count("-- step ") == 1 and box.none_alive(), (up, p.returncode, err, csv))
    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", BWX8_MARKER=box.marker)
    check("marker file present at the start: status 3, nothing starts, no result folder",
          rc == 3 and not box.launched() and not os.path.exists(box.results), (rc, err))

    # Design line 364: check the marker file "before each process".
    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="0.3", DUMMY_TOUCH="1")
    csv = box.csv("B6W")
    check("marker file appears between two processes: status 3, the first process ended, the second does not start",
          rc == 3 and csv.count("-- step ") == 1 and csv.count("M,dummy,1\n") == 1 and "-- killed" not in csv
          and len(box.launched()) == 2, (rc, err, csv))
    late = os.path.join(box.dir, "case%d" % (box.n + 1), "RUNNING")       # the marker path of the next case
    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", PS_TOUCH=late,
                           PATH=os.path.join(box.dir, "bin") + os.pathsep + os.environ["PATH"])
    launches = os.path.join(box.folder() or "", "launches.txt")
    check("marker file appears after the wait, directly before the launch: status 3, nothing starts",
          late == box.marker and os.path.exists(late) and rc == 3 and not box.launched() and "-- step" not in box.csv("B6W")
          and os.path.exists(launches) and open(launches).read().count("== B6W.csv idx ") == 1, (rc, err))

    p = box.start(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch()
    open(box.stopfile, "w").close()
    out, err = p.communicate(timeout=60)
    check("stop file appears during a process: status 5, '-- killed', no process left",
          up and p.returncode == 5 and "-- killed tag cpu2-p1 status 5" in box.csv("B6W") and box.none_alive(),
          (up, p.returncode, err))

    p = box.start(["B6W"], SESSION="1", STOP_AT="none", DUMMY_SLEEP="300")
    up = box.wait_launch()
    os.kill(p.pid, signal.SIGTERM)
    out, err = p.communicate(timeout=60)
    csv = box.csv("B6W")
    check("interrupted during a process: status 130, '-- killed' marks the cut process, no process left",
          up and p.returncode == 130 and box.none_alive()
          and re.search(r"^-- killed tag cpu2-p1 status 130 utc \S+$", csv, re.M) is not None
          and csv.count("-- step ") == 1, (up, p.returncode, err, csv))

    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT=utc(30))
    check("STOP_AT nearer than MARGIN: status 4, nothing starts",
          rc == 4 and not box.launched() and "less than 91 s away" in err, (rc, err))
    # MARGIN is the longest process of the step, rounded up to whole seconds, plus RESERVE. With the
    # test divisor 100 the longest B6W process is 0.156 s (1 s) and the longest P3G process 1.728 s (2 s).
    rc, out, err = box.run(["P3G"], SESSION="1", STOP_AT=utc(30))
    check("MARGIN follows the longest process of the step: P3G refuses at 92 s, not at 91 s",
          rc == 4 and not box.launched() and "less than 92 s away" in err and "longest process 2 s, MARGIN 92 s" in out,
          (rc, err, out))
    p = box.start(["B6W"], SESSION="1", STOP_AT=utc(45), RESERVE="0", DUMMY_SLEEP="300")
    up = box.wait_launch()
    out, err = p.communicate(timeout=120)
    check("STOP_AT reached during a process: status 4, '-- killed', no process left",
          up and p.returncode == 4 and "-- killed tag cpu2-p1 status 4" in box.csv("B6W") and box.none_alive(),
          (up, p.returncode, err))
    rc, out, err = box.run(["B6W"], SESSION="1")
    check("STOP_AT not set: status 2", rc == 2 and not box.launched(), (rc, err))

    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", DUMMY_EXIT="3")
    csv = box.csv("B6W")
    check("failing binary: status 1, '-- failed', the next process does not start",
          rc == 1 and "-- failed tag cpu2-p1 exit 3" in csv and csv.count("-- step ") == 1, (rc, err, csv))

    rc, out, err = box.run(["B6W"], SESSION="2", STOP_AT="none")
    check("session 2 without SESSION1_END: status 2, nothing starts",
          rc == 2 and "SESSION1_END" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["B6W"], SESSION="2", STOP_AT="none", SESSION1_END=utc(-3 * 3600 + 120))
    check("session 2 earlier than 3 h after SESSION1_END: refused with status 2, nothing starts",
          rc == 2 and "3 hours" in err and not box.launched() and not os.path.exists(box.results), (rc, err))
    # SESSION1_END must be a full UTC time. "date -d" alone reads a bare date as 00:00 and accepts
    # relative words, and each of these values would let session 2 start now.
    for value in ("garbage", time.strftime("%Y-%m-%d", time.gmtime()), "yesterday", "1", "@0", "-4 hours",
                  time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - 4 * 3600)),
                  "2026-13-45T25:00Z", "2026-02-30T00:00Z"):
        rc, out, err = box.run(["--from", "3", "B6W"], SESSION="2", STOP_AT="none", SESSION1_END=value)
        check("session 2 with SESSION1_END='%s': status 2, nothing starts" % value,
              rc == 2 and "bad SESSION1_END" in err and not box.launched() and not os.path.exists(box.results),
              (rc, err))
    rc, out, err = box.run(["--from", "3", "B6W"], SESSION="2", STOP_AT="none",
                           SESSION1_END=time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(time.time() - 3 * 3600 - 120)))
    check("session 2 with SESSION1_END as hours and minutes, more than 3 h ago: runs",
          rc == 0 and len(box.launched()) == 2, (rc, err))
    s1end = utc(-3 * 3600 - 60)
    rc, out, err = box.run(["--from", "3", "B6W"], SESSION="2", STOP_AT="none", SESSION1_END=s1end)
    env = open(os.path.join(box.folder(), "env.txt")).read() if box.folder() else ""
    check("session 2 later than 3 h after SESSION1_END: runs, folder -s2-, SESSION1_END in env.txt",
          rc == 0 and "bwx8-B6W-s2-" in (box.folder() or "") and ("SESSION1_END=" + s1end) in env
          and "-- step B6W session 2 idx 3 tag cpu2-p2 " in box.csv("B6W"), (rc, err))

    rc, out, err = box.run(["B6W"], STOP_AT="none")
    check("SESSION not set: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["B6"], SESSION="1", STOP_AT="none")
    check("unknown step: status 2", rc == 2 and not box.launched(), (rc, err))
    rc, out, err = box.run(["CM"], SESSION="1", STOP_AT="none")
    check("counter step without BWX_PMU_TYPE and BWX_EVENTS: status 2, nothing starts",
          rc == 2 and "BWX_PMU_TYPE" in err and not box.launched(), (rc, err))
    rc, out, err = box.run(["--from", "11", "CM"], SESSION="1", STOP_AT="none", BWX_PMU_TYPE="10", BWX_EVENTS="a=0x11")
    check("counter step with both settings: runs", rc == 0 and len(box.launched()) == 2, (rc, err))
    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", BWX8_SHA256="0" * 64)
    check("bwx8 differs from BWX8_SHA256: status 2, nothing starts", rc == 2 and not box.launched(), (rc, err))
    digest = subprocess.run(["sha256sum", box.bin], capture_output=True, text=True).stdout.split()[0]
    rc, out, err = box.run(["--from", "3", "B6W"], SESSION="1", STOP_AT="none", BWX8_SHA256=digest)
    check("bwx8 equals BWX8_SHA256: runs", rc == 0 and len(box.launched()) == 2, (rc, err))
    rc, out, err = box.run(["B6W"], SESSION="1", STOP_AT="none", BWX8_BIN=os.path.join(box.dir, "absent"))
    check("missing binary: status 2", rc == 2 and not box.launched(), (rc, err))
    os.rename(os.path.join(box.dir, "sched", "s1", "P3", "0004.plan"), os.path.join(box.dir, "moved.plan"))
    rc, out, err = box.run(["P3"], SESSION="1", STOP_AT="none")
    check("missing plan file: status 2 before the first launch", rc == 2 and not box.launched(), (rc, err))


def main():
    tmp = tempfile.mkdtemp(prefix="test_schedule8.")
    try:
        sched = schedule_checks(tmp)
        visit_checks(tmp)
        if "--no-run" in sys.argv[1:]:
            print("SKIP  the checks of run_bwx8.sh with a dummy bwx8 (--no-run)")
        else:
            run_checks(tmp, sched)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d check(s) failed" % len(FAILS) if FAILS else "all checks passed")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
