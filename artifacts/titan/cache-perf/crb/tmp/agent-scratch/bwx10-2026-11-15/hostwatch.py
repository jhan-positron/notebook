#!/usr/bin/env python3
"""hostwatch.py - host sampler: what the kernel does on one CPU while one process runs.

Usage: hostwatch.py --pid PID --cpu N --out FILE [--hz 20] [--max-s 120]

It only reads files under /proc. It pins nothing: the caller pins it (taskset) to a CPU
other than N. It ends when PID is gone, after --max-s seconds, or on SIGTERM or SIGINT.
Exit status 0 in all three cases, 2 for a usage error, 1 if an error outside a sample ended it.

Output file. Lines that start with "#" are header or footer lines:
  # hostwatch v1 pid=.. cpu=.. hz=.. max_s=..
  # clocks mono_ns=.. boot_ns=.. real_ns=..     CLOCK_MONOTONIC, CLOCK_BOOTTIME, CLOCK_REALTIME, read together
  # target starttime_ticks=.. clk_tck=.. comm=..   field 22 of /proc/PID/stat (ticks after boot) and SC_CLK_TCK
  # sampler pid=.. allowed_cpus=..              this process and the CPUs that it may run on
  # th tid=.. pid=.. comm=..                    one line per thread of the host whose last CPU was N at the start
  # scan threads=.. on_cpu=.. took_ms=..
  # end reason=pid_gone|max_s|signal|error samples=.. missed=.. max_sample_us=.. errors=..
                                                errors: samples or scan parts that raised an error. Such a sample
                                                writes the line "<t_mono_ns> hw.error:=<error type>" and the
                                                sampler goes on. reason=error: an error outside a sample ended it.
Sample lines:
  <t_mono_ns> key=delta key:=value ...          only when something changed since the last sample
                                                (a key that appears after the first sample: key:=its value)
  <t_mono_ns> ABS key=value ...                 every 5 s, and as the first line: all absolute values.
                                                With a delta line of the same time, the delta line comes first.
"key=delta" is the change of a counter. "key:=value" is a new state, not a difference
(a CPU number, "na" for a value that could not be read, a thread that appeared or left).

Keys:
  m.<f>            main thread of the target (tid == PID)
  w.<f>, w2.<f>..  other threads of the target in the order they appear (bwx8: w is the pinned worker)
                   <f>: run_ns wait_ns slices (schedstat), nvcsw nivcsw (status),
                        minflt majflt utime stime (stat; utime and stime in clock ticks),
                        cpu (state: the CPU it ran on last), tid (state)
  cpu.<f>          the cpuN line of /proc/schedstat: yld legacy sched goidle ttwu ttwu_local
                   run_ns wait_ns pcount
  sirq.<NAME>      column N of /proc/softirqs
  th.<tid>.<comm>.<f>   a thread of another process whose last CPU is N: run_ns wait_ns slices.
                   The comm is read again when the thread ran (the comm of a kworker names its work).
                   th.<tid>.<comm>.new:=<slices> a thread found on CPU N by a later scan (every 2 s);
                   .left:=<cpu> it ran on another CPU and is dropped; .gone:=1 it ended.
  vm.<key>         every key of /proc/vmstat whose value changed
  irq.<label>[.<description>]   column N of every row of /proc/interrupts, read twice per second
  hw.missed        sample slots that were skipped because a sample or a scan ran long
"""
import argparse
import os
import re
import signal
import sys
import time

CPU_FIELDS = ["yld", "legacy", "sched", "goidle", "ttwu", "ttwu_local", "run_ns", "wait_ns", "pcount"]
BAD = re.compile(r"[^A-Za-z0-9_/:+.@-]")
CLOCK_BOOTTIME = getattr(time, "CLOCK_BOOTTIME", 7)
ABS_PERIOD_NS = 5 * 10 ** 9
SCAN_PERIOD_NS = 2 * 10 ** 9
MAX_FOREIGN = 512


class Stop(Exception):
    pass


def on_signal(signum, frame):
    raise Stop()


def clock_ns(clock):
    if hasattr(time, "clock_gettime_ns"):
        return time.clock_gettime_ns(clock)
    return int(time.clock_gettime(clock) * 1e9)


def mono():
    return clock_ns(time.CLOCK_MONOTONIC)


def clean(text):
    return BAD.sub("_", text) or "_"


class Src:
    """One /proc file, opened once and read again from offset 0. A read that fails is tried
    once more after a new open. read() returns bytes, or None if the file cannot be read.
    single: a per-thread file (stat, status, schedstat). The kernel gives it in one piece, so one
    read holds it. Every other file is read until a read returns nothing: the kernel gives
    /proc/vmstat and /proc/interrupts in pieces of about one memory page (4 KiB on many hosts),
    and a shorter first piece does not mean that the file has ended."""

    def __init__(self, path, single=False):
        self.path, self.fd, self.single = path, -1, single

    def _read(self, upto):
        if self.fd < 0:
            self.fd = os.open(self.path, os.O_RDONLY)
        parts, off = [], 0
        while True:
            b = os.pread(self.fd, 1 << 16, off)
            if not b:
                break
            parts.append(b)
            off += len(b)
            if upto is not None:
                if upto(b"".join(parts)):
                    break
            elif self.single and len(b) < (1 << 16):
                break                      # a per-thread file: one read holds it
        return b"".join(parts)

    def read(self, upto=None):
        for _ in (0, 1):
            try:
                return self._read(upto)
            except OSError:
                self.close()
        return None

    def close(self):
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1


def stat_fields(data):
    """(comm, fields after the comm) of a stat file; field k of proc(5) is fields[k - 3]."""
    try:
        text = data.decode("ascii", "replace")
        a, b = text.index("("), text.rindex(")")
        return text[a + 1:b], text[b + 2:].split()
    except (ValueError, AttributeError):
        return None, None


def column_table(data, cpu):
    """Rows of /proc/softirqs or /proc/interrupts: [(label, value of column cpu, description)]."""
    rows = []
    if data is None:
        return None
    lines = data.split(b"\n")
    head = lines[0].split()
    try:
        col = head.index(b"CPU%d" % cpu)
    except ValueError:
        return None
    for line in lines[1:]:
        label, sep, rest = line.partition(b":")
        if not sep:
            continue
        parts = rest.split(None, col + 1)
        if len(parts) <= col or not parts[col].isdigit():
            continue
        rows.append((label.strip(), int(parts[col]), rest, len(head)))
    return rows


class Watch:
    def __init__(self, pid, cpu, out):
        self.pid, self.cpu, self.out = pid, cpu, out
        self.prev = {}                      # key -> last value (int, str, or None for "na")
        self.threads = {}                   # tid -> (prefix, schedstat, status, stat) of the target
        self.nworkers = 0
        self.foreign = {}                   # tid -> [pid, comm, schedstat Src, stat Src]
        self.schedstat = Src("/proc/schedstat")
        self.softirqs = Src("/proc/softirqs")
        self.vmstat = Src("/proc/vmstat")
        self.interrupts = Src("/proc/interrupts")
        self.irq_names = {}
        self.cpu_tag = b"\ncpu%d " % cpu
        self.events = []                    # "key:=value" items made outside a sample
        self.scan = None
        self.scan_count = 0

    # ---- the target ----
    def target(self, cur):
        """Reads every thread of the target. Returns False if the target is gone."""
        try:
            tids = os.listdir("/proc/%d/task" % self.pid)
        except OSError:
            return False
        alive = False
        for name in tids:
            tid = int(name)
            t = self.threads.get(tid)
            if t is None:
                if tid == self.pid:
                    pre = "m"
                else:
                    self.nworkers += 1
                    pre = "w" if self.nworkers == 1 else "w%d" % self.nworkers
                base = "/proc/%d/task/%d/" % (self.pid, tid)
                t = self.threads[tid] = (pre, Src(base + "schedstat", True), Src(base + "status", True), Src(base + "stat", True))
            pre = t[0]
            cur[pre + ".tid"] = tid
            f = (t[1].read() or b"").split()
            for i, k in enumerate(("run_ns", "wait_ns", "slices")):
                cur[pre + "." + k] = int(f[i]) if len(f) == 3 and f[i].isdigit() else None
            s = t[2].read() or b""
            for k, tag in (("nvcsw", b"\nvoluntary_ctxt_switches:"), ("nivcsw", b"\nnonvoluntary_ctxt_switches:")):
                i = s.find(tag)
                v = s[i + len(tag):].split(None, 1)[:1] if i >= 0 else []
                cur[pre + "." + k] = int(v[0]) if v and v[0].isdigit() else None
            _, sf = stat_fields(t[3].read())
            ok = sf is not None and len(sf) > 36
            for k, i in (("minflt", 7), ("majflt", 9), ("utime", 11), ("stime", 12)):
                cur[pre + "." + k] = int(sf[i]) if ok else None
            cur[pre + ".cpu"] = sf[36] if ok else None
            if ok and sf[0] not in ("Z", "X"):
                alive = True
        for tid in [t for t in self.threads if str(t) not in tids]:
            for src in self.threads.pop(tid)[1:]:
                src.close()
        return alive

    # ---- the CPU ----
    def cpu_line(self, cur):
        tag = self.cpu_tag
        data = self.schedstat.read(lambda b: b.find(b"\n", b.find(tag) + 1) > 0 if tag in b else False)
        i = data.find(tag) if data else -1
        if i < 0:
            cur["cpu.pcount"] = None
            return
        f = data[i + len(tag):].split(b"\n", 1)[0].split()
        for n, v in enumerate(f):
            name = CPU_FIELDS[n] if len(f) == len(CPU_FIELDS) else "f%d" % (n + 1)
            cur["cpu." + name] = int(v) if v.isdigit() else None

    def softirq(self, cur):
        rows = column_table(self.softirqs.read(), self.cpu)
        if rows is None:
            cur["sirq.TIMER"] = None
            return
        for label, v, _, _ in rows:
            cur["sirq." + clean(label.decode("ascii", "replace"))] = v

    def irq(self, cur):
        rows = column_table(self.interrupts.read(), self.cpu)
        if rows is None:
            cur["irq.na"] = None
            return
        for label, v, rest, ncpu in rows:
            name = self.irq_names.get(label)
            if name is None:
                desc = "_".join(x.decode("ascii", "replace") for x in rest.split()[ncpu:])
                name = "irq." + clean(label.decode("ascii", "replace"))
                if desc:
                    name += "." + clean(desc)[:48]
                self.irq_names[label] = name
            cur[name] = v

    def vm(self, cur):
        data = self.vmstat.read()
        if data is None:
            cur["vm.na"] = None
            return
        for line in data.split(b"\n"):
            k, _, v = line.partition(b" ")
            if v.isdigit():
                cur["vm." + k.decode("ascii", "replace")] = int(v)

    # ---- threads of other processes on the CPU ----
    def foreign_sample(self, cur):
        for tid in list(self.foreign):
            ent = self.foreign[tid]
            f = (ent[2].read() or b"").split()
            base = "th.%d.%s." % (tid, ent[1])
            if len(f) != 3:
                self.events.append(base + "gone:=1")
                self.drop(tid)
                continue
            slices = int(f[2])
            old = self.prev.get(("th", tid))
            if old is not None and slices != old[2]:
                # It ran: read the comm again, and the CPU it ran on last.
                comm, sf = stat_fields(ent[3].read())
                if comm is not None and len(sf) > 36:
                    if clean(comm) != ent[1]:
                        ent[1] = clean(comm)
                        base = "th.%d.%s." % (tid, ent[1])
                    if int(sf[36]) != self.cpu:
                        self.events.append("%sleft:=%s" % (base, sf[36]))
                        self.drop(tid)
                        continue
            cur[("th", tid)] = (int(f[0]), int(f[1]), slices)

    def drop(self, tid):
        ent = self.foreign.pop(tid)
        ent[2].close()
        ent[3].close()
        self.prev.pop(("th", tid), None)

    def scanner(self, first):
        """A generator that walks all threads of the host once. It yields after every process,
        so that the caller can stop at a deadline. New threads on the CPU are tracked."""
        me = os.getpid()
        n = 0
        try:
            pids = [d for d in os.listdir("/proc") if d.isdigit()]
        except OSError:
            pids = []
        for name in pids:
            pid = int(name)
            if pid == self.pid or pid == me:
                continue
            try:
                tids = os.listdir("/proc/%s/task" % name)
            except OSError:
                continue
            for t in tids:
                tid = int(t)
                n += 1
                if tid in self.foreign:
                    continue
                path = "/proc/%s/task/%s/stat" % (name, t)
                try:
                    fd = os.open(path, os.O_RDONLY)
                    try:
                        data = os.read(fd, 4096)
                    finally:
                        os.close(fd)
                except OSError:
                    continue
                comm, sf = stat_fields(data)
                if comm is None or len(sf) <= 36 or int(sf[36]) != self.cpu or len(self.foreign) >= MAX_FOREIGN:
                    continue
                ent = [pid, clean(comm), Src("/proc/%s/task/%s/schedstat" % (name, t), True), Src(path, True)]
                f = (ent[2].read() or b"").split()
                if len(f) != 3:
                    ent[2].close()
                    continue
                self.foreign[tid] = ent
                self.prev[("th", tid)] = (int(f[0]), int(f[1]), int(f[2]))
                if first:
                    self.out.write("# th tid=%d pid=%d comm=%s\n" % (tid, pid, ent[1]))
                else:
                    self.events.append("th.%d.%s.new:=%s" % (tid, ent[1], f[2].decode()))
            yield False
        self.scan_count = n
        yield True

    # ---- one sample ----
    def sample(self, t, with_irq, absolute, first):
        """Returns (target alive, text of the line or None)."""
        cur = {}
        alive = self.target(cur)
        self.cpu_line(cur)
        self.softirq(cur)
        self.foreign_sample(cur)
        self.vm(cur)
        if with_irq:
            self.irq(cur)
        items = self.events
        self.events = []
        prev = self.prev
        for k, v in cur.items():
            old = prev.get(k, v)
            if isinstance(k, tuple):                     # a thread of another process
                if v != old:
                    base = "th.%d.%s." % (k[1], self.foreign[k[1]][1])
                    for i, name in enumerate(("run_ns", "wait_ns", "slices")):
                        if v[i] != old[i]:
                            items.append("%s%s=%d" % (base, name, v[i] - old[i]))
            elif k not in prev:
                if not first:                            # a key that appeared after the first sample
                    items.append("%s:=%s" % (k, "na" if v is None else v))
            elif v != old:
                if isinstance(v, int) and isinstance(old, int):
                    items.append("%s=%d" % (k, v - old))
                else:
                    items.append("%s:=%s" % (k, "na" if v is None else v))
            prev[k] = v
        line = None
        if absolute:
            full = []
            for k in sorted(prev, key=str):
                v = prev[k]
                if isinstance(k, tuple):
                    if k[1] in self.foreign:
                        base = "th.%d.%s." % (k[1], self.foreign[k[1]][1])
                        full += ["%s%s=%d" % (base, name, v[i]) for i, name in enumerate(("run_ns", "wait_ns", "slices"))]
                elif not (k.startswith("irq.") and v == 0):
                    full.append("%s=%s" % (k, "na" if v is None else v))
            line = "%d ABS %s\n" % (t, " ".join(full))
        if items and not first:                          # the first line of the file is the absolute line
            line = "%d %s\n%s" % (t, " ".join(items), line or "")
        return alive, line


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--cpu", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hz", type=float, default=20.0)
    ap.add_argument("--max-s", type=float, default=120.0)
    a = ap.parse_args()
    if a.pid < 1 or a.cpu < 0 or not 0.1 <= a.hz <= 1000 or a.max_s <= 0:
        ap.error("--pid above 0, --cpu 0 or above, --hz from 0.1 to 1000, --max-s above 0")
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    out = open(a.out, "w", buffering=1 << 16)
    w = Watch(a.pid, a.cpu, out)
    period = int(1e9 / a.hz)
    irq_every = max(1, int(round(a.hz / 2)))
    samples = missed = max_us = errors = 0
    reason = "pid_gone"
    status = 0
    try:
        t0 = mono()
        out.write("# hostwatch v1 pid=%d cpu=%d hz=%g max_s=%g\n" % (a.pid, a.cpu, a.hz, a.max_s))
        out.write("# clocks mono_ns=%d boot_ns=%d real_ns=%d\n" % (t0, clock_ns(CLOCK_BOOTTIME), clock_ns(time.CLOCK_REALTIME)))
        comm, sf = stat_fields(Src("/proc/%d/stat" % a.pid).read())
        out.write("# target starttime_ticks=%s clk_tck=%d comm=%s\n" % (
            sf[19] if sf and len(sf) > 19 else "na", os.sysconf("SC_CLK_TCK"), clean(comm) if comm else "na"))
        out.write("# sampler pid=%d allowed_cpus=%s\n" % (os.getpid(), ",".join(map(str, sorted(os.sched_getaffinity(0))))))
        for _ in w.scanner(True):
            pass
        out.write("# scan threads=%d on_cpu=%d took_ms=%.1f\n" % (w.scan_count, len(w.foreign), (mono() - t0) / 1e6))
        out.flush()
        t0 = mono()
        last_abs = last_scan = last_flush = t0
        slot = 0
        first = True
        while True:
            t = mono()
            if t - t0 >= a.max_s * 1e9:
                reason = "max_s"
                break
            absolute = first or t - last_abs >= ABS_PERIOD_NS
            try:
                alive, line = w.sample(t, samples % irq_every == 0, absolute, first)
            except Stop:
                raise
            except Exception as e:           # an error must not end the sampling, and must not pass as "pid_gone"
                errors += 1
                alive, line = os.path.exists("/proc/%d" % a.pid), "%d hw.error:=%s\n" % (t, clean(type(e).__name__))
            first = False
            if absolute:
                last_abs = t
            if line:
                out.write(line)
            samples += 1
            done = mono()
            max_us = max(max_us, (done - t) // 1000)
            if not alive:
                break
            if done - last_flush >= 10 ** 9:
                out.flush()
                last_flush = done
            # The next slot on the fixed grid t0 + k x period.
            nxt = (done - t0) // period + 1
            deadline = t0 + nxt * period
            # A part of the host scan, in the time that is left before the next sample.
            if w.scan is None and done - last_scan >= SCAN_PERIOD_NS:
                w.scan, last_scan = w.scanner(False), done
            while w.scan is not None and mono() < deadline - period // 4:
                try:
                    if next(w.scan):
                        w.scan = None
                except Stop:
                    raise
                except Exception as e:       # this scan ends; the next one starts after 2 s
                    errors += 1
                    w.scan = None
                    w.events.append("hw.error:=scan_%s" % clean(type(e).__name__))
            if nxt > slot + 1:
                missed += nxt - slot - 1
                w.events.append("hw.missed:=%d" % missed)
            slot = nxt
            wait = deadline - mono()
            if wait > 0:
                time.sleep(wait / 1e9)
    except Stop:
        reason = "signal"
    except Exception as e:                   # an error outside a sample (header, first scan, output file)
        reason, status = "error", 1
        sys.stderr.write("hostwatch: %s: %s\n" % (type(e).__name__, e))
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        out.write("# end reason=%s samples=%d missed=%d max_sample_us=%d errors=%d\n" % (reason, samples, missed, max_us, errors))
        out.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
