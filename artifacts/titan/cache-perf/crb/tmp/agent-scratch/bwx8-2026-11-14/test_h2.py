#!/usr/bin/env python3
"""test_h2.py - local tests of run_h2.sh and of h2_analyze.py.

Runs on the development machine. It never contacts CRB. run_h2.sh is run
with two dummy binaries (shell scripts named bw_old and bw_new in a temporary
folder) through the test-only settings H2_DIR, H2_SHA256_OLD, H2_SHA256_NEW,
BWX8_MARKER, BWX8_STOPFILE and BWX8_RESULTS. The dummy binaries print rows in
the csv form of the original program, so rates mean nothing.

Usage: test_h2.py            (KEEP=1 keeps the temporary folder)
Output: one line per check, "PASS name" or "FAIL name: detail".
Exit status: 0 only if every check passed.

The full run of 72 dummy processes takes about 75 s on an idle machine,
because run_h2.sh looks at the marker file once per second while a process
runs. On a machine with more than 2 runnable tasks run_h2.sh also waits up to
20 s before every process (its "settle" rule), so the full run can take up to
26 min. The test allows 40 min for it.
"""
import contextlib
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_h2.sh")
VISIT = os.path.join(HERE, "visit_h2.sh")
A = os.path.normpath(os.path.join(HERE, "..", "..", "..", "new-test-kernel", "tackle-8mb-analysis"))
ORIG_RUN = os.path.join(HERE, "..", "kernels-2026-11-13", "run_kernels.sh")
sys.path.insert(0, A)
sys.dont_write_bytecode = True
import h2_analyze  # noqa: E402

OPTIONS = "--threads 1 --cpus %s --bytes 8M --kernel read --reps 3 --min-ms 500"

# The dummy binary. It logs its name and arguments, counts its calls, and prints what the original
# program prints. Rates: bw_old 67.00 to 67.02; bw_new on CPU 41 starts low and ends high.
# DUMMY_MARK_AT=n: the n-th call creates the marker file and then sleeps (the runner must kill it).
# DUMMY_FAIL_AT=n: the n-th call exits with status 7.
# DUMMY_SLEEP_AT=n: the n-th call sleeps for 300 s (the test stops the runner meanwhile).
# A call that sleeps writes its process id to the file "pid" first. run_h2.sh starts the dummy with
# setsid, so this id is also the id of its process group.
DUMMY = r"""#!/usr/bin/env bash
me=$(basename "$0"); d=$(dirname "$0")
echo "$me $*" >> "$d/calls.log"
n=$(wc -l < "$d/calls.log")
cpu=$4
if [[ -n ${DUMMY_FAIL_AT:-} && $n == "$DUMMY_FAIL_AT" ]]; then echo "dummy failure" >&2; exit 7; fi
echo "# bandwidth: GB = 1e9 bytes; dummy threads=1 bytes_per_thread=8388608 min_ms=500 thp=madvise"
echo "kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps"
if [[ $me == bw_old ]]; then r=(67.00 67.01 67.02); elif [[ $cpu == 41 ]]; then r=(69.10 70.00 71.60); else r=(67.50 67.60 67.70); fi
for i in 0 1 2; do echo "read,1,8388608,$i,33537654784,0.5001,${r[i]},${r[i]},${r[i]},${r[i]}"; done
if [[ -n ${DUMMY_MARK_AT:-} && $n == "$DUMMY_MARK_AT" ]]; then echo $$ > "$d/pid"; touch "$DUMMY_MARKER"; sleep 30; fi
if [[ -n ${DUMMY_SLEEP_AT:-} && $n == "$DUMMY_SLEEP_AT" ]]; then echo $$ > "$d/pid"; sleep 300; fi
echo "read,1,8388608,best,,,${r[2]},,,"
"""

failed = []


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else ": " + str(detail)[:400]))
    if not ok:
        failed.append(name)
    return ok


def sha(path):
    if not os.path.exists(path):
        return "0" * 64
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Box:
    """one temporary set-up: dummy binaries, results folder, marker and stop file paths"""

    def __init__(self, top, name):
        self.dir = os.path.join(top, name)
        self.bin = os.path.join(self.dir, "bin")
        self.results = os.path.join(self.dir, "results")
        os.makedirs(self.bin)
        os.makedirs(self.results)
        for b in ("bw_old", "bw_new"):
            p = os.path.join(self.bin, b)
            with open(p, "w") as f:
                f.write(DUMMY + "# %s\n" % b)
            os.chmod(p, 0o755)
        self.marker = os.path.join(self.dir, "RUNNING")
        self.stopfile = os.path.join(self.dir, "STOP")

    def env(self, **more):
        e = {k: v for k, v in os.environ.items()
             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED") and not k.startswith(("H2_", "BWX8_", "DUMMY_"))}
        e.update(H2_DIR=self.bin, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_RESULTS=self.results,
                 H2_SHA256_OLD=sha(os.path.join(self.bin, "bw_old")), H2_SHA256_NEW=sha(os.path.join(self.bin, "bw_new")),
                 DUMMY_MARKER=self.marker, HOME=self.dir)
        e.update(more)
        return {k: v for k, v in e.items() if v is not None}

    def run(self, *args, timeout=600, **more):
        return subprocess.run([RUN] + list(args), env=self.env(**more), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=timeout)

    def folders(self):
        return sorted(os.listdir(self.results))

    def calls(self):
        p = os.path.join(self.bin, "calls.log")
        return open(p).read().splitlines() if os.path.exists(p) else []


def group_left(box):
    """True if a process of the group of the sleeping dummy still exists (or if the dummy wrote no id)"""
    try:
        pid = int(open(os.path.join(box.bin, "pid")).read())
    except (OSError, ValueError):
        return True
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def run_until_sleep(box, act, **more):
    """start run_h2.sh, wait until a dummy sleeps, call act(runner), return (status, H2.csv text)"""
    p = subprocess.Popen([RUN], env=box.env(**more), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pidfile = os.path.join(box.bin, "pid")
    end = time.time() + 300
    while time.time() < end and p.poll() is None and not (os.path.exists(pidfile) and os.path.getsize(pidfile)):
        time.sleep(0.1)
    started = p.poll() is None and group_left(box)
    time.sleep(0.5)
    act(p)
    try:
        rc = p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        rc = "timeout"
    f = box.folders()
    csv = open(os.path.join(box.results, f[0], "H2.csv")).read() if f else ""
    return (rc if started else "the dummy did not start"), csv


def utc(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))


def dry_lines(out):
    return [l for l in out.splitlines() if l.startswith("bw_")]


def order_problems(rows, session):
    """problems of an order [(cpu, pair, pos, binary)] against the rules of the head of run_h2.sh"""
    p = []
    cpus = ["2", "0", "41"] if session == 1 else ["41", "0", "2"]
    if len(rows) != 72:
        return ["%d processes, 72 expected" % len(rows)]
    if list(dict.fromkeys(r[0] for r in rows)) != cpus:
        p.append("CPU order %s, expected %s" % (list(dict.fromkeys(r[0] for r in rows)), cpus))
    for ci, cpu in enumerate(cpus):
        blk = rows[ci * 24:(ci + 1) * 24]
        if any(r[0] != cpu for r in blk):
            p.append("CPU %s: its 24 processes are not in one run" % cpu)
            continue
        for b in ("bw_old", "bw_new"):
            if sum(r[3] == b for r in blk) != 12:
                p.append("CPU %s: %d processes of %s, 12 expected" % (cpu, sum(r[3] == b for r in blk), b))
            first = sum(r[3] == b and r[2] == "1" for r in blk)
            if first != 6:
                p.append("CPU %s: %s is first in %d pairs, 6 expected" % (cpu, b, first))
        for k in range(12):
            x, y = blk[2 * k], blk[2 * k + 1]
            if (x[1], y[1], x[2], y[2]) != (str(k + 1), str(k + 1), "1", "2") or {x[3], y[3]} != {"bw_old", "bw_new"}:
                p.append("CPU %s: places %d and %d are not pair %d with one process of each binary" % (cpu, 2 * k, 2 * k + 1, k + 1))
        # equal mean place of both binaries inside the block (no linear drift favours one binary)
        place = {b: sum(i for i, r in enumerate(blk) if r[3] == b) for b in ("bw_old", "bw_new")}
        if place["bw_old"] != place["bw_new"]:
            p.append("CPU %s: sum of places differs between the binaries: %s" % (cpu, place))
    return p


def dry_order(out):
    rows = []
    for l in dry_lines(out):
        m = re.match(r"(bw_\w+) --threads 1 --cpus (\d+) .*# idx (\d+), pair (\d+), pos (\d), tag (\S+)$", l)
        rows.append((m.group(2), m.group(4), m.group(5), m.group(1)) if m else ("?",) * 4)
    return rows


def synth_header(binary, cpu, session, idx, pair, pos):
    return ("-- binary %s kernel read threads 1 cpus %s bytes 8M round %d load 0.10 utc 01:02:03 session %d idx %d pair %d pos %d "
            "tag t waited_s 0 loadavg 0.10 0.10 0.10 1/900 logins 1" % (binary, cpu, session, session, idx, pair, pos))


def synth_rows(rates):
    out = ["# bandwidth: synthetic", "kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,x,y,z"]
    out += ["read,1,8388608,%d,1,0.5,%.2f,%.2f,%.2f,%.2f" % (i, r, r, r, r) for i, r in enumerate(rates)]
    if rates:
        out.append("read,1,8388608,best,,,%.2f,,," % max(rates))
    return out


def analyze(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = h2_analyze.main(list(argv))
    return rc, buf.getvalue(), err.getvalue()


def main():
    top = tempfile.mkdtemp(prefix="test_h2_")
    try:
        tests(top)
    finally:
        if os.environ.get("KEEP"):
            print("kept: %s" % top)
        else:
            shutil.rmtree(top, ignore_errors=True)
    print("%d checks failed" % len(failed) if failed else "all checks passed")
    return 1 if failed else 0


def tests(top):
    # ---- the files ----
    for f in (RUN, VISIT):
        r = subprocess.run(["bash", "-n", f], stderr=subprocess.PIPE, universal_newlines=True)
        check("syntax %s" % os.path.basename(f), r.returncode == 0, r.stderr)
    text = open(RUN).read()
    check("run_h2.sh never calls sudo, ssh, scp, gcc or make",
          not re.search(r"^[^#\n]*\b(sudo|ssh|scp|gcc|make)\b", text, re.M))
    check("run_h2.sh pins itself to CPUs 0-119", "exec taskset -c 0-119" in text)
    check("run_h2.sh holds the two digests of handoff.md",
          "e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa" in text
          and "fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6" in text)
    # the option spelling of the original "one" function
    orig = open(ORIG_RUN).read()
    check("original run_kernels.sh has the option line this test expects",
          '--threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500' in orig and "for bytes in 32K 1M 8M 1G" in orig)
    vt = open(VISIT).read()
    check("visit_h2.sh calls ./run_h2.sh after the marker check", "./run_h2.sh $*" in vt and "/tmp/positron-perf.RUNNING" in vt
          and "run_bwx8.sh" not in vt.replace("# ", ""))

    # ---- dry run ----
    b = Box(top, "dry")
    for s in (1, 2):
        r = b.run("--dry-run", SESSION=str(s))
        lines = dry_lines(r.stdout)
        check("dry run session %d: status 0 and 72 command lines" % s, r.returncode == 0 and len(lines) == 72
              and "count: 72 command lines" in r.stdout, (r.returncode, len(lines), r.stderr))
        check("dry run session %d: prints process count and nominal work first" % s,
              r.stdout.startswith("H2 session %d: 72 processes" % s) and "nominal kernel work 108.000 s" in r.stdout, r.stdout[:200])
        bad = [l for l in lines if not re.match(r"bw_(old|new) " + re.escape(OPTIONS).replace("%s", r"(2|0|41)") + r"  # ", l)]
        check("dry run session %d: every line has the original options" % s, not bad, bad[:2])
        check("dry run session %d: the order is balanced" % s, not order_problems(dry_order(r.stdout), s), order_problems(dry_order(r.stdout), s)[:3])
        check("dry run session %d: warns about each test setting" % s,
              all("warning: %s is set" % v in r.stderr for v in ("H2_DIR", "H2_SHA256_OLD", "H2_SHA256_NEW", "BWX8_MARKER", "BWX8_STOPFILE", "BWX8_RESULTS")))
    check("dry run: no result folder, no process started", b.folders() == [] and b.calls() == [])
    r1, r2 = dry_order(b.run("--dry-run", SESSION="1").stdout), dry_order(b.run("--dry-run", SESSION="2").stdout)
    check("session 2 reverses the CPU order and the first binary of every pair",
          [x[0] for x in r2[::24]] == [x[0] for x in r1[::24]][::-1]
          and all(dict(((x[0], x[1], x[2]), x[3]) for x in r1)[(y[0], y[1], y[2])] != y[3] for y in r2))
    # the order rule can fail: a changed order must be reported
    sw = list(r1)
    sw[2], sw[3] = (sw[2][0], sw[2][1], "1", sw[3][3]), (sw[3][0], sw[3][1], "2", sw[2][3])
    check("order rule reports an unbalanced order", order_problems(sw, 1) and order_problems(r1, 2) and order_problems(r1[:70], 1))
    r = b.run("--dry-run", "--from", "70", SESSION="1")
    check("dry run --from 70: 2 command lines", r.returncode == 0 and len(dry_lines(r.stdout)) == 2 and "count: 2 command lines" in r.stdout)
    r = b.run("--dry-run", "--from", "72", SESSION="1")
    check("dry run --from 72: status 2", r.returncode == 2, r.returncode)

    # ---- usage ----
    r = b.run("--dry-run", SESSION=None)
    check("no SESSION: status 2", r.returncode == 2 and "set SESSION" in r.stderr)
    r = b.run("--dry-run", "S2", SESSION="1")
    check("unknown argument: status 2", r.returncode == 2)
    r = b.run(SESSION="1")
    check("no STOP_AT: status 2, nothing started", r.returncode == 2 and "set STOP_AT" in r.stderr and b.calls() == [] and b.folders() == [])

    # ---- digest ----
    b = Box(top, "digest")
    r = b.run(SESSION="1", STOP_AT="none", H2_SHA256_NEW="0" * 64)
    check("digest of bw_new differs: status 2, nothing started", r.returncode == 2 and "bw_new does not have the expected sha256" in r.stderr
          and b.calls() == [] and b.folders() == [], (r.returncode, r.stderr[-200:]))
    r = b.run(SESSION="1", STOP_AT="none", H2_SHA256_OLD="0" * 64)
    check("digest of bw_old differs: status 2, nothing started", r.returncode == 2 and "bw_old does not have the expected sha256" in r.stderr
          and b.calls() == [] and b.folders() == [])
    r = b.run(SESSION="1", STOP_AT="none", H2_SHA256_OLD=None, H2_SHA256_NEW=None)
    check("dummy binaries against the real digests: status 2, nothing started", r.returncode == 2 and b.calls() == [] and b.folders() == [])
    os.remove(os.path.join(b.bin, "bw_new"))
    r = b.run(SESSION="1", STOP_AT="none")
    check("missing bw_new: status 2, no rebuild", r.returncode == 2 and "missing" in r.stderr and not os.path.exists(os.path.join(b.bin, "bw_new")))

    # ---- stop controls before the first process ----
    b = Box(top, "stops")
    open(b.marker, "w").close()
    r = b.run(SESSION="1", STOP_AT="none")
    check("marker file present: status 3, nothing started", r.returncode == 3 and "RUNNING file present" in r.stderr and b.calls() == [] and b.folders() == [],
          (r.returncode, r.stderr[-200:]))
    os.remove(b.marker)
    open(b.stopfile, "w").close()
    r = b.run(SESSION="1", STOP_AT="none")
    check("stop file present: status 5, nothing started", r.returncode == 5 and b.calls() == [] and b.folders() == [], (r.returncode, r.stderr[-200:]))
    os.remove(b.stopfile)
    r = b.run(SESSION="1", STOP_AT=utc(-60))
    check("STOP_AT in the past: status 4, nothing started", r.returncode == 4 and b.calls() == [] and b.folders() == [], (r.returncode, r.stderr[-200:]))
    r = b.run(SESSION="1", STOP_AT=utc(60))
    check("STOP_AT 60 s away (MARGIN 92 s): status 4, nothing started", r.returncode == 4 and "less than 92 s away" in r.stderr and b.calls() == [],
          (r.returncode, r.stderr[-200:]))
    r = b.run(SESSION="1", STOP_AT="not-a-time")
    check("bad STOP_AT: status 2", r.returncode == 2 and b.calls() == [])

    # ---- session 2 ----
    r = b.run(SESSION="2", STOP_AT="none")
    check("session 2 without SESSION1_END: status 2", r.returncode == 2 and "needs SESSION1_END" in r.stderr and b.calls() == [])
    r = b.run(SESSION="2", STOP_AT="none", SESSION1_END=utc(-10800 + 120))
    check("session 2 two minutes too early: status 2, nothing started", r.returncode == 2 and "3 hours after" in r.stderr and b.calls() == [] and b.folders() == [],
          (r.returncode, r.stderr[-200:]))
    r = b.run(SESSION="2", STOP_AT="none", SESSION1_END="yesterday")
    check("session 2 with a SESSION1_END that is not a full UTC time: status 2", r.returncode == 2 and "bad SESSION1_END" in r.stderr and b.calls() == [])
    r = b.run("--from", "70", SESSION="2", STOP_AT="none", SESSION1_END=utc(-10800 - 120))
    f = b.folders()
    check("session 2 three hours and two minutes after session 1: runs (--from 70: 2 processes)",
          r.returncode == 0 and len(b.calls()) == 2 and len(f) == 1 and re.match(r"h2-s2-\d{8}T\d{6}Z$", f[0]), (r.returncode, r.stderr[-300:], f))
    if f:
        env = open(os.path.join(b.results, f[0], "env.txt")).read()
        check("--from is recorded in env.txt", " from=70 " in env and "to_run_processes=2" in env)

    # ---- marker appears while a process runs ----
    b = Box(top, "midmark")
    r = b.run(SESSION="1", STOP_AT="none", DUMMY_MARK_AT="3")
    f = b.folders()
    csv = open(os.path.join(b.results, f[0], "H2.csv")).read() if f else ""
    check("marker appears during process 3: status 3, the process is killed, no later process starts",
          r.returncode == 3 and len(b.calls()) == 3 and csv.count("-- binary") == 3 and csv.count("read,1,8388608,best") == 2
          and re.search(r"^-- killed tag s1-c2-p02-new status 3 ", csv, re.M), (r.returncode, len(b.calls()), r.stderr[-200:]))
    check("marker appears during process 3: no process of its group is left", not group_left(b))
    # ---- interruption and stop file while a process runs: the process group must be gone afterwards ----
    for sig, name in ((15, "TERM"), (2, "INT"), (1, "HUP")):
        b = Box(top, "sig" + name)
        rc, csv = run_until_sleep(b, lambda p, sig=sig: p.send_signal(sig), SESSION="1", STOP_AT="none", DUMMY_SLEEP_AT="2")
        check("signal %s during process 2: status 130, a 'killed' line, no later process, no process of its group is left" % name,
              rc == 130 and len(b.calls()) == 2 and re.search(r"^-- killed tag s1-c2-p01-new status 130 ", csv, re.M) and not group_left(b),
              (rc, len(b.calls()), group_left(b)))
    b = Box(top, "midstop")
    rc, csv = run_until_sleep(b, lambda p: open(b.stopfile, "w").close(), SESSION="1", STOP_AT="none", DUMMY_SLEEP_AT="1")
    check("stop file appears during process 1: status 5, a 'killed' line, no later process, no process of its group is left",
          rc == 5 and len(b.calls()) == 1 and re.search(r"^-- killed tag s1-c2-p01-old status 5 ", csv, re.M) and not group_left(b),
          (rc, len(b.calls()), group_left(b)))
    b = Box(top, "midstopat")
    t0 = time.time()
    rc, csv = run_until_sleep(b, lambda p: None, SESSION="1", STOP_AT=utc(60), RESERVE="5", DUMMY_SLEEP_AT="1")
    check("STOP_AT is reached during process 1: status 4, a 'killed' line, no process of its group is left",
          rc == 4 and len(b.calls()) == 1 and re.search(r"^-- killed tag s1-c2-p01-old status 4 ", csv, re.M) and not group_left(b),
          (rc, len(b.calls()), group_left(b), time.time() - t0))
    b = Box(top, "fail")
    r = b.run(SESSION="1", STOP_AT="none", DUMMY_FAIL_AT="2")
    f = b.folders()
    csv = open(os.path.join(b.results, f[0], "H2.csv")).read() if f else ""
    check("a benchmark fails: status 1, a 'failed' line, no later process", r.returncode == 1 and len(b.calls()) == 2 and "-- failed tag s1-c2-p01-new exit 7" in csv,
          (r.returncode, len(b.calls())))

    # ---- a full run of session 1 ----
    b = Box(top, "full")
    r = b.run(SESSION="1", STOP_AT=utc(7200), timeout=2400)
    f = b.folders()
    check("full run: status 0, one folder h2-s1-<UTC>", r.returncode == 0 and len(f) == 1 and re.match(r"h2-s1-\d{8}T\d{6}Z$", f[0] if f else ""),
          (r.returncode, r.stderr[-300:], f))
    out = os.path.join(b.results, f[0]) if f else ""
    if f:
        check("full run: the folder holds exactly H2.csv env.txt launches.txt order.tsv stderr.txt",
              sorted(os.listdir(out)) == ["H2.csv", "env.txt", "launches.txt", "order.tsv", "stderr.txt"], sorted(os.listdir(out)))
        check("full run: nothing written outside the result folder and the dummy call log",
              sorted(os.listdir(b.dir)) == ["bin", "results"] and sorted(os.listdir(b.bin)) == ["bw_new", "bw_old", "calls.log"])
        check("full run: prints process count and nominal work before the start", r.stdout.startswith("H2 session 1: 72 processes") and
              r.stdout.index("H2 session 1") < r.stdout.index("result folder:"))
        order = [l.split("\t") for l in open(os.path.join(out, "order.tsv")).read().splitlines()]
        saved = [(x[1], x[2], x[3], x[4]) for x in order[1:]]
        check("full run: order.tsv is saved, balanced, and numbered 0 to 71",
              order[0] == ["idx", "cpu", "pair", "pos", "binary"] and [x[0] for x in order[1:]] == [str(i) for i in range(72)]
              and not order_problems(saved, 1), order_problems(saved, 1)[:3])
        check("full run: order.tsv equals the dry run", saved == r1)
        calls = b.calls()
        check("full run: 72 processes started, in the saved order, each with the original options",
              calls == ["%s %s" % (x[3], OPTIONS % x[0]) for x in saved], calls[:2])
        csv = open(os.path.join(out, "H2.csv")).read().splitlines()
        heads = [l for l in csv if l.startswith("-- ")]
        want = [r"-- binary %s kernel read threads 1 cpus %s bytes 8M round 1 load \S+ utc \d\d:\d\d:\d\d session 1 idx %d pair %s pos %s tag \S+ waited_s \d+ "
                % (x[3], x[0], i, x[1], x[2]) for i, x in enumerate(saved)]
        check("full run: H2.csv has one header line per process, in the saved order",
              len(heads) == 72 and all(re.match(w, h) for w, h in zip(want, heads)), heads[:1])
        check("full run: every header is followed by 3 repetition rows",
              len([l for l in csv if re.match(r"read,1,8388608,[012],", l)]) == 216 and all(csv[i + 3].startswith("read,1,8388608,0,") for i, l in enumerate(csv) if l.startswith("-- ")))
        sys.path.insert(0, os.path.dirname(h2_analyze.ORIGINAL))
        try:
            import summarize
            d, loads = summarize.load(os.path.join(out, "H2.csv"))
            check("full run: the original summarize.py reads H2.csv (36 repetitions per binary and CPU... 108 per binary)",
                  len(loads) == 72 and len(d["8M", "read", "bw_old"]) == 108 and len(d["8M", "read", "bw_new"]) == 108)
        except Exception as e:  # noqa: BLE001
            check("full run: the original summarize.py reads H2.csv", False, e)
        launches = open(os.path.join(out, "launches.txt")).read()
        check("full run: launches.txt has one load record per launch", len(re.findall(r"^== H2.csv idx \d+ \S+ utc \S+ loadavg ", launches, re.M)) == 72)
        env = open(os.path.join(out, "env.txt")).read()
        check("full run: env.txt has the settings, the digests and the end line",
              "session=1 from=0 " in env and "cpu_order=2 0 41" in env and "planned_processes=72" in env and sha(os.path.join(b.bin, "bw_old")) in env
              and sha(os.path.join(b.bin, "bw_new")) in env and re.search(r"^## end utc=", env, re.M) and "DIR=%s" % b.bin in env)
        rc, text, err = analyze("--results", b.results)
        check("h2_analyze.py on the full dummy run: status 0, 12 pairs per CPU",
              rc == 0 and len(re.findall(r"^  pair summary: 12 pairs", text, re.M)) == 3 and "H2 runs: 1 file(s)" in text, (rc, err))
        check("h2_analyze.py on the full dummy run: CPU 41 repetitions are low, between, high",
              "  session 1 CPU  41: 12 pairs | gain of medians: median   4.46 % | new repetitions: low 12, between 12, high 12" in text
              and "  session 1 CPU   2: 12 pairs | gain of medians: median   0.88 % | new repetitions: low 36, between 0, high 0" in text,
              [l for l in text.splitlines() if l.startswith("  session")])

    analyzer_tests(top)


def analyzer_tests(top):
    # ---- the functions ----
    c = h2_analyze.classify
    check("classify: borders", (c(69.5, 69.5, 70.5), c(69.51, 69.5, 70.5), c(70.49, 69.5, 70.5), c(70.5, 69.5, 70.5), c(67.7, 69.5, 70.5), c(71.6, 69.5, 70.5))
          == ("low", "between", "between", "high", "low", "high"))
    check("gain: 100 x (new / old - 1)", abs(h2_analyze.gain(67.71, 67.08) - 0.9392) < 1e-3 and h2_analyze.gain(60.0, 80.0) == -25.0)

    # ---- the original run ----
    rc, text, err = analyze("--results", os.path.join(top, "none"))
    check("original numbers: status 0 and the note that no H2 file exists", rc == 0 and "no H2.csv found" in text, (rc, err))
    check("original numbers: best rates 67.08 and 67.71 GB/s, gain 0.94 %, class low",
          "original, all CPUs: old best  67.08 | new best  67.71 | gain of the best repetitions   0.94 % | class of the new best: low" in text)
    gm = re.findall(r"^  pair  \d \((?:old|new) first\): .* gain of medians +(\S+) %", text, re.M)
    check("original numbers: the four pair gains of the design (0.51, 0.69, 0.94, 0.51 %)", gm == ["0.51", "0.69", "0.94", "0.51"], gm)
    check("original numbers: round 1 ran old first, round 2 new first",
          len(re.findall(r"^  pair  1 \(old first\)", text, re.M)) == 2 and len(re.findall(r"^  pair  2 \(new first\)", text, re.M)) == 2)
    check("original numbers: the three repetitions of the new read on CPU 2, round 1", "  new round 1:  67.71  67.66  67.65 | median  67.66 | max  67.71" in text)

    # ---- a synthetic H2.csv ----
    res = os.path.join(top, "synth")
    d1 = os.path.join(res, "h2-s1-20261115T000000Z")
    d2 = os.path.join(res, "h2-s2-20261115T040000Z")
    os.makedirs(d1)
    os.makedirs(d2)
    lines = []
    # session 1, CPU 2: pair 1 old first, pair 2 new first, pair 3 with a killed new process
    lines += [synth_header("bw_old", "2", 1, 0, 1, 1)] + synth_rows([67.00, 67.10, 67.20])
    lines += [synth_header("bw_new", "2", 1, 1, 1, 2)] + synth_rows([67.50, 69.50, 71.00])       # low low high, median 69.50
    lines += [synth_header("bw_new", "2", 1, 2, 2, 1)] + synth_rows([70.00, 70.50, 71.60])       # between high high
    lines += [synth_header("bw_old", "2", 1, 3, 2, 2)] + synth_rows([80.00, 80.00, 80.00])
    lines += [synth_header("bw_old", "2", 1, 4, 3, 1)] + synth_rows([67.00, 67.00, 67.00])
    lines += [synth_header("bw_new", "2", 1, 5, 3, 2)] + synth_rows([67.50]) + ["-- killed tag t status 3 utc 01:02:03"]
    # session 1, CPU 41: one pair
    lines += [synth_header("bw_new", "41", 1, 48, 1, 1)] + synth_rows([71.60, 71.60, 71.60])
    lines += [synth_header("bw_old", "41", 1, 49, 1, 2)] + synth_rows([71.60, 71.60, 35.80])
    with open(os.path.join(d1, "H2.csv"), "w") as f:
        f.write("\n".join(lines) + "\n")
    lines = [synth_header("bw_new", "41", 2, 0, 1, 1)] + synth_rows([69.10, 69.10, 69.10])
    lines += [synth_header("bw_old", "41", 2, 1, 1, 2)] + synth_rows([69.10, 69.10, 69.10])
    with open(os.path.join(d2, "H2.csv"), "w") as f:
        f.write("\n".join(lines) + "\n")
    rc, text, err = analyze("--results", res)
    check("synthetic: status 0, two files, sessions and CPUs in run order",
          rc == 0 and "H2 runs: 2 file(s)" in text
          and re.findall(r"^== (session \d, CPU \d+) ==", text, re.M) == ["session 1, CPU 2", "session 1, CPU 41", "session 2, CPU 41"], (rc, err))
    check("synthetic: a process line has the three rates, the median and the maximum",
          "  new idx  1 pair  1 pos 2:  67.50  69.50  71.00 | median  69.50 | max  71.00" in text
          and "  old idx  0 pair  1 pos 1:  67.00  67.10  67.20 | median  67.10 | max  67.20" in text)
    check("synthetic: pair 1 gain of medians 3.58 %, of maxima 5.65 %, old first",
          "  pair  1 (old first): old median  67.10 max  67.20 | new median  69.50 max  71.00 | gain of medians   3.58 % | gain of maxima   5.65 %" in text)
    check("synthetic: pair 2 gain -11.88 % and -10.50 %, new first",
          "  pair  2 (new first): old median  80.00 max  80.00 | new median  70.50 max  71.60 | gain of medians -11.88 % | gain of maxima -10.50 %" in text)
    check("synthetic: the killed process is shown as not complete, and pair 3 is left out",
          "  new idx  5 pair  3 pos 2:  67.50 | NOT COMPLETE (status killed, 1 of 3 repetitions): left out below" in text
          and "  pair summary: 2 pairs | gain of medians: median  -4.15 %, lowest -11.88 %, highest   3.58 %" in text and "pair  3 (" not in text)
    check("synthetic: classes per repetition of the new read (CPU 2, session 1)",
          "  new repetition 0: low 1, between 1, high 0" in text and "  new repetition 1: low 1, between 0, high 1" in text
          and "  new repetition 2: low 0, between 0, high 2" in text and "  new all repetitions (6): low 2, between 1, high 3" in text)
    check("synthetic: a process that changes class is listed", "  new idx 1 changes class inside the process: low low high (67.50  69.50  71.00)" in text
          and "  new idx 2 changes class inside the process: between high high" in text)
    check("synthetic: summary lines of both sessions",
          "  session 1 CPU   2:  2 pairs | gain of medians: median  -4.15 % | new repetitions: low 2, between 1, high 3" in text
          and "  session 1 CPU  41:  1 pairs | gain of medians: median   0.00 % | new repetitions: low 0, between 0, high 3" in text
          and "  session 2 CPU  41:  1 pairs | gain of medians: median   0.00 % | new repetitions: low 3, between 0, high 0" in text,
          [l for l in text.splitlines() if l.startswith("  session")])
    rc, text2, err = analyze("--results", res, "--low-max", "70.0", "--high-min", "71.5")
    check("synthetic: the levels of the command line change the classes",
          rc == 0 and "  new all repetitions (6): low 3, between 2, high 1" in text2, [l for l in text2.splitlines() if "new all" in l])
    rc, _, err = analyze("--results", res, "--low-max", "71", "--high-min", "70")
    check("levels in the wrong order: status 2", rc == 2)
    rc, text3, err = analyze(os.path.join(d2, "H2.csv"))
    check("a file named on the command line is the only one read", rc == 0 and "H2 runs: 1 file(s)" in text3 and "session 1, CPU" not in text3)
    # a continued session: idx 5 complete in a second folder replaces the killed one
    d3 = os.path.join(res, "h2-s1-20261115T000500Z")
    os.makedirs(d3)
    with open(os.path.join(d3, "H2.csv"), "w") as f:
        f.write("\n".join([synth_header("bw_new", "2", 1, 5, 3, 2)] + synth_rows([67.67, 67.67, 67.67])) + "\n")
    rc, text4, err = analyze("--results", res)
    check("a continued session (second folder, --from): the complete process replaces the killed one",
          rc == 0 and "  pair  3 (old first): old median  67.00 max  67.00 | new median  67.67 max  67.67 | gain of medians   1.00 %" in text4
          and "NOT COMPLETE" not in text4, (rc, err))
    # defects that must be reported
    bad = os.path.join(top, "bad.csv")
    with open(bad, "w") as f:
        f.write("\n".join(synth_rows([67.0, 67.0, 67.0])) + "\n")
    rc, _, err = analyze(bad)
    check("rows without a header line: status 2", rc == 2 and "does not belong" in err, (rc, err))
    with open(bad, "w") as f:
        f.write("-- binary bw_old kernel read threads 1 cpus 2 bytes 8M round 1 load 0.10 utc 18:12:59\n" + "\n".join(synth_rows([67.0, 67.0, 67.0])) + "\n")
    rc, _, err = analyze(bad)
    check("a file with headers of run_kernels.sh given as H2.csv: status 2", rc == 2 and "not a file of run_h2.sh" in err, (rc, err))
    rc, _, err = analyze(os.path.join(top, "missing.csv"))
    check("a file that does not exist: status 2", rc == 2)
    r = subprocess.run([sys.executable, os.path.join(A, "h2_analyze.py"), "--results", res], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    check("h2_analyze.py as a program: status 0 and the same text as the function", r.returncode == 0 and r.stdout == text4, r.stderr)


if __name__ == "__main__":
    sys.exit(main())
