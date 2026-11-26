#!/usr/bin/env python3
"""test_runner11.py - local tests of the runner bwx11 (round 4).

It is test_runner10.py with the names of bwx11, plus the checks of round 4:
the three kernels read_nop64, read_nop96, read_nop128, the option --evict-mb,
and check_listing11.py on synthetic listings. Every check of test_runner10.py
is kept. Where bwx11 differs from bwx10 by design, the check was changed and
says so:
 - "source": bwx11.c without its blocks "bwx11+" to "bwx11-" must be the
   accepted bwx10.c (its sha256 stands in ref-bwx10/build.txt). That text
   without its blocks "bwx10+" to "bwx10-" must be bwx8.c, as before;
 - counts: 29 kernels (21 of bwx8, 5 of round 3, 3 of round 4), 33 trial
   checks of the self-test, 2 more M rows (evict_mb, evict_ns);
 - the listing checks use the accepted listing of bwx10 (ref-bwx10) and add
   well-formed listings of the three new kernels. The checks on the prefetch
   kernels of check_listing10.py part 2 became checks on the nop kernels,
   because those prefetch kernels are now part of the reference;
 - the comparison of a real local listing uses a local build of the bwx10
   source (bwx11.c without its marked blocks) as the reference, with 26
   kernels, in place of the build of bwx.c with 21 kernels.

Runs on the development machine (x86-64). It builds bwx11.c with the flags of
build11.sh into a temporary folder. The read kernels are then plain C stand-in
loops, so rates mean nothing. The tests check the harness: the plan checks,
the rows, the timed sequence, the trace, the bins, the counter states, the
evict step, and the two build scripts.

Usage: test_runner11.py            (KEEP=1 keeps the temporary folder)
Output: one line per check, "PASS name" or "FAIL name: detail".
Exit status: 0 only if every check passed.

A rule that the tests check on the output of bwx11 is a function that returns
a list of problems. Each such function is also run on changed rows, where it
must report a problem. So a rule that could not fail would be seen.

Some rules cannot be shown to fail on changed rows, because the defect is in
bwx11.c itself. For these the test builds a copy of bwx11.c with one defect
(MUTANTS) and requires that the check fails on it.
"""
import hashlib
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "bwx-2026-11-13")
X8 = os.path.join(HERE, "..", "bwx8-2026-11-14")  # the accepted runner of rounds 1 and 2; only read
REF = os.path.join(HERE, "ref-bwx8")
REF10 = os.path.join(HERE, "ref-bwx10")  # the accepted build of bwx10: listing.txt, offsets.tsv, build.txt
B8 = "bwx8"
B10 = "bwx10"
NEW_KERNELS = ["read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]  # round 3
NOP_KERNELS = ["read_nop64", "read_nop96", "read_nop128"]  # round 4
NOPS = {"read_nop64": 64, "read_nop96": 96, "read_nop128": 128}
NEW_M = ["rec_pad", "hot_copy", "rec_addr", "win_addr", "win_size", "stack_addr", "buf_addr", "tw_addr"]  # round 3
NEW_M11 = ["evict_mb", "evict_ns"]  # round 4
ADDR_KEYS = ("rec_addr", "win_addr", "stack_addr", "buf_addr", "tw_addr")
CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "
          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()
MIB8 = 8 << 20
HEAD1 = "# bwx8-plan v1"
HEAD3 = "# trial cond rep prev pfx pred tgt nwin win_ms count bins"
SUFFIX = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}

failed = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else ": " + str(detail)[:400]))
    if not ok:
        failed.append(name)
    return ok


def size_of(text):
    return int(text[:-1]) * SUFFIX[text[-1]] if text[-1] in SUFFIX else int(text)


def expected_windows(f):
    """[(phase, widx, kernel, pass_bytes, min_ns)] of one plan line, from its fields"""
    out = []
    for phase, text, n in (("prev", f[3], 1), ("prefix", f[4], 4), ("pred", f[5], 1)):
        if text == "-":
            continue
        kernel, rest = text.split("@")
        size, ms = rest.split(":")
        out += [(phase, i, kernel, size_of(size), int(ms) // n * 1000000) for i in range(n)]
    kernel, size = f[6].split("@")
    out += [("target", i, kernel, size_of(size), int(f[8]) * 1000000) for i in range(int(f[7]))]
    return out


def rows_of(out):
    """{row type: [fields]} of the output of bwx11"""
    r = {}
    for line in out.splitlines():
        if line and not line.startswith("#"):
            f = line.split(",")
            r.setdefault(f[0], []).append(f)
    return r


def of_trial(rows, kind, trial):
    return [f for f in rows.get(kind, []) if f[1] == str(trial)]


# ---- rules ----

def window_problems(plan_fields, wrows):
    """W rows of one trial against its plan line"""
    exp, p, prev_end = expected_windows(plan_fields), [], None
    if len(wrows) != len(exp):
        return ["%d W rows, %d expected" % (len(wrows), len(exp))]
    for w, e in zip(wrows, exp):
        phase, widx, kernel, pb, by, t0, t1 = w[2], int(w[3]), w[4], int(w[5]), int(w[6]), int(w[7]), int(w[8])
        if (phase, widx, kernel, pb) != e[:4]:
            p.append("window %s %d %s %d, expected %s" % (phase, widx, kernel, pb, e[:4]))
        if by <= 0 or by % pb:
            p.append("%s %d: %d bytes is not a whole number of passes above 0" % (phase, widx, by))
        if MIB8 % pb == 0 and by % MIB8:
            p.append("%s %d: %d bytes is not a multiple of 8 MiB" % (phase, widx, by))
        if t1 - t0 < e[4]:
            p.append("%s %d: lasts %d ns, requested %d ns" % (phase, widx, t1 - t0, e[4]))
        if not t0 < t1 or (prev_end is not None and t0 < prev_end):
            p.append("%s %d: timestamps go back" % (phase, widx))
        prev_end = t1
    return p


def e_problems(plan_fields, wrows, erow):
    """E row of one trial against its W rows: wall time and the two gaps"""
    p = []
    g = len(wrows) - int(plan_fields[7])
    t0 = [int(w[7]) for w in wrows]
    t1 = [int(w[8]) for w in wrows]
    if int(erow[2]) != t1[-1] - t0[0]:
        p.append("wall_ns %s, W rows give %d" % (erow[2], t1[-1] - t0[0]))
    gap = "NA" if g == 0 else str(t0[g] - t1[g - 1])
    if erow[6] != gap:
        p.append("gap_ns %s, W rows give %s" % (erow[6], gap))
    gaps = [t0[i] - t1[i - 1] for i in range(1, len(wrows))]
    if erow[7] != (str(max(gaps)) if gaps else "NA"):
        p.append("max_boundary_gap_ns %s, W rows give %s" % (erow[7], max(gaps) if gaps else "NA"))
    return p


def bin_problems(plan_fields, wrows, brows, clock_times=None):
    """B rows of one trial. clock_times: the times of the clock reads of the trace, if there is one."""
    p = []
    targets = [w for w in wrows if w[2] == "target"]
    if plan_fields[10] == "0":
        return ["B rows in a trial without bins"] if brows else []
    for w in targets:
        pb, by, t0, t1 = int(w[5]), int(w[6]), int(w[7]), int(w[8])
        bins = [b for b in brows if b[2] == w[3]]
        if not bins:
            p.append("window %s has no bin" % w[3])
            continue
        ends, cum = [int(b[4]) for b in bins], [int(b[5]) for b in bins]
        if [int(b[3]) for b in bins] != list(range(len(bins))):
            p.append("window %s: bin numbers are not 0, 1, 2, ..." % w[3])
        if ends != sorted(set(ends)) or ends[0] <= t0 or ends[-1] != t1:
            p.append("window %s: bin ends do not rise to the end of the window" % w[3])
        per_bin = [c - d for c, d in zip(cum, [0] + cum[:-1])]
        if sum(per_bin) != by or min(per_bin) <= 0:
            p.append("window %s: the bins sum to %d bytes, the window has %d" % (w[3], sum(per_bin), by))
        if any(b % pb for b in per_bin):
            p.append("window %s: a bin does not hold whole passes" % w[3])
        if len(bins) > 1 and ends[0] - t0 < 10000000:
            p.append("window %s: bin 0 is shorter than 10 ms" % w[3])
        if clock_times is not None and any(e not in clock_times for e in ends):
            p.append("window %s: a bin end is not a clock read of the trace" % w[3])
    if len(brows) != sum(1 for b in brows if b[2] in [w[3] for w in targets]):
        p.append("B rows of a window that is not a target window")
    return p


def trace_problems(plan_fields, events, wrows, erow):
    """TR events [(name, t)] of one trial. The timed sequence may hold clock
    reads and the first kernel call of each window. With count 'read' it also
    holds a counter read and a CPU clock read between the end clock and the
    start clock of each boundary of a target window. Nothing else."""
    exp, reads, p = expected_windows(plan_fields), plan_fields[9] == "read", []
    names = [e[0] for e in events]
    kf = [i for i, n in enumerate(names) if n.startswith("kernel_first")]
    want = ["kernel_first:%s:%d" % (e[0], e[1]) for e in exp]
    if [names[i] for i in kf] != want:
        return ["kernel calls %s, expected %s (a warm-up pass or a lost window)" % ([names[i] for i in kf], want)]
    start, end = kf[0] - 1, kf[-1] + 1
    while end < len(names) and names[end] == "clock":
        end += 1
    end -= 1
    if start < 0 or names[start] != "clock" or end == kf[-1]:
        return ["no clock read around the first or the last window"]
    count_tail = [["count_read", "cpu_clock"], ["cpu_clock"]] if reads else [[]]
    ends = []  # index of the end clock of each window
    for j, i in enumerate(kf):
        if names[i - 1] != "clock":
            p.append("window %d does not start directly after a clock read" % j)
        nxt = kf[j + 1] - 1 if j + 1 < len(kf) else end + 1  # the start clock of the next window
        body = names[i + 1:nxt]
        tail = []
        while body and body[-1] != "clock":
            tail.insert(0, body.pop())
        if not body or any(n != "clock" for n in body):
            p.append("inside window %d: %s" % (j, sorted(set(body) - {"clock"}) or "no clock read"))
        ends.append(i + len(body))
        if j + 1 < len(kf):
            allowed = count_tail if exp[j + 1][0] == "target" else [[]]
            if tail not in allowed:
                p.append("between window %d and window %d: %s, allowed %s" % (j, j + 1, tail, allowed))
        clocks, pb = len(body), exp[j][3]
        # the window ends at the first clock read at or after its requested duration
        if clocks > 1 and events[i + clocks - 1][1] - events[i - 1][1] >= exp[j][4]:
            p.append("window %d: runs on after the clock read that passed its requested duration" % j)
        if j < len(wrows) and clocks != int(wrows[j][6]) // (pb * max(1, MIB8 // pb)):
            p.append("window %d: %d clock reads for %s bytes" % (j, clocks, wrows[j][6]))
    before = names[:start]
    if reads and exp[0][0] == "target":
        if before[-2:] not in (["count_read", "cpu_clock"], ["cpu_clock", "cpu_clock"]):
            p.append("no counter read before the first target window")
        before = before[:-2] if before[-2:] == ["count_read", "cpu_clock"] else before[:-1]
    if [n for n in before if n not in ("count_open", "count_close")] != ["output", "page_read", "rusage", "cpu_clock"]:
        p.append("before the timed sequence: %s" % before)
    after = names[end + 1:]
    if reads:
        if after[:2] not in (["count_read", "cpu_clock"],) and after[:1] != ["cpu_clock"]:
            p.append("no counter read after the last target window")
        after = after[2:] if after[:1] == ["count_read"] else after[1:]
    if after != ["cpu_clock", "rusage", "page_read", "output"]:
        p.append("after the timed sequence: %s" % after)
    if not reads and "count_read" in names:
        p.append("a counter read in a trial with count %s" % plan_fields[9])
    # the W rows are the clock reads of the trace, and the gap is the time between two of them
    if len(wrows) == len(kf) and not p:
        for j, w in enumerate(wrows):
            if int(w[7]) != events[kf[j] - 1][1] or int(w[8]) != events[ends[j]][1]:
                p.append("window %d: the W row does not hold the clock reads of the trace" % j)
        g = len(wrows) - int(plan_fields[7])
        if g and erow[6] != str(events[kf[g] - 1][1] - events[ends[g - 1]][1]):
            p.append("gap_ns %s is not the time between the two clock reads of the trace" % erow[6])
    return p


# The timed sequence, read from the source and from the machine code. The
# trace holds only what the wrappers log themselves. These two rules do not
# depend on that log.
SEQ_SOURCE = {"timed_sequence": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall": 1},
              "timed_sequence_hot": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall_hot": 1},
              "tclock": {"now_ns": 1, "if": 1, "tev_add": 1},
              "tcall": {"if": 1, "tev_add": 1, "call": 1},
              "tcall_hot": {"if": 1, "tev_add": 1, "call": 1}}
SEQ_FUNCTIONS = ("timed_sequence", "timed_sequence_hot")
FN_HEAD = r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n"


def fn_span(src, fn):
    """(start, end) of the body of the C function fn, or None"""
    m = re.search(FN_HEAD % fn + r"(.*?)^\}\n", src, re.M | re.S)
    return (m.start(1), m.end(1)) if m else None


def replace_in(src, fn, good, bad):
    """src with 'good' replaced by 'bad' inside function fn (the whole text if fn is None).
    None unless 'good' stands exactly once there."""
    span = (0, len(src)) if fn is None else fn_span(src, fn)
    if src is None or span is None or src[span[0]:span[1]].count(good) != 1:
        return None
    return src[:span[0]] + src[span[0]:span[1]].replace(good, bad) + src[span[1]:]


def hot_source_problems(src):
    """timed_sequence_hot() of bwx11.c: between the start clock read of a window and the store of its results,
    the text names no field of the window record (x->), no field of the trial record (r->) and no win[]."""
    span = fn_span(src, "timed_sequence_hot")
    if span is None:
        return ["no function timed_sequence_hot"]
    body = src[span[0]:span[1]]
    a, b = body.find("        t0 = tclock(w);\n"), body.find("        x->bytes = bytes;\n")
    if a < 0 or b < a:
        return ["the start clock read or the store of the results is not found"]
    loop = re.sub(r"/\*.*?\*/", "", body[a:b], flags=re.S)
    p = ["the window loop of timed_sequence_hot names %s" % w for w in ("x->", "r->", "win") if w in loop]
    need = ("k = x->k", "phase = x->phase", "widx = x->widx", "bin_cap = x->bin_cap", "size = x->size", "passes = x->passes",
            "dur_ns = x->dur_ns", "bin = x->bin")
    return p + ["no copy '%s' before the window loop" % n for n in need if n not in body[:a]]
SEQ_ALLOWED = {"clock_gettime", "(indirect)", "tcount", "__stack_chk_fail"}


def seq_source_problems(src):
    """The words before a '(' in timed_sequence(), tclock() and tcall() of bwx11.c:
    one clock read at each end of a window, one kernel call per pass, the
    counter read at the two places of count 'read', and no other call."""
    p = []
    for fn, want in SEQ_SOURCE.items():
        m = re.search(r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n(.*?)^\}\n" % fn, src,
                      re.M | re.S)
        if not m:
            p.append("no function %s" % fn)
            continue
        got = {}
        for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)):
            got[name] = got.get(name, 0) + 1
        if got != want:
            p.append("%s holds %s, expected %s" % (fn, sorted(got.items()), sorted(want.items())))
    return p


def seq_targets(binary, fn="timed_sequence"):
    """{branch target outside function fn: count} from the machine code (x86-64 or AArch64 objdump text)"""
    out = subprocess.run(["objdump", "-d", "--no-show-raw-insn", "--disassemble=" + fn, binary],
                         stdout=subprocess.PIPE, universal_newlines=True).stdout
    t = {}
    for line in out.splitlines():
        f = line.split()
        if len(f) < 3 or not re.fullmatch(r"[0-9a-f]+:", f[0]):
            continue
        if re.search(r"\s(call|jmp)q?\s+\*", line) or f[1] in ("blr", "br"):
            name = "(indirect)"
        elif re.fullmatch(r"callq?|jmpq?|j[a-z]+|bl|b|b\.[a-z]+|cbn?z|tbn?z", f[1]) and re.fullmatch(r"<.*>", f[-1]):
            name = re.sub(r"\+0x[0-9a-f]+$|@plt", "", f[-1][1:-1])
            if name == fn:
                continue
        else:
            continue
        t[name] = t.get(name, 0) + 1
    return t


def seq_code_problems(targets, fn="timed_sequence"):
    p = ["%s reaches %s" % (fn, n) for n in sorted(set(targets) - SEQ_ALLOWED)]
    return p + ["%s has no call of %s" % (fn, n) for n in ("clock_gettime", "(indirect)") if n not in targets]


def placement_problems(lines, cpu, ctl):
    """Lines 'shim <call> pid=P tid=T <a> <b>' of the preloaded library, in time
    order. setaffinity: a = CPUs in the set, b = the first one. mmap: a = bytes.
    The controlling thread pins itself to ctl before the worker exists. The
    worker pins itself to cpu before it maps the buffer."""
    ev = []
    for line in lines:
        f = line.split()
        ev.append((f[1], f[3] == "tid=" + f[2][4:], f[3], int(f[4]), int(f[5])))
    first_worker = next((i for i, e in enumerate(ev) if not e[1]), None)
    if first_worker is None:
        return ["no call of the worker thread"]
    p = []
    if len({e[2] for e in ev}) != 2:
        p.append("%d threads, 2 expected" % len({e[2] for e in ev}))
    if ("setaffinity", True, 1, ctl) not in [(e[0], e[1], e[3], e[4]) for e in ev[:first_worker]]:
        p.append("the controlling thread did not pin itself to CPU %d before the worker started" % ctl)
    w = [e for e in ev if not e[1]]
    if (w[0][0], w[0][3], w[0][4]) != ("setaffinity", 1, cpu):
        p.append("the first call of the worker is %s %d %d, not its pin to CPU %d" % (w[0][0], w[0][3], w[0][4], cpu))
    if not any(e[0] == "mmap" and e[3] >= MIB8 for e in w[1:]):
        p.append("the worker did not map the buffer after its pin")
    if any(e[0] == "mmap" and e[1] and e[3] >= MIB8 for e in ev):
        p.append("the controlling thread mapped a buffer")
    return p


SHIM = r"""
#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
static void note(const char *what, long a, long b)
{
    char buf[128];
    int n = snprintf(buf, sizeof buf, "shim %s pid=%d tid=%ld %ld %ld\n", what, (int)getpid(), syscall(SYS_gettid), a, b);
    if (write(2, buf, (size_t)n) < 0)
        return;
}
int sched_setaffinity(pid_t pid, size_t len, const cpu_set_t *set)
{
    long first = -1;
    for (long c = 0; c < 8 * (long)len && first < 0; c++)
        if (CPU_ISSET_S(c, len, set))
            first = c;
    note("setaffinity", CPU_COUNT_S(len, set), first);
    return (int)syscall(SYS_sched_setaffinity, pid, len, set);
}
void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off)
{
    note("mmap", (long)len, 0);
    return (void *)syscall(SYS_mmap, addr, len, prot, flags, fd, off);
}
int madvise(void *addr, size_t len, int advice)
{
    if (getenv("SHIM_MADVISE_FAIL")) {
        errno = EINVAL;
        return -1;
    }
    return (int)syscall(SYS_madvise, addr, len, advice);
}
"""

# One defect each in a copy of bwx11.c: [(function or None for the whole text, text of bwx11.c, changed text)].
WARM = ("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) call(&kernels[x->k], "
        "&w->t, 0, x->size, 0, sink);\n        t0 = tclock(w);\n        next_bin")
PAGE = ("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) { long long vmx[4]; "
        "read_vmstat(vmx); fflush(stdout); }\n        t0 = tclock(w);\n        next_bin")
CLOCK = ("            t1 = tclock(w);\n", "            t1 = tclock(w);\n            if (x->bin) (void)now_ns();\n")
MUTANTS = {
    "a warm-up pass before the first target window": [("timed_sequence",) + WARM],
    "a page read and an output flush before the first target window": [("timed_sequence",) + PAGE],
    "an added clock read in a window with bins": [("timed_sequence",) + CLOCK],
    "the two context-switch counts exchanged in the E row":
        [(None, "r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]", "r->nivcsw[1] - r->nivcsw[0], r->nvcsw[1] - r->nvcsw[0]")],
    "wall time printed as cpu_ns":
        [(None, "(unsigned long long)(r->cpu[1] - r->cpu[0]));", "(unsigned long long)(r->win[r->nw - 1].t_end - r->win[0].t_start));")],
    "the pre snapshot printed in the post P row":
        [(None, 'print_p8(i, "post", &r->pg[1], r->vm[1]);', 'print_p8(i, "post", &r->pg[0], r->vm[0]);')],
    "C rows that hold the readings, not their differences":
        [(None, "(unsigned long long)(c1->enabled - c0->enabled)", "(unsigned long long)(c1->enabled)"),
         (None, "(unsigned long long)(c1->running - c0->running));\n        else", "(unsigned long long)(c1->running));\n        else"),
         (None, "(unsigned long long)(c1->val[at] - c0->val[at]));", "(unsigned long long)(c1->val[at]));")],
    "no X row count_multiplexed":
        [(None, "        if (m >= 0)\n", "        if (0 && m >= 0)\n")],
    "no X row sink":
        [(None, "    if (r->sink_ok == 0)\n        printf(\"X", "    if (0)\n        printf(\"X")],
    "no X row coverage_na":
        [(None, "    if (r->pg[0].kb_huge < 0 || r->pg[1].kb_huge < 0)\n", "    if (0)\n")],
    # gcc itself turns malloc + memset into calloc, which writes no page of a fresh block
    "record storage without the store to every page before the first trial":
        [(None, "        ((volatile char *)mem)[at] = 0;\n", "        ;\n"), (None, "    ((volatile char *)mem)[recsz.bytes - 1] = 0;\n", "")],
    # round 3: the same three defects of the timed sequence in the function of --hot-copy
    "a warm-up pass before the first target window, in timed_sequence_hot": [("timed_sequence_hot",) + WARM],
    "a page read and an output flush before the first target window, in timed_sequence_hot": [("timed_sequence_hot",) + PAGE],
    "an added clock read in a window with bins, in timed_sequence_hot": [("timed_sequence_hot",) + CLOCK],
    "timed_sequence_hot reads the pass count from the window record after every pass":
        [("timed_sequence_hot", "c < passes;", "c < passes && c < x->passes;")],
    "--hot-copy that still runs timed_sequence":
        [("run_trial", "    if (plan.hot_copy)\n", "    if (0)\n")],
    "--rec-pad that does not move the window records":
        [("alloc_records", "    win = (struct win *)((char *)win + plan.rec_pad);\n", "")],
    # round 4
    "an evict step that maps and unmaps the range but stores nothing":
        [("evict_step", "            m[i] = (uint64_t)i + (uint64_t)pass + 1;\n", "            ;\n")],
    "an evict step that runs after trial 0":
        [(None, "    if (evict_mb > 0 && evict_step() != 0) {\n", "    if (0) {\n"),
         (None, "        emit_trial(w, i);\n", "        emit_trial(w, i);\n        if (i == 0 && evict_mb > 0) evict_step();\n")],
}
SEQ_MUTANTS = list(MUTANTS)[:3]
ROW_MUTANTS = list(MUTANTS)[3:10]
TOUCH_MUTANT = list(MUTANTS)[10]
HOT_SEQ_MUTANTS = list(MUTANTS)[11:14]
HOT_READ_MUTANT, HOT_OFF_MUTANT, PAD_MUTANT = list(MUTANTS)[14:17]
EVICT_NOSTORE_MUTANT, EVICT_LATE_MUTANT = list(MUTANTS)[17:19]


def mutant_source(name):
    """bwx11.c with the defect 'name', or None if a text to change is not there exactly once"""
    with open(os.path.join(HERE, "bwx11.c")) as f:
        src = f.read()
    for fn, good, bad in MUTANTS[name]:
        src = replace_in(src, fn, good, bad)
        if src is None:
            return None
    return src


def mutant_build(name, tag):
    """builds the mutant in its own folder; returns the path of the binary, or None"""
    d = os.path.join(E.tmp, "mutant-" + tag)
    os.makedirs(d, exist_ok=True)
    src = mutant_source(name)
    if src is None:
        return None
    with open(os.path.join(d, "bwx11.c"), "w") as f:
        f.write(src)
    shutil.copy(os.path.join(HERE, "bwx11_selftest.c"), d)
    r = subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx11"), os.path.join(d, "bwx11.c")])
    return os.path.join(d, "bwx11") if r.returncode == 0 else None


# ---- running bwx11 ----

class Env:
    pass


E = Env()


def write_plan(name, lines, cpu=None, nbytes=MIB8, head1=HEAD1, head3=HEAD3, head2=None):
    cpu = E.cpu if cpu is None else cpu
    if head2 is None:
        head2 = "# step=T session=1 cpu=%d bytes=%d proc=0 seed=1 test=1" % (cpu, nbytes)
    path = os.path.join(E.tmp, name + ".plan")
    with open(path, "w") as f:
        f.write("\n".join([head1, head2, head3] + lines) + "\n")
    return path


def run(args, env_add=None, binary=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}
    env.update(env_add or {})
    r = subprocess.run([binary or E.bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                       universal_newlines=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def trial(plan, extra=None, cpu=None, nbytes="8M", env_add=None):
    return run(["--trial", "--cpus", str(E.cpu if cpu is None else cpu), "--bytes", nbytes, "--plan", plan] + (extra or []),
               env_add)


def fnv1a64(data):
    h = 14695981039346656037
    for b in data:
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return "%016x" % h


def plan_lines(path):
    with open(path) as f:
        return [line.split(" ") for line in f.read().splitlines()[3:]]


GOOD = "0 a 1 - oldread@8M:8 - oldread@8M 1 5 closed 0"


def test_bad_plans():
    """(a) every defect gives status 2, a message, and no row"""
    rc, out, _ = trial(write_plan("good", [GOOD]))
    check("a: the good control plan runs with status 0", rc == 0 and "\nE,0," in out, rc)

    def bad(name, line=None, **kw):
        plan = write_plan("bad", [GOOD] if line is None else [GOOD.replace("0 a", "0 first"), line], **kw)
        rc, out, err = trial(plan)
        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))

    t = "1 b 1 - oldread@8M:8 - %s 1 5 closed 0"
    bad("unknown kernel", t % "newread@8M")
    bad("write kernel as target", t % "write@8M")
    bad("copy kernel as target", t % "copy@8M")
    bad("write kernel as prefix", "1 b 1 - oldwrite@8M:8 - read@8M 1 5 closed 0")
    bad("copy kernel as predecessor", "1 b 1 - - asmcopy@8M:8 read@8M 1 5 closed 0")
    bad("size above --bytes", t % "read@16M")
    bad("size not a multiple of 256", t % "read@1000")
    bad("size 0", t % "read@0")
    bad("size with a fraction", t % "read@1.5M")
    bad("target with a duration", t % "read@8M:5")
    bad("prefix without a duration", "1 b 1 - oldread@8M - read@8M 1 5 closed 0")
    bad("pfx ms not a multiple of 4", "1 b 1 - oldread@8M:42 - read@8M 1 5 closed 0")
    bad("pred ms 0", "1 b 1 - - read@8M:0 read@8M 1 5 closed 0")
    bad("bad count word", "1 b 1 - - - read@8M 1 5 maybe 0")
    bad("bins 2", "1 b 1 - - - read@8M 1 5 closed 2")
    bad("nwin 0", "1 b 1 - - - read@8M 0 5 closed 0")
    bad("nwin 4097", "1 b 1 - - - read@8M 4097 5 closed 0")
    bad("win_ms 0", "1 b 1 - - - read@8M 1 0 closed 0")
    bad("rep 5", "1 b 5 - - - read@8M 1 5 closed 0")
    bad("trial number out of order", "2 b 1 - - - read@8M 1 5 closed 0")
    bad("10 fields", "1 b 1 - - - read@8M 1 5 closed")
    bad("12 fields", "1 b 1 - - - read@8M 1 5 closed 0 0")
    bad("two spaces between fields", "1 b 1 -  - - read@8M 1 5 closed 0")
    bad("comma in cond", "1 b,c 1 - - - read@8M 1 5 closed 0")
    bad("empty line in the plan", "")
    # Record storage above the bound (design: "Bound its size"). The plan below needs 23.6 GB of bins. The address
    # space limit keeps a runner without the bound from writing that much memory on this machine.
    plan = write_plan("bad", [GOOD.replace("0 a", "0 first"), "1 b 1 - - - oldread@8M 4096 3600000 closed 1"])
    r = subprocess.run([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, timeout=120,
                       preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30)))
    check("a: status 2, no row and a plan message that names line 5: record storage above the bound of 256 MiB",
          r.returncode == 2 and r.stdout == "" and r.stderr.startswith("bad plan") and "line 5:" in r.stderr,
          "rc=%s out=%r err=%r" % (r.returncode, r.stdout[:80], r.stderr[:160]))
    bad("wrong header line 1", head1="# bwx8-plan v2")
    bad("wrong header line 3", head3=HEAD3.replace("win_ms count", "count win_ms"))
    bad("plan bytes differ from --bytes", head2="# step=T cpu=%d bytes=%d" % (E.cpu, MIB8 // 2))
    bad("plan cpu differs from --cpus", head2="# step=T cpu=%d bytes=%d" % (E.cpu2, MIB8))
    bad("plan without bytes=", head2="# step=T cpu=%d" % E.cpu)
    bad("header pair without =", head2="# step cpu=%d bytes=%d" % (E.cpu, MIB8))
    with open(os.path.join(E.tmp, "empty.plan"), "w") as f:
        f.write("\n".join([HEAD1, "# cpu=%d bytes=%d" % (E.cpu, MIB8), HEAD3]) + "\n")
    rc, out, err = trial(os.path.join(E.tmp, "empty.plan"))
    check("a: status 2 and no row: plan without a trial", rc == 2 and out == "" and err.strip() != "", rc)

    good = write_plan("good", [GOOD])

    def bad_opt(name, args, env_add=None):
        rc, out, err = run(args, env_add)
        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))

    base = ["--trial", "--bytes", "8M", "--plan", good]
    bad_opt("worker CPU equal to the control CPU", base + ["--cpus", str(E.cpu), "--ctl-cpu", str(E.cpu)])
    bad_opt("worker CPU equal to the default control CPU 0", ["--trial", "--bytes", "8M", "--cpus", "0", "--plan",
                                                               write_plan("cpu0", [GOOD], cpu=0)])
    bad_opt("CPU above 119", ["--trial", "--bytes", "8M", "--cpus", "120", "--plan", write_plan("cpu120", [GOOD], cpu=120)])
    bad_opt("control CPU above 119", base + ["--cpus", str(E.cpu), "--ctl-cpu", "120"])
    bad_opt("two CPUs", base + ["--cpus", "%d,%d" % (E.cpu, E.cpu2)])
    bad_opt("no --cpus", base)
    bad_opt("no --bytes", ["--trial", "--cpus", str(E.cpu), "--plan", good])
    bad_opt("no --plan", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M"])
    bad_opt("plan file that does not exist", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good + ".none"])
    bad_opt("unknown option", base + ["--cpus", str(E.cpu), "--warmup"])
    bad_opt("--seq together with --trial", base + ["--cpus", str(E.cpu), "--seq", "read"])
    if E.absent is not None:
        bad_opt("worker CPU outside the allowed set of the process",
                ["--trial", "--bytes", "8M", "--cpus", str(E.absent), "--plan", write_plan("absent", [GOOD], cpu=E.absent)])
    else:
        check("a: worker CPU outside the allowed set (no such CPU from 0 to 119 on this machine: NOT RUN)", False)
    counted = write_plan("counted", [GOOD, "1 b 1 - - - read@8M 1 5 open 0"])
    bad_opt("count open without counter settings", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted])
    bad_opt("count open with a PMU type and no event",
            ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted, "--pmu-type", "1"])
    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted],
                     {"BWX_PMU_TYPE": "1", "BWX_EVENTS": "task_clock=1"})
    check("a: the same plan runs with the counter settings in the environment", rc == 0 and "\nE,1," in out, rc)


ALL = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 4 20 closed 0",
       "1 B 1 - read@1M:40 - read@1M 4 20 closed 0",
       "2 C 1 - - - asmread@32K 3 25 closed 1",
       "3 A 2 - oldread@8M:40 oldread@1M:20 read@8M 2 20 closed 1"]


def test_rows():
    """(b) (d) (e) (h) and the M, K, S, P rows of a short plan with all phases"""
    plan = write_plan("all", ALL)
    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)])
    if not check("b: the plan with all phases runs with status 0", rc == 0, err):
        return
    rows, lines = rows_of(out), plan_lines(plan)
    m = {f[1]: f[2] for f in rows.get("M", [])}
    need = ["mode", "cpu", "ctl_cpu", "bytes", "thp", "madvise_ok", "check_bytes", "kernels", "plan_fnv1a64", "ntrials",
            "rec_windows", "rec_bins", "rec_bytes", "trace", "pmu_type", "events"]
    check("b: every required M key is present", all(k in m for k in need), [k for k in need if k not in m])
    with open(plan, "rb") as f:
        digest = fnv1a64(f.read())
    check("b: M values", (m.get("mode"), m.get("cpu"), m.get("ctl_cpu"), m.get("bytes"), m.get("check_bytes"), m.get("ntrials"),
                          m.get("trace"), m.get("plan_fnv1a64"), m.get("kernels"), m.get("thp")) ==
          ("trial", str(E.cpu), str(E.ctl), str(MIB8), str(MIB8), "4", "0", digest, "STAND-IN", "madvise"), m)
    check("b: the plan pairs are copied to M,plan.<key> rows",
          {k: v for k, v in m.items() if k.startswith("plan.")} ==
          {"plan.step": "T", "plan.session": "1", "plan.cpu": str(E.cpu), "plan.bytes": str(MIB8), "plan.proc": "0",
           "plan.seed": "1", "plan.test": "1"})
    nwin = sum(len(expected_windows(f)) for f in lines)
    check("b: record storage is sized from the plan and its size is printed",
          m.get("rec_windows") == str(nwin) and m.get("rec_bins") == str(3 * 4 + 2 * 4) and int(m.get("rec_bytes", 0)) > 0, m)
    k = {f[1]: f for f in rows.get("K", [])}
    check("b: one K row per kernel of the plan, with the address modulo 64",
          sorted(k) == ["asmread", "oldread", "read"] and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)
    s = rows.get("S", [])
    check("b: S rows hold the plan fields and the previous trial",
          [f[1:12] for f in s] == lines and [f[12:] for f in s] ==
          [["none", "none"], ["A", "oldread@8M"], ["B", "read@1M"], ["C", "asmread@32K"]], s)
    check("b: one E row per S row", [f[1] for f in rows.get("E", [])] == [f[1] for f in s])
    check("b: P rows pre and post for every trial",
          [(f[1], f[2]) for f in rows.get("P", [])] == [(str(i), w) for i in range(4) for w in ("pre", "post")] and
          all(len(f) == 9 for f in rows["P"]))
    last = 0
    for i, f in enumerate(lines):
        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]
        p = window_problems(f, w)
        check("b: trial %d: W rows complete, whole passes, 8 MiB rule, durations, monotonic times" % i, not p, p)
        check("b: trial %d: starts after the trial before it" % i, int(w[0][7]) >= last)
        last = int(w[-1][8])
        p = e_problems(f, w, e)
        check("d: trial %d: wall_ns, gap_ns and max_boundary_gap_ns equal the W-row differences" % i, not p, p)
        p = bin_problems(f, w, of_trial(rows, "B", i))
        check("e: trial %d: bins rise to the window end and their bytes sum to the window bytes" % i, not p, p)
        check("b: trial %d: E row has 10 fields and count_state closed" % i, len(e) == 10 and e[9] == "closed", e)
        wall, cpu = int(e[2]), int(e[3])
        check("b: trial %d: cpu_ns is CPU time: not the wall time, at least half of it, at most 1 ms above it" % i,
              cpu != wall and wall // 2 <= cpu <= wall + 1000000, e)
        pre, post = of_trial(rows, "P", i)
        check("b: trial %d: both P rows hold 8192 kB for the 8 MiB buffer and a number in every field" % i,
              pre[3] == post[3] == "8192" and all(v.isdigit() for v in pre[3:] + post[3:]), (pre, post))
    e = rows["E"]
    check("h: sink_ok is 1 for the trials that ran old read", [f[8] for f in e] == ["1", "NA", "NA", "1"], [f[8] for f in e])
    check("d: gap_ns is NA for the trial whose target has no window before it", e[2][6] == "NA", e[2])
    # One pass over 8 MiB takes more than 20 us with the stand-in kernels, so a warm-up pass in the gap fails here.
    check("d: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",
          min(int(e[0][6]), int(e[3][6])) < 20000, (e[0][6], e[3][6]))
    check("b: the 1 MiB windows hold a multiple of 8 MiB",
          all(int(w[6]) % MIB8 == 0 for w in rows["W"] if w[5] == str(1 << 20)) and
          any(w[5] == str(1 << 20) for w in rows["W"]))
    check("b: no X row, no C row and no TR row in this run", not rows.get("X") and not rows.get("C") and not rows.get("TR"),
          rows.get("X"))

    # every rule must report a problem on changed rows
    f0, w0, e0 = lines[0], of_trial(rows, "W", 0), of_trial(rows, "E", 0)[0]

    def changed(row_index, field, value):
        w = [list(x) for x in w0]
        w[row_index][field] = str(value)
        return w

    check("b: the rule fails on a lost W row", window_problems(f0, w0[:-1]))
    check("b: the rule fails on a byte count that is not whole passes", window_problems(f0, changed(2, 6, int(w0[2][6]) + 64)))
    check("b: the rule fails on 0 bytes", window_problems(f0, changed(2, 6, 0)))
    check("b: the rule fails on a 1 MiB window with 9 MiB", window_problems(f0, changed(5, 6, 9 << 20)))
    check("b: the rule fails on a window shorter than requested", window_problems(f0, changed(6, 8, int(w0[6][7]) + 19999999)))
    check("b: the rule fails on a start before the end of the window before", window_problems(f0, changed(6, 7, int(w0[5][8]) - 1)))
    check("b: the rule fails on a wrong kernel in a window", window_problems(f0, changed(5, 4, "asmread")))
    e_bad = list(e0)
    e_bad[6] = str(int(e0[6]) + 1)
    check("d: the rule fails on a gap_ns that differs from the W rows by 1 ns", e_problems(f0, w0, e_bad))
    e_bad = list(e0)
    e_bad[6] = "0"
    check("d: the rule fails on a gap_ns of 0", int(e0[6]) > 0 and e_problems(f0, w0, e_bad), e0)
    f2, w2, b2 = lines[2], of_trial(rows, "W", 2), of_trial(rows, "B", 2)
    b_bad = [list(x) for x in b2]
    b_bad[-1][5] = str(int(b_bad[-1][5]) - (32 << 10))
    check("e: the rule fails when the bins do not sum to the window bytes", bin_problems(f2, w2, b_bad))
    check("e: the rule fails when the last bin is lost", bin_problems(f2, w2, b2[:-1]))
    check("e: the rule fails on B rows in a trial without bins", bin_problems(lines[1], of_trial(rows, "W", 1), b2))
    check("e: a 25 ms window has 1 to 3 bins", all(1 <= len([b for b in b2 if b[2] == str(i)]) <= 3 for i in range(3)), b2)


def test_sequence_code():
    """(c) the timed sequence in the source and in the machine code, without the trace; both functions"""
    with open(os.path.join(HERE, "bwx11.c")) as f:
        src = f.read()
    p = seq_source_problems(src)
    check("c: source: timed_sequence() and timed_sequence_hot() hold 2 clock reads, 1 kernel call, 2 counter reads and "
          "no other call", not p, p)
    for name in SEQ_MUTANTS + HOT_SEQ_MUTANTS:
        m = mutant_source(name)
        check("c: the source rule fails on a build with " + name, m is not None and seq_source_problems(m))
    p = hot_source_problems(src)
    check("c: source: the window loop of timed_sequence_hot() names no field of the window record", not p, p)
    m = mutant_source(HOT_READ_MUTANT)
    check("c: that rule fails on a source where " + HOT_READ_MUTANT, m is not None and hot_source_problems(m))
    for fn in SEQ_FUNCTIONS:
        t = seq_targets(E.bin, fn)
        p = seq_code_problems(t, fn)
        check("c: machine code: %s reaches only clock_gettime, the kernels, tcount and the stack-guard failure" % fn,
              not p, (p, t))
        check("c: the machine-code rule fails on a call of fflush (%s)" % fn, seq_code_problems(dict(t, fflush=1), fn))
        check("c: the machine-code rule fails on a helper that is not inlined (%s)" % fn, seq_code_problems(dict(t, tclock=2), fn))
        check("c: the machine-code rule fails when the function has no kernel call (%s)" % fn,
              seq_code_problems({k: v for k, v in t.items() if k != "(indirect)"}, fn))
    for fn, name, tag in (("timed_sequence", SEQ_MUTANTS[1], "seq"), ("timed_sequence_hot", HOT_SEQ_MUTANTS[1], "seqhot")):
        b = mutant_build(name, tag)
        other = [f for f in SEQ_FUNCTIONS if f != fn][0]
        check("c: the machine-code rule fails for %s on a real build with %s, and passes for %s" % (fn, name, other),
              b is not None and any("read_vmstat" in x or "fflush" in x for x in seq_code_problems(seq_targets(b, fn), fn)) and
              not seq_code_problems(seq_targets(b, other), other), b and seq_targets(b, fn))


def test_disturbed():
    """(i) the values that mark a disturbed trial, from a trial that shares its CPU with another process"""
    plan = write_plan("shared", ["0 a 1 - oldread@8M:200 - oldread@8M 2 100 closed 0"])
    spin = subprocess.Popen([sys.executable, "-c", "import os\nos.sched_setaffinity(0, {%d})\nwhile True:\n    pass" % E.cpu])
    try:
        time.sleep(0.5)  # the other process now runs on the worker CPU
        rc, out, err = trial(plan)
    finally:
        spin.kill()
        spin.wait()
    e = rows_of(out).get("E", [[]])[0]
    if not check("i: the trial on a shared CPU ends with status 0 and an E row", rc == 0 and len(e) == 10, err):
        return
    check("i: shared CPU: cpu_ns is below 0.9 x wall_ns", int(e[3]) < 0.9 * int(e[2]), e)
    check("i: shared CPU: nivcsw (involuntary) is above 0 and nvcsw (voluntary) is 0", int(e[5]) > 0 and e[4] == "0", e)


def test_placement():
    """(j) pin before allocation, the CPU of the controlling thread, and the X row of a failed madvise"""
    d = os.path.join(E.tmp, "shim")
    os.makedirs(d)
    with open(os.path.join(d, "shim.c"), "w") as f:
        f.write(SHIM)
    so = os.path.join(d, "shim.so")
    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, os.path.join(d, "shim.c")], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    if not check("j: the library that logs sched_setaffinity and mmap builds", r.returncode == 0, r.stdout):
        return
    plan = write_plan("place", [GOOD])
    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)], env_add={"LD_PRELOAD": so})
    lines = [x for x in err.splitlines() if x.startswith("shim ")]
    p = placement_problems(lines, E.cpu, E.ctl) if rc == 0 and lines else ["rc=%s, %d lines" % (rc, len(lines))]
    check("j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself "
          "before it maps the buffer", not p, (p, lines))
    if not p:
        w = [i for i, x in enumerate(lines) if x.split()[3] != "tid=" + x.split()[2][4:]]
        late = lines[:w[0]] + [lines[w[1]], lines[w[0]]] + lines[w[1] + 1:]
        check("j: the rule fails when the worker maps the buffer before its pin", placement_problems(late, E.cpu, E.ctl))
        no_ctl = [x for x in lines if not x.endswith(" 1 %d" % E.ctl)]
        check("j: the rule fails when the controlling thread does not pin itself", placement_problems(no_ctl, E.cpu, E.ctl))
        check("j: the rule fails when the worker pins itself to another CPU", placement_problems(lines, E.ctl, E.ctl))
    rows = rows_of(out)
    m = {f[1]: f[2] for f in rows.get("M", [])}
    check("j: madvise that works: M,madvise_ok,1 and no X row", m.get("madvise_ok") == "1" and not rows.get("X"), rows.get("X"))
    rc, out, err = trial(plan, env_add={"LD_PRELOAD": so, "SHIM_MADVISE_FAIL": "1"})
    rows = rows_of(out)
    m = {f[1]: f[2] for f in rows.get("M", [])}
    check("j: madvise that fails: status 0, M,madvise_ok,0, the row X,-1,madvise, and the trial still runs",
          rc == 0 and m.get("madvise_ok") == "0" and [f[1:3] for f in rows.get("X", [])] == [["-1", "madvise"]] and
          len(rows.get("E", [])) == 1, (rc, m.get("madvise_ok"), rows.get("X")))


def events_of(rows, trial_no):
    tr = of_trial(rows, "TR", trial_no)
    ok = [int(f[2]) for f in tr] == list(range(len(tr)))
    return [(f[3], int(f[4])) for f in tr], ok


def test_trace():
    """(c) the trace of closed, open and read trials, and the trace rule on broken traces"""
    plan = write_plan("trace", ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",
                                "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",
                                "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",
                                "3 D 1 - - - read@8M 2 20 read 0",
                                "4 E 1 - - - oldread@8M 2 20 closed 0"])
    rc, out, err = trial(plan, ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])
    if not check("c: the trace run ends with status 0", rc == 0, err):
        return
    rows, lines = rows_of(out), plan_lines(plan)
    states = [f[9] for f in rows["E"]]
    E.soft_counters = states == ["closed", "read", "open", "read", "closed"]
    check("c: the software events of Linux (PMU type 1) open on this machine", E.soft_counters, (states, rows.get("X")))
    saved = None
    for i, f in enumerate(lines):
        ev, numbered = events_of(rows, i)
        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]
        p = trace_problems(f, ev, w, e)
        check("c: trial %d (count %s): TR rows are numbered 0, 1, 2, ..." % (i, f[9]), numbered and len(ev) > 0)
        check("c: trial %d (count %s): no forbidden event in the timed sequence, and the W rows and gap_ns "
              "are clock reads of the trace" % (i, f[9]), not p, p)
        names = [n for n, _ in ev]
        want_reads = int(f[7]) + 1 if f[9] == "read" and E.soft_counters else 0
        check("c: trial %d (count %s): %d counter reads" % (i, f[9], want_reads), names.count("count_read") == want_reads,
              names.count("count_read"))
        check("c: trial %d: 2 page reads and 2 outputs, all outside the timed sequence" % i,
              names.count("page_read") == 2 and names.count("output") == 2)
        if i == 0:
            saved = (f, ev, w, e)
            times = {t for n, t in ev if n == "clock"}
            p = bin_problems(f, w, of_trial(rows, "B", 0), times)
            check("e: every bin end of the trace run is a clock read of the trace", not p, p)
            b_bad = [list(x) for x in of_trial(rows, "B", 0)]
            b_bad[0][4] = str(int(b_bad[0][4]) + 1)
            check("e: the rule fails on a bin end that is no clock read", bin_problems(f, w, b_bad, times))
    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)
    check("c: no minor page fault of the worker between the two rusage reads of any trial (records and buffer were "
          "first touched before)", faults == [(str(i), "0") for i in range(5)], faults)
    b = mutant_build(TOUCH_MUTANT, "touch")
    out_m = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--trace", "--pmu-type", "1", "--events",
                 "task_clock=1,cpu_clock=0"], binary=b)[1] if b else ""
    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out_m, re.M)
    check("c: that check fails on a build with " + TOUCH_MUTANT, len(faults) == 5 and any(int(n) > 0 for _, n in faults), faults)
    opens = [[n for n, _ in events_of(rows, i)[0] if n in ("count_open", "count_close")] for i in range(5)]
    check("c: the group opens before the first counted trial and closes before the next closed trial",
          opens == [[], ["count_open"], [], [], ["count_close"]], opens)

    # the rule on broken traces of trial 0 (closed, all phases)
    f, ev, w, e = saved
    names = [n for n, _ in ev]
    tgt0 = names.index("kernel_first:target:0")
    tgt1 = names.index("kernel_first:target:1")
    pred = names.index("kernel_first:pred:0")

    def broken(at, name):
        return ev[:at] + [(name, ev[at - 1][1])] + ev[at:]

    check("c: the rule passes on the unchanged trace", not trace_problems(f, ev, w, e))
    check("c: the rule fails on a page read between predecessor and target", trace_problems(f, broken(tgt0 - 1, "page_read"), w, e))
    check("c: the rule fails on a page read between the start clock read of the target and its first kernel call",
          trace_problems(f, broken(tgt0, "page_read"), w, e))
    check("c: the rule fails on an output between two target windows", trace_problems(f, broken(tgt1 - 1, "output"), w, e))
    check("c: the rule fails on a counter read between predecessor and target in a closed trial",
          trace_problems(f, broken(tgt0 - 1, "count_read"), w, e))
    check("c: the rule fails on a CPU clock read between predecessor and target in a closed trial",
          trace_problems(f, broken(tgt0 - 1, "cpu_clock"), w, e))
    check("c: the rule fails on a warm-up kernel call before the target", trace_problems(f, broken(tgt0 - 1, "kernel_first:warmup:0"), w, e))
    check("c: the rule fails on a second first call of the target window", trace_problems(f, broken(tgt0 + 1, "kernel_first:target:0"), w, e))
    check("c: the rule fails on a page read inside the predecessor window", trace_problems(f, broken(pred + 2, "page_read"), w, e))
    check("c: the rule fails on a counter open inside the prefix", trace_problems(f, broken(names.index("kernel_first:prefix:2") + 2, "count_open"), w, e))
    check("c: the rule fails on a lost clock read of a window", trace_problems(f, ev[:tgt0 + 1] + ev[tgt0 + 2:], w, e))
    one_clock = ev[:tgt0 - 2] + ev[tgt0 - 1:]
    check("c: the rule fails when one clock read serves as end and start of a boundary", trace_problems(f, one_clock, w, e))
    e_bad = list(e)
    e_bad[6] = str(int(e[6]) + 5)
    check("d: the rule fails when gap_ns is not the time between the two clock reads", trace_problems(f, ev, w, e_bad))
    # target window 0 (20 ms): the clock read before its last one already lies at the requested end
    late = list(ev)
    late[tgt1 - 3] = ("clock", ev[tgt0 - 1][1] + 20000000)
    p = trace_problems(f, late, w, e)
    check("c: the rule fails on a window that runs on after a clock read at its requested end",
          names[tgt1 - 3] == "clock" and tgt1 - 3 > tgt0 and p == ["window 6: runs on after the clock read that passed "
                                                                 "its requested duration"], p)


def test_counters():
    """(f) a failed open is reported, and the timing rows stay"""
    lines = ["0 A 1 - oldread@8M:20 - oldread@8M 2 10 closed 0",
             "1 B 1 - oldread@8M:20 - oldread@8M 2 10 read 0",
             "2 C 1 - oldread@8M:20 - oldread@8M 2 10 open 0"]
    plan = write_plan("count", lines)
    rc, out, err = trial(plan, ["--pmu-type", "999999", "--events", "cycles=0x11,instructions=0x08"])
    rows = rows_of(out)
    check("f: a PMU type that does not exist: status 0", rc == 0, err)
    x = [(f[1], f[2]) for f in rows.get("X", [])]
    check("f: an X row with code count_open for each counted trial, none for the closed trial",
          x == [("1", "count_open"), ("2", "count_open")], rows.get("X"))
    check("f: count_state is fail in the E rows of the counted trials", [f[9] for f in rows.get("E", [])] == ["closed", "fail", "fail"],
          rows.get("E"))
    check("f: the timing rows of the failed trials are kept",
          all(not window_problems(f, of_trial(rows, "W", i)) for i, f in enumerate(plan_lines(plan))))
    c = rows.get("C", [])
    check("f: the C rows of the failed read trial hold NA for the group and a number for the CPU time",
          len(c) == 2 and all(f[1] == "1" and f[3:5] == ["NA", "NA"] and f[5].isdigit() and f[6:] == ["NA", "NA"] for f in c), c)
    m = {f[1]: f[2] for f in rows.get("M", [])}
    check("f: M rows record the PMU type and the event codes", m.get("pmu_type") == "999999" and
          m.get("events") == "cycles=0x11;instructions=0x8", m)

    if not getattr(E, "soft_counters", False):
        check("f: counter rows with software events (NOT RUN: the events did not open in the trace test)", False)
        return
    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,bad=999"])
    rows = rows_of(out)
    c = rows.get("C", [])
    check("f: one event of two does not open: X rows count_open and count_state fail",
          rc == 0 and [(f[1], f[2]) for f in rows.get("X", [])] == [("1", "count_open"), ("2", "count_open")] and
          [f[9] for f in rows["E"]] == ["closed", "fail", "fail"] and "1 of 2" in rows["X"][0][3], rows.get("X"))
    check("f: the event that opened has numbers, the other has NA",
          len(c) == 2 and all(f[3].isdigit() and f[6].isdigit() and f[7] == "NA" for f in c), c)
    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])
    rows = rows_of(out)
    c = rows.get("C", [])
    check("f: events that open: no X row, count_state closed, read, open",
          rc == 0 and not rows.get("X") and [f[9] for f in rows["E"]] == ["closed", "read", "open"], rows.get("X"))
    check("f: one C row per target window of the read trial only, with enabled, running, CPU time and 2 counts",
          [(f[1], f[2]) for f in c] == [("1", "0"), ("1", "1")] and all(len(f) == 8 and all(v.isdigit() for v in f[3:]) for f in c), c)
    check("f: running time equals enabled time, and the CPU time is above 0",
          all(f[3] == f[4] and int(f[5]) > 0 for f in c), c)
    # A C row holds the change over its target window. The group was opened before the 20 ms prefix, so a row that
    # held the reading itself would be at least 3 times the 10 ms window.
    tw = [w for w in of_trial(rows, "W", 1) if w[2] == "target"]
    span = [int(w[8]) - int(w[7]) for w in tw]
    check("f: enabled time, CPU time and both software clocks of a C row lie between half of the window time and "
          "the window time plus 1 ms", len(c) == len(span) == 2 and
          all(n // 2 <= int(v) <= n + 1000000 for f, n in zip(c, span) for v in f[3:]), (c, span))


def test_kill_and_seq():
    """(g) S row without E row after SIGKILL, and the unchanged --seq mode"""
    plan = write_plan("kill", [GOOD, "1 long 1 - oldread@8M:400 - oldread@8M 4 5000 closed 0"])
    path = os.path.join(E.tmp, "kill.csv")
    with open(path, "w") as f:
        proc = subprocess.Popen([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=f,
                                stderr=subprocess.DEVNULL)
    deadline = time.time() + 30
    while time.time() < deadline and proc.poll() is None:
        with open(path) as f:
            if "\nS,1," in f.read():
                break
        time.sleep(0.02)
    time.sleep(0.2)  # the worker is now inside the timed sequence of trial 1
    alive = proc.poll() is None
    proc.send_signal(signal.SIGKILL)
    rc = proc.wait()
    with open(path) as f:
        rows = rows_of(f.read())
    check("g: the process was killed inside trial 1", alive and rc == -signal.SIGKILL, rc)
    check("g: after SIGKILL the S row of trial 1 has no E row, and trial 0 has both",
          [f[1] for f in rows.get("S", [])] == ["0", "1"] and [f[1] for f in rows.get("E", [])] == ["0"], rows.get("E"))
    check("g: no W row of the interrupted trial", not of_trial(rows, "W", 1))

    args = ["--seq", "oldread,asmread@1M,oldread,read", "--bytes", "8M", "--rounds", "2", "--min-ms", "20", "--stop", "pass",
            "--cpus", str(E.cpu), "--threads", "1"]
    rc, out, err = run(args)
    rc0, out0, _ = run(args, binary=E.bin_old)
    r = rows_of(out)
    check("g: --seq mode prints 8 I rows, 8 T rows and 8 P rows", rc == 0 and
          [len(r.get(k, [])) for k in "ITP"] == [8, 8, 8], (rc, err))

    def shape(text):
        return [line if line.startswith("#") else (line.split(",")[0], len(line.split(",")), line.split(",")[1:4]) for line in text.splitlines()]

    check("g: --seq mode: comment lines byte for byte and row order as the binary built from bwx.c",
          rc0 == 0 and shape(out) == shape(out0))
    check("g: that comparison can fail: another sequence gives another shape",
          shape(out) != shape(run(args[:1] + ["oldread,read"] + args[2:])[1]))


def strip_marked(text, tag="bwx10"):
    """(text without the blocks between a line '<tag>+' and a line '<tag>-', number of blocks, markers left)"""
    out, n = re.subn(r"^[ \t]*/\* %s\+ \*/\n.*?^[ \t]*/\* %s- \*/\n" % (tag, tag), "", text, flags=re.M | re.S)
    return out, n, out.count(tag + "+") + out.count(tag + "-")


def ref10_digest(name):
    """the sha256 of a file of the accepted bwx10 build, from ref-bwx10/build.txt"""
    with open(os.path.join(REF10, "build.txt")) as f:
        m = re.search(r"^([0-9a-f]{64})  %s$" % re.escape(name), f.read(), re.M)
    return m.group(1) if m else None


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def path_to_seq(binary, last="timed_sequence"):
    """(start of call modulo 64, [(function, distance from call, size)] from call to the function 'last')"""
    out = subprocess.run(["nm", "-n", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout
    s = [(p[3], int(p[0], 16), int(p[1], 16)) for p in (line.split() for line in out.splitlines()) if len(p) == 4 and p[2] in "tT"]
    names = [x[0] for x in s]
    if "call" not in names or last not in names:
        return None, []
    i, j = names.index("call"), names.index(last)
    return s[i][1] % 64, [(x[0], x[1] - s[i][1], x[2]) for x in s[i:j + 1]]


def test_source():
    """bwx11.c is the accepted bwx10.c plus marked additions; bwx10.c is bwx8.c plus marked additions; bwx8.c
    holds the text of bwx.c"""
    with open(os.path.join(OLD, "bwx.c")) as f:
        old = f.read()
    with open(os.path.join(HERE, "bwx11.c")) as f:
        new11 = f.read()
    with open(os.path.join(X8, B8 + ".c")) as f:
        new8 = f.read()
    new10, blocks11, left11 = strip_marked(new11, "bwx11")
    want = ref10_digest("bwx10.c")
    check("source: bwx11.c without its %d blocks 'bwx11+' to 'bwx11-' is the accepted bwx10.c byte for byte (sha256 of "
          "ref-bwx10/build.txt)" % blocks11,
          blocks11 >= 8 and left11 == 0 and want is not None and sha256(new10) == want, (blocks11, left11, want, sha256(new10)))
    check("source: that comparison can fail: one changed character outside the marked blocks",
          sha256(strip_marked(new11.replace("x->bytes = bytes;", "x->bytes = bytes ;", 1), "bwx11")[0]) != want)
    check("source: the text of bwx11.c that the compiler sees includes bwx11_selftest.c once, and the old include line "
          "stands inside '#if 0'",
          new11.count('#if 0\n/* bwx11- */\n#include "bwx10_selftest.c"\n/* bwx11+ */\n#endif\n#include "bwx11_selftest.c"\n') == 1 and
          new11.count('#include "bwx11_selftest.c"') == 1 and new11.count('#include "bwx10_selftest.c"') == 1)
    new, blocks, left = strip_marked(new10)
    inc = '#include "bwx10_selftest.c"\n'
    check("source: bwx10.c (that text) without its %d marked blocks, and with the old name of the self-test file, is the "
          "file of the accepted runner bwx8 byte for byte" % blocks,
          blocks >= 10 and left == 0 and new.count(inc) == 1 and new.replace(inc, inc.replace("bwx10", B8)) == new8,
          (blocks, left, len(new), len(new8)))
    check("source: that comparison can fail: one changed character outside the marked blocks (bwx8 level)",
          strip_marked(new10.replace("x->bytes = bytes;", "x->bytes = bytes ;", 1))[0].replace(inc, inc.replace("bwx10", B8)) != new8)
    a8, a11 = fn_span(new8, "timed_sequence"), fn_span(new11, "timed_sequence")
    check("source: timed_sequence() of bwx11.c is the text of the accepted runner",
          a8 is not None and a11 is not None and new8[a8[0]:a8[1]] == new11[a11[0]:a11[1]])
    h10, h11 = fn_span(new10, "timed_sequence_hot"), fn_span(new11, "timed_sequence_hot")
    check("source: timed_sequence_hot() of bwx11.c is the text of bwx10.c",
          h10 is not None and h11 is not None and new10[h10[0]:h10[1]] == new11[h11[0]:h11[1]])
    a, b = old.index("#define _GNU_SOURCE"), old.index('#include "bwx_selftest.c"')
    check("source: bwx.c from '#define _GNU_SOURCE' to the end of parse_events() stands unchanged in bwx11.c without "
          "its marked blocks", new.count(old[a:b]) == 1)
    kernels_end = new.index(old[a:b]) + len(old[a:b])
    check("source: every line of the trial mode stands after that text",
          min(new.index(s) for s in ("timed_sequence", "trial_main", "tclock", "struct trial")) > kernels_end)
    hook = ('    for (int i = 1; i < argc; i++)\n        if (!strcmp(argv[i], "--trial"))\n'
            '            return trial_main(argc, argv);\n')
    check("source: main() of bwx11.c is main() of bwx.c plus the 3 lines that start the trial mode",
          new11.count(hook) == 1 and new11[new11.index("int main("):].replace(hook, "") == old[old.index("int main("):])
    check("source: in bwx11.c the evict step and its variables stand after timed_sequence_hot() and before trial_worker()",
          0 < new11.find("static void timed_sequence_hot(struct tw") < new11.find("\nstatic long evict_mb;") <
          new11.find("static int evict_step(void)") < new11.find("\nstatic void *trial_worker("))
    with open(os.path.join(OLD, "bwx_selftest.c")) as f:
        old_st = f.read()
    with open(os.path.join(HERE, "bwx11_selftest.c")) as f:
        new_st11 = f.read()
    with open(os.path.join(X8, B8 + "_selftest.c")) as f:
        new_st8 = f.read()
    new_st10, blocks11, left11 = strip_marked(new_st11, "bwx11")
    want = ref10_digest("bwx10_selftest.c")
    check("source: bwx11_selftest.c without its %d blocks 'bwx11+' to 'bwx11-' is the accepted bwx10_selftest.c byte for byte "
          "(sha256 of ref-bwx10/build.txt)" % blocks11,
          blocks11 >= 3 and left11 == 0 and want is not None and sha256(new_st10) == want, (blocks11, left11))
    new_st, blocks, left = strip_marked(new_st10)
    check("source: bwx10_selftest.c (that text) without its %d marked blocks is the self-test file of the accepted runner" % blocks,
          blocks >= 3 and left == 0 and new_st == new_st8)
    a, b = old_st.index("static int failures;"), old_st.index("static int selftest(void)")
    check("source: the kernel checks of bwx_selftest.c stand unchanged in bwx11_selftest.c without its marked blocks",
          new_st.count(old_st[a:b]) == 1)

    def syms(binary):
        out = subprocess.run(["nm", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout
        return {p[3]: (int(p[0], 16) % 64, p[1]) for p in (line.split() for line in out.splitlines())
                if len(p) == 4 and p[3].startswith("k_")}

    s_old, s_8, s_10, s_new = syms(E.bin_old), syms(E.bin8), syms(E.bin10), syms(E.bin)
    common = {k: v for k, v in s_new.items() if k in s_old}
    check("source: the 21 old kernels have the same start modulo 64 and the same size in the local builds of bwx, of the "
          "accepted runner and of bwx11", len(s_old) == 21 and s_old == s_8 == common,
          {k: (s_old[k], s_new.get(k)) for k in s_old if s_old[k] != s_new.get(k)})
    check("source: the 26 kernels of bwx10 have the same start modulo 64 and the same size in the local builds of the bwx10 "
          "source and of bwx11", len(s_10) == 26 and s_10 == {k: v for k, v in s_new.items() if k in s_10},
          {k: (s_10[k], s_new.get(k)) for k in s_10 if s_10[k] != s_new.get(k)})
    check("source: bwx11 has 29 kernels: the 21 old ones, the 5 of round 3 and the 3 new ones",
          sorted(set(s_new) - set(s_old)) == sorted("k_" + k for k in NEW_KERNELS + NOP_KERNELS) and
          sorted(set(s_new) - set(s_10)) == sorted("k_" + k for k in NOP_KERNELS), sorted(set(s_new) - set(s_old)))
    check("source: the three new kernels start where asmread starts, modulo 64 (the pad of asmread)",
          all(s_new.get("k_" + k, (None,))[0] == s_new["k_asmread"][0] for k in NOP_KERNELS), [s_new.get("k_" + k) for k in NOP_KERNELS])

    def order(binary):
        out = subprocess.run(["nm", "-n", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout
        return [line.split()[-1] for line in out.splitlines() if line.split()[-1].startswith("k_")]

    o = order(E.bin)
    check("source: in the binary the 5 kernels of round 3 stand after every old kernel, in the order of the table, and the "
          "3 new kernels stand after them",
          o[21:26] == ["k_" + k for k in NEW_KERNELS] and o[:21] == order(E.bin8) and o[:26] == order(E.bin10) and
          o[26:] == ["k_" + k for k in NOP_KERNELS], o[20:])

    # The pad after the new kernels. bwx11.c holds the value of the accepted AArch64 build (24) in
    # PAD_after_kernels, and PAD_after_kernels11 takes that value. A copy built with the value of the local build
    # of the accepted runner must place every function from call() to timed_sequence() as that build does.
    E.call8, path8 = path_to_seq(E.bin8)
    if not check("source: the local build of the accepted runner has call() and timed_sequence() as functions "
                 "(needed for the placement checks)", E.call8 is not None and len(path8) >= 3, path8[:3]):
        return
    E.bin_placed = os.path.join(E.tmp, "bwx11-placed")
    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % E.call8, "-o", E.bin_placed, os.path.join(HERE, "bwx11.c")])
    call_p, path_p = path_to_seq(E.bin_placed) if r.returncode == 0 else (None, [])
    check("source: with the pad of the local build, the functions from call() to timed_sequence() (at least 10) have the "
          "start modulo 64, the distances and the sizes of the accepted runner",
          call_p == E.call8 and path_p == path8 and len(path8) >= 10, (call_p, E.call8, len(path8), [x for x in zip(path_p, path8) if x[0] != x[1]][:3]))
    other = (E.call8 + 4) % 64
    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % other, "-o", E.bin_placed + "-off", os.path.join(HERE, "bwx11.c")])
    check("source: that comparison can fail: a pad 4 bytes larger moves call() by 4 bytes",
          r.returncode == 0 and path_to_seq(E.bin_placed + "-off")[0] == other, (other, path_to_seq(E.bin_placed + "-off")[0]))
    with open(os.path.join(REF, "listing.txt")) as f:
        ref_text = f.read()
    last = max(int(x, 16) for x in re.findall(r"^\s+([0-9a-f]+):\t", ref_text, re.M))
    m = re.search(r"^#define PAD_after_kernels (\d+)$", new11, re.M)
    check("source: the pad in bwx11.c (24) is the address after the last instruction of the last kernel in "
          "ref-bwx8/listing.txt (0x4a14, a ret), modulo 64",
          m is not None and int(m.group(1)) == (last + 4) % 64 == 24 and "    %x:\tret\n" % last in ref_text, (m and m.group(1), hex(last)))
    # round 4: the same placement against the bwx10 source, up to timed_sequence_hot(). Both local builds use the
    # pad 24 of the source, so call() starts at 24 modulo 64 in both.
    call10, path10 = path_to_seq(E.bin10, "timed_sequence_hot")
    call11, path11 = path_to_seq(E.bin, "timed_sequence_hot")
    check("source: the functions from call() to timed_sequence_hot() (at least 12) have the start modulo 64, the distances "
          "and the sizes of the local build of the bwx10 source",
          call10 is not None and call11 == call10 == 24 and path11 == path10 and len(path10) >= 12,
          (call11, call10, len(path10), [x for x in zip(path11, path10) if x[0] != x[1]][:3]))
    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels11=28", "-o", E.bin_placed + "-off11", os.path.join(HERE, "bwx11.c")])
    check("source: that comparison can fail: with PAD_after_kernels11 set to 28, call() starts at 28 modulo 64",
          r.returncode == 0 and path_to_seq(E.bin_placed + "-off11", "timed_sequence_hot")[0] == 28)
    check("source: PAD_after_kernels11 takes the value of PAD_after_kernels unless it is given",
          "#ifndef PAD_after_kernels11\n#define PAD_after_kernels11 PAD_after_kernels\n#endif\nPLACE(after_kernels11);\n" in new11)
    with open(os.path.join(REF10, "build.txt")) as f:
        placed = re.search(r"^## placement bwx10 \(start modulo 64\): call=(\d+) ", f.read(), re.M)
    check("source: ref-bwx10/build.txt records call() of the accepted bwx10 at that pad (24) modulo 64",
          placed is not None and m is not None and placed.group(1) == m.group(1) == "24", placed and placed.group(0))
    # the bwx10 source with the local pad: the reference binary of the placement record of build11.sh
    E.bin10_placed = os.path.join(E.tmp, "bwx10-placed")
    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % E.call8, "-o", E.bin10_placed, os.path.join(E.src10, "bwx10.c")])
    check("source: the bwx10 source builds with the local pad (needed for the placement record of build11.sh)", r.returncode == 0)
    span = fn_span(new11, "evict_step")
    body = re.sub(r"/\*.*?\*/", "", new11[span[0]:span[1]], flags=re.S) if span else ""
    check("source: evict_step() maps plain anonymous private memory, stores one word per 64 B line in ascending order in "
          "2 passes, unmaps, and calls no madvise",
          "mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0)" in body and
          "    for (int pass = 0; pass < 2; pass++)\n        for (size_t i = 0; i < len / 8; i += 8)\n            m[i] = " in body and
          "volatile uint64_t *m" in body and "munmap((void *)m, len)" in body and "madvise" not in body and
          "size_t len = (size_t)evict_mb << 20;" in body, body[:300])


def test_selftest():
    rc, out, err = run(["--selftest"])
    trial_lines = [line for line in out.splitlines() if line.startswith("trial,")]
    check("selftest: status 0, no FAIL line, 33 checks of the trial mode (19 of the accepted runner, 8 with --hot-copy, "
          "3 of the touch test, 3 of the evict step)",
          rc == 0 and "FAIL" not in out and out.rstrip().endswith("# failures=0") and len(trial_lines) == 33 and
          all(line.endswith(",pass") for line in trial_lines) and
          len([x for x in trial_lines if x.startswith("trial,hot copy: ")]) == 8 and
          len([x for x in trial_lines if x.startswith("trial,hot touch: ")]) == 3 and
          len([x for x in trial_lines if x.startswith("trial,evict: ")]) == 3, (rc, err, len(trial_lines)))
    out10 = run(["--selftest"], binary=E.bin10)[1]
    drop = lambda text: [x for x in text.splitlines() if not x.startswith("#") and x.split(",")[0] not in NOP_KERNELS and
                         not (x.startswith("call,") and x.split(",")[1] in NOP_KERNELS) and not x.startswith("trial,evict: ")]
    check("selftest: without the lines of the three new kernels and of the evict step, the output is the output of the "
          "self-test of the bwx10 source, line for line", len(drop(out10)) > 200 and drop(out) == drop(out10),
          (len(drop(out)), len(drop(out10))))
    out8 = run(["--selftest"], binary=E.bin8)[1]

    def kernel_checks(text, k):
        return sorted(",".join(line.split(",")[1:]) for line in text.splitlines() if line.startswith(k + ","))

    want = kernel_checks(out8, "asmread")
    check("selftest: asmread has 8 checks in the accepted runner (the reference for the next check)",
          len(want) == 8 and all(x.endswith(",pass") for x in want), want)
    for k in NEW_KERNELS + NOP_KERNELS:
        check("selftest: %s gets the 8 checks of a read kernel, all pass" % k, kernel_checks(out, k) == want, kernel_checks(out, k))
    check("selftest: that comparison can fail: a kernel that is not in the output has no check", kernel_checks(out, "read_nop63") != want)
    # the self-test must fail on a broken wrapper: a build that counts one pass too many per clock read
    with open(os.path.join(HERE, "bwx11.c")) as f:
        src = f.read()
    good = "        x->bytes = bytes;\n"
    n = 0
    for fn, own in (("timed_sequence", "trial,every window lasts"), ("timed_sequence_hot", "trial,hot copy: every window lasts")):
        for name, bad in (("a window that counts 256 bytes too many", "        x->bytes = bytes + 256;\n"),
                          ("a window whose end is before its start", "        x->bytes = bytes; t1 = t0 - 1;\n")):
            n += 1
            d = os.path.join(E.tmp, "broken%d" % n)
            os.makedirs(d, exist_ok=True)
            changed = replace_in(src, fn, good, bad)
            with open(os.path.join(d, "bwx11.c"), "w") as f:
                f.write(changed or "")
            shutil.copy(os.path.join(HERE, "bwx11_selftest.c"), d)
            ok = changed is not None and subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx11"), os.path.join(d, "bwx11.c")]).returncode == 0
            rc, out, _ = run(["--selftest"], binary=os.path.join(d, "bwx11"))
            fails = [x for x in out.splitlines() if x.endswith(",FAIL")]
            check("selftest: status 1 for a build with %s in %s, and the failed checks are those of that function" % (name, fn),
                  ok and rc == 1 and any(x.startswith(own) or x.startswith(own.replace("lasts", "holds")) for x in fails) and
                  all(x.startswith("trial,hot ") if fn == "timed_sequence_hot" else not x.startswith("trial,hot copy: ") for x in fails),
                  (rc, fails))
    b = mutant_build(HOT_READ_MUTANT, "hotread")
    rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")
    fails = [x for x in out.splitlines() if x.endswith(",FAIL")]
    check("selftest: status 1 for a build where %s: the touch test sees it on the machine code" % HOT_READ_MUTANT,
          rc == 1 and fails == ["trial,hot touch: timed_sequence_hot does not touch the window record between the first "
                                "and the last pass,0,FAIL"], (rc, fails))


def test_selftest_rows():
    """the row checks of the self-test fail on a build that prints a wrong value"""
    for n, name in enumerate(ROW_MUTANTS):
        b = mutant_build(name, "row%d" % n)
        rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")
        check("selftest: status 1 for a build with " + name, rc == 1 and ",FAIL" in out, rc)


def run_listing(args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_listing11.py")] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return r.returncode, r.stdout


def shift_block(text, binary, kernel, by):
    """adds 'by' to every address of one '=== binary kernel ===' block of a listing"""
    out, inside = [], False
    for line in text.split("\n"):
        if line.startswith("==="):
            inside = line == "=== %s %s ===" % (binary, kernel)
        elif inside:
            line = re.sub(r"^(\s*)([0-9a-f]+)(:| <)", lambda m: "%s%0*x%s" % (m.group(1), len(m.group(2)), int(m.group(2), 16) + by, m.group(3)), line)
            line = re.sub(r"\b([0-9a-f]+) <k_", lambda m: "%x <k_" % (int(m.group(1), 16) + by), line)
        out.append(line)
    return "\n".join(out)


LDP8 = ["ldp\tq0, q1, [x0]", "ldp\tq2, q3, [x0, #32]", "ldp\tq4, q5, [x0, #64]", "ldp\tq6, q7, [x0, #96]",
        "ldp\tq8, q9, [x0, #128]", "ldp\tq10, q11, [x0, #160]", "ldp\tq12, q13, [x0, #192]", "ldp\tq14, q15, [x0, #224]"]
SAVES = ["stp\td8, d9, [sp, #-64]!", "add\tx1, x0, x1, lsl #3", "stp\td10, d11, [sp, #16]", "stp\td12, d13, [sp, #32]",
         "stp\td14, d15, [sp, #48]"]
RESTORES = ["ldp\td10, d11, [sp, #16]", "ldp\td12, d13, [sp, #32]", "ldp\td14, d15, [sp, #48]", "ldp\td8, d9, [sp], #64"]
STEP = ["add\tx0, x0, #0x100", "cmp\tx0, x1"]


def synth(kernel, start, head, body, tail=("ret",), binary="bwx11"):
    """(listing block, offsets row) of a kernel as build11.sh writes them on AArch64: head, loop body, the loop
    branch, tail. The loop start is start + 4 * len(head)."""
    loop = start + 4 * len(head)
    insns = list(head) + list(body) + ["b.cc\t%x <k_%s+0x%x>  // b.lo, b.ul, b.last" % (loop, kernel, loop - start)] + list(tail)
    text = "=== %s %s ===\n%016x <k_%s>:\n" % (binary, kernel, start, kernel)
    text += "".join("    %x:\t%s\n" % (start + 4 * i, x) for i, x in enumerate(insns)) + "\n"
    return text, "%s\t%s\tk_%s\t%x\t%x\t%d\n" % (binary, kernel, kernel, start, loop, loop % 64)


def nop_body(n):
    return LDP8 + ["nop"] * n + STEP


# Starts after the last kernel of the reference (read_1pl ends at 0x4df0), each at 0 modulo 64 as asmread.
NOP_START = {"read_nop64": 0x4e00, "read_nop96": 0x4f80, "read_nop128": 0x5180}
FULL = (SAVES, RESTORES + ["ret"])


def synth_new(change=None, by=0):
    """the 3 new kernels, well formed, at addresses after the last kernel of the reference. change: {kernel: (start,
    head, body, tail)} replaces the parts of single kernels. by: added to every start. Returns (listing text,
    offsets rows)."""
    parts = {k: (NOP_START[k] + by, SAVES, nop_body(NOPS[k]), RESTORES + ["ret"]) for k in NOP_KERNELS}
    parts.update(change or {})
    text = offs = ""
    for k in NOP_KERNELS:
        if parts[k] is not None:
            t, o = synth(k, *parts[k])
            text, offs = text + t, offs + o
    return text, offs


def test_listing_saved():
    """check_listing11.py on the accepted listing of bwx10 (ref-bwx10) plus synthetic new kernels, and on changed copies"""
    with open(os.path.join(REF10, "listing.txt")) as f:
        ref_listing = f.read()
    with open(os.path.join(REF10, "offsets.tsv")) as f:
        ref_offs = f.read()
    old_listing, old_offs = ref_listing.replace("=== %s " % B10, "=== bwx11 "), ref_offs.replace("\n%s\t" % B10, "\nbwx11\t")
    new_text, new_offs = synth_new()
    listing, offs = old_listing + new_text, old_offs + new_offs
    d = os.path.join(E.tmp, "listing")
    os.makedirs(d, exist_ok=True)

    def case(name, want_rc, new_listing, new_offs=offs, want_text=None, extra=None):
        with open(os.path.join(d, "listing.txt"), "w") as f:
            f.write(new_listing)
        with open(os.path.join(d, "offsets.tsv"), "w") as f:
            f.write(new_offs)
        rc, out = run_listing([os.path.join(d, "listing.txt")] + (extra or []))
        check("listing: " + name, rc == want_rc and (want_text is None or want_text in out), "rc=%d %s" % (rc, out[-400:]))
        return out

    out = case("the accepted listing of bwx10 under the name bwx11 plus 3 well-formed new kernels passes (exit 0)", 0, listing)
    check("listing: 26 kernels compared, 26 rows ok; 3 new kernels, 3 rows ok",
          out.count("\tsame\tok") == 26 and out.count("\texpected\tok") == 3 and
          "kernels=26 failed_rows=0 new_kernels=3 new_failed_rows=0" in out, out[-200:])
    check("listing: the synthetic new kernels have their loop at 20 modulo 64, as asmread",
          [r.split("\t")[5] for r in new_offs.splitlines()] == ["20"] * 3 and "bwx11\tasmread\tk_asmread\t42c0\t42d4\t20" in offs)
    check("listing: the synthetic new kernels hold 64, 96 and 128 nop",
          [new_text.split("=== bwx11 %s ===" % k)[1].split("===")[0].count("\tnop\n") for k in NOP_KERNELS] == [64, 96, 128])
    out = case("the accepted listing of bwx10 under its own name, with --binary bwx10 and --skip-new, passes against itself", 0,
               ref_listing, ref_offs, want_text="kernels=26 failed_rows=0 new_kernels=NOT CHECKED", extra=["--binary", "bwx10", "--skip-new"])

    # ---- the checks of part 1 (check_listing8.py), on the 26 kernels of the reference ----
    one = "ldp\tq29, q28, [x0, #32]"
    check("listing: the instruction to change stands once in k_read of bwx11",
          listing.split("=== bwx11 read ===")[1].split("===")[0].count(one) == 1)
    head, rest = listing.split("=== bwx11 read ===")
    case("one changed instruction in k_read fails (exit 1)", 1,
         head + "=== bwx11 read ===" + rest.replace(one, "ldp\tq29, q28, [x0, #48]", 1), want_text="read\t41a0\t41a4\t36\t36\tDIFFERS\tFAIL")
    check("listing: the loop start of k_asmread stands once", listing.count("    42d4:\tldp\tq0, q1, [x0]") == 1)
    case("one added nop before the loop of k_asmread fails", 1,
         listing.replace("    42d4:\tldp\tq0, q1, [x0]", "    42d0:\tnop\n    42d4:\tldp\tq0, q1, [x0]", 1), want_text="asmread")
    shifted = shift_block(listing, "bwx11", "asmread", 4)
    offs_shifted = offs.replace("bwx11\tasmread\tk_asmread\t42c0\t42d4\t20", "bwx11\tasmread\tk_asmread\t42c4\t42d8\t24")
    check("listing: the shifted copy differs from the saved one", shifted != listing and offs_shifted != offs)
    out = case("k_asmread shifted by 4 bytes, same text, fails on the loop offset (exit 1)", 1, shifted, offs_shifted,
               want_text="asmread\t42c4\t42d8\t24\t20\tsame\tFAIL: loop offset modulo 64 is 24, reference 20")
    check("listing: with k_asmread shifted, every new kernel fails too: its loop offset is compared with asmread",
          out.count("loop offset modulo 64 is 20, asmread has 24") == 3, out[-300:])
    case("the same shift with an offsets.tsv that still says 20 fails", 1, shifted, want_text="offsets.tsv gives 20")
    check("listing: the offsets row of k_oldread stands once", offs.count("bwx11\toldread\tk_oldread\t3e00\t3e68\t40") == 1)
    case("an offsets.tsv row that differs from the listing fails", 1, listing,
         offs.replace("bwx11\toldread\tk_oldread\t3e00\t3e68\t40", "bwx11\toldread\tk_oldread\t3e00\t3e68\t0"), want_text="offsets.tsv gives 0")
    whole = listing
    for k in re.findall(r"=== bwx11 (\S+) ===", listing):
        whole = shift_block(whole, "bwx11", k, 0x1040)
    check("listing: the moved copy differs and holds 29 kernels", whole != listing and len(re.findall(r"=== bwx11 (\S+) ===", listing)) == 29)
    case("all kernels moved by a multiple of 64 bytes pass: addresses are not compared", 0, whole)
    block = listing.split("=== bwx11 read_sparse ===")[1].split("===")[0]
    case("a listing without k_read_sparse fails", 1, listing.replace("=== bwx11 read_sparse ===" + block, ""), want_text="no listing or no loop")
    case("a listing with a kernel that the reference lacks and that is not a kernel of round 4 fails", 1,
         listing + "\n=== bwx11 read_new ===\n" + block, want_text="read_new")
    # the kernels of round 3 are part of the reference now: part 1 compares them
    pf_block = listing.split("=== bwx11 read_pf512 ===")[1].split("===")[0]
    case("a listing without k_read_pf512 (a kernel of round 3, now in the reference) fails", 1,
         listing.replace("=== bwx11 read_pf512 ===" + pf_block, ""), want_text="read_pf512\tNA\tNA\tNA\t20\t-\tFAIL: no listing or no loop")
    check("listing: the prfm to change stands once in k_read_pf512", pf_block.count("prfm\tpldl1keep, [x0, #576]") == 1)
    case("one changed prfm offset in k_read_pf512 fails", 1,
         listing.replace("=== bwx11 read_pf512 ===" + pf_block, "=== bwx11 read_pf512 ===" +
                         pf_block.replace("prfm\tpldl1keep, [x0, #576]", "prfm\tpldl1keep, [x0, #584]")),
         want_text="read_pf512\t4c40\t4c54\t20\t20\tDIFFERS\tFAIL")
    pl_block = listing.split("=== bwx11 read_1pl ===")[1].split("===")[0]
    check("listing: the load to change stands once in k_read_1pl", pl_block.count("ldr\tq2, [x0, #128]") == 1)
    case("one changed load offset in k_read_1pl fails", 1,
         listing.replace("=== bwx11 read_1pl ===" + pl_block, "=== bwx11 read_1pl ===" + pl_block.replace("ldr\tq2, [x0, #128]", "ldr\tq2, [x0, #136]")),
         want_text="read_1pl\t4dd0\t4dd4\t20\t20\tDIFFERS\tFAIL")
    got = "ldr\tx3, [x3, #4072]"
    check("listing: the pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got) == 2)
    got0 = "ldr\tx0, [x0, #4072]"
    check("listing: the second pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got0) == 2)
    out = case("another place of the stack-guard pointer in the table of the linker, the same in all four loads, "
               "passes with a note", 0, listing.replace(got, "ldr\tx3, [x3, #4064]").replace(got0, "ldr\tx0, [x0, #4064]"),
               want_text="\tsame\tNOTE: got_offset_differs (4064,4064, reference 4072,4072)")
    check("listing: the two rows with the note do not print a plain ok", out.count("\tsame\tok") == 24, out[-300:])
    adrp, stub = "adrp\tx3, 2f000 <__FRAME_END__+0x1bbf8>", "bl\t2040 <__stack_chk_fail@plt>"
    check("listing: the adrp before that load and the call of the stack-guard failure stand in k_oldread and k_oldread2",
          listing.count(adrp) == 2 and listing.count(stub) == 2)
    case("the first pointer load of k_oldread from another page of the table fails (exit 1)", 1,
         listing.replace(adrp, "adrp\tx3, 2a000 <some_other_table>", 1), want_text="use 2 places of the table")
    case("the first pointer load of k_oldread from another offset fails", 1,
         listing.replace(got, "ldr\tx3, [x3, #8]", 1), want_text="use 2 places of the table")
    case("k_oldread2 with its two pointer loads from another place than k_oldread fails", 1,
         "=== bwx11 oldread2 ===".join([listing.split("=== bwx11 oldread2 ===")[0],
                                        listing.split("=== bwx11 oldread2 ===")[1].replace("[x3, #4072]", "[x3, #16]", 1)
                                        .replace("[x0, #4072]", "[x0, #16]", 1)]),
         want_text="over all kernels")
    case("a call of another function in place of the stack-guard failure fails", 1,
         listing.replace(stub, "bl\t9999 <abort@plt>", 1), want_text="DIFFERS")
    check("listing: the load from the stack to change stands in k_oldread and k_oldread2", listing.count("ldr\tx2, [sp, #136]") == 2)
    case("another offset in a load from the stack fails", 1, listing.replace("ldr\tx2, [sp, #136]", "ldr\tx2, [sp, #128]", 1),
         want_text="DIFFERS")
    case("a listing with no block of bwx11 cannot be used (exit 2)", 2, listing.replace("=== bwx11 ", "=== other "))
    case("a reference that holds a kernel of round 4 cannot be used (exit 2)", 2, listing, want_text="holds a kernel of round 4",
         extra=["--ref-listing", os.path.join(d, "listing.txt"), "--ref-offsets", os.path.join(d, "offsets.tsv"), "--ref-binary", "bwx11"])

    # ---- the 3 new kernels ----
    def new_case(name, change, want_text, want_rc=1):
        t, o = synth_new(change)
        return case(name, want_rc, old_listing + t, old_offs + o, want_text=want_text)

    a64, body64 = NOP_START["read_nop64"], nop_body(64)
    new_case("read_nop64 with 63 nop fails (exit 1)", {"read_nop64": (a64, FULL[0], nop_body(63), FULL[1])},
             "read_nop64\t4e00\t4e14\t20\t20\tDIFFERS\tFAIL: the loop has 63 nop, expected 64")
    new_case("read_nop64 with 65 nop fails", {"read_nop64": (a64, FULL[0], nop_body(65), FULL[1])},
             "read_nop64\t4e00\t4e14\t20\t20\tDIFFERS\tFAIL: the loop has 65 nop, expected 64")
    new_case("read_nop96 with 97 nop fails", {"read_nop96": (NOP_START["read_nop96"], FULL[0], nop_body(97), FULL[1])},
             "read_nop96\t4f80\t4f94\t20\t20\tDIFFERS\tFAIL: the loop has 97 nop, expected 96")
    new_case("read_nop128 with the loop of read_nop96 fails", {"read_nop128": (NOP_START["read_nop128"], FULL[0], nop_body(96), FULL[1])},
             "read_nop128\t5180\t5194\t20\t20\tDIFFERS\tFAIL: the loop has 96 nop, expected 128")
    new_case("read_nop128 without any nop (the loop of asmread) fails", {"read_nop128": (NOP_START["read_nop128"], FULL[0], nop_body(0), FULL[1])},
             "the loop has 0 nop, expected 128")
    new_case("read_nop64 with another instruction in place of one nop fails",
             {"read_nop64": (a64, FULL[0], body64[:40] + ["mov\tx2, x2"] + body64[41:], FULL[1])},
             "loop instruction 40 is 'mov x2, x2', expected 'nop'")
    new_case("read_nop64 with one nop before the 8 ldp (64 nop in all) fails",
             {"read_nop64": (a64, FULL[0], ["nop"] + LDP8 + ["nop"] * 63 + STEP, FULL[1])},
             "read_nop64\t4e00\t4e14\t20\t20\tDIFFERS\tFAIL: loop instruction 0 is 'nop', expected 'ldp q0, q1, [x0]'")
    new_case("read_nop64 with the nop after the add fails",
             {"read_nop64": (a64, FULL[0], LDP8 + STEP[:1] + ["nop"] * 64 + STEP[1:], FULL[1])},
             "loop instruction 8 is 'add x0, x0, #0x100', expected 'nop'")
    new_case("read_nop64 with one wrong ldp offset (40 in place of 32) fails",
             {"read_nop64": (a64, FULL[0], [x.replace("[x0, #32]", "[x0, #40]") for x in body64], FULL[1])},
             "loop instruction 1 is 'ldp q2, q3, [x0, #40]', expected 'ldp q2, q3, [x0, #32]'")
    new_case("read_nop64 with 7 ldp fails", {"read_nop64": (a64 + 4, FULL[0], body64[:7] + body64[8:], FULL[1])},
             "loop instruction 7 is 'nop', expected 'ldp q14, q15, [x0, #224]'")
    new_case("read_nop64 with a step of 128 bytes fails",
             {"read_nop64": (a64, FULL[0], [x.replace("#0x100", "#0x80") for x in body64], FULL[1])},
             "loop instruction 72 is 'add x0, x0, #0x80', expected 'add x0, x0, #0x100'")
    new_case("read_nop64 with the loop moved by 4 bytes (offsets.tsv agrees with the listing) fails on the loop offset",
             {"read_nop64": (a64 + 4, FULL[0], body64, FULL[1])},
             "read_nop64\t4e04\t4e18\t24\t20\texpected\tFAIL: loop offset modulo 64 is 24, asmread has 20; loop offset modulo 64 is 24, planned 20")
    new_case("read_nop96 that starts at 20 modulo 64 (loop at 40) fails on the loop offset",
             {"read_nop96": (NOP_START["read_nop96"] + 20, FULL[0], nop_body(96), FULL[1])},
             "read_nop96\t4f94\t4fa8\t40\t20\texpected\tFAIL: loop offset modulo 64 is 40, asmread has 20")
    t, o = synth_new()
    case("a new kernel whose offsets.tsv row differs from the listing fails", 1, old_listing + t,
         old_offs + o.replace("bwx11\tread_nop128\tk_read_nop128\t5180\t5194\t20", "bwx11\tread_nop128\tk_read_nop128\t5180\t5194\t4"),
         want_text="read_nop128\t5180\t5194\t20\t20\texpected\tFAIL: offsets.tsv gives 4, the listing gives 20")
    # asmread and the new kernels all at 24: the new loops agree with asmread, and still miss the planned 20
    t, o = synth_new(by=4)
    out = case("with k_asmread and the three new kernels all moved by 4 bytes, each new kernel fails on the planned offset 20", 1,
               shift_block(old_listing, "bwx11", "asmread", 4) + t,
               old_offs.replace("bwx11\tasmread\tk_asmread\t42c0\t42d4\t20", "bwx11\tasmread\tk_asmread\t42c4\t42d8\t24") + o,
               want_text="read_nop64\t4e04\t4e18\t24\t24\texpected\tFAIL: loop offset modulo 64 is 24, planned 20")
    check("listing: that run names the planned offset 3 times and never a difference from asmread",
          out.count("loop offset modulo 64 is 24, planned 20") == 3 and "asmread has" not in out, out[-300:])
    new_case("read_nop64 without the store of d14 and d15 fails (the loop uses v14 and v15)",
             {"read_nop64": (a64 + 4, SAVES[:4], body64, FULL[1])}, "not stored before the loop: [14, 15]")
    new_case("read_nop64 without the load of d8 and d9 after the loop fails",
             {"read_nop64": (a64, FULL[0], body64, RESTORES[:3] + ["ret"])}, "not loaded after it: [8, 9]")
    new_case("read_nop64 with a second backward branch fails",
             {"read_nop64": (a64, FULL[0], body64, RESTORES + ["cbnz\tx2, 4e14 <k_read_nop64+0x14>", "ret"])},
             "FAIL: 2 backward branches, 1 expected")
    new_case("read_nop64 with a call after the loop fails",
             {"read_nop64": (a64, FULL[0], body64, RESTORES + ["bl\t2040 <abort@plt>", "ret"])}, "a branch or call beside the loop branch")
    new_case("read_nop64 with another instruction before the loop fails",
             {"read_nop64": (a64 - 4, SAVES + ["ldr\tq4, [x0, #4032]"], body64, FULL[1])},
             "is not the end pointer and not a store of d registers")
    new_case("read_nop64 that does not end with ret fails",
             {"read_nop64": (a64, FULL[0], body64, RESTORES)}, "the function does not end with ret")
    hi = old_listing + synth_new()[0].replace("b.cc\t4e14 <k_read_nop64+0x14>", "b.hi\t4e14 <k_read_nop64+0x14>")
    check("listing: the loop branch to change stands once", synth_new()[0].count("b.cc\t4e14 <k_read_nop64+0x14>") == 1)
    case("read_nop64 with b.hi in place of b.cc as its loop branch fails", 1, hi, want_text="the loop branch is 'b.hi")
    new_case("a listing without read_nop96 fails", {"read_nop96": None}, "read_nop96\tNA\tNA\tNA\t20\t-\tFAIL: no listing")
    out = case("the accepted listing alone (no new kernel) fails: all 3 new kernels are required", 1, old_listing, old_offs)
    check("listing: that run names 3 failed new rows and no failed old row", "failed_rows=0 new_kernels=3 new_failed_rows=3" in out, out[-200:])
    out = case("--skip-new: the same listing passes, and the last line says that the new kernels were not checked", 0,
               old_listing, old_offs, want_text="new_kernels=NOT CHECKED (--skip-new)", extra=["--skip-new"])


def test_build_scripts():
    """build11.sh on this machine, and check_listing11.py on two real listings of one compiler"""
    cpus = ",".join(str(c) for c in E.allowed)
    new, old = os.path.join(E.tmp, "new"), os.path.join(E.tmp, "old")
    os.makedirs(new)
    os.makedirs(old)
    for name in ("bwx11.c", "bwx11_selftest.c", "build11.sh"):
        shutil.copy(os.path.join(HERE, name), new)
    # The reference build of the listing comparison: build11.sh on the bwx10 source (bwx11.c without its marked
    # blocks), stored under the file name that the script compiles. Its listing has 26 kernels under the binary
    # name bwx11. The copy of bwx11_selftest.c is not compiled: the script only takes its digest.
    shutil.copy(os.path.join(E.src10, "bwx10.c"), os.path.join(old, "bwx11.c"))
    shutil.copy(os.path.join(E.src10, "bwx10_selftest.c"), old)
    for name in ("bwx11_selftest.c", "build11.sh"):
        shutil.copy(os.path.join(HERE, name), old)
    marker = os.path.join(E.tmp, "marker")
    open(marker, "w").close()
    env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=marker)
    env.pop("_PINNED", None)
    r = subprocess.run(["bash", os.path.join(new, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check("build11.sh: exit 3 and no file written while the marker file is present",
          r.returncode == 3 and sorted(os.listdir(new)) == ["build11.sh", "bwx11.c", "bwx11_selftest.c"], (r.returncode, os.listdir(new)))
    # The marker file appears while the self-test runs. A script stands for the compiler. The "binary" that it
    # writes creates the marker file in its self-test and leaves a file if it is run in any other way.
    late = os.path.join(E.tmp, "late")
    os.makedirs(late)
    for name in ("bwx11.c", "bwx11_selftest.c", "build11.sh"):
        shutil.copy(os.path.join(HERE, name), late)
    late_marker, ran = os.path.join(E.tmp, "late-marker"), os.path.join(E.tmp, "late-ran")
    cc = os.path.join(E.tmp, "fake-cc")
    with open(cc, "w") as f:
        f.write('#!/bin/sh\n[ "$1" = --version ] && { echo fake; exit 0; }\n'
                'while [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done\n'
                'printf \'#!/bin/sh\\nif [ "$1" = --selftest ]; then : > "%s"; echo "# failures=0"; else : > "%s"; fi\\n\' > "$out"\n'
                'chmod +x "$out"\n' % (late_marker, ran))
    os.chmod(cc, 0o755)
    r = subprocess.run(["bash", os.path.join(late, "build11.sh")], env=dict(env, BWX_MARKER=late_marker, CC=cc),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check("build11.sh: exit 3 and no further run of the binary when the marker file appears during the self-test",
          r.returncode == 3 and os.path.exists(late_marker) and os.path.exists(os.path.join(late, "selftest-bwx11.txt")) and
          not os.path.exists(ran), (r.returncode, os.path.exists(late_marker), os.path.exists(ran), r.stderr[-200:]))
    env["BWX_MARKER"] = marker + ".none"
    r = subprocess.run(["bash", os.path.join(new, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    made = sorted(os.listdir(new))
    check("build11.sh: exit 0; writes bwx11, build.txt, listing.txt, offsets.tsv, selftest-bwx11.txt, seq-listing.txt",
          r.returncode == 0 and made == sorted(["build11.sh", "bwx11.c", "bwx11_selftest.c", "bwx11", "build.txt", "listing.txt",
                                                "offsets.tsv", "selftest-bwx11.txt", "seq-listing.txt"]), (r.returncode, made, r.stderr[-300:]))
    if r.returncode != 0:
        return
    with open(os.path.join(new, "build.txt")) as f:
        build = f.read()
    with open(os.path.join(OLD, "build.sh")) as f:
        old_flags = re.search(r'^CFLAGS="(.*)"$', f.read(), re.M).group(1)
    check("build11.sh: build.txt holds the CFLAGS of build.sh, no compiler message, the self-test result and 7 digests",
          "## CFLAGS=%s\n" % old_flags in build and "## compiler messages:\n## compiler messages end\n" in build and
          "## selftest bwx11 exit=0 # failures=0" in build and len(re.findall(r"^[0-9a-f]{64}  ", build, re.M)) == 7, build[-600:])
    for fn in SEQ_FUNCTIONS:
        t = seq_targets(os.path.join(new, "bwx11"), fn)
        check("build11.sh: build.txt lists the branch targets of %s, as the machine-code rule reads them" % fn,
              "## %s branch targets: %s\n" % (fn, " ".join("%s=%d" % (k, t[k]) for k in sorted(t))) in build and
              not seq_code_problems(t, fn), re.findall(r"^## timed_sequence.*$", build, re.M))
    check("build11.sh: build.txt holds the placement of bwx11, and says that the accepted binary was not found beside it",
          re.search(r"^## placement bwx11 \(start modulo 64\): call=\d+ read_smaps=\d+ tcount=\d+ timed_sequence=\d+ "
                    r"timed_sequence_hot=\d+$", build, re.M) and "## placement against bwx8: not compared (no file " in build,
          re.findall(r"^## placement.*$", build, re.M))
    check("build11.sh: build.txt also says that the accepted binary of bwx10 was not found beside it",
          "## placement against bwx10: not compared (no file " in build and len(re.findall(r"^## placement.*$", build, re.M)) == 3,
          re.findall(r"^## placement.*$", build, re.M))
    with open(os.path.join(new, "seq-listing.txt")) as f:
        seq_text = f.read()
    check("build11.sh: seq-listing.txt holds the machine code of both timed functions",
          re.findall(r"^=== bwx11 (\S+) ===$", seq_text, re.M) == list(SEQ_FUNCTIONS) and
          all("<%s>:" % fn in seq_text for fn in SEQ_FUNCTIONS) and len(seq_text.splitlines()) > 60, seq_text[:200])
    seq = os.path.join(E.tmp, "seq")
    os.makedirs(seq)
    for name in ("bwx11_selftest.c", "build11.sh"):
        shutil.copy(os.path.join(HERE, name), seq)
    with open(os.path.join(seq, "bwx11.c"), "w") as f:
        f.write(mutant_source(SEQ_MUTANTS[1]) or "")
    r6 = subprocess.run(["bash", os.path.join(seq, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True)
    check("build11.sh: exit 6 for a build with " + SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and
          "fflush" in r6.stderr and "timed_sequence of bwx11:" in r6.stderr and "timed_sequence_hot of" not in r6.stderr,
          (r6.returncode, r6.stderr[-300:]))
    seqh = os.path.join(E.tmp, "seqh")
    os.makedirs(seqh)
    for name in ("bwx11_selftest.c", "build11.sh"):
        shutil.copy(os.path.join(HERE, name), seqh)
    with open(os.path.join(seqh, "bwx11.c"), "w") as f:
        f.write(mutant_source(HOT_SEQ_MUTANTS[1]) or "")
    r6 = subprocess.run(["bash", os.path.join(seqh, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True)
    check("build11.sh: exit 6 for a build with " + HOT_SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and
          "fflush" in r6.stderr and "timed_sequence_hot of bwx11:" in r6.stderr and "timed_sequence of" not in r6.stderr,
          (r6.returncode, r6.stderr[-300:]))
    with open(os.path.join(new, "offsets.tsv")) as f:
        rows = [line.split("\t") for line in f.read().splitlines()[1:]]
    check("build11.sh: offsets.tsv has one row per kernel of binary bwx11, each with a loop",
          len(rows) == 29 and [r[1] for r in rows[21:26]] == NEW_KERNELS and [r[1] for r in rows[26:]] == NOP_KERNELS and
          all(r[0] == "bwx11" and r[5].isdigit() for r in rows), rows[:3])
    r = subprocess.run(["bash", os.path.join(old, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(os.path.join(old, "offsets.tsv")) as f:
        ref_rows = [line.split("\t") for line in f.read().splitlines()[1:]]
    if not check("build11.sh on the bwx10 source runs in a temporary copy and lists 26 kernels (the reference for the next check)",
                 r.returncode == 0 and len(ref_rows) == 26 and [x[1] for x in ref_rows] == [x[1] for x in rows[:26]], r.stderr[-300:]):
        return
    ref = ["--ref-listing", os.path.join(old, "listing.txt"), "--ref-offsets", os.path.join(old, "offsets.tsv"),
           "--ref-binary", "bwx11"]
    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref + ["--skip-new"])
    check("listing: on this machine the 26 kernels of bwx10 in bwx11 equal the kernels of a build of the bwx10 source, text and "
          "loop offset (--skip-new: the new kernels are stand-in loops here)",
          rc == 0 and out.count("\tsame\tok") == 26 and "new_kernels=NOT CHECKED" in out, out[-400:])
    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref)
    check("listing: without --skip-new the stand-in loops of the new kernels are rejected (exit 1), and the 26 old rows stay ok",
          rc == 1 and out.count("\tsame\tok") == 26 and "failed_rows=0 new_kernels=3 new_failed_rows=3" in out, out[-400:])
    # a bwx11 build whose kernel was moved must be rejected
    moved = os.path.join(E.tmp, "moved")
    os.makedirs(moved)
    for name in ("bwx11.c", "bwx11_selftest.c", "build11.sh"):
        shutil.copy(os.path.join(HERE, name), moved)
    with open(os.path.join(moved, "bwx11.c")) as f:
        src = f.read()
    with open(os.path.join(moved, "bwx11.c"), "w") as f:
        f.write(src.replace("#define PAD_asmread 0\n", "#define PAD_asmread 16\n"))
    r = subprocess.run(["bash", os.path.join(moved, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # the placement record against the accepted binary: a copy with the local pad, and a copy with another pad
    if getattr(E, "call8", None) is None:
        check("build11.sh: placement record against the accepted binary (NOT RUN: the placement check of the source test failed)", False)
    elif getattr(E, "bin10_placed", None) is None or not os.path.exists(E.bin10_placed):
        check("build11.sh: placement record against bwx10 (NOT RUN: the bwx10 source did not build with the local pad)", False)
    else:
        for tag, pad in (("local", E.call8), ("other", (E.call8 + 4) % 64)):
            d = os.path.join(E.tmp, "placed-" + tag)
            os.makedirs(d)
            for name in ("bwx11_selftest.c", "build11.sh"):
                shutil.copy(os.path.join(HERE, name), d)
            with open(os.path.join(d, "bwx11.c"), "w") as f:
                f.write(src.replace("#define PAD_after_kernels 24\n", "#define PAD_after_kernels %d\n" % pad))
            rp = subprocess.run(["bash", os.path.join(d, "build11.sh")], env=dict(env, BWX8_BIN=E.bin8, BWX10_BIN=E.bin10_placed),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            lines = []
            if os.path.exists(os.path.join(d, "build.txt")):
                with open(os.path.join(d, "build.txt")) as f:
                    lines = re.findall(r"^## placement.*$", f.read(), re.M)
            want = "same" if tag == "local" else "DIFFERS"
            check("build11.sh: with the accepted binary given and the %s pad, build.txt holds both placements and the word %s" % (tag, want),
                  rp.returncode == 0 and len(lines) == 5 and lines[0].startswith("## placement bwx11 (start modulo 64): call=%d " % pad) and
                  lines[1].startswith("## placement bwx8 (start modulo 64): call=%d " % E.call8) and
                  lines[2] == "## placement up to timed_sequence against bwx8: " + want, (rp.returncode, lines))
            check("build11.sh: with a bwx10 binary given and the %s pad, build.txt holds its placement and the word %s" % (tag, want),
                  len(lines) == 5 and lines[3].startswith("## placement bwx10 (start modulo 64): call=%d " % E.call8) and
                  "timed_sequence_hot=" in lines[3] and
                  lines[4] == "## placement up to timed_sequence_hot against bwx10: " + want, lines)
    rc, out = run_listing([os.path.join(moved, "listing.txt")] + ref + ["--skip-new"])
    check("listing: a real bwx11 build with k_asmread moved by 16 bytes is rejected (exit 1)",
          r.returncode == 0 and rc == 1 and "loop offset modulo 64" in out, (r.returncode, rc, out[-300:]))


def structure(out, drop_m=()):
    """The rows of a run without what differs between two runs of one plan: times, byte counts, counter values
    and addresses. Comment lines byte for byte. M rows with their values, apart from the addresses and an evict_ns
    above 0. S rows whole.
    W rows: trial, phase, widx, kernel, pass_bytes. P rows: trial, when, kB_total. E rows: trial, field count,
    sink_ok, count_state. B rows: one entry per window that has bins. Other rows: type and field count."""
    s = []
    for line in out.splitlines():
        f = line.split(",")
        if line.startswith("#"):
            item = line
        elif f[0] == "M":
            if f[1] in drop_m:
                continue
            item = ("M", f[1], None if f[1] in ADDR_KEYS or (f[1] == "evict_ns" and f[2] != "0") else ",".join(f[2:]))
        elif f[0] == "S":
            item = tuple(f)
        elif f[0] == "W":
            item = tuple(f[:6]) + (len(f),)
        elif f[0] == "P":
            item = tuple(f[:4]) + (len(f),)
        elif f[0] == "E":
            item = ("E", f[1], len(f), f[8], f[9])
        elif f[0] == "B":
            item = ("B", f[1], f[2], len(f))
            if s and s[-1] == item:
                continue
        elif f[0] == "K":
            item = ("K", f[1], len(f))
        else:
            item = (f[0], len(f))
        s.append(item)
    return s


def m_of(out):
    return {f[1]: f[2] for f in rows_of(out).get("M", [])}


def accounting_problems(plan, out):
    """the W, E and B rules of test_rows on every trial of a run"""
    rows, p = rows_of(out), []
    for i, f in enumerate(plan_lines(plan)):
        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)
        if len(e) != 1:
            p.append("trial %d: %d E rows" % (i, len(e)))
            continue
        p += ["trial %d: %s" % (i, x) for x in window_problems(f, w) + e_problems(f, w, e[0]) + bin_problems(f, w, of_trial(rows, "B", i))]
    return p


def test_new_kernels():
    """(k) the five kernels of round 3 in --list, in the plan parser, in the trial mode and in the interval mode"""
    rc, out, _ = run(["--list"])
    rc8, out8, _ = run(["--list"], binary=E.bin8)
    names = out.split()
    check("k: --list prints 29 kernels: the 21 of the accepted runner in their order, then the 5 of round 3, then the 3 new ones",
          rc == 0 and rc8 == 0 and len(names) == 29 and names[:21] == out8.split() and names[21:26] == NEW_KERNELS and
          names[26:] == NOP_KERNELS and names[:26] == run(["--list"], binary=E.bin10)[1].split(), names[20:])
    lines = ["0 A 1 read_pf256@8M:8 read_pf512@8M:40 read_pf1024@1M:8 read_pf2048@8M 2 10 closed 0",
             "1 B 1 - read_1pl@8M:40 read_1pl@1M:8 read_1pl@8M 2 10 closed 1",
             "2 C 1 - oldread@8M:8 - read_pf256@32K 3 10 closed 0",
             "3 D 1 read_1pl@8M:8 - - read_pf512@1M 2 10 closed 0"]
    plan = write_plan("newk", lines)
    for extra in ([], ["--hot-copy"]):
        rc, out, err = trial(plan, extra)
        tag = "with --hot-copy" if extra else "plain"
        if not check("k: a plan that uses every new kernel as previous activity, prefix, predecessor or target runs with "
                     "status 0 (%s)" % tag, rc == 0, err):
            continue
        rows = rows_of(out)
        k = {f[1]: f for f in rows.get("K", [])}
        check("k: one K row per new kernel of the plan, with the address modulo 64 (%s)" % tag,
              sorted(k) == sorted(NEW_KERNELS + ["oldread"]) and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)
        p = accounting_problems(plan, out)
        check("k: W, E and B rows of the new kernels: whole passes, 8 MiB rule, durations, gaps, bins (%s)" % tag, not p, p)
        check("k: the W rows name the kernel of the plan in every window (%s)" % tag,
              [w[4] for w in rows["W"]] == [e[2] for f in plan_lines(plan) for e in expected_windows(f)])
        check("k: sink_ok is 1 only for the trial that ran old read, and no X row (%s)" % tag,
              [f[8] for f in rows["E"]] == ["NA", "NA", "1", "NA"] and not rows.get("X"), rows.get("X"))
    for bad_name in ("read_pf128", "read_pf", "read_1pl2", "READ_PF256"):
        rc, out, err = trial(write_plan("badk", ["0 a 1 - - - %s@8M 1 5 closed 0" % bad_name]))
        check("k: status 2 and no row for the unknown kernel %s" % bad_name, rc == 2 and out == "" and "unknown kernel" in err, (rc, err[:100]))
    rc, out, err = run(["--seq", "read_pf512,read_1pl@1M,asmread", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])
    r = rows_of(out)
    check("k: the interval mode (--seq) runs the new kernels",
          rc == 0 and [f[3] for f in r.get("I", [])] == ["read_pf512", "read_1pl", "asmread"], (rc, err[:200]))


def test_rec_pad():
    """(l) --rec-pad: the layout with 0, the move of the window records, bad values"""
    plan = write_plan("pad", ALL)
    outs = {}
    for key, extra, binary in (("accepted", [], E.bin8), ("none", [], None), (0, ["--rec-pad", "0"], None),
                               (80, ["--rec-pad", "80"], None), (4000, ["--rec-pad", "4000"], None),
                               (65536, ["--rec-pad", "65536"], None)):
        rc, out, err = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan] + extra, binary=binary)
        check("l: the plan with all phases runs with status 0 (%s)" % (key if binary or key == "none" else "--rec-pad %s" % key),
              rc == 0 and len(rows_of(out).get("E", [])) == 4, (rc, err[:200]))
        outs[key] = out
    m = {k: m_of(v) for k, v in outs.items()}
    check("l: --rec-pad 0 prints the rows of a run without the option: comment lines, every M value but the addresses, "
          "and the S, K, P, W, B, E structure", structure(outs[0]) == structure(outs["none"]),
          [x for x in zip(structure(outs[0]), structure(outs["none"])) if x[0] != x[1]][:3])
    check("l: that comparison can fail: --rec-pad 80 gives another structure", structure(outs[80]) != structure(outs["none"]))
    check("l: bwx11 without the option prints the rows of the accepted runner plus the 8 M rows of round 3 and the 2 of "
          "round 4: comment lines, M values (rec_bytes among them), S, K, P, W, B, E structure",
          structure(outs["none"], drop_m=NEW_M + NEW_M11) == structure(outs["accepted"]) and "rec_bytes" in m["accepted"],
          [x for x in zip(structure(outs["none"], drop_m=NEW_M + NEW_M11), structure(outs["accepted"])) if x[0] != x[1]][:3])
    check("l: that comparison can fail: with --rec-pad 80 the M row rec_bytes differs from the accepted runner",
          structure(outs[80], drop_m=NEW_M + NEW_M11) != structure(outs["accepted"]))
    keys = [f[1] for f in rows_of(outs["none"])["M"]]
    check("l: the 8 M rows of round 3 stand together, in the documented order, directly after M,trace",
          keys[keys.index("trace") + 1:keys.index("trace") + 9] == NEW_M and all(keys.count(k) == 1 for k in NEW_M), keys)
    check("l: M,rec_pad holds the option value and is 0 without the option",
          [m[k].get("rec_pad") for k in ("none", 0, 80, 4000, 65536)] == ["0", "0", "80", "4000", "65536"])
    check("l: M,hot_copy is 0 and M,win_size is 80 (the size of one window record) in every run",
          all(m[k].get("hot_copy") == "0" and m[k].get("win_size") == "80" for k in ("none", 0, 80, 4000, 65536)), m["none"])
    hexa = re.compile(r"[0-9a-f]+")
    check("l: the five address rows hold hex numbers above 0",
          all(hexa.fullmatch(m[k].get(a, "")) and int(m[k][a], 16) > 0 for k in ("none", 0, 80, 4000, 65536) for a in ADDR_KEYS), m["none"])
    a = {k: {x: int(m[k][x], 16) for x in ADDR_KEYS} for k in ("none", 0, 80, 4000, 65536)}
    check("l: buf_addr is a multiple of 2 MiB, and the five addresses differ from each other",
          all(a[k]["buf_addr"] % (2 << 20) == 0 and len(set(a[k].values())) == 5 for k in a), a["none"])
    base = a[0]["win_addr"] - a[0]["rec_addr"]
    check("l: without a pad win[0] stands after the 4 trial records of the plan: win_addr - rec_addr is a multiple of 4 above 0, "
          "the same without the option and with --rec-pad 0", base > 0 and base % 4 == 0 and a["none"]["win_addr"] - a["none"]["rec_addr"] == base, base)
    for pad in (80, 4000, 65536):
        check("l: --rec-pad %d: win_addr - rec_addr grows by exactly %d bytes, and rec_bytes grows by exactly %d bytes" % (pad, pad, pad),
              a[pad]["win_addr"] - a[pad]["rec_addr"] - base == pad and int(m[pad]["rec_bytes"]) - int(m[0]["rec_bytes"]) == pad,
              (a[pad]["win_addr"] - a[pad]["rec_addr"] - base, m[pad]["rec_bytes"], m[0]["rec_bytes"]))
        p = accounting_problems(plan, outs[pad])
        check("l: --rec-pad %d: W, E and B rows keep the rules (whole passes, durations, gaps, bins)" % pad, not p, p)
    # The absolute address. The record block is the first block that the worker thread takes from malloc. glibc
    # gives a thread its own heap, which starts at a multiple of 64 MiB. So the address of the block modulo 64 MiB
    # is the same in every process (below the size from which malloc maps a block on its own, 128 KiB by default).
    big = write_plan("padbig", ["0 a 1 - - - asmread@8M 120 2 closed 0"])
    abs_addr = {}
    for pad in (0, 80, 4000):
        rc, out, err = trial(big, ["--rec-pad", str(pad)])
        abs_addr[pad] = int(m_of(out).get("win_addr", "0"), 16) if rc == 0 else None
    low = {k: None if v is None else v % (64 << 20) for k, v in abs_addr.items()}
    for pad in (80, 4000):
        check("l: a plan of 120 windows: win_addr modulo 64 MiB moves up by exactly %d bytes with --rec-pad %d (three processes "
              "with address randomization; this relies on the thread heap of glibc)" % (pad, pad),
              None not in low.values() and low[pad] - low[0] == pad, low)
    b = mutant_build(PAD_MUTANT, "pad")
    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--rec-pad", "80"], binary=b) if b else (1, "", "")
    mm = m_of(out)
    check("l: the move check fails on a build with " + PAD_MUTANT,
          rc == 0 and int(mm["win_addr"], 16) - int(mm["rec_addr"], 16) == base, (rc, mm.get("win_addr")))
    r = subprocess.run(["setarch", os.uname().machine, "-R", "true"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        check("l: absolute win_addr without address randomization (setarch -R does not work here: NOT RUN)", False, r.stderr)
    else:
        fixed = {}
        for pad in (0, 80, 4000):
            # tw_addr lies on the stack of the main thread, below the argument and environment text. "0", "80" and
            # "4000" differ in length, which can move it by 16 or more bytes. The variable TEST_FILL makes the
            # text of the three runs equally long. (test_runner10.py has no such fill: there the check depends
            # on the size of the environment of the caller.)
            r = subprocess.run(["setarch", os.uname().machine, "-R", E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M",
                                "--plan", big, "--rec-pad", str(pad)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=120, env=dict(os.environ, TEST_FILL="x" * (4 - len(str(pad)))))
            fixed[pad] = {k: int(v, 16) for k, v in m_of(r.stdout).items() if k in ADDR_KEYS}
        check("l: without address randomization (setarch -R) the absolute win_addr moves by exactly 80 and 4000 bytes, and "
              "rec_addr, buf_addr, stack_addr and tw_addr do not move",
              all(len(fixed[p]) == 5 for p in fixed) and
              all(fixed[p]["win_addr"] - fixed[0]["win_addr"] == p for p in (80, 4000)) and
              all(fixed[p][k] == fixed[0][k] for p in (80, 4000) for k in ADDR_KEYS if k != "win_addr"), fixed)

    good = write_plan("good", [GOOD])
    base_args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good]
    for name, value in (("a negative value", "-8"), ("a value above 65536", "65544"), ("65537", "65537"), ("a word", "abc"),
                        ("a number with a letter after it", "80x"), ("a fraction", "80.5"), ("an empty value", ""),
                        ("a value that is not a multiple of 8", "12"), ("a hex number", "0x50")):
        rc, out, err = run(base_args + ["--rec-pad", value])
        check("l: status 2, no row and a message for --rec-pad with " + name, rc == 2 and out == "" and "--rec-pad" in err,
              "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))
    rc, out, err = run(base_args + ["--rec-pad"])
    check("l: status 2 and no row for --rec-pad without a value", rc == 2 and out == "" and err.strip() != "", rc)
    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--rec-pad", "80"])
    check("l: status 2 and no row for --rec-pad outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)
    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--hot-copy"])
    check("l: status 2 and no row for --hot-copy outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)
    rc, out, err = run(base_args + ["--rec-pad", "0"])
    check("l: the control: the same command with --rec-pad 0 runs with status 0", rc == 0 and "\nE,0," in out, rc)


TRACE_PLAN = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",
              "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",
              "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",
              "3 D 1 - - - read@8M 2 20 read 0",
              "4 E 1 - - - oldread@8M 2 20 closed 0"]


def trace_run_problems(plan, out):
    """the trace rule, the bin rule on the clock reads of the trace, and the page-fault line, for every trial"""
    rows, p = rows_of(out), []
    for i, f in enumerate(plan_lines(plan)):
        ev, numbered = events_of(rows, i)
        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)
        if not numbered or not ev or len(e) != 1:
            p.append("trial %d: TR rows or E row missing" % i)
            continue
        p += ["trial %d: %s" % (i, x) for x in trace_problems(f, ev, w, e[0])]
        p += ["trial %d: %s" % (i, x) for x in bin_problems(f, w, of_trial(rows, "B", i), {t for n, t in ev if n == "clock"})]
    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)
    if faults != [(str(i), "0") for i in range(len(plan_lines(plan)))]:
        p.append("minor page faults in a timed sequence: %s" % faults)
    return p


def test_hot_copy():
    """(m) --hot-copy: the rows, the byte accounting, the trace rules"""
    plan = write_plan("hot", ALL)
    rc0, out0, _ = trial(plan)
    rc, out, err = trial(plan, ["--hot-copy"])
    if not check("m: the plan with all phases runs with status 0 with and without --hot-copy", rc == 0 and rc0 == 0, err):
        return
    check("m: M,hot_copy is 1 with the option and 0 without it", (m_of(out).get("hot_copy"), m_of(out0).get("hot_copy")) == ("1", "0"))
    check("m: --hot-copy prints the rows of a plain run: comment lines, every M value but hot_copy and the addresses, "
          "and the S, K, P, W, B, E structure",
          structure(out, drop_m=["hot_copy"]) == structure(out0, drop_m=["hot_copy"]),
          [x for x in zip(structure(out), structure(out0)) if x[0] != x[1]][:3])
    check("m: that comparison can fail: another plan gives another structure",
          structure(out, drop_m=["hot_copy"]) != structure(trial(write_plan("hot2", ALL[:3]))[1], drop_m=["hot_copy"]))
    p = accounting_problems(plan, out)
    check("m: --hot-copy: byte accounting of every window: whole passes, the 8 MiB rule, durations, monotonic times, "
          "wall_ns and gaps from the W rows, bins that sum to the window bytes", not p, p)
    rows = rows_of(out)
    check("m: --hot-copy: sink_ok is 1 for the trials that ran old read, and no X row",
          [f[8] for f in rows["E"]] == ["1", "NA", "NA", "1"] and not rows.get("X"), rows.get("X"))
    check("m: --hot-copy: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",
          min(int(rows["E"][0][6]), int(rows["E"][3][6])) < 20000, (rows["E"][0][6], rows["E"][3][6]))
    rc, out, err = trial(plan, ["--hot-copy", "--rec-pad", "4000"])
    p = accounting_problems(plan, out) if rc == 0 else ["rc=%s" % rc]
    mm = m_of(out)
    check("m: --hot-copy together with --rec-pad 4000 runs, both M rows are set, and the byte accounting holds",
          not p and (mm.get("hot_copy"), mm.get("rec_pad")) == ("1", "4000"), p)

    tplan = write_plan("hottrace", TRACE_PLAN)
    counted = ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"]
    rc, out, err = trial(tplan, counted + ["--hot-copy"])
    if not check("m: the trace run with --hot-copy ends with status 0", rc == 0, err):
        return
    rows = rows_of(out)
    states = [f[9] for f in rows["E"]]
    check("m: trace with --hot-copy: the count states are closed, read, open, read, closed", states == ["closed", "read", "open", "read", "closed"], states)
    p = trace_run_problems(tplan, out)
    check("m: trace with --hot-copy: no forbidden event in any timed sequence, the W rows, gap_ns and the bin ends are clock "
          "reads of the trace, and no minor page fault", not p, p)
    reads = [[n for n, _ in events_of(rows, i)[0]].count("count_read") for i in range(5)]
    check("m: trace with --hot-copy: nwin + 1 counter reads in the trials with count read, none in the others",
          reads == [0, 4, 0, 3, 0], reads)
    names = lambda o: [[n for n, _ in events_of(rows_of(o), i)[0]] for i in range(5)]
    plain = trial(tplan, counted)[1]

    def no_clock_runs(seqs):
        # the number of clock reads inside a window depends on the speed of the run; the order of the other events does not
        return [[n for j, n in enumerate(s) if n != "clock" or j == 0 or s[j - 1] != "clock"] for s in seqs]

    check("m: trace with --hot-copy: the events of every trial stand in the order of the plain run (runs of clock reads "
          "counted once)", no_clock_runs(names(out)) == no_clock_runs(names(plain)) and len(names(out)[0]) > 20)
    # --hot-copy must select timed_sequence_hot(): a defect in that function shows only with the option, and a
    # defect in timed_sequence() only without it. The defect is a warm-up pass before the first target window.
    # The trace does not log it (it does not go through tcall), but the gap before the target then holds one
    # pass over 8 MiB, which takes more than 20 us with the stand-in kernels.
    def gap_ok(o):
        e = rows_of(o).get("E", [])
        return len(e) == 4 and min(int(e[0][6]), int(e[3][6])) < 20000

    for name, tag, fails_with in ((HOT_SEQ_MUTANTS[0], "hotwarm", True), (SEQ_MUTANTS[0], "warm", False)):
        b = mutant_build(name, tag)
        got = {}
        for hot in (False, True):
            o = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan] + (["--hot-copy"] if hot else []), binary=b) if b else (1, "", "")
            got[hot] = o[0] == 0 and gap_ok(o[1])
        check("m: a build with %s: the gap rule fails %s --hot-copy and passes %s it" %
              (name, "with" if fails_with else "without", "without" if fails_with else "with"),
              b is not None and not got[fails_with] and got[not fails_with], got)
    b = mutant_build(HOT_OFF_MUTANT, "hotoff")
    o = run(["--selftest"], binary=b) if b else (None, "", "")
    check("m: a build with %s fails the self-test only in the touch check of timed_sequence_hot" % HOT_OFF_MUTANT,
          o[0] == 1 and [x for x in o[1].splitlines() if x.endswith(",FAIL")] ==
          ["trial,hot touch: timed_sequence_hot does not touch the window record between the first and the last pass,0,FAIL"],
          (o[0], [x for x in o[1].splitlines() if x.endswith(",FAIL")]))


def test_nop_kernels():
    """(n) the three kernels of round 4 in the plan parser, in the trial mode and in the interval mode"""
    lines = ["0 A 1 read_nop64@8M:8 read_nop96@8M:40 read_nop128@1M:8 read_nop64@8M 2 10 closed 0",
             "1 B 1 - read_nop128@8M:40 read_nop64@1M:8 read_nop96@8M 2 10 closed 1",
             "2 C 1 - oldread@8M:8 - read_nop128@32K 3 10 closed 0",
             "3 D 1 read_nop96@8M:8 - - read_nop128@1M 2 10 closed 0"]
    plan = write_plan("nopk", lines)
    for extra in ([], ["--hot-copy"], ["--evict-mb", "8"]):
        rc, out, err = trial(plan, extra)
        tag = "with " + " ".join(extra) if extra else "plain"
        if not check("n: a plan that uses every nop kernel as previous activity, prefix, predecessor and target runs with "
                     "status 0 (%s)" % tag, rc == 0, err):
            continue
        rows = rows_of(out)
        k = {f[1]: f for f in rows.get("K", [])}
        check("n: one K row per nop kernel of the plan, with the address modulo 64 (%s)" % tag,
              sorted(k) == sorted(NOP_KERNELS + ["oldread"]) and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)
        p = accounting_problems(plan, out)
        check("n: W, E and B rows of the nop kernels: whole passes, 8 MiB rule, durations, gaps, bins (%s)" % tag, not p, p)
        check("n: the W rows name the kernel of the plan in every window (%s)" % tag,
              [w[4] for w in rows["W"]] == [e[2] for f in plan_lines(plan) for e in expected_windows(f)])
        check("n: sink_ok is 1 only for the trial that ran old read, and no X row (%s)" % tag,
              [f[8] for f in rows["E"]] == ["NA", "NA", "1", "NA"] and not rows.get("X"), rows.get("X"))
    for bad_name in ("read_nop63", "read_nop", "read_nop256", "READ_NOP64", "read_nop64x"):
        rc, out, err = trial(write_plan("badn", ["0 a 1 - - - %s@8M 1 5 closed 0" % bad_name]))
        check("n: status 2 and no row for the unknown kernel %s" % bad_name, rc == 2 and out == "" and "unknown kernel" in err, (rc, err[:100]))
    rc, out, err = run(["--seq", "read_nop64,read_nop96@1M,read_nop128", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])
    r = rows_of(out)
    check("n: the interval mode (--seq) runs the nop kernels",
          rc == 0 and [f[3] for f in r.get("I", [])] == NOP_KERNELS, (rc, err[:200]))
    rc, out, err = run(["--seq", "read_nop63", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])
    check("n: the interval mode gives status 2 for the unknown kernel read_nop63", rc == 2 and "I," not in out, (rc, err[:100]))


def evict_problems(rows, want_mb, traced):
    """The rows of the evict step. M,evict_mb holds the option value. M,evict_ns is 0 without a step and above 0
    with one. With --trace and a step: the two rows TR,-1 hold its start and its end, their difference is
    evict_ns, and the step lies outside every timed sequence: it ends before the first window of the first trial,
    it overlaps no trial (first window start to last window end), and no clock read of a trial lies inside it."""
    p = []
    m = {f[1]: f[2] for f in rows.get("M", [])}
    if m.get("evict_mb") != str(want_mb):
        p.append("M,evict_mb is %s, expected %d" % (m.get("evict_mb"), want_mb))
    ns = m.get("evict_ns", "")
    if not ns.isdigit():
        return p + ["M,evict_ns is '%s'" % ns]
    if (int(ns) > 0) != (want_mb > 0):
        p.append("M,evict_ns is %s with %d MiB" % (ns, want_mb))
    tr = [f for f in rows.get("TR", []) if f[1] == "-1"]
    if not (traced and want_mb > 0):
        return p + (["TR rows of the evict step without --trace or without a step"] if tr else [])
    if [f[2:4] for f in tr] != [["0", "evict_start"], ["1", "evict_end"]]:
        return p + ["the TR rows of the evict step are %s" % tr]
    t0, t1 = int(tr[0][4]), int(tr[1][4])
    if t0 <= 0 or t1 <= t0 or t1 - t0 != int(ns):
        p.append("evict_start %d, evict_end %d, evict_ns %s" % (t0, t1, ns))
    w = rows.get("W", [])
    if not w:
        return p + ["no W row"]
    if t1 > min(int(f[7]) for f in w):
        p.append("the evict step ends at %d ns, after the start of the first window (%d ns)" % (t1, min(int(f[7]) for f in w)))
    for i in sorted({int(f[1]) for f in w}):
        a, b = min(int(f[7]) for f in w if f[1] == str(i)), max(int(f[8]) for f in w if f[1] == str(i))
        if t0 <= b and t1 >= a:
            p.append("the evict step (%d to %d ns) overlaps the timed sequence of trial %d (%d to %d ns)" % (t0, t1, i, a, b))
    inside = [f for f in rows.get("TR", []) if f[1] != "-1" and f[3] == "clock" and t0 <= int(f[4]) <= t1]
    if inside:
        p.append("%d clock reads of a trial lie inside the evict step" % len(inside))
    return p


def run_maxrss(args, binary=None):
    """(exit status, stdout, peak resident set size in kB) of one run"""
    path = os.path.join(E.tmp, "rss.out")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}
    with open(path, "w") as f:
        proc = subprocess.Popen([binary or E.bin] + args, stdout=f, stderr=subprocess.DEVNULL, env=env)
        _, status, ru = os.wait4(proc.pid, 0)
    proc.returncode = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
    with open(path) as f:
        return proc.returncode, f.read(), ru.ru_maxrss


def test_evict():
    """(o) --evict-mb: the rows with 0, the step with a value above 0, the place of the step, bad values"""
    plan = write_plan("evict", ALL)
    base_args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan]
    outs = {}
    for key, extra, binary in (("bwx10", [], E.bin10), ("none", [], None), (0, ["--evict-mb", "0"], None),
                               (8, ["--evict-mb", "8"], None), (64, ["--evict-mb", "64"], None)):
        rc, out, err = run(base_args + extra, binary=binary)
        check("o: the plan with all phases runs with status 0 (%s)" % (key if binary or key == "none" else "--evict-mb %s" % key),
              rc == 0 and len(rows_of(out).get("E", [])) == 4, (rc, err[:200]))
        outs[key] = out
    m = {k: m_of(v) for k, v in outs.items()}
    check("o: --evict-mb 0 prints the rows of a run without the option: comment lines, every M value but the addresses, "
          "and the S, K, P, W, B, E structure", structure(outs[0]) == structure(outs["none"]),
          [x for x in zip(structure(outs[0]), structure(outs["none"])) if x[0] != x[1]][:3])
    check("o: that comparison can fail: --evict-mb 8 gives another structure", structure(outs[8]) != structure(outs["none"]))
    check("o: --evict-mb 8 differs from a run without the option only in the two M rows evict_mb and evict_ns",
          structure(outs[8], drop_m=NEW_M11) == structure(outs["none"], drop_m=NEW_M11),
          [x for x in zip(structure(outs[8], drop_m=NEW_M11), structure(outs["none"], drop_m=NEW_M11)) if x[0] != x[1]][:3])
    check("o: bwx11 without the option prints the rows of the bwx10 source plus the 2 new M rows: comment lines, M values, "
          "S, K, P, W, B, E structure",
          structure(outs["none"], drop_m=NEW_M11) == structure(outs["bwx10"]) and "tw_addr" in m["bwx10"] and "evict_mb" not in m["bwx10"],
          [x for x in zip(structure(outs["none"], drop_m=NEW_M11), structure(outs["bwx10"])) if x[0] != x[1]][:3])
    check("o: that comparison can fail: without leaving out the 2 new M rows the structures differ",
          structure(outs["none"]) != structure(outs["bwx10"]))
    keys = [f[1] for f in rows_of(outs["none"])["M"]]
    check("o: the 2 new M rows stand together, evict_mb first, directly after M,tw_addr (the last M row of round 3)",
          keys[keys.index("tw_addr") + 1:keys.index("tw_addr") + 3] == NEW_M11 and all(keys.count(k) == 1 for k in NEW_M11), keys)
    check("o: M,evict_mb holds the option value and is 0 without the option",
          [m[k].get("evict_mb") for k in ("none", 0, 8, 64)] == ["0", "0", "8", "64"], [m[k].get("evict_mb") for k in ("none", 0, 8, 64)])
    check("o: M,evict_ns is 0 without the option and with --evict-mb 0",
          m["none"].get("evict_ns") == "0" and m[0].get("evict_ns") == "0", (m["none"].get("evict_ns"), m[0].get("evict_ns")))
    check("o: M,evict_ns is a whole number above 0 with --evict-mb 8 and --evict-mb 64, and the larger step takes longer",
          all(m[k].get("evict_ns", "").isdigit() for k in (8, 64)) and 0 < int(m[8]["evict_ns"]) < int(m[64]["evict_ns"]),
          (m[8].get("evict_ns"), m[64].get("evict_ns")))
    for key in ("none", 0, 8, 64):
        p = evict_problems(rows_of(outs[key]), 0 if key == "none" else key, False)
        check("o: the rule of the evict rows passes (%s)" % (key if key == "none" else "--evict-mb %s" % key), not p, p)
    for mb in (8, 64):
        p = accounting_problems(plan, outs[mb])
        check("o: --evict-mb %d: the windows still account bytes correctly: whole passes, the 8 MiB rule, durations, monotonic "
              "times, wall_ns and gaps from the W rows, bins that sum to the window bytes" % mb, not p, p)
        rows = rows_of(outs[mb])
        check("o: --evict-mb %d: sink_ok is 1 for the trials that ran old read (the buffer still holds its values), no X row, "
              "no TR row" % mb, [f[8] for f in rows["E"]] == ["1", "NA", "NA", "1"] and not rows.get("X") and not rows.get("TR"), rows.get("X"))
        check("o: --evict-mb %d: both P rows of every trial hold 8192 kB for the buffer (the evict range is gone from the "
              "page reads)" % mb, [f[3] for f in rows["P"]] == ["8192"] * 8, [f[3] for f in rows["P"]])
    check("o: the accounting rule can fail on these rows: one changed byte count",
          accounting_problems(plan, outs[8].replace("\nW,0,target,0,oldread,8388608,", "\nW,0,target,0,oldread,8388608,1", 1)))
    rc, out, err = run(base_args + ["--evict-mb", "8", "--hot-copy", "--rec-pad", "80"])
    mm = m_of(out)
    p = accounting_problems(plan, out) + evict_problems(rows_of(out), 8, False) if rc == 0 else ["rc=%s" % rc]
    check("o: --evict-mb 8 together with --hot-copy and --rec-pad 80 runs, the three M rows are set, and the byte accounting holds",
          not p and (mm.get("hot_copy"), mm.get("rec_pad"), mm.get("evict_mb")) == ("1", "80", "8"), p)

    # the rule on changed rows
    r8 = rows_of(outs[8])
    changed = lambda key, value: dict(r8, M=[[f[0], f[1], value] if f[1] == key else f for f in r8["M"]])
    check("o: the rule fails on evict_ns 0 with 8 MiB", evict_problems(changed("evict_ns", "0"), 8, False))
    check("o: the rule fails on another evict_mb", evict_problems(changed("evict_mb", "0"), 8, False))
    check("o: the rule fails on a missing M,evict_ns row", evict_problems(dict(r8, M=[f for f in r8["M"] if f[1] != "evict_ns"]), 8, False))
    check("o: the rule fails on an evict_ns above 0 without a step",
          evict_problems(dict(rows_of(outs[0]), M=[[f[0], f[1], "5"] if f[1] == "evict_ns" else f for f in rows_of(outs[0])["M"]]), 0, False))

    # the step is real: the process holds the range in memory, and a build that stores nothing does not
    rss = {}
    for key, extra, binary in ((0, [], None), (256, ["--evict-mb", "256"], None)):
        rc, out, kb = run_maxrss(base_args + extra, binary)
        rss[key] = kb if rc == 0 and len(rows_of(out).get("E", [])) == 4 else None
    check("o: --evict-mb 256: the peak resident set size of the process is at least 200 MiB above a run without the step "
          "(the range was written)", None not in rss.values() and rss[256] - rss[0] >= 200 << 10, rss)
    b = mutant_build(EVICT_NOSTORE_MUTANT, "nostore")
    rc, out, kb = run_maxrss(base_args + ["--evict-mb", "256"], b) if b else (None, "", 0)
    check("o: that check fails on a build with " + EVICT_NOSTORE_MUTANT,
          rc == 0 and rss[0] is not None and kb - rss[0] < 100 << 10 and m_of(out).get("evict_mb") == "256", (rc, kb, rss))

    # the calls of the step: one mmap of exactly N MiB by the worker, after the buffer and the record block
    d = os.path.join(E.tmp, "shim11")
    os.makedirs(d)
    with open(os.path.join(d, "shim.c"), "w") as f:
        f.write(SHIM)
    so = os.path.join(d, "shim.so")
    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, os.path.join(d, "shim.c")], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    if check("o: the library that logs mmap builds", r.returncode == 0, r.stdout):
        maps = {}
        for mb in (0, 24):
            rc, out, err = run(base_args + ["--evict-mb", str(mb)], env_add={"LD_PRELOAD": so})
            # worker lines only: the thread id differs from the process id
            maps[mb] = [int(x.split()[4]) for x in err.splitlines()
                        if x.startswith("shim mmap ") and x.split()[3] != "tid=" + x.split()[2][4:]] if rc == 0 else None
        buf = 12 << 20  # the 8 MiB buffer is mapped with 4 MiB around it
        check("o: --evict-mb 24: the worker maps exactly 24 MiB once, after the buffer, and it is its last mmap before the trials "
              "apart from memory that stdio or malloc may take",
              maps[24] is not None and maps[24].count(24 << 20) == 1 and buf in maps[24] and
              maps[24].index(24 << 20) > maps[24].index(buf), maps[24])
        check("o: without a step the worker maps the same ranges apart from the 24 MiB",
              maps[0] is not None and maps[24] is not None and (24 << 20) not in maps[0] and
              [x for x in maps[24] if x != 24 << 20] == maps[0], (maps[0], maps[24]))

    # a failed mmap: the address space of the process is limited to 2 GiB
    limit = lambda: resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    r = subprocess.run([E.bin] + base_args + ["--evict-mb", "4096"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=120, preexec_fn=limit)
    rows = rows_of(r.stdout)
    mm = m_of(r.stdout)
    check("o: an mmap that fails (4096 MiB under an address space limit of 2 GiB): status 2, the last row is X,-1,evict with "
          "a text, M,evict_mb,4096 is printed, and no M,evict_ns row, no S row and no trial row follow",
          r.returncode == 2 and r.stdout.rstrip().splitlines()[-1].startswith("X,-1,evict,mmap of 4096 MiB failed: ") and
          mm.get("evict_mb") == "4096" and "evict_ns" not in mm and not any(rows.get(k) for k in "SWEPBK") and
          [f[1:3] for f in rows.get("X", [])] == [["-1", "evict"]], (r.returncode, r.stdout[-200:], r.stderr[-200:]))
    r = subprocess.run([E.bin] + base_args + ["--evict-mb", "8"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=120, preexec_fn=limit)
    check("o: the control: under the same limit --evict-mb 8 runs with status 0 and 4 E rows",
          r.returncode == 0 and len(rows_of(r.stdout).get("E", [])) == 4, (r.returncode, r.stderr[-200:]))

    # --trace: the step lies outside every timed sequence
    tplan = write_plan("evicttrace", TRACE_PLAN)
    counted = ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"]
    for extra in ([], ["--hot-copy"]):
        tag = " with --hot-copy" if extra else ""
        rc, out, err = trial(tplan, counted + ["--evict-mb", "8"] + extra)
        if not check("o: the trace run with --evict-mb 8%s ends with status 0" % tag, rc == 0, err):
            continue
        rows = rows_of(out)
        p = evict_problems(rows, 8, True)
        check("o: trace with --evict-mb 8%s: the rows TR,-1,0,evict_start and TR,-1,1,evict_end hold the step, their "
              "difference is evict_ns, the step ends before the first window, overlaps no timed sequence, and holds no "
              "clock read of a trial" % tag, not p, p)
        p = trace_run_problems(tplan, out)
        check("o: trace with --evict-mb 8%s: no forbidden event in any timed sequence, the W rows, gap_ns and the bin ends are "
              "clock reads of the trace, and no minor page fault in a timed sequence" % tag, not p, p)
        check("o: trace with --evict-mb 8%s: the two rows of the step stand before the first S row" % tag,
              out.index("\nTR,-1,1,evict_end,") < out.index("\nS,0,"))
        if extra:
            continue
        tr = [f for f in rows["TR"] if f[1] == "-1"]
        w0 = of_trial(rows, "W", 0)
        mid = (int(w0[0][7]) + int(w0[-1][8])) // 2
        moved = lambda t0, t1: dict(rows, TR=[f for f in rows["TR"] if f[1] != "-1"] +
                                    [tr[0][:4] + [str(t0)], tr[1][:4] + [str(t1)]],
                                    M=[[f[0], f[1], str(t1 - t0)] if f[1] == "evict_ns" else f for f in rows["M"]])
        check("o: the rule passes on rows rebuilt with the times of the run", not evict_problems(moved(int(tr[0][4]), int(tr[1][4])), 8, True))
        check("o: the rule fails on a step that ends inside the timed sequence of trial 0",
              evict_problems(moved(int(tr[0][4]), mid), 8, True))
        check("o: the rule fails on a step that lies wholly inside the timed sequence of trial 0",
              any("overlaps the timed sequence of trial 0" in x for x in evict_problems(moved(mid, mid + 1000), 8, True)))
        w3 = of_trial(rows, "W", 3)
        check("o: the rule fails on a step that lies inside a window of trial 3",
              any("overlaps the timed sequence of trial 3" in x for x in evict_problems(moved(int(w3[0][7]) + 10, int(w3[0][7]) + 20), 8, True)))
        gap_a, gap_b = int(of_trial(rows, "W", 1)[-1][8]), int(of_trial(rows, "W", 2)[0][7])
        check("o: the rule fails on a step between trial 1 and trial 2 (after the first window)",
              gap_b - gap_a > 4 and evict_problems(moved(gap_a + 1, gap_b - 1), 8, True))
        check("o: the rule fails when evict_ns is not the difference of the two rows",
              evict_problems(dict(rows, M=[[f[0], f[1], str(int(f[2]) + 1)] if f[1] == "evict_ns" else f for f in rows["M"]]), 8, True))
        check("o: the rule fails when the row evict_end is lost", evict_problems(dict(rows, TR=[f for f in rows["TR"] if f[3] != "evict_end"]), 8, True))
        check("o: the rule fails on these rows if they are said to come from a run without --trace", evict_problems(rows, 8, False))
    rc, out, err = trial(tplan, counted + ["--evict-mb", "0"])
    check("o: trace with --evict-mb 0: no TR row of an evict step, and the trace rules hold",
          rc == 0 and not evict_problems(rows_of(out), 0, True) and not [f for f in rows_of(out).get("TR", []) if f[1] == "-1"] and
          not trace_run_problems(tplan, out), rc)
    b = mutant_build(EVICT_LATE_MUTANT, "late")
    rc, out, err = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", tplan] + counted + ["--evict-mb", "8"], binary=b) if b else (None, "", "")
    check("o: the rule fails on a build with " + EVICT_LATE_MUTANT, rc == 0 and evict_problems(rows_of(out), 8, True),
          (rc, [f for f in rows_of(out).get("M", []) if f[1] in NEW_M11]))

    # the layout: without address randomization the five addresses are those of the bwx10 source
    r = subprocess.run(["setarch", os.uname().machine, "-R", "true"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        check("o: addresses without address randomization (setarch -R does not work here: NOT RUN)", False, r.stderr)
    else:
        fixed = {}
        for key, extra, binary in (("bwx10", [], E.bin10), ("none", [], E.bin), (0, ["--evict-mb", "0"], E.bin), (8, ["--evict-mb", "8"], E.bin)):
            r = subprocess.run(["setarch", os.uname().machine, "-R", binary] + base_args + extra, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
            fixed[key] = {k: int(v, 16) for k, v in m_of(r.stdout).items() if k in ADDR_KEYS}
        shown = {k: {a: hex(v) for a, v in fixed[k].items()} for k in fixed}
        check("o: without address randomization (setarch -R), bwx11 without the option has the five addresses of the bwx10 "
              "source: buffer, record block, window records, worker stack variable, worker record (binaries with file "
              "names of the same length, same arguments)",
              len(os.path.basename(E.bin)) == len(os.path.basename(E.bin10)) and os.path.dirname(E.bin) == os.path.dirname(E.bin10) and
              len(fixed["bwx10"]) == 5 and fixed["none"] == fixed["bwx10"], shown)
        # tw_addr lies on the stack of the main thread, below the arguments: two more arguments move it
        heap = [k for k in ADDR_KEYS if k != "tw_addr"]
        check("o: with --evict-mb 0 and with --evict-mb 8 the buffer, the record block, the window records and the worker "
              "stack variable stand at the addresses of a run without the option (the range is mapped after them, and "
              "unmapped again)",
              all(len(fixed[k]) == 5 and [fixed[k][a] for a in heap] == [fixed["none"][a] for a in heap] for k in (0, 8)), shown)
        check("o: --evict-mb 8 has all five addresses of --evict-mb 0 (arguments of the same length)",
              len(fixed[8]) == 5 and fixed[8] == fixed[0], shown)

    good = write_plan("good", [GOOD])
    args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good]
    for name, value in (("a negative value", "-1"), ("a value above 4096", "4097"), ("a word", "abc"),
                        ("a number with a letter after it", "8x"), ("a fraction", "1.5"), ("an empty value", ""),
                        ("a hex number", "0x8"), ("a number with a unit", "8M")):
        rc, out, err = run(args + ["--evict-mb", value])
        check("o: status 2, no row and a message for --evict-mb with " + name, rc == 2 and out == "" and "--evict-mb" in err,
              "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))
    rc, out, err = run(args + ["--evict-mb"])
    check("o: status 2 and no row for --evict-mb without a value", rc == 2 and out == "" and err.strip() != "", rc)
    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--evict-mb", "8"])
    check("o: status 2 and no row for --evict-mb outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)
    rc, out, err = run(args + ["--evict-mb", "0"])
    check("o: the control: the same command with --evict-mb 0 runs with status 0", rc == 0 and "\nE,0," in out, rc)
    rc, out, err = run(args + ["--evict-mb", "4096"])
    check("o: the largest value, --evict-mb 4096, runs with status 0 on this machine (4 GiB of memory are written twice)",
          rc == 0 and "\nE,0," in out and m_of(out).get("evict_mb") == "4096" and int(m_of(out).get("evict_ns", "0")) > 0,
          (rc, err[:200], out[-200:]))


def main():
    with open("/proc/loadavg") as f:
        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))
    E.allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)
    if len(E.allowed) < 3 or 0 not in E.allowed:
        print("FAIL setup: CPU 0 and two more CPUs from 0 to 119 are needed in the allowed set: %s" % E.allowed)
        return 1
    E.cpu, E.cpu2 = [c for c in E.allowed if c != 0][:2]  # worker CPU, and a second CPU
    E.ctl = E.cpu2                                         # a control CPU that is not the default
    E.absent = next((c for c in range(120) if c not in E.allowed), None)
    E.tmp = tempfile.mkdtemp(prefix="bwx11-test-")
    E.bin, E.bin_old, E.bin8 = os.path.join(E.tmp, "bwx11"), os.path.join(E.tmp, "bwx"), os.path.join(E.tmp, B8)
    E.bin10, E.src10 = os.path.join(E.tmp, B10), os.path.join(E.tmp, "src10")  # the bwx10 source: bwx11.c without its marked blocks
    print("# worker CPU %d, control CPU 0 (default) or %d, temporary folder %s" % (E.cpu, E.ctl, E.tmp))
    try:
        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin, os.path.join(HERE, "bwx11.c")], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        if not check("build: bwx11.c compiles with the flags of build11.sh and no compiler message", r.returncode == 0 and r.stdout == "", r.stdout):
            return 1
        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin_old, os.path.join(OLD, "bwx.c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not check("build: bwx.c compiles (reference for the --seq mode)", r.returncode == 0):
            return 1
        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin8, os.path.join(X8, B8 + ".c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not check("build: the source of the accepted runner compiles (reference for the layout and the kernel list)", r.returncode == 0):
            return 1
        os.makedirs(E.src10)
        for name in ("bwx11.c", "bwx11_selftest.c"):
            with open(os.path.join(HERE, name)) as f:
                text = strip_marked(f.read(), "bwx11")[0]
            with open(os.path.join(E.src10, name.replace("bwx11", B10)), "w") as f:
                f.write(text)
        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin10, os.path.join(E.src10, B10 + ".c")], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        if not check("build: bwx11.c without its marked blocks (the bwx10 source) compiles with no compiler message (reference "
                     "for the layout, the rows and the kernel list of bwx10)", r.returncode == 0 and r.stdout == "", r.stdout):
            return 1
        for test in (test_source, test_selftest, test_selftest_rows, test_bad_plans, test_rows, test_sequence_code,
                     test_trace, test_counters, test_disturbed, test_placement, test_kill_and_seq, test_listing_saved,
                     test_build_scripts, test_new_kernels, test_rec_pad, test_hot_copy, test_nop_kernels, test_evict):
            test()
    finally:
        if os.environ.get("KEEP"):
            print("# kept: %s" % E.tmp)
        else:
            shutil.rmtree(E.tmp, ignore_errors=True)
    with open("/proc/loadavg") as f:
        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))
    print("# checks failed: %d%s" % (len(failed), "".join("\n#   " + n for n in failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
