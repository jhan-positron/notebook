#!/usr/bin/env python3
"""make_report.py - builds the report page of the whole-chip read rerun at 7200 MT/s.

Output: crb/new-test-kernel/whole-chip-rerun-7200.html (one self-contained HTML file).
Input:  facts.json of this folder (records "intervals", meta.launches, meta.rerun).

Rules of this script:
- Every measured number of the page is computed here from the interval records. No measured number is typed.
- facts.json holds the bwx rates rounded to 0.001 GB/s. For the last digit at 0.01 GB/s the function val() sums the
  thread rows of the raw csv that a record names, and it stops when that sum does not round to the record value.
- Record counts are asserted. A wrong count stops the build.
- The computed values are compared with FACTS.md and with the "verdicts" of facts.json.
  A mismatch is printed in the self-check list, the page is not written, and the exit status is 1.
- The facts of the section "Machine state" are checked in the raw files (read only) before they are written.
- Every record must name its row in the raw csv file: the interval row with its rate (part A), or the interval row
  and the 120 thread rows after it (bwx12). A tooltip cites that row.
- Figure 1 is drawn in three layouts (940, 726 and 386 px wide). The style block shows the one that fits the window.
Python 3 standard library only. Edit this file, never the HTML.
"""
import html
import json
import math
import os
import re
import sys
import time
from decimal import Decimal, ROUND_HALF_UP

S = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
R = "/home/jhan/workspace/titan/cache-perf/crb/results"
OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"
EARLIER = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html"

BLUE, ORANGE = "#2a78d6", "#eb6834"          # old read kernel, load-only loop (validated, see palette check)
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BAND, BAND_EDGE, LINK = "#ebe9e0", "#b9b7ae", "#8d8c86"

CHECKS = []          # (ok, text)
PROSE = []           # visible prose outside tables, captions, word list and references (for the word count)


def stop(msg):
    sys.exit("make_report.py: STOP: " + msg)


def need(cond, msg):
    """Hard assertion. A wrong record count or a failed raw-file check stops the build."""
    if not cond:
        stop(msg)


def check(ok, text):
    CHECKS.append((bool(ok), text))


def grouped(label, start):
    """Replace the checks added since index start by one line: n of m equal, and the first mismatch."""
    sub = CHECKS[start:]
    del CHECKS[start:]
    bad = [t for ok, t in sub if not ok]
    check(not bad, f"{label}: {len(sub) - len(bad)} of {len(sub)} comparisons equal" + ("" if not bad else ". First mismatch: " + bad[0]))


def read_retry(path, parse, complete=lambda t: True):
    """Another agent rebuilds facts.json and FACTS.md from time to time. Retry a failed or partial read."""
    last = None
    for _ in range(10):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if complete(text):
                return parse(text)
            last = "file is not complete"
        except (OSError, ValueError) as e:
            last = e
        time.sleep(1.5)
    stop(f"cannot read {path}: {last}")


def lines_of(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


# ------------------------------------------------------------------ numbers
def D(x):
    return x if isinstance(x, Decimal) else Decimal(str(x))


def q(x, places="0.01"):
    return D(x).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def f2(x):
    return f"{q(x):.2f}"


def f1(x):
    return f"{q(x, '0.1'):.1f}"


def median(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def esc(s):
    return html.escape(str(s), quote=True)


_TROWS = {}
_FILES = {}


def file_lines(rec):
    """The lines of the csv file that a record names."""
    key = (rec["folder"], rec["file"])
    if key not in _FILES:
        _FILES[key] = lines_of(os.path.join(R, rec["folder"].replace("R/", "", 1), rec["file"]))
    return _FILES[key]


def t_rows(rec):
    """The T rows (one per thread) of the interval of a bwx record: (cpu, bytes, elapsed_s, t_start_s, t_end_s, line number).
    They must be the 120 lines directly after the I row that the record names."""
    key = (rec["folder"], rec["file"])
    if key not in _TROWS:
        d = {}
        for no, line in enumerate(file_lines(rec), 1):
            if line.startswith("T,"):
                p = line.split(",")
                need(len(p) == 13, f"{key}: a T row without 13 fields")
                d.setdefault((int(p[1]), int(p[2]), p[3]), []).append((int(p[5]), int(p[6]), float(p[7]), float(p[9]), float(p[10]), no))
        _TROWS[key] = d
    tl = _TROWS[key].get((rec["round"], rec["pos"], rec["kernel"]), [])
    need(len(tl) == 120, f"{key}: no 120 T rows for round {rec['round']} position {rec['pos']} {rec['kernel']}")
    need([t[5] for t in tl] == list(range(rec["line"] + 1, rec["line"] + 121)), f"{key}: the T rows are not the 120 lines after line {rec['line']}")
    return tl


def t_rows_block(rec):
    """The T rows of an interval record of the older runner bwx, as t_rows() returns them.
    A csv file of that runner holds several processes. So the rows are taken by their place:
    they must be the 120 lines directly after the I row that the record names, with its round, position and kernel."""
    fl = file_lines(rec)
    where = f"{rec['folder']}/{rec['file']} line {rec['line']}"
    tl = []
    for no in range(rec["line"] + 1, rec["line"] + 121):
        p = fl[no - 1].split(",")
        need(len(p) == 13 and p[0] == "T" and (int(p[1]), int(p[2]), p[3]) == (rec["round"], rec["pos"], rec["kernel"]),
             f"{where}: line {no} is not a T row of this interval")
        tl.append((int(p[5]), int(p[6]), float(p[7]), float(p[9]), float(p[10]), no))
    need(len(fl) == rec["line"] + 120 or not fl[rec["line"] + 120].startswith("T,"), f"{where}: more than 120 T rows follow the I row")
    return tl


def i_row_rate(rec):
    """The rate that the interval row (I row) of a bwx record prints, in GB/s. The row must be the row of this record."""
    p = file_lines(rec)[rec["line"] - 1].split(",")
    need(len(p) == 9 and p[0] == "I" and (int(p[1]), int(p[2]), p[3], int(p[5])) == (rec["round"], rec["pos"], rec["kernel"], 120),
         f"{rec['folder']}/{rec['file']} line {rec['line']}: not the I row of round {rec['round']} position {rec['pos']} {rec['kernel']}")
    return Decimal(p[8])


def file_process(rec):
    """Part A: the number of the process inside its csv file (1 = first), counted from the header lines ("-- ...") up to the record.
    The row of the record must hold the rate of the record."""
    fl = file_lines(rec)
    p = fl[rec["line"] - 1].split(",")
    need(len(p) == 10 and p[0] == rec["kernel"] and int(p[1]) == 120 and int(p[3]) == rec["interval"] and D(p[6]) == D(rec["GBps"]),
         f"{rec['folder']}/{rec['file']} line {rec['line']}: not the interval row of this record")
    return sum(1 for l in fl[:rec["line"]] if l.startswith("-- "))


def val(rec):
    """Rate of an interval record in GB/s.
    Part A: the record holds the value of the csv (2 decimals).
    bwx runners: facts.json holds the rate rounded to 0.001 GB/s, and FACTS.md rounds the unrounded value to 0.01 GB/s.
    For the same last digit this function sums the 120 T rows that the record names (the method of build_facts.py)
    and stops when the sum does not round to the value of the record."""
    if rec["part"] == "A":
        return D(rec["GBps"])
    if "_exact" not in rec:
        tl = t_rows(rec) if rec["binary"] == "bwx12" else t_rows_block(rec)
        tot =sum(b / e / 1e9 for c, b, e, *_ in tl if c < 64) + sum(b / e / 1e9 for c, b, e, *_ in tl if c >= 64)
        need(abs(round(tot, 3) - rec["GBps"]) < 1e-9, f"{rec['folder']}/{rec['file']} line {rec['line']}: sum of the T rows {tot:.6f} is not the record value {rec['GBps']}")
        rec["_exact"] = Decimal(repr(round(tot, 6)))
    return rec["_exact"]


class Rg:
    """Lowest-to-highest range of a list of interval records."""

    def __init__(self, recs):
        need(len(recs) > 0, "empty selection")
        self.recs = sorted(recs, key=lambda r: (r["launch_utc"], r["interval"]))
        self.v = [val(r) for r in self.recs]
        self.lo, self.hi, self.med = min(self.v), max(self.v), median(self.v)
        self.n = len(recs)
        self.procs = sorted({r["proc_key"] for r in recs})
        self.np = len(self.procs)

    def txt(self):
        return f"{f2(self.lo)} to {f2(self.hi)}"

    def overlaps(self, other):
        return self.lo <= other.hi and other.lo <= self.hi

    def nearest(self, other):
        """Distance of the nearest ends, + when self is the higher range. 0 when the ranges overlap."""
        if self.overlaps(other):
            return Decimal(0)
        return self.lo - other.hi if self.lo > other.hi else self.hi - other.lo

    def farthest(self, other):
        return max(self.hi - other.lo, other.hi - self.lo)


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}{'es' if word.endswith('s') else 's'}"


def signed(x):
    x = q(x)
    return "0" if x == 0 else f"{'+' if x > 0 else '-'}{abs(x):.2f}"


# ------------------------------------------------------------------ load the facts
def facts_complete(t):
    return "Output files of this sheet" in t and "## 7. Files" in t


FJ = read_retry(S + "/facts.json", json.loads)
FMD = read_retry(S + "/FACTS.md", lambda t: t, facts_complete)
IV = FJ["intervals"]
META = FJ["meta"]
RERUN = META["rerun"]
need(len(IV) == META["counts"]["intervals"], "facts.json: number of interval records differs from meta.counts")


def sel(**kw):
    out = []
    for r in IV:
        ok = True
        for k, v in kw.items():
            if callable(v):
                ok = v(r[k])
            elif isinstance(v, (list, tuple, set)):
                ok = r[k] in v
            else:
                ok = r[k] == v
            if not ok:
                break
        if ok:
            out.append(r)
    return out


def expect(recs, n, nproc, what):
    need(len(recs) == n, f"{what}: expected {n} interval records, found {len(recs)}")
    got = len({r["proc_key"] for r in recs})
    need(got == nproc, f"{what}: expected {nproc} processes, found {got}")
    need(all(r["threads"] == 120 for r in recs), f"{what}: a record is not a 120-thread interval")
    return recs


LPOOL = ("L-1", "L-2", "L-3", "L-4")
APOOL = ("A-1", "A-2", "A-3")

# part A, the repeat of the 2026-11-13 test
A_OLD = expect(sel(dataset="rerun-A", binary="bw_old", kernel="read"), 18, 6, "part A, bw_old read")
A_NEW = expect(sel(dataset="rerun-A", binary="bw_new", kernel="read"), 18, 6, "part A, bw_new read")
# part L and the rows of the same argument line
L_OLD = expect(sel(dataset="rerun-L", kernel="oldread", pos=0), 6, 3, "part L, oldread")
L_ASM = expect(sel(dataset="rerun-L", kernel="asmread", pos=1), 6, 3, "part L, asmread")
I_OLD = expect(sel(dataset="control-I", kernel="oldread", pos=0), 4, 2, "control I, oldread")
I_ASM = expect(sel(dataset="control-I", kernel="asmread", pos=1), 4, 2, "control I, asmread")
F_OLD = expect(sel(dataset="F72d12", kernel="oldread", pos=0), 2, 1, "F72d12, oldread")
F_ASM = expect(sel(dataset="F72d12", kernel="asmread", pos=1), 2, 1, "F72d12, asmread")
# part C
C_OLD = expect(sel(dataset="rerun-C", kernel="oldread"), 8, 4, "part C, oldread")
C_READ = expect(sel(dataset="rerun-C", kernel="read"), 8, 4, "part C, read")
C_ASM = expect(sel(dataset="rerun-C", kernel="asmread"), 8, 4, "part C, asmread")
C_READ_AO = expect([r for r in C_READ if r["kernel_before"] == "oldread"], 4, 2, "part C, read after oldread")
C_READ_AA = expect([r for r in C_READ if r["kernel_before"] == "asmread"], 4, 2, "part C, read after asmread")
C_ASM_AR = expect([r for r in C_ASM if r["kernel_before"] == "read"], 4, 2, "part C, asmread after read")
C_ASM_AO = expect([r for r in C_ASM if r["kernel_before"] == "oldread"], 2, 2, "part C, asmread after oldread")
C_ASM_FI = expect([r for r in C_ASM if r["kernel_before"].startswith("none")], 2, 2, "part C, asmread first interval")
# 8000 MT/s rows
B_L_OLD = {d: sel(dataset=d, kernel="oldread", pos=0) for d in LPOOL}
B_L_ASM = {d: sel(dataset=d, kernel="asmread", pos=1) for d in LPOOL}
for d, n, p in (("L-1", 2, 1), ("L-2", 4, 2), ("L-3", 2, 1), ("L-4", 3, 3)):
    expect(B_L_OLD[d], n, p, f"{d}, oldread at position 0")
    expect(B_L_ASM[d], n, p, f"{d}, asmread at position 1")
P_L_OLD = expect([r for d in LPOOL for r in B_L_OLD[d]], 11, 7, "pool L-1 to L-4, oldread")
P_L_ASM = expect([r for d in LPOOL for r in B_L_ASM[d]], 11, 7, "pool L-1 to L-4, asmread")
B_A_OLD = {d: sel(dataset=d, binary="bw_old", kernel="read") for d in APOOL}
B_A_NEW = {d: sel(dataset=d, binary="bw_new", kernel="read") for d in ("A-1", "A-2")}
for d, n, p in (("A-1", 6, 2), ("A-2", 6, 2), ("A-3", 9, 3)):
    expect(B_A_OLD[d], n, p, f"{d}, bw_old read")
for d in ("A-1", "A-2"):
    expect(B_A_NEW[d], 6, 2, f"{d}, bw_new read")
P_A_OLD = expect([r for d in APOOL for r in B_A_OLD[d]], 21, 7, "pool A-1 to A-3, bw_old read")

USED = (A_OLD + A_NEW + L_OLD + L_ASM + I_OLD + I_ASM + F_OLD + F_ASM + C_OLD + C_READ + C_ASM
        + P_L_OLD + P_L_ASM + P_A_OLD + B_A_NEW["A-1"] + B_A_NEW["A-2"])
need(all(r["modules"] == 12 for r in USED), "a record used on the page is not a 12-module run")
SEVEN = [r for r in USED if r["speed_MTps"] == 7200]
EIGHT = [r for r in USED if r["speed_MTps"] == 8000]
need(len(SEVEN) + len(EIGHT) == len(USED), "a record has another memory speed")
need({r["boot"] for r in SEVEN} == {RERUN["boot_id"]}, "the 7200 MT/s records are not from one boot")
need(len({r["boot"] for r in EIGHT}) == 1, "the 8000 MT/s records are not from one boot")
need({r["dataset"] for r in SEVEN} == {"rerun-A", "rerun-L", "rerun-C", "control-I", "F72d12"}, "7200 MT/s datasets")
need(all(r["min_ms"] == 500 and r["stop"] == "whole pass" for r in USED if r["part"] == "A"), "part A method")
need(all(r["stop"] == "common" for r in USED if r["part"] != "A"), "bwx12 rows: stop rule")
need(all(r["min_ms"] == 6000 for r in USED if r["dataset"] in ("rerun-L", "rerun-C", "control-I", "F72d12", "L-1")),
     "6 s rows")
need(all(r["min_ms"] == 4000 for r in USED if r["dataset"] in ("L-2", "L-3", "L-4")), "4 s rows")
# Rows of the older runner bwx (another binary, not like-for-like). The rules file names them as the reference of part C
# (rule V2 point 4: folders B7 and C3, tags common-6000-*). The page shows them in one note under Table 2 and gives no wording from them.
BWX_POOL = ("B7a", "B7b", "C3a", "C3b")
X_READ_AO = expect(sel(dataset=BWX_POOL, kernel="read", pos=1), 48, 24, "runner bwx, read at position 1")
X_READ_AA = expect(sel(dataset=BWX_POOL, kernel="read", pos=6), 48, 24, "runner bwx, read at position 6")
X_ASM_AR = expect(sel(dataset=BWX_POOL, kernel="asmread", pos=2), 48, 24, "runner bwx, asmread at position 2")
X_LOADS = expect(sel(dataset=BWX_POOL, kernel=("read", "asmread")), 192, 24, "runner bwx, all intervals of read and asmread")
need({r["kernel_before"] for r in X_READ_AO} == {"oldread"} and {r["kernel_before"] for r in X_READ_AA} == {"asmread"}
     and {r["kernel_before"] for r in X_ASM_AR} == {"read"}, "runner bwx: the kernel directly before is not as rule V2 point 4 states")
need(all(r["tag"].startswith("common-6000-") for r in X_LOADS), "runner bwx: a row has another tag than common-6000-*")
# four more processes of the same runner with the reverse kernel order (two B5 folders): higher values at 8000 MT/s
X_REV_READ = expect(sel(dataset=("B5a-rev", "B5b-rev"), kernel="read"), 4, 4, "runner bwx, reverse order, read")
X_REV_ASM = expect(sel(dataset=("B5a-rev", "B5b-rev"), kernel="asmread"), 4, 4, "runner bwx, reverse order, asmread")
OTHER = X_LOADS + X_REV_READ + X_REV_ASM
need(all(r["binary"] == "bwx" and r["modules"] == 12 and r["speed_MTps"] == 8000 and r["stop"] == "common" and r["min_ms"] == 6000 for r in OTHER),
     "runner bwx: a row is not a 6 s common-stop run of bwx at 8000 MT/s with 12 modules")
need({r["boot"] for r in OTHER} == {r["boot"] for r in EIGHT}, "runner bwx: a row is not from the boot of the other 8000 MT/s rows")
check(True, f"record counts: {len(USED)} interval records used, all 120 threads, 12 modules; "
            f"7200 MT/s records from 1 boot, 8000 MT/s records from 1 boot; {len(OTHER)} more records of runner bwx (same 8000 MT/s boot) for one note under Table 2")
# bwx12 and bwx: the page value is the sum of the thread rows. The interval row of the csv prints a rate too: how far the two differ
BWX_USED = [r for r in USED if r["part"] != "A"]
IROW_DIFF = [abs(q(val(r)) - i_row_rate(r)) for r in BWX_USED]
IROW_MAX = max(IROW_DIFF)
need(IROW_MAX <= Decimal("0.02"), f"bwx12: an interval row differs from the sum of its thread rows by {IROW_MAX} GB/s")
IROW_MAX_X = max(abs(q(val(r)) - i_row_rate(r)) for r in OTHER)
need(IROW_MAX_X <= Decimal("0.02"), f"runner bwx: an interval row differs from the sum of its thread rows by {IROW_MAX_X} GB/s")
# part A: the process number inside the file. facts.json counts the processes of rows A-1, A-2 and of the rerun in the same way
A_USED = [r for r in USED if r["part"] == "A"]
for r in A_USED:
    r["_fproc"] = file_process(r)
need(all(r["_fproc"] == r["process"] for r in A_USED if r["dataset"] != "A-3"), "part A: a process number of facts.json is not the number of the process in its file")
check(True, f"raw csv rows: {len(BWX_USED)} bwx12 records and {len(OTHER)} bwx records name their interval row and the 120 thread rows after it "
            f"(printed rate and sum of the thread rows differ by at most {f2(IROW_MAX)} GB/s for bwx12 and {f2(IROW_MAX_X)} GB/s for bwx); "
            f"{len(A_USED)} part A records name the row with their rate")


SUM_NOTE = "The rate is the sum of the 120 thread rows after it"


def src(recs):
    """Source text for a tooltip: file and line numbers. For bwx12 the lines are interval rows, and the rate is the sum of the thread rows."""
    by = {}
    for r in recs:
        by.setdefault(f"{r['folder']}/{r['file']}", []).append(r["line"])
    bwx = recs[0]["part"] != "A"
    need(all((r["part"] != "A") == bwx for r in recs), "src: part A and bwx12 records in one source text")

    def one(p, ls):
        many = len(ls) > 1
        nums = ", ".join(str(x) for x in sorted(ls))
        return f"{p}, interval row{'s' if many else ''} in line{'s' if many else ''} {nums}" if bwx else f"{p} line{'s' if many else ''} {nums}"
    out = " and ".join(one(p, ls) for p, ls in by.items())
    if bwx:
        out += ". " + (SUM_NOTE if len(recs) == 1 else "Each rate is the sum of the 120 thread rows after its interval row")
    return out


def hm(utc, date=False):
    return (utc[:10] + " " if date else "") + utc[11:16] + " UTC"


def n7200(recs, pairs=None):
    """n as intervals / processes / sessions / boots for records of the 7200 MT/s boot."""
    ds = {r["dataset"] for r in recs}
    np_ = len({r["proc_key"] for r in recs})
    first = plural(pairs, "pair") if pairs is not None else plural(len(recs), "interval")
    if ds <= {"control-I", "F72d12"}:
        sess = "no session"
    else:
        named = sorted({r["session"] for r in recs if r["session"] is not None})
        extra = len({r["proc_key"] for r in recs if r["session"] is None})
        if extra == 0:
            sess = plural(len(named), "session")
            if len(named) < 3:
                sess = ("session " if len(named) == 1 else "sessions ") + " and ".join(str(s) for s in named)
        else:
            sess = (f"{plural(len(named), 'session')}" if len(named) != 1 else f"session {named[0]}") \
                   + f" and {extra} extra process"
    return f"{first} / {plural(np_, 'process')} / {sess} / 1 boot"


def n8000(recs, pairs=None):
    first = plural(pairs, "pair") if pairs is not None else plural(len(recs), "interval")
    return f"{first} / {plural(len({r['proc_key'] for r in recs}), 'process')} / 1 boot"


# ------------------------------------------------------------------ Q1: drops
def pairs_in_process(olds, news):
    """Pairs of (old, load-only) intervals of the same process and round."""
    out = []
    for n in sorted(news, key=lambda r: (r["launch_utc"], r["round"])):
        o = [x for x in olds if x["proc_key"] == n["proc_key"] and x["round"] == n["round"]]
        need(len(o) == 1, "pair: no single old-kernel interval for a load-only interval")
        out.append((o[0], n))
    return out


def drop(old, new):
    return (1 - D(new) / D(old)) * 100


def drops_of(pairs):
    return [drop(val(o), val(n)) for o, n in pairs]


def drop_txt(ds):
    lo, hi = f1(min(ds)), f1(max(ds))
    return f"{lo} %" if lo == hi else f"{lo} % to {hi} %"


Q1 = {}
Q1["C_ao"] = dict(pairs=pairs_in_process(C_OLD, C_READ_AO))
Q1["C_aa"] = dict(pairs=pairs_in_process(C_OLD, C_READ_AA))
Q1["L"] = dict(pairs=pairs_in_process(L_OLD, L_ASM))
Q1["I"] = dict(pairs=pairs_in_process(I_OLD, I_ASM))
Q1["F"] = dict(pairs=pairs_in_process(F_OLD, F_ASM))
Q1["L1"] = dict(pairs=pairs_in_process(B_L_OLD["L-1"], B_L_ASM["L-1"]))
for k, npairs in (("C_ao", 4), ("C_aa", 4), ("L", 6), ("I", 4), ("F", 2), ("L1", 2)):
    need(len(Q1[k]["pairs"]) == npairs, f"Q1 {k}: expected {npairs} pairs")
    Q1[k]["drops"] = drops_of(Q1[k]["pairs"])
    Q1[k]["old"] = Rg([o for o, _ in Q1[k]["pairs"]])
    Q1[k]["new"] = Rg([n for _, n in Q1[k]["pairs"]])


def a_pair(olds, news, rnd):
    o = Rg([r for r in olds if r["round"] == rnd])
    n = Rg([r for r in news if r["round"] == rnd])
    need(o.n == 3 and n.n == 3 and o.np == 1 and n.np == 1, "part A pair: expected 3 intervals of 1 process per kernel")
    return dict(old=o, new=n, drop=drop(o.med, n.med), round=rnd)


A_PAIRS = {}       # (session, round) -> pair of process medians
for s_ in (1, 2, 3):
    for rnd in (1, 2):
        A_PAIRS[(s_, rnd)] = a_pair([r for r in A_OLD if r["session"] == s_], [r for r in A_NEW if r["session"] == s_], rnd)
A8_PAIRS = {(d, rnd): a_pair(B_A_OLD[d], B_A_NEW[d], rnd) for d in ("A-1", "A-2") for rnd in (1, 2)}
Q1["A"] = dict(drops=[p["drop"] for p in A_PAIRS.values()])
Q1["A8"] = dict(drops=[p["drop"] for p in A8_PAIRS.values()])
SAME_LINE_DROPS = Q1["L"]["drops"] + Q1["I"]["drops"] + Q1["F"]["drops"]     # the like.spec line in the 7200 MT/s boot
ALL_7200_DROPS = Q1["C_ao"]["drops"] + Q1["C_aa"]["drops"] + SAME_LINE_DROPS + Q1["A"]["drops"]
need(all(d > 0 for d in ALL_7200_DROPS), "a load-only interval is not below the old read kernel")

# ------------------------------------------------------------------ Q2: ranges
rA_old, rPA_old = Rg(A_OLD), Rg(P_A_OLD)
rL_old, rL_asm = Rg(L_OLD), Rg(L_ASM)
rC_old, rI_old, rI_asm, rF_old, rF_asm = Rg(C_OLD), Rg(I_OLD), Rg(I_ASM), Rg(F_OLD), Rg(F_ASM)
rPL_old, rPL_asm = Rg(P_L_OLD), Rg(P_L_ASM)
rL1_asm = Rg(B_L_ASM["L-1"])
rC_asm_ao = Rg(C_ASM_AO)
rC_read_ao, rC_read_aa = Rg(C_READ_AO), Rg(C_READ_AA)
WORD_SAME = "no difference seen"
WORD_DIFF = "differs between the 8000 MT/s boot and the 7200 MT/s boot"
need(FJ["verdicts"]["rule_wordings"]["same"] == WORD_SAME and FJ["verdicts"]["rule_wordings"]["differs"] == WORD_DIFF,
     "the fixed wordings differ from facts.json")


def width_pct(rg):
    """Width of a range in percent of its lower end: the size that a 'no difference seen' test cannot exclude (est.)."""
    return (rg.hi - rg.lo) / rg.lo * 100


def wording(r7, r8):
    return WORD_SAME if r7.overlaps(r8) else WORD_DIFF


# old read kernel
need(rA_old.overlaps(rPA_old) and rC_old.overlaps(rPL_old) and rF_old.overlaps(rPL_old) and rI_old.overlaps(rPL_old),
     "old read: an expected overlap is missing")
need(not rL_old.overlaps(rPL_old) and rL_old.hi < rPL_old.lo, "old read, part L: expected below the 8000 MT/s pool")
L_OLD_NEAR = rL_old.nearest(rPL_old)                       # negative: part L is lower
L_OLD_MED = rL_old.med - rPL_old.med
L_OLD_NEAR_PCT = abs(L_OLD_NEAR) / rPL_old.lo * 100        # percent of the lower end of the 8000 MT/s range
L_OLD_MED_PCT = abs(L_OLD_MED) / rPL_old.med * 100         # percent of the 8000 MT/s median
# load-only loop
need(not rL_asm.overlaps(rPL_asm) and rL_asm.lo > rPL_asm.hi, "asmread, part L: expected above the 8000 MT/s pool")
need(rF_asm.overlaps(rPL_asm), "asmread, F72d12: expected inside the 8000 MT/s pool")
need(rPL_asm.lo <= rF_asm.lo and rF_asm.hi <= rPL_asm.hi, "asmread, F72d12: expected inside the 8000 MT/s pool")
need(not rI_asm.overlaps(rPL_asm) and rI_asm.lo > rPL_asm.hi, "asmread, control I: expected above the 8000 MT/s pool")
need(not rC_asm_ao.overlaps(rPL_asm), "asmread after oldread, part C: expected above the 8000 MT/s pool")
need(not rF_asm.overlaps(rL_asm) and not rF_asm.overlaps(rI_asm) and not rI_asm.overlaps(rL_asm),
     "the three visits of the 7200 MT/s boot overlap")
VISIT_LO, VISIT_HI = min(rF_asm.lo, rL_asm.lo, rI_asm.lo), max(rF_asm.hi, rL_asm.hi, rI_asm.hi)
VISIT_OLD_LO, VISIT_OLD_HI = min(rF_old.lo, rL_old.lo, rI_old.lo), max(rF_old.hi, rL_old.hi, rI_old.hi)
DIST = {  # the same kind of distance on both sides: part L against the 8000 MT/s pool, part L against F72d12
    "nearest": (rL_asm.nearest(rPL_asm), rL_asm.nearest(rF_asm)),
    "medians": (rL_asm.med - rPL_asm.med, rL_asm.med - rF_asm.med),
    "farthest": (rL_asm.farthest(rPL_asm), rL_asm.farthest(rF_asm)),
}
# part A, new read kernel: session 1 against the 8000 MT/s processes of the same round (rule V3)
A_V3 = {}
for rnd in (1, 2):
    r7 = Rg([r for r in A_NEW if r["session"] == 1 and r["round"] == rnd])
    r8 = Rg([r for d in ("A-1", "A-2") for r in B_A_NEW[d] if r["round"] == rnd])
    need(r7.n == 3 and r7.np == 1 and r8.n == 6 and r8.np == 2, "part A, rule V3: record counts")
    need(not r7.overlaps(r8) and r7.lo > r8.hi, "part A, session 1: expected above the 8000 MT/s range of the round")
    A_V3[rnd] = dict(r7=r7, r8=r8, near=r7.nearest(r8),
                     p7=sorted({r["passes"] for r in r7.recs}), p8=sorted(r["passes"] for r in r8.recs))
need(all(len(A_V3[rnd]["p7"]) == 1 for rnd in (1, 2)), "part A, session 1, bw_new read: more than one pass count in a round")

# the pool L-1 to L-4 without the interval that holds the lowest asmread value (machine state section)
LOWEST_ASM = min(P_L_ASM, key=val)
rPL_asm_wo = Rg([r for r in P_L_ASM if r is not LOWEST_ASM])
need(rL_asm.lo > rPL_asm_wo.hi, "part L does not lie above the pool without its lowest interval")

# part A, old read kernel: the 7200 MT/s range is wider than the 8000 MT/s range, and some of its intervals lie outside that range
A_OLD_BELOW = [r for r in A_OLD if val(r) < rPA_old.lo]
A_OLD_ABOVE = [r for r in A_OLD if val(r) > rPA_old.hi]
A_OLD_W7, A_OLD_W8 = rA_old.hi - rA_old.lo, rPA_old.hi - rPA_old.lo
need(A_OLD_BELOW and A_OLD_ABOVE and A_OLD_W7 > A_OLD_W8, "part A, old read: the 7200 MT/s range is not wider than the 8000 MT/s range on both sides")


def one_process(recs):
    """'session s, round r' when the records are all intervals of one process of part A, else a stop."""
    key = {(r["session"], r["round"], r["proc_key"]) for r in recs}
    need(len(key) == 1 and len(recs) == 3, "part A, old read: the intervals outside the 8000 MT/s range are not the 3 intervals of one process")
    s_, rnd, _ = next(iter(key))
    return f"session {s_}, round {rnd}"


# rows of runner bwx (another binary): ranges with the same kernel directly before, for the note under Table 2
need({r["pos"] for r in C_ASM_AR} == {2} and {r["file"] for r in C_ASM_AR} == {"cfwd.csv"}, "part C, asmread after read: not position 2 of cfwd")
rC_asm_ar = Rg(C_ASM_AR)
rX_read_ao, rX_read_aa, rX_asm_ar = Rg(X_READ_AO), Rg(X_READ_AA), Rg(X_ASM_AR)
X_PAIRS = [(rC_read_ao, rX_read_ao), (rC_read_aa, rX_read_aa), (rC_asm_ar, rX_asm_ar)]
need(all(c.lo > x.hi for c, x in X_PAIRS), "part C: a group does not lie above the bwx rows with the same kernel directly before")
X_ABOVE = [c.nearest(x) for c, x in X_PAIRS]
X_MAX_READ = max(val(r) for r in X_LOADS if r["kernel"] == "read")
X_MAX_ASM = max(val(r) for r in X_LOADS if r["kernel"] == "asmread")
need(X_MAX_READ == max(rX_read_ao.hi, rX_read_aa.hi) and X_MAX_ASM == rX_asm_ar.hi, "runner bwx: the highest read or asmread value is not in the three ranges used")
X_REV_MAX_READ, X_REV_MAX_ASM = max(val(r) for r in X_REV_READ), max(val(r) for r in X_REV_ASM)
need(X_REV_MAX_READ > X_MAX_READ and X_REV_MAX_ASM > X_MAX_ASM, "runner bwx: the reverse-order processes do not hold higher values")
need(rC_read_ao.lo <= X_REV_MAX_READ <= rC_read_ao.hi and rC_read_aa.lo <= X_REV_MAX_READ <= rC_read_aa.hi,
     "runner bwx, reverse order: the highest read value is not inside both read ranges of part C")
need(rL_asm.lo <= X_REV_MAX_ASM <= rL_asm.hi, "runner bwx, reverse order: the highest asmread value is not inside the asmread range of part L")

# ------------------------------------------------------------------ cross-check with FACTS.md and facts.json verdicts
def md_sections(md):
    secs, cur = {}, None
    for line in md.splitlines():
        m = re.match(r"^#{2,3} (.*)$", line)
        if m:
            k = re.match(r"^(\d+(?:\.\d+)?)[. ]", m.group(1))
            cur = k.group(1) if k else "#" + m.group(1)
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(line)
    return {k: "\n".join(v) for k, v in secs.items()}


def md_tables(text):
    tables, cur = [], None
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cur is None:
                cur = {"head": cells, "rows": []}
                tables.append(cur)
            elif set("".join(cells)) <= set("-: "):
                continue
            else:
                cur["rows"].append(dict(zip(cur["head"], cells)))
        else:
            cur = None
    return tables


SEC = md_sections(FMD)
for k_ in ("0", "3.1", "3.2", "3.3", "3.4", "4.2", "4.3", "4.4", "4.5", "4.6", "4.9"):
    need(k_ in SEC and SEC[k_].strip(), f"FACTS.md: section {k_} not found")
NUM = r"[-+]?\d+(?:\.\d+)?"


def col(row, start):
    ks = [k for k in row if k.startswith(start)]
    need(len(ks) == 1, f"FACTS.md table: no single column that starts with '{start}'")
    return row[ks[0]]


def facts_row(sec, where, what):
    """The first table row of a FACTS.md section for which where(row) is true."""
    for t in md_tables(SEC[sec]):
        for row in t["rows"]:
            try:
                if where(row):
                    return row
            except KeyError:
                continue
    stop(f"FACTS.md section {sec}: row not found: {what}")


def rng_of(cell):
    m = re.search(rf"({NUM}) to ({NUM})", cell)
    need(m, f"FACTS.md: no range in cell '{cell}'")
    return Decimal(m.group(1)), Decimal(m.group(2))


def near(a, b, tol):
    return abs(D(a) - D(b)) <= Decimal(tol)


def xc_range(label, rg_lo, rg_hi, cell, tol="0.01", unit="GB/s", fmt=f2):
    lo, hi = rng_of(cell)
    check(near(q(rg_lo, tol), lo, tol) and near(q(rg_hi, tol), hi, tol),
          f"{label}: computed {fmt(rg_lo)} to {fmt(rg_hi)} {unit}, FACTS.md {lo} to {hi} {unit}")


def xc_val(label, mine, cell, tol="0.01", unit="GB/s", fmt=f2):
    m = re.search(NUM, cell)
    need(m, f"FACTS.md: no number in cell '{cell}'")
    theirs = Decimal(m.group(0))
    check(near(q(mine, tol), theirs, tol), f"{label}: computed {fmt(mine)} {unit}, FACTS.md {theirs} {unit}")


def xc_text(label, sec, value, unit, tol="0.01", fmt=f2):
    """A number with this unit, equal within the tolerance, stands in the text of a FACTS.md section."""
    found = [Decimal(x) for x in re.findall(rf"({NUM}) ?{re.escape(unit)}", SEC[sec])]
    check(any(near(q(abs(D(value)), tol), x, tol) for x in found),
          f"{label}: computed {fmt(abs(D(value)))} {unit}, present in FACTS.md section {sec}")


def xc_text_range(label, sec, lo, hi, unit_mid, tol, fmt):
    found = re.findall(rf"({NUM}){re.escape(unit_mid)} to ({NUM})", SEC[sec])
    check(any(near(q(lo, tol), Decimal(a), tol) and near(q(hi, tol), Decimal(b), tol) for a, b in found),
          f"{label}: computed {fmt(lo)} to {fmt(hi)}, present in FACTS.md section {sec}")


def xc_drops(label, ds, row):
    lo, hi = Decimal(col(row, "Smallest drop")), Decimal(col(row, "Largest drop"))
    check(near(q(min(ds), "0.1"), lo, "0.1") and near(q(max(ds), "0.1"), hi, "0.1"),
          f"{label}: computed {f1(min(ds))} % to {f1(max(ds))} %, FACTS.md {lo} % to {hi} %")


# Q1 (headline values)
T34 = lambda part, frag: facts_row("3.4", lambda r: r["Part"].startswith(part) and frag in r["Pair"], f"{part} {frag}")
xc_drops("Q1 part C, read directly after oldread", Q1["C_ao"]["drops"], T34("C", "`read` (new read kernel) directly after `oldread`"))
xc_drops("Q1 part C, read directly after asmread", Q1["C_aa"]["drops"], T34("C", "`read` (new read kernel) directly after `asmread`"))
xc_drops("Q1 part L, asmread against oldread", Q1["L"]["drops"], T34("L", "asmread"))
xc_drops("Q1 part A, process medians", Q1["A"]["drops"], T34("A", "bw_new"))
xc_drops("Q1 control I", Q1["I"]["drops"], T34("I (control", "asmread"))
xc_drops("Q1 F72d12", Q1["F"]["drops"], T34("F72d12", "asmread"))
G33 = lambda g: facts_row("3.3", lambda r: r["Group"].startswith(g), g)
xc_range("part C, read after oldread", rC_read_ao.lo, rC_read_ao.hi, col(G33("read after oldread"), "Min to max"))
xc_range("part C, read after asmread", rC_read_aa.lo, rC_read_aa.hi, col(G33("read after asmread"), "Min to max"))
xc_range("part C, oldread", rC_old.lo, rC_old.hi, col(G33("oldread, all positions"), "Min to max"))
for key_, ds in (("C_ao", Q1["C_ao"]["drops"]), ("C_aa", Q1["C_aa"]["drops"]), ("L", Q1["L"]["drops"]), ("A", Q1["A"]["drops"])):
    xc_text_range(f"Q1 drop {key_} in the Short version of FACTS.md", "0", min(ds), max(ds), " %", "0.1", f1)
g0 = len(CHECKS)
for (s_, rnd), p in A_PAIRS.items():
    row = facts_row("3.1", lambda r, s_=s_, rnd=rnd: r["Session"] == str(s_) and r["Round"] == str(rnd) and "New below old, %" in r,
                    f"session {s_} round {rnd}")
    xc_val(f"part A session {s_} round {rnd}, median bw_old read", p["old"].med, row["bw_old read, median GB/s"])
    xc_val(f"part A session {s_} round {rnd}, median bw_new read", p["new"].med, row["bw_new read, median GB/s"])
    xc_val(f"part A session {s_} round {rnd}, new below old", p["drop"], row["New below old, %"], "0.1", "%", f1)
grouped("FACTS.md section 3.1, part A per session and round: medians of bw_old read and bw_new read (0.01 GB/s) and the drop (0.1 %)", g0)
g0 = len(CHECKS)
for o, n in Q1["L"]["pairs"] + Q1["I"]["pairs"] + Q1["F"]["pairs"]:
    tag = n["tag"] if n["dataset"] != "F72d12" else "F72d12"
    row = facts_row("3.2", lambda r, tag=tag, n=n: r["Folder tag or row"] == tag and r["Round"] == str(n["round"]), f"{tag} round {n['round']}")
    xc_val(f"{tag} round {n['round']}, oldread", val(o), row["oldread, GB/s"])
    xc_val(f"{tag} round {n['round']}, asmread", val(n), row["asmread, GB/s"])
    xc_val(f"{tag} round {n['round']}, asmread below oldread", drop(val(o), val(n)), row["asmread below oldread, %"], "0.1", "%", f1)
grouped("FACTS.md section 3.2, part L, control I and F72d12 per process and round: oldread and asmread (0.01 GB/s) and the drop (0.1 %)", g0)

# Q2 old read kernel (headline values)
R42 = lambda name: facts_row("4.2", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)
C42 = lambda a, b: facts_row("4.2", lambda r: r["7200 MT/s row"].startswith(a) and r["8000 MT/s range used"].startswith(b), f"{a} / {b}")
xc_range("Q2 old read, part A", rA_old.lo, rA_old.hi, R42("part A, sessions 1 to 3")["Min to max, GB/s"])
xc_range("Q2 old read, pool A-1 to A-3", rPA_old.lo, rPA_old.hi, R42("pool A-1 to A-3")["Min to max, GB/s"])
xc_range("Q2 old read, part L", rL_old.lo, rL_old.hi, R42("part L (T72L1 to T72L3)")["Min to max, GB/s"])
xc_range("Q2 old read, pool L-1 to L-4", rPL_old.lo, rPL_old.hi, R42("pool L-1 to L-4")["Min to max, GB/s"])
xc_range("Q2 old read, part C", rC_old.lo, rC_old.hi, R42("part C, all oldread intervals")["Min to max, GB/s"])
xc_range("Q2 old read, F72d12", rF_old.lo, rF_old.hi, R42("F72d12")["Min to max, GB/s"])
xc_range("Q2 old read, control I", rI_old.lo, rI_old.hi, R42("control I")["Min to max, GB/s"])
xc_val("Q2 old read, median of part L", rL_old.med, R42("part L (T72L1 to T72L3)")["Median, GB/s"])
xc_val("Q2 old read, median of pool L-1 to L-4", rPL_old.med, R42("pool L-1 to L-4")["Median, GB/s"])
row = C42("part A, sessions 1 to 3", "pool A-1 to A-3")
check(WORD_SAME in col(row, "Wording") and wording(rA_old, rPA_old) == WORD_SAME, f'Q2 old read, part A: wording "{WORD_SAME}" computed and in FACTS.md')
xc_val("Q2 old read, part A: size the test cannot exclude (est.)", width_pct(rPA_old), col(row, "Width of the 8000 MT/s range"), "0.1", "%", f1)
row = C42("part C, all oldread intervals", "pool L-1 to L-4 (position 0)")
check(WORD_SAME in col(row, "Wording") and wording(rC_old, rPL_old) == WORD_SAME, f'Q2 old read, part C: wording "{WORD_SAME}" computed and in FACTS.md')
xc_val("Q2 old read, part C: size the test cannot exclude (est.)", width_pct(rPL_old), col(row, "Width of the 8000 MT/s range"), "0.1", "%", f1)
row = C42("part L", "pool L-1 to L-4")
check(WORD_DIFF in col(row, "Wording") and wording(rL_old, rPL_old) == WORD_DIFF, f'Q2 old read, part L: wording "{WORD_DIFF}" computed and in FACTS.md')
xc_val("Q2 old read, part L: distance of the nearest ends", L_OLD_NEAR, col(row, "Distance of the nearest ends"))
xc_text("Q2 old read, part L: distance of the medians", "4.9", L_OLD_MED, "GB/s")
xc_text("Q2 old read, part L: nearest ends in percent", "4.9", L_OLD_NEAR_PCT, "%", "0.1", f1)
xc_text("Q2 old read, part L: medians in percent", "4.9", L_OLD_MED_PCT, "%", "0.1", f1)
for nm, rg in (("F72d12", rF_old), ("control I", rI_old)):
    row = C42(nm, "pool L-1 to L-4")
    check(col(row, "Overlap") == "yes" and rg.overlaps(rPL_old), f"Q2 old read, {nm}: overlaps the 8000 MT/s pool, computed and in FACTS.md")

# Q2 load-only loop (headline values)
R44 = lambda name: facts_row("4.4", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)
C44 = lambda a, b: facts_row("4.4", lambda r: r["7200 MT/s row"].startswith(a) and r["8000 MT/s range used"] == b, f"{a} / {b}")
xc_range("Q2 load-only, part L asmread", rL_asm.lo, rL_asm.hi, R44("part L (T72L1 to T72L3)")["Min to max, GB/s"])
xc_range("Q2 load-only, pool L-1 to L-4 asmread", rPL_asm.lo, rPL_asm.hi, R44("pool L-1 to L-4")["Min to max, GB/s"])
xc_range("Q2 load-only, F72d12 asmread", rF_asm.lo, rF_asm.hi, R44("F72d12")["Min to max, GB/s"])
xc_range("Q2 load-only, control I asmread", rI_asm.lo, rI_asm.hi, R44("control I")["Min to max, GB/s"])
row = C44("part L", "pool L-1 to L-4")
check(WORD_DIFF in col(row, "Wording") and wording(rL_asm, rPL_asm) == WORD_DIFF, f'Q2 load-only, part L: wording "{WORD_DIFF}" computed and in FACTS.md')
xc_val("Q2 load-only, part L: distance of the nearest ends", DIST["nearest"][0], col(row, "Distance of the nearest ends"))
xc_val("Q2 load-only, F72d12 above L-1 alone", rF_asm.nearest(rL1_asm), col(C44("F72d12", "L-1 alone"), "Distance of the nearest ends"))
check(col(C44("F72d12", "pool L-1 to L-4"), "Overlap") == "yes", "Q2 load-only, F72d12: inside the 8000 MT/s pool range, computed and in FACTS.md")
xc_val("Q2 load-only, control I above the pool", rI_asm.nearest(rPL_asm), col(C44("control I", "pool L-1 to L-4"), "Distance of the nearest ends"))
for rnd in (1, 2):
    row = facts_row("4.3", lambda r, rnd=rnd: r["Binary and kernel"] == "bw_new read" and r["Round"] == str(rnd) and "Wording by rule V3" in r, f"bw_new read round {rnd}")
    v = A_V3[rnd]
    xc_range(f"Q2 part A, bw_new read, round {rnd}: 8000 MT/s range", v["r8"].lo, v["r8"].hi, row["8000 MT/s range of the round, GB/s"])
    cell7 = [Decimal(x) for x in re.findall(r"(\d+\.\d+) \(\d+\)", row["7200 MT/s, session 1"])]
    check(len(cell7) == 3 and near(min(cell7), q(v["r7"].lo), "0.01") and near(max(cell7), q(v["r7"].hi), "0.01"),
          f"Q2 part A, bw_new read, round {rnd}: session 1 computed {v['r7'].txt()} GB/s, FACTS.md {min(cell7)} to {max(cell7)} GB/s")
    check(row["Wording by rule V3"] == "outside (above)", f"Q2 part A, bw_new read, round {rnd}: wording outside (above), computed and in FACTS.md")
    xc_val(f"Q2 part A, bw_new read, round {rnd}: distance of the nearest ends", v["near"], col(row, "Distance to the nearer end"))
    pc = sorted(int(x) for x in re.findall(r"\((\d+)\)", row["8000 MT/s, A-1, same round"] + row["8000 MT/s, A-2, same round"]))
    check(pc == v["p8"], f"Q2 part A, bw_new read, round {rnd}: pass counts at 8000 MT/s {v['p8']}, FACTS.md {pc}")
row = facts_row("4.5", lambda r: r["7200 MT/s row"].startswith("part C, asmread after oldread") and r["8000 MT/s range used"].startswith("pool L-1 to L-4 (after oldread)"), "part C asmread after oldread")
xc_range("Q2 load-only, part C asmread after oldread", rC_asm_ao.lo, rC_asm_ao.hi, col(row, "Its range"))
xc_val("Q2 load-only, part C asmread after oldread: distance", rC_asm_ao.nearest(rPL_asm), col(row, "Distance of the nearest ends"))
check("Insufficient data: no 8000 MT/s run of kernel read with bwx12" in SEC["4.5"], "Q2 part C, kernel read: Insufficient data wording present in FACTS.md section 4.5")
xc_text("three visits of the 7200 MT/s boot: span", "4.6", VISIT_HI - VISIT_LO, "GB/s")
xc_text_range("three visits of the 7200 MT/s boot: lowest to highest asmread", "4.9", VISIT_LO, VISIT_HI, "", "0.01", f2)
for kind in ("nearest", "medians", "farthest"):
    xc_text(f"part L above the 8000 MT/s pool, {kind}", "4.6", DIST[kind][0], "GB/s")
    xc_text(f"part L above F72d12, {kind}", "4.6", DIST[kind][1], "GB/s")
xc_text("same line in the 7200 MT/s boot: span of oldread", "3.4", VISIT_OLD_HI - VISIT_OLD_LO, "GB/s")
# part A, old read: widths of the two ranges. Rows of runner bwx: ranges, distances and highest values (note under Table 2)
g0 = len(CHECKS)
xc_text("part A, old read: width of the 7200 MT/s range", "0", A_OLD_W7, "GB/s")
xc_text("part A, old read: width of the 8000 MT/s range", "0", A_OLD_W8, "GB/s")
check(f"{len(A_OLD_BELOW)} of its {rA_old.n} intervals lie below that range and {len(A_OLD_ABOVE)} lie above it" in SEC["0"],
      f"part A, old read: {len(A_OLD_BELOW)} of {rA_old.n} intervals below the 8000 MT/s range and {len(A_OLD_ABOVE)} above it, computed and in FACTS.md section 0")
grouped("FACTS.md section 0, part A, old read kernel: widths of the two ranges (0.01 GB/s) and the intervals outside the 8000 MT/s range", g0)
g0 = len(CHECKS)
X45 = lambda name: facts_row("4.5", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)["Min to max, GB/s"]
xc_range("runner bwx, read at position 1", rX_read_ao.lo, rX_read_ao.hi, X45("pool B7a, B7b, C3a, C3b, position 1"))
xc_range("runner bwx, read at position 6", rX_read_aa.lo, rX_read_aa.hi, X45("pool B7a, B7b, C3a, C3b, position 6"))
xc_range("runner bwx, asmread at position 2", rX_asm_ar.lo, rX_asm_ar.hi, X45("pool B7a, B7b, C3a, C3b, position 2"))
xc_text("part C, read after oldread, above the bwx rows", "4.5", X_ABOVE[0], "GB/s")
xc_text("part C, read after asmread, above the bwx rows", "4.5", X_ABOVE[1], "GB/s")
row = facts_row("4.5", lambda r: r["7200 MT/s row"].startswith("part C, asmread after read") and r["8000 MT/s range used"].startswith("other binary bwx"),
                "part C asmread after read against runner bwx")
xc_val("part C, asmread after read, above the bwx rows", X_ABOVE[2], col(row, "Distance of the nearest ends"))
xc_text("runner bwx: highest read value of the rows of rule V2 point 4", "4.6", X_MAX_READ, "GB/s")
xc_text("runner bwx: highest asmread value of the rows of rule V2 point 4", "4.6", X_MAX_ASM, "GB/s")
xc_text("runner bwx, reverse order: highest read value", "4.6", X_REV_MAX_READ, "GB/s")
xc_text("runner bwx, reverse order: highest asmread value", "4.6", X_REV_MAX_ASM, "GB/s")
check(f"({len(X_LOADS)} intervals / {Rg(X_LOADS).np} processes / 1 boot" in SEC["4.6"], f"runner bwx: {len(X_LOADS)} intervals / {Rg(X_LOADS).np} processes / 1 boot, computed and in FACTS.md section 4.6")
grouped("FACTS.md sections 4.5 and 4.6, rows of runner bwx: 3 ranges, 3 distances and 4 highest values (0.01 GB/s), and n", g0)

# the same values against the "verdicts" records of facts.json
V = FJ["verdicts"]


def vrow(part, kernel, row7, scope8):
    hit = [r for r in V["q2_rows"] if r["part"] == part and r["kernel"] == kernel and r["row_7200"] == row7 and r["scope_8000"] == scope8]
    need(len(hit) == 1, f"facts.json verdicts: no single row {part} / {kernel} / {row7} / {scope8}")
    return hit[0]


def xv(label, r7, r8, vr, dist):
    ok = (near(r7.lo, vr["lo_7200"], "0.001") and near(r7.hi, vr["hi_7200"], "0.001") and near(r8.lo, vr["lo_8000"], "0.001")
          and near(r8.hi, vr["hi_8000"], "0.001") and near(dist, vr["distance_GBps"], "0.001") and r7.overlaps(r8) == vr["overlap"]
          and r7.n == vr["n_7200"] and r8.n == vr["n_8000"] and r7.np == vr["processes_7200"] and r8.np == vr["processes_8000"])
    check(ok, f"{label}: ranges, n, overlap and distance equal to the verdict record of facts.json")


g0 = len(CHECKS)
xv("old read, part A", rA_old, rPA_old, vrow("A", "bw_old read", "part A, sessions 1 to 3", "pool A-1 to A-3"), 0)
xv("old read, part L", rL_old, rPL_old, vrow("L", "oldread", "part L", "pool L-1 to L-4"), L_OLD_NEAR)
xv("old read, part C", rC_old, rPL_old, vrow("C", "oldread", "part C, all oldread intervals", "pool L-1 to L-4 (position 0)"), 0)
xv("old read, F72d12", rF_old, rPL_old, vrow("L", "oldread", "F72d12 (same boot, not pooled)", "pool L-1 to L-4"), 0)
xv("old read, control I", rI_old, rPL_old, vrow("L", "oldread", "control I (same boot, not pooled)", "pool L-1 to L-4"), 0)
xv("asmread, part L", rL_asm, rPL_asm, vrow("L", "asmread", "part L", "pool L-1 to L-4"), DIST["nearest"][0])
xv("asmread, F72d12", rF_asm, rPL_asm, vrow("L", "asmread", "F72d12 (same boot, not pooled)", "pool L-1 to L-4"), 0)
xv("asmread, control I", rI_asm, rPL_asm, vrow("L", "asmread", "control I (same boot, not pooled)", "pool L-1 to L-4"), rI_asm.nearest(rPL_asm))
xv("asmread after oldread, part C", rC_asm_ao, rPL_asm, vrow("C", "asmread", "part C, asmread after oldread", "pool L-1 to L-4 (after oldread)"), rC_asm_ao.nearest(rPL_asm))
for rnd in (1, 2):
    xv(f"bw_new read, session 1, round {rnd}", A_V3[rnd]["r7"], A_V3[rnd]["r8"],
       vrow("A", "bw_new read", f"session 1, round {rnd}", f"A-1 and A-2, round {rnd}"), A_V3[rnd]["near"])
for key_, grp in (("C_ao", "read after oldread"), ("C_aa", "read after asmread")):
    vr = [r for r in V["q1_parts"] if r["part"] == "C" and r["group"] == grp]
    need(len(vr) == 1, f"facts.json verdicts: no single Q1 row {grp}")
    check(near(min(Q1[key_]["drops"]), vr[0]["smallest_drop_pct"], "0.01") and near(max(Q1[key_]["drops"]), vr[0]["largest_drop_pct"], "0.01"),
          f"Q1 part C, {grp}: drops equal to the verdict record of facts.json to 0.01 %")
grouped("verdict records of facts.json (11 comparisons of Q2 with ranges, n, overlap and distance to 0.001 GB/s; 2 drop ranges of Q1 to 0.01 %)", g0)
sb = V["same_boot"]
check(near(VISIT_HI - VISIT_LO, sb["spread_GBps"], "0.001")
      and all(near(DIST[k][0], sb["part_L_above_pool_8000_GBps"][j], "0.001") and near(DIST[k][1], sb["part_L_above_F72d12_GBps"][j], "0.001")
              for k, j in (("nearest", "nearest_ends"), ("medians", "medians"), ("farthest", "farthest_ends"))),
      "three visits of the 7200 MT/s boot: span and the 6 distances equal to the same_boot record of facts.json")

# ------------------------------------------------------------------ raw-file checks for the machine state section
REFS = []            # (key, path, text shown, note)


def addref(key, path, note, lines=None):
    need(os.path.exists(path), f"reference {key}: path does not exist: {path}")
    shown = path.replace(R + "/", "R/").replace(S + "/", "S/")
    REFS.append((key, shown + (f" ({lines})" if lines else ""), note))


def ref(*keys):
    """Reference marks. The numbers are given at the end, in the order of first use on the page (number_refs)."""
    for k in keys:
        need(sum(1 for r in REFS if r[0] == k) == 1, f"unknown reference key {k}")
    return '<span class="ref">' + "".join(f"\x00{k}\x00" for k in keys) + "</span>"


def number_refs(page):
    order = []
    for k in re.findall("\x00(.+?)\x00", page):
        if k not in order:
            order.append(k)
    uncited = [r[0] for r in REFS if r[0] not in order]
    num = {k: i + 1 for i, k in enumerate(order + uncited)}
    by_key = {r[0]: r for r in REFS}
    items = "".join(f'<li id="ref{num[k]}">[Ref{num[k]}] <code>{esc(by_key[k][1])}</code>: {esc(by_key[k][2])}</li>' for k in order + uncited)
    page = re.sub("\x00(.+?)\x00", lambda m: f'<a href="#ref{num[m.group(1)]}">[Ref{num[m.group(1)]}]</a>', page)
    return page.replace("\x01REFLIST\x01", items), uncited


GOLOG = R + "/go-T72-20261117T221209Z.log"
GO2LOG = R + "/go2-T72-20261117T222335Z.log"
STATE_RE = re.compile(r"^== (.+?) utc (\S+) boot (\S+) MemTotal: (\d+) kB load (\S+) (\S+) (\S+) (\d+)/(\d+) \d+ users (\d+) marker (\S+) processes per user: (.*)$")
SYSTEM_ACCOUNTS = {"messagebus", "polkitd", "syslog", "systemd-network", "systemd-resolve", "systemd-timesync"}


def state_lines(path):
    out = []
    for no, line in enumerate(lines_of(path), 1):
        m = STATE_RE.match(line)
        if m:
            users = {}
            for part in m.group(12).split(";"):
                part = part.split()
                if len(part) == 2:
                    users[part[1]] = int(part[0])
            out.append(dict(line=no, name=m.group(1), utc=m.group(2), boot=m.group(3), mem=int(m.group(4)),
                            load1=Decimal(m.group(5)), logins=int(m.group(10)), marker=m.group(11), users=users))
    return out


ST_GO, ST_GO2 = state_lines(GOLOG), state_lines(GO2LOG)
need(len(ST_GO) == 12 and len(ST_GO2) == 6, "run logs: expected 12 and 6 state lines")
ST_ALL = ST_GO + ST_GO2
need(all(s["boot"] == RERUN["boot_id"] for s in ST_ALL), "run logs: a state line holds another boot id")
need(all(s["mem"] == RERUN["memtotal_kB"] for s in ST_ALL), "run logs: a state line holds another MemTotal")
need(all(s["logins"] == 0 and s["marker"] == "absent" for s in ST_ALL), "run logs: a login or the marker file")
ACCOUNTS = set().union(*[set(s["users"]) for s in ST_ALL])
need(ACCOUNTS == {"jhan", "root"} | SYSTEM_ACCOUNTS, f"run logs: unexpected account owns a process: {sorted(ACCOUNTS)}")
need(all(s["users"][a] == 1 for s in ST_ALL for a in SYSTEM_ACCOUNTS), "run logs: a system account owns more than 1 process")
JHAN_PROCS = sorted({s["users"]["jhan"] for s in ST_ALL})
need(len(JHAN_PROCS) == 1, "run logs: the process count of jhan changes")
gl, g2l = lines_of(GOLOG), lines_of(GO2LOG)
GO_DONE = sum(1 for l in gl if l.startswith("done "))
need(GO_DONE == 10 and gl[-1] == "ALLDONE" and not any(l.startswith("FAILED") for l in gl), "go.sh log: not 10 steps, or not ALLDONE")
need(sum(1 for l in g2l if l.startswith("done ")) == 2 and g2l[-1] == "ALLDONE" and not any(l.startswith("FAILED") for l in g2l), "go2.sh log")
need(ST_GO[0]["utc"] == RERUN["go_start"] and ST_GO[-1]["utc"] == RERUN["go_end"], "go.sh log: start or end time differs from facts.json")
need(ST_GO2[0]["utc"] == RERUN["go2_start"] and ST_GO2[-1]["utc"] == RERUN["go2_end"], "go2.sh log: start or end time differs from facts.json")
LAUNCH = {l["tag"]: l for l in META["launches"]}
STEPS = ["T72A1", "T72L1", "T72C1", "T72A2", "T72L2", "T72C2", "T72A3", "T72L3", "T72C3", "T72C4", "T72I1", "T72I2"]
need([l["tag"] for l in META["launches"]] == STEPS, "meta.launches: unexpected list of steps")
BWX_FOLDERS = sorted({r["folder"] for r in L_OLD + C_OLD + I_OLD})
need(len(BWX_FOLDERS) == 9, "expected 9 bwx12 folders of the rerun and the control")
for fo in BWX_FOLDERS:
    ll = lines_of(fo.replace("R/", R + "/", 1) + "/launches.txt")
    need(sum(1 for l in ll if l.startswith("rc ")) == 1 and sum(1 for l in ll if l.startswith("rc 0 ")) == 1, f"{fo}: no single 'rc 0' line")
check(True, f"run logs: {len(ST_ALL)} state lines hold boot id {RERUN['boot_id']} and MemTotal {RERUN['memtotal_kB']} kB, 0 logins; "
            f"accounts with processes: jhan, root and {len(SYSTEM_ACCOUNTS)} system accounts; go.sh log: {GO_DONE} 'done' lines and ALLDONE; 9 bwx12 folders with one 'rc 0' line")

# the boot record of 12 modules at 7200 MT/s
TRY6 = R + "/dimm7200-20261117/try6.txt"
t6 = lines_of(TRY6)
need(t6[1].strip() == RERUN["boot_id"], "try6.txt: line 2 is not the boot id of the rerun")
need(re.match(r"^MemTotal:\s+%d kB$" % RERUN["memtotal_kB"], t6[3]), "try6.txt: line 4 holds another MemTotal")
m_ = re.match(r"^\s*(\d+)\s+Configured Memory Speed: (\d+) MT/s$", t6[6])
need(m_ and int(m_.group(1)) == 12 and int(m_.group(2)) == RERUN["speed_MTps"] == 7200, "try6.txt: line 7 is not 12 x 7200 MT/s")
need(t6[4].strip().endswith("ghes_edac: This system has 12 DIMM sockets."), "try6.txt: line 5 is not the kernel line with 12 modules")
m_ = re.match(r"^modules=(\d+)$", t6[5].strip())
need(m_, "try6.txt: line 6 is not a line 'modules=N'")
TRY6_MODLINE = int(m_.group(1))                            # not the module count: see the module list below
TRY6_UTC = t6[0].strip()
need(re.match(r"^2026-11-17T\d\d:\d\d:\d\dZ$", TRY6_UTC), "try6.txt: line 1 is not a time")
# why F72d12 belongs to this boot
BOOTS = R + "/dimm7200-20261117/boots.txt"
bl = [l.split() for l in lines_of(BOOTS) if l.strip()]
need(bl[-1][0] == "0" and bl[-1][1] == RERUN["boot_id"].replace("-", ""), "boots.txt: row 0 is not the boot of the rerun")
BOOT_FIRST, BOOT_LAST = bl[-1][4], bl[-1][8]
need(time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(BOOTS))) == BOOT_LAST, "boots.txt: its file time is not the end time of row 0")
FL = R + "/w120-w120-F72d12-20261117T200231Z/launches.txt"
fl = lines_of(FL)
m1, m2 = re.match(r"^launch a6456 utc (\S+) load (\S+) ", fl[0]), re.match(r"^rc 0 a6456 utc (\S+)$", fl[1])
need(m1 and m2, "F72d12 launches.txt: launch or rc line not found")
F_LAUNCH, F_END = m1.group(1), m2.group(1)
need(F_OLD[0]["launch_utc"] == f"2026-11-17T{F_LAUNCH}Z" and D(m1.group(2)) == D(F_OLD[0]["load1_at_launch"]), "F72d12: launch differs from facts.json")
need(TRY6_UTC[11:19] < F_LAUNCH and BOOT_FIRST <= F_LAUNCH < F_END <= BOOT_LAST and BOOT_LAST < ST_GO[0]["utc"][11:19],
     "F72d12: the process does not lie inside the recorded time of boot 3bfc57a1")
check(True, f"try6.txt ({TRY6_UTC}): boot id of the rerun, MemTotal {RERUN['memtotal_kB']} kB, 12 x 7200 MT/s; boots.txt row 0 = this boot, "
            f"{BOOT_FIRST} to {BOOT_LAST}; F72d12 ran {F_LAUNCH} to {F_END} inside it")

# corrected hardware error records in the journal of the 8000 MT/s boot (defect partL-r3-partL-1, checked here)
JOURNAL = R + "/dimm-check-20261117/h-5.txt"
HW = []
for no, line in enumerate(lines_of(JOURNAL), 1):
    m_ = re.match(r"^(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: (.*)$", line)
    if not m_:
        continue
    if m_.group(3).startswith("Hardware error from APEI"):
        HW.append(dict(line=no, ts=m_.group(1), sev=None))
    elif m_.group(3).startswith("event severity:") and HW:
        HW[-1]["sev"] = m_.group(3).split(":", 1)[1].strip()
need(len(HW) > 0 and {h["sev"] for h in HW} == {"corrected"}, "journal: no records, or a severity other than 'corrected'")
# the saved kernel log of the same boot: its first and last line, the module count line, the same number of records
KLOG = R + "/dimm-check-20261117/k-5.txt"
kl = lines_of(KLOG)
mk0, mk1 = re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", kl[0]), re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", kl[-1])
need(mk0 and mk1, "kernel log of the 8000 MT/s boot: first or last line has no time")
BOOT8_FROM, BOOT8_TO = f"2026-11-{mk0.group(1)}T{mk0.group(2)}Z", f"2026-11-{mk1.group(1)}T{mk1.group(2)}Z"
need(sum(1 for l in kl if "ghes_edac: This system has 12 DIMM sockets" in l) == 1, "kernel log of the 8000 MT/s boot: module count line")
need(sum(1 for l in kl if "Hardware error from APEI" in l) == len(HW), "kernel log and journal of the 8000 MT/s boot: record counts differ")
need(lines_of(JOURNAL)[0].startswith(BOOT8_FROM[:19]), "journal and kernel log of the 8000 MT/s boot: first line times differ")
need(all(BOOT8_FROM < r["launch_utc"] < BOOT8_TO for r in EIGHT + OTHER), "an 8000 MT/s row was not launched inside the saved kernel log of its boot")


def launch_window(folder, tag):
    ll = lines_of(R + "/" + folder + "/launches.txt")
    a = [re.match(rf"^launch {tag} utc (\S+) ", l) for l in ll]
    b = [re.match(rf"^rc 0 {tag} utc (\S+)$", l) for l in ll]
    a, b = [x for x in a if x], [x for x in b if x]
    need(len(a) == 1 and len(b) == 1, f"{folder}: launch window of {tag} not found")
    return a[0].group(1), b[0].group(1)


def hw_in(day, t0, t1):
    return [h for h in HW if h["ts"][:10] == day and t0 <= h["ts"][11:19] <= t1]


HW_ROWS = {}
for d in LPOOL:
    for pk in sorted({r["proc_key"] for r in B_L_ASM[d]}):
        r0 = [r for r in B_L_ASM[d] if r["proc_key"] == pk][0]
        folder, tag = r0["folder"].replace("R/", "", 1), r0["tag"]
        t0, t1 = launch_window(folder, tag)
        need(r0["launch_utc"][11:19] == t0, f"{d} {tag}: launch time differs from facts.json")
        HW_ROWS[(d, tag)] = dict(t0=t0, t1=t1, day=r0["launch_utc"][:10], recs=hw_in(r0["launch_utc"][:10], t0, t1))
HW_L1 = len(HW_ROWS[("L-1", "a6456")]["recs"])
HW_L2 = [len(HW_ROWS[("L-2", t)]["recs"]) for t in ("p1nop", "p2add")]
HW_L34 = sum(len(v["recs"]) for (d, _), v in HW_ROWS.items() if d in ("L-3", "L-4"))
need(HW_L1 > 0 and min(HW_L2) > 0 and HW_L34 == 0, "journal: the record counts of rows L-1 to L-4 are not as the defect states")
# the part A rows of the same boot (A-1, A-2, A-3): records between the launches that the csv files hold


def a_headers(rec):
    """(line number, launch time, text) of every process header line of the csv file of a part A record."""
    out = []
    for no, l in enumerate(file_lines(rec), 1):
        if l.startswith("-- "):
            m_ = re.search(r" utc (\d\d:\d\d:\d\d)\b", l)
            need(m_, f"{rec['folder']}/{rec['file']} line {no}: header without a launch time")
            out.append((no, m_.group(1), l))
    return out


def secs(hms):
    h, m, s_ = (int(x) for x in hms.split(":"))
    return h * 3600 + m * 60 + s_


A_DAY = "2026-11-13"
need({r["launch_utc"][:10] for d in APOOL for r in B_A_OLD[d]} == {A_DAY}, "rows A-1 to A-3 are not all of 2026-11-13")
HA1, HA2, HA3 = a_headers(B_A_OLD["A-1"][0]), a_headers(B_A_OLD["A-2"][0]), a_headers(B_A_OLD["A-3"][0])
A1_FIRST, A1_LAST, A2_FIRST, A2_LAST = HA1[0][1], HA1[-1][1], HA2[0][1], HA2[-1][1]
a3_used = sorted({r["_fproc"] for r in B_A_OLD["A-3"]})          # numbers of the processes used, inside the file
need(len(a3_used) == 3 and a3_used[-1] < len(HA3), "A-3: the 3 processes used, and a later process in the file")
A3_FIRST, A3_END = HA3[a3_used[0] - 1][1], HA3[a3_used[-1]][1]      # launch of the first one, launch of the process after the last one
need(A1_FIRST <= A1_LAST < A2_FIRST <= A2_LAST < A3_FIRST < A3_END, "rows A-1, A-2, A-3: order of the launch times")
HW_A = hw_in(A_DAY, A1_FIRST, A3_END)
HW_A2 = hw_in(A_DAY, A2_FIRST, A2_LAST)
need(len(HW_A) == len(HW_A2) == 4 and not hw_in(A_DAY, A1_FIRST, A1_LAST) and not hw_in(A_DAY, A3_FIRST, A3_END),
     "journal: the records of 2026-11-13 are not 4 records inside row A-2 and 0 inside A-1 and A-3")
# the last process of A-1 and of A-2 has no later header in its file: no record follows within 60 s of its launch
for last in (A1_LAST, A2_LAST):
    need(not [h for h in HW if h["ts"][:10] == A_DAY and 0 < secs(h["ts"][11:19]) - secs(last) <= 60], "journal: a record within 60 s after the last launch of A-1 or A-2")
HW_A2_T = sorted({h["ts"][11:19] for h in HW_A2})
need(len(HW_A2_T) == 2 and all(sum(1 for h in HW_A2 if h["ts"][11:19] == t) == 2 for t in HW_A2_T), "journal: row A-2 does not hold 2 + 2 records at two times")
a2_new_r1 = [r for r in B_A_NEW["A-2"] if r["round"] == 1]
need(len(a2_new_r1) == 3 and a2_new_r1[0]["launch_utc"][11:19] == HW_A2_T[0] == HA2[a2_new_r1[0]["_fproc"] - 1][1],
     "journal: the first two records of row A-2 are not in the launch second of bw_new read, round 1")
a2_other = [h for i, h in enumerate(HA2) if h[1] <= HW_A2_T[1] and (i + 1 == len(HA2) or HW_A2_T[1] < HA2[i + 1][1])]
need(len(a2_other) == 1, "journal: no single process of row A-2 for the second pair of records")
m_ = re.search(r" binary (\S+) .* --kernel (\S+) ", a2_other[0][2])
need(m_ and m_.group(2) not in ("read", "all"), "journal: the second pair of records of row A-2 falls into a read process")
A2_OTHER = f"{m_.group(1)} {m_.group(2)}"
check(True, f"journal of the 8000 MT/s boot, {A_DAY}: {len(HW_A)} corrected records from the first launch of A-1 ({A1_FIRST}) to the launch after the last A-3 process used ({A3_END}); "
            f"all in A-2: 2 at {HW_A2_T[0]} (launch second of bw_new read, round 1), 2 at {HW_A2_T[1]} (process {A2_OTHER}, launched {a2_other[0][1]})")

# the interval with the lowest asmread value of the pool: its time inside the process, from the T rows of the csv
need(LOWEST_ASM["dataset"] == "L-2" and LOWEST_ASM["tag"] == "p2add", "the lowest asmread interval of the pool is not in L-2 p2add")
T_START = Decimal(repr(min(t[3] for t in t_rows(LOWEST_ASM))))      # seconds since the process start
T_END = Decimal(repr(max(t[4] for t in t_rows(LOWEST_ASM))))


def clock(hms, add):
    """Launch time plus seconds since the process start, to the nearest second."""
    h, m, s = (int(x) for x in hms.split(":"))
    tot = h * 3600 + m * 60 + s + int(add.to_integral_value(rounding=ROUND_HALF_UP))
    return f"{tot // 3600:02d}:{tot // 60 % 60:02d}:{tot % 60:02d}"


LOW_T0 = HW_ROWS[("L-2", "p2add")]["t0"]
LOW_FROM, LOW_TO = clock(LOW_T0, T_START), clock(LOW_T0, T_END)
HW_LOW = hw_in(LOWEST_ASM["launch_utc"][:10], LOW_FROM, LOW_TO)
need(len(HW_LOW) == 2 and len({h["ts"] for h in HW_LOW}) == 1, "journal: not 2 records with one time inside the lowest asmread interval")
m_ = re.search(rf"Without this (?:one )?interval the pool spans ({NUM}) to ({NUM}) GB/s", FMD)
if m_:
    check(near(q(rPL_asm_wo.lo), m_.group(1), "0.01") and near(q(rPL_asm_wo.hi), m_.group(2), "0.01"),
          f"pool L-1 to L-4 (asmread) without its lowest interval: computed {rPL_asm_wo.txt()} GB/s, FACTS.md {m_.group(1)} to {m_.group(2)} GB/s")
else:
    check(True, f"pool L-1 to L-4 (asmread) without its lowest interval: computed {rPL_asm_wo.txt()} GB/s. FACTS.md holds no such sentence, so this value rests on the raw files only")
check(True, f"journal of the 8000 MT/s boot: corrected records during L-1: {HW_L1}, L-2: {HW_L2[0]} and {HW_L2[1]}, L-3 and L-4: {HW_L34}; "
            f"{len(HW_LOW)} records at {HW_LOW[0]['ts'][11:19]} inside the interval of {f2(val(LOWEST_ASM))} GB/s ({LOW_FROM} to {LOW_TO}); "
            f"pool without it {rPL_asm_wo.txt()} GB/s")

# firmware settings (defect state-r3-S3-1, checked here)
FW = R + "/fwtest-20261117"


def set_records(path):
    """(name, answer) of every response of a settings file that carries 'modified: true', and the time of line 1."""
    text = "\n".join(lines_of(path))
    out = [(m.group(1), m.group(2)) for m in re.finditer(r'name: "([^"]+)",\s*answer: "([^"]+)",[^}]*\},\s*modified: true', text, re.S)]
    for line in text.splitlines():
        if line.startswith('{"responses"'):
            for resp in json.loads(line)["responses"]:
                if resp.get("modified") is True:
                    out.append((resp["question"]["name"], resp["question"]["answer"]))
    m = re.match(r"^\w+ Nov 17 (\d\d:\d\d:\d\d) (AM|PM) UTC 2026$", text.splitlines()[0])
    when = None
    if m:
        h = int(m.group(1)[:2]) % 12 + (12 if m.group(2) == "PM" else 0)
        when = f"{h:02d}{m.group(1)[2:]}"
    return out, when


X1, X1_T = set_records(FW + "/x1/set.txt")
X2, X2_T = set_records(FW + "/x2/set.txt")
RV, RV_T = set_records(FW + "/revert/set.txt")
D72, _ = set_records(R + "/dimm7200-20261117/set.txt")
need(X1 == [("TXREQ Min", "1/4 L2 TQ")] and X2 == [("TXREQ Max", "1/4 L2 TQ")], "fwtest: the two TXREQ changes are not as expected")
Q_BASE = json.load(open(R + "/uefisettings-20261117/questions.json"))
Q_REV = json.load(open(FW + "/revert/questions.json"))
orig = {x["name"]: x["answer"] for x in Q_BASE if x["name"] in ("TXREQ Max", "TXREQ Min")}
need(len(orig) == 2 and sorted(RV) == sorted(orig.items()), "fwtest: the revert does not set both TXREQ settings to the original values")
need(X1_T and X2_T and RV_T and X1_T < X2_T < RV_T, "fwtest: times of the three records")
canon = lambda qs: sorted(json.dumps(x, sort_keys=True) for x in qs)
need(len(Q_BASE) == len(Q_REV) and canon(Q_BASE) == canon(Q_REV), "fwtest: the settings list after the revert differs from the list of the 8000 MT/s boot")
need([x["answer"] for x in Q_BASE if x["name"] == "DIMM Frequency"] == ["8000 MT/s"], "settings list of the 8000 MT/s boot: DIMM Frequency is not 8000 MT/s")
QBASE_T = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(R + "/uefisettings-20261117/questions.json")))
need(BOOT8_FROM < QBASE_T < BOOT8_TO, "settings list of the 8000 MT/s boot: its file time is not inside that boot")
N_SET = len(Q_BASE)
SAME_ORDER = Q_BASE == Q_REV
UNREAD = {}        # kind of error marker -> number of entries that show it in place of a value
for x in Q_BASE:
    m_ = re.match(r"^<(\w+):", str(x["answer"]))
    if m_:
        UNREAD[m_.group(1)] = UNREAD.get(m_.group(1), 0) + 1
need(set(UNREAD) == {"ValueUnavailable", "VStoreError"}, f"settings list: unexpected kinds of error marker: {sorted(UNREAD)}")
N_UNREAD = sum(UNREAD.values())
need(D72 == [("DIMM Frequency", "7200 MT/s")], "dimm7200 set.txt: not the single change DIMM Frequency = 7200 MT/s")
SET_FILES = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(R) for f in fs if f == "set.txt")
need(SET_FILES == sorted([FW + "/x1/set.txt", FW + "/x2/set.txt", FW + "/revert/set.txt", R + "/dimm7200-20261117/set.txt"]),
     "results folder: the files named set.txt are not the 4 expected ones")
D72_T = time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(R + "/dimm7200-20261117/set.txt")))
need(RV_T < D72_T < TRY6_UTC[11:19], "dimm7200 set.txt: file time is not between the revert and the boot record")
check(True, f"firmware settings: TXREQ Min changed {X1_T}, TXREQ Max changed {X2_T}, both set back {RV_T} to the values of the 8000 MT/s list; "
            f"list after the revert equal in {N_SET} entries ({N_UNREAD} without a readable value: {UNREAD['ValueUnavailable']} ValueUnavailable, {UNREAD['VStoreError']} VStoreError); 4 files set.txt under R, last: DIMM Frequency = 7200 MT/s ({D72_T} file time)")

# start state of the three visits of the part L line in the 7200 MT/s boot (process lists, time since the start of the boot)


def proc_list(path):
    """Time of line 1 and the rows (user, %CPU, command) of the process list of an env.txt file."""
    ll = lines_of(path)
    m_ = re.match(r"^\w+ Nov 17 (\d\d):(\d\d:\d\d) (AM|PM) UTC 2026$", ll[0])
    need(m_, f"{path}: line 1 is not a time of 2026-11-17")
    when = f"{int(m_.group(1)) % 12 + (12 if m_.group(3) == 'PM' else 0):02d}:{m_.group(2)}"
    need(ll[3].split() == ["USER", "%CPU", "COMMAND"], f"{path}: line 4 is not the head of the process list")
    rows = []
    for no, l in enumerate(ll[4:], 5):
        if l.startswith("binary "):
            break
        u, c, name = l.split(None, 2)
        rows.append((no, u, Decimal(c), name.strip()))
    need(len(rows) >= 3, f"{path}: process list too short")
    return when, rows


F_ENV = R + "/w120-w120-F72d12-20261117T200231Z/env.txt"
F_ENV_T, F_PROCS = proc_list(F_ENV)
F_TOP = max(F_PROCS, key=lambda x: x[2])
need(F_TOP[0] == 5 and F_TOP[3] == "pr/ttyAMA-1" and F_TOP[1] == "root", "F72d12 env.txt: the busiest process is not pr/ttyAMA-1 in line 5")
GAPS = R + "/dimm7200-20261117/gaps.txt"
m_ = re.match(r"^0 first=2026-11-17T(\d\d:\d\d:\d\d)\+00:00 ", lines_of(GAPS)[6])
need(m_, "gaps.txt: line 7 is not the row of boot 0")
BOOT7_KLOG = m_.group(1)                                   # first kernel log line of the boot of the rerun
F_AFTER_BOOT_S = secs(F_LAUNCH) - secs(BOOT7_KLOG)
F_ENV_BEFORE_S = secs(F_LAUNCH) - secs(F_ENV_T)
need(0 < F_AFTER_BOOT_S < 60 and 0 < F_ENV_BEFORE_S < 60, "F72d12: launch is not shortly after the first kernel log line and the process list")
VISIT_ENV = {}
for tg in ("T72L1", "T72L2", "T72L3", "T72I1", "T72I2"):
    fo = [r for r in L_OLD + I_OLD if r["tag"] == tg][0]["folder"].replace("R/", R + "/", 1)
    when, rows = proc_list(fo + "/env.txt")
    need(0 < secs(LAUNCH[tg]["first_launch"][11:19]) - secs(when) < 60, f"{tg}: env.txt was not written shortly before the launch")
    VISIT_ENV[tg] = (fo + "/env.txt", max(x[2] for x in rows))
L_ENV_MAX = max(VISIT_ENV[t][1] for t in ("T72L1", "T72L2", "T72L3"))
I_ENV_MAX = max(VISIT_ENV[t][1] for t in ("T72I1", "T72I2"))
need(max(L_ENV_MAX, I_ENV_MAX) < 1, "part L or control I: a process list shows a busy process")
check(True, f"start state: F72d12 launched {F_AFTER_BOOT_S} s after the first kernel log line of the boot ({BOOT7_KLOG}); its process list, written {F_ENV_BEFORE_S} s before the launch, "
            f"shows {F_TOP[3]} at {F_TOP[2]} %CPU; process lists of part L and control I: at most {max(L_ENV_MAX, I_ENV_MAX)} %CPU")

# the number in the kernel line "This system has N DIMM sockets" is not the slot count: a boot of 2026-11-17 printed 10
KLOG10 = R + "/dimm-check-20261117/k-1.txt"
k10 = lines_of(KLOG10)
K10_LINE = [i for i, l in enumerate(k10, 1) if "ghes_edac: This system has 10 DIMM sockets" in l]
mk10 = re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", k10[0])
need(len(K10_LINE) == 1 and mk10, "kernel log k-1.txt: no single line with 10 modules, or no time in line 1")
BOOT10_FROM = f"2026-11-{mk10.group(1)} {mk10.group(2)}"


def mem_line(ll):
    hit = [(i, re.search(r"kernel: Memory: (\d+)K/(\d+)K available", l)) for i, l in enumerate(ll, 1)]
    hit = [(i, int(m.group(2))) for i, m in hit if m]
    need(len(hit) == 1, "kernel log: no single line 'Memory:'")
    return hit[0]


K10_MEM, K12_MEM = mem_line(k10), mem_line(kl)
MEM_LESS_GIB = Decimal(K12_MEM[1] - K10_MEM[1]) / (1024 * 1024)
need(MEM_LESS_GIB == 64, "kernel logs: the 10-module boot does not show 64 GiB less memory than the 8000 MT/s boot")
# the module list that was saved in the boot of the rerun
DMI = R + "/dimm7200-20261117/dmi17-7200.txt"
dmi = lines_of(DMI)
DMI_N = sum(1 for l in dmi if l.strip() == "Memory Device")
need(DMI_N == 12 and sum(1 for l in dmi if "Configured Memory Speed:" in l) == 12 == sum(1 for l in dmi if l.strip() == "Configured Memory Speed: 7200 MT/s"),
     "module list of the rerun boot: not 12 modules with one line 'Configured Memory Speed: 7200 MT/s' each")
need(time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(DMI))) == BOOT_LAST, "module list of the rerun boot: its file time is not inside row 0 of boots.txt")
# line 6 of try6.txt ("modules=24") is not the module count: the module list holds that number of lines with the text "Size: 32 GB"
DMI_SIZE = sum(1 for l in dmi if "Size: 32 GB" in l)
DMI_SIZE_PLAIN = sum(1 for l in dmi if l.strip() == "Size: 32 GB")
DMI_SIZE_VOL = sum(1 for l in dmi if l.strip() == "Volatile Size: 32 GB")
need(DMI_SIZE == TRY6_MODLINE == DMI_SIZE_PLAIN + DMI_SIZE_VOL and DMI_SIZE_PLAIN == DMI_SIZE_VOL == DMI_N,
     "try6.txt line 6: its number is not the number of lines with 'Size: 32 GB' in the module list (one 'Size' and one 'Volatile Size' line per module)")
check(True, f"module count: try6.txt line 5 holds '12 DIMM sockets'; the module list saved at {BOOT_LAST} holds {DMI_N} modules with one speed line each; "
            f"the kernel log of the boot of {BOOT10_FROM} holds '10 DIMM sockets' and {MEM_LESS_GIB} GiB less memory; "
            f"try6.txt line 6 reads 'modules={TRY6_MODLINE}', and the module list holds {DMI_SIZE} lines with 'Size: 32 GB' ({DMI_SIZE_PLAIN} 'Size' and {DMI_SIZE_VOL} 'Volatile Size')")
need(all(l.startswith("done /home/jhan/") for l in gl + g2l if l.startswith("done ")), "run logs: a result folder is not under the home folder of jhan")

# the argument lines: which earlier rows ran the line of part L, and whether the lines of part C ran before
def spec_line(path):
    """(name, arguments, kernel sequence) of the one argument line of a spec file."""
    ll = [l for l in lines_of(path) if l.strip()]
    need(len(ll) == 1 and "|" in ll[0], f"{path}: not one argument line")
    name, args = ll[0].split("|", 1)
    m = re.search(r"--seq (\S+)", args)
    need(m, f"{path}: no kernel sequence")
    return name, args.strip(), m.group(1)


def launch_args(folder, tag):
    """The arguments of the launch line of a process in launches.txt of a result folder (R/...)."""
    hit = [l for l in lines_of(folder.replace("R/", R + "/", 1) + "/launches.txt") if l.startswith(f"launch {tag} ")]
    need(len(hit) == 1 and " args " in hit[0], f"{folder}: no single launch line of {tag}")
    return hit[0].split(" args ", 1)[1].strip()


SPEC = {nm: spec_line(f"{S}/{nm}.spec") for nm in ("like", "cfwd", "crev")}
LINE_L = SPEC["like"][0]                                   # the name of the part L line: its csv file carries it
no_seq = lambda a: re.sub(r"--seq \S+", "--seq X", a)
need(no_seq(SPEC["like"][1]) == no_seq(SPEC["cfwd"][1]) == no_seq(SPEC["crev"][1]) and len({v[2] for v in SPEC.values()}) == 3,
     "the three argument lines do not differ in the kernel sequence only")
SAME_LINE_FOLDERS = sorted({r["folder"] for r in L_OLD + I_OLD + F_OLD + B_L_OLD["L-1"]})
need(len(SAME_LINE_FOLDERS) == 7 and all(launch_args(fo, LINE_L) == SPEC["like"][1] for fo in SAME_LINE_FOLDERS),
     "row L-1, part L, control I or F72d12: a process did not run the argument line of part L")
need({r["file"] for r in L_OLD + I_OLD + F_OLD + B_L_OLD["L-1"]} == {LINE_L + ".csv"}, "the csv file of a process of the part L line does not carry the name of the line")
C_FOLDERS = sorted({r["folder"] for r in C_OLD})
for fo in C_FOLDERS:
    nms = sorted({r["file"][:-4] for r in C_OLD if r["folder"] == fo})
    need(len(nms) == 1 and nms[0] in ("cfwd", "crev") and launch_args(fo, nms[0]) == SPEC[nms[0]][1], f"{fo}: the process did not run the argument line of its spec file")
SEQ_FOLDERS, READ_FOLDERS, N_CSV = {}, set(), 0     # kernel sequence -> result folders with a csv file whose header line holds it
for dp_, _, fs_ in os.walk(R):
    for f_ in fs_:
        if f_.endswith(".csv"):
            N_CSV += 1
            with open(os.path.join(dp_, f_), encoding="utf-8", errors="replace") as fh_:
                for l in fh_:
                    if l.startswith("# bwx"):
                        if re.match(r"^# bwx\d+ trial mode:", l):
                            continue                # one-CPU trial files of older runners: they hold no kernel sequence
                        m_ = re.match(r"^# bwx: seq=(\S+)", l)
                        need(m_, f"{dp_}/{f_}: a header line of a runner that is neither a kernel sequence nor a trial-mode header")
                        fo_ = "R/" + os.path.relpath(dp_, R).split(os.sep)[0]
                        SEQ_FOLDERS.setdefault(m_.group(1), set()).add(fo_)
                        if "read" in m_.group(1).split(","):
                            READ_FOLDERS.add(fo_)
need(sorted(SEQ_FOLDERS[SPEC["cfwd"][2]] | SEQ_FOLDERS[SPEC["crev"][2]]) == C_FOLDERS, "csv files of the results folder: a folder other than the 4 part C folders holds a part C kernel sequence")
# the kernel read in a sequence: the 4 part C folders, and folders of the older runner bwx (rules file, part A list: B7-*, C3-*, SHORT-*; part C list: B5-*)
READ_OTHER = sorted(READ_FOLDERS - set(C_FOLDERS))
need(READ_OTHER and all(re.match(r"^R/(B5|B7|C3|SHORT)-2026111[34]T", fo_) for fo_ in READ_OTHER),
     f"csv files of the results folder: the kernel read is in a sequence of a folder that is neither part C nor a folder of runner bwx: {READ_OTHER}")
need({r["folder"] for r in OTHER} <= set(READ_OTHER), "runner bwx: a folder used on the page is not among the folders with the kernel read")
check(True, f"argument lines: like.spec, cfwd.spec and crev.spec differ in the kernel sequence only; row L-1, part L, control I and F72d12 ({len(SAME_LINE_FOLDERS)} folders) ran the line of like.spec; "
            f"header lines of the {N_CSV} csv files under R: only the {len(C_FOLDERS)} part C folders hold a part C sequence; the kernel read is in a sequence there and in {len(READ_OTHER)} folders of runner bwx only")

# rows of runner bwx: the header lines of their processes (start option, counter setting, load at launch).
# Rule V2 point 4 asks the report to state how these rows differ from part C. Table 6 gives their load at launch.
def bwx_header(rec):
    """Header facts of the process of a record of runner bwx, read from its csv file: the line "-- step ... tag T ... loadavg L ... utc H:M:S args ..."
    before the record, and the one line "# bwx: ..." that follows it. Both must agree with the record."""
    fl = file_lines(rec)
    i = rec["line"] - 1
    while i >= 0 and not fl[i].startswith("-- "):
        i -= 1
    where = f"{rec['folder']}/{rec['file']} line {i + 1}"
    m = re.match(r"^-- step \S+ tag (\S+) binary (\S+) .* loadavg (\S+) .* utc (\d\d:\d\d:\d\d) args (.*)$", fl[i]) if i >= 0 else None
    need(m and m.group(1) == rec["tag"] and m.group(2) == "bwx" and m.group(4) == rec["launch_utc"][11:19] and D(m.group(3)) == D(rec["load1_at_launch"]),
         f"{where}: not the header line of the process of this record (tag, binary, launch time or load differs)")
    hl = [l for l in fl[i + 1:rec["line"]] if l.startswith("# bwx:")]
    h = re.search(r" start=(\w+) .*\bcount=(\d)\b", hl[0]) if len(hl) == 1 else None
    need(h and h.group(1) == rec["start"] and int(h.group(2)) == rec["count"] and f"--start {rec['start']}" in m.group(5),
         f"{where}: the start option or the counter setting of the csv header differs from the record")
    sq = re.search(r"--seq (\S+)", m.group(5))
    need(sq, f"{where}: no kernel sequence in the header line")
    return dict(line=i + 1, start=h.group(1), count=int(h.group(2)), seq=sq.group(1), dataset=rec["dataset"], tag=rec["tag"], launch=rec["launch_utc"], load=D(rec["load1_at_launch"]))


X_HEAD = {}
for r in OTHER:
    if r["proc_key"] not in X_HEAD:
        X_HEAD[r["proc_key"]] = bwx_header(r)
X_POOL_HEAD = [h for h in X_HEAD.values() if h["dataset"] in BWX_POOL]
X_REV_HEAD = [h for h in X_HEAD.values() if h["dataset"] not in BWX_POOL]
need(len(X_POOL_HEAD) == 24 and len(X_REV_HEAD) == 4, "runner bwx: expected 24 + 4 processes with a header line")
need({d: sorted({h["count"] for h in X_POOL_HEAD if h["dataset"] == d}) for d in BWX_POOL} == {"B7a": [0], "B7b": [0], "C3a": [1], "C3b": [1]},
     "runner bwx: the counter setting is not 0 in the two B7 folders and 1 in the two C3 folders")
need(all(X_FILES_ := [sorted({r["folder"] for r in OTHER if r["dataset"] == d}) for d in BWX_POOL]) and [f[0][:5] for f in X_FILES_] == ["R/B7-", "R/B7-", "R/C3-", "R/C3-"],
     "runner bwx: the four datasets are not two B7 folders and two C3 folders")
X_OFFSET = sum(1 for h in X_POOL_HEAD if h["start"] == "offset")
need(X_OFFSET == 12 and {h["start"] for h in X_POOL_HEAD} == {"common", "offset"} and all((h["start"] == "offset") == ("-offset-" in h["tag"]) for h in X_POOL_HEAD),
     "runner bwx: not 12 of the 24 processes with the start option 'offset'")
# part C: the same two settings, from the one "# bwx:" line of each csv file and from the launch line
for fo in C_FOLDERS:
    r0 = [r for r in C_OLD if r["folder"] == fo][0]
    hl = [l for l in file_lines(r0) if l.startswith("# bwx:")]
    need(len(hl) == 1 and " start=common " in hl[0] and re.search(r"\bcount=1\b", hl[0]) and "--start common" in launch_args(fo, r0["file"][:-4]) and "--count" in launch_args(fo, r0["file"][:-4]).split(),
         f"{fo}: part C did not run with the start option 'common' and with counters")
need(all(r["count"] == 1 and r["start"] == "common" for r in C_OLD + C_READ + C_ASM), "part C: a record holds another start option or counter setting")
# the kernel sequence of the 24 bwx processes: 8 kernels, the order of cfwd at its start and the order of crev at its end
X_SEQ = {h["seq"] for h in X_POOL_HEAD}
need(len(X_SEQ) == 1, f"runner bwx, tags common-6000-*: not one kernel sequence: {sorted(X_SEQ)}")
X_SEQ = next(iter(X_SEQ)).split(",")
need(len(X_SEQ) == 8 and ",".join(X_SEQ[:3]) == SPEC["cfwd"][2] and ",".join(X_SEQ[-3:]) == SPEC["crev"][2],
     "runner bwx, tags common-6000-*: the sequence does not hold the order of cfwd at its start and the order of crev at its end")
check(True, f"rows of runner bwx: {len(X_HEAD)} header lines agree with the records (tag, launch time, load, start option, counter setting); counter setting 0 in the two B7 folders and 1 in the two C3 folders; "
            f"{X_OFFSET} of {len(X_POOL_HEAD)} processes with the start option 'offset'; part C: start option 'common' and counters in 4 of 4 csv headers; "
            f"sequence of {len(X_SEQ)} kernels with the order of cfwd at positions 0 to 2 and the order of crev at positions 5 to 7")


# rows that the rules file quotes and that are not rows of the list. Each one ran the argument line of part L once on 2026-11-17, in a boot of its own:
# X2d12 (12 modules, rules V2 point 4 and F2 point 2 against rule V4) and three boots with 10 modules (rule V1 points 3 and 4). Checked here in the raw files.
def klog_boot(name):
    """First and last time, module count and its line number of a saved kernel log of 2026-11-17."""
    path = f"{R}/dimm-check-20261117/{name}.txt"
    ll = lines_of(path)
    a, b = re.match(r"^Nov 17 (\d\d:\d\d:\d\d) ", ll[0]), re.match(r"^Nov 17 (\d\d:\d\d:\d\d) ", ll[-1])
    n = [(i, int(m.group(1))) for i, l in enumerate(ll, 1) for m in [re.search(r"ghes_edac: This system has (\d+) DIMM sockets", l)] if m]
    need(a and b and len(n) == 1, f"{path}: no times of 2026-11-17 in the first and last line, or no single module count line")
    return dict(path=path, t0=a.group(1), t1=b.group(1), modules=n[0][1], line=n[0][0], last=len(ll))


EXTRA = {}
for d_, kname in (("X1d10", "k-4"), ("X1d10b", "k-3"), ("X2d12", "k-2"), ("BASEd10", "k-1")):
    o_ = expect(sel(dataset=d_, kernel="oldread", pos=0), 2, 1, f"{d_}, oldread at position 0")
    a_ = expect(sel(dataset=d_, kernel="asmread", pos=1), 2, 1, f"{d_}, asmread at position 1")
    kb = klog_boot(kname)
    fo = o_[0]["folder"]
    ll_ = lines_of(fo.replace("R/", R + "/", 1) + "/launches.txt")
    m1, m2 = re.match(rf"^launch {LINE_L} utc (\S+) load (\S+) ", ll_[0]), re.match(rf"^rc 0 {LINE_L} utc (\S+)$", ll_[1])
    need(m1 and m2, f"{d_}: launch or 'rc 0' line of the part L line not found in lines 1 and 2 of launches.txt")
    need(all(r["folder"] == fo and r["file"] == LINE_L + ".csv" and r["binary"] == "bwx12" and r["speed_MTps"] == 8000 and r["stop"] == "common" and r["min_ms"] == 6000
             and r["modules"] == kb["modules"] and r["launch_utc"] == f"2026-11-17T{m1.group(1)}Z" and D(r["load1_at_launch"]) == D(m1.group(2)) for r in o_ + a_)
         and {r["proc_key"] for r in o_} == {r["proc_key"] for r in a_} and {r["kernel_before"] for r in a_} == {"oldread"},
         f"{d_}: a record is not a 6 s common-stop interval of bwx12 at 8000 MT/s with the module count of the kernel log, or its launch differs from launches.txt")
    need(launch_args(fo, LINE_L) == SPEC["like"][1], f"{d_}: the process did not run the argument line of part L")
    need(kb["t0"] < m1.group(1) < m2.group(1) < kb["t1"] and BOOT8_TO[11:19] < kb["t0"] and BOOT8_TO[:10] == "2026-11-17",
         f"{d_}: the process does not lie inside the kernel log {kname}.txt, or that boot does not start after the end of the 8000 MT/s boot of the list rows")
    bs_ = {r["boot"] for r in o_ + a_}
    need(len(bs_) == 1, f"{d_}: the records name more than one boot")
    EXTRA[d_] = dict(old=o_, asm=a_, klog=kb, folder=fo, launch=m1.group(1), end=m2.group(1), load=D(m1.group(2)), boot=bs_.pop())
need(len({v["boot"] for v in EXTRA.values()} | {r["boot"] for r in EIGHT}) == 5, "X2d12 and the 10-module rows: not four boots of their own")
need(all(EXTRA[a]["klog"]["t1"] < EXTRA[b]["klog"]["t0"] for a, b in (("X1d10", "X1d10b"), ("X1d10b", "X2d12"), ("X2d12", "BASEd10"))), "X2d12 and the 10-module rows: the four kernel logs overlap in time")
need([EXTRA[d_]["klog"]["modules"] for d_ in ("X1d10", "X1d10b", "X2d12", "BASEd10")] == [10, 10, 12, 10], "X2d12 and the 10-module rows: module counts of the kernel logs")
# firmware settings on record at the start of each of these boots (times of the files set.txt, all of 2026-11-17)
need(X1_T < EXTRA["X1d10"]["klog"]["t0"] and EXTRA["X1d10b"]["klog"]["t0"] < X2_T, "X1d10, X1d10b: the boots did not start between the TXREQ Min change and the TXREQ Max change")
need(X2_T < EXTRA["X2d12"]["klog"]["t0"] and EXTRA["X2d12"]["end"] < RV_T, "X2d12: the boot did not start after both TXREQ changes, or the process did not end before the revert")
need(RV_T < EXTRA["BASEd10"]["klog"]["t0"], "BASEd10: the boot did not start after the revert of the TXREQ settings")
need(all(v["klog"]["t1"] < D72_T for v in EXTRA.values()), "X2d12 or a 10-module boot did not end before the change of DIMM Frequency to 7200 MT/s was written")
rX2_old, rX2_asm = Rg(EXTRA["X2d12"]["old"]), Rg(EXTRA["X2d12"]["asm"])
T10_ASM = [Rg(EXTRA[d_]["asm"]) for d_ in ("X1d10", "X1d10b")]
T10_APART = (max(g.med for g in T10_ASM) / min(g.med for g in T10_ASM) - 1) * 100       # percent of the lower median
rT10_old = Rg([r for d_ in ("X1d10", "X1d10b", "BASEd10") for r in EXTRA[d_]["old"]])
need(rT10_old.n == 6 and rT10_old.np == 3, "10-module boots, old read: not 6 intervals of 3 processes")
g0 = len(CHECKS)
xc_range("X2d12, old read kernel", rX2_old.lo, rX2_old.hi, facts_row("4.2", lambda r: r["Row"].startswith("X2d12") and "Min to max, GB/s" in r, "X2d12")["Min to max, GB/s"])
xc_range("X2d12, asmread", rX2_asm.lo, rX2_asm.hi, facts_row("4.4", lambda r: r["Row"].startswith("X2d12") and "Min to max, GB/s" in r, "X2d12")["Min to max, GB/s"])
m_ = re.search(rf"gave asmread ({NUM}) / ({NUM}) and ({NUM}) / ({NUM}) GB/s, ({NUM}) % apart", SEC["4.6"])
check(bool(m_) and all(near(q(v), m_.group(i + 1), "0.01") for i, v in enumerate(T10_ASM[0].v + T10_ASM[1].v)) and near(q(T10_APART, "0.1"), m_.group(5), "0.1"),
      f"10-module boots, asmread: computed {' / '.join(f2(v) for v in T10_ASM[0].v)} and {' / '.join(f2(v) for v in T10_ASM[1].v)} GB/s, {f1(T10_APART)} % apart, "
      + (f"FACTS.md {m_.group(1)} / {m_.group(2)} and {m_.group(3)} / {m_.group(4)} GB/s, {m_.group(5)} % apart" if m_ else "sentence not found in FACTS.md section 4.6"))
m_ = re.search(rf"three 10-module boots gave old read ({NUM}) to ({NUM}) GB/s \(({NUM}) % wide, {rT10_old.n} intervals / {rT10_old.np} processes / 3 boots\)", SEC["4.6"])
check(bool(m_) and near(q(rT10_old.lo), m_.group(1), "0.01") and near(q(rT10_old.hi), m_.group(2), "0.01") and near(q(width_pct(rT10_old), "0.1"), m_.group(3), "0.1"),
      f"10-module boots, old read: computed {rT10_old.txt()} GB/s, {f1(width_pct(rT10_old))} % wide, "
      + (f"FACTS.md {m_.group(1)} to {m_.group(2)} GB/s, {m_.group(3)} % wide" if m_ else "sentence not found in FACTS.md section 4.6"))
grouped("FACTS.md sections 4.2, 4.4 and 4.6, rows quoted by the rules file and not used for a wording: X2d12 (2 ranges), 10-module boots (4 asmread values, 1 old read range, 2 percent values)", g0)
check(True, f"X2d12 and the three 10-module boots: each process ran the argument line of part L inside its own saved kernel log (k-4, k-3, k-2, k-1: {', '.join(str(EXTRA[d_]['klog']['modules']) for d_ in ('X1d10', 'X1d10b', 'X2d12', 'BASEd10'))} modules); "
            f"settings on record at the start of the boots: TXREQ Min changed (2 boots with 10 modules), TXREQ Min and TXREQ Max changed (X2d12), both set back (third boot with 10 modules)")
# the two decisions of the facts sheet that this page follows were made after the numbers were seen (decisions (k) and (r) of its section 2)
m_ = re.search(r"Decisions made while this sheet was built, after the numbers were seen:\n(.*?)\n## ", FMD, re.S)
need(m_ and re.search(r"^- \(k\) Range of the 8000 MT/s side", m_.group(1), re.M) and re.search(r"^- \(r\) Part C against 8000 MT/s", m_.group(1), re.M),
     "FACTS.md section 2: decisions (k) and (r) are not listed under the decisions made after the numbers were seen")

# the one-thread phase of the test of 2026-11-13 (rule F1 point 5): header lines of one-thread.csv, in the folder of row A-1
ONE = R + "/kernels-20261113T181222Z/one-thread.csv"
need(B_A_OLD["A-1"][0]["folder"] == "R/kernels-20261113T181222Z", "row A-1 is not in the folder of the one-thread file")
one_h = [l for l in lines_of(ONE) if l.startswith("-- ")]
one_t = [re.search(r" utc (\d\d:\d\d:\d\d)$", l) for l in one_h]
need(one_h and all(one_t) and all(" threads 1 " in l for l in one_h), "one-thread.csv: a header line is not a one-thread process with a launch time")
ONE_N, ONE_FIRST, ONE_LAST = len(one_h), one_t[0].group(1), one_t[-1].group(1)
need([m.group(1) for m in one_t] == sorted(m.group(1) for m in one_t) and 0 <= secs(A1_FIRST) - secs(ONE_LAST) <= 1,
     "one-thread.csv: the launch times are not in order, or the 120-thread part did not start within 1 s of the last one-thread launch")
check(True, f"one-thread phase of 2026-11-13: {ONE_N} one-thread processes launched {ONE_FIRST} to {ONE_LAST}; first 120-thread process of row A-1 launched {A1_FIRST}")
# rule F1 point 5, third sentence: the old read kernel of rows A-1 and A-2 after one-thread work and directly after 120-thread work.
# In both csv files the round-1 process of bw_old read is the first process, and the round-2 process is the last one.
rA12_old = Rg(expect(B_A_OLD["A-1"] + B_A_OLD["A-2"], 12, 4, "rows A-1 and A-2, bw_old read"))
A12_GAP = []                                               # seconds from the launch of the process before the round-2 process to the launch of the round-2 process
for d_, heads_ in (("A-1", HA1), ("A-2", HA2)):
    need(sorted({r["_fproc"] for r in B_A_OLD[d_] if r["round"] == 1}) == [1] and sorted({r["_fproc"] for r in B_A_OLD[d_] if r["round"] == 2}) == [len(heads_)],
         f"{d_}: bw_old read is not the first process (round 1) and the last process (round 2) of the csv file")
    need(" binary bw_new " in heads_[-2][2] and re.search(r"kernel read\b", heads_[-2][2]) and "threads 120 " in heads_[-2][2],
         f"{d_}: the process before the last process of the csv file is not a 120-thread process of bw_new read")
    A12_GAP.append(secs(heads_[-1][1]) - secs(heads_[-2][1]))
need(all(0 < x <= 5 for x in A12_GAP), f"rows A-1 and A-2: the round-2 process of bw_old read did not start within 5 s of the launch of the process before it: {A12_GAP}")
# row A-2 started after one-thread work too: the run that ended before it (its own result folder) holds one-thread processes only
ONE2 = R + "/partA-20261113T204939Z"
one2_h = [l for f_ in ("A5.csv", "A6.csv") for l in lines_of(f"{ONE2}/{f_}") if l.startswith("-- ")]
one2_end = [m.group(1) for m in (re.match(r"^## end utc=2026-11-13T(\d\d:\d\d:\d\d)Z", l) for l in lines_of(ONE2 + "/env.txt")) if m]
need(one2_h and all(" --threads 1 " in l for l in one2_h) and len([l for l in lines_of(ONE2 + "/launches.txt") if l.startswith("== ")]) == len(one2_h)
     and sorted(f_ for f_ in os.listdir(ONE2) if f_.endswith(".csv")) == ["A5.csv", "A6.csv"] and len(one2_end) == 1 and 0 < secs(A2_FIRST) - secs(one2_end[0]) <= 10,
     "row A-2: the run before it does not hold one-thread processes only, or it did not end within 10 s before the first launch of row A-2")
xc_text_range("rule F1 point 5: old read kernel of rows A-1 and A-2", "1.5", rA12_old.lo, rA12_old.hi, "", "0.01", f2)
check(True, f"rule F1 point 5: bw_old read of rows A-1 and A-2 gave {rA12_old.txt()} GB/s ({n8000(rA12_old.recs)}). In both csv files round 1 is the first process and round 2 is the last one, "
            f"launched {A12_GAP[0]} s and {A12_GAP[1]} s after a 120-thread process of bw_new read. Row A-1 started within 1 s of the last launch of its one-thread phase. "
            f"Row A-2 started {secs(A2_FIRST) - secs(one2_end[0])} s after the end of a run of {len(one2_h)} one-thread processes")

# the earlier report does not establish the cause of the lower rate of the load-only loop
need(os.path.exists(EARLIER), f"the earlier report does not exist: {EARLIER}")
with open(EARLIER, encoding="utf-8") as f_:
    need("the rule inside the core that causes this is not established" in f_.read(), "the earlier report: the sentence 'not established' of its Short version was not found")

# ------------------------------------------------------------------ references
addref("facts", S + "/FACTS.md", "the detailed record of this rerun (facts sheet): every interval, every check, every decision")
addref("json", S + "/facts.json", "every interval as one record, built from the raw files. Data source of this page")
addref("rules", S + "/baselines-and-rules.txt", "the list of 8000 MT/s rows and the comparison rules V1 to V4, F1, F2, written before the run")
addref("gen", S + "/make_report.py", "script: generator of this page. It computes every rate from the records of facts.json and prints the self-check list. "
       "The records hold each rate of bwx12 and bwx rounded to 0.001 GB/s. Rounding such a value again to 0.01 GB/s can change the last digit. "
       "So the script sums the 120 thread rows that the record names and rounds the sum once. "
       "It reads the machine-state facts of section 4 from the raw files")
addref("build", S + "/build_facts.py", "script: builds FACTS.md and facts.json from the raw files")
addref("go", S + "/go.sh", "script: driver of the rerun. Three sessions of parts A, L, C and a fourth part C process")
addref("ra", S + "/ra.sh", "script: part A, the 120-thread part of the test of 2026-11-13 with the same two binaries")
addref("go2", S + "/go2.sh", "script: control I (added after the first numbers were seen), the part L line twice from an idle machine", "lines 2 and 24 to 33")
addref("like", S + "/like.spec", "argument line of part L")
addref("cfwd", S + "/cfwd.spec", "argument line of part C, order oldread, read, asmread")
addref("crev", S + "/crev.spec", "argument line of part C, order asmread, read, oldread")
addref("golog", GOLOG, "log of go.sh: 12 state lines, 10 'done' lines, ALLDONE")
addref("go2log", GO2LOG, "log of go2.sh (control I, added after the first numbers were seen): 6 state lines, ALLDONE")
for s_ in (1, 2, 3):
    addref(f"A{s_}", R + "/" + [r for r in A_OLD if r["session"] == s_][0]["folder"][2:] + "/threads120.csv", f"part A, session {s_}: interval rows")
for s_ in (1, 2, 3):
    addref(f"L{s_}", R + "/" + [r for r in L_OLD if r["session"] == s_][0]["folder"][2:] + "/a6456.csv", f"part L, session {s_}: interval rows")
for t_ in ("T72C1", "T72C2", "T72C3", "T72C4"):
    r0 = [r for r in C_OLD if r["tag"] == t_][0]
    addref(t_, R + "/" + r0["folder"][2:] + "/" + r0["file"], f"part C, process {t_}: interval rows")
for t_ in ("T72I1", "T72I2"):
    r0 = [r for r in I_OLD if r["tag"] == t_][0]
    addref(t_, R + "/" + r0["folder"][2:] + "/" + r0["file"], f"control I (added after the first numbers were seen), process {t_}: interval rows")
addref("F72", R + "/w120-w120-F72d12-20261117T200231Z/a6456.csv", "F72d12 (earlier run of the same boot, not part of the rerun): interval rows")
addref("F72l", FL, "F72d12 (earlier run of the same boot, not part of the rerun): launch time, load at launch and end of the process", "lines 1 and 2")
addref("F72e", F_ENV, "F72d12 (earlier run of the same boot, not part of the rerun): time and process list before the launch", f"lines 1 and {F_TOP[0]}")
addref("gaps", GAPS, "first and last kernel log line of the boot of the rerun, saved in that boot", "line 7")
for t_ in ("T72L1", "T72L2", "T72L3", "T72I1", "T72I2"):
    addref("env" + t_, VISIT_ENV[t_][0], ("part L" if "L" in t_ else "control I (added after the first numbers were seen)") + f", process {t_}: time and process list before the launch")
addref("A-1", R + "/kernels-20261113T181222Z/threads120.csv", "row A-1 (8000 MT/s): the test of 2026-11-13. Header lines with the launch times", f"first and last header: lines {HA1[0][0]} and {HA1[-1][0]}")
addref("A-2", R + "/partA-20261113T205055Z/A1.csv", "row A-2 (8000 MT/s): same binaries, other process order. Header lines with the launch times",
       f"headers of bw_new read round 1 and of {A2_OTHER}: lines {HA2[a2_new_r1[0]['_fproc'] - 1][0]} and {a2_other[0][0]}")
addref("A-3", R + "/partA-20261113T205055Z/A3.csv", "row A-3 (8000 MT/s): three processes of bw_old read (tags onebuf-ms500-1, -2, -3)",
       "headers in lines " + ", ".join(str(HA3[i - 1][0]) for i in a3_used) + f", next header in line {HA3[a3_used[-1]][0]}")
addref("L-1", R + "/w120-R8-20261117T020549Z/a6456.csv", "row L-1 (8000 MT/s): the argument line of part L")
addref("L-1l", R + "/w120-R8-20261117T020549Z/launches.txt", "row L-1: launch time with the argument line, and end of the process", "lines 1 and 2")
addref("L-2a", R + "/w120-R1-20261115T185140Z/p1nop.csv", "row L-2 (8000 MT/s), process p1nop")
addref("L-2b", R + "/w120-R1-20261115T185140Z/p2add.csv", "row L-2 (8000 MT/s), process p2add. It holds the lowest asmread interval of the pool. "
       f"Its interval row prints {f2(i_row_rate(LOWEST_ASM))} GB/s. This page uses the sum of the 120 thread rows, {f2(val(LOWEST_ASM))} GB/s",
       f"interval row in line {LOWEST_ASM['line']}, the 120 thread rows in the lines after it")
addref("L-2l", R + "/w120-R1-20261115T185140Z/launches.txt", "row L-2: launch times and ends of the two processes", "lines 1 to 4")
addref("L-3", R + "/w120-R5-20261115T203152Z/thp.csv", "row L-3 (8000 MT/s)")
addref("L-3l", R + "/w120-R5-20261115T203152Z/launches.txt", "row L-3: launch time and end of the process thp", "lines 3 and 4")
addref("L-4a", R + "/w120-R6-20261115T203438Z/st1.csv", "row L-4 (8000 MT/s), process st1")
addref("L-4b", R + "/w120-R6-20261115T203438Z/st2.csv", "row L-4 (8000 MT/s), process st2")
addref("L-4c", R + "/w120-R6-20261115T203438Z/st3.csv", "row L-4 (8000 MT/s), process st3")
addref("L-4l", R + "/w120-R6-20261115T203438Z/launches.txt", "row L-4: launch times and ends of the three processes", "lines 1 to 6")
addref("try6", TRY6, f"record of boot 3bfc57a1: time, boot id, MemTotal, kernel log line with the module count, the line \"modules={TRY6_MODLINE}\" (not the module count), "
       "12 x \"Configured Memory Speed: 7200 MT/s\"", "lines 1, 2, 4, 5, 6 and 7")
addref("dmi", DMI, "module list saved in boot 3bfc57a1: 12 entries \"Memory Device\", each with one line \"Configured Memory Speed: 7200 MT/s\"")
addref("boots", BOOTS, "boot list of the journal, saved in boot 3bfc57a1: row 0 is this boot", "line 9")
addref("journal", JOURNAL, "saved journal lines of the 8000 MT/s boot (started 2026-11-09): hardware error records",
       "lines " + ", ".join(str(x) for x in sorted([h["line"] for v in HW_ROWS.values() for h in v["recs"]] + [h["line"] for h in HW_A])))
addref("klog", KLOG, "saved kernel log of the 8000 MT/s boot (started 2026-11-09): first line, memory size line, module count line, last line",
       f"lines 1, {K12_MEM[0]}, {[i for i, l in enumerate(kl, 1) if 'This system has 12 DIMM sockets' in l][0]} and {len(kl)}")
addref("klog10", KLOG10, f"saved kernel log of the boot that started on {BOOT10_FROM} UTC: first line, memory size line, module count line",
       f"lines 1, {K10_MEM[0]} and {K10_LINE[0]}")
addref("x1", FW + "/x1/set.txt", "firmware setting change: TXREQ Min", "lines 1, 8, 9 and 18")
addref("x2", FW + "/x2/set.txt", "firmware setting change: TXREQ Max", "lines 1 and 2")
addref("rev", FW + "/revert/set.txt", "firmware settings set back: TXREQ Max and TXREQ Min", "lines 1, 2 and 4")
addref("qbase", R + "/uefisettings-20261117/questions.json", "firmware settings list of the 8000 MT/s boot")
addref("qrev", FW + "/revert/questions.json", "firmware settings list saved after the revert")
addref("d72", R + "/dimm7200-20261117/set.txt", "firmware setting change: DIMM Frequency = 7200 MT/s", "lines 7 and 8")
addref("earlier", EARLIER, "the earlier report (2026-11-15) on the lower whole-chip read rate of the load-only loop. Its Short version says that the cause is not established")
addref("one", ONE, "the one-thread phase of the test of 2026-11-13: one header line with the launch time per process", f"first and last header: lines {[i for i, l in enumerate(lines_of(ONE), 1) if l.startswith('-- ')][0]} and {[i for i, l in enumerate(lines_of(ONE), 1) if l.startswith('-- ')][-1]}")
addref("xX2d12", R + "/" + EXTRA["X2d12"]["folder"][2:] + "/" + LINE_L + ".csv", "row X2d12 (8000 MT/s, 12 modules, shown and not used): interval rows of the argument line of part L")
addref("xX2d12l", R + "/" + EXTRA["X2d12"]["folder"][2:] + "/launches.txt", "row X2d12: launch time with the argument line and the load, and end of the process", "lines 1 and 2")
addref("klogX2d12", EXTRA["X2d12"]["klog"]["path"], "saved kernel log of the boot of row X2d12: first line, module count line, last line",
       f"lines 1, {EXTRA['X2d12']['klog']['line']} and {EXTRA['X2d12']['klog']['last']}")
for d_ in ("X1d10", "X1d10b", "BASEd10"):
    addref("x" + d_, R + "/" + EXTRA[d_]["folder"][2:] + "/" + LINE_L + ".csv", f"boot with 10 modules at 8000 MT/s (folder tag {d_}, not a row of the list): interval rows of the argument line of part L")
for d_ in ("X1d10", "X1d10b"):
    addref("klog" + d_, EXTRA[d_]["klog"]["path"], f"saved kernel log of the boot of the folder tag {d_}: first line, module count line, last line",
           f"lines 1, {EXTRA[d_]['klog']['line']} and {EXTRA[d_]['klog']['last']}")
need(EXTRA["BASEd10"]["klog"]["path"] == KLOG10, "BASEd10: its kernel log is not the file of the reference klog10")
X_FILES = {}
for d_ in BWX_POOL + ("B5a-rev", "B5b-rev"):
    fs_ = sorted({(r["folder"], r["file"]) for r in OTHER if r["dataset"] == d_})
    need(len(fs_) == 1, f"runner bwx, {d_}: more than one csv file")
    X_FILES[d_] = fs_[0]
    what_ = ("rows of runner bwx (other binary, 8000 MT/s), tags common-6000-*" if d_ in BWX_POOL else
             "rows of runner bwx (other binary, 8000 MT/s), the two processes with another kernel order (tags b5-rev-*)")
    addref("x" + d_, R + "/" + fs_[0][0][2:] + "/" + fs_[0][1], what_ + ": interval rows. This page uses the sum of the 120 thread rows after an interval row")
need(len(set(X_FILES.values())) == 6, "runner bwx: the 6 datasets do not come from 6 csv files")
need(not {X_FILES[d_][0] for d_ in ("B5a-rev", "B5b-rev")} & {X_FILES[d_][0] for d_ in BWX_POOL} and Rg(X_REV_READ).procs == Rg(X_REV_ASM).procs,
     "runner bwx: the processes with the other kernel order are not the same 4 processes of two other result folders")

# ------------------------------------------------------------------ small HTML helpers
CI = "control I (added after the first numbers were seen)"
F72 = "F72d12 (earlier run of the same boot, not part of the rerun)"


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r'<span class="ref">.*?</span>', " ", s)))


def P(text, cls=None):
    PROSE.append(text)
    return f'<p{" class=" + chr(34) + cls + chr(34) if cls else ""}>{text}</p>'


def UL(items):
    PROSE.extend(items)
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


WIDE = ("q1", "q2", "state", "load", "visits", "detail")        # tables with a fixed least width of 900 px (see the style block)


def table(head, rows, cls=""):
    o = ['<p class="hint ht">If the table does not fit the screen, scroll it sideways.</p>' if cls in WIDE else ""]
    o += [f'<div class="tw"><table class="{cls}"><thead><tr>']
    o += [f'<th{" class=n" if c.startswith("#") else ""}>{c.lstrip("#")}</th>' for c in head]
    o.append("</tr></thead><tbody>")
    for r in rows:
        if isinstance(r, str):
            o.append(f'<tr class="grp"><td colspan="{len(head)}">{r}</td></tr>')
            continue
        o.append("<tr>" + "".join(f'<td{" class=n" if head[i].startswith("#") else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>")
    o.append("</tbody></table></div>")
    return "".join(o)


def small(s):
    return f'<span class="sm">{s}</span>'


# ------------------------------------------------------------------ figure 1: dumbbell
def T(x, y, s, size=12, fill=INK, anchor="start", weight=None, extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}>{esc(s)}</text>'


HALO = f' paint-order="stroke" stroke="{SURF}" stroke-width="3.5" stroke-linejoin="round"'
TAB = ' style="font-variant-numeric:tabular-nums"'


def marker(x, y, color, hollow, r=5.5):
    """A hollow marker (8000 MT/s) carries its colour in the stroke. The hover style must not replace that stroke (classes ho and fi)."""
    if hollow:
        return f'<circle class="mk ho" cx="{x:.1f}" cy="{y:.1f}" r="{r - 0.9:.1f}" fill="{SURF}" stroke="{color}" stroke-width="2.2"/>'
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 1.6:.1f}" fill="{SURF}"/>'
            f'<circle class="mk fi" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}"/>')


def kernel_name(recs):
    r = recs[0]
    if r["part"] == "A":
        return f"{r['binary']} read ({'old' if r['binary'] == 'bw_old' else 'new'} read kernel)"
    return {"oldread": "oldread (old read kernel)", "read": "read (new read kernel)",
            "asmread": "asmread (in place of the new read kernel)"}[r["kernel"]]


def dot_title(name, rg):
    vals = ", ".join(f2(v) for v in rg.v)
    return (f"{name}: {kernel_name(rg.recs)}. Median {f2(rg.med)} GB/s. Intervals: {vals} GB/s. "
            f"n = {plural(rg.n, 'interval')} / {plural(rg.np, 'process')}. Source: {src(rg.recs)}.")


def f1_row(name, notes, old, new, drops, hollow, how):
    return dict(name=name, notes=notes, old=old, new=new, drops=drops, hollow=hollow, how=how)


def bwx_row(name, notes, olds, news, hollow=False):
    pr = pairs_in_process(olds, news)
    return f1_row(name, notes, Rg([o for o, _ in pr]), Rg([n for _, n in pr]), drops_of(pr), hollow,
                  "lowest and highest pair of the same process and round")


IN_PLACE = "asmread in place of the new read kernel"
B1_8000 = [bwx_row(f"L-1 · {hm(B_L_OLD['L-1'][0]['launch_utc'], True)}", [IN_PLACE, "row with the argument line of part L"], olds=B_L_OLD["L-1"], news=B_L_ASM["L-1"], hollow=True)]
B1_7200 = [bwx_row(f"F72d12 · {hm(F_OLD[0]['launch_utc'])}", [IN_PLACE, "earlier run of the same boot, not part of the rerun"], olds=F_OLD, news=F_ASM)]
for s_ in (1, 2, 3):
    o_ = [r for r in L_OLD if r["session"] == s_]
    B1_7200.append(bwx_row(f"Part L, session {s_} ({o_[0]['tag']})", [IN_PLACE], olds=o_, news=[r for r in L_ASM if r["session"] == s_]))
for t_ in ("T72C1", "T72C2", "T72C3", "T72C4"):
    o_ = [r for r in C_OLD if r["tag"] == t_]
    n_ = [r for r in C_READ if r["tag"] == t_]
    B1_7200.append(bwx_row(f"Part C, {t_} ({o_[0]['file'][:-4]})", [f"kernel read = the new read kernel, after {n_[0]['kernel_before']}"], olds=o_, news=n_))
for t_ in ("T72I1", "T72I2"):
    B1_7200.append(bwx_row(f"Control I, {t_}", [IN_PLACE, "added after the first numbers were seen"],
                           olds=[r for r in I_OLD if r["tag"] == t_], news=[r for r in I_ASM if r["tag"] == t_]))
B2_8000 = [f1_row(f"{d}, round {rnd} · {hm(p['old'].recs[0]['launch_utc'], True)}", ["bw_new read against bw_old read"], p["old"], p["new"], [p["drop"]], True,
                  "between the medians of the two processes")
           for (d, rnd), p in A8_PAIRS.items()]
B2_7200 = [f1_row(f"Part A, session {s_}, round {rnd} (T72A{s_})", ["bw_new read against bw_old read"], p["old"], p["new"], [p["drop"]], False,
                  "between the medians of the two processes")
           for (s_, rnd), p in A_PAIRS.items()]
F1_BLOCKS = [
    dict(title="6 s measurements, runner bwx12, all threads stop together", lines=["6 s measurements, runner bwx12,", "all threads stop together"],
         groups=[dict(title="8000 MT/s · hollow markers", rows=B1_8000), dict(title="7200 MT/s · filled markers", rows=B1_7200)]),
    dict(title="0.5 s measurements, the two binaries of 2026-11-13, each thread finishes its pass",
         lines=["0.5 s measurements, the two binaries of", "2026-11-13, each thread finishes its pass"],
         groups=[dict(title="8000 MT/s · hollow markers", rows=B2_8000), dict(title="7200 MT/s · filled markers", rows=B2_7200)]),
]
SAME_LINE_ROWS = [r for r in B1_7200 if not r["name"].startswith("Part C")]
need(len(SAME_LINE_ROWS) == 6, "figure 1: expected 6 rows of the argument line of part L in the 7200 MT/s boot")
F1_NROWS = sum(len(g["rows"]) for b in F1_BLOCKS for g in b["groups"])
need(F1_NROWS == 21, "figure 1: expected 21 rows")


def fig1(layout="wide"):
    """The dumbbell chart in one of three layouts, so that it never scrolls sideways.
    wide (940 px, windows from 1000 px) and mid (726 px, windows from 780 px): row names in a column at the left.
    narrow (386 px, windows below 780 px): the row name stands above its dumbbell, so the chart fits into a 420 px wide window."""
    narrow = layout == "narrow"
    W, X0, X1 = {"wide": (940, 356, 846), "mid": (726, 300, 646), "narrow": (386, 26, 332)}[layout]
    XMAX = 500
    sx = lambda v: X0 + (X1 - X0) * float(v) / XMAX

    def drawn(notes):
        """The note lines as this layout draws them. The mid layout has a label column of 300 px:
        a note of more than 44 characters is broken after its comma, so that it ends before the 0 gridline."""
        if layout != "mid":
            return list(notes)
        out = []
        for nt in notes:
            if len(nt) > 44:
                need(", " in nt, f"figure 1, mid layout: the note '{nt}' is too long and has no comma to break at")
                a, b_ = nt.split(", ", 1)
                out += [a + ",", b_]
            else:
                out.append(nt)
        return out
    y = 30
    for b in F1_BLOCKS:
        b["tl"] = b["lines"] if narrow else [b["title"]]
        b["y"] = y
        b["th"] = 10 + 16 * len(b["tl"])
        y += b["th"] + 4
        for g in b["groups"]:
            g["y"] = y
            y += 22
            for r in g["rows"]:
                r["dn"] = drawn(r["notes"])
                r["h"] = 52 + 13 * len(r["dn"]) if narrow else 22 + 13 * len(r["dn"])
                r["y"] = y
                y += r["h"]
        y += 6
    yb = y
    H = yb + (64 if narrow else 50)
    o = [f'<svg class="{dict(wide="f1w", mid="f1m", narrow="f1n")[layout]}" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Dumbbell chart: whole-chip read rate of the old read kernel and of the load-only loop, one row per bwx12 process or per round of the two part A binaries, {F1_NROWS} rows">']
    for t in range(0, XMAX + 1, 100):
        o.append(f'<line x1="{sx(t):.1f}" y1="24" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}"/>')
        o.append(T(sx(t), 17, t, 12, MUTED, "middle", extra=TAB))
        o.append(T(sx(t), yb + 16, t, 12, MUTED, "middle", extra=TAB))
    o.append(T(sx(XMAX) + 15, 17, "GB/s", 12, MUTED))
    if narrow:
        o.append(T(W / 2, yb + 36, "Whole-chip read rate, GB/s", 12.5, MUTED, "middle"))
        o.append(T(W / 2, yb + 52, "The axis starts at 0.", 12.5, MUTED, "middle"))
    else:
        o.append(T((X0 + X1) / 2, yb + 38, "Whole-chip read rate, GB/s. The axis starts at 0.", 12.5, MUTED, "middle"))
    for b in F1_BLOCKS:
        o.append(f'<rect x="0" y="{b["y"]}" width="{W}" height="{b["th"]}" fill="#f1f0ec"/>')
        for i, tl in enumerate(b["tl"]):
            o.append(T(8 if narrow else 12, b["y"] + 17.5 + 16 * i, tl, 13, INK, weight=600))
        for g in b["groups"]:
            o.append(T(8 if narrow else 12, g["y"] + 15, g["title"], 12, MUTED, weight=600, extra=HALO))
            for r in g["rows"]:
                if narrow:
                    ty = r["y"] + 14
                    cy = r["y"] + r["h"] - 13
                    o.append(f'<line x1="0" y1="{r["y"] + r["h"]}" x2="{W}" y2="{r["y"] + r["h"]}" stroke="{GRID}" stroke-opacity="0.6"/>')
                else:
                    cy = r["y"] + r["h"] / 2
                    ty = cy - 6.5 * len(r["dn"]) + 4
                tx = 12 if narrow else 24
                o.append(T(tx, ty, r["name"], 12.5, INK, extra=HALO))
                for i, nt in enumerate(r["dn"]):
                    o.append(T(tx, ty + 13 * (i + 1), nt, 11, MUTED, extra=HALO))
                xo, xn = sx(r["old"].med), sx(r["new"].med)
                dt = drop_txt(r["drops"])
                tipname = ", ".join([r["name"]] + r["notes"])
                o.append(f'<g><title>{esc(tipname)}: drop of the load-only loop below the old read kernel: {esc(dt)} ({esc(r["how"])}, n = {plural(len(r["drops"]), "pair")}). Source: {esc(src(r["old"].recs + r["new"].recs))}.</title>'
                         f'<line x1="{xn:.1f}" y1="{cy:.1f}" x2="{xo:.1f}" y2="{cy:.1f}" stroke="{LINK}" stroke-width="1.5"/>'
                         f'<line x1="{xn:.1f}" y1="{cy:.1f}" x2="{xo:.1f}" y2="{cy:.1f}" stroke="{SURF}" stroke-opacity="0" stroke-width="14"/>'
                         + T((xo + xn) / 2, cy - 7, dt, 11 if narrow else 11.5, INK, "middle", extra=HALO + TAB) + "</g>")
                for rg, x, color, side in ((r["old"], xo, BLUE, 1), (r["new"], xn, ORANGE, -1)):
                    xa, xb = sx(rg.lo), sx(rg.hi)
                    o.append(f'<g class="pt"><title>{esc(dot_title(tipname, rg))}</title>'
                             f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="12" fill="{SURF}" fill-opacity="0"/>'
                             + marker(x, cy, color, r["hollow"])
                             + f'<path d="M{xa:.1f} {cy - 3.5:.1f}V{cy + 3.5:.1f}M{xb:.1f} {cy - 3.5:.1f}V{cy + 3.5:.1f}M{xa:.1f} {cy:.1f}H{xb:.1f}" stroke="{INK}" stroke-width="1.1" fill="none"/></g>')
                    off = max(xb - x, x - xa) + 8
                    o.append(T(x + side * max(off, 10.5), cy + 4.2, f2(rg.med), 12, INK, "start" if side > 0 else "end", extra=HALO + TAB))
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ figure 2: every interval, two panels
def beeswarm(xs, r=4.3):
    """Vertical offsets so that dots of one row do not cover each other."""
    lanes = [0, -5.5, 5.5, -11, 11]
    placed, out = [], [0.0] * len(xs)
    for i in sorted(range(len(xs)), key=lambda k: xs[k]):
        for ln in lanes:
            if all(abs(xs[i] - px) >= 2 * r or ln != pl for px, pl in placed):
                break
        placed.append((xs[i], ln))
        out[i] = ln
    return out


def p_row(name, recs, hollow, notes=(), label=None, band=None, more=()):
    """One row of figure 2. With band (the 8000 MT/s range of the block) the row gets a note with its place against the band.
    The rate is on the horizontal axis, so a higher row lies to the right of the band.
    A note that starts with "!" is drawn in ink colour: it is the key distance of the row.
    A note that starts with "~" only repeats a part of the row name: it is drawn under the short label of the figure
    and left out of the tooltip, which shows the full row name. "|" is a line break inside one note."""
    rg = Rg(recs)
    notes = list(notes)
    if band is not None:
        d = rg.nearest(band)
        notes.append("!inside the band" if band.lo <= rg.lo and rg.hi <= band.hi else
                     f"!{f2(abs(d))} GB/s {'higher|(right' if d > 0 else 'lower|(left'} of the band)" if d != 0 else "!overlaps the band")
    notes += list(more)
    return dict(name=name, rg=rg, hollow=hollow, notes=notes, label=label or name)


def plain_notes(notes, tooltip=False):
    """The notes of a row as plain text. For a tooltip the notes that only repeat the row name are left out."""
    return [n.lstrip("!~").replace("|", " ") for n in notes if not (tooltip and n.startswith("~"))]


def note_lines(notes):
    """(text, strong) for every drawn line of the notes of a row."""
    return [(seg, n.startswith("!")) for n in notes for seg in n.lstrip("!~").split("|")]


F2_GAPS = []         # per panel of figure 2: (title, number of dots, smallest distance of two dots in px, hover areas cut by a neighbour, areas of all hover areas in px2)
HIT_R = 12.0         # radius of the hover area of a free-standing dot: 24 px across


def hit_cell(i, pts, nseg=32):
    """The hover area of dot i: the part of a circle of radius HIT_R around the dot that is nearer to it than to any other dot.
    The circle is a polygon of nseg corners. The half-way line to every dot within 2 x HIT_R cuts it (a Voronoi cell, clipped to the circle).
    So the areas of two dots never overlap, and the pointer only has to be nearest to a dot. Returns (corners, cut by a neighbour)."""
    x0, y0 = pts[i]
    poly = [(x0 + HIT_R * math.cos(2 * math.pi * k / nseg), y0 + HIT_R * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)]
    cut = False
    for j, (x1, y1) in enumerate(pts):
        dx, dy = x1 - x0, y1 - y0
        if j == i or dx * dx + dy * dy >= (2 * HIT_R) ** 2:
            continue
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        side = [(px - mx) * dx + (py - my) * dy for px, py in poly]          # above 0: nearer to the other dot
        out = []
        for k, a in enumerate(poly):
            b, sa, sb = poly[(k + 1) % len(poly)], side[k], side[(k + 1) % len(poly)]
            if sa <= 0:
                out.append(a)
            if (sa < 0 < sb) or (sb < 0 < sa):
                t = sa / (sa - sb)
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        cut = cut or len(out) != len(poly) or any(v > 0 for v in side)
        poly = out
        need(len(poly) >= 3, "figure 2: a hover area is empty")
    return poly, cut


def poly_area(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def panel(title, sub, lo, hi, majors, minors, blocks, color, aria):
    W, X0, X1 = 466, 190, 450
    sx = lambda v: X0 + (X1 - X0) * (float(v) - lo) / (hi - lo)
    y = 98
    for b in blocks:
        b["y"] = y
        y += 22 + 13 * len(b["band_txt"])
        for g in b["groups"]:
            g["y"] = y
            y += 20 + 12 * len(g.get("sub", ()))
            for r in g["rows"]:
                r["h"] = max(30, 8 + 13 * (2 + len(note_lines(r["notes"]))))
                r["y"] = y
                y += r["h"]
        b["yend"] = y
        y += 8
    yb = y
    H = yb + 56
    # Place every dot first. Then give each dot its hover area: the part of a 12 px circle that is nearer to it than to any other dot.
    # So the hover areas do not overlap, and the pointer only has to be nearest to a dot (a free-standing dot has a target of 24 px).
    placed = []
    for b in blocks:
        for g in b["groups"]:
            for r in g["rows"]:
                xs = [sx(v) for v in r["rg"].v]
                r["dots"] = [(rec, x, r["y"] + r["h"] / 2 + dy, len(placed) + i) for i, (rec, x, dy) in enumerate(zip(r["rg"].recs, xs, beeswarm(xs)))]
                placed += [(x, y_) for _, x, y_, _ in r["dots"]]
    gap = [min(((x - a) ** 2 + (y_ - c) ** 2) ** 0.5 for j, (a, c) in enumerate(placed) if j != i) for i, (x, y_) in enumerate(placed)]
    # 5.2 px is the outer radius of the largest mark while the pointer is on it (hollow mark: r 3.4 plus half of the 3.6 px hover stroke).
    # A filled mark has r 4.3, a surface ring up to r 4.9 under it, and a hover stroke up to r 5.1.
    need(min(gap) > 5.2, f"figure 2, panel '{title}': two dots are {min(gap):.2f} px apart, so one mark covers the centre of the other")
    cells = [hit_cell(i, placed) for i in range(len(placed))]
    F2_GAPS.append((title, len(placed), min(gap), sum(1 for _, cut in cells if cut), [poly_area(c) for c, _ in cells]))
    o = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(aria)}">']
    o.append(T(10, 18, title, 13.5, INK, weight=600))
    o.append(T(10, 33, sub, 11.5, MUTED))
    o.append(T(10, 48, "x axis: whole-chip read rate, GB/s.", 11.5, MUTED))
    o.append(T(10, 62, f"The axis starts at {lo} GB/s, not at 0.", 11.5, INK, weight=600))
    o.append(T(10, 77, "under a row name: lowest to", 10.5, MUTED))
    o.append(T(10, 89, "highest, GB/s (n intervals)", 10.5, MUTED))
    # The grey bands come first, and the grid lines are drawn over them. The grid colour is close to the band colour,
    # so each grid line is drawn again inside a band in a darker tone. A dot inside a band can then be read against a line.
    boxes = []
    for b in blocks:
        on = [g for g in b["groups"] if g.get("band")]
        if b.get("band") and on:
            y0, y1 = on[0]["y"] + 2, on[-1]["rows"][-1]["y"] + on[-1]["rows"][-1]["h"]
            xa, xb = sx(b["band"].lo), sx(b["band"].hi)
            boxes.append((xa, xb, y0, y1))
            o.append(f'<g><title>{esc(b["band_title"])}</title><rect x="{xa:.1f}" y="{y0}" width="{xb - xa:.1f}" height="{y1 - y0}" fill="{BAND}"/>'
                     f'<path d="M{xa:.1f} {y0}V{y1}M{xb:.1f} {y0}V{y1}" stroke="{BAND_EDGE}"/></g>')
    for t in minors:
        o.append(f'<line x1="{sx(t):.1f}" y1="94" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}" stroke-opacity="0.55"/>')
    for t in majors:
        o.append(f'<line x1="{sx(t):.1f}" y1="94" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}"/>')
        o.append(T(sx(t), 88, t, 11.5, MUTED, "middle", extra=TAB))
        o.append(T(sx(t), yb + 16, t, 11.5, MUTED, "middle", extra=TAB))
    for xa, xb, y0, y1 in boxes:
        for t in sorted(set(minors) | set(majors)):
            if xa + 3 < sx(t) < xb - 3:                 # a line within 3 px of a band edge would look like a second edge
                o.append(f'<line x1="{sx(t):.1f}" y1="{y0}" x2="{sx(t):.1f}" y2="{y1}" stroke="{BAND_EDGE}" stroke-opacity="{0.6 if t in majors else 0.32}" pointer-events="none"/>')
    # axis line with a break mark: the axis does not start at 0
    o.append(f'<path d="M{X0 - 14} {yb}h5l3 -5l4 10l3 -5H{X1}" stroke="{MUTED}" fill="none"/>')
    o.append(T((X0 + X1) / 2 - 20, yb + 34, "Whole-chip read rate, GB/s", 12, MUTED, "middle"))
    o.append(T((X0 + X1) / 2 - 20, yb + 49, f"The axis starts at {lo} GB/s, not at 0.", 12, INK, "middle", weight=600))
    for b in blocks:
        o.append(f'<rect x="0" y="{b["y"]}" width="{W}" height="{18 + 13 * len(b["band_txt"])}" fill="#f1f0ec"/>')
        o.append(T(10, b["y"] + 15, b["title"], 12.5, INK, weight=600))
        for i, bt in enumerate(b["band_txt"]):
            o.append(T(10, b["y"] + 29 + 13 * i, bt, 10.5, MUTED))
        for g in b["groups"]:
            o.append(T(10, g["y"] + 14, g["title"], 11.5, MUTED, weight=600, extra=HALO))
            for i, st in enumerate(g.get("sub", ())):
                o.append(T(10, g["y"] + 26 + 12 * i, st, 10.5, MUTED))
            for r in g["rows"]:
                cy = r["y"] + r["h"] / 2
                nl = 2 + len(note_lines(r["notes"]))
                ty = cy - 6.5 * (nl - 1) + 4
                o.append(T(18, ty, r["label"], 12, INK))
                o.append(T(18, ty + 13, f"{r['rg'].txt()} ({r['rg'].n})", 10.5, MUTED, extra=TAB))
                for i, (nt, strong) in enumerate(note_lines(r["notes"])):
                    o.append(T(18, ty + 13 * (i + 2), nt, 10.5, INK if strong else MUTED, weight=600 if strong else None))
                o.append(f'<line x1="{X0}" y1="{r["y"] + r["h"]}" x2="{X1}" y2="{r["y"] + r["h"]}" stroke="{GRID}" stroke-opacity="0.6"/>')
                for rec, x, yd, di in r["dots"]:
                    cell = "M" + "L".join(f"{cx_:.1f} {cy_:.1f}" for cx_, cy_ in cells[di][0]) + "Z"
                    kb = rec["kernel_before"]
                    if rec["part"] == "A" and rec["dataset"] == "A-3":
                        # row A-3 has no rounds: the number at the end of the tag counts the three repeats of the process
                        where = f"process {rec['_fproc']} of the file (tag {rec['tag']}), interval {rec['interval'] + 1}"
                    elif rec["part"] == "A":
                        where = f"process {rec['_fproc']} of the file, round {rec['round']}, interval {rec['interval'] + 1}"
                    else:
                        after = ("no kernel ran before it" if kb.startswith("none") else
                                 f"directly after {kb}" + ("" if kb in ("oldread", "read", "asmread") else " (another test loop of bwx12)"))
                        where = f"process {rec['tag']}, round {rec['round']}, position {rec['pos']}, {after}"
                    tipname = ", ".join([r["name"]] + plain_notes(r["notes"], tooltip=True))
                    tip = (f"{tipname}: {kernel_name([rec])}, {where}: {f2(val(rec))} GB/s. "
                           f"Row: {r['rg'].txt()} GB/s, n = {plural(r['rg'].n, 'interval')} / {plural(r['rg'].np, 'process')}. "
                           f"Source: {src([rec])}.")
                    # Both kinds of mark are 8.6 px across: the hollow one with its stroke, the filled one without a stroke on its edge.
                    # The filled mark has a surface-coloured ring of 0.6 px under it (r 4.9), which separates it from a dot that it overlaps.
                    # Only the hover area takes the pointer, not the painted mark. So where two marks overlap, the nearer dot still answers.
                    o.append(f'<g class="pt"><title>{esc(tip)}</title><path d="{cell}" fill="{SURF}" fill-opacity="0"/><g pointer-events="none">'
                             + (f'<circle class="mk ho" cx="{x:.1f}" cy="{yd:.1f}" r="3.4" fill="{SURF}" stroke="{color}" stroke-width="1.8"/>' if r["hollow"]
                                else f'<circle cx="{x:.1f}" cy="{yd:.1f}" r="4.9" fill="{SURF}"/><circle class="mk fi" cx="{x:.1f}" cy="{yd:.1f}" r="4.3" fill="{color}"/>') + "</g></g>")
    o.append("</svg>")
    return "\n".join(o)


def secs_txt(recs):
    return f"{int(recs[0]['min_ms']) // 1000} s"


def l_rows(pool):
    rows = []
    for d in LPOOL:
        rows.append(p_row(d, pool[d], True, label=f"{d} ({secs_txt(pool[d])})"))
    return rows


def band_title(what, rg, n):
    files = ", ".join(sorted({f"{r['folder']}/{r['file']}" for r in rg.recs}))
    return f"Grey band: {what}. {rg.txt()} GB/s, n = {n}. Source: {files}."


F72_NOTES = ["earlier run of the same boot,|not part of the rerun"]      # "|" = line break inside one note
IN_PLACE_2 = ["asmread in place of", "the new read kernel"]              # group label in two lines: it stays inside the label column
need(" ".join(IN_PLACE_2) == IN_PLACE, "figure 2: the group label is not the label of figure 1")
need({(r["round"], r["pos"], r["file"]) for r in C_ASM_AO} == {(1, 0, "crev.csv")}, "part C, asmread after oldread: not crev, round 1, position 0")
CI_NOTES = ["added after the first|numbers were seen"]
P_OLD_BLOCKS = [
    dict(title="0.5 s measurements, bw_old read", band=rPA_old,
         band_txt=["grey band = 8000 MT/s rows A-1 to A-3:", f"{rPA_old.txt()} GB/s, n = {n8000(P_A_OLD)}"],
         band_title=band_title("lowest to highest interval of the 8000 MT/s rows A-1 to A-3, bw_old read", rPA_old, n8000(P_A_OLD)),
         groups=[dict(title="8000 MT/s", band=True, rows=[p_row(d, B_A_OLD[d], True) for d in APOOL]),
                 dict(title="7200 MT/s, part A", band=True, rows=[p_row(f"Part A, session {s_}", [r for r in A_OLD if r["session"] == s_], False, label=f"Session {s_} (T72A{s_})", band=rPA_old)
                                                                  for s_ in (1, 2, 3)])]),
    dict(title="6 s measurements, bwx12 oldread", band=rPL_old,
         band_txt=["grey band = 8000 MT/s rows L-1 to L-4:", f"{rPL_old.txt()} GB/s, n = {n8000(P_L_OLD)}", "(L-2 to L-4: 4 s measurements, other hardware events counted)"],
         band_title=band_title("lowest to highest interval of the 8000 MT/s rows L-1 to L-4, oldread at position 0", rPL_old, n8000(P_L_OLD)),
         groups=[dict(title="8000 MT/s", band=True, rows=l_rows(B_L_OLD)),
                 dict(title="7200 MT/s", band=True, rows=[
                     p_row("F72d12", F_OLD, False, F72_NOTES, band=rPL_old),
                     p_row("Part L", L_OLD, False, label="Part L (3 sessions)", band=rPL_old, more=[f"!medians: {f2(abs(L_OLD_MED))} GB/s lower"]),
                     p_row("Part C", C_OLD, False, label="Part C (4 processes)", band=rPL_old),
                     p_row("Control I", I_OLD, False, CI_NOTES, band=rPL_old)])]),
]


def a_new_block(rnd):
    v = A_V3[rnd]
    rows8 = [p_row(f"{d}, round {rnd}", [r for r in B_A_NEW[d] if r["round"] == rnd], True, label=d) for d in ("A-1", "A-2")]
    rows7 = []
    for s_ in (1, 2, 3):
        rows7.append(p_row(f"Part A, session {s_}, round {rnd}", [r for r in A_NEW if r["session"] == s_ and r["round"] == rnd], False,
                           [] if s_ == 1 else ["used for Q1 only (rule V3)"], label=f"Session {s_} (T72A{s_})", band=v["r8"] if s_ == 1 else None))
    return dict(title=f"0.5 s measurements, bw_new read, round {rnd}", band=v["r8"],
                band_txt=[f"grey band = 8000 MT/s rows A-1 and A-2 of round {rnd}:", f"{v['r8'].txt()} GB/s, n = {n8000(v['r8'].recs)}"],
                band_title=band_title(f"lowest to highest interval of the 8000 MT/s rows A-1 and A-2, bw_new read, round {rnd}", v["r8"], n8000(v["r8"].recs)),
                groups=[dict(title="8000 MT/s", band=True, rows=rows8), dict(title="7200 MT/s, part A", band=True, rows=rows7)])


P_NEW_BLOCKS = [
    dict(title="6 s measurements, bwx12", band=rPL_asm,
         band_txt=["grey band = 8000 MT/s rows L-1 to L-4, asmread:", f"{rPL_asm.txt()} GB/s, n = {n8000(P_L_ASM)}", "(L-2 to L-4: 4 s measurements, other hardware events counted)"],
         band_title=band_title("lowest to highest interval of the 8000 MT/s rows L-1 to L-4, asmread at position 1, directly after oldread", rPL_asm, n8000(P_L_ASM)),
         groups=[dict(title="8000 MT/s", sub=IN_PLACE_2, band=True, rows=l_rows(B_L_ASM)),
                 dict(title="7200 MT/s", sub=IN_PLACE_2, band=True, rows=[
                     p_row("F72d12", F_ASM, False, F72_NOTES, band=rPL_asm),
                     p_row("Part L", L_ASM, False, label="Part L (3 sessions)", band=rPL_asm),
                     p_row("Part C, asmread directly after oldread (crev, round 1, position 0)", C_ASM_AO, False, ["~asmread after oldread"], label="Part C (crev, round 1)", band=rPL_asm),
                     p_row("Control I", I_ASM, False, CI_NOTES, band=rPL_asm)]),
                 dict(title="7200 MT/s, part C", sub=["no 8000 MT/s row of", "this kind (no band)"], band=False, rows=[
                     p_row("Part C, read directly after oldread", C_READ_AO, False, ["~new read kernel,|after oldread"], label="Part C, read"),
                     p_row("Part C, read directly after asmread", C_READ_AA, False, ["~new read kernel,|after asmread"], label="Part C, read"),
                     p_row("Part C, asmread directly after read", C_ASM_AR, False, ["~after read"], label="Part C, asmread"),
                     p_row("Part C, asmread as first interval of the process", C_ASM_FI, False, ["~first interval of the process"], label="Part C, asmread")])]),
    a_new_block(1), a_new_block(2),
]
P_OLD_BLOCKS.reverse()


def panel_rows(blocks, band_only=True):
    return [(b, g, r) for b in blocks for g in b["groups"] for r in g["rows"] if g["band"] or not band_only]


# facts that the takeaway line of figure 2 states: checked here, so the sentence cannot go stale
OLD_7200_BELOW = [r["name"] for b, g, r in panel_rows(P_OLD_BLOCKS) if not r["hollow"] and not r["rg"].overlaps(b["band"])]
need(OLD_7200_BELOW == ["Part L"], f"figure 2, old read: the rows outside the band are {OLD_7200_BELOW}")
# every 7200 MT/s row of the panel "Old read kernel" is compared with its band: each one carries the bold text with its place
OLD_CMP = [r for b, g, r in panel_rows(P_OLD_BLOCKS) if not r["hollow"]]
need(len(OLD_CMP) == 7 and all(any(n.startswith("!") for n in r["notes"]) for r in OLD_CMP), "figure 2, old read: a 7200 MT/s row has no bold text with its place relative to the band")
NEW_CMP = [(b, r) for b, g, r in panel_rows(P_NEW_BLOCKS) if not r["hollow"] and any(n.startswith("!") for n in r["notes"])]   # rows that are compared with a band
NEW_7200_IN = [r["name"] for b, r in NEW_CMP if r["rg"].overlaps(b["band"])]
NEW_7200_RIGHT = [r["name"] for b, r in NEW_CMP if r["rg"].lo > b["band"].hi]
need(NEW_7200_IN == ["F72d12"] and len(NEW_7200_RIGHT) == 5 and len(NEW_CMP) == 6, f"figure 2, load-only: compared rows inside the band {NEW_7200_IN}, right of it {len(NEW_7200_RIGHT)}")
need(sorted(NEW_7200_RIGHT) == sorted(["Part L", "Part C, asmread directly after oldread (crev, round 1, position 0)", "Control I", "Part A, session 1, round 1", "Part A, session 1, round 2"]),
     f"figure 2, load-only: the rows right of their band are not the five rows that the caption names: {NEW_7200_RIGHT}")
F2_RIGHT_TXT = ("The rows to the right of their band are part L, the part C row &quot;asmread after oldread&quot;, session 1 of part A in both rounds, "
                "and control I (added after the first numbers were seen).")
allv_old = [v for b, g, r in panel_rows(P_OLD_BLOCKS, False) for v in r["rg"].v]
allv_new = [v for b, g, r in panel_rows(P_NEW_BLOCKS, False) for v in r["rg"].v]
OLD_AX, NEW_AX = (458, 476), (276, 340)
need(OLD_AX[0] < min(allv_old) and max(allv_old) < OLD_AX[1] and NEW_AX[0] < min(allv_new) and max(allv_new) < NEW_AX[1], "figure 2: a value lies outside an axis")
N_DOTS = len(allv_old) + len(allv_new)


def legend(items):
    return '<div class="legend">' + "".join(f'<span class="li">{sw}<span>{txt}</span></span>' for sw, txt in items) + "</div>"


def sw_dot(color, hollow=False):
    c = (f'<circle cx="8" cy="8" r="4.6" fill="{SURF}" stroke="{color}" stroke-width="2.2"/>' if hollow else f'<circle cx="8" cy="8" r="5.5" fill="{color}"/>')
    return f'<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">{c}</svg>'


SW_WHISK = f'<svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true"><path d="M3 4.5V11.5M19 4.5V11.5M3 8H19" stroke="{INK}" stroke-width="1.1" fill="none"/></svg>'
SW_BAND = f'<svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true"><rect x="1" y="1" width="20" height="14" fill="{BAND}"/><path d="M1 1V15M21 1V15" stroke="{BAND_EDGE}"/></svg>'
SW_PCT = f'<svg width="30" height="16" viewBox="0 0 30 16" aria-hidden="true"><line x1="1" y1="11" x2="29" y2="11" stroke="{LINK}" stroke-width="1.5"/><text x="15" y="8" font-size="9" text-anchor="middle" fill="{INK}">%</text></svg>'
LEG1 = legend([
    (sw_dot(BLUE), "old read kernel, named oldread in bwx12 (median of the row)"),
    (sw_dot(ORANGE), "load-only loop: new read kernel, or asmread where the row says so"),
    (sw_dot(MUTED, True), "hollow marker: 8000 MT/s"),
    (sw_dot(MUTED), "filled marker: 7200 MT/s"),
    (SW_WHISK, "lowest to highest interval of the row, to scale (often narrower than the dot)"),
    (SW_PCT, "percent on the line: drop of the load-only loop below the old read kernel. A range gives the lowest and the highest pair of the row"),
])
LEG2 = legend([
    (sw_dot(BLUE), "old read kernel, one dot per interval"),
    (sw_dot(ORANGE), "load-only loop, one dot per interval"),
    (sw_dot(MUTED, True), "hollow marker: 8000 MT/s"),
    (sw_dot(MUTED), "filled marker: 7200 MT/s"),
    (SW_BAND, "grey band: lowest to highest interval of the 8000 MT/s rows of the block"),
])

# ------------------------------------------------------------------ tables
def lab(main, *subs):
    """A row label: the name, and under it its notes in small type (no semicolon between label parts)."""
    return main + "".join("<br>" + small(x) for x in subs)


def only(values, what):
    vs = sorted(set(values))
    need(len(vs) == 1, f"{what}: more than one value {vs}")
    return vs[0]


def q1_table():
    def row(label, key, n):
        ds = Q1[key]["drops"]
        return [label, f1(min(ds)), f1(max(ds)), Q1[key]["old"].txt(), Q1[key]["new"].txt(), n]

    def med_rng(pairs, which, rnd=None):
        ms = [p[which].med for (_, r_), p in pairs.items() if rnd is None or r_ == rnd]
        return f"{f2(min(ms))} to {f2(max(ms))}"

    def per_round(pairs):
        return f"round 1: {med_rng(pairs, 'new', 1)}<br>round 2: {med_rng(pairs, 'new', 2)}<br>{small('(medians of the processes)')}"
    a8 = Q1["A8"]["drops"]
    pos_ao, pos_aa, pos_l = only((r["pos"] for r in C_READ_AO), "position"), only((r["pos"] for r in C_READ_AA), "position"), only((r["pos"] for r in L_ASM), "position")
    ord_ao, ord_aa = only((r["file"][:-4] for r in C_READ_AO), "order"), only((r["file"][:-4] for r in C_READ_AA), "order")

    def where(recs):
        """Sessions of the processes of one kernel order of part C."""
        named = sorted({r["session"] for r in recs if r["session"] is not None})
        extra = len({r["proc_key"] for r in recs if r["session"] is None})
        return ("session " if len(named) == 1 else "sessions ") + " and ".join(str(x) for x in named) + (" and the extra process" if extra else "")
    need(Rg(C_READ_AO).np == 2 and Rg(C_READ_AA).np == 2, "part C: not 2 processes per kernel order")
    rows = [
        "7200 MT/s, the planned rerun",
        row(f"<b>Part C</b>: kernel read (the new read kernel) at position {pos_ao}, directly after oldread (order {ord_ao}), processes T72C1 and T72C3 {ref('T72C1', 'T72C3')}", "C_ao", n7200(Q1["C_ao"]["new"].recs, 4)),
        row(f"<b>Part C</b>: kernel read (the new read kernel) at position {pos_aa}, directly after asmread (order {ord_aa}), processes T72C2 and T72C4 {ref('T72C2', 'T72C4')}", "C_aa", n7200(Q1["C_aa"]["new"].recs, 4)),
        row(f"<b>Part L</b>: asmread (in place of the new read kernel) at position {pos_l}, directly after oldread {ref('L1', 'L2', 'L3')}", "L", n7200(Q1["L"]["new"].recs, 6)),
        [f"<b>Part A</b>: bw_new read against bw_old read, 0.5 s, whole-pass stop. Drop between the medians of the two processes. Less exact than parts L and C {ref('A1', 'A2', 'A3')}",
         f1(min(Q1["A"]["drops"])), f1(max(Q1["A"]["drops"])),
         f"{med_rng(A_PAIRS, 'old')}<br>{small(f'(medians of the {rA_old.np} processes)')}", per_round(A_PAIRS),
         f"{len(A_PAIRS)} pairs of process medians / {plural(rA_old.np + Rg(A_NEW).np, 'process')} / 3 sessions / 1 boot"],
        "7200 MT/s, same boot, not part of the planned rerun (own rows in every comparison with 8000 MT/s)",
        row(f"<b>Control I</b> (added after the first numbers were seen, not part of the plan fixed before the run): asmread (in place of the new read kernel), idle start {ref('T72I1', 'T72I2')}", "I", n7200(Q1["I"]["new"].recs, 4)),
        row("<b>F72d12</b> (earlier run of the same boot at " + hm(F_OLD[0]["launch_utc"]) + f", not part of the rerun): asmread (in place of the new read kernel) {ref('F72')}", "F", n7200(Q1["F"]["new"].recs, 2)),
        "8000 MT/s, for context only (same computation)",
        row(f"<b>L-1</b>: asmread (in place of the new read kernel) directly after oldread {ref('L-1')}", "L1", n8000(Q1["L1"]["new"].recs, 2)),
        [f"<b>A-1, A-2</b>: bw_new read against bw_old read, drop between the medians of the two processes {ref('A-1', 'A-2')}", f1(min(a8)), f1(max(a8)),
         f"{med_rng(A8_PAIRS, 'old')}<br>{small(f'(medians of the {len(A8_PAIRS)} processes)')}", per_round(A8_PAIRS),
         f"{len(A8_PAIRS)} pairs of process medians / {plural(Rg(B_A_OLD['A-1'] + B_A_OLD['A-2'] + B_A_NEW['A-1'] + B_A_NEW['A-2']).np, 'process')} / 1 boot"],
        "Note",
        f'<span class="tn">Part C: each kernel order has 2 processes. Order {ord_ao} ran in {where(C_READ_AO)}. Order {ord_aa} ran in {where(C_READ_AA)}. '
        f"So kernel order and session are not fully separated {ref('go')}.</span>",
    ]
    return table(["Part and pair", "#Lowest drop, %", "#Highest drop, %", "#Old read kernel, GB/s", "#Load-only loop, GB/s", "n"], rows, "q1")


def tnote(head, *points):
    """A note under a table: its first sentences, then one bullet per further point."""
    return f'<div class="tn">{head}' + '<ul class="cl">' + "".join(f"<li>{x}</li>" for x in points) + "</ul></div>"


def cmp_cell(rg, n):
    return f'<span class="num">{rg.txt()}</span><br>{small(n)}'


rC_old_p0 = Rg([r for r in C_OLD if r["pos"] == 0])
need(rC_old_p0.n == 4 and {r["file"] for r in rC_old_p0.recs} == {"cfwd.csv"} and rC_old_p0.overlaps(rPL_old), "part C, oldread at position 0: not 4 intervals of cfwd that overlap the pool")
C_OLD_P2 = [r for r in C_OLD if r["pos"] == 2]
need(len(C_OLD_P2) == 4 and {r["file"] for r in C_OLD_P2} == {"crev.csv"} and {r["kernel_before"] for r in C_OLD_P2} == {"read"}, "part C, oldread at position 2: not 4 intervals of crev directly after read")
need({r["pos"] for r in P_L_OLD} == {0} and {r["pos"] for r in P_L_ASM} == {1} and {r["kernel_before"] for r in P_L_ASM} == {"oldread"}, "pool L-1 to L-4: positions")
xc_text_range("part C, oldread at position 0 (the position of the 8000 MT/s rows)", "4.2", rC_old_p0.lo, rC_old_p0.hi, "", "0.01", f2)
# every comparison with 8000 MT/s of the rerun uses records of the rerun only: control I and F72d12 are never pooled into it
for rg_ in (rA_old, rC_old, rL_old, rL_asm, rC_asm_ao, A_V3[1]["r7"], A_V3[2]["r7"]):
    need({r["dataset"] for r in rg_.recs} <= {"rerun-A", "rerun-L", "rerun-C"}, "a comparison of the rerun with 8000 MT/s holds a record of control I or F72d12")
RERUN_CMP_NEW = [rL_asm.lo > rPL_asm.hi, rC_asm_ao.lo > rPL_asm.hi, A_V3[1]["r7"].lo > A_V3[1]["r8"].hi, A_V3[2]["r7"].lo > A_V3[2]["r8"].hi]
RERUN_CMP_C = 1                                             # one of them is a part C row (asmread directly after oldread), made by decision (r) of the facts sheet
need(all(RERUN_CMP_NEW), "load-only loop: a comparison of the rerun with 8000 MT/s is not 'higher'")
need(len(RERUN_CMP_NEW) == 4 and {r["dataset"] for r in rL_asm.recs} == {"rerun-L"} and {r["dataset"] for r in rC_asm_ao.recs} == {"rerun-C"}
     and all({r["kernel"] for r in rg_.recs} == {"asmread"} for rg_ in (rL_asm, rC_asm_ao))
     and all({(r["dataset"], r["binary"], r["kernel"], r["session"]) for r in A_V3[rnd]["r7"].recs} == {("rerun-A", "bw_new", "read", 1)} for rnd in (1, 2)),
     "load-only loop: the 4 comparisons of the rerun are not part L and part C with asmread, and session 1 of part A with bw_new read in rounds 1 and 2")
# caption of Table 2: which of its rows are the comparisons that sentence 3 of the Short version counts
T2_RERUN_ROWS = (f"The block &quot;Load-only loop&quot; holds the {len(RERUN_CMP_NEW)} comparisons of the rerun that sentence 3 of the Short version counts. "
                 "Two use the new read kernel itself: part A, session 1, rounds 1 and 2. Two use asmread in its place: part L, and the part C row &quot;asmread directly after oldread&quot;. "
                 f"The rows of {F72} and of {CI} are not comparisons of the rerun.")


def q2_table():
    pool_l = ("pool L-1 to L-4, oldread at position 0 (L-1: 6 s, the argument line of part L. It differs from the part C lines in the kernel order. "
              "L-2 to L-4: 4 s, other hardware events counted) " + ref("L-1", "L-1l", "L-2a", "L-2b", "L-3", "L-4a", "L-4b", "L-4c"))
    pool_old, pool_asm = "pool L-1 to L-4, oldread at position 0<br>", "pool L-1 to L-4, asmread at position 1<br>"
    cannot = lambda rg: f"The test cannot exclude a difference of about {f1(width_pct(rg))} % (est. from one boot)"
    rows = ["Old read kernel"]
    rows.append(["Part A (bw_old read)", cmp_cell(rA_old, n7200(A_OLD)), f"pool A-1 to A-3 {ref('A-1', 'A-2', 'A-3')}<br>" + cmp_cell(rPA_old, n8000(P_A_OLD)), "yes", "0",
                 f"&quot;{WORD_SAME}&quot;. {cannot(rPA_old)}. The 7200 MT/s range is wider than the 8000 MT/s range ({f2(A_OLD_W7)} GB/s against {f2(A_OLD_W8)} GB/s). "
                 f"{len(A_OLD_BELOW)} of its {rA_old.n} intervals lie below that range ({one_process(A_OLD_BELOW)}), and {len(A_OLD_ABOVE)} lie above it ({one_process(A_OLD_ABOVE)})"])
    rows.append([lab("Part C (oldread)", f"{rC_old_p0.n} intervals at position 0 (order cfwd), {len(C_OLD_P2)} at position 2 (order crev, directly after read)"),
                 cmp_cell(rC_old, n7200(C_OLD)), pool_l + "<br>" + cmp_cell(rPL_old, n8000(P_L_OLD)), "yes", "0",
                 f"&quot;{WORD_SAME}&quot;. {cannot(rPL_old)}. The 8000 MT/s rows hold oldread at position 0 only. "
                 f"The {rC_old_p0.n} part C intervals at position 0 span {rC_old_p0.txt()} GB/s and overlap too"])
    rows.append(["Part L (oldread at position 0)", cmp_cell(rL_old, n7200(L_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)), "no", signed(L_OLD_NEAR),
                 f"&quot;{WORD_DIFF}&quot;. Part L is lower by {f2(abs(L_OLD_NEAR))} GB/s at the nearest ends ({f1(L_OLD_NEAR_PCT)} % of the lower end of the 8000 MT/s range) "
                 f"and by {f2(abs(L_OLD_MED))} GB/s between the medians ({f1(L_OLD_MED_PCT)} % of the 8000 MT/s median). The data do not show the cause (section 3)"])
    rows.append([lab("F72d12 (oldread)", "earlier run of the same boot, not part of the rerun"), cmp_cell(rF_old, n7200(F_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)),
                 "yes", "0", f"&quot;{WORD_SAME}&quot;. {cannot(rPL_old)}. Not pooled with part L"])
    rows.append([lab("Control I (oldread)", "added after the first numbers were seen"), cmp_cell(rI_old, n7200(I_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)),
                 "yes", "0", f"&quot;{WORD_SAME}&quot;. {cannot(rPL_old)}. Not pooled with part L"])
    rows.append("Load-only loop (no percent change between the two speeds is given)")
    rows.append([lab("Part L (asmread at position 1)", "in place of the new read kernel"), cmp_cell(rL_asm, n7200(L_ASM)), pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)),
                 "no", signed(DIST["nearest"][0]), f"&quot;{WORD_DIFF}&quot;. Part L is higher"])
    for rnd in (1, 2):
        v = A_V3[rnd]
        p8 = ", ".join(str(x) for x in sorted(set(v["p8"])))
        rows.append([f"Part A, session 1, round {rnd} (bw_new read, the new read kernel)", cmp_cell(v["r7"], n7200(v["r7"].recs)),
                     f"A-1 and A-2, round {rnd}<br>" + cmp_cell(v["r8"], n8000(v["r8"].recs)), "no", signed(v["near"]),
                     f"outside (above) the 8000 MT/s range of the same round. Pass counts per interval: {v['p7'][0]} at 7200 MT/s, {p8} at 8000 MT/s. They are not all equal. So part A gives no exact size of the difference"])
    rows.append(["Part C, kernel read (the new read kernel) at position 1",
                 f'after oldread: <span class="num">{rC_read_ao.txt()}</span><br>{small(n7200(C_READ_AO))}<br>after asmread: <span class="num">{rC_read_aa.txt()}</span><br>{small(n7200(C_READ_AA))}',
                 "no bwx12 run", "-", "-",
                 "Insufficient data: no 8000 MT/s run of kernel read with bwx12. The bwx12 kernel read (new C read loop) was never run with bwx12 at 8000 MT/s. "
                 f"The 2026-11-15 investigation ran asmread (hand-written loop with the same 8 loads per 256 B) in its place {ref('rules', 'facts')}"])
    rows.append([lab("Part C, asmread directly after oldread", "order crev, round 1, position 0", "in place of the new read kernel"), cmp_cell(rC_asm_ao, n7200(C_ASM_AO)),
                 pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "no", signed(rC_asm_ao.nearest(rPL_asm)),
                 f"&quot;{WORD_DIFF}&quot;. Part C is higher. The 8000 MT/s rows match in the kernel that ran directly before (oldread). "
                 "They do not match in the position: asmread is at position 1 there"])
    rows.append([lab("F72d12 (asmread at position 1)", "in place of the new read kernel", "earlier run of the same boot, not part of the rerun"), cmp_cell(rF_asm, n7200(F_ASM)),
                 pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "yes", "0",
                 f"inside the range of the 8000 MT/s pool: &quot;{WORD_SAME}&quot;. The test cannot exclude a difference of {f2(rPL_asm.hi - rPL_asm.lo)} GB/s, the width of that range (est. from one boot). "
                 f"Against L-1 alone F72d12 is {f2(rF_asm.nearest(rL1_asm))} GB/s higher. Not pooled with part L"])
    rows.append([lab("Control I (asmread at position 1)", "in place of the new read kernel", "added after the first numbers were seen"), cmp_cell(rI_asm, n7200(I_ASM)),
                 pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "no", signed(rI_asm.nearest(rPL_asm)),
                 f"&quot;{WORD_DIFF}&quot;. Control I is higher. Not pooled with part L"])
    # the choice of the pool: the same test against row L-1 alone (the row with the argument line of part L)
    rL1_old = Rg(B_L_OLD["L-1"])
    alone = [("part L, oldread", rL_old, rPL_old, rL1_old), ("part C, oldread", rC_old, rPL_old, rL1_old), ("F72d12, oldread", rF_old, rPL_old, rL1_old),
             ("control I, oldread", rI_old, rPL_old, rL1_old), ("part L, asmread", rL_asm, rPL_asm, rL1_asm), ("part C, asmread", rC_asm_ao, rPL_asm, rL1_asm),
             ("F72d12, asmread", rF_asm, rPL_asm, rL1_asm), ("control I, asmread", rI_asm, rPL_asm, rL1_asm)]
    changed = [nm for nm, r7, pool, l1 in alone if r7.overlaps(pool) != r7.overlaps(l1)]
    need(changed == ["F72d12, asmread"], f"table 2: rows whose overlap result changes against L-1 alone: {changed}")
    # row X2d12 (12 modules, another boot, two changed TXREQ settings): shown, not used. Would it change an overlap result?
    pool_x = {id(rPL_old): Rg(P_L_OLD + EXTRA["X2d12"]["old"]), id(rPL_asm): Rg(P_L_ASM + EXTRA["X2d12"]["asm"])}
    need(all(r7.overlaps(pool) == r7.overlaps(pool_x[id(pool)]) for nm, r7, pool, l1 in alone), "table 2: an overlap result changes when row X2d12 is added to the pool")
    need(n8000(EXTRA["X2d12"]["old"]) == n8000(EXTRA["X2d12"]["asm"]), "X2d12: n differs between the two kernels")
    rows.append("Notes")
    rows.append(f'<span class="tn">Pool or L-1 alone: with row L-1 alone in place of the pool L-1 to L-4, {len(alone) - len(changed)} of the {len(alone)} rows that use the pool keep their overlap result. '
                f"The exception is F72d12 with asmread (earlier run of the same boot, not part of the rerun): it lies {f2(rF_asm.nearest(rL1_asm))} GB/s above L-1. "
                f"The choice of the pool was made after the numbers were seen (decision (k) of the facts sheet) {ref('facts')}.</span>")
    rows.append('<span class="tn">Part C: the rules file contradicts itself here. Rule F2 (points 2 and 3) would show part C at 7200 MT/s only. '
                "Rules V1 (point 2), V2 (point 4) and V4 compare part C with the 8000 MT/s rows. This page follows the facts sheet (its decision (r) in section 2) "
                f"and compares the two part C rows that have an 8000 MT/s row of the list {ref('facts', 'rules')}. This choice was made after the numbers were seen.</span>")
    rows.append(f'<span class="tn">Row X2d12 is shown here and not used. It is 1 process of the argument line of part L at 8000 MT/s with 12 modules, in another boot of 2026-11-17 {ref("xX2d12", "xX2d12l", "klogX2d12")}. '
                f"Rules V2 (point 4) and F2 (point 2) name it as an 8000 MT/s row of the part L line. Rule V4 lists it among the rows that are not used (a firmware test with two changed TXREQ settings) {ref('rules')}. "
                f"This page follows rule V4. X2d12 gave {rX2_old.txt()} GB/s for the old read kernel and {rX2_asm.txt()} GB/s for asmread ({n8000(EXTRA['X2d12']['old'])} per kernel). "
                f"With X2d12 added to the pool L-1 to L-4, all {len(alone)} rows that use the pool keep their overlap result.</span>")
    # rows of the older runner bwx: named by the rules file, another binary, so no wording comes from them
    n_rev = n8000(X_REV_READ)
    need(n_rev == n8000(X_REV_ASM) and n8000(X_READ_AO) == n8000(X_READ_AA) == n8000(X_ASM_AR), "runner bwx: n differs between the kernels")
    x_refs = ref("xB7a", "xB7b", "xC3a", "xC3b")
    sets = [("read after oldread", C_READ_AO, rX_read_ao, X_ABOVE[0]), ("read after asmread", C_READ_AA, rX_read_aa, X_ABOVE[1]), ("asmread after read", C_ASM_AR, rX_asm_ar, X_ABOVE[2])]
    need(len(sets) == len(X_PAIRS) and all(d_ > 0 for *_, d_ in sets), "runner bwx: the three sets of part C intervals")
    rows.append(tnote(
        f"Other runner binary (bwx, not the bwx12 binary of the rerun): rule V2 (point 4) names 8000 MT/s rows (12 modules) of the older runner bwx for the comparison with part C {ref('rules')}.",
        f"These rows differ from part C in at least four ways. They used the older binary bwx. Each process timed a sequence of {len(X_SEQ)} kernels, and a part C process timed {len(SPEC['cfwd'][2].split(','))}. "
        "The processes of the two result folders B7-* ran without the counting of hardware events of the CPU (count=0 in the csv header), "
        f"and those of the two folders C3-* ran with it (count=1). {X_OFFSET} of the {len(X_POOL_HEAD)} processes used the runner option <code>--start offset</code>. "
        f"Part C used bwx12 with the counting of hardware events and <code>--start common</code> {x_refs} {ref('T72C1', 'T72C2', 'T72C3', 'T72C4')}.",
        f"The highest of their load-only intervals ({n8000(X_LOADS)}) was {f2(X_MAX_READ)} GB/s for kernel read and {f2(X_MAX_ASM)} GB/s for asmread {x_refs}.",
        f"{('Three' if len(sets) == 3 else str(len(sets)))} sets of part C intervals have such bwx rows with the same kernel directly before ({n8000(X_READ_AO)} per set at 8000 MT/s). "
        "Each set lies above the highest value of its bwx rows. The distances are those of the nearest ends. "
        + " ".join(f"The set &quot;{nm}&quot; ({n7200(recs)}) lies {f2(d_)} GB/s above {f2(xr.hi)} GB/s." for nm, recs, xr, d_ in sets),
        f"The {Rg(X_REV_READ).np} bwx processes of two other result folders ran another kernel order. They reached {f2(X_REV_MAX_READ)} GB/s (read) and {f2(X_REV_MAX_ASM)} GB/s (asmread) "
        f"({n_rev} per kernel) {ref('xB5a-rev', 'xB5b-rev')}. "
        "The read value lies inside the 7200 MT/s range of both read rows of part C (after oldread and after asmread). The asmread value lies inside the 7200 MT/s asmread range of part L."))
    # the three boots with 10 modules that rule V1 (points 3 and 4) quotes: how far two boots at 8000 MT/s differ
    n10 = n8000(T10_ASM[0].recs)
    need(n10 == n8000(T10_ASM[1].recs), "10-module boots: n differs between the two boots")
    rows.append(tnote(
        f"Boots with 10 modules (rule V1, points 3 and 4) {ref('rules')}: on 2026-11-17 three boots at 8000 MT/s found 10 modules. Each ran the argument line of part L once "
        f"{ref('xX1d10', 'klogX1d10', 'xX1d10b', 'klogX1d10b', 'xBASEd10', 'klog10')}. They are not rows of the list, and no wording comes from them.",
        f"By the settings records of the results folder, two of these boots had the same firmware settings (TXREQ Min changed) {ref('x1', 'x2')}. Their asmread gave {' / '.join(f2(v) for v in T10_ASM[0].v)} GB/s "
        f"and {' / '.join(f2(v) for v in T10_ASM[1].v)} GB/s ({n10} each). The two medians are {f1(T10_APART)} % apart (percent of the lower median).",
        f"The three boots gave {rT10_old.txt()} GB/s for the old read kernel ({plural(rT10_old.n, 'interval')} / {plural(rT10_old.np, 'process')} / 3 boots). This range is {f1(width_pct(rT10_old))} % wide.",
        f"Limit: by the same records the third boot had the original firmware settings {ref('rev')}. So the three boots did not differ by the boot alone."))
    # rounding: a distance is computed before rounding (reader finding: two printed distances are not the difference of the printed rates)
    ex = [(f2(rF_asm.nearest(rL1_asm)), "this table", q(rF_asm.lo) - q(rL1_asm.hi)), (f2(DIST["farthest"][0]), "Table 4", q(rL_asm.hi) - q(rPL_asm.lo))]
    ex = [f"{shown} GB/s ({where_})" for shown, where_, from_rounded in ex if Decimal(shown) != from_rounded]
    rows.append('<span class="tn">Rounding: a distance is computed from the rates before rounding. So it can differ by 0.01 GB/s from the difference of the two rounded rates'
                + (". Examples: " + " and ".join(ex) if ex else "") + ".</span>")
    return table(["7200 MT/s row", "Range at 7200 MT/s, GB/s, and n", "8000 MT/s rows: range, GB/s, and n", "Overlap", "#Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)",
                  "Wording by the rules fixed before the run"], rows, "q2")


def visits_table():
    """The three visits of the part L line in the 7200 MT/s boot: when and from which state each one started."""
    hms = lambda utc: utc[11:19]
    l_launch = sorted({r["launch_utc"] for r in L_OLD})
    i_launch = sorted({r["launch_utc"] for r in I_OLD})
    l_load = sorted({D(r["load1_at_launch"]) for r in L_OLD})
    i_load = [D([r for r in I_OLD if r["tag"] == t][0]["load1_at_launch"]) for t in ("T72I1", "T72I2")]
    i_gap = [int(LAUNCH[t]["gap_s"]) for t in ("T72I1", "T72I2")]
    need(all(LAUNCH[t]["gap_s"] == 5 and "of part A" in LAUNCH[t]["start_state"] for t in ("T72L1", "T72L2", "T72L3")), "part L: a process did not start 5 s after part A")
    need(max(i_load) < 1 and D(F_OLD[0]["load1_at_launch"]) < 1, "control I or F72d12: load at launch is not below 1.0")
    per = lambda rg: n7200(rg.recs)
    need(n7200(F_ASM) == n7200(F_OLD) and n7200(L_ASM) == n7200(L_OLD) and n7200(I_ASM) == n7200(I_OLD), "table 3: n differs between the two kernels of a visit")
    rows = [
        [lab("F72d12", "earlier run of the same boot, not part of the rerun"), F_LAUNCH,
         f"{F_AFTER_BOOT_S} s after the first kernel log line of the boot ({BOOT7_KLOG} UTC) {ref('gaps')}. Load average {f2(F_OLD[0]['load1_at_launch'])} at launch {ref('F72l')}. "
         f"Process list, written {F_ENV_BEFORE_S} s before the launch: the Linux kernel thread {F_TOP[3]} at {F_TOP[2]} %CPU {ref('F72e')}",
         rF_asm.txt(), rF_old.txt(), per(rF_asm)],
        ["Part L", f"{hms(l_launch[0])} to {hms(l_launch[-1])}",
         f"5 s after the last 120-thread process of part A. Load average {f2(l_load[0])} to {f2(l_load[-1])} at launch. "
         f"Process lists before the launch: at most {L_ENV_MAX} %CPU {ref('envT72L1', 'envT72L2', 'envT72L3')}",
         rL_asm.txt(), rL_old.txt(), per(rL_asm)],
        [lab("Control I", "added after the first numbers were seen"), " and ".join(hms(x) for x in i_launch),
         f"Idle start: load average {f2(i_load[0])} and {f2(i_load[1])} at launch, {i_gap[0]} s and {i_gap[1]} s after the previous 120-thread process. "
         f"Process lists before the launch: at most {I_ENV_MAX} %CPU {ref('envT72I1', 'envT72I2')}",
         rI_asm.txt(), rI_old.txt(), per(rI_asm)],
    ]
    return table(["Visit", "Launch, UTC", "Start state", "#asmread, GB/s", "#oldread, GB/s", "n per kernel"], rows, "visits")


def dist_table():
    names = {"nearest": "Nearest ends of the two ranges", "medians": "Medians", "farthest": "Farthest ends of the two ranges"}
    rows = [[names[k], f2(DIST[k][0]), f2(DIST[k][1])] for k in ("nearest", "medians", "farthest")]
    return table(["Kind of distance", "#Part L above the 8000 MT/s pool L-1 to L-4, GB/s", "#Part L above F72d12 (same 7200 MT/s boot, earlier run, not part of the rerun), GB/s"], rows, "narrow")


def load_table():
    hms = lambda utc, date=False: (utc[:10] + " " if date else "") + utc[11:19] + " UTC"
    what = {"A": "part A, session {s}: first of {n} processes", "L": "part L, session {s}", "C": "part C", "I": "control I (added after the first numbers were seen)"}
    rows = ["7200 MT/s: first launch of every step of the rerun and of control I (added after the first numbers were seen)"]
    for tg in STEPS:
        l = LAUNCH[tg]
        w = what[l["part"]].format(s=l["session"], n=len({r["proc_key"] for r in sel(dataset="rerun-A", session=l["session"])}) if l["part"] == "A" else 0)
        if l["part"] == "C":
            w = "part C" + (f", session {l['session']}" if l["session"] else ", extra process")
        ld = f2(l["load1_at_first_launch"])
        if l["part"] == "A":
            used = sorted({(r["launch_utc"], r["proc_key"]): D(r["load1_at_launch"]) for r in A_OLD + A_NEW if r["session"] == l["session"]}.items())
            need(used[0][1] == D(l["load1_at_first_launch"]), "part A: the first read process is not the first launch of the step")
            ld += "<br>" + small(f"the {len(used)} read processes used: " + ", ".join(f2(v) for _, v in used))
        rows.append([tg, w, hms(l["first_launch"]), ld, "-" if l["gap_s"] is None else f"{int(l['gap_s'])}"])
    rows.append("Earlier rows shown on this page: launch of every process")
    rows.append(["F72d12", "earlier run of the same boot, not part of the rerun", hms(F_OLD[0]["launch_utc"]), f2(F_OLD[0]["load1_at_launch"]), "-"])
    for d, recs in (("A-1", B_A_OLD["A-1"] + B_A_NEW["A-1"]), ("A-2", B_A_OLD["A-2"] + B_A_NEW["A-2"]), ("A-3", B_A_OLD["A-3"]),
                    ("L-1", B_L_OLD["L-1"]), ("L-2", B_L_OLD["L-2"]), ("L-3", B_L_OLD["L-3"]), ("L-4", B_L_OLD["L-4"])):
        procs = {}
        for r in recs:
            procs[r["proc_key"]] = (r["launch_utc"], D(r["load1_at_launch"]))
        ps = sorted(procs.values())
        times = hms(ps[0][0], True) if len(ps) == 1 else f"{hms(ps[0][0], True)[:-4]} to {hms(ps[-1][0])}"
        rows.append([d, f"8000 MT/s, {plural(len(ps), 'process')}", times, ", ".join(f2(x[1]) for x in ps), "-"])
    span = lambda a, b: f"{hms(a, True)[:-4]} to {hms(b, True) if a[:10] != b[:10] else hms(b)}"
    for nm, heads, what_ in (("Runner bwx, tags common-6000-*", X_POOL_HEAD, "note under Table 2"), ("Runner bwx, tags b5-rev-*", X_REV_HEAD, "another kernel order, note under Table 2")):
        ls, ts = sorted(h["load"] for h in heads), sorted(h["launch"] for h in heads)
        rows.append([nm, f"8000 MT/s, {plural(len(heads), 'process')} ({what_})", span(ts[0], ts[-1]), f"{f2(ls[0])} to {f2(ls[-1])}<br>" + small("lowest to highest"), "-"])
    rows.append(["X2d12", "8000 MT/s, 12 modules, 1 process, shown and not used (note under Table 2)", hms(EXTRA["X2d12"]["old"][0]["launch_utc"], True), f2(EXTRA["X2d12"]["load"]), "-"])
    t10 = [EXTRA[d_] for d_ in ("X1d10", "X1d10b", "BASEd10")]
    rows.append(["Boots with 10 modules", f"8000 MT/s, {len(t10)} processes in {len(t10)} boots (note under Table 2)", span(t10[0]["old"][0]["launch_utc"], t10[-1]["old"][0]["launch_utc"]),
                 ", ".join(f2(x["load"]) for x in t10), "-"])
    return table(["Step or row", "What", "Launch", "#1-minute load average at launch", "#Time since the end of the previous 120-thread process of go.sh or go2.sh, s (given for their steps only)"], rows, "load")


def detail_fig1():
    rows = []
    for b in F1_BLOCKS:
        for g in b["groups"]:
            rows.append(f"{b['title']} · {g['title'].split(' ·')[0]}")
            for r in g["rows"]:
                rows.append([lab(esc(r["name"]), *[esc(n) for n in r["notes"]]),
                             f2(r["old"].med), ", ".join(f2(v) for v in r["old"].v), f2(r["new"].med), ", ".join(f2(v) for v in r["new"].v), drop_txt(r["drops"])])
    return table(["Row", "#Old read kernel: median, GB/s", "#Its intervals, GB/s", "#Load-only loop: median, GB/s", "#Its intervals, GB/s", "#Drop"], rows, "detail")


def detail_fig2():
    """Every interval of figure 2. A row carries the label that the figure shows, and each note once."""
    rows = []
    for nm, blocks in (("Old read kernel", P_OLD_BLOCKS), ("Load-only loop", P_NEW_BLOCKS)):
        for b in blocks:
            for g in b["groups"]:
                rows.append(" · ".join([nm, b["title"], g["title"] + (", " + " ".join(g["sub"]) if g.get("sub") else "")]))
                for r in g["rows"]:
                    rows.append([lab(esc(r["label"]), *[esc(n) for n in plain_notes(r["notes"])]), str(r["rg"].n), ", ".join(f2(v) for v in sorted(r["rg"].v))])
    return table(["Row", "#n intervals", "Intervals, GB/s, sorted"], rows, "detail")


# ------------------------------------------------------------------ word list
def facts_words():
    m = re.search(r"<summary>Words used here</summary>(.*?)</details>", FMD, re.S)
    need(m, "FACTS.md: word list not found")
    out = {}
    for line in m.group(1).splitlines():
        k = re.match(r"^- \*\*(.+?)\*\*: (.*)$", line)
        if k:
            out[k.group(1)] = k.group(2)
    return out


FW_WORDS = facts_words()


def fw(key, swap=()):
    """A definition of the word list of FACTS.md, reused word for word ("this sheet" becomes "this page").
    swap = (old, new): one phrase of the sheet that this page words in another way. The phrase must be present."""
    need(key in FW_WORDS, f"FACTS.md word list: term '{key}' not found")
    t = FW_WORDS[key]
    if swap:
        need(swap[0] in t, f"FACTS.md word list, term '{key}': phrase '{swap[0]}' not found")
        t = t.replace(swap[0], swap[1])
    t = re.sub(r"\s*\[Ref\d+\]", "", t).replace("this sheet", "this page").replace("This sheet", "This page")
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(t).replace("&quot;", '"'))
    return t[0].upper() + t[1:]


BOOT8 = RERUN["boot_id"][:8]
# part A: how many processes a session ran, and how many of them this page uses (the scope cut is stated in the word list)
A_ALL = sel(dataset="rerun-A")
A_KERNELS = [k for k in ("read", "write", "copy", "asmread", "asmwrite", "asmcopy") if any(r["kernel"] == k for r in A_ALL)]
A_PER_SESSION = sorted({len({r["proc_key"] for r in A_ALL if r["session"] == s_}) for s_ in (1, 2, 3)})
A_USED_PER_SESSION = sorted({len({r["proc_key"] for r in A_OLD + A_NEW if r["session"] == s_}) for s_ in (1, 2, 3)})
# part A: round 2 runs the processes of round 1 in the reverse order (launch order of session 1, by binary and kernel)
a_order = {rnd: [k for k, _ in sorted({(r["binary"], r["kernel"]): r["launch_utc"] for r in A_ALL if r["session"] == 1 and r["round"] == rnd}.items(), key=lambda kv: kv[1])] for rnd in (1, 2)}
need(len(a_order[1]) == 12 and a_order[2] == a_order[1][::-1], "part A, session 1: round 2 does not run the 12 processes of round 1 in the reverse order")
need({r["kernel"] for r in A_ALL} == set(A_KERNELS) and {r["binary"] for r in A_ALL} == {"bw_old", "bw_new"} and {r["round"] for r in A_ALL} == {1, 2}
     and A_PER_SESSION == [len(A_KERNELS) * 2 * 2] and len(A_USED_PER_SESSION) == 1, "part A: a session is not kernels x 2 binaries x 2 rounds")
# names of argument lines that the tooltips of the earlier bwx12 rows show, and the tags of row A-3
LINE_TAGS = sorted({r["tag"] for d in LPOOL for r in B_L_OLD[d] + B_L_ASM[d]} | {r["tag"] for r in F_OLD + F_ASM})
need(LINE_TAGS == sorted([LINE_L, "p1nop", "p2add", "thp", "st1", "st2", "st3"])
     and all(r["file"] == r["tag"] + ".csv" for d in LPOOL for r in B_L_OLD[d] + B_L_ASM[d]), "rows L-1 to L-4 and F72d12: the tags are not the expected line names, or a csv file has another name")
A3_TAGS = sorted({r["tag"] for r in B_A_OLD["A-3"]})
need(A3_TAGS == [f"onebuf-ms500-{i}" for i in (1, 2, 3)], "row A-3: unexpected tags")
WORDS = [
    ("Q1, Q2", "The two questions of the rerun. Q1: is the whole-chip read rate of the new read kernel still below that of the old read kernel at 7200 MT/s, and by how much. Q2: did the rate of either kernel differ from the earlier runs at 8000 MT/s."),
    ("Rerun", f"The {GO_DONE} steps that go.sh ran at 7200 MT/s on 2026-11-17 from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC: 3 sessions of parts A, L and C, and one more part C process. "
              "Parts A and L repeat tests that ran earlier at 8000 MT/s. Part C is new. No earlier run in the results folder used one of its two argument lines. "
              f"Runs of the older runner bwx timed the same three kernels in both orders inside a longer sequence of {len(X_SEQ)} kernels (note under Table 2). "
              "Control I (added after the first numbers were seen) and F72d12 (earlier run of the same boot) are not part of the rerun."),
    ("CRB", fw("CRB")),
    ("Whole chip, 120 threads", "The runs use 120 threads on CPUs 0-119 only. Each thread reads its own buffer of 256 MiB from memory (1 MiB is 2^20 bytes)."),
    ("MT/s", fw("MT/s")),
    ("Memory module", "One DIMM (dual in-line memory module). CRB has 12 slots for them."),
    ("GB/s", "Gigabytes per second. 1 GB is 1e9 bytes."),
    ("Read kernel", fw("Read kernel")),
    ("Old read kernel", fw("Old read kernel")),
    ("New read kernel", fw("New read kernel")),
    ("asmread", fw("asmread")),
    ("Load-only loop", fw("Load-only loop")),
    ("bandwidth.c, bw_old, bw_new", fw("bandwidth.c, bw_old, bw_new")),
    ("bwx12, bwx11, bwx", fw("bwx12, bwx11, bwx", ("bwx12 is the runner of the 2026-11-15 investigation.",
                                                    "bwx12 is the runner of the investigation of 2026-11-15 into the lower read rate of the load-only loop."))),
    ("Process, interval, round, position", "A process is one start of a benchmark binary. An interval is one timed measurement inside a process. "
                                           "bwx12 times a sequence of kernels and repeats the sequence. Each repeat is a round (counted from 0). "
                                           "The position is the place of a kernel in the sequence (counted from 0). "
                                           f"In part A the script runs its {A_PER_SESSION[0] // 2} read, write and copy processes twice. Each run is a round (1 or 2). Round 2 runs the processes in the reverse order."),
    ("Rate", fw("Rate, total", ("bwx runners", "bwx12 and bwx"))),
    ("Interval row, thread rows", "bwx12 and bwx write two kinds of row into a csv file that this page uses. An interval row starts with the letter I and holds one interval. "
                                  "A thread row starts with the letter T and holds one thread of one interval. The 120 thread rows of an interval follow its interval row."),
    ("Median", "The middle value of a sorted list. For an even number of values it is the mean of the two middle values."),
    ("Facts sheet", "The file FACTS.md with its data file facts.json. It is the detailed record of this rerun. A script built it from the raw result files."),
    ("R, S", "Short forms of two folders: R is the results folder, and S is the scratch folder of this rerun. The reference list gives both paths."),
    ("Session, step", fw("Session") + " go.sh ran 3 sessions and then one more part C process (T72C4). The n column calls T72C4 the extra process. "
                      "A step is one part of one session, the extra part C process, or one process of control I (added after the first numbers were seen)."),
    ("go.sh, go2.sh", "The driver scripts. go.sh ran the planned rerun. go2.sh ran control I (added after the first numbers were seen)."),
    ("Part A", fw("Part A") + f" Each session ran {A_PER_SESSION[0]} processes: {len(A_KERNELS)} kernels ({', '.join(A_KERNELS)}) x 2 binaries x 2 rounds. "
               f"This page uses the {A_USED_PER_SESSION[0]} read processes of each session. The facts sheet holds the other {A_PER_SESSION[0] - A_USED_PER_SESSION[0]} (its sections 3.1 and 5) {ref('facts')}."),
    ("Part L", "One bwx12 process that times oldread, then asmread, then three other test loops that this page does not use. The process runs this sequence twice (rounds 0 and 1)."),
    ("Part C, cfwd, crev, kernel order", fw("Part C") + " Each process runs its sequence twice (rounds 0 and 1). The kernel order is the order of the kernels in this sequence."),
    ("Control I", fw("Control I")),
    ("F72d12", "One process of the part L line. It ran at " + hm(F_OLD[0]["launch_utc"]) + " on 2026-11-17 for another test, in the same boot as the rerun and before it. It is not part of the rerun."),
    ("T72A1 to T72I2", "The names of the result folders of the rerun (parts A, L, C) and of control I (I, added after the first numbers were seen): T72, then the letter, then a number."),
    ("A-1, A-2, A-3", "The 8000 MT/s rows for part A, all of 2026-11-13, with the same two binaries. A-1 is the original test. A-2 is a second run with another process order. A-3 is three more processes of bw_old read."),
    ("L-1, L-2, L-3, L-4", "The 8000 MT/s rows for parts L and C, all with bwx12. L-1 (2026-11-17) used the argument line of part L unchanged. L-2 to L-4 (2026-11-15) used 4 s measurements and counted other hardware events of the CPU. From these rows only oldread at position 0 and asmread at position 1 are used."),
    (", ".join(LINE_TAGS), f"Names of argument lines. In the rows L-1 to L-4 and in F72d12 (earlier run of the same boot, not part of the rerun) a bwx12 process carries the name of its line, and so does its csv file. "
                           f"A tooltip names such a process by this name. {LINE_L} is the part L line."),
    (f"{A3_TAGS[0]} to {A3_TAGS[-1]}", "The tags that the csv file of row A-3 gives its three processes."),
    ("Line, argument line, spec file", fw("Line, argument line") + " A spec file is a text file with one argument line."),
    ("Visit", fw("Visit")),
    ("Idle start", fw("Idle start")),
    ("Whole-pass stop", fw("Whole-pass stop")),
    ("Pass count", "Part A only: the number of buffer passes that all 120 threads completed in one interval."),
    ("Pair, drop", "A pair is one load-only interval and one old-kernel interval of the same process and round. The drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A the two kernels run in two processes. There the drop uses the medians of the two processes of one session and round."),
    ("List of 8000 MT/s rows", "The 8000 MT/s runs with 12 modules that this page compares with: rows A-1 to A-3 and L-1 to L-4. The rules file fixed them before the run. "
                               "The rules file also names rows of two older runner binaries (bwx11 and bwx). This page does not use the bwx11 rows. It shows the bwx rows in one note under Table 2 only. "
                               "Two more notes under Table 2 show rows that the rules file names and that are not rows of the list: row X2d12, and three boots with 10 modules. No wording comes from them."),
    ("Pool", fw("Pool")),
    ("Overlap of two ranges", fw("Ranges overlap")),
    ("Distance of the nearest ends, farthest ends", fw("Distance of the nearest ends") + " The distance of the farthest ends is the highest value of the higher range minus the lowest value of the lower range."),
    ("n", fw("n")),
    ("Rules V1 to V4, F1, F2", fw("Rules V1 to V4, F1, F2")),
    ("Boot, boot id", f"A boot is one run of the machine from a start to the next restart. The boot id is a random identifier that Linux creates at each start. Equal boot ids mean the same boot. The rerun ran in boot {BOOT8} (the first 8 characters of its boot id)."),
    ("MemTotal", fw("MemTotal")),
    ("State line", fw("State line")),
    ("Load average, load", fw("Load average")),
    ("%CPU, process list", "A process list is the output of the tool ps that a run script saves before a launch. "
                           + fw("%CPU", ("the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is", "%CPU is the column pcpu of this output. It is"))),
    ("pr/ttyAMA-1", fw("pr/ttyAMA-1", ("By its name it prints kernel messages", "Its name suggests that it prints Linux kernel messages"))),
    ("Exit status", "The number that a process returns when it ends. 0 means success."),
    ("Root", "Administrator rights on the machine. They were not approved for this task."),
    ("Journal, kernel log", "The kernel log is the list of messages of the Linux kernel. The journal is the saved system log of one boot. It holds the kernel log."),
    ("Hardware error record, corrected record", fw("Hardware error record")),
    ("Module list", "The output of the command <code>dmidecode -t 17</code>. It holds one entry &quot;Memory Device&quot; per memory module, with the configured speed of the module."),
    ("Firmware setting, DIMM Frequency, TXREQ", "A firmware setting is a value that the machine applies at its next start. &quot;DIMM Frequency&quot; sets the memory speed. TXREQ is a group of settings that were changed for another investigation."),
    ("GiB", "2^30 bytes."),
    ("est.", fw("est.")),
]

# ------------------------------------------------------------------ text of the page
def nw(text):
    """A number with its unit that must not break across two lines."""
    return f'<span class="num">{text}</span>'


OLD_PARTS = [(rA_old, rPA_old), (rC_old, rPL_old), (rL_old, rPL_old)]          # old read kernel: parts A, C, L of the rerun
need([a.overlaps(b) for a, b in OLD_PARTS] == [True, True, False], "Short version: the old read kernel does not overlap in parts A and C, with part L as the third part")
c_ao, c_aa = Q1["C_ao"]["drops"], Q1["C_aa"]["drops"]
need(only((r["kernel_before"] for r in C_READ_AA), "kernel before") == "asmread", "part C, second order: read does not follow asmread")
need(VISIT_LO == rF_asm.lo and VISIT_HI == rL_asm.hi, "the span of the three visits does not run from F72d12 to part L")
need(len(c_ao) == len(c_aa), "part C: the two kernel orders have different numbers of pairs")
c_all = c_ao + c_aa
SHORT = [
    f"At 7200 MT/s with 12 memory modules, the new read kernel (a benchmark loop with loads only) still read {nw(f1(min(c_all)) + ' %')} to {nw(f1(max(c_all)) + ' %')} less than the "
    f"old read kernel (each load is followed by an add) in {len(c_all)} pairs of 6 s measurements.",
    "For the old read kernel, no difference from the earlier 8000 MT/s runs was seen in two of the three tests (parts A and C), "
    f"and in the third (part L) it was lower by {nw(f1(L_OLD_NEAR_PCT) + ' %')} (nearest ends of the two ranges) and {nw(f1(L_OLD_MED_PCT) + ' %')} (medians).",
    f"The load-only loop gave higher rates than these 8000 MT/s runs in all {len(RERUN_CMP_NEW)} comparisons of the rerun (Table 2), "
    "and the data do not show that the memory speed caused either difference.",
]
need(n7200(L_OLD) == n7200(L_ASM) and n8000(P_L_OLD) == n8000(P_L_ASM), "Short version, part L: n differs between the two kernels")
# Table 2 holds load-only comparisons that are not part of the rerun (F72d12 lies inside the 8000 MT/s range). So the count of sentence 3 must name its scope.
need(f"in all {len(RERUN_CMP_NEW)} comparisons of the rerun (Table 2)" in SHORT[2], "Short version, sentence 3: the count of comparisons does not name the rerun as its scope")
need(rPL_asm.lo <= rF_asm.lo and rF_asm.hi <= rPL_asm.hi and rF_asm.hi < rL_asm.lo, "Short version: F72d12 is not inside the 8000 MT/s range and below part L")
SHORT_MORE = UL([
    f"Sentence 1 (part C): {f1(min(c_ao))} % to {f1(max(c_ao))} % lower when the new read kernel ran directly after the old read kernel, "
    f"and {f1(min(c_aa))} % to {f1(max(c_aa))} % lower directly after asmread, a hand-written loop with the same loads ({len(c_ao)} pairs / 2 processes each).",
    f"Part L (sentences 2 and 3), 7200 MT/s against 8000 MT/s: n = {n7200(L_OLD)} against {n8000(P_L_OLD)}. A boot is one run of the machine between two restarts. "
    f"Old read kernel: {rL_old.txt()} against {rPL_old.txt()} GB/s. It was lower by {f2(abs(L_OLD_NEAR))} GB/s at the nearest ends "
    f"and by {f2(abs(L_OLD_MED))} GB/s between the medians ({f1(L_OLD_NEAR_PCT)} % and {f1(L_OLD_MED_PCT)} % of the 8000 MT/s values). The data do not show the cause. "
    f"Load-only loop (asmread in place of the new read kernel): {rL_asm.txt()} against {rPL_asm.txt()} GB/s.",
    f"Parts A and C (sentence 2): the tests cannot exclude a difference of about {f1(width_pct(rPA_old))} % and {f1(width_pct(rPL_old))} % (est.). Table 2 gives the ranges and n.",
    "Part C (sentences 2 and 3): the rules fixed before the run contradict each other on whether part C is compared with the 8000 MT/s runs. This page compares it. "
    f"That choice was made after the numbers were seen (note under Table 2). Without part C, sentence 2 keeps parts A and L, and sentence 3 keeps {len(RERUN_CMP_NEW) - RERUN_CMP_C} of its {len(RERUN_CMP_NEW)} comparisons.",
    f"Sentence 3: the comparison uses 1 boot per memory speed. {F72} ran the argument line of part L. Its asmread gave {rF_asm.txt()} GB/s ({n7200(F_ASM)}). "
    f"That is inside the 8000 MT/s range. It is {f2(abs(DIST['nearest'][1]))} GB/s below part L at the nearest ends.",
])

l1d = Q1["L1"]["drops"]
GO_SECS = secs(RERUN["go_end"][11:19]) - secs(RERUN["go_start"][11:19])
N_RERUN_PAIRS = (len(c_ao) + len(c_aa), len(Q1["L"]["drops"]), len(Q1["A"]["drops"]))
need(sum(N_RERUN_PAIRS) + len(Q1["I"]["drops"]) + len(Q1["F"]["drops"]) == len(ALL_7200_DROPS), "pair counts of the 7200 MT/s rows")
# part C holds asmread too: its pairs with oldread of the same process and round (Table 1 does not show them)
C_ASM_DROPS = drops_of(pairs_in_process(C_OLD, C_ASM))
need(len(C_ASM_DROPS) == 8 and all(d > 0 for d in C_ASM_DROPS), "part C: not 8 asmread pairs, or asmread is not below oldread in a pair")
SEC1_INTRO = UL([
    f"The rerun ran parts A, L and C three times (three sessions) and then part C once more, from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC, all in boot {BOOT8} {ref('go', 'golog')}.",
    f"Part A repeats the 120-thread part of the test of 2026-11-13 with the same two binaries {ref('ra')}. "
    f"With its whole-pass stop the pass count of an interval changes by whole passes, and the rate changes with it. So part A is less exact than parts L and C {ref('facts')}.",
    f"Part C runs the new read kernel itself {ref('cfwd', 'crev')}. Part L runs asmread in its place {ref('like')}.",
    f"This page does not examine why the load-only loop is lower. The investigation of 2026-11-15 examined it and did not establish the cause {ref('earlier')}.",
])
SEC1_AFTER = UL([
    f"The drop is not one fixed value. The same argument line gave {drop_txt(Q1['L']['drops'])} in part L, {drop_txt(Q1['I']['drops'])} in {CI} and {drop_txt(Q1['F']['drops'])} in {F72}, "
    "all inside the one 7200 MT/s boot.",
    f"At 8000 MT/s the same line gave {drop_txt(l1d)} (row L-1). The data do not show that the smaller drop of the rerun is an effect of the memory speed (section 2).",
])
SEC2_INTRO = UL([
    f"The comparison rules and the list of 8000 MT/s rows were fixed before the run {ref('rules')}. A rule compares the lowest-to-highest range of the 7200 MT/s intervals with that of the 8000 MT/s rows.",
    f"Overlap: &quot;{WORD_SAME}&quot;. The width of the 8000 MT/s range is then the size that the test cannot exclude (est.).",
    f"No overlap: &quot;{WORD_DIFF}&quot;.",
    "The comparison uses exactly 1 boot per memory speed. So a difference between the two boots is not shown to be an effect of the memory speed.",
])
SEC2_BOOT = UL([
    f"The part L line ran in three visits of the 7200 MT/s boot (Table 3): {F72}, part L, and {CI}.",
    f"The three asmread ranges do not overlap each other. Together they span {f2(VISIT_LO)} to {f2(VISIT_HI)} GB/s ({f2(VISIT_HI - VISIT_LO)} GB/s).",
    "The three visits did not start from the same state. The data do not show which difference changed the rate.",
])
INSUFF = UL([
    "Insufficient data: whether a difference of the new read kernel comes from the memory speed. Runs in several boots per speed would resolve it (needs reboots and a change of the firmware setting).",
    "Insufficient data: why the rate of the load-only loop changed between the three visits of the one 7200 MT/s boot (Table 3). "
    "Two measurements would resolve it. First: run the part L line alternately from an idle start and directly after part A, at least 3 times each in one boot. "
    "Second: repeat the idle-start line some hours later in the same boot, and once directly after a reboot (needs approval).",
    "Insufficient data: why the old read kernel was lower in part L. The first of these two measurements would resolve it.",
    "Insufficient data: no 8000 MT/s run of kernel read with bwx12. A run of the two part C lines at 8000 MT/s would resolve it (needs a firmware change and a reboot).",
    "Insufficient data: whether hardware error records occurred during the rerun. A count of the &quot;[Hardware Error]&quot; lines of the kernel log would resolve it (needs root, which was not approved for this task).",
    "Insufficient data: a direct reading of the memory speed during the rerun. A module list read during the rerun would resolve it. "
    "The command <code>sudo dmidecode -t 17</code> prints this list (needs root).",
])
go_first = LAUNCH["T72A1"]
others = [LAUNCH[t]["load1_at_first_launch"] for t in STEPS[1:10]]
need(all(LAUNCH[t]["gap_s"] == 5 for t in STEPS[1:10]), "a step of go.sh did not start 5 s after the previous process")
need(LAUNCH["T72A1"]["gap_s"] is None, "T72A1 is not the first step")
need(D(go_first["load1_at_first_launch"]) < 1, "the first launch of the rerun is not an idle start")


# reading notes of figure 2: the start of part A in sessions 2 and 3, and the load at the first launch of session 1 and of rows A-1 and A-2
need(all(LAUNCH[t]["gap_s"] == 5 and "120-thread bwx12 process T72C" in LAUNCH[t]["start_state"] for t in ("T72A2", "T72A3")), "part A, sessions 2 and 3: not started 5 s after a part C process")
A_FIRST_LOAD = {"T72A1": D(go_first["load1_at_first_launch"])}
for d_ in ("A-1", "A-2"):
    first = min(sel(dataset=d_), key=lambda r: r["launch_utc"])
    need(first in B_A_OLD[d_] and first["_fproc"] == 1 and first["round"] == 1, f"{d_}: the first process of the file is not a read process that this page uses")
    A_FIRST_LOAD[d_] = D(first["load1_at_launch"])
need(all(v < 2 for v in A_FIRST_LOAD.values()), "session 1, A-1 or A-2: the first process did not start at a low load average")
a_sess_n = {(len(x), len({r["proc_key"] for r in x})) for x in ([r for r in A_OLD if r["session"] == s_] for s_ in (1, 2, 3))}
need(a_sess_n == {(6, 2)}, "part A, old read kernel: a session does not have 6 intervals of 2 processes")
A_SESSION_N = "6 intervals / 2 processes / 1 session / 1 boot"


def cl(*items):
    """A list inside one table cell: one point per bullet."""
    return '<ul class="cl">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def state_table():
    hw_refs = ref("journal", "L-1l", "L-2l", "L-3l", "L-4l")
    low_day = LOWEST_ASM["launch_utc"][:10]
    need(HW_LOW[0]["ts"][:10] == low_day == "2026-11-15", "the lowest asmread interval of the pool is not of 2026-11-15")
    rows = [
        ["12 memory modules during the rerun",
         cl(f"MemTotal is {RERUN['memtotal_kB']} kB in all {len(ST_ALL)} state lines of the two run logs {ref('golog', 'go2log')}.",
            f"The record of this boot (a file written at {TRY6_UTC[11:19]} UTC) holds the same value. It also holds the kernel log line &quot;This system has 12 DIMM sockets&quot; "
            f"and the count 12 of the lines &quot;Configured Memory Speed&quot; {ref('try6')}.",
            f"The module list saved in the same boot has one line &quot;Configured Memory Speed&quot; for each of its {DMI_N} modules {ref('dmi')}."),
         cl(f"The record also holds the line &quot;modules={TRY6_MODLINE}&quot; {ref('try6')}. This is not the module count. The module list holds {DMI_SIZE} lines with the text &quot;Size: 32 GB&quot;: "
            f"{DMI_SIZE_PLAIN} lines &quot;Size&quot; and {DMI_SIZE_VOL} lines &quot;Volatile Size&quot; {ref('dmi')}.",
            f"Hypothesis, not checked: the script that wrote the record counted these {DMI_SIZE} lines. Reading that script would confirm or reject it.")],
        ["Memory speed 7200 MT/s during the rerun",
         f"Every state line holds the boot id {RERUN['boot_id']}. The record of this boot, written at {TRY6_UTC[11:19]} UTC, shows 12 x &quot;Configured Memory Speed: 7200 MT/s&quot; {ref('try6')}.",
         "The speed was not read during the rerun. Reading it needs root. Assumption, not measured: the speed does not change inside one boot."],
        ["The rerun is complete",
         f"go.sh ran from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC. The script stops at the first exit status other than 0 {ref('go')}. Its log holds {GO_DONE} &quot;done&quot; lines and the final line ALLDONE {ref('golog')}. So {GO_DONE} of {GO_DONE} steps ended with exit status 0.",
         "-"],
        ["Logins and accounts with processes during go.sh",
         f"The {len(ST_GO)} state lines of the go.sh log show 0 logins. They list processes of {len(ACCOUNTS)} accounts only: jhan (the account that ran the rerun), root and {len(SYSTEM_ACCOUNTS)} system accounts {ref('golog')}.",
         "-"],
        ["Control I (added after the first numbers were seen) ran afterwards",
         f"go2.sh waits for a 1-minute load average below 1.0 and then runs the part L line. It does this twice {ref('go2')}. It ran from {RERUN['go2_start'][11:19]} to {RERUN['go2_end'][11:19]} UTC. "
         f"Its log holds 2 &quot;done&quot; lines and the final line ALLDONE {ref('go2log')}.",
         "Control I is not part of the plan fixed before the run."],
        [f"F72d12 (earlier run of the same boot, not part of the rerun) belongs to boot {BOOT8}",
         f"The record of this boot was written at {TRY6_UTC[11:19]} UTC {ref('try6')}. The boot list, saved at {BOOT_LAST} UTC, shows this boot from {BOOT_FIRST} UTC as the last boot {ref('boots')}. "
         f"The F72d12 process ran from {F_LAUNCH} to {F_END} UTC {ref('F72l')}. The go.sh log shows the same boot id at {RERUN['go_start'][11:19]} UTC {ref('golog')}.",
         "The proof uses these times only. The speed was not read during the process."],
        ["Work before the first 120-thread process of part A",
         f"On 2026-11-13 the test script launched {ONE_N} one-thread processes from {ONE_FIRST} to {ONE_LAST} UTC, directly before its 120-thread part {ref('one')}. "
         f"The rerun did not repeat this one-thread phase {ref('ra')}. "
         f"At 8000 MT/s the old read kernel gave {rA12_old.txt()} GB/s after one-thread work and directly after 120-thread work (rows A-1 and A-2, {n8000(rA12_old.recs)}) {ref('A-1', 'A-2', 'facts')}.",
         "Insufficient data: whether the work before the first 120-thread process changes the rate of the new read kernel. "
         f"A run with the new kernel at several positions, after an idle start and after 120-thread work, would resolve it {ref('rules')}."],
        ["Firmware settings other than the memory speed",
         f"Two TXREQ settings were changed for another test on 2026-11-17, at {X1_T} and {X2_T} UTC {ref('x1', 'x2')}. Both were set back at {RV_T} UTC to their values of the 8000 MT/s boot {ref('rev')}. "
         f"The settings list saved after that is equal to the list of the 8000 MT/s boot in all {N_SET} entries{'' if SAME_ORDER else ' (the order of the entries differs)'} {ref('qbase', 'qrev')}. "
         f"The only later change on record is DIMM Frequency = 7200 MT/s (file time {D72_T} UTC) {ref('d72')}.",
         cl(f"{N_UNREAD} of the {N_SET} entries show no readable value in both lists ({UNREAD['ValueUnavailable']} show ValueUnavailable, {UNREAD['VStoreError']} show VStoreError).",
            f"&quot;On record&quot; means the {len(SET_FILES)} files named set.txt in the results folder.",
            "Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. No full list was saved in that boot. A settings list saved in that boot would resolve it (needs root).")],
        ["The 8000 MT/s rows: one boot, 12 modules",
         cl(f"The saved kernel log of that boot runs from {BOOT8_FROM[:10]} {BOOT8_FROM[11:19]} to {BOOT8_TO[:10]} {BOOT8_TO[11:19]} UTC and holds the line &quot;This system has 12 DIMM sockets&quot; {ref('klog')}.",
            f"The kernel log of the boot that started on {BOOT10_FROM} UTC holds &quot;This system has 10 DIMM sockets&quot;, and its memory size line shows {MEM_LESS_GIB} GiB less {ref('klog10')}. "
            "So the number in this line is not the slot count of the board. This page reads it as the number of modules that the boot found.",
            f"Every process of the rows A-1 to A-3, of the rows L-1 to L-4 and of runner bwx was launched inside the time of this kernel log {ref('json')}. "
            "Row X2d12 and the three boots with 10 modules ran in later boots (notes under Table 2).",
            f"The settings list saved in that boot shows DIMM Frequency = 8000 MT/s {ref('qbase')}."),
         "No reading of the applied speed was saved in that boot."],
        ["Corrected hardware error records in the 8000 MT/s rows",
         cl(f"Rows L-1 to L-4: the journal of the 8000 MT/s boot holds corrected hardware error records during two of the four rows. It holds {HW_L1} during L-1, and {HW_L2[0]} and {HW_L2[1]} during the two processes of L-2. "
            f"It holds {HW_L34} during L-3 and L-4 {hw_refs}.",
            f"Rows A-1 to A-3 ({A_DAY}): the journal holds {len(HW_A)} records between the first launch of A-1 ({A1_FIRST} UTC) and the launch that followed the last A-3 process used here ({A3_END} UTC). "
            f"All {len(HW_A)} records have times inside row A-2. 2 records have the time {HW_A2_T[0]} UTC. The bw_new read process of round 1 was launched at {HW_A2_T[0]} UTC too. "
            f"The other 2 records have the time {HW_A2_T[1]} UTC. A {A2_OTHER} process, which this page does not use, was launched {secs(HW_A2_T[1]) - secs(a2_other[0][1])} s before that {ref('journal', 'A-1', 'A-2', 'A-3')}."),
         cl("The data do not show that a record changed a rate.",
            "For the rerun the kernel log was not read (section 3).",
            "The rows of runner bwx (note under Table 2) were not checked for such records.")],
        ["The lowest asmread value of the 8000 MT/s pool comes from an interval with corrected hardware error records",
         cl(f"The lowest asmread value of the pool L-1 to L-4 is {f2(val(LOWEST_ASM))} GB/s. Its interval ran from about {LOW_FROM} to {LOW_TO} UTC on {low_day} "
            f"(est.: time of the launch line plus the seconds since the process start in the thread rows) {ref('L-2b', 'L-2l')}.",
            f"{len(HW_LOW)} corrected hardware error records have the journal time {low_day} {HW_LOW[0]['ts'][11:19]} UTC, inside this interval {ref('journal')}.",
            f"Without this one interval the pool spans {rPL_asm_wo.txt()} GB/s ({n8000(rPL_asm_wo.recs)}). Part L ({rL_asm.txt()} GB/s, {n7200(L_ASM)}) still lies above it, by {f2(rL_asm.nearest(rPL_asm_wo))} GB/s at the nearest ends."),
         "The data do not show that the records lowered this interval. Both times have a resolution of 1 s."],
    ]
    return table(["Fact", "Proof", "Limit"], rows, "state")


LOAD_CAPTION = (f"The first launch of the rerun was at a 1-minute load average of {f2(go_first['load1_at_first_launch'])}. The other {len(others)} steps of go.sh started at a 1-minute load average of "
                f"{f2(min(others))} to {f2(max(others))}, each 5 s after a 120-thread process of the rerun had ended. "
                "Hypothesis, not tested: these high values come from the rerun's own 120-thread processes. Two more facts fit it. The load value is an average over the last minute. "
                f"The state lines of the go.sh log show 0 logins and processes of jhan, root and {len(SYSTEM_ACCOUNTS)} system accounts only {ref('golog')}. "
                "A sample of the load average and of the running processes, taken once per second between two steps, would confirm or reject it.")


CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:28px;line-height:1.25;margin:0 0 6px}
h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}
h3{font-size:17px;margin:22px 0 8px}
p{margin:8px 0}
ul{margin:4px 0 8px;padding-left:22px}
li{margin:3px 0}
a{color:inherit}
code{font-size:0.92em;overflow-wrap:anywhere}
.sub{color:#52514e;font-size:14px;margin:0 0 18px}
.short{background:#f1f0ec;border-left:4px solid #2a78d6;padding:12px 16px;margin:14px 0}
.short p{margin:6px 0}
.more{font-size:14.5px;margin:10px 0 0}
.more+ul{font-size:14.5px}
dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}
dl.words dt{font-weight:600}
dl.words dd{margin:0}
@media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}
.tw{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;font-size:14px;line-height:1.35}
th,td{border-bottom:1px solid #e4e3df;padding:4px 10px;text-align:left;vertical-align:top}
th{background:#f1f0ec;font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
td.n{white-space:nowrap}
tr.grp td{background:#f8f7f4;font-weight:600;color:#52514e;font-size:13px}
tr.grp td .tn{font-weight:400;color:#0b0b0b;font-size:13.5px}
tr.grp td .tn ul.cl{margin-top:3px}
/* Widths: the page content is the window width minus 32 px, and minus up to 17 px more when the browser draws a scrollbar.
   The wide tables have a least width of 900 px. So a wide table can scroll sideways in windows below 949 px, and the hint is shown there. */
table.q1,table.q2,table.state,table.load,table.visits,table.detail{min-width:900px}
.hint{display:none;color:#52514e;font-size:13.5px;margin:4px 0}
@media (max-width:949px){.hint.ht{display:block}}
/* A panel of figure 2 is 468 px wide with its border: it can scroll sideways in windows below 517 px. */
@media (max-width:519px){.hint.h2{display:block}}
table.state td:first-child{min-width:150px}
table.state td:nth-child(2){min-width:300px}
table.state td:nth-child(3){min-width:190px}
table.q1 td:first-child{min-width:190px}
table.q1 td:last-child{min-width:130px}
table.q2 td:first-child{min-width:140px}
table.q2 td:nth-child(2),table.q2 td:nth-child(3){min-width:160px}
table.q2 td:last-child{min-width:220px}
table.q2 th:nth-child(5){min-width:110px}
table.visits td:first-child{min-width:120px}
table.visits td:nth-child(2){min-width:90px}
table.visits td:nth-child(3){min-width:280px}
table.visits td:last-child{min-width:110px}
table.narrow{max-width:760px}
table.load td.n{white-space:normal}
table.load td:nth-child(2){min-width:150px}
table.load td:nth-child(3){min-width:110px}
table.load td:nth-child(4){min-width:170px}
table.load td:nth-child(5){min-width:190px}
table.detail{font-size:13px}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.sm{color:#52514e;font-size:12.5px}
figure{margin:16px 0}
.fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}
.fig.fit{width:fit-content;max-width:100%}
.fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
/* Figure 1 has three layouts, so it never scrolls sideways: 940 px wide in windows from 1000 px, 726 px from 780 px, 386 px below that.
   The box has a border of 1 px on each side, so the layouts need 942 + 49 px and 728 + 49 px of window width. */
.fig svg.f1m,.fig svg.f1n{display:none}
@media (max-width:999px){.fig svg.f1w{display:none}.fig svg.f1m{display:block}}
@media (max-width:779px){.fig svg.f1m{display:none}.fig svg.f1n{display:block;max-width:100%;height:auto}}
.panels{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start}
.panels>.fig,.panels>.col{flex:0 1 468px;max-width:100%}
ul.how{font-size:13.5px;color:#52514e;margin:10px 0 0;padding-left:20px}
.legend{display:flex;flex-wrap:wrap;gap:4px 18px;font-size:13.5px;margin:0 0 8px}
.legend .li{display:inline-flex;align-items:center;gap:6px}
.legend svg{flex:none}
.scale{font-size:13.5px;margin:0 0 8px}
g.pt:hover .mk.fi{stroke:#0b0b0b;stroke-width:1.6}
g.pt:hover .mk.ho{stroke-width:3.6}
figcaption{font-size:14.5px;margin-top:8px}
.take{font-weight:600}
.ref{color:#52514e;font-size:0.85em}
.ref a{text-decoration:none;white-space:nowrap}
.ref a:hover{text-decoration:underline}
.note{color:#52514e;font-size:14px}
.tcap{font-size:14.5px;margin:18px 0 0}
.tcap b{font-weight:600}
.tcap b .ref{font-weight:400}
td ul.cl{margin:0;padding-left:16px}
td ul.cl li{margin:0 0 5px}
td ul.cl li:last-child{margin-bottom:0}
ol.refs{font-size:14px;padding-left:0;list-style:none}
ol.refs li{margin:5px 0;overflow-wrap:anywhere}
details{margin:8px 0}
summary{cursor:pointer;font-weight:600}
"""


def build():
    words = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in WORDS)
    short = "".join(P(s) for s in SHORT)
    how1 = ('<ul class="how">'
            "<li>Each dot is the median of the intervals of its row. Point at a mark to see its values and its source file.</li>"
            f"<li>For bwx12 a source names the interval row of the csv file. The rate is the sum of the 120 thread rows after it. This sum differs from the rate printed in the interval row by at most {f2(IROW_MAX)} GB/s.</li>"
            f"<li>The data of both figures come from facts.json, the data file of the facts sheet {ref('json')}.</li></ul>")
    how2 = ('<ul class="how">'
            "<li>A 7200 MT/s row with all dots left of the band, or all dots right of it, does not overlap the 8000 MT/s range.</li>"
            "<li>The bold text under a row name says where the row lies relative to the band: left of it (lower), inside it, overlapping it, or right of it (higher). "
            "A 7200 MT/s row without bold text is not compared with a band.</li>"
            "<li>Panel &quot;Load-only loop&quot;, 0.5 s blocks: only session 1 is compared, each round against the same round (rule V3). "
            "Sessions 2 and 3 started 5 s after a 120-thread process of part C. Session 1 and the rows A-1 and A-2 did not. "
            f"Their first process started at a 1-minute load average of {f2(A_FIRST_LOAD['T72A1'])}, {f2(A_FIRST_LOAD['A-1'])} and {f2(A_FIRST_LOAD['A-2'])} (Table 6).</li>"
            f"<li>The figure shows {N_DOTS} intervals. Control I was added after the first numbers were seen. "
            "Table 2 gives n for every comparison, except the three part A session rows of the old read kernel. "
            f"Each of them has {A_SESSION_N} and is a part of the Table 2 row &quot;Part A (bw_old read)&quot;.</li></ul>")
    fig2 = ('<div class="panels"><div class="col"><div class="fig">'
            + panel("Old read kernel", "bw_old read and bwx12 oldread", OLD_AX[0], OLD_AX[1], range(460, 477, 4), range(458, 477, 2), P_OLD_BLOCKS, BLUE,
                    "Strip plot: every interval of the old read kernel, rows by method and memory speed")
            + '</div>' + how2 + '</div><div class="fig">'
            + panel("Load-only loop", "new read kernel, or asmread in its place where the label says so", NEW_AX[0], NEW_AX[1], range(280, 341, 20), range(280, 341, 10), P_NEW_BLOCKS, ORANGE,
                    "Strip plot: every interval of the load-only loop, rows by method and memory speed")
            + "</div></div>")
    page = f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Whole-chip read test at 7200 MT/s</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Whole-chip read test at 7200 MT/s: old read kernel against new read kernel</h1>
<p class="sub">2026-11-17, all times in UTC. Machine: CRB (an Arm reference server with 128 CPUs). 120 threads on CPUs 0-119, 256 MiB per thread. 12 memory modules at 7200 MT/s (million transfers per second, the unit of memory speed).</p>

<h2 id="short">Short version</h2>
<div class="short">
{short}
</div>
<p class="more">More detail for these three sentences:</p>
{SHORT_MORE}

<details><summary>Words used here</summary>
<dl class="words">{words}</dl>
</details>

<h2 id="q1">1. Is the new read kernel still below the old one? (Q1)</h2>
{SEC1_INTRO}
<figure>
{LEG1}
<div class="fig fit">{fig1("wide")}
{fig1("mid")}
{fig1("narrow")}</div>
<figcaption><span class="take">Figure 1. In the {len(SAME_LINE_ROWS)} rows that ran the argument line of part L (the same benchmark arguments) at 7200 MT/s, the blue dot (old read kernel) stays at nearly the same place, and the orange dot (load-only loop) moves. The intervals of the blue dots span {f2(VISIT_OLD_HI - VISIT_OLD_LO)} GB/s, and those of the orange dots span {f2(VISIT_HI - VISIT_LO)} GB/s.</span> The {len(SAME_LINE_ROWS)} rows are part L, {CI} and {F72}. Their ranges are {f2(VISIT_OLD_LO)} to {f2(VISIT_OLD_HI)} GB/s (old read kernel) and {f2(VISIT_LO)} to {f2(VISIT_HI)} GB/s (load-only loop). The orange dot is left of the blue dot in every row of the figure. So the load-only rate is lower in every row.</figcaption>
{how1}
</figure>
<p class="tcap"><b>Table 1. The drop per part.</b> The load-only loop is below the old read kernel in all {sum(N_RERUN_PAIRS)} pairs of the rerun rows of this table. It is also below it in the {len(C_ASM_DROPS)} asmread pairs of part C, which the table does not show {ref('T72C1', 'T72C2', 'T72C3', 'T72C4')}.</p>
{q1_table()}
{SEC1_AFTER}
<details><summary>Table view of Figure 1: every row</summary>
{detail_fig1()}
</details>

<h2 id="q2">2. Did a rate differ from the 8000 MT/s runs? (Q2)</h2>
{SEC2_INTRO}
<figure>
{LEG2}
<p class="scale">The two panels have different scales. The panel &quot;Old read kernel&quot; shows {OLD_AX[1] - OLD_AX[0]} GB/s over its width, and the panel &quot;Load-only loop&quot; shows {NEW_AX[1] - NEW_AX[0]} GB/s. So the same distance on the screen is {f1(Decimal(NEW_AX[1] - NEW_AX[0]) / Decimal(OLD_AX[1] - OLD_AX[0]))} times as many GB/s in the panel &quot;Load-only loop&quot;.</p>
<p class="hint h2">If a panel does not fit the screen, scroll it sideways to see all dots.</p>
{fig2}
<figcaption><span class="take">Figure 2. In the panel &quot;Old read kernel&quot; every 7200 MT/s row overlaps the grey band of its block, except part L. In the panel &quot;Load-only loop&quot; every 7200 MT/s row that is compared with a band lies to the right of it (higher), except F72d12 (earlier run of the same boot, not part of the rerun).</span> {F2_RIGHT_TXT} Part L of the old read kernel lies {f2(abs(L_OLD_NEAR))} GB/s left of its band at the nearest ends (lower), and its median is {f2(abs(L_OLD_MED))} GB/s below the median of the band rows. F72d12 lies inside its band.</figcaption>
</figure>
<p class="tcap"><b>Table 2. 7200 MT/s against 8000 MT/s, one row per comparison.</b> The rows that are compared come from 1 boot per memory speed. All {GO_DONE} steps of the rerun ran inside one period of {GO_SECS // 60} min {GO_SECS % 60} s ({RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC) of the 7200 MT/s boot. {T2_RERUN_ROWS}</p>
{q2_table()}
<h3>The rate of the load-only loop changed inside the one 7200 MT/s boot</h3>
{SEC2_BOOT}
<p class="tcap"><b>Table 3. The three visits of the part L line in the 7200 MT/s boot.</b> asmread is at position 1 and oldread at position 0 of each process {ref('json')}.</p>
{visits_table()}
<p class="tcap"><b>Table 4. Three kinds of distance (asmread), each for part L against the 8000 MT/s pool and for part L against F72d12 (earlier run of the same boot, not part of the rerun) {ref('json')}.</b> n of part L: {n7200(L_ASM)}. n of the pool L-1 to L-4: {n8000(P_L_ASM)}. n of F72d12: {n7200(F_ASM)}. At the nearest ends and at the medians, part L lies farther above F72d12 than above the pool. At the farthest ends the order is the opposite.</p>
{dist_table()}
<details><summary>Table view of Figure 2: every interval</summary>
{detail_fig2()}
</details>

<h2 id="open">3. What the data do not show</h2>
{INSUFF}

<h2 id="state">4. Machine state and system load</h2>
<p class="tcap"><b>Table 5. Machine state: each fact with its proof and its limit.</b></p>
{state_table()}
<h3>System load</h3>
<p class="tcap"><b>Table 6. 1-minute load average of Linux, read by the scripts directly before each launch {ref('json')}.</b> {LOAD_CAPTION}</p>
{load_table()}

<h2 id="refs">References</h2>
<p class="note">A script computed every rate of this page from the interval records of the facts sheet and from the thread rows of the csv files that these records name. It read the facts of section 4 from the raw files cited there {ref('gen', 'json', 'facts', 'build')}.</p>
<p class="note">R = <code>{R}</code><br>S = <code>{S}</code></p>
<ol class="refs">\x01REFLIST\x01</ol>
</main>
</body>
</html>
"""
    return page


PAGE, UNCITED = number_refs(build())

# ------------------------------------------------------------------ checks of the built page
words_n = sum(len([w for w in re.findall(r"\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)]) for t in PROSE)   # a lone "%" or "/" is not a word
how_n = sum(len([w for w in re.findall(r"\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)]) for t in re.findall(r'<ul class="how">(.*?)</ul>', PAGE, re.S))
check(700 <= words_n <= 1000, f"prose outside tables, captions, word list and references: {words_n} words (target 700 to 1000). "
                              f"Counted as captions and not as prose: the figure and table captions, and the reading notes under the two figures ({how_n} words)")
check(len(SHORT) == 3 and all(len(re.findall(r"[.!?](?:\s|$)", strip_tags(s).replace("MT/s.", "MT/s"))) == 1 for s in SHORT), "Short version: 3 sentences")
check(not UNCITED, f"references: {len(REFS)} paths exist, {len(REFS) - len(UNCITED)} are cited in the body, numbered in the order of first use")
check(not re.search(r"prefers-color-scheme|<script|<link|@import|url\(|<img|src=", PAGE), "one light theme, no script, no external file")
# control I and F72d12 carry their label in every bullet, caption, table row and tooltip that names them
units = [strip_tags(x[1]) for x in re.findall(r"<(li|p|figcaption|title|dd|tr)\b[^>]*>(.*?)</\1>", PAGE, re.S)]
for lab_, pat, must in (("control I", r"[Cc]ontrol I\b", ("added after the first numbers were seen",)),
                        ("F72d12", r"F72d12", ("not part of the rerun",))):
    hit = [u for u in units if re.search(pat, u)]
    miss = [u for u in hit if not any(m in u for m in must)]
    check(len(hit) > 0 and not miss, f"label of {lab_}: {len(hit)} text units name it, {len(miss)} without the label in the same unit" + ("" if not miss else ": " + " | ".join(m[:60] for m in miss)))
check(len(re.findall(r"<title>", PAGE)) - 1 >= N_DOTS + 2 * F1_NROWS, f"tooltips: {len(re.findall(r'<title>', PAGE)) - 1} SVG titles for {N_DOTS} interval dots and {3 * F1_NROWS} marks of figure 1 (drawn in three layouts)")
# wording checks of the visible text and of the tooltips (the style block is not text)
VISIBLE = strip_tags(re.sub(r"<style>.*?</style>", " ", PAGE, flags=re.S))
BANNED = [";", "load-only kernel", "at three times", "directly after none", "counter events", "bwx runners", "I row", "T rows", "ran above", "loop moved",
          "identical argument line", "facts file", "fall into", "lies against", "explains why", "By its name"]
found = [b for b in BANNED if b in VISIBLE]
check(not found, f"wording: none of {len(BANNED)} phrases that the review rejected is in the text or in a tooltip (semicolon, 'load-only kernel', 'at three times', ...)" + ("" if not found else ". Found: " + ", ".join(repr(b) for b in found)))

# "kernel" alone means the benchmark loop on this page. The operating system kernel is written "Linux kernel" ("kernel log" has its own entry in the word list)
bare = re.findall(r"(?<!Linux )\bkernel (?:thread|line|message)\w*", VISIBLE)
check(not bare, "wording: every kernel thread, kernel line and kernel message is written with 'Linux' before it" + ("" if not bare else ". Found: " + ", ".join(sorted(set(bare)))))
f2_areas = sorted(a for g in F2_GAPS for a in g[4])
check(len(F2_GAPS) == 2 and sum(g[1] for g in F2_GAPS) == N_DOTS == len(f2_areas),
      f"figure 2, hover areas: {N_DOTS} dots. The smallest distance of two dots is {min(g[2] for g in F2_GAPS):.2f} px (more than 5.2 px, the largest radius of a mark). "
      f"Each hover area is the part of a circle of {HIT_R:.0f} px radius that is nearer to its dot than to any other dot, so no two areas overlap. "
      f"{N_DOTS - sum(g[3] for g in F2_GAPS)} areas are the full circle ({max(f2_areas):.0f} px2), and a neighbour cuts {sum(g[3] for g in F2_GAPS)}. "
      f"Smallest area {f2_areas[0]:.0f} px2, median {median(f2_areas):.0f} px2 (a painted mark of 4.3 px radius covers {math.pi * 4.3 ** 2:.0f} px2)")

print("self-check list of make_report.py")
bad = 0
for ok, text in CHECKS:
    bad += 0 if ok else 1
    print(("  PASS  " if ok else "  FAIL  ") + text)
print(f"{len(CHECKS) - bad} of {len(CHECKS)} checks pass")
if bad:
    print("NOT WRITTEN: a check failed. The page on disk was not changed.")
    sys.exit(1)
DATA = PAGE.encode("utf-8")
with open(OUT, "wb") as f:
    f.write(DATA)
print(f"wrote {OUT} ({len(DATA)} bytes, {len(PAGE)} characters)")
print("Short version as built:")
for s in SHORT:
    print("  " + re.sub(r"\s+", " ", strip_tags(s)).replace("( ", "(").replace(" )", ")").strip())
